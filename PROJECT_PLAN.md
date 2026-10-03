# Group 17 — JDSearch Project Plan

Status: interim data foundation consolidated, 2026-10-03; report writing and team review pending. Interim report due **4 Oct 2026, 11:59 PM** (Canvas). Final code and data due 9 Nov, report and slides 10 Nov, presentation 11 Nov.

The report's raw-data summaries and feature statistics are consolidated in `notebooks/02_interim_report.ipynb`. Raw summaries cover the full files; engineered features use 5,000 uniformly sampled whole records, seed 4222. Detailed exploratory checks remain in notebooks 03 and 04 and their companion findings under `reports/interim/`. Their untrained ranking results do not commit a model architecture. The report itself has not yet been drafted.

---

## 1. One-paragraph summary

Re-rank the products supplied for a JDSearch query using the current query, the shopper's supplied history, and candidate metadata. The business decision is **how much past behaviour should influence the current ranking, and which parts of that history provide useful evidence**. We will investigate query relevance, product/brand/shop matches, four-level category relationships, action type, query presence, and recency. The prediction task uses the observed interaction grades (0-3), with evaluation on **full, un-downsampled candidate lists**. Concrete architectures, feature combinations, and training objectives remain open until exploratory analysis and baseline comparisons establish which signals are useful.

---

## 2. Business objective and ML task (interim report Part 1)

- **Business objective:** improve search relevance by using historical preferences where they provide useful evidence for the current query. Helping shoppers find suitable products and supporting purchases are the business motivations; offline ranking quality is the measurable outcome.
- **ML task:** personalised re-ranking of the supplied candidate list for each search.
- **Input sample:** one (session, candidate) pair, described by
  - the user's history (items, action types, time gaps, past queries),
  - the current query,
  - the candidate's metadata (title tokens, brand, 4-level category, shop).
  All candidates from one search form one ranking group and remain together when sampling or splitting.
- **Target label:** graded interaction level per candidate: 0 = no interaction, 1 = click, 2 = add to cart, 3 = purchase.
  - Evaluation: graded ranking metrics on complete candidate lists, with gains and treatment of all-zero lists explicitly documented. Purchases receive greater relevance gain than clicks as an evaluation choice, not a measured monetary value.
- **Investigation:** which historical behaviours provide useful predictive evidence for the current search, and under which conditions? Category depth and adaptive history selection are hypotheses to test, not assumed improvements.
- **Model selection:** architecture, training objective, and exact feature combinations will be selected after exploration and baseline comparisons. Binary engagement prediction may serve as a baseline without replacing the graded re-ranking task.
- **Interim foundation:** JDSearch, the grouped search/candidate inputs, and the observed graded labels form the stable project foundation. Model training and completed feature engineering are not required for the interim report.

---

## 3. Data in plain terms

### 3.1 One row is one search moment

`user_behavior_data.txt` has 173,831 rows. Each row describes one user's search and their past.

| Column | Meaning |
|---|---|
| `query` | Anonymised term IDs of the current search |
| `candidate_wid_list` | Products JD returned (about 89 per row). These were **shown** to the user (impressions). |
| `candidate_label_list` | What the user did with each: 0 none, 1 click, 2 cart, 3 purchase |
| `history_qry_list` | Earlier queries (`-1` = no search, e.g. clicked a recommendation) |
| `history_wid_list` | Earlier products interacted with, in order |
| `history_type_list` | CLICK / CART / FLW (follow) / ORD (purchase) |
| `history_time_list` | Gaps between actions, plus the gap from the last action to the test query. It has one more element than the other history lists. The initial value is 0; there is one extra final gap to the test query. Report raw units; derived hours/days assume seconds following the course examples. |

`product_meta_data.txt`: 12,141,247 products with `wid`, `name`, `brand_id`, `brand_name`, `cate_id_1..4`, `cate_name_1..4`, `shop_id`. All text is anonymised term IDs.

### 3.2 Mapping to ML terms

| ML term | In this data |
|---|---|
| Example | One (session, candidate) pair. 173,831 sessions × about 89 ≈ 15.5M pairs |
| Group | The candidate list of one session. Items in it compete with each other. |
| Features | Facts about the user history, the query, the product, and how they relate |
| Label | 0 / 1 / 2 / 3 per candidate |
| Positive / negative | Positive = label ≥ 1. A negative (0) is **exposed but not engaged**, which is a real signal. Unexposed products are unobserved, which is different. |

### 3.3 Verified foundation and interpretation

