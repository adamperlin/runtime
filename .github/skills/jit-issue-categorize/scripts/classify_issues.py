#!/usr/bin/env python3
"""Classify JIT issues and write a CSV report.

Usage:
    python classify_issues.py <issues_json> <output_csv>

<issues_json>  Consolidated JSON file produced by ``extract_issues.py``.
<output_csv>   Path to the CSV file to write.

The classifier uses heuristics based on labels, title keywords, and body
keywords to assign category, theme, skill level, cost, impact, architecture,
OS, and stress flag for each issue.
"""

import csv
import json
import re
import sys

# ── Categories ──────────────────────────────────────────────────────────────

CATEGORIES = [
    "correctness", "performance", "cq", "basic-cq", "throughput",
    "proposal", "implementation", "eng-sys", "design", "planning",
    "documentation", "testing", "question", "reach", "security",
]

# label -> category mapping (first match wins)
_LABEL_TO_CATEGORY: list[tuple[str, str]] = [
    ("bug", "correctness"),
    ("tenet-performance", "performance"),
    ("api-suggestion", "proposal"),
    ("question", "question"),
    ("documentation", "documentation"),
    ("tracking", "planning"),
]

# keyword patterns (applied to lower-cased title+body)
_KW_CATEGORY: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(crash|wrong result|miscompil|assert\b|assertion fail|access violation|\bav\b|ice\b|internal compiler error|silent bad codegen|sigfault|sigsegv|incorrect result|incorrect codegen|invalid codegen|wrong codegen)", re.I), "correctness"),
    (re.compile(r"\b(regression|slower|perf regression|throughput regression)", re.I), "performance"),
    (re.compile(r"\b(code quality|codegen quality|missed optimiz|suboptimal|unnecessary instruction|redundant|missed opt)", re.I), "cq"),
    (re.compile(r"\b(basic code quality|simple optimiz|low.hanging|obvious missed)", re.I), "basic-cq"),
    (re.compile(r"\b(jit throughput|compilation time|jit memory|compile speed|jit time)", re.I), "throughput"),
    (re.compile(r"\bapi.?proposal\b", re.I), "proposal"),
    (re.compile(r"\b(implement|add support for|enable\b|new feature)", re.I), "implementation"),
    (re.compile(r"\b(ci\b|build infra|test infra|tooling|superpmi|pipeline|eng.sys)", re.I), "eng-sys"),
    (re.compile(r"\b(design|architecture|rfc|refactor)", re.I), "design"),
    (re.compile(r"\b(plan|roadmap|tracking issue|umbrella)", re.I), "planning"),
    (re.compile(r"\b(doc|comment|readme)", re.I), "documentation"),
    (re.compile(r"\b(test coverage|stress test|test infra)", re.I), "testing"),
    (re.compile(r"\b(how to|why does|is it possible)", re.I), "question"),
    (re.compile(r"\b(stretch goal|nice to have|long.term|aspirational)", re.I), "reach"),
    (re.compile(r"\b(security|cve|vulnerability|hardening)", re.I), "security"),
]

# ── Themes ──────────────────────────────────────────────────────────────────

