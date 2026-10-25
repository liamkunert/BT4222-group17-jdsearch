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
