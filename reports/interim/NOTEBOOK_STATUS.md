# Interim notebook status — 3 October 2026

`notebooks/02_interim_report.ipynb` is the consolidated evidence source for report drafting. All **29 code cells** executed successfully; outputs, **21 tables** and **8 figures** are saved. The overview was additionally refreshed to show the complete product count.

## Scope

- Raw summaries: all **173,831 records**, **15,510,012 candidate occurrences**, **26,667,260 historical actions**, and **12,141,247 catalog rows**.
- Complete product universe: catalog rows plus **731,389 observed IDs missing metadata** = **12,872,636 products**, matching the paper.
- Engineered features: **5,000 uniformly sampled complete records**, seed **4222**, with **449,052 candidates** and all supplied history retained. This is an exploratory feature sample, not a model train/test split.
- Product-title and other text lengths now use the complete applicable files and actual term boundaries; no file-prefix title sample is used for the main statistics.

## Corrections

- Exclusive labels and cumulative grade thresholds replace unsupported event-funnel/conversion claims.
- The file-order audit is explicitly separated from unavailable display-rank CTR.
- The published collection period is distinguished from unavailable absolute row timestamps. Raw intervals are reported; hours/days assume seconds. One record's derived history span exceeds a year and remains flagged for audit.
- Text matching uses whole term IDs, and category matching uses ancestor paths consistently with notebook 04.
- Missing candidate metadata yields unavailable attribute/text features; missing history metadata may hide matches. Lookup includes both candidate and historical products against the full catalog.
- Feature-mean ratios are described as pooled associations, not engagement multipliers, causal effects or proof of model improvement. Population frequencies/cold flags are labelled `_eda` and require training-only versions later.
- The interim does not fix an architecture, model-development sample size or train/test split.

## Validation

Raw list lengths, candidate labels, initial time placeholders, nonnegative gaps and catalog-ID uniqueness passed. Feature sample sizes, label counts and all 21 source/attribute positive-match counts agree with the diagnostic notebooks. Numeric missingness/observation denominators and label/action sums passed. Frequency-based text statistics were checked against pandas, and a small synthetic log independently checked time alignment, missing metadata, coldness denominators and actual feature values. Key exported figures were visually inspected.

## Remaining work

Draft the report from these scoped tables; select representative feature groups instead of reproducing all 49 dictionary rows. Add the cover-page member names, review the interpretation and formatting as a team, export to PDF/DOCX and submit. Model development and the relative-time anomaly audit are subsequent work, not claimed completed here.

## File organisation

The main notebook stays in `notebooks/`; detailed experiments are in `notebooks/diagnostics/`. Reusable code is in `scripts/`. All generated CSV/JSON tables and PNG figures live under ignored `outputs/interim/`, and existing exports were preserved during the move. The main notebook loads diagnostics from that folder; a fresh checkout regenerates them by running the query notebook, then the history notebook, then the main notebook. Written findings remain here in `reports/interim/`. This organisation change updates paths and preserves executed results; it does not rerun the full-data analyses.
