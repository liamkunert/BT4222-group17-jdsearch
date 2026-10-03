"""Reproducible exploratory query checks; no model fitting or candidate-position features."""
from collections import Counter
from pathlib import Path
import json

import numpy as np
import pandas as pd

TERM_SEPARATOR = "\x18"  # README: octal \030, displayed as ^X


def tokenize(text):
    """Return ordered term IDs; query-less -1 and empty metadata are not terms."""
    if text is None or text in ("", "-1"):
        return ()
    terms = tuple(text.split(TERM_SEPARATOR))
    if not all(term.isdecimal() for term in terms):
        raise ValueError(f"Invalid anonymised term sequence: {text!r}")
    return terms


def token_set(text):
    return frozenset(tokenize(text))


def any_token_match(query, text):
    return bool(token_set(query) & token_set(text))


def overlap_features(query_terms, document_terms):
    shared = len(query_terms & document_terms)
    union = len(query_terms | document_terms)
    return shared, shared / len(query_terms) if query_terms else 0.0, shared / union if union else 0.0


def expected_ndcg(scores, labels, k=10):
    """Linear gains 0/1/2/3, with exact expected DCG under random tie breaking.

    Original file order never resolves ties: positives are stored first in JDSearch.
    """
    scores, labels = np.asarray(scores), np.asarray(labels, dtype=float)
    if len(scores) != len(labels) or not np.all(np.isfinite(scores)):
        raise ValueError("Scores and labels must be aligned and finite")
    discount = 1 / np.log2(np.arange(2, min(k, len(labels)) + 2))
    ideal = np.dot(np.sort(labels)[::-1][:len(discount)], discount)
    if ideal == 0:
        return np.nan
    order = np.argsort(-scores, kind="stable")
    sorted_scores, gains = scores[order], labels[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_scores)) + 1]
    ends = np.r_[starts[1:], len(scores)]
    dcg = 0.0
    for start, end in zip(starts, ends):
        if start >= len(discount):
            break
        dcg += gains[start:end].mean() * discount[start:min(end, len(discount))].sum()
    return dcg / ideal


