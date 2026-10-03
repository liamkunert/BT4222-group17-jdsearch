"""Exploratory history/candidate matches on complete, reproducibly sampled slates."""
from collections import Counter
from pathlib import Path
import json

import numpy as np
import pandas as pd

from scripts.query_diagnostics import bootstrap_mean, expected_ndcg

LEVELS = ("product", "brand", "shop", "L1", "L2", "L3", "L4")
SOURCES = ("all", "search", "queryless")


def metadata_keys(wid, metadata):
    """Category keys use the complete ancestor path, guarding against reused IDs.

    Missing metadata never matches other missing metadata. Product identity is
    observable in the behaviour file even if its catalog row is missing.
    """
    if wid not in metadata:
        return (wid, None, None, None, None, None, None)
    brand, shop, *categories = metadata[wid]
    paths = []
    for depth in range(1, 5):
        path = tuple(categories[:depth])
        paths.append(path if all(v is not None for v in path) else None)
    return (wid, brand, shop, *paths)


def match_counts(candidates, past_items, has_query, metadata):
    candidate_keys = [metadata_keys(wid, metadata) for wid in candidates]
    counters = {source: [Counter() for _ in LEVELS] for source in SOURCES}
    eligible_history = {source: np.zeros(len(LEVELS), dtype=int) for source in SOURCES}
    for wid, from_search in zip(past_items, has_query):
        keys = metadata_keys(wid, metadata)
        source = "search" if from_search else "queryless"
        for j, key in enumerate(keys):
            if key is not None:
                for target in ("all", source):
                    counters[target][j][key] += 1
                    eligible_history[target][j] += 1
    scores = {source: np.asarray([[counters[source][j][key] if key is not None else 0
                                  for j, key in enumerate(keys)] for keys in candidate_keys])
              for source in SOURCES}
    known = np.asarray([[key is not None for key in keys] for keys in candidate_keys])
    assert np.array_equal(scores["all"], scores["search"] + scores["queryless"])
    # Because categories use paths, a deeper match must also be an ancestor match.
    assert np.all(scores["all"][:, 4:] <= scores["all"][:, 3:-1])
    return scores, known, candidate_keys, eligible_history


def validate_match_helpers():
    meta = {"a": (10, 20, 1, 2, 3, 4), "b": (10, 21, 1, 2, 3, 5),
            "c": (11, 22, 1, 7, 3, 4), "d": (None, None, 1, 2, 3, None)}
    scores, known, _, _ = match_counts(["a", "b", "c", "d", "missing"],
                                      ["a", "a", "b", "missing"], [True, False, False, True], meta)
    assert scores["all"][0].tolist() == [2, 3, 2, 3, 3, 3, 2]
    assert scores["search"][0, 0] == 1 and scores["queryless"][0, 0] == 1
    assert scores["all"][2, 5] == 0  # same child ID, different ancestor: no L3 path match
    assert scores["all"][3, 6] == 0 and not known[3, 6]  # missing L4
    assert scores["all"][4, 0] == 1 and not known[4, 1:].any()
    empty, _, _, _ = match_counts(["a"], [], [], meta)
    assert not empty["all"].any()


