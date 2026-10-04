# Exploration notebooks

Supporting analyses from the data-understanding phase. They are **not part of the modelling pipeline**; their results are summarised in [`docs/FINDINGS.md`](../../docs/FINDINGS.md), which is what pipeline work should build on. Keep them runnable: the interim report's section 2.4 numbers come from the two validation notebooks.

| Notebook | Purpose | Status |
|---|---|---|
| `query_signal_validation.ipynb` | Query tokenisation, query-title overlap, current vs past query overlap, hard query filter on history | Executed; feeds interim §2.4 and FINDINGS §4 |
| `history_match_validation.ipynb` | Product, brand, shop and category-path matches against history, split by search-linked vs query-less history | Executed; feeds interim §2.4 and FINDINGS §4 |
| `session_context_check.ipynb` | How time since the last action, past-query overlap, query length and history length change the value of history | Executed; evidence for the session-aware hypothesis (FINDINGS §6) |
| `early_eda.ipynb` | The team's first exploratory pass over the raw files | Superseded by `01_data_understanding.ipynb`; kept for reference |

## Run order

All notebooks share the 5,000-record sample (seed 4222) and write tables to the Git-ignored `outputs/interim/tables/`.

1. `query_signal_validation.ipynb`
2. `history_match_validation.ipynb`
3. `../01_data_understanding.ipynb` (cross-checks its features against the tables from steps 1–2)
4. `session_context_check.ipynb` (reads the tables from steps 1–2 and the raw behaviour file)

`python scripts/signal_check_figure.py` redraws the interim report's Figure 5 from the step 1–2 tables.
