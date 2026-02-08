# Influence Scoring — Design & Implementation

This document describes the unified influence scoring system used across all
entity types in the evolution map. It supersedes the earlier three-separate-
systems approach (min-max topics, min-max EIPs, JavaScript paper scoring).

## Overview

All entity types — ethresear.ch topics, EIPs, and academic papers — share a
common scoring methodology:

1. **Percentile-based normalization** with midrank tie handling
2. **Power-2.0 shaping** (right-skewed, mean ≈ 0.33, median ≈ 0.25)
3. **Two-phase scoring**: intrinsic signals, then cross-entity reinforcement
4. **Single pipeline**: all scoring in `analyze.py`, never in the renderer

### Score Distribution

The `shaped_rank(values, power=2.0)` function maps percentile ranks to a
right-skewed distribution:

| Percentile | Score | Meaning |
|------------|-------|---------|
| 0.50 | 0.25 | Median item |
| 0.71 | 0.50 | Moderately influential |
| 0.87 | 0.75 | Highly influential |
| 1.00 | 1.00 | Most influential |

This ensures most items score low, with a long tail of high-influence items.

### Tie Handling

`percentile_rank()` uses **midrank** (average rank for tied values):
- `[5, 5, 5]` → `[0.5, 0.5, 0.5]` (not `[0.0, 0.5, 1.0]`)
- `[1, 5, 5, 10]` → `[0.0, 0.5, 0.5, 1.0]`

---

## Phase 1: Entity-Intrinsic Scores

### Topics (ethresear.ch)

```
engagement = percentile_rank(likes + sqrt(posts) + log1p(views))
citation   = percentile_rank(in_degree)
intrinsic  = 0.50 * citation + 0.50 * engagement
```

**Inputs**: Discourse `like_count`, `posts_count`, `views`, and citation
in-degree (count of other topics linking to this one). All 2,903 topics
are scored; tier filtering selects ~600 for the "included" set.

### EIPs

```
status_w   = {Final: 1.0, Living: 0.85, LastCall: 0.65, Review: 0.5,
              Draft: 0.3, Stagnant: 0.1, Withdrawn: 0.05, Moved: 0.02}
engagement = percentile_rank(magicians_likes + log1p(magicians_views) + sqrt(magicians_posts))
ethresearch = percentile_rank(ethresearch_citation_count)
fork_bonus = 1.0 if assigned to shipped fork, else 0
requires_d = min(1.0, len(requires) * 0.15)
intrinsic  = 0.20 * status_w + 0.25 * engagement + 0.25 * ethresearch
           + 0.20 * fork_bonus + 0.10 * requires_d
```

**Inputs**: EIP status, ethereum-magicians.org engagement metrics,
ethresear.ch citation count (how many topics mention this EIP), fork
assignment, and `requires` dependency count. All 885 EIPs are scored.

### Papers

```
citations     = percentile_rank(cited_by_count)     # zero-cite papers → 0
protocol_rel  = percentile_rank(relevance_score)
eip_anchoring = min(1.0, eip_ref_count / 2.0)

# Relevance gate: low-relevance papers (rel < 10) get citation dampened
if relevance_score < 10:
    citations *= 0.25

intrinsic_raw = 0.40 * citations + 0.40 * protocol_rel + 0.20 * eip_anchoring

# Recency damping (newer papers penalized until citations stabilize)
recency_damp  = {age<=0: 0.55, age==1: 0.70, age==2: 0.85, else: 1.0}
intrinsic     = intrinsic_raw * recency_damp
```

**Inputs**: OpenAlex `cited_by_count`, `relevance_score` from papers-db.json
(protocol relevance computed by `build_papers_db.py`), and EIP mentions in
paper title. 685 papers from papers-db.json are scored.

**Relevance gate**: Papers with `relevance_score < 10` (bottom ~71%) get
their citation contribution dampened to 25%. This prevents "blockchain for
healthcare/supply chain" papers with high academic citations but low protocol
relevance from dominating the rankings.

