# Query signal validation — 3 October 2026

The project direction remains worth investigating. Queries provide usable lexical information, but the evidence argues against automatically discarding history that lacks matching query terms. Architecture selection remains open.

## What was run

`notebooks/diagnostics/03_query_signal_validation.ipynb` executes `scripts/query_diagnostics.py`. A uniform sample of **5,000 complete search records**, seed **4222**, contains **449,052 candidate occurrences**. The entire **12,141,247-row catalog** was scanned to retrieve these candidates' metadata; 99.56% of sampled candidate occurrences have metadata. The repeat-query audit covers all **173,831 records**. These denominators must not be mixed.

The official [dataset README](https://github.com/rucliujn/JDsearch#dataset-files) specifies `_` between list entries and `\x18` (octal `\030`) between term IDs. Empty text and `-1` do not contribute terms. Overlap uses distinct token sets, ignoring order and multiplicity. Original words remain unavailable.

## Findings

- **Exact repeats are rare, though the earlier count was misleading.** Raw string matching finds only **1** current query in its own history. Matching distinct term sets finds **610 records (0.35%)** on the full data. Inspected examples differ in token order. Neither result supports building the project around exact repeats.
- **Partial historical-query overlap is available for 41.14% of sampled records.** The mean within-record share of search-associated history actions with any matching term is **10.09%**, among records with search-associated history. Any shared token is weak lexical evidence, not proof of the same shopping goal. Multiple actions may belong to one historical search.
- **Query-title overlap can distinguish candidates.** Coverage differs among candidates with known metadata in **90.00%** of sampled lists. For each eligible search, engaged candidates' mean query coverage exceeds ignored candidates' by **0.0164** on average (95% paired-record bootstrap interval **0.0110–0.0221**). Actual-query coverage exceeds coverage from a shuffled other-record query by **0.6860** (**0.6789–0.6932**). This supports using shared term IDs for lexical comparison; it does not recover their meanings.
- **A lexical-only ranking score gives a small improvement over random ranking.** The table below quantifies this; it does not demonstrate improvement over a trained baseline or last year's project.
- **The simplest hard query filter makes exact-product history ranking worse.** Its difference from unrestricted history is **−0.0493 NDCG@10**, with paired bootstrap interval **−0.0552 to −0.0437**. Keeping query-less and non-overlapping history available is therefore sensible. This result does not test learned attention or softer relevance weights.

| Untrained ranking score | Mean NDCG@10 | Difference from random, 95% interval |
|---|---:|---:|
| Expected random order | 0.0809 | — |
| Query coverage in title | 0.0917 | +0.0108 [0.0082, 0.0135] |
| Query-title Jaccard overlap | 0.0948 | +0.0139 [0.0090, 0.0186] |
| Candidate interaction count in all own history | 0.1809 | +0.1000 [0.0925, 0.1077] |
| Count only history actions with overlapping recorded query | 0.1316 | +0.0507 [0.0451, 0.0562] |

Ranking uses full lists, linear relevance gains 0/1/2/3, and exact expected DCG under random tie breaking. The **59 all-zero lists** are excluded, leaving **4,941 evaluated searches**. Confidence intervals use **2,000 paired bootstrap resamples of searches**. File position never resolves ties. These are exploratory results, not held-out model evaluation, causal effects or revenue estimates.

## Notebook correction and validation

The interim notebook now counts actual terms and uses exact-token brand/category overlap. The old rule required a whole name substring with at least eight digits. In the sample, it had **zero legacy-only matches unsupported by token overlap**, but the new any-token definition adds **64,099 brand** and **70,937 level-3 category** matches. Those changes reflect both removal of the digit-length rule and a different feature definition; an any-token brand match does not establish that the query expresses brand intent.

Parser assertions cover substrings, short IDs, placeholders, reordered/repeated tokens and malformed inputs. An independent permutation calculation verifies tie-safe NDCG. The edited interim token-count and matching cells were also executed on a code-validation fixture of 200 real records and 200,000 catalog rows, and checked against direct splitting; that prefix fixture supplies no project findings. All diagnostic notebook code cells were executed, and both notebooks' code cells compile.

The consolidated main interim notebook has now been rerun. Its raw summaries cover the full files, and its corrected feature statistics use the same 5,000-record sample. Fresh query/history features are checked against the diagnostic tables; architecture selection remains open.

## Implication for scope

Keep the question: **which historical behaviours provide useful evidence for the current search?** Include lexical query relevance and exact-product history as comparison features; avoid committing to repeated-query modelling or hard filtering. Next examine brand/shop/category-depth match coverage and within-list variation, including query-less history. A controlled model comparison is still needed to establish whether adaptive weighting adds value beyond richer inputs.