- **Scope:** 173,831 records, 15,510,012 candidate occurrences, 26,667,260 history actions and 12,141,247 catalog rows. The catalog plus observed products lacking metadata totals 12,872,636 distinct products, matching the paper. Full-data statistics and sample feature statistics are marked separately in exported tables.
- **Interaction grades:** labels 0/1/2/3 describe recorded outcomes. Approximately 2.07% of candidates have a positive label. Cumulative grade thresholds are not observed click/cart/purchase transitions, so do not call their ratios conversion rates.
- **Candidate order:** the full-file check finds every positive before every negative in positive-containing records. No reliable display rank is available. Exclude position features and avoid resolving ties with file order.
- **All-zero records:** 2,103 supplied rows have no positive candidate; retain them in EDA. The source excludes these from test evaluation. Decide and document training/evaluation treatment before comparisons.
- **Collection period:** the [paper, section 3.1](https://arxiv.org/html/2305.14810) documents histories from 18 Oct 2021 to 17 Oct 2022 and last test queries on 17 Oct 2022. Relative gaps cannot reconstruct a cross-user chronological split. Derived spans assuming seconds may exceed the documented year and require a unit/logging audit.
- **User grouping:** the source describes one user's last query per record. No persistent user-ID field is released; group by record rather than trying to infer accounts from history overlap.
- **Queries:** text has recoverable term boundaries. Raw exact current/history query matching finds only one record; distinct-term-set matching finds 610 (0.35%) over all records. Partial overlap occurs for 41.14% of the 5,000-record diagnostic sample. These matches are lexical evidence, not proof of the same intent.
- **Categories:** no empty/-1 category IDs are found among catalog rows. Some IDs have multiple parents (17 L3 and 33 L4), so category features consistently match ancestor paths. In the diagnostic sample, paths vary within 66.34% / 78.90% / 89.04% / 91.16% of lists at L1-L4. L4 adds a small gain over L3 for simple count ranking; learned-model value remains untested.
- **History absence/coldness:** report distinct-item and candidate-occurrence denominators separately. Descriptive absence from all supplied histories is different from absence in a future training split. Neither guarantees that a shopper has never seen a product elsewhere.

### 3.4 Limitations to state

The released data does not provide reliable display rank, persistent user IDs or absolute row timestamps. Grade labels do not reveal interaction paths, revenue or explicit dislikes. Missing history metadata can conceal preferences; lookup must include both historical and candidate products against the full catalog. Repeated history-query entries can be several actions under one search. A uniform sample preserves whole records but cannot remove the source's active-user/last-query selection or guarantee enough examples in rare subgroups.

---

## 4. Concepts we rely on (short glossary)

- **Impression:** a product shown to the user. All candidates are impressions.
- **Pointwise ranking:** score each candidate independently, then sort. Simple and explainable.
- **Graded relevance:** labels have levels of importance (0–3), not just yes/no. A purchase receives greater relevance gain as an evaluation choice; monetary value is unobserved.
- **NDCG@10:** score of the top 10 where each item's gain is its grade, discounted by position (higher positions count more), divided by the best possible score. 1.0 = perfect ordering.
- **MRR:** 1 divided by the rank of the first engaged item, averaged over sessions.
- **Recall@k:** the share of a session's engaged items that appear in the top k.
- **Cold start:** items (or users) with no history signal. Metadata-based features can complement item IDs; evaluate their contribution rather than assuming a particular handling strategy.
- **Why not accuracy/F1:** about 98% of candidates are 0, so "predict 0 for everything" gets about 98% accuracy.

---

## 5. Feature plan (starter set; full feature dictionary goes in the report)

| Group | Feature idea | Intuition |
|---|---|---|
| Query–item match | Exact term-ID overlap with candidate title, brand name and category names | Lexical relevance; overlap alone does not identify a semantic query type |
| User affinity | Count of past interactions with the candidate's brand, category (each of 4 levels), shop | "User often buys in this category" |
| Action weighting | Separate affinity by action type; compare learned or tested weights | Different actions may carry different evidence; do not assume fixed weights |
| Recency | Recency-weighted affinity using the history time gaps | Test whether recent actions add predictive value |
| Repeat | Candidate already in history, and with which action | Prior interest or repeat interaction; not necessarily a reorder |
| Context | History length, time since last action, query length (number of terms) | Browsing burst vs returning user |
| Cold flag | Candidate never seen in any history | Evaluate complementary metadata when direct history evidence is absent |
| Item popularity | Interaction count of the candidate in training histories | Head vs long tail |

Interim report: describe these and give descriptive statistics for the ones already computed. Full engineering is not required until the final submission.

**History-match checks (5,000 complete records):** exact-product matches are strong but cover only 0.79% of candidates; shop matches cover 7.16%, brand 22.69%, and category-path matches cover 75.17% at L1 to 37.59% at L4. Query-less actions comprise 64.75% of sampled history and also provide useful exploratory ranking signals. Retain both history sources. These comparisons do not select an architecture or establish source reliability independently of history volume. Notebook 02 now uses the same ancestor-path definitions as notebook 04 and reports missing candidate metadata explicitly.

---

## 6. Sampling and scaling plan

- **Interim raw summaries:** full behaviour and catalog files, streamed into compact arrays/aggregates.
- **Interim engineered features:** uniform sample of 5,000 complete records, seed 4222, consistent across notebooks 02-04. No model split is assigned yet.
- **Sampling unit:** whole search records. Preserve all candidates and history; look up metadata against the complete catalog rather than sampling catalog rows.
- **Model development remains open:** select a manageable sample size after this exploration (30,000-50,000 is an option, not a commitment). Make any split by whole record and save its indices.
- **Evaluation:** full, un-downsampled slates; exclude file position and use label-independent tie handling. Fix gain definitions and all-zero treatment before model comparisons.
- **Population features:** full-history frequencies are `_eda` descriptors in the interim. Future models derive population features from training records only; supervised aggregates are out-of-fold within training.
- **Scale carefully:** more records require rerunning metadata lookup and reporting the new scope. A uniform sample addresses our sampling choice, not the source dataset's selection or logging biases.

---

## 7. Modelling plan (after the interim report)

1. **Baselines:** random order; popularity order; simple category-affinity heuristic.
2. **Candidate models (not yet selected):** logistic regression or boosted-tree scoring/ranking can test explicit features; the previous sequence-based hybrid provides a recommender baseline and a possible starting point for adaptation. Select the main model based on useful signals, comparison results, and a manageable scope.
3. **Evaluation:** NDCG@10, MRR, Recall@k on full test slates. Break results down by segment: cold vs warm candidates, short vs long history, query-overlap strength (definitions to fix before modelling).
4. **Prior-work comparison (planned benchmarking):** Team 3's repository (https://github.com/myathetchai/bt4222-team3-jdsearch) used an LSTM+attention+NCF hybrid and framed the task as 4-class classification. Reproduce a suitable baseline under a shared evaluation protocol and distinguish corrections from the effects of richer inputs or architectural changes. Observed issues from their notebooks:
   - They downsampled negatives to 4 per positive, shrinking evaluation lists. Their reported Hit Rate@10 is not directly comparable to full-slate ranking; rerun to quantify the effect.
   - They report accuracy, precision, recall and F1. The unweighted model predicted class 0 for 98.7% of samples; the ordinal variant collapsed to class 1 for about 90%.
   - The main history attention is not conditioned on the current query, which is not used by the main model.
   - Candidate-catalog filtering can discard historical products; the GRU variant also splits candidate pairs before regrouping. Audit and separate these corrections from input/architecture improvements.
5. **Conditional extension:** query-dependent history attention or another focused adaptation if simpler comparisons reveal a limitation it can address. Compare adaptive and non-adaptive models with the same information. Recency-weighted affinity is a feature idea; it does not require a sequence architecture.

---

## 8. Interim report checklist (due 4 Oct)

**Format:** cover page with title, group number and member names; 1.5 line spacing; Arial/Calibri/Times New Roman 11 pt; normal margins; one column; PDF or DOCX.

The notebook supplies the data foundation below; completion of the report and team review are separate tasks.

- [ ] Draft Part 1: concise business objective, grouped inputs and graded target (§2).
- [ ] Write 2.1 from the full-data overview, published collection period and explicitly scoped 5,000-record feature sample.
- [ ] Write 2.2 from slate/history distributions, exclusive labels and grade thresholds, file-order audit, feedback semantics, popularity and raw intervals. Explain why display-rank CTR and true event-transition conversion rates are unavailable.
- [ ] Write 2.3 using the feature dictionary, numeric statistics, categorical counts and actual term lengths. Group related features in the report to keep it concise.
- [ ] Summarise metadata missingness, category-parent reuse, source selection and time interpretation.
- [ ] Add the verified query/history findings with their exact scope and exploratory status; no architecture commitment is needed.
- [ ] Add full member names, review the text/figures as a team, export and submit the report.

---

## 9. Open decisions for the team

1. Select the model family and training objective after exploration; keep the graded re-ranking task as the foundation. Define evaluation gains and the treatment of all-zero slates before comparing models.
2. Model-development sample size and grouped split? Interim features already use a fixed 5,000-record sample; raw summaries are full-data.
3. Who computes which interim statistics (split by report section)?
4. Where do shared processed artefacts live (Drive vs repo)? The raw data must never be committed.
5. Audit relative-time units/spans before making recency or calendar claims; the published collection period and source all-zero test exclusion are documented.

---

## 10. Suggested timeline

| Date | Milestone |
|---|---|
| 2–3 Oct | Compute remaining statistics; write report sections |
| 3–4 Oct | Team review; export to PDF/DOCX; submit by 11:59 PM 4 Oct |
| Week 7 onwards | Feature engineering and baselines (note: TA checkpoint in Week 7) |
| Mid Oct | Main models and evaluation; midterm 12 Oct (Weeks 1–8) |
| Week 11 | Final consultation with the lecturer |
| 9 Nov | Code and data artefacts on GitHub; PDF with links on Canvas |
| 10–11 Nov | Report, slides, presentation |

AI use must be logged in `AI_LOG.md` as work progresses (one entry per substantive commit, as the log's rules describe).
