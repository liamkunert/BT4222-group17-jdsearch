"""Reading helpers for the modelling pipeline (notebooks 02 onwards).

``session_id`` is always the 0-based data row of ``user_behavior_data.txt`` (header excluded), the same
convention as the interim exploration. Candidate file order encodes the label, so no helper here returns
a candidate position.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HEADER = ["query", "candidate_wid_list", "candidate_label_list", "history_qry_list",
          "history_wid_list", "history_type_list", "history_time_list"]
SECONDS_PER_DAY = 86400
EXPLORED_SIZE, EXPLORED_SEED = 5000, 4222  # the interim exploration sample


def iter_records(path):
    """Yield (session_id, fields) for every behaviour record."""
    with Path(path).open(encoding="utf-8") as handle:
        assert next(handle).rstrip("\r\n").split("\t") == HEADER
        for session_id, line in enumerate(handle):
            fields = line.rstrip("\r\n").split("\t")
            assert len(fields) == len(HEADER)
            yield session_id, fields


def elapsed_days(gaps):
    """Days from each past action to the search; ``gaps`` = [0, g1, ..., gn, gap to the search] in seconds."""
    gaps = np.asarray(gaps, dtype=np.int64)
    return np.cumsum(gaps[::-1])[::-1][1:] / SECONDS_PER_DAY


def explored_ids(n_records, size=EXPLORED_SIZE, seed=EXPLORED_SEED):
    """Session IDs of the interim exploration sample (same draw as scripts/query_diagnostics.py)."""
    return np.sort(np.random.default_rng(seed).choice(n_records, size, replace=False))


def search_table(path):
    """One row per search: list size, label counts and history context used for splits and segments."""
    rows = []
    for session_id, fields in iter_records(path):
        labels = np.array([int(float(v)) for v in fields[2].split("_")])
        types = np.array(fields[5].split("_"))
        gaps = np.array(fields[6].split("_"), dtype=np.int64)
        assert len(gaps) == len(types) + 1 and len(labels) == fields[1].count("_") + 1
        elapsed = elapsed_days(gaps)
        rows.append((session_id, len(labels), int((labels >= 1).sum()), int((labels == 3).sum()), len(types),
                     int((types == "CLICK").sum()), int((types == "CART").sum()), int((types == "ORD").sum()),
                     int((types == "FLW").sum()), int((elapsed < 7).sum()), gaps[-1] / SECONDS_PER_DAY, int(gaps[-1])))
    table = pd.DataFrame(rows, columns=[
        "session_id", "n_candidates", "n_engaged", "n_purchased", "history_len", "n_click", "n_cart", "n_ord",
        "n_flw", "actions_last_7d", "days_since_last_action", "final_gap_s"]).set_index("session_id")
    # The final gap is never 0 but exactly 1 s in 5.3% of records: most likely gaps <= 0 clamped to 1 s, i.e. the
    # history contains actions from during or after the final search (E12). Flagged; excluded downstream.
    table["final_gap_clamped"] = table.final_gap_s == 1
    return table


def load_metadata(path, wids):
    """Catalogue rows for the given products: wid -> (brand, shop, cate_1, cate_2, cate_3, cate_4).

    Same columns and missing-value rule as the interim validation (empty or -1 = None). Products without a
    catalogue row are simply absent; use scripts.history_match_diagnostics.metadata_keys to match them.
    """
    wids, metadata = set(wids), {}
    with Path(path).open(encoding="utf-8") as handle:
        assert next(handle).split("\t", 1)[0] == "wid"
        for line in handle:
            wid = line.split("\t", 1)[0]
            if wid in wids:
                fields = line.rstrip("\r\n").split("\t")
                metadata[wid] = tuple(int(fields[j]) if fields[j] not in ("", "-1") else None
                                      for j in (2, 12, 4, 6, 8, 10))
    return metadata


def load_candidates(path, session_ids, shuffle_seed=EXPLORED_SEED):
    """Long table (session_id, wid, label) for the given searches; one row per candidate occurrence.

    Candidates are shuffled within each search (seeded), because the file stores engaged candidates first:
    a model must never see that order, not even through row order during training. Pass
    ``shuffle_seed=None`` to keep file order (only for checks).
    """
    selected = set(np.asarray(session_ids).tolist())
    rng = None if shuffle_seed is None else np.random.default_rng(shuffle_seed)
    parts = []
    for session_id, fields in iter_records(path):
        if session_id in selected:
            wids = np.array(fields[1].split("_"))
            labels = np.array([int(float(v)) for v in fields[2].split("_")])
            if rng is not None:
                order = rng.permutation(len(wids))
                wids, labels = wids[order], labels[order]
            parts.append(pd.DataFrame({"session_id": session_id, "wid": wids, "label": labels}))
    frame = pd.concat(parts, ignore_index=True)
    frame["label"] = frame["label"].astype(np.int8)
    assert frame.session_id.nunique() == len(selected)
    return frame
