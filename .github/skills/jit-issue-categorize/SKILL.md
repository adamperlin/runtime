---
name: jit-issue-categorize
description: >
  Batch-categorize JIT issues labeled area-CodeGen-coreclr in dotnet/runtime.
  Queries GitHub for matching issues, classifies each by category, theme, skill
  level, cost, and impact, detects possible duplicates, and outputs a CSV file.
  USE FOR: "categorize JIT issues", "triage area-CodeGen-coreclr issues",
  "produce a JIT issue spreadsheet", "classify open JIT bugs", bulk issue
  categorization for the JIT team. DO NOT USE FOR: triaging a single issue
  in depth (use issue-triage skill), creating regression tests (use
  jit-regression-test skill), or reviewing code changes (use code-review skill).
---

# JIT Issue Batch Categorization

> **This is an output-only skill.** It produces a CSV file for human review.
> It does NOT modify issues, add labels, close issues, or post comments.

Batch-categorize all open issues with the `area-CodeGen-coreclr` label in
`dotnet/runtime`. For each issue, assign a category, theme, skill level, cost
estimate, impact estimate, and detect up to 4 possible duplicates. Output the
results as a CSV file.

## Reusable Scripts

This skill includes Python scripts in `scripts/` that automate the heavy
lifting. **Use these scripts instead of reimplementing classification logic
from scratch.**

| Script | Purpose |
|--------|---------|
| [`scripts/extract_issues.py`](scripts/extract_issues.py) | Reads raw JSON responses from `github-mcp-server-search_issues` and consolidates them into a single JSON file with only the fields needed for classification. |
| [`scripts/classify_issues.py`](scripts/classify_issues.py) | Classifies issues by category, theme, skill level, cost, impact, architecture, OS, and stress. Integrates duplicate detection. Writes CSV output. |
| [`scripts/find_duplicates.py`](scripts/find_duplicates.py) | TF-IDF cosine-similarity duplicate detector that runs locally on the fetched issue data (no additional API calls). |
| [`scripts/validate_csv.py`](scripts/validate_csv.py) | Validates the final CSV: correct column count, allowed enum values, well-formed links. |

### Quick-start (recommended workflow)

```bash
# 1. Save raw API JSON pages into a directory (see Step 1 below)
mkdir raw_pages/

# 2. Consolidate into one JSON file
python scripts/extract_issues.py raw_pages/ all_issues.json

# 3. Classify + detect duplicates + write CSV
cd scripts/  # needed so classify_issues.py can import find_duplicates
python classify_issues.py ../all_issues.json ../../jit-issues.csv

# 4. Validate
python validate_csv.py ../../jit-issues.csv

# 5. Clean up raw data
rm -rf raw_pages/ all_issues.json
```

## When to Use This Skill

Use this skill when:
- Asked to categorize, classify, or triage JIT issues in bulk
- Asked to produce a spreadsheet or CSV of `area-CodeGen-coreclr` issues
- Asked to assess the JIT issue backlog
- Asked "categorize these JIT issues", "make a JIT issue spreadsheet"

Do NOT use this skill for:
- Deep-diving into a single issue (use `issue-triage` instead)
- Creating JIT regression tests (use `jit-regression-test` instead)
- Performance benchmarking (use `performance-benchmark` instead)

## Input

The user may optionally provide:
- A **filter** to narrow issues (e.g., "only issues from the last 6 months",
  "only issues with no milestone", "only open issues with the `bug` label").
- A **list of specific issue numbers** to categorize instead of querying all.
- An **output file path** for the CSV (default: `jit-issues.csv` in the
  current working directory).

If no filters are provided, process all open issues with the
`area-CodeGen-coreclr` label.

## Workflow

### Step 1: Query Issues

Use `github-mcp-server-search_issues` to fetch all matching issues from
`dotnet/runtime`.

```
Query: label:area-CodeGen-coreclr state:open
Sort:  created (desc)
```

Handle pagination -- the GitHub API returns at most 100 results per page.
Fetch pages 1-10 in parallel where possible. **Save each raw JSON response
to a file** (e.g., `raw_pages/page01.json` … `page10.json`) so that
classification can be re-run without re-fetching.

