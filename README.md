# BT4222 Group 17 - JD Search Recommender Systems

This repository contains Group 17's BT4222 project on developing and evaluating recommender systems using the JD Search dataset.

New group members should follow [ONBOARDING.md](ONBOARDING.md).

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

The project uses Python 3.12:

- Python 3.12.10 for local development
- Python 3.12.13 in the Google Colab 2026.07 runtime
- Package versions listed in `requirements.txt`

To set up the project locally, install Python 3.12 and create a virtual environment.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

In VS Code, select `.venv` as the notebook kernel.

In Google Colab, select the `2026.07` runtime. The required libraries are already installed in that runtime, so `requirements.txt` is only used for local setup.

## Notebooks

- `00_setup_and_data_access.ipynb`: locates the dataset and verifies the local or Colab environment.
