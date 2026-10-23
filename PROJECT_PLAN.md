# Group 17 — JDSearch Project Plan

Status (20 Oct 2026): interim report submitted (source in `reports/interim/`); modelling phase started. Final code and data due **9 Nov**, report and slides 10 Nov, presentation 11 Nov.

Evidence and detailed results are in [docs/FINDINGS.md](docs/FINDINGS.md), every experiment in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md); this file holds direction, decisions and timeline.

---

## 1. One-paragraph summary

Re-rank the products JD returned for a search using the current query, the shopper's history and candidate metadata. The business decision is **how much past behaviour should influence the current ranking, and which parts of that history to trust**. One promising lead from a quick check: history seems more useful shortly after the last action and when past queries overlap the current one (FINDINGS §6). Since the interim we know that history consists of three windows with different retention (clicks 7 days, carts and follows 90 days, orders 365 days; FINDINGS §7), so history features and the context lead must respect those windows. The target is the observed interaction grade (0-3), evaluated on full, un-downsampled candidate lists.

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
- **Context signals to investigate** (FINDINGS §6): a quick untrained check suggests history helps more shortly after the last action and when past queries overlap the current one; history length and query-linked vs query-less history may also matter. Checks owed before relying on it: history strictly precedes the search; exclude exact re-finds; larger sample; test inside trained models; and, since the interim, separate recency from the retention windows (searches 7+ days after the last action have no clicks by construction, FINDINGS §7).
- **Supporting components:** query-title relevance (BM25 or term-ID embeddings), metadata features for cold candidates, full category paths, query-less history as its own source.
- **Possible side analysis:** repurchase vs "already bought" by category (FINDINGS §8).
- **Novelty framing:** query-aware and adaptive personalisation already exist (the JDsearch paper benchmarks such models). Our contribution is a corrected evaluation of the prior baseline plus controlled, interpretable evidence on when and how strongly history should shape search.

## 5. Roadmap (from 20 Oct 2026)

Pipeline notebooks continue the numbering in `notebooks/`. Each step ends with entries in the experiment log; steps are revisited as results come in.

0. **`02_split_and_evaluation` (foundation):** one fixed split by whole search record, the shared evaluation function (`scripts/evaluation.py`: NDCG@10, Recall@10, MRR, exact under random ties, by segment) and the results registry (`docs/experiment_results.csv`). Every later result uses both.
1. **Re-checks under the window lens** (exploration notebooks): the context lead with the visible action types held fixed; history-match signals by action type and window; history strictly before the search; exact re-finds excluded.
2. **`03_features`:** window-aligned history features (short 0-7 days: all types and recent queries; medium 7-90 days: carts and follows; long 90-365 days: orders), recency measured from the search, query-title relevance (BM25), training-only popularity, metadata for cold candidates.
3. **`04_baselines`:** random order, popularity, BM25, one-signal rules, and Team 3's model re-evaluated under our protocol (including the random-order simulation on their downsampled lists).
4. **`05_models`:** a LightGBM ranker (LambdaRank) built up step by step with the same split: no history, then pooled history (Team 3-like), then window-aligned features, then query-weighted history. Then a neural model with one encoder per window and a learned, query-aware weighting between them, compared on the same inputs.
5. **`06_diagnostics`:** NDCG by segment (activity in the last 7 days or not, cold vs warm candidates, history length, query overlap), feature importance and learned window weights, business insights.

## 6. Sampling and splits (decided 20 Oct 2026)

- Unit: whole search records; keep all candidates and history; look up metadata in the full catalogue.
- **Test:** 20,000 records, drawn only from records outside the 5,000 explored at the interim (seed 4222), untouched until the final models.
- **Validation:** 20,000 records, also outside the explored records; used for all model comparisons.
- **Training:** the remaining 133,831 records, including the 5,000 explored ones. A fixed 40,000-record development subsample keeps experiments quick; final models train on all training records.
- Searches without an engaged candidate stay in their split but are excluded from evaluation and from ranking training (every ordering scores the same).
- Population features from training records only; supervised aggregates out-of-fold. Split indices are regenerated deterministically by `02_split_and_evaluation` and saved under `data/processed/`.
- A uniform split addresses our sampling choice, not the source's selection of active users' last searches.

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
