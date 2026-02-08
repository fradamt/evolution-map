#!/usr/bin/env python3
"""
Prototype: Unified influence scoring system

Reads analysis.json and papers-db.json from the current directory and computes
per-entity scores per the specified formulas:

Phase 1 (intrinsic):
  - Topics: citation + engagement percentiles
  - EIPs: status, engagement, ethresearch citations, fork shipped, requires
  - Papers: citations (nonzero only) + relevance, with recency damping

Phase 2 (cross-entity boost):
  - Topic boosts from EIPs they mention (>=0.3 intrinsic), Final status, shipped fork
  - Clamp to [0, 1], then percentile-normalize per entity type

Outputs four tables:
  1) Top 20 Topics
  2) Top 20 EIPs
  3) Top 20 Papers
  4) Combined Top 50

Usage:
  python3 prototype_scoring.py
"""

from __future__ import annotations

import json
import math
import sys
from bisect import bisect_left
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


# Constants
CURRENT_YEAR = 2026  # Recency damping anchor


# ------------------------------ Utilities ---------------------------------
def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: File not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"Error: Failed to parse JSON {path}: {e}")


def parse_date(d: Any) -> date | None:
    """Parse a date-like string into a date. Returns None if not parseable.

    Accepts common ISO-ish forms (YYYY, YYYY-MM, YYYY-MM-DD)."""
    if d in (None, "", 0):
        return None
    if isinstance(d, (int, float)):
        # Not expected, but handle yyyy as int
        try:
            return date(int(d), 1, 1)
        except Exception:
            return None
    s = str(d).strip()
    # Try full ISO first
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            # Fill missing parts (month/day) with 1
            year = dt.year
            month = dt.month if "%m" in fmt else 1
            day = dt.day if "%d" in fmt else 1
            return date(year, month, day)
        except ValueError:
            continue
    # Try fromisoformat (covers some variants)
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def percentile_ranks(values: List[float]) -> List[float]:
    """Compute percentile_rank per the spec for a list of values.

    Definition: for value v in values, return count(values < v)/(n-1) if n>1 else 0.5.
    We use a sorted copy and bisect_left for O(n log n).
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [0.5]
    sorted_vals = sorted(values)
    denom = float(n - 1)
    out = []
    for v in values:
        # number strictly less is index of first occurrence
        idx = bisect_left(sorted_vals, v)
        out.append(idx / denom)
    return out


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def trunc(s: str, maxlen: int) -> str:
    s = (s or "").replace("\n", " ").strip()
    if len(s) <= maxlen:
        return s
    if maxlen <= 3:
        return s[:maxlen]
    return s[: maxlen - 3] + "..."


# ------------------------------ Scoring ------------------------------------
def score_topics(all_topics: Dict[str, Dict[str, Any]],
                 eip_intrinsic: Dict[str, float],
                 shipped_fork_names: set[str],
                 eip_catalog: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Compute topic scores.

    Returns (intrinsic, final_normalized)
    """
    topic_ids = list(all_topics.keys())
    # Phase 1: intrinsic
    cit_raw = [float(all_topics[tid].get("in_degree", 0) or 0) for tid in topic_ids]
    eng_raw = []
    for tid in topic_ids:
        t = all_topics[tid]
        likes = float(t.get("like_count", 0) or 0)
        posts = float(t.get("posts_count", 0) or 0)
        views = float(t.get("views", 0) or 0)
        eng = likes + math.sqrt(max(posts, 0.0)) + math.log1p(max(views, 0.0))
        eng_raw.append(eng)
    cit_pct = percentile_ranks(cit_raw)
    eng_pct = percentile_ranks(eng_raw)
    intrinsic = {tid: 0.50 * cit_pct[i] + 0.50 * eng_pct[i] for i, tid in enumerate(topic_ids)}

    # Phase 2: cross-entity boost
    # - +0.05 per mentioned EIP with intrinsic >= 0.3, capped at +0.15
    # - +0.03 for each Final EIP mentioned
    # - +0.05 for each EIP whose fork is shipped mentioned
    boosted_raw = {}
    for tid in topic_ids:
        t = all_topics[tid]
        mentions = t.get("eip_mentions", []) or []
        boost = 0.0
        good_eips = 0
        for eip in mentions:
            eip_str = str(eip)
            ei = eip_intrinsic.get(eip_str, 0.0)
            if ei >= 0.3:
                good_eips += 1
        boost += min(0.15, 0.05 * good_eips)

        # Extra boosts from Final and shipped fork status
        for eip in mentions:
            eip_str = str(eip)
            e = eip_catalog.get(eip_str)
            if not isinstance(e, dict):
                continue
            if str(e.get("status", "")) == "Final":
                boost += 0.03
            if (e.get("fork") or None) in shipped_fork_names:
                boost += 0.05

        boosted_raw[tid] = clamp01(intrinsic[tid] + boost)

    # Return both intrinsic and boosted_raw; normalization is done by caller
    return intrinsic, boosted_raw


