# Group 17 — JDSearch Project Plan

Status: draft for team discussion, 2026-10-02. Interim report due **4 Oct 2026, 11:59 PM** (Canvas). Final code and data due 9 Nov, report and slides 10 Nov, presentation 11 Nov.

Numbers below come from the group's EDA notebook (`JDSearch_Data_Anlaysis.ipynb`) unless marked otherwise. Items marked **[to verify]** still need checking.

---

## 1. One-paragraph summary

Re-rank the products that JD.com's search returns for a user, so that products the user will click, add to cart or buy appear near the top. We score each (user session, candidate product) pair with a **simple, explainable model** (logistic regression and gradient-boosted trees) using hand-built features about the user's history, the query, and the product's brand/category/shop. We evaluate on the **full, un-downsampled candidate list** with ranking metrics (NDCG@10, MRR, Recall@k), and explain the model with coefficients and SHAP values.

---

## 2. Business objective and ML task (interim report Part 1)

- **Business objective:** raise the quality of JD's search results so that shoppers find and buy what they want faster. Purchases matter more than clicks.
- **ML task:** personalised re-ranking of a search result list. Pointwise scoring, then sort by score.
- **Input sample:** one (session, candidate) pair, described by
  - the user's history (items, action types, time gaps, past queries),
  - the current query,
  - the candidate's metadata (brand, 4-level category, shop).
- **Target label:** graded interaction level per candidate: 0 = no interaction, 1 = click, 2 = add to cart, 3 = purchase.
  - Training: a binary "engaged vs not" model is the simplest start. A graded regression is an optional extension.
  - Evaluation: graded labels, so a purchase ranked high scores better than a click ranked high.
- **Decision locked at interim:** dataset (JDSearch) and target (above). Changing either later is penalised by the course, so confirm as a team before submitting.

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
| `history_time_list` | Gaps between actions, plus the gap from the last action to the test query. It has one more element than the other history lists. The unit is undocumented; assumed seconds. |

`product_meta_data.txt`: 12,141,247 products with `wid`, `name`, `brand_id`, `brand_name`, `cate_id_1..4`, `cate_name_1..4`, `shop_id`. All text is anonymised term IDs.

### 3.2 Mapping to ML terms

| ML term | In this data |
|---|---|
| Example | One (session, candidate) pair. 173,831 sessions × about 89 ≈ 15.5M pairs |
| Group | The candidate list of one session. Items in it compete with each other. |
| Features | Facts about the user history, the query, the product, and how they relate |
| Label | 0 / 1 / 2 / 3 per candidate |
| Positive / negative | Positive = label ≥ 1. A negative (0) is **exposed but not engaged**, which is a real signal. Unexposed products are unobserved, which is different. |

### 3.3 Key facts from the EDA

- **Funnel (candidates):** 15,510,012 total. Label 0: 97.9%; click 1.45%; cart 0.49%; purchase 0.13%. Overall positive rate about 2.07%.
- **Slate size:** mean 89.22, max 200.
- **History actions:** 26,667,260 in total (CART 11.5M, CLICK 8.3M, ORD 6.8M, FLW 25k).
- **Cold start:** 80.54% of candidate products never appear in any user's history. Cold users (fewer than 3 history items) are only 2.34%.
- **Queries:** 111,556 distinct across 173,831 rows. 62.14% contain a term matching a product name, brand or category value. The same query gets very different candidate lists for different rows (mean Jaccard overlap about 0.13), so results look personalised or time-varying.
- **Time:** 10.52% of history intervals are zero (burst actions). The median gap from last action to the test query is about 19,287 (about 5.4 h if seconds). There are no absolute dates, so the **time span cannot be reported**.
- **Users:** there is no user ID. Histories barely overlap (Jaccard about 0.0002), so each row is treated as a different user. **[to verify against the paper]**
- **Categories:** the four levels are hierarchical and level-specific (13,701 of 13,702 IDs appear at only one level).

### 3.4 Data limitations to state in the report

1. **Candidate order is not display order.** On the first 40,000 rows of the raw file, 98.8% of sessions with a positive have the positive as the **first** candidate, and 88.6% of all sessions have labels sorted descending. Position-based analysis (CTR by rank) would just measure how the file was written. We therefore state that **position bias cannot be studied** (the course lecturer confirmed this is acceptable), and we **shuffle candidate order** before building features or splits.
2. **Sessions appear pre-filtered to contain an interaction:** 98.8% of the 40,000 rows checked have at least one positive. We cannot study whether a search leads to any interaction at all. **[to verify on the full file]**
3. **No timestamps:** only relative gaps. A time-based train/test split is not possible directly.
4. **Anonymised text:** we cannot read queries or product names. We work with IDs and overlaps.
5. **Sampling introduces selection bias** (see §6).

---

## 4. Concepts we rely on (short glossary)

- **Impression:** a product shown to the user. All candidates are impressions.
- **Pointwise ranking:** score each candidate independently, then sort. Simple and explainable.
- **Graded relevance:** labels have levels of importance (0–3), not just yes/no. A purchase is worth more than a click.
- **NDCG@10:** score of the top 10 where each item's gain is its grade, discounted by position (higher positions count more), divided by the best possible score. 1.0 = perfect ordering.
- **MRR:** 1 divided by the rank of the first engaged item, averaged over sessions.
- **Recall@k:** the share of a session's engaged items that appear in the top k.
- **Cold start:** items (or users) with no history signal. We handle it with metadata-based features (brand/category/shop) instead of item IDs.
- **Why not accuracy/F1:** about 98% of candidates are 0, so "predict 0 for everything" gets about 98% accuracy.

