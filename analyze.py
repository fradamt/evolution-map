#!/usr/bin/env python3
"""Process ethresear.ch scraped data + protocol history → analysis.json.

Reads 2,903 topics from ../index.json and ../topics/, cross-references with
ethereum-knowledge/fork-history.md, and produces a structured JSON suitable
for both HTML visualization and Markdown narrative generation.

Usage:
    python3 analyze.py
"""

import html
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
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
COAUTHOR_REPORT_PATH = SCRIPT_DIR / "coauthor-report.json"
COAUTHOR_REPORT_MD_PATH = SCRIPT_DIR / "coauthor-report.md"
EIP_METADATA_PATH = SCRIPT_DIR / "eip-metadata.json"
MAGICIANS_INDEX_PATH = SCRAPE_DIR / "magicians_index.json"
MAGICIANS_TOPICS_DIR = SCRAPE_DIR / "magicians_topics"

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
            # Broader PBS/MEV patterns
            r"proposer.?builder", r"block.?builder", r"mev.?boost",
            r"order.?flow", r"block.?auction", r"timing.?game",
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
            # Broader DA patterns
            r"fulldas", r"full.?das", r"peerdas", r"peer.?das",
            r"big.?block", r"block.?size", r"blob.?count", r"target.?blob",
            r"blob.?market", r"data.?column",
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
            # Broader L2 patterns
            r"layer.?2", r"optimistic", r"based.?rollup", r"native.?rollup",
            r"sequenc", r"bridge", r"cross.?chain",
        ],
        "tag_patterns": [r"plasma", r"rollup", r"layer-2"],
        "category_hints": [],
        "key_authors": ["vbuterin", "JustinDrake", "karl"],
    },
    "pos_casper": {
        "name": "Consensus & Finality",
        "title_patterns": [
            r"casper", r"proof.?of.?stake", r"\bpos\b", r"beacon.?chain",
            r"finality", r"fork.?choice", r"lmd.?ghost", r"ffg",
            r"cbc", r"slashing", r"attestat",
            # SSF patterns (merged from ssf thread)
            r"single.?slot.?final", r"\bssf\b", r"orbit.?ssf",
            r"3sf", r"slot.?final",
            # Broader consensus patterns
            r"finality.?gadget", r"committee", r"validator.?set",
            r"rainbow.?staking", r"liquid.?staking",
        ],
        "tag_patterns": [r"casper", r"pos", r"beacon", r"ssf"],
        "category_hints": [],
        "key_authors": ["vbuterin", "JustinDrake", "djrtwo", "fradamt"],
    },
    "issuance_economics": {
        "name": "Issuance & Staking Economics",
        "title_patterns": [
            r"issuance", r"staking.?econom", r"endgame.?stak", r"yield",
            r"minimum.?viable.?issuance", r"reward.?curve", r"staking.?ratio",
            r"max.?eb\b", r"max_effective_balance", r"validator.?economics",
            r"consolidat",
            # Broader economics patterns
            r"staking.?reward", r"issuance.?curve",
            r"endgame.*stak", r"minimum.?viable.?issuance",
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
            # Broader censorship resistance patterns
            r"censorship", r"inclusion.?list", r"il.?design",
            r"focil", r"unconditional",
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
            # Broader preconf patterns
            r"based.?sequenc", r"preconf", r"pre.?conf",
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
            # Broader ZK patterns
            r"zero.?knowledge", r"recursive", r"folding",
            r"plonk", r"halo", r"groth16", r"kzg",
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
            # Broader fee market patterns
            r"gas.?price", r"gas.?cost", r"gas.?limit",
            r"resource.?pric", r"blob.?fee", r"base.?fee",
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
            # Broader privacy patterns
            r"stealth.?address", r"zk.?passport", r"anonymous",
            r"rln", r"semaphore",
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
            # Broader state/execution patterns
            r"verkle", r"state.?expir", r"state.?rent",
            r"access.?list", r"stateless", r"witness",
            r"trie", r"state.?growth",
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

# Coauthor detection helpers
COAUTHOR_ALIASES = {
    # normalized name -> username
    "vitalik": "vbuterin",
    "vitalik buterin": "vbuterin",
    "francesco": "fradamt",
    "francesco d amato": "fradamt",
    "thomas thiery": "soispoke",
    "thomas": "soispoke",
    "barry whitehat": "barryWhiteHat",
    "caspar": "casparschwa",
    "mike": "mikeneuder",
    "joachim neu": "jneu",
    "david tse": "David Tse",  # Stanford professor — no Discourse account
}

# Names that should never be treated as coauthors (blacklist)
_COAUTHOR_BLACKLIST = {
    "myself", "me", "team", "the quilt team", "the storagebeat team",
    "from the codex team", "from titania research", "chorus one",
    "option i mean", "mastodon", "ethereum",
    # Orgs / projects (not people)
    "anoma", "fairblock", "ethgas", "zeropool", "sigma prime", "kiln",
    "decipherglobal", "nobitex labs",
    # Stray fragments
    "inspiration", "bm",
}

_COAUTHOR_CUT_RE = re.compile(
    r"\b(?:thanks|special thanks|feedback|based on|discussion|discussions|tl;?dr|abstract|introduction|update)\b",
    re.IGNORECASE,
)

_COAUTHOR_PATTERNS = [
    re.compile(r"\bco-?authored?\s+by\s+(.+)", re.IGNORECASE),
    re.compile(r"\bco-?authored?\s+with\s+(.+)", re.IGNORECASE),
    re.compile(r"\bpost\s+co-?authored\s+with\s+(.+)", re.IGNORECASE),
    re.compile(r"\bauthors?:\s*(.+)", re.IGNORECASE),
    re.compile(r"\bpost\s+by\s+(.+)", re.IGNORECASE),
    re.compile(r"\bby\s+(.+)", re.IGNORECASE),
]

_COAUTHOR_SPLIT_RE = re.compile(r"\s*(?:,|&|/|\+|\band\b)\s*", re.IGNORECASE)

# Boilerplate prefixes to strip from post excerpts
_BOILERPLATE_RE = re.compile(
    r"^(?:introduction|abstract|summary|tl;?dr|background|motivation|overview|edit:|update:)\s*",
    re.IGNORECASE,
)

# Sentence boundary: period followed by whitespace and a capital letter
_SENTENCE_END_RE = re.compile(r"\.\s+(?=[A-Z])")


def _clean_excerpt(cooked_html):
    """Extract a clean 2-3 sentence excerpt from a Discourse post's cooked HTML.

    Steps:
      1. Strip all HTML tags
      2. Remove common boilerplate prefix words (Introduction, Abstract, etc.)
      3. Collapse whitespace
      4. Take the first 2-3 complete sentences (up to ~300 chars)
      5. Truncate at a word boundary if still too long
    """
    if not cooked_html:
        return ""

    # 1. Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", cooked_html)

    # 3. Collapse whitespace (do this before prefix removal so we work on clean text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    # 2. Remove boilerplate prefixes (may appear at the very start)
    text = _BOILERPLATE_RE.sub("", text).strip()

    # 4. Extract first 3-5 complete sentences up to ~600 chars
    # Find sentence boundaries
    boundaries = [m.end() - 1 for m in _SENTENCE_END_RE.finditer(text)]
    # Each boundary points to the position right after the period

    excerpt = ""
    for i, boundary in enumerate(boundaries):
        # boundary is at the space after the period; the sentence ends at the period
        # We want to include up to and including the period
        candidate = text[: boundary + 1].strip()
        if len(candidate) > 600:
            # If the very first sentence is already > 600 chars, truncate it
            if i == 0:
                excerpt = candidate
                break
            # Otherwise, stop at the previous sentence boundary
            break
        excerpt = candidate
        if i >= 4:  # collected 5 sentences (indices 0, 1, 2, 3, 4)
            break

    # If no sentence boundaries found, use the whole text
    if not excerpt:
        excerpt = text

    # 5. Truncate at a word boundary at ~550 chars and add "..."
    if len(excerpt) > 600:
        # Find the last space at or before position 550
        cut = excerpt.rfind(" ", 0, 550)
        if cut == -1:
            cut = 550
        excerpt = excerpt[:cut].rstrip(".,;:!? ") + "..."

    return excerpt


def _extract_intro_lines(cooked_html, max_lines=4, max_chars=400):
    """Extract the first few human-readable lines from cooked HTML."""
    if not cooked_html:
        return []

    text = cooked_html
    # Preserve line breaks for common block elements
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h\d|li|blockquote|pre|ul|ol)>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\r", "")

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]

    out = []
    total = 0
    for ln in lines:
        if out and total + len(ln) > max_chars:
            break
        out.append(ln)
        total += len(ln)
        if len(out) >= max_lines:
            break
    return out


