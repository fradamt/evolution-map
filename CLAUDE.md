# CLAUDE.md — evolution-map

This is the **git repo**. When you finish a task — code changes work, local testing passes (e.g. re-generated HTML looks correct) — commit and push here. No need to ask first. Document changes in this file.

## What This Is

An analysis pipeline over a scraped archive of **ethresear.ch** (Ethereum's Discourse research forum) that produces an "Evolution Map" — a narrative and interactive visualization tracing how Ethereum research ideas became protocol.

- **~2,903 topics** scraped via the Discourse API (stdlib-only Python) — scraped data lives in the parent directory (`../topics/`, `../index.json`)
- **All 2,903 topics** in a unified dict — influence slider controls visibility (no separate "minor topics" toggle)
- **550 influential topics** with **1,007 cross-references**, **2,353 lower-influence topics** (flagged `mn: true`)
- **12 research threads** (PBS/MEV, Sharding/DA, Casper/PoS, Fee Markets, etc.) across **5 eras** (Early Research, PoS Transition, Rollup-centric, Danksharding, Endgame)
- **18 forks** on timeline (Genesis through Osaka, including early pre-ethresearch forks)
- **Cross-forum entities**: EIP catalog + first-class `magicians_topics` + explicit `cross_forum_edges` links for topic/EIP/Magicians traversal

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

**Cross-forum enrichment**: `analyze.py` loads `eip-metadata.json` (from `extract_eips.py`) and optionally scans `../magicians_topics/` to build:
- Per-topic `magicians_refs`
- First-class `magicians_topics` entities
- Explicit `cross_forum_edges` (`topic_eip`, `eip_magicians`, `eip_ethresearch`, `topic_magicians`)

## Key Design Decisions

**Unified influence scoring** (in `analyze.py`): All entity types (topics, EIPs, papers) use percentile-based scoring with shaped_rank(power=2.0) transformation, producing a right-skewed [0, 1] distribution (mean≈0.33, median≈0.25). `percentile_rank()` uses midrank tie handling. Two-phase approach — see `INFLUENCE_REDESIGN.md` for full details.

*Phase 1 — Intrinsic scores:*
- **Topics**: 50% citation in-degree percentile + 50% engagement percentile (likes + sqrt(posts) + log1p(views)).
- **EIPs**: 20% status weight (Final=1.0, Living=0.85, Draft=0.3, Moved=0.02) + 25% magicians engagement percentile + 25% ethresearch citation percentile + 20% fork bonus (1.0 if shipped) + 10% requires depth.
- **Papers**: 40% citation percentile + 40% relevance percentile + 20% EIP anchoring. Relevance gate: papers with `relevance_score < 10` (bottom ~71%) get citation contribution dampened to 25%, preventing "blockchain for healthcare/supply chain" papers from dominating. Recency damping: current year ×0.55, -1yr ×0.70, -2yr ×0.85.

*Phase 2 — Cross-entity reinforcement (single pass):*
- Topics mentioning Final EIPs get +0.03 each (capped +0.12); topics mentioning fork-shipped EIPs get +0.04 each (capped +0.12).
- EIPs cited by high-influence topics (intrinsic ≥ 0.3) get +0.02 each (capped +0.10).

Tier 1 topics have influence ≥ 0.70 or in-degree ≥ 3; Tier 2 are referenced by Tier 1 with influence ≥ 0.30. Combined top 50: 30 Topics, 9 EIPs, 7 Papers. Paper influence is pre-computed in Python (not JavaScript); `render_html.py` has a fallback JS formula for any unscored papers but it should never trigger.

**Research thread assignment**: Pattern-matching on title, tags, post excerpt, and author identity against seed definitions in `THREAD_SEEDS`. A topic must pass both:
- Thread seed score (`>= 1.0`)
- Global protocol relevance guardrail (`is_protocol_relevant_topic`)
The guardrail combines protocol anchors, non-protocol negatives, EIP signals, and category penalties to avoid assigning non-protocol topics to protocol threads. Era is assigned to all topics based on date.

**Corpus exclusions (hard filter)**: `excluded_corpus_reason(...)` removes topics before influence scoring/thread assignment/graph build when:
- Category is excluded (default includes `Protocol Calls`)
- Title matches exclusion patterns (default includes ACD/Core Dev call/meeting/notes variants)
Exclusion counts are reported in metadata: `excluded_topics`, `excluded_by_category`, `excluded_by_title`.

**Primary vs. secondary EIPs**: Title EIPs are always primary. OP EIPs are primary only if mentioned ≥3 times (passing references don't count). All other mentions are secondary.

**EIP author name normalization** (in `analyze.py`): EIP front-matter authors use inconsistent naming (e.g. "Francesco" vs "Francesco D'Amato" vs "Francesco D\`Amato"). A 5-step pipeline canonicalizes names:
1. Punctuation fix (backticks/smart quotes → apostrophes)
2. Case-insensitive dedup (lightclient/Lightclient → lightclient)
3. Unicode diacritics dedup (Paweł/Pawel Bylica → Paweł Bylica)
4. Short→full prefix merge, case-insensitive (mike → Mike Neuder, Francesco → Francesco D'Amato)
5. Same-last-name merge with ≥2-char first-name prefix match (Mike/Michael Neuder)

All EIP authors are treated equally — no distinction between first-author and co-author. ~30 names merged across 885 EIP authors.

**No topic→fork "shipped in" mapping**: The code intentionally leaves `shipped_in` empty. Counting EIP mentions is a poor proxy for "this research led to that protocol change" — that would need semantic analysis.

## Data Shapes

**analysis.json**: `{ metadata, eras[], forks[], eip_catalog{}, magicians_topics{}, cross_forum_edges[], eip_authors{}, eip_graph{ nodes[], edges[] }, topics{}, minor_topics{}, authors{}, research_threads{}, graph{ nodes[], edges[] }, co_author_graph{ nodes[], edges[] } }`

**metadata**: Includes corpus/accounting fields and cross-forum counters:
- `total_topics`, `scraped_topics`, `excluded_topics`, `excluded_by_category`, `excluded_by_title`, `included`
- `total_edges`, `included_edges`, `eip_catalog_size`, `eip_nodes`, `eip_edges`
- `magicians_topics`, `cross_forum_edges`, `generated_at`

**eip_catalog{}** (~885 entries, keyed by EIP number string): `title, status, type, category, created, fork, authors[], requires[], magicians_topic_id, ethresearch_topic_id, influence_score, research_thread, ethresearch_citation_count, magicians_views, magicians_likes, magicians_posts, magicians_participants, magicians_score_sum, magicians_participants_list[]`. Top-level (not duplicated per-topic).

**eip_authors{}** (~40 entries, keyed by canonical name): `name, eips[], eip_count, influence_sum, statuses{}, forks_contributed[], active_years, score`. All authored EIPs in a single `eips` list (no first-author/co-author distinction).

**eip_graph{}**: `nodes[]` (~490 EIPs with influence ≥ 0.05), `edges[]` (~734 edges of 3 types: `eip_topic`, `eip_requires`, `eip_fork`).

**topics{}** (included, ~550): Full detail — `id, title, author, coauthors, authors, date, category_name, views, like_count, posts_count, influence_score, research_thread, era, first_post_excerpt, tags, eip_mentions, primary_eips, in_degree, out_degree, shipped_in, magicians_refs, participants, outgoing_refs, incoming_refs`.

**minor_topics{}** (~2,353): Below influence threshold — same fields as topics except no `outgoing_refs`, `incoming_refs`, `participants`, `shipped_in`. Includes `magicians_refs`.

**magicians_refs** (per-topic): List of ethereum-magicians.org topic IDs related to this ethresear.ch topic via shared EIP mentions. Computed by: (1) topic mentions EIP → EIP's `discussions-to` → magicians topic ID, (2) magicians topics that link back to this ethresear.ch topic URL, (3) EIPs whose `discussions-to` points to this ethresear.ch topic.

**magicians_topics{}** (keyed by magicians topic ID): `id, title, slug, date, category_name, author, views, like_count, posts_count, tags, eips, ethresearch_refs`.

**cross_forum_edges[]**: Explicit directional links across entities:
- `topic -> eip` (`type = topic_eip`)
- `eip -> magicians_topic` (`type = eip_magicians`)
- `eip -> topic` (`type = eip_ethresearch`)
- `topic -> magicians_topic` (`type = topic_magicians`)

**HTML compact format**: All 2,903 topics live in a single `DATA.topics` dict. Field names are abbreviated: `t` = title, `a` = author, `d` = date, `inf` = influence_score, `th` = research_thread, `vw` = views, `lk` = like_count, `pc` = posts_count, `ind` = in_degree, `outd` = out_degree, `eips` = eip_mentions, `peips` = primary_eips, `exc` = first_post_excerpt, `tg` = tags, `cat` = category_name, `out` = outgoing_refs, `inc` = incoming_refs, `coauth` = coauthors, `mn` = true (lower-influence topic flag — `out`/`inc` are `[]`). `DATA.minorTopics` is `{}` (kept for backward compat, always empty).

EIP-related compact data:
- `DATA.eipCatalog{}`: keyed by EIP number, adds `inf` (influence), `th` (thread), `mv`/`ml`/`mp`/`mpc` (magicians views/likes/posts/participants), `erc` (ethresearch citation count)
- `DATA.eipAuthors[]`: `n` = name, `eips` = EIP numbers list, `inf` = influence_sum, `sc` = score, `fk` = forks_contributed
- `DATA.eipGraph{}`: `nodes[]` and `edges[]` for EIP citation/dependency network

**Scraped data** (parent directory):
- `index.json`: `{ "topic_id_str": { id, title, category_id, category_name, posts_count, created_at, last_posted_at, views, like_count } }`
- `topics/{id}.json`: Full Discourse topic JSON including `post_stream.posts[]` (with `cooked` HTML, `link_counts[]`), `details.participants[]`, `tags[]`, `word_count`.

## HTML Visualization

Self-contained single HTML file using D3.js v7 from CDN. Three views:
- **Timeline**: swim-lane layout by research thread, X-axis is time, circle size = influence
- **Network**: force-directed citation graph with fork diamonds and EIP squares
- **Co-Author**: force-directed collaboration network

All topics live in one unified dict. The influence slider controls visibility — default threshold hides lower-influence topics so the initial view matches the original ~550. Slide to 0 to see all 2,903. Lower-influence topics are drawn with dashed circles and show a "Minor Topic" badge in the detail panel. Network view only shows topics with citation edges (no change). Search, author detail, and filtering work across the full spectrum.

**Content toggles**: Two independent toggle chips — `[● Posts ✓] [■ EIPs]`. Default: Posts on, EIPs off (preserves original behavior). When both are on, cross-reference edges (dashed lines) appear between EIP squares and related topic circles.

**EIP swim lane**: Dedicated 80px-tall lane at the top of the timeline (above research thread lanes). EIP nodes are rounded squares, colored by status (Final=green, Living=teal, Review=yellow, Draft=blue, Stagnant/Withdrawn=gray). Layout uses `topicLaneY0 = eipReservedH + eipGap` to offset all topic lanes below. EIP zoom updates are integrated into the main `onZoom` handler (not a separate patch function).

**EIP display modes**:
- `EIPs` toggle adds EIP nodes/squares to timeline and network.
- `Linked EIPs` (default mode when EIPs are shown) displays only EIPs with an `eip_topic` edge to ethresear.ch topics.
- `All EIPs` includes disconnected EIP nodes as well.
- URL hash supports this mode via `eipmode=all`.

**EIP detail panel**: Full right-side panel showing status badge, type/category, fork tag, influence score, magicians engagement stats, ethresearch citation count, authors, requires/required-by (clickable), external links, and related ethresearch topics (top 10 by influence).

**EIP author sidebar**: Toggle in author sidebar header — `[ethresearch] [EIP Authors]`. Shows top 25 EIP authors sorted by influence, click for detail with EIP list as clickable tags.

**Timeline landmarks**: Fork lines at the bottom include Genesis (2015-07-30) through Osaka. An "ethresear.ch live" annotation (green dashed line) marks the forum creation date (2017-08-17). Fork labels and date axis are on separate rows to avoid overlap. Zoom is clamped: `scaleExtent([1, 8])` prevents zooming out past the initial view.

**macOS trackpad swipe-back prevention**: Three-layer defense stops the browser from interpreting leftward two-finger trackpad swipes as "navigate back":
1. **Document capture-phase handler** — `document.addEventListener('wheel', ..., {passive: false, capture: true})` on `#main-area` targets; fires at the top of the event dispatch chain before the compositor can act
2. **JS-applied `overscroll-behavior: none`** on `html` and `body` (supplements CSS in case the compositor doesn't pick up stylesheet rules)
3. **Element-level handlers** — non-passive `preventDefault()` on both the SVG node and the wrapper div, plus `touch-action: none` CSS on `.timeline-container` and its SVG

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
