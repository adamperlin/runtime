Issue URL: https://github.com/dotnet/runtime/issues/<ISSUE_NUMBER>

## Background

We have a very large backlog of open issues (over 1200), many of which may no
longer be relevant, and all of which need to be categorized for triage. We wish
to assign them categories and themes according to the reference at
`.github/skills/jit-issue-categorize/references/categories.md`.

## Objective

Analyze the issue and produce a structured JSON classification.

### Step 1: Determine Relevance

Some issues may be particularly relevant to JIT developers. In particular, consider:
  - Perf regressions which need triage and repro
  - Bug reports from users that need triage and repro
  - Regressions in benchmarks that have clear, actionable data.

In older issues, consider if a repro might resolve the issue for good, i.e., is the issue a perf regression
from an older .NET version which could have been fixed in a newer version and this is something we could confirm?
Wishes, vague feature requests, and requests that don't have an easy action item are likely to need less timely attention. 

### Step 2: Categorize and Assign Themes

Categorize and assign themes to this GitHub issue according to
`.github/skills/jit-issue-categorize/references/categories.md`, picking
exactly one category and at most 2 themes.

### Step 3: Assess Skill Level

Estimate the skill level needed to address the issue:

| Level | Indicators |
|-------|-----------|
| `Beginner` | Documentation updates, simple test additions, well-defined small tasks, issues marked `good first issue` or `help wanted`. |
| `Intermediate` | Targeted optimizations, adding support for specific patterns, moderate refactoring, familiarity with one JIT subsystem needed. |
| `Expert` | Fundamental JIT architectural changes, register allocator work, new optimization passes, changes spanning multiple subsystems, deep codegen knowledge required. |

### Step 4: Determine Architecture and OS

Infer from the issue body, labels, and any referenced CI runs:

- **Architecture**: `x64`, `x86`, `arm64`, `arm32`, `all`, or leave blank.
  Multiple values separated by `;`.
- **OS**: `windows`, `linux`, `macos`, `all`, or leave blank.
  Multiple values separated by `;`.

Look for:
- Explicit mentions ("this only happens on ARM64", "Windows-specific")
- CI failure links that indicate platform
- Labels like `os-linux`, `arch-arm64`

If the issue applies to all platforms or doesn't specify, use `all`.

### Step 5: Determine Stress

Set to `yes` if the issue mentions stress testing, GC stress, JIT stress,
`DOTNET_JitStress`, `DOTNET_GCStress`, or `DOTNET_JitStressModeNames`.
Otherwise `no`.

## Output

A JSON blob in the following format. If the caller specifies a file path to
write to, write **only** the JSON object to that file — no markdown fences,
no commentary, no extra text. If no file path is given, output **only** the
JSON to stdout.

```json
{
    "title": "<issue title>",
    "url": "<issue url>",
    "category": "<category>",
    "themes": ["theme1", "theme2"],
    "skillLevel": "Beginner|Intermediate|Expert",
    "architecture": "<x64|x86|arm64|arm32|all or blank, semicolon-separated>",
    "os": "<windows|linux|macos|all or blank, semicolon-separated>",
    "stress": "yes|no",
    "needsAttention": true,
    "attentionReason": "<reason or empty string>"
}
```

Field rules:
- `category`: Exactly one value from `categories.md`.
- `themes`: Array of at most 2 strings from the themes list in `categories.md`.
- `skillLevel`: One of `Beginner`, `Intermediate`, `Expert`.
- `architecture`: One or more of `x64`, `x86`, `arm64`, `arm32`, `all`
  (semicolon-separated), or empty string.
- `os`: One or more of `windows`, `linux`, `macos`, `all`
  (semicolon-separated), or empty string.
- `stress`: `yes` or `no`.
- `needsAttention`: Boolean. `true` if the issue needs attention.
- `attentionReason`: Non-empty only when `needsAttention` is `true`.