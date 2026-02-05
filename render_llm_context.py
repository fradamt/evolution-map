#!/usr/bin/env python3
"""Render analysis.json → evolution-map-llm.md (LLM-optimized context document).

Generates a ~15-20K token Markdown document designed for LLM context windows.
Enables answering questions like: "What research led to EIP-4844?",
"Who's working on PBS?", "What topics should I cite for SSF?"

Usage:
    python3 render_llm_context.py
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_PATH = SCRIPT_DIR / "analysis.json"
OUTPUT_PATH = SCRIPT_DIR / "evolution-map-llm.md"

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
        return "ACTIVE"
    if recent >= 2:
        return "MODERATE"
    return "DORMANT"


def topic_link(tid, title):
    return f"[{title}](https://ethresear.ch/t/{tid})"


def eip_link(num):
    return f"[EIP-{num}](https://eips.ethereum.org/EIPS/eip-{num})"


def main():
    with open(ANALYSIS_PATH) as f:
        data = json.load(f)

    meta = data["metadata"]
    topics = data["topics"]
    authors = data["authors"]
    threads = data["research_threads"]
    forks = data["forks"]
    graph = data["graph"]

    # Pre-compute: EIP → fork mapping
    eip_to_fork = {}
    for fork in forks:
        for eip in fork["eips"]:
            eip_to_fork[eip] = fork.get("combined_name") or fork["name"]

    # Sort topics by influence
    all_topics = sorted(topics.values(), key=lambda t: t["influence_score"], reverse=True)

    lines = []
    w = lines.append

    # === HEADER ===
    w("# Ethereum Research Map — LLM Context")
    w("")
    # Compute date range from topics
    all_dates = sorted(t["date"] for t in topics.values() if t.get("date"))
    year_range = f"{all_dates[0][:4]}–{all_dates[-1][:4]}" if all_dates else "?"

    w(f"Generated from {meta['total_topics']:,} ethresear.ch topics ({year_range}). "
      f"{meta['included']} influential topics connected by {meta['included_edges']} citations.")
    w("")

    # === THREAD OVERVIEW TABLE ===
    w("## Thread Overview")
    w("")
    w("| Thread | Status | Topics | Date Range | Key Authors |")
    w("|--------|--------|--------|------------|-------------|")
    for tid in THREAD_ORDER:
        th = threads.get(tid)
        if not th:
            continue
        status = thread_status(th)
        dr = th.get("date_range", ["?", "?"])
        key_authors = ", ".join(list(th.get("key_authors", {}).keys())[:3])
        w(f"| {th['name']} | {status} | {th['topic_count']} | {dr[0][:7]}–{dr[1][:7]} | {key_authors} |")
    w("")

    # === PER-THREAD SECTIONS ===
    for tid in THREAD_ORDER:
        th = threads.get(tid)
        if not th:
            continue
        status = thread_status(th)
        w(f"## Thread: {th['name']}")
        w("")
        w(f"**Status:** {status} · **Topics:** {th['topic_count']} · "
          f"**Peak year:** {th.get('peak_year', '?')} · "
          f"**Active years:** {', '.join(str(y) for y in th.get('active_years', []))}")
        w("")

        # Milestones
        milestones = th.get("milestones", [])
        if milestones:
            w("**Milestones:**")
            for ms in milestones:
                note = ms.get("note", "").replace("_", " ")
                w(f"- {ms['date'][:7]} — {ms['title'][:80]} ({note})")
            w("")

        # Top 5 topics with excerpts
        top_ids = th.get("top_topics", [])[:5]
        if top_ids:
            w("**Key topics:**")
            for top_id in top_ids:
                t = topics.get(str(top_id))
                if not t:
                    continue
                excerpt = t.get("first_post_excerpt", "")[:200]
                if len(t.get("first_post_excerpt", "")) > 200:
                    excerpt = excerpt.rstrip(".,;:!? ") + "..."
                w(f"- {topic_link(t['id'], t['title'])} ({t['date'][:7]}, by {t['author']}) — {excerpt}")
            w("")

        # EIPs discussed → which fork shipped them
        eip_mentions = th.get("top_eips", th.get("eip_mentions", []))[:8]
        if eip_mentions:
            eip_parts = []
            for e in eip_mentions:
                fork = eip_to_fork.get(e, "unshipped")
                eip_parts.append(f"EIP-{e} ({fork})")
            w(f"**EIPs:** {', '.join(eip_parts)}")
            w("")

        # Key authors
        ka = th.get("key_authors", {})
        if ka:
            w(f"**Key authors:** {', '.join(f'{name} ({count})' for name, count in list(ka.items())[:5])}")
            w("")

    # === CROSS-THREAD CONNECTIONS ===
    w("## Cross-Thread Connections")
    w("")

    # Find topics that cite topics in different threads (bridge topics)
    bridge_topics = []
    for t in all_topics[:200]:
        t_thread = t.get("research_thread")
        if not t_thread:
            continue
        out_refs = t.get("outgoing_refs", [])
        in_refs = t.get("incoming_refs", [])
        other_threads = set()
        for ref_id in out_refs + in_refs:
            ref = topics.get(str(ref_id))
            if ref and ref.get("research_thread") and ref["research_thread"] != t_thread:
                other_threads.add(ref["research_thread"])
        if len(other_threads) >= 2:
            bridge_topics.append((t, other_threads))

    bridge_topics.sort(key=lambda x: len(x[1]), reverse=True)
    w("**Bridge topics** (citing across 2+ threads):")
    for t, other_ths in bridge_topics[:10]:
        thread_names = []
        for ot in other_ths:
            th_obj = threads.get(ot)
            if th_obj:
                thread_names.append(th_obj["name"])
        w(f"- {topic_link(t['id'], t['title'])} ({t.get('research_thread', '?')}) → {', '.join(thread_names)}")
    w("")

    # Author overlap between threads
    w("**Author overlap:**")
    thread_authors = {}
    for tid in THREAD_ORDER:
        th = threads.get(tid)
        if th:
            thread_authors[tid] = set(th.get("key_authors", {}).keys())

    overlaps = []
    tids = [t for t in THREAD_ORDER if t in thread_authors]
    for i in range(len(tids)):
        for j in range(i + 1, len(tids)):
            shared = thread_authors[tids[i]] & thread_authors[tids[j]]
            if shared:
                n1 = threads[tids[i]]["name"]
                n2 = threads[tids[j]]["name"]
                overlaps.append((n1, n2, shared))
    overlaps.sort(key=lambda x: len(x[2]), reverse=True)
    for n1, n2, shared in overlaps[:8]:
        w(f"- {n1} ↔ {n2}: {', '.join(sorted(shared))}")
    w("")

    # === FORK TIMELINE ===
    w("## Fork Timeline")
    w("")
    for fork in forks:
        if not fork.get("date"):
            label = f"**{fork['name']}** (unscheduled)"
        else:
            label = f"**{fork['name']}** ({fork['date']})"
        eip_strs = [f"EIP-{e}" for e in fork["eips"][:10]]
        w(f"- {label}: {', '.join(eip_strs) if eip_strs else 'N/A'}")

        # Related research topics
        related = fork.get("related_topics", [])[:3]
        for rt_id in related:
            rt = topics.get(str(rt_id))
            if rt:
                w(f"  - {topic_link(rt['id'], rt['title'])}")
    w("")

    # === CITATION INDEX (TOP 50) ===
    w("## Citation Index (Top 50 by Influence)")
    w("")
    w("| # | Title | Author | Date | Thread | Inf. | Cited by |")
    w("|---|-------|--------|------|--------|------|----------|")
    for i, t in enumerate(all_topics[:50], 1):
        thread_name = ""
        if t.get("research_thread") and t["research_thread"] in threads:
            thread_name = threads[t["research_thread"]]["name"]
        title_short = t["title"][:60]
        if len(t["title"]) > 60:
            title_short += "..."
        w(f"| {i} | {topic_link(t['id'], title_short)} | {t['author']} | {t['date'][:7]} | {thread_name} | {t['influence_score']:.2f} | {t['in_degree']} |")
    w("")

    # === WRITE OUTPUT ===
    output = "\n".join(lines)
    with open(OUTPUT_PATH, "w") as f:
        f.write(output)

    # Estimate tokens (~4 chars per token)
    token_est = len(output) // 4
    print(f"Written: {OUTPUT_PATH} ({len(output):,} chars, ~{token_est:,} tokens)")


if __name__ == "__main__":
    main()