# Map of keyword/label pattern -> theme
_THEME_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bcse\b", re.I), "cse"),
    (re.compile(r"\bsuper.?pmi\b|\bspmi\b", re.I), "super-pmi"),
    (re.compile(r"\bredundant.branch", re.I), "redundant-branches"),
    (re.compile(r"\bloop.opt|loop.?unroll|loop.?cloning|loop.?hoist|loop.?invar|loop.?iv|iv.?widen", re.I), "loop-opt"),
    (re.compile(r"\blower", re.I), "lower"),
    (re.compile(r"\bvector|simd|Vector128|Vector256|Vector512|System\.Runtime\.Intrinsics", re.I), "vector-codegen"),
    (re.compile(r"\btier|tiered|osr|on.?stack.?replac", re.I), "tiering"),
    (re.compile(r"\bgc.?info|gc.?reporting", re.I), "gc-info"),
    (re.compile(r"\bregister.?alloc|regalloc|lsra\b", re.I), "register-allocator"),
    (re.compile(r"\bpgo|profile.?guided|profile.?feedback|dynamic.?pgo", re.I), "profile-feedback"),
    (re.compile(r"\bfloat|double|fp\b|floating.?point|System\.Math\b", re.I), "floating-point"),
    (re.compile(r"\bdelegate", re.I), "delegates"),
    (re.compile(r"\bassertion.?prop", re.I), "assertion-prop"),
    (re.compile(r"\bcall.?conv|calling.?convention|\bSysV\b|\bABI\b", re.I), "calling-convention"),
    (re.compile(r"\btail.?call", re.I), "tail-call"),
    (re.compile(r"\binlin", re.I), "inlining"),
    (re.compile(r"\bready.?to.?run|r2r|crossgen", re.I), "ready-to-run"),
    (re.compile(r"\bimporter\b", re.I), "importer"),
    (re.compile(r"\bbounds.?check", re.I), "bounds-checks"),
    (re.compile(r"\bbuild.?break|build.?fail|build.?error|build infra", re.I), "build"),
    (re.compile(r"\bstruct\b", re.I), "structs"),
    (re.compile(r"\bintrinsic|HWIntrinsic|avx\b|sse[0-9]?\b|neon\b|sve\b|bmi[0-9]?\b|fma\b|popcnt|lzcnt|tzcnt|pclmulqdq|aes\b|crc32|sha\b|AdvSimd|Arm\.|blsi|blsmsk|blsr|pdep|pext", re.I), "hardware-intrinsics"),
    (re.compile(r"\bdevirtualiz", re.I), "devirtualization"),
    (re.compile(r"\beh\b|exception.?handl", re.I), "eh"),
    (re.compile(r"\bvalue.?number", re.I), "value-numbering"),
    (re.compile(r"\bdiv\b|mod\b|rem\b|divis", re.I), "div-mod-rem"),
    (re.compile(r"\bemitt", re.I), "emitter"),
    (re.compile(r"\bpinning|pinned.?local", re.I), "pinning"),
    (re.compile(r"\btest.?coverage|test.?infra|stress.?test|test.?fail", re.I), "testing"),
    (re.compile(r"\bjit.?dump|spmi.?dump|disasm|natvis|gtDisp|gtGetLclVarName", re.I), "debug-dumps"),
    (re.compile(r"\bgeneric|typeof|__Canon", re.I), "generics"),
    (re.compile(r"\bzero.?init|initblk", re.I), "zero-init"),
    (re.compile(r"\bpinvoke|p/invoke|dllimport|marshal", re.I), "pinvoke"),
    (re.compile(r"\bblock.?layout", re.I), "block-layout"),
    (re.compile(r"\bnull.?check", re.I), "null-checks"),
    (re.compile(r"\bblock.?opt|block.?merg", re.I), "block-opts"),
    (re.compile(r"\balign", re.I), "alignment"),
    (re.compile(r"\bssa\b", re.I), "ssa"),
    (re.compile(r"\bdead.?code", re.I), "dead-code"),
    (re.compile(r"\baltjit|alt.?jit", re.I), "altjit"),
    (re.compile(r"\bliveness", re.I), "liveness"),
    (re.compile(r"\bprolog|epilog", re.I), "prolog-epilog"),
    (re.compile(r"\brange.?check", re.I), "range-check"),
    (re.compile(r"\bgc.?stress", re.I), "gc-stress"),
    (re.compile(r"\bosr\b", re.I), "osr"),
    (re.compile(r"\bdebug.?info", re.I), "debug-info"),
    (re.compile(r"\bbox", re.I), "boxing"),
    (re.compile(r"\bcopy.?prop", re.I), "copy-prop"),
    (re.compile(r"\bngen\b", re.I), "ngen"),
    (re.compile(r"\bbarrier|write.?barrier", re.I), "barriers"),
    (re.compile(r"\bmsil\b|cil\b|il\b.?gen", re.I), "msil"),
    (re.compile(r"\bminopts\b|min.?opt", re.I), "minopts"),
    (re.compile(r"\bmorph", re.I), "morph"),
    (re.compile(r"\bswitch", re.I), "switches"),
    (re.compile(r"\bvolatile\b", re.I), "volatile"),
    (re.compile(r"\bvararg", re.I), "varargs"),
    (re.compile(r"\bflowgraph|flow.?graph|\bbbNum\b|predecessor", re.I), "flowgraph"),
    (re.compile(r"\blarge.?method", re.I), "large-methods"),
    (re.compile(r"\bhelper", re.I), "helpers"),
    (re.compile(r"\binvalid.?il\b", re.I), "invalid-il"),
    (re.compile(r"\blong.?type|int64", re.I), "long-type"),
    (re.compile(r"\bref.?count", re.I), "ref-counts"),
    (re.compile(r"\binterpreter\b", re.I), "interpreter"),
    (re.compile(r"\bmd.?array|multi.?dim", re.I), "md-arrays"),
    (re.compile(r"\bstack.?alloc", re.I), "stack-allocation"),
    (re.compile(r"\baddress.{0,5}mode", re.I), "addressing-modes"),
    (re.compile(r"\bmemory.?usage|jit.?memory", re.I), "memory-usage"),
    (re.compile(r"\bbenchmark.?infra|benchmark.?harness|BenchmarkDotNet", re.I), "benchmarks"),
    (re.compile(r"\btype.?intrinsic|typeof|IsValueType", re.I), "type-intrinsics"),
    (re.compile(r"\bverif", re.I), "verification"),
    (re.compile(r"\bTYP_|signedness|normaliz.{0,10}type|type.{0,10}normaliz|zero.?ext|sign.?ext|\btype\s*checker\b", re.I), "jit-type-system"),
    (re.compile(r"\bconstant.{0,3}fold|const.{0,3}prop|fold.{0,10}constant", re.I), "constant-folding"),
    (re.compile(r"\bphysical.{0,3}promot", re.I), "physical-promotion"),
    (re.compile(r"\bunnecessary\s+(?:conditional|overflow|bounds?)\s*check|redundant\s*check|eliminate\s*bound|conditional.*ignored|check.*unexpectedly\s*ignored", re.I), "conditional-elimination"),
    (re.compile(r"\bbranchless|branch.?free|\bcmov\b|conditional\s*move|\bsetcc\b|if.?conversion|branchless\s*clamp", re.I), "branchless-codegen"),
    (re.compile(r"\basync\b|runtime.?async", re.I), "codegen"),
    (re.compile(r"\bexpression", re.I), "expression-opts"),
    (re.compile(r"\boptimiz", re.I), "optimization"),
    (re.compile(r"\bcodegen|code.?gen", re.I), "codegen"),
]

