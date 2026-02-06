# CLAUDE.md — evolution-map

This is the **git repo**. When you finish a task — code changes work, local testing passes (e.g. re-generated HTML looks correct) — commit and push here. No need to ask first. Document changes in this file.

## What This Is

An analysis pipeline over a scraped archive of **ethresear.ch** (Ethereum's Discourse research forum) that produces an "Evolution Map" — a narrative and interactive visualization tracing how Ethereum research ideas became protocol.

- **~2,903 topics** scraped via the Discourse API (stdlib-only Python) — scraped data lives in the parent directory (`../topics/`, `../index.json`)
- **All 2,903 topics** in a unified dict — influence slider controls visibility (no separate "minor topics" toggle)
- **550 influential topics** with **1,007 cross-references**, **2,353 lower-influence topics** (flagged `mn: true`)
- **12 research threads** (PBS/MEV, Sharding/DA, Casper/PoS, Fee Markets, etc.) across **5 eras** (2017–2026)

## Repository Structure

```
extract_eips.py      # Parses EIP front-matter → eip-metadata.json (stdlib-only)
eip-metadata.json    # EIP catalog: number → title, status, fork, authors, links
analyze.py           # Processes scraped data + EIP catalog → analysis.json
analysis.json        # Structured analysis output (~4 MB, the central artifact)
render_html.py       # analysis.json → self-contained D3.js HTML visualization
render_markdown.py   # analysis.json → ~10,000 word narrative Markdown document
evolution-map.html   # Generated: interactive timeline/network/co-author viz
evolution-map.md     # Generated: narrative document with appendices
```

Scraped data (not in this repo, lives in parent `ethresear.ch/`):
```
../scrape.py         # Discourse API scraper (stdlib-only, parameterized via CLI)
../index.json        # Topic ID → metadata map (all 2,903 ethresear.ch topics)
../categories.json   # Forum category definitions
../topics/           # 2,903 individual topic JSON files (topics/{id}.json)
../magicians_index.json   # (optional) ethereum-magicians.org topic index
../magicians_topics/      # (optional) magicians topic JSON files
```

## Pipeline

All scripts are stdlib-only Python (no pip install needed). Run from this directory:

```bash
# Step 1a: Scrape ethresear.ch (idempotent — skips already-downloaded files)
python3 ../scrape.py

# Step 1b: (Optional) Scrape ethereum-magicians.org for cross-forum links
python3 ../scrape.py --base-url https://ethereum-magicians.org \
  --index magicians_index.json --topics-dir magicians_topics

# Step 2: Extract EIP metadata from the EIPs repo
python3 extract_eips.py

# Step 3: Analyze scraped data + EIP catalog → analysis.json
python3 analyze.py

# Step 4a: Generate interactive HTML visualization
python3 render_html.py

# Step 4b: Generate narrative Markdown document
python3 render_markdown.py
```

**Idempotency**: `scrape.py` checks for existing files before fetching. Re-running only fetches missing topics. The analysis and render scripts always regenerate their outputs.

**Cross-forum enrichment**: `analyze.py` loads `eip-metadata.json` (from `extract_eips.py`) and optionally scans `../magicians_topics/` to build cross-forum links between ethresear.ch topics, EIP specifications, and ethereum-magicians.org discussion threads.

## Key Design Decisions

**Influence scoring** (in `analyze.py`): Topics are ranked by a weighted composite — 30% citation in-degree, 25% likes, 20% log(views), 15% post count, 10% prolific author bonus. Tier 1 topics have influence ≥ 0.25 or in-degree ≥ 3; Tier 2 are referenced by Tier 1 with influence ≥ 0.10.

**Research thread assignment**: Pattern-matching on title, tags, post excerpt, and author identity against seed definitions in `THREAD_SEEDS`. All 2,903 topics are scored; those with score ≥ 1.0 get a thread, the rest stay `null` ("Unassigned"). Era is likewise assigned to all topics based on date.

**Primary vs. secondary EIPs**: Title EIPs are always primary. OP EIPs are primary only if mentioned ≥3 times (passing references don't count). All other mentions are secondary.

**No topic→fork "shipped in" mapping**: The code intentionally leaves `shipped_in` empty. Counting EIP mentions is a poor proxy for "this research led to that protocol change" — that would need semantic analysis.

## Data Shapes

**analysis.json**: `{ metadata, eras[], forks[], eip_catalog{}, topics{}, minor_topics{}, authors{}, research_threads{}, graph{ nodes[], edges[] }, co_author_graph{ nodes[], edges[] } }`

**eip_catalog{}** (~885 entries, keyed by EIP number string): `title, status, type, category, created, fork, authors[], requires[], magicians_topic_id, ethresearch_topic_id`. Top-level (not duplicated per-topic).

**topics{}** (included, ~550): Full detail — `id, title, author, coauthors, authors, date, category_name, views, like_count, posts_count, influence_score, research_thread, era, first_post_excerpt, tags, eip_mentions, primary_eips, in_degree, out_degree, shipped_in, magicians_refs, participants, outgoing_refs, incoming_refs`.

**minor_topics{}** (~2,353): Below influence threshold — same fields as topics except no `outgoing_refs`, `incoming_refs`, `participants`, `shipped_in`. Includes `magicians_refs`.

**magicians_refs** (per-topic): List of ethereum-magicians.org topic IDs related to this ethresear.ch topic via shared EIP mentions. Computed by: (1) topic mentions EIP → EIP's `discussions-to` → magicians topic ID, (2) magicians topics that link back to this ethresear.ch topic URL, (3) EIPs whose `discussions-to` points to this ethresear.ch topic.

**HTML compact format**: All 2,903 topics live in a single `DATA.topics` dict. Field names are abbreviated: `t` = title, `a` = author, `d` = date, `inf` = influence_score, `th` = research_thread, `vw` = views, `lk` = like_count, `pc` = posts_count, `ind` = in_degree, `outd` = out_degree, `eips` = eip_mentions, `peips` = primary_eips, `exc` = first_post_excerpt, `tg` = tags, `cat` = category_name, `out` = outgoing_refs, `inc` = incoming_refs, `coauth` = coauthors, `mn` = true (lower-influence topic flag — `out`/`inc` are `[]`). `DATA.minorTopics` is `{}` (kept for backward compat, always empty).

**Scraped data** (parent directory):
- `index.json`: `{ "topic_id_str": { id, title, category_id, category_name, posts_count, created_at, last_posted_at, views, like_count } }`
- `topics/{id}.json`: Full Discourse topic JSON including `post_stream.posts[]` (with `cooked` HTML, `link_counts[]`), `details.participants[]`, `tags[]`, `word_count`.

## HTML Visualization

Self-contained single HTML file using D3.js v7 from CDN. Three views:
- **Timeline**: swim-lane layout by research thread, X-axis is time, circle size = influence
- **Network**: force-directed citation graph with fork diamonds
- **Co-Author**: force-directed collaboration network

All topics live in one unified dict. The influence slider controls visibility — default threshold hides lower-influence topics so the initial view matches the original ~550. Slide to 0 to see all 2,903. Lower-influence topics are drawn with dashed circles and show a "Minor Topic" badge in the detail panel. Network view only shows topics with citation edges (no change). Search, author detail, and filtering work across the full spectrum.

## Scraper Details

- **Parameterized**: `scrape.py` accepts `--base-url`, `--index`, `--topics-dir` CLI args. Defaults match original ethresear.ch behavior.
- Rate-limited: 0.3s between requests, exponential backoff on 429/5xx
- Handles post pagination (fetches missing post IDs in chunks of 20)
- SSL context manually configured for macOS Python cert issues
- Two-phase: first collects all topic IDs by paginating categories + `/latest`, then fetches full topic content
- Works with any Discourse forum (ethereum-magicians.org, ethresear.ch, etc.)

## EIP Metadata Extractor

`extract_eips.py` parses front-matter from `~/EF/EIPs/EIPS/eip-*.md` files. Stdlib-only (no YAML library).

- Extracts: eip number, title, authors (with `@handle` stripped), status, type, category, created date, requires list, discussions-to URL
- Derives: `magicians_topic_id` and `ethresearch_topic_id` from `discussions-to` URL patterns
- Assigns fork from `FORKS_EIP_MAP` (same mapping as `FORKS_MANUAL` in analyze.py)
- ~885 EIPs, ~423 with magicians links, ~7 with ethresearch links, ~66 with fork assignments
