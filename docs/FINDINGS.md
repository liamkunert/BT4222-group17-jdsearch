# Findings from data exploration

What our exploration established, and what each result means for the pipeline. This file replaces the interim-stage notes (`QUERY_VALIDATION.md`, `HISTORY_MATCH_VALIDATION.md`, `NOTEBOOK_STATUS.md`). The evidence lives in executed notebooks:

| Evidence | Notebook |
|---|---|
| Full-data summaries, feature dictionary, statistics | `notebooks/01_data_understanding.ipynb` |
| Query tokens, query-title overlap, current/past query overlap | `notebooks/exploration/query_signal_validation.ipynb` |
| Product/brand/shop/category history matches, query-less history | `notebooks/exploration/history_match_validation.ipynb` |
| How search context changes the value of history (section 6) | `notebooks/exploration/session_context_check.ipynb` |
| Interim report Figure 5 | `scripts/signal_check_figure.py` |
| Action types by days before the search (section 7) | `notebooks/exploration/history_timeline.ipynb` |
| Signals by window and type, context lead re-check, leakage and re-finds (sections 6-7) | `notebooks/exploration/window_recheck.ipynb` |
| First team EDA (superseded, kept for reference) | `notebooks/exploration/early_eda.ipynb` |

Last updated 25 October 2026 (section 7 added after the interim feedback; section 6 revised by the window re-check; wording in sections 5-7 tightened after an independent review, E06; section 8 revised with feature set v2, E08).

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
- **Per-user features only**: all 15 meta features are constant within a list, so on their own or added linearly they cannot separate candidates; they could only matter through interactions with candidate features, which depends on the architecture. The KMeans cluster ID is standardised as if numeric. (Their stronger flaws are the ranking score, downsampled lists, the lookup error and label-dependent history filtering.)
- **Wrong product lookup** (3.1): candidate indices come from a history-only vocabulary built from Python `set` order, but index a candidate encoder built with a different vocabulary (`Models/2. Candidate Embedding.ipynb`). Candidates get other products' brand, shop and category; candidates absent from history share index 0 (padding). The "pretrained" candidate encoder was never trained.

**Splits**

- **Row-level split** (3.2): `train_test_split` on flattened (user, candidate) rows puts one user's candidates in train, validation and test.
- **Scaler and KMeans fitted on all users** before the split (minor).

## 6. Promising lead: history's value depends on search context (revised 23 Oct)

> **Revised by the window re-check (E04, section 7.1; wording tightened after E06):** a large part of the gradient below disappears when fresh evidence is removed: without clicks it shrinks by about 70%, and for history older than 7 days the difference in total gain is at most about 0.007 (vs 0.126 pooled). This does **not** show that session context is irrelevant: the near-equal total gain of old history combines higher coverage with lower conditional gain for recently active shoppers, and context could still decide which fresh evidence matters. Whether context features add value beyond window-aligned evidence will be tested in trained models (with vs without time since last action and its interactions). The past-query-overlap moderator below has not been re-checked yet.

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
- ~~Confirm that history strictly precedes the search~~: no sign of leakage (E05a, section 7.1).
- ~~Exclude exact re-finds and check that shop/brand gains remain~~: they remain (E05b, section 7.1).
- ~~Rerun on a larger sample~~: done on 19,733 training searches (E04), with the revision above; test the interaction inside trained models (a tree ranker with time-since-last-action may capture it without a custom architecture, in which case the contribution is the analysis).
- Not new in the literature (short- vs long-term interest; adaptive personalisation such as ZAM); claim evidence and interpretability on real search data, not novelty of the idea.

## 7. History has action-specific observation windows (post-interim)

Prompted by the interim feedback (clicks should outnumber carts 5-10:1 and carts outnumber orders 3-5:1, yet history shows the reverse). Evidence: `notebooks/exploration/history_timeline.ipynb` on the full data (26,667,260 actions), experiment E01 in [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md). Elapsed days = sum of all gaps after an action, including the final gap to the search.

| Action type | Actions | Recorded up to | Window |
|---|---:|---:|---|
| CLICK | 8,298,894 | 7 days (107 stragglers up to day 13) | short |
| CART | 11,526,504 | 90 days (1,204 stragglers beyond) | medium |
| FLW | 24,579 | 90 days | medium |
| ORD | 6,817,283 | 365 days | long |

