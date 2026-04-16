# CSV Output Format

This reference defines the CSV output format for the JIT issue categorization
skill. The output file should be importable into Excel or Google Sheets.

## Columns

| # | Column Name | Type | Allowed Values | Description |
|---|-------------|------|---------------|-------------|
| 1 | `Github Issue ID` | Integer | Any valid issue number | The GitHub issue number (e.g., `12345`). |
| 2 | `Category` | Enum | See [categories.md](categories.md) | Exactly one category from the predefined list. |
| 3 | `Theme` | Enum (multi) | See [categories.md](categories.md) | One or more themes, separated by `;` if multiple (max 2). |
| 4 | `SkillLevel` | Enum | `Beginner`, `Intermediate`, `Expert` | Estimated skill level needed to address the issue. |
| 5 | `Architecture` | String | `x64`, `x86`, `arm64`, `arm32`, `all`, or blank | Target architecture, inferred from issue body, labels, or CI. Multiple values separated by `;`. |
| 6 | `OS` | String | `windows`, `linux`, `macos`, `all`, or blank | Target OS, inferred from issue body, labels, or CI. Multiple values separated by `;`. |
| 7 | `Stress` | Boolean | `yes`, `no`, or blank | Whether the issue relates to stress testing or GC stress. |
| 8 | `ShouldClose` | Boolean | `yes`, `no` | Whether the issue should be closed (no longer relevant, duplicate, untenable, etc.). |
| 9 | `CloseReason` | String | Free text or blank | Reason for closing. Non-blank only when `ShouldClose` is `yes`. |
| 10 | `Milestone` | String | Any milestone name or blank | The milestone attached to the issue on GitHub, if any. |
| 11 | `Assignees` | String | GitHub usernames or blank | Semicolon-separated list of assigned users. |
| 12 | `Full link` | URL | `https://github.com/dotnet/runtime/issues/<id>` | Direct link to the issue. |

## Rules

- **Quoting**: Use standard CSV quoting -- enclose fields containing commas,
  newlines, or double quotes in double quotes. Escape internal double quotes
  by doubling them.
- **Multi-value fields**: When a field contains multiple values (Theme,
  Architecture, OS, Assignees), separate them with `;` (semicolon) within a
  single CSV field.
- **Empty fields**: Leave blank (two consecutive commas) when a value cannot be
  determined.
- **Header row**: The first row of the CSV must be the column headers exactly
  as listed above.
- **Encoding**: UTF-8 without BOM.
- **ERROR rows**: If a subagent invocation fails for a given issue, the
  `Category` column is set to `ERROR` and remaining classification fields are
  left blank. These rows should be retried manually.

## Example

```csv
Github Issue ID,Category,Theme,SkillLevel,Architecture,OS,Stress,ShouldClose,CloseReason,Milestone,Assignees,Full link
98765,correctness,register-allocator,Expert,x64,linux,no,no,,10.0,user1;user2,https://github.com/dotnet/runtime/issues/98765
87654,cq,inlining;structs,Intermediate,all,all,no,no,,,user3,https://github.com/dotnet/runtime/issues/87654
76543,eng-sys,super-pmi,Beginner,all,all,no,yes,Superseded by #80000,Future,,https://github.com/dotnet/runtime/issues/76543
```

## Skill Level Heuristics

| Level | Indicators |
|-------|-----------|
| `Beginner` | Documentation updates, simple test additions, well-defined small tasks, issues marked `good first issue` or `help wanted`. |
| `Intermediate` | Targeted optimizations, adding support for specific patterns, moderate refactoring, issues requiring familiarity with one JIT subsystem. |
| `Expert` | Fundamental JIT architectural changes, register allocator work, new optimization passes, changes spanning multiple subsystems, issues requiring deep understanding of codegen. |
