# Group 17 — JDSearch Project Plan

Status: interim report submitted (source in `reports/interim/`). Modelling is complete: LambdaMART screening and ablations (E14-E22), full-data finalists (E23), robustness (E24), the independent reviews with their checks and corrections (E25, E26, E30) and the neural models (E27-E29, regularised attention E31). Diagnostics (06, E32) and the final independent reviews with their fixes (E33) are done. Remaining: a self-contained submission pipeline, run once end to end on Colab including the single test run, then report and slides (section 9).

Evidence and detailed results are in [docs/FINDINGS.md](docs/FINDINGS.md), every experiment in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md); this file holds direction, decisions and the remaining steps.

---

## 1. One-paragraph summary

Re-rank the products JD returned for a search using the current query, the shopper's history and candidate metadata. The business decision is **how much past behaviour should influence the current ranking, and which parts of that history to trust**. Since the interim we know that history has action-specific observation windows (clicks 7 days, carts and follows 90 days, orders 365 days; FINDINGS §7). Re-checked under those windows, a large part of the interim lead (history helps more right after the last action) disappears when fresh evidence is removed; whether session context adds value beyond fresh evidence was then tested in trained models (FINDINGS §6-7.1). **Model ablations (E18-E20, dev subsample):** four pooled history match counts carry almost the whole personal gain (+0.041 over a relevance and popularity ranker); splitting by action type or age, session context, query overlap and history source add small amounts at most, all below our +0.003 threshold. Confirmed with all training data (E23, E30: base 0.350, pooled history 0.389); item-item CF adds no robust gain (E30), neural models do not beat the trees (E27-E31). The target is the observed interaction grade (0-3), evaluated on full, un-downsampled candidate lists.

## 2. Business objective and ML task (fixed at the interim)

The guideline penalises switching dataset or redefining the target after the interim; refinements to sampling, features and supplementary data are allowed.

- **Business objective:** help shoppers find and buy suitable products sooner by using their history where it is useful evidence for the current search, without letting past favourites crowd out what the query asks for. Offline ranking quality is the measurable proxy.
- **ML task:** personalised re-ranking of each search's supplied candidate list.
- **Input sample:** one (search, candidate) pair, scored within its complete list: current query, shopper history (products, action types, past queries, time gaps) and candidate metadata (title terms, brand, four-level category, shop). All candidates of one search stay together when sampling or splitting.
- **Target:** graded label per candidate: 0 none, 1 click, 2 cart, 3 purchase, used as the NDCG gain.
- **Evaluation:** NDCG@10 on complete lists; Recall@10 as support (MRR under discussion); searches without an engaged candidate excluded; random tie-breaking, never file order. Full protocol in FINDINGS §3.

## 3. The data in plain terms

`user_behavior_data.txt` has 173,831 rows; each row is one user's last search plus their history. `product_meta_data.txt` describes 12,141,247 products. All text is anonymised term IDs.

| Column | Meaning |
|---|---|
| `query` | Term IDs of the current search |
| `candidate_wid_list` | Products JD showed (about 89 per row): the impressions |
| `candidate_label_list` | Outcome per candidate: 0 none, 1 click, 2 cart, 3 purchase |
| `history_qry_list` | Query behind each past action (`-1` = no search, e.g. a recommendation click) |
| `history_wid_list` | Product of each past action, in order |
| `history_type_list` | CLICK / CART / FLW (follow) / ORD (purchase) |
| `history_time_list` | Gaps in seconds: an initial 0, one per transition, and a final gap to the current search |

Pitfalls and rules (file order leaks labels, missing metadata, category IDs with several parents, and more) are in FINDINGS §2.

## 4. Direction and contribution