def _normalize_alias(name):
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _is_headerish_line(line, idx):
    if idx > 2 or len(line) > 200:
        return False
    low = line.lower()
    if low.startswith(("by ", "authors:", "author:", "co-authored", "coauthored", "post by", "post co-authored")):
        return True
    if any(sep in line for sep in ["·", "|", "—", "–"]):
        return True
    return False


def _trim_author_phrase(text):
    for sep in ["·", "|", "—", "–"]:
        if sep in text:
            text = text.split(sep, 1)[0]
    m = _COAUTHOR_CUT_RE.search(text)
    if m:
        text = text[: m.start()]
    if "." in text:
        text = text.split(".", 1)[0]
    return text.strip()


_JUNK_NAME_RE = re.compile(
    r"^(?:\d{4}|et al\)?|on behalf of .+|in collaboration with .+|"
    r"from .+|both .+|all .+|significant input by|"
    r"co-?founder|zk researcher at .+|core dev of .+|"
    r"a .+ team member|members of .+|whose .+|inspiration from .+|"
    r"now|here|found here.*|"
    # Sentence fragments starting with common non-name words
    r"other .+|the \w+|a \w.*|an \w+|on \w+ \d.*|have \w.*|"
    # Org / role suffixes that leaked through
    r".+ labs?$|.+ research$|.+ protocol$)$",
    re.IGNORECASE,
)

# Trailing date or Discourse link-count patterns to strip
_TRAILING_DATE_RE = re.compile(
    r"\s*[-–—]\s*(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\s*$",
    re.IGNORECASE,
)
_TRAILING_NUM_RE = re.compile(r"\s+\d{1,2}\s*$")
_TRAILING_YEAR_RE = re.compile(r"\s*[-–—;,]\s*(?:may|june|july)?\s*\d{4}\s*$", re.IGNORECASE)


def _is_valid_name(name):
    """Reject names that are obviously not people."""
    if not name or len(name) <= 1:
        return False
    low = name.lower().strip()
    if low in _COAUTHOR_BLACKLIST:
        return False
    # Pure numbers (years, etc.)
    if re.fullmatch(r"\d+", name):
        return False
    # Too many words = sentence fragment
    if len(name.split()) > 5:
        return False
    if _JUNK_NAME_RE.match(name):
        return False
    return True


def _clean_name(name):
    """Strip trailing dates, Discourse link counts, org suffixes, and junk."""
    name = _TRAILING_DATE_RE.sub("", name)
    name = _TRAILING_YEAR_RE.sub("", name)
    name = _TRAILING_NUM_RE.sub("", name)
    # Strip trailing " in" or " in YYYY" (e.g. "Julian in", "Vitalik Buterin in 2021")
    name = re.sub(r"\s+in\s*(?:\d{4})?\s*$", "", name, flags=re.IGNORECASE)
    # Strip trailing "; month" without year (e.g. "justin drake ; may")
    name = re.sub(r"\s*;\s*\w+\s*$", "", name)
    # Strip " - OrgName" suffix (e.g. "Alex Watts  - FastLane Labs")
    name = re.sub(r"\s+-\s+.+$", "", name)
    # Strip " from OrgName" suffix (e.g. "Lichu from Semiotic Labs")
    name = re.sub(r"\s+from\s+.+$", "", name, flags=re.IGNORECASE)
    # Strip " et al" suffix
    name = re.sub(r"\s+et\s+al\.?\s*$", "", name, flags=re.IGNORECASE)
    # Strip title prefixes (Professor, Dr., Prof.)
    name = re.sub(r"^(?:Professor|Prof\.?|Dr\.?)\s+", "", name, flags=re.IGNORECASE)
    # Strip quoted nicknames (e.g. Brandon \u201cCryptskii\u201d Ramsay → Brandon Ramsay)
    name = re.sub(r'\s*[\u201c\u201d""][^\u201c\u201d""]*[\u201c\u201d""]\s*', " ", name)
    # Strip trailing unclosed parenthesis (e.g. "Nobitex Labs (")
    name = re.sub(r"\s*\([^)]*$", "", name)
    # Strip "@ " prefix (e.g. "@ d1ll0n" → "d1ll0n")
    name = re.sub(r"^@\s+", "", name)
    return name.strip()


