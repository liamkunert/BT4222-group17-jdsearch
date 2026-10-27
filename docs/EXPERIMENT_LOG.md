# Experiment log

The running record of everything we try after the interim: data checks, feature ideas, baselines and models, including the ones that fail. It feeds the final report (sections 1-3) and the presentation, so every number we quote should trace back to an entry here.

How the documentation fits together:

| File | Holds | Changes when |
|---|---|---|
| `docs/EXPERIMENT_LOG.md` (this file) | Each experiment: question, setup, result, decision | Every run worth remembering, newest at the bottom |
| `docs/FINDINGS.md` | Established facts and what they mean for the pipeline | An experiment changes what we believe |
| `PROJECT_PLAN.md` | Direction, decisions, timeline | An experiment changes what we do next |
| `AI_LOG.md` | AI-influenced decisions (report appendix) | AI materially shaped a decision |

## Rules

1. One entry per experiment, numbered `E01`, `E02`, ... in order. Never renumber or delete; mark dead ends as such.
2. Write the question and expected outcome **before** running; fill in the result and decision after.
3. Record enough to rerun it: notebook, commit, data sample and split, seed, features, model settings.
4. Model results always use the shared split and evaluation function, and report validation NDCG@10 against the current best and against random. Test-set numbers only for final models.
5. Keep entries short (about 15 lines). Tables and figures stay in the notebook; link them.
6. If the result changes a belief, update FINDINGS; if it changes the plan, update PROJECT_PLAN. Note which in the entry.

## Template

```markdown
### E00 - Short title (YYYY-MM-DD, member)

- **Question:** what we want to learn, and why it matters for the ranking
- **Expectation:** what we think will happen
- **Setup:** notebook, commit, data (sample, split, seed), features, model and settings
- **Result:** headline numbers (validation NDCG@10 vs best so far and vs random), with link to output
- **Decision:** keep / drop / follow up; FINDINGS or PLAN updated?
```

## Entries

### E01 - History timeline by action type (2026-10-19, Liam)

