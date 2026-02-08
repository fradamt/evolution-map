# Influence Scoring Redesign

## Status Quo

### Three Separate Systems

| System | Where | Formula | Range | Entity Count |
|--------|-------|---------|-------|-------------|
| Topic influence | `analyze.py` L1334-1360 | 30% citation in-degree, 25% likes, 20% log(views), 15% posts, 10% prolific author | 0.01–0.80 | 2,903 (550 included) |
| EIP influence | `analyze.py` L2026-2076 | 25% status weight, 30% magicians engagement, 20% ethresearch citations, 15% fork bonus, 10% requires depth | 0.01–0.80 | 885 (264 above 0.10) |
| Paper influence | `render_html.py` L3607-3633 (JavaScript!) | 62% citation count, 23% relevance, 15% EIP refs; recency damping | 0.03–0.52 | 685 |

### Problems

1. **Scores are incomparable**: A topic at 0.30, an EIP at 0.30, and a paper at 0.30 use entirely different scales and normalization approaches (min-max for topics/EIPs, custom mapping for papers).

2. **No cross-entity reinforcement**: EIP-1559 (highest EIP at 0.80) doesn't boost its related ethresearch topics. A highly-cited paper on MEV doesn't boost MEV topics.

3. **Paper scoring is in the wrong place**: Computed in JavaScript at render time, not in the Python analysis pipeline. This means `analysis.json` has no paper influence scores.

4. **Top papers are generic surveys**: "Blockchain-based traceability in Agri-Food supply chain" (824 citations, inf=0.41) outranks core protocol research papers with fewer citations.

5. **Min-max normalization is outlier-sensitive**: One topic with extreme views skews the entire distribution.

6. **Magicians topics have no influence score at all**.

## Design

### Principles

1. **Single pipeline**: All scoring in `analyze.py`. The HTML renderer consumes scores, never computes them.
2. **Percentile-based normalization**: Rank-based scoring (percentile) instead of min-max to resist outliers.
3. **Two-phase scoring**: Intrinsic signals first, then cross-entity reinforcement.
4. **Protocol-relevance focus**: "Importance to Ethereum protocol evolution" over raw popularity.
5. **Comparable scales**: After normalization, 0.50 should mean roughly "top 50th percentile of influence within that entity type."

### Phase 1: Entity-Intrinsic Scores

#### Topics (ethresear.ch)
```
engagement = percentile_rank(likes + sqrt(posts) + log1p(views))
citation   = percentile_rank(in_degree)
intrinsic  = 0.50 * citation + 0.50 * engagement
```

#### EIPs
```
status_w   = {Final: 1.0, Living: 0.85, LastCall: 0.65, Review: 0.5, Draft: 0.3, Stagnant: 0.1, Withdrawn: 0.05, Moved: 0.02}
engagement = percentile_rank(magicians_likes + log1p(magicians_views) + sqrt(magicians_posts))
ethresearch = percentile_rank(ethresearch_citation_count)
fork_bonus  = 1.0 if assigned to shipped fork, else 0
requires_d  = min(1.0, len(requires) * 0.15)
intrinsic   = 0.20 * status_w + 0.25 * engagement + 0.25 * ethresearch + 0.20 * fork_bonus + 0.10 * requires_d
```

#### Papers
```
citations     = percentile_rank(cited_by_count, among papers with >0 cites; 0-cite papers get 0)
protocol_rel  = percentile_rank(relevance_score)
eip_anchoring = min(1.0, eip_ref_count / 2.0)
intrinsic_raw = 0.45 * citations + 0.35 * protocol_rel + 0.20 * eip_anchoring
recency_damp  = {age<=0: 0.55, age==1: 0.70, age==2: 0.85, else: 1.0}
intrinsic     = intrinsic_raw * recency_damp
```

### Phase 2: Cross-Entity Reinforcement (Single Pass)

After intrinsic scores, apply additive boosts:

| Rule | Boost | Cap |
|------|-------|-----|
| Topic mentions Final EIP → topic boost | +0.03 per Final EIP mentioned | +0.12 |
| Topic mentions fork-shipped EIP → topic boost | +0.04 per shipped EIP | +0.12 |
| EIP cited by high-influence topic → EIP boost | +0.02 per topic with intrinsic ≥ 0.3 | +0.10 |
| Paper cites EIP with intrinsic ≥ 0.2 → paper boost | +0.03 per such EIP | +0.09 |
| Topic related to high-citation paper → topic boost | +0.02 per paper with intrinsic ≥ 0.3 | +0.08 |

After boosts, re-normalize per entity type using percentile rank to keep [0, 1] range.

### Phase 3: Tier Classification

After final scores, classify:
- **Tier 1**: influence ≥ 0.40 or in_degree ≥ 3 (for topics)
- **Tier 2**: referenced by Tier 1 with influence ≥ 0.15
- **Included**: Tier 1 ∪ Tier 2 (target ~550 topics)

### Data Pipeline Changes

1. `analyze.py` loads `papers-db.json` (not just `papers-seed.json`)
2. Computes paper intrinsic scores in Python
3. Stores paper scores in `analysis.json` under `papers` key with `influence_score` field
4. `render_html.py` reads pre-computed paper influence instead of computing it

### Output Shape Changes

```json
{
  "papers": {
    "doi:10.1109/sp.2020.00032": {
      "id": "...",
      "title": "...",
      "influence_score": 0.72,
      "intrinsic_score": 0.68,
      "cross_entity_boost": 0.04,
      ...
    }
  }
}
```

### Validation Criteria

1. EIP-1559, EIP-4844, EIP-7702 should be top-5 EIPs
2. "Flash Boys 2.0" should be top-3 papers
3. "Blockchain-based supply chain" papers should NOT be top-20
4. Top topics should be recognizable protocol research (Plasma, rollups, PBS, etc.)
5. Cross-entity: topics about EIP-1559 should score higher than similar topics without that EIP link
6. Combined top-50 across all types should have a mix (not all one type)
