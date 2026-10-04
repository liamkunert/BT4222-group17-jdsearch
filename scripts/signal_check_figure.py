"""Draw the interim report's Figure 5: NDCG@10 of one-signal rankings versus random order.

Reads the tables saved by notebooks/exploration/query_signal_validation.ipynb and
history_match_validation.ipynb, and writes outputs/interim/figures/2_4_signal_checks.png.
Run from anywhere inside the repository: ``python scripts/signal_check_figure.py``.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES = REPO_ROOT / "outputs/interim/tables"
OUT = REPO_ROOT / "outputs/interim/figures/2_4_signal_checks.png"


def main():
    history = pd.read_csv(TABLES / "history_validation/history_match_ranking.csv")
    query = pd.read_csv(TABLES / "query_validation/query_diagnostics_ranking.csv").set_index("score")
    random_ndcg = json.loads((TABLES / "history_validation/history_match_summary.json").read_text())[
        "mean_random_ndcg_at_10"]
    ndcg = history[history.source == "all"].set_index("level").ndcg_at_10

    rows = [  # (label, NDCG@10, colour role), most to least informative
        ("Same product in history", ndcg["product"], "accent"),
        ("Same shop in history", ndcg["shop"], "grey"),
        ("Same product, query-matched history only",
         query.loc["matching_query_history_item_count", "mean_ndcg_at_10"], "light"),
        ("Same brand in history", ndcg["brand"], "grey"),
        ("Same L4 category in history", ndcg["L4"], "grey"),
        ("Query–title term overlap (Jaccard)", query.loc["title_jaccard", "mean_ndcg_at_10"], "grey"),
        ("Same L3 category in history", ndcg["L3"], "grey"),
        ("Same L2 category in history", ndcg["L2"], "grey"),
        ("Same L1 category in history", ndcg["L1"], "grey"),
    ][::-1]
    colours = {"accent": "#2a78d6", "light": "#9bbfea", "grey": "#c4c3bc"}

    plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 180, "savefig.bbox": "tight",
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.titlelocation": "left"})
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh([r[0] for r in rows], [r[1] for r in rows], color=[colours[r[2]] for r in rows], height=0.62)
    for i, (_, value, _) in enumerate(rows):
        ax.annotate(f"{value:.3f}", (value, i), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9)
    ax.axvline(random_ndcg, color="#6f6e69", linestyle="--", linewidth=1.2)
    ax.set_ylim(-0.6, len(rows) - 0.05)
    ax.annotate(f"random order {random_ndcg:.3f}", (random_ndcg, len(rows) - 0.32), xytext=(5, 0),
                textcoords="offset points", fontsize=9, color="#6f6e69", va="center")
    ax.set_xlim(0, 0.2)
    ax.set_xlabel("mean NDCG@10 over 4,941 sampled searches (ties broken at random)")
    ax.set_title("Ranking each search by one signal: history beats query overlap", pad=10)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(f"Saved {OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
