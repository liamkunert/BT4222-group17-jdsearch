# E12: Independent, bounded data-generation audit

Date: 26 October 2026. Source checkout: `feat/baselines`, `de7e407` before audit edits. No model training, GPU computation, test-label analysis, or changes to existing model/feature code.

## What was actually verified

The preceding conversational review inspected the source paper, documentation and selected implementation, but did not run fresh data analysis. This audit adds direct empirical verification. Its conclusions apply to the released dataset and existing split, not to production causal effects.

- Parsed all **133,831 training and 20,000 validation records**, including 13,725,099 candidate occurrences. Held-out test lines were skipped before parsing their fields. Reading through a shared file is not a chronological evaluation.
- Independently reconstructed the three population features and exact-product personal-history counts for **all 1,781,573 validation candidates**.
- Evaluated 22 fixed single-signal rankings on all **19,772 eligible validation searches**. No hyperparameter search or model fitting. Exact random-tie expectation and linear gains; all released candidates retained.
- Ran whole-search paired bootstrap intervals, 1,000 resamples, seed 4222. Three important differences were also checked with a query-cluster bootstrap preserving search-weighted point estimates.
- Compared engaged/zero candidate pairs within searches, including restrictions to equal historical popularity counts.
- Scanned all **12,141,247 catalogue rows** to independently reconstruct six features on a fixed random sample of **300 validation searches / 27,540 candidates**. This is sample verification, not verification of every metadata feature everywhere.
- Checked persisted E11 per-search results, model preparation and training/scoring code. Did not repeat neural training or reconstruct unavailable probabilities.

Reproduction: `notebooks/exploration/data_generation_audit.ipynb`. Machine-readable evidence: `outputs/data_generation_audit/`; principal summary tables are also copied to `docs/audit_e12/`. Large intermediate outputs remain ignored by Git. The notebook states which checks are exploratory follow-ups and the limits of their interpretation.

## 1. Integrity: the checked inputs and reported reference metrics pass

Across the 153,831 inspected records:

| Check | Result |
|---|---:|
| Duplicate candidate IDs within a search | 0 records |
| Candidate/label length mismatch | 0 |
| History product/type/query/gap length mismatch | 0 |
| Negative time gaps | 0 records |
| Nonzero initial placeholder gap | 0 records |
| All engaged candidates before all zeros | 153,831 / 153,831 |

Across the complete validation feature table:

| Independently reconstructed quantity | Mismatches |
|---|---:|
| Candidate identities and labels, aligned by search and product | 0 |
| Own-history exact-product event counts | 0 |
| Training candidate exposure count | 0 |
| Training history event count | 0 |
| Out-of-fold engagement rate, including fold-specific prior | 0 at stored float32 precision |

The engagement-rate maximum difference before rounding was 2.69e-8. Reconstruction uses the actual fold assignment, not a simplified full-training rate.

Independent metric calculation reproduces the reference results: random 0.084481, history popularity 0.340944, exposures 0.315018, engagement rate 0.244990, exact-product history 0.181985, recent-click exact matches 0.155351, title Jaccard 0.097307, BM25 0.092979. Selected searches agree with the shared evaluator to floating-point precision. Exhaustive small-list permutations additionally test the expectation calculation, including ties crossing a cutoff.

The 300-search metadata reconstruction found zero mismatches for catalogue presence, pooled exact product, shop on other products, brand on other products, L3 ancestor-path matches, and title Jaccard. This checks 165,240 feature values, including missing-value semantics.

**Contained conclusion:** no error was detected in these quantities. This does not certify every feature, training procedure, or the upstream dataset exporter. Engaged-first file order is confirmed and must remain inaccessible to models and tie-breaking.

## 2. Popularity survives both timing and repeat-event checks

Historical popularity currently counts events, not distinct users. Each row represents one sampled user; the alternative distinct-user count contributes at most one count per training row and product.

| Fixed ranking signal | NDCG@10 | Difference from current history-event popularity, paired 95% CI |
|---|---:|---:|
| Current historical event count | 0.340944 | Reference |
| Distinct training users | 0.340800 | -0.000144 [-0.001412, +0.001104] |
| Events >24 hours before their donor search | 0.336950 | -0.003995 [-0.004924, -0.003139] |
| Distinct users with an event >24 hours old | 0.336961 | -0.003983 [-0.005404, -0.002599] |
| Events >48 hours before their donor search | 0.334582 | -0.006362 [-0.007540, -0.005240] |
| Events >7 days before their donor search | 0.324162 | -0.016783 [-0.018677, -0.015030] |