- **Table stakes: the prior baseline.** Every group has Team 3's code and will find its flaws. We reproduce and correct it under our protocol, but it is not our main contribution. Diagnosis in FINDINGS §5; note that their pipeline drops the gap to the search, one of the context signals we test.
- **Main question** (as in the interim report): which history signals improve the ranking, and does weighting history by its relevance to the query beat using all of it or filtering it?
- **How history should be weighted** (FINDINGS §6-7.1, re-checked under the windows and reviewed in E06): single-signal checks suggest the value of evidence depends on its age, type and level (broad brand/shop/category evidence weaker when old, exact-product evidence much less so). No sign of leakage (not proof); shop and brand evidence from other products helps. Tested **as model ablations** on the same split: (1) time since last action and its interactions (session context), (2) query overlap between current query and history, (3) past orders by age and category (repurchase), (4) coverage of matching history (exact product, only shop/brand, none), (5) query-linked vs query-less history. **Outcome (E18-E20, E23, E30):** none of (1), (2), (4), (5) or the type and window splits adds a practically relevant amount (all below +0.003) to pooled match counts in LambdaMART; older history does add signal (+0.012 over the last 7 days). Learned, query-conditioned weighting of individual events (the attention model, E28-E31) does not beat pooled counts either.
- **Supporting components:** query-title relevance (BM25 or term-ID embeddings), metadata features for cold candidates, full category paths, query-less history as its own source.
- **Possible side analysis:** repurchase vs "already bought" by category (FINDINGS §9).
- **Novelty framing:** query-aware and adaptive personalisation already exist (the JDsearch paper benchmarks such models). Our contribution is a corrected evaluation of the prior baseline plus controlled, interpretable evidence on when and how strongly history should shape search.

## 5. Roadmap

Pipeline notebooks continue the numbering in `notebooks/`. Each step ends with entries in the experiment log; steps are revisited as results come in.

