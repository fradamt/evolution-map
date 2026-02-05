#!/usr/bin/env python3
"""Process ethresear.ch scraped data + protocol history → analysis.json.

Reads 2,903 topics from ../index.json and ../topics/, cross-references with
ethereum-knowledge/fork-history.md, and produces a structured JSON suitable
for both HTML visualization and Markdown narrative generation.

Usage:
    python3 analyze.py
"""

import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SCRAPE_DIR = SCRIPT_DIR.parent
TOPICS_DIR = SCRAPE_DIR / "topics"
INDEX_PATH = SCRAPE_DIR / "index.json"
CATEGORIES_PATH = SCRAPE_DIR / "categories.json"
FORK_HISTORY_PATH = SCRAPE_DIR.parent / "ethereum-knowledge" / "fork-history.md"
OUTPUT_PATH = SCRIPT_DIR / "analysis.json"

# ---------------------------------------------------------------------------
# Fork timeline (parsed from fork-history.md, with manual fallback)
# ---------------------------------------------------------------------------
FORKS_MANUAL = [
    {"name": "Byzantium", "date": "2017-10-16", "el": "Byzantium", "cl": None,
     "combined": None, "eips": [100, 140, 196, 197, 198, 211, 214, 649, 658], "meta_eip": 609},
    {"name": "Constantinople", "date": "2019-02-28", "el": "Constantinople", "cl": None,
     "combined": None, "eips": [145, 1014, 1052, 1234, 1283], "meta_eip": 1013},
    {"name": "Istanbul", "date": "2019-12-08", "el": "Istanbul", "cl": None,
     "combined": None, "eips": [152, 1108, 1344, 1884, 2028, 2200], "meta_eip": 1679},
    {"name": "Berlin", "date": "2021-04-15", "el": "Berlin", "cl": None,
     "combined": None, "eips": [2565, 2929, 2718, 2930], "meta_eip": None},
    {"name": "London", "date": "2021-08-05", "el": "London", "cl": None,
     "combined": None, "eips": [1559, 3198, 3529, 3541, 3554], "meta_eip": None},
    {"name": "Phase 0", "date": "2020-12-01", "el": None, "cl": "Phase 0",
     "combined": None, "eips": [], "meta_eip": None},
    {"name": "Altair", "date": "2021-10-27", "el": None, "cl": "Altair",
     "combined": None, "eips": [], "meta_eip": None},
    {"name": "The Merge", "date": "2022-09-15", "el": "Paris", "cl": "Bellatrix",
     "combined": "The Merge", "eips": [3675, 4399], "meta_eip": None},
    {"name": "Shapella", "date": "2023-04-12", "el": "Shanghai", "cl": "Capella",
     "combined": "Shapella", "eips": [3651, 3855, 3860, 4895, 6049], "meta_eip": None},
    {"name": "Dencun", "date": "2024-03-13", "el": "Cancun", "cl": "Deneb",
     "combined": "Dencun", "eips": [1153, 4788, 4844, 5656, 6780, 7044, 7045, 7514, 7516], "meta_eip": 7569},
    {"name": "Pectra", "date": "2025-05-07", "el": "Prague", "cl": "Electra",
     "combined": "Pectra", "eips": [2537, 2935, 6110, 7002, 7251, 7549, 7623, 7685, 7691, 7702], "meta_eip": 7600},
    {"name": "Fusaka", "date": "2025-12-03", "el": "Osaka", "cl": "Fulu",
     "combined": "Fusaka", "eips": [7594, 7823, 7825, 7883, 7917, 7918, 7934, 7939, 7951], "meta_eip": 7607},
    {"name": "Glamsterdam", "date": None, "el": "Amsterdam", "cl": "Gloas",
     "combined": "Glamsterdam", "eips": [7732, 7928], "meta_eip": 7773},
]

# Build EIP → fork lookup
EIP_TO_FORK = {}
for f in FORKS_MANUAL:
    for eip in f["eips"]:
        EIP_TO_FORK[eip] = f["name"]

# All known fork EIPs for quick membership test
ALL_FORK_EIPS = set(EIP_TO_FORK.keys())

