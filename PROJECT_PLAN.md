# Group 17 — JDSearch Project Plan

Status (4 Oct 2026): data understanding complete; interim report due **4 Oct 2026, 11:59 PM** on Canvas (draft in `docs/interim/`). Final code and data due 9 Nov, report and slides 10 Nov, presentation 11 Nov.

Evidence and detailed results are in [docs/FINDINGS.md](docs/FINDINGS.md); this file holds direction, decisions and timeline.

---

## 1. One-paragraph summary

Re-rank the products JD returned for a search using the current query, the shopper's history and candidate metadata. The business decision is **how much past behaviour should influence the current ranking, and which parts of that history to trust**. One promising lead from a quick check: history seems more useful shortly after the last action and when past queries overlap the current one (FINDINGS §6). The target is the observed interaction grade (0-3), evaluated on full, un-downsampled candidate lists.

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
- **Context signals to investigate** (FINDINGS §6): a quick untrained check suggests history helps more shortly after the last action and when past queries overlap the current one; history length and query-linked vs query-less history may also matter. Checks owed before relying on it: history strictly precedes the search; exclude exact re-finds; larger sample; test inside trained models.
- **Supporting components:** query-title relevance (BM25 or term-ID embeddings), metadata features for cold candidates, full category paths, query-less history as its own source.
- **Possible side analysis:** repurchase vs "already bought" by category (FINDINGS §7).
- **Novelty framing:** query-aware and adaptive personalisation already exist (the JDsearch paper benchmarks such models). Our contribution is a corrected evaluation of the prior baseline plus controlled, interpretable evidence on when and how strongly history should shape search.

## 5. Modelling plan (after the interim)

Pipeline notebooks continue the numbering in `notebooks/`:

1. **`02_preprocessing`:** grouped train/validation/test split; training-only population features; session features from time gaps (time since last action, session boundaries, in-session actions, repeated queries); history-match features (FINDINGS §4); text relevance.
2. **`03_baselines`:** random order, popularity, one-signal rules, and Team 3's model re-evaluated (including the random-baseline simulation on their downsampled lists).
3. **`04_models`:** a no-history reference (query–product match, candidate metadata, training-set popularity) that isolates what personalisation adds; a feature-based learning-to-rank model with history; then a model combining relevance, short-term and long-term history with a context-dependent weighting. Compare models with the same inputs.
4. **`05_diagnostics`:** NDCG by segment (time since last action, cold vs warm candidates, history length, query overlap), learned weights, and business insights.

## 6. Sampling and scaling

- Sampling unit: whole search records; keep all candidates and history; look up metadata in the full catalogue.
- Model-development sample size still open (30,000-50,000 records is an option); save split indices.
- The 5,000 explored records (seed 4222) have informed feature choices; keep this in mind for the final evaluation.
- Population features from training records only; supervised aggregates out-of-fold.
- A uniform sample addresses our sampling choice, not the source's selection of active users' last searches.

## 7. Open decisions

1. Keep or drop MRR as a supporting metric.
2. Model-development sample size and split proportions.
3. Training treatment of searches without an engaged candidate.
4. Who owns which pipeline stage.
5. Where shared processed artefacts live (Drive vs repo). Raw data is never committed.

## 8. Timeline

| Date | Milestone |
|---|---|
| 4 Oct | Submit interim report by 11:59 PM |
| Week 7 | Preprocessing and baselines; TA checkpoint |
| 12 Oct | Midterm (Weeks 1-8) |
| Mid Oct | Main models and evaluation; context-signal checks |
| Week 11 | Final consultation with the lecturer |
| 9 Nov | Code and data artefacts on GitHub; PDF with links on Canvas |
| 10-11 Nov | Report, slides, presentation; peer evaluation |

## 9. Key terms

- **Impression:** a product shown to the user; all candidates are impressions.
- **Graded relevance:** labels 0-3 carry different gains; a purchase counting more is an evaluation choice, not a measured monetary value.
- **NDCG@10:** gain of the top 10, discounted by position, divided by the best possible; 1.0 = perfect ordering.
- **Recall@k:** share of a search's engaged products in the top k. **MRR:** 1 / rank of the first engaged product, averaged over searches.
- **Cold item:** a product with no interactions to learn from; metadata features can stand in for it.
- **Why not accuracy:** about 98% of candidates are 0, so predicting 0 everywhere is about 98% accurate.

Log substantive AI-assisted decisions in `AI_LOG.md` as work progresses, following its rules.
