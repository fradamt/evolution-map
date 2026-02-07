#!/usr/bin/env python3
"""Fuzzy search papers by title and/or author.

Examples:
    python3 search_papers.py "roughgarden" --author
    python3 search_papers.py "eip-4844"
    python3 search_papers.py "loss versus rebalancing" --title --limit 15
"""

import argparse
import json
import math
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SCRIPT_DIR / "papers-db.json"


def normalize_text(value):
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def tokenize(value):
    return [t for t in normalize_text(value).split(" ") if t]


def fuzzy_score(query, candidate):
    """Return fuzzy score in [0, 100]."""
    q = normalize_text(query)
    c = normalize_text(candidate)
    if not q or not c:
        return 0.0

    seq = SequenceMatcher(None, q, c).ratio() * 45.0

    if q in c:
        substr = 25.0 + min(15.0, 20.0 * len(q) / max(1, len(c)))
    elif c in q:
        substr = 15.0
    else:
        substr = 0.0

    q_tokens = set(tokenize(q))
    c_tokens = set(tokenize(c))
    overlap = len(q_tokens & c_tokens)
    if q_tokens and c_tokens:
        jaccard = overlap / len(q_tokens | c_tokens)
        containment = overlap / len(q_tokens)
        token_score = (jaccard * 20.0) + (containment * 20.0)
    else:
        token_score = 0.0

    prefix = 8.0 if c.startswith(q) else 0.0

    score = seq + substr + token_score + prefix
    return min(100.0, score)


def load_papers(path):
    with open(path) as f:
        payload = json.load(f)
    papers = payload.get("papers") if isinstance(payload, dict) else payload
    if not isinstance(papers, list):
        raise ValueError("Expected `papers` list in database file")
    return papers


def best_author_score(query, authors):
    best = 0.0
    best_name = None
    for name in authors or []:
        score = fuzzy_score(query, name)
        if score > best:
            best = score
            best_name = name
    return best, best_name


def paper_result(query, paper, mode):
    title = paper.get("title") or ""
    authors = paper.get("authors") or []
    title_score = fuzzy_score(query, title)
    author_score, best_author = best_author_score(query, authors)

    if mode == "title":
        score = title_score
    elif mode == "author":
        score = author_score
    else:
        score = max(title_score, author_score)
        if title_score >= 45 and author_score >= 45:
            score += 6.0

    relevance = paper.get("relevance_score") or 0.0
    score += min(4.0, math.log1p(max(0.0, float(relevance))))
    score = min(100.0, score)

    return {
        "score": round(score, 2),
        "title_score": round(title_score, 2),
        "author_score": round(author_score, 2),
        "best_author": best_author,
        "paper": paper,
    }


def print_results(rows, query, mode):
    print(f"Query: {query}")
    print(f"Mode: {mode}")
    print(f"Matches: {len(rows)}")
    print("")

    for i, row in enumerate(rows, start=1):
        p = row["paper"]
        year = p.get("year") or "?"
        title = p.get("title") or "(untitled)"
        authors = ", ".join(p.get("authors") or [])[:150]
        if len(", ".join(p.get("authors") or [])) > 150:
            authors += "..."
        venue = p.get("venue") or "-"
        rel = p.get("relevance_score")
        pid = p.get("id")
        url = p.get("url") or "-"

        print(f"{i:>2}. [{row['score']:>5}] {title} ({year})")
        print(
            "    "
            f"title={row['title_score']:.1f} author={row['author_score']:.1f} "
            f"best_author={row['best_author'] or '-'} rel={rel if rel is not None else '-'}"
        )
        print(f"    authors: {authors or '-'}")
        print(f"    venue: {venue}")
        print(f"    id: {pid}")
        print(f"    url: {url}")
        print("")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Search query")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to papers DB JSON")
    parser.add_argument("--limit", type=int, default=20, help="Max results to return")
    parser.add_argument("--min-score", type=float, default=30.0, help="Minimum match score")
    parser.add_argument("--author", action="store_true", help="Search author names only")
    parser.add_argument("--title", action="store_true", help="Search titles only")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")
    args = parser.parse_args()

    mode = "both"
    if args.author and not args.title:
        mode = "author"
    elif args.title and not args.author:
        mode = "title"

    papers = load_papers(Path(args.db))
    scored = [paper_result(args.query, p, mode) for p in papers]
    filtered = [r for r in scored if r["score"] >= args.min_score]
    filtered.sort(
        key=lambda r: (
            -r["score"],
            -(r["paper"].get("relevance_score") or 0),
            -(r["paper"].get("cited_by_count") or 0),
            -(r["paper"].get("year") or 0),
            (r["paper"].get("title") or "").lower(),
        )
    )

    results = filtered[: max(1, args.limit)]

    if args.json:
        output = []
        for row in results:
            out = {
                "score": row["score"],
                "title_score": row["title_score"],
                "author_score": row["author_score"],
                "best_author": row["best_author"],
                "paper": row["paper"],
            }
            output.append(out)
        print(json.dumps(output, indent=2, ensure_ascii=True))
        return

    print_results(results, args.query, mode)


if __name__ == "__main__":
    main()
