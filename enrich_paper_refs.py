#!/usr/bin/env python3
"""Enrich papers-db.json with referenced_works from OpenAlex.

Fetches the `referenced_works` field for each paper that has an OpenAlex ID,
then writes the updated papers-db.json in place.

Usage:
    python3 enrich_paper_refs.py
    python3 enrich_paper_refs.py --dry-run   # preview without writing
"""

import argparse
import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PAPERS_DB_PATH = SCRIPT_DIR / "papers-db.json"
OPENALEX_BASE = "https://api.openalex.org"
USER_AGENT = "evolution-map-papers-builder/1.0"

# OpenAlex filter supports up to 50 IDs per pipe-separated list
BATCH_SIZE = 50


def short_openalex_id(openalex_id):
    if not openalex_id:
        return None
    value = openalex_id.strip()
    m = re.search(r"/([AW]\d+)$", value)
    if m:
        return m.group(1)
    return value


def http_get_json(path, params=None, retries=5, pause=0.15):
    params = params or {}
    query = urllib.parse.urlencode(params, doseq=True)
    url = f"{OPENALEX_BASE}{path}"
    if query:
        url = f"{url}?{query}"

    for attempt in range(retries + 1):
        try:
            proc = subprocess.run(
                [
                    "curl", "-fsSL",
                    "--connect-timeout", "10",
                    "--max-time", "30",
                    "-A", USER_AGENT,
                    url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(proc.stdout)
        except Exception as err:
            if attempt == retries:
                raise RuntimeError(f"OpenAlex request failed: {url}") from err
            time.sleep(pause * (2 ** attempt))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    print("Loading papers-db.json...")
    with open(PAPERS_DB_PATH) as f:
        payload = json.load(f)

    papers = payload.get("papers", [])
    print(f"  {len(papers)} papers loaded")

    # Collect papers with OpenAlex IDs that need referenced_works
    needs_refs = []
    for paper in papers:
        oa_id = paper.get("openalex_id")
        if not oa_id:
            continue
        short = short_openalex_id(oa_id)
        if not short:
            continue
        # Skip papers that already have referenced_works populated
        if paper.get("referenced_works"):
            continue
        needs_refs.append((short, paper))

    print(f"  {len(needs_refs)} papers need referenced_works enrichment")
    if not needs_refs:
        print("Nothing to do.")
        return

    if args.dry_run:
        print("Dry run — would fetch referenced_works for these papers.")
        return

    # Fetch in batches using OpenAlex filter
    enriched = 0
    total_refs = 0
    batches = [needs_refs[i:i + BATCH_SIZE] for i in range(0, len(needs_refs), BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches, 1):
        ids_filter = "|".join(f"https://openalex.org/{short}" for short, _ in batch)
        print(f"  Batch {batch_idx}/{len(batches)} ({len(batch)} papers)...", flush=True)

        # Build lookup for this batch
        batch_lookup = {short: paper for short, paper in batch}

        cursor = "*"
        while cursor:
            data = http_get_json(
                "/works",
                {
                    "filter": f"openalex:{ids_filter}",
                    "select": "id,referenced_works",
                    "per_page": 200,
                    "cursor": cursor,
                },
            )

            for work in data.get("results", []):
                work_id = short_openalex_id(work.get("id"))
                if work_id and work_id in batch_lookup:
                    refs = []
                    for ref_id in work.get("referenced_works") or []:
                        short_ref = short_openalex_id(ref_id)
                        if short_ref:
                            refs.append(short_ref)
                    batch_lookup[work_id]["referenced_works"] = refs
                    enriched += 1
                    total_refs += len(refs)

            # Handle pagination
            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not data.get("results"):
                break

        time.sleep(0.2)  # Rate limiting between batches

    print(f"  Enriched {enriched} papers with {total_refs} total references")

    # Write back
    print("Writing papers-db.json...")
    with open(PAPERS_DB_PATH, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=True)
        f.write("\n")
    print("Done!")


if __name__ == "__main__":
    main()
