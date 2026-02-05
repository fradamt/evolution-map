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
analyze.py           # Processes scraped data → analysis.json
analysis.json        # Structured analysis output (~3.5 MB, the central artifact)
render_html.py       # analysis.json → self-contained D3.js HTML visualization
render_markdown.py   # analysis.json → ~10,000 word narrative Markdown document
evolution-map.html   # Generated: interactive timeline/network/co-author viz
evolution-map.md     # Generated: narrative document with appendices
```

Scraped data (not in this repo, lives in parent `ethresear.ch/`):
```
../scrape.py         # Discourse API scraper (stdlib-only, no dependencies)
../index.json        # Topic ID → metadata map (all 2,903 topics)
../categories.json   # Forum category definitions
../topics/           # 2,903 individual topic JSON files (topics/{id}.json)
```

## Pipeline

The three scripts form a linear pipeline. All use stdlib-only Python (no pip install needed). Run from this directory:

```bash
# Step 1: Scrape ethresear.ch (idempotent — skips already-downloaded files)
python3 ../scrape.py

# Step 2: Analyze scraped data → analysis.json
python3 analyze.py

# Step 3a: Generate interactive HTML visualization
python3 render_html.py

# Step 3b: Generate narrative Markdown document
python3 render_markdown.py
```

**Idempotency**: `scrape.py` checks for existing files before fetching. Re-running only fetches missing topics. The analysis and render scripts always regenerate their outputs.

## Key Design Decisions

**Influence scoring** (in `analyze.py`): Topics are ranked by a weighted composite — 30% citation in-degree, 25% likes, 20% log(views), 15% post count, 10% prolific author bonus. Tier 1 topics have influence ≥ 0.25 or in-degree ≥ 3; Tier 2 are referenced by Tier 1 with influence ≥ 0.10.

**Research thread assignment**: Pattern-matching on title, tags, post excerpt, and author identity against seed definitions in `THREAD_SEEDS`. All 2,903 topics are scored; those with score ≥ 1.0 get a thread, the rest stay `null` ("Unassigned"). Era is likewise assigned to all topics based on date.

**Primary vs. secondary EIPs**: Title EIPs are always primary. OP EIPs are primary only if mentioned ≥3 times (passing references don't count). All other mentions are secondary.

**No topic→fork "shipped in" mapping**: The code intentionally leaves `shipped_in` empty. Counting EIP mentions is a poor proxy for "this research led to that protocol change" — that would need semantic analysis.

## Data Shapes

**analysis.json**: `{ metadata, eras[], forks[], topics{}, minor_topics{}, authors{}, research_threads{}, graph{ nodes[], edges[] }, co_author_graph{ nodes[], edges[] } }`

**topics{}** (included, ~550): Full detail — `id, title, author, coauthors, authors, date, category_name, views, like_count, posts_count, influence_score, research_thread, era, first_post_excerpt, tags, eip_mentions, primary_eips, in_degree, out_degree, shipped_in, participants, outgoing_refs, incoming_refs`.

**minor_topics{}** (~2,353): Below influence threshold — same fields as topics except no `outgoing_refs`, `incoming_refs`, `participants`, `shipped_in`.

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

- Rate-limited: 0.3s between requests, exponential backoff on 429/5xx
- Handles post pagination (fetches missing post IDs in chunks of 20)
- SSL context manually configured for macOS Python cert issues
- Two-phase: first collects all topic IDs by paginating categories + `/latest`, then fetches full topic content