The >24-hour version retains **98.44% of the current gain above random**. The small timing difference is statistically distinguishable from zero, but is not an explanation for most of the popularity advantage. Distinct-user counting does not materially change overall performance in this comparison. The query-cluster bootstrap gives the same substantive conclusions.

Because target searches share a calendar date, an event strictly more than 24 hours before its own target search precedes every target search that day, assuming the supplied date and gap semantics are correct. This is a conservative historical-event sensitivity check, not an exact common timestamp cutoff. Selection of the donor users still depends on activity on the target day; catalogue timing and training-label timing are not repaired by this check.

The >7-day comparison also changes action composition: clicks are absent from that training-history subset. Its effect cannot be attributed solely to staleness. Standalone training-history counts by type score CLICK 0.320768, CART 0.331093, ORD 0.283861 and FLW 0.121005; these mix coverage, retention and signal quality and are not causal action-importance estimates.

**Decision:** keep popularity as a strong reference. Downgrade the hypotheses that repeated actions or same-day history account for most of its dominance. Continue to distinguish history events from same-day candidate exposure counts and target engagement rates. Do not assert that an optimistic base necessarily makes personalization gains conservative.

Code inspection also confirms that the existing `MIN_AGE_DAYS` filters personal history but does not filter the `in_history` population accumulator. It is not a substitute for this population-lag experiment.

## 3. Personal exact matches depend strongly on the most recent evidence

| Personal exact-product count used for ranking | NDCG@10 | Difference from unrestricted exact-product count, paired 95% CI |
|---|---:|---:|
| All own-history events | 0.181985 | Reference |
| Events at least 1 minute old | 0.166067 | -0.015917 [-0.017484, -0.014367] |
| Events at least 10 minutes old | 0.146744 | -0.035240 [-0.037546, -0.033056] |
| Events at least 1 hour old | 0.139098 | -0.042887 [-0.045438, -0.040454] |

Removing ten minutes removes 36.14% of the exact-match gain above random; removing one hour removes 43.98%. These are untrained exact-match rankings, not retrained full-model ablations. They establish sensitivity to recent evidence, not leakage. Legitimate re-finding, session intent, and attribution/boundary problems remain observationally compatible.

Only 3,115 eligible searches (15.75%) contain an engaged candidate previously observed in the user's own history. Among the remaining 16,657 searches, other-product shop matching still reaches 0.131117 versus random 0.084639. This label-defined subgroup is descriptive, cannot be selected at inference, and does not prove improvement beyond popularity. It does show that all shop signal is not confined to searches with a previously seen engaged product.

**Decision:** retain recent exact matches, but complete the planned retrained safety-gap checks before making claims about the final model. Preserve other-product matches and a non-personal fallback.

## 4. Personal and lexical signals retain conditional discrimination

For each eligible search with both engaged and zero-labelled candidates, compare every engaged/zero pair. A signal gets 1 when it ranks the engaged product higher, 0 when lower, and 0.5 for a tie. Average pairs within each search, then average searches. This is binary pairwise concordance, **not NDCG or a predicted model increment**.

For pairs with **exactly equal training historical event counts**, there are 982,763 comparisons in 11,216 searches:

| Signal | Mean concordance | Whole-search bootstrap 95% CI |
|---|---:|---:|
| Historical event count | 0.5000 | All ties by construction |
| Own exact-product history count | 0.5384 | [0.5361, 0.5408] |
| Own shop matches on other products | 0.5221 | [0.5196, 0.5248] |
| Own brand matches on other products | 0.5161 | [0.5127, 0.5191] |
| Query-title Jaccard | 0.5499 | [0.5439, 0.5557] |

A broader restriction using `floor(log2(history_count + 1))` and equal presence/absence of lexical overlap retains 1,016,521 pairs across 17,294 searches. Concordance remains 0.5464 for exact matches, 0.5140 for shop-other, and 0.5068 for brand-other.

Limitations: exact-count matching changes the population and includes zero-count pairs; this controls one popularity statistic, not all metadata, exposure, source or selection effects. Unobserved labels are treated as zero as in the benchmark. Intervals are exploratory and not adjusted for multiple comparisons.

**Decision:** there is a concrete reason to test personal and lexical features in a learned ranker despite weak standalone NDCG. Their incremental value over a trained multifeature base remains untested.

