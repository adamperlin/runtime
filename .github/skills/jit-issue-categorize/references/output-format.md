# CSV Output Format

This reference defines the CSV output format for the JIT issue categorization
skill. The output file should be importable into Excel or Google Sheets.

## Columns

| # | Column Name | Type | Allowed Values | Description |
|---|-------------|------|---------------|-------------|
| 1 | `Github Issue ID` | Integer | Any valid issue number | The GitHub issue number (e.g., `12345`). |
| 2 | `Category` | Enum | See [categories.md](categories.md) | Exactly one category from the predefined list. |
| 3 | `Theme` | Enum (multi) | See [categories.md](categories.md) | One or more themes, separated by `;` if multiple. |
| 4 | `SkillLevel` | Enum | `Beginner`, `Intermediate`, `Expert` | Estimated skill level needed to address the issue. |
| 5 | `Cost` | Enum | `Low`, `Medium`, `High` | Estimated implementation/design/planning time cost. |
| 6 | `Impact` | Enum | `Low`, `Medium`, `High` | Product/revenue/performance impact. Major features and perf improvements are weighted higher. |
| 7 | `Architecture` | String | `x64`, `x86`, `arm64`, `arm32`, `all`, or blank | Target architecture, inferred from issue body, labels, or CI. Multiple values separated by `;`. |
| 8 | `OS` | String | `windows`, `linux`, `macos`, `all`, or blank | Target OS, inferred from issue body, labels, or CI. Multiple values separated by `;`. |
| 9 | `Stress` | Boolean | `yes`, `no`, or blank | Whether the issue relates to stress testing or GC stress. |
| 10 | `Milestone` | String | Any milestone name or blank | The milestone attached to the issue on GitHub, if any. |
| 11 | `Assignees` | String | GitHub usernames or blank | Semicolon-separated list of assigned users. |
| 12 | `Full link` | URL | `https://github.com/dotnet/runtime/issues/<id>` | Direct link to the issue. |
| 13 | `Possible duplicate 1` | Integer or blank | Issue number | First candidate duplicate issue. |
| 14 | `Possible duplicate 2` | Integer or blank | Issue number | Second candidate duplicate issue. |
| 15 | `Possible duplicate 3` | Integer or blank | Issue number | Third candidate duplicate issue. |
| 16 | `Possible duplicate 4` | Integer or blank | Issue number | Fourth candidate duplicate issue. |

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

## Example

```csv
Github Issue ID,Category,Theme,SkillLevel,Cost,Impact,Architecture,OS,Stress,Milestone,Assignees,Full link,Possible duplicate 1,Possible duplicate 2,Possible duplicate 3,Possible duplicate 4
98765,correctness,register-allocator,Expert,High,High,x64,linux,no,10.0,user1;user2,https://github.com/dotnet/runtime/issues/98765,98000,97500,,
87654,cq,inlining;structs,Intermediate,Medium,Medium,all,all,no,,user3,https://github.com/dotnet/runtime/issues/87654,87000,,,
76543,eng-sys,super-pmi,Beginner,Low,Low,all,all,no,Future,,https://github.com/dotnet/runtime/issues/76543,,,,
```

## Skill Level Heuristics

| Level | Indicators |
|-------|-----------|
| `Beginner` | Documentation updates, simple test additions, well-defined small tasks, issues marked `good first issue` or `help wanted`. |
| `Intermediate` | Targeted optimizations, adding support for specific patterns, moderate refactoring, issues requiring familiarity with one JIT subsystem. |
| `Expert` | Fundamental JIT architectural changes, register allocator work, new optimization passes, changes spanning multiple subsystems, issues requiring deep understanding of codegen. |

## Cost Heuristics

| Level | Indicators |
|-------|-----------|
| `Low` | Estimated < 1 week of work. Well-scoped, clear implementation path. |
| `Medium` | Estimated 1-4 weeks of work. Requires design decisions or touches multiple files. |
| `High` | Estimated > 1 month of work. Major feature, significant refactoring, or research needed. |

## Impact Heuristics

| Level | Indicators |
|-------|-----------|
| `Low` | Edge case, cosmetic improvement, rare scenario, adequate workaround exists. |
| `Medium` | Targeted improvement affecting a meaningful set of users or workloads. |
| `High` | Major new feature, significant perf win, correctness bug affecting common scenarios, high community demand (+1 reactions). |
