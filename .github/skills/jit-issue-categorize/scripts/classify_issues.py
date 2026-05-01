#!/usr/bin/env python3
"""Classify JIT issues via Copilot subagent invocations and write a CSV report.

Usage:
    python classify_issues.py <issues_json> <output_csv> [options]

Options:
    --concurrency N   Number of parallel subagent invocations (default: 5).
    --timeout SECS    Timeout per subagent invocation in seconds (default: 120).
    --resume          If the output CSV already exists, skip issues that have
                      already been classified.

<issues_json>  Consolidated JSON file produced by ``extract_issues.py``.
<output_csv>   Path to the CSV file to write.

For each issue, this script invokes the Copilot CLI as a subagent with the
prompt at ``.github/skills/jit-issue-categorize/references/subagent-prompt``,
parses the resulting JSON classification, and writes the combined results to a
CSV file.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Constants ───────────────────────────────────────────────────────────────

CSV_COLUMNS = [
    "Github Issue ID",
    "Category",
    "Theme",
    "SkillLevel",
    "Architecture",
    "OS",
    "Stress",
    "NeedsAttention",
    "AttentionReason",
    "Milestone",
    "Assignees",
    "Full link",
]

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SUBAGENT_PROMPT_REF = (
    ".github/skills/jit-issue-categorize/references/subagent-prompt"
)

_JSON_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


# ── Subagent invocation ────────────────────────────────────────────────────

def _build_copilot_command(issue_number: int, output_file: str) -> list[str]:
    """Build the copilot CLI command for classifying one issue.

    The subagent is instructed to write its JSON classification to
    *output_file* so that this script can read it back reliably, avoiding
    the need to parse the rich terminal UI output from ``copilot``.
    """
    prompt = (
        f"Please use @{_SUBAGENT_PROMPT_REF} for issue #{issue_number}. "
        f"IMPORTANT: Write ONLY the final JSON classification object to the "
        f"file at '{output_file}'. The file must contain nothing but the "
        f"JSON object — no markdown fences, no commentary."
    )
    return [
        "copilot",
        "--yolo",
        "--model", "gpt-5.4",
        "--autopilot",
        "--no-ask-user",
        "-p", prompt,
    ]


def _read_json_file(path: str) -> dict | None:
    """Read and parse a JSON classification from *path*.

    Falls back to regex extraction in case the subagent wrapped the JSON
    in markdown fences or other text.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read().strip()
    except OSError:
        return None
    if not text:
        return None

    # Fast-path: the file contains valid JSON directly.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "category" in obj:
            return obj
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON from surrounding text / markdown fences.
    for match in _JSON_RE.finditer(text):
        try:
            obj = json.loads(match.group())
            if "category" in obj:
                return obj
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def _classify_one(issue: dict, timeout: int) -> dict:
    """Invoke the copilot subagent for a single issue and return a row dict."""
    number = issue["number"]

    # Create a temp file for the subagent to write its JSON result into.
    fd, tmp_path = tempfile.mkstemp(suffix=f"_issue{number}.json", prefix="jit_classify_")
    os.close(fd)

    try:
        cmd = _build_copilot_command(number, tmp_path)
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(_REPO_ROOT),
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT: issue #{number}", file=sys.stderr)
            return _error_row(issue)
        except FileNotFoundError:
            print(
                "ERROR: 'copilot' command not found. Ensure the Copilot CLI is "
                "installed and on your PATH.",
                file=sys.stderr,
            )
            sys.exit(1)

        parsed = _read_json_file(tmp_path)
        if parsed is None:
            print(f"  NO JSON: issue #{number}", file=sys.stderr)
            return _error_row(issue)

        return _build_row(issue, parsed)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _error_row(issue: dict) -> dict:
    """Return a CSV row dict with ERROR for issues that failed classification."""
    return {
        "number": issue["number"],
        "category": "ERROR",
        "theme": "",
        "skill": "",
        "arch": "",
        "os": "",
        "stress": "",
        "needs_attention": "",
        "attention_reason": "",
        "milestone": issue.get("milestone", ""),
        "assignees": ";".join(issue.get("assignees", [])),
        "link": f"https://github.com/dotnet/runtime/issues/{issue['number']}",
    }