# ---------------------------------------------------------------------------
# Era definitions
# ---------------------------------------------------------------------------
ERAS = [
    {"id": "genesis", "name": "Genesis", "start": "2017-09-01", "end": "2017-12-31",
     "character": "Casper basics, stateless clients, early sharding ideas",
     "forks": ["Byzantium"]},
    {"id": "scaling_wars", "name": "Scaling Wars", "start": "2018-01-01", "end": "2018-12-31",
     "character": "Plasma, sharding execution, VDFs, Casper FFG/CBC debates",
     "forks": ["Constantinople"]},
    {"id": "eth2_design", "name": "Eth2 Design", "start": "2019-01-01", "end": "2020-12-31",
     "character": "Phase 0/1 specs, rollup emergence, beacon chain launch",
     "forks": ["Istanbul", "Phase 0"]},
    {"id": "post_merge_build", "name": "Post-Merge Build", "start": "2021-01-01", "end": "2022-12-31",
     "character": "PBS, EIP-1559, PoW→PoS transition, MEV awareness",
     "forks": ["Berlin", "London", "Altair", "The Merge"]},
    {"id": "endgame", "name": "Endgame Architecture", "start": "2023-01-01", "end": "2026-12-31",
     "character": "ePBS, SSF, based rollups, blobs, PeerDAS, staking economics",
     "forks": ["Shapella", "Dencun", "Pectra", "Fusaka", "Glamsterdam"]},
]


def era_for_date(date_str):
    """Return era ID for an ISO date string."""
    for era in ERAS:
        if era["start"] <= date_str[:10] <= era["end"]:
            return era["id"]
    return "endgame"  # fallback for future dates