def run_history_validation(data_dir, output_dir, sample_size=5000, seed=4222, expected_sample_path=None):
    validate_match_helpers()
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    user_path = data_dir / "user_behavior_data.txt"
    with user_path.open(encoding="utf-8") as handle:
        header = next(handle).rstrip("\r\n").split("\t")
        total_records = sum(1 for _ in handle)
    assert header == ["query", "candidate_wid_list", "candidate_label_list", "history_qry_list", "history_wid_list", "history_type_list", "history_time_list"]
    sample_ids = np.sort(np.random.default_rng(seed).choice(total_records, min(sample_size, total_records), replace=False))
    if expected_sample_path is not None:
        previous = pd.read_csv(expected_sample_path).session_id.to_numpy()
        assert np.array_equal(sample_ids, previous), "History and query diagnostic samples differ"
    selected, needed, records = set(sample_ids.tolist()), set(), []
    with user_path.open(encoding="utf-8") as handle:
        next(handle)
        for session_id, line in enumerate(handle):
            if session_id not in selected:
                continue
            fields = line.rstrip("\r\n").split("\t")
            assert len(fields) == 7
            candidates = fields[1].split("_")
            labels = np.asarray([int(float(value)) for value in fields[2].split("_")], dtype=np.int8)
            past_queries = fields[3].split("_") if fields[3] else []
            past_items = fields[4].split("_") if fields[4] else []
            actions = fields[5].split("_") if fields[5] else []
            assert len(candidates) == len(labels) and set(labels).issubset({0, 1, 2, 3})
            assert len(past_queries) == len(past_items) == len(actions)
            assert all(q != "" for q in past_queries)
            has_query = np.asarray([q != "-1" for q in past_queries], dtype=bool)
            records.append((session_id, candidates, labels, past_items, has_query))
            needed.update(candidates)
            needed.update(past_items)
    print(f"Loaded {len(records):,} complete records; need metadata for {len(needed):,} products", flush=True)
    metadata, catalog_rows = {}, 0
    parent_maps = {level: {} for level in (2, 3, 4)}
    parent_conflicts = {level: set() for level in (2, 3, 4)}
    catalog_missing = Counter()
    duplicate_L4_L3 = 0
    with (data_dir / "product_meta_data.txt").open(encoding="utf-8") as handle:
        header = next(handle).rstrip("\r\n").split("\t")
        assert len(header) == 13 and header[0] == "wid"
        for line in handle:
            fields = line.rstrip("\r\n").split("\t")
            assert len(fields) == 13
            catalog_rows += 1
            values = tuple(int(fields[j]) if fields[j] not in ("", "-1") else None for j in (2, 12, 4, 6, 8, 10))
            for name, value in zip(LEVELS[1:], values):
                catalog_missing[name] += value is None
            categories = values[2:]
            duplicate_L4_L3 += categories[3] is not None and categories[3] == categories[2]
            for level in (2, 3, 4):
                child, parent = categories[level - 1], categories[level - 2]
                if child is None or parent is None:
                    continue
                if child in parent_maps[level] and parent_maps[level][child] != parent:
                    parent_conflicts[level].add(child)
                else:
                    parent_maps[level][child] = parent
            if fields[0] in needed:
                assert fields[0] not in metadata
                metadata[fields[0]] = values
    print(f"Scanned {catalog_rows:,} catalog rows; retained {len(metadata):,} matching rows", flush=True)
    # Per-record sufficient statistics retain grouping for within-search comparisons.
    totals = {(source, level): np.zeros(4, dtype=np.int64) for source in SOURCES for level in LEVELS}
    contrasts = {(source, level): [] for source in SOURCES for level in LEVELS}
    per_search_rows, missing_rows = [], []
    audit_checks = 0
    for record_index, (session_id, candidates, labels, past_items, has_query) in enumerate(records):
        scores, known, keys, eligible_history = match_counts(candidates, past_items, has_query, metadata)
        # Independent direct comparison on actual records, rather than using the counters.
        if record_index < 5:
            past_keys = [metadata_keys(wid, metadata) for wid in past_items]
            for i in range(min(15, len(candidates))):
                for source in SOURCES:
                    mask = np.ones(len(past_items), dtype=bool) if source == "all" else has_query if source == "search" else ~has_query
                    for j, candidate_key in enumerate(keys[i]):
                        brute = sum(keep and candidate_key is not None and candidate_key == past[j]
                                    for keep, past in zip(mask, past_keys))
                        assert scores[source][i, j] == brute
                        audit_checks += 1
        row = {"session_id": session_id, "candidates": len(candidates), "history_events": len(past_items),
               "search_history_events": int(has_query.sum()), "queryless_history_events": int((~has_query).sum()),
               "positive_candidates": int((labels > 0).sum()), "ndcg_random": expected_ndcg(np.zeros(len(labels)), labels)}
        history_keys = [metadata_keys(wid, metadata) for wid in past_items]
        for j, level in enumerate(LEVELS):
            candidate_known = known[:, j]
            positive = labels > 0
            valid_keys = {key[j] for key in keys if key[j] is not None}
            row[f"{level}_attribute_varies"] = len(valid_keys) > 1
            row[f"{level}_known_candidates"] = int(candidate_known.sum())
            for source in SOURCES:
                counts = scores[source][:, j]
                matched = candidate_known & (counts > 0)
                unmatched = candidate_known & (counts == 0)
                totals[source, level] += [matched.sum(), (matched & positive).sum(), unmatched.sum(), (unmatched & positive).sum()]
                row[f"{source}_{level}_count_varies"] = bool(candidate_known.sum() > 1 and np.ptp(counts[candidate_known]) > 0)
                row[f"{source}_{level}_match_flag_varies"] = bool(matched.any() and unmatched.any())
                row[f"{source}_{level}_any_match"] = bool(matched.any())
                row[f"{source}_{level}_matched_candidates"] = int(matched.sum())
                row[f"{source}_{level}_ndcg"] = expected_ndcg(counts, labels)
                if matched.any() and unmatched.any():
                    contrasts[source, level].append(float(positive[matched].mean() - positive[unmatched].mean()))
            for source in SOURCES:
                source_size = len(past_items) if source == "all" else int(has_query.sum()) if source == "search" else int((~has_query).sum())
                missing_rows.append({"session_id": session_id, "source": source, "level": level,
                                     "history_events": source_size, "history_events_with_usable_metadata": int(eligible_history[source][j])})
        per_search_rows.append(row)
    per_search = pd.DataFrame(per_search_rows).set_index("session_id")
    comparison_rows, ranking_rows = [], []
    for source in SOURCES:
        for level in LEVELS:
            n_match, positives_match, n_no, positives_no = totals[source, level]
            valid = n_match + n_no
            rate_match = positives_match / n_match if n_match else np.nan
            rate_no = positives_no / n_no if n_no else np.nan
            contrast, lo, hi = bootstrap_mean(contrasts[source, level], seed)
            comparison_rows.append({"source": source, "level": level, "eligible_candidate_occurrences": int(valid),
                                    "matched_candidate_occurrences": int(n_match), "matched_share": n_match / valid if valid else np.nan,
                                    "engagement_with_match": rate_match, "engagement_without_match": rate_no,
                                    "pooled_rate_ratio": rate_match / rate_no if rate_no > 0 else np.nan,
                                    "searches_with_any_match_share": per_search[f"{source}_{level}_any_match"].mean(),
                                    "attribute_varies_search_share": per_search[f"{level}_attribute_varies"].mean(),
                                    "count_varies_search_share": per_search[f"{source}_{level}_count_varies"].mean(),
                                    "match_flag_varies_search_share": per_search[f"{source}_{level}_match_flag_varies"].mean(),
                                    "contrast_eligible_searches": len(contrasts[source, level]),
                                    "query_balanced_engagement_difference": contrast, "difference_ci_low": lo, "difference_ci_high": hi})
            delta = per_search[f"{source}_{level}_ndcg"] - per_search.ndcg_random
            mean, lo, hi = bootstrap_mean(delta, seed)
            ranking_rows.append({"source": source, "level": level, "evaluated_searches": int(delta.notna().sum()),
                                 "ndcg_at_10": per_search[f"{source}_{level}_ndcg"].mean(),
                                 "delta_vs_random": mean, "delta_ci_low": lo, "delta_ci_high": hi})
    comparisons, ranking = pd.DataFrame(comparison_rows), pd.DataFrame(ranking_rows)
    depth_rows = []
    for source in SOURCES:
        for shallow, deep in [("L1", "L2"), ("L2", "L3"), ("L3", "L4")]:
            mean, lo, hi = bootstrap_mean(per_search[f"{source}_{deep}_ndcg"] - per_search[f"{source}_{shallow}_ndcg"], seed)
            depth_rows.append({"source": source, "comparison": f"{deep} minus {shallow}",
                               "ndcg_difference": mean, "ci_low": lo, "ci_high": hi})
    depth_comparisons = pd.DataFrame(depth_rows)
    history_missing = pd.DataFrame(missing_rows).groupby(["source", "level"])[["history_events", "history_events_with_usable_metadata"]].sum()
    history_missing["metadata_usable_share"] = history_missing.history_events_with_usable_metadata / history_missing.history_events
    candidate_total = int(per_search.candidates.sum())
    summary = {"seed": seed, "total_records": total_records, "sample_records": len(records),
               "candidate_occurrences": candidate_total, "history_events": int(per_search.history_events.sum()),
               "search_history_events": int(per_search.search_history_events.sum()),
               "queryless_history_events": int(per_search.queryless_history_events.sum()),
               "catalog_rows_scanned": catalog_rows, "distinct_behavior_products_requested": len(needed),
               "distinct_behavior_products_with_metadata": len(metadata),
               "catalog_missing_id_counts": dict(catalog_missing),
               "catalog_L4_equals_L3_rows": duplicate_L4_L3,
               "category_child_ids_with_multiple_parents": {f"L{level}": len(values) for level, values in parent_conflicts.items()},
               "candidate_metadata_usable_share": {level: int(per_search[f"{level}_known_candidates"].sum()) / candidate_total for level in LEVELS},
               "independent_actual_record_count_checks": audit_checks,
               "all_zero_sample_records": int(per_search.positive_candidates.eq(0).sum()),
               "evaluated_positive_searches": int(per_search.ndcg_random.notna().sum()),
               "mean_random_ndcg_at_10": float(per_search.ndcg_random.mean()),
               "note": "Exploratory 5k-record sample, complete slates, linear gains and random tie expectation. Metadata scans and hierarchy checks use the full catalog. Association does not establish causation; source comparisons are not controlled for history volume."}
    comparisons.to_csv(output_dir / "history_match_coverage_and_engagement.csv", index=False)
    ranking.to_csv(output_dir / "history_match_ranking.csv", index=False)
    depth_comparisons.to_csv(output_dir / "history_match_depth_comparisons.csv", index=False)
    history_missing.to_csv(output_dir / "history_match_metadata_coverage.csv")
    per_search.to_csv(output_dir / "history_match_per_search.csv")
    (output_dir / "history_match_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print(comparisons[comparisons.source == "all"].to_string(index=False), flush=True)
    print(ranking.to_string(index=False), flush=True)
    return summary, comparisons, ranking, depth_comparisons, history_missing, per_search