#### GitHub Search API 1000-Result Cap

> **Critical:** The GitHub search API returns at most **1,000 results** per
> query (10 pages × 100 per page). As of March 2026, the JIT backlog has
> ~1,200+ open issues, so a single query will NOT retrieve them all.

**Workaround — date-range split:**

1. Fetch pages 1-10 of the main query (gets the newest 1,000 issues).
2. Find the `created_at` date of the oldest issue on page 10.
3. Issue a second query with `created:<THAT_DATE` to get the remaining older
   issues. This second result set is typically <300 issues and fits within the
   1,000-result cap.
4. Save these additional pages alongside the main pages.

The `extract_issues.py` script deduplicates by issue number, so overlap
between queries is safe.

If the user provided filters (date range, additional labels, milestone, etc.),
incorporate them into the query.

Report to the user how many issues were found before proceeding.

### Step 2: Extract and Consolidate

Run `scripts/extract_issues.py` to consolidate all raw JSON pages into a
single file containing only the fields needed for classification:

```bash
python scripts/extract_issues.py raw_pages/ all_issues.json
```

Each issue record contains: `number`, `title`, `body` (truncated to 2,000
chars), `labels`, `assignees`, `milestone`, `reactions_plus1`,
`reactions_total`.

### Step 3: Classify Each Issue

Run `scripts/classify_issues.py` on the consolidated JSON. This script
applies heuristic rules (described below) and automatically invokes
`find_duplicates.py` for duplicate detection.

```bash
cd scripts/
python classify_issues.py ../all_issues.json ../../jit-issues.csv
```

The classifier determines the following for each issue:

#### 3a: Category

Assign exactly **one** category from the list in
[references/categories.md](references/categories.md).

Use these heuristics to guide classification:

| Category | Primary Signals |
|----------|----------------|
| `correctness` | Labels: `bug`; keywords: crash, wrong result, miscompile, assert, AV, ICE, internal compiler error, silent bad codegen |
| `performance` | Labels: `tenet-performance`; title prefix `[Perf]`; keywords: regression, slower, perf |
| `cq` | Keywords: code quality, codegen quality, missed optimization, suboptimal, unnecessary instruction |
| `basic-cq` | Keywords: basic code quality, simple optimization, low-hanging, obvious missed opt |
| `throughput` | Keywords: JIT throughput, compilation time, JIT memory, compile speed |
| `proposal` | Labels: `api-suggestion`; title starts with `[API Proposal]` |
| `implementation` | Keywords: implement, add support for, enable, new feature |
| `eng-sys` | Keywords: CI, build infra, test infra, tooling, SuperPMI, pipeline |
| `design` | Keywords: design, architecture, RFC, refactor |
| `planning` | Labels: `tracking`; keywords: plan, roadmap, tracking issue, umbrella |
| `documentation` | Labels: `documentation`; keywords: docs, comments, README |
| `testing` | Keywords: test coverage, stress test, test infra |
| `question` | Labels: `question`; keywords: how to, why does, is it possible |
| `reach` | Keywords: stretch goal, nice to have, long-term, aspirational |
| `security` | Keywords: security, CVE, vulnerability, hardening |

When multiple categories could apply, prefer the one that best describes the
*primary ask* of the issue. For example, an issue requesting a new optimization
that would fix a codegen quality problem is `cq`, not `implementation`.

> **Note on automated perf regression issues:** The performance bot
> auto-files issues with titles like `[Perf] Linux/arm64: 1 Regression on …`.
> These dominate the `performance` category (~30-35% of all issues). If the
> user wants to exclude them, filter on title prefix `[Perf]` or the
> `untriaged` label.

#### 3b: Theme

Assign one or more **themes** from the list in
[references/categories.md](references/categories.md).

To determine the theme:

1. **Check existing labels** -- Many JIT issues carry labels that map directly
   to themes (e.g., `optimization-cse` -> `cse`, `optimization-inlining` ->
   `inlining`, `JitStress` -> `gc-stress`, `runtime-async` -> `codegen`).
2. **Scan the title and body** for JIT subsystem names (register allocator,
   loop optimization, SSA, etc.).