# label-name to theme
_LABEL_TO_THEME: dict[str, str] = {
    "optimization-cse": "cse",
    "optimization-inlining": "inlining",
    "optimization-loop-opt": "loop-opt",
    "optimization-register-allocator": "register-allocator",
    "optimization-devirtualization": "devirtualization",
    "optimization-assertion-prop": "assertion-prop",
    "optimization-value-numbering": "value-numbering",
    "optimization-copy-prop": "copy-prop",
    "optimization-dead-code": "dead-code",
    "JitStress": "gc-stress",
    "runtime-async": "codegen",
}

# ── Architecture / OS ──────────────────────────────────────────────────────

_ARCH_LABELS = {
    "arch-arm64": "arm64",
    "arch-arm32": "arm32",
    "arch-x64": "x64",
    "arch-x86": "x86",
}

_OS_LABELS = {
    "os-linux": "linux",
    "os-windows": "windows",
    "os-mac-os-x": "macos",
    "os-mac": "macos",
}

_ARCH_KW: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\barm64|aarch64\b", re.I), "arm64"),
    (re.compile(r"\barm32\b", re.I), "arm32"),
    (re.compile(r"\bx64|amd64|x86.64\b", re.I), "x64"),
    (re.compile(r"\bx86\b(?!.64)", re.I), "x86"),
]

