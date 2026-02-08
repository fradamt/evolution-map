#!/usr/bin/env python3
"""Render analysis.json -> evolution-map.html (interactive visualization).

Generates a single self-contained HTML file with D3.js v7 (from CDN).
Five panels: Timeline Swim Lanes, Citation Network, Co-Author Network,
Author Sidebar, Detail Panel.

Usage:
    python3 render_html.py
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_PATH = SCRIPT_DIR / "analysis.json"
OUTPUT_PATH = SCRIPT_DIR / "evolution-map.html"
PAPERS_DB_PATH = SCRIPT_DIR / "papers-db.json"

# Thread display order and colors
THREAD_COLORS = {
    "pos_casper": "#e63946",
    "sharding_da": "#457b9d",
    "plasma_l2": "#2a9d8f",
    "fee_markets": "#e9c46a",
    "pbs_mev": "#f4a261",
    "ssf": "#d62828",
    "issuance_economics": "#6a994e",
    "inclusion_lists": "#bc6c25",
    "based_preconf": "#7209b7",
    "zk_proofs": "#4361ee",
    "state_execution": "#606c38",
    "privacy_identity": "#9d4edd",
}

THREAD_ORDER = [
    "pos_casper", "sharding_da", "plasma_l2", "fee_markets",
    "pbs_mev", "ssf", "issuance_economics", "inclusion_lists",
    "based_preconf", "zk_proofs", "state_execution", "privacy_identity",
]

# Top author colors (up to 15, rest gray)
AUTHOR_COLORS = [
    "#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261",
    "#d62828", "#6a994e", "#bc6c25", "#7209b7", "#4361ee",
    "#606c38", "#9d4edd", "#264653", "#a8dadc", "#b5838d",
]

# High-confidence manual links between EIP metadata names and ethresear.ch usernames.
# Auto-linking handles most first-initial+surname style usernames; these cover common
# aliases where normalization is not enough (eg, "fradamt" vs "Francesco D'Amato").
EIP_TO_ETH_AUTHOR_OVERRIDES = {
    "Vitalik Buterin": ["vbuterin"],
    "Justin Drake": ["JustinDrake"],
    "Ansgar Dietrichs": ["adietrichs"],
    "Anders Elowsson": ["aelowsson"],
    "Dankrad Feist": ["dankrad"],
    "Francesco D'Amato": ["fradamt"],
    "Danny Ryan": ["djrtwo"],
    "Toni Wahrstätter": ["Nero_eth"],
    "Carl Beekhuizen": ["CarlBeek"],
    "Michael Neuder": ["mikeneuder"],
    "Mike Neuder": ["mikeneuder"],
    "Mike": ["mikeneuder"],
    "mike": ["mikeneuder"],
}

# Manual aliases for Magicians handles that should map to ethresear.ch usernames.
MAG_TO_ETH_AUTHOR_OVERRIDES = {
    "vbuterin_old": ["vbuterin"],
    "Nerolation": ["Nero_eth"],
}

# Manual aliases for Magicians handles that should map directly to EIP author names.
MAG_TO_EIP_AUTHOR_OVERRIDES = {
    "vbuterin": ["Vitalik Buterin"],
    "JustinDrake": ["Justin Drake"],
    "CarlBeek": ["Carl Beekhuizen"],
    "Nerolation": ["Toni Wahrstätter"],
    "djrtwo": ["Danny Ryan"],
}

PAPER_EIP_RE = re.compile(r"\beip[\s-]?(\d{1,5})\b", re.IGNORECASE)


def _extract_eip_refs_from_texts(texts):
    refs = set()
    for text in texts:
        if not text:
            continue
        for match in PAPER_EIP_RE.findall(str(text)):
            try:
                num = int(match)
            except (TypeError, ValueError):
                continue
            if num > 0:
                refs.add(num)
    return sorted(refs)


def _load_papers_for_viz(data):
    """Load paper corpus for website rendering, preferring papers-db.json."""
    def clean_opt(value):
        if value is None:
            return None
        s = str(value).strip()
        if not s or s.lower() in {"none", "null", "nan"}:
            return None
        return s

    source = "analysis"
    rows = []
    if PAPERS_DB_PATH.exists():
        try:
            with open(PAPERS_DB_PATH) as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                rows = payload.get("papers", []) or []
            elif isinstance(payload, list):
                rows = payload
            source = "papers-db"
        except Exception:  # noqa: BLE001
            rows = []

    if not rows:
        analysis_papers = data.get("papers", {})
        if isinstance(analysis_papers, dict):
            rows = list(analysis_papers.values())
        elif isinstance(analysis_papers, list):
            rows = analysis_papers
        source = "analysis"

    compact = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("id", "")).strip()
        title = str(row.get("title", "")).strip()
        if not pid or not title:
            continue

        authors = []
        for a in row.get("authors", []) or []:
            s = str(a).strip()
            if s:
                authors.append(s)

        tags = []
        for t in row.get("tags", []) or []:
            s = str(t).strip().lower()
            if s and s not in tags:
                tags.append(s)

        matched_queries = [str(q).strip() for q in (row.get("matched_queries", []) or []) if str(q).strip()]
        eip_refs = _extract_eip_refs_from_texts([title] + matched_queries)

        year = row.get("year")
        try:
            year = int(year) if year is not None else None
        except (TypeError, ValueError):
            year = None

        cited_by = row.get("cited_by_count")
        try:
            cited_by = int(cited_by) if cited_by is not None else 0
        except (TypeError, ValueError):
            cited_by = 0

        relevance = row.get("relevance_score")
        try:
            relevance = float(relevance) if relevance is not None else 0.0
        except (TypeError, ValueError):
            relevance = 0.0

        url = clean_opt(row.get("url"))
        doi = clean_opt(row.get("doi"))
        if not url and doi:
            url = "https://doi.org/" + doi

        compact[pid] = {
            "id": pid,
            "t": title,
            "y": year,
            "a": authors[:12],
            "v": clean_opt(row.get("venue")),
            "u": url,
            "doi": doi,
            "ax": clean_opt(row.get("arxiv_id")) or clean_opt(row.get("eprint_id")),
            "cb": cited_by,
            "rs": round(relevance, 3),
            "tg": tags[:12],
            "eq": eip_refs,
        }

    return compact, source


def _norm_alnum(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _norm_alpha(value):
    return re.sub(r"[^a-z]", "", (value or "").lower())


def _collect_ethresearch_usernames(data):
    usernames = set(data.get("authors", {}).keys())
    for source in ("topics", "minor_topics"):
        for topic in data.get(source, {}).values():
            author = topic.get("author")
            if author:
                usernames.add(author)
            usernames.update(topic.get("coauthors", []))
            usernames.update(topic.get("authors", []))
    # Ignore trivial usernames that create noisy false positives in heuristic matching.
    return sorted(u for u in usernames if len(_norm_alnum(u)) >= 4)


def _collect_magicians_usernames(data):
    usernames = set()
    for topic in data.get("magicians_topics", {}).values():
        author = (topic.get("author") or "").strip()
        if author:
            usernames.add(author)
    return sorted(u for u in usernames if len(_norm_alnum(u)) >= 3)


def _score_handle_to_handle_match(source_handle, target_handle):
    src = _norm_alnum(source_handle)
    tgt = _norm_alnum(target_handle)
    if not src or not tgt:
        return 0
    if src == tgt:
        return 320
    # Allow tiny affixes around an otherwise exact handle match.
    if src in tgt and len(tgt) - len(src) <= 2:
        return 250
    if tgt in src and len(src) - len(tgt) <= 2:
        return 250
    return 0


def _score_eip_name_to_mag_handle(eip_name, mag_handle):
    """Scoring for matching a full EIP author name to a Magicians handle."""
    handle = _norm_alnum(mag_handle)
    if not handle:
        return 0

    full = _norm_alnum(eip_name)
    parts = [_norm_alpha(p) for p in str(eip_name).split() if _norm_alpha(p)]
    first = parts[0] if parts else ""
    last = parts[-1] if parts else ""
    first_last = (first + last) if first and last else ""

    score = 0
    if handle == full:
        score += 320
    if first_last:
        if handle == first_last:
            score += 300
        if handle == first[0] + last:
            score += 280
        if handle.startswith(first[0] + last):
            score += 260
        if first_last in handle and len(handle) - len(first_last) <= 2:
            score += 250
        if len(last) >= 4 and last in handle:
            score += 90
        if len(first) >= 3 and first in handle:
            score += 30
    if handle in full and len(full) - len(handle) <= 2:
        score += 180
    return score


def _score_eip_to_eth_match(eip_name, username):
    """Return a confidence score for matching an EIP full name to a username."""
    user_norm = _norm_alnum(username)
    name_norm = _norm_alnum(eip_name)
    if not user_norm:
        return 0

    parts = [_norm_alpha(p) for p in str(eip_name).split() if _norm_alpha(p)]
    first = parts[0] if parts else ""
    last = parts[-1] if parts else ""

    score = 0
    if user_norm == name_norm:
        score += 300
    if first and user_norm == first and len(first) >= 6:
        score += 230
    if first and last:
        if user_norm == first + last:
            score += 280
        if user_norm == first[0] + last:
            score += 260
        if user_norm.startswith(first[0] + last):
            score += 240
        if len(first) >= 2 and user_norm.startswith(first[:2] + last):
            score += 220
        if len(first) >= 3 and user_norm.startswith(first[:3] + last):
            score += 200
        if len(last) >= 5 and len(user_norm) > 3 and user_norm.startswith(first[:2]) and last.startswith(user_norm[2:]):
            score += 175
        if len(last) >= 5 and len(user_norm) > 2 and user_norm.startswith(first[0]) and last.startswith(user_norm[1:]):
            score += 185
        if last in user_norm:
            score += 90
        if first in user_norm:
            score += 30

    if user_norm and user_norm in name_norm:
        score += 30
    return score


def _build_author_links(data):
    """Create bidirectional links between ethresear.ch and EIP author identities."""
    usernames = _collect_ethresearch_usernames(data)
    mag_usernames = _collect_magicians_usernames(data)
    eip_names = set(data.get("eip_authors", {}).keys())
    for e in (data.get("eip_catalog", {}) or {}).values():
        for raw_name in (e.get("authors", []) or []):
            name = str(raw_name or "").strip()
            if name:
                eip_names.add(name)
    eip_names = sorted(eip_names)

    eip_to_eth = {}
    for eip_name in eip_names:
        mapped = []
        for override in EIP_TO_ETH_AUTHOR_OVERRIDES.get(eip_name, []):
            if override and override not in mapped:
                mapped.append(override)

        scored = sorted(
            ((_score_eip_to_eth_match(eip_name, username), username) for username in usernames),
            key=lambda x: x[0],
            reverse=True,
        )
        best_score, best_user = scored[0] if scored else (0, None)
        second_score = scored[1][0] if len(scored) > 1 else 0

        # Conservative auto-linking: only when no manual override exists.
        if not mapped and best_user and best_score >= 240 and (best_score - second_score) >= 40:
            if best_user not in mapped:
                mapped.append(best_user)

        if mapped:
            eip_to_eth[eip_name] = sorted(mapped)

    eth_to_eip = {}
    for eip_name, eth_users in eip_to_eth.items():
        for username in eth_users:
            eth_to_eip.setdefault(username, []).append(eip_name)
    for username in list(eth_to_eip.keys()):
        eth_to_eip[username] = sorted(set(eth_to_eip[username]))

    mag_to_eth = {}
    for mag_user in mag_usernames:
        mapped = []
        for override in MAG_TO_ETH_AUTHOR_OVERRIDES.get(mag_user, []):
            if override and override not in mapped:
                mapped.append(override)

        scored = sorted(
            ((_score_handle_to_handle_match(mag_user, username), username) for username in usernames),
            key=lambda x: x[0],
            reverse=True,
        )
        best_score, best_user = scored[0] if scored else (0, None)
        second_score = scored[1][0] if len(scored) > 1 else 0
        if not mapped and best_user and best_score >= 300 and (best_score - second_score) >= 40:
            if best_user not in mapped:
                mapped.append(best_user)

        if mapped:
            mag_to_eth[mag_user] = sorted(set(mapped))

    eth_to_mag = {}
    for mag_user, eth_users in mag_to_eth.items():
        for username in eth_users:
            eth_to_mag.setdefault(username, []).append(mag_user)
    for username in list(eth_to_mag.keys()):
        eth_to_mag[username] = sorted(set(eth_to_mag[username]))

    mag_to_eip = {}
    for mag_user in mag_usernames:
        mapped = []

        # User-provided/manual aliasing first.
        for override in MAG_TO_EIP_AUTHOR_OVERRIDES.get(mag_user, []):
            if override in eip_names and override not in mapped:
                mapped.append(override)

        # Bridge via ethresear.ch identity links.
        for eth_user in mag_to_eth.get(mag_user, []):
            for eip_name in eth_to_eip.get(eth_user, []):
                if eip_name not in mapped:
                    mapped.append(eip_name)

        # Conservative direct matching to EIP author names.
        scored = sorted(
            ((_score_eip_name_to_mag_handle(eip_name, mag_user), eip_name) for eip_name in eip_names),
            key=lambda x: x[0],
            reverse=True,
        )
        best_score, best_name = scored[0] if scored else (0, None)
        second_score = scored[1][0] if len(scored) > 1 else 0
        if not mapped and best_name and best_score >= 240 and (best_score - second_score) >= 40:
            if best_name not in mapped:
                mapped.append(best_name)

        if mapped:
            mag_to_eip[mag_user] = sorted(set(mapped))

    eip_to_mag = {}
    for mag_user, eip_linked in mag_to_eip.items():
        for eip_name in eip_linked:
            eip_to_mag.setdefault(eip_name, []).append(mag_user)
    for eip_name in list(eip_to_mag.keys()):
        eip_to_mag[eip_name] = sorted(set(eip_to_mag[eip_name]))

    return {
        "ethToEip": eth_to_eip,
        "eipToEth": eip_to_eth,
        "magToEth": mag_to_eth,
        "ethToMag": eth_to_mag,
        "magToEip": mag_to_eip,
        "eipToMag": eip_to_mag,
    }


def _eip_author_name_quality(name):
    s = str(name or "").strip()
    if not s:
        return -1000
    norm = _norm_alpha(s)
    parts = [p for p in re.split(r"\s+", s) if p]
    score = 0
    if s in EIP_TO_ETH_AUTHOR_OVERRIDES:
        score += 280
    if len(parts) >= 2:
        score += 120
    if any(ch.isupper() for ch in s):
        score += 18
    if len(parts) == 1 and len(norm) <= 5:
        score -= 45
    if s.islower() and len(parts) == 1:
        score -= 35
    score += len(norm)
    return score


def _build_eip_author_canonical_map(eip_names, author_links):
    names = sorted({str(n or "").strip() for n in eip_names if str(n or "").strip()})
    if not names:
        return {}, {}

    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        if a not in parent or b not in parent:
            return
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for linked_names in (author_links.get("ethToEip") or {}).values():
        linked = [n for n in (linked_names or []) if n in parent]
        if len(linked) < 2:
            continue
        first = linked[0]
        for other in linked[1:]:
            union(first, other)

    for linked_names in (author_links.get("magToEip") or {}).values():
        linked = [n for n in (linked_names or []) if n in parent]
        if len(linked) < 2:
            continue
        first = linked[0]
        for other in linked[1:]:
            union(first, other)

    groups = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)

    canonical = {}
    aliases_by_canonical = {}
    for members in groups.values():
        sorted_members = sorted(
            members,
            key=lambda n: (-_eip_author_name_quality(n), -len(_norm_alpha(n)), n.lower(), n),
        )
        canon = sorted_members[0]
        member_set = sorted(set(members))
        aliases_by_canonical[canon] = [m for m in member_set if m != canon]
        for name in member_set:
            canonical[name] = canon

    return canonical, aliases_by_canonical


def _canonicalize_author_links(author_links, canonical_eip_map):
    def canonical_name(name):
        key = str(name or "").strip()
        if not key:
            return ""
        return canonical_eip_map.get(key, key)

    def uniq_sorted(values):
        return sorted({v for v in values if v})

    eth_to_eip = {}
    for username, names in (author_links.get("ethToEip") or {}).items():
        canonical_names = uniq_sorted(canonical_name(n) for n in (names or []))
        if canonical_names:
            eth_to_eip[username] = canonical_names

    eip_to_eth_sets = {}
    for name, usernames in (author_links.get("eipToEth") or {}).items():
        canonical = canonical_name(name)
        if not canonical:
            continue
        bucket = eip_to_eth_sets.setdefault(canonical, set())
        for username in (usernames or []):
            u = str(username or "").strip()
            if u:
                bucket.add(u)
    for username, names in eth_to_eip.items():
        for name in names:
            eip_to_eth_sets.setdefault(name, set()).add(username)
    eip_to_eth = {name: sorted(users) for name, users in eip_to_eth_sets.items() if users}

    mag_to_eth = {}
    for mag_user, usernames in (author_links.get("magToEth") or {}).items():
        users = uniq_sorted(str(u or "").strip() for u in (usernames or []))
        if users:
            mag_to_eth[mag_user] = users

    eth_to_mag = {}
    for username, mag_users in (author_links.get("ethToMag") or {}).items():
        mags = uniq_sorted(str(m or "").strip() for m in (mag_users or []))
        if mags:
            eth_to_mag[username] = mags

    mag_to_eip = {}
    for mag_user, names in (author_links.get("magToEip") or {}).items():
        canonical_names = uniq_sorted(canonical_name(n) for n in (names or []))
        if canonical_names:
            mag_to_eip[mag_user] = canonical_names

    eip_to_mag_sets = {}
    for name, mag_users in (author_links.get("eipToMag") or {}).items():
        canonical = canonical_name(name)
        if not canonical:
            continue
        bucket = eip_to_mag_sets.setdefault(canonical, set())
        for mag_user in (mag_users or []):
            m = str(mag_user or "").strip()
            if m:
                bucket.add(m)
    for mag_user, names in mag_to_eip.items():
        for name in names:
            eip_to_mag_sets.setdefault(name, set()).add(mag_user)
    eip_to_mag = {name: sorted(mags) for name, mags in eip_to_mag_sets.items() if mags}

    alias_to_canonical = {
        alias: canonical
        for alias, canonical in canonical_eip_map.items()
        if alias != canonical
    }

    return {
        "ethToEip": eth_to_eip,
        "eipToEth": eip_to_eth,
        "magToEth": mag_to_eth,
        "ethToMag": eth_to_mag,
        "magToEip": mag_to_eip,
        "eipToMag": eip_to_mag,
        "eipAliasToCanonical": alias_to_canonical,
    }


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_unified_node_id(node_id):
    if isinstance(node_id, int):
        return node_id
    if isinstance(node_id, str):
        if node_id.startswith(("eip_", "mag_", "fork_")):
            return node_id
        coerced = _to_int(node_id)
        if coerced is not None:
            return coerced
    return node_id


def _cross_forum_node_id(source_type, source):
    if source_type == "topic":
        return _to_int(source)
    if source_type == "eip":
        eip_num = _to_int(source)
        return f"eip_{eip_num}" if eip_num is not None else None
    if source_type == "magicians_topic":
        mtid = _to_int(source)
        return f"mag_{mtid}" if mtid is not None else None
    if source_type == "fork":
        return f"fork_{source}" if source else None
    return None


def _add_unified_edge(edges, edge_keys, source, target, edge_type):
    source = _normalize_unified_node_id(source)
    target = _normalize_unified_node_id(target)
    if source is None or target is None:
        return
    key = (str(source), str(target), str(edge_type or ""))
    if key in edge_keys:
        return
    edge_keys.add(key)
    edges.append({
        "source": source,
        "target": target,
        "type": edge_type,
    })


def _build_unified_graph(topics, graph, forks, eip_graph, magicians_topics, cross_forum_edges):
    nodes = []
    edges = []
    node_keys = set()
    edge_keys = set()

    def add_node(node):
        node_id = _normalize_unified_node_id(node.get("id"))
        if node_id is None:
            return
        key = str(node_id)
        if key in node_keys:
            return
        node_keys.add(key)
        node["id"] = node_id
        nodes.append(node)

    # Ethresear.ch topic nodes (include both primary + minor topics).
    for t in topics.values():
        node_id = _normalize_unified_node_id(t.get("id"))
        add_node({
            "id": node_id,
            "sourceType": "topic",
            "title": t.get("t"),
            "author": t.get("a"),
            "date": t.get("d"),
            "influence": t.get("inf", 0),
            "thread": t.get("th"),
            "era": t.get("era"),
            "primaryEips": t.get("peips", []),
            "isMinor": bool(t.get("mn")),
        })
    # Topic citation edges from the curated citation graph.
    for e in graph.get("edges", []):
        _add_unified_edge(
            edges,
            edge_keys,
            e.get("source"),
            e.get("target"),
            "topic_citation",
        )

    # Fork nodes + fork -> related topic edges.
    for f in forks:
        fork_name = f.get("n")
        if not fork_name:
            continue
        fork_id = f"fork_{fork_name}"
        add_node({
            "id": fork_id,
            "sourceType": "fork",
            "title": f.get("cn") or f.get("n"),
            "date": f.get("d"),
            "fork": fork_name,
        })
        for tid in f.get("rt", []):
            _add_unified_edge(edges, edge_keys, fork_id, tid, "fork_topic")

    # EIP nodes + native EIP graph edges.
    for en in eip_graph.get("nodes", []):
        eip_id = en.get("id")
        eip_num = _to_int(en.get("eip_num"))
        if not eip_id and eip_num is not None:
            eip_id = f"eip_{eip_num}"
        add_node({
            "id": eip_id,
            "sourceType": "eip",
            "eipNum": eip_num,
            "title": en.get("title"),
            "date": en.get("date"),
            "influence": en.get("influence", 0),
            "status": en.get("status"),
            "thread": en.get("thread"),
            "fork": en.get("fork"),
        })
    for edge in eip_graph.get("edges", []):
        _add_unified_edge(
            edges,
            edge_keys,
            edge.get("source"),
            edge.get("target"),
            edge.get("type"),
        )

    # Magicians topic nodes.
    for mtid, mt in magicians_topics.items():
        mtid_int = _to_int(mtid)
        node_id = f"mag_{mtid_int}" if mtid_int is not None else f"mag_{mtid}"
        add_node({
            "id": node_id,
            "sourceType": "magicians",
            "magiciansId": mtid_int,
            "title": mt.get("t"),
            "date": mt.get("d"),
            "author": mt.get("a"),
            "category": mt.get("cat"),
            "views": mt.get("vw", 0),
            "likes": mt.get("lk", 0),
            "posts": mt.get("pc", 0),
            "eips": mt.get("eips", []),
            "er": mt.get("er", []),
        })

    # Cross-forum edges.
    for edge in cross_forum_edges:
        source = _cross_forum_node_id(edge.get("sT"), edge.get("s"))
        target = _cross_forum_node_id(edge.get("tT"), edge.get("t"))
        _add_unified_edge(edges, edge_keys, source, target, edge.get("ty"))

    # Keep only edges whose endpoints exist in the node set.
    node_keys = {str(n["id"]) for n in nodes}
    edges = [
        e for e in edges
        if str(e.get("source")) in node_keys and str(e.get("target")) in node_keys
    ]

    return {
        "nodes": nodes,
        "edges": edges,
    }


def main():
    with open(ANALYSIS_PATH) as f:
        data = json.load(f)

    viz_data = prepare_viz_data(data)
    viz_json = json.dumps(viz_data, separators=(",", ":"))

    html = generate_html(viz_json, data)

    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Written: {OUTPUT_PATH} ({size_kb:.0f} KB)")


def prepare_viz_data(data):
    """Prepare a compact version of analysis data for the HTML visualization."""
    topics = data["topics"]
    authors = data["authors"]
    threads = data["research_threads"]
    forks = data["forks"]
    graph = data["graph"]

    compact_topics = {}
    for tid, t in topics.items():
        compact_topics[tid] = {
            "id": t["id"],
            "t": t["title"],
            "a": t["author"],
            "d": t["date"],
            "inf": t["influence_score"],
            "th": t.get("research_thread"),
            "era": t.get("era"),
            "lk": t["like_count"],
            "vw": t["views"],
            "pc": t["posts_count"],
            "ind": t["in_degree"],
            "eips": t.get("eip_mentions", []),
            "peips": t.get("primary_eips", []),
            "cat": t.get("category_name", ""),
            "tg": t.get("tags", [])[:5],
            "exc": t.get("first_post_excerpt", "")[:600],
            "out": t.get("outgoing_refs", []),
            "inc": t.get("incoming_refs", []),
            "parts": t.get("authors", [t["author"]])[:3],
            "coauth": [u for u in t.get("coauthors", []) if u != t["author"]],
            "mr": t.get("magicians_refs", []),
        }

    # Minor topics (below influence threshold) — merged into compact_topics
    minor_topics = data.get("minor_topics", {})
    for tid, mt in minor_topics.items():
        compact_topics[tid] = {
            "id": mt["id"],
            "t": mt["title"],
            "a": mt["author"],
            "d": mt["date"],
            "inf": mt["influence_score"],
            "vw": mt["views"],
            "lk": mt["like_count"],
            "pc": mt["posts_count"],
            "cat": mt.get("category_name", ""),
            "coauth": [u for u in mt.get("coauthors", []) if u != mt["author"]],
            "mn": True,
            "th": mt.get("research_thread"),
            "era": mt.get("era"),
            "exc": mt.get("first_post_excerpt", "")[:600],
            "tg": mt.get("tags", [])[:5],
            "eips": mt.get("eip_mentions", []),
            "peips": mt.get("primary_eips", []),
            "ind": mt.get("in_degree", 0),
            "outd": mt.get("out_degree", 0),
            "out": [],
            "inc": [],
            "mr": mt.get("magicians_refs", []),
        }

    compact_authors = {}
    author_list = sorted(authors.values(), key=lambda a: a["influence_score"], reverse=True)
    for i, a in enumerate(author_list):
        compact_authors[a["username"]] = {
            "u": a["username"],
            "tc": a["topics_created"],
            "tp": a["total_posts"],
            "lk": a["total_likes"],
            "ind": a["total_in_degree"],
            "inf": a["influence_score"],
            "yrs": a["active_years"],
            "cats": a["category_focus"],
            "ths": a["thread_focus"],
            "tops": a["top_topics"][:5],
            "co": dict(list(a["co_researchers"].items())[:5]),
            "rank": i,
            "at": a.get("all_topic_ids", []),
        }

    compact_threads = {}
    for tid, th in threads.items():
        compact_threads[tid] = {
            "id": tid,
            "n": th["name"],
            "tc": th["topic_count"],
            "dr": th["date_range"],
            "ka": dict(list(th["key_authors"].items())[:5]),
            "eips": th.get("eip_mentions", []),
            "tops": th["top_topics"][:10],
            "qc": th.get("quarterly_counts", []),
            "ms": [  # milestones
                {"id": m["id"], "t": m["title"][:60], "d": m["date"], "n": m["note"]}
                for m in th.get("milestones", [])
            ],
            "py": th.get("peak_year"),
            "ay": th.get("active_years", []),
            "ad": th.get("author_diversity"),
            "te": th.get("top_eips", [])[:5],
        }

    compact_forks = []
    for f in forks:
        compact_forks.append({
            "n": f["name"],
            "d": f["date"],
            "el": f.get("el_name"),
            "cl": f.get("cl_name"),
            "cn": f.get("combined_name"),
            "eips": f["eips"],
            "rt": f.get("related_topics", [])[:10],
        })

    raw_author_links = _build_author_links(data)
    eip_author_names = set(data.get("eip_authors", {}).keys())
    for e in (data.get("eip_catalog", {}) or {}).values():
        for raw_name in (e.get("authors", []) or []):
            name = str(raw_name or "").strip()
            if name:
                eip_author_names.add(name)
    for source_key in ("eipToEth", "eipToMag"):
        eip_author_names.update((raw_author_links.get(source_key) or {}).keys())
    for source_key in ("ethToEip", "magToEip"):
        for names in (raw_author_links.get(source_key) or {}).values():
            eip_author_names.update(names or [])

    eip_author_canonical, eip_author_aliases = _build_eip_author_canonical_map(
        eip_author_names,
        raw_author_links,
    )
    author_links = _canonicalize_author_links(raw_author_links, eip_author_canonical)

    def canonical_eip_author(name):
        key = str(name or "").strip()
        if not key:
            return ""
        return eip_author_canonical.get(key, key)

    compact_eips = {}
    for eip_str, e in data.get("eip_catalog", {}).items():
        canonical_authors = []
        seen_authors = set()
        for raw_name in (e.get("authors", []) or []):
            name = canonical_eip_author(raw_name)
            if not name or name in seen_authors:
                continue
            seen_authors.add(name)
            canonical_authors.append(name)
        compact_eips[eip_str] = {
            "t": e.get("title"),
            "s": e.get("status"),
            "ty": e.get("type"),
            "c": e.get("category"),
            "cr": e.get("created"),
            "fk": e.get("fork"),
            "au": canonical_authors,
            "rq": e.get("requires", []),
            "mt": e.get("magicians_topic_id"),
            "et": e.get("ethresearch_topic_id"),
            "inf": e.get("influence_score", 0),
            "th": e.get("research_thread"),
            "mv": e.get("magicians_views", 0),
            "ml": e.get("magicians_likes", 0),
            "mp": e.get("magicians_posts", 0),
            "mpc": e.get("magicians_participants", 0),
            "erc": e.get("ethresearch_citation_count", 0),
        }

    # Compact EIP authors (canonicalized aliases merged into a single profile).
    compact_eip_authors = {}
    eip_influence_by_num = {}

    def ensure_eip_author_entry(name):
        entry = compact_eip_authors.get(name)
        if entry is None:
            entry = {
                "eips": set(),
                "st": {},
                "fk": set(),
                "inf": 0.0,
                "yrs": set(),
                "aliases": set(eip_author_aliases.get(name, [])),
            }
            compact_eip_authors[name] = entry
        else:
            entry["aliases"].update(eip_author_aliases.get(name, []))
        return entry

    for name, a in data.get("eip_authors", {}).items():
        canonical_name = canonical_eip_author(name)
        if not canonical_name:
            continue
        entry = ensure_eip_author_entry(canonical_name)
        for num in (a.get("eips", []) or []):
            n = _to_int(num)
            if n is not None:
                entry["eips"].add(n)
        for status, count in (a.get("statuses") or {}).items():
            st = str(status or "").strip()
            if not st:
                continue
            try:
                c = int(count)
            except (TypeError, ValueError):
                c = 0
            if c > 0:
                entry["st"][st] = entry["st"].get(st, 0) + c
        for fork in (a.get("forks_contributed", []) or []):
            f = str(fork or "").strip()
            if f:
                entry["fk"].add(f)
        for year in (a.get("active_years", []) or []):
            y = _to_int(year)
            if y is not None:
                entry["yrs"].add(y)
        entry["inf"] += float(a.get("influence_score", 0) or 0)

    # Ensure authors found in EIP metadata appear in sidebar/detail even if they
    # were not present in precomputed eip_authors aggregates.
    for eip_str, e in data.get("eip_catalog", {}).items():
        num = _to_int(eip_str)
        if num is None:
            continue
        inf = float(e.get("influence_score", 0) or 0)
        eip_influence_by_num[num] = inf
        status = str(e.get("status") or "").strip()
        fork = str(e.get("fork") or "").strip()
        year = None
        created = str(e.get("created") or "").strip()
        if created and len(created) >= 4 and created[:4].isdigit():
            year = int(created[:4])
        for raw_name in (e.get("authors", []) or []):
            canonical_name = canonical_eip_author(raw_name)
            if not canonical_name:
                continue
            entry = ensure_eip_author_entry(canonical_name)
            entry["eips"].add(num)
            if status:
                entry["st"][status] = entry["st"].get(status, 0) + 1
            if fork:
                entry["fk"].add(fork)
            if year is not None:
                entry["yrs"].add(year)

    merged_eip_authors = {}
    for name, entry in compact_eip_authors.items():
        eips = sorted(entry["eips"])
        inf = sum(eip_influence_by_num.get(num, 0.0) for num in eips)
        if inf == 0:
            inf = float(entry["inf"] or 0.0)
        aliases = sorted({a for a in entry["aliases"] if a and a != name})
        merged_eip_authors[name] = {
            "n": name,
            "eips": eips,
            "st": dict(sorted(entry["st"].items(), key=lambda kv: kv[0])),
            "fk": sorted(entry["fk"]),
            "inf": round(inf, 3),
            "yrs": sorted(entry["yrs"]),
            "al": aliases,
        }
    compact_eip_authors = merged_eip_authors

    # Compact EIP graph
    eip_graph = data.get("eip_graph", {"nodes": [], "edges": []})

    # Compact Magicians topic entities
    compact_magicians = {}
    for mtid, mt in data.get("magicians_topics", {}).items():
        compact_magicians[str(mtid)] = {
            "id": mt.get("id"),
            "t": mt.get("title"),
            "sl": mt.get("slug"),
            "d": mt.get("date"),
            "cat": mt.get("category_name"),
            "a": mt.get("author"),
            "vw": mt.get("views", 0),
            "lk": mt.get("like_count", 0),
            "pc": mt.get("posts_count", 0),
            "tg": mt.get("tags", [])[:8],
            "eips": mt.get("eips", []),
            "er": mt.get("ethresearch_refs", [])[:24],
        }

    # Compact explicit cross-forum edges
    compact_cross_edges = []
    for edge in data.get("cross_forum_edges", []):
        compact_cross_edges.append({
            "sT": edge.get("source_type"),
            "s": edge.get("source"),
            "tT": edge.get("target_type"),
            "t": edge.get("target"),
            "ty": edge.get("type"),
        })

    compact_papers, papers_source = _load_papers_for_viz(data)

    unified_graph = _build_unified_graph(
        compact_topics,
        graph,
        compact_forks,
        eip_graph,
        compact_magicians,
        compact_cross_edges,
    )

    return {
        "meta": data["metadata"],
        "topics": compact_topics,
        "minorTopics": {},
        "authors": compact_authors,
        "threads": compact_threads,
        "forks": compact_forks,
        "eras": data["eras"],
        "eipCatalog": compact_eips,
        "eipAuthors": compact_eip_authors,
        "eipGraph": eip_graph,
        "magiciansTopics": compact_magicians,
        "crossForumEdges": compact_cross_edges,
        "papers": compact_papers,
        "papersMeta": {"count": len(compact_papers), "source": papers_source},
        "unifiedGraph": unified_graph,
        "authorLinks": author_links,
        "graph": {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        },
        "coGraph": data["co_author_graph"],
    }


def generate_html(viz_json, data):
    """Generate the full HTML document."""
    meta = data["metadata"]

    # Build the JS/CSS as a plain string to avoid f-string brace hell
    # We'll insert the data blob and a few Python values, but keep JS braces literal
    # by using a template with explicit markers.

    # Write CSS, HTML structure, then JS separately
    css = _build_css()
    js = _build_js()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ethereum Evolution</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
{css}
</style>
</head>
<body>
<div id="app">
  <header>
    <div class="header-row header-row-top">
      <h1>Ethereum Evolution</h1>
      <div class="header-top-main">
        <div class="stats">
          <button id="milestone-toggle" class="milestone-toggle" onclick="toggleMilestones()" title="Toggle influential post markers">\u2605 Influential Posts</button>
        </div>
        <div class="content-toggles">
          <button id="toggle-posts" class="content-toggle active" onclick="toggleContent('posts')" title="Toggle ethresear.ch topics">\u25CF EthResearch</button>
          <button id="toggle-eips" class="content-toggle" onclick="toggleContent('eips')" title="Toggle EIP nodes">\u25A0 EIPs</button>
          <button id="toggle-magicians" class="content-toggle" onclick="toggleContent('magicians')" title="Toggle Magicians nodes">\u25B2 Magicians</button>
          <button id="toggle-papers" class="content-toggle papers-toggle" onclick="toggleContent('papers')" title="Cycle papers: off \u2192 focus \u2192 context \u2192 broad \u2192 off">\u25C6 Papers</button>
        </div>
        <div class="inf-slider-wrap">
          <label for="inf-slider" style="font-size:10px;color:#666;white-space:nowrap">Min influence</label>
          <input type="range" id="inf-slider" min="0" max="100" value="0" step="1">
          <span id="inf-slider-label" style="font-size:10px;color:#888;min-width:32px">0</span>
        </div>
        <div class="controls">
          <button id="btn-timeline" class="active" onclick="showView('timeline')">Timeline</button>
          <button id="btn-network" onclick="showView('network')">Network</button>
          <button id="btn-coauthor" onclick="showView('coauthor')">Authors</button>
          <button class="help-btn" onclick="toggleHelp()" title="Keyboard shortcuts">?</button>
        </div>
      </div>
    </div>
    <div class="header-row header-row-bottom">
      <div id="filter-breadcrumb" class="breadcrumb"></div>
      <div class="search-wrap header-search-wrap">
        <input type="text" id="search-box" placeholder="Search topics, authors, EIPs...">
        <div class="search-dropdown" id="search-dropdown"></div>
      </div>
    </div>
  </header>
  <div id="main-area">
    <div id="timeline-view"></div>
    <div id="network-view"></div>
    <div id="coauthor-view"></div>
    <div id="detail-panel">
      <button class="close-btn" onclick="closeDetail()">&times;</button>
      <div id="detail-content"></div>
    </div>
  </div>
  <div id="sidebar">
    <button id="sidebar-width-toggle" class="sidebar-width-toggle" onclick="toggleSidebarWidth()" title="Expand sidebar">&#9664;</button>
    <button id="sidebar-hide-toggle" class="sidebar-hide-toggle" onclick="toggleSidebarHidden()" title="Hide sidebar">&#9654;</button>
    <div class="sidebar-section">
      <h3>Research Threads</h3>
      <div id="thread-legend" class="thread-legend"></div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-collapse-hdr" onclick="toggleCollapse('cat')">
        <span class="toggle-arrow" id="cat-arrow">&#9656;</span>
        <h3>Categories</h3>
      </div>
      <div class="sidebar-collapse-body" id="cat-body">
        <div id="cat-chips" class="cat-chips"></div>
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-collapse-hdr" onclick="toggleCollapse('tag')">
        <span class="toggle-arrow" id="tag-arrow">&#9656;</span>
        <h3>Tags</h3>
      </div>
      <div class="sidebar-collapse-body" id="tag-body">
        <div id="tag-chips" class="tag-chips"></div>
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-collapse-hdr" onclick="toggleCollapse('papers')">
        <span class="toggle-arrow open" id="papers-arrow">&#9662;</span>
        <h3>Papers</h3>
      </div>
      <div class="sidebar-collapse-body open" id="papers-body">
        <div class="paper-filter-grid">
          <div class="paper-filter-row">
            <span class="pf-label">Year</span>
            <input id="paper-year-min" class="pf-input" type="number" step="1">
            <span class="pf-sep">&#8211;</span>
            <input id="paper-year-max" class="pf-input" type="number" step="1">
          </div>
          <div class="paper-filter-row">
            <span class="pf-label">Min citations</span>
            <input id="paper-min-cites" class="pf-range" type="range" min="0" max="1000" step="1" value="0">
            <span id="paper-min-cites-label" class="pf-value">0</span>
          </div>
          <div class="paper-filter-row">
            <span class="pf-label">Tag</span>
            <select id="paper-tag-filter" class="pf-select"></select>
          </div>
          <div class="paper-filter-row">
            <span class="pf-label">Sort</span>
            <select id="paper-sort-filter" class="pf-select">
              <option value="relevance">Relevance</option>
              <option value="citations">Citations</option>
              <option value="recent">Recent</option>
            </select>
            <button id="paper-filter-reset" class="pf-reset-btn" type="button">Reset</button>
          </div>
        </div>
        <div id="paper-sidebar-summary" class="paper-sidebar-summary"></div>
        <div id="paper-sidebar-list" class="paper-sidebar-list"></div>
      </div>
    </div>
    <div class="sidebar-section">
      <h3 style="display:flex;align-items:center;justify-content:space-between">Top Authors
        <select id="author-sort" onchange="sortAuthorList(this.value)" style="font-size:10px;background:#1a1a2e;color:#aaa;border:1px solid #333;border-radius:3px;padding:1px 4px;cursor:pointer">
          <option value="inf">Influence</option>
          <option value="tc">Topics</option>
          <option value="lk">Likes</option>
          <option value="ind">Citations</option>
          <option value="tp">Posts</option>
        </select>
        <select id="eip-author-sort" onchange="buildEipAuthorList(this.value)" style="display:none;font-size:10px;background:#1a1a2e;color:#aaa;border:1px solid #333;border-radius:3px;padding:1px 4px;cursor:pointer">
          <option value="inf">Influence</option>
          <option value="total">Total</option>
          <option value="shipped">Shipped (Final)</option>
        </select>
      </h3>
      <div class="author-tab-wrap">
        <span class="author-tab active" data-tab="ethresearch" onclick="switchAuthorTab(false)">ethresearch</span>
        <span class="author-tab" data-tab="eip" onclick="switchAuthorTab(true)">EIP Authors</span>
      </div>
      <div id="author-list"></div>
    </div>
  </div>
</div>
<div class="tooltip" id="tooltip"></div>
<div id="eip-popover"></div>
<div class="toast" id="toast"></div>
<div id="help-overlay" class="help-overlay" onclick="toggleHelp()">
  <div class="help-card" onclick="event.stopPropagation()">
    <h3>Keyboard Shortcuts &amp; Interactions</h3>
    <div class="help-grid">
      <div class="help-key">Click node</div><div class="help-desc">Pin/focus node and highlight links</div>
      <div class="help-key">Double-click node</div><div class="help-desc">Open detail sidebar for that node</div>
      <div class="help-key">Click thread/author</div><div class="help-desc">Filter by thread or author</div>
      <div class="help-key">Double-click thread/author</div><div class="help-desc">Filter &amp; open detail sidebar</div>
      <div class="help-key">Shift+Click</div><div class="help-desc">Find citation path from pinned to clicked topic</div>
      <div class="help-key">&larr; &rarr;</div><div class="help-desc">Navigate between connected topics</div>
      <div class="help-key">Hover ref link</div><div class="help-desc">Highlight referenced topic in view</div>
      <div class="help-key">Scroll / Trackpad</div><div class="help-desc">Zoom timeline</div>
      <div class="help-key">Drag timeline</div><div class="help-desc">Pan horizontally</div>
      <div class="help-key">Double-click</div><div class="help-desc">Reset zoom</div>
      <div class="help-key">Esc</div><div class="help-desc">Clear all filters &amp; close panels</div>
      <div class="help-key">?</div><div class="help-desc">Toggle this help overlay</div>
    </div>
    <p style="margin-top:12px;color:#888;font-size:11px">
      Click thread chips for thread details. Use search to find topics by title, author, or EIP number.
      Trace Lineage shows the citation tree (2 hops up and down) from any topic.
    </p>
  </div>
</div>

<script>
const DATA = {viz_json};
const THREAD_COLORS = {json.dumps(THREAD_COLORS)};
const THREAD_ORDER = {json.dumps(THREAD_ORDER)};
const AUTHOR_COLORS = {json.dumps(AUTHOR_COLORS)};
{js}
</script>
</body>
</html>"""


def _build_css():
    return """
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
  overscroll-behavior-x: none;
  overscroll-behavior-y: none;
}
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0a0a0f; color: #e0e0e0; overflow: hidden; height: 100vh; }
#app { --sidebar-width: 300px; display: grid; grid-template-rows: auto 1fr; grid-template-columns: 1fr var(--sidebar-width); height: 100vh; }
#app.sidebar-wide { --sidebar-width: 460px; }
#app.sidebar-hidden { --sidebar-width: 0px; }

header { grid-column: 1 / -1; padding: 10px 20px; background: #12121a;
         border-bottom: 1px solid #2a2a3a; display: flex; flex-direction: column; align-items: stretch; gap: 8px; }
.header-row { display: flex; align-items: center; gap: 12px; min-height: 28px; }
.header-row-top { justify-content: flex-start; }
.header-row-bottom { justify-content: flex-start; }
header h1 { font-size: 18px; font-weight: 600; color: #fff; white-space: nowrap; }
header h1 .title-short { display: none; }
header .header-top-main { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; flex-wrap: wrap; }
header .stats { font-size: 12px; color: #888; display: flex; gap: 15px; }
header .stats span { white-space: nowrap; }
.inf-slider-wrap { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.inf-slider-wrap input[type=range] { width: 80px; height: 4px; -webkit-appearance: none; appearance: none;
  background: #333; border-radius: 2px; outline: none; cursor: pointer; }
.inf-slider-wrap input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none;
  width: 12px; height: 12px; border-radius: 50%; background: #667; cursor: pointer; }
.inf-slider-wrap input[type=range]::-moz-range-thumb { width: 12px; height: 12px; border-radius: 50%;
  background: #667; cursor: pointer; border: none; }
.inf-slider-wrap input[type=range]::-webkit-slider-thumb:hover { background: #88a; }
.bc-hint { font-size: 10px; color: #555; font-style: italic; }
.controls { display: flex; gap: 8px; flex-shrink: 0; margin-left: auto; }
.controls button { background: #1e1e2e; border: 1px solid #333; color: #ccc;
                   padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; }
.controls button:hover { background: #2a2a3e; }
.controls button.active { background: #333366; border-color: #5555aa; color: #fff; }

#main-area { grid-column: 1; overflow: hidden; position: relative; overscroll-behavior: none; min-width: 0; }
#sidebar { grid-column: 2; background: #12121a; border-left: 1px solid #2a2a3a; overflow-y: auto; position: relative; min-width: 0; }
#app.sidebar-hidden #sidebar { border-left: none; overflow: hidden; }
#sidebar::-webkit-scrollbar { width: 6px; }
#sidebar::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.sidebar-width-toggle { position: fixed; left: 0; top: 50%; transform: translate(-50%, -50%);
                        width: 24px; height: 36px; border: 1px solid #2a2a3a;
                        border-radius: 0 6px 6px 0; background: #12121a; color: #7788cc;
                        font-size: 11px; cursor: pointer; z-index: 200; line-height: 1; padding: 0; }
.sidebar-width-toggle:hover { background: #1a1a2e; color: #aab6ff; }
.sidebar-hide-toggle { position: fixed; left: 0; top: 50%; transform: translate(-50%, -50%);
                       width: 24px; height: 36px; border: 1px solid #2a2a3a;
                       border-radius: 0 6px 6px 0; background: #12121a; color: #88aacc;
                       font-size: 11px; cursor: pointer; z-index: 200; line-height: 1; padding: 0; }
.sidebar-hide-toggle:hover { background: #1a1a2e; color: #bbd6ff; }
#sidebar .sidebar-section:first-child { padding-top: 12px; }

#timeline-view, #network-view, #coauthor-view { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
#timeline-view { display: block; overscroll-behavior: none; }
#network-view { display: none; }
#coauthor-view { display: none; }

/* Timeline */
.timeline-container { width: 100%; height: 100%; overflow: hidden; overscroll-behavior: none; touch-action: none; }
.timeline-container svg { touch-action: none; }
.fork-line { stroke: #555; stroke-width: 1.5; stroke-dasharray: 4,4; }
.fork-label { fill: #999; font-size: 12px; font-weight: 600; }
.era-bg { opacity: 0.03; }
.histogram-bar { fill: rgba(255,255,255,0.13); }
.histogram-bar:hover { fill: rgba(255,255,255,0.25); }

/* CRITICAL: pointer-events:all so circles with transparent fill are still hoverable */
.topic-circle { cursor: pointer; pointer-events: all; }
.edge-line { stroke: #556; }

/* Arrow markers (default barely visible, highlighted more visible) */
.arrow-default { fill: #556; }
.arrow-highlight { fill: #88aaff; }
.arrow-lineage { fill: #88aaff; }
.arrow-net-default { fill: #334; }
.arrow-net-highlight { fill: #88aaff; }

/* Network */
.net-node { cursor: pointer; }
.net-link { stroke: #334; }
.fork-diamond { fill: #ffcc00; stroke: #aa8800; stroke-width: 1.5; cursor: pointer; }
.net-paper-shape { fill: #2f4f77; stroke: #8fb8ef; stroke-width: 0.9; }

/* Co-Author Network */
.coauthor-node { cursor: pointer; }
.coauthor-link { stroke: #445566; }
.coauthor-label { fill: #ccc; font-size: 11px; font-weight: 500; pointer-events: none;
                  text-anchor: middle; dominant-baseline: central; text-shadow: 0 1px 3px #000, 0 0 6px #000; }
.coauthor-label-hover { fill: #fff; font-size: 10px; font-weight: 400; pointer-events: none;
                        text-anchor: middle; dominant-baseline: central; text-shadow: 0 1px 3px #000, 0 0 6px #000; }

/* Sidebar */
.sidebar-section { padding: 12px 14px; border-bottom: 1px solid #1e1e2e; }
.sidebar-section h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
                      color: #666; margin-bottom: 8px; }
.thread-legend { display: flex; flex-direction: column; gap: 3px; }
.thread-chip { font-size: 10px; padding: 2px 6px; border-radius: 3px; cursor: pointer;
               opacity: 0.7; transition: opacity 0.15s; white-space: nowrap;
               display: flex; align-items: center; gap: 6px; }
.thread-chip:hover, .thread-chip.active { opacity: 1; }
.thread-chip .thread-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.thread-chip .thread-count { font-size: 9px; opacity: 0.6; flex-shrink: 0; }
.thread-chip .status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-left: -2px; }
.thread-chip .status-dot.active { background: #4caf50; }
.thread-chip .status-dot.moderate { background: #ffc107; }
.thread-chip .status-dot.dormant { background: #555; }
.thread-chip .sparkline-wrap { flex-shrink: 0; position: relative; }
.thread-chip .sparkline-wrap svg { display: block; }
.author-item { padding: 6px 0; cursor: pointer; display: flex; align-items: center; gap: 8px; }
.author-item:hover { background: #1a1a2a; }
.author-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.author-name { font-size: 12px; flex: 1; min-width: 0; overflow: hidden;
               text-overflow: ellipsis; white-space: nowrap; }
.author-count { font-size: 10px; color: #666; flex-shrink: 0; max-width: 145px; overflow: hidden;
                text-overflow: ellipsis; white-space: nowrap; text-align: right; }
#app.sidebar-wide .author-count { max-width: 260px; }
.author-item.active .author-name { color: #fff; font-weight: 600; }

/* Collapsible sidebar sections */
.sidebar-collapse-hdr { display: flex; align-items: center; cursor: pointer;
                        user-select: none; gap: 6px; }
.sidebar-collapse-hdr h3 { margin-bottom: 0; }
.sidebar-collapse-hdr .toggle-arrow { font-size: 10px; color: #666; transition: transform 0.15s; }
.sidebar-collapse-hdr .toggle-arrow.open { transform: rotate(90deg); }
.sidebar-collapse-body { overflow: hidden; max-height: 0; transition: max-height 0.25s ease; }
.sidebar-collapse-body.open { max-height: 600px; }

/* Category chips */
.cat-chips { display: flex; flex-wrap: wrap; gap: 4px; padding-top: 8px; }
.cat-chip { font-size: 10px; padding: 2px 6px; border-radius: 3px; cursor: pointer;
            background: rgba(100,120,160,0.15); color: #8899bb; border: 1px solid rgba(100,120,160,0.25);
            opacity: 0.75; transition: opacity 0.15s, border-color 0.15s, background 0.15s;
            white-space: nowrap; display: inline-flex; align-items: center; gap: 4px; }
.cat-chip:hover { opacity: 1; }
.cat-chip.active { opacity: 1; border-color: #8899cc; background: rgba(100,120,180,0.3); color: #aabbdd; }
.cat-chip .chip-count { font-size: 9px; color: #667; }

/* Tag chips -- smaller and more compact */
.tag-chips { display: flex; flex-wrap: wrap; gap: 3px; padding-top: 8px; }
.tag-chip { font-size: 9px; padding: 1px 5px; border-radius: 3px; cursor: pointer;
            background: rgba(130,130,130,0.1); color: #889; border: 1px solid rgba(130,130,130,0.2);
            opacity: 0.7; transition: opacity 0.15s, border-color 0.15s, background 0.15s;
            white-space: nowrap; display: inline-flex; align-items: center; gap: 3px; }
.tag-chip:hover { opacity: 1; }
.tag-chip.active { opacity: 1; border-color: #99aaaa; background: rgba(130,160,160,0.25); color: #aacccc; }
.tag-chip .chip-count { font-size: 8px; color: #556; }

/* Detail panel */
#detail-panel { display: none; position: absolute; top: 0; right: 0; width: 420px; height: 100%;
                background: #15151f; border-left: 1px solid #2a2a3a; overflow-y: auto;
                z-index: 100; padding: 16px;
                scrollbar-width: thin; scrollbar-color: #3a3a4d #15151f; }
#detail-panel::-webkit-scrollbar { width: 8px; }
#detail-panel::-webkit-scrollbar-track { background: #15151f; }
#detail-panel::-webkit-scrollbar-thumb { background: #3a3a4d; border-radius: 4px; }
#detail-panel::-webkit-scrollbar-thumb:hover { background: #4a4a66; }
#detail-panel.open { display: block; }
#detail-panel .close-btn { position: absolute; top: 8px; right: 12px; background: none;
                           border: none; color: #666; font-size: 18px; cursor: pointer; }
#detail-panel .close-btn:hover { color: #fff; }
#detail-panel h2 { font-size: 16px; color: #fff; margin-bottom: 4px;
                   padding-right: 30px; line-height: 1.3; }
#detail-panel .meta { font-size: 12px; color: #888; margin-bottom: 12px; }
#detail-panel .meta a { color: #7788cc; text-decoration: none; }
#detail-panel .meta a:hover { text-decoration: underline; }
.detail-stat { display: flex; justify-content: space-between; padding: 4px 0;
               font-size: 12px; border-bottom: 1px solid #1a1a2a; }
.detail-stat .label { color: #888; }
.detail-stat .value { color: #ccc; }
.detail-excerpt { font-size: 12px; color: #999; margin: 12px 0; line-height: 1.5; font-style: italic; }
.detail-refs { margin-top: 12px; }
.detail-refs h4 { font-size: 11px; text-transform: uppercase; color: #666; margin-bottom: 6px; }
.detail-refs .ref-item { font-size: 11px; padding: 3px 0; }
.detail-refs .ref-item a { color: #7788cc; text-decoration: none; cursor: pointer; }
.detail-refs .ref-item a:hover { text-decoration: underline; }
.paper-item { padding: 6px 0; border-bottom: 1px solid #1a1a2a; }
.paper-item:last-child { border-bottom: none; }
.paper-title { color: #9cc8ff; text-decoration: none; font-size: 11px; line-height: 1.35; }
.paper-title:hover { text-decoration: underline; }
.paper-meta { color: #7f7f95; font-size: 10px; margin-top: 2px; }
.paper-reasons { color: #6f8a6f; font-size: 10px; margin-top: 2px; }
.paper-expand { margin-top: 6px; font-size: 10px; color: #88aadd; cursor: pointer; user-select: none; display: inline-block; }
.paper-expand:hover { text-decoration: underline; }
.paper-filter-grid { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.paper-filter-row { display: flex; align-items: center; gap: 6px; }
.paper-filter-row .pf-label { width: 74px; flex-shrink: 0; font-size: 10px; color: #8b8ba3; text-transform: uppercase; letter-spacing: 0.4px; }
.paper-filter-row .pf-sep { color: #666; font-size: 10px; }
.pf-input, .pf-select { background: #1a1a2e; border: 1px solid #333; color: #bbb; border-radius: 4px; font-size: 10px; padding: 2px 6px; min-width: 0; }
.pf-input { width: 62px; }
.pf-select { flex: 1; }
.pf-range { flex: 1; min-width: 0; accent-color: #6c8fb6; }
.pf-value { width: 36px; text-align: right; color: #8a8aa0; font-size: 10px; }
.pf-reset-btn { margin-left: auto; background: #1a1a2a; border: 1px solid #334; color: #88aadd; border-radius: 4px; padding: 2px 7px; font-size: 10px; cursor: pointer; }
.pf-reset-btn:hover { border-color: #446a99; color: #aaccff; }
.paper-sidebar-summary { color: #6f6f86; font-size: 10px; margin: 4px 0 6px; }
.paper-sidebar-list { max-height: 300px; overflow-y: auto; border-top: 1px solid #1a1a2a; }
.paper-sidebar-list::-webkit-scrollbar { width: 6px; }
.paper-sidebar-list::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.paper-sidebar-item { padding: 7px 0; border-bottom: 1px solid #1a1a2a; cursor: pointer; }
.paper-sidebar-item:last-child { border-bottom: none; }
.paper-sidebar-item:hover .paper-title { text-decoration: underline; }
.eip-tag { display: inline-block; font-size: 10px; padding: 1px 5px; background: #1e2a3a;
           border: 1px solid #2a3a5a; border-radius: 3px; margin: 1px; color: #88aacc; cursor: pointer; }
.eip-tag:hover { border-color: #4a6a9a; }
.eip-tag.primary { background: #1a3a1a; border-color: #2a5a2a; color: #88cc88; }
.eip-tag.primary:hover { border-color: #4a8a4a; }
#eip-popover { position: fixed; z-index: 300; background: #1a1a2e; border: 1px solid #444;
               border-radius: 6px; padding: 12px 16px; max-width: 380px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
               font-size: 12px; color: #ccc; display: none; }
#eip-popover h3 { margin: 0 0 8px; font-size: 14px; color: #eee; }
.eip-status { display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 3px; margin-left: 6px; }
.eip-status-final { background: #1a3a1a; color: #88cc88; }
.eip-status-draft { background: #1a2a3a; color: #88aadd; }
.eip-status-review { background: #3a3a1a; color: #cccc88; }
.eip-status-stagnant, .eip-status-withdrawn { background: #2a2a2a; color: #888; }
.eip-status-living { background: #1a3a3a; color: #88cccc; }
.magicians-link { color: #bb88cc; text-decoration: none; font-size: 11px; }
.magicians-link:hover { text-decoration: underline; }
.search-item-eip { border-left: 2px solid #88aacc; }
.search-item-paper { border-left: 2px solid #8fb8ef; }
.fork-tag { display: inline-block; font-size: 10px; padding: 1px 5px; background: #3a3a1a;
            border: 1px solid #5a5a2a; border-radius: 3px; margin: 1px; color: #cccc88; cursor: pointer; }
.fork-tag:hover { background: #45451d; border-color: #6a6a33; }

/* Thread bar in author detail */
.thread-bar-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 11px; }
.thread-bar-label { color: #888; width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
.thread-bar-track { flex: 1; height: 6px; background: #1a1a2a; border-radius: 3px; overflow: hidden; }
.thread-bar-fill { height: 100%; border-radius: 3px; }
.thread-bar-pct { color: #666; font-size: 10px; width: 32px; text-align: right; flex-shrink: 0; }

#search-box { width: 100%; padding: 6px 8px; background: #1a1a2a; border: 1px solid #333;
              border-radius: 4px; color: #ccc; font-size: 12px; }
#search-box:focus { outline: none; border-color: #555; }
.search-wrap { position: relative; margin-bottom: 8px; }
.header-search-wrap { margin-left: auto; margin-bottom: 0; width: min(420px, 46vw); flex-shrink: 0; }
.search-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: #1a1a2e;
                   border: 1px solid #444; border-top: none; border-radius: 0 0 4px 4px;
                   max-height: 280px; overflow-y: auto; z-index: 200; display: none; }
.search-dropdown::-webkit-scrollbar { width: 5px; }
.search-dropdown::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.search-item { padding: 6px 10px; cursor: pointer; font-size: 11px; border-bottom: 1px solid #1e1e2e; }
.search-item:hover, .search-item.active { background: #252540; }
.search-item .si-title { color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.search-item .si-meta { color: #666; font-size: 10px; margin-top: 1px; }
.search-item .si-thread { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; }

/* Topic labels on timeline */
.topic-label { fill: #bbb; font-size: 9px; pointer-events: none; font-weight: 500;
               text-shadow: 0 0 4px #0a0a0f, 0 0 8px #0a0a0f, 0 1px 3px #0a0a0f; }

/* Fork line hover area */
.fork-hover-line { stroke: transparent; stroke-width: 16; cursor: pointer; }

/* Milestone markers on timeline */
.milestone-marker { fill: #ffcc44; stroke: #aa8800; stroke-width: 1; cursor: pointer; pointer-events: all; }
.milestone-badge { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 3px; margin: 8px 0;
                   background: #3a3010; border: 1px solid #5a5020; color: #ffcc44; }
.milestone-badge .mb-icon { margin-right: 4px; }
.milestone-toggle { background: none !important; border: 1px solid #5a5020 !important; color: #aa8800;
                    padding: 2px 8px !important; border-radius: 3px !important; font-size: 10px !important;
                    cursor: pointer; margin-left: 6px; }
.milestone-toggle.active { border-color: #ffcc44 !important; color: #ffcc44; }
.paper-match-toggle { background: none !important; border: 1px solid #334a66 !important; color: #88aadd;
                      padding: 2px 8px !important; border-radius: 3px !important; font-size: 10px !important;
                      cursor: pointer; margin-left: 6px; }
.paper-match-toggle:hover { border-color: #446a99 !important; color: #aaccff; }
.paper-match-toggle.mode-strict { border-color: #5a5a2a !important; color: #d9cc88; }
.paper-match-toggle.mode-loose { border-color: #2a5a3a !important; color: #8ad0a0; }

/* Thread detail stats */
.thread-stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin: 10px 0; }
.thread-stat-box { background: #1a1a2a; border-radius: 4px; padding: 6px 8px; text-align: center; }
.thread-stat-box .tsb-val { font-size: 16px; font-weight: 600; color: #fff; }
.thread-stat-box .tsb-lbl { font-size: 9px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
.milestone-list { margin: 8px 0; }
.milestone-item { font-size: 11px; padding: 4px 0; border-bottom: 1px solid #1a1a2a; display: flex; gap: 8px; }
.milestone-item .ms-note { color: #ffcc44; font-size: 9px; text-transform: uppercase; min-width: 65px; }
.milestone-item .ms-title { color: #ccc; flex: 1; cursor: pointer; }
.milestone-item .ms-title:hover { color: #fff; text-decoration: underline; }

/* Filter breadcrumb */
.breadcrumb { font-size: 11px; color: #888; display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.breadcrumb:empty { display: none; }
.bc-tag { display: inline-flex; align-items: center; gap: 4px; background: #1e1e2e; border: 1px solid #333;
          border-radius: 3px; padding: 2px 8px; color: #bbb; white-space: nowrap; }
.bc-tag .bc-close { cursor: pointer; color: #666; margin-left: 2px; }
.bc-tag .bc-close:hover { color: #fff; }

/* Help overlay */
.help-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; }
.help-overlay.open { display: flex; }
.help-card { background: #1a1a2a; border: 1px solid #333; border-radius: 8px; padding: 24px;
             max-width: 480px; width: 90%; }
.help-card h3 { color: #fff; font-size: 15px; margin-bottom: 16px; }
.help-grid { display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; }
.help-key { font-size: 11px; color: #88aaff; font-weight: 600; white-space: nowrap; }
.help-desc { font-size: 11px; color: #bbb; }
.help-btn { background: none !important; border: 1px solid #444 !important; width: 24px; height: 24px;
            font-size: 13px !important; font-weight: 700; border-radius: 50% !important;
            padding: 0 !important; display: flex; align-items: center; justify-content: center; }

/* Network node labels */
.net-label { fill: #bbb; font-size: 8px; pointer-events: none; font-weight: 500;
             text-anchor: middle; dominant-baseline: hanging;
             text-shadow: 0 0 3px #0a0a0f, 0 0 6px #0a0a0f; }

/* Toast notification */
.toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
         background: #2a3a2a; border: 1px solid #4a6a4a; color: #88cc88; padding: 8px 16px;
         border-radius: 4px; font-size: 12px; z-index: 1000; opacity: 0; transition: opacity 0.3s;
         pointer-events: none; }
.toast.show { opacity: 1; }

.tooltip { position: fixed; background: #1e1e2e; border: 1px solid #444; border-radius: 4px;
           padding: 8px 12px; font-size: 11px; color: #ccc; pointer-events: none;
           z-index: 500; max-width: 350px; line-height: 1.4; display: none;
           box-shadow: 0 4px 12px rgba(0,0,0,0.5); }

/* Minor topics */
.minor-ref a { color: #889 !important; font-style: italic; }
.minor-ref a:hover { color: #aab !important; }

/* Content toggle buttons */
.content-toggles { display: flex; gap: 4px; flex-shrink: 0; }
.content-toggle { background: #1e1e2e; border: 1px solid #333; color: #888; padding: 2px 8px;
                  border-radius: 3px; cursor: pointer; font-size: 10px; }
.content-toggle:hover { background: #2a2a3e; }
.content-toggle.active { background: #2a3a2a; border-color: #4a6a4a; color: #88cc88; }
.content-toggle.papers-toggle.active { background: #1f2f45; border-color: #4b6f9d; color: #9cc8ff; }
.content-toggle.papers-toggle.mode-focus { border-color: #4b6f9d; color: #9cc8ff; }
.content-toggle.papers-toggle.mode-context { border-color: #4b7d5a; color: #9cddb4; }
.content-toggle.papers-toggle.mode-broad { border-color: #7d6a4b; color: #e3c58f; }
.content-toggle.disabled { opacity: 0.45; cursor: default; pointer-events: none; }

@media (max-width: 1450px) {
  header { padding: 10px 12px; gap: 8px; }
  header h1 .title-long { display: none; }
  header h1 .title-short { display: inline; }
  .header-row-top { gap: 8px; }
  .header-row-bottom { gap: 8px; min-height: 24px; }
  .header-search-wrap { width: min(340px, 45vw); }
  .content-toggles { flex-wrap: wrap; }
}

@media (max-width: 1240px) {
  .controls button { padding: 4px 8px; font-size: 10px; }
  .header-search-wrap { width: min(300px, 42vw); }
}

/* EIP squares on timeline */
.eip-square { cursor: pointer; pointer-events: all; }
.magicians-triangle { cursor: pointer; pointer-events: all; }
.paper-diamond { cursor: pointer; pointer-events: all; }
.paper-hit { cursor: pointer; pointer-events: all; fill: transparent; stroke: transparent; stroke-width: 12; }
.magicians-label { fill: #c8b5db; font-size: 8px; pointer-events: none; }
.paper-label { fill: #9ec6ff; font-size: 8px; pointer-events: none; }

/* Cross-reference edges (EIP ↔ topic) */
.cross-ref-edge { stroke-dasharray: 4 3; pointer-events: none; }
.magicians-ref-edge { pointer-events: none; }
.paper-topic-ref-edge { stroke-dasharray: 2 3; pointer-events: none; }
.paper-eip-ref-edge { stroke-dasharray: 3 2; pointer-events: none; }
.paper-paper-edge { stroke-dasharray: 1 0; pointer-events: none; }
.cross-ref-edge, .magicians-ref-edge, .paper-topic-ref-edge, .paper-eip-ref-edge, .paper-paper-edge, .focus-eip-topic-edge {
  stroke-linecap: round; pointer-events: none;
}

/* EIP status colors */
.eip-color-final { fill: #4caf50; stroke: #4caf50; }
.eip-color-living { fill: #26c6da; stroke: #26c6da; }
.eip-color-review { fill: #fdd835; stroke: #fdd835; }
.eip-color-lastcall { fill: #fdd835; stroke: #fdd835; }
.eip-color-draft { fill: #42a5f5; stroke: #42a5f5; }
.eip-color-stagnant { fill: #666; stroke: #666; }
.eip-color-withdrawn { fill: #555; stroke: #555; }
.eip-color-moved { fill: #555; stroke: #555; }

/* EIP detail panel additions */
.eip-detail-stat { display: flex; justify-content: space-between; padding: 4px 0;
                   font-size: 12px; border-bottom: 1px solid #1a1a2a; }
.eip-detail-stat .label { color: #888; }
.eip-detail-stat .value { color: #ccc; }
.eip-requires-tag { display: inline-block; font-size: 10px; padding: 1px 5px; background: #1e2a3a;
                    border: 1px solid #2a3a5a; border-radius: 3px; margin: 1px; color: #88aacc; cursor: pointer; }
.eip-requires-tag:hover { border-color: #4a6a9a; background: #2a3a4a; }

/* EIP author sidebar tab */
.author-tab-wrap { display: flex; gap: 0; margin-bottom: 8px; }
.author-tab { flex: 1; text-align: center; font-size: 10px; padding: 3px 6px; cursor: pointer;
              color: #888; border-bottom: 2px solid transparent; }
.author-tab:hover { color: #ccc; }
.author-tab.active { color: #fff; border-bottom-color: #88aaff; }

/* EIP network node */
.eip-net-node { cursor: pointer; pointer-events: all; }
"""


def _build_js():
    # Return JS as a plain string -- no Python f-string interpolation needed
    # (DATA, THREAD_COLORS etc. are injected as separate <script> constants)
    return r"""
// === GLOBALS ===
let activeView = 'timeline';
let activeThread = null;
let activeAuthor = null;
let activeEipAuthor = null;
let activeCategory = null;
let activeTag = null;
let minInfluence = 0;
let simulation = null;
let coAuthorSimulation = null;
let hoveredTopicId = null;
let pinnedTopicId = null;
let activeMagiciansId = null;
let activeEipNum = null;
let activePaperId = null;
let lineageActive = false;
let lineageSet = new Set();
let lineageEdgeSet = new Set(); // "src-tgt" strings for fast edge lookup
let milestonesVisible = false;
let pathMode = false;
let pathStart = null;
let pathSet = new Set();
let pathEdgeSet = new Set();
let showPosts = true;
let showEips = false;
let showMagicians = false;
let showPapers = false;
let paperLayerMode = 'focus'; // 'focus' | 'context' | 'broad'
let eipVisibilityMode = 'connected'; // 'connected' | 'all'
let eipAuthorTab = false; // false = ethresearch, true = EIP authors
let sidebarWide = false;
let sidebarHidden = false;
let paperMatchMode = 'balanced'; // 'strict' | 'balanced' | 'loose'
let paperFilterYearMin = null;
let paperFilterYearMax = null;
let paperFilterMinCitations = 0;
let paperFilterTag = '';
let paperSidebarSort = 'relevance'; // 'relevance' | 'citations' | 'recent'

// --- Prevent macOS trackpad swipe-back/forward ---
// On macOS, the browser compositor may detect navigation gestures from
// trackpad two-finger swipes BEFORE element-level handlers fire.
// A document capture-phase non-passive handler is the earliest JS hook.
// Also force overscroll-behavior via JS in case CSS isn't picked up.
document.documentElement.style.overscrollBehavior = 'none';
document.body.style.overscrollBehavior = 'none';
document.addEventListener('wheel', function(ev) {
  if (activeView !== 'timeline') return;
  // Keep native scrolling inside right-side detail panel.
  if (ev.target && ev.target.closest && ev.target.closest('#detail-panel')) return;
  // Only intercept events targeting the main visualization area
  if (ev.target.closest && ev.target.closest('#main-area')) {
    ev.preventDefault();
  }
}, {passive: false, capture: true});

// Build milestone index: topic_id -> {threadId, threadName, note, human}
const MILESTONE_LABELS = {
  earliest: 'Earliest topic',
  latest: 'Most recent topic',
  peak_influence: 'Most influential topic',
  peak_citations: 'Most cited within thread',
  interval: 'Key topic in this period'
};
const milestoneIndex = {};
THREAD_ORDER.forEach(function(tid) {
  var th = DATA.threads[tid];
  if (!th || !th.ms) return;
  th.ms.forEach(function(ms) {
    milestoneIndex[ms.id] = {
      threadId: tid,
      threadName: th.n,
      note: ms.n,
      human: MILESTONE_LABELS[ms.n] || ms.n
    };
  });
});

// Build index: topic_id -> set of connected topic_ids (for edge highlighting)
const topicEdgeIndex = {};
DATA.graph.edges.forEach(e => {
  const s = String(e.source), t = String(e.target);
  if (!topicEdgeIndex[s]) topicEdgeIndex[s] = new Set();
  if (!topicEdgeIndex[t]) topicEdgeIndex[t] = new Set();
  topicEdgeIndex[s].add(Number(e.target));
  topicEdgeIndex[t].add(Number(e.source));
});

// Inverted indices for similarity search
const eipToTopics = {};
const tagToTopics = {};
Object.values(DATA.topics).forEach(function(t) {
  (t.eips || []).concat(t.peips || []).forEach(function(e) {
    if (!eipToTopics[e]) eipToTopics[e] = new Set();
    eipToTopics[e].add(t.id);
  });
  (t.tg || []).forEach(function(tag) {
    if (!tagToTopics[tag]) tagToTopics[tag] = new Set();
    tagToTopics[tag].add(t.id);
  });
});

// Reverse lookup: magicians_topic_id -> [eip_number_strings]
var magiciansToEips = {};
Object.entries(DATA.eipCatalog || {}).forEach(function(entry) {
  var eipNum = entry[0], eip = entry[1];
  if (eip.mt) {
    if (!magiciansToEips[eip.mt]) magiciansToEips[eip.mt] = [];
    magiciansToEips[eip.mt].push(eipNum);
  }
});
var magiciansTopicById = DATA.magiciansTopics || {};

// Cross-forum traversal indices
var eipToMagiciansRefs = {};
var topicToMagiciansRefs = {};
(DATA.crossForumEdges || []).forEach(function(edge) {
  if (!edge) return;
  if (edge.sT === 'eip' && edge.tT === 'magicians_topic' && edge.s !== undefined && edge.t !== undefined) {
    var eipNum = String(edge.s);
    if (!eipToMagiciansRefs[eipNum]) eipToMagiciansRefs[eipNum] = new Set();
    eipToMagiciansRefs[eipNum].add(Number(edge.t));
  }
  if (edge.sT === 'topic' && edge.tT === 'magicians_topic' && edge.s !== undefined && edge.t !== undefined) {
    var topicId = String(edge.s);
    if (!topicToMagiciansRefs[topicId]) topicToMagiciansRefs[topicId] = new Set();
    topicToMagiciansRefs[topicId].add(Number(edge.t));
  }
});

// EIP status → color
var EIP_STATUS_COLORS = {
  'Final': '#4caf50', 'Living': '#26c6da', 'Review': '#fdd835', 'Last Call': '#fdd835',
  'Draft': '#42a5f5', 'Stagnant': '#666', 'Withdrawn': '#555', 'Moved': '#555'
};
function eipColor(eip) { return EIP_STATUS_COLORS[eip.s] || '#555'; }

// Build reverse lookup: eip_num -> set of topic IDs mentioning it (for cross-ref edges)
var eipToTopicIds = {};
Object.values(DATA.topics).forEach(function(t) {
  (t.eips || []).forEach(function(e) {
    if (!eipToTopicIds[e]) eipToTopicIds[e] = [];
    eipToTopicIds[e].push(t.id);
  });
});

// EIPs that are directly connected to ethresear.ch topics
var connectedEipNodeIds = new Set();
((DATA.eipGraph || {}).edges || []).forEach(function(edge) {
  if (edge.type === 'eip_topic' && typeof edge.source === 'string' && edge.source.indexOf('eip_') === 0) {
    connectedEipNodeIds.add(edge.source);
  }
});

// Linked author identities across ethresear.ch and EIP datasets.
const AUTHOR_LINKS = DATA.authorLinks || {};
const ETH_TO_EIP_AUTHORS = AUTHOR_LINKS.ethToEip || {};
const EIP_TO_ETH_AUTHORS = AUTHOR_LINKS.eipToEth || {};
const MAG_TO_ETH_AUTHORS = AUTHOR_LINKS.magToEth || {};
const ETH_TO_MAG_AUTHORS = AUTHOR_LINKS.ethToMag || {};
const MAG_TO_EIP_AUTHORS = AUTHOR_LINKS.magToEip || {};
const EIP_TO_MAG_AUTHORS = AUTHOR_LINKS.eipToMag || {};
const EIP_ALIAS_TO_CANONICAL = AUTHOR_LINKS.eipAliasToCanonical || {};

function canonicalEipAuthorName(name) {
  var raw = String(name || '').trim();
  if (!raw) return raw;
  return EIP_ALIAS_TO_CANONICAL[raw] || raw;
}

function identityNode(kind, name) {
  return String(kind) + ':' + String(name);
}

function parseIdentityNode(node) {
  var idx = String(node).indexOf(':');
  if (idx < 0) return {kind: '', name: String(node)};
  return {kind: String(node).slice(0, idx), name: String(node).slice(idx + 1)};
}

function sortedSetValues(setObj) {
  return Array.from(setObj || []).sort(function(a, b) { return String(a).localeCompare(String(b)); });
}

const IDENTITY_GRAPH = new Map();
const IDENTITY_COMPONENT_BY_NODE = new Map();
const IDENTITY_MEMBERS_BY_COMPONENT = new Map();

function ensureIdentityNode(kind, name) {
  if (!name) return;
  var node = identityNode(kind, name);
  if (!IDENTITY_GRAPH.has(node)) IDENTITY_GRAPH.set(node, new Set());
}

function connectIdentityNodes(aKind, aName, bKind, bName) {
  if (!aName || !bName) return;
  var a = identityNode(aKind, aName);
  var b = identityNode(bKind, bName);
  ensureIdentityNode(aKind, aName);
  ensureIdentityNode(bKind, bName);
  if (a === b) return;
  IDENTITY_GRAPH.get(a).add(b);
  IDENTITY_GRAPH.get(b).add(a);
}

(function buildIdentityGraph() {
  Object.keys(DATA.authors || {}).forEach(function(username) {
    ensureIdentityNode('eth', username);
  });
  Object.values(DATA.topics || {}).forEach(function(t) {
    if (t && t.a) ensureIdentityNode('eth', t.a);
    (t && t.coauth ? t.coauth : []).forEach(function(username) {
      if (username) ensureIdentityNode('eth', username);
    });
    (t && t.parts ? t.parts : []).forEach(function(username) {
      if (username) ensureIdentityNode('eth', username);
    });
  });
  Object.keys(DATA.eipAuthors || {}).forEach(function(name) {
    ensureIdentityNode('eip', name);
  });
  Object.values(DATA.magiciansTopics || {}).forEach(function(mt) {
    if (mt && mt.a) ensureIdentityNode('mag', mt.a);
  });

  Object.entries(ETH_TO_EIP_AUTHORS).forEach(function(entry) {
    var username = entry[0];
    (entry[1] || []).forEach(function(name) {
      connectIdentityNodes('eth', username, 'eip', name);
    });
  });
  Object.entries(MAG_TO_ETH_AUTHORS).forEach(function(entry) {
    var handle = entry[0];
    (entry[1] || []).forEach(function(username) {
      connectIdentityNodes('mag', handle, 'eth', username);
    });
  });
  Object.entries(MAG_TO_EIP_AUTHORS).forEach(function(entry) {
    var handle = entry[0];
    (entry[1] || []).forEach(function(name) {
      connectIdentityNodes('mag', handle, 'eip', name);
    });
  });
})();

(function buildIdentityComponents() {
  var compIndex = 0;
  IDENTITY_GRAPH.forEach(function(_edges, startNode) {
    if (IDENTITY_COMPONENT_BY_NODE.has(startNode)) return;
    compIndex += 1;
    var compId = 'idc' + String(compIndex);
    var members = {eth: new Set(), eip: new Set(), mag: new Set()};
    var stack = [startNode];
    IDENTITY_COMPONENT_BY_NODE.set(startNode, compId);
    while (stack.length > 0) {
      var node = stack.pop();
      var parsed = parseIdentityNode(node);
      if (members[parsed.kind]) members[parsed.kind].add(parsed.name);
      var neighbors = IDENTITY_GRAPH.get(node) || new Set();
      neighbors.forEach(function(nextNode) {
        if (!IDENTITY_COMPONENT_BY_NODE.has(nextNode)) {
          IDENTITY_COMPONENT_BY_NODE.set(nextNode, compId);
          stack.push(nextNode);
        }
      });
    }
    IDENTITY_MEMBERS_BY_COMPONENT.set(compId, members);
  });
})();

function identityMembers(kind, name) {
  var empty = {eth: [], eip: [], mag: []};
  if (!name) return empty;
  var node = identityNode(kind, name);
  if (!IDENTITY_GRAPH.has(node)) {
    var fallback = {eth: [], eip: [], mag: []};
    if (fallback[kind]) fallback[kind] = [String(name)];
    return fallback;
  }
  var compId = IDENTITY_COMPONENT_BY_NODE.get(node);
  if (!compId) {
    var lonely = {eth: [], eip: [], mag: []};
    if (lonely[kind]) lonely[kind] = [String(name)];
    return lonely;
  }
  var members = IDENTITY_MEMBERS_BY_COMPONENT.get(compId);
  if (!members) return empty;
  return {
    eth: sortedSetValues(members.eth),
    eip: sortedSetValues(members.eip),
    mag: sortedSetValues(members.mag)
  };
}

function linkedEipAuthors(username) {
  return identityMembers('eth', username).eip;
}

function linkedEthAuthors(eipAuthorName) {
  return identityMembers('eip', canonicalEipAuthorName(eipAuthorName)).eth;
}

function linkedEthAuthorsFromMag(magAuthor) {
  return identityMembers('mag', magAuthor).eth;
}

function linkedEipAuthorsFromMag(magAuthor) {
  return identityMembers('mag', magAuthor).eip;
}

function linkedMagAuthorsFromEth(username) {
  return identityMembers('eth', username).mag;
}

function linkedMagAuthorsFromEip(eipAuthorName) {
  return identityMembers('eip', canonicalEipAuthorName(eipAuthorName)).mag;
}

const PAPER_MATCH_MODES = {
  strict: {
    label: 'strict',
    limit: 12,
    relevanceWeight: 0.75,
    minTopic: 3.9,
    minEip: 4.5,
    minFork: 3.9,
    minAuthor: 3.8,
    minEipAuthor: 3.8,
  },
  balanced: {
    label: 'balanced',
    limit: 18,
    relevanceWeight: 1.0,
    minTopic: 2.9,
    minEip: 3.4,
    minFork: 3.0,
    minAuthor: 3.0,
    minEipAuthor: 3.0,
  },
  loose: {
    label: 'loose',
    limit: 28,
    relevanceWeight: 1.2,
    minTopic: 2.1,
    minEip: 2.6,
    minFork: 2.3,
    minAuthor: 2.2,
    minEipAuthor: 2.2,
  },
};

function getPaperMatchConfig() {
  return PAPER_MATCH_MODES[paperMatchMode] || PAPER_MATCH_MODES.balanced;
}

function clearRelatedPapersCache() {
  Object.keys(RELATED_PAPERS_CACHE).forEach(function(kind) {
    RELATED_PAPERS_CACHE[kind] = {};
  });
}

function refreshOpenDetailPanel() {
  var panel = document.getElementById('detail-panel');
  if (!panel || !panel.classList.contains('open')) return;

  if (pinnedTopicId && DATA.topics[pinnedTopicId]) {
    showDetail(DATA.topics[pinnedTopicId]);
    return;
  }
  if (activeEipNum !== null && activeEipNum !== undefined) {
    showEipDetailByNum(activeEipNum);
    return;
  }
  if (activeMagiciansId !== null && activeMagiciansId !== undefined) {
    showMagiciansTopicDetailById(activeMagiciansId);
    return;
  }
  if (activePaperId) {
    var activePaper = (DATA.papers || {})[String(activePaperId)];
    if (activePaper) {
      showPaperDetail(activePaper, null);
      return;
    }
  }
  if (activeEipAuthor) {
    showEipAuthorDetail(activeEipAuthor);
    return;
  }
  if (activeAuthor) {
    showAuthorDetail(activeAuthor);
  }
}

function updatePaperMatchToggleUi() {
  var btn = document.getElementById('paper-match-toggle');
  if (!btn) return;
  var mode = paperMatchMode || 'balanced';
  btn.textContent = 'Papers: ' + mode;
  btn.classList.remove('mode-strict', 'mode-loose');
  if (mode === 'strict') btn.classList.add('mode-strict');
  if (mode === 'loose') btn.classList.add('mode-loose');
}

function setPaperMatchMode(mode, persist) {
  var next = PAPER_MATCH_MODES[mode] ? mode : 'balanced';
  if (paperMatchMode === next) {
    updatePaperMatchToggleUi();
    return;
  }
  paperMatchMode = next;
  clearRelatedPapersCache();
  updatePaperMatchToggleUi();
  if (persist !== false) {
    try { localStorage.setItem('evmap.paperMatchMode', next); } catch (e) {}
  }
  refreshOpenDetailPanel();
  if (showPapers) {
    var netSvg = document.querySelector('#network-view svg');
    if (activeView === 'network') {
      if (netSvg) { netSvg.remove(); simulation = null; }
      buildNetwork();
    } else if (netSvg) {
      netSvg.remove();
      simulation = null;
    }
  }
}

function cyclePaperMatchMode() {
  var order = ['strict', 'balanced', 'loose'];
  var idx = order.indexOf(paperMatchMode);
  if (idx < 0) idx = 1;
  var next = order[(idx + 1) % order.length];
  setPaperMatchMode(next, true);
}

function setupPaperMatchMode() {
  var mode = 'balanced';
  try {
    var saved = localStorage.getItem('evmap.paperMatchMode');
    if (saved && PAPER_MATCH_MODES[saved]) mode = saved;
  } catch (e) {}
  paperMatchMode = mode;
  updatePaperMatchToggleUi();
}

const THREAD_PAPER_TAG_HINTS = {
  pos_casper: ['consensus', 'proof-of-stake', 'finality'],
  sharding_da: ['rollups_da', 'data-availability', 'ethereum'],
  plasma_l2: ['rollups_da', 'ethereum'],
  fee_markets: ['defi_markets', 'fee-market', 'ethereum'],
  pbs_mev: ['mev_pbs', 'defi_markets', 'ethereum'],
  ssf: ['consensus', 'proof-of-stake', 'ethereum'],
  issuance_economics: ['defi_markets', 'economics', 'ethereum'],
  inclusion_lists: ['mev_pbs', 'consensus', 'ethereum'],
  based_preconf: ['mev_pbs', 'consensus', 'ethereum'],
  zk_proofs: ['zk', 'rollups_da', 'ethereum'],
  state_execution: ['execution_state', 'ethereum'],
  privacy_identity: ['zk', 'execution_state', 'ethereum']
};

const PAPER_STOPWORDS = new Set([
  'the', 'and', 'for', 'with', 'from', 'into', 'towards', 'toward', 'under',
  'over', 'through', 'between', 'about', 'using', 'use', 'via', 'of', 'on',
  'in', 'to', 'a', 'an', 'by', 'is', 'are', 'be', 'or', 'as', 'at', 'that',
  'this', 'these', 'those', 'it', 'its', 'their', 'our', 'we', 'can', 'will',
  'new', 'study', 'analysis', 'approach', 'model', 'based', 'blockchain'
]);

const PAPER_LIST = Object.values(DATA.papers || {});

function paperYearValue(paper) {
  var y = Number((paper || {}).y || 0);
  if (!isFinite(y) || y <= 0) return null;
  return y;
}

function paperCitationValue(paper) {
  var c = Number((paper || {}).cb || 0);
  if (!isFinite(c) || c < 0) return 0;
  return c;
}

function paperPassesSidebarFilters(paper) {
  if (!paper) return false;
  var year = paperYearValue(paper);
  if (paperFilterYearMin !== null && year !== null && year < paperFilterYearMin) return false;
  if (paperFilterYearMax !== null && year !== null && year > paperFilterYearMax) return false;
  if (paperFilterMinCitations > 0 && paperCitationValue(paper) < paperFilterMinCitations) return false;
  if (paperFilterTag) {
    var tags = (paper.tg || []).map(function(t) { return String(t); });
    if (tags.indexOf(paperFilterTag) < 0) return false;
  }
  return true;
}

function paperSidebarRankScore(paper) {
  var rel = Number((paper || {}).rs || 0);
  var cites = paperCitationValue(paper);
  var year = paperYearValue(paper) || 0;
  if (paperSidebarSort === 'citations') return cites * 100 + rel * 10 + year * 0.001;
  if (paperSidebarSort === 'recent') return year * 100 + rel * 10 + Math.log1p(cites);
  return rel * 160 + Math.log1p(cites) * 18 + year * 0.01;
}

function filteredAndSortedPapersForSidebar() {
  var rows = PAPER_LIST.filter(function(p) { return paperPassesSidebarFilters(p); });
  rows.sort(function(a, b) {
    var diff = paperSidebarRankScore(b) - paperSidebarRankScore(a);
    if (diff !== 0) return diff;
    return String(a.t || '').localeCompare(String(b.t || ''));
  });
  return rows;
}

function renderPaperSidebarList() {
  var listEl = document.getElementById('paper-sidebar-list');
  var summaryEl = document.getElementById('paper-sidebar-summary');
  if (!listEl || !summaryEl) return;
  var rows = filteredAndSortedPapersForSidebar();
  var total = PAPER_LIST.length;
  summaryEl.textContent = rows.length + ' / ' + total + ' papers';
  var topRows = rows.slice(0, 40);
  listEl.innerHTML = topRows.map(function(paper) {
    var title = escHtml(paper.t || 'Untitled paper');
    var year = paperYearValue(paper);
    var cites = paperCitationValue(paper);
    var rel = Number((paper || {}).rs || 0);
    var authors = paperAuthorsShort(paper, 2);
    var metaParts = [];
    if (year) metaParts.push(String(year));
    if (authors) metaParts.push(authors);
    metaParts.push('OpenAlex cites ' + cites.toLocaleString());
    metaParts.push('rel ' + rel.toFixed(2));
    return '<div class="paper-sidebar-item" data-paper-id="' + escHtml(String(paper.id || '')) + '">' +
      '<div class="paper-title">' + title + '</div>' +
      '<div class="paper-meta">' + escHtml(metaParts.join(' - ')) + '</div>' +
      '</div>';
  }).join('');
  listEl.querySelectorAll('.paper-sidebar-item').forEach(function(el) {
    el.addEventListener('click', function() {
      var pid = el.getAttribute('data-paper-id') || '';
      var paper = (DATA.papers || {})[pid];
      if (!paper) return;
      if (!showPapers) toggleContent('papers', 'on');
      showPaperDetail(paper, null);
    });
  });
}

function refreshNetworkForPaperFilterChange() {
  var netSvg = document.querySelector('#network-view svg');
  if (netSvg) {
    netSvg.remove();
    simulation = null;
  }
  if (activeView === 'network') buildNetwork();
}

function applyPaperSidebarFilters(refreshNetwork) {
  clearRelatedPapersCache();
  renderPaperSidebarList();
  refreshOpenDetailPanel();
  if (refreshNetwork !== false) refreshNetworkForPaperFilterChange();
  applyFilters();
}

function setupPaperSidebarPanel() {
  var minYearInput = document.getElementById('paper-year-min');
  var maxYearInput = document.getElementById('paper-year-max');
  var minCitesInput = document.getElementById('paper-min-cites');
  var minCitesLabel = document.getElementById('paper-min-cites-label');
  var tagSelect = document.getElementById('paper-tag-filter');
  var sortSelect = document.getElementById('paper-sort-filter');
  var resetBtn = document.getElementById('paper-filter-reset');
  if (!minYearInput || !maxYearInput || !minCitesInput || !minCitesLabel || !tagSelect || !sortSelect || !resetBtn) return;

  var years = PAPER_LIST.map(function(p) { return paperYearValue(p); }).filter(function(y) { return y !== null; });
  var minYear = years.length > 0 ? d3.min(years) : 2014;
  var maxYear = years.length > 0 ? d3.max(years) : (new Date().getFullYear());
  minYearInput.min = String(minYear);
  minYearInput.max = String(maxYear);
  maxYearInput.min = String(minYear);
  maxYearInput.max = String(maxYear);
  minYearInput.value = String(minYear);
  maxYearInput.value = String(maxYear);
  paperFilterYearMin = minYear;
  paperFilterYearMax = maxYear;

  var maxCites = d3.max(PAPER_LIST, function(p) { return paperCitationValue(p); }) || 0;
  var sliderMax = Math.max(50, Math.ceil(maxCites / 50) * 50);
  minCitesInput.min = '0';
  minCitesInput.max = String(sliderMax);
  minCitesInput.value = '0';
  paperFilterMinCitations = 0;
  minCitesLabel.textContent = '0';

  var tagCounts = {};
  PAPER_LIST.forEach(function(paper) {
    (paper.tg || []).forEach(function(tag) {
      var key = String(tag || '').trim();
      if (!key) return;
      tagCounts[key] = (tagCounts[key] || 0) + 1;
    });
  });
  var tagEntries = Object.entries(tagCounts).sort(function(a, b) {
    if (b[1] !== a[1]) return b[1] - a[1];
    return a[0].localeCompare(b[0]);
  });
  tagSelect.innerHTML = '<option value="">All tags</option>' + tagEntries.slice(0, 40).map(function(entry) {
    return '<option value="' + escHtml(entry[0]) + '">' + escHtml(entry[0] + ' (' + entry[1] + ')') + '</option>';
  }).join('');
  paperFilterTag = '';

  sortSelect.value = paperSidebarSort;

  function commitYearFilters() {
    var minVal = Number(minYearInput.value || minYear);
    var maxVal = Number(maxYearInput.value || maxYear);
    if (!isFinite(minVal)) minVal = minYear;
    if (!isFinite(maxVal)) maxVal = maxYear;
    minVal = Math.max(minYear, Math.min(maxYear, Math.round(minVal)));
    maxVal = Math.max(minYear, Math.min(maxYear, Math.round(maxVal)));
    if (minVal > maxVal) {
      var swap = minVal;
      minVal = maxVal;
      maxVal = swap;
    }
    minYearInput.value = String(minVal);
    maxYearInput.value = String(maxVal);
    paperFilterYearMin = minVal;
    paperFilterYearMax = maxVal;
    applyPaperSidebarFilters(true);
  }

  minYearInput.addEventListener('change', commitYearFilters);
  maxYearInput.addEventListener('change', commitYearFilters);

  minCitesInput.addEventListener('input', function() {
    minCitesLabel.textContent = String(Math.round(Number(minCitesInput.value || 0)));
  });
  minCitesInput.addEventListener('change', function() {
    paperFilterMinCitations = Math.max(0, Math.round(Number(minCitesInput.value || 0)));
    minCitesLabel.textContent = String(paperFilterMinCitations);
    applyPaperSidebarFilters(true);
  });

  tagSelect.addEventListener('change', function() {
    paperFilterTag = String(tagSelect.value || '');
    applyPaperSidebarFilters(true);
  });

  sortSelect.addEventListener('change', function() {
    paperSidebarSort = String(sortSelect.value || 'relevance');
    renderPaperSidebarList();
  });

  resetBtn.addEventListener('click', function() {
    minYearInput.value = String(minYear);
    maxYearInput.value = String(maxYear);
    minCitesInput.value = '0';
    minCitesLabel.textContent = '0';
    tagSelect.value = '';
    paperFilterYearMin = minYear;
    paperFilterYearMax = maxYear;
    paperFilterMinCitations = 0;
    paperFilterTag = '';
    applyPaperSidebarFilters(true);
  });

  renderPaperSidebarList();
}

function normalizeSearchText(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function tokenizeSearchText(value) {
  var norm = normalizeSearchText(value);
  if (!norm) return [];
  return norm.split(/\s+/).filter(Boolean);
}

function keywordTokenList(value) {
  return tokenizeSearchText(value).filter(function(tok) {
    return tok.length >= 3 && !PAPER_STOPWORDS.has(tok);
  });
}

function uniqueSortedNumbers(values) {
  var out = [];
  var seen = new Set();
  (values || []).forEach(function(v) {
    var n = Number(v);
    if (!isFinite(n) || n <= 0) return;
    if (seen.has(n)) return;
    seen.add(n);
    out.push(n);
  });
  out.sort(function(a, b) { return a - b; });
  return out;
}

function setOverlapArray(aSet, bSet) {
  var out = [];
  if (!aSet || !bSet) return out;
  aSet.forEach(function(v) {
    if (bSet.has(v)) out.push(v);
  });
  out.sort(function(a, b) {
    if (typeof a === 'number' && typeof b === 'number') return a - b;
    return String(a).localeCompare(String(b));
  });
  return out;
}

function setIntersectionCount(aSet, bSet) {
  if (!aSet || !bSet || aSet.size === 0 || bSet.size === 0) return 0;
  var small = aSet.size <= bSet.size ? aSet : bSet;
  var big = aSet.size <= bSet.size ? bSet : aSet;
  var count = 0;
  small.forEach(function(v) {
    if (big.has(v)) count += 1;
  });
  return count;
}

function buildAliasRows(names) {
  var out = [];
  var seen = new Set();
  (names || []).forEach(function(name) {
    var raw = String(name || '').trim();
    if (!raw) return;
    var norm = normalizeIdentityToken(raw);
    if (!norm || seen.has(norm)) return;
    seen.add(norm);
    out.push({
      raw: raw,
      norm: norm,
      tokens: keywordTokenList(raw),
    });
  });
  return out;
}

function scoreAuthorAliasMatch(aliasRow, paperAuthorRow) {
  if (!aliasRow || !paperAuthorRow) return 0;
  if (aliasRow.norm === paperAuthorRow.norm) return 4.2;
  if (!aliasRow.norm || !paperAuthorRow.norm) return 0;

  var aliasTokens = aliasRow.tokens || [];
  var paperTokens = paperAuthorRow.tokens || [];

  if (aliasTokens.length >= 2 && paperTokens.length >= 2) {
    var aFirst = aliasTokens[0];
    var aLast = aliasTokens[aliasTokens.length - 1];
    var pFirst = paperTokens[0];
    var pLast = paperTokens[paperTokens.length - 1];
    if (aLast && pLast && aLast === pLast) {
      if (aFirst === pFirst) return 3.9;
      if (aFirst && pFirst && aFirst[0] === pFirst[0]) return 3.3;
      return 2.4;
    }
    if (aFirst && pFirst && aFirst === pFirst && aLast && pLast && (aLast.indexOf(pLast) === 0 || pLast.indexOf(aLast) === 0)) {
      return 2.8;
    }
  }

  if (aliasRow.norm.length >= 6 && paperAuthorRow.norm.indexOf(aliasRow.norm) >= 0) return 2.4;
  if (paperAuthorRow.norm.length >= 6 && aliasRow.norm.indexOf(paperAuthorRow.norm) >= 0) return 2.2;

  if (aliasTokens.length === 1 && aliasTokens[0].length >= 5 && paperAuthorRow.norm.indexOf(aliasTokens[0]) >= 0) return 1.8;
  return 0;
}

function bestAliasMatch(aliasRows, paperAuthorRows) {
  var best = {score: 0, alias: null, paperAuthor: null};
  (aliasRows || []).forEach(function(aliasRow) {
    (paperAuthorRows || []).forEach(function(authorRow) {
      var score = scoreAuthorAliasMatch(aliasRow, authorRow);
      if (score > best.score) {
        best = {score: score, alias: aliasRow.raw, paperAuthor: authorRow.raw};
      }
    });
  });
  return best;
}

function threadPaperTags(threadId) {
  return THREAD_PAPER_TAG_HINTS[threadId] || [];
}

const PAPER_INDEX = (function() {
  return PAPER_LIST.map(function(p) {
    var title = p.t || '';
    var tagSet = new Set((p.tg || []).map(function(tag) { return String(tag).toLowerCase(); }));
    var eipSet = new Set(uniqueSortedNumbers(p.eq || []));
    var authorRows = (p.a || []).map(function(name) {
      return {
        raw: String(name || ''),
        norm: normalizeIdentityToken(name || ''),
        tokens: keywordTokenList(name || ''),
      };
    }).filter(function(row) { return row.norm; });

    return {
      p: p,
      titleNorm: normalizeSearchText(title),
      titleTokenSet: new Set(keywordTokenList(title)),
      tagSet: tagSet,
      eipSet: eipSet,
      authorRows: authorRows,
      relevance: Number(p.rs || 0),
      citedBy: Number(p.cb || 0),
    };
  }).sort(function(a, b) {
    var rs = (b.relevance || 0) - (a.relevance || 0);
    if (rs !== 0) return rs;
    var cb = (b.citedBy || 0) - (a.citedBy || 0);
    if (cb !== 0) return cb;
    return String((a.p || {}).t || '').localeCompare(String((b.p || {}).t || ''));
  });
})();

const PAPER_INDEX_BY_ID = {};
const EIP_TO_PAPER_IDS = {};
const PAPER_TO_EIP_IDS = {};
const PAPER_TO_TOPIC_IDS = {};
const PAPER_TO_MAGICIANS_IDS = {};
const PAPER_TO_PAPER_IDS = {};
const TOPIC_TITLE_TOKEN_SET = {};
const TOPIC_TAG_SET = {};
const TOPIC_EIP_SET = {};
const TOPIC_IDS_BY_THREAD = {};
const TOPIC_IDS_BY_TITLE_TOKEN = {};
const TOPIC_TO_MAG_IDS = {};

(function buildPaperTopicIndices() {
  Object.values(DATA.topics || {}).forEach(function(topic) {
    if (!topic || topic.id === undefined || topic.id === null) return;
    var tid = Number(topic.id);
    if (!isFinite(tid)) return;

    var titleTokens = new Set(keywordTokenList(topic.t || ''));
    TOPIC_TITLE_TOKEN_SET[tid] = titleTokens;
    titleTokens.forEach(function(tok) {
      if (!TOPIC_IDS_BY_TITLE_TOKEN[tok]) TOPIC_IDS_BY_TITLE_TOKEN[tok] = [];
      TOPIC_IDS_BY_TITLE_TOKEN[tok].push(tid);
    });

    var tagSet = new Set((topic.tg || []).map(function(tag) {
      return String(tag || '').toLowerCase();
    }).filter(Boolean));
    TOPIC_TAG_SET[tid] = tagSet;

    TOPIC_EIP_SET[tid] = new Set(uniqueSortedNumbers((topic.eips || []).concat(topic.peips || [])));

    var th = topic.th || '_other';
    if (!TOPIC_IDS_BY_THREAD[th]) TOPIC_IDS_BY_THREAD[th] = [];
    TOPIC_IDS_BY_THREAD[th].push(tid);
  });

  Object.keys(TOPIC_IDS_BY_TITLE_TOKEN).forEach(function(tok) {
    TOPIC_IDS_BY_TITLE_TOKEN[tok].sort(function(a, b) {
      var ta = DATA.topics[a] || {};
      var tb = DATA.topics[b] || {};
      return Number(tb.inf || 0) - Number(ta.inf || 0);
    });
  });

  Object.keys(TOPIC_IDS_BY_THREAD).forEach(function(th) {
    TOPIC_IDS_BY_THREAD[th].sort(function(a, b) {
      var ta = DATA.topics[a] || {};
      var tb = DATA.topics[b] || {};
      return Number(tb.inf || 0) - Number(ta.inf || 0);
    });
  });

  Object.entries(DATA.magiciansTopics || {}).forEach(function(entry) {
    var mid = Number(entry[0]);
    if (!isFinite(mid)) return;
    var mt = entry[1] || {};
    (mt.er || []).forEach(function(tidRaw) {
      var tid = Number(tidRaw);
      if (!isFinite(tid)) return;
      if (!TOPIC_TO_MAG_IDS[tid]) TOPIC_TO_MAG_IDS[tid] = new Set();
      TOPIC_TO_MAG_IDS[tid].add(mid);
    });
  });
})();

function paperPairMeta(paperId, paperObj) {
  var pid = String(paperId || '').trim();
  var paper = paperObj || (DATA.papers || {})[pid] || {};
  return {
    eipSet: new Set(PAPER_TO_EIP_IDS[pid] || uniqueSortedNumbers(paper.eq || [])),
    topicSet: new Set(PAPER_TO_TOPIC_IDS[pid] || []),
    tagSet: new Set((paper.tg || []).map(function(t) { return String(t || '').toLowerCase(); }).filter(Boolean)),
    authorSet: new Set((paper.a || []).map(function(a) { return normalizeIdentityToken(a); }).filter(Boolean)),
    titleTokenSet: new Set(keywordTokenList(paper.t || '')),
    thread: inferPaperThread(paper),
    year: Number(paper.y || 0),
  };
}

function paperPairSimilarity(metaA, metaB) {
  var score = 0;
  var reasons = [];

  var sharedEips = setIntersectionCount(metaA.eipSet, metaB.eipSet);
  if (sharedEips > 0) {
    score += 2.2 + Math.min(2.1, (sharedEips - 1) * 0.8);
    reasons.push('shared EIP');
  }

  var sharedTopics = setIntersectionCount(metaA.topicSet, metaB.topicSet);
  if (sharedTopics > 0) {
    score += 1.35 + Math.min(1.7, (sharedTopics - 1) * 0.45);
    reasons.push('shared topic');
  }

  var sharedAuthors = setIntersectionCount(metaA.authorSet, metaB.authorSet);
  if (sharedAuthors > 0) {
    score += 2.0 + Math.min(1.4, (sharedAuthors - 1) * 0.45);
    reasons.push('shared author');
  }

  var sharedTags = setIntersectionCount(metaA.tagSet, metaB.tagSet);
  if (sharedTags >= 2) {
    score += 1.0 + Math.min(0.9, (sharedTags - 2) * 0.2);
    reasons.push('shared tags');
  } else if (sharedTags === 1) {
    score += 0.35;
  }

  var sharedTitleTokens = setIntersectionCount(metaA.titleTokenSet, metaB.titleTokenSet);
  if (sharedTitleTokens >= 2) score += Math.min(0.8, 0.3 + (sharedTitleTokens - 2) * 0.1);

  if (metaA.thread && metaB.thread && metaA.thread === metaB.thread) score += 0.45;
  if (metaA.year > 0 && metaB.year > 0 && Math.abs(metaA.year - metaB.year) <= 2) score += 0.2;

  return {
    score: Number(score.toFixed(3)),
    reason: reasons.join(' + ') || 'paper similarity',
  };
}

function buildPaperPairRows(paperRows, options) {
  var opts = options || {};
  var candidateMin = Math.max(0, Number(opts.candidateMin || 1.15));
  var minScore = Math.max(candidateMin, Number(opts.minScore || 2.0));
  var limit = Math.max(0, Number(opts.limit || 0));
  var ensurePerPaper = Math.max(0, Number(opts.ensurePerPaper || 0));
  var extraBudget = Math.max(0, Number(opts.extraBudget || 0));

  var rows = (paperRows || []).filter(function(row) {
    return !!(row && row.id);
  }).map(function(row) {
    var pid = String(row.id || '').trim();
    var paper = row.paper || (DATA.papers || {})[pid] || {};
    return {
      id: pid,
      paper: paper,
      date: row.date || null,
      yPos: row.yPos,
      meta: row.meta || paperPairMeta(pid, paper),
    };
  });

  var candidates = [];
  for (var i = 0; i < rows.length; i++) {
    for (var j = i + 1; j < rows.length; j++) {
      var a = rows[i];
      var b = rows[j];
      var sim = paperPairSimilarity(a.meta, b.meta);
      if (sim.score < candidateMin) continue;
      candidates.push({
        key: a.id < b.id ? (a.id + '|' + b.id) : (b.id + '|' + a.id),
        paperA: a.id,
        paperB: b.id,
        paperDateA: a.date,
        paperDateB: b.date,
        paperYA: a.yPos,
        paperYB: b.yPos,
        score: sim.score,
        reason: sim.reason,
      });
    }
  }

  candidates.sort(function(a, b) {
    if (Number(b.score || 0) !== Number(a.score || 0)) return Number(b.score || 0) - Number(a.score || 0);
    return String(a.key || '').localeCompare(String(b.key || ''));
  });

  var selected = [];
  var maxInitial = limit > 0 ? limit : candidates.length;
  for (var c = 0; c < candidates.length && selected.length < maxInitial; c++) {
    if (Number(candidates[c].score || 0) < minScore) continue;
    selected.push(candidates[c]);
  }

  if (ensurePerPaper > 0 && rows.length > 0 && candidates.length > 0) {
    var degree = {};
    rows.forEach(function(row) { degree[row.id] = 0; });
    selected.forEach(function(ed) {
      degree[ed.paperA] = (degree[ed.paperA] || 0) + 1;
      degree[ed.paperB] = (degree[ed.paperB] || 0) + 1;
    });
    var selectedKeys = new Set(selected.map(function(ed) { return ed.key; }));
    var unresolved = function() {
      return rows.some(function(row) { return (degree[row.id] || 0) < ensurePerPaper; });
    };
    for (var k = 0; k < candidates.length && unresolved(); k++) {
      if (extraBudget <= 0) break;
      var edge = candidates[k];
      if (selectedKeys.has(edge.key)) continue;
      var leftNeeds = (degree[edge.paperA] || 0) < ensurePerPaper;
      var rightNeeds = (degree[edge.paperB] || 0) < ensurePerPaper;
      if (!leftNeeds && !rightNeeds) continue;
      if (Number(edge.score || 0) < candidateMin) continue;
      selected.push(edge);
      selectedKeys.add(edge.key);
      degree[edge.paperA] = (degree[edge.paperA] || 0) + 1;
      degree[edge.paperB] = (degree[edge.paperB] || 0) + 1;
      extraBudget -= 1;
    }
  }

  return selected;
}

(function buildPaperRelationIndices() {
  PAPER_INDEX.forEach(function(pidx) {
    var p = pidx && pidx.p ? pidx.p : null;
    if (!p) return;
    var pid = String(p.id || '').trim();
    if (!pid) return;
    PAPER_INDEX_BY_ID[pid] = pidx;

    var eips = uniqueSortedNumbers(p.eq || []);
    PAPER_TO_EIP_IDS[pid] = eips;

    var topicSet = new Set();
    var magSet = new Set();
    var paperEipSet = new Set(eips);
    eips.forEach(function(num) {
      var eipKey = String(num);
      if (!EIP_TO_PAPER_IDS[eipKey]) EIP_TO_PAPER_IDS[eipKey] = new Set();
      EIP_TO_PAPER_IDS[eipKey].add(pid);

      (eipToTopicIds[eipKey] || []).forEach(function(tid) { topicSet.add(Number(tid)); });
      (eipToMagiciansRefs[eipKey] || new Set()).forEach(function(mid) { magSet.add(Number(mid)); });
      var eMeta = (DATA.eipCatalog || {})[eipKey] || {};
      if (eMeta.mt !== undefined && eMeta.mt !== null && !isNaN(Number(eMeta.mt))) {
        magSet.add(Number(eMeta.mt));
      }
    });

    // Expand paper-to-topic links beyond explicit EIP refs so papers without direct EIP
    // citations still anchor to the most relevant research lanes.
    var titleTokenSet = new Set(keywordTokenList(p.t || ''));
    var paperTagSet = new Set((p.tg || []).map(function(tag) {
      return String(tag || '').toLowerCase();
    }).filter(Boolean));
    var threadCounts = {};
    topicSet.forEach(function(tid) {
      var topic = DATA.topics[tid];
      if (!topic || !topic.th) return;
      threadCounts[topic.th] = (threadCounts[topic.th] || 0) + 2;
    });
    eips.forEach(function(num) {
      var eMeta = (DATA.eipCatalog || {})[String(num)];
      if (!eMeta || !eMeta.th) return;
      threadCounts[eMeta.th] = (threadCounts[eMeta.th] || 0) + 1;
    });
    Object.entries(THREAD_PAPER_TAG_HINTS || {}).forEach(function(entry) {
      var th = entry[0];
      var tags = entry[1] || [];
      var matched = tags.some(function(tag) {
        return paperTagSet.has(String(tag || '').toLowerCase());
      });
      if (matched) threadCounts[th] = (threadCounts[th] || 0) + 1;
    });
    var paperThread = null;
    var bestThreadCount = 0;
    Object.keys(threadCounts).forEach(function(th) {
      if (threadCounts[th] > bestThreadCount) {
        bestThreadCount = threadCounts[th];
        paperThread = th;
      }
    });
    var candidateTopicIds = new Set(Array.from(topicSet));

    if (paperThread && TOPIC_IDS_BY_THREAD[paperThread]) {
      TOPIC_IDS_BY_THREAD[paperThread].slice(0, 140).forEach(function(tid) {
        candidateTopicIds.add(Number(tid));
      });
    }
    titleTokenSet.forEach(function(tok) {
      (TOPIC_IDS_BY_TITLE_TOKEN[tok] || []).slice(0, 40).forEach(function(tid) {
        candidateTopicIds.add(Number(tid));
      });
    });

    var scoredTopics = [];
    candidateTopicIds.forEach(function(tid) {
      var topic = DATA.topics[tid];
      if (!topic) return;
      var score = 0;

      var topicEipSet = TOPIC_EIP_SET[tid] || new Set();
      var sharedEips = setIntersectionCount(paperEipSet, topicEipSet);
      if (sharedEips > 0) score += 2.2 + Math.min(1.6, (sharedEips - 1) * 0.7);

      if (paperThread && topic.th === paperThread) score += 1.05;

      var topicTitleTokenSet = TOPIC_TITLE_TOKEN_SET[tid] || new Set();
      var titleOverlap = setIntersectionCount(titleTokenSet, topicTitleTokenSet);
      if (titleOverlap > 0) score += Math.min(1.45, 0.45 * titleOverlap);

      var topicTagSet = TOPIC_TAG_SET[tid] || new Set();
      var tagOverlap = setIntersectionCount(paperTagSet, topicTagSet);
      if (tagOverlap > 0) score += Math.min(1.05, 0.45 + tagOverlap * 0.22);

      score += Math.min(0.45, Math.max(0, Number(topic.inf || 0)) / 220);
      if (topic.mn) score -= 0.2;

      var minScore = eips.length > 0 ? 1.2 : 1.6;
      if (score < minScore) return;
      scoredTopics.push({tid: Number(tid), score: Number(score.toFixed(3))});
    });

    scoredTopics.sort(function(a, b) {
      if (b.score !== a.score) return b.score - a.score;
      var ta = DATA.topics[a.tid] || {};
      var tb = DATA.topics[b.tid] || {};
      return Number(tb.inf || 0) - Number(ta.inf || 0);
    });

    var augmentBudget = eips.length > 0 ? 6 : 8;
    for (var i = 0; i < scoredTopics.length && augmentBudget > 0; i++) {
      var tid = Number(scoredTopics[i].tid);
      if (topicSet.has(tid)) continue;
      topicSet.add(tid);
      augmentBudget -= 1;
    }

    if (topicSet.size === 0 && paperThread && TOPIC_IDS_BY_THREAD[paperThread]) {
      TOPIC_IDS_BY_THREAD[paperThread].slice(0, 3).forEach(function(tid) {
        topicSet.add(Number(tid));
      });
    }

    topicSet.forEach(function(tid) {
      (TOPIC_TO_MAG_IDS[tid] || new Set()).forEach(function(mid) {
        magSet.add(Number(mid));
      });
    });

    PAPER_TO_TOPIC_IDS[pid] = Array.from(topicSet).sort(function(a, b) {
      var ta = DATA.topics[a] || {};
      var tb = DATA.topics[b] || {};
      return Number(tb.inf || 0) - Number(ta.inf || 0);
    });
    PAPER_TO_MAGICIANS_IDS[pid] = Array.from(magSet);
  });
})();

(function buildPaperPeerIndex() {
  var rows = buildPaperPairRows(PAPER_LIST.map(function(paper) {
    var pid = String((paper && paper.id) || '').trim();
    if (!pid) return null;
    return {
      id: pid,
      paper: paper,
      meta: paperPairMeta(pid, paper),
    };
  }).filter(Boolean), {
    candidateMin: 1.2,
    minScore: 1.95,
    limit: 280,
    ensurePerPaper: 1,
    extraBudget: 80,
  });

  var bucket = {};
  function add(a, b, score) {
    if (!a || !b) return;
    if (!bucket[a]) bucket[a] = {};
    var prev = Number(bucket[a][b] || 0);
    if (score > prev) bucket[a][b] = score;
  }

  rows.forEach(function(ed) {
    if (!ed) return;
    var a = String(ed.paperA || '').trim();
    var b = String(ed.paperB || '').trim();
    var score = Number(ed.score || 0);
    add(a, b, score);
    add(b, a, score);
  });

  Object.keys(bucket).forEach(function(pid) {
    PAPER_TO_PAPER_IDS[pid] = Object.entries(bucket[pid])
      .sort(function(a, b) { return Number(b[1] || 0) - Number(a[1] || 0); })
      .map(function(entry) { return entry[0]; });
  });
})();

const PAPER_TAG_TO_THREADS = (function() {
  var out = {};
  Object.entries(THREAD_PAPER_TAG_HINTS || {}).forEach(function(entry) {
    var th = entry[0];
    (entry[1] || []).forEach(function(tag) {
      var key = String(tag || '').toLowerCase();
      if (!key) return;
      if (!out[key]) out[key] = [];
      if (out[key].indexOf(th) < 0) out[key].push(th);
    });
  });
  return out;
})();

function paperTimelineInfluence(nodeOrPaper) {
  var p = nodeOrPaper || {};
  if (p._paperInf !== undefined && p._paperInf !== null) return Number(p._paperInf) || 0;
  return paperMetadataToInfluence(p);
}

function paperTimelineThread(nodeOrPaper) {
  var p = nodeOrPaper || {};
  if (p._paperThread !== undefined && p._paperThread !== null) return p._paperThread;
  return inferPaperThread(p);
}

function inferPaperThread(paper) {
  if (!paper) return null;
  var pid = String(paper.id || '').trim();
  var eips = PAPER_TO_EIP_IDS[pid] || uniqueSortedNumbers(paper.eq || []);
  var topicIds = PAPER_TO_TOPIC_IDS[pid] || [];
  var counts = {};

  topicIds.forEach(function(tid) {
    var t = DATA.topics[tid];
    if (!t || !t.th) return;
    counts[t.th] = (counts[t.th] || 0) + 2;
  });

  eips.forEach(function(num) {
    var eMeta = (DATA.eipCatalog || {})[String(num)];
    if (!eMeta || !eMeta.th) return;
    counts[eMeta.th] = (counts[eMeta.th] || 0) + 1;
  });

  (paper.tg || []).forEach(function(tag) {
    var threads = PAPER_TAG_TO_THREADS[String(tag || '').toLowerCase()] || [];
    threads.forEach(function(th) { counts[th] = (counts[th] || 0) + 1; });
  });

  var best = null;
  var bestCount = 0;
  Object.keys(counts).forEach(function(th) {
    if (counts[th] > bestCount) {
      bestCount = counts[th];
      best = th;
    }
  });
  return best;
}

function paperTimelineDate(paper) {
  if (!paper) return null;
  var year = paperYearValue(paper);
  if (year === null) return null;
  var pid = String(paper.id || '').trim();
  var seed = hashText(pid || String(year));
  var month = seed % 12;
  var day = 3 + (seed % 24);
  var d = new Date(year, month, day);
  if (isNaN(d)) return null;
  return d;
}

function activePaperAliasRows() {
  if (!hasAuthorFilter()) return null;
  var names = new Set();
  getActiveEthAuthorSet().forEach(function(username) {
    names.add(username);
    linkedEipAuthors(username).forEach(function(name) { names.add(name); });
  });
  getActiveEipAuthorSet().forEach(function(name) {
    names.add(name);
    linkedEthAuthors(name).forEach(function(username) {
      names.add(username);
      linkedEipAuthors(username).forEach(function(eipName) { names.add(eipName); });
    });
  });
  if (names.size === 0) return [];
  return buildAliasRows(Array.from(names));
}

function paperMatchesTimelineFilterBase(nodeOrPaper) {
  if (!showPapers || !nodeOrPaper) return false;
  var pid = String(nodeOrPaper._paperId || nodeOrPaper.id || '').replace(/^paper_/, '').trim();
  var paper = (DATA.papers || {})[pid] || nodeOrPaper;
  if (!paper || !paper.id) return false;
  if (!paperPassesSidebarFilters(paper)) return false;

  var inf = paperTimelineInfluence(paper);
  if (minInfluence > 0 && inf < minInfluence) return false;

  var thread = paperTimelineThread(paper);
  if (activeThread && thread !== activeThread) return false;

  if (activeCategory || activeTag) {
    var topicIds = PAPER_TO_TOPIC_IDS[pid] || [];
    var hasTopicMatch = topicIds.some(function(tid) {
      var t = DATA.topics[tid];
      if (!t) return false;
      if (activeCategory && t.cat !== activeCategory) return false;
      if (activeTag && !(t.tg || []).includes(activeTag)) return false;
      return true;
    });
    if (!hasTopicMatch) return false;
  }

  if (hasAuthorFilter()) {
    var aliases = activePaperAliasRows();
    if (!aliases || aliases.length === 0) return false;
    var pidx = PAPER_INDEX_BY_ID[pid];
    var authorRows = pidx ? (pidx.authorRows || []) : buildAliasRows(paper.a || []);
    var match = bestAliasMatch(aliases, authorRows);
    if (match.score < 2.0) return false;
  }

  return true;
}

function paperTimelineVisibilityKey() {
  var ethAuthors = Array.from(getActiveEthAuthorSet()).sort().join(',');
  var eipAuthors = Array.from(getActiveEipAuthorSet()).sort().join(',');
  return [
    String(showPapers ? 1 : 0),
    String(paperLayerMode || 'focus'),
    Number(minInfluence || 0).toFixed(6),
    String(activeThread || ''),
    String(activeCategory || ''),
    String(activeTag || ''),
    String(paperFilterYearMin || ''),
    String(paperFilterYearMax || ''),
    String(paperFilterMinCitations || 0),
    String(paperFilterTag || ''),
    String(activePaperId || ''),
    ethAuthors,
    eipAuthors,
  ].join('|');
}

function recomputePaperTimelineVisibleSet() {
  var key = paperTimelineVisibilityKey();
  if (key === paperTimelineVisibleKey) return;
  paperTimelineVisibleKey = key;
  paperTimelineVisibleIds = new Set();

  if (!showPapers) return;

  var mode = PAPER_TIMELINE_LIMITS[paperLayerMode] ? paperLayerMode : 'focus';
  var limit = Math.max(1, Number(PAPER_TIMELINE_LIMITS[mode] || 80));
  var rows = Object.values(DATA.papers || {}).filter(function(p) {
    return paperMatchesTimelineFilterBase(p);
  });

  rows.sort(function(a, b) {
    var bInf = paperTimelineInfluence(b);
    var aInf = paperTimelineInfluence(a);
    if (bInf !== aInf) return bInf - aInf;
    var bRel = Number(b.rs || 0);
    var aRel = Number(a.rs || 0);
    if (bRel !== aRel) return bRel - aRel;
    var bCb = Number(b.cb || 0);
    var aCb = Number(a.cb || 0);
    if (bCb !== aCb) return bCb - aCb;
    var bYear = Number(b.y || 0);
    var aYear = Number(a.y || 0);
    if (bYear !== aYear) return bYear - aYear;
    return String(a.t || '').localeCompare(String(b.t || ''));
  });

  rows.slice(0, limit).forEach(function(p) {
    var pid = String((p || {}).id || '').trim();
    if (pid) paperTimelineVisibleIds.add(pid);
  });

  if (activePaperId) {
    var activePaper = (DATA.papers || {})[String(activePaperId)];
    if (activePaper && paperMatchesTimelineFilterBase(activePaper)) {
      paperTimelineVisibleIds.add(String(activePaperId));
    }
  }
}

function paperMatchesTimelineFilter(nodeOrPaper) {
  if (!showPapers || !nodeOrPaper) return false;
  var pid = String(nodeOrPaper._paperId || nodeOrPaper.id || '').replace(/^paper_/, '').trim();
  var paper = (DATA.papers || {})[pid] || nodeOrPaper;
  if (!paper || !paper.id) return false;
  if (!paperMatchesTimelineFilterBase(paper)) return false;
  recomputePaperTimelineVisibleSet();
  if (!paperTimelineVisibleIds.has(String(paper.id || ''))) return false;
  return true;
}

const RELATED_PAPERS_CACHE = {
  topic: {},
  eip: {},
  magicians: {},
  fork: {},
  author: {},
  eipAuthor: {},
};

function paperRelevanceBonus(pidx, cfg) {
  var weight = Number((cfg && cfg.relevanceWeight) || 1.0);
  var relBonus = Math.min(1.4 * weight, (Math.max(0, Number((pidx && pidx.relevance) || 0)) / 12) * weight);
  var citedBy = Math.max(0, Number((pidx && pidx.citedBy) || 0));
  var citationBonus = Math.min(1.2 * weight, Math.log10(1 + citedBy) * 0.45 * weight);
  return relBonus + citationBonus;
}

function rankRelatedPapers(scoreFn, minScore, limit) {
  var rows = [];
  PAPER_INDEX.forEach(function(pidx) {
    if (!paperPassesSidebarFilters(pidx.p)) return;
    var result = scoreFn(pidx);
    if (!result || !isFinite(result.score) || result.score < minScore) return;
    rows.push(result);
  });
  rows.sort(function(a, b) {
    if (b.score !== a.score) return b.score - a.score;
    var bRel = Number((b.paper || {}).rs || 0);
    var aRel = Number((a.paper || {}).rs || 0);
    if (bRel !== aRel) return bRel - aRel;
    var bCb = Number((b.paper || {}).cb || 0);
    var aCb = Number((a.paper || {}).cb || 0);
    if (bCb !== aCb) return bCb - aCb;
    var bYear = Number((b.paper || {}).y || 0);
    var aYear = Number((a.paper || {}).y || 0);
    if (bYear !== aYear) return bYear - aYear;
    return String((a.paper || {}).t || '').localeCompare(String((b.paper || {}).t || ''));
  });
  return rows.slice(0, Math.max(1, limit || 18));
}

function relatedPapersForTopic(topicId) {
  var key = String(topicId);
  var cacheKey = key + '|' + paperMatchMode;
  if (RELATED_PAPERS_CACHE.topic[cacheKey]) return RELATED_PAPERS_CACHE.topic[cacheKey];
  var t = DATA.topics[topicId];
  if (!t) return [];
  var cfg = getPaperMatchConfig();

  var topicEips = new Set(uniqueSortedNumbers((t.eips || []).concat(t.peips || [])));
  var primaryEips = new Set(uniqueSortedNumbers(t.peips || []));
  var topicTitleTokens = new Set(keywordTokenList(t.t || ''));
  var topicThreadTags = new Set(threadPaperTags(t.th));

  var aliasNames = new Set();
  if (t.a) aliasNames.add(t.a);
  (t.coauth || []).forEach(function(u) { if (u) aliasNames.add(u); });
  (t.parts || []).forEach(function(u) { if (u) aliasNames.add(u); });
  Array.from(aliasNames).forEach(function(u) {
    linkedEipAuthors(u).forEach(function(name) { aliasNames.add(name); });
  });
  var aliasRows = buildAliasRows(Array.from(aliasNames));

  var rows = rankRelatedPapers(function(pidx) {
    var score = paperRelevanceBonus(pidx, cfg);
    var reasons = [];

    var eipOverlap = setOverlapArray(topicEips, pidx.eipSet);
    if (eipOverlap.length > 0) {
      score += Math.min(6.2, 2.8 + eipOverlap.length * 1.0);
      reasons.push('EIP overlap: ' + eipOverlap.slice(0, 3).map(function(n) { return 'EIP-' + n; }).join(', '));
      var primOverlap = eipOverlap.filter(function(n) { return primaryEips.has(n); });
      if (primOverlap.length > 0) {
        score += 1.2;
        reasons.push('primary EIP match');
      }
    }

    var authorMatch = bestAliasMatch(aliasRows, pidx.authorRows);
    if (authorMatch.score >= 2.0) {
      score += Math.min(3.2, authorMatch.score);
      reasons.push('author match: ' + authorMatch.alias);
    }

    var titleOverlap = setOverlapArray(topicTitleTokens, pidx.titleTokenSet);
    if (titleOverlap.length >= 2) {
      score += Math.min(2.2, titleOverlap.length * 0.65);
      reasons.push('title overlap');
    }

    var tagOverlap = setOverlapArray(topicThreadTags, pidx.tagSet);
    if (tagOverlap.length > 0) {
      score += 1.0;
      reasons.push('thread/domain match');
    }

    if (score < cfg.minTopic) return null;
    return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
  }, cfg.minTopic, cfg.limit);

  RELATED_PAPERS_CACHE.topic[cacheKey] = rows;
  return rows;
}

function relatedPapersForEip(num, eip) {
  var key = String(num);
  var cacheKey = key + '|' + paperMatchMode;
  if (RELATED_PAPERS_CACHE.eip[cacheKey]) return RELATED_PAPERS_CACHE.eip[cacheKey];
  var eipNum = Number(num);
  var cfg = getPaperMatchConfig();
  var threadTags = new Set(threadPaperTags(eip && eip.th));
  var titleTokens = new Set(keywordTokenList((eip && eip.t) || ''));
  var aliasRows = buildAliasRows((eip && eip.au) || []);

  var rows = rankRelatedPapers(function(pidx) {
    var score = paperRelevanceBonus(pidx, cfg);
    var reasons = [];

    if (pidx.eipSet.has(eipNum)) {
      score += 6.0;
      reasons.push('mentions EIP-' + eipNum);
    }

    var authorMatch = bestAliasMatch(aliasRows, pidx.authorRows);
    if (authorMatch.score >= 2.0) {
      score += Math.min(2.8, authorMatch.score * 0.8);
      reasons.push('author match: ' + authorMatch.alias);
    }

    var titleOverlap = setOverlapArray(titleTokens, pidx.titleTokenSet);
    if (titleOverlap.length >= 2) {
      score += Math.min(1.9, titleOverlap.length * 0.55);
      reasons.push('title overlap');
    }

    var tagOverlap = setOverlapArray(threadTags, pidx.tagSet);
    if (tagOverlap.length > 0) {
      score += 0.9;
      reasons.push('thread/domain match');
    }

    if (score < cfg.minEip) return null;
    return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
  }, cfg.minEip, cfg.limit);

  RELATED_PAPERS_CACHE.eip[cacheKey] = rows;
  return rows;
}

function relatedPapersForMagiciansTopic(topicId, mt) {
  var key = String(topicId || '');
  if (!key) return [];
  var cacheKey = key + '|' + paperMatchMode;
  if (RELATED_PAPERS_CACHE.magicians[cacheKey]) return RELATED_PAPERS_CACHE.magicians[cacheKey];
  var cfg = getPaperMatchConfig();
  var topic = mt || (DATA.magiciansTopics || {})[String(topicId)] || {};

  var topicEips = new Set(uniqueSortedNumbers(topic.eips || []));
  var threadTags = new Set(threadPaperTags(magiciansThreadFromTopic(topic)));
  var titleTokens = new Set(keywordTokenList(topic.t || ''));
  var aliasNames = new Set();
  if (topic.a) aliasNames.add(topic.a);
  linkedEthAuthorsFromMag(topic.a || '').forEach(function(username) { aliasNames.add(username); });
  linkedEipAuthorsFromMag(topic.a || '').forEach(function(name) { aliasNames.add(name); });
  var aliasRows = buildAliasRows(Array.from(aliasNames));

  var rows = rankRelatedPapers(function(pidx) {
    var score = paperRelevanceBonus(pidx, cfg);
    var reasons = [];

    var eipOverlap = setOverlapArray(topicEips, pidx.eipSet);
    if (eipOverlap.length > 0) {
      score += Math.min(5.8, 2.5 + eipOverlap.length * 1.0);
      reasons.push('EIP overlap: ' + eipOverlap.slice(0, 3).map(function(n) { return 'EIP-' + n; }).join(', '));
    }

    var authorMatch = bestAliasMatch(aliasRows, pidx.authorRows);
    if (authorMatch.score >= 2.0) {
      score += Math.min(2.8, authorMatch.score * 0.9);
      reasons.push('author match: ' + authorMatch.alias);
    }

    var titleOverlap = setOverlapArray(titleTokens, pidx.titleTokenSet);
    if (titleOverlap.length >= 2) {
      score += Math.min(1.6, titleOverlap.length * 0.5);
      reasons.push('title overlap');
    }

    var tagOverlap = setOverlapArray(threadTags, pidx.tagSet);
    if (tagOverlap.length > 0) {
      score += 0.9;
      reasons.push('thread/domain match');
    }

    if (score < cfg.minTopic) return null;
    return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
  }, cfg.minTopic, cfg.limit);

  RELATED_PAPERS_CACHE.magicians[cacheKey] = rows;
  return rows;
}

function relatedPapersForFork(forkObj) {
  var key = String((forkObj && (forkObj.cn || forkObj.n)) || '');
  if (!key) return [];
  var cacheKey = key + '|' + paperMatchMode;
  if (RELATED_PAPERS_CACHE.fork[cacheKey]) return RELATED_PAPERS_CACHE.fork[cacheKey];
  var cfg = getPaperMatchConfig();

  var forkEips = new Set(uniqueSortedNumbers((forkObj && forkObj.eips) || []));
  var threadTagSet = new Set();
  ((forkObj && forkObj.rt) || []).forEach(function(tid) {
    var t = DATA.topics[tid];
    threadPaperTags(t && t.th).forEach(function(tag) { threadTagSet.add(tag); });
  });

  var rows = rankRelatedPapers(function(pidx) {
    var score = paperRelevanceBonus(pidx, cfg);
    var reasons = [];

    var overlap = setOverlapArray(forkEips, pidx.eipSet);
    if (overlap.length > 0) {
      score += Math.min(8.0, 3.4 + (overlap.length - 1) * 1.1);
      reasons.push('includes fork EIP: ' + overlap.slice(0, 3).map(function(n) { return 'EIP-' + n; }).join(', '));
    }

    var tagOverlap = setOverlapArray(threadTagSet, pidx.tagSet);
    if (tagOverlap.length > 0) {
      score += 0.8;
      reasons.push('domain match');
    }

    if (score < cfg.minFork) return null;
    return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
  }, cfg.minFork, cfg.limit);

  RELATED_PAPERS_CACHE.fork[cacheKey] = rows;
  return rows;
}

function topAuthorThreads(username) {
  var profile = getAuthorProfile(username);
  if (!profile || !profile.ths) return [];
  return Object.entries(profile.ths)
    .sort(function(a, b) { return b[1] - a[1]; })
    .slice(0, 3)
    .map(function(entry) { return entry[0]; });
}

function relatedPapersForEthAuthor(username) {
  var key = String(username || '');
  if (!key) return [];
  var cacheKey = key + '|' + paperMatchMode;
  if (RELATED_PAPERS_CACHE.author[cacheKey]) return RELATED_PAPERS_CACHE.author[cacheKey];
  var cfg = getPaperMatchConfig();

  var aliasNames = new Set([username]);
  linkedEipAuthors(username).forEach(function(name) { aliasNames.add(name); });
  var aliasRows = buildAliasRows(Array.from(aliasNames));

  var threadTagSet = new Set();
  topAuthorThreads(username).forEach(function(tid) {
    threadPaperTags(tid).forEach(function(tag) { threadTagSet.add(tag); });
  });
  var authorTopicEips = new Set();
  var authorTopicTitleTokens = new Set();
  Object.values(DATA.topics || {}).forEach(function(topic) {
    if (!topic) return;
    var participants = new Set([topic.a].concat(topic.coauth || []).concat(topic.parts || []));
    if (!participants.has(username)) return;
    uniqueSortedNumbers((topic.eips || []).concat(topic.peips || [])).forEach(function(num) {
      authorTopicEips.add(Number(num));
    });
    keywordTokenList(topic.t || '').forEach(function(tok) { authorTopicTitleTokens.add(tok); });
  });

  var rows = rankRelatedPapers(function(pidx) {
    var score = paperRelevanceBonus(pidx, cfg);
    var reasons = [];
    var match = bestAliasMatch(aliasRows, pidx.authorRows);
    if (match.score < 2.0) return null;
    score += 1.8 + Math.min(3.0, match.score);
    reasons.push('author match: ' + match.alias);

    var tagOverlap = setOverlapArray(threadTagSet, pidx.tagSet);
    if (tagOverlap.length > 0) {
      score += 0.8;
      reasons.push('thread/domain match');
    }

    if (score < cfg.minAuthor) return null;
    return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
  }, cfg.minAuthor, cfg.limit);

  if (rows.length < Math.min(5, cfg.limit)) {
    var authorEips = new Set();
    linkedEipAuthors(username).forEach(function(name) {
      var ea = (DATA.eipAuthors || {})[name];
      (ea && ea.eips ? ea.eips : []).forEach(function(num) { authorEips.add(Number(num)); });
    });
    authorTopicEips.forEach(function(num) { authorEips.add(Number(num)); });

    var fallbackRows = rankRelatedPapers(function(pidx) {
      var score = paperRelevanceBonus(pidx, cfg);
      var reasons = [];

      var match = bestAliasMatch(aliasRows, pidx.authorRows);
      if (match.score >= 1.6) {
        score += 1.2 + Math.min(1.8, match.score * 0.7);
        reasons.push('author-adjacent: ' + match.alias);
      }

      var eipOverlap = setOverlapArray(authorEips, pidx.eipSet);
      if (eipOverlap.length > 0) {
        score += Math.min(3.1, 1.6 + eipOverlap.length * 0.75);
        reasons.push('EIP overlap: ' + eipOverlap.slice(0, 3).map(function(n) { return 'EIP-' + n; }).join(', '));
      }

      var tagOverlap = setOverlapArray(threadTagSet, pidx.tagSet);
      if (tagOverlap.length > 0) {
        score += Math.min(1.6, 0.9 + tagOverlap.length * 0.35);
        reasons.push('thread/domain match');
      }
      var titleOverlap = setOverlapArray(authorTopicTitleTokens, pidx.titleTokenSet);
      if (titleOverlap.length >= 2) {
        score += Math.min(1.4, 0.7 + titleOverlap.length * 0.2);
        reasons.push('title/domain overlap');
      }

      if ((pidx.p.tg || []).indexOf('known-authors') >= 0) score += 0.45;
      if (reasons.length === 0) return null;
      var fallbackMin = Math.max(1.9, cfg.minAuthor - 0.9);
      if (score < fallbackMin) return null;
      return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
    }, Math.max(1.9, cfg.minAuthor - 0.9), cfg.limit);

    if (fallbackRows.length > 0) {
      var seenIds = new Set(rows.map(function(r) { return String((r.paper || {}).id || ''); }));
      fallbackRows.forEach(function(r) {
        var pid = String((r.paper || {}).id || '');
        if (!pid || seenIds.has(pid)) return;
        rows.push(r);
        seenIds.add(pid);
      });
      rows.sort(function(a, b) {
        if (b.score !== a.score) return b.score - a.score;
        return Number((b.paper || {}).cb || 0) - Number((a.paper || {}).cb || 0);
      });
      rows = rows.slice(0, Math.max(1, cfg.limit));
    }
  }

  // Last-resort fallback: keep author pages useful even when strict/alias matching is sparse.
  if (rows.length === 0) {
    rows = rankRelatedPapers(function(pidx) {
      var score = paperRelevanceBonus(pidx, cfg) * 0.7;
      var reasons = [];
      var eipOverlap = setOverlapArray(authorTopicEips, pidx.eipSet);
      if (eipOverlap.length > 0) {
        score += Math.min(2.7, 1.4 + eipOverlap.length * 0.65);
        reasons.push('EIP overlap: ' + eipOverlap.slice(0, 3).map(function(n) { return 'EIP-' + n; }).join(', '));
      }
      var tagOverlap = setOverlapArray(threadTagSet, pidx.tagSet);
      if (tagOverlap.length > 0) {
        score += Math.min(1.4, 0.8 + tagOverlap.length * 0.3);
        reasons.push('thread/domain match');
      }
      var titleOverlap = setOverlapArray(authorTopicTitleTokens, pidx.titleTokenSet);
      if (titleOverlap.length >= 2) {
        score += Math.min(1.25, 0.65 + titleOverlap.length * 0.18);
        reasons.push('title/domain overlap');
      }
      if (reasons.length === 0) return null;
      if (score < Math.max(1.45, cfg.minAuthor - 1.35)) return null;
      return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
    }, Math.max(1.45, cfg.minAuthor - 1.35), Math.min(cfg.limit, 10));
  }

  RELATED_PAPERS_CACHE.author[cacheKey] = rows;
  return rows;
}

function relatedPapersForEipAuthor(name) {
  var key = String(name || '');
  if (!key) return [];
  var cacheKey = key + '|' + paperMatchMode;
  if (RELATED_PAPERS_CACHE.eipAuthor[cacheKey]) return RELATED_PAPERS_CACHE.eipAuthor[cacheKey];
  var cfg = getPaperMatchConfig();

  var aliasNames = new Set([name]);
  linkedEthAuthors(name).forEach(function(username) {
    aliasNames.add(username);
    linkedEipAuthors(username).forEach(function(n) { aliasNames.add(n); });
  });
  var aliasRows = buildAliasRows(Array.from(aliasNames));

  var authorObj = (DATA.eipAuthors || {})[name];
  var threadTagSet = new Set();
  if (authorObj && authorObj.eips) {
    (authorObj.eips || []).forEach(function(num) {
      var e = (DATA.eipCatalog || {})[String(num)];
      threadPaperTags(e && e.th).forEach(function(tag) { threadTagSet.add(tag); });
    });
  }

  var rows = rankRelatedPapers(function(pidx) {
    var score = paperRelevanceBonus(pidx, cfg);
    var reasons = [];
    var match = bestAliasMatch(aliasRows, pidx.authorRows);
    if (match.score < 2.0) return null;
    score += 1.8 + Math.min(3.0, match.score);
    reasons.push('author match: ' + match.alias);

    var tagOverlap = setOverlapArray(threadTagSet, pidx.tagSet);
    if (tagOverlap.length > 0) {
      score += 0.8;
      reasons.push('thread/domain match');
    }

    if (score < cfg.minEipAuthor) return null;
    return {paper: pidx.p, score: Number(score.toFixed(3)), reasons: reasons};
  }, cfg.minEipAuthor, cfg.limit);

  RELATED_PAPERS_CACHE.eipAuthor[cacheKey] = rows;
  return rows;
}

const NETWORK_PAPER_LIMITS = {
  focus: {
    maxTopics: 36,
    maxEips: 48,
    maxMagicians: 30,
    perTopic: 1,
    perEip: 2,
    perMagicians: 1,
    maxPapers: 40,
    maxPaperPaperEdges: 50,
    topicWeight: 0.7,
    eipWeight: 1.0,
    magiciansWeight: 0.8,
  },
  context: {
    maxTopics: 80,
    maxEips: 105,
    maxMagicians: 70,
    perTopic: 2,
    perEip: 2,
    perMagicians: 2,
    maxPapers: 90,
    maxPaperPaperEdges: 120,
    topicWeight: 0.72,
    eipWeight: 1.0,
    magiciansWeight: 0.85,
  },
  broad: {
    maxTopics: 130,
    maxEips: 180,
    maxMagicians: 120,
    perTopic: 2,
    perEip: 3,
    perMagicians: 2,
    maxPapers: 150,
    maxPaperPaperEdges: 220,
    topicWeight: 0.75,
    eipWeight: 1.02,
    magiciansWeight: 0.9,
  },
};

function paperNodeId(paperId) {
  return 'paper_' + String(paperId || '').trim();
}

function paperIdFromNode(node) {
  if (!node) return null;
  if (node._paperId !== undefined && node._paperId !== null) {
    var innerPid = String(node._paperId).trim();
    if (innerPid) return innerPid;
  }
  if (node.paperId !== undefined && node.paperId !== null) {
    var explicitPid = String(node.paperId).trim();
    if (explicitPid) return explicitPid;
  }
  if (node.id !== undefined && node.id !== null) {
    var idStr = String(node.id).trim();
    if (!idStr) return null;
    if (idStr.indexOf('paper_') === 0) return String(idStr.slice(6));
    if ((DATA.papers || {})[idStr]) return idStr;
  }
  return null;
}

function paperFromNode(node) {
  var pid = paperIdFromNode(node);
  if (!pid) return null;
  return (DATA.papers || {})[pid] || null;
}

function paperScoreToInfluence(score) {
  var s = Math.max(0, Number(score || 0));
  // Relation-score -> influence mapping (used for network paper augmentation).
  // Keep it conservative so paper overlay does not dominate core topic graph.
  return Math.max(0.03, Math.min(0.62, 0.04 + (s / 36)));
}

function paperMetadataToInfluence(paper) {
  if (!paper) return 0.03;
  var rs = Math.max(0, Number(paper.rs || 0));
  var cites = Math.max(0, Number(paper.cb || 0));
  var eipRefs = uniqueSortedNumbers(paper.eq || []).length;
  var year = paperYearValue(paper);

  // Relevance scores have a high floor in the ingestion pipeline.
  // Normalize around that floor so "just mentions Ethereum" does not score high.
  var relNorm = Math.max(0, Math.min(1, (rs - 10.0) / 8.0));
  var citeNorm = Math.max(0, Math.min(1, Math.log1p(cites) / Math.log(1 + 800)));
  var eipNorm = Math.max(0, Math.min(1, eipRefs / 2.0));

  // Citations are the strongest signal; relevance and explicit EIP anchors refine it.
  var base = (0.62 * citeNorm) + (0.23 * relNorm) + (0.15 * eipNorm);

  // Recency damping: very recent uncited papers should not outrank foundational work.
  var nowYear = new Date().getFullYear();
  var age = (year !== null) ? (nowYear - year) : 3;
  var recencyMultiplier = 1.0;
  if (age <= 0) recencyMultiplier = 0.55 + Math.min(0.25, citeNorm * 0.20);
  else if (age === 1) recencyMultiplier = 0.68 + Math.min(0.28, citeNorm * 0.45);
  else if (age === 2) recencyMultiplier = 0.84 + Math.min(0.16, citeNorm * 0.30);

  var influence = 0.03 + (0.62 * base * recencyMultiplier);
  return Math.max(0.03, Math.min(0.62, influence));
}

function buildNetworkPaperAugment(baseNodeMap) {
  if (!showPapers) return {nodes: [], links: []};
  var modeCfg = NETWORK_PAPER_LIMITS[paperLayerMode] || NETWORK_PAPER_LIMITS.focus;

  var relationByKey = {};
  var paperScoreById = {};
  var linkedTargetsByPaper = {};

  function addRelation(paperId, targetId, score, reason) {
    var pid = String(paperId || '').trim();
    if (!pid) return;
    if (!targetId || !baseNodeMap[targetId]) return;
    var paper = (DATA.papers || {})[pid];
    if (!paper) return;
    if (!paperPassesSidebarFilters(paper)) return;

    var relScore = Math.max(0.15, Number(score || 0));
    var sourceId = paperNodeId(pid);
    var edgeKey = sourceId + '->' + String(targetId);
    var prev = relationByKey[edgeKey];
    if (!prev || relScore > prev.score) {
      relationByKey[edgeKey] = {
        source: sourceId,
        target: targetId,
        edgeType: 'paper_related',
        paperId: pid,
        score: Number(relScore.toFixed(3)),
        reason: reason || '',
      };
    }
    paperScoreById[pid] = (paperScoreById[pid] || 0) + relScore;
    if (!linkedTargetsByPaper[pid]) linkedTargetsByPaper[pid] = new Set();
    linkedTargetsByPaper[pid].add(targetId);
  }

  function addRowsForTarget(rows, targetId, limit, weight) {
    (rows || []).slice(0, Math.max(1, limit || 1)).forEach(function(row) {
      if (!row || !row.paper || !row.paper.id) return;
      var score = Number(row.score || 0) * Number(weight || 1);
      var reason = (row.reasons && row.reasons.length > 0) ? String(row.reasons[0]) : '';
      addRelation(row.paper.id, targetId, score, reason);
    });
  }

  var topicTargets = Object.values(baseNodeMap)
    .filter(function(n) {
      return networkNodeSourceType(n) === 'topic' && DATA.topics[n.id];
    })
    .sort(function(a, b) {
      return (Number(b.influence || 0) - Number(a.influence || 0));
    })
    .slice(0, modeCfg.maxTopics);

  topicTargets.forEach(function(n) {
    var topicId = Number(n.id);
    if (!isFinite(topicId)) return;
    addRowsForTarget(relatedPapersForTopic(topicId), n.id, modeCfg.perTopic, modeCfg.topicWeight);
  });

  var eipTargets = Object.values(baseNodeMap)
    .filter(function(n) {
      return networkNodeSourceType(n) === 'eip' && eipNumFromNode(n) !== null;
    })
    .sort(function(a, b) {
      return (Number(b.influence || 0) - Number(a.influence || 0));
    })
    .slice(0, modeCfg.maxEips);

  eipTargets.forEach(function(n) {
    var eipNum = eipNumFromNode(n);
    if (eipNum === null || !isFinite(eipNum)) return;
    var eipMeta = (DATA.eipCatalog || {})[String(eipNum)] || {};
    addRowsForTarget(relatedPapersForEip(eipNum, eipMeta), n.id, modeCfg.perEip, modeCfg.eipWeight);
  });

  var magiciansTargets = Object.values(baseNodeMap)
    .filter(function(n) {
      return networkNodeSourceType(n) === 'magicians' && magiciansTopicId(n) !== null;
    })
    .sort(function(a, b) {
      return (Number(b.influence || 0) - Number(a.influence || 0));
    })
    .slice(0, modeCfg.maxMagicians);

  magiciansTargets.forEach(function(n) {
    var mid = magiciansTopicId(n);
    if (mid === null || !isFinite(mid)) return;
    var mt = (DATA.magiciansTopics || {})[String(mid)] || n;
    addRowsForTarget(relatedPapersForMagiciansTopic(mid, mt), n.id, modeCfg.perMagicians, modeCfg.magiciansWeight);
  });

  if (pinnedTopicId !== null && baseNodeMap[pinnedTopicId]) {
    addRowsForTarget(relatedPapersForTopic(Number(pinnedTopicId)), pinnedTopicId, 10, 1.25);
  }
  if (activeEipNum !== null) {
    var focusedEipNodeId = 'eip_' + String(activeEipNum);
    if (baseNodeMap[focusedEipNodeId]) {
      addRowsForTarget(
        relatedPapersForEip(Number(activeEipNum), (DATA.eipCatalog || {})[String(activeEipNum)] || {}),
        focusedEipNodeId,
        10,
        1.35
      );
    }
  }
  if (activeMagiciansId !== null) {
    var focusedMagNodeId = magiciansNodeId(activeMagiciansId);
    if (baseNodeMap[focusedMagNodeId]) {
      var focusedMt = (DATA.magiciansTopics || {})[String(activeMagiciansId)] || {};
      addRowsForTarget(
        relatedPapersForMagiciansTopic(Number(activeMagiciansId), focusedMt),
        focusedMagNodeId,
        10,
        1.25
      );
    }
  }

  var rankedPaperIds = Object.entries(paperScoreById)
    .sort(function(a, b) { return Number(b[1] || 0) - Number(a[1] || 0); })
    .slice(0, modeCfg.maxPapers)
    .map(function(entry) { return entry[0]; });
  var keep = new Set(rankedPaperIds);

  var paperNodes = rankedPaperIds.map(function(pid) {
    var p = (DATA.papers || {})[pid];
    var score = Number(paperScoreById[pid] || 0);
    return {
      id: paperNodeId(pid),
      sourceType: 'paper',
      isPaper: true,
      paperId: pid,
      title: p ? (p.t || 'Untitled paper') : 'Untitled paper',
      influence: paperScoreToInfluence(score),
      paperScore: Number(score.toFixed(3)),
      linkedTargets: Array.from(linkedTargetsByPaper[pid] || []),
      y: p ? (p.y || null) : null,
    };
  });

  var paperLinks = Object.values(relationByKey)
    .filter(function(rel) {
      return keep.has(rel.paperId);
    })
    .map(function(rel) {
      return {
        source: rel.source,
        target: rel.target,
        edgeType: rel.edgeType,
        score: rel.score,
        reason: rel.reason,
      };
    });

  var paperPairLimit = Math.max(0, Number(modeCfg.maxPaperPaperEdges || 0));
  var paperPairRows = buildPaperPairRows(rankedPaperIds.map(function(pid) {
    return {id: pid, paper: (DATA.papers || {})[pid] || null};
  }), {
    candidateMin: 1.2,
    minScore: 2.0,
    limit: paperPairLimit,
    ensurePerPaper: 1,
    extraBudget: Math.max(12, Math.round(paperPairLimit * 0.35)),
  }).map(function(ed) {
    return {
      source: paperNodeId(ed.paperA),
      target: paperNodeId(ed.paperB),
      edgeType: 'paper_paper',
      score: Number(ed.score || 0),
      reason: ed.reason || 'paper similarity',
    };
  });
  paperLinks = paperLinks.concat(paperPairRows);

  return {nodes: paperNodes, links: paperLinks};
}

function safeDomId(value) {
  return String(value || '').replace(/[^a-zA-Z0-9_-]/g, '_');
}

function paperUrl(paper) {
  if (!paper) return '';
  if (paper.u) return String(paper.u);
  if (paper.doi) return 'https://doi.org/' + paper.doi;
  if (paper.ax) {
    if (String(paper.ax).indexOf('http') === 0) return String(paper.ax);
    return 'https://arxiv.org/abs/' + String(paper.ax);
  }
  return '';
}

function paperAuthorsShort(paper, maxCount) {
  var authors = (paper && paper.a) ? paper.a : [];
  if (authors.length === 0) return '';
  var max = Math.max(1, maxCount || 3);
  if (authors.length <= max) return authors.join(', ');
  return authors.slice(0, max).join(', ') + ' +' + (authors.length - max);
}

function togglePaperRows(rowClass, toggleId, extraCount) {
  var rows = document.querySelectorAll('.' + rowClass);
  if (!rows || rows.length === 0) return;
  var hidden = rows[0].style.display === 'none';
  rows.forEach(function(row) {
    row.style.display = hidden ? 'block' : 'none';
  });
  var btn = document.getElementById(toggleId);
  if (btn) {
    btn.textContent = hidden ? 'Show fewer' : ('Show ' + extraCount + ' more papers');
  }
}

function buildRelatedPapersHtml(rows, sectionId, heading) {
  if (!rows || rows.length === 0) return '';
  var initialVisible = 6;
  var domId = safeDomId(sectionId);
  var rowClass = 'paper-extra-' + domId;
  var toggleId = 'paper-toggle-' + domId;
  var extraCount = Math.max(0, rows.length - initialVisible);

  var itemsHtml = rows.map(function(row, idx) {
    var paper = row.paper || {};
    var hidden = idx >= initialVisible;
    var url = paperUrl(paper);
    var titleHtml = url
      ? '<a class="paper-title" href="' + escHtml(url) + '" target="_blank">' + escHtml(paper.t || '') + '</a>'
      : '<span class="paper-title">' + escHtml(paper.t || '') + '</span>';
    var metaParts = [];
    if (paper.y) metaParts.push(String(paper.y));
    var authorsShort = paperAuthorsShort(paper, 3);
    if (authorsShort) metaParts.push(authorsShort);
    if (paper.v) metaParts.push(String(paper.v));
    if (paper.cb) metaParts.push('OpenAlex cites ' + Number(paper.cb).toLocaleString());
    var reasons = (row.reasons || []).slice(0, 2).join(' - ');
    return '<div class="paper-item ' + (hidden ? rowClass : '') + '"' + (hidden ? ' style="display:none"' : '') + '>' +
      titleHtml +
      (metaParts.length > 0 ? '<div class="paper-meta">' + escHtml(metaParts.join(' - ')) + '</div>' : '') +
      (reasons ? '<div class="paper-reasons">' + escHtml(reasons) + '</div>' : '') +
      '</div>';
  }).join('');

  var toggleHtml = '';
  if (extraCount > 0) {
    toggleHtml = '<span id="' + toggleId + '" class="paper-expand" onclick="togglePaperRows(' + jsQuote(rowClass) + ', ' + jsQuote(toggleId) + ', ' + extraCount + ')">' +
      'Show ' + extraCount + ' more papers</span>';
  }

  return '<div class="detail-refs"><h4>' + escHtml(heading || 'Related Papers') + ' (' + rows.length + ')</h4>' + itemsHtml + toggleHtml + '</div>';
}

const COAUTHOR_ALIAS_OVERRIDES = {
  caspar: {kind: 'eth', target: 'casparschwa'},
  francesco: {kind: 'eth', target: 'fradamt'},
  carl: {kind: 'eip', target: 'Carl Beekhuizen'},
  barnabe: {kind: 'eth', target: 'barnabe'},
  danny: {kind: 'eth', target: 'Danny'}
};

const COAUTHOR_ETH_USERNAMES = (function() {
  var out = new Set(Object.keys(DATA.authors || {}));
  Object.values(DATA.topics || {}).forEach(function(t) {
    if (t.a) out.add(t.a);
    (t.coauth || []).forEach(function(u) { if (u) out.add(u); });
    (t.parts || []).forEach(function(u) { if (u) out.add(u); });
  });
  return Array.from(out);
})();

function topCountsAsObject(counter, limit) {
  var entries = Object.entries(counter || {}).sort(function(a, b) {
    if (b[1] !== a[1]) return b[1] - a[1];
    return String(a[0]).localeCompare(String(b[0]));
  }).slice(0, limit);
  var out = {};
  entries.forEach(function(entry) { out[entry[0]] = entry[1]; });
  return out;
}

function topTopicIdsByInfluence(topicIds, limit) {
  return (topicIds || []).slice().sort(function(a, b) {
    var ta = DATA.topics[a] || {};
    var tb = DATA.topics[b] || {};
    return (tb.inf || 0) - (ta.inf || 0);
  }).slice(0, limit);
}

const ALL_ETH_AUTHORS = (function() {
  var out = {};

  Object.entries(DATA.authors || {}).forEach(function(entry) {
    var username = entry[0];
    var a = entry[1] || {};
    out[username] = {
      u: username,
      tc: a.tc || 0,
      tp: a.tp || 0,
      lk: a.lk || 0,
      ind: a.ind || 0,
      inf: a.inf || 0,
      yrs: (a.yrs || []).slice(),
      cats: Object.assign({}, a.cats || {}),
      ths: Object.assign({}, a.ths || {}),
      tops: (a.tops || []).slice(),
      co: Object.assign({}, a.co || {}),
      rank: a.rank !== undefined ? a.rank : 9999,
      at: (a.at || []).slice(),
    };
  });

  var synth = {};
  function ensureSynth(username) {
    if (!synth[username]) {
      synth[username] = {
        tc: 0,
        lk: 0,
        ind: 0,
        inf: 0,
        years: new Set(),
        cats: {},
        ths: {},
        co: {},
        topicIds: [],
        allTopicIds: [],
      };
    }
    return synth[username];
  }

  Object.values(DATA.topics || {}).forEach(function(t) {
    if (!t) return;
    var topicId = t.id;
    var authors = [];
    if (t.a) authors.push(t.a);
    (t.coauth || []).forEach(function(username) {
      if (username && authors.indexOf(username) < 0) authors.push(username);
    });
    if (authors.length === 0) return;

    authors.forEach(function(username) {
      if (out[username]) return;
      var a = ensureSynth(username);
      if (topicId !== undefined && topicId !== null && a.allTopicIds.indexOf(topicId) < 0) a.allTopicIds.push(topicId);
      if (!t.mn && topicId !== undefined && topicId !== null && a.topicIds.indexOf(topicId) < 0) a.topicIds.push(topicId);
      if (t.d && t.d.length >= 4) {
        var year = Number(t.d.slice(0, 4));
        if (!isNaN(year)) a.years.add(year);
      }
      if (t.cat) a.cats[t.cat] = (a.cats[t.cat] || 0) + 1;
      if (t.th) a.ths[t.th] = (a.ths[t.th] || 0) + 1;
      if (!t.mn) {
        a.tc += 1;
        a.lk += Number(t.lk || 0);
        a.ind += Number(t.ind || 0);
        a.inf += Number(t.inf || 0);
      }
      authors.forEach(function(other) {
        if (!other || other === username) return;
        a.co[other] = (a.co[other] || 0) + 1;
      });
    });
  });

  Object.entries(synth).forEach(function(entry) {
    var username = entry[0];
    var a = entry[1];
    var years = Array.from(a.years).sort(function(x, y) { return x - y; });
    var topTopicIds = topTopicIdsByInfluence(
      (a.topicIds && a.topicIds.length > 0) ? a.topicIds : a.allTopicIds,
      5
    );
    out[username] = {
      u: username,
      tc: a.tc,
      tp: 0,
      lk: a.lk,
      ind: a.ind,
      inf: Number(a.inf.toFixed(1)),
      yrs: years,
      cats: topCountsAsObject(a.cats, 5),
      ths: topCountsAsObject(a.ths, 3),
      tops: topTopicIds,
      co: topCountsAsObject(a.co, 5),
      rank: 9999,
      at: a.allTopicIds.slice().sort(function(x, y) { return x - y; }),
    };
  });

  return out;
})();

function getAuthorProfile(username) {
  return ALL_ETH_AUTHORS[username] || null;
}

const COAUTHOR_EIP_AUTHOR_NAMES = Object.keys(DATA.eipAuthors || {});

function normalizeIdentityToken(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '');
}

function normalizeAlphaToken(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z]/g, '');
}

function pickBestIdentityCandidate(scored, minScore, minMargin) {
  var sorted = scored.filter(function(row) { return row.score > 0; })
    .sort(function(a, b) { return b.score - a.score; });
  if (sorted.length === 0) return null;
  var best = sorted[0];
  if (best.score < minScore) return null;
  var second = sorted.length > 1 ? sorted[1] : null;
  if (second && (best.score - second.score) < minMargin) return null;
  return best;
}

function resolveBylineCoauthorIdentity(rawName) {
  var raw = String(rawName || '').trim();
  var norm = normalizeIdentityToken(raw);
  if (!norm) return {kind: 'raw', label: raw, key: 'raw:' + raw.toLowerCase()};

  var override = COAUTHOR_ALIAS_OVERRIDES[norm];
  if (override) {
    if (override.kind === 'eth' && COAUTHOR_ETH_USERNAMES.indexOf(override.target) >= 0) {
      return {kind: 'eth', target: override.target, label: override.target, key: 'eth:' + normalizeIdentityToken(override.target)};
    }
    if (override.kind === 'eip' && COAUTHOR_EIP_AUTHOR_NAMES.indexOf(override.target) >= 0) {
      return {kind: 'eip', target: override.target, label: override.target, key: 'eip:' + normalizeIdentityToken(override.target)};
    }
  }

  var bestEth = pickBestIdentityCandidate(COAUTHOR_ETH_USERNAMES.map(function(username) {
    var uNorm = normalizeIdentityToken(username);
    var score = 0;
    if (uNorm === norm) score = 320;
    else if (norm.length >= 4 && uNorm.indexOf(norm) === 0) score = 250;
    else if (norm.length >= 5 && uNorm.indexOf(norm) >= 0) score = 185;
    return {kind: 'eth', target: username, label: username, key: 'eth:' + uNorm, score: score};
  }), 230, 35);

  var bestEip = pickBestIdentityCandidate(COAUTHOR_EIP_AUTHOR_NAMES.map(function(name) {
    var full = normalizeIdentityToken(name);
    var parts = String(name || '').split(/\s+/).map(normalizeAlphaToken).filter(Boolean);
    var first = parts[0] || '';
    var last = parts.length > 0 ? parts[parts.length - 1] : '';
    var score = 0;
    if (full === norm) score = 340;
    else if (norm.length >= 4 && first === norm) score = 275;
    else if (norm.length >= 4 && last === norm) score = 285;
    else if (norm.length >= 4 && (first.indexOf(norm) === 0 || last.indexOf(norm) === 0)) score = 230;
    else if (norm.length >= 6 && full.indexOf(norm) >= 0) score = 180;
    return {kind: 'eip', target: name, label: name, key: 'eip:' + full, score: score};
  }), 230, 35);

  if (bestEth && bestEip) {
    if (Math.abs(bestEth.score - bestEip.score) < 15) {
      return {kind: 'raw', label: raw, key: 'raw:' + norm};
    }
    return bestEth.score > bestEip.score ? bestEth : bestEip;
  }
  if (bestEth) return bestEth;
  if (bestEip) return bestEip;
  return {kind: 'raw', label: raw, key: 'raw:' + norm};
}

const TOPIC_COAUTHOR_IDENTITIES_CACHE = {};

function topicResolvedCoauthorIdentities(t) {
  if (!t || t.id === undefined || t.id === null) return {eth: new Set(), eip: new Set()};
  var cacheKey = String(t.id);
  if (TOPIC_COAUTHOR_IDENTITIES_CACHE[cacheKey]) return TOPIC_COAUTHOR_IDENTITIES_CACHE[cacheKey];

  var out = {eth: new Set(), eip: new Set()};
  (t.coauth || []).forEach(function(username) {
    if (username) out.eth.add(username);
  });

  inferredCoauthorNamesFromExcerpt(t).forEach(function(name) {
    var resolved = resolveBylineCoauthorIdentity(name);
    if (!resolved) return;
    if (resolved.kind === 'eth' && resolved.target) out.eth.add(resolved.target);
    if (resolved.kind === 'eip' && resolved.target) {
      out.eip.add(resolved.target);
      linkedEthAuthors(resolved.target).forEach(function(username) { out.eth.add(username); });
    }
  });

  TOPIC_COAUTHOR_IDENTITIES_CACHE[cacheKey] = out;
  return out;
}

function getActiveEthAuthorSet() {
  var out = new Set();
  if (activeAuthor) out.add(activeAuthor);
  if (activeEipAuthor) {
    linkedEthAuthors(activeEipAuthor).forEach(function(u) { out.add(u); });
  }
  return out;
}

function getActiveEipAuthorSet() {
  var out = new Set();
  if (activeEipAuthor) out.add(activeEipAuthor);
  if (activeAuthor) {
    linkedEipAuthors(activeAuthor).forEach(function(name) { out.add(name); });
  }
  return out;
}

function getActiveMagiciansAuthorSet() {
  var out = new Set();
  if (activeAuthor) {
    out.add(activeAuthor);
    linkedMagAuthorsFromEth(activeAuthor).forEach(function(name) { out.add(name); });
  }
  if (activeEipAuthor) {
    linkedMagAuthorsFromEip(activeEipAuthor).forEach(function(name) { out.add(name); });
  }
  return out;
}

function hasAuthorFilter() {
  return !!activeAuthor || !!activeEipAuthor;
}

function clearAuthorFilterState() {
  activeAuthor = null;
  activeEipAuthor = null;
}

function clearAuthorFilter() {
  clearAuthorFilterState();
  lineageActive = false;
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  refreshAuthorSidebarList();
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function selectLinkedAuthorIdentity(ethUsername, eipAuthorName) {
  activeAuthor = ethUsername || null;
  activeEipAuthor = eipAuthorName ? canonicalEipAuthorName(eipAuthorName) : null;
  lineageActive = false;
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  refreshAuthorSidebarList();
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function jsQuote(s) {
  return '\'' + String(s || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'") + '\'';
}

function openMagiciansAuthor(authorName) {
  var linkedEth = linkedEthAuthorsFromMag(authorName);
  var linkedEip = linkedEipAuthorsFromMag(authorName);
  if (linkedEth.length === 0 && linkedEip.length === 0) {
    showToast('No linked ethresearch/EIP identity for ' + authorName);
    return;
  }
  if (linkedEth.length > 0) {
    selectAuthor(linkedEth[0]);
    showAuthorDetail(linkedEth[0]);
    return;
  }
  openEipAuthor(linkedEip[0]);
}

function refreshAuthorSidebarList() {
  if (eipAuthorTab) buildEipAuthorList();
  else sortAuthorList(document.getElementById('author-sort').value || 'inf');
}

// Build reverse lookup: eip_num -> list of EIPs that require it
var eipRequiredBy = {};
Object.entries(DATA.eipCatalog || {}).forEach(function(entry) {
  var eipNum = entry[0], eip = entry[1];
  (eip.rq || []).forEach(function(req) {
    if (!eipRequiredBy[req]) eipRequiredBy[req] = [];
    eipRequiredBy[req].push(Number(eipNum));
  });
});

function eipNumFromNode(node) {
  if (!node) return null;
  if (node._eipNum !== undefined && node._eipNum !== null) return Number(node._eipNum);
  if (node.eipNum !== undefined && node.eipNum !== null) return Number(node.eipNum);
  if (node.id && typeof node.id === 'string' && node.id.indexOf('eip_') === 0) {
    return Number(node.id.slice(4));
  }
  return null;
}

function eipNodeId(node) {
  if (!node) return null;
  if (node._eipNodeId) return node._eipNodeId;
  if (node.id && typeof node.id === 'string' && node.id.indexOf('eip_') === 0) return node.id;
  var num = eipNumFromNode(node);
  if (num === null || isNaN(num)) return null;
  return 'eip_' + num;
}

function eipThread(node) {
  if (!node) return null;
  if (node._eipThread !== undefined && node._eipThread !== null) return node._eipThread;
  return node.th || node.thread || node.eipThread || null;
}

function eipInfluence(node) {
  if (!node) return 0;
  if (node.eipInf !== undefined && node.eipInf !== null) return node.eipInf;
  if (node.inf !== undefined && node.inf !== null) return node.inf;
  if (node.influence !== undefined && node.influence !== null) return node.influence;
  return 0;
}

function eipAuthorsFromNode(node) {
  function canonicalUniqueNames(names) {
    var out = [];
    var seen = new Set();
    (names || []).forEach(function(name) {
      var canonical = canonicalEipAuthorName(name);
      if (!canonical || seen.has(canonical)) return;
      seen.add(canonical);
      out.push(canonical);
    });
    return out;
  }
  if (!node) return [];
  if (Array.isArray(node.au) && node.au.length > 0) return canonicalUniqueNames(node.au);
  var num = eipNumFromNode(node);
  if (num === null || isNaN(num)) return [];
  var eip = (DATA.eipCatalog || {})[String(num)];
  return (eip && Array.isArray(eip.au)) ? canonicalUniqueNames(eip.au) : [];
}

function eipMatchesFilter(node) {
  if (!node) return false;
  var nid = eipNodeId(node);
  if (!nid) return false;
  if (eipVisibilityMode === 'connected' && !connectedEipNodeIds.has(nid)) return false;
  if (minInfluence > 0 && eipInfluence(node) < minInfluence) return false;
  if (activeThread && eipThread(node) !== activeThread) return false;
  var activeEipAuthors = getActiveEipAuthorSet();
  if (hasAuthorFilter()) {
    if (activeEipAuthors.size === 0) return false;
    var authors = eipAuthorsFromNode(node);
    var matches = authors.some(function(name) { return activeEipAuthors.has(name); });
    if (!matches) return false;
  }
  return true;
}

function magiciansTopicId(node) {
  if (!node) return null;
  if (node._magId !== undefined && node._magId !== null) return Number(node._magId);
  if (node.magiciansId !== undefined && node.magiciansId !== null) return Number(node.magiciansId);
  if (node.id !== undefined && node.id !== null) return Number(node.id);
  return null;
}

function magiciansLinkedEips(node) {
  var id = magiciansTopicId(node);
  if (id === null || isNaN(id)) return [];
  return magiciansToEips[String(id)] || [];
}

function isEipDiscussionMagiciansTopic(node) {
  return magiciansLinkedEips(node).length > 0;
}

function magiciansDisplayTitle(node) {
  var title = (node && node.t ? String(node.t) : '').trim();
  if (title) return title;
  var id = magiciansTopicId(node);
  if (id !== null && !isNaN(id)) return 'Untitled Topic (M#' + id + ')';
  return 'Untitled Topic';
}

function magiciansLabelTitle(node, maxLen) {
  var title = magiciansDisplayTitle(node);
  if (!maxLen || title.length <= maxLen) return title;
  return title.slice(0, maxLen - 1) + '\u2026';
}

function magiciansRawEngagementScore(mt) {
  if (!mt) return 0;
  var views = Number(mt.vw || 0);
  var likes = Number(mt.lk || 0);
  var posts = Number(mt.pc || 0);
  var log10Views = Math.log(views + 10) / Math.LN10;
  var score = 0;
  score += Math.min(0.45, log10Views / 10);
  score += Math.min(0.30, likes / 200);
  score += Math.min(0.30, posts / 120);
  return Math.max(0.04, score);
}

function quantileSorted(values, p) {
  if (!values || values.length === 0) return 0;
  if (p <= 0) return values[0];
  if (p >= 1) return values[values.length - 1];
  var idx = p * (values.length - 1);
  var lo = Math.floor(idx);
  var hi = Math.ceil(idx);
  if (lo === hi) return values[lo];
  var t = idx - lo;
  return values[lo] * (1 - t) + values[hi] * t;
}

// Normalize Magicians influence into the EthResearch influence distribution
// so the global slider treats both sources on a comparable scale.
var magiciansInfluenceById = {};
(function buildMagiciansInfluenceMap() {
  var ethInfs = Object.values(DATA.topics || {})
    .map(function(t) { return Number(t.inf || 0); })
    .filter(function(v) { return isFinite(v) && v >= 0; })
    .sort(function(a, b) { return a - b; });
  if (ethInfs.length === 0) return;

  var rows = Object.entries(DATA.magiciansTopics || {}).map(function(entry) {
    var id = String(entry[0]);
    var mt = entry[1] || {};
    return {id: id, raw: magiciansRawEngagementScore(mt)};
  });
  if (rows.length === 0) return;

  rows.sort(function(a, b) { return a.raw - b.raw; });
  rows.forEach(function(row, idx) {
    var p = rows.length === 1 ? 0.5 : (idx / (rows.length - 1));
    magiciansInfluenceById[row.id] = quantileSorted(ethInfs, p);
  });
})();

function magiciansMatchesFilter(node) {
  if (!node || !showMagicians) return false;
  if (showEips && isEipDiscussionMagiciansTopic(node)) return false;
  var inf = node._magInf;
  if (inf === undefined || inf === null) inf = magiciansInfluenceScore(node);
  if (minInfluence > 0 && inf < minInfluence) return false;
  var th = node._magThread;
  if (th === undefined) th = magiciansThreadFromTopic(node);
  if (activeThread && th !== activeThread) return false;
  var activeMagAuthors = getActiveMagiciansAuthorSet();
  if (hasAuthorFilter()) {
    if (activeMagAuthors.size === 0) return false;
    var author = (node.a || '').trim();
    if (!author || !activeMagAuthors.has(author)) return false;
  }
  return true;
}

function magiciansNodeId(id) {
  return 'mag_' + String(id);
}

function crossForumNodeId(sourceType, source) {
  if (sourceType === 'topic') return Number(source);
  if (sourceType === 'eip') return 'eip_' + Number(source);
  if (sourceType === 'magicians_topic') return magiciansNodeId(source);
  return null;
}

function magiciansThreadFromTopic(mt) {
  if (!mt) return null;
  var counts = {};
  (mt.er || []).forEach(function(tid) {
    var t = DATA.topics[tid];
    if (!t || !t.th) return;
    counts[t.th] = (counts[t.th] || 0) + 1;
  });
  (mt.eips || []).forEach(function(eipNum) {
    var e = (DATA.eipCatalog || {})[String(eipNum)];
    if (!e || !e.th) return;
    counts[e.th] = (counts[e.th] || 0) + 1;
  });
  var best = null;
  var bestCount = 0;
  Object.keys(counts).forEach(function(th) {
    if (counts[th] > bestCount) {
      bestCount = counts[th];
      best = th;
    }
  });
  return best;
}

function magiciansInfluenceScore(mt) {
  if (!mt) return 0;
  var id = magiciansTopicId(mt);
  if (id !== null && !isNaN(id)) {
    var mapped = magiciansInfluenceById[String(id)];
    if (mapped !== undefined) return mapped;
  }
  return magiciansRawEngagementScore(mt);
}

function timelineTopicVisible(topicId) {
  if (!showPosts) return false;
  var tid = Number(topicId);
  if (!isFinite(tid)) return false;
  var t = DATA.topics[tid];
  if (!t) return false;
  return topicMatchesFilter(t);
}

function timelineEipVisibleByNum(eipNum) {
  if (!showEips) return false;
  var num = Number(eipNum);
  if (!isFinite(num)) return false;
  var eMeta = (DATA.eipCatalog || {})[String(num)];
  if (!eMeta) return false;
  // Mirror drawEipTimeline gating so we never render dangling paper/EIP links.
  if (!eMeta.cr || Number(eMeta.inf || 0) < 0.05) return false;
  if (!eMeta._eipDate || eMeta._eipYPos === undefined || eMeta._eipYPos === null) return false;
  return eipMatchesFilter(eMeta);
}

function timelineMagiciansVisibleById(magId) {
  if (!showMagicians) return false;
  var mid = Number(magId);
  if (!isFinite(mid)) return false;
  var mt = (DATA.magiciansTopics || {})[String(mid)];
  if (!mt) return false;
  if (!mt._magDate || mt._magYPos === undefined || mt._magYPos === null) return false;
  return magiciansMatchesFilter(mt);
}

function timelinePaperVisibleById(paperId) {
  if (!showPapers) return false;
  var pid = String(paperId || '').replace(/^paper_/, '').trim();
  if (!pid) return false;
  var p = (DATA.papers || {})[pid];
  if (!p) return false;
  if (!p._paperDate || p._paperYPos === undefined || p._paperYPos === null) return false;
  return paperMatchesTimelineFilter(p);
}

function clearTimelineAuxEdgeMarkers() {
  d3.selectAll('.cross-ref-edge,.magicians-ref-edge,.paper-topic-ref-edge,.paper-eip-ref-edge,.paper-paper-edge,.focus-eip-topic-edge')
    .attr('marker-end', null);
}

function networkNodeSourceType(node) {
  if (!node) return null;
  if (node.sourceType) return node.sourceType;
  if (node.isFork) return 'fork';
  if (node.isEip) return 'eip';
  if (node.isPaper) return 'paper';
  if (node.id && typeof node.id === 'string' && node.id.indexOf('eip_') === 0) return 'eip';
  if (node.id && typeof node.id === 'string' && node.id.indexOf('mag_') === 0) return 'magicians';
  if (node.id && typeof node.id === 'string' && node.id.indexOf('paper_') === 0) return 'paper';
  return 'topic';
}

function genericNodeThread(node) {
  if (!node) return null;
  if (node.thread !== undefined && node.thread !== null) return node.thread;
  if (node.th !== undefined && node.th !== null) return node.th;
  return null;
}

function genericNodeInfluence(node) {
  if (!node) return 0;
  if (node.influence !== undefined && node.influence !== null) return node.influence;
  if (node.inf !== undefined && node.inf !== null) return node.inf;
  return 0;
}

function genericNetworkNodeMatchesFilter(node) {
  if (!node) return false;
  if (minInfluence > 0 && genericNodeInfluence(node) < minInfluence) return false;
  var th = genericNodeThread(node);
  if (activeThread && th && th !== activeThread) return false;
  return true;
}

function networkNodeMatchesFilter(node) {
  if (!node) return false;
  var sourceType = networkNodeSourceType(node);
  if (sourceType === 'fork') return true;
  if (sourceType === 'eip') return showEips && eipMatchesFilter(node);
  if (sourceType === 'magicians') return magiciansMatchesFilter(node);
  if (sourceType === 'paper') {
    if (!showPapers) return false;
    if (!paperPassesSidebarFilters(paperFromNode(node))) return false;
    if (minInfluence > 0 && genericNodeInfluence(node) < minInfluence) return false;
    return true;
  }
  if (sourceType === 'topic') {
    if (!showPosts) return false;
    var t = DATA.topics[node.id];
    if (t) return topicMatchesFilter(t);
  }
  // Generic fallback so future source types (e.g., Magicians nodes) participate
  // in network filtering/highlighting without needing source-specific branches.
  return genericNetworkNodeMatchesFilter(node);
}

function updateEipVisibilityUi() {
  var eipBtn = document.getElementById('toggle-eips');
  if (!eipBtn) return;
  var suffix = '';
  if (showEips) suffix = eipVisibilityMode === 'connected' ? ' (linked)' : ' (all)';
  eipBtn.textContent = '\u25A0 EIPs' + suffix;
  eipBtn.classList.toggle('active', showEips);
  eipBtn.title = showEips
    ? 'Click cycles linked/all/off'
    : 'Toggle EIP nodes';
}

const PAPER_LAYER_MODES = {
  focus: {label: 'focus'},
  context: {label: 'context'},
  broad: {label: 'broad'},
};
const PAPER_TIMELINE_LIMITS = {
  focus: 45,
  context: 80,
  broad: 130,
};
let paperTimelineVisibleIds = new Set();
let paperTimelineVisibleKey = '';

function updatePaperLayerModeUi() {
  var btn = document.getElementById('toggle-papers');
  if (!btn) return;
  var mode = PAPER_LAYER_MODES[paperLayerMode] ? paperLayerMode : 'focus';
  btn.textContent = showPapers ? ('\u25C6 Papers: ' + PAPER_LAYER_MODES[mode].label) : '\u25C6 Papers';
  btn.classList.remove('mode-focus', 'mode-context', 'mode-broad');
  btn.classList.toggle('active', showPapers);
  if (showPapers) btn.classList.add('mode-' + mode);
  btn.classList.remove('disabled');
  btn.title = 'Cycle papers: off \u2192 focus \u2192 context \u2192 broad \u2192 off';
}

function setPaperLayerMode(mode, persist) {
  var next = PAPER_LAYER_MODES[mode] ? mode : 'focus';
  if (paperLayerMode === next) {
    updatePaperLayerModeUi();
    return;
  }
  paperLayerMode = next;
  updatePaperLayerModeUi();
  if (persist !== false) {
    try { localStorage.setItem('evmap.paperLayerMode', next); } catch (e) {}
  }
  if (showPapers) {
    var netSvg = document.querySelector('#network-view svg');
    if (activeView === 'network') {
      if (netSvg) { netSvg.remove(); simulation = null; }
      buildNetwork();
    } else if (netSvg) {
      netSvg.remove();
      simulation = null;
    }
  }
  updateHash();
}

function cyclePaperLayerMode() {
  if (!showPapers) return;
  var order = ['focus', 'context', 'broad'];
  var idx = order.indexOf(paperLayerMode);
  if (idx < 0) idx = 0;
  var next = order[(idx + 1) % order.length];
  setPaperLayerMode(next, true);
}

function setupPaperLayerMode() {
  var mode = 'focus';
  try {
    var saved = localStorage.getItem('evmap.paperLayerMode');
    if (saved && PAPER_LAYER_MODES[saved]) mode = saved;
  } catch (e) {}
  paperLayerMode = mode;
  updatePaperLayerModeUi();
}

// Build co-author edge index: author_id -> set of connected author_ids
const coAuthorEdgeIndex = {};
const coAuthorNodeSet = new Set((DATA.coGraph.nodes || []).map(function(n) { return n.id; }));
(DATA.coGraph.edges || []).forEach(e => {
  if (!coAuthorEdgeIndex[e.source]) coAuthorEdgeIndex[e.source] = new Set();
  if (!coAuthorEdgeIndex[e.target]) coAuthorEdgeIndex[e.target] = new Set();
  coAuthorEdgeIndex[e.source].add(e.target);
  coAuthorEdgeIndex[e.target].add(e.source);
});

// Author color map
const authorList = Object.values(DATA.authors).sort((a,b) => b.inf - a.inf);
const authorColorMap = {};
authorList.forEach((a, i) => { authorColorMap[a.u] = i < 15 ? AUTHOR_COLORS[i] : '#555'; });

// Top 15 authors by influence (for persistent labels in co-author network)
const top15Authors = new Set(authorList.slice(0, 15).map(a => a.u));


// Influence slider setup
const maxDataInf = d3.max(Object.values(DATA.topics), t => t.inf) || 1;
// Compute default threshold: show the same count as original non-minor topics.
// Sort all influences descending, pick the Nth value (N = non-minor count).
const nonMinorCount = Object.values(DATA.topics).filter(t => !t.mn).length;
const allInfsSorted = Object.values(DATA.topics).map(t => t.inf).sort((a, b) => b - a);
const defaultInfluenceThreshold = nonMinorCount > 0 && nonMinorCount < allInfsSorted.length
  ? allInfsSorted[nonMinorCount - 1] : 0;
const defaultSliderPct = maxDataInf > 0 ? Math.round(defaultInfluenceThreshold / maxDataInf * 100) : 0;

function sliderLabel(pct) {
  return pct === 0 ? '0%' : pct + '%';
}

function setupInfSlider() {
  var slider = document.getElementById('inf-slider');
  var label = document.getElementById('inf-slider-label');
  // Set default value so initial view matches original (~550 topics visible)
  slider.value = defaultSliderPct;
  minInfluence = defaultInfluenceThreshold;
  label.textContent = sliderLabel(defaultSliderPct);
  slider.addEventListener('input', function() {
    var pct = Number(this.value);
    minInfluence = pct / 100 * maxDataInf;
    label.textContent = sliderLabel(pct);
    applyFilters();
  });
}

function canApplyFocusedHighlightInView() {
  if (pinnedTopicId !== null) return true;
  if (activeView === 'timeline' || activeView === 'network') {
    if (activeEipNum !== null && !showEips) return false;
    if (activeMagiciansId !== null && !showMagicians) return false;
    if (activePaperId && !showPapers) return false;
  }
  return hasFocusedEntity();
}

function rebuildActiveViewLayout() {
  if (activeView === 'timeline') {
    var tlContainer = document.getElementById('timeline-view');
    if (tlContainer) tlContainer.innerHTML = '';
    tlSvg = null;
    tlZoom = null;
    tlXScale = null;
    tlXScaleOrig = null;
    buildTimeline();
    if (showEips && !document.querySelector('.eip-square')) drawEipTimeline();
    if (showMagicians && !document.querySelector('.magicians-triangle')) drawMagiciansTimeline();
    if (showPapers && !document.querySelector('.paper-diamond')) drawPaperTimeline();
  } else if (activeView === 'network') {
    var netContainer = document.getElementById('network-view');
    if (netContainer) netContainer.innerHTML = '';
    if (simulation) simulation.stop();
    simulation = null;
    buildNetwork();
  } else if (activeView === 'coauthor') {
    var coContainer = document.getElementById('coauthor-view');
    if (coContainer) coContainer.innerHTML = '';
    if (coAuthorSimulation) coAuthorSimulation.stop();
    coAuthorSimulation = null;
    buildCoAuthorNetwork();
  }
  applyFilters();
  if (canApplyFocusedHighlightInView()) applyFocusedEntityHighlight();
}

function activeViewContainerElement() {
  if (activeView === 'timeline') return document.getElementById('timeline-view');
  if (activeView === 'network') return document.getElementById('network-view');
  if (activeView === 'coauthor') return document.getElementById('coauthor-view');
  return null;
}

function scheduleActiveViewRebuild(attempt) {
  var tries = Number(attempt) || 0;
  requestAnimationFrame(function() {
    var container = activeViewContainerElement();
    var cw = container ? Number(container.clientWidth || 0) : 0;
    var ch = container ? Number(container.clientHeight || 0) : 0;
    if ((cw < 40 || ch < 40) && tries < 8) {
      scheduleActiveViewRebuild(tries + 1);
      return;
    }
    rebuildActiveViewLayout();
  });
}

function positionSidebarToggle() {
  var sidebar = document.getElementById('sidebar');
  var widthBtn = document.getElementById('sidebar-width-toggle');
  var hideBtn = document.getElementById('sidebar-hide-toggle');
  if (!sidebar || !widthBtn || !hideBtn) return;
  var rect = sidebar.getBoundingClientRect();
  if (!isFinite(rect.left) || !isFinite(rect.top)) return;
  var y = Math.round(rect.top + Math.max(120, rect.height) / 2);
  var x = Math.round(rect.left);
  widthBtn.style.left = x + 'px';
  widthBtn.style.top = y + 'px';
  hideBtn.style.left = x + 'px';
  hideBtn.style.top = (y + 44) + 'px';
}

function applySidebarWidthState() {
  var app = document.getElementById('app');
  var widthBtn = document.getElementById('sidebar-width-toggle');
  var hideBtn = document.getElementById('sidebar-hide-toggle');
  if (!app || !widthBtn || !hideBtn) return;
  app.classList.toggle('sidebar-wide', sidebarWide);
  app.classList.toggle('sidebar-hidden', sidebarHidden);
  widthBtn.innerHTML = sidebarWide ? '&#9654;' : '&#9664;';
  widthBtn.title = sidebarWide ? 'Narrow sidebar' : 'Widen sidebar';
  widthBtn.style.display = sidebarHidden ? 'none' : 'block';
  hideBtn.innerHTML = sidebarHidden ? '&#9664;' : '&#9654;';
  hideBtn.title = sidebarHidden ? 'Show sidebar' : 'Hide sidebar';
  requestAnimationFrame(positionSidebarToggle);
}

function setupSidebarWidth() {
  try {
    sidebarWide = localStorage.getItem('evmap.sidebarWide') === '1';
    sidebarHidden = localStorage.getItem('evmap.sidebarHidden') === '1';
  } catch (e) {
    sidebarWide = false;
    sidebarHidden = false;
  }
  applySidebarWidthState();
}

function toggleSidebarWidth() {
  if (sidebarHidden) return;
  sidebarWide = !sidebarWide;
  applySidebarWidthState();
  try { localStorage.setItem('evmap.sidebarWide', sidebarWide ? '1' : '0'); } catch (e) {}
  scheduleActiveViewRebuild(0);
  refreshAuthorSidebarList();
}

function toggleSidebarHidden() {
  sidebarHidden = !sidebarHidden;
  if (!sidebarHidden) sidebarWide = false;
  applySidebarWidthState();
  try { localStorage.setItem('evmap.sidebarHidden', sidebarHidden ? '1' : '0'); } catch (e) {}
  scheduleActiveViewRebuild(0);
  if (!sidebarHidden) {
    refreshAuthorSidebarList();
  }
}

// === INIT ===
document.addEventListener('DOMContentLoaded', () => {
  setupSidebarWidth();
  setupPaperMatchMode();
  setupPaperLayerMode();
  buildSidebar();
  setupPaperSidebarPanel();
  buildTimeline();
  setupSearch();
  setupInfSlider();
  updateEipVisibilityUi();
  positionSidebarToggle();
  window.addEventListener('resize', positionSidebarToggle);
  var sidebarEl = document.getElementById('sidebar');
  if (sidebarEl) sidebarEl.addEventListener('scroll', positionSidebarToggle, {passive: true});
  // Click outside dismisses EIP popover
  document.addEventListener('click', function(ev) {
    var pop = document.getElementById('eip-popover');
    if (pop.style.display === 'block' && !pop.contains(ev.target) && !ev.target.classList.contains('eip-tag')) {
      pop.style.display = 'none';
    }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      var pop = document.getElementById('eip-popover');
      if (pop.style.display === 'block') { pop.style.display = 'none'; return; }
      var helpEl = document.getElementById('help-overlay');
      if (helpEl.classList.contains('open')) { helpEl.classList.remove('open'); return; }
      closeDetail(); clearFilters();
    }
    if (e.key === '?' && !e.ctrlKey && !e.metaKey && document.activeElement.tagName !== 'INPUT') {
      toggleHelp();
    }
    // Arrow key navigation between connected topics
    if (pinnedTopicId && (e.key === 'ArrowLeft' || e.key === 'ArrowRight') && document.activeElement.tagName !== 'INPUT') {
      e.preventDefault();
      navigateConnected(e.key === 'ArrowRight' ? 'next' : 'prev');
    }
  });
  // Apply initial hash state after a short delay to ensure views are ready
  setTimeout(function() { applyHash(); }, 50);
  // Listen for browser back/forward
  window.addEventListener('hashchange', function() {
    applyHash();
  });
});

// === VIEW SWITCHING ===
function showView(view) {
  activeView = view;
  document.getElementById('timeline-view').style.display = view === 'timeline' ? 'block' : 'none';
  document.getElementById('network-view').style.display = view === 'network' ? 'block' : 'none';
  document.getElementById('coauthor-view').style.display = view === 'coauthor' ? 'block' : 'none';
  document.getElementById('btn-timeline').classList.toggle('active', view === 'timeline');
  document.getElementById('btn-network').classList.toggle('active', view === 'network');
  document.getElementById('btn-coauthor').classList.toggle('active', view === 'coauthor');
  if (view === 'timeline') {
    if (!document.querySelector('#timeline-view svg')) buildTimeline();
    if (showEips && !document.querySelector('.eip-square')) drawEipTimeline();
    if (showMagicians && !document.querySelector('.magicians-triangle')) drawMagiciansTimeline();
    if (showPapers && !document.querySelector('.paper-diamond')) drawPaperTimeline();
  }
  if (view === 'network' && !document.querySelector('#network-view svg')) buildNetwork();
  if (view === 'coauthor' && !document.querySelector('#coauthor-view svg')) buildCoAuthorNetwork();
  if (lineageActive) applyLineageHighlight();
  updateHash();
}

// === SIDEBAR ===
function buildSidebar() {
  const legend = document.getElementById('thread-legend');
  THREAD_ORDER.forEach(tid => {
    const th = DATA.threads[tid];
    if (!th) return;
    const color = THREAD_COLORS[tid] || '#555';
    const chip = document.createElement('div');
    chip.className = 'thread-chip';
    chip.style.background = color + '33';
    chip.style.color = color;
    chip.style.border = '1px solid ' + color + '66';
    chip.title = th.n + ' (' + th.tc + ' topics)';
    chip.onclick = (function(id) {
      var clickTimer = null;
      return function(ev) {
        if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; return; }
        clickTimer = setTimeout(function() { clickTimer = null; toggleThread(id); }, 250);
      };
    })(tid);
    chip.ondblclick = (function(id) {
      return function() { selectThread(id); showThreadDetail(id); };
    })(tid);
    chip.dataset.thread = tid;

    // Thread status: count topics from 2024+ quarters
    var recentCount = (th.qc || []).reduce(function(sum, d) {
      return sum + (d.q >= '2024' ? d.c : 0);
    }, 0);
    var statusClass = recentCount >= 5 ? 'active' : recentCount >= 2 ? 'moderate' : 'dormant';
    var dot = document.createElement('span');
    dot.className = 'status-dot ' + statusClass;
    dot.title = recentCount + ' topics since 2024 (' + (statusClass === 'active' ? 'Active' : statusClass === 'moderate' ? 'Moderate' : 'Dormant') + ')';
    chip.appendChild(dot);

    const lbl = document.createElement('span');
    lbl.className = 'thread-label';
    lbl.textContent = th.n.split('&')[0].trim();
    chip.appendChild(lbl);

    const cnt = document.createElement('span');
    cnt.className = 'thread-count';
    cnt.textContent = th.tc;
    chip.appendChild(cnt);

    // Sparkline SVG from quarterly counts
    var qc = th.qc || [];
    if (qc.length > 0) {
      var sparkW = 80, sparkH = 16;
      var maxC = Math.max(1, Math.max.apply(null, qc.map(function(d) { return d.c; })));
      var stepX = sparkW / Math.max(1, qc.length - 1);
      var points = qc.map(function(d, i) {
        var x = i * stepX;
        var y = sparkH - (d.c / maxC) * (sparkH - 2) - 1;
        return x.toFixed(1) + ',' + y.toFixed(1);
      });
      var areaPoints = points.join(' ') + ' ' + sparkW.toFixed(1) + ',' + sparkH + ' 0,' + sparkH;

      var wrap = document.createElement('span');
      wrap.className = 'sparkline-wrap';
      wrap.innerHTML =
        '<svg width="' + sparkW + '" height="' + sparkH + '" viewBox="0 0 ' + sparkW + ' ' + sparkH + '">' +
        '<polygon points="' + areaPoints + '" fill="' + color + '" opacity="0.3"/>' +
        '<polyline points="' + points.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="1" opacity="0.8"/>' +
        '</svg>';

      var svgEl = wrap.querySelector('svg');
      svgEl.style.cursor = 'default';
      svgEl.addEventListener('mousemove', (function(qcData, sw) {
        return function(ev) {
          var rect = ev.currentTarget.getBoundingClientRect();
          var mx = ev.clientX - rect.left;
          var idx = Math.round(mx / sw * (qcData.length - 1));
          idx = Math.max(0, Math.min(qcData.length - 1, idx));
          var d = qcData[idx];
          var tip = document.getElementById('tooltip');
          tip.innerHTML = d.q + ': ' + d.c + ' topic' + (d.c !== 1 ? 's' : '');
          tip.style.display = 'block';
          tip.style.left = (ev.clientX + 10) + 'px';
          tip.style.top = (ev.clientY - 24) + 'px';
          ev.stopPropagation();
        };
      })(qc, sparkW));
      svgEl.addEventListener('mouseleave', function() { hideTooltip(); });
      svgEl.addEventListener('click', function(ev) { ev.stopPropagation(); });

      chip.appendChild(wrap);
    }

    legend.appendChild(chip);
  });

  // --- Category chips ---
  const catCounts = {};
  Object.values(DATA.topics).forEach(t => {
    if (t.cat) catCounts[t.cat] = (catCounts[t.cat] || 0) + 1;
  });
  const topCats = Object.entries(catCounts).sort((a,b) => b[1] - a[1]).slice(0, 10);
  const catContainer = document.getElementById('cat-chips');
  topCats.forEach(([cat, count]) => {
    const chip = document.createElement('span');
    chip.className = 'cat-chip';
    chip.dataset.cat = cat;
    chip.innerHTML = escHtml(cat) + ' <span class="chip-count">' + count + '</span>';
    chip.title = cat + ' (' + count + ' topics)';
    chip.onclick = () => toggleCategory(cat);
    catContainer.appendChild(chip);
  });

  // --- Tag chips ---
  const tagCounts = {};
  Object.values(DATA.topics).forEach(t => {
    (t.tg || []).forEach(tag => { tagCounts[tag] = (tagCounts[tag] || 0) + 1; });
  });
  const topTags = Object.entries(tagCounts).sort((a,b) => b[1] - a[1]).slice(0, 15);
  const tagContainer = document.getElementById('tag-chips');
  topTags.forEach(([tag, count]) => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.dataset.tag = tag;
    chip.innerHTML = escHtml(tag) + ' <span class="chip-count">' + count + '</span>';
    chip.title = tag + ' (' + count + ' topics)';
    chip.onclick = () => toggleTag(tag);
    tagContainer.appendChild(chip);
  });

  sortAuthorList('inf');
}

var authorSortLabels = {inf: 'inf', tc: 'topics', lk: 'likes', ind: 'cited', tp: 'posts'};

function sortAuthorList(field) {
  var sorted = Object.values(DATA.authors).slice().sort(function(a, b) { return (b[field] || 0) - (a[field] || 0); });
  var selectedEthAuthors = getActiveEthAuthorSet();
  var list = document.getElementById('author-list');
  list.innerHTML = '';
  sorted.slice(0, 25).forEach(function(a) {
    var item = document.createElement('div');
    item.className = 'author-item';
    item.dataset.author = a.u;
    var linked = linkedEipAuthors(a.u);
    var valLabel = field === 'inf' ? a.inf.toFixed(1) : (a[field] || 0);
    var countLabel = String(valLabel);
    if (linked.length > 0) {
      countLabel += ' · ' + linked[0] + (linked.length > 1 ? ' +' + (linked.length - 1) : '');
    }
    item.innerHTML = '<span class="author-dot" style="background:' + (authorColorMap[a.u] || '#555') + '"></span>' +
      '<span class="author-name">' + a.u + '</span>' +
      '<span class="author-count">' + escHtml(countLabel) + '</span>';
    item.onclick = (function(username) {
      var clickTimer = null;
      return function() {
        if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; return; }
        clickTimer = setTimeout(function() { clickTimer = null; toggleAuthor(username); }, 250);
      };
    })(a.u);
    item.ondblclick = (function(username) {
      return function() { selectAuthor(username); showAuthorDetail(username); };
    })(a.u);
    if (selectedEthAuthors.has(a.u)) item.classList.add('active');
    list.appendChild(item);
  });
}

function clearFilters() {
  activeThread = null;
  clearAuthorFilterState();
  activeCategory = null;
  activeTag = null;
  activeMagiciansId = null;
  activeEipNum = null;
  activePaperId = null;
  minInfluence = defaultInfluenceThreshold;
  var slider = document.getElementById('inf-slider');
  if (slider) { slider.value = defaultSliderPct; }
  var slLabel = document.getElementById('inf-slider-label');
  if (slLabel) { slLabel.textContent = sliderLabel(defaultSliderPct); }
  lineageActive = false;
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  pathMode = false; pathStart = null; pathSet = new Set(); pathEdgeSet = new Set();
  // Reset content toggles to defaults
  showPosts = true; showEips = false; showMagicians = false; showPapers = false; eipVisibilityMode = 'connected';
  document.getElementById('toggle-posts').classList.add('active');
  document.getElementById('toggle-eips').classList.remove('active');
  document.getElementById('toggle-magicians').classList.remove('active');
  document.getElementById('toggle-papers').classList.remove('active');
  updatePaperLayerModeUi();
  updateEipVisibilityUi();
  applyContentVisibility();
  if (similarActive) clearSimilar();
  document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.author-item').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.tag-chip').forEach(c => c.classList.remove('active'));
  document.getElementById('search-box').value = '';
  var dd = document.getElementById('search-dropdown');
  if (dd) { dd.style.display = 'none'; searchDropdownIdx = -1; }
  var pyMin = document.getElementById('paper-year-min');
  var pyMax = document.getElementById('paper-year-max');
  var pcMin = document.getElementById('paper-min-cites');
  var pcLabel = document.getElementById('paper-min-cites-label');
  var ptSel = document.getElementById('paper-tag-filter');
  var psSel = document.getElementById('paper-sort-filter');
  if (pyMin && pyMax) {
    pyMin.value = String(pyMin.min || pyMin.value || '');
    pyMax.value = String(pyMax.max || pyMax.value || '');
    paperFilterYearMin = Number(pyMin.value || 0);
    paperFilterYearMax = Number(pyMax.value || 0);
  }
  if (pcMin) pcMin.value = '0';
  if (pcLabel) pcLabel.textContent = '0';
  paperFilterMinCitations = 0;
  if (ptSel) ptSel.value = '';
  paperFilterTag = '';
  paperSidebarSort = 'relevance';
  if (psSel) psSel.value = 'relevance';
  clearRelatedPapersCache();
  renderPaperSidebarList();
  var btn = document.getElementById('lineage-btn');
  if (btn) { btn.textContent = 'Trace Lineage'; btn.style.borderColor = '#5566aa'; btn.style.color = '#8899cc'; }
  refreshAuthorSidebarList();
  applyFilters();
  updateHash();
}

function toggleThread(tid) {
  activeThread = activeThread === tid ? null : tid;
  lineageActive = false; lineageSet = new Set(); lineageEdgeSet = new Set();
  document.querySelectorAll('.thread-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.thread === activeThread));
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function selectThread(tid) {
  activeThread = tid;
  lineageActive = false; lineageSet = new Set(); lineageEdgeSet = new Set();
  document.querySelectorAll('.thread-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.thread === activeThread));
  document.getElementById('search-box').value = '';
  applyFilters();
  updateHash();
}

function toggleAuthor(username) {
  var linkedEips = linkedEipAuthors(username);
  var sameSelection = activeAuthor === username && (!activeEipAuthor || linkedEips.indexOf(activeEipAuthor) >= 0);
  if (sameSelection) clearAuthorFilter();
  else selectLinkedAuthorIdentity(username, linkedEips.length > 0 ? linkedEips[0] : null);
}

function selectAuthor(username) {
  var linkedEips = linkedEipAuthors(username);
  selectLinkedAuthorIdentity(username, linkedEips.length > 0 ? linkedEips[0] : null);
}

function toggleEipAuthor(name) {
  var canonical = canonicalEipAuthorName(name);
  var linkedEth = linkedEthAuthors(canonical);
  var sameSelection = activeEipAuthor === canonical && (!activeAuthor || linkedEth.indexOf(activeAuthor) >= 0);
  if (sameSelection) clearAuthorFilter();
  else selectLinkedAuthorIdentity(linkedEth.length > 0 ? linkedEth[0] : null, canonical);
}

function selectEipAuthor(name) {
  var canonical = canonicalEipAuthorName(name);
  var linkedEth = linkedEthAuthors(canonical);
  selectLinkedAuthorIdentity(linkedEth.length > 0 ? linkedEth[0] : null, canonical);
}

function openAuthor(username) {
  if (getAuthorProfile(username)) {
    selectAuthor(username);
    showAuthorDetail(username);
    return;
  }
  selectAuthor(username);
  var profileUrl = 'https://ethresear.ch/u/' + encodeURIComponent(username);
  window.open(profileUrl, '_blank');
  showToast('Opened ethresearch profile for ' + username);
}

function openEipAuthor(name) {
  var canonical = canonicalEipAuthorName(name);
  selectEipAuthor(canonical);
  showEipAuthorDetail(canonical);
}

function toggleCategory(cat) {
  activeCategory = activeCategory === cat ? null : cat;
  document.querySelectorAll('.cat-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.cat === activeCategory));
  applyFilters();
}

function toggleTag(tag) {
  activeTag = activeTag === tag ? null : tag;
  document.querySelectorAll('.tag-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.tag === activeTag));
  applyFilters();
}

function toggleMilestones() {
  milestonesVisible = !milestonesVisible;
  d3.selectAll('.milestone-marker')
    .style('display', milestonesVisible ? null : 'none');
  var btn = document.getElementById('milestone-toggle');
  if (btn) btn.classList.toggle('active', milestonesVisible);
}

function toggleContent(type, mode) {
  if (type === 'posts') {
    showPosts = !showPosts;
    document.getElementById('toggle-posts').classList.toggle('active', showPosts);
  } else if (type === 'eips') {
    var prevShowEips = showEips;
    var prevMode = eipVisibilityMode;
    if (mode === 'off') {
      showEips = false;
      eipVisibilityMode = 'connected';
    } else if (mode === 'on') {
      showEips = true;
    } else {
      // Single-button cycle: off -> linked -> all -> off
      if (!showEips) {
        showEips = true;
        eipVisibilityMode = 'connected';
      } else if (eipVisibilityMode === 'connected') {
        eipVisibilityMode = 'all';
      } else {
        showEips = false;
        eipVisibilityMode = 'connected';
      }
    }
    // Draw EIP nodes on timeline if first time
    if (showEips && activeView === 'timeline' && !document.querySelector('.eip-square')) {
      drawEipTimeline();
    }
    // Rebuild network when EIP visibility/mode changes and network is visible
    if (activeView === 'network' && (prevShowEips !== showEips || prevMode !== eipVisibilityMode)) {
      var netSvg = document.querySelector('#network-view svg');
      if (netSvg) { netSvg.remove(); simulation = null; }
      buildNetwork();
    }
  } else if (type === 'magicians') {
    showMagicians = !showMagicians;
    document.getElementById('toggle-magicians').classList.toggle('active', showMagicians);
    if (showMagicians && activeView === 'timeline' && !document.querySelector('.magicians-triangle')) {
      drawMagiciansTimeline();
    }
    if (activeView === 'network') {
      var mNetSvg = document.querySelector('#network-view svg');
      if (mNetSvg) { mNetSvg.remove(); simulation = null; }
      buildNetwork();
    }
  } else if (type === 'papers') {
    var prevShowPapers = showPapers;
    var prevPaperMode = paperLayerMode;
    var order = ['focus', 'context', 'broad'];
    if (mode === 'off') {
      showPapers = false;
    } else if (mode === 'on') {
      showPapers = true;
    } else {
      // Single-button cycle: off -> focus -> context -> broad -> off
      if (!showPapers) {
        showPapers = true;
      } else {
        var idx = order.indexOf(paperLayerMode);
        if (idx < 0) idx = 0;
        if (idx >= order.length - 1) {
          showPapers = false;
        } else {
          paperLayerMode = order[idx + 1];
          try { localStorage.setItem('evmap.paperLayerMode', paperLayerMode); } catch (e) {}
        }
      }
    }
    updatePaperLayerModeUi();
    if (showPapers && activeView === 'timeline' && !document.querySelector('.paper-diamond')) {
      drawPaperTimeline();
    }
    var pNetSvg = document.querySelector('#network-view svg');
    if (activeView === 'network' && (prevShowPapers !== showPapers || prevPaperMode !== paperLayerMode)) {
      if (pNetSvg) { pNetSvg.remove(); simulation = null; }
      buildNetwork();
    } else if (pNetSvg && prevShowPapers !== showPapers) {
      pNetSvg.remove();
      simulation = null;
    }
  }
  updateEipVisibilityUi();
  applyContentVisibility();
  applyFilters();
  updateHash();
}

function toggleEipVisibilityMode() {
  if (!showEips) return;
  eipVisibilityMode = eipVisibilityMode === 'connected' ? 'all' : 'connected';
  updateEipVisibilityUi();
  if (activeView === 'network') {
    var netSvg = document.querySelector('#network-view svg');
    if (netSvg) { netSvg.remove(); simulation = null; }
    buildNetwork();
  }
  applyFilters();
  updateHash();
}

function applyContentVisibility() {
  d3.selectAll('.topic-circle').style('display', showPosts ? null : 'none');
  d3.selectAll('.topic-label').style('display', showPosts ? null : 'none');
  d3.selectAll('.edge-line').style('display', showPosts ? null : 'none');
  clearTimelineAuxEdgeMarkers();
  d3.selectAll('.milestone-marker').style('display', function(d) {
    return showPosts && milestonesVisible ? null : 'none';
  });
  d3.selectAll('.eip-square').style('display', function(d) {
    return showEips && eipMatchesFilter(d) ? null : 'none';
  });
  d3.selectAll('.eip-label').style('display', function(d) {
    return showEips && eipMatchesFilter(d) ? null : 'none';
  });
  d3.selectAll('.magicians-triangle').style('display', function(d) {
    return magiciansMatchesFilter(d) ? null : 'none';
  });
  d3.selectAll('.magicians-label').style('display', function(d) {
    return magiciansMatchesFilter(d) ? null : 'none';
  });
  d3.selectAll('.paper-diamond').style('display', function(d) {
    return paperMatchesTimelineFilter(d) ? null : 'none';
  });
  d3.selectAll('.paper-hit').style('display', function(d) {
    return paperMatchesTimelineFilter(d) ? null : 'none';
  });
  d3.selectAll('.paper-label').style('display', function(d) {
    return paperMatchesTimelineFilter(d) ? null : 'none';
  });
  d3.selectAll('.paper-topic-ref-edge').style('display', function(d) {
    if (!d) return 'none';
    if (!timelinePaperVisibleById(d.paperId)) return 'none';
    if (!timelineTopicVisible(d.topicId)) return 'none';
    return null;
  });
  d3.selectAll('.paper-eip-ref-edge').style('display', function(d) {
    if (!d) return 'none';
    if (!timelinePaperVisibleById(d.paperId)) return 'none';
    if (!timelineEipVisibleByNum(d.eipNum)) return 'none';
    return null;
  });
  d3.selectAll('.paper-paper-edge').style('display', function(d) {
    if (!showPapers || !d) return 'none';
    if (!timelinePaperVisibleById(d.paperA)) return 'none';
    if (!timelinePaperVisibleById(d.paperB)) return 'none';
    return null;
  });
  d3.selectAll('.magicians-ref-edge').style('display', function(d) {
    if (!d || !d.magTopic) return 'none';
    if (!timelineMagiciansVisibleById(magiciansTopicId(d.magTopic))) return 'none';
    if (!timelineTopicVisible(d.topicId)) return 'none';
    return null;
  });
  d3.selectAll('.eip-lane-label').style('display', showEips ? null : 'none');
  // Cross-ref edges: only when both posts and EIPs are visible
  d3.selectAll('.cross-ref-edge').style('display', function(d) {
    if (!d) return 'none';
    if (!timelineTopicVisible(d.topicId)) return 'none';
    if (!timelineEipVisibleByNum(d.eipNum)) return 'none';
    return null;
  });
}

function toggleCollapse(id) {
  var body = document.getElementById(id + '-body');
  var arrow = document.getElementById(id + '-arrow');
  if (body && arrow) {
    body.classList.toggle('open');
    arrow.classList.toggle('open');
  }
}

function applyFilters() {
  if (activeView === 'timeline') filterTimeline();
  else if (activeView === 'network') filterNetwork();
  else if (activeView === 'coauthor') filterCoAuthorNetwork();
  updateBreadcrumb();
}

// === SEARCH ===
var searchDropdownIdx = -1; // keyboard nav index

function setupSearch() {
  const box = document.getElementById('search-box');
  const dropdown = document.getElementById('search-dropdown');
  let timeout;

  box.addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      const q = box.value.toLowerCase().trim();
      if (!q) {
        dropdown.style.display = 'none';
        searchDropdownIdx = -1;
        applyFilters();
        return;
      }
      // Clear sidebar filters when searching
      activeThread = null;
      clearAuthorFilterState();
      document.querySelectorAll('.thread-chip').forEach(c => c.classList.remove('active'));
      refreshAuthorSidebarList();
      filterBySearch(q);
      populateDropdown(q);
    }, 150);
  });

  box.addEventListener('keydown', function(ev) {
    var items = dropdown.querySelectorAll('.search-item');
    if (!items.length || dropdown.style.display === 'none') return;
    if (ev.key === 'ArrowDown') {
      ev.preventDefault();
      searchDropdownIdx = Math.min(searchDropdownIdx + 1, items.length - 1);
      items.forEach(function(el, i) { el.classList.toggle('active', i === searchDropdownIdx); });
    } else if (ev.key === 'ArrowUp') {
      ev.preventDefault();
      searchDropdownIdx = Math.max(searchDropdownIdx - 1, 0);
      items.forEach(function(el, i) { el.classList.toggle('active', i === searchDropdownIdx); });
    } else if (ev.key === 'Enter') {
      ev.preventDefault();
      if (searchDropdownIdx >= 0 && searchDropdownIdx < items.length) {
        items[searchDropdownIdx].click();
      } else if (items.length > 0) {
        items[0].click();
      }
    } else if (ev.key === 'Escape') {
      dropdown.style.display = 'none';
      searchDropdownIdx = -1;
    }
  });

  // Close dropdown on outside click
  document.addEventListener('click', function(ev) {
    if (!box.contains(ev.target) && !dropdown.contains(ev.target)) {
      dropdown.style.display = 'none';
      searchDropdownIdx = -1;
    }
  });
}

function populateDropdown(q) {
  var dropdown = document.getElementById('search-dropdown');
  var results = [];

  if (activeView === 'coauthor') {
    // Show matching authors
    Object.values(ALL_ETH_AUTHORS).forEach(function(a) {
      if (a.u.toLowerCase().includes(q)) {
        results.push({type: 'author', id: a.u, inf: a.inf || 0, tc: a.tc || 0});
      }
    });
    results.sort(function(a, b) { return b.inf - a.inf; });
    results = results.slice(0, 8);
    dropdown.innerHTML = results.map(function(r) {
      var color = authorColorMap[r.id] || '#667';
      return '<div class="search-item" data-author="' + escHtml(r.id) + '">' +
        '<div class="si-title"><span style="color:' + color + '">\u25CF</span> ' + escHtml(r.id) + '</div>' +
        '<div class="si-meta">' + r.tc + ' topics \u00b7 inf: ' + r.inf.toFixed(2) + '</div></div>';
    }).join('');
  } else {
    // Show matching authors first, then topics
    var authorResults = [];
    Object.values(ALL_ETH_AUTHORS).forEach(function(a) {
      var aliases = linkedEipAuthors(a.u);
      var aliasMatch = aliases.some(function(name) { return name.toLowerCase().includes(q); });
      if (a.u.toLowerCase().includes(q) || aliasMatch) {
        authorResults.push({author: a, aliases: aliases});
      }
    });
    authorResults.sort(function(a, b) { return (b.author.inf || 0) - (a.author.inf || 0); });
    var authorSlice = authorResults.slice(0, 3);
    var authorHtml = authorSlice.map(function(entry) {
      var a = entry.author;
      var aliases = entry.aliases || [];
      var color = authorColorMap[a.u] || '#667';
      var aliasMeta = aliases.length > 0 ? ' · EIP: ' + aliases[0] + (aliases.length > 1 ? ' +' + (aliases.length - 1) : '') : '';
      return '<div class="search-item" data-author="' + escHtml(a.u) + '">' +
        '<div class="si-title"><span style="color:' + color + '">\u25CF</span> ' + escHtml(a.u) + '</div>' +
        '<div class="si-meta">' + a.tc + ' topics \u00b7 inf: ' + a.inf.toFixed(2) + escHtml(aliasMeta) + '</div></div>';
    }).join('');

    // Match EIP authors (with linked ethresear.ch aliases)
    var eipAuthorResults = [];
    Object.values(DATA.eipAuthors || {}).forEach(function(a) {
      var linkedEth = linkedEthAuthors(a.n);
      var linkedMatch = linkedEth.some(function(u) { return u.toLowerCase().includes(q); });
      if (a.n.toLowerCase().includes(q) || linkedMatch) {
        eipAuthorResults.push({author: a, linkedEth: linkedEth});
      }
    });
    eipAuthorResults.sort(function(a, b) { return (b.author.inf || 0) - (a.author.inf || 0); });
    var eipAuthorSlice = eipAuthorResults.slice(0, 2);
    var eipAuthorHtml = eipAuthorSlice.map(function(entry) {
      var a = entry.author;
      var linkedEth = entry.linkedEth || [];
      var meta = (a.eips || []).length + ' EIPs' +
        (linkedEth.length > 0 ? ' · eth: ' + linkedEth[0] + (linkedEth.length > 1 ? ' +' + (linkedEth.length - 1) : '') : '');
      return '<div class="search-item" data-eip-author="' + escHtml(a.n) + '">' +
        '<div class="si-title"><span style="color:#88aacc">\u25A0</span> ' + escHtml(a.n) + '</div>' +
        '<div class="si-meta">' + escHtml(meta) + '</div></div>';
    }).join('');

    // Match EIPs from catalog by number or title
    var eipResults = [];
    Object.entries(DATA.eipCatalog || {}).forEach(function(entry) {
      var num = entry[0], eip = entry[1];
      var numMatch = num.startsWith(q.replace(/^eip-?/i, '')) || ('eip-' + num).includes(q);
      var titleMatch = eip.t && eip.t.toLowerCase().includes(q);
      if (numMatch || titleMatch) {
        eipResults.push({num: num, eip: eip, exact: num === q.replace(/^eip-?/i, '')});
      }
    });
    eipResults.sort(function(a, b) { return (b.exact ? 1 : 0) - (a.exact ? 1 : 0); });
    var eipSlice = eipResults.slice(0, 3);
    var eipHtml = eipSlice.map(function(r) {
      var meta = [r.eip.s, r.eip.ty, r.eip.c, r.eip.fk].filter(Boolean).join(' \u00b7 ');
      return '<div class="search-item search-item-eip" data-eip="' + r.num + '">' +
        '<div class="si-title"><span class="eip-tag primary" style="margin-right:4px">EIP-' + r.num + '</span>' + escHtml(r.eip.t || '') + '</div>' +
        '<div class="si-meta">' + escHtml(meta) + '</div></div>';
    }).join('');

    // Match papers by title/author/tag/EIP, prioritizing explicit author matches.
    var paperResults = [];
    var qNorm = normalizeSearchText(q);
    var qTokens = tokenizeSearchText(qNorm);
    Object.values(DATA.papers || {}).forEach(function(paper) {
      if (!paperPassesSidebarFilters(paper)) return;
      var score = 0;
      var titleNorm = normalizeSearchText(paper.t || '');
      var titleTokens = titleNorm ? titleNorm.split(/\s+/).filter(Boolean) : [];
      var authorNames = (paper.a || []);
      var authorNormRows = authorNames.map(function(name) { return normalizeSearchText(name); }).filter(Boolean);
      var tagNormRows = (paper.tg || []).map(function(tag) { return normalizeSearchText(tag); }).filter(Boolean);

      var matchedAuthor = '';
      var authorExact = false;
      var authorTokenMatch = false;
      var authorPrefixMatch = false;
      var authorSubstringMatch = false;
      if (qNorm) {
        authorNames.forEach(function(name) {
          if (matchedAuthor) return;
          var nNorm = normalizeSearchText(name || '');
          if (!nNorm) return;
          var nTokens = nNorm.split(/\s+/).filter(Boolean);
          if (nNorm === qNorm) {
            matchedAuthor = String(name || '');
            authorExact = true;
            return;
          }
          if (qTokens.length > 0 && qTokens.every(function(tok) { return nTokens.indexOf(tok) >= 0; })) {
            matchedAuthor = String(name || '');
            authorTokenMatch = true;
            return;
          }
          if (qTokens.length === 1 && qTokens[0].length >= 2 &&
              nTokens.some(function(tok) { return tok.indexOf(qTokens[0]) === 0; })) {
            matchedAuthor = String(name || '');
            authorPrefixMatch = true;
            return;
          }
          if (nNorm.indexOf(qNorm) >= 0) {
            matchedAuthor = String(name || '');
            authorSubstringMatch = true;
          }
        });
      }

      if (authorExact) score += 8;
      else if (authorTokenMatch) score += 6;
      else if (authorPrefixMatch) score += 4;
      else if (authorSubstringMatch) score += 3;

      var titleExactTokenMatch = qTokens.length > 0 &&
        qTokens.every(function(tok) { return titleTokens.indexOf(tok) >= 0; });
      var titlePhraseMatch = qNorm.length >= 4 && titleNorm.indexOf(qNorm) >= 0;
      var titlePrefixMatch = qTokens.length === 1 && qTokens[0].length >= 4 &&
        titleTokens.some(function(tok) { return tok.indexOf(qTokens[0]) === 0; });
      if (titleExactTokenMatch) score += 3;
      else if (titlePhraseMatch) score += 2;
      else if (titlePrefixMatch) score += 1;

      if (qNorm && tagNormRows.some(function(tag) { return tag.indexOf(qNorm) >= 0; })) score += 1;
      if ((paper.eq || []).some(function(e) { return ('eip-' + e).includes(q) || String(e) === q; })) score += 2;

      if (score > 0) {
        paperResults.push({
          paper: paper,
          score: score,
          matchedAuthor: matchedAuthor,
          authorStrong: !!(authorExact || authorTokenMatch || authorPrefixMatch),
          authorExact: !!authorExact,
        });
      }
    });
    paperResults.sort(function(a, b) {
      if (Number(b.authorExact || 0) !== Number(a.authorExact || 0)) {
        return Number(b.authorExact || 0) - Number(a.authorExact || 0);
      }
      if (Number(b.authorStrong || 0) !== Number(a.authorStrong || 0)) {
        return Number(b.authorStrong || 0) - Number(a.authorStrong || 0);
      }
      if (b.score !== a.score) return b.score - a.score;
      var bCb = Number((b.paper || {}).cb || 0);
      var aCb = Number((a.paper || {}).cb || 0);
      if (bCb !== aCb) return bCb - aCb;
      var bRs = Number((b.paper || {}).rs || 0);
      var aRs = Number((a.paper || {}).rs || 0);
      if (bRs !== aRs) return bRs - aRs;
      return String((a.paper || {}).t || '').localeCompare(String((b.paper || {}).t || ''));
    });
    var paperSlice = paperResults.slice(0, 4);
    var paperHtml = paperSlice.map(function(entry) {
      var p = entry.paper || {};
      var year = p.y ? String(p.y) : '?';
      var authorShort = paperAuthorsShort(p, 2);
      var meta = year +
        (authorShort ? ' \u00b7 ' + authorShort : '') +
        (p.cb ? ' \u00b7 OpenAlex cites ' + Number(p.cb).toLocaleString() : '');
      if (entry.matchedAuthor) meta += ' \u00b7 author match: ' + entry.matchedAuthor;
      return '<div class="search-item search-item-paper" data-paper-id="' + escHtml(String(p.id || '')) + '">' +
        '<div class="si-title"><span style="color:#9cc8ff">\u25C6</span> ' + escHtml(p.t || '') + '</div>' +
        '<div class="si-meta">' + escHtml(meta) + '</div></div>';
    }).join('');

    var topicResults = [];
    Object.values(DATA.topics).forEach(function(t) {
      var score = 0;
      var tl = t.t.toLowerCase();
      if (tl.includes(q)) score += 3;
      if (t.a.toLowerCase().includes(q) || (t.coauth || []).some(function(u) { return u.toLowerCase().includes(q); })) score += 2;
      if (linkedEipAuthors(t.a || '').some(function(name) { return name.toLowerCase().includes(q); })) score += 2;
      if ((t.coauth || []).some(function(u) {
        return linkedEipAuthors(u).some(function(name) { return name.toLowerCase().includes(q); });
      })) score += 1;
      if (t.cat && t.cat.toLowerCase().includes(q)) score += 1;
      if (t.eips.some(function(e) { return ('eip-'+e).includes(q) || (''+e) === q; })) score += 2;
      if ((t.tg || []).some(function(tag) { return tag.toLowerCase().includes(q); })) score += 1;
      if (score > 0) topicResults.push({topic: t, score: score});
    });
    topicResults.sort(function(a, b) { return b.score - a.score || b.topic.inf - a.topic.inf; });
    var maxTopics = 8 - authorSlice.length - eipSlice.length - eipAuthorSlice.length - paperSlice.length;
    if (maxTopics < 0) maxTopics = 0;
    var topicHtml = topicResults.slice(0, maxTopics).map(function(r) {
      var t = r.topic;
      var thColor = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';
      return '<div class="search-item" data-topic-id="' + t.id + '">' +
        '<div class="si-title"><span class="si-thread" style="background:' + thColor + '"></span>' + escHtml(t.t) + '</div>' +
        '<div class="si-meta">' + escHtml(t.a) + ' \u00b7 ' + t.d.slice(0,7) + ' \u00b7 inf: ' + t.inf.toFixed(2) + '</div></div>';
    }).join('');

    dropdown.innerHTML = eipHtml + eipAuthorHtml + authorHtml + paperHtml + topicHtml;
    results = eipSlice.map(function() { return {type:'eip'}; })
      .concat(eipAuthorSlice.map(function() { return {type:'eip_author'}; }))
      .concat(authorSlice.map(function() { return {type:'author'}; }))
      .concat(paperSlice.map(function() { return {type:'paper'}; }))
      .concat(topicResults.slice(0, maxTopics).map(function(r) { return {type:'topic'}; }));
  }

  searchDropdownIdx = -1;
  dropdown.style.display = results.length > 0 ? 'block' : 'none';

  // Attach click handlers
  dropdown.querySelectorAll('.search-item').forEach(function(el) {
    el.addEventListener('click', function(ev) {
      var topicId = el.dataset.topicId;
      var authorId = el.dataset.author;
      var eipId = el.dataset.eip;
      var eipAuthorId = el.dataset.eipAuthor;
      var paperId = el.dataset.paperId;
      if (eipId) {
        showEipDetailByNum(Number(eipId));
      } else if (paperId) {
        var paper = (DATA.papers || {})[paperId];
        if (paper) {
          if (!showPapers) toggleContent('papers', 'on');
          showPaperDetail(paper, null);
        }
      } else if (eipAuthorId) {
        openEipAuthor(eipAuthorId);
      } else if (topicId) {
        var t = DATA.topics[Number(topicId)];
        if (t) showDetail(t);
      } else if (authorId) {
        selectAuthor(authorId);
        showAuthorDetail(authorId);
      }
      dropdown.style.display = 'none';
      searchDropdownIdx = -1;
    });
    el.addEventListener('mouseenter', function() {
      var topicId = el.dataset.topicId;
      if (topicId) highlightTopicInView(Number(topicId));
    });
    el.addEventListener('mouseleave', function() {
      restorePinnedHighlight();
    });
  });
}

function filterBySearch(q) {
  if (activeView === 'coauthor') {
    var matchingAuthors = new Set();
    (DATA.coGraph.nodes || []).forEach(function(n) {
      if (n.id.toLowerCase().includes(q)) matchingAuthors.add(n.id);
    });
    Object.entries(EIP_TO_ETH_AUTHORS).forEach(function(entry) {
      var eipAuthor = entry[0], linkedEth = entry[1] || [];
      if (eipAuthor.toLowerCase().includes(q)) {
        linkedEth.forEach(function(u) { matchingAuthors.add(u); });
      }
    });
    highlightCoAuthorSet(matchingAuthors);
    return;
  }
  const matching = new Set();
  Object.values(DATA.topics).forEach(t => {
    var authorAliasMatch = linkedEipAuthors(t.a || '').some(function(name) {
      return name.toLowerCase().includes(q);
    });
    var coauthorAliasMatch = (t.coauth || []).some(function(u) {
      return linkedEipAuthors(u).some(function(name) { return name.toLowerCase().includes(q); });
    });
    if (t.t.toLowerCase().includes(q) || t.a.toLowerCase().includes(q) ||
        (t.coauth || []).some(u => u.toLowerCase().includes(q)) ||
        authorAliasMatch || coauthorAliasMatch ||
        (t.cat && t.cat.toLowerCase().includes(q)) ||
        t.eips.some(e => ('eip-'+e).includes(q) || (''+e) === q) ||
        (t.tg || []).some(tag => tag.toLowerCase().includes(q))) {
      matching.add(t.id);
    }
  });
  highlightTopicSet(matching);
}

function highlightTopicSet(ids) {
  if (activeView === 'timeline') {
    var targetOp = {};
    d3.selectAll('.topic-circle').each(function(d) {
      targetOp[d.id] = ids.has(d.id) ? 0.9 : 0.08;
    });
    d3.selectAll('.topic-circle')
      .transition().duration(200)
      .attr('opacity', d => targetOp[d.id])
      .attr('r', d => ids.has(d.id) ? tlRScale(d.inf) * 1.3 : tlRScale(d.inf));
    d3.selectAll('.edge-line').attr('stroke-opacity', 0.01);
    syncLabelsFromMap(targetOp);
  } else {
    d3.selectAll('.net-node .net-shape').attr('opacity', d => ids.has(d.id) ? 0.9 : 0.06);
    d3.selectAll('.net-link').attr('stroke-opacity', 0.02);
  }
}

function highlightCoAuthorSet(ids) {
  d3.selectAll('.coauthor-node circle').attr('opacity', function(d) {
    return ids.has(d.id) ? 1 : 0.06;
  });
  d3.selectAll('.coauthor-link').attr('stroke-opacity', 0.02);
  d3.selectAll('.coauthor-label').attr('opacity', function(d) {
    return ids.has(d.id) ? 1 : 0.1;
  });
  d3.selectAll('.coauthor-label-hover').attr('opacity', function(d) {
    return ids.has(d.id) ? 1 : 0;
  });
}

// === TIMELINE ===
let tlRScale; // shared so search can use it
let tlXScale; // current x scale (updated on zoom)
let tlXScaleOrig; // original x scale (for zoom reset)
let tlSvg = null; // timeline SVG element (for programmatic zoom)
let tlZoom = null; // D3 zoom behavior (for programmatic transform)
let tlPlotW = 0; // plot width
let tlMarginLeft = 0; // left margin
const TL_MIN_ZOOM = 1;
const TL_MAX_ZOOM = 8;
const TL_EDGE_PAD_MIN = 72;
const TL_EDGE_PAD_FRACTION = 0.5;

function clampTimelineTransform(t) {
  var k = t && isFinite(t.k) ? t.k : 1;
  k = Math.max(TL_MIN_ZOOM, Math.min(TL_MAX_ZOOM, k));

  if (!tlPlotW || tlPlotW <= 0) {
    return d3.zoomIdentity.translate(0, 0).scale(k);
  }

  var edgePad = Math.max(TL_EDGE_PAD_MIN, tlPlotW * TL_EDGE_PAD_FRACTION);
  var minX = tlPlotW * (1 - k) - edgePad;
  var maxX = edgePad;
  var x = t && isFinite(t.x) ? t.x : 0;
  if (x < minX) x = minX;
  if (x > maxX) x = maxX;

  return d3.zoomIdentity.translate(x, 0).scale(k);
}

function buildTimeline() {
  const container = document.getElementById('timeline-view');
  const width = container.clientWidth || 900;
  const height = container.clientHeight || 700;

  const histH = 24; // histogram height
  const eipReservedH = 0; // no dedicated EIP lane in thread-native mode
  const eipGap = 0;
  const forkLabelH = 18; // extra row for fork labels between histogram and x-axis dates
  const margin = {top: 50, right: 40, bottom: 30 + histH + forkLabelH, left: 180};
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const swimH = plotH - histH; // full swim-lane area for thread-native entities
  const topicLaneY0 = 0;

  // Group topics by thread for swim lanes
  const threadTopics = {};
  THREAD_ORDER.forEach(tid => { threadTopics[tid] = []; });
  threadTopics['_other'] = [];

  Object.values(DATA.topics).forEach(t => {
    const th = t.th;
    if (th && threadTopics[th]) threadTopics[th].push(t);
    else threadTopics['_other'].push(t);
  });

  const laneOrder = [...THREAD_ORDER.filter(t => (threadTopics[t]||[]).length > 0), '_other'];
  const laneH = swimH / laneOrder.length;

  // Time scale — includes topic dates, fork dates, and EIP dates
  const allDates = Object.values(DATA.topics).map(t => new Date(t.d)).filter(d => !isNaN(d));
  DATA.forks.forEach(f => { if (f.d) allDates.push(new Date(f.d)); });
  Object.values(DATA.eipCatalog || {}).forEach(e => { if (e.cr) { var d = new Date(e.cr); if (!isNaN(d)) allDates.push(d); } });
  const xDomainOrig = [d3.min(allDates), d3.max(allDates)];
  const xScale = d3.scaleTime()
    .domain(xDomainOrig.slice())
    .range([0, plotW]);

  tlXScale = xScale;
  tlXScaleOrig = xScale.copy();

  // Size scale
  const maxInf = d3.max(Object.values(DATA.topics), t => t.inf) || 1;
  const rScale = d3.scaleSqrt().domain([0, maxInf]).range([2.5, 14]);
  tlRScale = rScale; // expose for search

  // Create SVG (fits the container -- no oversized width)
  const wrapper = document.createElement('div');
  wrapper.className = 'timeline-container';
  container.appendChild(wrapper);

  const svg = d3.select(wrapper).append('svg')
    .attr('width', width)
    .attr('height', height);

  // Block browser swipe-back/forward at the SVG element itself (where
  // the event originates).  On macOS, the compositor detects navigation
  // gestures from wheel events on the *target* element; calling
  // preventDefault on an ancestor (wrapper) may be too late.
  var svgNode = svg.node();
  svgNode.addEventListener('wheel', function(ev) {
    if (activeView !== 'timeline') return;
    ev.preventDefault();
  }, {passive: false});

  // Clip path so zoomed content doesn't overflow into the label area
  var tlDefs = svg.append('defs');
  tlDefs.append('clipPath').attr('id', 'tl-clip')
    .append('rect').attr('x', 0).attr('y', -margin.top).attr('width', plotW).attr('height', height);

  // Arrow markers for citation edges (default: subtle, highlighted: visible)
  tlDefs.append('marker').attr('id', 'arrow-default')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-default').attr('opacity', 0.3);
  tlDefs.append('marker').attr('id', 'arrow-highlight')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-highlight').attr('opacity', 0.8);
  tlDefs.append('marker').attr('id', 'arrow-lineage')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-lineage').attr('opacity', 0.9);

  // Root group offset by margins
  const root = svg.append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

  // Fixed layer for y-axis labels (never affected by zoom)
  const fixedG = root.append('g');

  // Clipped layer for all zoomable content
  const clipG = root.append('g').attr('clip-path', 'url(#tl-clip)');
  const zoomG = clipG.append('g');

  // Era backgrounds
  const eraColors = ['#334', '#343', '#334', '#433', '#343'];
  const eraRects = [];
  const eraTexts = [];
  DATA.eras.forEach((era, i) => {
    const x0 = xScale(new Date(era.start));
    const x1 = xScale(new Date(era.end));
    eraRects.push(
      zoomG.append('rect').attr('class', 'era-bg')
        .attr('x', x0).attr('y', 0).attr('width', x1 - x0).attr('height', topicLaneY0 + swimH)
        .attr('fill', eraColors[i] || '#333')
        .datum({start: new Date(era.start), end: new Date(era.end)})
    );
    eraTexts.push(
      zoomG.append('text').attr('x', (x0 + x1) / 2).attr('y', -8)
        .attr('text-anchor', 'middle').attr('fill', '#555').attr('font-size', 10)
        .style('cursor', 'pointer')
        .text(era.name)
        .datum({start: new Date(era.start), end: new Date(era.end), idx: i})
        .on('click', function(ev, d) { showEraDetail(d.idx); })
        .on('mouseover', function() { d3.select(this).attr('fill', '#999'); })
        .on('mouseout', function() { d3.select(this).attr('fill', '#555'); })
    );
  });

  // Fork lines + labels + hover areas
  const forkLines = [];
  const forkLabels = [];
  const forkHoverLines = [];
  DATA.forks.forEach(f => {
    if (!f.d) return;
    const fd = new Date(f.d);
    const x = xScale(fd);
    forkLines.push(
      zoomG.append('line').attr('class', 'fork-line')
        .attr('x1', x).attr('x2', x).attr('y1', -5).attr('y2', topicLaneY0 + swimH + histH)
        .datum(fd)
    );
    forkLabels.push(
      zoomG.append('text').attr('class', 'fork-label')
        .attr('x', x).attr('y', topicLaneY0 + swimH + histH + 15).attr('text-anchor', 'middle')
        .text(f.cn || f.n)
        .attr('paint-order', 'stroke').attr('stroke', '#0a0a0f').attr('stroke-width', 3)
        .datum(fd)
    );
    // Invisible wide hover area for fork interaction
    var hoverLine = zoomG.append('line').attr('class', 'fork-hover-line')
      .attr('x1', x).attr('x2', x).attr('y1', -5).attr('y2', topicLaneY0 + swimH + histH)
      .datum({date: fd, fork: f})
      .on('mouseover', function(ev, d) { showForkTooltip(ev, d.fork); })
      .on('mouseout', function() { hideTooltip(); })
      .on('click', function(ev, d) { ev.stopPropagation(); showForkPopover(ev, d.fork); });
    forkHoverLines.push(hoverLine);
  });

  // "ethresear.ch live" annotation marker (Aug 17, 2017)
  var ethresearchLiveDate = new Date('2017-08-17');
  var ethresearchLiveX = xScale(ethresearchLiveDate);
  var liveLineData = {date: ethresearchLiveDate};
  var liveLine = zoomG.append('line')
    .attr('class', 'ethresearch-live-line')
    .attr('x1', ethresearchLiveX).attr('x2', ethresearchLiveX)
    .attr('y1', -5).attr('y2', topicLaneY0 + swimH + histH)
    .attr('stroke', '#5a8a5a').attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '6 3').attr('opacity', 0.6)
    .datum(liveLineData);
  var liveLabel = zoomG.append('text')
    .attr('class', 'ethresearch-live-label')
    .attr('x', ethresearchLiveX).attr('y', -12)
    .attr('text-anchor', 'middle').attr('fill', '#6aaa6a').attr('font-size', 10).attr('font-weight', 600)
    .attr('paint-order', 'stroke').attr('stroke', '#0a0a0f').attr('stroke-width', 3)
    .text('ethresear.ch live')
    .datum(liveLineData);

  // Swim lane labels + separators (labels are fixed; separators are in zoomG)
  const laneIdx = {};
  laneOrder.forEach((tid, i) => {
    laneIdx[tid] = i;
    const y = topicLaneY0 + i * laneH + laneH / 2;
    const name = tid === '_other' ? 'Other' : (DATA.threads[tid] ? DATA.threads[tid].n : tid);
    const color = tid === '_other' ? '#555' : (THREAD_COLORS[tid] || '#555');
    fixedG.append('text').attr('x', -10).attr('y', y)
      .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
      .attr('fill', color).attr('font-size', 11).attr('font-weight', 500)
      .text(name.length > 22 ? name.slice(0, 20) + '\u2026' : name);
    if (i > 0) {
      fixedG.append('line').attr('x1', 0).attr('x2', plotW)
        .attr('y1', topicLaneY0 + i * laneH).attr('y2', topicLaneY0 + i * laneH)
        .attr('stroke', '#1a1a2a').attr('stroke-width', 0.5);
    }
  });

  // Expose lane geometry for thread-native non-topic entities (EIPs/Magicians).
  window._topicLaneY0 = topicLaneY0;
  window._laneH = laneH;
  window._laneIdx = laneIdx;

  // Pre-compute fixed y positions for topics (y is stable across zoom)
  Object.values(DATA.topics).forEach(t => {
    const th = (t.th && laneIdx[t.th] !== undefined) ? t.th : '_other';
    const lane = laneIdx[th];
    const yBase = topicLaneY0 + lane * laneH + laneH * 0.12;
    const yRange = laneH * 0.76;
    t._yPos = yBase + (hashCode(t.id) % 100) / 100 * yRange;
    t._date = new Date(t.d);
  });

  // Draw edges (below circles)
  const edgeG = zoomG.append('g');
  DATA.graph.edges.forEach(e => {
    const sT = DATA.topics[e.source];
    const tT = DATA.topics[e.target];
    if (sT && tT && sT._yPos !== undefined && tT._yPos !== undefined) {
      edgeG.append('line').attr('class', 'edge-line')
        .attr('x1', xScale(sT._date)).attr('y1', sT._yPos)
        .attr('x2', xScale(tT._date)).attr('y2', tT._yPos)
        .attr('stroke-opacity', 0.06)
        .attr('marker-end', 'url(#arrow-default)')
        .datum({source: e.source, target: e.target, sd: sT._date, td: tT._date, sy: sT._yPos, ty: tT._yPos});
    }
  });

  // Draw topic circles
  const circleG = zoomG.append('g');
  Object.values(DATA.topics).forEach(t => {
    if (t._yPos === undefined) return;
    const color = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';
    var clickTimer = null;

    var circle = circleG.append('circle')
      .attr('class', 'topic-circle')
      .attr('cx', xScale(t._date)).attr('cy', t._yPos)
      .attr('r', rScale(t.inf))
      .attr('fill', color)
      .attr('stroke', color)
      .attr('stroke-width', t.mn ? 1 : 0.5)
      .attr('opacity', 0.65)
      .datum(t)
      .on('click', function(ev, d) {
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
          handleTopicDoubleClick(ev, d);
          return;
        }
        clickTimer = setTimeout(function() {
          clickTimer = null;
          handleTopicClick(ev, d);
        }, 220);
      })
      .on('mouseover', function(ev, d) { onTimelineHover(ev, d, true); })
      .on('mouseout', function(ev, d) { onTimelineHover(ev, d, false); });
    if (t.mn) circle.attr('stroke-dasharray', '3 2');
  });

  // --- Topic labels for high-influence nodes ---
  var topByInf = Object.values(DATA.topics).filter(function(t) { return t._yPos !== undefined; })
    .sort(function(a, b) { return b.inf - a.inf; }).slice(0, 30);
  var labelSet = new Set(topByInf.map(function(t) { return t.id; }));

  var labelG = zoomG.append('g');
  topByInf.forEach(function(t) {
    var maxChars = 28;
    var txt = t.t.length > maxChars ? t.t.slice(0, maxChars - 1) + '\u2026' : t.t;
    labelG.append('text').attr('class', 'topic-label')
      .attr('x', xScale(t._date) + rScale(t.inf) + 3)
      .attr('y', t._yPos + 3)
      .attr('opacity', 0.75)
      .datum(t)
      .text(txt);
  });

  // --- Milestone markers (star-shaped markers for thread milestones) ---
  var milestoneG = zoomG.append('g');
  var milestoneData = [];
  THREAD_ORDER.forEach(function(tid) {
    var th = DATA.threads[tid];
    if (!th || !th.ms) return;
    th.ms.forEach(function(ms) {
      var topic = DATA.topics[ms.id];
      if (topic && topic._yPos !== undefined) {
        milestoneData.push({topic: topic, note: ms.n, threadId: tid});
      }
    });
  });
  milestoneData.forEach(function(md) {
    var r = rScale(md.topic.inf) + 4;
    var msClickTimer = null;
    milestoneG.append('polygon')
      .attr('class', 'milestone-marker')
      .attr('points', starPoints(xScale(md.topic._date), md.topic._yPos, r, r * 0.5, 4))
      .datum(md.topic)
      .on('click', function(ev, d) {
        if (msClickTimer) {
          clearTimeout(msClickTimer);
          msClickTimer = null;
          handleTopicDoubleClick(ev, d);
          return;
        }
        msClickTimer = setTimeout(function() {
          msClickTimer = null;
          handleTopicClick(ev, d);
        }, 220);
      })
      .on('mouseover', function(ev, d) { showTooltip(ev, d); })
      .on('mouseout', function() { hideTooltip(); })
      .style('display', milestonesVisible ? null : 'none');
  });

  // --- Monthly activity histogram ---
  var monthBins = {};
  Object.values(DATA.topics).forEach(function(t) {
    var d = t._date;
    if (!d || isNaN(d)) return;
    var key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
    if (!monthBins[key]) monthBins[key] = {date: new Date(d.getFullYear(), d.getMonth(), 1), count: 0};
    monthBins[key].count++;
  });
  var histData = Object.values(monthBins).sort(function(a, b) { return a.date - b.date; });
  var maxCount = d3.max(histData, function(d) { return d.count; }) || 1;
  var histYScale = d3.scaleLinear().domain([0, maxCount]).range([0, histH - 2]);

  // Compute bar width: ~30 days in the time scale
  var barWidthBase = Math.max(1, xScale(new Date(2020, 1, 1)) - xScale(new Date(2020, 0, 1)));

  var histG = zoomG.append('g').attr('class', 'histogram-g')
    .attr('transform', 'translate(0,' + (topicLaneY0 + swimH) + ')');

  histG.selectAll('.histogram-bar')
    .data(histData)
    .join('rect')
    .attr('class', 'histogram-bar')
    .attr('x', function(d) { return xScale(d.date); })
    .attr('y', function(d) { return histH - histYScale(d.count); })
    .attr('width', Math.max(1, barWidthBase * 0.85))
    .attr('height', function(d) { return histYScale(d.count); })
    .attr('rx', 1)
    .on('mouseover', function(ev, d) {
      var tip = document.getElementById('tooltip');
      var mn = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      tip.innerHTML = mn[d.date.getMonth()] + ' ' + d.date.getFullYear() + ': ' + d.count + ' topic' + (d.count !== 1 ? 's' : '');
      tip.style.display = 'block';
      tip.style.left = (ev.clientX + 10) + 'px';
      tip.style.top = (ev.clientY - 24) + 'px';
    })
    .on('mouseout', function() { hideTooltip(); });

  // X axis (below fork labels, which are below histogram)
  var xAxisG = root.append('g')
    .attr('class', 'x-axis')
    .attr('transform', 'translate(0,' + (topicLaneY0 + swimH + histH + forkLabelH) + ')');
  var xAxisFn = d3.axisBottom(xScale).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
  xAxisG.call(xAxisFn);
  xAxisG.selectAll('text').attr('fill', '#666').attr('font-size', 12);
  xAxisG.selectAll('.domain, .tick line').attr('stroke', '#333');

  // === D3 ZOOM (horizontal only) ===
  // Strategy: wheel/trackpad (and pinch) = zoom, drag = horizontal pan,
  // double-click = reset.
  tlPlotW = plotW;
  tlMarginLeft = margin.left;

  var zoom = d3.zoom()
    .scaleExtent([TL_MIN_ZOOM, TL_MAX_ZOOM])
    .translateExtent([[0, 0], [plotW, height]])
    .extent([[0, 0], [plotW, height]])
    .constrain(function(transform) {
      return clampTimelineTransform(transform);
    })
    .filter(function(ev) {
      // Allow wheel/trackpad and pinch zoom gestures directly.
      if (ev.type === 'wheel') return true;
      // Block double-click (handled separately below)
      if (ev.type === 'dblclick') return false;
      // Allow drag (button 0) and touch events
      return !ev.button;
    })
    .on('zoom', onZoom);

  svg.call(zoom);
  tlSvg = svg;
  tlZoom = zoom;

  svg.on('click.clearFocus', function(ev) {
    if (!hasFocusedEntity() || ev.defaultPrevented) return;
    var target = ev && ev.target ? ev.target : null;
    if (target && target.closest && target.closest(
      '.topic-circle,.milestone-marker,.eip-square,.magicians-triangle,.paper-diamond,.paper-hit,.fork-hover-line,.eip-label,.magicians-label,.paper-label,.eip-tag'
    )) return;
    clearFocusedEntityState({keepDetailOpen: false});
  });

  // Double-click resets zoom only when the click lands on empty canvas.
  svg.on('dblclick.zoom', function(ev) {
    var target = ev && ev.target ? ev.target : null;
    if (target && target.closest && target.closest(
      '.topic-circle,.milestone-marker,.eip-square,.magicians-triangle,.paper-diamond,.paper-hit,.fork-hover-line,.eip-label,.magicians-label,.paper-label,.eip-tag,.histogram-bar'
    )) {
      return;
    }
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
  });

  function onZoom(ev) {
    // Rescale x only (horizontal pan/zoom; y stays fixed)
    var t = ev.transform;
    var newX = t.rescaleX(tlXScaleOrig);
    tlXScale = newX;

    // Update topic circles (only cx changes)
    d3.selectAll('.topic-circle').attr('cx', function(d) { return newX(d._date); });

    // Update topic labels (x position tracks circle + offset)
    d3.selectAll('.topic-label').attr('x', function(d) { return newX(d._date) + rScale(d.inf) + 3; });

    // Update milestone markers
    d3.selectAll('.milestone-marker').attr('points', function(d) {
      var r = rScale(d.inf) + 4;
      return starPoints(newX(d._date), d._yPos, r, r * 0.5, 4);
    });

    // Update edges
    d3.selectAll('.edge-line')
      .attr('x1', function(d) { return newX(d.sd); })
      .attr('x2', function(d) { return newX(d.td); });

    // Update era backgrounds
    eraRects.forEach(function(r) {
      var d = r.datum();
      r.attr('x', newX(d.start)).attr('width', Math.max(0, newX(d.end) - newX(d.start)));
    });
    eraTexts.forEach(function(txt) {
      var d = txt.datum();
      txt.attr('x', (newX(d.start) + newX(d.end)) / 2);
    });

    // Update fork lines + labels + hover areas
    forkLines.forEach(function(l) { var d = l.datum(); l.attr('x1', newX(d)).attr('x2', newX(d)); });
    forkLabels.forEach(function(l) { var d = l.datum(); l.attr('x', newX(d)); });
    forkHoverLines.forEach(function(l) { var d = l.datum(); l.attr('x1', newX(d.date)).attr('x2', newX(d.date)); });

    // Update ethresear.ch live marker
    var liveX = newX(liveLine.datum().date);
    liveLine.attr('x1', liveX).attr('x2', liveX);
    liveLabel.attr('x', liveX);

    // Update histogram bars
    var zoomedBarW = Math.max(1, (newX(new Date(2020, 1, 1)) - newX(new Date(2020, 0, 1))) * 0.85);
    d3.selectAll('.histogram-bar')
      .attr('x', function(d) { return newX(d.date); })
      .attr('width', zoomedBarW);

    // Update EIP squares
    d3.selectAll('.eip-square').attr('x', function(d) {
      if (!d || !d._eipDate) return 0;
      var sz = eipRScale ? eipRScale(d.inf) * 1.4 : 6;
      return newX(d._eipDate) - sz / 2;
    });
    // Update EIP labels
    d3.selectAll('.eip-label').attr('x', function(d) {
      if (!d || !d._eipDate) return 0;
      var sz = eipRScale ? eipRScale(d.inf) * 1.4 : 6;
      return newX(d._eipDate) + sz / 2 + 3;
    });
    // Update cross-ref edges
    d3.selectAll('.cross-ref-edge')
      .attr('x1', function(d) { return d && d.eipDate ? newX(d.eipDate) : 0; })
      .attr('x2', function(d) { return d && d.topicDate ? newX(d.topicDate) : 0; });
    d3.selectAll('.focus-eip-topic-edge')
      .attr('x1', function(d) { return d && d.eipDate ? newX(d.eipDate) : 0; })
      .attr('x2', function(d) { return d && d.topicDate ? newX(d.topicDate) : 0; });

    // Update Magicians triangles + labels + cross-ref edges
    d3.selectAll('.magicians-triangle').attr('d', function(d) {
      if (!d || !d._magDate) return '';
      var r = magiciansRScale ? magiciansRScale(d._magInf || 0) : 6;
      return trianglePath(newX(d._magDate), d._magYPos, r);
    });
    d3.selectAll('.magicians-label').attr('x', function(d) {
      if (!d || !d._magDate) return 0;
      var r = magiciansRScale ? magiciansRScale(d._magInf || 0) : 6;
      return newX(d._magDate) + r + 3;
    });
    d3.selectAll('.magicians-ref-edge')
      .attr('x1', function(d) { return d && d.magDate ? newX(d.magDate) : 0; })
      .attr('x2', function(d) { return d && d.topicDate ? newX(d.topicDate) : 0; });

    // Update paper diamonds + labels + ref edges
    d3.selectAll('.paper-diamond').attr('d', function(d) {
      if (!d || !d._paperDate) return '';
      var r = paperTimelineRScale ? paperTimelineRScale(d._paperInf || paperTimelineInfluence(d)) : 5;
      return diamondPath(newX(d._paperDate), d._paperYPos, r);
    });
    d3.selectAll('.paper-hit').attr('d', function(d) {
      if (!d || !d._paperDate) return '';
      var r = paperTimelineRScale ? paperTimelineRScale(d._paperInf || paperTimelineInfluence(d)) : 5;
      return diamondPath(newX(d._paperDate), d._paperYPos, Math.max(6.5, r + 2.5));
    });
    d3.selectAll('.paper-label').attr('x', function(d) {
      if (!d || !d._paperDate) return 0;
      var r = paperTimelineRScale ? paperTimelineRScale(d._paperInf || paperTimelineInfluence(d)) : 5;
      return newX(d._paperDate) + r + 3;
    });
    d3.selectAll('.paper-topic-ref-edge')
      .attr('x1', function(d) { return d && d.paperDate ? newX(d.paperDate) : 0; })
      .attr('x2', function(d) { return d && d.topicDate ? newX(d.topicDate) : 0; });
    d3.selectAll('.paper-eip-ref-edge')
      .attr('x1', function(d) { return d && d.paperDate ? newX(d.paperDate) : 0; })
      .attr('x2', function(d) { return d && d.eipDate ? newX(d.eipDate) : 0; });
    d3.selectAll('.paper-paper-edge')
      .attr('x1', function(d) { return d && d.paperDateA ? newX(d.paperDateA) : 0; })
      .attr('x2', function(d) { return d && d.paperDateB ? newX(d.paperDateB) : 0; });

    // Update x-axis with adaptive tick density
    var axisFn;
    if (t.k > 4) {
      axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(1)).tickFormat(d3.timeFormat('%b %Y'));
    } else if (t.k > 2) {
      axisFn = d3.axisBottom(newX).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat('%b %Y'));
    } else {
      axisFn = d3.axisBottom(newX).ticks(d3.timeYear.every(1)).tickFormat(d3.timeFormat('%Y'));
    }
    xAxisG.call(axisFn);
    xAxisG.selectAll('text').attr('fill', '#666').attr('font-size', 12);
    xAxisG.selectAll('.domain, .tick line').attr('stroke', '#333');
  }
}

function hasFocusedEntity() {
  return pinnedTopicId !== null || activeEipNum !== null || activeMagiciansId !== null || !!activePaperId;
}

function clearFocusedEntityState(options) {
  var opts = options || {};
  var panel = document.getElementById('detail-panel');
  if (!opts.keepDetailOpen && panel) panel.classList.remove('open');
  pinnedTopicId = null;
  activeEipNum = null;
  activeMagiciansId = null;
  activePaperId = null;
  if (similarActive) clearSimilar();
  else applyFilters();
  if (showPapers) refreshNetworkForFocusChange();
  if (!opts.skipHash) updateHash();
}

function focusedEntityDescriptor() {
  if (pinnedTopicId !== null) {
    var tid = Number(pinnedTopicId);
    return {kind: 'topic', key: isNaN(tid) ? pinnedTopicId : tid};
  }
  if (activeEipNum !== null) {
    return {kind: 'eip', key: 'eip_' + String(activeEipNum)};
  }
  if (activeMagiciansId !== null) {
    var mid = Number(activeMagiciansId);
    return {kind: 'magicians', key: isNaN(mid) ? activeMagiciansId : mid};
  }
  if (activePaperId) {
    return {kind: 'paper', key: paperNodeId(activePaperId)};
  }
  return null;
}

function isHoverBlockedByFocusedEntity(kind, node) {
  if (!canApplyFocusedHighlightInView()) return false;
  var focus = focusedEntityDescriptor();
  if (!focus) return false;
  if (kind === 'topic') {
    var topicId = node && node.id !== undefined ? Number(node.id) : NaN;
    if (focus.kind === 'topic' && !isNaN(topicId) && topicId === Number(focus.key)) return false;
    return true;
  }
  if (kind === 'eip') {
    var eid = eipNodeId(node);
    if (focus.kind === 'eip' && String(eid) === String(focus.key)) return false;
    return true;
  }
  if (kind === 'magicians') {
    var mid = magiciansTopicId(node);
    if (focus.kind === 'magicians' && Number(mid) === Number(focus.key)) return false;
    return true;
  }
  if (kind === 'paper') {
    var pid = paperIdFromNode(node);
    if (focus.kind === 'paper' && String(paperNodeId(pid)) === String(focus.key)) return false;
    return true;
  }
  return true;
}

function buildEntityFocusContext(kind, node) {
  var linkedTopics = new Set();
  var linkedEips = new Set();
  var linkedMagicians = new Set();
  var linkedPapers = new Set();
  var entityTopicId = null;
  var entityNodeId = null;
  var entityMagId = null;
  var entityEipNum = null;
  var entityPaperId = null;
  function rankPaperIds(ids, limit) {
    return Array.from(ids || [])
      .map(function(pid) { return String(pid || '').trim(); })
      .filter(function(pid) { return !!(pid && (DATA.papers || {})[pid]); })
      .sort(function(a, b) {
        var pa = (DATA.papers || {})[a] || {};
        var pb = (DATA.papers || {})[b] || {};
        var ib = paperTimelineInfluence(pb);
        var ia = paperTimelineInfluence(pa);
        if (ib !== ia) return ib - ia;
        var rb = Number(pb.rs || 0);
        var ra = Number(pa.rs || 0);
        if (rb !== ra) return rb - ra;
        return Number(pb.cb || 0) - Number(pa.cb || 0);
      })
      .slice(0, Math.max(0, Number(limit || 0)));
  }
  function addRankedPaperIds(ids, limit) {
    rankPaperIds(ids, limit).forEach(function(pid) { linkedPapers.add(pid); });
  }

  if (kind === 'topic') {
    var tid = Number(node && node.id);
    if (!isFinite(tid)) return null;
    var t = DATA.topics[tid] || node;
    entityTopicId = tid;
    linkedTopics.add(tid);
    (topicEdgeIndex[String(tid)] || new Set()).forEach(function(otherTid) {
      linkedTopics.add(Number(otherTid));
    });

    var topicEips = uniqueSortedNumbers((t.eips || []).concat(t.peips || []));
    var topicPaperCandidates = new Set();
    topicEips.forEach(function(eipNum) {
      linkedEips.add('eip_' + String(eipNum));
      (eipToMagiciansRefs[String(eipNum)] || new Set()).forEach(function(mid) { linkedMagicians.add(Number(mid)); });
      var eMeta = (DATA.eipCatalog || {})[String(eipNum)] || {};
      if (eMeta.mt !== undefined && eMeta.mt !== null && !isNaN(Number(eMeta.mt))) linkedMagicians.add(Number(eMeta.mt));
      (EIP_TO_PAPER_IDS[String(eipNum)] || new Set()).forEach(function(pid) { topicPaperCandidates.add(String(pid)); });
    });
    addRankedPaperIds(topicPaperCandidates, 34);

    relatedPapersForTopic(tid).slice(0, 12).forEach(function(row) {
      var pid = String((((row || {}).paper) || {}).id || '');
      if (!pid) return;
      linkedPapers.add(pid);
      (PAPER_TO_EIP_IDS[pid] || []).forEach(function(eipNum) {
        linkedEips.add('eip_' + String(eipNum));
      });
      (PAPER_TO_MAGICIANS_IDS[pid] || []).forEach(function(mid) {
        linkedMagicians.add(Number(mid));
      });
    });
  } else if (kind === 'eip') {
    entityNodeId = eipNodeId(node);
    var eipNum = eipNumFromNode(node);
    if (eipNum === null || isNaN(eipNum)) return null;
    entityEipNum = Number(eipNum);
    (eipToTopicIds[String(eipNum)] || []).forEach(function(tid) { linkedTopics.add(Number(tid)); });
    (eipToMagiciansRefs[String(eipNum)] || new Set()).forEach(function(mid) { linkedMagicians.add(Number(mid)); });
    var eipMeta = (DATA.eipCatalog || {})[String(eipNum)];
    if (eipMeta && eipMeta.mt) linkedMagicians.add(Number(eipMeta.mt));
    addRankedPaperIds(EIP_TO_PAPER_IDS[String(eipNum)] || new Set(), 40);
    relatedPapersForEip(Number(eipNum), eipMeta || {}).slice(0, 12).forEach(function(row) {
      var pid = String((((row || {}).paper) || {}).id || '');
      if (pid) linkedPapers.add(pid);
    });
    ((DATA.eipGraph || {}).edges || []).forEach(function(edge) {
      if (!edge || edge.type !== 'eip_requires') return;
      if (edge.source === entityNodeId && edge.target) linkedEips.add(String(edge.target));
      if (edge.target === entityNodeId && edge.source) linkedEips.add(String(edge.source));
    });
  } else if (kind === 'magicians') {
    entityMagId = magiciansTopicId(node);
    if (entityMagId === null || isNaN(entityMagId)) return null;
    linkedMagicians.add(Number(entityMagId));
    var mt = (DATA.magiciansTopics || {})[String(entityMagId)] || node;
    (mt.er || []).forEach(function(tid) { linkedTopics.add(Number(tid)); });
    var magPaperCandidates = new Set();
    (magiciansLinkedEips(mt) || []).forEach(function(eipNum) {
      linkedEips.add('eip_' + String(eipNum));
      (EIP_TO_PAPER_IDS[String(eipNum)] || new Set()).forEach(function(pid) { magPaperCandidates.add(String(pid)); });
    });
    addRankedPaperIds(magPaperCandidates, 32);
    relatedPapersForMagiciansTopic(Number(entityMagId), mt).slice(0, 10).forEach(function(row) {
      var pid = String((((row || {}).paper) || {}).id || '');
      if (pid) linkedPapers.add(pid);
    });
  } else if (kind === 'paper') {
    var pid = String((node && (node._paperId || node.paperId || node.id)) || '').replace(/^paper_/, '').trim();
    if (!pid) return null;
    var p = (DATA.papers || {})[pid] || node;
    if (!p) return null;
    entityPaperId = pid;
    linkedPapers.add(pid);
    // Keep direct peer-paper neighbors visible when focusing a paper; otherwise
    // edges can appear to end in empty space because peer nodes are dimmed away.
    (PAPER_TO_PAPER_IDS[pid] || []).slice(0, 18).forEach(function(peerPid) {
      if (peerPid) linkedPapers.add(String(peerPid));
    });
    (PAPER_TO_EIP_IDS[pid] || uniqueSortedNumbers(p.eq || [])).forEach(function(eipNum) {
      linkedEips.add('eip_' + String(eipNum));
    });
    (PAPER_TO_TOPIC_IDS[pid] || []).forEach(function(tid) { linkedTopics.add(Number(tid)); });
    (PAPER_TO_MAGICIANS_IDS[pid] || []).forEach(function(mid) { linkedMagicians.add(Number(mid)); });
  } else {
    return null;
  }

  return {
    kind: kind,
    entityTopicId: entityTopicId,
    entityNodeId: entityNodeId,
    entityMagId: entityMagId,
    entityEipNum: entityEipNum,
    entityPaperId: entityPaperId,
    linkedTopics: linkedTopics,
    linkedEips: linkedEips,
    linkedMagicians: linkedMagicians,
    linkedPapers: linkedPapers,
  };
}

function applyEntityFocusTimeline(context) {
  if (!context) return;
  var hasFilter = activeThread || hasAuthorFilter() || activeCategory || activeTag || minInfluence > 0;
  var isPaperFocus = context.kind === 'paper';
  clearTimelineAuxEdgeMarkers();

  var topicOp = {};
  d3.selectAll('.topic-circle').each(function(t) {
    if (context.kind === 'topic' && context.entityTopicId !== null && Number(t.id) === Number(context.entityTopicId)) {
      topicOp[t.id] = 1;
      return;
    }
    if (context.linkedTopics.has(t.id) && (!hasFilter || topicMatchesFilter(t))) { topicOp[t.id] = 0.84; return; }
    if (hasFilter && !topicMatchesFilter(t)) { topicOp[t.id] = 0.03; return; }
    topicOp[t.id] = 0.06;
  });
  d3.selectAll('.topic-circle')
    .attr('opacity', function(t) { return topicOp[t.id]; })
    .attr('stroke-width', function(t) {
      var base = t.mn ? 1 : 0.5;
      return context.linkedTopics.has(t.id) ? Math.max(1.4, base) : base;
    });
  syncLabelsFromMap(topicOp);

  d3.selectAll('.edge-line')
    .style('display', isPaperFocus ? 'none' : null)
    .attr('stroke-opacity', function(e) {
      if (isPaperFocus) return 0;
      if (context.kind === 'topic' && context.entityTopicId !== null) {
        var isFocusEdge = (Number(e.source) === Number(context.entityTopicId) || Number(e.target) === Number(context.entityTopicId));
        if (isFocusEdge) return 0.86;
      }
      if (context.linkedTopics.has(e.source) && context.linkedTopics.has(e.target)) return 0.62;
      return 0.02;
    })
    .attr('stroke-width', function(e) {
      if (isPaperFocus) return 0.6;
      if (context.kind === 'topic' && context.entityTopicId !== null) {
        var isFocusEdge = (Number(e.source) === Number(context.entityTopicId) || Number(e.target) === Number(context.entityTopicId));
        if (isFocusEdge) return 2.0;
      }
      return (context.linkedTopics.has(e.source) && context.linkedTopics.has(e.target)) ? 1.9 : 0.9;
    })
    .attr('stroke', function(e) {
      if (isPaperFocus) return '#556';
      if (context.kind === 'topic' && context.entityTopicId !== null) {
        var isFocusEdge = (Number(e.source) === Number(context.entityTopicId) || Number(e.target) === Number(context.entityTopicId));
        if (isFocusEdge) return '#9fc0ff';
      }
      if (context.linkedTopics.has(e.source) && context.linkedTopics.has(e.target)) return '#9fc0ff';
      return '#556';
    })
    .attr('marker-end', function(e) {
      if (isPaperFocus) return null;
      if (context.kind === 'topic' && context.entityTopicId !== null) {
        var isFocusEdge = (Number(e.source) === Number(context.entityTopicId) || Number(e.target) === Number(context.entityTopicId));
        if (isFocusEdge) return 'url(#arrow-highlight)';
      }
      return (context.linkedTopics.has(e.source) && context.linkedTopics.has(e.target)) ? 'url(#arrow-highlight)' : 'url(#arrow-default)';
    });

  d3.selectAll('.eip-square').attr('opacity', function(e) {
    if (!showEips || !eipMatchesFilter(e)) return 0.05;
    var eid = eipNodeId(e);
    if (context.kind === 'eip' && context.entityNodeId && String(eid) === String(context.entityNodeId)) return 1;
    if (context.linkedEips.has(String(eid))) return 0.92;
    return 0.15;
  });

  d3.selectAll('.magicians-triangle').attr('opacity', function(mt) {
    if (!showMagicians || !magiciansMatchesFilter(mt)) return 0.05;
    var mid = magiciansTopicId(mt);
    if (context.kind === 'magicians' && context.entityMagId !== null && Number(mid) === Number(context.entityMagId)) return 1;
    if (context.linkedMagicians.has(mid)) return 0.92;
    return 0.15;
  });

  d3.selectAll('.paper-diamond').attr('opacity', function(p) {
    var pid = String((p && (p._paperId || p.id)) || '').replace(/^paper_/, '');
    var paper = (DATA.papers || {})[pid] || p;
    if (!showPapers || !paperMatchesTimelineFilter(paper)) return 0.05;
    if (context.kind === 'paper' && context.entityPaperId && String(pid) === String(context.entityPaperId)) return 1;
    if (context.linkedPapers.has(String(pid))) return 0.9;
    return 0.045;
  });
  d3.selectAll('.paper-label').attr('opacity', function(p) {
    var pid = String((p && (p._paperId || p.id)) || '').replace(/^paper_/, '');
    var paper = (DATA.papers || {})[pid] || p;
    if (!showPapers || !paperMatchesTimelineFilter(paper)) return 0;
    if (context.kind === 'paper' && context.entityPaperId && String(pid) === String(context.entityPaperId)) return 0.95;
    return context.linkedPapers.has(String(pid)) ? 0.78 : 0;
  });

  d3.selectAll('.cross-ref-edge')
    .style('display', function(ed) {
      if (isPaperFocus) return 'none';
      if (!ed) return 'none';
      if (!timelineTopicVisible(ed.topicId)) return 'none';
      if (!timelineEipVisibleByNum(ed.eipNum)) return 'none';
      return null;
    })
    .attr('stroke', '#8fb4ff')
    .attr('stroke-opacity', function(ed) {
      if (!showPosts || !showEips) return 0.01;
      if (!ed) return 0.02;
      if (!timelineTopicVisible(ed.topicId) || !timelineEipVisibleByNum(ed.eipNum)) return 0.02;
      if (context.kind === 'eip') {
        return String(ed.eipNodeId) === String(context.entityNodeId) ? 0.92 : 0.02;
      }
      return (context.linkedTopics.has(ed.topicId) && context.linkedEips.has(String(ed.eipNodeId))) ? 0.70 : 0.02;
    })
    .attr('stroke-width', function(ed) {
      if (!showPosts || !showEips) return 0.4;
      if (!ed) return 0.6;
      if (!timelineTopicVisible(ed.topicId) || !timelineEipVisibleByNum(ed.eipNum)) return 0.6;
      if (context.kind === 'eip') {
        return String(ed.eipNodeId) === String(context.entityNodeId) ? 1.9 : 0.6;
      }
      return (context.linkedTopics.has(ed.topicId) && context.linkedEips.has(String(ed.eipNodeId))) ? 1.5 : 0.6;
    });

  d3.selectAll('.magicians-ref-edge')
    .style('display', function(ed) {
      if (isPaperFocus) return 'none';
      if (!ed || !ed.magTopic) return 'none';
      if (!timelineMagiciansVisibleById(magiciansTopicId(ed.magTopic))) return 'none';
      if (!timelineTopicVisible(ed.topicId)) return 'none';
      return null;
    })
    .attr('stroke', '#bf93df')
    .attr('stroke-opacity', function(ed) {
      if (!showPosts || !showMagicians) return 0.01;
      if (!ed || !ed.magTopic) return 0.02;
      if (!timelineMagiciansVisibleById(magiciansTopicId(ed.magTopic)) || !timelineTopicVisible(ed.topicId)) return 0.02;
      if (context.kind === 'magicians') {
        return Number(magiciansTopicId(ed.magTopic)) === Number(context.entityMagId) ? 0.90 : 0.02;
      }
      return context.linkedMagicians.has(magiciansTopicId(ed.magTopic)) ? 0.68 : 0.02;
    })
    .attr('stroke-width', function(ed) {
      if (!showPosts || !showMagicians) return 0.4;
      if (!ed || !ed.magTopic) return 0.6;
      if (!timelineMagiciansVisibleById(magiciansTopicId(ed.magTopic)) || !timelineTopicVisible(ed.topicId)) return 0.6;
      if (context.kind === 'magicians') {
        return Number(magiciansTopicId(ed.magTopic)) === Number(context.entityMagId) ? 1.7 : 0.6;
      }
      return context.linkedMagicians.has(magiciansTopicId(ed.magTopic)) ? 1.4 : 0.6;
    });

  d3.selectAll('.paper-topic-ref-edge')
    .style('display', function(ed) {
      if (!ed) return 'none';
      if (!timelinePaperVisibleById(ed.paperId)) return 'none';
      if (!timelineTopicVisible(ed.topicId)) return 'none';
      if (isPaperFocus && String(ed.paperId) !== String(context.entityPaperId || '')) return 'none';
      return null;
    })
    .attr('stroke', '#8eb8ff')
    .attr('stroke-opacity', function(ed) {
      if (!showPosts || !showPapers || !ed) return 0.01;
      if (!timelinePaperVisibleById(ed.paperId) || !timelineTopicVisible(ed.topicId)) return 0.02;
      if (isPaperFocus) return String(ed.paperId) === String(context.entityPaperId) ? 0.90 : 0;
      if (context.kind === 'eip') {
        var edgeEips = Array.isArray(ed.eipNodeIds) ? ed.eipNodeIds : [];
        var linkedToFocusedEip = edgeEips.some(function(eid) {
          return String(eid) === String(context.entityNodeId || '');
        });
        return linkedToFocusedEip ? 0.74 : 0.02;
      }
      if (context.kind === 'magicians') return context.linkedMagicians.has(Number(ed.magId || -1)) ? 0.68 : 0.02;
      return context.linkedPapers.has(String(ed.paperId)) ? 0.66 : 0.02;
    })
    .attr('stroke-width', function(ed) {
      if (!showPosts || !showPapers || !ed) return 0.5;
      if (isPaperFocus) return String(ed.paperId) === String(context.entityPaperId) ? 1.8 : 0.6;
      if (context.kind === 'eip') {
        var edgeEips = Array.isArray(ed.eipNodeIds) ? ed.eipNodeIds : [];
        var linkedToFocusedEip = edgeEips.some(function(eid) {
          return String(eid) === String(context.entityNodeId || '');
        });
        return linkedToFocusedEip ? 1.5 : 0.6;
      }
      return context.linkedPapers.has(String(ed.paperId)) ? 1.4 : 0.6;
    });

  d3.selectAll('.paper-eip-ref-edge')
    .style('display', function(ed) {
      if (!ed) return 'none';
      if (!timelinePaperVisibleById(ed.paperId)) return 'none';
      if (!timelineEipVisibleByNum(ed.eipNum)) return 'none';
      if (isPaperFocus && String(ed.paperId) !== String(context.entityPaperId || '')) return 'none';
      return null;
    })
    .attr('stroke', '#94c3ff')
    .attr('stroke-opacity', function(ed) {
      if (!showEips || !showPapers || !ed) return 0.01;
      if (!timelinePaperVisibleById(ed.paperId) || !timelineEipVisibleByNum(ed.eipNum)) return 0.02;
      if (isPaperFocus) return String(ed.paperId) === String(context.entityPaperId) ? 0.88 : 0;
      if (context.kind === 'eip') return String(ed.eipNodeId || '') === String(context.entityNodeId || '') ? 0.86 : 0.02;
      if (context.kind === 'magicians') return context.linkedMagicians.has(Number(ed.magId || -1)) ? 0.66 : 0.02;
      return context.linkedPapers.has(String(ed.paperId)) ? 0.66 : 0.02;
    })
    .attr('stroke-width', function(ed) {
      if (!showEips || !showPapers || !ed) return 0.5;
      if (isPaperFocus) return String(ed.paperId) === String(context.entityPaperId) ? 1.8 : 0.6;
      if (context.kind === 'eip') return String(ed.eipNodeId || '') === String(context.entityNodeId || '') ? 1.8 : 0.6;
      return context.linkedPapers.has(String(ed.paperId)) ? 1.3 : 0.6;
    });

  d3.selectAll('.paper-paper-edge')
    .style('display', function(ed) {
      if (!showPapers || !ed) return 'none';
      if (!timelinePaperVisibleById(ed.paperA)) return 'none';
      if (!timelinePaperVisibleById(ed.paperB)) return 'none';
      if (!isPaperFocus) return null;
      var focusPid = String(context.entityPaperId || '');
      return (String(ed.paperA) === focusPid || String(ed.paperB) === focusPid) ? null : 'none';
    })
    .attr('stroke', '#8fb7ef')
    .attr('stroke-opacity', function(ed) {
      if (!showPapers || !ed) return 0.01;
      if (!timelinePaperVisibleById(ed.paperA) || !timelinePaperVisibleById(ed.paperB)) return 0.02;
      if (isPaperFocus) {
        var pid = String(context.entityPaperId || '');
        return (String(ed.paperA) === pid || String(ed.paperB) === pid) ? 0.72 : 0;
      }
      return (context.linkedPapers.has(String(ed.paperA)) && context.linkedPapers.has(String(ed.paperB))) ? 0.40 : 0.03;
    })
    .attr('stroke-width', function(ed) {
      if (!showPapers || !ed) return 0.5;
      if (isPaperFocus) {
        var pid = String(context.entityPaperId || '');
        return (String(ed.paperA) === pid || String(ed.paperB) === pid) ? 1.45 : 0.6;
      }
      return (context.linkedPapers.has(String(ed.paperA)) && context.linkedPapers.has(String(ed.paperB))) ? 1.1 : 0.6;
    });

  updateFocusedTimelineExtraEdges(context, hasFilter);
}

function clearFocusedTimelineExtraEdges() {
  d3.selectAll('.focus-eip-topic-edge').remove();
}

function updateFocusedTimelineExtraEdges(context, hasFilter) {
  var zoomG = d3.select('#timeline-view svg g g[clip-path] g');
  if (zoomG.empty()) return;
  var layer = zoomG.select('.entity-focus-link-layer');
  if (layer.empty()) layer = zoomG.append('g').attr('class', 'entity-focus-link-layer');

  if (!context || context.kind !== 'eip' || context.entityEipNum === null || context.entityEipNum === undefined) {
    layer.selectAll('.focus-eip-topic-edge').remove();
    return;
  }

  var eipMeta = (DATA.eipCatalog || {})[String(context.entityEipNum)];
  if (!eipMeta || !eipMeta._eipDate || eipMeta._eipYPos === undefined) {
    layer.selectAll('.focus-eip-topic-edge').remove();
    return;
  }

  var rows = [];
  context.linkedTopics.forEach(function(tid) {
    var t = DATA.topics[tid];
    if (!t || !t._date || t._yPos === undefined) return;
    if (hasFilter && !topicMatchesFilter(t)) return;
    rows.push({
      key: String(context.entityEipNum) + ':' + String(tid),
      eipDate: eipMeta._eipDate,
      eipY: eipMeta._eipYPos,
      topicDate: t._date,
      topicY: t._yPos,
    });
  });

  if (rows.length > 220) {
    rows.sort(function(a, b) {
      return Math.abs(a.topicY - a.eipY) - Math.abs(b.topicY - b.eipY);
    });
    rows = rows.slice(0, 220);
  }

  var sel = layer.selectAll('.focus-eip-topic-edge')
    .data(rows, function(d) { return d.key; });
  sel.exit().remove();
  sel.enter().append('line')
    .attr('class', 'focus-eip-topic-edge')
    .attr('marker-end', null)
    .attr('stroke', '#a8c4ff')
    .attr('stroke-opacity', 0.56)
    .attr('stroke-width', 1.2)
    .attr('stroke-dasharray', '4 2')
    .merge(sel)
    .attr('x1', function(d) { return tlXScale(d.eipDate); })
    .attr('y1', function(d) { return d.eipY; })
    .attr('x2', function(d) { return tlXScale(d.topicDate); })
    .attr('y2', function(d) { return d.topicY; })
    .style('display', (showPosts && showEips) ? null : 'none');
}

function applyFocusedEntityHighlightTimeline() {
  if (pinnedTopicId !== null) {
    clearFocusedTimelineExtraEdges();
    applyPinnedHighlightTimeline();
    return;
  }
  if (activeEipNum !== null) {
    if (!showEips) {
      clearFocusedTimelineExtraEdges();
      filterTimeline(true);
      return;
    }
    var eipNum = Number(activeEipNum);
    if (!isNaN(eipNum)) {
      var eipMeta = (DATA.eipCatalog || {})[String(eipNum)] || {};
      var ctxEip = buildEntityFocusContext('eip', {
        id: 'eip_' + String(eipNum),
        _eipNum: eipNum,
        inf: eipMeta.inf || 0,
        s: eipMeta.s || null,
      });
      applyEntityFocusTimeline(ctxEip);
    }
    return;
  }
  if (activeMagiciansId !== null) {
    if (!showMagicians) {
      clearFocusedTimelineExtraEdges();
      filterTimeline(true);
      return;
    }
    var mid = Number(activeMagiciansId);
    if (!isNaN(mid)) {
      var mt = (DATA.magiciansTopics || {})[String(mid)] || {id: mid};
      var ctxMag = buildEntityFocusContext('magicians', mt);
      applyEntityFocusTimeline(ctxMag);
    }
    return;
  }
  if (activePaperId) {
    if (!showPapers) {
      clearFocusedTimelineExtraEdges();
      filterTimeline(true);
      return;
    }
    var paper = (DATA.papers || {})[String(activePaperId)];
    if (paper) {
      var ctxPaper = buildEntityFocusContext('paper', paper);
      applyEntityFocusTimeline(ctxPaper);
    }
    return;
  }
  clearFocusedTimelineExtraEdges();
}

function focusedNetworkNodeId() {
  if (pinnedTopicId !== null) return Number(pinnedTopicId);
  if (activeEipNum !== null) return 'eip_' + String(activeEipNum);
  if (activeMagiciansId !== null) return magiciansNodeId(activeMagiciansId);
  if (activePaperId) return paperNodeId(activePaperId);
  return null;
}

function applyFocusedEntityHighlightNetwork() {
  if (pinnedTopicId !== null) {
    applyPinnedHighlightNetwork();
    return;
  }
  if (activeEipNum !== null && !showEips) return;
  if (activeMagiciansId !== null && !showMagicians) return;
  if (activePaperId && !showPapers) return;
  var focusId = focusedNetworkNodeId();
  if (focusId === null || focusId === undefined) return;

  var focusExists = false;
  d3.selectAll('.net-node').each(function(n) {
    if (n && n.id === focusId) focusExists = true;
  });
  if (!focusExists) return;

  var connected = new Set([focusId]);
  d3.selectAll('.net-link').each(function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (sid === focusId) connected.add(tid);
    if (tid === focusId) connected.add(sid);
  });

  d3.selectAll('.net-node .net-shape').attr('opacity', function(n) {
    return connected.has(n.id) ? 1 : 0.08;
  });

  d3.selectAll('.net-link').attr('stroke-opacity', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === focusId || tid === focusId) ? 0.92 : 0.02;
  }).attr('stroke-width', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === focusId || tid === focusId) ? 2.2 : 0.9;
  }).attr('stroke', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === focusId || tid === focusId) ? '#a7c8ff' : '#334';
  }).attr('marker-end', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (l.edgeType === 'paper_paper') return null;
    return (sid === focusId || tid === focusId) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
  });
}

function applyFocusedEntityHighlight() {
  if (!hasFocusedEntity()) return;
  if (activeView === 'timeline') applyFocusedEntityHighlightTimeline();
  else if (activeView === 'network') applyFocusedEntityHighlightNetwork();
}

function onTimelineHover(ev, d, entering) {
  var hasFilter = activeThread || hasAuthorFilter() || activeCategory || activeTag;
  if (entering) {
    hoveredTopicId = d.id;
    showTooltip(ev, d);
    if (hasFocusedEntity() && isHoverBlockedByFocusedEntity('topic', d)) return;

    // If a filter is active and this node doesn't match, only show tooltip
    if (hasFilter && !topicMatchesFilter(d)) return;

    // Highlight this topic and its direct connections
    const connected = topicEdgeIndex[String(d.id)] || new Set();

    var targetOp = {};
    d3.selectAll('.topic-circle').each(function(t) {
      if (t.id === d.id) { targetOp[t.id] = 1; return; }
      if (connected.has(t.id) && (!hasFilter || topicMatchesFilter(t))) { targetOp[t.id] = 0.8; return; }
      if (hasFilter && !topicMatchesFilter(t)) { targetOp[t.id] = 0.03; return; }
      targetOp[t.id] = 0.12;
    });
    d3.selectAll('.topic-circle').attr('opacity', function(t) { return targetOp[t.id]; });

    d3.selectAll('.edge-line')
      .attr('stroke-opacity', function(e) {
        if (e.source === d.id || e.target === d.id) return 0.85;
        return 0.02;
      })
      .attr('stroke-width', function(e) {
        return (e.source === d.id || e.target === d.id) ? 2.0 : 0.9;
      })
      .attr('stroke', function(e) {
        if (e.source === d.id || e.target === d.id) return '#9fc0ff';
        return '#556';
      })
      .attr('marker-end', function(e) {
        if (e.source === d.id || e.target === d.id) return 'url(#arrow-highlight)';
        return 'url(#arrow-default)';
      });
    syncLabelsFromMap(targetOp);
  } else {
    hoveredTopicId = null;
    hideTooltip();
    if (hasFocusedEntity()) {
      applyFocusedEntityHighlightTimeline();
      return;
    }
    // If we didn't change opacities (dimmed node hover), nothing to restore
    if (hasFilter && !topicMatchesFilter(d)) return;
    if (pinnedTopicId) {
      applyPinnedHighlightTimeline();
    } else {
      filterTimeline();
    }
  }
}

function onTimelineEntityHover(ev, node, kind, entering) {
  if (entering) {
    if (kind === 'eip') {
      showEipTooltip(ev, node);
    } else if (kind === 'magicians') {
      var magId = magiciansTopicId(node);
      if (magId !== null && !isNaN(magId)) {
        var mt = (DATA.magiciansTopics || {})[String(magId)] || node;
        showMagiciansTooltip(ev, mt);
      } else showMagiciansTooltip(ev, node);
    } else if (kind === 'paper') {
      var paper = paperFromNode(node) || node;
      showPaperTooltip(ev, paper, node);
    } else {
      return;
    }

    if (hasFocusedEntity() && isHoverBlockedByFocusedEntity(kind, node)) return;

    var hasFilter = activeThread || hasAuthorFilter() || activeCategory || activeTag || minInfluence > 0;
    // If a filter is active and this node doesn't match, only show tooltip.
    if (hasFilter) {
      if (kind === 'eip' && !eipMatchesFilter(node)) return;
      if (kind === 'magicians' && !magiciansMatchesFilter(node)) return;
      if (kind === 'paper' && !paperMatchesTimelineFilter(node)) return;
    }
    var context = buildEntityFocusContext(kind, node);
    if (!context && kind === 'paper') {
      var fallbackPaper = paperFromNode(node);
      if (fallbackPaper) context = buildEntityFocusContext('paper', fallbackPaper);
    }
    if (!context) return;
    applyEntityFocusTimeline(context);
  } else {
    hideTooltip();
    if (hasFocusedEntity()) {
      applyFocusedEntityHighlightTimeline();
    } else {
      filterTimeline();
    }
  }
}

function topicMatchesFilter(t) {
  if (minInfluence > 0 && (t.inf || 0) < minInfluence) return false;
  if (activeThread && t.th !== activeThread) return false;
  var activeEthAuthors = getActiveEthAuthorSet();
  var activeEipAuthors = getActiveEipAuthorSet();
  if (hasAuthorFilter()) {
    var resolved = topicResolvedCoauthorIdentities(t);
    var matchesEth = activeEthAuthors.size > 0 &&
      (activeEthAuthors.has(t.a) || Array.from(activeEthAuthors).some(function(username) { return resolved.eth.has(username); }));
    var matchesEip = activeEipAuthors.size > 0 &&
      Array.from(activeEipAuthors).some(function(name) { return resolved.eip.has(name); });
    if (!matchesEth && !matchesEip) return false;
  }
  if (activeCategory && t.cat !== activeCategory) return false;
  if (activeTag && !(t.tg || []).includes(activeTag)) return false;
  return true;
}

// === PINNED TOPIC HIGHLIGHTING ===
function applyPinnedHighlight() {
  if (!pinnedTopicId) return;
  if (activeView === 'timeline') applyPinnedHighlightTimeline();
  else if (activeView === 'network') applyPinnedHighlightNetwork();
}

function applyPinnedHighlightTimeline() {
  if (!pinnedTopicId) return;
  var topic = DATA.topics[Number(pinnedTopicId)];
  if (!topic) return;
  var context = buildEntityFocusContext('topic', topic);
  if (!context) return;
  applyEntityFocusTimeline(context);
}

function applyPinnedHighlightNetwork() {
  if (!pinnedTopicId) return;
  var connected = topicEdgeIndex[String(pinnedTopicId)] || new Set();
  connected = new Set(connected);
  connected.add(pinnedTopicId);
  d3.selectAll('.net-link').each(function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    if (sid === pinnedTopicId) connected.add(tid);
    if (tid === pinnedTopicId) connected.add(sid);
  });

  d3.selectAll('.net-node .net-shape').attr('opacity', function(n) {
    return connected.has(n.id) ? 1 : 0.08;
  });
  d3.selectAll('.net-link').attr('stroke-opacity', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === pinnedTopicId || tid === pinnedTopicId) ? 0.92 : 0.02;
  }).attr('stroke-width', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === pinnedTopicId || tid === pinnedTopicId) ? 2.2 : 0.9;
  }).attr('stroke', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === pinnedTopicId || tid === pinnedTopicId) ? '#a7c8ff' : '#334';
  }).attr('marker-end', function(l) {
    var sid = typeof l.source === 'object' ? l.source.id : l.source;
    var tid = typeof l.target === 'object' ? l.target.id : l.target;
    return (sid === pinnedTopicId || tid === pinnedTopicId) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
  });
}

function highlightTopicInView(topicId) {
  // While a non-topic entity is focused, keep that focus stable and ignore
  // sidebar hover-driven topic previews.
  if (hasFocusedEntity() && pinnedTopicId === null) return;
  // Temporarily highlight a topic (for reference link hover)
  if (activeView === 'timeline') {
    var connected = topicEdgeIndex[String(topicId)] || new Set();
    d3.selectAll('.topic-circle')
      .attr('opacity', function(t) {
        if (t.id === topicId) return 1;
        if (t.id === pinnedTopicId) return 0.7;
        if (connected.has(t.id)) return 0.8;
        if (!topicMatchesFilter(t)) return 0.03;
        return 0.12;
      })
      .attr('stroke-width', function(t) { return t.id === topicId ? 2.5 : 0.5; });
    d3.selectAll('.edge-line')
      .attr('stroke-opacity', function(e) {
        if (e.source === topicId || e.target === topicId) return 0.88;
        if (e.source === pinnedTopicId || e.target === pinnedTopicId) return 0.48;
        return 0.02;
      })
      .attr('stroke-width', function(e) {
        if (e.source === topicId || e.target === topicId) return 2.1;
        if (e.source === pinnedTopicId || e.target === pinnedTopicId) return 1.4;
        return 0.9;
      })
      .attr('stroke', function(e) {
        if (e.source === topicId || e.target === topicId) return '#ffc26a';
        if (e.source === pinnedTopicId || e.target === pinnedTopicId) return '#9fc0ff';
        return '#556';
      })
      .attr('marker-end', function(e) {
        if (e.source === topicId || e.target === topicId) return 'url(#arrow-highlight)';
        if (e.source === pinnedTopicId || e.target === pinnedTopicId) return 'url(#arrow-highlight)';
        return 'url(#arrow-default)';
      });
    syncLabels();
  } else if (activeView === 'network') {
    var connected = topicEdgeIndex[String(topicId)] || new Set();
    var connSet = new Set(connected);
    connSet.add(topicId);
    d3.selectAll('.net-node .net-shape')
      .attr('opacity', function(n) { return connSet.has(n.id) ? 1 : (n.id === pinnedTopicId ? 0.7 : 0.08); })
      .attr('stroke-width', function(n) { return n.id === topicId ? 2.5 : 0.5; });
    d3.selectAll('.net-link').attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === topicId || tid === topicId) ? 0.92 : 0.02;
    }).attr('stroke-width', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === topicId || tid === topicId) ? 2.2 : 0.9;
    }).attr('stroke', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === topicId || tid === topicId) ? '#ffc26a' : '#334';
    }).attr('marker-end', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === topicId || tid === topicId) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
    });
  }
}

function restorePinnedHighlight() {
  // Revert stroke-width and restore pinned or filter state
  d3.selectAll('.topic-circle').attr('stroke-width', 0.5);
  d3.selectAll('.net-node .net-shape').attr('stroke-width', 0.5);
  if (hasFocusedEntity()) {
    applyFocusedEntityHighlight();
    return;
  }
  applyFilters();
}

function filterTimeline(skipFocusedHighlight) {
  if (lineageActive) { applyLineageTimeline(); return; }
  const hasFilter = activeThread || hasAuthorFilter() || activeCategory || activeTag || minInfluence > 0;

  // Compute target opacities upfront so labels/milestones can sync immediately
  var targetOp = {};
  d3.selectAll('.topic-circle').each(function(d) {
    targetOp[d.id] = hasFilter ? (topicMatchesFilter(d) ? 0.85 : 0.08) : 0.7;
  });

  d3.selectAll('.topic-circle')
    .transition().duration(200)
    .attr('opacity', function(d) { return targetOp[d.id]; })
    .attr('r', function(d) { return tlRScale(d.inf); });

  d3.selectAll('.edge-line')
    .attr('stroke', '#556')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', function(e) {
      if (!hasFilter) return 0.06;
      const sT = DATA.topics[e.source];
      const tT = DATA.topics[e.target];
      if (sT && tT && topicMatchesFilter(sT) && topicMatchesFilter(tT)) return 0.25;
      return 0.01;
    })
    .attr('marker-end', 'url(#arrow-default)');
  clearTimelineAuxEdgeMarkers();
  syncLabelsFromMap(targetOp);

  // Filter EIP squares
  if (showEips) {
    d3.selectAll('.eip-square')
      .style('display', function(d) { return eipMatchesFilter(d) ? null : 'none'; })
      .transition().duration(200)
      .attr('opacity', function(d) {
        return 0.7;
      });
    d3.selectAll('.eip-label')
      .style('display', function(d) { return eipMatchesFilter(d) ? null : 'none'; });
    d3.selectAll('.cross-ref-edge')
      .style('display', function(d) {
        if (!d) return 'none';
        if (!timelineTopicVisible(d.topicId)) return 'none';
        if (!timelineEipVisibleByNum(d.eipNum)) return 'none';
        return null;
      })
      .attr('stroke-opacity', function(d) {
        if (!d) return 0.02;
        return (timelineTopicVisible(d.topicId) && timelineEipVisibleByNum(d.eipNum)) ? 0.14 : 0.02;
      })
      .attr('stroke-width', function(d) {
        return (!d || !timelineTopicVisible(d.topicId) || !timelineEipVisibleByNum(d.eipNum)) ? 0.6 : 0.8;
      });
  }

  // Filter Magicians triangles
  if (showMagicians) {
    d3.selectAll('.magicians-triangle')
      .style('display', function(d) { return magiciansMatchesFilter(d) ? null : 'none'; })
      .transition().duration(200)
      .attr('opacity', 0.78);
    d3.selectAll('.magicians-label')
      .style('display', function(d) { return magiciansMatchesFilter(d) ? null : 'none'; });
    d3.selectAll('.magicians-ref-edge')
      .style('display', function(d) {
        if (!d || !d.magTopic) return 'none';
        if (!timelineMagiciansVisibleById(magiciansTopicId(d.magTopic))) return 'none';
        if (!timelineTopicVisible(d.topicId)) return 'none';
        return null;
      })
      .attr('stroke-opacity', function(d) {
        return (!d || !timelineMagiciansVisibleById(magiciansTopicId(d.magTopic)) || !timelineTopicVisible(d.topicId)) ? 0.02 : 0.14;
      })
      .attr('stroke-width', function(d) {
        return (!d || !timelineMagiciansVisibleById(magiciansTopicId(d.magTopic)) || !timelineTopicVisible(d.topicId)) ? 0.7 : 0.9;
      });
  }

  // Filter papers on timeline
  if (showPapers) {
    d3.selectAll('.paper-diamond')
      .style('display', function(d) { return paperMatchesTimelineFilter(d) ? null : 'none'; })
      .transition().duration(200)
      .attr('opacity', 0.76);
    d3.selectAll('.paper-hit')
      .style('display', function(d) { return paperMatchesTimelineFilter(d) ? null : 'none'; });
    d3.selectAll('.paper-label')
      .style('display', function(d) { return paperMatchesTimelineFilter(d) ? null : 'none'; })
      .attr('opacity', 0.74);
    d3.selectAll('.paper-topic-ref-edge')
      .style('display', function(d) {
        if (!d) return 'none';
        if (!timelinePaperVisibleById(d.paperId)) return 'none';
        if (!timelineTopicVisible(d.topicId)) return 'none';
        return null;
      })
      .attr('stroke-opacity', function(d) {
        return (!d || !timelinePaperVisibleById(d.paperId) || !timelineTopicVisible(d.topicId)) ? 0.02 : 0.12;
      })
      .attr('stroke-width', function(d) {
        return (!d || !timelinePaperVisibleById(d.paperId) || !timelineTopicVisible(d.topicId)) ? 0.6 : 0.9;
      });
    d3.selectAll('.paper-eip-ref-edge')
      .style('display', function(d) {
        if (!d) return 'none';
        if (!timelinePaperVisibleById(d.paperId)) return 'none';
        if (!timelineEipVisibleByNum(d.eipNum)) return 'none';
        return null;
      })
      .attr('stroke-opacity', function(d) {
        return (!d || !timelinePaperVisibleById(d.paperId) || !timelineEipVisibleByNum(d.eipNum)) ? 0.02 : 0.12;
      })
      .attr('stroke-width', function(d) {
        return (!d || !timelinePaperVisibleById(d.paperId) || !timelineEipVisibleByNum(d.eipNum)) ? 0.6 : 0.9;
      });
    d3.selectAll('.paper-paper-edge')
      .style('display', function(d) {
        if (!showPapers || !d) return 'none';
        if (!timelinePaperVisibleById(d.paperA)) return 'none';
        if (!timelinePaperVisibleById(d.paperB)) return 'none';
        return null;
      })
      .attr('stroke-opacity', function(d) {
        return (!d || !timelinePaperVisibleById(d.paperA) || !timelinePaperVisibleById(d.paperB)) ? 0.02 : 0.10;
      })
      .attr('stroke-width', function(d) {
        return (!d || !timelinePaperVisibleById(d.paperA) || !timelinePaperVisibleById(d.paperB)) ? 0.5 : 0.85;
      });
  }

  if (!skipFocusedHighlight && hasFocusedEntity() && canApplyFocusedHighlightInView()) {
    applyFocusedEntityHighlightTimeline();
  } else {
    clearFocusedTimelineExtraEdges();
  }
}

// Sync topic labels and milestones to match circle opacity.
// syncLabels reads current DOM opacity; syncLabelsFromMap uses precomputed target values
// (needed when circles are animated via transition).
function syncLabelsFromMap(opMap) {
  d3.selectAll('.topic-label').attr('opacity', function(d) {
    var cOp = opMap[d.id];
    return (cOp !== undefined && cOp > 0.25) ? Math.min(cOp + 0.05, 0.9) : 0;
  });
  d3.selectAll('.milestone-marker').each(function(d) {
    var cOp = opMap[d.id];
    var vis = milestonesVisible && (cOp === undefined || cOp > 0.25);
    d3.select(this).style('display', vis ? null : 'none');
  });
}
function syncLabels() {
  var opMap = {};
  d3.selectAll('.topic-circle').each(function(d) {
    opMap[d.id] = parseFloat(d3.select(this).attr('opacity'));
  });
  syncLabelsFromMap(opMap);
}

function showForkTooltip(ev, f) {
  var tip = document.getElementById('tooltip');
  var eipList = (f.eips || []).map(function(e) { return 'EIP-' + e; }).join(', ');
  var relCount = (f.rt || []).length;
  tip.innerHTML = '<strong>' + escHtml(f.cn || f.n) + '</strong>' +
    (f.d ? '<br><span style="color:#888">' + f.d + '</span>' : '') +
    (f.el ? '<br>EL: ' + escHtml(f.el) : '') +
    (f.cl ? ' &middot; CL: ' + escHtml(f.cl) : '') +
    (eipList ? '<br><span style="color:#88aacc">EIPs: ' + eipList + '</span>' : '') +
    (relCount > 0 ? '<br><span style="color:#666">' + relCount + ' related topics</span>' : '');
  tip.style.display = 'block';
  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

// === NETWORK ===
function buildNetwork() {
  const container = document.getElementById('network-view');
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  // Arrow markers for network edges
  var netDefs = svg.append('defs');
  netDefs.append('marker').attr('id', 'net-arrow-default')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-net-default').attr('opacity', 0.25);
  netDefs.append('marker').attr('id', 'net-arrow-highlight')
    .attr('viewBox', '0 0 6 4').attr('refX', 6).attr('refY', 2)
    .attr('markerWidth', 6).attr('markerHeight', 4)
    .attr('orient', 'auto')
    .append('path').attr('d', 'M0,0 L6,2 L0,4 Z').attr('class', 'arrow-net-highlight').attr('opacity', 0.8);

  const g = svg.append('g');

  // Zoom
  svg.call(d3.zoom().scaleExtent([0.15, 5]).on('zoom', function(ev) {
    g.attr('transform', ev.transform);
  }));

  svg.on('click.clearFocus', function(ev) {
    if (!hasFocusedEntity() || ev.defaultPrevented) return;
    var target = ev && ev.target ? ev.target : null;
    if (target && target.closest && target.closest('.net-node,.net-label,.fork-diamond')) return;
    clearFocusedEntityState({keepDetailOpen: false});
  });

  // Prepare data from canonical unified graph payload.
  const unifiedGraph = DATA.unifiedGraph || {nodes: [], edges: []};
  const sourceNodes = Array.isArray(unifiedGraph.nodes) ? unifiedGraph.nodes : [];
  const sourceEdges = Array.isArray(unifiedGraph.edges) ? unifiedGraph.edges : [];
  const includeConnectedOnly = showEips && eipVisibilityMode === 'connected';

  const nodes = [];
  const nodeMap = {};

  sourceNodes.forEach(function(rawNode) {
    if (!rawNode || rawNode.id === undefined || rawNode.id === null) return;
    var n = Object.assign({}, rawNode);
    var sourceType = networkNodeSourceType(n);

    if (sourceType === 'eip') {
      if (!showEips) return;
      if (includeConnectedOnly && !connectedEipNodeIds.has(String(n.id))) return;
      n.isEip = true;
      var eipNum = eipNumFromNode(n);
      if (eipNum !== null && !isNaN(eipNum)) n.eipNum = eipNum;
      var eipMeta = n.eipNum !== undefined ? (DATA.eipCatalog || {})[String(n.eipNum)] : null;
      if ((!n.title || !String(n.title).trim()) && eipMeta) {
        n.title = 'EIP-' + String(n.eipNum) + ': ' + (eipMeta.t || '');
      }
      if ((n.influence === undefined || n.influence === null) && eipMeta) n.influence = eipMeta.inf || 0;
      if ((n.thread === undefined || n.thread === null) && eipMeta) n.thread = eipMeta.th || null;
      if ((n.status === undefined || n.status === null) && eipMeta) n.status = eipMeta.s || null;
    } else if (sourceType === 'magicians') {
      if (!showMagicians) return;
      var magId = magiciansTopicId(n);
      if (magId === null || isNaN(magId)) {
        if (typeof n.id === 'string' && n.id.indexOf('mag_') === 0) {
          magId = Number(n.id.slice(4));
        }
      }
      if (magId !== null && !isNaN(magId)) n.magiciansId = Number(magId);
      if (showEips && isEipDiscussionMagiciansTopic(n)) return;
      n.isMagicians = true;
      var mt = (n.magiciansId !== undefined) ? (DATA.magiciansTopics || {})[String(n.magiciansId)] : null;
      if ((!n.title || !String(n.title).trim()) && mt) n.title = magiciansDisplayTitle(mt);
      if ((!n.title || !String(n.title).trim())) n.title = magiciansDisplayTitle(n);
      if ((n.influence === undefined || n.influence === null)) {
        n.influence = mt ? magiciansInfluenceScore(mt) : magiciansInfluenceScore(n);
      }
      if (n.thread === undefined || n.thread === null) {
        n.thread = mt ? magiciansThreadFromTopic(mt) : magiciansThreadFromTopic(n);
      }
      if ((n.category === undefined || n.category === null) && mt) n.category = mt.cat || null;
      if ((n.author === undefined || n.author === null) && mt) n.author = mt.a || null;
      if ((n.date === undefined || n.date === null) && mt) n.date = mt.d || null;
    } else if (sourceType === 'paper') {
      if (!showPapers) return;
      n.isPaper = true;
      var p = paperFromNode(n);
      if ((!n.title || !String(n.title).trim()) && p) n.title = p.t || 'Untitled paper';
      if ((n.influence === undefined || n.influence === null)) {
        n.influence = p ? paperMetadataToInfluence(p) : 0.2;
      }
    } else if (sourceType === 'fork') {
      n.isFork = true;
      if (n.influence === undefined || n.influence === null) n.influence = 0;
    } else {
      n.sourceType = 'topic';
      var t = DATA.topics[n.id];
      if ((n.influence === undefined || n.influence === null) && t) n.influence = t.inf || 0;
      if ((n.thread === undefined || n.thread === null) && t) n.thread = t.th || null;
    }

    n.sourceType = sourceType || n.sourceType || 'topic';
    nodes.push(n);
    nodeMap[n.id] = n;
  });

  const links = [];
  const linkSet = new Set();
  sourceEdges.forEach(function(rawEdge) {
    if (!rawEdge) return;
    var src = rawEdge.source;
    var tgt = rawEdge.target;
    if (!nodeMap[src] || !nodeMap[tgt]) return;
    var edgeType = rawEdge.type || null;
    var key = String(src) + '->' + String(tgt) + '|' + String(edgeType || '');
    if (linkSet.has(key)) return;
    linkSet.add(key);
    links.push({
      source: src,
      target: tgt,
      edgeType: edgeType
    });
  });

  if (showPapers) {
    var paperAugment = buildNetworkPaperAugment(nodeMap);
    (paperAugment.nodes || []).forEach(function(pn) {
      if (!pn || !pn.id || nodeMap[pn.id]) return;
      pn.isPaper = true;
      nodes.push(pn);
      nodeMap[pn.id] = pn;
    });
    (paperAugment.links || []).forEach(function(pl) {
      if (!pl || !nodeMap[pl.source] || !nodeMap[pl.target]) return;
      var pKey = String(pl.source) + '->' + String(pl.target) + '|' + String(pl.edgeType || '');
      if (linkSet.has(pKey)) return;
      linkSet.add(pKey);
      links.push({
        source: pl.source,
        target: pl.target,
        edgeType: pl.edgeType || 'paper_related',
        score: Number(pl.score || 0),
        reason: pl.reason || '',
      });
    });
  }

  const maxInf = d3.max(nodes, function(n) { return n.influence || 0; }) || 1;
  const rScale = d3.scaleSqrt().domain([0, maxInf]).range([3, 16]);

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(function(d) { return d.id; }).distance(60).strength(0.1))
    .force('charge', d3.forceManyBody().strength(-30))
    .force('center', d3.forceCenter(width/2, height/2))
    .force('collision', d3.forceCollide().radius(function(d) {
      if (d.isFork) return 10;
      if (d.isPaper) return Math.max(4, rScale(d.influence || 0) * 0.78) + 2;
      return rScale(d.influence || 0) + 2;
    }));

  const link = g.append('g').selectAll('line')
    .data(links).join('line')
    .attr('class', 'net-link')
    .attr('stroke-opacity', function(d) {
      if (d.edgeType === 'paper_related') return 0.09;
      if (d.edgeType === 'paper_paper') return 0.075;
      return 0.12;
    })
    .attr('stroke-dasharray', function(d) {
      if (d.edgeType === 'eip_requires') return '4 3';
      if (d.edgeType === 'topic_magicians') return '2 3';
      if (d.edgeType === 'eip_magicians' || d.edgeType === 'topic_eip' || d.edgeType === 'eip_ethresearch') return '5 3';
      if (d.edgeType === 'paper_related') return '2 2';
      if (d.edgeType === 'paper_paper') return null;
      return null;
    })
    .attr('marker-end', function(d) {
      return d.edgeType === 'paper_paper' ? null : 'url(#net-arrow-default)';
    });

  const node = g.append('g').selectAll('g')
    .data(nodes).join('g')
    .attr('class', 'net-node')
    .call(d3.drag()
      .on('start', function(ev, d) {
        if (!ev.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', function(ev, d) { d.fx = ev.x; d.fy = ev.y; })
      .on('end', function(ev, d) {
        if (!ev.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      })
    );

  // Fork diamonds
  node.filter(function(d) { return d.isFork; }).append('rect')
    .attr('class', 'fork-diamond net-shape')
    .attr('width', 12).attr('height', 12)
    .attr('transform', 'rotate(45)')
    .attr('x', -6).attr('y', -6);
  node.filter(function(d) { return d.isFork; }).append('title')
    .text(function(d) { return d.title || d.fork || 'Fork'; });

  // Topic circles
  node.filter(function(d) { return !d.isFork && !d.isEip && !d.isMagicians && !d.isPaper; }).append('circle')
    .attr('class', 'net-shape net-topic-shape')
    .attr('r', function(d) { return rScale(d.influence || 0); })
    .attr('fill', function(d) { return THREAD_COLORS[d.thread] || '#555'; })
    .attr('stroke', function(d) { return THREAD_COLORS[d.thread] || '#555'; })
    .attr('stroke-width', 0.5)
    .attr('opacity', 0.65);

  // EIP squares in network
  node.filter(function(d) { return d.isEip; }).append('rect')
    .attr('class', 'net-shape net-eip-shape')
    .attr('width', function(d) { return rScale(d.influence || 0) * 1.4; })
    .attr('height', function(d) { return rScale(d.influence || 0) * 1.4; })
    .attr('x', function(d) { return -rScale(d.influence || 0) * 0.7; })
    .attr('y', function(d) { return -rScale(d.influence || 0) * 0.7; })
    .attr('rx', 3)
    .attr('fill', function(d) { return EIP_STATUS_COLORS[d.status] || '#555'; })
    .attr('stroke', function(d) { return EIP_STATUS_COLORS[d.status] || '#555'; })
    .attr('stroke-width', 0.5)
    .attr('opacity', 0.7);

  // Magicians topics as triangles in network
  node.filter(function(d) { return d.isMagicians; }).append('path')
    .attr('class', 'net-shape net-magicians-shape')
    .attr('d', function(d) {
      var r = rScale(d.influence || 0) * 0.9;
      return 'M0,' + (-r.toFixed(2)) + ' L' + r.toFixed(2) + ',' + r.toFixed(2) +
        ' L' + (-r.toFixed(2)) + ',' + r.toFixed(2) + ' Z';
    })
    .attr('fill', '#bb88cc')
    .attr('stroke', '#bb88cc')
    .attr('stroke-width', 0.5)
    .attr('opacity', 0.78);

  // Papers in network
  node.filter(function(d) { return d.isPaper; }).append('circle')
    .attr('class', 'net-shape net-paper-shape')
    .attr('r', function(d) {
      return Math.max(4, rScale(d.influence || 0) * 0.78);
    })
    .attr('opacity', 0.72);

  // Network node labels for top 20 by influence
  var netTopNodes = nodes.filter(function(n) { return !n.isFork && !n.isPaper && n.influence; })
    .sort(function(a, b) { return (b.influence || 0) - (a.influence || 0); }).slice(0, 20);
  var netLabelSet = new Set(netTopNodes.map(function(n) { return n.id; }));
  node.filter(function(d) { return netLabelSet.has(d.id); }).append('text')
    .attr('class', 'net-label')
    .attr('dy', function(d) { return rScale(d.influence || 0) + 10; })
    .text(function(d) {
      var t = DATA.topics[d.id];
      var title = t ? t.t : (d.title || '');
      return title.length > 24 ? title.slice(0, 23) + '\u2026' : title;
    });

  // Events
  function handleNetworkNodeSingleClick(ev, d) {
    if (d.isPaper) { focusPaperNode(paperIdFromNode(d)); return; }
    if (d.isEip && d.eipNum) { focusEipNode(d.eipNum); return; }
    if (d.isMagicians && d.magiciansId) { focusMagiciansNode(d.magiciansId); return; }
    var t = DATA.topics[d.id];
    if (t) { handleTopicClick(ev, t); return; }
  }

  function handleNetworkNodeDoubleClick(ev, d) {
    if (d.isFork) {
      ev.stopPropagation();
      var fork = findForkByName(d.fork || d.title);
      if (fork) showForkDetail(fork);
      else showToast('No fork metadata found for ' + (d.title || d.fork || 'this fork'));
      return;
    }
    if (d.isPaper) {
      showPaperDetail(paperFromNode(d), d);
      return;
    }
    if (d.isEip && d.eipNum) { showEipDetailByNum(d.eipNum); return; }
    if (d.isMagicians && d.magiciansId) { showMagiciansTopicDetailById(d.magiciansId); return; }
    var t = DATA.topics[d.id];
    if (t) handleTopicDoubleClick(ev, t);
  }

  var netClickTimer = null;
  var netClickNodeId = null;
  node.on('click', function(ev, d) {
    if (netClickTimer && netClickNodeId === d.id) {
      clearTimeout(netClickTimer);
      netClickTimer = null;
      netClickNodeId = null;
      handleNetworkNodeDoubleClick(ev, d);
      return;
    }
    if (netClickTimer) {
      clearTimeout(netClickTimer);
      netClickTimer = null;
      netClickNodeId = null;
    }
    netClickNodeId = d.id;
    netClickTimer = setTimeout(function() {
      netClickTimer = null;
      netClickNodeId = null;
      handleNetworkNodeSingleClick(ev, d);
    }, 220);
  });

  node.on('mouseover', function(ev, d) {
    if (d.isFork) {
      var fork = findForkByName(d.fork || d.title);
      showForkTooltip(ev, fork || {
        n: d.fork || d.title || 'Fork',
        cn: d.title || d.fork || 'Fork',
        d: d.date || '',
        eips: [],
        rt: []
      });
      return;
    }
    if (d.isPaper) {
      showPaperTooltip(ev, paperFromNode(d), d);
    }
    var t = DATA.topics[d.id];
    if (d.isEip && d.eipNum) {
      var e = DATA.eipCatalog[String(d.eipNum)];
      if (e) {
        showEipTooltip(ev, {
          _eipNum: d.eipNum,
          t: e.t || d.title,
          s: e.s,
          fk: e.fk,
          inf: e.inf || d.influence || 0,
          erc: e.erc || 0,
          ml: e.ml || 0,
        });
      }
    } else if (d.isMagicians && d.magiciansId) {
      var mt = (DATA.magiciansTopics || {})[String(d.magiciansId)];
      if (mt) showMagiciansTooltip(ev, mt);
    } else if (t) {
      showTooltip(ev, t);
    }

    var nodeKind = d.isEip ? 'eip' : (d.isMagicians ? 'magicians' : (d.isPaper ? 'paper' : 'topic'));
    if (hasFocusedEntity() && isHoverBlockedByFocusedEntity(nodeKind, d)) return;

    // If a filter is active and this node doesn't match, only show tooltip
    var hasFilter = activeThread || hasAuthorFilter() || activeCategory || activeTag || minInfluence > 0;
    if (hasFilter && !networkNodeMatchesFilter(d)) return;

    // Highlight connections
    var connected = new Set();
    links.forEach(function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      if (sid === d.id) connected.add(tid);
      if (tid === d.id) connected.add(sid);
    });
    connected.add(d.id);

    node.selectAll('.net-shape').attr('opacity', function(n) {
      if (connected.has(n.id) && (!hasFilter || networkNodeMatchesFilter(n))) return 1;
      if (hasFilter && !networkNodeMatchesFilter(n)) return 0.05;
      return 0.08;
    });
    link.attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (connected.has(sid) && connected.has(tid)) ? 0.92 : 0.02;
    }).attr('stroke-width', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (connected.has(sid) && connected.has(tid)) ? 2.1 : 0.9;
    }).attr('stroke', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (connected.has(sid) && connected.has(tid)) ? '#a7c8ff' : '#334';
    }).attr('marker-end', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      if (l.edgeType === 'paper_paper') return null;
      return (connected.has(sid) && connected.has(tid)) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
    });
  });

  node.on('mouseout', function(ev, d) {
    hideTooltip();
    if (hasFocusedEntity()) {
      applyFocusedEntityHighlightNetwork();
      return;
    }
    // If we didn't change opacities (dimmed node hover), nothing to restore
    var hasFilter = activeThread || hasAuthorFilter() || activeCategory || activeTag || minInfluence > 0;
    if (hasFilter && !networkNodeMatchesFilter(d)) return;
    if (pinnedTopicId) {
      applyPinnedHighlightNetwork();
    } else {
      filterNetwork();
    }
  });

  simulation.on('tick', function() {
    link.attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
    node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
  });

  if (hasFocusedEntity()) applyFocusedEntityHighlightNetwork();
  else filterNetwork();
}

function filterNetwork() {
  if (lineageActive) { applyLineageNetwork(); return; }
  var hasFilter = activeThread || hasAuthorFilter() || activeCategory || activeTag || minInfluence > 0;
  var visibleById = {};

  d3.selectAll('.net-node').each(function(d) {
    var visible = networkNodeMatchesFilter(d);
    visibleById[d.id] = visible;
    d3.select(this).style('display', visible ? null : 'none');
    d3.select(this).selectAll('.net-shape').attr('opacity', function(n) {
      if (!visible) return 0;
      if (n.isFork) return hasFilter ? 0.55 : 0.65;
      if (n.isEip) return hasFilter ? 0.85 : 0.75;
      if (n.isPaper) return hasFilter ? 0.78 : 0.68;
      return hasFilter ? 0.85 : 0.7;
    });
  });

  // Paper nodes remain visible only if they are linked to at least one visible non-paper node.
  d3.selectAll('.net-node').each(function(d) {
    if (!d || !d.isPaper) return;
    var targets = Array.isArray(d.linkedTargets) ? d.linkedTargets : [];
    var hasVisibleTarget = targets.some(function(targetId) { return !!visibleById[targetId]; });
    var visible = !!visibleById[d.id] && hasVisibleTarget;
    visibleById[d.id] = visible;
    d3.select(this).style('display', visible ? null : 'none');
  });

  d3.selectAll('.net-link')
    .style('display', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (visibleById[sid] && visibleById[tid]) ? null : 'none';
    })
    .attr('stroke', '#334')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      if (!visibleById[sid] || !visibleById[tid]) return 0;
      var isPaperEdge = (l.edgeType === 'paper_related' || l.edgeType === 'paper_paper');
      if (hasFilter) return isPaperEdge ? 0.13 : 0.16;
      return isPaperEdge ? 0.10 : 0.12;
    })
    .attr('marker-end', function(l) {
      return l.edgeType === 'paper_paper' ? null : 'url(#net-arrow-default)';
    });

  if (hasFocusedEntity()) applyFocusedEntityHighlightNetwork();
}

// === CO-AUTHOR NETWORK ===
function buildCoAuthorNetwork() {
  var container = document.getElementById('coauthor-view');
  var width = container.clientWidth || 800;
  var height = container.clientHeight || 600;

  var svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  var g = svg.append('g');
  var coUserInteracted = false;
  var coAutoFitted = false;

  // Zoom
  var coZoom = d3.zoom()
    .scaleExtent([0.3, 5])
    .extent([[0, 0], [width, height]])
    .translateExtent([[-width * 0.8, -height * 0.8], [width * 1.8, height * 1.8]])
    .on('start', function() {
      coUserInteracted = true;
      hideTooltip();
      filterCoAuthorNetwork();
    })
    .on('zoom', function(ev) {
      g.attr('transform', ev.transform);
    });
  svg.call(coZoom);
  svg.on('mouseleave', function() {
    hideTooltip();
    filterCoAuthorNetwork();
  });

  // Prepare co-author data
  var coNodes = (DATA.coGraph.nodes || []).map(function(n) {
    var copy = Object.assign({}, n);
    if (copy.influence !== undefined && copy.inf === undefined) copy.inf = copy.influence;
    return copy;
  });
  var coNodeMap = {};
  coNodes.forEach(function(n) { coNodeMap[n.id] = n; });

  var coLinks = (DATA.coGraph.edges || [])
    .filter(function(e) { return coNodeMap[e.source] && coNodeMap[e.target]; })
    .map(function(e) { return {source: e.source, target: e.target, weight: e.weight || 1}; });

  // Scales
  var maxInf = d3.max(coNodes, function(n) { return n.inf || 0; }) || 1;
  var rScale = d3.scaleSqrt().domain([0, maxInf]).range([5, 28]);

  var maxWeight = d3.max(coLinks, function(e) { return e.weight; }) || 1;
  var linkWidthScale = d3.scaleLinear().domain([1, maxWeight]).range([0.5, 4]);

  // Determine dominant thread color for each author node
  function getAuthorColor(n) {
    // Use the author color map if available (top 15 get unique colors)
    if (authorColorMap[n.id] && authorColorMap[n.id] !== '#555') return authorColorMap[n.id];
    // Otherwise, color by dominant thread
    var profile = getAuthorProfile(n.id);
    var thrs = n.thrs || (profile ? profile.ths : null);
    if (thrs) {
      var bestThread = null;
      var bestCount = 0;
      for (var tid in thrs) {
        if (thrs[tid] > bestCount) { bestCount = thrs[tid]; bestThread = tid; }
      }
      if (bestThread && THREAD_COLORS[bestThread]) return THREAD_COLORS[bestThread];
    }
    return '#667';
  }

  function fitCoAuthorToViewport(animate) {
    if (coNodes.length === 0) return;
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    var found = 0;
    coNodes.forEach(function(n) {
      if (!isFinite(n.x) || !isFinite(n.y)) return;
      found += 1;
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    });
    if (found < 2) return;
    var dx = Math.max(1, maxX - minX);
    var dy = Math.max(1, maxY - minY);
    var padding = 90;
    var scale = Math.min(2.4, Math.max(0.7, Math.min((width - padding) / dx, (height - padding) / dy)));
    var cx = (minX + maxX) / 2;
    var cy = (minY + maxY) / 2;
    var t = d3.zoomIdentity
      .translate((width / 2) - (scale * cx), (height / 2) - (scale * cy))
      .scale(scale);
    if (animate) svg.transition().duration(420).call(coZoom.transform, t);
    else svg.call(coZoom.transform, t);
  }

  // Force simulation
  coAuthorSimulation = d3.forceSimulation(coNodes)
    .force('link', d3.forceLink(coLinks).id(function(d) { return d.id; })
      .distance(function(d) { return Math.max(26, 88 - d.weight * 7); })
      .strength(function(d) { return 0.2 + (d.weight / maxWeight) * 0.3; }))
    .force('charge', d3.forceManyBody().strength(-95))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('x', d3.forceX(width / 2).strength(0.045))
    .force('y', d3.forceY(height / 2).strength(0.045))
    .force('collision', d3.forceCollide().radius(function(d) {
      return rScale(d.inf || 0) + 3;
    }));

  // Draw links
  var link = g.append('g').selectAll('line')
    .data(coLinks).join('line')
    .attr('class', 'coauthor-link')
    .attr('stroke-width', function(d) { return linkWidthScale(d.weight); })
    .attr('stroke-opacity', 0.2);

  // Draw nodes
  var node = g.append('g').selectAll('g')
    .data(coNodes).join('g')
    .attr('class', 'coauthor-node')
    .call(d3.drag()
      .on('start', function(ev, d) {
        if (!ev.active) coAuthorSimulation.alphaTarget(0.3).restart();
        coUserInteracted = true;
        d._dragMoved = false;
        d.fx = d.x; d.fy = d.y;
        hideTooltip();
        filterCoAuthorNetwork();
      })
      .on('drag', function(ev, d) {
        d._dragMoved = true;
        d.fx = ev.x; d.fy = ev.y;
      })
      .on('end', function(ev, d) {
        if (!ev.active) coAuthorSimulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      })
    );

  // Author circles
  node.append('circle')
    .attr('r', function(d) { return rScale(d.inf || 0); })
    .attr('fill', function(d) { return getAuthorColor(d); })
    .attr('stroke', function(d) { return getAuthorColor(d); })
    .attr('stroke-width', 1)
    .attr('opacity', 0.7);

  // Persistent labels for top 15 by influence
  node.filter(function(d) { return top15Authors.has(d.id); })
    .append('text')
    .attr('class', 'coauthor-label')
    .attr('dy', function(d) { return rScale(d.inf || 0) + 12; })
    .text(function(d) { return d.id; });

  // Hover labels for all others (hidden by default)
  node.filter(function(d) { return !top15Authors.has(d.id); })
    .append('text')
    .attr('class', 'coauthor-label-hover')
    .attr('dy', function(d) { return rScale(d.inf || 0) + 10; })
    .attr('opacity', 0)
    .text(function(d) { return d.id; });

  // Click opens detail. Shift+click toggles author filter.
  var coauthorClickTimer = null;
  node.on('click', function(ev, d) {
    if (coauthorClickTimer) { clearTimeout(coauthorClickTimer); coauthorClickTimer = null; return; }
    var shiftHeld = !!ev.shiftKey;
    coauthorClickTimer = setTimeout(function() {
      coauthorClickTimer = null;
      if (d._dragMoved) {
        d._dragMoved = false;
        return;
      }
      if (shiftHeld) {
        toggleAuthor(d.id);
        return;
      }
      showAuthorDetail(d.id);
    }, 220);
  });
  node.on('dblclick', function(ev, d) {
    if (d._dragMoved) {
      d._dragMoved = false;
      return;
    }
    showAuthorDetail(d.id);
  });

  // Hover -> tooltip + highlight connections
  node.on('mouseover', function(ev, d) {
    showCoAuthorTooltip(ev, d);

    // Show hover label for this node
    d3.select(this).select('.coauthor-label-hover').attr('opacity', 1);

    // Highlight connections
    var connected = coAuthorEdgeIndex[d.id] || new Set();
    var connectedWithSelf = new Set(connected);
    connectedWithSelf.add(d.id);

    node.selectAll('circle').attr('opacity', function(n) {
      return connectedWithSelf.has(n.id) ? 1 : 0.08;
    });
    node.selectAll('.coauthor-label').attr('opacity', function(n) {
      return connectedWithSelf.has(n.id) ? 1 : 0.1;
    });
    // Show hover labels for connected nodes too
    node.selectAll('.coauthor-label-hover').attr('opacity', function(n) {
      return connected.has(n.id) ? 1 : (n.id === d.id ? 1 : 0);
    });
    link.attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? 0.7 : 0.02;
    }).attr('stroke', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? '#88aaff' : '#445566';
    });
  });

  node.on('mouseout', function() {
    hideTooltip();
    filterCoAuthorNetwork();
  });

  // Tick
  coAuthorSimulation.on('tick', function() {
    link.attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
    node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
  });
  coAuthorSimulation.on('end', function() {
    if (!coAutoFitted && !coUserInteracted) {
      coAutoFitted = true;
      fitCoAuthorToViewport(true);
    }
  });
  setTimeout(function() {
    if (!coAutoFitted && !coUserInteracted) {
      coAutoFitted = true;
      fitCoAuthorToViewport(true);
    }
  }, 600);
}

function filterCoAuthorNetwork() {
  var selectedAuthors = getActiveEthAuthorSet();
  var selectedInGraph = new Set();
  selectedAuthors.forEach(function(authorId) {
    if (coAuthorNodeSet.has(authorId)) selectedInGraph.add(authorId);
  });
  var hasFilter = hasAuthorFilter();
  var connectedAuthors = new Set();
  selectedInGraph.forEach(function(authorId) {
    var connected = coAuthorEdgeIndex[authorId] || new Set();
    connected.forEach(function(otherId) { connectedAuthors.add(otherId); });
  });

  d3.selectAll('.coauthor-node circle').attr('opacity', function(d) {
    if (hasFilter) {
      if (selectedInGraph.has(d.id)) return 1;
      if (connectedAuthors.has(d.id)) return 0.8;
      return 0.06;
    }
    return 0.7;
  });

  d3.selectAll('.coauthor-label').attr('opacity', function(d) {
    if (hasFilter) {
      if (selectedInGraph.has(d.id)) return 1;
      if (connectedAuthors.has(d.id)) return 1;
      return 0.1;
    }
    return 1;
  });

  d3.selectAll('.coauthor-label-hover').attr('opacity', function(d) {
    if (hasFilter) {
      return connectedAuthors.has(d.id) ? 1 : 0;
    }
    return 0;
  });

  d3.selectAll('.coauthor-link')
    .attr('stroke', '#445566')
    .attr('stroke-opacity', function(l) {
      if (!hasFilter) return 0.2;
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (selectedInGraph.has(sid) || selectedInGraph.has(tid)) ? 0.6 : 0.02;
    });
}

function showCoAuthorTooltip(ev, d) {
  var tip = document.getElementById('tooltip');
  var a = getAuthorProfile(d.id);
  var topThread = '';
  if (d.thrs || (a && a.ths)) {
    var thrs = d.thrs || a.ths;
    var bestThread = null, bestCount = 0;
    for (var tid in thrs) {
      if (thrs[tid] > bestCount) { bestCount = thrs[tid]; bestThread = tid; }
    }
    if (bestThread && DATA.threads[bestThread]) {
      topThread = '<br>Top thread: <span style="color:' + (THREAD_COLORS[bestThread] || '#888') + '">' +
                  DATA.threads[bestThread].n + '</span>';
    }
  }
  tip.innerHTML = '<strong>' + escHtml(d.id) + '</strong><br>' +
    'Topics: ' + (d.tc || (a ? a.tc : '?')) +
    ' &middot; Influence: ' + ((d.inf || (a ? a.inf : 0)).toFixed(2)) +
    topThread;
  tip.style.display = 'block';

  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

// === AUTHOR DETAIL PANEL ===
function showAuthorDetail(username) {
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var a = getAuthorProfile(username);
  if (!a) {
    selectAuthor(username);
    var profileUrl = 'https://ethresear.ch/u/' + encodeURIComponent(username);
    window.open(profileUrl, '_blank');
    showToast('Opened ethresearch profile for ' + username);
    return;
  }

  var color = authorColorMap[username] || '#667';
  var linkedEips = linkedEipAuthors(username);
  var linkedEipStats = linkedEips.map(function(name) {
    return (DATA.eipAuthors || {})[name];
  }).filter(Boolean);
  var linkedEipCount = linkedEipStats.reduce(function(sum, entry) {
    return sum + ((entry.eips || []).length || 0);
  }, 0);

  // Thread distribution bars
  var thrs = a.ths || {};
  var thrEntries = Object.entries(thrs).sort(function(a,b) { return b[1] - a[1]; });
  var thrTotal = thrEntries.reduce(function(sum, e) { return sum + e[1]; }, 0) || 1;
  var threadBarsHtml = thrEntries.slice(0, 6).map(function(entry) {
    var tid = entry[0], count = entry[1];
    var pct = Math.round(count / thrTotal * 100);
    var tColor = THREAD_COLORS[tid] || '#555';
    var tName = DATA.threads[tid] ? DATA.threads[tid].n : tid;
    return '<div class="thread-bar-row">' +
      '<span class="thread-bar-label" style="color:' + tColor + '">' + escHtml(tName) + '</span>' +
      '<span class="thread-bar-track"><span class="thread-bar-fill" style="width:' + pct + '%;background:' + tColor + '"></span></span>' +
      '<span class="thread-bar-pct">' + pct + '%</span></div>';
  }).join('');

  // Top topics
  var topTopicsHtml = '';
  if (a.tops && a.tops.length > 0) {
    topTopicsHtml = a.tops.map(function(tid) {
      var topic = DATA.topics[tid];
      if (!topic) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + tid + '])" ' +
        'onmouseenter="highlightTopicInView(' + tid + ')" ' +
        'onmouseleave="restorePinnedHighlight()">' +
        escHtml(topic.t) + '</a> <span style="color:#666;font-size:10px">(' + topic.inf.toFixed(2) + ')</span></div>';
    }).join('');
  }

  // Other (minor) topics for this author
  var otherTopicsHtml = '';
  var minorForAuthor = Object.values(DATA.topics).filter(function(t) {
    return t.mn && (t.a === username || (t.coauth || []).indexOf(username) >= 0);
  });
  minorForAuthor.sort(function(a, b) { return (b.d || '').localeCompare(a.d || ''); });
  if (minorForAuthor.length > 0) {
    var showCount = Math.min(15, minorForAuthor.length);
    otherTopicsHtml = minorForAuthor.slice(0, showCount).map(function(mt) {
      return '<div class="ref-item minor-ref"><a onclick="showDetail(DATA.topics[' + mt.id + '])" style="color:#889;font-style:italic">' +
        escHtml(mt.t) + '</a> <span style="color:#556;font-size:10px">' + (mt.d || '').slice(0, 7) + '</span></div>';
    }).join('');
    if (minorForAuthor.length > showCount) {
      otherTopicsHtml += '<div style="font-size:10px;color:#667;padding:3px 0">+' + (minorForAuthor.length - showCount) + ' more</div>';
    }
  }

  // Co-researchers
  var coHtml = '';
  if (a.co && Object.keys(a.co).length > 0) {
    coHtml = Object.entries(a.co).map(function(entry) {
      var coName = entry[0], coCount = entry[1];
      var coColor = authorColorMap[coName] || '#667';
      return '<span style="display:inline-block;font-size:11px;margin:2px 4px 2px 0;padding:1px 6px;' +
        'background:' + coColor + '22;border:1px solid ' + coColor + '44;border-radius:3px;color:' + coColor + ';cursor:pointer" ' +
        'onclick="openAuthor(' + jsQuote(coName) + ')">' +
        escHtml(coName) + ' <span style="color:#666;font-size:9px">(' + coCount + ')</span></span>';
    }).join('');
  }

  // Active years
  var yearsHtml = '';
  if (a.yrs && a.yrs.length > 0) {
    yearsHtml = a.yrs.join(', ');
  }

  var identityTabsHtml = '';
  if (linkedEips.length > 0) {
    identityTabsHtml = '<div class="author-tab-wrap" style="margin-top:2px;margin-bottom:10px">' +
      '<span class="author-tab active">ethresearch</span>' +
      '<span class="author-tab" onclick="openEipAuthor(' + jsQuote(linkedEips[0]) + ')">EIPs</span>' +
      '</div>';
  }

  var linkedEipHtml = '';
  if (linkedEips.length > 0) {
    linkedEipHtml = '<div class="detail-stat"><span class="label">Linked EIP Authors</span><span class="value">' +
      linkedEips.map(function(name) {
        return '<span style="cursor:pointer;color:#7788cc" onclick="openEipAuthor(' + jsQuote(name) + ')">' + escHtml(name) + '</span>';
      }).join(', ') + '</span></div>' +
      '<div class="detail-stat"><span class="label">Linked EIPs</span><span class="value">' + linkedEipCount + '</span></div>';
  }
  var authorPapersHtml = buildRelatedPapersHtml(relatedPapersForEthAuthor(username), 'author-' + username, 'Related Papers');

  content.innerHTML =
    '<h2 style="color:' + color + '">' + escHtml(username) + '</h2>' +
    '<div class="meta">Researcher &middot; <a href="https://ethresear.ch/u/' + encodeURIComponent(username) +
    '" target="_blank">View profile &rarr;</a></div>' +
    identityTabsHtml +
    '<div class="detail-stat"><span class="label">Topics Created</span><span class="value">' + a.tc + ' influential' + (a.at && a.at.length > a.tc ? ' / ' + a.at.length + ' total' : '') + '</span></div>' +
    '<div class="detail-stat"><span class="label">Total Posts</span><span class="value">' + a.tp.toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Total Likes</span><span class="value">' + a.lk.toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Influence Score</span><span class="value">' + a.inf.toFixed(3) + '</span></div>' +
    '<div class="detail-stat"><span class="label">Cited by</span><span class="value">' + a.ind + ' topics</span></div>' +
    '<div class="detail-stat"><span class="label">Active Years</span><span class="value">' + yearsHtml + '</span></div>' +
    linkedEipHtml +
    (threadBarsHtml ?
      '<div style="margin-top:12px"><strong style="font-size:11px;color:#888">Thread Distribution</strong>' +
      '<div style="margin-top:6px">' + threadBarsHtml + '</div></div>' : '') +
    (topTopicsHtml ?
      '<div class="detail-refs" style="margin-top:12px"><h4>Top Topics</h4>' + topTopicsHtml + '</div>' : '') +
    (otherTopicsHtml ?
      '<div class="detail-refs" style="margin-top:12px"><h4 style="color:#667">Other Topics</h4>' + otherTopicsHtml + '</div>' : '') +
    authorPapersHtml +
    (coHtml ?
      '<div style="margin-top:12px"><strong style="font-size:11px;color:#888">Co-Researchers</strong>' +
      '<div style="margin-top:6px">' + coHtml + '</div></div>' : '');

  panel.classList.add('open');
}

// === SCROLL TO TOPIC ===
function scrollToTopic(topicId) {
  if (activeView !== 'timeline' || !tlSvg || !tlZoom || !tlXScaleOrig) return;
  var topic = DATA.topics[topicId];
  if (!topic || !topic._date) return;

  // Compute where this topic is in the original (unzoomed) scale
  var origX = tlXScaleOrig(topic._date);
  var centerTarget = tlPlotW / 2;

  // Get current transform
  var cur = d3.zoomTransform(tlSvg.node());
  // We want: cur.k * origX + newTx = centerTarget
  // newTx = centerTarget - cur.k * origX
  var newTx = centerTarget - cur.k * origX;

  var newTransform = clampTimelineTransform(
    d3.zoomIdentity.translate(newTx, 0).scale(cur.k)
  );
  tlSvg.transition().duration(400).call(tlZoom.transform, newTransform);
}

// === KEYBOARD NAVIGATION ===
function navigateConnected(direction) {
  if (!pinnedTopicId) return;
  var current = DATA.topics[pinnedTopicId];
  if (!current) return;

  // Get connected topics sorted by date
  var refs = direction === 'next' ? (current.inc || []) : (current.out || []);
  if (refs.length === 0) {
    // Fallback: try the other direction
    refs = direction === 'next' ? (current.out || []) : (current.inc || []);
  }
  if (refs.length === 0) return;

  // Sort by date and pick the closest one in the chosen direction
  var candidates = refs.map(function(id) { return DATA.topics[id]; }).filter(Boolean);
  candidates.sort(function(a, b) { return new Date(a.d) - new Date(b.d); });

  var currentDate = new Date(current.d);
  var target = null;
  if (direction === 'next') {
    // Pick earliest topic after current date, or first if all are before
    target = candidates.find(function(t) { return new Date(t.d) >= currentDate && t.id !== current.id; });
    if (!target) target = candidates[candidates.length - 1];
  } else {
    // Pick latest topic before current date, or last if all are after
    var reversed = candidates.slice().reverse();
    target = reversed.find(function(t) { return new Date(t.d) <= currentDate && t.id !== current.id; });
    if (!target) target = candidates[0];
  }

  if (target && target.id !== pinnedTopicId) {
    showDetail(target);
    scrollToTopic(target.id);
  }
}

// === THREAD DETAIL PANEL ===
function showThreadDetail(tid) {
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var th = DATA.threads[tid];
  if (!th) return;

  var color = THREAD_COLORS[tid] || '#555';

  // Stats grid
  var statsHtml = '<div class="thread-stat-grid">' +
    '<div class="thread-stat-box"><div class="tsb-val">' + th.tc + '</div><div class="tsb-lbl">Topics</div></div>' +
    '<div class="thread-stat-box"><div class="tsb-val">' + (th.ay || []).length + '</div><div class="tsb-lbl">Active Years</div></div>' +
    '<div class="thread-stat-box"><div class="tsb-val">' + (th.py || '\u2014') + '</div><div class="tsb-lbl">Peak Year</div></div>' +
    '<div class="thread-stat-box"><div class="tsb-val">' + ((th.ad || 0) * 100).toFixed(0) + '%</div><div class="tsb-lbl">Author Diversity</div></div>' +
    '</div>';

  // Key authors
  var authorsHtml = '';
  if (th.ka && Object.keys(th.ka).length > 0) {
    authorsHtml = '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Key Authors</strong><div style="margin-top:4px">';
    Object.entries(th.ka).forEach(function(entry) {
      var name = entry[0], count = entry[1];
      var aColor = authorColorMap[name] || '#667';
      authorsHtml += '<span style="display:inline-block;font-size:11px;margin:2px 4px 2px 0;padding:1px 6px;' +
        'background:' + aColor + '22;border:1px solid ' + aColor + '44;border-radius:3px;color:' + aColor + ';cursor:pointer" ' +
        'onclick="showAuthorDetail(\'' + escHtml(name) + '\')">' +
        escHtml(name) + ' <span style="color:#666;font-size:9px">(' + count + ')</span></span>';
    });
    authorsHtml += '</div></div>';
  }

  // EIPs
  var eipsHtml = '';
  if (th.te && th.te.length > 0) {
    eipsHtml = '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Top EIPs</strong> ';
    eipsHtml += th.te.map(function(e) { return '<span class="eip-tag primary" onclick="showEipPopover(' + e + ', event)">EIP-' + e + '</span>'; }).join(' ');
    eipsHtml += '</div>';
  }

  // Milestones
  var msHtml = '';
  if (th.ms && th.ms.length > 0) {
    msHtml = '<div style="margin:12px 0"><strong style="font-size:11px;color:#888">Influential Posts</strong>' +
      '<div class="milestone-list">';
    th.ms.forEach(function(ms) {
      var noteLabel = ms.n.replace('_', ' ');
      msHtml += '<div class="milestone-item">' +
        '<span class="ms-note">' + noteLabel + '</span>' +
        '<span class="ms-title" onclick="showDetail(DATA.topics[' + ms.id + '])" ' +
        'onmouseenter="highlightTopicInView(' + ms.id + ')" onmouseleave="restorePinnedHighlight()">' +
        escHtml(ms.t) + '</span>' +
        '<span style="color:#666;font-size:10px;flex-shrink:0">' + (ms.d || '').slice(0, 7) + '</span></div>';
    });
    msHtml += '</div></div>';
  }

  // Top topics
  var topsHtml = '';
  if (th.tops && th.tops.length > 0) {
    topsHtml = '<div class="detail-refs"><h4>Top Topics</h4>';
    th.tops.forEach(function(tid) {
      var topic = DATA.topics[tid];
      if (!topic) return;
      topsHtml += '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + tid + '])" ' +
        'onmouseenter="highlightTopicInView(' + tid + ')" onmouseleave="restorePinnedHighlight()">' +
        escHtml(topic.t) + '</a> <span style="color:#666;font-size:10px">(' + topic.inf.toFixed(2) + ')</span></div>';
    });
    topsHtml += '</div>';
  }

  content.innerHTML =
    '<h2 style="color:' + color + '">' + escHtml(th.n) + '</h2>' +
    '<div class="meta">Research Thread \u00b7 ' + (th.dr ? th.dr[0] + ' to ' + th.dr[1] : '') + '</div>' +
    statsHtml + authorsHtml + eipsHtml + msHtml + topsHtml;

  panel.classList.add('open');
}

// === ERA DETAIL ===
function showEraDetail(eraIdx) {
  var era = DATA.eras[eraIdx];
  if (!era) return;
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');

  // Forks in this era
  var eraForks = DATA.forks.filter(function(f) {
    return f.d && f.d >= era.start && f.d <= era.end;
  });
  var forksHtml = eraForks.length > 0 ?
    '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Forks Shipped</strong><div style="margin-top:4px">' +
    eraForks.map(function(f) {
      var forkName = f.cn || f.n;
      return '<span class="fork-tag" onclick="openForkByName(' + jsQuote(forkName) + ', event)">' + escHtml(forkName) + ' (' + f.d.slice(0, 7) + ')</span>';
    }).join(' ') + '</div></div>' : '';

  // Most active threads in this era (count topics per thread)
  var threadCounts = {};
  Object.values(DATA.topics).forEach(function(t) {
    if (t.d >= era.start && t.d <= era.end && t.th) {
      threadCounts[t.th] = (threadCounts[t.th] || 0) + 1;
    }
  });
  var sortedThreads = Object.entries(threadCounts).sort(function(a, b) { return b[1] - a[1]; });
  var threadsHtml = sortedThreads.length > 0 ?
    '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Most Active Threads</strong><div style="margin-top:4px">' +
    sortedThreads.slice(0, 5).map(function(entry) {
      var tid = entry[0], count = entry[1];
      var color = THREAD_COLORS[tid] || '#555';
      var name = DATA.threads[tid] ? DATA.threads[tid].n : tid;
      return '<span style="display:inline-block;font-size:11px;margin:2px 4px 2px 0;padding:1px 6px;' +
        'background:' + color + '22;border:1px solid ' + color + '44;border-radius:3px;color:' + color + ';cursor:pointer" ' +
        'onclick="toggleThread(\'' + tid + '\')">' +
        escHtml(name) + ' <span style="color:#666;font-size:9px">(' + count + ')</span></span>';
    }).join('') + '</div></div>' : '';

  // Top topics of this era
  var eraTopics = Object.values(DATA.topics).filter(function(t) {
    return t.d >= era.start && t.d <= era.end;
  }).sort(function(a, b) { return b.inf - a.inf; });
  var topsHtml = eraTopics.length > 0 ?
    '<div class="detail-refs"><h4>Top Topics (' + eraTopics.length + ' total)</h4>' +
    eraTopics.slice(0, 10).map(function(t) {
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + t.id + '])" ' +
        'onmouseenter="highlightTopicInView(' + t.id + ')" onmouseleave="restorePinnedHighlight()">' +
        escHtml(t.t) + '</a> <span style="color:#666;font-size:10px">(' + t.inf.toFixed(2) + ')</span></div>';
    }).join('') + '</div>' : '';

  content.innerHTML =
    '<h2>' + escHtml(era.name) + '</h2>' +
    '<div class="meta">Era \u00b7 ' + era.start.slice(0, 7) + ' to ' + era.end.slice(0, 7) + '</div>' +
    '<div class="detail-excerpt" style="font-style:normal">' + escHtml(era.character) + '</div>' +
    forksHtml + threadsHtml + topsHtml;

  panel.classList.add('open');
}

// === LINEAGE TRACING ===
function traceLineage(topicId) {
  if (lineageActive && lineageSet.has(topicId)) {
    // Toggle off
    clearLineage();
    return;
  }

  // BFS upstream (follow incoming refs) and downstream (follow outgoing refs)
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  lineageSet.add(topicId);

  // Upstream: who does this topic cite, and who do THEY cite (2 hops via t.out)
  // Actually incoming refs = topics that cite this one = descendants
  // outgoing refs = topics this one cites = ancestors
  // "upstream" = ancestors = follow outgoing refs
  // "downstream" = descendants = follow incoming refs

  var upQueue = [{id: topicId, depth: 0}];
  var visited = new Set([topicId]);
  while (upQueue.length > 0) {
    var cur = upQueue.shift();
    if (cur.depth >= 2) continue;
    var topic = DATA.topics[cur.id];
    if (!topic) continue;
    (topic.out || []).forEach(function(refId) {
      lineageSet.add(refId);
      lineageEdgeSet.add(cur.id + '-' + refId);
      lineageEdgeSet.add(refId + '-' + cur.id);
      if (!visited.has(refId)) {
        visited.add(refId);
        upQueue.push({id: refId, depth: cur.depth + 1});
      }
    });
  }

  // Downstream: follow incoming refs (topics that cite this one)
  var downQueue = [{id: topicId, depth: 0}];
  visited = new Set([topicId]);
  while (downQueue.length > 0) {
    var cur = downQueue.shift();
    if (cur.depth >= 2) continue;
    var topic = DATA.topics[cur.id];
    if (!topic) continue;
    (topic.inc || []).forEach(function(refId) {
      lineageSet.add(refId);
      lineageEdgeSet.add(cur.id + '-' + refId);
      lineageEdgeSet.add(refId + '-' + cur.id);
      if (!visited.has(refId)) {
        visited.add(refId);
        downQueue.push({id: refId, depth: cur.depth + 1});
      }
    });
  }

  lineageActive = true;
  applyLineageHighlight();
  updateLineageButton(topicId);
}

function clearLineage() {
  lineageActive = false;
  lineageSet = new Set();
  lineageEdgeSet = new Set();
  applyFilters();
  // Update button if detail panel is open
  var btn = document.getElementById('lineage-btn');
  if (btn) {
    btn.textContent = 'Trace Lineage';
    btn.style.borderColor = '#5566aa';
    btn.style.color = '#8899cc';
  }
}

function updateLineageButton(topicId) {
  var btn = document.getElementById('lineage-btn');
  if (btn) {
    btn.textContent = 'Clear Lineage (' + lineageSet.size + ' topics)';
    btn.style.borderColor = '#88aaff';
    btn.style.color = '#88aaff';
  }
}

function applyLineageHighlight() {
  if (!lineageActive) return;
  if (activeView === 'timeline') applyLineageTimeline();
  else if (activeView === 'network') applyLineageNetwork();
}

function applyLineageTimeline() {
  d3.selectAll('.topic-circle')
    .attr('opacity', function(d) { return lineageSet.has(d.id) ? 1 : 0.04; })
    .attr('r', function(d) { return lineageSet.has(d.id) ? tlRScale(d.inf) * 1.2 : tlRScale(d.inf); });

  d3.selectAll('.edge-line')
    .attr('stroke', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? '#88aaff' : '#556';
    })
    .attr('stroke-opacity', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? 0.6 : 0.01;
    })
    .attr('stroke-width', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? 2 : 1;
    })
    .attr('marker-end', function(e) {
      var key = e.source + '-' + e.target;
      return lineageEdgeSet.has(key) ? 'url(#arrow-lineage)' : 'url(#arrow-default)';
    });
  syncLabels();
}

function applyLineageNetwork() {
  d3.selectAll('.net-node .net-shape').attr('opacity', function(d) {
    return lineageSet.has(d.id) ? 1 : 0.04;
  });

  d3.selectAll('.net-link')
    .attr('stroke', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? '#88aaff' : '#334';
    })
    .attr('stroke-opacity', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? 0.7 : 0.02;
    })
    .attr('stroke-width', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? 2.5 : 1;
    })
    .attr('marker-end', function(l) {
      var sid = typeof l.source === 'object' ? l.source.id : l.source;
      var tid = typeof l.target === 'object' ? l.target.id : l.target;
      var key = sid + '-' + tid;
      return lineageEdgeSet.has(key) ? 'url(#net-arrow-highlight)' : 'url(#net-arrow-default)';
    });
}

// === FIND PATH ===
function refreshNetworkForFocusChange() {
  if (!showPapers) return;
  var netSvg = document.querySelector('#network-view svg');
  if (activeView === 'network') {
    if (netSvg) { netSvg.remove(); simulation = null; }
    buildNetwork();
  } else if (netSvg) {
    netSvg.remove();
    simulation = null;
  }
}

function focusTopicNode(d) {
  if (!d) return;
  var panel = document.getElementById('detail-panel');
  if (panel) panel.classList.remove('open');
  if (similarActive) clearSimilar();
  pinnedTopicId = d.id;
  activeEipNum = null;
  activeMagiciansId = null;
  activePaperId = null;
  applyFilters();
  refreshNetworkForFocusChange();
  updateHash();
}

function focusEipNode(num) {
  var n = Number(num);
  if (!isFinite(n)) return;
  var panel = document.getElementById('detail-panel');
  if (panel) panel.classList.remove('open');
  if (similarActive) clearSimilar();
  pinnedTopicId = null;
  activeEipNum = n;
  activeMagiciansId = null;
  activePaperId = null;
  applyFilters();
  refreshNetworkForFocusChange();
  updateHash();
}

function focusMagiciansNode(id) {
  var mid = Number(id);
  if (!isFinite(mid)) return;
  var panel = document.getElementById('detail-panel');
  if (panel) panel.classList.remove('open');
  if (similarActive) clearSimilar();
  pinnedTopicId = null;
  activeEipNum = null;
  activeMagiciansId = mid;
  activePaperId = null;
  applyFilters();
  refreshNetworkForFocusChange();
  updateHash();
}

function focusPaperNode(paperId) {
  var pid = String(paperId || '').trim();
  if (!pid || !(DATA.papers || {})[pid]) return;
  var panel = document.getElementById('detail-panel');
  if (panel) panel.classList.remove('open');
  if (similarActive) clearSimilar();
  pinnedTopicId = null;
  activeEipNum = null;
  activeMagiciansId = null;
  activePaperId = pid;
  applyFilters();
  refreshNetworkForFocusChange();
  updateHash();
}

function handleTopicClick(ev, d) {
  if (ev.shiftKey && pinnedTopicId && pinnedTopicId !== d.id) {
    // Shift+click = find path from pinned to clicked
    activatePath(pinnedTopicId, d.id);
    return;
  }
  focusTopicNode(d);
}

function handleTopicDoubleClick(ev, d) {
  if (!d) return;
  showDetail(d);
}

function findPath(startId, endId) {
  // BFS on topicEdgeIndex to find shortest path
  if (startId === endId) return [startId];
  var visited = new Set([startId]);
  var queue = [[startId]];
  while (queue.length > 0) {
    var path = queue.shift();
    var current = path[path.length - 1];
    var neighbors = topicEdgeIndex[String(current)] || new Set();
    for (var n of neighbors) {
      if (n === endId) return path.concat([n]);
      if (!visited.has(n)) {
        visited.add(n);
        queue.push(path.concat([n]));
      }
    }
    if (path.length > 8) break; // max depth
  }
  return null; // no path found
}

function activatePath(startId, endId) {
  var path = findPath(startId, endId);
  if (!path) {
    showToast('No citation path found (max 8 hops)');
    pathMode = false; pathStart = null;
    return;
  }
  pathSet = new Set(path);
  pathEdgeSet = new Set();
  for (var i = 0; i < path.length - 1; i++) {
    pathEdgeSet.add(path[i] + '-' + path[i + 1]);
    pathEdgeSet.add(path[i + 1] + '-' + path[i]);
  }
  pathMode = true;

  // Highlight path
  applyPathHighlight();

  // Show path in detail panel
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  content.innerHTML = '<h2>Citation Path (' + path.length + ' steps)</h2>' +
    '<div class="meta">From ' + escHtml(DATA.topics[startId].t) + ' to ' + escHtml(DATA.topics[endId].t) + '</div>' +
    '<div class="detail-refs" style="margin-top:12px">' +
    path.map(function(id, i) {
      var t = DATA.topics[id];
      if (!t) return '';
      return '<div class="ref-item" style="display:flex;align-items:center;gap:6px">' +
        '<span style="color:#44cc88;font-size:10px;font-weight:600;flex-shrink:0">' + (i + 1) + '</span>' +
        '<a onclick="showDetail(DATA.topics[' + id + '])" ' +
        'onmouseenter="highlightTopicInView(' + id + ')" onmouseleave="restorePinnedHighlight()">' +
        escHtml(t.t) + '</a> <span style="color:#666;font-size:10px">(' + t.d.slice(0, 7) + ')</span></div>';
    }).join('') + '</div>' +
    '<div style="margin-top:10px"><button onclick="clearPath()" ' +
    'style="background:#1a1a2e;border:1px solid #44cc88;color:#44cc88;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">Clear Path</button></div>';
  panel.classList.add('open');
}

function clearPath() {
  pathMode = false; pathStart = null;
  pathSet = new Set(); pathEdgeSet = new Set();
  applyFilters();
  document.getElementById('detail-panel').classList.remove('open');
}

function applyPathHighlight() {
  if (activeView === 'timeline') {
    d3.selectAll('.topic-circle')
      .attr('opacity', function(d) { return pathSet.has(d.id) ? 1 : 0.04; })
      .attr('r', function(d) { return pathSet.has(d.id) ? tlRScale(d.inf) * 1.3 : tlRScale(d.inf); });
    d3.selectAll('.edge-line')
      .attr('stroke', function(d) {
        var key = d.source + '-' + d.target;
        return pathEdgeSet.has(key) ? '#44cc88' : '#556';
      })
      .attr('stroke-opacity', function(d) {
        var key = d.source + '-' + d.target;
        return pathEdgeSet.has(key) ? 0.8 : 0.01;
      })
      .attr('stroke-width', function(d) {
        var key = d.source + '-' + d.target;
        return pathEdgeSet.has(key) ? 2.5 : 1;
      });
    syncLabels();
  } else if (activeView === 'network') {
    d3.selectAll('.net-node .net-shape').attr('opacity', function(d) { return pathSet.has(d.id) ? 1 : 0.04; });
    d3.selectAll('.net-link')
      .attr('stroke', function(l) {
        var sid = typeof l.source === 'object' ? l.source.id : l.source;
        var tid = typeof l.target === 'object' ? l.target.id : l.target;
        return pathEdgeSet.has(sid + '-' + tid) ? '#44cc88' : '#334';
      })
      .attr('stroke-opacity', function(l) {
        var sid = typeof l.source === 'object' ? l.source.id : l.source;
        var tid = typeof l.target === 'object' ? l.target.id : l.target;
        return pathEdgeSet.has(sid + '-' + tid) ? 0.8 : 0.02;
      });
  }
}

// === FIND SIMILAR ===
let similarActive = false;
let similarSet = new Set();

function jaccardSets(a, b) {
  if (a.size === 0 && b.size === 0) return 0;
  var inter = 0;
  a.forEach(function(v) { if (b.has(v)) inter++; });
  return inter / (a.size + b.size - inter);
}

function findSimilar(topicId) {
  if (similarActive && similarSet.has(topicId)) {
    clearSimilar();
    return;
  }
  var t = DATA.topics[topicId];
  if (!t) return;

  var tRefs = new Set((t.out || []).concat(t.inc || []));
  var tEips = new Set((t.eips || []).concat(t.peips || []));
  var tTags = new Set(t.tg || []);
  var tParts = new Set(t.parts || []);

  var scores = [];
  Object.values(DATA.topics).forEach(function(other) {
    if (other.id === topicId) return;
    var oRefs = new Set((other.out || []).concat(other.inc || []));
    var oEips = new Set((other.eips || []).concat(other.peips || []));
    var oTags = new Set(other.tg || []);
    var oParts = new Set(other.parts || []);

    var refScore = jaccardSets(tRefs, oRefs);
    var eipScore = jaccardSets(tEips, oEips);
    var tagScore = jaccardSets(tTags, oTags);
    var threadBonus = (t.th && t.th === other.th) ? 1 : 0;
    var partScore = jaccardSets(tParts, oParts);

    var score = 0.4 * refScore + 0.2 * eipScore + 0.2 * tagScore + 0.1 * threadBonus + 0.1 * partScore;
    if (score > 0.01) scores.push({id: other.id, score: score});
  });

  scores.sort(function(a, b) { return b.score - a.score; });
  var top10 = scores.slice(0, 10);

  similarSet = new Set([topicId]);
  top10.forEach(function(s) { similarSet.add(s.id); });
  similarActive = true;

  highlightTopicSet(similarSet);

  // Update button
  var btn = document.getElementById('similar-btn');
  if (btn) { btn.textContent = 'Clear Similar (' + top10.length + ')'; btn.style.borderColor = '#44aa88'; btn.style.color = '#44aa88'; }

  // Show similar list in detail panel
  var listEl = document.getElementById('similar-list');
  if (listEl) {
    listEl.innerHTML = '<h4>Similar Topics</h4>' + top10.map(function(s) {
      var ref = DATA.topics[s.id];
      if (!ref) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + s.id + '])" ' +
        'onmouseenter="highlightTopicInView(' + s.id + ')" onmouseleave="restorePinnedHighlight()">' +
        escHtml(ref.t) + '</a> <span style="color:#666;font-size:10px">(' + (s.score * 100).toFixed(0) + '%)</span></div>';
    }).join('');
  }
}

function clearSimilar() {
  similarActive = false;
  similarSet = new Set();
  applyFilters();
  var btn = document.getElementById('similar-btn');
  if (btn) { btn.textContent = 'Find Similar'; btn.style.borderColor = '#44aa88'; btn.style.color = '#66bbaa'; }
  var listEl = document.getElementById('similar-list');
  if (listEl) listEl.innerHTML = '';
}


// === EXCERPT TOGGLE ===
function toggleExcerpt() {
  var short = document.getElementById('excerpt-short');
  var full = document.getElementById('excerpt-full');
  var btn = document.getElementById('excerpt-toggle');
  if (!short || !full || !btn) return;
  if (full.style.display === 'none') {
    short.style.display = 'none'; full.style.display = 'inline'; btn.textContent = 'show less';
  } else {
    short.style.display = 'inline'; full.style.display = 'none'; btn.textContent = 'show more';
  }
}

// === TOAST ===
function showToast(msg) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(function() { el.classList.remove('show'); }, 2000);
}

// === EXPORT REFS ===
function exportRefsMarkdown(topicId, direction) {
  var t = DATA.topics[topicId];
  if (!t) return;
  var refs = direction === 'out' ? (t.out || []) : (t.inc || []);
  if (refs.length === 0) { showToast('No references to export'); return; }
  var lines = refs.map(function(id) {
    var ref = DATA.topics[id];
    if (!ref) return null;
    return '- [' + ref.t + '](https://ethresear.ch/t/' + id + ')';
  }).filter(Boolean);
  var header = '## ' + (direction === 'out' ? 'References from' : 'Citations of') + ': ' + t.t + '\n\n';
  navigator.clipboard.writeText(header + lines.join('\n')).then(function() {
    showToast('Copied ' + lines.length + ' references as Markdown');
  });
}

function toggleCrossForumMode() {
  var panel = document.getElementById('cross-forum-panel');
  var btn = document.getElementById('cross-forum-btn');
  if (!panel || !btn) return;
  var currentlyOpen = panel.style.display !== 'none';
  panel.style.display = currentlyOpen ? 'none' : 'block';
  btn.textContent = currentlyOpen ? 'Cross-Forum Mode' : 'Hide Cross-Forum';
}

function magiciansRefTag(mid, maxLen) {
  var mt = (DATA.magiciansTopics || {})[String(mid)];
  var text = mt ? magiciansLabelTitle(mt, maxLen || 34) : ('M#' + mid);
  var full = mt ? magiciansDisplayTitle(mt) : ('M#' + mid);
  return '<span class="eip-tag" style="border-color:#6a4a85;color:#c8b5db;cursor:pointer" ' +
    'title="' + escHtml(full) + '" onclick="showMagiciansTopicDetailById(' + mid + ')">' + escHtml(text) + '</span>';
}

function buildCrossForumTraversalHtml(t) {
  if (!t) return '';

  var orderedEips = [];
  var seenEips = new Set();
  (t.peips || []).concat(t.eips || []).forEach(function(e) {
    var num = Number(e);
    if (!num || seenEips.has(num)) return;
    seenEips.add(num);
    orderedEips.push(num);
  });

  var eipRows = orderedEips.slice(0, 18).map(function(eipNum) {
    var magSet = new Set();
    var eip = (DATA.eipCatalog || {})[String(eipNum)];
    if (eip && eip.mt) magSet.add(Number(eip.mt));
    var mapped = eipToMagiciansRefs[String(eipNum)];
    if (mapped) mapped.forEach(function(mid) { magSet.add(Number(mid)); });

    var magArr = Array.from(magSet).filter(Boolean).sort(function(a, b) { return a - b; });
    var magHtml = magArr.length > 0
      ? magArr.map(function(mid) {
          return magiciansRefTag(mid, 32);
        }).join(' ')
      : '<span style="color:#666;font-size:10px">no linked Magicians thread</span>';

    return '<div class="ref-item"><span class="eip-tag primary" onclick="showEipDetailByNum(' + eipNum + ')">EIP-' + eipNum + '</span> ' +
      '<span style="color:#666">\u2192</span> ' + magHtml + '</div>';
  }).join('');

  var directMagSet = new Set((t.mr || []).map(function(mid) { return Number(mid); }));
  var directMapped = topicToMagiciansRefs[String(t.id)];
  if (directMapped) directMapped.forEach(function(mid) { directMagSet.add(Number(mid)); });
  var directMagArr = Array.from(directMagSet).filter(Boolean).sort(function(a, b) { return a - b; });
  var directHtml = directMagArr.length > 0
    ? directMagArr.map(function(mid) {
        return magiciansRefTag(mid, 34);
      }).join(' ')
    : '<span style="color:#666;font-size:10px">none</span>';

  if (!eipRows && directMagArr.length === 0) {
    return '<div id="cross-forum-panel" class="detail-refs" style="display:none"><h4>Cross-Forum Traversal</h4>' +
      '<div style="font-size:11px;color:#666">No related EIP/Magicians links for this topic.</div></div>';
  }

  return '<div id="cross-forum-panel" class="detail-refs" style="display:none">' +
    '<h4>Cross-Forum Traversal</h4>' +
    '<div style="font-size:10px;color:#666;margin-bottom:6px">ethresear.ch topic \u2192 related EIPs \u2192 related Magicians threads</div>' +
    (eipRows ? '<div style="margin-bottom:8px">' + eipRows + '</div>' : '') +
    '<div><strong style="font-size:11px;color:#888">Direct topic \u2192 Magicians</strong><div style="margin-top:4px">' + directHtml + '</div></div>' +
    '</div>';
}

function inferredCoauthorNamesFromExcerpt(t) {
  if (!t || !t.exc) return [];
  var m = String(t.exc).match(/co-?authored by\s+([^\.]+)/i);
  if (!m || !m[1]) return [];
  var phrase = String(m[1]).replace(/\s+/g, ' ').trim();
  if (!phrase) return [];
  phrase = phrase.replace(/\s+(and|&)\s+/gi, ', ');
  return phrase.split(',').map(function(name) {
    return String(name).replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, '').trim();
  }).filter(Boolean).slice(0, 8);
}

function buildCrossForumTraversalHtmlForEip(num, eip, relTopics) {
  var magSet = new Set();
  if (eip && eip.mt) magSet.add(Number(eip.mt));
  var mapped = eipToMagiciansRefs[String(num)];
  if (mapped) mapped.forEach(function(mid) { magSet.add(Number(mid)); });
  var magArr = Array.from(magSet).filter(Boolean).sort(function(a, b) { return a - b; });
  var magHtml = magArr.length > 0
    ? magArr.map(function(mid) {
        return magiciansRefTag(mid, 34);
      }).join(' ')
    : '<span style="color:#666;font-size:10px">none</span>';

  var topicHtml = '';
  if (relTopics && relTopics.length > 0) {
    var sorted = relTopics.map(function(tid) { return DATA.topics[tid]; }).filter(Boolean)
      .sort(function(a, b) { return (b.inf || 0) - (a.inf || 0); }).slice(0, 10);
    topicHtml = sorted.map(function(t) {
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + t.id + '])" ' +
        'onmouseenter="highlightTopicInView(' + t.id + ')" onmouseleave="restorePinnedHighlight()">' +
        escHtml(t.t) + '</a> <span style="color:#666;font-size:10px">(' + t.inf.toFixed(2) + ')</span></div>';
    }).join('');
  }

  return '<div id="cross-forum-panel" class="detail-refs" style="display:none">' +
    '<h4>Cross-Forum Traversal</h4>' +
    '<div style="font-size:10px;color:#666;margin-bottom:6px">ethresear.ch topic \u2192 EIP-' + num + ' \u2192 related Magicians threads</div>' +
    (topicHtml ? '<div style="margin-bottom:8px"><strong style="font-size:11px;color:#888">Related ethresear.ch topics</strong>' + topicHtml + '</div>' : '') +
    '<div><strong style="font-size:11px;color:#888">EIP \u2192 Magicians</strong><div style="margin-top:4px">' + magHtml + '</div></div>' +
    '</div>';
}

// === DETAIL PANEL ===
function showDetail(t) {
  var wasAlreadyPinned = pinnedTopicId !== null;
  pinnedTopicId = t.id;
  activeEipNum = null;
  activeMagiciansId = null;
  activePaperId = null;
  applyFilters();
  if (showPapers) {
    var netSvgShowDetail = document.querySelector('#network-view svg');
    if (activeView === 'network') {
      if (netSvgShowDetail) { netSvgShowDetail.remove(); simulation = null; }
      buildNetwork();
    } else if (netSvgShowDetail) {
      netSvgShowDetail.remove();
      simulation = null;
    }
  }
  // Auto-scroll timeline when navigating between topics (not on first click)
  if (wasAlreadyPinned) scrollToTopic(t.id);

  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');

  // EIP tags -- distinguish primary (topic is about this EIP) from mentions
  var primarySet = new Set(t.peips || []);

  var thread = t.th ? DATA.threads[t.th] : null;
  var threadName = thread ? thread.n : 'Unassigned';
  var threadColor = t.th ? (THREAD_COLORS[t.th] || '#555') : '#555';

  // Build refs HTML
  var outRefs = '';
  if (t.out && t.out.length > 0) {
    outRefs = t.out.slice(0, 10).map(function(id) {
      var ref = DATA.topics[id];
      if (!ref) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + id + '])" ' +
             'onmouseenter="highlightTopicInView(' + id + ')" ' +
             'onmouseleave="restorePinnedHighlight()">' +
             escHtml(ref.t) + '</a></div>';
    }).join('');
  }

  var incRefs = '';
  if (t.inc && t.inc.length > 0) {
    incRefs = t.inc.slice(0, 10).map(function(id) {
      var ref = DATA.topics[id];
      if (!ref) return '';
      return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + id + '])" ' +
             'onmouseenter="highlightTopicInView(' + id + ')" ' +
             'onmouseleave="restorePinnedHighlight()">' +
             escHtml(ref.t) + '</a></div>';
    }).join('');
  }

  // Milestone badge
  var msBadge = '';
  var msInfo = milestoneIndex[t.id];
  if (msInfo) {
    var msColor = THREAD_COLORS[msInfo.threadId] || '#ffcc44';
    msBadge = '<div class="milestone-badge"><span class="mb-icon">\u2605</span>' +
      escHtml(msInfo.human) + ' in <span style="color:' + msColor + ';cursor:pointer" onclick="toggleThread(\'' + escHtml(msInfo.threadId) + '\')">' +
      escHtml(msInfo.threadName) + '</span></div>';
  }

  var minorBadge = t.mn ? '<div style="display:inline-block;font-size:10px;padding:2px 8px;border-radius:3px;margin:4px 0 8px;' +
    'background:#1a1a2a;border:1px solid #333;color:#889">Minor Topic</div>' : '';

  // Magicians cross-references
  var magiciansHtml = '';
  if (t.mr && t.mr.length > 0) {
    magiciansHtml = '<div class="detail-refs"><h4>Magicians Discussions (' + t.mr.length + ')</h4>';
    t.mr.forEach(function(mtid) {
      var mt = (DATA.magiciansTopics || {})[String(mtid)] || null;
      var rowTitle = mt ? magiciansDisplayTitle(mt) : ('M#' + mtid);
      var rowLabel = mt ? magiciansLabelTitle(mt, 62) : ('M#' + mtid);
      var linkedEips = magiciansToEips[String(mtid)] || [];
      var eipHtml = linkedEips.slice(0, 2).map(function(e) {
        return '<span class="eip-tag primary" onclick="showEipDetailByNum(' + e + ')">EIP-' + e + '</span>';
      }).join(' ');
      if (linkedEips.length > 2) {
        eipHtml += ' <span style="color:#666;font-size:10px">+' + (linkedEips.length - 2) + '</span>';
      }
      var mergedBadge = linkedEips.length > 0 && showEips
        ? '<span style="color:#88719d;font-size:10px">merged when EIPs visible</span>'
        : '';
      magiciansHtml += '<div class="ref-item">' +
        '<a onclick="showMagiciansTopicDetailById(' + mtid + ')" style="color:#bb88cc;cursor:pointer" title="' + escHtml(rowTitle) + '">' + escHtml(rowLabel) + '</a>' +
        (eipHtml ? ' <span style="margin-left:4px">' + eipHtml + '</span>' : '') +
        (mergedBadge ? ' <span style="margin-left:4px">' + mergedBadge + '</span>' : '') +
        ' <a href="https://ethereum-magicians.org/t/' + mtid + '" target="_blank" class="magicians-link">open on magicians &#8599;</a></div>';
    });
    magiciansHtml += '</div>';
  }
  var traversalHtml = buildCrossForumTraversalHtml(t);
  var topicPapersHtml = buildRelatedPapersHtml(relatedPapersForTopic(t.id), 'topic-' + t.id, 'Related Papers');
  var coauthorEntries = [];
  var seenCoauthors = new Set();
  var mainAuthorNorm = normalizeIdentityToken(t.a);
  function addResolvedCoauthor(entry) {
    if (!entry) return;
    var key = entry.key || (entry.kind + ':' + normalizeIdentityToken(entry.target || entry.label));
    if (!key || seenCoauthors.has(key)) return;
    if (entry.kind === 'eth' && normalizeIdentityToken(entry.target || entry.label) === mainAuthorNorm) return;
    if (entry.kind === 'eip' && (linkedEipAuthors(t.a) || []).indexOf(entry.target) >= 0) return;
    seenCoauthors.add(key);
    coauthorEntries.push(entry);
  }
  (t.coauth || []).forEach(function(u) {
    addResolvedCoauthor({kind: 'eth', target: u, label: u, key: 'eth:' + normalizeIdentityToken(u)});
  });
  inferredCoauthorNamesFromExcerpt(t).forEach(function(name) {
    addResolvedCoauthor(resolveBylineCoauthorIdentity(name));
  });
  function renderCoauthorEntry(entry) {
    if (entry.kind === 'eth') {
      return '<span onclick="openAuthor(' + jsQuote(entry.target) + ')" style="cursor:pointer;color:#7788cc">' + escHtml(entry.label || entry.target) + '</span>';
    }
    if (entry.kind === 'eip') {
      return '<span onclick="openEipAuthor(' + jsQuote(entry.target) + ')" style="cursor:pointer;color:#88aacc">' + escHtml(entry.label || entry.target) + '</span>';
    }
    return '<span style="color:#9aa5d4">' + escHtml(entry.label || '') + '</span>';
  }
  var coauthorInline = '';
  if (coauthorEntries.length > 0) {
    var inlineLinks = coauthorEntries.slice(0, 3).map(renderCoauthorEntry).join(', ');
    if (coauthorEntries.length > 3) {
      inlineLinks += ' <span style="color:#666">+' + (coauthorEntries.length - 3) + '</span>';
    }
    coauthorInline = ' \u00b7 with ' + inlineLinks;
  }
  var coauthorRow = coauthorEntries.length > 3
    ? '<div class="detail-stat"><span class="label">Coauthors</span><span class="value">' + coauthorEntries.map(renderCoauthorEntry).join(', ') + '</span></div>'
    : '';

  content.innerHTML =
    '<h2>' + escHtml(t.t) + '</h2>' +
    minorBadge +
    msBadge +
    '<div class="meta">by <strong onclick="openAuthor(\'' + escHtml(t.a) + '\')" style="cursor:pointer;color:#7788cc">' + escHtml(t.a) + '</strong>' + coauthorInline + ' \u00b7 ' + (t.d || '') +
    ' \u00b7 <a href="https://ethresear.ch/t/' + t.id + '" target="_blank">Open on ethresear.ch \u2192</a></div>' +
    coauthorRow +
    '<div class="detail-stat"><span class="label">Thread</span><span class="value" style="color:' + threadColor + ';cursor:pointer" onclick="toggleThread(\'' + escHtml(t.th || '') + '\')">' + threadName + '</span></div>' +
    '<div class="detail-stat"><span class="label">Influence</span><span class="value">' + (t.inf || 0).toFixed(3) + '</span></div>' +
    '<div class="detail-stat"><span class="label">Views</span><span class="value">' + (t.vw || 0).toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Likes</span><span class="value">' + (t.lk || 0) + '</span></div>' +
    '<div class="detail-stat"><span class="label">Posts</span><span class="value">' + (t.pc || 0) + '</span></div>' +
    '<div class="detail-stat"><span class="label">Cited by</span><span class="value">' + (t.ind || 0) + ' topics</span></div>' +
    '<div class="detail-stat"><span class="label">Category</span><span class="value" style="cursor:pointer;color:#7788cc" onclick="toggleCategory(\'' + escHtml(t.cat || '') + '\')">' + escHtml(t.cat || '') + '</span></div>' +
    '<div style="margin:10px 0 6px;display:flex;gap:6px"><button id="lineage-btn" onclick="traceLineage(' + t.id + ')" ' +
    'style="background:#1a1a2e;border:1px solid ' + (lineageActive && lineageSet.has(t.id) ? '#88aaff' : '#5566aa') +
    ';color:' + (lineageActive && lineageSet.has(t.id) ? '#88aaff' : '#8899cc') +
    ';padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">' +
    (lineageActive && lineageSet.has(t.id) ? 'Clear Lineage (' + lineageSet.size + ' topics)' : 'Trace Lineage') +
    '</button>' +
    '<button id="similar-btn" onclick="findSimilar(' + t.id + ')" ' +
    'style="background:#1a1a2e;border:1px solid ' + (similarActive && similarSet.has(t.id) ? '#44aa88' : '#44aa88') +
    ';color:' + (similarActive && similarSet.has(t.id) ? '#44aa88' : '#66bbaa') +
    ';padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">' +
    (similarActive && similarSet.has(t.id) ? 'Clear Similar (' + (similarSet.size - 1) + ')' : 'Find Similar') +
    '</button>' +
    '<button id="cross-forum-btn" onclick="toggleCrossForumMode()" ' +
    'style="background:#1a1a2e;border:1px solid #6a4a85;color:#c8b5db;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">Cross-Forum Mode</button>' +
    '</div>' +
    (t.exc ? '<div class="detail-excerpt"><span id="excerpt-short">' + escHtml(t.exc.length > 300 ? t.exc.slice(0, 300) + '...' : t.exc) + '</span>' +
      '<span id="excerpt-full" style="display:none">' + escHtml(t.exc) + '</span>' +
      (t.exc.length > 300 ? ' <span onclick="toggleExcerpt()" style="color:#66bbaa;cursor:pointer;font-size:10px;font-style:normal" id="excerpt-toggle">show more</span>' : '') +
      '</div>' : '') +
    (t.peips && t.peips.length > 0 ? '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIPs discussed:</strong> ' +
      t.peips.map(function(e) { return '<span class="eip-tag primary" onclick="showEipPopover(' + e + ', event)">EIP-' + e + '</span>'; }).join(' ') + '</div>' : '') +
    (t.eips && t.eips.length > (t.peips||[]).length ?
      '<div style="margin:4px 0"><strong style="font-size:11px;color:#666">Also mentions:</strong> ' +
      (t.eips || []).filter(function(e) { return !primarySet.has(e); }).map(function(e) {
        return '<span class="eip-tag" onclick="showEipPopover(' + e + ', event)">EIP-' + e + '</span>';
      }).join(' ') + '</div>' : '') +
    topicPapersHtml +
    traversalHtml +
    magiciansHtml +
    (outRefs ? '<div class="detail-refs"><h4>References (' + t.out.length + ') <span onclick="exportRefsMarkdown(' + t.id + ',\'out\')" ' +
      'style="font-size:9px;color:#66bbaa;cursor:pointer;text-transform:none;font-weight:400;margin-left:6px">copy md</span></h4>' + outRefs + '</div>' : '') +
    (incRefs ? '<div class="detail-refs"><h4>Cited by (' + t.inc.length + ') <span onclick="exportRefsMarkdown(' + t.id + ',\'inc\')" ' +
      'style="font-size:9px;color:#66bbaa;cursor:pointer;text-transform:none;font-weight:400;margin-left:6px">copy md</span></h4>' + incRefs + '</div>' : '') +
    '<div id="similar-list" class="detail-refs"></div>';

  panel.classList.add('open');
  updateHash();

  // Re-populate similar list if still active for this topic
  if (similarActive && similarSet.has(t.id)) findSimilar(t.id);
}

function closeDetail() {
  clearFocusedEntityState({keepDetailOpen: false});
}

// === TOOLTIP ===
function showTooltip(ev, t) {
  var tip = document.getElementById('tooltip');
  var primary = (t.peips && t.peips.length > 0) ? ' [EIP-' + t.peips.join(', EIP-') + ']' : '';
  tip.innerHTML = '<strong>' + escHtml(t.t) + '</strong><br>' +
                  escHtml(t.a) + ' \u00b7 ' + t.d + ' \u00b7 inf: ' + t.inf.toFixed(2) +
                  primary;
  tip.style.display = 'block';

  // Position near cursor, fixed to viewport
  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  // Keep on screen
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

function showPaperTooltip(ev, paper, node) {
  if (!paper) return;
  var tip = document.getElementById('tooltip');
  var pid = String((paper.id || (node && (node.paperId || node._paperId || node.id)) || '')).replace(/^paper_/, '').trim();
  var year = paper.y ? String(paper.y) : '?';
  var authors = paperAuthorsShort(paper, 2);
  var eips = PAPER_TO_EIP_IDS[pid] || uniqueSortedNumbers(paper.eq || []);
  var eipHint = eips.length > 0
    ? '<br><span style="color:#9cc8ff">' + eips.slice(0, 3).map(function(n) { return 'EIP-' + n; }).join(', ') + '</span>'
    : '';
  tip.innerHTML =
    '<strong>' + escHtml(paper.t || 'Untitled paper') + '</strong><br>' +
    year +
    (authors ? ' · ' + escHtml(authors) : '') +
    (paper.cb ? ' · OpenAlex cites ' + Number(paper.cb).toLocaleString() : '') +
    (node && node.paperScore ? ' · score ' + Number(node.paperScore).toFixed(2) : '') +
    eipHint;
  tip.style.display = 'block';

  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

function showPaperDetail(paper, node) {
  if (!paper) return;
  var pid = String(paper.id || '').trim();
  if (pid) {
    pinnedTopicId = null;
    activeEipNum = null;
    activeMagiciansId = null;
    activePaperId = pid;
    applyFilters();
    refreshNetworkForFocusChange();
  }
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var url = paperUrl(paper);
  var eips = PAPER_TO_EIP_IDS[pid] || uniqueSortedNumbers(paper.eq || []);
  var authors = (paper.a || []);
  var tagChips = (paper.tg || []).slice(0, 8).map(function(tag) {
    return '<span class="eip-tag" style="border-color:#3a4f6c;color:#9cc8ff">' + escHtml(tag) + '</span>';
  }).join(' ');
  var eipChips = eips.slice(0, 14).map(function(num) {
    return '<span class="eip-tag primary" onclick="showEipDetailByNum(' + num + ')">EIP-' + num + '</span>';
  }).join(' ');
  if (eips.length > 14) {
    eipChips += ' <span style="color:#666;font-size:10px">+' + (eips.length - 14) + '</span>';
  }

  var linkedTargets = [];
  var linkedSeen = new Set();
  function addLinkedTarget(targetId) {
    if (targetId === undefined || targetId === null) return;
    var normalized = targetId;
    if (typeof normalized === 'number') normalized = Number(normalized);
    if (typeof normalized === 'string') normalized = normalized.trim();
    if (!normalized && normalized !== 0) return;
    var key = String(normalized);
    if (linkedSeen.has(key)) return;
    linkedSeen.add(key);
    linkedTargets.push(normalized);
  }
  var nodeTargets = [];
  if (node && Array.isArray(node.linkedTargets)) nodeTargets = nodeTargets.concat(node.linkedTargets);
  if (node && Array.isArray(node._paperLinkedTargets)) nodeTargets = nodeTargets.concat(node._paperLinkedTargets);
  nodeTargets.forEach(addLinkedTarget);
  (PAPER_TO_TOPIC_IDS[pid] || []).forEach(function(tid) { addLinkedTarget(Number(tid)); });
  (PAPER_TO_EIP_IDS[pid] || []).forEach(function(num) { addLinkedTarget('eip_' + String(num)); });
  (PAPER_TO_MAGICIANS_IDS[pid] || []).forEach(function(mid) { addLinkedTarget('mag_' + String(mid)); });

  var linkedRows = '';
  if (linkedTargets.length > 0) {
    linkedRows = linkedTargets.slice(0, 14).map(function(targetId) {
      if (typeof targetId === 'number') {
        var t = DATA.topics[targetId];
        if (!t) return '';
        return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + targetId + '])">' + escHtml(t.t) + '</a></div>';
      }
      if (typeof targetId === 'string' && targetId.indexOf('eip_') === 0) {
        var num = Number(targetId.slice(4));
        var e = (DATA.eipCatalog || {})[String(num)] || {};
        var label = 'EIP-' + num + (e.t ? ': ' + e.t : '');
        return '<div class="ref-item"><a onclick="showEipDetailByNum(' + num + ')">' + escHtml(label) + '</a></div>';
      }
      if (typeof targetId === 'string' && targetId.indexOf('mag_') === 0) {
        var mid = Number(targetId.slice(4));
        var mt = (DATA.magiciansTopics || {})[String(mid)];
        if (!mt) return '';
        return '<div class="ref-item"><a onclick="showMagiciansTopicDetailById(' + mid + ')">' + escHtml(magiciansDisplayTitle(mt)) + '</a></div>';
      }
      return '';
    }).filter(Boolean).join('');
  }

  content.innerHTML =
    '<h2>' + escHtml(paper.t || 'Untitled paper') + '</h2>' +
    '<div class="meta">' +
    (authors.length > 0 ? escHtml(authors.join(', ')) + ' · ' : '') +
    (paper.y ? paper.y : '?') +
    (paper.v ? ' · ' + escHtml(paper.v) : '') +
    ' · ' +
    (url ? '<a href="' + escHtml(url) + '" target="_blank">Open paper →</a>' : 'No canonical URL') +
    '</div>' +
    (node && node.paperScore ? '<div class="detail-stat"><span class="label">Network Score</span><span class="value">' + Number(node.paperScore).toFixed(3) + '</span></div>' : '') +
    '<div class="detail-stat"><span class="label">Relevance</span><span class="value">' + Number(paper.rs || 0).toFixed(3) + '</span></div>' +
    '<div class="detail-stat"><span class="label">Citations (OpenAlex)</span><span class="value">' + Number(paper.cb || 0).toLocaleString() + '</span></div>' +
    (paper.doi ? '<div class="detail-stat"><span class="label">DOI</span><span class="value">' + escHtml(paper.doi) + '</span></div>' : '') +
    (paper.ax ? '<div class="detail-stat"><span class="label">ArXiv/ePrint</span><span class="value">' + escHtml(paper.ax) + '</span></div>' : '') +
    (eipChips ? '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIP Mentions</strong> ' + eipChips + '</div>' : '') +
    (tagChips ? '<div style="margin:8px 0"><strong style="font-size:11px;color:#666">Tags</strong> ' + tagChips + '</div>' : '') +
    (linkedRows ? '<div class="detail-refs"><h4>Linked in Network</h4>' + linkedRows + '</div>' : '');

  panel.classList.add('open');
  updateHash();
}

function magiciansTopicUrl(mt) {
  if (!mt) return 'https://ethereum-magicians.org';
  if (mt.sl) return 'https://ethereum-magicians.org/t/' + encodeURIComponent(mt.sl) + '/' + mt.id;
  return 'https://ethereum-magicians.org/t/' + mt.id;
}

function showMagiciansTooltip(ev, mt) {
  if (!mt) return;
  var tip = document.getElementById('tooltip');
  var title = magiciansDisplayTitle(mt);
  var mid = magiciansTopicId(mt);
  var eipHint = (mt.eips || []).slice(0, 3).map(function(e) { return 'EIP-' + e; }).join(', ');
  tip.innerHTML = '<strong>' + escHtml(title) + '</strong><br>' +
                  '<span style="color:#bfa6d6">M#' + (mid !== null ? mid : '?') + '</span> \u00b7 ' +
                  escHtml(mt.a || 'unknown') + ' \u00b7 ' + (mt.d || '') +
                  ' \u00b7 posts: ' + Number(mt.pc || 0) +
                  (eipHint ? '<br><span style="color:#bfa6d6">' + eipHint + '</span>' : '');
  tip.style.display = 'block';
  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

function showMagiciansTopicDetailById(id) {
  var mt = (DATA.magiciansTopics || {})[String(id)];
  if (!mt) return;
  showMagiciansTopicDetail(mt);
}

function showMagiciansTopicDetail(mt) {
  if (!mt) return;
  pinnedTopicId = null;
  activeEipNum = null;
  activeMagiciansId = mt.id;
  activePaperId = null;
  if (similarActive) clearSimilar();
  applyFilters();
  if (showPapers) {
    var netSvgMag = document.querySelector('#network-view svg');
    if (activeView === 'network') {
      if (netSvgMag) { netSvgMag.remove(); simulation = null; }
      buildNetwork();
    } else if (netSvgMag) {
      netSvgMag.remove();
      simulation = null;
    }
  }
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var threadId = magiciansThreadFromTopic(mt);
  var thread = threadId ? DATA.threads[threadId] : null;
  var threadName = thread ? thread.n : 'Unassigned';
  var threadColor = threadId ? (THREAD_COLORS[threadId] || '#bb88cc') : '#bb88cc';
  var title = magiciansDisplayTitle(mt);
  var topicId = magiciansTopicId(mt);
  var authorName = (mt.a || 'unknown').trim();
  var linkedEth = linkedEthAuthorsFromMag(authorName);
  var linkedEip = linkedEipAuthorsFromMag(authorName);
  var mergedEips = magiciansLinkedEips(mt);
  var eips = (mt.eips || []);
  var relTopics = (mt.er || []).map(function(tid) { return DATA.topics[tid]; }).filter(Boolean)
    .sort(function(a, b) { return (b.inf || 0) - (a.inf || 0); });
  var relTopicsHtml = relTopics.slice(0, 12).map(function(t) {
    return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + t.id + '])" ' +
      'onmouseenter="highlightTopicInView(' + t.id + ')" ' +
      'onmouseleave="restorePinnedHighlight()">' + escHtml(t.t) + '</a></div>';
  }).join('');
  var tagsHtml = (mt.tg || []).map(function(tag) {
    return '<span class="eip-tag" style="border-color:#6a4a85;color:#c8b5db">' + escHtml(tag) + '</span>';
  }).join(' ');
  var eipsHtml = eips.map(function(e) {
    return '<span class="eip-tag primary" onclick="showEipDetailByNum(' + e + ')">EIP-' + e + '</span>';
  }).join(' ');
  var linkedEthHtml = linkedEth.map(function(username) {
    return '<span style="cursor:pointer;color:#7788cc" onclick="openAuthor(' + jsQuote(username) + ')">' + escHtml(username) + '</span>';
  }).join(', ');
  var linkedEipHtml = linkedEip.map(function(name) {
    return '<span style="cursor:pointer;color:#7788cc" onclick="openEipAuthor(' + jsQuote(name) + ')">' + escHtml(name) + '</span>';
  }).join(', ');
  var authorLinkable = linkedEth.length > 0 || linkedEip.length > 0;
  var authorHtml = authorLinkable
    ? '<span style="cursor:pointer;color:#7788cc" onclick="openMagiciansAuthor(' + jsQuote(authorName) + ')">' + escHtml(authorName || 'unknown') + '</span>'
    : '<strong>' + escHtml(authorName || 'unknown') + '</strong>';
  var threadValueHtml = threadId
    ? '<span class="value" style="color:' + threadColor + ';cursor:pointer" onclick="toggleThread(\'' + escHtml(threadId) + '\')">' + threadName + '</span>'
    : '<span class="value" style="color:' + threadColor + '">' + threadName + '</span>';
  var mergedHtml = mergedEips.length > 0
    ? '<div class="milestone-badge"><span class="mb-icon">\u25A0</span>Merged with EIP node when EIPs are visible</div>'
    : '';

  content.innerHTML =
    '<h2>' + escHtml(title) + '</h2>' +
    '<div class="meta">M#' + (topicId !== null ? topicId : '?') + ' \u00b7 by ' + authorHtml + ' \u00b7 ' + (mt.d || '') +
    ' \u00b7 <a href="' + magiciansTopicUrl(mt) + '" target="_blank">Open on ethereum-magicians.org \u2192</a></div>' +
    mergedHtml +
    '<div class="detail-stat"><span class="label">Thread</span>' + threadValueHtml + '</div>' +
    '<div class="detail-stat"><span class="label">Views</span><span class="value">' + Number(mt.vw || 0).toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Likes</span><span class="value">' + Number(mt.lk || 0).toLocaleString() + '</span></div>' +
    '<div class="detail-stat"><span class="label">Posts</span><span class="value">' + Number(mt.pc || 0).toLocaleString() + '</span></div>' +
    (linkedEthHtml ? '<div class="detail-stat"><span class="label">ethresearch</span><span class="value">' + linkedEthHtml + '</span></div>' : '') +
    (linkedEipHtml ? '<div class="detail-stat"><span class="label">EIP Authors</span><span class="value">' + linkedEipHtml + '</span></div>' : '') +
    (mt.cat ? '<div class="detail-stat"><span class="label">Category</span><span class="value">' + escHtml(mt.cat) + '</span></div>' : '') +
    (eipsHtml ? '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Related EIPs</strong> ' + eipsHtml + '</div>' : '') +
    (tagsHtml ? '<div style="margin:8px 0"><strong style="font-size:11px;color:#666">Tags</strong> ' + tagsHtml + '</div>' : '') +
    (relTopicsHtml ? '<div class="detail-refs"><h4>Related ethresear.ch Topics (' + relTopics.length + ')</h4>' + relTopicsHtml + '</div>' : '');
  panel.classList.add('open');
  updateHash();
}

// === EIP POPOVER ===
function showEipPopover(eipNum, ev) {
  ev.stopPropagation();
  var pop = document.getElementById('eip-popover');
  var eipStr = String(eipNum);
  var eip = (DATA.eipCatalog || {})[eipStr];

  if (!eip) {
    // No catalog entry — show minimal popover
    pop.innerHTML = '<h3>EIP-' + eipNum + '</h3><div style="color:#888">No metadata available</div>' +
      '<div style="margin-top:8px"><a href="https://eips.ethereum.org/EIPS/eip-' + eipNum + '" target="_blank" class="magicians-link">View on eips.ethereum.org &#8599;</a></div>';
    positionPopover(pop, ev);
    return;
  }

  var statusClass = 'eip-status eip-status-' + (eip.s || '').toLowerCase().replace(/\s+/g, '');
  var html = '<h3>EIP-' + eipNum + ': ' + escHtml(eip.t || '') + '</h3>';
  html += '<span class="' + statusClass + '">' + escHtml(eip.s || 'Unknown') + '</span>';

  // Type / Category
  var typeCat = [];
  if (eip.ty) typeCat.push(escHtml(eip.ty));
  if (eip.c) typeCat.push(escHtml(eip.c));
  if (typeCat.length) html += '<div style="margin-top:6px;color:#aaa;font-size:11px">' + typeCat.join(' &middot; ') + '</div>';

  // Fork
  if (eip.fk) html += '<div style="margin-top:4px"><span class="fork-tag" onclick="openForkByName(' + jsQuote(eip.fk) + ', event)">' + escHtml(eip.fk) + '</span></div>';

  // Created
  if (eip.cr) html += '<div style="margin-top:4px;color:#888;font-size:11px">Created: ' + escHtml(eip.cr) + '</div>';

  // Authors
  if (eip.au && eip.au.length > 0) {
    html += '<div style="margin-top:4px;color:#888;font-size:11px">Authors: ' + eip.au.map(function(a) { return escHtml(a); }).join(', ') + '</div>';
  }

  // Requires
  if (eip.rq && eip.rq.length > 0) {
    html += '<div style="margin-top:6px;font-size:11px;color:#888">Requires: ' +
      eip.rq.map(function(r) { return '<span class="eip-tag" onclick="showEipPopover(' + r + ', event)">EIP-' + r + '</span>'; }).join(' ') + '</div>';
  }

  // External links
  html += '<div style="margin-top:8px;display:flex;flex-direction:column;gap:3px">';
  html += '<a href="https://eips.ethereum.org/EIPS/eip-' + eipNum + '" target="_blank" class="magicians-link">View on eips.ethereum.org &#8599;</a>';
  if (eip.mt) {
    html += '<a href="https://ethereum-magicians.org/t/' + eip.mt + '" target="_blank" class="magicians-link">Magicians discussion &#8599;</a>';
  }
  if (eip.et) {
    html += '<a href="https://ethresear.ch/t/' + eip.et + '" target="_blank" class="magicians-link">ethresear.ch discussion &#8599;</a>';
  }
  html += '</div>';

  // Related topics (from eipToTopics index)
  var relTopics = eipToTopics[eipNum] || eipToTopics[eipStr];
  if (relTopics && relTopics.size > 0) {
    var sorted = Array.from(relTopics).map(function(tid) { return DATA.topics[tid]; }).filter(Boolean)
      .sort(function(a, b) { return (b.inf || 0) - (a.inf || 0); }).slice(0, 5);
    if (sorted.length > 0) {
      html += '<div style="margin-top:8px;border-top:1px solid #333;padding-top:6px">' +
        '<div style="font-size:10px;color:#666;margin-bottom:4px">Related topics (' + relTopics.size + ')</div>';
      sorted.forEach(function(rt) {
        html += '<div style="font-size:11px;padding:2px 0"><a onclick="closeEipPopover();showDetail(DATA.topics[' + rt.id + '])" ' +
          'style="color:#7788cc;cursor:pointer;text-decoration:none">' + escHtml(rt.t) + '</a></div>';
      });
      html += '</div>';
    }
  }

  pop.innerHTML = html;
  positionPopover(pop, ev);
}

function positionPopover(pop, ev) {
  pop.style.display = 'block';
  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  var pw = pop.offsetWidth;
  var ph = pop.offsetHeight;
  if (x + pw > window.innerWidth - 10) x = ev.clientX - pw - 14;
  if (y + ph > window.innerHeight - 10) y = window.innerHeight - ph - 10;
  if (y < 5) y = 5;
  pop.style.left = x + 'px';
  pop.style.top = y + 'px';
}

function closeEipPopover() {
  document.getElementById('eip-popover').style.display = 'none';
}

function findForkByName(name) {
  if (!name) return null;
  var needle = String(name).toLowerCase();
  for (var i = 0; i < (DATA.forks || []).length; i++) {
    var f = DATA.forks[i];
    if (!f) continue;
    if ((f.cn && String(f.cn).toLowerCase() === needle) ||
        (f.n && String(f.n).toLowerCase() === needle) ||
        (f.el && String(f.el).toLowerCase() === needle) ||
        (f.cl && String(f.cl).toLowerCase() === needle)) {
      return f;
    }
  }
  return null;
}

function openForkByName(name, ev) {
  var f = findForkByName(name);
  if (!f) {
    showToast('No fork metadata found for ' + name);
    return;
  }
  if (ev && ev.stopPropagation) ev.stopPropagation();
  if (ev && ev.clientX !== undefined && ev.clientY !== undefined) {
    showForkPopover(ev, f);
    return;
  }
  showForkPopover({clientX: window.innerWidth * 0.55, clientY: 120, stopPropagation: function() {}}, f);
}

function showForkDetail(f) {
  if (!f) return;
  hideTooltip();
  closeEipPopover();
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var name = f.cn || f.n || 'Fork';
  var eips = (f.eips || []).slice();
  var related = (f.rt || []).map(function(tid) { return DATA.topics[tid]; }).filter(Boolean)
    .sort(function(a, b) { return (b.inf || 0) - (a.inf || 0); });
  var eipsHtml = eips.map(function(e) {
    return '<span class="eip-tag primary" onclick="showEipDetailByNum(' + e + ')">EIP-' + e + '</span>';
  }).join(' ');
  var relatedHtml = related.slice(0, 16).map(function(rt) {
    return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + rt.id + '])" ' +
      'onmouseenter="highlightTopicInView(' + rt.id + ')" ' +
      'onmouseleave="restorePinnedHighlight()">' + escHtml(rt.t) + '</a>' +
      ' <span style="color:#666;font-size:10px">(' + (rt.inf || 0).toFixed(2) + ')</span></div>';
  }).join('');
  var forkPapersHtml = buildRelatedPapersHtml(
    relatedPapersForFork(f),
    'fork-' + (f.cn || f.n || ''),
    'Related Papers'
  );

  content.innerHTML =
    '<h2>' + escHtml(name) + '</h2>' +
    '<div class="meta">Fork milestone' + (f.d ? ' \u00b7 ' + escHtml(f.d) : '') + '</div>' +
    (f.el || f.cl ? '<div class="detail-stat"><span class="label">Clients</span><span class="value">' +
      (f.el ? ('EL: ' + escHtml(f.el)) : '') +
      (f.el && f.cl ? ' \u00b7 ' : '') +
      (f.cl ? ('CL: ' + escHtml(f.cl)) : '') +
      '</span></div>' : '') +
    '<div class="detail-stat"><span class="label">EIPs</span><span class="value">' + eips.length + '</span></div>' +
    '<div class="detail-stat"><span class="label">Related topics</span><span class="value">' + related.length + '</span></div>' +
    (eipsHtml ? '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Included EIPs</strong> ' + eipsHtml + '</div>' : '') +
    (relatedHtml ? '<div class="detail-refs"><h4>Top Related Topics</h4>' + relatedHtml + '</div>' : '') +
    forkPapersHtml;
  panel.classList.add('open');
}

function showForkPopover(ev, f) {
  var pop = document.getElementById('eip-popover');
  var html = '<h3>' + escHtml(f.cn || f.n) + '</h3>';
  if (f.d) html += '<div style="color:#888;font-size:11px">' + escHtml(f.d) + '</div>';
  if (f.el || f.cl) {
    html += '<div style="color:#aaa;font-size:11px;margin-top:4px">';
    if (f.el) html += 'EL: ' + escHtml(f.el);
    if (f.el && f.cl) html += ' &middot; ';
    if (f.cl) html += 'CL: ' + escHtml(f.cl);
    html += '</div>';
  }
  if (f.eips && f.eips.length > 0) {
    html += '<div style="margin-top:8px"><div style="font-size:10px;color:#666;margin-bottom:4px">EIPs (' + f.eips.length + ')</div>';
    html += f.eips.map(function(e) {
      return '<span class="eip-tag primary" onclick="showEipPopover(' + e + ', event)">EIP-' + e + '</span>';
    }).join(' ');
    html += '</div>';
  }
  if (f.rt && f.rt.length > 0) {
    var sorted = f.rt.map(function(tid) { return DATA.topics[tid]; }).filter(Boolean)
      .sort(function(a, b) { return (b.inf || 0) - (a.inf || 0); }).slice(0, 5);
    if (sorted.length > 0) {
      html += '<div style="margin-top:8px;border-top:1px solid #333;padding-top:6px">' +
        '<div style="font-size:10px;color:#666;margin-bottom:4px">Related topics (' + f.rt.length + ')</div>';
      sorted.forEach(function(rt) {
        html += '<div style="font-size:11px;padding:2px 0"><a onclick="closeEipPopover();showDetail(DATA.topics[' + rt.id + '])" ' +
          'style="color:#7788cc;cursor:pointer;text-decoration:none">' + escHtml(rt.t) + '</a></div>';
      });
      html += '</div>';
    }
  }
  pop.innerHTML = html;
  positionPopover(pop, ev);
}

// === URL HASH ROUTING ===
function parseHash() {
  var hash = window.location.hash.replace(/^#/, '');
  if (!hash) return {};
  var params = {};
  hash.split('&').forEach(function(part) {
    var kv = part.split('=');
    if (kv.length === 2) params[kv[0]] = decodeURIComponent(kv[1]);
  });
  return params;
}

function buildHash() {
  var parts = [];
  var panel = document.getElementById('detail-panel');
  var detailOpen = !!(panel && panel.classList.contains('open'));
  if (activeView && activeView !== 'timeline') parts.push('view=' + activeView);
  if (activeThread) parts.push('thread=' + encodeURIComponent(activeThread));
  if (activeAuthor) parts.push('author=' + encodeURIComponent(activeAuthor));
  if (activeEipAuthor) parts.push('eip_author=' + encodeURIComponent(activeEipAuthor));
  if (detailOpen && pinnedTopicId) parts.push('topic=' + pinnedTopicId);
  if (detailOpen && activeEipNum !== null && activeEipNum !== undefined) parts.push('eip=' + activeEipNum);
  if (detailOpen && activeMagiciansId) parts.push('mag=' + activeMagiciansId);
  if (detailOpen && activePaperId) parts.push('paper=' + encodeURIComponent(String(activePaperId)));
  if (showEips) {
    parts.push('eips=1');
    if (eipVisibilityMode === 'all') parts.push('eipmode=all');
  }
  if (showMagicians) parts.push('mags=1');
  if (showPapers) {
    parts.push('papers=1');
    parts.push('pmode=' + encodeURIComponent(paperLayerMode));
  }
  return parts.length > 0 ? '#' + parts.join('&') : '';
}

function updateHash() {
  var newHash = buildHash();
  var current = window.location.hash || '';
  if (newHash !== current) {
    if (newHash) {
      history.replaceState(null, '', newHash);
    } else {
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }
}

function applyHash() {
  var params = parseHash();
  var changed = false;
  var eipModeChanged = false;
  var paperModeChanged = false;

  // Switch view if specified
  if (params.view && params.view !== activeView) {
    if (params.view === 'network' || params.view === 'coauthor' || params.view === 'timeline') {
      showView(params.view);
      changed = true;
    }
  }

  // Apply thread filter
  if (params.thread && params.thread !== activeThread) {
    if (DATA.threads[params.thread]) {
      activeThread = params.thread;
      document.querySelectorAll('.thread-chip').forEach(function(c) {
        c.classList.toggle('active', c.dataset.thread === activeThread);
      });
      changed = true;
    }
  }

  // Apply author filter
  if (params.author || params.eip_author) {
    var nextEthAuthor = params.author || null;
    var nextEipAuthor = params.eip_author ? canonicalEipAuthorName(params.eip_author) : null;
    if (nextEthAuthor && !nextEipAuthor) {
      var linkedEips = linkedEipAuthors(nextEthAuthor);
      if (linkedEips.length > 0) nextEipAuthor = linkedEips[0];
    }
    if (nextEipAuthor && !nextEthAuthor) {
      var linkedEth = linkedEthAuthors(nextEipAuthor);
      if (linkedEth.length > 0) nextEthAuthor = linkedEth[0];
    }
    if (nextEthAuthor !== activeAuthor || nextEipAuthor !== activeEipAuthor) {
      activeAuthor = nextEthAuthor;
      activeEipAuthor = nextEipAuthor;
      refreshAuthorSidebarList();
      changed = true;
    }
  }

  if (params.pmode && PAPER_LAYER_MODES[params.pmode]) {
    if (params.pmode !== paperLayerMode) {
      paperLayerMode = params.pmode;
      updatePaperLayerModeUi();
      paperModeChanged = true;
      changed = true;
      try { localStorage.setItem('evmap.paperLayerMode', paperLayerMode); } catch (e) {}
    }
  }

  // Apply EIP toggle from hash
  if (params.eipmode) {
    var mode = params.eipmode === 'all' ? 'all' : 'connected';
    if (mode !== eipVisibilityMode) {
      eipVisibilityMode = mode;
      eipModeChanged = true;
      changed = true;
    }
  }
  updateEipVisibilityUi();

  if (params.eips === '1' && !showEips) {
    toggleContent('eips', 'on');
    changed = true;
  } else if (params.eips === '1' && showEips && eipModeChanged && activeView === 'network') {
    var netSvg = document.querySelector('#network-view svg');
    if (netSvg) { netSvg.remove(); simulation = null; }
    buildNetwork();
  }

  if (params.mags === '1' && !showMagicians) {
    toggleContent('magicians');
    changed = true;
  }
  if (params.papers === '1' && !showPapers) {
    toggleContent('papers');
    changed = true;
  } else if (params.papers === '1' && showPapers && paperModeChanged && activeView === 'network') {
    var paperNetSvg = document.querySelector('#network-view svg');
    if (paperNetSvg) { paperNetSvg.remove(); simulation = null; }
    buildNetwork();
  }

  if (changed) applyFilters();

  // Open topic detail
  if (params.topic) {
    var topicId = Number(params.topic);
    var t = DATA.topics[topicId];
    if (t) {
      showDetail(t);
      changed = true;
    }
  }

  // Open EIP detail from hash
  if (params.eip) {
    showEipDetailByNum(Number(params.eip));
    changed = true;
  }

  // Open Magicians detail from hash
  if (params.mag) {
    showMagiciansTopicDetailById(Number(params.mag));
    changed = true;
  }

  if (params.paper) {
    var paper = (DATA.papers || {})[String(params.paper)];
    if (paper) {
      showPaperDetail(paper, null);
      changed = true;
    }
  }
}

// === HELP & BREADCRUMB ===
function toggleHelp() {
  document.getElementById('help-overlay').classList.toggle('open');
}

function updateBreadcrumb() {
  var bc = document.getElementById('filter-breadcrumb');
  var parts = [];
  if (activeThread) {
    var th = DATA.threads[activeThread];
    var color = THREAD_COLORS[activeThread] || '#555';
    parts.push('<span class="bc-tag" style="border-color:' + color + '55;color:' + color + '">' +
      (th ? th.n : activeThread) + '<span class="bc-close" onclick="event.stopPropagation();toggleThread(\'' + activeThread + '\')">&times;</span></span>');
  }
  if (hasAuthorFilter()) {
    var aColor = activeAuthor ? (authorColorMap[activeAuthor] || '#667') : '#88aacc';
    var authorLabel = activeAuthor || activeEipAuthor || '';
    if (activeAuthor && activeEipAuthor) {
      authorLabel = activeAuthor + ' \u2194 ' + activeEipAuthor;
    }
    parts.push('<span class="bc-tag" style="border-color:' + aColor + '55;color:' + aColor + '">' +
      escHtml(authorLabel) + '<span class="bc-close" onclick="event.stopPropagation();clearAuthorFilter()">&times;</span></span>');
  }
  if (activeCategory) {
    parts.push('<span class="bc-tag">' + escHtml(activeCategory) +
      '<span class="bc-close" onclick="event.stopPropagation();toggleCategory(\'' + escHtml(activeCategory) + '\')">&times;</span></span>');
  }
  if (activeTag) {
    parts.push('<span class="bc-tag">' + escHtml(activeTag) +
      '<span class="bc-close" onclick="event.stopPropagation();toggleTag(\'' + escHtml(activeTag) + '\')">&times;</span></span>');
  }
  if (parts.length === 0) {
    parts.push('<span class="bc-hint">Click to filter \u00b7 Double-click for details \u00b7 <span style="cursor:pointer;color:#667" onclick="toggleHelp()">?</span> for shortcuts</span>');
  }
  bc.innerHTML = parts.join('');
}

// === UTILS ===
function hashCode(n) {
  return ((n * 2654435761) >>> 0) % 10000;
}

function hashText(value) {
  var s = String(value || '');
  var h = 2166136261 >>> 0;
  for (var i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
}

function starPoints(cx, cy, outerR, innerR, nPoints) {
  var pts = [];
  for (var i = 0; i < nPoints * 2; i++) {
    var angle = (i * Math.PI / nPoints) - Math.PI / 2;
    var r = i % 2 === 0 ? outerR : innerR;
    pts.push((cx + r * Math.cos(angle)).toFixed(1) + ',' + (cy + r * Math.sin(angle)).toFixed(1));
  }
  return pts.join(' ');
}

// ========================================================================
// EIP TIMELINE NODES
// ========================================================================
var eipRScale = null;
var magiciansRScale = null;
var paperTimelineRScale = null;

function inferEipThread(eipNum) {
  var tids = eipToTopicIds[eipNum] || eipToTopicIds[String(eipNum)] || [];
  var counts = {};
  tids.forEach(function(tid) {
    var t = DATA.topics[tid];
    if (!t || !t.th) return;
    counts[t.th] = (counts[t.th] || 0) + 1;
  });
  var best = null;
  var bestCount = 0;
  Object.keys(counts).forEach(function(th) {
    if (counts[th] > bestCount) {
      bestCount = counts[th];
      best = th;
    }
  });
  return best;
}

function timelineLaneYForThread(threadId, seed) {
  var laneIdx = window._laneIdx || {};
  var laneH = window._laneH || 0;
  var topicLaneY0 = window._topicLaneY0 || 0;
  if (!laneH) return null;
  var resolved = (threadId && laneIdx[threadId] !== undefined) ? threadId : '_other';
  var lane = laneIdx[resolved];
  if (lane === undefined) lane = 0;
  var yBase = topicLaneY0 + lane * laneH + laneH * 0.12;
  var yRange = laneH * 0.76;
  return yBase + (hashCode(seed) % 100) / 100 * yRange;
}

function trianglePath(cx, cy, r) {
  return 'M' + cx.toFixed(2) + ',' + (cy - r).toFixed(2) +
    ' L' + (cx + r).toFixed(2) + ',' + (cy + r).toFixed(2) +
    ' L' + (cx - r).toFixed(2) + ',' + (cy + r).toFixed(2) + ' Z';
}

function diamondPath(cx, cy, r) {
  return 'M' + cx.toFixed(2) + ',' + (cy - r).toFixed(2) +
    ' L' + (cx + r).toFixed(2) + ',' + cy.toFixed(2) +
    ' L' + cx.toFixed(2) + ',' + (cy + r).toFixed(2) +
    ' L' + (cx - r).toFixed(2) + ',' + cy.toFixed(2) + ' Z';
}

function drawEipTimeline() {
  // Find the timeline's zoom group
  var zoomG = d3.select('#timeline-view svg g g[clip-path] g');
  if (zoomG.empty()) return;

  // EIP influence scale (squares are sized by influence)
  var maxEipInf = 0;
  Object.values(DATA.eipCatalog || {}).forEach(function(e) {
    if ((e.inf || 0) > maxEipInf) maxEipInf = e.inf;
  });
  eipRScale = d3.scaleSqrt().domain([0, maxEipInf || 1]).range([3, 12]);

  // Prepare EIP data with positions
  var eipData = [];
  Object.entries(DATA.eipCatalog || {}).forEach(function(entry) {
    var num = entry[0], e = entry[1];
    if ((e.inf || 0) < 0.05 || !e.cr) return;
    var d = new Date(e.cr);
    if (isNaN(d)) return;
    var inferredThread = e.th || inferEipThread(Number(num));
    var yPos = timelineLaneYForThread(inferredThread, Number(num));
    if (yPos === null) return;
    e._eipDate = d;
    e._eipNum = Number(num);
    e._eipNodeId = 'eip_' + num;
    e._eipThread = inferredThread || null;
    e._eipYPos = yPos;
    eipData.push(e);
  });

  // Draw EIP squares in the same thread lanes as topics
  var eipG = zoomG.append('g').attr('class', 'eip-layer');

  // Cross-reference edges (EIP → related topic)
  var crossRefG = eipG.append('g');
  var eipGraphEdges = (DATA.eipGraph || {}).edges || [];
  eipGraphEdges.forEach(function(edge) {
    if (edge.type !== 'eip_topic') return;
    var eipNum = edge.source.replace('eip_', '');
    var eip = DATA.eipCatalog[eipNum];
    var topic = DATA.topics[edge.target];
    if (!eip || !eip._eipDate || !topic || topic._yPos === undefined) return;
    crossRefG.append('line')
      .attr('class', 'cross-ref-edge')
      .attr('x1', tlXScale(eip._eipDate)).attr('y1', eip._eipYPos)
      .attr('x2', tlXScale(topic._date)).attr('y2', topic._yPos)
      .attr('marker-end', null)
      .attr('stroke', '#6f94f2').attr('stroke-opacity', 0.14).attr('stroke-width', 0.8)
      .datum({
        eipDate: eip._eipDate,
        topicDate: topic._date,
        eipY: eip._eipYPos,
        topicY: topic._yPos,
        eipNodeId: edge.source,
        eipNum: Number(eipNum),
        eipInf: eip.inf || 0,
        eipThread: eip._eipThread || eip.th || null,
        topicId: edge.target,
      })
      .style('display', (showPosts && showEips) ? null : 'none');
  });

  // Squares
  var squareG = eipG.append('g');
  eipData.forEach(function(e) {
    var sz = eipRScale(e.inf) * 1.4;
    var color = eipColor(e);
    var eipClickTimer = null;
    squareG.append('rect')
      .attr('class', 'eip-square')
      .attr('x', tlXScale(e._eipDate) - sz/2)
      .attr('y', e._eipYPos - sz/2)
      .attr('width', sz).attr('height', sz)
      .attr('rx', 3)
      .attr('fill', color).attr('stroke', color).attr('stroke-width', 0.5)
      .attr('opacity', 0.7)
      .datum(e)
      .on('click', function(ev, d) {
        if (eipClickTimer) {
          clearTimeout(eipClickTimer);
          eipClickTimer = null;
          showEipDetailByNum(d._eipNum);
          return;
        }
        eipClickTimer = setTimeout(function() {
          eipClickTimer = null;
          focusEipNode(d._eipNum);
        }, 220);
      })
      .on('mouseover', function(ev, d) { onTimelineEntityHover(ev, d, 'eip', true); })
      .on('mouseout', function(ev, d) { onTimelineEntityHover(ev, d, 'eip', false); })
      .style('display', showEips ? null : 'none');
  });

  // Labels for top EIPs
  var topEips = eipData.slice().sort(function(a, b) { return b.inf - a.inf; }).slice(0, 15);
  var labelG = eipG.append('g');
  topEips.forEach(function(e) {
    var sz = eipRScale(e.inf) * 1.4;
    labelG.append('text')
      .attr('class', 'eip-label')
      .attr('x', tlXScale(e._eipDate) + sz/2 + 3)
      .attr('y', e._eipYPos + 3)
      .attr('fill', '#99aabb').attr('font-size', 8).attr('pointer-events', 'none')
      .text('EIP-' + e._eipNum)
      .datum(e)
      .style('display', showEips ? null : 'none');
  });

}

function drawMagiciansTimeline() {
  var zoomG = d3.select('#timeline-view svg g g[clip-path] g');
  if (zoomG.empty()) return;

  var maxMagInf = 0;
  Object.values(DATA.magiciansTopics || {}).forEach(function(mt) {
    var inf = magiciansInfluenceScore(mt);
    if (inf > maxMagInf) maxMagInf = inf;
  });
  magiciansRScale = d3.scaleSqrt().domain([0, maxMagInf || 1]).range([3, 11]);

  var magData = [];
  Object.entries(DATA.magiciansTopics || {}).forEach(function(entry) {
    var mtid = entry[0], mt = entry[1] || {};
    if (!mt.d) return;
    var d = new Date(mt.d);
    if (isNaN(d)) return;
    var thread = magiciansThreadFromTopic(mt);
    var yPos = timelineLaneYForThread(thread, Number(mtid));
    if (yPos === null) return;
    mt._magDate = d;
    mt._magId = Number(mtid);
    mt._magInf = magiciansInfluenceScore(mt);
    mt._magThread = thread || null;
    mt._magYPos = yPos;
    magData.push(mt);
  });

  var magG = zoomG.append('g').attr('class', 'magicians-layer');

  // Cross-reference edges (Magicians topic -> related ethresearch topic)
  var crossRefG = magG.append('g');
  magData.forEach(function(mt) {
    (mt.er || []).forEach(function(tid) {
      var topic = DATA.topics[tid];
      if (!topic || topic._yPos === undefined) return;
      crossRefG.append('line')
        .attr('class', 'magicians-ref-edge')
        .attr('x1', tlXScale(mt._magDate)).attr('y1', mt._magYPos)
        .attr('x2', tlXScale(topic._date)).attr('y2', topic._yPos)
        .attr('marker-end', null)
        .attr('stroke', '#9b72c2').attr('stroke-opacity', 0.14).attr('stroke-width', 0.9)
        .attr('stroke-dasharray', '3 3')
        .datum({
          magDate: mt._magDate,
          topicDate: topic._date,
          magY: mt._magYPos,
          topicY: topic._yPos,
          magTopic: mt,
          topicId: tid
        })
        .style('display', (showPosts && showMagicians && magiciansMatchesFilter(mt)) ? null : 'none');
    });
  });

  var triG = magG.append('g');
  magData.forEach(function(mt) {
    var r = magiciansRScale(mt._magInf);
    var magClickTimer = null;
    triG.append('path')
      .attr('class', 'magicians-triangle')
      .attr('d', trianglePath(tlXScale(mt._magDate), mt._magYPos, r))
      .attr('fill', '#bb88cc')
      .attr('stroke', '#bb88cc')
      .attr('stroke-width', 0.5)
      .attr('opacity', 0.78)
      .datum(mt)
      .on('click', function(ev, d) {
        if (magClickTimer) {
          clearTimeout(magClickTimer);
          magClickTimer = null;
          showMagiciansTopicDetailById(d._magId);
          return;
        }
        magClickTimer = setTimeout(function() {
          magClickTimer = null;
          focusMagiciansNode(d._magId);
        }, 220);
      })
      .on('mouseover', function(ev, d) { onTimelineEntityHover(ev, d, 'magicians', true); })
      .on('mouseout', function(ev, d) { onTimelineEntityHover(ev, d, 'magicians', false); })
      .style('display', magiciansMatchesFilter(mt) ? null : 'none');
  });

  var topMagicians = magData.filter(function(mt) {
    return !(showEips && isEipDiscussionMagiciansTopic(mt));
  }).slice().sort(function(a, b) { return (b._magInf || 0) - (a._magInf || 0); }).slice(0, 12);
  var labelG = magG.append('g');
  topMagicians.forEach(function(mt) {
    var r = magiciansRScale(mt._magInf);
    labelG.append('text')
      .attr('class', 'magicians-label')
      .attr('x', tlXScale(mt._magDate) + r + 3)
      .attr('y', mt._magYPos + 3)
      .attr('fill', '#c8b5db').attr('font-size', 8).attr('pointer-events', 'none')
      .text(magiciansLabelTitle(mt, 28))
      .datum(mt)
      .style('display', magiciansMatchesFilter(mt) ? null : 'none');
  });
}

function drawPaperTimeline() {
  var zoomG = d3.select('#timeline-view svg g g[clip-path] g');
  if (zoomG.empty()) return;

  var paperData = [];
  var maxPaperInf = 0;
  PAPER_LIST.forEach(function(paper) {
    if (!paper || !paper.id) return;
    var pid = String(paper.id || '').trim();
    if (!pid) return;
    var d = paperTimelineDate(paper);
    if (!d || isNaN(d)) return;
    var th = inferPaperThread(paper);
    var yPos = timelineLaneYForThread(th, hashText(pid));
    if (yPos === null) return;
    var inf = paperTimelineInfluence(paper);
    if (inf > maxPaperInf) maxPaperInf = inf;

    var topicIds = (PAPER_TO_TOPIC_IDS[pid] || []).filter(function(tid) {
      var t = DATA.topics[tid];
      return !!(t && t._date && t._yPos !== undefined);
    }).sort(function(a, b) {
      var ta = DATA.topics[a] || {};
      var tb = DATA.topics[b] || {};
      return (Number(tb.inf || 0) - Number(ta.inf || 0));
    }).slice(0, 9);

    var eipNums = (PAPER_TO_EIP_IDS[pid] || []).filter(function(num) {
      var eMeta = (DATA.eipCatalog || {})[String(num)];
      return !!(eMeta && eMeta.cr);
    }).slice(0, 8);

    paper._paperId = pid;
    paper._paperDate = d;
    paper._paperThread = th || null;
    paper._paperYPos = yPos;
    paper._paperInf = inf;
    paper._paperTopicIds = topicIds;
    paper._paperEipNums = eipNums;
    paper._paperLinkedTargets = topicIds.concat(eipNums.map(function(num) { return 'eip_' + String(num); }));
    paperData.push(paper);
  });

  paperTimelineRScale = d3.scaleSqrt().domain([0, maxPaperInf || 1]).range([3.5, 10.5]);
  var paperG = zoomG.append('g').attr('class', 'paper-layer');

  var topicRefG = paperG.append('g');
  var eipRefG = paperG.append('g');
  var paperRefG = paperG.append('g');
  var paperPairRows = buildPaperPairRows(paperData.map(function(paper) {
    return {
      id: String(paper._paperId || ''),
      paper: paper,
      date: paper._paperDate,
      yPos: paper._paperYPos,
      meta: paperPairMeta(String(paper._paperId || ''), paper),
    };
  }), {
    candidateMin: 1.2,
    minScore: 1.95,
    limit: 280,
    ensurePerPaper: 1,
    extraBudget: 80,
  });

  paperPairRows.forEach(function(ed) {
    paperRefG.append('line')
      .attr('class', 'paper-paper-edge')
      .attr('x1', tlXScale(ed.paperDateA)).attr('y1', ed.paperYA)
      .attr('x2', tlXScale(ed.paperDateB)).attr('y2', ed.paperYB)
      .attr('marker-end', null)
      .attr('stroke', '#8fb7ef').attr('stroke-opacity', 0.10).attr('stroke-width', 0.85)
      .datum(ed)
      .style('display', (showPapers &&
        paperMatchesTimelineFilter((DATA.papers || {})[String(ed.paperA)] || {}) &&
        paperMatchesTimelineFilter((DATA.papers || {})[String(ed.paperB)] || {})) ? null : 'none');
  });

  paperData.forEach(function(paper) {
    var pid = String(paper._paperId || '');
    var pDate = paper._paperDate;
    var pY = paper._paperYPos;

    (paper._paperTopicIds || []).forEach(function(tid) {
      var t = DATA.topics[tid];
      if (!t || !t._date || t._yPos === undefined) return;
      var bestMagId = null;
      var topicEipNodeIds = [];
      var eips = PAPER_TO_EIP_IDS[pid] || [];
      for (var i = 0; i < eips.length; i++) {
        var num = eips[i];
        if ((eipToTopicIds[String(num)] || []).indexOf(Number(tid)) >= 0) {
          topicEipNodeIds.push('eip_' + String(num));
          var eMeta = (DATA.eipCatalog || {})[String(num)] || {};
          if (eMeta.mt !== undefined && eMeta.mt !== null && !isNaN(Number(eMeta.mt))) {
            bestMagId = Number(eMeta.mt);
          }
        }
      }
      topicRefG.append('line')
        .attr('class', 'paper-topic-ref-edge')
        .attr('x1', tlXScale(pDate)).attr('y1', pY)
        .attr('x2', tlXScale(t._date)).attr('y2', t._yPos)
        .attr('marker-end', null)
        .attr('stroke', '#7ea9e4').attr('stroke-opacity', 0.12).attr('stroke-width', 0.9)
        .datum({
          paperId: pid,
          paperDate: pDate,
          paperY: pY,
          topicId: Number(tid),
          topicDate: t._date,
          topicY: t._yPos,
          magId: bestMagId,
          eipNodeIds: topicEipNodeIds,
        })
        .style('display', (showPosts && showPapers && paperMatchesTimelineFilter(paper) && topicMatchesFilter(t)) ? null : 'none');
    });

    (paper._paperEipNums || []).forEach(function(num) {
      var eMeta = (DATA.eipCatalog || {})[String(num)];
      if (!eMeta || !eMeta.cr) return;
      var eDate = eMeta._eipDate;
      if (!eDate) {
        eDate = new Date(eMeta.cr);
        if (isNaN(eDate)) return;
      }
      var eY = eMeta._eipYPos;
      if (eY === undefined || eY === null) {
        var inferredThread = eMeta.th || inferEipThread(Number(num));
        eY = timelineLaneYForThread(inferredThread, Number(num));
      }
      if (eY === undefined || eY === null) return;
      eipRefG.append('line')
        .attr('class', 'paper-eip-ref-edge')
        .attr('x1', tlXScale(pDate)).attr('y1', pY)
        .attr('x2', tlXScale(eDate)).attr('y2', eY)
        .attr('marker-end', null)
        .attr('stroke', '#8fb7ef').attr('stroke-opacity', 0.12).attr('stroke-width', 0.9)
        .datum({
          paperId: pid,
          paperDate: pDate,
          paperY: pY,
          eipNum: Number(num),
          eipNodeId: 'eip_' + String(num),
          eipDate: eDate,
          eipY: eY,
          magId: (eMeta.mt !== undefined && eMeta.mt !== null && !isNaN(Number(eMeta.mt))) ? Number(eMeta.mt) : null,
        })
        .style('display', (showEips && showPapers && paperMatchesTimelineFilter(paper) && eipMatchesFilter(eMeta)) ? null : 'none');
    });
  });

  var shapeG = paperG.append('g');
  paperData.forEach(function(paper) {
    var r = paperTimelineRScale(paper._paperInf || 0);
    var clickTimer = null;
    function onPaperClick(ev, d) {
      if (clickTimer) {
        clearTimeout(clickTimer);
        clickTimer = null;
        showPaperDetail(d, {
          paperId: d._paperId,
          linkedTargets: (d._paperLinkedTargets || []).slice(0),
          paperScore: Number(d.rs || 0),
        });
        return;
      }
      clickTimer = setTimeout(function() {
        clickTimer = null;
        focusPaperNode(d._paperId);
      }, 220);
    }
    function onPaperOver(ev, d) { onTimelineEntityHover(ev, d, 'paper', true); }
    function onPaperOut(ev, d) { onTimelineEntityHover(ev, d, 'paper', false); }
    function onPaperMove(ev, d) { showPaperTooltip(ev, paperFromNode(d) || d, d); }

    shapeG.append('path')
      .attr('class', 'paper-diamond')
      .attr('d', diamondPath(tlXScale(paper._paperDate), paper._paperYPos, r))
      .attr('fill', '#6fa3df')
      .attr('stroke', '#afd1ff')
      .attr('stroke-width', 0.7)
      .attr('opacity', 0.76)
      .datum(paper)
      .on('click', onPaperClick)
      .on('mouseover', onPaperOver)
      .on('mousemove', onPaperMove)
      .on('mouseout', onPaperOut)
      .style('display', paperMatchesTimelineFilter(paper) ? null : 'none');

    shapeG.append('path')
      .attr('class', 'paper-hit')
      .attr('d', diamondPath(tlXScale(paper._paperDate), paper._paperYPos, Math.max(6.5, r + 2.5)))
      .datum(paper)
      .on('click', onPaperClick)
      .on('mouseover', onPaperOver)
      .on('mousemove', onPaperMove)
      .on('mouseout', onPaperOut)
      .style('display', paperMatchesTimelineFilter(paper) ? null : 'none');
  });

  var topPapers = paperData.slice().sort(function(a, b) {
    var d = paperTimelineInfluence(b) - paperTimelineInfluence(a);
    if (d !== 0) return d;
    d = Number(b.cb || 0) - Number(a.cb || 0);
    if (d !== 0) return d;
    return Number(b.rs || 0) - Number(a.rs || 0);
  }).slice(0, 14);
  var labelG = paperG.append('g');
  topPapers.forEach(function(paper) {
    var r = paperTimelineRScale(paper._paperInf || 0);
    labelG.append('text')
      .attr('class', 'paper-label')
      .attr('x', tlXScale(paper._paperDate) + r + 3)
      .attr('y', paper._paperYPos + 3)
      .text((paper.t || '').length > 32 ? (paper.t || '').slice(0, 31) + '\u2026' : (paper.t || 'paper'))
      .datum(paper)
      .style('display', paperMatchesTimelineFilter(paper) ? null : 'none');
  });
}

function showEipTooltip(ev, e) {
  var tip = document.getElementById('tooltip');
  tip.innerHTML = '<strong>EIP-' + e._eipNum + ': ' + escHtml(e.t || '') + '</strong><br>' +
    '<span class="eip-status eip-status-' + (e.s || '').toLowerCase().replace(/\s+/g, '') + '">' + escHtml(e.s || '') + '</span>' +
    (e.fk ? ' <span class="fork-tag">' + escHtml(e.fk) + '</span>' : '') +
    '<br>Influence: ' + (e.inf || 0).toFixed(3) +
    (e.erc ? ' \u00b7 Citations: ' + e.erc : '') +
    (e.ml ? ' \u00b7 Mag likes: ' + e.ml : '');
  tip.style.display = 'block';
  var x = ev.clientX + 14;
  var y = ev.clientY - 10;
  var tw = tip.offsetWidth;
  var th = tip.offsetHeight;
  if (x + tw > window.innerWidth - 10) x = ev.clientX - tw - 14;
  if (y + th > window.innerHeight - 10) y = window.innerHeight - th - 10;
  if (y < 5) y = 5;
  tip.style.left = x + 'px';
  tip.style.top = y + 'px';
}

// ========================================================================
// EIP DETAIL PANEL
// ========================================================================
function showEipDetailByNum(num) {
  var eipStr = String(num);
  var eip = (DATA.eipCatalog || {})[eipStr];
  if (!eip) return;
  showEipDetail(eip, num);
}

function showEipDetail(eip, num) {
  pinnedTopicId = null;
  activeEipNum = Number(num);
  activeMagiciansId = null;
  activePaperId = null;
  applyFilters();
  if (showPapers) {
    var netSvgEip = document.querySelector('#network-view svg');
    if (activeView === 'network') {
      if (netSvgEip) { netSvgEip.remove(); simulation = null; }
      buildNetwork();
    } else if (netSvgEip) {
      netSvgEip.remove();
      simulation = null;
    }
  }
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var color = eipColor(eip);
  var statusClass = 'eip-status eip-status-' + (eip.s || '').toLowerCase().replace(/\s+/g, '');

  // Type / Category
  var typeCatParts = [];
  if (eip.ty) typeCatParts.push(escHtml(eip.ty));
  if (eip.c) typeCatParts.push(escHtml(eip.c));

  // Requires
  var reqHtml = '';
  if (eip.rq && eip.rq.length > 0) {
    reqHtml = '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Requires</strong> ' +
      eip.rq.map(function(r) { return '<span class="eip-requires-tag" onclick="showEipDetailByNum(' + r + ')">EIP-' + r + '</span>'; }).join(' ') +
      '</div>';
  }

  // Required by (reverse)
  var reqByList = eipRequiredBy[num] || eipRequiredBy[String(num)] || [];
  var reqByHtml = '';
  if (reqByList.length > 0) {
    reqByHtml = '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Required by</strong> ' +
      reqByList.map(function(r) { return '<span class="eip-requires-tag" onclick="showEipDetailByNum(' + r + ')">EIP-' + r + '</span>'; }).join(' ') +
      '</div>';
  }

  // Authors
  var authorsHtml = '';
  if (eip.au && eip.au.length > 0) {
    authorsHtml = '<div class="eip-detail-stat"><span class="label">Authors</span><span class="value">' +
      eip.au.map(function(a) {
        var canonical = canonicalEipAuthorName(a);
        var ea = (DATA.eipAuthors || {})[canonical];
        if (ea) return '<span style="cursor:pointer;color:#7788cc" onclick="openEipAuthor(' + jsQuote(canonical) + ')">' + escHtml(canonical) + '</span>';
        return escHtml(a);
      }).join(', ') + '</span></div>';
  }

  // External links
  var linksHtml = '<div style="margin-top:8px;display:flex;flex-direction:column;gap:3px">' +
    '<a href="https://eips.ethereum.org/EIPS/eip-' + num + '" target="_blank" class="magicians-link">eips.ethereum.org &#8599;</a>';
  if (eip.mt) linksHtml += '<a href="https://ethereum-magicians.org/t/' + eip.mt + '" target="_blank" class="magicians-link">Magicians discussion &#8599;</a>';
  if (eip.et) linksHtml += '<a href="https://ethresear.ch/t/' + eip.et + '" target="_blank" class="magicians-link">ethresear.ch discussion &#8599;</a>';
  linksHtml += '</div>';

  // Related ethresearch topics
  var relTopics = eipToTopicIds[num] || eipToTopicIds[String(num)] || [];
  var relHtml = '';
  if (relTopics.length > 0) {
    var sorted = relTopics.map(function(tid) { return DATA.topics[tid]; }).filter(Boolean)
      .sort(function(a, b) { return (b.inf || 0) - (a.inf || 0); }).slice(0, 10);
    if (sorted.length > 0) {
      relHtml = '<div class="detail-refs" style="margin-top:12px"><h4>Related ethresearch topics (' + relTopics.length + ')</h4>' +
        sorted.map(function(t) {
          return '<div class="ref-item"><a onclick="showDetail(DATA.topics[' + t.id + '])" ' +
            'onmouseenter="highlightTopicInView(' + t.id + ')" onmouseleave="restorePinnedHighlight()">' +
            escHtml(t.t) + '</a> <span style="color:#666;font-size:10px">(' + t.inf.toFixed(2) + ')</span></div>';
        }).join('') + '</div>';
    }
  }
  var traversalHtml = buildCrossForumTraversalHtmlForEip(num, eip, relTopics);
  var eipPapersHtml = buildRelatedPapersHtml(relatedPapersForEip(num, eip), 'eip-' + num, 'Related Papers');

  content.innerHTML =
    '<h2 style="color:' + color + '">EIP-' + num + ': ' + escHtml(eip.t || '') + '</h2>' +
    '<div class="meta"><span class="' + statusClass + '">' + escHtml(eip.s || '') + '</span>' +
    (typeCatParts.length ? ' \u00b7 ' + typeCatParts.join(' \u00b7 ') : '') +
    (eip.fk ? ' <span class="fork-tag" onclick="openForkByName(' + jsQuote(eip.fk) + ', event)">' + escHtml(eip.fk) + '</span>' : '') +
    '</div>' +
    '<div class="eip-detail-stat"><span class="label">Created</span><span class="value">' + escHtml(eip.cr || '') + '</span></div>' +
    '<div class="eip-detail-stat"><span class="label">Influence</span><span class="value">' + (eip.inf || 0).toFixed(3) + '</span></div>' +
    (eip.mv ? '<div class="eip-detail-stat"><span class="label">Magicians Views</span><span class="value">' + (eip.mv || 0).toLocaleString() + '</span></div>' : '') +
    (eip.ml ? '<div class="eip-detail-stat"><span class="label">Magicians Likes</span><span class="value">' + (eip.ml || 0) + '</span></div>' : '') +
    (eip.mp ? '<div class="eip-detail-stat"><span class="label">Magicians Posts</span><span class="value">' + (eip.mp || 0) + '</span></div>' : '') +
    (eip.mpc ? '<div class="eip-detail-stat"><span class="label">Magicians Participants</span><span class="value">' + (eip.mpc || 0) + '</span></div>' : '') +
    '<div class="eip-detail-stat"><span class="label">ethresearch Citations</span><span class="value">' + (eip.erc || 0) + '</span></div>' +
    '<div style="margin:10px 0 6px;display:flex;gap:6px"><button id="cross-forum-btn" onclick="toggleCrossForumMode()" ' +
    'style="background:#1a1a2e;border:1px solid #6a4a85;color:#c8b5db;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">Cross-Forum Mode</button></div>' +
    traversalHtml +
    authorsHtml +
    reqHtml + reqByHtml + linksHtml + eipPapersHtml + relHtml;

  panel.classList.add('open');
  updateHash();
}

// ========================================================================
// EIP AUTHOR DETAIL
// ========================================================================
function showEipAuthorDetail(name) {
  name = canonicalEipAuthorName(name);
  var panel = document.getElementById('detail-panel');
  var content = document.getElementById('detail-content');
  var a = (DATA.eipAuthors || {})[name];
  if (!a) return;
  var linkedEth = linkedEthAuthors(name);
  var linkedEthSet = new Set(linkedEth);
  var linkedTopicCount = 0;
  if (linkedEth.length > 0) {
    Object.values(DATA.topics).forEach(function(t) {
      if (linkedEthSet.has(t.a) || (t.coauth || []).some(function(u) { return linkedEthSet.has(u); })) {
        linkedTopicCount += 1;
      }
    });
  }

  var eipTagsHtml = function(nums, label) {
    if (!nums || nums.length === 0) return '';
    return '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">' + label + ' (' + nums.length + ')</strong><div style="margin-top:4px">' +
      nums.map(function(n) { return '<span class="eip-requires-tag" onclick="showEipDetailByNum(' + n + ')">EIP-' + n + '</span>'; }).join(' ') +
      '</div></div>';
  };

  var forksHtml = '';
  if (a.fk && a.fk.length > 0) {
    forksHtml = '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">Forks Contributed</strong><div style="margin-top:4px">' +
      a.fk.map(function(f) { return '<span class="fork-tag" onclick="openForkByName(' + jsQuote(f) + ', event)">' + escHtml(f) + '</span>'; }).join(' ') + '</div></div>';
  }

  var yearsHtml = (a.yrs && a.yrs.length > 0) ? a.yrs.join(', ') : '';
  var statusHtml = '';
  if (a.st && Object.keys(a.st).length > 0) {
    statusHtml = '<div style="margin:8px 0"><strong style="font-size:11px;color:#888">EIP Statuses</strong><div style="margin-top:4px;font-size:11px;color:#aaa">' +
      Object.entries(a.st).map(function(e) { return e[0] + ': ' + e[1]; }).join(', ') + '</div></div>';
  }

  var identityTabsHtml = '';
  if (linkedEth.length > 0) {
    identityTabsHtml = '<div class="author-tab-wrap" style="margin-top:2px;margin-bottom:10px">' +
      '<span class="author-tab" onclick="openAuthor(' + jsQuote(linkedEth[0]) + ')">ethresearch</span>' +
      '<span class="author-tab active">EIPs</span>' +
      '</div>';
  }

  var linkedEthHtml = '';
  if (linkedEth.length > 0) {
    linkedEthHtml = '<div class="eip-detail-stat"><span class="label">ethresearch</span><span class="value">' +
      linkedEth.map(function(username) {
        return '<span style="cursor:pointer;color:#7788cc" onclick="openAuthor(' + jsQuote(username) + ')">' + escHtml(username) + '</span>';
      }).join(', ') + '</span></div>' +
      '<div class="eip-detail-stat"><span class="label">Linked Topics</span><span class="value">' + linkedTopicCount + '</span></div>';
  }
  var eipAuthorPapersHtml = buildRelatedPapersHtml(
    relatedPapersForEipAuthor(name),
    'eip-author-' + name,
    'Related Papers'
  );

  content.innerHTML =
    '<h2>' + escHtml(name) + '</h2>' +
    '<div class="meta">EIP Author</div>' +
    identityTabsHtml +
    '<div class="eip-detail-stat"><span class="label">EIPs</span><span class="value">' + (a.eips || []).length + '</span></div>' +
    '<div class="eip-detail-stat"><span class="label">Influence Score</span><span class="value">' + (a.inf || 0).toFixed(3) + '</span></div>' +
    '<div class="eip-detail-stat"><span class="label">Active Years</span><span class="value">' + yearsHtml + '</span></div>' +
    linkedEthHtml +
    eipTagsHtml(a.eips, 'EIPs') +
    forksHtml + statusHtml + eipAuthorPapersHtml;

  panel.classList.add('open');
}

// ========================================================================
// EIP AUTHOR TAB IN SIDEBAR
// ========================================================================
function switchAuthorTab(isEip) {
  eipAuthorTab = isEip;
  document.querySelectorAll('.author-tab').forEach(function(el) {
    el.classList.toggle('active', el.dataset.tab === (isEip ? 'eip' : 'ethresearch'));
  });
  if (isEip) {
    buildEipAuthorList(document.getElementById('eip-author-sort').value || 'inf');
  } else {
    sortAuthorList(document.getElementById('author-sort').value || 'inf');
  }
  // Toggle sort dropdown visibility per tab
  var ethSortEl = document.getElementById('author-sort');
  if (ethSortEl) ethSortEl.style.display = isEip ? 'none' : '';
  var eipSortEl = document.getElementById('eip-author-sort');
  if (eipSortEl) eipSortEl.style.display = isEip ? '' : 'none';
}

function eipAuthorTotalCount(a) {
  return (a && a.eips) ? a.eips.length : 0;
}

function eipAuthorShippedCount(a) {
  if (!a) return 0;
  if (a.st && a.st.Final !== undefined) return Number(a.st.Final || 0);
  return (a.eips || []).filter(function(num) {
    var eip = (DATA.eipCatalog || {})[String(num)];
    return eip && eip.s === 'Final';
  }).length;
}

function eipAuthorSortMetric(a, sortField) {
  if (sortField === 'total') return eipAuthorTotalCount(a);
  if (sortField === 'shipped') return eipAuthorShippedCount(a);
  return Number(a.inf || 0);
}

function buildEipAuthorList(sortField) {
  if (!sortField) sortField = (document.getElementById('eip-author-sort').value || 'inf');
  var list = document.getElementById('author-list');
  var selectedEipAuthors = getActiveEipAuthorSet();
  var authors = Object.values(DATA.eipAuthors || {}).sort(function(a, b) {
    var diff = eipAuthorSortMetric(b, sortField) - eipAuthorSortMetric(a, sortField);
    if (diff !== 0) return diff;
    return (Number(b.inf || 0) - Number(a.inf || 0));
  });
  list.innerHTML = '';
  authors.slice(0, 25).forEach(function(a) {
    var item = document.createElement('div');
    item.className = 'author-item';
    item.dataset.eipAuthor = a.n;
    var eipCount = eipAuthorTotalCount(a);
    var shippedCount = eipAuthorShippedCount(a);
    var topFork = (a.fk && a.fk.length > 0) ? a.fk[0] : '';
    var linkedEth = linkedEthAuthors(a.n);
    var metricLabel = sortField === 'shipped'
      ? (shippedCount + ' Final')
      : (sortField === 'total'
          ? (eipCount + ' total')
          : ((Number(a.inf || 0)).toFixed(2) + ' inf'));
    var countLabel = metricLabel + ' · ' + eipCount + ' EIPs';
    if (sidebarWide) {
      if (topFork) countLabel += ' · ' + topFork;
      if (linkedEth.length > 0) {
        countLabel += ' · eth: ' + linkedEth[0] + (linkedEth.length > 1 ? ' +' + (linkedEth.length - 1) : '');
      }
    }
    item.innerHTML = '<span class="author-dot" style="background:#88aacc"></span>' +
      '<span class="author-name">' + escHtml(a.n) + '</span>' +
      '<span class="author-count">' + escHtml(countLabel) + '</span>';
    item.onclick = (function(name) {
      var clickTimer = null;
      return function() {
        if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; return; }
        clickTimer = setTimeout(function() { clickTimer = null; toggleEipAuthor(name); }, 250);
      };
    })(a.n);
    item.ondblclick = (function(name) {
      return function() { selectEipAuthor(name); showEipAuthorDetail(name); };
    })(a.n);
    if (selectedEipAuthors.has(a.n)) item.classList.add('active');
    list.appendChild(item);
  });
}

// (EIP zoom updates are integrated into the main onZoom handler in buildTimeline)
"""


if __name__ == "__main__":
    main()
