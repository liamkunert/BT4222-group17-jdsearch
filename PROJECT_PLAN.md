# Group 17 — JDSearch Project Plan

Status (20 Oct 2026): interim report submitted (source in `reports/interim/`); modelling phase started. Final code and data due **9 Nov**, report and slides 10 Nov, presentation 11 Nov.

Evidence and detailed results are in [docs/FINDINGS.md](docs/FINDINGS.md), every experiment in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md); this file holds direction, decisions and timeline.

---

## 1. One-paragraph summary

Re-rank the products JD returned for a search using the current query, the shopper's history and candidate metadata. The business decision is **how much past behaviour should influence the current ranking, and which parts of that history to trust**. Since the interim we know that history has action-specific observation windows (clicks 7 days, carts and follows 90 days, orders 365 days; FINDINGS §7). Re-checked under those windows, a large part of the interim lead (history helps more right after the last action) disappears when fresh evidence is removed; whether session context adds value beyond fresh evidence is open and will be tested in trained models (FINDINGS §6-7.1). Past-query overlap remains a candidate moderator. The target is the observed interaction grade (0-3), evaluated on full, un-downsampled candidate lists.

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
- **How history should be weighted** (FINDINGS §6-7.1, re-checked 23 Oct, reviewed in E06): single-signal checks suggest the value of evidence depends on its age, type and level (broad brand/shop/category evidence weaker when old, exact-product evidence much less so). No sign of leakage (not proof); shop and brand evidence from other products helps. Tested next **as model ablations** on the same split: (1) time since last action and its interactions (session context), (2) query overlap between current query and history, (3) past orders by age and category (repurchase), (4) coverage of matching history (exact product, only shop/brand, none), (5) query-linked vs query-less history.
- **Supporting components:** query-title relevance (BM25 or term-ID embeddings), metadata features for cold candidates, full category paths, query-less history as its own source.
- **Possible side analysis:** repurchase vs "already bought" by category (FINDINGS §9).
- **Novelty framing:** query-aware and adaptive personalisation already exist (the JDsearch paper benchmarks such models). Our contribution is a corrected evaluation of the prior baseline plus controlled, interpretable evidence on when and how strongly history should shape search.

## 5. Roadmap (from 20 Oct 2026)

Pipeline notebooks continue the numbering in `notebooks/`. Each step ends with entries in the experiment log; steps are revisited as results come in.

0. **`02_split_and_evaluation` (foundation):** one fixed split by whole search record, the shared evaluation function (`scripts/evaluation.py`: NDCG@10, Recall@10, MRR, exact under random ties, by segment) and the results registry (`docs/experiment_results.csv`). Every later result uses both.
1. **Re-checks under the window lens** (done 23 Oct, `exploration/window_recheck.ipynb`, E03-E05; reviewed in E06): history-match signals by action type and window; the context lead with action types held fixed (largely explained by fresh evidence; context value open); leakage indications and re-find checks.
2. **`03_features`** (v1 23 Oct, E07; **v2 25 Oct, E08** after two reviews): groups G0 search, G1 relevance (BM25, title overlap), G2 popularity (training only; label-free counts exclude the own search, engagement rate out-of-fold), H1 pooled history, H2 history by type, H3 history by window (0-7 d all types; 7+ d carts; 7-90 d and 90+ d orders; follows), H4 match recency, C1 history volume, C2 session context, Q1 query-history (all ages and last 7 days), S1 search-linked vs query-less history. The same four match definitions (exact product, shop and brand via other products, L3 path) in every history group. `MIN_AGE_DAYS` rebuilds everything with a history safety gap. Later, if diagnostics ask for it: query-product popularity, normalised matches, history metadata coverage, list-relative ranks, query-category compatibility.
3. **`04_baselines`:** simple references done 25 Oct (E09: history popularity 0.341 best, best personal signal 0.182, BM25 0.093, random 0.085). Team 3 part 1 done 25 Oct (E10: on their protocol random order already scores 0.532 vs their reported 0.568). Still to add: Team 3 part 2, their model re-implemented and corrected one flaw at a time on our protocol (correction ladder).
4. **`05_models`:** a LightGBM ranker (LambdaRank, **`label_gain=[0,1,2,3]`** to match our linear gains; LightGBM's default is exponential). Controlled ablations instead of one ladder (E08):
   - **Reference:** base = G0-G2 (strong non-personalised ranker). Personalisation is judged by what it adds on top of it.
   - **Window question:** base + H1 (pooled) vs base + H2 (by type, no age) vs base + H3 (type and age); same match definitions in all three; H4 recency added separately.
   - **Context question:** full model vs full model without **all** context (C1 history volume, which overlaps with recent activity, and C2); `days_since_last_action` also removed on its own. A small gain from C2 alone does not show that context is unimportant.
   - **Query and source questions:** Q1 and S1 each removed from the full model (not only added at the end), because their marginal value depends on what is already present.
   - **Protocol:** same searches, fixed hyperparameters across variants (plus one tuned run), a fixed set of seeds with seed spread reported separately, paired bootstrap intervals of the **difference**; model selection and early stopping with our exact tie-aware NDCG@10 (or a verified match with LightGBM's metric).
   - **Hygiene:** inputs only from `features_v2_meta.json` groups (never `session_id`, `wid`, `label`); `last_action_type` categorical; searches with no engaged candidate and single-candidate lists dropped from training; search-level features act only through interactions, which is stated when reporting them; importances are not read as preference weights.
   - **Robustness:** rebuild features with `MIN_AGE_DAYS` = 1 min / 10 min / 1 h and retrain.
   - Then a compact neural model: shared product and metadata representations with type and age information and masked pooling per window; separate encoders or attention only if time allows.
5. **`06_diagnostics`:** NDCG by segment (activity in the last 7 days or not, cold vs warm candidates, history length, query overlap), feature importance and learned window weights, business insights.

## 6. Sampling and splits (decided 20 Oct 2026)

- Unit: whole search records; keep all candidates and history; look up metadata in the full catalogue.
- **Test:** 20,000 records, drawn only from records outside the 5,000 explored at the interim (seed 4222); no model is tuned or selected on test labels, and only the pre-selected final models are evaluated on it. Full-data descriptions (E01, split profiles) did include these records; the report states this.
- **Validation:** 20,000 records, also outside the explored records; used for all model comparisons.
- **Training:** the remaining 133,831 records, including the 5,000 explored ones. A fixed 40,000-record development subsample keeps experiments quick; final models train on all training records.
- Searches without an engaged candidate stay in their split but are excluded from evaluation and from ranking training (every ordering scores the same).
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
| 26 Oct - 1 Nov | Features (03); baselines incl. Team 3 re-evaluation (04); LightGBM ladder (05) |
| 2-6 Nov | Multi-window neural model (05); diagnostics (06); final test-set runs |
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
