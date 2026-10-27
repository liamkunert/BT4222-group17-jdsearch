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

Last updated 25 October 2026 (section 7 added after the interim feedback; section 6 revised by the window re-check; wording in sections 5-7 tightened after an independent review, E06; section 8 revised with feature set v2, E08); section 11 (trained rankers) added 27 October 2026, E14.

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
| History under the current query was removed by the publishers (E12) | Exactly 1 of 26.7M history actions carries the current query string, although 43% of training queries recur across users; same distinct term set in 610 records (0.35%) | Query-overlap features measure overlap with *other* queries only; same-query history is unobservable, not rare behaviour |
| Final gap clamped to 1 s in 5.3% of records (E12) | The gap from the last action to the search is never 0 s but exactly 1 s in 9,241 records (2 s: 110); in these, the last product is in the list 30% of the time and then engaged 74% of the time | Most likely post-search actions in the history (label leak). Flag `final_gap_clamped` in the search table; exclude from training; main evaluation on the remaining searches, all searches as sensitivity |
| Candidate lists are result pages (E12) | Same-query lists share a head (products in >50% of lists) and a relevant tail; engaged products sit mostly in the head; lengths cluster at multiples of 30 (90 most common, cap 200) and grow with the number of engagements | List length reflects scrolling after the query: not a feature, only a segment. Popularity partly proxies JD's own ranking |
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
- **Downsampled lists** (`Data Preparation/1. Sampling.ipynb`): all positives plus 4 negatives per positive, so lists average 9.3 candidates and 81% have 10 or fewer. Applying their sampling to the full data (171,728 searches, 20 random orderings each, their NDCG formula with gains 2^label - 1): random order scores **HR@10 0.992 and NDCG@10 0.533**, against their reported **0.978 and 0.568**. On complete lists, random NDCG@10 with the same formula is 0.083. Reproduced on our validation searches in `notebooks/04_baselines.ipynb` (E10): random 0.532 / 0.992; on their protocol a one-line same-product rule reaches 0.585 and history popularity 0.742, both above their model. The gain formula barely matters; downsampling causes the inflation.
- **Class collapse**: the unweighted model predicts class 0 for 98.74% of test candidates (accuracy 0.8015 = the share of class 0 after downsampling); the weighted model reaches accuracy 0.5117, macro F1 0.289; the ordinal model predicts class 1 for 89.84% (accuracy 0.1825) and is described as an improvement.
- **No baselines** (random, popularity) anywhere.
- **Stale outputs**: the evaluation code sets `K = 5` but the printed result says "@10"; the GRU notebook has no saved results.

**Data pipeline**

- **History gutted** (`1. Sampling.ipynb`, `2. Data Preprocessing.ipynb`): the catalogue is cut to products in the downsampled candidate lists, then history items outside it are deleted. Mean history drops from 153.4 to 65.7 actions; 4,515 users end up with none. Engaged candidates are always kept but only a few ignored ones are, so a user's history mostly retains products they later engaged with: label-dependent filtering of inputs. Combined with the wrong product lookup this becomes a direct label leak (E11 data check): candidates that receive an index through their history vocabulary are engaged 8.9% of the time vs 1.1% without one, and the cut includes the test users' own lists.
- **Time gaps corrupted**: the history filter zips the time list (one element longer) with the other lists, silently dropping the final gap from the last action to the search. `3. Merged Feature Engineering.ipynb` then drops another element, assuming it is that gap, and the time-decay feature drops the most recent action type. **This removes the gap to the search, one of the context signals in section 6.**
- **Positive-first list order** is kept and never shuffled, so tied scores can sort by label.

**Model**