| Window before search | Clicks | Carts | Orders | Clicks per cart | Carts per order |
|---|---:|---:|---:|---:|---:|
| 0-7 days | 8,298,787 | 1,335,157 | 202,822 | 6.2 | 6.6 |
| 7-90 days | 107 | 10,190,143 | 1,833,103 | – | 5.6 |
| 90-365 days | 0 | 1,203 | 4,781,358 | – | – |

What this means:

1. **The inverted funnel is an artefact of the published data's observation windows.** Hard, type-specific cutoffs at 7, 90 and 365 days point to a technical selection (export filter, source systems or retention); the paper only describes one year of history, so the exact mechanism is unknown. Inside the 7-day window where all types are observed, the event ratios are plausible (about 6 clicks per cart, 6-7 carts per order); these are event counts, not a validated conversion funnel. The interim statement "carts outnumber clicks in history" (action mix 43/31/26) describes the observation windows, not behaviour.
2. **Action type and age are confounded.** A click is always recent; an order is usually old. Any feature or model weight "per action type" also encodes age, and any recency feature also encodes type mix. Compare types only within a shared window.
3. **"No clicks" mostly means "no activity in the last 7 days"**, not "a user who doesn't click": 28,184 records (16.2%) have no click at all; 71.6% of them had no action of any type in the last 7 days, the rest only carts or orders.
4. **Re-check results that pooled the windows.** The context lead in section 6 (history helps more shortly after the last action): searches with more than 7 days since the last action have no clicks by construction, so part of the gradient may be the visible action types, not recency itself. Also affected: history-length effects, the query-less share (28% of clicks vs 51% of orders are search-linked), and same-product matches (a 7-day click is a re-find, a 6-month order is a repurchase).
5. **Feature engineering follows the windows:** a short-term block (0-7 days, all types and recent queries), a medium-term block (7-90 days, carts, follows **and orders**) and a long-term block (90-365 days, orders only), each with its own match features and recency measured from the search. Missing old clicks are **unobserved**, not "no interest"; the data cannot say how useful clicks older than 7 days would be.
6. **Minor:** carts dip around day 64 before the search (possible logging gap); orders show spikes (likely sales events). Not yet investigated.

### 7.1 Re-check under the windows (E03-E05)

Evidence: `notebooks/exploration/window_recheck.ipynb`, 19,733 searches with an engaged candidate from the training dev subsample (validation and test labels not used). Gain = single-signal NDCG@10 minus random, exact under random ties; untrained associations that guide hypotheses, not feature weights. "Gain where it varies" averages over **different subsets of searches** per block (for example 0-7 d orders vary for only ~190 searches), so rows are not a like-for-like comparison of evidence quality.

**E03: signal by window and type** (gain where the signal varies within the list; coverage = share of searches where it varies)

| History block | Coverage (shop) | Same product | Same shop | Same brand | Same L3 path |
|---|---:|---:|---:|---:|---:|
| 0-7 d CLICK | 33% | 0.324 | 0.186 | 0.070 | 0.031 |
| 0-7 d CART | 19% | 0.251 | 0.169 | 0.064 | 0.031 |
| 0-7 d ORD | 3% | 0.273 | 0.140 | 0.052 | 0.019 |
| 7-90 d CART | 25% | 0.253 | 0.137 | 0.032 | 0.019 |
| 7-90 d ORD | 9% | 0.265 | 0.125 | 0.042 | 0.008 |
| 90-365 d ORD | 12% | 0.236 | 0.111 | 0.038 | 0.003 |

1. **Recent clicks alone reach about 70% of the pooled-history gain** over all searches (0.068 vs 0.093 product; 0.062 vs 0.088 shop). This is a stand-alone comparison, not a decomposition: rankings do not add up signals.
2. **Type at fixed age:** within 0-7 days, click-based rankings are not weaker than cart- or order-based ones where they apply. Because the subsets differ (and clicks are younger on average), this does not prove equal quality per action; a paired comparison on searches with both signals would be needed.
3. **Age at fixed type:** broad evidence is weaker in older blocks (brand from carts 0.064 to 0.032; L3 path from orders 0.019 to 0.003), exact-product evidence much less so (orders 0.27 / 0.27 / 0.24). Ageing is still mixed with selection (old exact matches may pick out persistent interests or repurchased products).

**E04: context lead with types held fixed** (same-product gain, last action under 10 minutes minus 6 hours to 7 days before the search)

| History used | Difference [95% interval] |
|---|---:|
| Pooled (interim replication) | 0.126 [0.118, 0.135] |
| No clicks | 0.038 [0.032, 0.044] |
| Carts and orders older than 7 days | 0.002 [-0.003, 0.007] |

