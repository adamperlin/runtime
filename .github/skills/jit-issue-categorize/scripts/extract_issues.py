#!/usr/bin/env python3
"""Extract essential fields from raw GitHub search-issues JSON responses.

Usage:
    python extract_issues.py <input_dir> <output_file>

<input_dir>  Directory containing one or more JSON files produced by the
             GitHub MCP ``search_issues`` tool (each file is one page of
             results).
<output_file> Path to the consolidated JSON file that will be written.

Each output record contains:
    number, title, body (truncated to 2000 chars), labels, assignees,
    milestone, reactions_plus1, reactions_total.
"""

import json
import os
import sys


def extract(item: dict) -> dict:
    """Return a slim dict with the fields needed for classification."""
    labels = [label["name"] for label in item.get("labels", [])]
    assignees = [a["login"] for a in item.get("assignees", [])]
    milestone = item.get("milestone") or {}
    reactions = item.get("reactions", {})
    return {
        "number": item["number"],
        "title": item["title"],
        "body": (item.get("body") or "")[:2000],
        "labels": labels,
        "assignees": assignees,
        "milestone": milestone.get("title", ""),
        "reactions_plus1": reactions.get("+1", 0),
        "reactions_total": reactions.get("total_count", 0),
    }


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_dir = sys.argv[1]
    output_file = sys.argv[2]

    all_issues: list[dict] = []
    seen: set[int] = set()

    for fname in sorted(os.listdir(input_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(input_dir, fname)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        items = data.get("items", data) if isinstance(data, dict) else data
        for item in items:
            num = item["number"]
            if num not in seen:
                seen.add(num)
                all_issues.append(extract(item))

    all_issues.sort(key=lambda i: i["number"], reverse=True)
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(all_issues, fh, ensure_ascii=False, indent=1)

    print(f"Extracted {len(all_issues)} unique issues -> {output_file}")


if __name__ == "__main__":
    main()
