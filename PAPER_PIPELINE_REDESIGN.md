# Paper Pipeline Redesign

## Problem Statement

The current 651-paper corpus has significant coverage gaps:

- **Only 7.3% of citation links are internal** — 1,337 of 18,302 reference links point to papers in our corpus
- **Fundamental papers are missing**: Casper FFG (423 cites), Ouroboros (1,408 cites), Ethereum Yellow Paper (5,313 cites), Algorand (1,406 cites)
- **Recent consensus papers absent**: RLMD-GHOST (arxiv:2302.11326), Ebb-and-Flow (arxiv:2009.04987)
- **OpenAlex reference data incomplete**: 96/651 papers still have 0 referenced_works after 3-pass enrichment
- **Citation counts diverge wildly**: Ebb-and-Flow shows 9 cites on OpenAlex vs 100 on Semantic Scholar

### Root Causes

1. **Discovery by keyword only**: Papers must match keyword queries + pass relevance scoring. Papers that don't mention "Ethereum" in title/abstract (like protocol-agnostic consensus work) are missed.
2. **No citation-graph discovery**: If our papers cite a paper 120 times, it should be in the corpus — but there's no mechanism for this.
3. **OpenAlex metadata gaps**: Preprints often have 0 references; published versions may not be linked. Citation counts are much lower than Semantic Scholar for CS conference papers.
4. **Single-source dependency**: Everything goes through OpenAlex, with SS only used for citation count enrichment.

## Proposed Architecture

### Phase 1: Discovery (multiple sources)

```
                    ┌──────────────┐
                    │ Keyword      │
                    │ Queries (OA) │──────┐
                    └──────────────┘      │
                    ┌──────────────┐      │
                    │ Author-based │      ├──→ Candidate Pool
                    │ Search (OA)  │──────┤    (dedup by DOI/title)
                    └──────────────┘      │
                    ┌──────────────┐      │
                    │ Citation     │      │
                    │ Expansion    │──────┤
                    └──────────────┘      │
                    ┌──────────────┐      │
                    │ Curated      │      │
                    │ Seeds        │──────┘
                    └──────────────┘
```

**Citation Expansion** (NEW): After initial keyword+author discovery:
1. Collect all referenced_works from accepted papers
2. Count how many corpus papers cite each external paper
3. Papers cited by ≥ 3 corpus papers → auto-add to candidates
4. Fetch their metadata from OpenAlex
5. Repeat for 1-2 rounds (snowball sampling)

This would catch Casper FFG (cited by 35 corpus papers), Ouroboros (cited by 37), etc.

### Phase 2: Enrichment (dual-source)

```
  Candidates ──→ OpenAlex metadata (batch, free)
       │              title, authors, year, venue, DOI, concepts
       │
       ├──→ Semantic Scholar enrichment (batch + per-paper)
       │         citation count (more accurate)
       │         references list (more complete)
       │         influential citation count
       │
       └──→ Relevance scoring + filtering
                  → papers-db.json
```

**Key change**: Use Semantic Scholar as the primary source for:
- Citation counts (SS is consistently more accurate for CS papers)
- Reference lists (SS parses references from PDFs directly, not just metadata)
- Paper search for papers not found in OpenAlex

Use OpenAlex as the primary source for:
- Batch discovery (keyword + author search — free, unlimited)
- Concepts/keywords (richer topic tagging)
- Venue/publisher metadata

### Phase 3: Citation Graph (in analyze.py)

```
  papers-db.json ──→ Build OA ID + DOI + arXiv lookups
       │
       ├──→ OA referenced_works → internal edges
       ├──→ SS references → internal edges (union)
       │
       └──→ paper_graph { nodes[], edges[] }
                 → analysis.json
```

**Key change**: Union OA and SS reference lists to maximize internal edge coverage.
Currently 1,329 edges; projected 2,000+ with SS references + citation expansion.

## Implementation Plan

### Step 1: Add citation expansion to build_papers_db.py

After initial keyword+author candidates are scored and filtered:

```python
# Citation expansion: find papers our corpus cites frequently
external_ref_counts = Counter()
for paper in accepted:
    for ref_oa_id in paper.get("referenced_works", []):
        if ref_oa_id not in accepted_oa_ids:
            external_ref_counts[ref_oa_id] += 1

# Auto-add papers cited by >= 3 corpus papers
expansion_ids = [oa_id for oa_id, count in external_ref_counts.items()
                 if count >= 3]
# Batch-fetch from OpenAlex, score, and add
```

This is ~150-300 papers per round. Run 1-2 rounds.

### Step 2: Upgrade enrich_paper_refs.py to use SS as primary ref source

Current: OA IDs → OA DOIs → SS fallback
New: For ALL papers, fetch SS references first (batch endpoint), then fill gaps with OA.

SS batch endpoint: `POST /paper/batch` with fields `references.externalIds`
- Supports up to 500 papers per request
- Returns full reference lists with external IDs (DOI, ArXiv, etc.)

```python
# SS batch reference fetch
ss_ids = [ss_paper_id(p) for p in papers if ss_paper_id(p)]
batches = chunk(ss_ids, 500)
for batch in batches:
    response = post("/paper/batch", {"ids": batch},
                    fields="references.externalIds")
    # Map SS references back to OA short IDs
```

### Step 3: Dual-source citation counts

Replace single `cited_by_count` with:
- `oa_cited_by_count`: from OpenAlex
- `ss_cited_by_count`: from Semantic Scholar
- `cited_by_count`: max(oa, ss) — used for influence scoring

This is already partially done but should be formalized.

### Step 4: SS-based search for missing papers

For papers we know should exist but OA doesn't find:
- Use SS `/paper/search` with Ethereum-specific queries
- SS search often returns papers OA misses (especially IACR ePrints)

Add queries like:
- "ethereum proof of stake consensus"
- "ethereum finality"
- "ethereum fork choice"
- "gasper protocol"
- "single slot finality"

### Step 5: Preprint/published version merging

Currently handled by `merge_paper_rows` with DOI-based dedup.
Enhance:
- Also merge by arXiv ID → published DOI mapping
- When merging, keep the version with more references
- Keep the higher citation count

## Expected Outcomes

| Metric | Current | Projected |
|--------|---------|-----------|
| Papers in corpus | 651 | 800-950 |
| Papers with references | 555 | 800+ |
| Internal citation edges | 1,329 | 2,500+ |
| Internal reference rate | 7.3% | 15-20% |
| Fundamental papers coverage | ~60% | ~95% |

## Risk Mitigation

- **Rate limits**: SS is 100 req/5min unauthenticated. Citation expansion + batch refs for 800 papers ≈ 10-15 minutes. Acceptable.
- **Corpus bloat**: Citation expansion adds general CS papers (Bitcoin, BFT, etc.). Filter by: must be cited by ≥ 3 corpus papers, OR have relevance score ≥ 6.
- **Stale data**: OA/SS data changes over time. The pipeline is already idempotent; re-running updates everything.

## Implementation Order

1. **Citation expansion** in `build_papers_db.py` — biggest impact, catches all fundamental papers
2. **SS batch references** in `enrich_paper_refs.py` — completes the citation graph
3. **SS citation counts** — more accurate influence scoring
4. **SS search fallback** — catches remaining edge cases
5. **Better dedup** — preprint/published merging