def _split_author_phrase(text):
    text = _trim_author_phrase(text)
    if not text:
        return []
    parts = _COAUTHOR_SPLIT_RE.split(text)
    names = []
    for part in parts:
        if not part:
            continue
        # Extract @handles (still validate against blacklist)
        handles = re.findall(r"@([A-Za-z0-9_\-]+)", part)
        for h in handles:
            if h and _is_valid_name(h):
                names.append(h)
        part = re.sub(r"@([A-Za-z0-9_\-]+)", "", part)
        part = re.sub(r"\([^)]*\)", "", part).strip()
        part = re.sub(r"^(by|with)\s+", "", part, flags=re.IGNORECASE).strip()
        if not part:
            continue
        if _COAUTHOR_CUT_RE.search(part):
            continue
        part = _clean_name(part)
        if _is_valid_name(part):
            names.append(part)
    return [n for n in names if n]


_REF_HEADER_RE = re.compile(
    r"(?i)^(?:related\s+(?:work|research|posts?|reading)|references?|"
    r"previous\s+(?:work|research)|prior\s+(?:work|art)|see\s+also)\s*:?\s*$"
)

# Citation pattern: "Title, by Author – Date" (a reference, not a byline)
_CITATION_RE = re.compile(
    r".{10,},\s*by\s+\w+.*[-–—]\s*"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4}",
    re.IGNORECASE,
)


def extract_coauthor_names(lines):
    """Extract coauthor name strings from intro lines."""
    names = []
    seen = set()
    for idx, line in enumerate(lines):
        low = line.lower()
        # Stop scanning at reference/related-work headers
        if _REF_HEADER_RE.match(line):
            break
        # Skip citation-style lines ("Title, by Author – Date")
        if _CITATION_RE.search(line):
            continue
        if "thanks to" in low or "special thanks" in low:
            continue
        for pat in _COAUTHOR_PATTERNS:
            if pat.pattern.startswith("\\bby") and not _is_headerish_line(line, idx):
                continue
            m = pat.search(line)
            if not m:
                continue
            for name in _split_author_phrase(m.group(1)):
                key = name.lower()
                if key not in seen:
                    names.append(name)
                    seen.add(key)
    return names


def build_name_index(username_to_names, usernames):
    alias_to_users = defaultdict(set)
    first_to_users = defaultdict(set)
    last_to_users = defaultdict(set)

    for username in usernames:
        alias_to_users[_normalize_alias(username)].add(username)

    for username, names in username_to_names.items():
        for name in names:
            norm = _normalize_alias(name)
            if not norm:
                continue
            alias_to_users[norm].add(username)
            parts = norm.split()
            if parts:
                first_to_users[parts[0]].add(username)
                last_to_users[parts[-1]].add(username)

    return alias_to_users, first_to_users, last_to_users