- **Question:** Why do carts and orders outnumber clicks in history (the interim feedback)? Convert gaps to elapsed days before the search and look at each action type over time.
- **Expectation (lecturer's hint):** clicks thin out further back in time.
- **Setup:** `notebooks/exploration/history_timeline.ipynb`, full behaviour file (173,831 records, 26,667,260 actions); outputs in `outputs/eda/history_timeline/`.
- **Result:** each type is only recorded within a fixed window: clicks 7 days, carts and follows 90 days, orders 365 days. Within 0-7 days the funnel is normal (6.2 clicks per cart, 6.6 carts per order). 16.2% of records have no click; 71.6% of these had no action at all in the last 7 days, the rest only carts or orders.
- **Correction (E06):** call these action-specific observation windows of the published data (mechanism unknown), and the 0-7 day ratios plausible event ratios, not a validated funnel.
- **Decision:** history is three censored windows, not one sequence. Build features per window; re-check the section 6 context lead and other pooled results under this lens. FINDINGS section 7 added; roadmap added to PROJECT_PLAN section 5 (20 Oct).

### E02 - Fixed split, shared evaluation and the random-order floor (2026-10-20, Liam)

- **Question:** Can every later experiment be compared on the same searches with the same metric? What NDCG@10 does random order reach on validation (the floor every model must beat)?
- **Expectation:** a uniform split gives near-identical profiles; random NDCG@10 near the interim sample's 0.081.
- **Setup:** `notebooks/02_split_and_evaluation.ipynb`; helpers `scripts/jd_data.py` and `scripts/evaluation.py`. Split `split_v1` (seed 4222): test 20,000 and validation 20,000 drawn outside the 5,000 explored records, train 133,831 with a 40,000 dev subsample; saved to `data/processed/split_v1.csv`. Metrics are exact expectations under random tie-breaking, checked against hand cases, brute force over all orderings and the interim `expected_ndcg`.
- **Result:** split profiles match (engaged share 2.07-2.09%, searches with a purchase 11.5-11.9%, activity in the last 7 days 88.2-88.4%). Validation, 19,772 searches with an engaged candidate: random order NDCG@10 **0.0845** [0.0830, 0.0860], Recall@10 0.160, MRR 0.102. Random NDCG@10 falls from 0.331 (lists up to 30 candidates) to 0.037 (151-200). Oracle Recall@10 is 0.998 because some searches have more than 10 engaged candidates.
- **Decision:** foundation in place; first row in `docs/experiment_results.csv`. Compare models with random **within** each segment, because the floor depends on list size. Note: `log_result` records the last commit, so commit code before logging final results.

### E03 - History signal by window and action type (2026-10-23, Liam)

- **Question:** Which history windows and action types carry ranking signal once type and age are separated?
- **Expectation:** orders and carts are stronger evidence than clicks; older evidence is weaker.
- **Setup:** `notebooks/exploration/window_recheck.ipynb`; 20,000 searches from the training dev subsample (seed 4222), 19,733 with an engaged candidate; single-signal rankings by matching-action counts per block (0-7 d CLICK/CART/ORD, 7-90 d CART/ORD, 90-365 d ORD) and level (product, shop, brand, L3 path); gain = NDCG@10 minus random.
- **Result:** recent clicks give ~70% of the pooled total gain (product 0.068 vs 0.093). Within 0-7 days, clicks are at least as informative per evidence as carts/orders (product 0.32 vs 0.25/0.27). Broad evidence fades with age (brand from carts 0.064 to 0.032), exact-product evidence hardly (orders 0.27 to 0.24). Expectation on type not supported.
- **Correction (E06):** "at least as informative per evidence" and "~70% of the gain" overstate: the blocks are compared on different subsets of searches (0-7 d orders vary in ~190 searches), and stand-alone gains are not a decomposition.
- **Decision:** features per (window, type, level); age-aware weighting for broad matches. FINDINGS 7.1 added.

### E04 - Context lead with action types held fixed (2026-10-23, Liam)

- **Question:** Does "history helps more right after the last action" (FINDINGS 6) survive when the visible action types are held fixed?
- **Expectation:** the gradient shrinks once clicks are removed; unclear whether it survives for old history.
- **Setup:** same notebook and sample as E03; gains by time since the last action for pooled history, history without clicks, and carts/orders older than 7 days; bootstrap intervals for (< 10 min) minus (6 h - 7 d).
- **Result:** same-product difference 0.126 [0.118, 0.135] pooled, 0.038 [0.032, 0.044] without clicks, 0.002 [-0.003, 0.007] for history older than 7 days (shop and brand alike). Shoppers inactive 7+ days gain less from old history (shop 0.022 vs 0.040-0.053), unexplained.
- **Correction (E06):** the near-zero difference for old history combines higher coverage with lower conditional gain for recently active shoppers, so it does not rule out a context effect; the 7+ day drop is mainly less history (27 vs ~100 old actions).
- **Decision:** a large part of the interim recency difference disappears without fresh evidence; whether context features add value is tested in trained models (with vs without time since last action). FINDINGS 6 revised; PROJECT_PLAN 1 and 4 updated.

### E05 - Leakage and re-find checks (2026-10-23, Liam)

- **Question:** Does history contain the current search's own interactions? Do shop/brand matches help beyond re-finding the same product?
- **Expectation:** no leakage; shop/brand keep part of their gain.
- **Setup:** same notebook and sample; for candidates seen in history: recency of the latest action and whether it carried the current query; shop/brand counts excluding the candidate's own product.
- **Result:** engaged candidates are in history far more often (9.4% vs 0.6%), but only 0.7% of recent (< 10 min) actions on them carry the current query. **Correction (E06):** this is an indication, not proof (about half have no query; 1.45% among known queries); the dataset description is the stronger evidence. Without the candidate's own product, shop keeps 60% of its gain (0.052 of 0.088), brand 40%.
- **Decision:** keep recent history; separate exact-product and other-product match features; report results with and without very recent same-product matches. FINDINGS 6 checks marked done.

### E06 - Independent review of E01-E05 (2026-10-23, Liam)

- **Question:** Do the conclusions of E01-E05 hold up under an independent critical review?
- **Expectation:** the numbers hold; some interpretations may overreach.
- **Setup:** a second LLM reviewed the repository files, recomputed saved results, checked the metrics against enumerated orderings and examined the E03-E05 sample. See AI_LOG for the interaction.
- **Result:** metrics and numbers confirmed. Overreaching interpretations: E04 does not rule out session context (old history: coverage 11.4% vs 9.2%, conditional product gain 0.238 vs 0.274 for recently active vs 6 h - 7 d; the 7+ day group has 27 vs ~100 old actions); E03 "per evidence" comparisons use different search subsets; E05 query check is weak (1.45% among known queries; 0.83% with all actions within 10 minutes). Errors found: medium block omitted 7-90 d orders; LightGBM defaults to exponential label gains; evaluation lacked completeness checks; training must not see file order.
- **Decision:** wording in FINDINGS 5-7 and E01/E03-E05 corrected; evaluation guardrails and candidate shuffling added (notebook 02, section 8); context, query overlap and repurchase become model ablations instead of further single-signal checks; `label_gain=[0,1,2,3]` required.

### E07 - Feature set v1 (2026-10-23, Liam)

- **Question:** Can we build the planned feature groups (G0-G6) reproducibly and without leakage, and do they reproduce the re-check signals?
- **Expectation:** history features reproduce E03; query-title relevance modest; popularity useful.
- **Setup:** `notebooks/03_features.ipynb`; 40,000 training (dev) and 20,000 validation searches; 68 features in 7 groups; candidates shuffled within each search; popularity from training records only, out-of-fold for training rows (5 folds by search, rescaled 5/4); BM25 with whole-catalogue statistics; outputs `data/processed/features_v1_*.parquet`.
- **Result:** all checks passed; pooled product / shop / recent-click gains on training rows 0.094 / 0.087 / 0.069 (E03: 0.093 / 0.088 / 0.068). Popularity means within 1% between splits. Strongest single signal: training exposures NDCG@10 0.311 (+0.227 over random), engagement rate +0.168; BM25 only +0.008, title Jaccard +0.014.
- **Correction (E08):** the popularity mechanism above is not supported (only 12% of exposure mass from identical queries), and the 5/4 rescaling made means match but not distributions; superseded by feature set v2.
- **Decision:** feature set v1 is the input for baselines and models. The non-personalised reference must include popularity; personalisation is measured on top of it. Open question: exposure counts may partly recover JD's own ranking (position bias); check within queries before interpreting. FINDINGS 8 added.

### E08 - Reviews of feature set v1 and feature set v2 (2026-10-25, Liam)

- **Question:** Is feature set v1 correct and leakage-free, and does it support the planned ablations?
- **Expectation:** no leakage; some design gaps.
- **Setup:** two independent reviews (Claude subagent: re-implemented 12 features on 300 searches, decomposed the popularity signal; second LLM: code and ablation design). Fixes in `notebooks/03_features.ipynb`, rebuilt as feature set v2 (90 features, 11 groups) with distribution checks (zero shares, quantiles), a permutation test and a popularity-mechanism check on training rows.
- **Result:** v1 had no leakage, but popularity counts were distributed differently for training and validation rows (zero exposures 46.6% vs 43.9%, 1.25 grid), the prior used all training labels, missing brand names gave 0 (7.35% of candidates), shuffling depended on the set of built searches, two block names hid open upper bounds, and our popularity explanation was wrong. In v2 the zero shares match (43.6% vs 43.9%), all checks pass, and the features reproduce E03/E07. Popularity: 12% of exposure mass from identical queries; other queries alone 0.309. History popularity is the strongest single signal (0.339).
- **Decision:** v2 is the input for baselines and models. Ablations are redesigned (PROJECT_PLAN 5): window question with H1 vs H2 vs H3 at equal match definitions, context question removing all context including history volume. FINDINGS 8 rewritten.

### E09 - Simple references on validation (2026-10-25, Liam)

- **Question:** How far do untrained single-signal rankings (relevance, popularity, personal history) get on validation, and how do they compare per segment?
- **Expectation:** the order of the training-row results (E07, E08): popularity first, personal history second, lexical relevance last.
- **Setup:** `notebooks/04_baselines.ipynb`, feature set v2, 19,772 validation searches with an engaged candidate; ten references fixed in advance from training-row evidence; NaN scored as 0; exact tie expectation; paired bootstrap differences; logged to `docs/experiment_results.csv` (commit 289d8e1).
- **Result:** history popularity 0.341, exposures 0.315, engagement rate 0.245, same product (all history) 0.182, recent clicks 0.155, shop via other products 0.136, query-related history 0.136, Jaccard 0.097, BM25 0.093, random 0.085. Personal history gains mainly with recent activity (+0.107 vs +0.027) and longer histories; popularity gains are the same with and without recent activity.
- **Decision:** expectation confirmed. The trained G0-G2 ranker is the reference for personalisation; next the LightGBM base model and ablations (05). Team 3's model and correction ladder still to add to 04.

### E10 - Team 3's evaluation protocol applied to known rankings (2026-10-25, Liam)

- **Question:** How much do Team 3's evaluation choices (downsampled lists, exponential gains, array-order ties) inflate NDCG, and what does their reported 0.568 mean?
- **Expectation:** random order scores far above 0.085 on their downsampled lists (the interim simulation on all data gave 0.533).
- **Setup:** `notebooks/04_baselines.ipynb` (part 1 of the Team 3 section); their sampling and their NDCG / HR functions copied verbatim; applied to our 19,772 validation searches for random order, history popularity and same-product history; 20 random tie orders per search; no model trained; nothing logged to the registry (not comparable with full lists).
- **Result:** downsampled lists average 9.4 candidates. Team 3 protocol: random NDCG@10 0.532 / HR@10 0.992, same-product history 0.585, history popularity 0.742; their model reported 0.568 / 0.978. Gain formula barely matters (random 0.532 vs 0.535 with our metric on the same lists).
- **Decision:** expectation confirmed; their reported model is +0.036 above random and below a one-line history rule on their own protocol. Part 2: re-implement their model and correct one flaw at a time on our protocol (correction ladder). FINDINGS 5 updated.

### E11 - Team 3 correction ladder (2026-10-25, Liam; run on Colab 2026-10-26)

- **Question:** How much does each of Team 3's flaws cost on our protocol? Rungs (cumulative): R0 as published; R0b their history filter built from training lists only (removes the label leak); R1 correct candidate lookup; R2 rank by expected label instead of maximum class probability; R3 full history with the gap to the search; R4 train on complete lists; R5 add our relevance and popularity features (G0-G2).
- **Expectation:** R0 looks better than it is because of the label leak; the corrections after R0b help modestly; R5 helps most, but stays near the popularity reference (0.341) because their architecture has no strong candidate-level signal.
- **Setup:** `notebooks/04b_team3_prep.ipynb` (CPU, local, about 7 minutes) writes `data/processed/team3/`; `notebooks/04c_team3_ladder.ipynb` re-implements their model (LSTM with attention, summed candidate embeddings, 15 meta features, MLP with BatchNorm, weighted cross-entropy, their optimiser settings) and trains each rung on the 40,000 training dev searches (10% inner validation for checkpointing), evaluated on all 20,000 validation searches; GPU on Colab, smoke test locally.
- **Data check before training:** their catalogue cut (sampled lists of all users: every positive, four negatives each) combined with their history-vocabulary lookup makes "the candidate has an index" a label signal: 8.9% of validation candidates with an index are engaged vs 1.1% without (cut from training lists only: 6.0% vs 1.7%; correct lookup: 3.2% vs 1.4%). Filtered histories keep 43 of 153 actions on average; 2,709 searches end up empty. Local smoke test (2,000 / 1,000 searches, one epoch) runs all rungs in about 6 minutes; its numbers are not results.
- **Result:** (Colab T4, seed 1, 19,772 validation searches) R0 0.151 (random 0.084, history popularity 0.341); on Team 3's protocol R0 gives HR@10 0.980 / NDCG@10 0.519, matching their reported 0.978 / 0.568 and below random order (0.532). R0b -0.039 [-0.043, -0.035]: more than half of R0's gain over random is the label leak. R1 lookup +0.043; R2 expected-label score -0.015; R3 full history +0.002 (n.s.); R4 complete lists +0.005; R5 relevance and popularity +0.149 to 0.297, still -0.044 [-0.048, -0.041] below popularity alone. Best epoch 2-3 in every rung. Logged as E11 rows (code commit ead2194).
- **Decision:** expectation largely confirmed, except that ranking by expected label hurt (hypothesis: class weights distort probabilities; untested). Team 3's architecture is not a viable base; our models are compared with popularity and a trained non-personalised ranker. FINDINGS 5 updated.

### E12 - Independent data-generation audits (2026-10-26, Liam)

- **Question:** Which of our findings could be artefacts of how JDsearch was built, and which assumptions should we second-guess before the final models? (Prompted by the missed observation windows, E01.)
- **Expectation:** popularity may partly reflect same-day information or list construction; something like the funnel may still be hidden.
- **Setup:** two independent audits. (a) A Claude subagent on training labels only (scratch scripts; re-verified here where stated). (b) An external LLM on training and validation records, no test labels: [DATA_GENERATION_AUDIT.md](DATA_GENERATION_AUDIT.md), `notebooks/exploration/data_generation_audit.ipynb`, `docs/audit_e12/`, 12 fixed-signal rows in the registry (commit de7e407).
- **Result:** (a) found two artefacts, both re-verified on all records: the final gap is clamped to 1 s in 5.3% of records (post-search actions in the history; these searches carry ~27% of the same-product gain), and history under the current query was removed (1 of 26.7M actions). Candidate lists are result pages whose length grows with scrolling; popularity proxies JD's production prominence; lagged history popularity is deployable (1 day: 0.336, 7 days: 0.324). (b) reconstructed all validation features and references with zero discrepancies; popularity robust to distinct-user counting (0.3408 vs 0.3409) and a 24-hour lag (0.337); exact-product history loses 36% of its gain with a 10-minute safety gap; personal and lexical signals still discriminate within equal popularity (pairwise concordance 0.538 / 0.550); missing metadata grows with history age (old orders 10.7% vs recent 0.3%, sample); E11 wording needs precision (sequence capped at 200; coverage 39% refers to dev lists). (b) did not find the clamp or the same-query removal.
- **Decision:** fixes in E13: flag and exclude clamped searches; remove `n_candidates`; add lagged history popularity and metadata coverage (feature set v3); rerun E03-E05 on clean searches; correct FINDINGS 2, 5, 6, 7.1, 8, 10 and the plan's ablation wording.

### E13 - Fixes after the data-generation audits (2026-10-26, Liam)

- **Question:** How do the audit findings (E12) change the data, the features and the reference numbers?
- **Expectation:** popularity unchanged; personal exact-product signals smaller once clamped searches are removed; the recency gradient of E04 weaker.
- **Setup:** search table flags `final_gap_clamped` (notebook 02); feature set v3 (notebook 03: `n_candidates` removed, `pop_history_lag1d`, metadata coverage per block H5; 97 features; memory-efficient build); window re-check rerun on clean searches (`exploration/window_recheck.ipynb`, E13 section); references on the clean validation population (notebook 04 section 5, logged as E13, split `validation_clean`); external audit notebook executed with outputs. Code committed first (e3c4047).
- **Result:** 9,241 clamped searches (5.3%; validation 1,063, of which 928 with an engaged candidate). Clean validation: history popularity 0.341 (unchanged), lagged by one day 0.337, exposures 0.315; same product in all history 0.159 (was 0.182), recent clicks 0.133 (was 0.155); on the clamped searches the same-product rule reaches 0.640. Training rows: clamped searches carried 26% of the pooled same-product gain and 34% of the recent-click gain, only 7% of shop-via-other-products; E04 same-product gradient 0.077 [0.069, 0.084] (was 0.126). v3 distributions match between training and validation.
- **Decision:** from now on train without clamped searches and evaluate on `validation_clean` (all searches as sensitivity); deployable non-personalised reference = lagged history popularity (0.337). Expectations confirmed.

### E14 - Memory profile and deployable LambdaMART base (2026-10-27, Liam)

- **Question:** Does a trained non-personalised ranker (G0 search + G1 relevance + G2a lagged popularity) beat sorting by lagged history popularity alone, and how much memory do the full v3 features need for the planned ablations?
- **Expectation:** a modest gain, about +0.005 to +0.02 NDCG@10 on `validation_clean`: relevance is weak alone (E09) but trees can use it among products of similar popularity. Success criterion (fixed before running): lower bound of the paired 95% interval vs lagged popularity above +0.003. If not met: check features, grouping, gains and evaluator before any ablation. Memory: the full 97 features of the dev subsample fit (about 1.4 GB as float32).
- **Setup:** `notebooks/05_models.ipynb` sections 1-2; feature set v3; training = dev searches without clamped gap, without engaged candidate and without single-candidate lists (37,567), of which 10% (seed 4222, whole searches) are an inner set for early stopping only; LightGBM 4.6.0 LambdaRank, `label_gain=[0,1,2,3]`, NDCG@10 for stopping, truncation level 20, 31 leaves, learning rate 0.05, at least 500 rows per leaf, early stopping after 100 rounds without gain, seed 1; missing values left to LightGBM (unknown, not 0); evaluation on all validation lists with our exact tie-aware evaluator, main population `validation_clean`, all searches as sensitivity. Code committed first (282a119).
- **Result:** 0.347 on `validation_clean` (18,844 searches) vs lagged popularity 0.337 and random 0.084: **+0.0096 [0.0076, 0.0114]**; all searches +0.0089 [0.0071, 0.0107]. The gain sits in lists up to 84 candidates (+0.019 / +0.024); 85-95 +0.007; over 95 +0.0015 [-0.0010, 0.0042]. Lagged popularity has 86% of the split gain, BM25 9%; 89 trees. Memory: 97 features of the training searches 1.3 GB as float32; with LightGBM dataset and validation features peak 2.8 GB; all training searches about 11.3M rows (4.4 GB). Training 16 s.
- **Decision:** expectation and success criterion met; the base (0.347) is the reference for the personalisation ablations. Full-feature ablations run on the dev subsample in memory; whether full training data is needed is left to the learning curve. Next: full base + G2b (E15). FINDINGS 11 added; PROJECT_PLAN 5 updated.

### E15 - Full base with same-day popularity (2026-10-27, Liam)

- **Question:** How much do the same-day popularity signals (G2b: exposures, out-of-fold engagement rate, unlagged history popularity; not deployable) add on top of the deployable base?
- **Expectation:** a small gain, about +0.005 to +0.01 over the base (0.347): exposures alone reach 0.315 and overlap strongly with history popularity. It is an optimistic reference, not a candidate model.
- **Setup:** `notebooks/05_models.ipynb` section 4; same population, inner early-stopping set, LightGBM configuration and evaluation as E14; features G0 + G1 + G2a + G2b (13; written as 14 before running, G2b has three features). Code committed first (85de125); E14 rerun in the same execution reproduced its numbers exactly.
- **Result:** 0.366 on `validation_clean`, **+0.0185 [0.0164, 0.0206]** over the deployable base and +0.028 over lagged popularity; all searches +0.0188. Unlagged history popularity takes 71% of the split gain, the lagged version 2%; 284 trees.
- **Decision:** gain about twice the expectation: same-day information is worth much more inside a model than the single-signal lag cost (0.341 vs 0.337) suggested. Stays a non-deployable reference; which G2b signal carries the gain is not separated (not needed for the plan). FINDINGS 11 updated.

### E16 - Learning curve of the deployable full model (2026-10-27, Liam)

- **Question:** Does the deployable full model (all v3 groups except G2b: base plus history, context, query and source features) still gain from more training searches at the size of the dev subsample? And, as a first look, how much does it add over the deployable base?
- **Expectation:** clearly above the base, about +0.02 to +0.05 (own history first, then popularity reached 0.386 on training rows before the clamped searches were removed). Small but positive gain from 20k to 33.8k fit searches, about +0.002 to +0.005. Decision rule fixed before running: if 33.8k minus 20k is above +0.003 with a paired interval excluding 0, build the features for all training searches right after the first ablations (about 30 Oct) instead of 3-5 Nov.
- **Setup:** `notebooks/05_models.ipynb` section 5; 94 features; nested random subsets of the fit searches (10,000, 20,000, all 33,810; seed 4222), the same inner set of 3,757 searches for early stopping; configuration as E14; evaluation on `validation_clean`, paired per search. Screening results on the dev subsample (PROJECT_PLAN 5, final runs). Code committed first (85de125).
- **Result:** 10k / 20k / 33.8k fit searches: 0.384 / 0.385 / **0.389**; steps +0.0012 [-0.0002, 0.0027] and **+0.0041 [0.0028, 0.0053]**; best iterations 231 / 169 / 361; largest fit 124 s, peak memory 2.8 GB. The 33.8k model vs deployable base **+0.042 [0.040, 0.045]** (all searches +0.058); active in the last 7 days +0.045 vs inactive +0.021; lists over 95 candidates +0.040. Split gain: lagged popularity 63%, pooled history 18% (exact product 16%), match recency 4%, other history and context groups about 1% each.
- **Decision:** expectations met. The decision rule is met: build v3 features for all training searches right after the first ablations (about 30 Oct), not 3-5 Nov. Uneven steps with one seed: the curve shows that more data helps, not how much. Proposed next, before the ablations: an untrained "own history first, then lagged popularity" rule on `validation_clean`, to check that the trained gain is more than a simple rule. FINDINGS 11 and PROJECT_PLAN 5 / 9 updated.
