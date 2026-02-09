#!/usr/bin/env python3
"""Export analysis.json + papers-db.json -> v2/data/*.json (5 split files).

Reuses prepare_viz_data() from render_html.py, then splits the monolithic
data blob into progressively-loaded chunks for the v2 frontend.

Usage:
    python3 export_data.py
"""

import json
import math
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_PATH = SCRIPT_DIR / "analysis.json"
V2_DATA_DIR = SCRIPT_DIR / "v2" / "data"

# Import prepare_viz_data from render_html.py
sys.path.insert(0, str(SCRIPT_DIR))
from render_html import prepare_viz_data  # noqa: E402


def _precompute_warm_positions(topics, forks, threads, eras):
    """Precompute timeline X/Y positions per topic for warm-starting network force sim."""
    import datetime

    # Date range
    all_dates = []
    for t in topics.values():
        d = t.get("d")
        if d:
            try:
                all_dates.append(datetime.date.fromisoformat(d[:10]))
            except (ValueError, TypeError):
                pass

    if not all_dates:
        return {}

    min_date = min(all_dates)
    max_date = max(all_dates)
    date_span = (max_date - min_date).days or 1

    # Thread lane Y positions (proportional)
    thread_order = [
        "consensus", "scaling", "layer2", "mev",
        "execution", "cryptography", "defi", "privacy",
        "security", "governance",
    ]
    thread_y = {}
    for i, tid in enumerate(thread_order):
        thread_y[tid] = (i + 0.5) / len(thread_order)
    # "Other" lane for unthreaded topics
    thread_y[None] = 0.95

    positions = {}
    for tid, t in topics.items():
        d = t.get("d")
        if not d:
            continue
        try:
            dt = datetime.date.fromisoformat(d[:10])
        except (ValueError, TypeError):
            continue

        x = (dt - min_date).days / date_span  # 0..1
        th = t.get("th")
        y = thread_y.get(th, thread_y[None])
        # Add slight jitter based on topic ID to prevent overlap
        jitter = (hash(str(tid)) % 1000) / 10000 - 0.05
        positions[str(tid)] = {"x": round(x, 4), "y": round(y + jitter, 4)}

    return positions


def _compute_magicians_influence(magicians_topics, topics):
    """Map magicians engagement percentile to topic influence quantile (matches V1 algorithm)."""
    topic_infs = sorted(t.get("inf", 0) for t in topics.values())
    if not topic_infs:
        return

    entries = []
    for mtid, mt in magicians_topics.items():
        raw = (mt.get("lk", 0) * 2
               + math.sqrt(mt.get("pc", 0))
               + math.log1p(mt.get("vw", 0)) * 0.3)
        entries.append((mtid, raw))

    if not entries:
        return

    entries.sort(key=lambda x: x[1])
    n = len(entries)
    m = len(topic_infs)

    for i, (mtid, _raw) in enumerate(entries):
        p = 0.5 if n == 1 else i / (n - 1)
        idx = p * (m - 1)
        lo = int(idx)
        hi = min(lo + 1, m - 1)
        frac = idx - lo
        inf = topic_infs[lo] * (1 - frac) + topic_infs[hi] * frac
        magicians_topics[mtid]["inf"] = round(inf, 4)


def export():
    print("Loading analysis.json...")
    with open(ANALYSIS_PATH) as f:
        data = json.load(f)

    print("Running prepare_viz_data()...")
    viz = prepare_viz_data(data)

    # Precompute warm-start positions
    positions = _precompute_warm_positions(
        viz["topics"], viz["forks"], viz["threads"], viz["eras"],
    )

    V2_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- core.json ---
    # Topics + threads + forks + eras + authors + topic edges + warm positions
    core = {
        "meta": viz["meta"],
        "topics": viz["topics"],
        "authors": viz["authors"],
        "threads": viz["threads"],
        "forks": viz["forks"],
        "eras": viz["eras"],
        "graph": viz["graph"],
        "warmPositions": positions,
    }
    core_path = V2_DATA_DIR / "core.json"
    with open(core_path, "w") as f:
        json.dump(core, f, separators=(",", ":"))
    print(f"  core.json: {core_path.stat().st_size / 1024:.0f} KB")

    # --- eips.json ---
    # EIP catalog + EIP authors + EIP graph + author links
    eips = {
        "eipCatalog": viz["eipCatalog"],
        "eipAuthors": viz["eipAuthors"],
        "eipGraph": viz["eipGraph"],
        "authorLinks": viz["authorLinks"],
    }
    eips_path = V2_DATA_DIR / "eips.json"
    with open(eips_path, "w") as f:
        json.dump(eips, f, separators=(",", ":"))
    print(f"  eips.json: {eips_path.stat().st_size / 1024:.0f} KB")

    # --- papers.json ---
    # Paper corpus + paper graph
    papers = {
        "papers": viz["papers"],
        "papersMeta": viz["papersMeta"],
        "paperGraph": viz["paperGraph"],
    }
    papers_path = V2_DATA_DIR / "papers.json"
    with open(papers_path, "w") as f:
        json.dump(papers, f, separators=(",", ":"))
    print(f"  papers.json: {papers_path.stat().st_size / 1024:.0f} KB")

    # --- Compute magicians influence ---
    _compute_magicians_influence(viz["magiciansTopics"], viz["topics"])

    # --- graph.json ---
    # Unified graph + cross-forum edges + magicians topics + EIP catalog (for graph indexes)
    graph = {
        "unifiedGraph": viz["unifiedGraph"],
        "crossForumEdges": viz["crossForumEdges"],
        "magiciansTopics": viz["magiciansTopics"],
        "eipCatalog": viz["eipCatalog"],
    }
    graph_path = V2_DATA_DIR / "graph.json"
    with open(graph_path, "w") as f:
        json.dump(graph, f, separators=(",", ":"))
    print(f"  graph.json: {graph_path.stat().st_size / 1024:.0f} KB")

    # --- coauthor.json ---
    # Co-author graph
    coauthor = viz["coGraph"]
    coauthor_path = V2_DATA_DIR / "coauthor.json"
    with open(coauthor_path, "w") as f:
        json.dump(coauthor, f, separators=(",", ":"))
    print(f"  coauthor.json: {coauthor_path.stat().st_size / 1024:.0f} KB")

    total = sum(
        (V2_DATA_DIR / name).stat().st_size
        for name in ["core.json", "eips.json", "papers.json", "graph.json", "coauthor.json"]
    )
    print(f"\nTotal: {total / 1024:.0f} KB ({total / (1024*1024):.1f} MB)")
    print(f"Files written to: {V2_DATA_DIR}")


if __name__ == "__main__":
    export()