3. **Check for hardware/SIMD mentions** -- Issues mentioning AVX, SSE, NEON,
   SVE, or `System.Runtime.Intrinsics` -> `hardware-intrinsics`. Issues about
   `Vector<T>`, `Vector128`, `Vector256` codegen -> `vector-codegen`.
4. If multiple themes apply, list them separated by `;` with the most specific
   first. Limit to 3 themes per issue.
5. Use `needs-triage` only if no theme can be determined at all.

> **Pattern-matching pitfalls to avoid:**
> - `\btest\b` is far too broad — it matches any issue that mentions "test" in
>   any context. Use `test coverage`, `test infra`, `stress test` instead.
> - `\bbenchmark` matches too many issues. Prefer `benchmark infra`,
>   `BenchmarkDotNet` for the `benchmarks` theme.
> - `\bbuild\b` matches generic text. Prefer `build break`, `build fail`,
>   `build infra` for the `build` theme.
> - `\bdiv` without end-of-word boundary matches "provide", "individual", etc.
>   Use `\bdiv\b` or `\bdivis` for the `div-mod-rem` theme.
> - `\bemit` matches "emit" in many unrelated contexts. Prefer `\bemitt` (for
>   "emitter", "emitting") to target JIT emitter issues specifically.
> - `arm64` alone should map to architecture, not `hardware-intrinsics`.
>   Only map to `hardware-intrinsics` when specific instructions or intrinsic
>   APIs (e.g., `AdvSimd`, `Arm.`) are mentioned.

#### 3c: Skill Level

Assess the skill level needed to address the issue:

| Level | Indicators |
|-------|-----------|
| `Beginner` | Documentation, simple test additions, well-defined small tasks, `good first issue` or `help wanted` labels. |
| `Intermediate` | Targeted optimizations, adding support for specific patterns, moderate refactoring, familiarity with one JIT subsystem needed. |
| `Expert` | Fundamental JIT changes, register allocator work, new optimization passes, changes spanning multiple subsystems, deep codegen knowledge required. |

#### 3d: Cost

Estimate the implementation/design/planning time:

| Level | Indicators |
|-------|-----------|
| `Low` | < 1 week. Well-scoped, clear path. |
| `Medium` | 1-4 weeks. Requires design decisions or touches multiple files. |
| `High` | > 1 month. Major feature, significant refactoring, or research needed. |

#### 3e: Impact

Assess the product/revenue/performance impact:

| Level | Indicators |
|-------|-----------|
| `Low` | Edge case, cosmetic, rare scenario, workaround exists. |
| `Medium` | Targeted improvement for a meaningful set of users. |
| `High` | Major feature, significant perf win, correctness bug in common scenario, high community demand (many +1 reactions). |

#### 3f: Architecture and OS

Infer from the issue body, labels, and any referenced CI runs:

- **Architecture**: `x64`, `x86`, `arm64`, `arm32`, `all`, or leave blank.
- **OS**: `windows`, `linux`, `macos`, `all`, or leave blank.

Look for:
- Explicit mentions ("this only happens on ARM64", "Windows-specific")
- CI failure links that indicate platform
- Labels like `os-linux`, `arch-arm64`

If the issue applies to all platforms or doesn't specify, use `all`.

#### 3g: Stress

Set to `yes` if the issue mentions stress testing, GC stress, JIT stress,
`DOTNET_JitStress`, `DOTNET_GCStress`, or `DOTNET_JitStressModeNames`.
Otherwise `no` or blank.

#### 3h: Milestone, Assignees, Full Link

Extract directly from the GitHub issue metadata:
- **Milestone**: The milestone name, or blank if none.
- **Assignees**: Semicolon-separated GitHub usernames, or blank.
- **Full link**: `https://github.com/dotnet/runtime/issues/<number>`

### Step 4: Detect Possible Duplicates

`classify_issues.py` automatically calls `find_duplicates.py`, which uses
**TF-IDF cosine similarity** on issue titles to identify up to 4 possible
duplicates per issue (similarity threshold ≥ 0.30).

