#!/usr/bin/env python3
"""Render analysis.json → evolution-map.md (narrative document).

Produces an ~8,000-10,000 word Markdown document covering:
1. Executive Summary
2. The Researchers (top author profiles)
3. Research Threads (narrative per thread)
4. Era Analysis
5. Methodology
6. Appendix A: Top 100 Topics
7. Appendix B: Fork Timeline with Topic Cross-References

Usage:
    python3 render_markdown.py
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_PATH = SCRIPT_DIR / "analysis.json"
OUTPUT_PATH = SCRIPT_DIR / "evolution-map.md"

THREAD_ORDER = [
    "pos_casper", "sharding_da", "plasma_l2", "fee_markets",
    "pbs_mev", "ssf", "issuance_economics", "inclusion_lists",
    "based_preconf", "zk_proofs", "state_execution", "privacy_identity",
]

ERA_ORDER = ["genesis", "scaling_wars", "eth2_design", "post_merge_build", "endgame"]


def topic_link(topic):
    """Generate a Markdown link to an ethresear.ch topic."""
    tid = topic["id"]
    title = topic["title"]
    return f"[{title}](https://ethresear.ch/t/{tid})"


def eip_link(eip_num):
    """Generate a Markdown link to an EIP."""
    return f"[EIP-{eip_num}](https://eips.ethereum.org/EIPS/eip-{eip_num})"


def main():
    with open(ANALYSIS_PATH) as f:
        data = json.load(f)

    meta = data["metadata"]
    eras = {e["id"]: e for e in data["eras"]}
    forks = data["forks"]
    topics = data["topics"]
    authors = data["authors"]
    threads = data["research_threads"]

    # Sort topics by influence
    all_topics_sorted = sorted(topics.values(), key=lambda t: t["influence_score"], reverse=True)
    top_100 = all_topics_sorted[:100]

    # Authors sorted by influence
    authors_sorted = sorted(authors.values(), key=lambda a: a["influence_score"], reverse=True)

    lines = []
    w = lines.append

    # ===================================================================
    # TITLE
    # ===================================================================
    w("# Ethereum Research Evolution Map")
    w("")
    w(f"*An analysis of {meta['total_topics']:,} ethresear.ch topics (2017–2026), "
      f"tracing how ideas became protocol.*")
    w("")

    # ===================================================================
    # 1. EXECUTIVE SUMMARY
    # ===================================================================
    w("## 1. Executive Summary")
    w("")

    # Stats
    thread_topic_sum = sum(t["topic_count"] for t in threads.values())
    fork_count = sum(1 for f in forks if f["date"])

    w(f"From September 2017 to February 2026, the Ethereum research forum "
      f"accumulated **{meta['total_topics']:,} topics** — a living record of how "
      f"one of the most ambitious distributed systems projects evolved in the open.")
    w("")
    w(f"This analysis identifies **{meta['included']} influential topics** connected by "
      f"**{meta['included_edges']:,} cross-references**, organized into "
      f"**{len(threads)} research threads** across **5 eras**, spanning "
      f"**{fork_count} mainnet forks** from Byzantium (2017) through Fusaka (2025).")
    w("")

    # Key findings
    w("### Key Findings")
    w("")
    w("- **The forum's center of gravity shifted dramatically.** Early years (2017–2018) "
      "were dominated by sharding and Plasma; by 2023–2026, the discourse had moved to "
      "PBS, staking economics, and based rollups — reflecting the pivot from execution "
      "sharding to a rollup-centric roadmap.")
    w("- **Research-to-deployment lag varies widely.** EIP-1559 was discussed on "
      "ethresear.ch as early as 2018 and shipped in London (August 2021) — a 3-year cycle. "
      "Proposer-builder separation, first formalized in 2021, has its enshrined version "
      "(EIP-7732) targeted for Glamsterdam, still unscheduled as of 2026.")
    w("- **A small cohort drives outsized impact.** The top 5 authors by influence "
      "(vbuterin, JustinDrake, mikeneuder, Nero_eth, aelowsson) created "
      f"{sum(authors[a]['topics_created'] for a in ['vbuterin','JustinDrake','mikeneuder','Nero_eth','aelowsson'] if a in authors)} "
      "of the included topics — but the community broadened significantly post-2022.")

    w("")

    # ===================================================================
    # 2. THE RESEARCHERS
    # ===================================================================
    w("## 2. The Researchers")
    w("")
    w("The ethresear.ch community evolved from a small group of core researchers into a "
      "broader ecosystem. Here are the most influential contributors, measured by topic "
      "count, citation impact (in-degree from other topics), and community engagement (likes).")
    w("")

    for i, author in enumerate(authors_sorted[:15]):
        username = author["username"]
        years = author["active_years"]
        year_range = f"{years[0]}–{years[-1]}" if years else "unknown"

        w(f"### {i+1}. {username}")
        w("")
        w(f"**Active:** {year_range} · "
          f"**Topics:** {author['topics_created']} · "
          f"**Likes received:** {author['total_likes']} · "
          f"**Cited by:** {author['total_in_degree']} other topics")
        w("")

        # Category focus
        if author["category_focus"]:
            cats = ", ".join(f"{cat} ({n})" for cat, n in list(author["category_focus"].items())[:3])
            w(f"**Focus areas:** {cats}")
            w("")

        # Thread focus
        if author["thread_focus"]:
            thread_names = []
            for tid, count in list(author["thread_focus"].items())[:3]:
                if tid in threads:
                    thread_names.append(threads[tid]["name"])
            if thread_names:
                w(f"**Research threads:** {', '.join(thread_names)}")
                w("")

        # Top topics
        top = author["top_topics"][:5]
        if top:
            w("**Most influential topics:**")
            for tid in top:
                t = topics.get(str(tid))
                if t:
                    w(f"- {topic_link(t)} ({t['date'][:4]}, influence: {t['influence_score']:.2f})")
            w("")

        # Co-researchers
        if author["co_researchers"]:
            top_co = list(author["co_researchers"].items())[:5]
            co_names = ", ".join(f"{name} ({count})" for name, count in top_co)
            w(f"**Frequent collaborators:** {co_names}")
            w("")

        # Narrative color for top authors
        if username == "vbuterin":
            w("Vitalik's research presence on ethresear.ch is unmatched — spanning every "
              "major thread from Casper and sharding through PBS and SSF. His posts often "
              "serve as foundational framings that the community then iterates on. His "
              "posting volume peaked during the Scaling Wars era (2018) and surged again "
              "in the Endgame Architecture era (2023–2026) as the protocol's endgame "
              "design crystallized.")
            w("")
        elif username == "JustinDrake":
            w("Justin Drake emerged as the second most prolific researcher, with "
              "deep contributions to sharding, data availability, and more recently "
              "based rollups and preconfirmations. His work bridges theoretical "
              "proposals and practical protocol design, often co-developing ideas "
              "that later become EIPs.")
            w("")
        elif username == "mikeneuder":
            w("Mike Neuder rose to prominence in the 2023–2025 period as a key voice "
              "on PBS, inclusion lists, and censorship resistance — topics that define "
              "the post-MEV research agenda. His work on ePBS and FOCIL directly "
              "influenced Glamsterdam planning.")
            w("")

    w("---")
    w("")

    # ===================================================================
    # 3. RESEARCH THREADS
    # ===================================================================
    w("## 3. Research Threads")
    w("")
    w("Each thread traces a line of inquiry from early proposals through protocol deployment. "
      "Topics are connected by explicit cross-references — citations that researchers made "
      "when building on or responding to prior work.")
    w("")

    for thread_id in THREAD_ORDER:
        if thread_id not in threads:
            continue
        thread = threads[thread_id]

        w(f"### {thread['name']}")
        w("")

        # Stats line
        date_range = thread["date_range"]
        dr_str = f"{date_range[0][:4]}–{date_range[1][:4]}" if date_range[0] and date_range[1] else "—"
        w(f"**{thread['topic_count']} topics** · {dr_str} · "
          f"Top authors: {', '.join(list(thread['key_authors'].keys())[:5])}")
        w("")

        # EIP mentions
        if thread.get("eip_mentions"):
            eip_strs = [eip_link(e) for e in thread["eip_mentions"][:8]]
            w(f"**EIPs discussed:** {', '.join(eip_strs)}")
        w("")

        # Narrative per thread
        top_topics = thread["top_topics"][:10]
        topic_objs = [topics.get(str(tid)) for tid in top_topics]
        topic_objs = [t for t in topic_objs if t]

        # Write narrative based on thread type
        _write_thread_narrative(w, thread_id, thread, topic_objs, topics, topic_link)
        w("")

        # Top topics table
        w("| Topic | Author | Year | Influence | EIPs |")
        w("|-------|--------|------|-----------|------|")
        for t in topic_objs[:8]:
            eips_str = ", ".join(f"EIP-{e}" for e in t["eip_mentions"][:4]) if t["eip_mentions"] else "—"
            w(f"| {topic_link(t)} | {t['author']} | {t['date'][:4]} | {t['influence_score']:.2f} | {eips_str} |")
        w("")

    # ===================================================================
    # 4. ERA ANALYSIS
    # ===================================================================
    w("## 4. Era Analysis")
    w("")

    for era_id in ERA_ORDER:
        era = eras[era_id]
        era_topics = [t for t in all_topics_sorted if t.get("era") == era_id]

        w(f"### {era['name']} ({era['start'][:4]}–{era['end'][:4]})")
        w("")
        w(f"*{era['character']}*")
        w("")
        w(f"**{len(era_topics)} included topics**")
        w("")

        # What shipped
        era_forks = [f for f in forks if f["name"] in era.get("forks", [])]
        if era_forks:
            w("**What shipped:**")
            for f in era_forks:
                date_str = f["date"] or "TBD"
                eip_strs = ", ".join(f"EIP-{e}" for e in f["eips"][:6])
                label = f["combined_name"] or f["name"]
                w(f"- **{label}** ({date_str}): {eip_strs or 'beacon chain genesis'}")
            w("")

        # Thread distribution
        thread_dist = {}
        for t in era_topics:
            th = t.get("research_thread")
            if th and th in threads:
                thread_dist[th] = thread_dist.get(th, 0) + 1
        if thread_dist:
            sorted_threads = sorted(thread_dist.items(), key=lambda x: x[1], reverse=True)
            dist_str = ", ".join(f"{threads[tid]['name']} ({count})" for tid, count in sorted_threads[:5])
            w(f"**Dominant threads:** {dist_str}")
            w("")

        # Era narrative
        _write_era_narrative(w, era_id, era_topics, topics, topic_link)
        w("")

        # Top 5 topics of the era
        w("**Top topics:**")
        for t in era_topics[:5]:
            w(f"1. {topic_link(t)} by {t['author']} (influence: {t['influence_score']:.2f})")
        w("")

    # ===================================================================
    # 5. METHODOLOGY
    # ===================================================================
    w("## 5. Methodology")
    w("")
    w("### Data Source")
    w(f"All {meta['total_topics']:,} topics from ethresear.ch were scraped via the Discourse API, "
      "including full post content, cross-references (link_counts), view/like counts, "
      "tags, and participant lists.")
    w("")
    w("### Influence Score")
    w("Each topic receives a composite score:")
    w("```")
    w("influence = 0.30 × norm(in_degree)")
    w("         + 0.25 × norm(likes)")
    w("         + 0.20 × norm(log(views))")
    w("         + 0.15 × norm(posts_count)")
    w("         + 0.10 × prolific_author")
    w("```")
    w("Where `norm()` is min-max normalization across all topics, and `prolific_author` "
      "is 1.0 if the author has 5+ included topics.")
    w("")
    w("### Topic Filtering")
    w(f"- **Tier 1**: influence ≥ 0.25 or in-degree ≥ 3 ({meta['included']} topics after adjustment)")
    w("- **Tier 2**: referenced by a Tier 1 topic with influence ≥ 0.10")
    w(f"- Final set: **{meta['included']} topics** from {meta['total_topics']:,} total")
    w("")
    w("### Cross-References")
    w(f"Extracted from `post_stream.posts[].link_counts[]` where `internal=true`. "
      f"Total: {meta['total_edges']:,} edges, {meta['included_edges']:,} after filtering "
      "to included topics.")
    w("")
    w("### Research Threads")
    w("Assigned via seed-based pattern matching on topic titles, tags, post content, "
      "and author identity. Each topic is assigned to its best-matching thread "
      "(minimum score threshold: 1.5).")
    w("")
    w("### EIP Mapping")
    w("EIP numbers extracted via regex from topic titles and post content (HTML). "
      "Primary EIPs are those mentioned in the title or referenced ≥3 times in "
      "the opening post. All other mentions are recorded as secondary references.")
    w("")

    # ===================================================================
    # 6. APPENDIX A: TOP 100 TOPICS
    # ===================================================================
    w("## Appendix A: Top 100 Topics by Influence")
    w("")
    w("| # | Topic | Author | Date | Score | In° | Likes | Thread |")
    w("|---|-------|--------|------|-------|-----|-------|--------|")
    for i, t in enumerate(top_100, 1):
        thread_name = threads[t["research_thread"]]["name"] if t.get("research_thread") and t["research_thread"] in threads else "—"
        w(f"| {i} | {topic_link(t)} | {t['author']} | {t['date']} | "
          f"{t['influence_score']:.2f} | {t['in_degree']} | {t['like_count']} | "
          f"{thread_name} |")
    w("")

    # ===================================================================
    # 7. APPENDIX B: FORK TIMELINE
    # ===================================================================
    w("## Appendix B: Fork Timeline with Topic Cross-References")
    w("")
    w("| Fork | Date | EIPs | Related Topics |")
    w("|------|------|------|----------------|")
    for f in forks:
        if not f["date"]:
            date_str = "TBD"
        else:
            date_str = f["date"]
        label = f["combined_name"] or f["name"]
        eips = ", ".join(str(e) for e in f["eips"][:6])
        related = f["related_topics"][:5]
        if related:
            topic_strs = "; ".join(
                f"[{topics[str(tid)]['title'][:40]}...](https://ethresear.ch/t/{tid})"
                if len(topics.get(str(tid), {}).get("title", "")) > 40
                else f"[{topics[str(tid)]['title']}](https://ethresear.ch/t/{tid})"
                for tid in related if str(tid) in topics
            )
        else:
            topic_strs = "—"
        w(f"| {label} | {date_str} | {eips or '—'} | {topic_strs} |")
    w("")

    # ===================================================================
    # Write output
    # ===================================================================
    content = "\n".join(lines)
    with open(OUTPUT_PATH, "w") as f:
        f.write(content)

    word_count = len(content.split())
    print(f"Written: {OUTPUT_PATH}")
    print(f"  {word_count:,} words, {len(lines)} lines")


# ---------------------------------------------------------------------------
# Thread narratives
# ---------------------------------------------------------------------------
def _write_thread_narrative(w, thread_id, thread, top_topics, all_topics, topic_link):
    """Write a narrative paragraph for each research thread."""

    if thread_id == "pos_casper":
        w("The Proof-of-Stake thread is the bedrock of ethresear.ch. The forum launched "
          "in September 2017 with Casper as the central research question: how to replace "
          "proof-of-work with a provably secure proof-of-stake protocol. Early posts explored "
          "Casper FFG (the finality gadget) and Casper CBC (the correct-by-construction "
          "variant), with Vitalik and Justin Drake as the primary architects.")
        w("")
        w("The thread tracks the full arc from theoretical Casper designs through the "
          "beacon chain spec (Phase 0, launched December 2020) to the Merge itself "
          "(September 2022). Key inflection points include the pivot from Casper CBC "
          "to pure FFG+LMD-GHOST, the decision to separate the beacon chain from "
          "execution (leading to the Merge architecture), and the post-Merge focus on "
          "validator set management and attestation optimization.")

    elif thread_id == "sharding_da":
        w("Sharding dominated ethresear.ch's first two years. The original vision was "
          "*execution sharding* — running the EVM across many parallel chains. This "
          "evolved through a series of increasingly sophisticated proposals: quadratic "
          "sharding, super-quadratic sharding, cross-shard transactions, and ultimately "
          "the realization that data availability was the core primitive to get right.")
        w("")
        w("By 2020, the pivot to *data availability sharding* was underway, culminating "
          "in Danksharding and its pragmatic first step, proto-danksharding (EIP-4844), "
          "which shipped in Cancun (March 2024). The thread continues through PeerDAS "
          "(EIP-7594), which shipped in Fusaka (December 2025), implementing distributed "
          "data availability sampling via data columns.")

    elif thread_id == "plasma_l2":
        w("The Plasma thread captures one of Ethereum's most dramatic pivots. In 2018, "
          "Plasma was the primary L2 scaling solution — Minimal Viable Plasma, Plasma "
          "Cash, and Plasma Debit generated enormous discussion. But fundamental data "
          "availability challenges led to the rise of rollups by 2019–2020.")
        w("")
        w("The thread traces this transition through optimistic rollups, zk-rollups, "
          "and eventually the rollup-centric roadmap that defines Ethereum today. "
          "Recent developments include *based rollups* (sequenced by L1 proposers) "
          "and *native rollups* — ideas that may eventually dissolve the L1/L2 boundary.")

    elif thread_id == "fee_markets":
        w("Fee market research on ethresear.ch predates EIP-1559 and continues well "
          "beyond it. The thread began with analysis of first-price auction inefficiencies "
          "and gas price volatility, leading to the base fee mechanism that shipped in "
          "London (August 2021). But the bigger story is the evolution toward "
          "*multidimensional* resource pricing.")
        w("")
        w("EIP-4844 introduced a separate blob gas market in Cancun, and research "
          "continues on further resource dimensions (state access, computation, "
          "bandwidth). The thread connects directly to EIP-8037 (state growth metering), "
          "still in development, which would add a third gas dimension.")

    elif thread_id == "pbs_mev":
        w("Proposer-builder separation emerged from the MEV crisis of 2021. As MEV "
          "extraction became systematic, researchers recognized that block building "
          "and block proposing needed to be separated to preserve validator "
          "decentralization. The thread tracks the evolution from external PBS (via "
          "MEV-Boost and Flashbots) to enshrined PBS (ePBS).")
        w("")
        w("Key developments include the original PBS proposal, MEV burn mechanisms "
          "(returning MEV value to the protocol), payload timeliness committees, "
          "and the ongoing debate about inclusion lists as a complement to ePBS. "
          "EIP-7732 (ePBS) is targeted for Glamsterdam, making this one of the "
          "longest-running research-to-deployment pipelines on ethresear.ch.")

    elif thread_id == "ssf":
        w("Single Slot Finality aims to finalize blocks in a single slot (~12 seconds) "
          "rather than the current ~13 minutes (2 epochs). The thread is relatively "
          "small but contains some of the most architecturally ambitious proposals on "
          "the forum. Key challenges include aggregating signatures from the full "
          "validator set and maintaining economic security.")
        w("")
        w("Variants include 3SF (three-slot finality) and Orbit SSF, which uses "
          "rotating validator subsets. These proposals interact deeply with the staking "
          "economics thread (since validator set size affects aggregation costs) "
          "and PBS (since finality timing affects MEV dynamics).")

    elif thread_id == "issuance_economics":
        w("The issuance and staking economics thread gained momentum post-Merge, when "
          "Ethereum's monetary policy became a live research question. Core debates "
          "include the optimal staking ratio, minimum viable issuance (reducing ETH "
          "inflation to the minimum needed for security), and the effects of liquid "
          "staking derivatives.")
        w("")
        w("Anders Elowsson, Caspar Schwarz-Schilling, and Barnabé Monnot are the "
          "primary contributors, producing detailed quantitative analyses of reward "
          "curves and staking equilibria. EIP-7251 (MaxEB increase, shipped in Pectra) "
          "emerged partly from this thread's work on validator consolidation economics.")

    elif thread_id == "inclusion_lists":
        w("Inclusion lists address censorship resistance — ensuring that even a "
          "compromised or extractive builder cannot indefinitely exclude valid "
          "transactions. The thread tracks the evolution from simple CR-lists through "
          "unconditional inclusion lists to the FOCIL (Fork-Choice Enforced Inclusion "
          "Lists) proposal.")
        w("")
        w("Mike Neuder and Francesco (fradamt) are the primary researchers, with "
          "contributions examining the interaction between inclusion lists, PBS, and "
          "the fork-choice rule. EIP-7805 (FOCIL) is a leading candidate for "
          "Glamsterdam, making this an active research-to-deployment pipeline.")

    elif thread_id == "based_preconf":
        w("Based sequencing and preconfirmations represent a frontier research area "
          "that gained traction in 2023–2024. \"Based rollups\" are rollups that use "
          "L1 proposers as their sequencer, inheriting L1's liveness and censorship "
          "resistance guarantees. Preconfirmations extend this with fast commitments "
          "from proposers about future block contents.")
        w("")
        w("Justin Drake is the primary architect of this research direction, which "
          "connects to PBS (proposers making commitments) and the broader question "
          "of Ethereum's role as a settlement layer. No EIPs have shipped yet, "
          "but the area is actively explored for future forks.")

    elif thread_id == "zk_proofs":
        w("Zero-knowledge proof research on ethresear.ch spans the theoretical "
          "foundations (PLONK, STARKs, recursive proofs) and practical applications "
          "(zk-rollups, private transactions, proof-of-identity). Barry WhiteHat was "
          "an early champion, with posts on Semaphore, MACI, and various mixer designs.")
        w("")
        w("The thread connects to multiple deployment paths: zk-rollups as L2 scaling "
          "(zkSync, Scroll, Polygon zkEVM), BLS12-381 precompiles (EIP-2537, shipped in "
          "Pectra), and the long-term vision of ZK-proving the entire EVM state transition "
          "to enable fully trustless light clients.")

    elif thread_id == "state_execution":
        w("State and execution layer research addresses Ethereum's growing state size "
          "and the viability of stateless execution. The thread covers Verkle trees "
          "(EIP-6800, targeted for Glamsterdam), state expiry mechanisms, history "
          "expiry, and portal networks for distributed state access.")
        w("")
        w("This thread has one of the longest research-to-deployment timelines. "
          "Stateless client proposals date to 2017 (among the very first ethresear.ch "
          "posts), and the Verkle transition has been discussed since 2020. The "
          "execution layer's conservative upgrade approach means state structure "
          "changes require extensive testing and coordination across all clients.")

    elif thread_id == "privacy_identity":
        w("The privacy thread covers both technical mechanisms (mixers, ring "
          "signatures, stealth addresses) and identity systems (MACI for anti-collusion "
          "voting, zk-passport for citizenship proofs). Barry WhiteHat and the "
          "Applied ZK team were early contributors.")
        w("")
        w("While privacy features haven't shipped as core protocol changes, the "
          "research influenced application-layer tools (Tornado Cash, Semaphore) "
          "and the growing interest in account abstraction (EIP-7702) as a pathway "
          "to better privacy at the wallet level.")

    else:
        # Generic fallback
        if top_topics:
            w(f"This thread spans {thread['topic_count']} topics from "
              f"{thread['date_range'][0][:4] if thread['date_range'][0] else '?'} to "
              f"{thread['date_range'][1][:4] if thread['date_range'][1] else '?'}.")


# ---------------------------------------------------------------------------
# Era narratives
# ---------------------------------------------------------------------------
def _write_era_narrative(w, era_id, era_topics, all_topics, topic_link):
    """Write a narrative paragraph for each era."""

    if era_id == "genesis":
        w("Ethresear.ch launched in September 2017, just weeks before the Byzantium fork "
          "brought BN256 precompiles and REVERT to mainnet. The earliest posts read like "
          "a brain dump of everything the research team had been thinking about: Casper "
          "FFG fundamentals, early sharding designs, and the first sketches of stateless "
          "client architectures. The community was small and the discourse was dense — "
          "nearly every post was a technical proposal by a core researcher.")
        w("")
        w("Notably, many ideas from this era took years to mature. The proposer/builder "
          "separation concept (implicit in early collation proposals), data availability "
          "challenges (raised in the context of sharding), and validator economics "
          "(Casper deposit mechanics) all planted seeds that would grow into major "
          "research threads over the next decade.")

    elif era_id == "scaling_wars":
        w("2018 was ethresear.ch's most prolific year by topic count, driven by the urgent "
          "question: how does Ethereum scale? The Scaling Wars played out across two fronts. "
          "On-chain, sharding proposals grew increasingly sophisticated — quadratic sharding "
          "gave way to super-quadratic designs, cross-shard communication protocols "
          "multiplied, and the first data availability schemes appeared.")
        w("")
        w("Off-chain, Plasma variants proliferated: Minimal Viable Plasma, Plasma Cash, "
          "Plasma Debit, Plasma Snapp. VDF research (verifiable delay functions) aimed "
          "to solve randomness for validator selection. The Casper FFG vs CBC debate "
          "continued, with the community gradually converging on FFG as the practical path.")
        w("")
        w("In retrospect, this era's most lasting contribution was the data availability "
          "problem formulation. The recognition that data availability — not execution — "
          "was the bottleneck for scaling would reshape the entire roadmap by 2020.")

    elif era_id == "eth2_design":
        w("The Eth2 Design era (2019–2020) saw the research community transition from "
          "exploration to specification. The beacon chain spec (Phase 0) was finalized "
          "and launched in December 2020, marking the first time ethresear.ch research "
          "shipped as production code. Phase 1 (data sharding) spec work continued, "
          "though it would later be superseded by Danksharding.")
        w("")
        w("Two pivotal shifts happened in this era. First, the rollup-centric roadmap "
          "emerged: Vitalik's October 2020 analysis of \"eth2 as data availability engine\" "
          "signaled that execution sharding was being deprioritized in favor of rollups "
          "as the primary scaling mechanism. Second, MEV awareness grew as Flashbots "
          "documented the scale of miner extractable value, setting the stage for the "
          "PBS research thread.")

    elif era_id == "post_merge_build":
        w("The 2021–2022 era was bookended by two landmark deployments: EIP-1559 in "
          "London (August 2021) and the Merge itself (September 2022). Research during "
          "this period focused on making these transitions safe while laying groundwork "
          "for the next phase.")
        w("")
        w("PBS emerged as a major research thread, driven by the MEV crisis. The "
          "proposer/builder separation went from theoretical concept to externalized "
          "implementation (MEV-Boost) to active enshrined design (ePBS). Fee market "
          "research continued with analysis of EIP-1559's behavior in practice and "
          "early multidimensional gas proposals. The withdrawal mechanism (EIP-4895) "
          "was designed for Shapella, completing the Merge's economic loop.")

    elif era_id == "endgame":
        w("The Endgame Architecture era (2023–2026) is defined by protocol maturity. "
          "With the Merge complete and blobs live (Dencun, March 2024), research shifted "
          "to the \"endgame\" questions: what does Ethereum look like at steady state?")
        w("")
        w("This era produced the highest topic count, driven by multiple concurrent "
          "research frontiers. Staking economics received rigorous treatment "
          "(minimum viable issuance, staking ratio targeting). PBS evolved toward "
          "ePBS with detailed mechanism design for payload timeliness committees. "
          "Inclusion lists and censorship resistance moved from theoretical to "
          "concrete (FOCIL, EIP-7805). SSF proposals matured with Orbit SSF. "
          "Based rollups and preconfirmations opened a new design space for L1/L2 "
          "integration.")
        w("")
        w("Pectra (May 2025) shipped MaxEB (EIP-7251) and in-protocol deposits "
          "(EIP-6110), directly influenced by staking economics research. "
          "Fusaka (December 2025) delivered PeerDAS (EIP-7594), the first "
          "data availability sampling deployment. Glamsterdam, still unscheduled, "
          "targets ePBS (EIP-7732) and FOCIL (EIP-7805) — ideas that have been "
          "on ethresear.ch for years.")


if __name__ == "__main__":
    main()
