# BT4222 Group 17 - JD Search Recommender Systems

This repository contains Group 17's BT4222 project on developing and evaluating recommender systems using the JD Search dataset.

Meaningful AI-assisted technical decisions are recorded concisely in [AI_LOG.md](AI_LOG.md).

## Project status

Data understanding is complete and the interim report is drafted. Next: preprocessing, baselines and models. All exploration results, including a promising lead on search context (time since the last action), are in [docs/FINDINGS.md](docs/FINDINGS.md).

## Repository structure

```text
README.md                        This file: setup and pipeline map
PROJECT_PLAN.md                  Project direction, decisions and timeline
AI_LOG.md                        AI interaction log (required in the final report)
docs/
  FINDINGS.md                    What exploration established and what it means for the pipeline
  dataset-specific-insights.md   The lecturer's dataset hints
  guidelines/                    Course guidelines (interim report, final deliverables)
  interim/                       Interim report draft
notebooks/
  00_setup_and_data_access.ipynb Environment and data checks
  01_data_understanding.ipynb    Full-data summaries, feature dictionary, interim report evidence
  exploration/                   Supporting analyses, not part of the pipeline (see its README)
scripts/                         Analysis modules used by the notebooks
outputs/interim/                 Generated tables and figures (ignored by Git)
data/                            Raw data and temporary arrays (ignored by Git)
```

Pipeline notebooks are numbered by stage (`00_`, `01_`, ...); preprocessing, baselines, models and diagnostics will follow as `02_` onwards. Start with `docs/FINDINGS.md` for the results, or `notebooks/01_data_understanding.ipynb` for the full exploration; the notebook displays the relevant tables, so there is no need to browse individual CSVs.

The project will be developed locally and periodically tested in Google Colab. The JD Search dataset must not be committed to GitHub.

## Data

The authoritative dataset is stored in the shared [Google Drive folder](https://drive.google.com/drive/folders/1YJBaPU-CY-JP458exZQdOogz5a2C-U82?usp=sharing).

For local development, download the files into the repository's `data/` folder:

```text
data/
├── user_behavior_data.txt
└── product_meta_data.txt
```

The `data/` folder contents are ignored by Git. For Colab, add the shared `BT4222 Group Project` folder as a shortcut directly under `My Drive`; the notebook will then use `MyDrive/BT4222 Group Project/data/`.

## Environment

The project uses Python 3.12 and [uv](https://docs.astral.sh/uv/) for Python and dependency management.

The local Python version is pinned in `.python-version`, while project dependencies and their resolved versions are defined by `pyproject.toml` and `uv.lock`.

### Local setup

Install `uv` by following the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

Then, from the repository root:

```bash
uv python install
uv sync
```

`uv python install` installs the Python version specified in `.python-version`, and `uv sync` creates the project's `.venv` and installs the locked dependencies.

PyCharm should automatically detect the .venv when running Jupyter notebooks.
In VS Code, select the project's `.venv` as the notebook kernel.

## Notebooks

- `00_setup_and_data_access.ipynb`: locates the dataset and verifies the local or Colab environment.
- `01_data_understanding.ipynb`: consolidated raw-data summaries, feature dictionary, statistics and report figures. Raw summaries use the full files; engineered features use 5,000 uniformly sampled whole records, seed 4222.
- `exploration/`: query and history validation notebooks, the session-context check and the first team EDA. Their purpose and run order are in [notebooks/exploration/README.md](notebooks/exploration/README.md).

The notebooks use helpers in `scripts/`. In Colab, provide the complete repository checkout, including that folder, in the runtime and open it as the working directory; the mounted Drive folder supplies the raw data. For a fresh set of detailed diagnostics, run the two validation notebooks in `exploration/` before `01_data_understanding.ipynb`, which checks their saved tables against its newly recomputed sample features; its core exploration also runs when those tables are absent.

## Generated outputs and reusable code

`outputs/interim/tables/` contains regenerated CSV statistics and diagnostic JSON summaries; `outputs/interim/figures/` contains exported PNG charts. All of `outputs/` is ignored by Git, so these files do not clutter source changes. Current results also remain displayed in the executed notebooks. A fresh checkout needs the raw data and the notebook run order above to regenerate the detailed exports. Keep selected figures with the report if needed for submission.

The files in `scripts/` are source code, not disposable outputs: `interim_eda.py` supports the main exploration, `query_diagnostics.py` supports query checks, `history_match_diagnostics.py` supports history/category checks, and `signal_check_figure.py` redraws the interim report's Figure 5. The main notebook also reuses their validated matching functions.

Temporary population counts and record samples go under ignored `data/processed/`. The full-data popularity/cold flags are descriptive EDA features; future model versions must calculate population statistics from training records only.