- **No query input** in any model.
- **Per-user features only**: all 15 meta features are constant within a list, so on their own or added linearly they cannot separate candidates; they could only matter through interactions with candidate features, which depends on the architecture. The KMeans cluster ID is standardised as if numeric. (Their stronger flaws are the ranking score, downsampled lists, the lookup error and label-dependent history filtering.)
- **Wrong product lookup** (3.1): candidate indices come from a history-only vocabulary built from Python `set` order, but index a candidate encoder built with a different vocabulary (`Models/2. Candidate Embedding.ipynb`). Candidates get other products' brand, shop and category; candidates absent from history share index 0 (padding). The "pretrained" candidate encoder was never trained.

**Correction ladder (E11, `notebooks/04c_team3_ladder.ipynb`)**: their model re-implemented and corrected one flaw at a time, evaluated on our protocol (19,772 validation searches; random 0.084, history popularity alone 0.341).

| Rung | NDCG@10 | Step |
|---|---:|---:|
| R0 as published | 0.151 | |
| R0b label leak removed | 0.112 | -0.039 |
| R1 correct candidate lookup | 0.156 | +0.043 |
| R2 rank by expected label | 0.141 | -0.015 |
| R3 unfiltered history (latest 200 actions) and time gaps | 0.143 | +0.002 (n.s.) |
| R4 train on complete lists | 0.148 | +0.005 |
| R5 add relevance and popularity | 0.297 | +0.149 |

- The rebuild reproduces their reported HR@10 (0.980 vs 0.978) and scores below random order on their own protocol (NDCG@10 0.519 vs 0.532).
- More than half of R0's gain over random is the label leak.
- Code and design fixes add little on this architecture (+0.035 from R0b to R4).
- Even with our relevance and popularity features the model stays below sorting by popularity alone (-0.044 [-0.048, -0.041]).
- One seed; small steps (R3, R4) are within typical seed variance.

**Splits**

- **Row-level split** (3.2): `train_test_split` on flattened (user, candidate) rows puts one user's candidates in train, validation and test.
- **Scaler and KMeans fitted on all users** before the split (minor).

## 6. Promising lead: history's value depends on search context (revised 23 Oct)

> **Revised by the window re-check (E04, section 7.1; wording tightened after E06):** a large part of the gradient below disappears when fresh evidence is removed: without clicks it shrinks by about 70%, and for history older than 7 days the difference in total gain is at most about 0.007 (vs 0.126 pooled). This does **not** show that session context is irrelevant: the near-equal total gain of old history combines higher coverage with lower conditional gain for recently active shoppers, and context could still decide which fresh evidence matters. Whether context features add value beyond window-aligned evidence will be tested in trained models (with vs without time since last action and its interactions). The past-query-overlap moderator below has not been re-checked yet; it can only reflect *other* past queries, because history under the current query was removed by the publishers (E12). **E13:** without the 5% of searches with a clamped final gap (post-search actions in the history), the pooled same-product difference shrinks further from 0.126 to 0.077 [0.069, 0.084]; for history older than 7 days it stays at about 0.

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

**E13 (searches with a clamped 1-second final gap removed, 18,813 of 19,733):** these 4.7% of searches carried 26% of the pooled same-product gain and 34% of the recent-click same-product gain, but only 7% of the shop-via-other-products gain and 5% of the gain from history older than 7 days. Clean values: pooled same product 0.071 (was 0.093), recent clicks 0.047 (was 0.068), shop via other products 0.051. The E04 difference for same product shrinks to 0.077 [0.069, 0.084] (was 0.126); without clicks 0.020 (was 0.038); older than 7 days about 0. Fresh exact-product matches are partly leakage; broad and older evidence is not affected.

**E05: leakage and re-finds**

- **No sign of leakage, but no proof either:** engaged candidates appear in history far more often than ignored ones (9.4% vs 0.6%; latest action within 10 minutes 3.9% vs 0.2%), yet only 0.7% of those recent actions carry the current query (1.45% among those with a known query; 0.83% if any action within 10 minutes counts, E06). The query check is weak because about half of these actions have no query. The strongest evidence is the dataset description (history before the last search). Robustness check for the models: retrain and evaluate with history from at least 1 minute, 10 minutes and 1 hour before the search.
- **Shop and brand evidence from other products helps:** matches on other products of the same shop keep 60% of the shop gain (0.052 of 0.088 over all searches), brand 40% (0.014 of 0.035). This does not yet show that the gain comes from personally unknown or cold candidates; check in model diagnostics with coldness defined on training data only.

