# Findings from data exploration

What our exploration established, and what each result means for the pipeline. This file replaces the interim-stage notes (`QUERY_VALIDATION.md`, `HISTORY_MATCH_VALIDATION.md`, `NOTEBOOK_STATUS.md`). The evidence lives in executed notebooks:

| Evidence | Notebook |
|---|---|
| Full-data summaries, feature dictionary, statistics | `notebooks/01_data_understanding.ipynb` |
| Query tokens, query-title overlap, current/past query overlap | `notebooks/exploration/query_signal_validation.ipynb` |
| Product/brand/shop/category history matches, query-less history | `notebooks/exploration/history_match_validation.ipynb` |
| How search context changes the value of history (section 6) | `notebooks/exploration/session_context_check.ipynb` |
| Interim report Figure 5 | `scripts/signal_check_figure.py` |
| First team EDA (superseded, kept for reference) | `notebooks/exploration/early_eda.ipynb` |

Last updated 4 October 2026.

## 1. Scope conventions

- **Raw summaries** use the full files: 173,831 search records, 15,510,012 candidate occurrences, 26,667,260 historical actions, 12,141,247 catalogue rows.
- **Feature statistics and signal checks** use one uniform sample of **5,000 whole search records, seed 4222**: 449,052 candidates and 758,712 historical actions, with metadata looked up in the full catalogue. All exploration notebooks share it.
- **Signal checks** rank complete candidate lists, use linear gains 0/1/2/3, take the exact expected DCG under random tie-breaking, and exclude the 59 sampled searches without an engaged candidate, leaving **4,941 searches**. Intervals use 2,000 paired bootstrap resamples of searches.
- These are untrained, exploratory heuristics, not held-out model results. Do not mix full-data and sample denominators.

## 2. Dataset facts and pipeline rules

| Fact | Evidence | Rule for the pipeline |
|---|---|---|
| Candidate file order encodes the label | In 100% of searches with an engaged candidate, every engaged candidate precedes every non-engaged one | Never use list position as a feature; shuffle candidates or break score ties at random |
| Some searches have no engaged candidate | 2,103 records (1.21%) | Exclude from evaluation (as the source paper does); decide training use explicitly |
| Time gaps are in seconds | Read as seconds, the median history span is 283 days and the 95th percentile 362 days; only 1 record exceeds the documented one-year window | Treat gaps as seconds. `history_time_list` has one more element than the other history lists: an initial 0 and a final gap to the current search |
| No user IDs, no absolute timestamps | One row = one sampled user's last search; all final searches fall on 17 Oct 2022 | Split by whole search record; no cross-user temporal split |
| Missing catalogue metadata | 731,389 behaviour products have no catalogue row; metadata covers 99.6% of candidate occurrences and 95.1% of historical actions (full data); 103,162 catalogue rows lack a shop ID | Treat missing metadata as unknown, never as "no match"; look up both history and candidate products in the full catalogue |
| Category IDs reused under different parents | 17 level-3 and 33 level-4 IDs have more than one parent; no empty or -1 category IDs in the catalogue | Match categories on the full ancestor path |
| Most history is query-less | 64.7% of past actions have query `-1` (browsing, recommendations) | Keep query-less history as its own source |
| Text is anonymised | Term IDs separated by `\x18`; list entries by `_` | Compare whole term IDs as distinct token sets; meanings are unavailable |
| Selected sample | Records are active users' last searches; 98.8% contain an engagement | Rates do not represent JD's overall traffic |
| Exact repeat queries are rare | Raw string repeat in 1 record; same distinct term set in 610 records (0.35%) | Don't build the project around exact query repeats |
| Labels are deepest outcomes | One label per candidate (0 none, 1 click, 2 cart, 3 purchase) | Threshold shares are depth of engagement, not click-to-cart-to-purchase conversion |

## 3. Evaluation protocol (decided)

- Task: personalised re-ranking of each search's complete candidate list; target = graded label used as the NDCG gain.
- Primary metric NDCG@10 on complete, un-downsampled lists; Recall@10 (and MRR, under team discussion) as support.
- Random tie-breaking; position never used.
- Splits by whole search record. The 5,000 explored records have informed feature choices; keep this in mind when setting up the final evaluation.
- Population features (item popularity, cold flags) from training records only; supervised encodings out-of-fold within training. The `_eda` features in notebook 01 are descriptive only.

## 4. Signal evidence (4,941 sampled searches)