**Why this works**: Relevance scores range 8.1–20.9. Protocol-relevant papers
(Flash Boys 2.0, EIP-1559 analysis, GHOST/Casper, etc.) score 12+. Generic
"blockchain for X" papers cluster at 8.3–9.3. The gate at 10.0 cleanly
separates these populations.

---

## Phase 2: Cross-Entity Reinforcement

After intrinsic scoring, a single additive boost pass provides cross-entity
signal. Boosts are applied to the intrinsic composite before the final
`shaped_rank()` transformation.

### Topic → EIP Boosts

Topics mentioning important EIPs receive a boost:

| Condition | Boost per EIP | Cap |
|-----------|---------------|-----|
| EIP has status `Final` | +0.03 | +0.12 total |
| EIP is assigned to a shipped fork | +0.04 | +0.12 total |

### EIP → Topic Boosts

EIPs cited by high-influence topics receive a boost:

| Condition | Boost per topic | Cap |
|-----------|-----------------|-----|
| Topic has intrinsic score ≥ 0.3 | +0.02 | +0.10 total |

### Final Normalization

After boosts, each entity type is independently passed through
`shaped_rank(power=2.0)` to produce the final `influence_score` in [0, 1].

---

## Tier Classification (Topics Only)

Topics are classified into tiers for the "included" set:

- **Tier 1**: `influence_score >= 0.70` OR `in_degree >= 3`
- **Tier 2**: Referenced by a Tier 1 topic AND `influence_score >= 0.30`
- **Included**: Tier 1 ∪ Tier 2

Adaptive thresholds keep the included set between 400–600 topics (target ~600):
- If `< 400`: add topics with `influence >= 0.15` or `in_degree >= 2`
- If `> 600`: trim lowest Tier 2 topics down to 550

---

## Validation Results

### Score Distributions

| Metric | Topics (included) | EIPs | Papers |
|--------|-------------------|------|--------|
| Count | 600 | 885 | 676 |
| Mean | 0.799 | 0.329 | 0.338 |
| Median | 0.805 | 0.247 | 0.257 |
| Range | [0.24, 1.00] | [0.00, 1.00] | [0.00, 1.00] |

EIP and paper distributions are comparable (mean ≈ 0.33, median ≈ 0.25).
Included-topic scores are higher because they are the top of the full
2,903-topic distribution after tier filtering.

### Top Entities

**Top 5 Topics**: Based Rollups, Mass TX Validation, Based Preconfirmations,
Plasma Cash, MEV Burn — all core protocol research.

**Top 5 EIPs**: EIP-7702, EIP-4844, EIP-1559, EIP-7251, EIP-2930 — all
Final status, shipped in production forks.

**Top 5 Papers**: Flash Boys 2.0, Empirical Analysis of EIP-1559, Quantifying
BEV, Tesseract, Securify — all Ethereum-specific research.

### Combined Top 50

30 Topics, 9 EIPs, 7 Papers — proportional to dataset sizes (65/20/15%).
No irrelevant papers in top 50 (previously 6 healthcare/supply chain papers
appeared in top 50 before the relevance gate fix).

### Regression Checks

- EIP-1559: rank #3 EIP (was top EIP in old system)
- EIP-4844: rank #2 EIP
- Minimal Viable Plasma: rank #6 topic (was top topic in old system)
- Flash Boys 2.0: rank #1 paper
- 0 supply chain / generic survey papers in top 20

---

## Previous System (Replaced)

Three independent scoring systems with different normalization:

| System | Normalization | Formula |
|--------|--------------|---------|
| Topics | Min-max | 30% in-degree, 25% likes, 20% log(views), 15% posts, 10% prolific author |
| EIPs | Min-max | 25% status, 30% magicians engagement, 20% citations, 15% fork, 10% requires |
| Papers | Custom (JS) | 62% citations, 23% relevance, 15% EIP refs; computed in render_html.py |

**Problems solved**:
1. Scores were incomparable across types (different scales, normalization)
2. No cross-entity reinforcement
3. Paper scoring in JavaScript, not the analysis pipeline
4. Generic high-citation papers dominated paper rankings
5. Min-max was outlier-sensitive