def validate_helpers():
    # These cases catch partial digit matches, order sensitivity and placeholder leakage.
    assert tokenize("12\x1832\x1856") == ("12", "32", "56")
    assert token_set("12\x1832\x1812") == token_set("32\x1812")
    assert not token_set("-1") and not token_set("")
    assert not any_token_match("123456789", "23456789")
    assert any_token_match("12\x1832", "32")  # valid short IDs must count
    assert overlap_features(token_set("12\x1832"), token_set("32\x1856")) == (1, 0.5, 1 / 3)
    assert expected_ndcg([0, 0], [3, 0], 1) == 0.5
    assert expected_ndcg([0, 1], [3, 0], 1) == 0.0
    assert expected_ndcg([1, 0], [3, 0], 1) == 1.0
    assert np.isnan(expected_ndcg([0, 0], [0, 0]))
    for bad in ("12_32", "12 32", "12\x18", "-1\x1812"):
        try:
            tokenize(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted malformed text: {bad!r}")
    # A tied ranker must have the same result after permuting the input slate.
    assert expected_ndcg([1, 1, 0], [3, 0, 1]) == expected_ndcg([0, 1, 1], [1, 0, 3])


def bootstrap_mean(values, seed=4222, repeats=2000):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = [rng.choice(values, len(values), replace=True).mean() for _ in range(repeats)]
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(values.mean()), float(lo), float(hi)


def run_validation(data_dir, output_dir, sample_size=5000, seed=4222):
    """Two streaming behaviour passes and one catalog pass; full sampled slates."""
    validate_helpers()
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    user_path = data_dir / "user_behavior_data.txt"
    metadata_path = data_dir / "product_meta_data.txt"
    with user_path.open(encoding="utf-8") as handle:
        header = next(handle).rstrip("\r\n").split("\t")
        n_records = sum(1 for _ in handle)
    assert header == ["query", "candidate_wid_list", "candidate_label_list", "history_qry_list", "history_wid_list", "history_type_list", "history_time_list"]
    rng = np.random.default_rng(seed)
    sample_ids = np.sort(rng.choice(n_records, min(sample_size, n_records), replace=False))
    selected = set(sample_ids.tolist())
    records, needed, all_query_terms = [], set(), set()
    full_raw_repeat, full_set_repeat = 0, 0
    repeat_examples = []
    for_query_rows = []
    with user_path.open(encoding="utf-8") as handle:
        next(handle)
        for session_id, line in enumerate(handle):
            fields = line.rstrip("\r\n").split("\t")
            assert len(fields) == len(header)
            query_terms = token_set(fields[0])
            assert query_terms
            all_query_terms.update(query_terms)
            # Audit the suspicious exact-repeat finding on the complete behaviour file.
            historical_queries = fields[3].split("_")
            full_raw_repeat += fields[0] in historical_queries
            equal_terms = next((q for q in historical_queries if q != "-1" and frozenset(q.split(TERM_SEPARATOR)) == query_terms), None)
            full_set_repeat += equal_terms is not None
            if equal_terms is not None and fields[0] not in historical_queries and len(repeat_examples) < 3:
                repeat_examples.append({"current": tokenize(fields[0]), "past": tokenize(equal_terms)})
            if session_id not in selected:
                continue
            candidates = fields[1].split("_")
            labels = np.asarray([int(float(v)) for v in fields[2].split("_")], dtype=np.int8)
            past_q = historical_queries
            past_items = fields[4].split("_")
            actions = fields[5].split("_")
            assert len(candidates) == len(labels) and set(labels).issubset({0, 1, 2, 3})
            assert len(past_q) == len(past_items) == len(actions)
            assert len(fields[6].split("_")) == len(past_items) + 1
            all_history, matched_history = Counter(past_items), Counter()
            similarities, search_events, exact_events, shared_events = [], 0, 0, 0
            raw_exact = False
            distinct_past = set()
            for q, item in zip(past_q, past_items):
                past_terms = token_set(q)
                if not past_terms:
                    continue
                search_events += 1
                distinct_past.add(tuple(sorted(past_terms)))
                raw_exact |= q == fields[0]
                exact_events += past_terms == query_terms
                shared, coverage, jaccard = overlap_features(query_terms, past_terms)
                similarities.append(jaccard)
                if shared:
                    shared_events += 1
                    matched_history[item] += 1
            for_query_rows.append({
                "session_id": session_id, "query_terms": len(query_terms), "history_events": len(past_items),
                "search_history_events": search_events, "distinct_history_queries": len(distinct_past),
                "raw_exact_repeat": raw_exact, "set_exact_repeat": exact_events > 0,
                "history_any_token_overlap": shared_events > 0, "matching_history_events": shared_events,
                "share_search_events_matching": shared_events / search_events if search_events else np.nan,
                "max_history_query_jaccard": max(similarities, default=0),
                "repeated_history_query_event_share": 1 - len(distinct_past) / search_events if search_events else np.nan,
                "positive_candidates": int((labels > 0).sum()), "candidate_count": len(candidates),
            })
            records.append((session_id, fields[0], query_terms, candidates, labels, all_history, matched_history))
            needed.update(candidates)
    print(f"Sample: {len(records):,}/{n_records:,} records; {len(needed):,} distinct candidate IDs", flush=True)
    metadata, metadata_rows = {}, 0
    with metadata_path.open(encoding="utf-8") as handle:
        meta_header = next(handle).rstrip("\r\n").split("\t")
        assert meta_header == ["wid", "name", "brand_id", "brand_name", "cate_id_1", "cate_name_1", "cate_id_2", "cate_name_2", "cate_id_3", "cate_name_3", "cate_id_4", "cate_name_4", "shop_id"]
        for line in handle:
            metadata_rows += 1
            # Scan the complete file, keeping only the sampled candidate metadata.
            wid = line.split("\t", 1)[0]
            if wid not in needed:
                continue
            fields = line.rstrip("\r\n").split("\t")
            assert len(fields) == len(meta_header) and wid not in metadata
            metadata[wid] = (token_set(fields[1]), token_set(fields[3]), token_set(fields[9]), fields[3], fields[9])
    print(f"Catalog scan: {metadata_rows:,} rows; found {len(metadata):,}/{len(needed):,} sampled items", flush=True)
    per_query = pd.DataFrame(for_query_rows).set_index("session_id")
    labels_all, features_all, known_all = [], [], []
    query_contrasts, disagreements = [], []
    matched_title_vocabulary = set()
    permutation = rng.permutation(len(records))
    for index, (session_id, raw_query, query_terms, candidates, labels, history, matched_history) in enumerate(records):
        shuffled_query = records[permutation[index]][2]
        rows, known = [], []
        legacy_matches, exact_matches = [], []
        for wid in candidates:
            found = wid in metadata
            title, brand, category, raw_brand, raw_category = metadata.get(wid, (frozenset(), frozenset(), frozenset(), "", ""))
            shared, coverage, jaccard = overlap_features(query_terms, title)
            matched_title_vocabulary.update(title & all_query_terms)
            rows.append((shared, coverage, jaccard, bool(query_terms & brand), bool(query_terms & category),
                         overlap_features(shuffled_query, title)[1], history[wid], matched_history[wid]))
            known.append(found)
            legacy_matches.append((found and len(raw_brand) >= 8 and raw_brand in raw_query,
                                   found and len(raw_category) >= 8 and raw_category in raw_query))
            exact_matches.append((bool(query_terms & brand), bool(query_terms & category)))
        features = np.asarray(rows, dtype=float)
        known = np.asarray(known)
        labels_all.append(labels)
        features_all.append(features)
        known_all.append(known)
        legacy, exact = np.asarray(legacy_matches), np.asarray(exact_matches)
        disagreements.append(np.column_stack((legacy & ~exact, exact & ~legacy)))
        random_ndcg = expected_ndcg(np.zeros(len(labels)), labels)
        per_query.loc[session_id, "candidate_metadata_coverage"] = known.mean()
        # Missing metadata must not create artificial evidence of title-score variation.
        per_query.loc[session_id, "title_coverage_varies"] = bool(known.sum() > 1 and np.ptp(features[known, 1]) > 0)
        per_query.loc[session_id, "any_title_overlap"] = bool(np.any(features[:, 0] > 0))
        for col, feature_index in [("title_coverage", 1), ("title_jaccard", 2), ("history_item_count", 6), ("matching_query_history_item_count", 7)]:
            per_query.loc[session_id, f"ndcg_{col}"] = expected_ndcg(features[:, feature_index], labels)
        per_query.loc[session_id, "ndcg_random"] = random_ndcg
        per_query.loc[session_id, "mean_title_overlap"] = features[known, 1].mean() if known.any() else np.nan
        per_query.loc[session_id, "mean_shuffled_query_title_overlap"] = features[known, 5].mean() if known.any() else np.nan
        positive, negative = known & (labels > 0), known & (labels == 0)
        if positive.any() and negative.any():
            query_contrasts.append(features[positive, 1].mean() - features[negative, 1].mean())
    # Scalar assignments above create object columns in some pandas versions.
    # Explicit boolean dtype avoids numpy.bool_ object reductions behaving like OR.
    for column in ["title_coverage_varies", "any_title_overlap"]:
        per_query[column] = per_query[column].astype(bool)
    assert per_query.title_coverage_varies.sum() == np.count_nonzero(per_query.title_coverage_varies.to_numpy())
    labels_all, features_all, known_all = np.concatenate(labels_all), np.concatenate(features_all), np.concatenate(known_all)
    feature_names = ["title_shared_terms", "title_query_coverage", "title_jaccard", "brand_any_token", "category3_any_token", "shuffled_query_title_coverage", "history_item_count", "matching_query_history_item_count"]
    pooled = pd.DataFrame(features_all, columns=feature_names)
    pooled["label"], pooled["metadata_known"] = labels_all, known_all
    group_stats = pooled.loc[known_all].groupby("label")[feature_names].mean()
    group_stats.insert(0, "candidate_count", pooled.loc[known_all].groupby("label").size())
    disagreement_counts = np.concatenate(disagreements).sum(axis=0)
    discrepancy = pd.DataFrame({"legacy_only": disagreement_counts[:2], "token_only": disagreement_counts[2:]}, index=["brand", "category3"])
    metric_rows = []
    for name in ["title_coverage", "title_jaccard", "history_item_count", "matching_query_history_item_count"]:
        delta = per_query[f"ndcg_{name}"] - per_query.ndcg_random
        mean, lo, hi = bootstrap_mean(delta, seed)
        metric_rows.append({"score": name, "evaluated_queries": int(delta.notna().sum()),
                            "mean_ndcg_at_10": per_query[f"ndcg_{name}"].mean(),
                            "delta_vs_random": mean, "delta_ci_low": lo, "delta_ci_high": hi})
    metrics = pd.DataFrame(metric_rows).set_index("score")
    summary = {
        "seed": seed, "total_records": n_records, "sample_records": len(records),
        "sample_candidate_occurrences": len(labels_all), "metadata_catalog_rows_scanned": metadata_rows,
        "candidate_metadata_coverage": float(known_all.mean()),
        "all_zero_sample_records": int((per_query.positive_candidates == 0).sum()),
        "share_sample_records_with_search_history": float((per_query.search_history_events > 0).mean()),
        "raw_exact_repeat_records": int(per_query.raw_exact_repeat.sum()),
        "set_exact_repeat_records": int(per_query.set_exact_repeat.sum()),
        "full_data_raw_exact_repeat_records": full_raw_repeat,
        "full_data_distinct_token_set_repeat_records": full_set_repeat,
        "full_data_token_set_repeat_share": full_set_repeat / n_records,
        "repeat_examples_order_or_multiplicity_differences": repeat_examples,
        "share_records_with_any_history_query_overlap": float(per_query.history_any_token_overlap.mean()),
        "mean_share_search_history_events_matching": float(per_query.share_search_events_matching.mean()),
        "history_max_jaccard_quantiles": per_query.max_history_query_jaccard.quantile([0, .25, .5, .75, .95, 1]).to_dict(),
        "share_records_with_title_overlap": float(per_query.any_title_overlap.mean()),
        "share_records_with_varying_title_coverage": float(per_query.title_coverage_varies.mean()),
        "title_coverage_engaged_minus_ignored_query_balanced_ci": bootstrap_mean(query_contrasts, seed),
        "title_coverage_actual_minus_shuffled_query_ci": bootstrap_mean(per_query.mean_title_overlap - per_query.mean_shuffled_query_title_overlap, seed),
        "current_query_vocabulary_size_full_data": len(all_query_terms),
        "current_query_terms_seen_in_sampled_candidate_titles": len(matched_title_vocabulary),
        "mean_ndcg_at_10_random": float(per_query.ndcg_random.mean()),
        "matching_query_history_minus_all_history_ndcg_ci": bootstrap_mean(per_query.ndcg_matching_query_history_item_count - per_query.ndcg_history_item_count, seed),
        "note": "Exploratory sample, not held-out model evaluation; linear gains; full slates; expected random tie breaking; bootstrap units are search records. Repeated history queries may be multiple actions under one issued query.",
    }
    per_query.to_csv(output_dir / "query_diagnostics_per_search.csv")
    group_stats.to_csv(output_dir / "query_diagnostics_by_label.csv")
    discrepancy.to_csv(output_dir / "query_diagnostics_legacy_vs_tokens.csv")
    metrics.to_csv(output_dir / "query_diagnostics_ranking.csv")
    (output_dir / "query_diagnostics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print(metrics.to_string(), flush=True)
    return summary, group_stats, discrepancy, metrics, per_query
