# Group Member Setup

## 1. Install the required software

Install:

- Git
- Python 3.12
- Visual Studio Code
- The Python and Jupyter extensions for Visual Studio Code

Restart Visual Studio Code after installing Python.

## 2. Clone the repository

```bash
git clone https://github.com/liamkunert/BT4222-group17-jdsearch.git
cd BT4222-group17-jdsearch
```

## 3. Create the local Python environment

This setup is required once per computer. Run it again only if `requirements.txt` changes or `.venv` is recreated.

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

## 4. Add the local dataset

Download the two files from the [shared Google Drive folder](https://drive.google.com/drive/folders/1YJBaPU-CY-JP458exZQdOogz5a2C-U82?usp=sharing) and place them here:

```text
data/
├── user_behavior_data.txt
└── product_meta_data.txt
```

The files in `data/` are ignored by Git and must not be committed.

## 5. Check the setup in Visual Studio Code

1. Open the cloned repository in Visual Studio Code.
2. Open `notebooks/00_setup_and_data_access.ipynb`.
3. Select `.venv` as the notebook kernel.
4. Run all cells.
5. Confirm that both dataset files and the expected package versions are shown.

## 6. Prepare Google Colab

1. Open the shared Google Drive folder.
2. Add `BT4222 Group Project` as a shortcut directly under `My Drive`.
3. Open [`00_setup_and_data_access.ipynb` in Colab](https://colab.research.google.com/github/liamkunert/BT4222-group17-jdsearch/blob/main/notebooks/00_setup_and_data_access.ipynb).
4. Select runtime version `2026.07`.
5. Run all cells and allow Google Drive access when prompted.

Colab already contains the required packages. Do not install `requirements.txt` inside Colab.