Same pattern for shop (0.080 / 0.030 / -0.004) and brand (0.043 / 0.017 / -0.001). **A large part of the recency difference disappears when fresh evidence is removed; an additional value of context features is untested.** The near-zero difference for old history hides offsetting parts (E06 recomputation): recently active shoppers have more old evidence (variation in 11.4% vs 9.2% of searches for product) but lower conditional gain (0.238 vs 0.274). Shoppers inactive 7+ days gain less mainly because they have far less old history (27 vs 93-107 old actions on average).

**E05: leakage and re-finds**

- **No sign of leakage, but no proof either:** engaged candidates appear in history far more often than ignored ones (9.4% vs 0.6%; latest action within 10 minutes 3.9% vs 0.2%), yet only 0.7% of those recent actions carry the current query (1.45% among those with a known query; 0.83% if any action within 10 minutes counts, E06). The query check is weak because about half of these actions have no query. The strongest evidence is the dataset description (history before the last search). Robustness check for the models: retrain and evaluate with history from at least 1 minute, 10 minutes and 1 hour before the search.
- **Shop and brand evidence from other products helps:** matches on other products of the same shop keep 60% of the shop gain (0.052 of 0.088 over all searches), brand 40% (0.014 of 0.035). This does not yet show that the gain comes from personally unknown or cold candidates; check in model diagnostics with coldness defined on training data only.

**Consequences for `03_features`:** match features per (window, type, level) instead of pooled counts; age information for broad matches (brand, shop, category); exact-product and other-product matches as separate features; keep time since last action as a context feature. Which features matter is decided by retrained group ablations, not by these single-signal rankings.

## 8. Popularity is the strongest single signal (feature sets v1-v2, E07-E08)

Evidence: `notebooks/03_features.ipynb` (v2), single-feature rankings on 40,000 **training** searches. Label-free popularity counts exclude the search's own list and history; the engagement rate is out-of-fold. All searches are from the same day, so popularity uses other users' outcomes from that day (a deployed system would not have them): the non-personalised reference is optimistic, and personalisation gains measured on top of it are conservative.

| Signal | NDCG@10 | Gain over random |
|---|---:|---:|
| History popularity (how often the product is in training users' histories) | 0.339 | +0.256 |
| Training exposures (how often the product was shown) | 0.315 | +0.231 |
| Smoothed training engagement rate | 0.252 | +0.168 |
| Pooled history, same product | 0.178 | +0.094 |
| Recent clicks (0-7 d), same product | 0.152 | +0.069 |
| Query-title Jaccard | 0.097 | +0.014 |
| BM25 | 0.091 | +0.008 |

1. **A strong non-personalised reference is essential.** Personal history must be judged by what it adds on top of popularity and relevance (a trained G0-G2 ranker), not against random order. Confirmed on validation (E09): history popularity 0.341, exposures 0.315, best personal single signal 0.182, BM25 0.093, random 0.085. Popularity helps equally with and without recent activity; personal history mainly with recent activity (+0.107 vs +0.027 over random).
2. **The signal is mostly a cross-query property of the product.** Only 12% of the exposure mass comes from training searches with the identical query; exposures from other queries alone reach 0.309, from identical queries alone 0.178. The independent review found term-disjoint queries alone still reach 0.262. It is stronger for queries that recur in training (0.359 vs random 0.062) than for unseen ones (0.282 vs 0.099). Our earlier explanation ("products JD ranks highly for common queries") is therefore not supported.
3. **Position bias cannot be tested with this data:** display positions are not released, and file order among non-engaged candidates carries no usable rank information (Spearman with exposures -0.02, E08 review). Product appeal, retrieval selection, availability and position effects cannot be separated.
4. **Lexical relevance features add little** as single signals (as in FINDINGS 4.5). That JD's retrieval already returns lexically relevant products is a plausible explanation, not a tested one.

## 9. Parked ideas

- **Repurchase vs "already bought"**: category-dependent effect of a past purchase (consumables vs durables). Crisp insight, but exact repeats cover only 0.79% of candidates and follows (FLW) are 0.09% of history. Good side analysis.
- **Better text relevance**: BM25 and term-ID embeddings learned from titles and queries. Necessary relevance component; every group will build it; lexical gains are modest here.
- **Purchase-oriented or multi-objective ranking**: strong business story, but only 20,836 purchases (11.7% of searches) and a target shift after the interim is penalised.
- **Evaluation integrity**: quantify how downsampling, file-order ties and wrong ranking scores inflate metrics. Supporting material for the baseline section.
