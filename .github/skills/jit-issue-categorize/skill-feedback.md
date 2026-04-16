1. GitHub API 502 errors: 3 of the initial 10 parallel page fetches returned 502 Server Error. Retries succeeded, but this is a common friction point — the skill instructions don't mention retry strategy. Parallel fetches of large result sets seem
 to trigger rate-limiting or server-side throttle.
 2. 1,000-result cap workaround works but is manual: The date-range split (fetching created:<DATE for older issues) correctly captured all 1,233 issues, but I had to manually inspect the oldest page-10 date and construct the follow-up query. This 
could be automated in the scripts.
 3. needs-triage fallback is notable (103 issues, ~8.4%): These are issues where heuristics couldn't determine a theme — consistent with the skill's documented 8–10% expectation.
 4. Performance bot issues dominate: The performance category (421 issues, ~34%) is heavily inflated by automated [Perf] regression bot issues. Consider filtering on title prefix [Perf] if a more curated view is needed.
 5. cq as default category is aggressive: 457 issues defaulted to cq. Since this is the fallback when no other category pattern matches, some may be miscategorized.
 6. Theme overlap between codegen, optimization, and vector-codegen/hardware-intrinsics: These broad themes match many issues simultaneously. The 3-theme cap helps, but the first-matched theme may not always be the most specific.
 7. Large output handling: Every API page produced output too large for inline reading (600KB–960KB each), requiring file-based round-tripping. The workflow handles this correctly via the extract script, but it's a significant amount of data 
movement.