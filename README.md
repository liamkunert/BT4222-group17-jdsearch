# BT4222 Group 17 - JD Search Recommender Systems

This repository contains Group 17's BT4222 project on developing and evaluating recommender systems using the JD Search dataset.

Meaningful AI-assisted technical decisions are recorded concisely in [AI_LOG.md](AI_LOG.md).

## Project status

Initial project setup.

## Repository structure

```text
notebooks/   Jupyter notebooks for data preparation, modelling, and evaluation
data/        Local dataset copies (not tracked by Git)
```

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


