# Papers Corpus

This repo now includes a broad, filterable Ethereum-adjacent paper corpus:

- `papers-db.json`: generated database
- `build_papers_db.py`: reproducible builder
- `search_papers.py`: fuzzy title/author search utility

## Rebuild

Default (recommended broad baseline):

```bash
python3 build_papers_db.py
```

Current default config:

- `--min-score 8.0`
- `--min-year 2014`
- `--query-pages 2`
- `--author-pages 1`
- `--per-page 100`

Higher recall (more papers, more noise):

```bash
python3 build_papers_db.py --min-score 7 --query-pages 3 --author-pages 2
```

Higher precision (fewer papers, cleaner):

```bash
python3 build_papers_db.py --min-score 9
```

## Output shape

Top-level:

- `version`, `generated_at`, `description`
- `config`, `queries`, `author_seeds`, `stats`
- `papers[]`

Each paper row includes:

- Core metadata: `id`, `title`, `year`, `authors`, `venue`, `doi`, `arxiv_id`, `url`, `openalex_id`
- Metrics: `cited_by_count`, `relevance_score`
- Explainability: `relevance_reasons`, `tags`, `matched_queries`, `source_types`
- Dedupe helpers: optional `aliases`

## Notes

- Discovery source is OpenAlex plus the curated `papers-seed.json`.
- Rows are deduped by normalized `title + year`.
- The goal is broad coverage with an explicit minimum relevance floor, not final curation.

## Quick search

Search by author:

```bash
python3 search_papers.py "tim roughgarden" --author
```

Search by title:

```bash
python3 search_papers.py "eip-4844" --title
```

Search both fields (default):

```bash
python3 search_papers.py "loss versus rebalancing" --limit 15
```
