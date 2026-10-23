"""Shared ranking evaluation for the modelling pipeline (notebooks 02 onwards).

Protocol (PROJECT_PLAN sections 2 and 6, FINDINGS section 3):
- each search's complete candidate list is ranked by a model score; higher = ranked earlier;
- gains are the labels 0/1/2/3 (linear); "engaged" means label >= 1;
- ties are never resolved by file order (it encodes the label): every metric is the exact expectation
  over a uniformly random order within each group of tied scores;
- searches without an engaged candidate are excluded (every ordering scores the same).

Main entry points: ``evaluate`` (per-search metrics), ``summarise`` (means with bootstrap intervals,
optionally by segment), ``paired_difference`` (model A vs B on the same searches) and ``log_result``
(appends one row to docs/experiment_results.csv).
"""
from datetime import date
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

K = 10
REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "docs/experiment_results.csv"
RESULT_COLUMNS = ["date", "experiment", "model", "split", "searches", "ndcg_at_10", "ndcg_ci_low", "ndcg_ci_high",
                  "recall_at_10", "mrr", "commit", "notes"]


def _tie_blocks(scores):
    """Sort by descending score; return the order and the [start, end) positions of each tie group."""
    order = np.argsort(-scores, kind="stable")
    sorted_scores = scores[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_scores)) + 1]
    return order, starts, np.r_[starts[1:], len(scores)]


def _expected_reciprocal_rank(start, size, engaged):
    """E[1 / rank of the first engaged item] when `engaged` of `size` tied items fill positions start.. ."""
    j = np.arange(size - engaged + 1)
    # P(first engaged offset >= j) = C(size - j, engaged) / C(size, engaged), as a running product.
    survival = np.r_[1.0, np.cumprod((size - engaged - j[:-1]) / (size - j[:-1]))] if len(j) > 1 else np.ones(1)
    probability = survival - np.r_[survival[1:], 0.0]
    return float(np.dot(probability, 1.0 / (start + j + 1)))


def expected_metrics(scores, labels, k=K):
    """(NDCG@k, Recall@k, MRR) for one search, exact under random tie-breaking; NaNs if nothing is engaged."""
    scores, labels = np.asarray(scores, dtype=float), np.asarray(labels, dtype=float)
    if len(scores) != len(labels) or not np.all(np.isfinite(scores)):
        raise ValueError("Scores and labels must be aligned and finite")
    engaged = labels >= 1
    if not engaged.any():
        return np.nan, np.nan, np.nan
    discount = 1 / np.log2(np.arange(2, min(k, len(labels)) + 2))
    ideal = np.dot(np.sort(labels)[::-1][:len(discount)], discount)
    order, starts, ends = _tie_blocks(scores)
    gains, hits = labels[order], engaged[order]
    dcg = found = 0.0
    mrr = None
    for start, end in zip(starts, ends):
        size, block_hits = end - start, hits[start:end].sum()
        if start < len(discount):
            slots = discount[start:min(end, len(discount))]
            dcg += gains[start:end].mean() * slots.sum()
            found += block_hits / size * len(slots)
        if mrr is None and block_hits:
            mrr = _expected_reciprocal_rank(start, size, int(block_hits))
        if start >= len(discount) and mrr is not None:
            break
    return dcg / ideal, found / engaged.sum(), mrr


def evaluate(frame, score_col="score", k=K):
    """Per-search metrics for a long table with columns session_id, label and `score_col`."""
    frame = frame.sort_values("session_id", kind="stable")
    sessions = frame.session_id.to_numpy()
    scores, labels = frame[score_col].to_numpy(dtype=float), frame.label.to_numpy()
    bounds = np.r_[0, np.flatnonzero(np.diff(sessions)) + 1, len(sessions)]
    rows = []
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        ndcg, recall, mrr = expected_metrics(scores[lo:hi], labels[lo:hi], k)
        rows.append((sessions[lo], hi - lo, int((labels[lo:hi] >= 1).sum()), ndcg, recall, mrr))
    per_search = pd.DataFrame(rows, columns=["session_id", "n_candidates", "n_engaged", "ndcg", "recall", "mrr"])
    return per_search[per_search.n_engaged > 0].set_index("session_id")


def bootstrap_interval(values, seed=4222, repeats=1000):
    """Mean and 95% percentile interval over resampled searches."""
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = np.array([values[rng.integers(0, len(values), len(values))].mean() for _ in range(repeats)])
    return values.mean(), *np.quantile(means, [0.025, 0.975])


def summarise(per_search, by=None):
    """Mean metrics with a bootstrap interval for NDCG; `by` is a Series of segment labels per search."""
    def one(part):
        mean, low, high = bootstrap_interval(part.ndcg)
        return pd.Series({"searches": len(part), "ndcg_at_10": mean, "ndcg_ci_low": low, "ndcg_ci_high": high,
                          "recall_at_10": part.recall.mean(), "mrr": part.mrr.mean()})
    if by is None:
        return one(per_search).to_frame("all").T
    return per_search.groupby(by.reindex(per_search.index), observed=True).apply(one)


def paired_difference(per_a, per_b, metric="ndcg"):
    """Mean of A minus B over the same searches, with a bootstrap interval."""
    a, b = per_a[metric].align(per_b[metric], join="inner")
    return bootstrap_interval(a - b)


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def log_result(experiment, model, split, per_search, notes="", path=RESULTS):
    """Append one evaluated ranking to the shared results registry and return the row."""
    summary = summarise(per_search).iloc[0]
    row = {"date": date.today().isoformat(), "experiment": experiment, "model": model, "split": split,
           "searches": int(summary.searches), **{c: round(float(summary[c]), 5) for c in RESULT_COLUMNS[5:10]},
           "commit": _commit(), "notes": notes}
    path = Path(path)
    pd.DataFrame([row], columns=RESULT_COLUMNS).to_csv(path, mode="a", header=not path.exists(), index=False)
    return pd.Series(row)


def validate_evaluation():
    """Hand-checked cases; raises AssertionError if the metric logic changes."""
    assert expected_metrics([1, 0], [3, 0], 1)[0] == 1.0
    assert expected_metrics([0, 1], [3, 0], 1)[0] == 0.0
    assert expected_metrics([0, 0], [3, 0], 1)[0] == 0.5          # tie: each order is equally likely
    assert all(np.isnan(expected_metrics([0, 0], [0, 0])))        # nothing engaged: excluded
    assert expected_metrics([2, 1, 0], [0, 0, 1], 2)[1] == 0.0    # engaged item ranked third: Recall@2 = 0
    assert np.isclose(expected_metrics([0, 0, 0], [1, 0, 0])[2], (1 + 1 / 2 + 1 / 3) / 3)
    assert np.isclose(expected_metrics([0, 0, 0], [1, 1, 0])[2], (2 / 3) * 1 + (1 / 3) * (1 / 2))
    # A tied ranker gives the same result after permuting the input list.
    assert expected_metrics([1, 1, 0], [3, 0, 1]) == expected_metrics([0, 1, 1], [1, 0, 3])
