#!/usr/bin/env python3
"""Render analysis.json → evolution-map-api.json (machine-readable flat JSON).

Generates a simplified JSON file for programmatic queries and RAG systems.
Flat arrays: topics[], threads[], forks[], edges[].

Usage:
    python3 render_api.py
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_PATH = SCRIPT_DIR / "analysis.json"
OUTPUT_PATH = SCRIPT_DIR / "evolution-map-api.json"

THREAD_ORDER = [
    "pos_casper", "sharding_da", "plasma_l2", "fee_markets",
    "pbs_mev", "ssf", "issuance_economics", "inclusion_lists",
    "based_preconf", "zk_proofs", "state_execution", "privacy_identity",
]


def thread_status(thread):
    """Compute ACTIVE/MODERATE/DORMANT from quarterly counts."""
    qc = thread.get("quarterly_counts", [])
    recent = sum(q["c"] for q in qc if q["q"] >= "2024")
    if recent >= 5:
        return "active"
    if recent >= 2:
        return "moderate"
    return "dormant"


def main():
    with open(ANALYSIS_PATH) as f:
        data = json.load(f)

    meta = data["metadata"]
    topics = data["topics"]
    threads = data["research_threads"]
    forks = data["forks"]
    graph = data["graph"]
    papers = data.get("papers", {})

    # Flat topics array
    api_topics = []
    for tid, t in sorted(topics.items(), key=lambda x: x[1]["influence_score"], reverse=True):
        api_topics.append({
            "id": t["id"],
            "title": t["title"],
            "author": t["author"],
            "coauthors": t.get("coauthors", []),
            "authors": t.get("authors", [t["author"]]),
            "date": t["date"],
            "thread": t.get("research_thread"),
            "era": t.get("era"),
            "influence": round(t["influence_score"], 4),
            "in_degree": t["in_degree"],
            "views": t["views"],
            "likes": t["like_count"],
            "posts": t["posts_count"],
            "category": t.get("category_name", ""),
            "tags": t.get("tags", []),
            "eips": t.get("eip_mentions", []),
            "primary_eips": t.get("primary_eips", []),
            "excerpt": t.get("first_post_excerpt", ""),
            "outgoing_refs": t.get("outgoing_refs", []),
            "incoming_refs": t.get("incoming_refs", []),
            "participants": [p["username"] for p in t.get("participants", [])[:5]],
            "url": f"https://ethresear.ch/t/{t['id']}",
        })

    # Flat threads array
    api_threads = []
    for tid in THREAD_ORDER:
        th = threads.get(tid)
        if not th:
            continue
        api_threads.append({
            "id": tid,
            "name": th["name"],
            "status": thread_status(th),
            "topic_count": th["topic_count"],
            "date_range": th.get("date_range"),
            "peak_year": th.get("peak_year"),
            "active_years": th.get("active_years", []),
            "key_authors": th.get("key_authors", {}),
            "top_eips": th.get("top_eips", th.get("eip_mentions", []))[:10],
            "milestones": [
                {"id": m["id"], "title": m["title"], "date": m["date"], "note": m["note"]}
                for m in th.get("milestones", [])
            ],
            "top_topics": th.get("top_topics", [])[:10],
        })

    # Flat forks array
    api_forks = []
    for f in forks:
        api_forks.append({
            "name": f["name"],
            "date": f.get("date"),
            "el_name": f.get("el_name"),
            "cl_name": f.get("cl_name"),
            "combined_name": f.get("combined_name"),
            "eips": f["eips"],
            "related_topics": f.get("related_topics", [])[:10],
        })

    # Flat edges array
    api_edges = [{"source": e["source"], "target": e["target"]} for e in graph["edges"]]

    # Flat papers array
    api_papers = []
    for pid, p in sorted(
        papers.items(),
        key=lambda x: (
            -((x[1].get("cited_by_count") or 0)),
            -((x[1].get("year") or 0)),
            x[1].get("title", ""),
        ),
    ):
        api_papers.append({
            "id": pid,
            "title": p.get("title"),
            "year": p.get("year"),
            "authors": p.get("authors", []),
            "venue": p.get("venue"),
            "doi": p.get("doi"),
            "arxiv_id": p.get("arxiv_id"),
            "eprint_id": p.get("eprint_id"),
            "url": p.get("url"),
            "cited_by_count": p.get("cited_by_count"),
            "tags": p.get("tags", []),
            "source": p.get("source"),
        })

    # Compute date range from topics
    all_dates = sorted(t["date"] for t in topics.values() if t.get("date"))
    date_range = [all_dates[0], all_dates[-1]] if all_dates else None

    output = {
        "metadata": {
            "total_topics": meta["total_topics"],
            "included_topics": meta["included"],
            "included_edges": meta["included_edges"],
            "papers_count": meta.get("papers_count", len(api_papers)),
            "date_range": date_range,
            "generated_by": "render_api.py",
        },
        "topics": api_topics,
        "threads": api_threads,
        "forks": api_forks,
        "papers": api_papers,
        "edges": api_edges,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Written: {OUTPUT_PATH} ({size_kb:.0f} KB, {len(api_topics)} topics, "
          f"{len(api_threads)} threads, {len(api_forks)} forks, {len(api_papers)} papers, {len(api_edges)} edges)")


if __name__ == "__main__":
    main()
