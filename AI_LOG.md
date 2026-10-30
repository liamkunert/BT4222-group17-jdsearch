# AI Interaction Log

This log records only meaningful AI-assisted technical decisions that may be useful for the final report appendix. It is not a chat history.

## Rules

1. Add at most one entry per substantive commit or pull request.
2. Combine all related prompts and discussion into one outcome-focused summary.
3. Keep each entry under 120 words.
4. Log an interaction only when AI materially influenced a modelling, data, evaluation, or non-trivial debugging decision.
5. Do not log routine syntax help, formatting, Git commands, wording changes, or generated boilerplate.
6. Do not include raw chat transcripts, full prompts, or large code excerpts.
7. The responsible group member must review the entry and state how the AI output was checked or corrected.
8. Do not create entries for commits that only update this log or other documentation.

## Entry template

### YYYY-MM-DD - Short title

- **Member:**
- **Related work:** Commit, pull request, or notebook
- **Objective:**
- **AI contribution:**
- **Critical evaluation:**
- **Final action and validation:**

## Entries

### 2026-10-30 - Two independent AI reviews of the final results

- **Member:** Liam Kunert
- **Related work:** E33, `docs/FINDINGS.md` section 11, `notebooks/06_diagnostics.ipynb`
- **Objective:** Check the final results, diagnostics and conclusions before the single test run.
- **AI contribution:** A Claude subagent (no test data) and an external LLM reviewed code, outputs and claims; both found no leakage, flagged overclaims and the missing test-scoring path.
- **Critical evaluation:** Re-computed the disputed numbers before accepting them: displacement within own-product searches (-1.8 points), cold products half of the missed engagement, E30 mixing subsampling with seeds. Rejected nothing material; kept the pre-registered final model.
- **Final action and validation:** Claims reworded, 06 extended and re-run on Colab; test run moved into one reproducible Colab pipeline. DRAFT: member to review.

### 2026-10-29 - Two independent AI reviews of the LambdaMART phase

- **Member:** Liam Kunert
- **Related work:** E25-E26, E30, `docs/FINDINGS.md` section 11
- **Objective:** Check E14-E24 for leakage, evaluation problems and overclaims before the neural models and the report.
- **AI contribution:** A Claude subagent (training data only) and an external LLM reviewed code, saved outputs and conclusions; the subagent proposed a fairer comparison rule and found possible post-search actions in 2-5 s final gaps.
- **Critical evaluation:** No critical issue; both confirmed the pipeline. Accepted after verifying them here: overclaims ("adds nothing", the 70/30 split, the E24 reading, CF robustness) and the near-clamp leak. Minor points deferred to one pass.
- **Final action and validation:** Four checks (E30): CF not robust across seeds, fairer rule reaches 88% of the gain, short gaps reported as sensitivity; wording corrected. Reviewed by Liam.

### 2026-10-27 - Independent AI review of the model plan

- **Member:** Liam Kunert
- **Related work:** `PROJECT_PLAN.md` section 5 (`05_models`)
- **Objective:** Choose models that fit our data and findings, cover lecture topics sensibly and fit 13 days.
- **AI contribution:** An external LLM reviewed our proposal (LambdaMART, collaborative features, neural attention) and gave concrete formulations and stop rules.
- **Critical evaluation:** Accepted: GCN, full Transformer and stacking dropped; cross-fitted lagged CF graph; feature MLP as neural control; popularity residual. Adjusted: ablations on the 40k subsample (memory); LightGBM's NDCG for early stopping, our evaluator for final comparisons.
- **Final action and validation:** Plan rewritten with success criteria and time boxes. Reviewed by Liam.

### 2026-10-26 - Two independent AI data-generation audits

- **Member:** Liam Kunert
- **Related work:** E12-E13, `docs/DATA_GENERATION_AUDIT.md`, `notebooks/exploration/data_generation_audit.ipynb`
- **Objective:** Find dataset artefacts that could distort our signals before final modelling (after missing the observation windows).
- **AI contribution:** A Claude subagent audited training data; an external LLM reconstructed validation features and tested timing and coverage hypotheses.
- **Critical evaluation:** Only the subagent found the clamped 1-second gap (post-search actions) and the removed same-query history; we re-verified both on all records. The external audit confirmed every reference number and added metadata-coverage and wording issues.
- **Final action and validation:** Clamped searches excluded, features rebuilt (v3), findings corrected. Reviewed by Liam.

### 2026-10-23 - Independent AI review of the window re-check

- **Member:** Liam Kunert
- **Related work:** `notebooks/exploration/window_recheck.ipynb`, experiments E03-E06
- **Objective:** Check whether the re-check conclusions (history signals by window; interim context lead) hold.
- **AI contribution:** Claude Code ran the analysis and drafted interpretations; a second LLM, given a neutral prompt and the repository, critically reviewed them and recomputed parts.
- **Critical evaluation:** Numbers held, but three claims overreached: "session context irrelevant" (offsetting coverage and conditional gain), "equal evidence quality per action" (different search subsets), "no leakage" (weak query test). It also found a documentation error and LightGBM's default exponential gains.
- **Final action and validation:** Claims weakened, errors fixed, evaluation guardrails added; context becomes a model ablation. Reviewed by Liam.

### 2026-10-25 - Two independent AI reviews of feature set v1

- **Member:** Liam Kunert
- **Related work:** `notebooks/03_features.ipynb` (v1 to v2), experiments E07-E08
- **Objective:** Find leakage, bugs and overreaching claims before training models on the features.
- **AI contribution:** A Claude subagent re-implemented 12 features (0 mismatches) and decomposed the popularity signal; a second LLM reviewed the code and the planned ablations.
- **Critical evaluation:** No leakage, but popularity counts were distributed differently for training and validation rows, missing text gave 0 instead of unknown, and our popularity explanation was contradicted. The ablation ladder could not separate windows from context.
- **Final action and validation:** Rebuilt as v2 with distribution and permutation checks; ablation design rewritten. Reviewed by Liam.