## 5. Candidate structure supports query-conditioned sets, not arbitrary catalogue negatives

The original paper describes exposed products, deduplicated and capped at 200. Its training negative-sampling statement should not be confused with construction of evaluation candidates. See [the source paper, section 3.1](https://playbigdata.ruc.edu.cn/dou/publication/2023_SIGIR_ps_dataset.pdf) and [official data format](https://github.com/rucliujn/JDsearch#data-content-and-format).

Empirical checks on the 153,831 non-test records:

- Candidate-count median 90, interquartile range 77-95, range 1-200.
- Length 90 occurs 23,656 times; length 30 occurs 4,689 times, length 60 occurs 4,529 times and length 200 occurs 4,664 times (3.03%).
- Exactly four zeros per positive occurs in only 365 records, approximately 0.24%. This is not the Team 3 downsampled-list protocol.
- Candidate count and number of positives have Spearman correlation 0.3798. This could reflect opportunity to interact or construction, and does not identify direction or cause.
- Among 5,551 comparisons of repeated validation queries, mean candidate-set Jaccard is 0.0697 and median 0.0582. Comparisons use up to three preceding saved lists per exact query; this is a bounded diagnostic, not every possible pair. Identical queries do not normally share identical candidate sets.
- In the 300-search reconstruction sample, 92.29% of candidate/query pairs with available titles share a title term, versus 12.33% for 30,000 background query/title pairs. Background titles come from a systematic catalogue sample with seeded starting offset, then 100 sampled titles per query. This is a coarse comparison, not an unbiased sampling-mechanism estimator.
- Across the full validation set, 89.89% of zero-labelled candidates have positive title overlap; even ignored candidates are usually lexically related.

**Contained conclusion:** a hypothesis of largely arbitrary, query-independent catalogue negatives is inconsistent with the strong query conditioning observed here. Query-conditioned negative sampling remains possible. Peaks around multiples of 30 are compatible with pagination or export rules but do not establish them. We still cannot recover original display positions, the cap-selection rule, or whether the list represents one page, multiple pages, or aggregated exposures.

## 6. Missing metadata is associated with historical age

In the fixed 300-search sample:

| Historical action block | Events | Missing catalogue row |
|---|---:|---:|
| CLICK, 0-7 days | 14,243 | 0.92% |
| CART, 0-7 days | 2,144 | 0.70% |
| CART, 7-90 days | 16,946 | 5.59% |
| ORD, 0-7 days | 350 | 0.29% |
| ORD, 7-90 days | 3,005 | 2.73% |
| ORD, 90+ days | 6,996 | 10.65% |

Search-cluster intervals are in `docs/audit_e12/sample_history_metadata_intervals.csv`. The 350 recent orders are sparse; do not treat their point estimate as precisely known. This is descriptive evidence from 300 searches, not a full-history missingness census.

By contrast, only 7,861 validation candidate occurrences (0.44%) lack a catalogue row; their engagement rate is 1.14%, versus 2.09% with metadata. None of those missing-catalogue validation candidates has a purchase label. This is an association, not evidence that missing products cannot be purchased.

**Decision:** broad-match age effects can partly reflect age-dependent observability. Add per-window metadata coverage/known-event denominators when practical, and distinguish observed match count from available evidence. Do not infer the strength of latent older preferences directly from unnormalized broad-match rankings. Product IDs remain usable even when attributes are missing.

## 7. Purchase and re-finding hypotheses have limited observed coverage

Among the 2,405 validation candidate occurrences labelled purchase:

- 8.02% have a recorded previous cart event on the exact product.
- 6.53% have a recorded previous order on the exact product.
- 14.26% have any recorded exact-product history.
- 4.86% have an exact-product event within ten minutes.

The corresponding prior-cart fraction among zero-labelled candidates is 0.27%, so prior carts are strongly associated with eventual purchase labels. However, **91.98% of purchase-labelled candidates do not have an observed prior exact-product cart**. The claim that most purchase labels are visibly identifiable earlier-cart checkouts is not supported. Censoring, missing channels, and different product/SKU identity can hide prior carts; therefore the converse behavioral claim is also not identified.

## 8. E11 is numerically corroborated, but its scope needs precise wording

The saved per-search outputs contain exactly the same 19,772 eligible validation searches. Their random and popularity references match the independent reconstruction to 2.22e-16. All seven rung means match the results registry to rounding precision. R5 minus popularity is -0.044406, paired 95% CI [-0.047684, -0.041018]. This validates the saved comparison, not the neural training execution itself.

Code and prepared arrays establish:

- 39.15% of validation candidate occurrences occur in the 40k development lists; 37.62% occur in the approximately 36k actual fitting lists after the inner holdout. Coverage against all 133,831 training lists is 56.10%.
- 40.60% occur in the full training histories. Candidate-list coverage and history coverage are different; user-history and candidate embedding tables are also separate in this architecture.
- The sequence called `full` is truncated to the latest 200 actions. Prepared lengths equal `min(raw_history_length, 200)` exactly; 4,726 validation histories (23.63%) are shortened. Full-history metadata summaries may still use more events; the sequence encoder does not.
- Checkpoint selection and learning-rate scheduling use weighted classification loss on the inner validation set, not NDCG. Best epochs 2-3 do not establish where ranking performance peaked.
- Inverse-frequency cross-entropy weights in the fitting full lists are approximately [0.001014, 0.068646, 0.205000, 0.725340] for labels 0/1/2/3. Purchase receives about 715 times the per-example weight of zero. The code subsequently computes expected grade from uncorrected softmax outputs.

This verifies the conditions behind the calibration concern; it does not prove recalibration would improve NDCG. No saved checkpoint or per-candidate probability artifact was available in the inspected folder, so that experiment was not run. Weighted-CE probabilities are generally tilted; an idealized inverse-weight correction is a diagnostic, not a guaranteed repair to a fitted, sampled model.

**Decision:** E11 supports moving away from this implementation, not rejecting neural personalization generally. Use 'history filtering removed; sequence capped at 200' and specify the development/fitting population for coverage statistics.

## 9. Ablations remain useful but do not isolate every conceptual factor

For all validation rows, pooled product/shop-other/brand-other counts are exactly recoverable both by summing their action-type counts and by summing their linked/query-less counts. Six checked identities have zero mismatches. The representation groups overlap informationally, so drop-one-group effects are conditional on what remains.

Recent activity is recoverable from the recent CLICK/CART/ORD volume counts for 19,950 of 20,000 validation searches; follow events and boundary/straggler cases require care in the remaining 50. Removing C2 alone therefore leaves almost all of this volume signal. Removing both C1 and C2 still leaves match-recency and recent matching evidence in H3/H4/Q1; that operation should be called 'remove explicit context features,' not 'remove all context.'

Within every tested list-length bin, popularity beats random. This excludes an explanation based solely on averaging easy short lists with harder long lists, while allowing residual variation in difficulty and selection. Keep paired model-minus-base differences and list-length reporting in the final analysis.

## What remains unresolved or deliberately skipped

| Question | Why this audit cannot settle it |
|---|---|
| Does personalized LightGBM improve over the trained non-personal base? | No model training was performed. Conditional pairwise signal is not a model result. |
| Does a full model retain its gain after history safety gaps? | Only fixed exact-product rankings were recomputed. Full retrained ablations remain necessary. |
| Does matched donor-history replacement eliminate personalized gains? | Not run; the full learned-model control remains a useful later experiment. |
| Is popularity preference, exposure policy, availability or promotion? | These mechanisms are not separately identified without additional logs or interventions. |
| Are candidates from one page, several pages or a query-conditioned sample? | Position, exporter and cap-selection details are unavailable. |
| Are recent matches leakage or legitimate re-finding? | Timing sensitivity alone cannot identify attribution semantics. |
| Would probability correction repair E11? | Saved per-candidate probabilities/checkpoints were unavailable; retraining was skipped. |
| Will the result generalize to future dates or all search users? | Single-day, last-search selection and missing absolute timestamps remain. |

These are limits to the evidence, not evidence of bugs. Intervals describe sampling variation within this benchmark, not uncertainty about the upstream data-generation mechanism or future-day performance. Repeated validation analysis also means these are development findings; reserve the held-out test set for the preselected final models.

## Updated priorities

1. Retain current popularity as a reference and carry the historical-only alternative into the next model comparison; the raw-event timing concern is now bounded and small for this signal.
2. Train the planned non-personal LightGBM base and history variants. Personal and lexical signals retain conditional discrimination, so this is justified rather than speculative.
3. Run retrained history safety gaps: exact-product evidence is measurably sensitive to the last minutes.
4. Include metadata coverage in the interpretation of broad-match age effects, and ideally in the feature audit/ablations.
5. Correct the ablation and E11 wording above. Do not spend the remaining deadline on a new large neural architecture before these comparisons are complete.