This approach is **local and offline** — it runs on the already-fetched issue
data without making additional API calls. This is critical for large backlogs
(1,000+ issues) where per-issue API searches would be impractical.

> **Why not per-issue API search?** With 1,200+ issues, searching GitHub for
> each issue's keywords would require 1,200+ API calls, take a very long time,
> and likely hit rate limits. The local TF-IDF approach processes all issues in
> under a second.

**Limitations of local duplicate detection:**
- Only compares within the fetched issue set (does not find duplicates among
  closed issues or issues in other repos).
- Title-based only — issues with different titles but similar bodies may be
  missed.
- Threshold of 0.30 is a reasonable default but may need tuning.

**Important:** Duplicate detection is best-effort. Not every match is a true
duplicate. The human reviewer makes the final call.

### Step 5: Validate CSV

Run `scripts/validate_csv.py` to verify the output:

```bash
python scripts/validate_csv.py jit-issues.csv
```

This checks:
- Header matches expected column names
- All rows have the correct number of columns
- Category, SkillLevel, Cost, Impact, Stress values are from allowed sets
- Full link is a valid GitHub issue URL

### Step 6: Present Summary

After writing the CSV, present a summary to the user:

1. **Total issues processed**: Count of issues categorized.
2. **Breakdown by category**: How many issues in each category.
3. **Top themes**: Top 10-15 most common themes.
4. **Duplicate coverage**: How many issues have at least one duplicate
   candidate.
5. **Low-confidence notes**: Mention how many issues got `needs-triage` as
   their theme, and note any systematic patterns (e.g., bot-generated perf
   regression issues dominating a category).
6. **Output file location**: Path to the CSV file.

## Modifying the Classification Rules

The classification heuristics live in `scripts/classify_issues.py`. To update
them:

- **Add a new category keyword**: Add a `(re.compile(…), "category")`
  entry to the `_KW_CATEGORY` list.
- **Add a new theme pattern**: Add a `(re.compile(…), "theme")` entry to
  the `_THEME_PATTERNS` list.
- **Map a new GitHub label to a theme**: Add an entry to the
  `_LABEL_TO_THEME` dict.
- **Adjust duplicate sensitivity**: Change the `threshold` parameter in the
  `find_duplicates()` call (lower = more candidates, higher = fewer).

After modifying, re-run against the same `all_issues.json` to test without
re-fetching from GitHub.

## Known Issues and Pitfalls

- **GitHub search API 1,000-result cap**: See the date-range-split workaround
  in Step 1. Always verify the extracted issue count matches the total count
  reported by the API.
- **Bot-generated perf issues**: The `[Perf]` automated regression bot
  creates many issues. These inflate the `performance` category to ~30-35% of
  all issues. Consider offering the user an option to exclude them.
- **`needs-triage` fallback**: ~8-10% of issues may end up with
  `needs-triage` as their theme because their titles and bodies lack
  subsystem-specific keywords. This is acceptable — prefer `needs-triage`
  over incorrect theme assignment.
- **Body truncation**: Issue bodies are truncated to 2,000 characters for
  efficiency. Occasionally classification-relevant text appears deeper in the
  body. This is a reasonable trade-off for processing 1,000+ issues.
- **`cq` as default category**: Issues that don't match any specific category
  pattern default to `cq` (code quality), since the majority of JIT issues
  are about codegen quality. Review the `cq` bucket for miscategorized issues.

## Tips

- **Parallel fetching**: Fetch multiple API pages in parallel (e.g., pages
  2-5 simultaneously) to speed up data collection.
- **Save raw data**: Always save raw JSON responses before processing. This
  allows re-running classification with updated rules without re-fetching.
- **Re-run workflow**: To reclassify with updated heuristics, keep the
  `all_issues.json` file and re-run `classify_issues.py` directly.
- **Existing labels are strong signals**: If an issue already has a well-known
  JIT label (e.g., `optimization-loop-opt`), trust it for theme assignment.
- **Rate limiting**: GitHub API has rate limits. If fetching many pages,
  use parallel calls where the MCP tool supports it, and report progress.
- **Confidence notes**: When unsure about a classification, prefer
  `needs-triage` for theme and note it in the summary rather than guessing
  incorrectly.