0. **`02_split_and_evaluation` (foundation):** one fixed split by whole search record, the shared evaluation function (`scripts/evaluation.py`: NDCG@10, Recall@10, MRR, exact under random ties, by segment) and the results registry (`docs/experiment_results.csv`). Every later result uses both.
1. **Re-checks under the window lens** (done, `exploration/window_recheck.ipynb`, E03-E05; reviewed in E06): history-match signals by action type and window; the context lead with action types held fixed (largely explained by fresh evidence; context value open); leakage indications and re-find checks.
2. **`03_features`** (v1 E07; v2 E08 after two reviews; **v3 E13** after the data-generation audits: `n_candidates` removed because list length forms after the query, deployable lagged history popularity, metadata coverage per block): groups G0 search (query length), G1 relevance (BM25, title overlap), G2a deployable popularity (history actions at least one day old), G2b same-day popularity (exposures, unlagged history, out-of-fold engagement rate; training only, label-free counts exclude the own search), H5 metadata coverage per block, H1 pooled history, H2 history by type, H3 history by window (0-7 d all types; 7+ d carts; 7-90 d and 90+ d orders; follows), H4 match recency, C1 history volume, C2 session context, Q1 query-history (all ages and last 7 days), S1 search-linked vs query-less history. The same four match definitions (exact product, shop and brand via other products, L3 path) in every history group. `MIN_AGE_DAYS` rebuilds the personal history and context features with a history safety gap (it does not lag the population counts; `pop_history_lag1d` covers that).
3. **`04_baselines`:** simple references (E09: history popularity 0.341 best, best personal signal 0.182, BM25 0.093, random 0.085). Team 3 part 1 (E10: on their protocol random order already scores 0.532 vs their reported 0.568). Team 3 part 2 (E11, Colab T4): R0 0.151, more than half of its gain over random is a label leak; all fixes on their architecture reach 0.148; with our relevance and popularity features 0.297, still below popularity alone (0.341). Team 3 is not a viable base. Clean population (E13): references without the clamped searches; deployable reference = lagged history popularity 0.337; same-product history 0.159 (was 0.182).
4. **`05_models`** (model choice after an external review, see AI_LOG). One model family at a time, each with a success criterion and a time box; every iteration in the experiment log. Primary benchmark: **lagged history popularity, 0.337 NDCG@10 on clean validation**; improvements below 0.003-0.005 are not treated as meaningful.
   - **a) LambdaMART (main model):** LightGBM gradient-boosted trees with the LambdaRank objective, `label_gain=[0,1,2,3]`, NDCG@10 evaluation, `lambdarank_truncation_level` around 13-20; one fixed configuration for all ablations (about 31 leaves, learning rate 0.05, sizeable minimum leaf support, early stopping), a small bounded tuning budget only for finalists. Screening on the 40k dev subsample; finalists on all training searches.
     - **References (E14-E17):** deployable base 0.347, +0.0096 [0.0076, 0.0114] over lagged popularity; early stopping on an inner 10% of the training searches, never on validation; memory peak 2.8 GB with all 97 features on the dev subsample. Full base with same-day popularity 0.366 (reference only, not deployable). Deployable full model 0.389 (+0.042 over the base); the learning curve still rose (20k to 33.8k fit searches +0.0041), so features for all training searches were built (E21). Untrained "own products first, then popularity" rule 0.373; the trained model adds +0.016.
     - **Personalisation (E18-E19):** pooled history (H1) alone gives +0.041 over the base; type and window splits add at most +0.0013 (all training data; type within the last 7 days +0.002), below the threshold; older history adds +0.012 over the last 7 days (common-window control). Working representation: base + H1.
     - **Context, query and source (E20):** match recency, metadata coverage, volume and context, time since the last action, query history and history source each added to base + H1: none helps (-0.0013 to +0.0002; all six +0.0006). The planned removals from the full model were replaced by these additions (all groups together added only about +0.002, so removal effects were expected to be small; not a mathematical bound).
   - **b) Item-item collaborative features (time box 2 days):** one pooled cosine graph over deduplicated training histories, built from **lagged events only** (at least one day old), with shrinkage `n_ij / (n_ij + 10)`, minimum item support about 5, pair support at least 2, top 50 neighbours per item, long histories capped reproducibly; computed as a sparse matrix product, never a full item-by-item matrix. **3-fold cross-fitting** for training rows (graph from two folds, features for the third); validation and test use the graph from all training records. Features per candidate: mean (unweighted and recency-weighted), maximum and matched-neighbour count of similarities to the user's history, pooled and per action type, plus CF coverage. Exact-product repeats stay separate (the graph diagonal is zero).
     - **Result (E22):** M1 + CF +0.0019 [0.0006, 0.0031] over pooled history on the dev subsample, below the threshold; links are sparse (only 2-3% of candidates have a similar product in the shopper's history). **CF closed after one cycle:** the SVD variant is dropped, since the expected gain is small and the time is better spent on the final runs and the report.
   - **c) Neural ranking (Colab GPU, bounded):** a **feature MLP** with the same inputs and a ranking loss (control), then **query- and candidate-conditioned attention over the history** (DIN-style: shop, brand and category embeddings, action type and age per event, the 50 most recent events; no capacity reserved by action and age, since E18 found no gain from type or age splits). Score = `alpha * log(1 + lagged popularity) + f(query, candidate, history, features)`, with the residual initialised at zero so the untrained model reproduces popularity. Loss: gain-normalised listwise softmax cross-entropy over the full list (all-zero searches omitted). Early stopping on our NDCG; **one fixed configuration per model, one debugging cycle, no tuning**. Not beating LambdaMART is an acceptable, reportable result.
     - **Result (E27-E29, E31, `notebooks/05b_neural.ipynb`, Colab T4):** feature MLP 0.389 (about equal to LambdaMART M1, -0.0028 vs M1 + CF with the same inputs); history attention 0.380, after the one debugging cycle 0.382 (-0.0073 vs the MLP, overfitting). One pre-registered regularised run (16-d embeddings, embedding dropout, weight decay on the embeddings) tests the overfitting diagnosis: 0.387, +0.0051 over E29, -0.0023 vs the MLP; overfitting largely removed; no tested attention configuration improves on the MLP (one seed per model; the last gap is below our 0.003 threshold). **The neural part is closed**; results are evaluated and logged via 05 section 15.
   - **Out of the committed scope:** full Transformer, GCN, knowledge graphs, stacking, multi-sided marketplace modelling (reasons in the AI_LOG entry on the model plan). NCF is covered by the Team 3 diagnosis.
   - **Protocol:** same searches for every comparison; per-search paired differences with bootstrap intervals over whole searches; one seed for screening; three seeds (with feature subsampling) only for M1 and M1 + CF (E30); LightGBM's NDCG (linear gains) for early stopping, final comparisons with our exact tie-aware evaluator.
   - **Population (E13):** searches with a clamped 1-second final gap are dropped from training; the main evaluation uses `validation_clean`, all searches as sensitivity.
   - **Hygiene:** inputs only from `features_v3_meta.json` groups (never `session_id`, `wid`, `label`, `n_candidates`); `last_action_type` categorical; searches with no engaged candidate and single-candidate lists dropped from training; all global statistics (popularity, CF graph, factors, vocabularies) from training records only and lagged; search-level features act only through interactions; importances are not read as preference weights.
   - **Robustness (E24):** features rebuilt with one history safety gap, `MIN_AGE_DAYS` = 10 minutes, and the dev-trained M1 + CF retrained: -0.0125; the gain over the base stays +0.030 (was +0.043).
   - **Final runs on all training data (gate before any conclusion):** ablations and model screening ran on the 40k dev subsample, so their numbers are screening results only. The finalists are **retrained on all training searches** (121,989 fit searches: the 125,746 clean training searches minus the inner early-stopping set; feature set v3 for all training records, built in chunks: about 11.3M rows, 4.4 GB as float32) and re-evaluated on `validation_clean`; the report quotes these numbers, and the test set is scored once afterwards. **Finalists:** deployable base, M1 (base + pooled history), M3 (by type and window), M1 + all six E20 groups, M1 + CF and the deployable full model.
   - **Result (E23, E30):** base 0.350, M1 0.389, M3 0.390, M1 + all six 0.391, full 0.391, M1 + CF 0.392 (vs M1 +0.0031 [0.0020, 0.0043], just meets the rule in the deterministic run, but +0.0004 to +0.0017 across three seeds). More data added only +0.001 to +0.003. Report numbers in FINDINGS 11. **Final LambdaMART: M1 + CF** (by the pre-registered rule), with **M1 as an equal co-headline** because the CF gain is not robust. The feature MLP uses the same inputs.
   - **Scope narrowed:** CF closed after one cycle; neural models with one fixed configuration each; one robustness setting; diagnostics limited to the segments below. Reason: the main question has a clear answer (pooled history carries the personal gain), and the remaining time goes to confirming it on all training data and to the report.