def resolve_coauthor_name(name, alias_to_users, first_to_users, last_to_users, username_lookup):
    if not name:
        return None
    norm = _normalize_alias(name)
    if not norm:
        return None
    if norm in COAUTHOR_ALIASES:
        return COAUTHOR_ALIASES[norm]
    if norm in username_lookup:
        return username_lookup[norm]
    users = alias_to_users.get(norm)
    if users and len(users) == 1:
        return next(iter(users))
    parts = norm.split()
    if parts:
        users = first_to_users.get(parts[0])
        if users and len(users) == 1:
            return next(iter(users))
        users = last_to_users.get(parts[-1])
        if users and len(users) == 1:
            return next(iter(users))
    return None


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
    # Load EIP metadata catalog (from extract_eips.py output)
    # -----------------------------------------------------------------------
    eip_catalog = {}
    if EIP_METADATA_PATH.exists():
        print("Loading EIP metadata...")
        with open(EIP_METADATA_PATH) as f:
            eip_catalog = json.load(f)
        print(f"  {len(eip_catalog)} EIPs loaded")
    else:
        print(f"  Warning: {EIP_METADATA_PATH} not found — run extract_eips.py first")
        print("  Continuing without EIP catalog")

    # Build reverse lookups from EIP catalog
    # magicians_topic_id → list of EIP numbers that point to it
    magicians_to_eips = defaultdict(list)
    # ethresearch_topic_id → list of EIP numbers that point to it
    ethresearch_to_eips = defaultdict(list)
    for eip_str, eip_meta in eip_catalog.items():
        mtid = eip_meta.get("magicians_topic_id")
        if mtid:
            magicians_to_eips[mtid].append(int(eip_str))
        etid = eip_meta.get("ethresearch_topic_id")
        if etid:
            ethresearch_to_eips[etid].append(int(eip_str))

    # -----------------------------------------------------------------------
    # Load magicians topics (for cross-forum reverse links)
    # -----------------------------------------------------------------------
    magicians_ethresearch_refs = defaultdict(set)  # magicians_topic_id → set of ethresear.ch topic_ids
    if MAGICIANS_TOPICS_DIR.exists():
        magicians_files = list(MAGICIANS_TOPICS_DIR.glob("*.json"))
        if magicians_files:
            print(f"Scanning {len(magicians_files)} magicians topics for ethresear.ch links...")
            ethresearch_url_re = re.compile(r"https?://ethresear\.ch/t/[^/]+/(\d+)")
            scanned = 0
            for mf in magicians_files:
                try:
                    with open(mf) as f:
                        mdata = json.load(f)
                    mtid = mdata.get("id")
                    for post in mdata.get("post_stream", {}).get("posts", []):
                        cooked = post.get("cooked", "")
                        for m in ethresearch_url_re.finditer(cooked):
                            magicians_ethresearch_refs[mtid].add(int(m.group(1)))
                    scanned += 1
                except (json.JSONDecodeError, IOError):
                    continue
            total_refs = sum(len(v) for v in magicians_ethresearch_refs.values())
            print(f"  Scanned {scanned} magicians topics, found {total_refs} ethresear.ch references")

    # Load magicians index for EIP engagement metrics
    magicians_index = {}
    if MAGICIANS_INDEX_PATH.exists():
        with open(MAGICIANS_INDEX_PATH) as f:
            magicians_index = json.load(f)

    # -----------------------------------------------------------------------
    # Enrich EIP catalog with magicians engagement metrics
    # -----------------------------------------------------------------------
    print("Enriching EIP catalog with magicians engagement...")
    eip_magicians_enriched = 0
    for eip_str, eip_meta in eip_catalog.items():
        mtid = eip_meta.get("magicians_topic_id")
        if not mtid:
            continue
        mtid_str = str(mtid)
        # Get basic metrics from magicians index
        midx = magicians_index.get(mtid_str, {})
        eip_meta["magicians_views"] = midx.get("views", 0)
        eip_meta["magicians_likes"] = midx.get("like_count", 0)
        eip_meta["magicians_posts"] = midx.get("posts_count", 0)

        # Load full topic file for richer metrics
        mtopic_path = MAGICIANS_TOPICS_DIR / f"{mtid}.json"
        if mtopic_path.exists():
            try:
                with open(mtopic_path) as f:
                    mdata = json.load(f)
                parts = mdata.get("details", {}).get("participants", [])
                eip_meta["magicians_participants"] = len(parts)
                # Sum of post scores and incoming links
                score_sum = 0
                link_sum = 0
                for post in mdata.get("post_stream", {}).get("posts", []):
                    score_sum += post.get("score", 0)
                    link_sum += post.get("incoming_link_count", 0)
                eip_meta["magicians_score_sum"] = round(score_sum, 1)
                # Top 10 participants
                eip_meta["magicians_participants_list"] = [
                    {"username": p["username"], "post_count": p["post_count"]}
                    for p in parts[:10]
                ]
                eip_magicians_enriched += 1
            except (json.JSONDecodeError, IOError):
                eip_meta["magicians_participants"] = 0
                eip_meta["magicians_score_sum"] = 0
                eip_meta["magicians_participants_list"] = []
        else:
            eip_meta["magicians_participants"] = 0
            eip_meta["magicians_score_sum"] = 0
            eip_meta["magicians_participants_list"] = []
    print(f"  Enriched {eip_magicians_enriched} EIPs with magicians topic data")

    # -----------------------------------------------------------------------
    # Pass 1: Load all topics, extract metadata and links
    # -----------------------------------------------------------------------
    print("Loading topic files (pass 1)...")
    topics = {}
    all_internal_links = {}  # topic_id -> set of target topic_ids
    all_reflection_links = {}  # topic_id -> set of source topic_ids
    username_to_names = defaultdict(set)
    all_usernames = set()
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

        if created_by.get("username"):
            all_usernames.add(created_by["username"])
            if created_by.get("name"):
                username_to_names[created_by["username"]].add(created_by["name"])

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
        intro_lines = []
        for post in posts:
            username = post.get("username")
            if username:
                all_usernames.add(username)
                if post.get("name"):
                    username_to_names[username].add(post.get("name"))
                if post.get("display_username"):
                    username_to_names[username].add(post.get("display_username"))
            cooked = post.get("cooked", "")
            post_eips = extract_eips_from_text(cooked)
            all_eip_mentions.update(post_eips)
            if post.get("post_number") == 1:
                op_eips.update(post_eips)
                for e in EIP_RE.findall(cooked):
                    op_eip_counts[int(e)] += 1
                if cooked:
                    first_post_excerpt = _clean_excerpt(cooked)
                    intro_lines = _extract_intro_lines(cooked)

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
            "intro_lines": intro_lines,
        }

    if load_errors:
        print(f"  Warning: {load_errors} topic files failed to load")
    print(f"  Loaded {len(topics)} topics")

    # -----------------------------------------------------------------------
    # Coauthor detection (from first post intro lines)
    # -----------------------------------------------------------------------
    print("Detecting coauthors...")
    username_lookup = {u.lower(): u for u in all_usernames}
    alias_to_users, first_to_users, last_to_users = build_name_index(username_to_names, all_usernames)
    coauthor_topics = 0
    unresolved_counter = Counter()
    unresolved_examples = defaultdict(list)
    resolved_counter = Counter()
    resolved_examples = defaultdict(list)
    resolved_to_user = defaultdict(Counter)

    for t in topics.values():
        names = extract_coauthor_names(t.get("intro_lines", []))
        resolved = []
        for name in names:
            username = resolve_coauthor_name(
                name,
                alias_to_users,
                first_to_users,
                last_to_users,
                username_lookup,
            )
            if username:
                resolved.append(username)
                resolved_counter[name] += 1
                resolved_to_user[name][username] += 1
                if len(resolved_examples[name]) < 5:
                    resolved_examples[name].append(t["id"])
            else:
                unresolved_counter[name] += 1
                if len(unresolved_examples[name]) < 5:
                    unresolved_examples[name].append(t["id"])
        coauthors = sorted({u for u in resolved if u and u != t["author"]})
        t["coauthors"] = coauthors
        t["authors"] = [t["author"]] + [u for u in coauthors if u != t["author"]]
        if coauthors:
            coauthor_topics += 1

    print(f"  {coauthor_topics} topics with detected coauthors")

    # Write coauthor resolution report
    resolved_list = []
    for name, count in resolved_counter.most_common():
        users = resolved_to_user.get(name, {})
        resolved_list.append({
            "name": name,
            "count": count,
            "resolved_usernames": [u for u, _c in users.most_common()],
            "topics": resolved_examples.get(name, []),
        })

    unresolved_list = []
    for name, count in unresolved_counter.most_common():
        unresolved_list.append({
            "name": name,
            "count": count,
            "topics": unresolved_examples.get(name, []),
        })

    report_payload = {
        "generated_at": datetime.now().isoformat()[:19],
        "topics_with_coauthors": coauthor_topics,
        "resolved_names": resolved_list,
        "unresolved_names": unresolved_list,
        "aliases": dict(COAUTHOR_ALIASES),
    }

    with open(COAUTHOR_REPORT_PATH, "w") as f:
        json.dump(report_payload, f, indent=2, ensure_ascii=False)

    # Write Markdown report for quick review
    def _md_table(rows, include_usernames):
        if include_usernames:
            header = "| Name | Count | Resolved Usernames | Sample Topics |\n| --- | --- | --- | --- |\n"
        else:
            header = "| Name | Count | Sample Topics |\n| --- | --- | --- |\n"
        lines = [header]
        for row in rows:
            topics_str = ", ".join(str(t) for t in row.get("topics", [])[:5])
            if include_usernames:
                users_str = ", ".join(row.get("resolved_usernames", []))
                lines.append(f"| {row['name']} | {row['count']} | {users_str} | {topics_str} |\n")
            else:
                lines.append(f"| {row['name']} | {row['count']} | {topics_str} |\n")
        return "".join(lines)

    resolved_preview = resolved_list[:50]
    unresolved_preview = unresolved_list[:50]
    with open(COAUTHOR_REPORT_MD_PATH, "w") as f:
        f.write("# Coauthor Resolution Report\n\n")
        f.write(f"Generated at: {report_payload['generated_at']}\n\n")
        f.write(f"Topics with detected coauthors: {coauthor_topics}\n\n")
        f.write(f"Resolved unique names: {len(resolved_list)}\n\n")
        f.write(f"Unresolved unique names: {len(unresolved_list)}\n\n")
        f.write("## Resolved Names (Top 50)\n\n")
        f.write(_md_table(resolved_preview, include_usernames=True))
        f.write("\n## Unresolved Names (Top 50)\n\n")
        f.write(_md_table(unresolved_preview, include_usernames=False))

    print(f"  Wrote coauthor report to {COAUTHOR_REPORT_PATH} and {COAUTHOR_REPORT_MD_PATH}")

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

    # Assign each topic to best-matching thread (all topics, not just included)
    for tid in tids:
        t = topics[tid]
        best_thread = None
        best_score = 0
        for thread_id, thread_def in THREAD_SEEDS.items():
            s = match_thread(t, thread_def)
            if s > best_score:
                best_score = s
                best_thread = thread_id
        if best_score >= 1.0:
            t["research_thread"] = best_thread
        else:
            t["research_thread"] = None

    # Thread stats
    thread_counts = Counter(topics[t]["research_thread"] for t in included if topics[t].get("research_thread"))
    unassigned = sum(1 for t in included if not topics[t].get("research_thread"))
    print(f"  Thread assignments: {dict(thread_counts)}")
    print(f"  Unassigned: {unassigned}")

    # -----------------------------------------------------------------------
    # Thread evolution milestones
    # -----------------------------------------------------------------------
    print("Computing thread evolution milestones...")
    thread_milestones = {}  # thread_id -> list of milestone dicts

    for thread_id in THREAD_SEEDS:
        thread_tids = [
            tid for tid in included
            if topics[tid].get("research_thread") == thread_id and topics[tid]["date"]
        ]
        if not thread_tids:
            thread_milestones[thread_id] = []
            continue

        # Sort by date
        thread_tids.sort(key=lambda t: topics[t]["date"])

        # Compute in-degree within the thread for peak_citations detection
        thread_tid_set = set(thread_tids)
        thread_in_degree = Counter()
        for tid in thread_tids:
            for tgt in all_internal_links.get(tid, set()):
                if tgt in thread_tid_set:
                    thread_in_degree[tgt] += 1

        # Find the topic with highest in-degree in the thread
        peak_citations_tid = None
        if thread_in_degree:
            peak_citations_tid = thread_in_degree.most_common(1)[0][0]

        # Find the topic with highest influence score in the thread
        peak_influence_tid = max(thread_tids, key=lambda t: topics[t]["influence_score"])

        # Earliest and latest topics
        earliest_tid = thread_tids[0]
        latest_tid = thread_tids[-1]

        # Divide time range into equal intervals and pick best topic per interval
        first_date = topics[earliest_tid]["date"]
        last_date = topics[latest_tid]["date"]

        # Convert dates to ordinal for arithmetic
        first_ord = datetime.strptime(first_date, "%Y-%m-%d").toordinal()
        last_ord = datetime.strptime(last_date, "%Y-%m-%d").toordinal()
        span = last_ord - first_ord

        # We want up to 5 milestones total. The first and last are always
        # candidates, so divide into 5 intervals and pick 1 per interval.
        num_intervals = 5
        interval_picks = {}  # interval_index -> best tid

        if span > 0:
            for tid in thread_tids:
                t_ord = datetime.strptime(topics[tid]["date"], "%Y-%m-%d").toordinal()
                bucket = min(int((t_ord - first_ord) / span * num_intervals), num_intervals - 1)
                prev = interval_picks.get(bucket)
                if prev is None or topics[tid]["influence_score"] > topics[prev]["influence_score"]:
                    interval_picks[bucket] = tid
        else:
            # All topics on the same date — just pick the highest influence
            interval_picks[0] = peak_influence_tid

        # Assemble milestone candidates with notes, deduplicating by tid
        milestone_map = {}  # tid -> note

        # Always include earliest and latest
        if earliest_tid not in milestone_map:
            milestone_map[earliest_tid] = "earliest"
        if latest_tid not in milestone_map:
            milestone_map[latest_tid] = "latest"

        # Include peak influence
        if peak_influence_tid not in milestone_map:
            milestone_map[peak_influence_tid] = "peak_influence"

        # Include peak citations (highest in-degree within thread)
        if peak_citations_tid and peak_citations_tid not in milestone_map:
            milestone_map[peak_citations_tid] = "peak_citations"

        # Fill remaining slots from interval picks
        for _bucket, tid in sorted(interval_picks.items()):
            if len(milestone_map) >= 5:
                break
            if tid not in milestone_map:
                milestone_map[tid] = "interval"

        # Build sorted milestone list
        milestones = []
        for tid, note in sorted(milestone_map.items(), key=lambda kv: topics[kv[0]]["date"]):
            t = topics[tid]
            milestones.append({
                "id": tid,
                "title": t["title"],
                "date": t["date"],
                "influence": t["influence_score"],
                "note": note,
            })

        thread_milestones[thread_id] = milestones

    milestone_total = sum(len(m) for m in thread_milestones.values())
    print(f"  {milestone_total} milestones across {len(thread_milestones)} threads")

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
    for tid in tids:
        t = topics[tid]
        t["era"] = era_for_date(t["date"]) if t["date"] else "endgame"

    era_counts = Counter(topics[t]["era"] for t in included)
    print(f"  Era distribution: {dict(era_counts)}")

    # -----------------------------------------------------------------------
    # Author → all topic IDs (full corpus, for minor topics feature)
    # -----------------------------------------------------------------------
    print("Building author → all topic IDs index...")
    author_all_topic_ids = defaultdict(set)
    for tid in tids:
        t = topics[tid]
        for author_username in t.get("authors", [t["author"]]):
            author_all_topic_ids[author_username].add(tid)

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
        for author_username in t.get("authors", [t["author"]]):
            a = author_data[author_username]
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
            "all_topic_ids": sorted(author_all_topic_ids.get(username, set())),
        }

    print(f"  {len(authors_output)} author profiles")

    # -----------------------------------------------------------------------
    # Research thread summaries
    # -----------------------------------------------------------------------
    print("Building research thread summaries...")

    # Build the full quarter range for sparklines: 2017-Q3 through 2026-Q1
    all_quarters = []
    for year in range(2017, 2027):
        for q in range(1, 5):
            label = f"{year}-Q{q}"
            all_quarters.append(label)
    # Trim to 2017-Q3 through 2026-Q1
    start_idx = all_quarters.index("2017-Q3")
    end_idx = all_quarters.index("2026-Q1")
    all_quarters = all_quarters[start_idx:end_idx + 1]

    def date_to_quarter(date_str):
        """Convert 'YYYY-MM-DD' to 'YYYY-QN'."""
        if not date_str or len(date_str) < 7:
            return None
        year = date_str[:4]
        month = int(date_str[5:7])
        q = (month - 1) // 3 + 1
        return f"{year}-Q{q}"

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
            for auth in topics[tid].get("authors", [topics[tid]["author"]]):
                thread_authors[auth] += 1
            for p in topics[tid]["participants"]:
                thread_authors[p["username"]] += 0.5

        # EIPs mentioned across the thread (for reference, not "shipped" claims)
        thread_eips = set()
        for tid in thread_topics:
            thread_eips.update(topics[tid]["primary_eips"])

        # Sort topics by influence
        thread_topics_sorted = sorted(thread_topics, key=lambda t: topics[t]["influence_score"], reverse=True)

        # Quarterly counts for sparkline
        quarter_counter = Counter()
        for tid in thread_topics:
            q = date_to_quarter(topics[tid]["date"])
            if q:
                quarter_counter[q] += 1
        quarterly_counts = [{"q": q, "c": quarter_counter.get(q, 0)} for q in all_quarters]

        # --- Thread summary statistics ---

        # peak_year: year with the most topics in this thread
        year_counter = Counter()
        for tid in thread_topics:
            d = topics[tid]["date"]
            if d:
                year_counter[int(d[:4])] += 1
        peak_year = year_counter.most_common(1)[0][0] if year_counter else None

        # active_years: years with >= 3 topics
        active_years = sorted(y for y, c in year_counter.items() if c >= 3)

        # top_eips: top 5 most-mentioned EIPs across thread's topics (by count)
        thread_eip_counter = Counter()
        for tid in thread_topics:
            for eip in topics[tid]["eip_mentions"]:
                thread_eip_counter[eip] += 1
        top_eips = [eip for eip, _count in thread_eip_counter.most_common(5)]

        # author_diversity: distinct authors / total topics (0-1)
        distinct_authors = len({topics[tid]["author"] for tid in thread_topics})
        author_diversity = round(distinct_authors / len(thread_topics), 4) if thread_topics else 0

        threads_output[thread_id] = {
            "id": thread_id,
            "name": thread_def["name"],
            "topic_count": len(thread_topics),
            "topic_ids": thread_topics_sorted,
            "date_range": [dates[0] if dates else None, dates[-1] if dates else None],
            "key_authors": dict(Counter({a: int(c) for a, c in thread_authors.most_common(10)}).most_common(10)),
            "eip_mentions": sorted(thread_eips),
            "top_topics": thread_topics_sorted[:15],
            "quarterly_counts": quarterly_counts,
            "milestones": thread_milestones.get(thread_id, []),
            "peak_year": peak_year,
            "active_years": active_years,
            "top_eips": top_eips,
            "author_diversity": author_diversity,
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
        authors = topics[tid].get("authors", [topics[tid]["author"]])
        if len(authors) < 2:
            continue
        for a, b in combinations(sorted(set(authors)), 2):
            coauthor_edges[(a, b)] += 1

    coauthor_author_set = set()
    for (a, b), weight in coauthor_edges.items():
        if weight >= 1:
            coauthor_author_set.add(a)
            coauthor_author_set.add(b)

    coauthor_nodes = []
    for username in sorted(coauthor_author_set):
        data = author_data.get(username)
        topics_created = data["topics_created"] if data else 0
        influence = author_scores.get(username, 0.0)
        coauthor_nodes.append({
            "id": username,
            "topics": topics_created,
            "influence": round(influence, 1),
        })

    coauthor_edge_list = []
    for (a, b), weight in coauthor_edges.items():
        if weight >= 1:
            coauthor_edge_list.append({"source": a, "target": b, "weight": weight})

    print(f"  {len(coauthor_nodes)} author nodes, {len(coauthor_edge_list)} edges")

    # -----------------------------------------------------------------------
    # Cross-forum references (ethresear.ch ↔ EIP ↔ magicians)
    # -----------------------------------------------------------------------
    print("Building cross-forum references...")
    # For each topic, find magicians topic IDs linked via shared EIPs
    topic_magicians_refs = {}  # ethresearch topic_id → set of magicians topic_ids
    for tid in tids:
        t = topics[tid]
        mrefs = set()
        for eip_num in t.get("eip_mentions", []):
            eip_str = str(eip_num)
            eip_meta = eip_catalog.get(eip_str)
            if eip_meta and eip_meta.get("magicians_topic_id"):
                mrefs.add(eip_meta["magicians_topic_id"])
        # Also add reverse refs: magicians topics that link to this ethresear.ch topic
        for mtid, er_tids in magicians_ethresearch_refs.items():
            if tid in er_tids:
                mrefs.add(mtid)
        # Also check if this topic is directly referenced by an EIP's discussions-to
        if tid in ethresearch_to_eips:
            for eip_num in ethresearch_to_eips[tid]:
                eip_meta = eip_catalog.get(str(eip_num))
                if eip_meta and eip_meta.get("magicians_topic_id"):
                    mrefs.add(eip_meta["magicians_topic_id"])
        topic_magicians_refs[tid] = sorted(mrefs)

    total_with_mrefs = sum(1 for v in topic_magicians_refs.values() if v)
    print(f"  {total_with_mrefs} topics with magicians cross-references")

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
            "coauthors": t.get("coauthors", []),
            "authors": t.get("authors", [t["author"]]),
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
            "first_post_excerpt": t.get("first_post_excerpt", "")[:600],
            "participants": t["participants"][:5],
            "magicians_refs": topic_magicians_refs.get(tid, []),
            "outgoing_refs": sorted(all_internal_links.get(tid, set()) & included),
            "incoming_refs": [e["source"] for e in graph_edges if e["target"] == tid],
        }

    # -----------------------------------------------------------------------
    # Minor topics (below threshold, for author detail view)
    # -----------------------------------------------------------------------
    print("Building minor topics...")
    minor_topics_output = {}
    for tid in tids:
        if tid in included:
            continue
        t = topics[tid]
        minor_topics_output[str(tid)] = {
            "id": tid,
            "title": t["title"],
            "author": t["author"],
            "coauthors": t.get("coauthors", []),
            "authors": t.get("authors", [t["author"]]),
            "date": t["date"],
            "category_name": t["category_name"],
            "views": t["views"],
            "like_count": t["like_count"],
            "posts_count": t["posts_count"],
            "influence_score": t["influence_score"],
            "research_thread": t.get("research_thread"),
            "era": t.get("era"),
            "first_post_excerpt": t.get("first_post_excerpt", "")[:600],
            "tags": t.get("tags", [])[:5],
            "eip_mentions": t.get("eip_mentions", []),
            "primary_eips": t.get("primary_eips", []),
            "in_degree": t.get("in_degree", 0),
            "out_degree": t.get("out_degree", 0),
            "magicians_refs": topic_magicians_refs.get(tid, []),
        }
    print(f"  {len(minor_topics_output)} minor topics")

    # -----------------------------------------------------------------------
    # EIP influence scoring
    # -----------------------------------------------------------------------
    print("Computing EIP influence scores...")

    # Status weights
    EIP_STATUS_WEIGHT = {
        "Final": 1.0, "Living": 0.9, "Last Call": 0.7, "Review": 0.6,
        "Draft": 0.4, "Stagnant": 0.2, "Withdrawn": 0.05, "Moved": 0.05,
    }

    # Pre-compute ethresearch citation count: how many topics mention each EIP
    eip_ethresearch_citations = Counter()
    for tid in tids:
        for eip_num in topics[tid].get("eip_mentions", []):
            eip_ethresearch_citations[eip_num] += 1

    # Shipped forks set
    shipped_forks = {f["name"] for f in FORKS_MANUAL if f["date"]}

    # Collect raw component values for normalization
    eip_nums = sorted(eip_catalog.keys(), key=lambda x: int(x))
    raw_magicians = []
    raw_citations = []
    for eip_str in eip_nums:
        em = eip_catalog[eip_str]
        likes = em.get("magicians_likes", 0)
        views = em.get("magicians_views", 0)
        posts = em.get("magicians_posts", 0)
        raw_magicians.append(likes + math.log1p(views) + math.sqrt(posts))
        raw_citations.append(eip_ethresearch_citations.get(int(eip_str), 0))

    norm_mag = normalize(raw_magicians)
    norm_cit = normalize(raw_citations)

    above_010 = 0
    above_015 = 0
    for i, eip_str in enumerate(eip_nums):
        em = eip_catalog[eip_str]
        status = em.get("status", "")
        status_w = EIP_STATUS_WEIGHT.get(status, 0.1)
        fork = em.get("fork")
        fork_bonus = 0.3 if fork and fork in shipped_forks else 0.0
        requires = em.get("requires", [])
        requires_depth = min(len(requires) * 0.05, 0.3)

        score = (
            0.25 * status_w
            + 0.30 * norm_mag[i]
            + 0.20 * norm_cit[i]
            + 0.15 * fork_bonus
            + 0.10 * requires_depth
        )
        em["influence_score"] = round(score, 4)
        em["ethresearch_citation_count"] = eip_ethresearch_citations.get(int(eip_str), 0)

        if score >= 0.10:
            above_010 += 1
        if score >= 0.15:
            above_015 += 1

    print(f"  {above_010} EIPs above 0.10, {above_015} above 0.15")

    # -----------------------------------------------------------------------
    # Assign EIP research threads
    # -----------------------------------------------------------------------
    print("Assigning EIP research threads...")
    eip_thread_assigned = 0
    for eip_str, em in eip_catalog.items():
        title = em.get("title", "")
        if not title:
            em["research_thread"] = None
            continue
        best_thread = None
        best_score = 0
        title_lower = title.lower()
        for thread_id, thread_def in THREAD_SEEDS.items():
            s = 0
            for pat in thread_def["title_patterns"]:
                if re.search(pat, title_lower):
                    s += 2
                    break
            # Boost from related ethresearch topics' thread assignments
            eip_num = int(eip_str)
            related_tids = eipToTopics_set = set()
            for tid in tids:
                if eip_num in topics[tid].get("eip_mentions", []):
                    related_tids.add(tid)
            thread_count = sum(1 for t in related_tids if topics[t].get("research_thread") == thread_id)
            if thread_count >= 2:
                s += 1
            if s > best_score:
                best_score = s
                best_thread = thread_id
        em["research_thread"] = best_thread if best_score >= 1.0 else None
        if em["research_thread"]:
            eip_thread_assigned += 1
    print(f"  {eip_thread_assigned} EIPs assigned to research threads")

    # -----------------------------------------------------------------------
    # Build EIP graph nodes and edges
    # -----------------------------------------------------------------------
    print("Building EIP graph...")
    eip_graph_nodes = []
    eip_graph_edges = []

    # Nodes: EIPs with influence >= 0.05
    eip_node_set = set()
    for eip_str, em in eip_catalog.items():
        if em.get("influence_score", 0) >= 0.05:
            eip_node_set.add(eip_str)
            eip_graph_nodes.append({
                "id": "eip_" + eip_str,
                "eip_num": int(eip_str),
                "title": em.get("title", ""),
                "date": em.get("created"),
                "influence": em.get("influence_score", 0),
                "status": em.get("status"),
                "thread": em.get("research_thread"),
                "fork": em.get("fork"),
                "is_eip": True,
            })

    # Edges: eip_topic (EIP → top 5 most-influential ethresearch topics mentioning it)
    for eip_str in eip_node_set:
        eip_num = int(eip_str)
        related = []
        for tid in tids:
            t = topics[tid]
            if eip_num in t.get("eip_mentions", []) and tid in included:
                related.append((tid, t["influence_score"]))
        related.sort(key=lambda x: -x[1])
        for tid, _ in related[:5]:
            eip_graph_edges.append({
                "source": "eip_" + eip_str,
                "target": tid,
                "type": "eip_topic",
            })

    # Edges: eip_requires (EIP → required EIPs)
    for eip_str in eip_node_set:
        em = eip_catalog[eip_str]
        for req in em.get("requires", []):
            req_str = str(req)
            if req_str in eip_node_set:
                eip_graph_edges.append({
                    "source": "eip_" + eip_str,
                    "target": "eip_" + req_str,
                    "type": "eip_requires",
                })

    # Edges: eip_fork (EIP → fork name)
    for eip_str in eip_node_set:
        em = eip_catalog[eip_str]
        if em.get("fork"):
            eip_graph_edges.append({
                "source": "eip_" + eip_str,
                "target": "fork_" + em["fork"],
                "type": "eip_fork",
            })

    print(f"  {len(eip_graph_nodes)} EIP nodes, {len(eip_graph_edges)} EIP edges")

    # -----------------------------------------------------------------------
    # Build EIP author profiles
    # -----------------------------------------------------------------------
    print("Building EIP author profiles...")
    eip_author_data = defaultdict(lambda: {
        "eips_authored": [], "eips_coauthored": [],
        "statuses": Counter(), "forks_contributed": set(),
        "influence_sum": 0.0, "active_years": set(),
    })

    for eip_str, em in eip_catalog.items():
        eip_authors_list = em.get("authors", [])
        if not eip_authors_list:
            continue
        inf = em.get("influence_score", 0)
        status = em.get("status", "")
        fork = em.get("fork")
        created = em.get("created", "")
        year = created[:4] if created and len(created) >= 4 else None

        for i, author_name in enumerate(eip_authors_list):
            ad = eip_author_data[author_name]
            if i == 0:
                ad["eips_authored"].append(int(eip_str))
            else:
                ad["eips_coauthored"].append(int(eip_str))
            ad["statuses"][status] += 1
            if fork:
                ad["forks_contributed"].add(fork)
            ad["influence_sum"] += inf
            if year:
                ad["active_years"].add(int(year))

    # Compute author influence and select top 40
    eip_author_scores = {}
    for name, ad in eip_author_data.items():
        authored = len(ad["eips_authored"])
        coauthored = len(ad["eips_coauthored"])
        forks = len(ad["forks_contributed"])
        score = ad["influence_sum"] + 2 * authored + 0.5 * coauthored + 5 * forks
        eip_author_scores[name] = score

    top_eip_authors = sorted(eip_author_scores.keys(), key=lambda n: eip_author_scores[n], reverse=True)[:40]

    eip_authors_output = {}
    for name in top_eip_authors:
        ad = eip_author_data[name]
        eip_authors_output[name] = {
            "name": name,
            "eips_authored": sorted(ad["eips_authored"]),
            "eips_coauthored": sorted(ad["eips_coauthored"]),
            "statuses": dict(ad["statuses"].most_common()),
            "forks_contributed": sorted(ad["forks_contributed"]),
            "influence_sum": round(ad["influence_sum"], 3),
            "influence_score": round(eip_author_scores[name], 3),
            "active_years": sorted(ad["active_years"]),
        }

    print(f"  {len(eip_authors_output)} EIP author profiles")

    # -----------------------------------------------------------------------
    # Assemble output
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # Build EIP catalog for output (slim version — no raw discussions_to URL)
    # -----------------------------------------------------------------------
    eip_catalog_output = {}
    for eip_str, eip_meta in eip_catalog.items():
        eip_catalog_output[eip_str] = {
            "title": eip_meta.get("title"),
            "status": eip_meta.get("status"),
            "type": eip_meta.get("type"),
            "category": eip_meta.get("category"),
            "created": eip_meta.get("created"),
            "fork": eip_meta.get("fork"),
            "authors": eip_meta.get("authors", []),
            "requires": eip_meta.get("requires", []),
            "magicians_topic_id": eip_meta.get("magicians_topic_id"),
            "ethresearch_topic_id": eip_meta.get("ethresearch_topic_id"),
            "influence_score": eip_meta.get("influence_score", 0),
            "research_thread": eip_meta.get("research_thread"),
            "magicians_views": eip_meta.get("magicians_views", 0),
            "magicians_likes": eip_meta.get("magicians_likes", 0),
            "magicians_posts": eip_meta.get("magicians_posts", 0),
            "magicians_participants": eip_meta.get("magicians_participants", 0),
            "ethresearch_citation_count": eip_meta.get("ethresearch_citation_count", 0),
        }

    print("Writing analysis.json...")
    output = {
        "metadata": {
            "total_topics": len(index),
            "included": len(included),
            "total_edges": total_edges,
            "included_edges": len(graph_edges),
            "eip_catalog_size": len(eip_catalog_output),
            "eip_nodes": len(eip_graph_nodes),
            "eip_edges": len(eip_graph_edges),
            "generated_at": datetime.now().isoformat()[:19],
        },
        "eras": ERAS,
        "forks": forks_output,
        "eip_catalog": eip_catalog_output,
        "eip_authors": eip_authors_output,
        "eip_graph": {
            "nodes": eip_graph_nodes,
            "edges": eip_graph_edges,
        },
        "topics": topics_output,
        "minor_topics": minor_topics_output,
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
