#!/usr/bin/env python3
"""Validate the structure of a JIT-issues CSV file.

Usage:
    python validate_csv.py <csv_file>

Checks:
- Header matches the expected column names.
- All rows have the correct number of columns.
- Category, SkillLevel, Stress, and NeedsAttention values are from allowed sets.
- Full link column is a valid GitHub issue URL.
"""

import csv
import re
import sys

EXPECTED_COLUMNS = [
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

VALID_CATEGORIES = {
    "cq", "basic-cq", "correctness", "performance", "throughput",
    "implementation", "proposal", "design", "planning", "eng-sys",
    "documentation", "testing", "question", "reach", "security",
    "ERROR",
}

VALID_SKILL = {"Beginner", "Intermediate", "Expert", ""}
VALID_STRESS = {"yes", "no", ""}
VALID_NEEDS_ATTENTION = {"yes", "no", ""}

LINK_RE = re.compile(r"^https://github\.com/dotnet/runtime/issues/\d+$")


def validate(csv_path: str) -> bool:
    errors: list[str] = []
    warnings: list[str] = []

    with open(csv_path, encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)

        if header != EXPECTED_COLUMNS:
            errors.append(f"Header mismatch.\n  Got:      {header}\n  Expected: {EXPECTED_COLUMNS}")

        rows = list(reader)

    print(f"Columns:   {len(header)}")
    print(f"Data rows: {len(rows)}")

    bad_cols = [i + 2 for i, r in enumerate(rows) if len(r) != len(header)]
    if bad_cols:
        errors.append(f"Rows with wrong column count (line numbers): {bad_cols[:10]}")
    else:
        print("All rows have correct column count: OK")

    error_count = 0
    for i, row in enumerate(rows, start=2):
        if len(row) != len(header):
            continue
        issue_id = row[0]
        cat = row[1]
        skill = row[3]
        stress = row[6]
        needs_attention = row[7]
        link = row[11]

        if cat not in VALID_CATEGORIES:
            errors.append(f"Line {i} (#{issue_id}): invalid category '{cat}'")
        if cat == "ERROR":
            error_count += 1
        if skill not in VALID_SKILL:
            errors.append(f"Line {i} (#{issue_id}): invalid skill '{skill}'")
        if stress not in VALID_STRESS:
            warnings.append(f"Line {i} (#{issue_id}): unexpected stress value '{stress}'")
        if needs_attention not in VALID_NEEDS_ATTENTION:
            warnings.append(f"Line {i} (#{issue_id}): unexpected NeedsAttention value '{needs_attention}'")
        if not LINK_RE.match(link):
            errors.append(f"Line {i} (#{issue_id}): bad link '{link}'")

    attention_count = sum(1 for r in rows if len(r) > 7 and r[7] == "yes")
    print(f"Issues needing attention: {attention_count}")
    if error_count:
        print(f"Issues with classification errors: {error_count}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings[:20]:
            print(f"  {w}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors[:20]:
            print(f"  {e}")
        return False

    print("\nValidation passed!")
    return True


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    ok = validate(sys.argv[1])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