5. **`06_diagnostics`:** NDCG by segment (activity in the last 7 days or not, history length, list length, whether a candidate is already in the shopper's history, final gap), cold vs warm candidates, a few figures for the report, business insights; no training and no new models (window weights dropped after E18). History ages around day 64-66 before the search (logging outage) and sales days (Double 11, 618) are not interpreted per day. **Done (E32, wording corrected in E33):** 92% of the net personal gain comes from the 27% of searches whose list contains one of the shopper's own products; there, other engaged products lose 1.8 points of top-10 probability, far outweighed by the own-product gain; cold products (31% of engaged candidates) rarely reach the top 10 under any ranking and are about half of the engaged candidates M1 misses. Five report figures in `outputs/diagnostics/`.
6. **Test run:** after the final review, configurations are frozen and the finalists, fixed in a list before the run, are scored once on the 20,000 test searches, as the last notebook of the submission pipeline's single Colab run (section 9). Nothing is changed or selected on the test result.

## 6. Sampling and splits (decided after the interim)

- Unit: whole search records; keep all candidates and history; look up metadata in the full catalogue.
- **Test:** 20,000 records, drawn only from records outside the 5,000 explored at the interim (seed 4222); no model is tuned or selected on test labels, and only the pre-selected final models are evaluated on it. Full-data descriptions (E01, split profiles) did include these records; the report states this.
- **Validation:** 20,000 records, also outside the explored records; used for all model comparisons.
- **Training:** the remaining 133,831 records, including the 5,000 explored ones. A fixed 40,000-record development subsample keeps experiments quick; final models train on all training records.
- Searches without an engaged candidate stay in their split but are excluded from evaluation and from ranking training (every ordering scores the same).
- Searches with a clamped 1-second final gap (`final_gap_clamped` in the search table; 5.3% in every split) stay in their split but are excluded from training; the main evaluation uses the remaining searches, all searches are reported as sensitivity (E12-E13).
- Population features from training records only; supervised aggregates out-of-fold. Split indices are regenerated deterministically by `02_split_and_evaluation` and saved under `data/processed/`.
- A uniform split addresses our sampling choice, not the source's selection of active users' last searches.
- Candidates are shuffled within each search (seeded) before any training, so file order (which encodes the label) can never reach a model.
- Protocol difference to the source paper: the paper trains on historical search interactions and evaluates the last queries; we train and evaluate on last searches of different users. Published model scores are therefore not directly comparable.

## 7. Open decisions

1. Keep or drop MRR as a supporting metric (computed by default).
2. Who owns which pipeline stage.
3. Where shared processed artefacts live (Drive vs repo). Raw data is never committed.

Decided: split sizes and treatment of searches without an engaged candidate (section 6).

## 8. Documentation and working conventions

Every implementation, change and new finding is documented, so the work stays traceable while we iterate and every number in the report can be traced back to a run.

- **Experiments** go into `docs/EXPERIMENT_LOG.md` (E01, E02, ...): question and expectation before running; setup, result and decision after. Dead ends stay in the log.
- **Results** of every evaluated ranking go into `docs/experiment_results.csv` via `log_result` in `scripts/evaluation.py`.
- **Established facts** go into `docs/FINDINGS.md`; **changes of direction** into this file; **AI-influenced decisions** into `AI_LOG.md`.
- **Code** lives in Jupyter notebooks that run on Colab and are committed with outputs saved, with markdown explaining purpose, approach and logic. Only functions shared by several notebooks (parsing, evaluation) live in `scripts/`.

## 9. Remaining steps

In this order; each ends with its experiment-log entry and, where it changes a belief or the plan, FINDINGS and this file.

1. **Diagnostics (`06_diagnostics`, done, E32):** segments, own-history, warm and cold candidates and figures for the report (section 5, step 5); reads saved validation scores only.
2. **Final independent review (done, E33):** a Claude subagent and an external LLM, cross-checked; wording fixes and the 06 displacement section applied.
3. **Submission pipeline:** a separate, self-contained repository with only the pipeline (stage-numbered notebooks 01-07 incl. our Team 3 re-implementation, `scripts/` helpers, pinned versions, one path setting, run instructions and the Drive data link; development logs stay in this repository and are linked). It closes the reproducibility gaps of E33 (one branch, the E24 rebuild as a switch, saved neural weights and CF graph, CF features for test) and adds `07_test`. Design agreed with Liam before building.
4. **One Colab run of the whole pipeline, including the single test run:** `07_test` first re-scores validation with the models of this run and checks them against the reported numbers (tolerances fixed in advance), then scores test once. Test list, tolerances and contrasts are fixed in E34 before the run: random, lagged popularity, base, the rule, M1, M1 + CF, feature MLP, regularised attention; supporting: M3, M1 + all six, the full model. Nothing is changed or selected on the test result.
5. **Deliverables:** code and data artefacts on GitHub with a PDF of links on Canvas; report and slides; presentation and peer evaluation (course deadlines on Canvas); final consultation with the lecturer in week 11.

## 10. Key terms

- **Impression:** a product shown to the user; all candidates are impressions.
- **Graded relevance:** labels 0-3 carry different gains; a purchase counting more is an evaluation choice, not a measured monetary value.
- **NDCG@10:** gain of the top 10, discounted by position, divided by the best possible; 1.0 = perfect ordering.
- **Recall@k:** share of a search's engaged products in the top k. **MRR:** 1 / rank of the first engaged product, averaged over searches.
- **Cold item:** a product with no interactions to learn from; metadata features can stand in for it.
- **Why not accuracy:** about 98% of candidates are 0, so predicting 0 everywhere is about 98% accurate.

Log substantive AI-assisted decisions in `AI_LOG.md` as work progresses, following its rules; everything else follows section 8.