---

## 5. Feature plan (starter set; full feature dictionary goes in the report)

| Group | Feature idea | Intuition |
|---|---|---|
| Query–item match | Query terms match the candidate's brand / category / name | "User searched for the brand and this is that brand" |
| User affinity | Count of past interactions with the candidate's brand, category (each of 4 levels), shop | "User often buys in this category" |
| Action weighting | Affinity weighted by action type (ORD > CART > CLICK) | A purchase says more than a click |
| Recency | Recency-weighted affinity using the history time gaps | Recent behaviour matters more |
| Repeat | Candidate already in history, and with which action | Reorders |
| Context | History length, time since last action, query length (number of terms) | Browsing burst vs returning user |
| Cold flag | Candidate never seen in any history | Model must rely on metadata |
| Item popularity | Interaction count of the candidate in training histories | Head vs long tail |

Interim report: describe these and give descriptive statistics for the ones already computed. Full engineering is not required until the final submission.

---

## 6. Sampling and scaling plan

- **Unit of sampling: the session (whole candidate list).** Never sample individual candidates, which would break the ranking problem.
- **Start with a random subsample of sessions** (suggested 30,000–50,000) because parsing all lists in pandas exceeded 12.7 GB RAM on Colab.
- **Fix a random seed and save the sampled session IDs** in a file so results are reproducible and extendable.
- **Do not downsample negatives.** Evaluate on full slates. If training needs fewer negatives for speed, downsample **only in training** and evaluate on full lists.
- **Split by user/session** (for example 70/15/15) so no user is in two splits. A temporal split is not available (§3.4).
- **Scaling to the full data later: yes.** The pipeline should be config-driven (sample size set in one place) and read the data in chunks (for example with pyarrow) so moving from 40k sessions to all 173,831 only means changing a parameter and rerunning everything. Do not mix numbers across sample sizes.
- **Report the bias:** a random user sample is the least biased option. Filtering to heavy users would limit conclusions to heavy users. State this explicitly (the lecturer asked groups to acknowledge selection bias).

---

## 7. Modelling plan (after the interim report)

1. **Baselines:** random order; popularity order; simple category-affinity heuristic.
2. **Main model:** logistic regression (coefficients) and LightGBM (SHAP, feature importance), on the features above.
3. **Evaluation:** NDCG@10, MRR, Recall@k on full test slates. Break results down by segment: cold vs warm candidates, short vs long history, query type (matches brand / category / none).
4. **Prior-work comparison (conceptual):** Team 3's repository (https://github.com/myathetchai/bt4222-team3-jdsearch) used an LSTM+attention+NCF hybrid and framed the task as 4-class classification. Observed issues from their notebooks:
   - They downsampled negatives to 4 per positive, which shrank slates from about 89 to about 9.3 items per user, so their **Hit Rate@10 of 0.978 is close to trivial**.
   - They report accuracy, precision, recall and F1. The unweighted model predicted class 0 for 98.7% of samples; the ordinal variant collapsed to class 1 for about 90%.
   - Deep model, hard to interpret.
   - Item-ID based history encoding, while 80.5% of candidates are cold.
5. **Optional extension if time allows:** a small sequence feature (for example recency-weighted category affinity) or a simple learning-to-rank objective in LightGBM (LambdaRank).

---

## 8. Interim report checklist (due 4 Oct)

**Format:** cover page (title, group number, full names); 1.5 line spacing; Arial, Calibri or Times New Roman 11 pt; normal margins; one column; PDF or DOCX.

- [ ] **Part 1:** business objective and ML task; input sample; target (§2).
- [ ] **2.1 Overview and sampling:** source (JD Search / Liu et al. 2023); sizes; unique users (173,831 assumed), unique items; time span (state: not available); sampling scheme (§6).
- [ ] **2.2 Impression and interaction dynamics:**
  - [ ] Slate length distribution (have mean and max; need histogram and median).
  - [ ] Funnel with volumes and conversion rates (have counts).
  - [ ] Click-through rate by position: **state not studied** and why (§3.4).
  - [ ] Feedback semantics (exposed-but-ignored vs unobserved).
  - [ ] Sparsity: history length distribution, item popularity head vs tail, time gaps.
- [ ] **2.3 Feature dictionary and descriptive statistics:** feature name, description, type/unit; numeric stats (min, max, mean, median, std, missing); categorical (distinct count, examples, missing); text/ID length stats.
- [ ] Add a short "Limitations and risks" section (§3.4).

**Gaps to compute before the deadline:** unique items overall; item popularity distribution; history-length percentiles; slate-length median and histogram; missing-value counts; candidate-order check on the **full** file.

---

## 9. Open decisions for the team

1. Confirm the target: graded labels for evaluation, with binary or graded for training?
2. Sample size for the interim and development phases (30k, 50k, other)?
3. Who computes which interim statistics (split by report section)?
4. Where do shared processed artefacts live (Drive vs repo)? The raw data must never be committed.
5. Confirm with the paper (https://arxiv.org/pdf/2305.14810) whether candidate order, time unit, and session pre-filtering are documented.

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