| One-signal ranking | Coverage of candidates | Engagement with / without match | NDCG@10 | Difference from random [95% interval] |
|---|---:|---:|---:|---:|
| Expected random order | | | 0.0809 | |
| Query coverage in title | | | 0.0917 | +0.0108 [0.0082, 0.0135] |
| Query-title Jaccard | | | 0.0948 | +0.0139 [0.0090, 0.0186] |
| Same product in own history | 0.79% | 25.82% / 1.89% | 0.1809 | +0.1000 [0.0925, 0.1077] |
| Same product, query-matched history only | | | 0.1316 | +0.0507 [0.0451, 0.0562] |
| Same brand | 22.69% | 2.99% / 1.81% | 0.1198 | |
| Same shop | 7.16% | 6.46% / 1.75% | 0.1706 | |
| Same category path L1 | 75.17% | 2.16% / 1.83% | 0.0849 | |
| L2 | 57.49% | 2.27% / 1.82% | 0.0882 | |
| L3 | 40.66% | 2.48% / 1.81% | 0.0945 | |
| L4 | 37.59% | 2.56% / 1.79% | 0.0958 | |

Coverage denominators: 449,052 candidates for product, 447,092 for brand and categories, 443,089 for shop. Pooled engagement rates are associations, not effects; within-search differences are positive for every match type (intervals in `outputs/interim/tables/history_validation/history_match_coverage_and_engagement.csv`).

What this means:

1. **Exact repeats are strong but rare**: a key feature that cannot carry a model alone.
2. **Shop and brand history generalise** to never-seen products, which matters because 56.5% of candidate occurrences (80.5% of distinct candidates) never appear in any history.
3. **Hard-filtering history by query overlap hurts** (difference -0.0493 [-0.0552, -0.0437]). Weight history; don't discard it. This does not test learned or soft weighting.
4. **Query-less history carries signal**: shop ranking scores 0.1496 from query-less history, 0.1454 from search-linked history, 0.1706 combined. Not proof that one source is more reliable; volumes and action mixes differ.
5. **Query-title overlap is real but modest.** Coverage differs within 90.00% of lists; engaged candidates' coverage exceeds ignored candidates' by 0.0164 [0.0110, 0.0221]; a shuffled-query control drops coverage by 0.6860. JD's retrieval already returns lexically relevant products.
6. **Category depth adds little beyond L3**: L2 over L1 +0.0033 [0.0019, 0.0047], L3 over L2 +0.0063 [0.0045, 0.0080], L4 over L3 +0.0013 [0.0004, 0.0022]. Candidate category paths vary within 66.34% / 78.90% / 89.04% / 91.16% of lists at L1-L4.
7. **Pooled feature-mean ratios mislead**: query-title overlap shows ratios of only 1.0-1.1 pooled, yet helps within searches. Use within-search comparisons.

Validation behind these numbers: parser assertions (substrings, short IDs, placeholders, reordered tokens), an independent permutation check of tie-safe NDCG, 1,344 direct count comparisons on actual records, and cross-checks of notebook 01's features against all 21 source/attribute match counts.

## 5. Prior baseline: Team 3 diagnosis