_OS_KW: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\blinux|ubuntu|debian|fedora|centos|rhel\b", re.I), "linux"),
    (re.compile(r"\bwindows|win\b", re.I), "windows"),
    (re.compile(r"\bmacos|mac.?os|osx|darwin\b", re.I), "macos"),
]

_STRESS_RE = re.compile(
    r"DOTNET_JitStress|DOTNET_GCStress|DOTNET_JitStressModeNames|"
    r"\bstress.?test|gc.?stress|jit.?stress",
    re.I,
)


# ── Classification helpers ──────────────────────────────────────────────────

def _classify_category(issue: dict) -> str:
    labels = set(issue["labels"])
    text = (issue["title"] + " " + issue["body"]).lower()

    # Perf regression bot issues
    if issue["title"].startswith("[Perf]") or "regression" in issue["title"].lower():
        if "tenet-performance" in labels or "perf" in text:
            return "performance"

    # Label-based
    for lbl, cat in _LABEL_TO_CATEGORY:
        if lbl in labels:
            return cat

    # Keyword-based
    for pat, cat in _KW_CATEGORY:
        if pat.search(text):
            return cat

    return "cq"  # default for JIT issues


def _classify_themes(issue: dict) -> list[str]:
    labels = set(issue["labels"])
    text = issue["title"] + " " + issue["body"]
    themes: list[str] = []
    seen: set[str] = set()

    # Label-based
    for lbl, theme in _LABEL_TO_THEME.items():
        if lbl in labels and theme not in seen:
            themes.append(theme)
            seen.add(theme)

    # Keyword-based
    for pat, theme in _THEME_PATTERNS:
        if theme not in seen and pat.search(text):
            themes.append(theme)
            seen.add(theme)

    if not themes:
        themes = ["needs-triage"]

    return themes[:3]


def _classify_skill(issue: dict, category: str) -> str:
    labels = set(issue["labels"])
    if "good first issue" in labels or "help wanted" in labels:
        return "Beginner"
    if category in ("documentation", "question", "testing"):
        return "Beginner"
    if category in ("basic-cq", "eng-sys"):
        return "Intermediate"
    if category in ("correctness", "design", "planning"):
        return "Expert"
    text = (issue["title"] + " " + issue["body"]).lower()
    if any(kw in text for kw in ("register alloc", "fundamental", "major refactor", "new pass")):
        return "Expert"
    return "Intermediate"


def _classify_cost(issue: dict, category: str) -> str:
    if category in ("question", "documentation"):
        return "Low"
    if category in ("planning", "design"):
        return "High"
    text = (issue["title"] + " " + issue["body"]).lower()
    if any(kw in text for kw in ("tracking", "umbrella", "meta", "epic")):
        return "High"
    if any(kw in text for kw in ("simple", "trivial", "easy", "small")):
        return "Low"
    return "Medium"


def _classify_impact(issue: dict, category: str) -> str:
    if category == "correctness":
        return "High"
    if category == "question":
        return "Low"
    plus1 = issue.get("reactions_plus1", 0)
    if plus1 >= 10:
        return "High"
    if plus1 >= 3:
        return "Medium"
    if category in ("planning", "design"):
        return "Medium"
    return "Medium"


def _classify_arch(issue: dict) -> str:
    labels = set(issue["labels"])
    archs: set[str] = set()
    for lbl, arch in _ARCH_LABELS.items():
        if lbl in labels:
            archs.add(arch)
    text = issue["title"] + " " + issue["body"]
    for pat, arch in _ARCH_KW:
        if pat.search(text):
            archs.add(arch)
    if not archs:
        return "all"
    return ";".join(sorted(archs))


