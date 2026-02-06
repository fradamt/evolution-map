#!/usr/bin/env python3
"""Parse EIP front-matter → eip-metadata.json.

Reads all eip-*.md files from the EIPs repository and extracts structured
metadata from their YAML-like front-matter blocks. Stdlib-only (no YAML library).

Usage:
    python3 extract_eips.py [--eips-dir PATH] [--output PATH]
"""

import glob
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent

# Default paths
DEFAULT_EIPS_DIR = SCRIPT_DIR.parent.parent / "EIPs" / "EIPS"
DEFAULT_OUTPUT = SCRIPT_DIR / "eip-metadata.json"

# Fork → EIP mapping (same as FORKS_MANUAL in analyze.py)
FORKS_EIP_MAP = {
    "Byzantium": [100, 140, 196, 197, 198, 211, 214, 649, 658],
    "Constantinople": [145, 1014, 1052, 1234, 1283],
    "Istanbul": [152, 1108, 1344, 1884, 2028, 2200],
    "Berlin": [2565, 2929, 2718, 2930],
    "London": [1559, 3198, 3529, 3541, 3554],
    "The Merge": [3675, 4399],
    "Shapella": [3651, 3855, 3860, 4895, 6049],
    "Dencun": [1153, 4788, 4844, 5656, 6780, 7044, 7045, 7514, 7516],
    "Pectra": [2537, 2935, 6110, 7002, 7251, 7549, 7623, 7685, 7691, 7702],
    "Fusaka": [7594, 7823, 7825, 7883, 7917, 7918, 7934, 7939, 7951],
    "Glamsterdam": [7732, 7928],
}

EIP_TO_FORK = {}
for fork_name, eips in FORKS_EIP_MAP.items():
    for eip_num in eips:
        EIP_TO_FORK[eip_num] = fork_name

# Regex to extract topic ID from Discourse URLs
TOPIC_ID_RE = re.compile(r"/t/[^/]+/(\d+)")


def parse_front_matter(text):
    """Parse the first ---...--- block into a dict of key: value pairs.

    Handles:
    - Simple key: value lines
    - Comma-separated lists (requires field)
    - Multiline author fields with (@handle) annotations
    """
    lines = text.split("\n")

    # Find opening ---
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            start = i
            break
    if start is None:
        return {}

    # Find closing ---
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}

    result = {}
    current_key = None
    current_value = None

    for line in lines[start + 1:end]:
        # Continuation line (starts with whitespace, no colon before content)
        if line and line[0] in (" ", "\t") and current_key:
            current_value += " " + line.strip()
            result[current_key] = current_value
            continue

        # New key: value pair
        colon_pos = line.find(":")
        if colon_pos > 0:
            current_key = line[:colon_pos].strip()
            current_value = line[colon_pos + 1:].strip()
            result[current_key] = current_value
        # Lines without colon on first position are ignored

    return result


def parse_authors(author_str):
    """Parse author field into list of name strings.

    Input: 'Vitalik Buterin (@vbuterin), Dankrad Feist (@dankrad), et al.'
    Output: ['Vitalik Buterin', 'Dankrad Feist']
    """
    if not author_str:
        return []

    # Split by comma
    parts = [p.strip() for p in author_str.split(",")]
    names = []
    for part in parts:
        if not part:
            continue
        # Skip "et al." entries
        if re.match(r"^et\s+al\.?$", part.strip(), re.IGNORECASE):
            continue
        # Remove (@handle), (<email>), and <email> annotations
        name = re.sub(r"\s*\(@[^)]*\)", "", part)
        name = re.sub(r"\s*\(<[^>]*>\)", "", name)
        name = re.sub(r"\s*<[^>]*>", "", name)
        name = name.strip()
        if name:
            names.append(name)
    return names


def parse_requires(requires_str):
    """Parse comma-separated list of EIP numbers.

    Input: '1559, 2718, 2930'
    Output: [1559, 2718, 2930]
    """
    if not requires_str:
        return []
    nums = []
    for part in requires_str.split(","):
        part = part.strip()
        if part.isdigit():
            nums.append(int(part))
    return nums


def extract_topic_id(url, domain):
    """Extract Discourse topic ID from a URL."""
    if not url or domain not in url:
        return None
    m = TOPIC_ID_RE.search(url)
    if m:
        return int(m.group(1))
    return None


def parse_eip_file(filepath):
    """Parse a single EIP markdown file into metadata dict."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    fm = parse_front_matter(text)
    if not fm:
        return None

    eip_num_raw = fm.get("eip", "")
    if not eip_num_raw or not str(eip_num_raw).strip().isdigit():
        return None
    eip_num = int(eip_num_raw)

    discussions_to = fm.get("discussions-to", "").strip()
    discussions_domain = None
    if discussions_to:
        try:
            parsed = urlparse(discussions_to)
            discussions_domain = parsed.hostname
        except Exception:
            pass

    return {
        "eip": eip_num,
        "title": fm.get("title", "").strip() or None,
        "authors": parse_authors(fm.get("author", "")),
        "status": fm.get("status", "").strip() or None,
        "type": fm.get("type", "").strip() or None,
        "category": fm.get("category", "").strip() or None,
        "created": fm.get("created", "").strip() or None,
        "requires": parse_requires(fm.get("requires", "")),
        "discussions_to": discussions_to or None,
        "discussions_to_domain": discussions_domain,
        "magicians_topic_id": extract_topic_id(discussions_to, "ethereum-magicians.org"),
        "ethresearch_topic_id": extract_topic_id(discussions_to, "ethresear.ch"),
        "fork": EIP_TO_FORK.get(eip_num),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract EIP metadata from markdown files")
    parser.add_argument("--eips-dir", type=Path, default=DEFAULT_EIPS_DIR,
                        help="Directory containing eip-*.md files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Output JSON file path")
    args = parser.parse_args()

    eips_dir = args.eips_dir
    output_path = args.output

    if not eips_dir.is_dir():
        print(f"Error: EIPs directory not found: {eips_dir}", file=sys.stderr)
        sys.exit(1)

    pattern = str(eips_dir / "eip-*.md")
    files = sorted(glob.glob(pattern))
    print(f"Found {len(files)} EIP files in {eips_dir}")

    catalog = {}
    errors = 0
    magicians_count = 0
    ethresearch_count = 0
    fork_count = 0

    for filepath in files:
        meta = parse_eip_file(filepath)
        if meta is None:
            errors += 1
            continue

        eip_num = meta["eip"]
        catalog[str(eip_num)] = meta

        if meta["magicians_topic_id"]:
            magicians_count += 1
        if meta["ethresearch_topic_id"]:
            ethresearch_count += 1
        if meta["fork"]:
            fork_count += 1

    with open(output_path, "w") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"\nWrote {output_path} ({size_kb:.0f} KB)")
    print(f"  {len(catalog)} EIPs parsed ({errors} errors)")
    print(f"  {magicians_count} with magicians_topic_id")
    print(f"  {ethresearch_count} with ethresearch_topic_id")
    print(f"  {fork_count} with fork assignment")

    # Spot-check
    if "4844" in catalog:
        e = catalog["4844"]
        print(f"\n  Spot-check EIP-4844: magicians_topic_id={e['magicians_topic_id']}, "
              f"fork={e['fork']}, status={e['status']}")
    if "2474" in catalog:
        e = catalog["2474"]
        print(f"  Spot-check EIP-2474: ethresearch_topic_id={e['ethresearch_topic_id']}, "
              f"discussions_to_domain={e['discussions_to_domain']}")


if __name__ == "__main__":
    main()