Reviewed 4 October 2026 from [their repository](https://github.com/myathetchai/bt4222-team3-jdsearch). Every group has this code, so fixing it is table stakes (final rubric aspect 2), not our main contribution.

**Evaluation**

- **Ranking by the wrong score** (`Models/3.1_Hybrid_NCF_with_LSTM.ipynb` and `3.2_Hybrid_NCF_with_GRU.ipynb`, test cells): candidates are ranked by `probs.max(dim=1)`, the highest class probability, so a confident "no interaction" prediction ranks at the top.
- **Downsampled lists** (`Data Preparation/1. Sampling.ipynb`): all positives plus 4 negatives per positive, so lists average 9.3 candidates and 81% have 10 or fewer. Applying their sampling to the full data (171,728 searches, 20 random orderings each, their NDCG formula with gains 2^label - 1): random order scores **HR@10 0.992 and NDCG@10 0.533**, against their reported **0.978 and 0.568**. On complete lists, random NDCG@10 with the same formula is 0.083. This simulation was run ad hoc; add it to the baselines notebook.
- **Class collapse**: the unweighted model predicts class 0 for 98.74% of test candidates (accuracy 0.8015 = the share of class 0 after downsampling); the weighted model reaches accuracy 0.5117, macro F1 0.289; the ordinal model predicts class 1 for 89.84% (accuracy 0.1825) and is described as an improvement.
- **No baselines** (random, popularity) anywhere.
- **Stale outputs**: the evaluation code sets `K = 5` but the printed result says "@10"; the GRU notebook has no saved results.

**Data pipeline**

- **History gutted** (`1. Sampling.ipynb`, `2. Data Preprocessing.ipynb`): the catalogue is cut to products in the downsampled candidate lists, then history items outside it are deleted. Mean history drops from 153.4 to 65.7 actions; 4,515 users end up with none. Engaged candidates are always kept but only a few ignored ones are, so a user's history mostly retains products they later engaged with: label-dependent filtering of inputs.
- **Time gaps corrupted**: the history filter zips the time list (one element longer) with the other lists, silently dropping the final gap from the last action to the search. `3. Merged Feature Engineering.ipynb` then drops another element, assuming it is that gap, and the time-decay feature drops the most recent action type. **This removes the gap to the search, one of the context signals in section 6.**
- **Positive-first list order** is kept and never shuffled, so tied scores can sort by label.

**Model**

- **No query input** in any model.
- **Per-user features only**: all 15 meta features are constant within a list, so they cannot rank candidates; the KMeans cluster ID is standardised as if numeric.
- **Wrong product lookup** (3.1): candidate indices come from a history-only vocabulary built from Python `set` order, but index a candidate encoder built with a different vocabulary (`Models/2. Candidate Embedding.ipynb`). Candidates get other products' brand, shop and category; candidates absent from history share index 0 (padding). The "pretrained" candidate encoder was never trained.

**Splits**

- **Row-level split** (3.2): `train_test_split` on flattened (user, candidate) rows puts one user's candidates in train, validation and test.
- **Scaler and KMeans fitted on all users** before the split (minor).

## 6. Promising lead: history's value depends on search context

**Lead** (from a quick untrained check, not yet a central claim). The value of a shopper's history may depend on whether the search continues an ongoing shopping session. Mid-session, history (especially recent and query-related history) should strongly shape the ranking; for a shopper returning after days, ranking should rely more on query relevance and popularity. This sharpens our business question ("how much should past behaviour shape search?") without changing the task or target.

**Evidence** (`notebooks/exploration/session_context_check.ipynb`; gain = NDCG@10 minus random):

| Time since last action | Searches | Same product | Same shop | Same brand | Query-title Jaccard |
|---|---:|---:|---:|---:|---:|
| Under 10 minutes | 1,940 (39.3%) | 0.181 | 0.141 | 0.069 | 0.013 |
| 10 minutes to 6 hours | 527 | 0.079 | 0.091 | 0.039 | 0.013 |
| 6 hours to 7 days | 1,868 | 0.046 | 0.056 | 0.016 | 0.013 |
| Over 7 days | 606 | 0.025 | 0.029 | 0.012 | 0.022 |

- Same-shop gain, within 10 minutes minus later: **0.084 [0.072, 0.096]**.
- **Past-query overlap is a second, separate moderator**: same-product gain 0.160 when a past query shares a term with the current one, 0.058 otherwise. It holds within recency groups: 0.208 (recent and overlapping), 0.142 (recent only), 0.096 (overlapping only), 0.028 (neither). Supports weighting history by query relevance rather than filtering.
- **Not supported**: personalising "ambiguous" queries more. Longer queries benefit slightly more (same product 0.121 for 4+ terms vs 0.096 for 1 term), and category diversity of the list barely matters (0.103 vs 0.095).
- Longer histories give larger gains (same product 0.128 above 300 actions vs 0.086 up to 30).

**Why it suits the project**

- Uses the prof's hints: relative time only (#1), active vs passive intent (#4), repeated queries within a session (#6), text relevance as the non-personal component (#7), category depth (#8). See `docs/dataset-specific-insights.md`.
- Rubric: session features from time gaps (aspect 1); Team 3 drops exactly the gap to the search (aspect 2); a model combining relevance, short-term and long-term history with a learned context-dependent weighting (aspect 3, temporal dynamics); learned weights and segment-level NDCG as diagnostics (aspect 4).
- Business insight: personalise aggressively mid-session; fall back to relevance for returning shoppers.

**Caveats and checks owed**

- Untrained single-signal rankings on a 4,941-search sample; segments are correlated, effects are not causal.
- Confirm that history strictly precedes the search (no leakage from the final search's own interactions).
- Exclude exact re-finds of products interacted with minutes earlier and check that shop/brand gains remain.
- Rerun on a larger sample; test the interaction inside trained models (a tree ranker with time-since-last-action may capture it without a custom architecture, in which case the contribution is the analysis).
- Not new in the literature (short- vs long-term interest; adaptive personalisation such as ZAM); claim evidence and interpretability on real search data, not novelty of the idea.

## 7. Parked ideas

- **Repurchase vs "already bought"**: category-dependent effect of a past purchase (consumables vs durables). Crisp insight, but exact repeats cover only 0.79% of candidates and follows (FLW) are 0.09% of history. Good side analysis.
- **Better text relevance**: BM25 and term-ID embeddings learned from titles and queries. Necessary relevance component; every group will build it; lexical gains are modest here.
- **Purchase-oriented or multi-objective ranking**: strong business story, but only 20,836 purchases (11.7% of searches) and a target shift after the interim is penalised.
- **Evaluation integrity**: quantify how downsampling, file-order ties and wrong ranking scores inflate metrics. Supporting material for the baseline section.
