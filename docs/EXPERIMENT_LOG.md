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
