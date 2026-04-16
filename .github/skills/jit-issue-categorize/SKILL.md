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
`dotnet/runtime`. For each issue, invoke a **Copilot subagent** to assign a
category, theme, skill level, architecture, OS, stress flag, and a
close/keep recommendation. Output the results as a CSV file.

## Reusable Scripts

This skill includes Python scripts in `scripts/` that automate the heavy
lifting. **Use these scripts instead of reimplementing classification logic
from scratch.**

| Script | Purpose |
|--------|---------|
| [`scripts/extract_issues.py`](scripts/extract_issues.py) | Reads raw JSON responses from `github-mcp-server-search_issues` and consolidates them into a single JSON file with only the fields needed for classification. |
| [`scripts/classify_issues.py`](scripts/classify_issues.py) | Invokes a Copilot subagent per issue for AI-driven classification. Supports concurrency, resume, and timeout. Writes CSV output. |
| [`scripts/find_duplicates.py`](scripts/find_duplicates.py) | TF-IDF cosine-similarity duplicate detector (kept for optional use; not called by the default workflow). |
| [`scripts/validate_csv.py`](scripts/validate_csv.py) | Validates the final CSV: correct column count, allowed enum values, well-formed links. |

### Quick-start (recommended workflow)

```bash
# 1. Save raw API JSON pages into a directory (see Step 1 below)
mkdir raw_pages/

# 2. Consolidate into one JSON file
python scripts/extract_issues.py raw_pages/ all_issues.json

# 3. Classify via Copilot subagent + write CSV
python scripts/classify_issues.py all_issues.json jit-issues.csv --concurrency 5

# 4. Validate
python scripts/validate_csv.py jit-issues.csv

# 5. If there were errors, re-run with --resume to retry failed issues
python scripts/classify_issues.py all_issues.json jit-issues.csv --resume

# 6. Clean up raw data
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

### Step 3: Classify Each Issue via Copilot Subagent

Run `scripts/classify_issues.py` on the consolidated JSON. This script
invokes a **Copilot subagent** for each issue using the prompt at
[references/subagent-prompt.md](references/subagent-prompt.md).

```bash
python scripts/classify_issues.py all_issues.json jit-issues.csv --concurrency 5
```

#### How the subagent works

For each issue, the script runs:

```
copilot --yolo --model "gpt-5.4" --autopilot --no-ask-user \
  -p "Please use @.github/skills/jit-issue-categorize/references/subagent-prompt \
      for issue #<NUMBER>"
```

The subagent reads the issue from GitHub, applies the categories and themes
from [references/categories.md](references/categories.md), and returns a JSON
blob with:

- **category** — exactly one from the predefined list
- **themes** — at most 2 from the themes list
- **skillLevel** — `Beginner`, `Intermediate`, or `Expert`
- **architecture** — `x64`, `x86`, `arm64`, `arm32`, `all`, or blank
- **os** — `windows`, `linux`, `macos`, `all`, or blank
- **stress** — `yes` or `no`
- **shouldClose** — whether the issue should be closed
- **closeReason** — explanation if shouldClose is true

The script parses this JSON, merges it with issue metadata (milestone,
assignees), and writes the CSV.

#### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--concurrency N` | 5 | Number of parallel subagent invocations |
| `--timeout SECS` | 120 | Timeout per subagent invocation in seconds |
| `--resume` | off | Skip issues already present in the output CSV |

#### Error handling

If a subagent invocation fails (timeout, non-zero exit, or no valid JSON in
output), the issue is written to the CSV with `ERROR` in the Category column.
The script does **not** abort — it continues with the remaining issues. Use
`--resume` to retry only the failed issues.

### Step 4: Validate CSV

Run `scripts/validate_csv.py` to verify the output:

```bash
python scripts/validate_csv.py jit-issues.csv
```

This checks:
- Header matches expected column names
- All rows have the correct number of columns
- Category, SkillLevel, Stress, ShouldClose values are from allowed sets
- Full link is a valid GitHub issue URL
- Reports count of issues recommended to close and classification errors

### Step 5: Present Summary

After writing the CSV, present a summary to the user:

1. **Total issues processed**: Count of issues categorized.
2. **Breakdown by category**: How many issues in each category.
3. **Top themes**: Top 10-15 most common themes.
4. **Recommended to close**: How many issues the subagent flagged for closing.
5. **Classification errors**: How many issues failed subagent invocation
   (marked as `ERROR`). If any, suggest re-running with `--resume`.
6. **Output file location**: Path to the CSV file.

## Modifying the Classification Rules

Classification is driven by the **subagent prompt** at
[references/subagent-prompt.md](references/subagent-prompt.md) and the
**categories/themes reference** at
[references/categories.md](references/categories.md). To update them:

- **Add a new category or theme**: Edit `references/categories.md`.
- **Change classification guidance**: Edit `references/subagent-prompt.md`
  (e.g., adjust skill level heuristics, add new assessment criteria).
- **Change the Copilot model**: Edit the `_build_copilot_command()` function
  in `scripts/classify_issues.py`.
- **Change CSV output format**: Edit `references/output-format.md` and update
  `CSV_COLUMNS` in both `scripts/classify_issues.py` and
  `scripts/validate_csv.py`.

After modifying the prompt or categories, re-run against the same
`all_issues.json` to test without re-fetching from GitHub.

## Known Issues and Pitfalls

- **GitHub search API 1,000-result cap**: See the date-range-split workaround
  in Step 1. Always verify the extracted issue count matches the total count
  reported by the API.
- **Subagent invocation speed**: Each subagent call takes ~30-60 seconds. With
  1,200+ issues at concurrency=5, expect ~4-8 hours for a full run. Use
  `--resume` to handle interruptions gracefully.
- **Bot-generated perf issues**: The `[Perf]` automated regression bot
  creates many issues. These inflate the `performance` category to ~30-35% of
  all issues. Consider offering the user an option to exclude them.
- **Body truncation**: Issue bodies are truncated to 2,000 characters in the
  consolidated JSON. The subagent reads the full issue from GitHub directly,
  so this only affects the local data file, not classification quality.
- **Copilot CLI must be installed**: The `copilot` command must be on `PATH`.
  The script checks for this at startup and exits with a clear error if not
  found.

## Tips

- **Parallel fetching**: Fetch multiple API pages in parallel (e.g., pages
  2-5 simultaneously) to speed up data collection.
- **Save raw data**: Always save raw JSON responses before processing. This
  allows re-running classification with updated prompts without re-fetching.
- **Re-run workflow**: To reclassify with an updated prompt, keep the
  `all_issues.json` file and re-run `classify_issues.py` directly.
- **Resume after interruption**: If the script is interrupted or times out,
  re-run with `--resume` to pick up where it left off.
- **Rate limiting**: GitHub API has rate limits. If fetching many pages,
  use parallel calls where the MCP tool supports it, and report progress.
- **Adjust concurrency**: If seeing many timeouts, reduce `--concurrency`.
  If the machine and network can handle more, increase it.