def score_eips(eip_catalog: Dict[str, Dict[str, Any]], shipped_fork_names: set[str]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Compute EIP intrinsic and normalized final scores.

    Returns (intrinsic, final_normalized)
    """
    status_map = {
        "Final": 1.0,
        "Living": 0.85,
        "Last Call": 0.65,
        "Review": 0.5,
        "Draft": 0.3,
        "Stagnant": 0.1,
        "Withdrawn": 0.05,
        "Moved": 0.02,
    }

    eip_ids = list(eip_catalog.keys())
    # Engagement raw
    eng_raw = []
    eth_cites_raw = []
    for eid in eip_ids:
        e = eip_catalog[eid]
        likes = float(e.get("magicians_likes", 0) or 0)
        views = float(e.get("magicians_views", 0) or 0)
        posts = float(e.get("magicians_posts", 0) or 0)
        eng_raw.append(likes + math.log1p(max(views, 0.0)) + math.sqrt(max(posts, 0.0)))
        eth_cites_raw.append(float(e.get("ethresearch_citation_count", 0) or 0))

    eng_pct = percentile_ranks(eng_raw)
    eth_pct = percentile_ranks(eth_cites_raw)

    intrinsic: Dict[str, float] = {}
    for i, eid in enumerate(eip_ids):
        e = eip_catalog[eid]
        status_score = status_map.get(str(e.get("status", "")), 0.0)
        fork_score = 1.0 if (e.get("fork") or None) in shipped_fork_names else 0.0
        requires = e.get("requires", []) or []
        requires_score = min(1.0, 0.15 * len(requires))
        s = (
            0.20 * status_score
            + 0.25 * eng_pct[i]
            + 0.25 * eth_pct[i]
            + 0.20 * fork_score
            + 0.10 * requires_score
        )
        intrinsic[eid] = s

    # Clamp then percentile-normalize
    pre_norm = [clamp01(intrinsic[eid]) for eid in eip_ids]
    final_pct = percentile_ranks(pre_norm)
    final = {eip_ids[i]: final_pct[i] for i in range(len(eip_ids))}
    return intrinsic, final


def score_papers(papers: List[Dict[str, Any]]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Compute intrinsic and final percentile-normalized scores for papers."""
    # Build arrays
    ids: List[str] = []
    cites_raw: List[float] = []
    rel_raw: List[float] = []
    for p in papers:
        pid = str(p.get("id", "")).strip()
        title = p.get("title")
        if not pid or not title:
            continue
        ids.append(pid)
        cb = int(p.get("cited_by_count", 0) or 0)
        cites_raw.append(float(cb if cb > 0 else 0))
        rel_raw.append(float(p.get("relevance_score", 0.0) or 0.0))

    # Citation percentile among nonzero only
    nonzero = [c for c in cites_raw if c > 0]
    if len(nonzero) == 0:
        cites_pct = [0.0 for _ in cites_raw]
    elif len(nonzero) == 1:
        # single nonzero => that one gets 0.5, zeros get 0
        val = nonzero[0]
        cites_pct = [0.5 if c == val and c > 0 else 0.0 for c in cites_raw]
    else:
        nz_sorted = sorted(nonzero)
        denom = float(len(nonzero) - 1)
        # map each c>0 to its percentile per spec
        def nz_rank(v: float) -> float:
            return bisect_left(nz_sorted, v) / denom

        cites_pct = [nz_rank(c) if c > 0 else 0.0 for c in cites_raw]

    rel_pct = percentile_ranks(rel_raw)

    intrinsic: Dict[str, float] = {}
    # build id->paper map once
    pid_map = {str(p.get("id", "")).strip(): p for p in papers if str(p.get("id", "")).strip()}
    for i, pid in enumerate(ids):
        base = 0.55 * cites_pct[i] + 0.45 * rel_pct[i]
        # Recency damping relative to CURRENT_YEAR
        y = pid_map.get(pid, {}).get("year")
        damp = 1.0
        if isinstance(y, int):
            if y == CURRENT_YEAR:
                damp = 0.6
            elif y == CURRENT_YEAR - 1:
                damp = 0.75
            elif y == CURRENT_YEAR - 2:
                damp = 0.9
        intrinsic[pid] = base * damp

    # Clamp and percentile-normalize
    pre_norm = [clamp01(intrinsic[pid]) for pid in ids]
    final_pct = percentile_ranks(pre_norm)
    final = {ids[i]: final_pct[i] for i in range(len(ids))}
    return intrinsic, final


def papers_by_id(papers: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(p.get("id", "")).strip(): p for p in papers if str(p.get("id", "")).strip()}


# ------------------------------ Pipeline -----------------------------------
def compute_scores(analysis: Dict[str, Any], papers_payload: Dict[str, Any]) -> Dict[str, Any]:
    topics = analysis.get("topics", {}) or {}
    minor_topics = analysis.get("minor_topics", {}) or {}
    # Combine topics + minor_topics into one pool
    all_topics: Dict[str, Dict[str, Any]] = {}
    for k, v in topics.items():
        all_topics[str(k)] = v
    for k, v in minor_topics.items():
        all_topics[str(k)] = v

    eip_catalog: Dict[str, Dict[str, Any]] = analysis.get("eip_catalog", {}) or {}

    # Shipped forks: date != None and date <= today
    shipped_fork_names: set[str] = set()
    today = date.today()
    for f in analysis.get("forks", []) or []:
        d = parse_date(f.get("date"))
        if d is not None and d <= today:
            name = f.get("name")
            if name:
                shipped_fork_names.add(name)

    # Phase 1: EIPs first (topics boosts depend on EIP intrinsic)
    eip_intrinsic, eip_final = score_eips(eip_catalog, shipped_fork_names)

    # Phase 1: Topics (with cross-entity boosts applied here)
    topic_intrinsic, topic_boosted_raw = score_topics(all_topics, eip_intrinsic, shipped_fork_names, eip_catalog)

    # Clamp topics then normalize
    topic_ids = list(all_topics.keys())
    topic_pre_norm = [clamp01(topic_boosted_raw[tid]) for tid in topic_ids]
    topic_final_pct = percentile_ranks(topic_pre_norm)
    topic_final = {topic_ids[i]: topic_final_pct[i] for i in range(len(topic_ids))}

    # Papers
    papers = papers_payload.get("papers", []) if isinstance(papers_payload, dict) else papers_payload
    paper_intrinsic, paper_final = score_papers(papers)

    return {
        "topics": {
            "intrinsic": topic_intrinsic,
            "final": topic_final,
        },
        "eips": {
            "intrinsic": eip_intrinsic,
            "final": eip_final,
        },
        "papers": {
            "intrinsic": paper_intrinsic,
            "final": paper_final,
        },
        "context": {
            "shipped_forks": sorted(shipped_fork_names),
            "counts": {
                "topics": len(topic_ids),
                "eips": len(eip_catalog),
                "papers": len(papers),
            },
        },
    }


# ------------------------------ Printing -----------------------------------
def print_tables(analysis: Dict[str, Any], papers_payload: Dict[str, Any], scores: Dict[str, Any]) -> None:
    topics = analysis.get("topics", {}) or {}
    minor_topics = analysis.get("minor_topics", {}) or {}
    all_topics: Dict[str, Dict[str, Any]] = {**{str(k): v for k, v in topics.items()}, **{str(k): v for k, v in minor_topics.items()}}
    eip_catalog: Dict[str, Dict[str, Any]] = analysis.get("eip_catalog", {}) or {}
    papers: List[Dict[str, Any]] = papers_payload.get("papers", []) if isinstance(papers_payload, dict) else papers_payload
    p_by_id = papers_by_id(papers)

    topic_final = scores["topics"]["final"]
    topic_intr = scores["topics"]["intrinsic"]
    eip_final = scores["eips"]["final"]
    eip_intr = scores["eips"]["intrinsic"]
    paper_final = scores["papers"]["final"]
    paper_intr = scores["papers"]["intrinsic"]

    # === TOP 20 TOPICS ===
    print("=== TOP 20 TOPICS ===")
    # Columns: rank, id, title(50), old_score, new_score, delta
    print(f"{ 'Rank':>4} {'ID':<12} {'Title':<50} {'Old':>7} {'New':>7} {'Delta':>7}")
    topic_rows = []
    for tid, t in all_topics.items():
        old = float(t.get("influence_score", 0.0) or 0.0)
        new = float(topic_final.get(tid, 0.0))
        topic_rows.append((tid, trunc(t.get("title", ""), 50), old, new))
    topic_rows.sort(key=lambda r: r[3], reverse=True)
    for i, (tid, title, old, new) in enumerate(topic_rows[:20], start=1):
        delta = new - old
        print(f"{i:>4} {str(all_topics.get(tid, {}).get('id', tid))[:12]:<12} {title:<50} {old:7.3f} {new:7.3f} {delta:7.3f}")

    # === TOP 20 EIPs ===
    print("\n=== TOP 20 EIPs ===")
    print(f"{ 'Rank':>4} {'EIP':<8} {'Title':<50} {'Old':>7} {'New':>7} {'Delta':>7}")
    eip_rows = []
    for eid, e in eip_catalog.items():
        old = float(e.get("influence_score", 0.0) or 0.0)
        new = float(eip_final.get(eid, 0.0))
        eip_rows.append((eid, trunc(e.get("title", ""), 50), old, new))
    eip_rows.sort(key=lambda r: r[3], reverse=True)
    for i, (eid, title, old, new) in enumerate(eip_rows[:20], start=1):
        delta = new - old
        print(f"{i:>4} {str(eid):<8} {title:<50} {old:7.3f} {new:7.3f} {delta:7.3f}")

    # === TOP 20 PAPERS ===
    print("\n=== TOP 20 PAPERS ===")
    # Columns: rank, title(55), year, cited_by, old_relevance, new_score
    print(f"{ 'Rank':>4} {'Title':<55} {'Year':>6} {'CitedBy':>8} {'OldRel':>8} {'New':>7}")
    paper_rows = []
    for pid, p in p_by_id.items():
        year = p.get("year", "?")
        cited = int(p.get("cited_by_count", 0) or 0)
        old_rel = float(p.get("relevance_score", 0.0) or 0.0)
        new = float(paper_final.get(pid, 0.0))
        paper_rows.append((trunc(p.get("title", ""), 55), year, cited, old_rel, new))
    paper_rows.sort(key=lambda r: r[-1], reverse=True)
    for i, (title, year, cited, old_rel, new) in enumerate(paper_rows[:20], start=1):
        print(f"{i:>4} {title:<55} {str(year):>6} {cited:>8} {old_rel:>8.3f} {new:7.3f}")

    # === COMBINED TOP 50 ===
    print("\n=== COMBINED TOP 50 ===")
    print(f"{ 'Rank':>4} {'Type':<6} {'Identifier':<14} {'Title':<45} {'New':>7}")
    combined: List[Tuple[str, str, str, float]] = []
    for tid, t in all_topics.items():
        combined.append(("Topic", str(t.get("id", tid)), trunc(t.get("title", ""), 45), float(topic_final.get(tid, 0.0))))
    for eid, e in eip_catalog.items():
        combined.append(("EIP", str(eid), trunc(e.get("title", ""), 45), float(eip_final.get(eid, 0.0))))
    for pid, p in p_by_id.items():
        combined.append(("Paper", str(pid), trunc(p.get("title", ""), 45), float(paper_final.get(pid, 0.0))))
    combined.sort(key=lambda r: r[3], reverse=True)
    for i, (etype, ident, title, new) in enumerate(combined[:50], start=1):
        print(f"{i:>4} {etype:<6} {ident:<14} {title:<45} {new:7.3f}")


def main() -> None:
    base = Path.cwd()
    analysis = load_json(base / "analysis.json")
    papers_payload = load_json(base / "papers-db.json")
    scores = compute_scores(analysis, papers_payload)
    print_tables(analysis, papers_payload, scores)


if __name__ == "__main__":
    main()
