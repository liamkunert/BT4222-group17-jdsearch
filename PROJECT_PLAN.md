# Group 17 — JDSearch Project Plan

Status (29 Oct 2026): interim report submitted (source in `reports/interim/`); LambdaMART screening and ablations (E14-E22), full-data finalists (E23), robustness (E24), independent reviews and their checks (E25, E26, E30) and the neural models (E27-E29, regularised attention E31) done. Remaining: deferred review wording is applied, diagnostics (06), final review, one test run, Colab reproducibility (section 9). Final code and data due **9 Nov**, report and slides 10 Nov, presentation 11 Nov.

Evidence and detailed results are in [docs/FINDINGS.md](docs/FINDINGS.md), every experiment in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md); this file holds direction, decisions and timeline.

---

## 1. One-paragraph summary

Re-rank the products JD returned for a search using the current query, the shopper's history and candidate metadata. The business decision is **how much past behaviour should influence the current ranking, and which parts of that history to trust**. Since the interim we know that history has action-specific observation windows (clicks 7 days, carts and follows 90 days, orders 365 days; FINDINGS §7). Re-checked under those windows, a large part of the interim lead (history helps more right after the last action) disappears when fresh evidence is removed; whether session context adds value beyond fresh evidence was then tested in trained models (FINDINGS §6-7.1). **Model ablations (E18-E20, 28 Oct, dev subsample):** four pooled history match counts carry almost the whole personal gain (+0.041 over a relevance and popularity ranker); splitting by action type or age, session context, query overlap and history source add small amounts at most, all below our +0.003 threshold. Confirmed with all training data (E23, E30: base 0.350, pooled history 0.389); item-item CF adds no robust gain (E30), neural models do not beat the trees (E27-E29). The target is the observed interaction grade (0-3), evaluated on full, un-downsampled candidate lists.

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
- **How history should be weighted** (FINDINGS §6-7.1, re-checked 23 Oct, reviewed in E06): single-signal checks suggest the value of evidence depends on its age, type and level (broad brand/shop/category evidence weaker when old, exact-product evidence much less so). No sign of leakage (not proof); shop and brand evidence from other products helps. Tested next **as model ablations** on the same split: (1) time since last action and its interactions (session context), (2) query overlap between current query and history, (3) past orders by age and category (repurchase), (4) coverage of matching history (exact product, only shop/brand, none), (5) query-linked vs query-less history. **Outcome (E18-E20, E23, E30):** none of (1), (2), (4), (5) or the type and window splits adds a practically relevant amount (all below +0.003) to pooled match counts in LambdaMART; older history does add signal (+0.012 over the last 7 days). Query-conditioned weighting of individual events is tested once more by the attention model.
- **Supporting components:** query-title relevance (BM25 or term-ID embeddings), metadata features for cold candidates, full category paths, query-less history as its own source.
- **Possible side analysis:** repurchase vs "already bought" by category (FINDINGS §9).
- **Novelty framing:** query-aware and adaptive personalisation already exist (the JDsearch paper benchmarks such models). Our contribution is a corrected evaluation of the prior baseline plus controlled, interpretable evidence on when and how strongly history should shape search.

## 5. Roadmap (from 20 Oct 2026)

Pipeline notebooks continue the numbering in `notebooks/`. Each step ends with entries in the experiment log; steps are revisited as results come in.

