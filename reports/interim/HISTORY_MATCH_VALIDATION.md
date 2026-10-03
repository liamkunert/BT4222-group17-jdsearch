# History matches and category depth — 3 October 2026

The checks support investigating which historical behaviours should influence the current search. Exact-product, shop, brand and category matches all provide available signals. Finer category matches give a modest improvement in simple rankings, while query-less history remains useful. These findings leave the architecture open.

## Scope and definitions

The executed `notebooks/diagnostics/04_history_match_validation.ipynb` uses the **same 5,000 records** as the query diagnostics, seed **4222**, with **449,052 candidate occurrences** and **758,712 historical actions**. It scans all **12,141,247 catalog rows** and retains metadata for the union of historical and candidate products. It does not sample catalog rows or drop history products outside the candidate set.

A candidate matches history if the shopper previously interacted with the same product, brand, shop or category path. Count scores use numbers of past actions; no action-strength or recency weights are imposed. Category L3, for example, matches the L1/L2/L3 path. Brand and shop are separate attributes, not levels of the category hierarchy.

Coverage and engagement comparisons exclude candidates whose required metadata is unavailable. Counts of matching actions can differ even when all candidates have some match, so both binary match variation and count variation are measured. Searches receive equal weight in the within-search comparisons.

## Main results using all supplied history

| Match | Candidates with an observed match | Engagement with / without a match | Lists where history counts vary | Count-score NDCG@10 |
|---|---:|---:|---:|---:|
| Exact product | 0.79% | 25.82% / 1.89% | 29.52% | 0.1809 |
| Brand | 22.69% | 2.99% / 1.81% | 59.44% | 0.1198 |
| Shop | 7.16% | 6.46% / 1.75% | 50.78% | 0.1706 |
| Category L1 | 75.17% | 2.16% / 1.83% | 58.96% | 0.0849 |
| Category L2 | 57.49% | 2.27% / 1.82% | 60.70% | 0.0882 |
| Category L3 | 40.66% | 2.48% / 1.81% | 55.96% | 0.0945 |
| Category L4 | 37.59% | 2.56% / 1.79% | 55.92% | 0.0958 |

The coverage denominators are 449,052 candidates for product, 447,092 for brand/categories and 443,089 for shop. Each list-variation percentage uses all 5,000 searches. Pooled engagement rates describe associations and can reflect differences between searches; they are not conversion effects or causal estimates.

Within-search engagement differences are also positive for every all-history match type, with paired-record bootstrap intervals excluding zero. The comparison is restricted to searches with both matched and unmatched eligible candidates, so its search count differs by feature. Those counts and intervals are in `outputs/interim/tables/history_validation/history_match_coverage_and_engagement.csv`.

### What the category levels add

Known candidates have different category paths in **66.34% / 78.90% / 89.04% / 91.16%** of lists at levels 1–4. Broad categories are not constant in most lists, though their match counts are weak ranking scores here. Deeper matches become less common but more selective.

Paired NDCG improvements are **L2 over L1: +0.0033** (95% interval 0.0019–0.0047), **L3 over L2: +0.0063** (0.0045–0.0080), and **L4 over L3: +0.0013** (0.0004–0.0022). Thus category depth is worth retaining as a hypothesis, but the fourth level supplies a small incremental gain in this simple comparison. No learned combination or neural architecture has been tested.

### History with versus without a recorded query

**491,270 actions (64.75%)** in this sample are query-less; 267,442 have a recorded query. Both sources provide positive exploratory ranking signals. For example, shop-count ranking scores **0.1454** using search-associated history and **0.1496** using query-less history, compared with **0.0809** for expected random order. Combining both sources gives **0.1706**.

Do not interpret this as proof that query-less history is intrinsically more reliable: there is more of it, and the action mix can differ. Nor does query presence establish relevance to the current query. These results support retaining both sources for controlled comparisons and possible learned weighting.

## Metadata and hierarchy checks

Catalog metadata covers **99.56% of sampled candidate occurrences** and **95.19% of sampled historical actions**. Shop IDs are usable for 98.67% of candidate occurrences and 94.83% of historical actions. Missing history metadata can hide genuine matches, so zero means no *observed* match.

The full catalog has **no empty/-1 category IDs**, including L4, and no rows with L4 equal to L3. This does not imply complete category information for products absent from the catalog.

Some category IDs have multiple observed parents: **17 L3 IDs** and **33 L4 IDs**; L2 has none. Full ancestor paths therefore avoid conflating identically numbered categories under different parents. The consolidated notebook 02 now uses the same ancestor-path definitions. Its fresh positive-match counts are checked against all 21 source/attribute combinations in these diagnostic tables.

## Validation and limits

Synthetic assertions cover missing metadata, repeated actions, query-source alignment, reused child IDs, missing L4 and empty history. **1,344 direct count comparisons** on actual records verify the aggregation. Search and query-less counts sum to all-history counts, and deeper path counts never exceed ancestor counts.

Ranking uses full candidate lists, linear gains 0/1/2/3 and expected random tie breaking. It excludes 59 all-zero lists, leaving **4,941 searches**. Confidence intervals use **2,000 paired bootstrap resamples of searches**. These are untrained, exploratory heuristics on the diagnostic sample. They do not establish improvement over a trained baseline or last year's model.

## Implication for the proposal

Keep exact-product matches as a strong but rare signal, with brand/shop/category matches as more widely available evidence. Keep multiple category depths and test their incremental value. Preserve query-less history. The next modelling question is whether combining and selectively weighting these signals improves on straightforward counts and query relevance; no specific architecture is committed by this analysis.