def _build_row(issue: dict, parsed: dict) -> dict:
    """Merge subagent JSON output with issue metadata into a CSV row dict."""
    themes = parsed.get("themes", [])
    if isinstance(themes, list):
        theme_str = ";".join(str(t) for t in themes[:2])
    else:
        theme_str = str(themes)

    needs_attention = parsed.get("needsAttention", False)
    if isinstance(needs_attention, bool):
        needs_attention_str = "yes" if needs_attention else "no"
    else:
        needs_attention_str = str(needs_attention).lower()

    return {
        "number": issue["number"],
        "category": parsed.get("category", "ERROR"),
        "theme": theme_str,
        "skill": parsed.get("skillLevel", ""),
        "arch": parsed.get("architecture", ""),
        "os": parsed.get("os", ""),
        "stress": parsed.get("stress", ""),
        "needs_attention": needs_attention_str,
        "attention_reason": parsed.get("attentionReason", "") if needs_attention_str == "yes" else "",
        "milestone": issue.get("milestone", ""),
        "assignees": ";".join(issue.get("assignees", [])),
        "link": f"https://github.com/dotnet/runtime/issues/{issue['number']}",
    }


# ── Resume support ──────────────────────────────────────────────────────────

def _load_existing_csv(csv_path: str) -> set[int]:
    """Read an existing CSV and return the set of already-classified issue numbers."""
    done: set[int] = set()
    if not os.path.exists(csv_path):
        return done
    with open(csv_path, encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # skip header
        for row in reader:
            if row:
                try:
                    done.add(int(row[0]))
                except ValueError:
                    pass
    return done


# ── CSV output ──────────────────────────────────────────────────────────────

def write_csv(
    classifications: list[dict],
    output_path: str,
    append: bool = False,
) -> None:
    """Write (or append to) the final CSV."""
    mode = "a" if append else "w"
    with open(output_path, mode, newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if not append:
            writer.writerow(CSV_COLUMNS)
        for c in classifications:
            writer.writerow([
                c["number"],
                c["category"],
                c["theme"],
                c["skill"],
                c["arch"],
                c["os"],
                c["stress"],
                c["needs_attention"],
                c["attention_reason"],
                c["milestone"],
                c["assignees"],
                c["link"],
            ])
    action = "Appended" if append else "Wrote"
    print(f"{action} {len(classifications)} rows -> {output_path}")


# ── Summary ─────────────────────────────────────────────────────────────────

def print_summary(classifications: list[dict]) -> None:
    """Print a human-readable summary of the classifications."""
    cats = Counter(c["category"] for c in classifications)
    themes_counter: Counter = Counter()
    for c in classifications:
        for t in c["theme"].split(";"):
            if t:
                themes_counter[t] += 1

    attention_count = sum(1 for c in classifications if c["needs_attention"] == "yes")
    error_count = sum(1 for c in classifications if c["category"] == "ERROR")

    print(f"\n{'='*60}")
    print(f"Total issues classified: {len(classifications)}")
    print(f"{'='*60}")
    print("\nBreakdown by category:")
    for cat, cnt in cats.most_common():
        print(f"  {cat:20s} {cnt:5d}")
    print("\nTop 15 themes:")
    for theme, cnt in themes_counter.most_common(15):
        print(f"  {theme:25s} {cnt:5d}")
    print(f"\nNeeds attention: {attention_count}")
    if error_count:
        print(f"Classification errors: {error_count} (re-run with --resume)")
    print()


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify JIT issues via Copilot subagent invocations."
    )
    parser.add_argument("issues_json", help="Consolidated JSON from extract_issues.py")
    parser.add_argument("output_csv", help="Path to the output CSV file")
    parser.add_argument(
        "--concurrency", type=int, default=5,
        help="Number of parallel subagent invocations (default: 5)",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="Timeout per subagent invocation in seconds (default: 120)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip issues already present in the output CSV",
    )
    args = parser.parse_args()

    with open(args.issues_json, encoding="utf-8") as fh:
        issues = json.load(fh)

    already_done: set[int] = set()
    if args.resume:
        already_done = _load_existing_csv(args.output_csv)
        if already_done:
            print(f"Resuming: {len(already_done)} issues already classified")

    remaining = [i for i in issues if i["number"] not in already_done]
    total = len(remaining)
    print(f"Classifying {total} issues (concurrency={args.concurrency}, "
          f"timeout={args.timeout}s)...")

    classifications: list[dict] = []
    completed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {
            pool.submit(_classify_one, issue, args.timeout): issue
            for issue in remaining
        }
        for future in as_completed(futures):
            row = future.result()
            classifications.append(row)
            completed += 1
            if completed % 10 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(
                    f"  Progress: {completed}/{total} "
                    f"({rate:.1f} issues/sec)",
                    file=sys.stderr,
                )

    classifications.sort(key=lambda c: c["number"], reverse=True)
    write_csv(classifications, args.output_csv, append=args.resume and bool(already_done))
    print_summary(classifications)


if __name__ == "__main__":
    main()