0. **`02_split_and_evaluation` (foundation):** one fixed split by whole search record, the shared evaluation function (`scripts/evaluation.py`: NDCG@10, Recall@10, MRR, exact under random ties, by segment) and the results registry (`docs/experiment_results.csv`). Every later result uses both.
1. **Re-checks under the window lens** (done 23 Oct, `exploration/window_recheck.ipynb`, E03-E05; reviewed in E06): history-match signals by action type and window; the context lead with action types held fixed (largely explained by fresh evidence; context value open); leakage indications and re-find checks.
2. **`03_features`** (v1 23 Oct, E07; v2 25 Oct, E08 after two reviews; **v3 26 Oct, E13** after the data-generation audits: `n_candidates` removed because list length forms after the query, deployable lagged history popularity, metadata coverage per block): groups G0 search (query length), G1 relevance (BM25, title overlap), G2a deployable popularity (history actions at least one day old), G2b same-day popularity (exposures, unlagged history, out-of-fold engagement rate; training only, label-free counts exclude the own search), H5 metadata coverage per block, H1 pooled history, H2 history by type, H3 history by window (0-7 d all types; 7+ d carts; 7-90 d and 90+ d orders; follows), H4 match recency, C1 history volume, C2 session context, Q1 query-history (all ages and last 7 days), S1 search-linked vs query-less history. The same four match definitions (exact product, shop and brand via other products, L3 path) in every history group. `MIN_AGE_DAYS` rebuilds the personal history and context features with a history safety gap (it does not lag the population counts; `pop_history_lag1d` covers that). Later, if diagnostics ask for it: query-product popularity, normalised matches, list-relative ranks, query-category compatibility.
3. **`04_baselines`:** simple references done 25 Oct (E09: history popularity 0.341 best, best personal signal 0.182, BM25 0.093, random 0.085). Team 3 part 1 done 25 Oct (E10: on their protocol random order already scores 0.532 vs their reported 0.568). Team 3 part 2 done 26 Oct (E11, Colab T4): R0 0.151, more than half of its gain over random is a label leak; all fixes on their architecture reach 0.148; with our relevance and popularity features 0.297, still below popularity alone (0.341). Team 3 is not a viable base. Clean population added 26 Oct (E13): references without the clamped searches; deployable reference = lagged history popularity 0.337; same-product history 0.159 (was 0.182).
4. **`05_models`** (model decision 27 Oct after an external review, see AI_LOG). One model family at a time, each with a success criterion and a time box; every iteration in the experiment log. Primary benchmark: **lagged history popularity, 0.337 NDCG@10 on clean validation**; improvements below 0.003-0.005 are not treated as meaningful.
   - **a) LambdaMART (main model):** LightGBM gradient-boosted trees with the LambdaRank objective, `label_gain=[0,1,2,3]`, NDCG@10 evaluation, `lambdarank_truncation_level` around 13-20; one fixed configuration for all ablations (about 31 leaves, learning rate 0.05, sizeable minimum leaf support, early stopping), a small bounded tuning budget only for finalists. Trained on the 40k dev subsample (learning curve 20k vs 40k decides whether full training data is needed; full data is about 4.6 GB of features before LightGBM's copies).
     - **References:** deployable base = G0 + G1 + G2a (must clearly beat 0.337; otherwise check features, grouping, gains, evaluator); full base = + G2b. **Done 27 Oct (E14):** deployable base 0.347, +0.0096 [0.0076, 0.0114] over lagged popularity; early stopping on an inner 10% of the training searches, never on validation; memory peak 2.8 GB with all 97 features on the dev subsample. **E15:** full base 0.366 (same-day signals +0.0185 over the base; reference only). **E16:** deployable full model 0.389 (+0.042 over the base); the learning curve still rises (20k to 33.8k fit searches +0.0041), so the full-data features are built right after the first ablations (about 30 Oct). **E17:** untrained "own products first, then popularity" rule 0.373; the trained model adds +0.016. **E18-E19 (28 Oct):** pooled history (H1) alone gives +0.041 over the base; type and window splits add at most +0.0013 (all training data; type within the last 7 days +0.002), below the threshold; older history adds +0.012 over the last 7 days; all remaining groups together about +0.002. Working representation: base + H1. **E20:** match recency, metadata coverage, volume and context, time since the last action, query history and history source each added to base + H1: none helps (-0.0013 to +0.0002; all six +0.0006). Working LambdaMART: base + H1 (14 inputs); the planned removals from the full model were replaced by these additions (all groups together added only about +0.002, so removal effects were expected to be small; not a mathematical bound).
     - **Personalisation:** base vs base + history; pooled (H1) vs by type (H2) vs type and window (H3), with a **common-window control** (only the last 7 days, where all action types are observed) before reading window effects as temporal preference; H4 recency and H5 coverage added separately.
     - **Context, query and source:** full model without the explicit context features (C1 + C2) and without `days_since_last_action` alone; Q1 and S1 each removed from the full model.
   - **b) Item-item collaborative features (time box 2 days):** one pooled cosine graph over deduplicated training histories, built from **lagged events only** (at least one day old), with shrinkage `n_ij / (n_ij + 10)`, minimum item support about 5, pair support at least 2, top 50 neighbours per item, long histories capped reproducibly; computed as a sparse matrix product, never a full item-by-item matrix. **3-fold cross-fitting** for training rows (graph from two folds, features for the third); validation and test use the graph from all training records. Features per candidate: mean (unweighted and recency-weighted), maximum and matched-neighbour count of similarities to the user's history, pooled and per action type, plus CF coverage. Exact-product repeats stay separate (the graph diagonal is zero). Stop if usable coverage is low or there is no gain after one cycle. Optional add-on: truncated SVD (32-64 dimensions) of the same normalised history matrix, passed to the trees as scalar candidate-history similarities only.
     - **E22 (28 Oct):** M1 + CF +0.0019 [0.0006, 0.0031] over pooled history, below the threshold; links are sparse (only 2-3% of candidates have a similar product in the shopper's history). **CF closed (scope decision 28 Oct):** the SVD variant is dropped, since the expected gain is small and the time is better spent on the final runs and the report.
   - **c) Neural ranking (Colab GPU, bounded):** first a **feature MLP** with the same inputs and a ranking loss (control), then **query- and candidate-conditioned attention over the history** (DIN-style: product, shop, brand and category embeddings, action type and age per event, the 50 most recent events; simplified 28 Oct: no capacity reserved by action and age, since E18 found no gain from type or age splits). Score = `alpha * log(1 + lagged popularity) + f(query, candidate, history, features)`, with the residual initialised at zero so the untrained model reproduces popularity. Loss: gain-normalised listwise softmax cross-entropy over the full list (all-zero searches omitted); fallback: pairwise logistic loss weighted by |delta NDCG@10|. Early stopping on our NDCG; **one fixed configuration per model, one debugging cycle, no tuning** (28 Oct); three seeds only for the final full-data run if time allows. Not beating LambdaMART is an acceptable, reportable result.
     - **Done 29 Oct (E27-E29, `notebooks/05b_neural.ipynb`, Colab T4):** feature MLP 0.389 (equal to LambdaMART M1, -0.0028 vs M1 + CF); history attention 0.380, after the one debugging cycle 0.382 (-0.0073 vs the MLP, overfitting). The neural part ends here; results logged via 05 section 15. **E31 (pre-registered 29 Oct, Liam):** one regularised attention run (16-d embeddings, embedding dropout, weight decay on the embeddings) as a test of the overfitting diagnosis: 0.387, +0.0051 over E29, -0.0023 vs the MLP; overfitting largely removed, attention still below the MLP. The neural part ends here.
   - **Out of the committed scope:** full Transformer, GCN, knowledge graphs, stacking, multi-sided marketplace modelling (reasons in the AI_LOG entry of 27 Oct). NCF is covered by the Team 3 diagnosis.
   - **Protocol:** same searches for every comparison; per-search paired differences with bootstrap intervals over whole searches; one seed for screening, three for finalists; LightGBM's NDCG (linear gains) for early stopping, final comparisons with our exact tie-aware evaluator.
   - **Population (E13):** searches with a clamped 1-second final gap are dropped from training; the main evaluation uses `validation_clean`, all searches as sensitivity.
   - **Hygiene:** inputs only from `features_v3_meta.json` groups (never `session_id`, `wid`, `label`, `n_candidates`); `last_action_type` categorical; searches with no engaged candidate and single-candidate lists dropped from training; all global statistics (popularity, CF graph, factors, vocabularies) from training records only and lagged; search-level features act only through interactions; importances are not read as preference weights.
   - **Robustness:** rebuild features with a history safety gap and retrain the final LambdaMART; narrowed 28 Oct to one setting, `MIN_AGE_DAYS` = 10 minutes (was 1 min / 10 min / 1 h). **Done 29 Oct (E24):** -0.0125 for the final model; gain over the base stays +0.030 (was +0.043).
   - **Final runs on all training data (gate before any conclusion):** ablations and model screening run on the 40k dev subsample, so their numbers are screening results only. Before we draw conclusions, write the report's results or run the final independent review, the finalists are **retrained on all 133,831 training searches** (feature set v3 for all training records, built in chunks: about 11.3M rows, 4.4 GB as float32) and re-evaluated on `validation_clean`. The report quotes these numbers; the test set is scored once afterwards. Include M1 (pooled) vs M3 (by type and window) and M1 vs M1 + all E20 groups in these runs: finer representations and extra groups may only pay off with more data (E18, E20). **Finalists (28 Oct):** deployable base, M1 (base + pooled history, the working model), M3, M1 + CF and the deployable full model; features for all training searches built on Colab (E21).
   - **E23 (28 Oct, done):** finalists on all training searches: base 0.350, M1 0.389, M3 0.390, full 0.391, M1 + CF 0.392 (vs M1 +0.0031 [0.0020, 0.0043], just meets the rule); more data added only +0.001 to +0.003. Report numbers in FINDINGS 11. **Final LambdaMART: M1 + CF** (decision 28 Oct, by the pre-registered rule; M1 reported alongside). The feature MLP uses its inputs; the robustness check retrains it.
   - **Scope narrowed (28 Oct):** CF closed after one cycle; neural models with one fixed configuration each; one robustness setting; diagnostics limited to the segments below. Reason: the main question has a clear answer (pooled history carries the personal gain), and the remaining time goes to confirming it on all training data and to the report.
