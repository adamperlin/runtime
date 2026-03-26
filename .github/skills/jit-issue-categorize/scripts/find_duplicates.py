#!/usr/bin/env python3
"""Simple text-similarity-based duplicate detection for JIT issues.

Usage (standalone):
    python find_duplicates.py <issues.json> <output.json>

Or import ``find_duplicates(issues)`` from another script.

Uses TF-IDF cosine similarity on issue titles to find the top-4 most
similar issues for each issue.  This is a *best-effort, offline*
approach -- it works on the already-fetched issue data without making
additional API calls.
"""

import json
import math
import re
import sys
from collections import Counter


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip markdown/URLs, split on non-alpha."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9]", " ", text.lower())
    return [w for w in text.split() if len(w) > 2]


def _build_tfidf(docs: list[list[str]]) -> tuple[list[dict[str, float]], dict[str, float]]:
    """Return per-document TF-IDF vectors and IDF map."""
    n = len(docs)
    df: Counter = Counter()
    for tokens in docs:
        df.update(set(tokens))
    idf = {term: math.log(n / (1 + count)) for term, count in df.items()}

    vectors: list[dict[str, float]] = []
    for tokens in docs:
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec = {t: (c / total) * idf.get(t, 0) for t, c in tf.items()}
        vectors.append(vec)
    return vectors, idf


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def find_duplicates(
    issues: list[dict],
    top_k: int = 4,
    threshold: float = 0.30,
) -> dict[int, list[int]]:
    """Return {issue_number: [dup1, dup2, ...]} for each issue.

    Only includes candidates above *threshold* similarity.
    """
    titles = [issue["title"] for issue in issues]
    docs = [_tokenize(t) for t in titles]
    vectors, _ = _build_tfidf(docs)

    result: dict[int, list[int]] = {}
    for i, issue in enumerate(issues):
        scores: list[tuple[float, int]] = []
        for j, other in enumerate(issues):
            if i == j:
                continue
            sim = _cosine(vectors[i], vectors[j])
            if sim >= threshold:
                scores.append((sim, other["number"]))
        scores.sort(reverse=True)
        result[issue["number"]] = [num for _, num in scores[:top_k]]

    return result


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as fh:
        issues = json.load(fh)

    dups = find_duplicates(issues)
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        json.dump(dups, fh, indent=1)

    has_dups = sum(1 for v in dups.values() if v)
    print(f"Found possible duplicates for {has_dups}/{len(issues)} issues -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