def _classify_os(issue: dict) -> str:
    labels = set(issue["labels"])
    oses: set[str] = set()
    for lbl, osname in _OS_LABELS.items():
        if lbl in labels:
            oses.add(osname)
    text = issue["title"] + " " + issue["body"]
    for pat, osname in _OS_KW:
        if pat.search(text):
            oses.add(osname)
    if not oses:
        return "all"
    return ";".join(sorted(oses))


def _classify_stress(issue: dict) -> str:
    text = issue["title"] + " " + issue["body"] + " ".join(issue["labels"])
    if _STRESS_RE.search(text):
        return "yes"
    return "no"


def classify(issue: dict) -> dict:
    """Return a classification dict for one issue."""
    cat = _classify_category(issue)
    themes = _classify_themes(issue, )
    return {
        "number": issue["number"],
        "category": cat,
        "theme": ";".join(themes),
        "skill": _classify_skill(issue, cat),
        "cost": _classify_cost(issue, cat),
        "impact": _classify_impact(issue, cat),
        "arch": _classify_arch(issue),
        "os": _classify_os(issue),
        "stress": _classify_stress(issue),
        "milestone": issue.get("milestone", ""),
        "assignees": ";".join(issue.get("assignees", [])),
        "link": f"https://github.com/dotnet/runtime/issues/{issue['number']}",
    }


# ── CSV output ──────────────────────────────────────────────────────────────

CSV_COLUMNS = [
    "Github Issue ID",
    "Category",
    "Theme",
    "SkillLevel",
    "Cost",
    "Impact",
    "Architecture",
    "OS",
    "Stress",
    "Milestone",
    "Assignees",
    "Full link",
    "Possible duplicate 1",
    "Possible duplicate 2",
    "Possible duplicate 3",
    "Possible duplicate 4",
]


def write_csv(
    classifications: list[dict],
    duplicates: dict[int, list[int]],
    output_path: str,
) -> None:
    """Write the final CSV."""
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for c in classifications:
            dups = duplicates.get(c["number"], [])
            dups_padded = (dups + ["", "", "", ""])[:4]
            writer.writerow([
                c["number"],
                c["category"],
                c["theme"],
                c["skill"],
                c["cost"],
                c["impact"],
                c["arch"],
                c["os"],
                c["stress"],
                c["milestone"],
                c["assignees"],
                c["link"],
                *dups_padded,
            ])
    print(f"Wrote {len(classifications)} rows -> {output_path}")


# ── Summary ─────────────────────────────────────────────────────────────────

def print_summary(classifications: list[dict]) -> None:
    """Print a human-readable summary of the classifications."""
    from collections import Counter

    cats = Counter(c["category"] for c in classifications)
    themes_counter: Counter = Counter()
    for c in classifications:
        for t in c["theme"].split(";"):
            if t:
                themes_counter[t] += 1

    print(f"\n{'='*60}")
    print(f"Total issues classified: {len(classifications)}")
    print(f"{'='*60}")
    print("\nBreakdown by category:")
    for cat, cnt in cats.most_common():
        print(f"  {cat:20s} {cnt:5d}")
    print("\nTop 15 themes:")
    for theme, cnt in themes_counter.most_common(15):
        print(f"  {theme:25s} {cnt:5d}")
    print()


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python classify_issues.py <issues.json> <output.csv>")
        sys.exit(1)

    issues_file = sys.argv[1]
    output_csv = sys.argv[2]

    with open(issues_file, encoding="utf-8") as fh:
        issues = json.load(fh)

    print(f"Classifying {len(issues)} issues...")
    classifications = [classify(issue) for issue in issues]

    # Duplicate detection
    print("Detecting possible duplicates (TF-IDF cosine similarity)...")
    from find_duplicates import find_duplicates
    duplicates = find_duplicates(issues, top_k=4, threshold=0.30)
    has_dups = sum(1 for v in duplicates.values() if v)
    print(f"  Found possible duplicates for {has_dups}/{len(issues)} issues")

    write_csv(classifications, duplicates, output_csv)
    print_summary(classifications)


if __name__ == "__main__":
    main()