# ---------------------------------------------------------------------------
# Research thread seeds
# ---------------------------------------------------------------------------
THREAD_SEEDS = {
    "pbs_mev": {
        "name": "PBS, MEV & Block Production",
        "title_patterns": [
            r"proposer.builder", r"\bpbs\b", r"\bmev\b", r"block.?build",
            r"mev.?burn", r"epbs", r"enshrined.*proposer", r"builder.?separation",
            r"auction", r"block.?production", r"payload.?timeliness",
        ],
        "tag_patterns": [r"pbs", r"mev", r"builder"],
        "category_hints": [],
        "key_authors": ["vbuterin", "JustinDrake", "mikeneuder", "quintus", "barnabe"],
    },
    "sharding_da": {
        "name": "Sharding & Data Availability",
        "title_patterns": [
            r"\bshard", r"data.?availab", r"\bdas\b", r"danksharding", r"proto.?dank",
            r"blob", r"4844", r"peer.?das", r"data.?column", r"erasure.?cod",
            r"kzg", r"kate.?commitment", r"stateless.?client",
        ],
        "tag_patterns": [r"shard", r"data-availab", r"blob", r"das"],
        "category_hints": [],
        "key_authors": ["vbuterin", "JustinDrake", "dankrad"],
    },
    "plasma_l2": {
        "name": "Plasma & L2 Scaling",
        "title_patterns": [
            r"\bplasma\b", r"rollup", r"\bl2\b", r"layer.?2", r"based.?rollup",
            r"native.?rollup", r"optimistic.?roll", r"zk.?roll", r"state.?channel",
            r"pre.?confirmation", r"sequenc",
        ],
        "tag_patterns": [r"plasma", r"rollup", r"layer-2"],
        "category_hints": [],
        "key_authors": ["vbuterin", "JustinDrake", "karl"],
    },
    "pos_casper": {
        "name": "Proof-of-Stake & Casper",
        "title_patterns": [
            r"casper", r"proof.?of.?stake", r"\bpos\b", r"beacon.?chain",
            r"finality", r"fork.?choice", r"lmd.?ghost", r"ffg",
            r"cbc", r"slashing", r"attestat",
        ],
        "tag_patterns": [r"casper", r"pos", r"beacon"],
        "category_hints": [],
        "key_authors": ["vbuterin", "JustinDrake", "djrtwo"],
    },
    "ssf": {
        "name": "Single Slot Finality",
        "title_patterns": [
            r"single.?slot.?final", r"\bssf\b", r"orbit.?ssf",
            r"3sf", r"slot.?final",
        ],
        "tag_patterns": [r"ssf"],
        "category_hints": [],
        "key_authors": ["vbuterin", "fradamt"],
    },
    "issuance_economics": {
        "name": "Issuance & Staking Economics",
        "title_patterns": [
            r"issuance", r"staking.?econom", r"endgame.?stak", r"yield",
            r"minimum.?viable.?issuance", r"reward.?curve", r"staking.?ratio",
            r"max.?eb\b", r"max_effective_balance", r"validator.?economics",
            r"consolidat",
        ],
        "tag_patterns": [r"issuance", r"staking", r"economics"],
        "category_hints": [],
        "key_authors": ["barnabe", "casparschwa", "aelowsson", "anderselowsson"],
    },
    "inclusion_lists": {
        "name": "Inclusion Lists & Censorship Resistance",
        "title_patterns": [
            r"inclusion.?list", r"\bfocil\b", r"censorship.?resist",
            r"unconditional.?inclusion", r"crlist", r"force.?inclus",
        ],
        "tag_patterns": [r"inclusion-list", r"censorship"],
        "category_hints": [],
        "key_authors": ["mikeneuder", "fradamt", "vbuterin"],
    },
    "based_preconf": {
        "name": "Based Sequencing & Preconfirmations",
        "title_patterns": [
            r"based.?sequenc", r"pre.?confirm", r"preconf",
            r"based.?rollup", r"proposer.?commit",
        ],
        "tag_patterns": [r"preconf", r"based"],
        "category_hints": [],
        "key_authors": ["JustinDrake"],
    },
    "zk_proofs": {
        "name": "ZK Proofs & SNARKs/STARKs",
        "title_patterns": [
            r"\bzk\b", r"snark", r"stark", r"plonk", r"zero.?knowledge",
            r"zkp", r"groth16", r"proof.?system", r"verifiable.?comput",
            r"recursive.?proof",
        ],
        "tag_patterns": [r"zk", r"snark", r"stark"],
        "category_hints": [],
        "key_authors": ["barryWhiteHat"],
    },
    "fee_markets": {
        "name": "Fee Markets & EIP-1559",
        "title_patterns": [
            r"1559", r"fee.?market", r"base.?fee", r"gas.?price",
            r"multidimensional", r"resource.?pric", r"eip.?4844.*fee",
            r"blob.?fee", r"gas.?limit",
        ],
        "tag_patterns": [r"1559", r"fee-market", r"gas"],
        "category_hints": [],
        "key_authors": ["vbuterin", "barnabe"],
    },
    "privacy_identity": {
        "name": "Privacy & Identity",
        "title_patterns": [
            r"privacy", r"\bmaci\b", r"mixer", r"anonymous", r"stealth.?addr",
            r"tornado", r"ring.?sig", r"zk.?passport", r"identity",
            r"semaphore",
        ],
        "tag_patterns": [r"privacy", r"identity"],
        "category_hints": [],
        "key_authors": ["barryWhiteHat"],
    },
    "state_execution": {
        "name": "State & Execution Layer",
        "title_patterns": [
            r"verkle", r"stateless", r"state.?expir", r"state.?growth",
            r"state.?size", r"trie", r"witness", r"binary.?trie",
            r"portal.?network", r"history.?expir", r"purge",
            r"evm.*improv", r"eof\b",
        ],
        "tag_patterns": [r"verkle", r"stateless", r"state"],
        "category_hints": [],
        "key_authors": ["vbuterin", "Nero_eth", "gballet"],
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EIP_RE = re.compile(r"EIP[- ]?(\d{1,5})", re.IGNORECASE)
ETHRESEAR_URL_RE = re.compile(r"https?://ethresear\.ch/t/[^/]+/(\d+)")


def parse_date(iso_str):
    """Parse ISO timestamp to YYYY-MM-DD."""
    if not iso_str:
        return None
    return iso_str[:10]


def normalize(values):
    """Min-max normalize a list of values to [0, 1]."""
    if not values:
        return []
    mn, mx = min(values), max(values)
    rng = mx - mn
    if rng == 0:
        return [0.5] * len(values)
    return [(v - mn) / rng for v in values]


def extract_eips_from_text(text):
    """Extract EIP numbers from text."""
    return list(set(int(m) for m in EIP_RE.findall(text)))


def extract_internal_links(posts):
    """Extract target topic IDs from internal links in posts."""
    targets = set()
    for post in posts:
        for link in post.get("link_counts", []):
            if link.get("internal") and not link.get("reflection"):
                m = ETHRESEAR_URL_RE.search(link["url"])
                if m:
                    targets.add(int(m.group(1)))
    return targets


def extract_reflection_links(posts):
    """Extract topic IDs that link TO this topic (reflection links)."""
    targets = set()
    for post in posts:
        for link in post.get("link_counts", []):
            if link.get("internal") and link.get("reflection"):
                m = ETHRESEAR_URL_RE.search(link["url"])
                if m:
                    targets.add(int(m.group(1)))
    return targets


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------
def main():
    print("Loading index...")
    with open(INDEX_PATH) as f:
        index = json.load(f)
    print(f"  {len(index)} topics in index")

    # Load categories
    with open(CATEGORIES_PATH) as f:
        cat_data = json.load(f)
    categories = {}
    for cat in cat_data.get("category_list", {}).get("categories", []):
        categories[cat["id"]] = cat["name"]

    # -----------------------------------------------------------------------
    # Pass 1: Load all topics, extract metadata and links
    # -----------------------------------------------------------------------
    print("Loading topic files (pass 1)...")
    topics = {}
    all_internal_links = {}  # topic_id -> set of target topic_ids
    all_reflection_links = {}  # topic_id -> set of source topic_ids
    load_errors = 0

    for tid_str, meta in index.items():
        tid = int(tid_str)
        topic_path = TOPICS_DIR / f"{tid}.json"
        if not topic_path.exists():
            load_errors += 1
            continue

        try:
            with open(topic_path) as f:
                topic_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            load_errors += 1
            continue

        posts = topic_data.get("post_stream", {}).get("posts", [])
        created_by = topic_data.get("details", {}).get("created_by", {})
        author = created_by.get("username", "unknown")
        participants = topic_data.get("details", {}).get("participants", [])

        # Extract EIP mentions with provenance tracking
        # Title EIPs = strong signal the topic IS about that EIP
        # OP EIPs = moderate signal if mentioned substantively
        # Reply EIPs = weak, often just citing context
        title = topic_data.get("title", meta.get("title", ""))
        title_eips = set(extract_eips_from_text(title))
        op_eips = set()
        op_eip_counts = Counter()  # how many times each EIP appears in OP
        all_eip_mentions = set(title_eips)
        first_post_excerpt = ""
        for post in posts:
            cooked = post.get("cooked", "")
            post_eips = extract_eips_from_text(cooked)
            all_eip_mentions.update(post_eips)
            if post.get("post_number") == 1:
                op_eips.update(post_eips)
                for e in EIP_RE.findall(cooked):
                    op_eip_counts[int(e)] += 1
                if cooked:
                    text = re.sub(r"<[^>]+>", " ", cooked)
                    text = re.sub(r"\s+", " ", text).strip()
                    first_post_excerpt = text[:500]

        # Primary EIPs: what this topic is actually ABOUT
        # - Title EIPs: always primary (strongest signal)
        # - OP EIPs: primary only if mentioned ≥3 times in the OP
        #   (passing references like "as defined by EIP-1559" don't count)
        primary_eips = set(title_eips)
        for eip in op_eips:
            if op_eip_counts.get(eip, 0) >= 3:
                primary_eips.add(eip)

        # Extract cross-references
        outgoing = extract_internal_links(posts)
        incoming = extract_reflection_links(posts)
        outgoing.discard(tid)  # no self-links
        incoming.discard(tid)

        all_internal_links[tid] = outgoing
        all_reflection_links[tid] = incoming

        # Tags
        tags = topic_data.get("tags", []) or []

        topics[tid] = {
            "id": tid,
            "title": title,
            "author": author,
            "date": parse_date(meta.get("created_at")),
            "category_id": meta.get("category_id"),
            "category_name": meta.get("category_name", categories.get(meta.get("category_id"), "")),
            "tags": tags,
            "views": meta.get("views", 0),
            "like_count": meta.get("like_count", 0),
            "posts_count": meta.get("posts_count", 1),
            "word_count": topic_data.get("word_count", 0),
            "eip_mentions": sorted(all_eip_mentions),
            "primary_eips": sorted(primary_eips),
            "participants": [{"username": p["username"], "post_count": p["post_count"]}
                             for p in participants],
            "first_post_excerpt": first_post_excerpt,
        }

    if load_errors:
        print(f"  Warning: {load_errors} topic files failed to load")
    print(f"  Loaded {len(topics)} topics")

    # -----------------------------------------------------------------------
    # Build cross-reference graph (in-degree based on outgoing links)
    # -----------------------------------------------------------------------
    print("Building cross-reference graph...")
    in_degree = Counter()
    out_degree = Counter()
    edges = []

    for src, targets in all_internal_links.items():
        for tgt in targets:
            if tgt in topics:
                in_degree[tgt] += 1
                out_degree[src] += 1
                edges.append({"source": src, "target": tgt})

    # Also count reflection links as in-degree (these are links FROM other topics)
    for tid, sources in all_reflection_links.items():
        for src in sources:
            if src in topics and src not in all_internal_links.get(tid, set()):
                # Only add if not already counted via outgoing
                pass  # reflection links are the reverse perspective of outgoing links

    total_edges = len(edges)
    print(f"  {total_edges} cross-reference edges")

    # -----------------------------------------------------------------------
    # Compute influence scores
    # -----------------------------------------------------------------------
    print("Computing influence scores...")
    tids = sorted(topics.keys())

    # Prolific authors (5+ topics)
    author_topic_counts = Counter(topics[t]["author"] for t in tids)
    prolific_authors = {a for a, c in author_topic_counts.items() if c >= 5}

    raw_in = [in_degree.get(t, 0) for t in tids]
    raw_likes = [topics[t]["like_count"] for t in tids]
    raw_views = [math.log1p(topics[t]["views"]) for t in tids]
    raw_posts = [topics[t]["posts_count"] for t in tids]
    raw_prolific = [1.0 if topics[t]["author"] in prolific_authors else 0.0 for t in tids]

    norm_in = normalize(raw_in)
    norm_likes = normalize(raw_likes)
    norm_views = normalize(raw_views)
    norm_posts = normalize(raw_posts)

    for i, tid in enumerate(tids):
        score = (
            0.30 * norm_in[i]
            + 0.25 * norm_likes[i]
            + 0.20 * norm_views[i]
            + 0.15 * norm_posts[i]
            + 0.10 * raw_prolific[i]
        )
        topics[tid]["influence_score"] = round(score, 4)
        topics[tid]["in_degree"] = in_degree.get(tid, 0)
        topics[tid]["out_degree"] = out_degree.get(tid, 0)

    # -----------------------------------------------------------------------
    # Topic filtering: Tier 1 + Tier 2
    # -----------------------------------------------------------------------
    print("Filtering topics...")
    tier1 = set()
    for tid in tids:
        t = topics[tid]
        if t["influence_score"] >= 0.25 or t["in_degree"] >= 3:
            tier1.add(tid)

    # Tier 2: referenced by Tier 1 with influence >= 0.10
    tier2 = set()
    for tid in tier1:
        for tgt in all_internal_links.get(tid, set()):
            if tgt in topics and tgt not in tier1:
                if topics[tgt]["influence_score"] >= 0.10:
                    tier2.add(tgt)

    included = tier1 | tier2
    print(f"  Tier 1: {len(tier1)}, Tier 2: {len(tier2)}, Total included: {len(included)}")

    # If too few, lower threshold
    if len(included) < 400:
        print("  Adjusting thresholds to include more topics...")
        for tid in tids:
            if tid not in included and (topics[tid]["influence_score"] >= 0.15 or topics[tid]["in_degree"] >= 2):
                included.add(tid)
        print(f"  After adjustment: {len(included)}")

    # If too many, raise threshold
    if len(included) > 600:
        # Remove lowest-influence tier2 topics
        tier2_sorted = sorted(tier2, key=lambda t: topics[t]["influence_score"])
        while len(included) > 550 and tier2_sorted:
            removed = tier2_sorted.pop(0)
            included.discard(removed)
            tier2.discard(removed)
        print(f"  After trimming: {len(included)}")

    # -----------------------------------------------------------------------
    # Research thread assignment
    # -----------------------------------------------------------------------
    print("Assigning research threads...")

    def match_thread(topic, thread_def):
        """Score how well a topic matches a thread definition."""
        score = 0
        title_lower = topic["title"].lower()
        tags_lower = [t.lower() for t in topic.get("tags", [])]

        for pat in thread_def["title_patterns"]:
            if re.search(pat, title_lower):
                score += 2
                break  # one title match is enough

        for pat in thread_def["tag_patterns"]:
            for tag in tags_lower:
                if re.search(pat, tag):
                    score += 1
                    break

        if topic["author"] in thread_def["key_authors"]:
            score += 0.5

        # Check first post excerpt too
        excerpt_lower = topic.get("first_post_excerpt", "").lower()
        for pat in thread_def["title_patterns"]:
            if re.search(pat, excerpt_lower):
                score += 1
                break

        return score

    # Assign each included topic to best-matching thread
    for tid in included:
        t = topics[tid]
        best_thread = None
        best_score = 0
        for thread_id, thread_def in THREAD_SEEDS.items():
            s = match_thread(t, thread_def)
            if s > best_score:
                best_score = s
                best_thread = thread_id
        if best_score >= 1.5:
            t["research_thread"] = best_thread
        else:
            t["research_thread"] = None

    # Thread stats
    thread_counts = Counter(topics[t]["research_thread"] for t in included if topics[t].get("research_thread"))
    unassigned = sum(1 for t in included if not topics[t].get("research_thread"))
    print(f"  Thread assignments: {dict(thread_counts)}")
    print(f"  Unassigned: {unassigned}")

    # -----------------------------------------------------------------------
    # EIP → fork mapping for topics
    # -----------------------------------------------------------------------
    # NOTE: We intentionally do NOT map topics → "shipped in fork".
    # Counting EIP mentions is a poor proxy for "this research contributed
    # to that EIP." A real mapping would need semantic understanding of
    # whether the topic's core idea actually ended up in the protocol.
    # That's a future project. For now, shipped_in is always empty.
    for tid in included:
        topics[tid]["shipped_in"] = []

    # -----------------------------------------------------------------------
    # Era assignment
    # -----------------------------------------------------------------------
    for tid in included:
        t = topics[tid]
        t["era"] = era_for_date(t["date"]) if t["date"] else "endgame"

    era_counts = Counter(topics[t]["era"] for t in included)
    print(f"  Era distribution: {dict(era_counts)}")

    # -----------------------------------------------------------------------
    # Author profiles
    # -----------------------------------------------------------------------
    print("Building author profiles...")
    author_data = defaultdict(lambda: {
        "topics_created": 0, "total_posts": 0, "total_likes": 0,
        "total_in_degree": 0, "years": set(), "categories": Counter(),
        "topic_ids": [], "threads": Counter(),
    })

    for tid in included:
        t = topics[tid]
        a = author_data[t["author"]]
        a["topics_created"] += 1
        a["total_likes"] += t["like_count"]
        a["total_in_degree"] += t["in_degree"]
        a["topic_ids"].append(tid)
        if t["date"]:
            a["years"].add(int(t["date"][:4]))
        if t["category_name"]:
            a["categories"][t["category_name"]] += 1
        if t.get("research_thread"):
            a["threads"][t["research_thread"]] += 1

    # Also count posts from participants
    for tid in included:
        t = topics[tid]
        for p in t["participants"]:
            author_data[p["username"]]["total_posts"] += p["post_count"]

    # Compute author influence and select top authors
    author_scores = {}
    for username, data in author_data.items():
        if data["topics_created"] < 2:
            continue
        score = (
            data["topics_created"] * 2
            + data["total_likes"] * 0.5
            + data["total_in_degree"] * 3
        )
        author_scores[username] = score

    top_authors = sorted(author_scores.keys(), key=lambda u: author_scores[u], reverse=True)[:40]

    authors_output = {}
    for username in top_authors:
        data = author_data[username]
        top_topics = sorted(data["topic_ids"], key=lambda t: topics[t]["influence_score"], reverse=True)[:10]
        years = sorted(data["years"]) if data["years"] else []

        # Co-researchers: authors who participate in the same topics
        co_researchers = Counter()
        for tid in data["topic_ids"]:
            for p in topics[tid]["participants"]:
                if p["username"] != username:
                    co_researchers[p["username"]] += 1

        authors_output[username] = {
            "username": username,
            "topics_created": data["topics_created"],
            "total_posts": data["total_posts"],
            "total_likes": data["total_likes"],
            "total_in_degree": data["total_in_degree"],
            "influence_score": round(author_scores[username], 1),
            "active_years": years,
            "category_focus": dict(data["categories"].most_common(5)),
            "thread_focus": dict(data["threads"].most_common(3)),
            "top_topics": top_topics,
            "co_researchers": dict(co_researchers.most_common(10)),
        }

    print(f"  {len(authors_output)} author profiles")

    # -----------------------------------------------------------------------
    # Research thread summaries
    # -----------------------------------------------------------------------
    print("Building research thread summaries...")
    threads_output = {}
    for thread_id, thread_def in THREAD_SEEDS.items():
        thread_topics = [tid for tid in included if topics[tid].get("research_thread") == thread_id]
        if not thread_topics:
            continue

        dates = [topics[t]["date"] for t in thread_topics if topics[t]["date"]]
        dates.sort()

        # Key authors for this thread
        thread_authors = Counter()
        for tid in thread_topics:
            thread_authors[topics[tid]["author"]] += 1
            for p in topics[tid]["participants"]:
                thread_authors[p["username"]] += 0.5

        # EIPs mentioned across the thread (for reference, not "shipped" claims)
        thread_eips = set()
        for tid in thread_topics:
            thread_eips.update(topics[tid]["primary_eips"])

        # Sort topics by influence
        thread_topics_sorted = sorted(thread_topics, key=lambda t: topics[t]["influence_score"], reverse=True)

        threads_output[thread_id] = {
            "id": thread_id,
            "name": thread_def["name"],
            "topic_count": len(thread_topics),
            "topic_ids": thread_topics_sorted,
            "date_range": [dates[0] if dates else None, dates[-1] if dates else None],
            "key_authors": dict(Counter({a: int(c) for a, c in thread_authors.most_common(10)}).most_common(10)),
            "eip_mentions": sorted(thread_eips),
            "top_topics": thread_topics_sorted[:15],
        }

    print(f"  {len(threads_output)} threads with topics")

    # -----------------------------------------------------------------------
    # Fork → topic cross-references
    # -----------------------------------------------------------------------
    print("Building fork-topic cross-references...")
    forks_output = []
    for fork in FORKS_MANUAL:
        # Find topics that mention any of this fork's EIPs as primary
        fork_eip_set = set(fork["eips"])
        related_topics = []
        for tid in included:
            topic_primary = set(topics[tid].get("primary_eips", []))
            if topic_primary & fork_eip_set:
                related_topics.append(tid)
        related_topics.sort(key=lambda t: topics[t]["influence_score"], reverse=True)

        forks_output.append({
            "name": fork["name"],
            "date": fork["date"],
            "el_name": fork["el"],
            "cl_name": fork["cl"],
            "combined_name": fork["combined"],
            "eips": fork["eips"],
            "meta_eip": fork["meta_eip"],
            "related_topics": related_topics[:20],
        })

    # -----------------------------------------------------------------------
    # Graph data for visualization (only included topics)
    # -----------------------------------------------------------------------
    print("Building graph data...")
    graph_nodes = []
    for tid in included:
        t = topics[tid]
        graph_nodes.append({
            "id": tid,
            "title": t["title"],
            "author": t["author"],
            "date": t["date"],
            "influence": t["influence_score"],
            "thread": t.get("research_thread"),
            "era": t.get("era"),
            "primary_eips": t.get("primary_eips", []),
        })

    graph_edges = [e for e in edges if e["source"] in included and e["target"] in included]
    print(f"  {len(graph_nodes)} nodes, {len(graph_edges)} edges")

    # -----------------------------------------------------------------------
    # Co-author graph
    # -----------------------------------------------------------------------
    print("Building co-author graph...")
    coauthor_edges = defaultdict(int)
    for tid in included:
        participants = [p["username"] for p in topics[tid]["participants"]]
        for i, a in enumerate(participants):
            for b in participants[i + 1:]:
                pair = tuple(sorted([a, b]))
                coauthor_edges[pair] += 1

    coauthor_nodes = []
    for username in top_authors:
        coauthor_nodes.append({
            "id": username,
            "topics": authors_output[username]["topics_created"],
            "influence": authors_output[username]["influence_score"],
        })

    top_author_set = set(top_authors)
    coauthor_edge_list = []
    for (a, b), weight in coauthor_edges.items():
        if a in top_author_set and b in top_author_set and weight >= 2:
            coauthor_edge_list.append({"source": a, "target": b, "weight": weight})

    print(f"  {len(coauthor_nodes)} author nodes, {len(coauthor_edge_list)} edges")

    # -----------------------------------------------------------------------
    # Build included topics output (only included ones, slimmed down)
    # -----------------------------------------------------------------------
    topics_output = {}
    for tid in included:
        t = topics[tid]
        topics_output[str(tid)] = {
            "id": tid,
            "title": t["title"],
            "author": t["author"],
            "date": t["date"],
            "category_name": t["category_name"],
            "tags": t["tags"],
            "views": t["views"],
            "like_count": t["like_count"],
            "posts_count": t["posts_count"],
            "influence_score": t["influence_score"],
            "in_degree": t["in_degree"],
            "out_degree": t["out_degree"],
            "research_thread": t.get("research_thread"),
            "era": t.get("era"),
            "eip_mentions": t["eip_mentions"],
            "primary_eips": t["primary_eips"],
            "shipped_in": t.get("shipped_in", []),
            "first_post_excerpt": t.get("first_post_excerpt", "")[:300],
            "participants": t["participants"][:5],
            "outgoing_refs": sorted(all_internal_links.get(tid, set()) & included),
            "incoming_refs": [e["source"] for e in graph_edges if e["target"] == tid],
        }

    # -----------------------------------------------------------------------
    # Assemble output
    # -----------------------------------------------------------------------
    print("Writing analysis.json...")
    output = {
        "metadata": {
            "total_topics": len(index),
            "included": len(included),
            "total_edges": total_edges,
            "included_edges": len(graph_edges),
            "generated_at": datetime.now().isoformat()[:19],
        },
        "eras": ERAS,
        "forks": forks_output,
        "topics": topics_output,
        "authors": authors_output,
        "research_threads": threads_output,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
        "co_author_graph": {
            "nodes": coauthor_nodes,
            "edges": coauthor_edge_list,
        },
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Done! {OUTPUT_PATH} ({size_mb:.1f} MB)")
    print(f"  {len(included)} topics, {len(graph_edges)} edges, "
          f"{len(authors_output)} authors, {len(threads_output)} threads")

    # Quick validation
    print("\n--- Validation ---")
    for thread_id, thread in sorted(threads_output.items(), key=lambda x: x[1]["topic_count"], reverse=True):
        print(f"  {thread['name']}: {thread['topic_count']} topics, "
              f"EIPs mentioned: {thread['eip_mentions'][:5]}")

    print(f"\nTop 10 authors:")
    for username in top_authors[:10]:
        a = authors_output[username]
        print(f"  {username}: {a['topics_created']} topics, "
              f"influence={a['influence_score']:.0f}, years={a['active_years'][0]}-{a['active_years'][-1]}")


if __name__ == "__main__":
    main()