**Consequences for `03_features`:** match features per (window, type, level) instead of pooled counts; age information for broad matches (brand, shop, category); exact-product and other-product matches as separate features; keep time since last action as a context feature. Which features matter is decided by retrained group ablations, not by these single-signal rankings.

## 8. Popularity is the strongest single signal (feature sets v1-v2, E07-E08)

Evidence: `notebooks/03_features.ipynb` (v2), single-feature rankings on 40,000 **training** searches. Label-free popularity counts exclude the search's own list and history; the engagement rate is out-of-fold. Exposure counts and engagement rates use other users' same-day target searches, so chronological availability is not established. History popularity instead counts earlier historical events, some potentially from that day. E12 independently reconstructed the validation features: restricting historical events to more than 24 hours before each donor search changes NDCG from 0.340944 to 0.336950, retaining 98.44% of the gain over random. This bounds the timing sensitivity of history popularity, not the full pipeline. An optimistic base does not guarantee conservative personalization gains; compare the model increments empirically. See [DATA_GENERATION_AUDIT.md](DATA_GENERATION_AUDIT.md).

| Signal | NDCG@10 | Gain over random |
|---|---:|---:|
| History popularity (how often the product is in training users' histories) | 0.339 | +0.256 |
| Training exposures (how often the product was shown) | 0.315 | +0.231 |
| Smoothed training engagement rate | 0.252 | +0.168 |
| Pooled history, same product | 0.178 | +0.094 |
| Recent clicks (0-7 d), same product | 0.152 | +0.069 |
| Query-title Jaccard | 0.097 | +0.014 |
| BM25 | 0.091 | +0.008 |

0. **Clean validation population (E13, clamped searches removed):** history popularity 0.341, lagged by one day 0.337 (the deployable reference), exposures 0.315; same product in all history 0.159 (0.182 on all searches), recent clicks 0.133. On the 928 clamped searches the same-product rule reaches 0.640.
1. **A strong non-personalised reference is essential.** Personal history must be judged by what it adds on top of popularity and relevance (a trained G0-G2 ranker), not against random order. Confirmed on validation (E09): history popularity 0.341, exposures 0.315, best personal single signal 0.182, BM25 0.093, random 0.085. Popularity helps equally with and without recent activity; personal history mainly with recent activity (+0.107 vs +0.027 over random).
2. **The signal is mostly a cross-query property of the product.** Only 12% of the exposure mass comes from training searches with the identical query; exposures from other queries alone reach 0.309, from identical queries alone 0.178. The independent review found term-disjoint queries alone still reach 0.262. It is stronger for queries that recur in training (0.359 vs random 0.062) than for unseen ones (0.282 vs 0.099). Our earlier explanation ("products JD ranks highly for common queries") is therefore not supported. **E12:** within identical queries, engaged products sit mostly in the shared head of the lists (an engaged product of one user appears in another user's list 52.7% of the time, a non-engaged one 17.2%), and popularity is much weaker in long, deep-scroll lists. Popularity is therefore best described as **prior production prominence** (partly JD's own ranking and exposure), not product appeal. Deployable version: history popularity from actions at least one day old reaches 0.337 (vs 0.341), at least seven days 0.324; exposures cannot be lagged (all lists are from one day).
3. **Position bias cannot be tested with this data:** display positions are not released, and file order among non-engaged candidates carries no usable rank information (Spearman with exposures -0.02, E08 review). Product appeal, retrieval selection, availability and position effects cannot be separated.
4. **Lexical relevance features add little** as single signals (as in FINDINGS 4.5). That JD's retrieval already returns lexically relevant products is a plausible explanation, not a tested one.

## 9. Parked ideas

- **Repurchase vs "already bought"**: category-dependent effect of a past purchase (consumables vs durables). Crisp insight, but exact repeats cover only 0.79% of candidates and follows (FLW) are 0.09% of history. Good side analysis.
- **Better text relevance**: BM25 and term-ID embeddings learned from titles and queries. Necessary relevance component; every group will build it; lexical gains are modest here.
- **Purchase-oriented or multi-objective ranking**: strong business story, but only 20,836 purchases (11.7% of searches) and a target shift after the interim is penalised.
- **Evaluation integrity**: quantify how downsampling, file-order ties and wrong ranking scores inflate metrics. Supporting material for the baseline section.

## 10. Independent data-generation audits (E12)

Two independent audits (26 Oct): a Claude subagent working on training labels only (scratch scripts, findings verified in the repository where stated), and an external LLM working on training and validation records (no test labels), whose report, notebook and tables are in the repository. Both are summarised here; corrections follow in E13.

**Subagent (training records); the two artefacts below were re-verified on all 173,831 records:**
- **Clamped final gap (label leak):** never 0 s, exactly 1 s in 9,241 records (5.3%; 2 s: 110). Last product in the list 30% of the time, then engaged 74%; a query-less order of exactly the purchased product within seconds occurs 114 times for purchased candidates vs 81 times among 11.7M non-engaged. These 4.6% of searches carried about 27% of the same-product gain. Handling: section 2.
- **History under the current query removed:** 1 of 26.7M history actions carries the current query string, although 43% of training queries recur across users.
- **Candidate lists are result pages:** same-query lists share a head and a relevant tail; engaged products sit mostly in the head; lengths at multiples of 30 (90: 15%; 30, 60, 200: 3% each) and longer with more engagements (Spearman 0.38). `n_candidates` forms after the query.
- **Popularity is deployable and not a re-find effect:** lag 1 day 0.336, 7 days 0.324 (training rows); without a personal match still +0.262; ranking own matches first, then popularity: 0.386. Weak in long lists (95-150 candidates: +0.129 vs +0.312 for 85-95).
- **Purchases are mostly not checkout:** only 7.1% of searches with a purchase bought from the user's own cart history.
- **Logging outage and sales days:** carts fall to 7% on day 65 before the search (13 Aug 2022); order spikes on 18 Jun 2022 (618), 1 Jun 2022, 11 Nov 2021 (Double 11), 1 Nov 2021 and 12 Dec 2021. Windows are calendar-aligned. No duplicate users.

**External LLM:** evidence and limits in [DATA_GENERATION_AUDIT.md](DATA_GENERATION_AUDIT.md); reproducible `notebooks/exploration/data_generation_audit.ipynb`; compact tables in `docs/audit_e12/`. No model training or held-out test-label analysis.

- Parsed 133,831 training and 20,000 validation records. No candidate duplicates, misaligned fields, negative gaps or nonzero initial gap placeholders. All released lists put positives first. Validation IDs, labels, exact-product counts and three population features reconstruct with zero discrepancies at stored precision.
- Recounting history popularity by distinct training users gives 0.340800 versus event count 0.340944; no material overall difference detected. Its dominance is not explained by repeat events or the youngest historical events.
- Removing personal history younger than ten minutes lowers exact-product single-signal NDCG from 0.181985 to 0.146744 (paired 95% difference interval [-0.037546, -0.033056]). This is dependence on fresh evidence, not proof of leakage; full-model retraining remains untested.
- Within-search pairs with exactly equal historical popularity retain discrimination from exact-product history, shop-other, brand-other and lexical overlap. This supports testing them in a ranker; it does not establish an incremental NDCG gain over a trained base.
- In a fixed 300-search sample, old-order metadata is missing in 10.65% of events (90+ days), versus 0.29% of recent orders (0-7 days). Age-dependent observability can contribute to weaker broad matches; metadata-coverage features and denominators deserve attention. Six independently reconstructed features have zero mismatches across 27,540 sampled candidates.
- E11's persisted per-search means and references reconcile. The 'full' sequence still uses the latest 200 events (23.63% of validation histories truncated); 39.15% candidate coverage is against the 40k development lists, versus 56.10% against full training lists. Checkpoints are selected by weighted classification loss, not NDCG.
- Candidate structure and lexical conditioning oppose a simple arbitrary-catalogue-negative explanation, but do not reveal pagination, the 200-item cap rule, or position bias. C1/C2 removal tests explicit context features, with context proxies still present elsewhere.

## 11. Trained rankers (05_models)

Evidence: `notebooks/05_models.ipynb`, results in `docs/experiment_results.csv`. LightGBM LambdaRank with linear gains, trained on the clean dev searches (37,567; early stopping on an inner 10%), evaluated with our exact tie-aware evaluator on `validation_clean` (18,844 searches); differences are paired per search with bootstrap intervals. **These are screening results on the dev subsample;** the numbers for conclusions and the report come from the finalists retrained on all training searches (PROJECT_PLAN 5, "Final runs").

| Model | NDCG@10 | vs lagged popularity [95% interval] | Experiment |
|---|---:|---:|---|
| Random order | 0.084 | | E13 |
| Lagged history popularity (single signal) | 0.337 | | E13 |
| LambdaMART base: query length, relevance, lagged popularity (G0 + G1 + G2a) | 0.347 | +0.0096 [0.0076, 0.0114] | E14 |
| Untrained rule: own products first (history count), then lagged popularity | 0.373 | +0.036 [0.033, 0.038] | E17 |
| Full base: + same-day popularity (G2b; not deployable) | 0.366 | +0.028 (vs base +0.0185 [0.0164, 0.0206]) | E15 |
| Deployable full model: all groups except G2b (94 features) | 0.389 | +0.052 (vs base +0.042 [0.040, 0.045]) | E16 |

1. **Relevance adds about 0.01 on top of deployable popularity once a model combines them**, although BM25 alone scores only 0.093 (E09). The gain is concentrated in lists of up to 84 candidates (+0.02); in lists of more than 95 candidates the base is not distinguishable from popularity. Lagged popularity has 86% of the split gain, BM25 9%.
2. **The deployable base (0.347) is the reference for personalisation**: history features are judged by what they add to it, not to the single popularity signal.
3. **Memory is not a constraint on the dev subsample**: all 97 features with a LightGBM dataset and the validation features peak at 2.8 GB. All training searches would be about 11.3M rows (4.4 GB as float32).
4. **Same-day information is worth much more inside a model than as a single signal** (E15): lagging history popularity by a day costs 0.004 as a sort key, but the same-day signals add +0.0185 to the trained base, and the trees prefer unlagged over lagged popularity (71% vs 2% of the split gain). A deployed ranker cannot use this; the full base is an optimistic reference only.
5. **Personal history and context add about +0.04 to the deployable base** (E16), about twice as much for shoppers active in the last 7 days (+0.045 vs +0.021), and also in long lists where relevance did not help (+0.040). Pooled exact-product history takes most of the history split gain; which groups matter is left to the ablations. Clamped searches would inflate the gain to +0.058.
6. **About 70% of the personal gain is the obvious step, about 30% is learned** (E17): an untrained rule "products from the shopper's history first, then lagged popularity" reaches 0.373; the trained deployable model adds +0.016 [0.014, 0.018] beyond it, in searches without an own product among the candidates (+0.017, relevance plus shop/brand/category evidence and context) as well as in those with one (+0.013). On the clamped searches rule and model are equal (0.699 vs 0.700): their exact matches are post-search actions.
7. **More training data still helps at the dev size** (E16): 20k to 33.8k fit searches +0.0041 [0.0028, 0.0053] (10k to 20k +0.0012, n.s.; one seed, uneven steps). Final models therefore need features for all training searches.