5. **`06_diagnostics`:** NDCG by segment (activity in the last 7 days or not, cold vs warm candidates, history length, list length: up to 60, 85-95, over 95), a few figures for the report, business insights; no new analyses (narrowed 28 Oct; window weights dropped after E18). History ages around day 64-66 before the search (logging outage) and sales days (Double 11, 618) are not interpreted per day.

## 6. Sampling and splits (decided 20 Oct 2026)

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

## 9. Timeline

| Date | Milestone |
|---|---|
| 4 Oct | Interim report submitted |
| 20-25 Oct | Foundation: split and evaluation (02); re-checks under the window lens; random and popularity reference |
| 23-26 Oct | Features v1-v3 (03); baselines incl. Team 3 diagnosis (04); data-generation audits and fixes (E12-E13) |
| 27-28 Oct | `05_models`: LambdaMART base, ablations (E14-E20), CF features (E22); full-data features on Colab (E21) |
| 29 Oct | Finalists retrained on all training searches (LambdaMART) |
| 30 Oct | Robustness rebuild (10-minute history gap) and retrain; data preparation for the neural models |
| 31 Oct-3 Nov | Feature MLP, then history attention (Colab), one configuration each |
| 4-5 Nov | Diagnostics (06), figures for the report; review fixes deferred from E25 (wording, cache robustness, fairer rule, final-gap sensitivity, three seeds for M1 and M1 + CF, full-data "M1 + all six") |
| 6 Nov | Buffer; independent review of the final results |
| 7 Nov | Freeze configurations, one test run |
| 8 Nov | Reproducibility check on Colab, documentation |
| Week 11 | Final consultation with the lecturer |
| 9 Nov | Code and data artefacts on GitHub; PDF with links on Canvas |
| 10-11 Nov | Report, slides, presentation; peer evaluation |

## 10. Key terms

- **Impression:** a product shown to the user; all candidates are impressions.
- **Graded relevance:** labels 0-3 carry different gains; a purchase counting more is an evaluation choice, not a measured monetary value.
- **NDCG@10:** gain of the top 10, discounted by position, divided by the best possible; 1.0 = perfect ordering.
- **Recall@k:** share of a search's engaged products in the top k. **MRR:** 1 / rank of the first engaged product, averaged over searches.
- **Cold item:** a product with no interactions to learn from; metadata features can stand in for it.
- **Why not accuracy:** about 98% of candidates are 0, so predicting 0 everywhere is about 98% accurate.

Log substantive AI-assisted decisions in `AI_LOG.md` as work progresses, following its rules; everything else follows section 8.
