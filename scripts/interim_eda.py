"""Memory-bounded full-data summaries and sampled interim feature statistics."""
from array import array
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.query_diagnostics import token_set, tokenize, overlap_features
from scripts.history_match_diagnostics import LEVELS, SOURCES, match_counts


def numeric_stats(frame):
    return pd.DataFrame({"min": frame.min(), "max": frame.max(), "mean": frame.mean(),
                         "median": frame.median(), "std": frame.std(), "missing": frame.isna().sum(),
                         "observed": frame.notna().sum()})


def describe_frequency(counts):
    """Exact descriptive statistics from an integer-value frequency table."""
    keys = np.asarray(sorted(counts), dtype=np.int64)
    freq = np.asarray([counts[int(key)] for key in keys], dtype=np.int64)
    n = int(freq.sum())
    if not n:
        return pd.Series(dtype=float)
    cumulative = np.cumsum(freq)
    mean = np.dot(keys.astype(float), freq) / n
    def quantile(p):
        location = (n - 1) * p
        low, high = int(np.floor(location)), int(np.ceil(location))
        a, b = keys[np.searchsorted(cumulative, [low + 1, high + 1])]
        return float(a + (b - a) * (location - low))
    variance = np.dot((keys - mean) ** 2, freq) / (n - 1) if n > 1 else np.nan
    return pd.Series({"count": n, "min": keys[0], "max": keys[-1], "mean": mean,
                      "median": quantile(.5), "std": np.sqrt(variance), "p25": quantile(.25), "p75": quantile(.75), "p95": quantile(.95)})


def members(sorted_ids, ids):
    indices = np.minimum(np.searchsorted(sorted_ids, ids), len(sorted_ids) - 1)
    return sorted_ids[indices] == ids


def compact_lorenz(counts):
    ordered = np.sort(counts)[::-1]
    cumulative = np.cumsum(ordered)
    stops = np.unique(np.r_[0, np.linspace(1, len(ordered), 1001).astype(int)])
    shares = np.r_[0., cumulative[stops[1:] - 1] / cumulative[-1]]
    return stops / len(ordered), shares


def build_full_profile(data_dir):
    """Read raw files without retaining their text or a full candidate feature table."""
    data_dir = Path(data_dir)
    candidate_buffer, history_buffer, gap_buffer = array("q"), array("q"), array("q")
    label_buffer = array("b")
    session_rows, raw_queries = [], Counter()
    actions, queryless_actions, text_counts, text_chars = Counter(), Counter(), {}, {}
    excluded_text = Counter()
    query_vocabulary = set()
    label_session_counts = np.zeros(4, dtype=np.int64)
    threshold_session_counts = np.zeros(4, dtype=np.int64)
    positive_prefix_records, positive_records = 0, 0
    def text_observation(field, value):
        if value in ("", "-1"):
            excluded_text[field] += 1
            return
        text_counts.setdefault(field, Counter())[value.count("\x18") + 1] += 1
        text_chars.setdefault(field, Counter())[len(value)] += 1
    with (data_dir / "user_behavior_data.txt").open(encoding="utf-8") as handle:
        header = next(handle).rstrip("\r\n").split("\t")
        assert header == ["query", "candidate_wid_list", "candidate_label_list", "history_qry_list", "history_wid_list", "history_type_list", "history_time_list"]
        for session_id, line in enumerate(handle):
            fields = line.rstrip("\r\n").split("\t")
            assert len(fields) == 7
            candidates = np.fromstring(fields[1], sep="_", dtype=np.int64)
            raw_labels = np.fromstring(fields[2], sep="_", dtype=float)
            labels = raw_labels.astype(np.int8)
            histories = np.fromstring(fields[4], sep="_", dtype=np.int64)
            history_queries, history_actions = fields[3].split("_"), fields[5].split("_")
            times = np.fromstring(fields[6], sep="_", dtype=np.int64)
            assert len(candidates) == len(labels) and np.array_equal(raw_labels, labels)
            assert set(labels).issubset({0, 1, 2, 3}) and len(candidates) > 0
            assert len(histories) == len(history_queries) == len(history_actions)
            assert len(times) == len(histories) + 1 and times[0] == 0 and np.all(times >= 0)
            candidate_buffer.frombytes(candidates.tobytes())
            history_buffer.frombytes(histories.tobytes())
            label_buffer.frombytes(labels.tobytes())
            gap_buffer.frombytes(times[1:-1].tobytes())  # exclude initial placeholder and final test gap
            for q, action in zip(history_queries, history_actions):
                assert action in ("CLICK", "CART", "ORD", "FLW")
                actions[action] += 1
                queryless_actions[action] += q == "-1"
                text_observation("past query (non-placeholder)", q)
            terms = tokenize(fields[0])
            query_vocabulary.update(terms)
            raw_queries[fields[0]] += 1
            text_observation("current query", fields[0])
            positive = labels > 0
            has_positive = bool(positive.any())
            positive_records += has_positive
            if has_positive:
                positive_prefix_records += not np.any(positive[1:] & ~positive[:-1])
            label_session_counts += [np.any(labels == grade) for grade in range(4)]
            threshold_session_counts += [True, np.any(labels >= 1), np.any(labels >= 2), np.any(labels == 3)]
            session_rows.append((len(candidates), len(histories), int(times[-1]), int(times[1:-1].sum()),
                                 int((labels > 0).sum()), int((labels == 3).sum())))
            if (session_id + 1) % 50000 == 0:
                print(f"Behaviour records summarised: {session_id + 1:,}", flush=True)
    sessions = pd.DataFrame(session_rows, columns=["slate_len", "history_len", "time_since_last_raw", "history_span_raw", "positive_candidates", "purchase_candidates"])
    cand_ids, hist_ids = np.frombuffer(candidate_buffer, dtype=np.int64), np.frombuffer(history_buffer, dtype=np.int64)
    labels, gaps = np.frombuffer(label_buffer, dtype=np.int8), np.frombuffer(gap_buffer, dtype=np.int64)
    n_records, n_candidates, n_histories = len(sessions), len(cand_ids), len(hist_ids)
    candidate_ids, exposures = np.unique(cand_ids, return_counts=True)
    historical_ids, interactions = np.unique(hist_ids, return_counts=True)
    processed = data_dir / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    np.save(processed / "eda_history_item_ids.npy", historical_ids)
    np.save(processed / "eda_history_item_counts.npy", interactions)
    catalog_buffer, category_buffer = array("q"), array("q")
    field_counts = {field: Counter() for field in ["brand_id", "shop_id", "cate_id_1", "cate_id_2", "cate_id_3", "cate_id_4", "brand_name"]}
    missing = Counter()
    with (data_dir / "product_meta_data.txt").open(encoding="utf-8") as handle:
        metadata_header = next(handle).rstrip("\r\n").split("\t")
        assert len(metadata_header) == 13 and metadata_header[0] == "wid"
        for i, line in enumerate(handle):
            fields = line.rstrip("\r\n").split("\t")
            assert len(fields) == 13
            catalog_buffer.append(int(fields[0]))
            category_buffer.append(int(fields[4]))
            for field, position in [("brand_id", 2), ("shop_id", 12), ("cate_id_1", 4), ("cate_id_2", 6), ("cate_id_3", 8), ("cate_id_4", 10), ("brand_name", 3)]:
                value = fields[position]
                if value in ("", "-1"):
                    missing[field] += 1
                else:
                    field_counts[field][value] += 1
            for field, position in [("product title", 1), ("brand name (nonempty)", 3), ("category L3 name", 9)]:
                text_observation(field, fields[position])
                if fields[position] in ("", "-1"):
                    missing[field] += 1
            if (i + 1) % 4000000 == 0:
                print(f"Catalog rows summarised: {i + 1:,}", flush=True)
    catalog_ids, category_ids = np.frombuffer(catalog_buffer, dtype=np.int64), np.frombuffer(category_buffer, dtype=np.int64)
    catalog_order = np.argsort(catalog_ids)
    sorted_catalog = catalog_ids[catalog_order]
    assert np.all(sorted_catalog[1:] > sorted_catalog[:-1]), "Duplicate catalog IDs"
    all_ids = np.union1d(candidate_ids, historical_ids)
    cold = ~members(historical_ids, candidate_ids)
    cold_occurrence_share = exposures[cold].sum() / n_candidates
    catalog_present = members(sorted_catalog, all_ids)
    n_missing_behavior_ids = int((~catalog_present).sum())
    catalog_candidate_mask = members(sorted_catalog, candidate_ids)
    candidate_catalog_share = exposures[catalog_candidate_mask].sum() / n_candidates
    history_catalog_mask = members(sorted_catalog, historical_ids)
    history_catalog_share = interactions[history_catalog_mask].sum() / n_histories
    label_counts = np.bincount(labels, minlength=4)
    label_names = ["No recorded interaction (0)", "Click label (1)", "Cart label (2)", "Purchase label (3)"]
    label_distribution = pd.DataFrame({"candidate occurrences": label_counts, "share of candidates": label_counts / n_candidates,
                                       "searches with this label": label_session_counts, "share of searches": label_session_counts / n_records}, index=label_names)
    threshold_counts = [n_candidates, (labels > 0).sum(), (labels >= 2).sum(), (labels == 3).sum()]
    thresholds = pd.DataFrame({"candidate occurrences": threshold_counts, "share of candidates": np.asarray(threshold_counts) / n_candidates,
                               "searches with this threshold": threshold_session_counts, "share of searches": threshold_session_counts / n_records},
                              index=["All exposed candidates", "Any recorded engagement (>=1)", "Cart or purchase label (>=2)", "Purchase label (=3)"])
    category_counts, category_engaged, category_purchased = Counter(), Counter(), Counter()
    position_counts, position_engaged = np.zeros(30, dtype=np.int64), np.zeros(30, dtype=np.int64)
    # Candidate arrays are read in record order; positions are only used to audit file ordering.
    offsets = np.r_[0, np.cumsum(sessions.slate_len.to_numpy())]
    for start, end in zip(offsets[:-1], offsets[1:]):
        stop = min(30, end - start)
        position_counts[:stop] += 1
        position_engaged[:stop] += labels[start:start + stop] > 0
    for start in range(0, n_candidates, 250000):
        ids, outcomes = cand_ids[start:start + 250000], labels[start:start + 250000]
        locations = np.minimum(np.searchsorted(sorted_catalog, ids), len(sorted_catalog) - 1)
        valid = sorted_catalog[locations] == ids
        categories = np.where(valid, category_ids[catalog_order[locations]], -1)
        values, inverse = np.unique(categories, return_inverse=True)
        count = np.bincount(inverse)
        engaged = np.bincount(inverse, weights=outcomes > 0).astype(np.int64)
        bought = np.bincount(inverse, weights=outcomes == 3).astype(np.int64)
        category_counts.update(dict(zip(values.tolist(), count.tolist())))
        category_engaged.update(dict(zip(values.tolist(), engaged.tolist())))
        category_purchased.update(dict(zip(values.tolist(), bought.tolist())))
    category_rates = pd.DataFrame({"impressions": category_counts, "engaged": category_engaged, "purchased": category_purchased}).fillna(0)
    category_rates["engagement_rate"] = category_rates.engaged / category_rates.impressions
    category_rates["purchase_rate"] = category_rates.purchased / category_rates.impressions
    category_rates.index.name = "cate_id_1"
    category_rates = category_rates.sort_values("impressions", ascending=False)
    def concentration(counts):
        ordered = np.sort(counts)[::-1]
        return [len(counts), counts.mean(), np.median(counts), counts.max(), ordered[:max(1, int(len(counts) * .01))].sum() / counts.sum(),
                ordered[:max(1, int(len(counts) * .20))].sum() / counts.sum(), (counts == 1).mean()]
    popularity = pd.DataFrame({"candidate exposures": concentration(exposures), "history interactions": concentration(interactions)},
                             index=["distinct items", "mean per item", "median per item", "max per item", "share held by top 1%", "share held by top 20%", "share occurring once"])
    action_mix = pd.DataFrame({"actions": actions, "queryless actions": queryless_actions})
    action_mix["share"] = action_mix.actions / n_histories
    action_mix["share queryless within action"] = action_mix["queryless actions"] / action_mix.actions
    categorical = []
    for field, counts in field_counts.items():
        categorical.append({"field": field, "distinct nonmissing": len(counts), "most common values": ", ".join(k for k, _ in counts.most_common(3)),
                            "top value share among nonmissing": max(counts.values()) / sum(counts.values()), "missing": missing[field], "scope": "full catalog"})
    for field, counts in [("history action", actions), ("candidate label", dict(enumerate(label_counts)))]:
        categorical.append({"field": field, "distinct nonmissing": len(counts), "most common values": ", ".join(str(k) for k in counts),
                            "top value share among nonmissing": max(counts.values()) / sum(counts.values()), "missing": 0, "scope": "full behaviour file"})
    categorical = pd.DataFrame(categorical).set_index("field")
    token_lengths = pd.DataFrame({field: describe_frequency(counts) for field, counts in text_counts.items()}).T
    character_lengths = pd.DataFrame({field: describe_frequency(counts) for field, counts in text_chars.items()}).T
    token_lengths["empty / placeholder excluded"] = [excluded_text[field] for field in token_lengths.index]
    # Quantiles need one contiguous gap array; histogramming is chunked to avoid a float copy.
    gap_bins = np.linspace(0, 8, 81)
    gap_hist = np.zeros(len(gap_bins) - 1, dtype=np.int64)
    for start in range(0, len(gaps), 500000):
        gap_hist += np.histogram(np.log10(gaps[start:start + 500000] + 1), bins=gap_bins)[0]
    gap_stats = pd.Series(gaps).describe(percentiles=[.25, .5, .75, .95])
    since_stats = sessions.time_since_last_raw.describe(percentiles=[.25, .5, .75, .95])
    gap_table = pd.DataFrame({"between historical actions (raw units)": gap_stats, "last action to query (raw units)": since_stats})
    gap_table.loc["share equal to zero"] = [(gaps == 0).mean(), sessions.time_since_last_raw.eq(0).mean()]
    overview = pd.DataFrame({"count": {"Users / supplied search records": n_records, "Distinct current query strings": len(raw_queries),
                           "Candidate occurrences": n_candidates, "History actions": n_histories, "Products in catalog": len(catalog_ids),
                           "Distinct candidate products": len(candidate_ids), "Distinct history products": len(historical_ids),
                           "Distinct products in any behaviour": len(all_ids), "Behaviour products missing from catalog": n_missing_behavior_ids,
                           "Distinct brands": len(field_counts["brand_id"]), "Distinct shops (nonmissing)": len(field_counts["shop_id"]),
                           **{f"Distinct category IDs L{k}": len(field_counts[f"cate_id_{k}"]) for k in range(1, 5)},
                           "Current-query term vocabulary": len(query_vocabulary)}})
    feedback = pd.DataFrame({"count": {"Engaged candidate occurrences": int((labels > 0).sum()), "Exposed, no recorded interaction": int((labels == 0).sum()),
                                        "Catalog products absent from all supplied candidate lists": int(len(catalog_ids) - catalog_candidate_mask.sum()), "Positive historical actions": n_histories}})
    metadata_coverage = pd.DataFrame({"metadata present share": {"Candidate occurrences": candidate_catalog_share, "Historical actions": history_catalog_share}})
    return {"sessions": sessions, "overview": overview, "label_distribution": label_distribution, "thresholds": thresholds,
            "action_mix": action_mix, "popularity": popularity, "categorical": categorical, "text_tokens": token_lengths, "text_chars": character_lengths,
            "gap_table": gap_table, "gap_histogram": (gap_bins, gap_hist), "category_rates": category_rates, "feedback": feedback,
            "metadata_coverage": metadata_coverage, "lorenz": {"exposures": compact_lorenz(exposures), "history": compact_lorenz(interactions)},
            "position_rate": pd.Series(position_engaged / position_counts, index=np.arange(1, 31)),
            "positive_prefix_share": positive_prefix_records / positive_records, "all_zero_records": n_records - positive_records,
            "cold_distinct_share": float(cold.mean()), "cold_occurrence_share": float(cold_occurrence_share),
            "candidate_count": n_candidates, "history_count": n_histories, "catalog_count": len(catalog_ids)}


def build_sample_features(data_dir, sample_ids):
    """Compute features on complete sampled records, reusing validated match definitions."""
    data_dir, selected = Path(data_dir), set(np.asarray(sample_ids).tolist())
    records, needed = [], set()
    with (data_dir / "user_behavior_data.txt").open(encoding="utf-8") as handle:
        next(handle)
        for session_id, line in enumerate(handle):
            if session_id not in selected:
                continue
            fields = line.rstrip("\r\n").split("\t")
            candidates, past = fields[1].split("_"), fields[4].split("_")
            queries, actions = fields[3].split("_"), fields[5].split("_")
            labels = np.asarray([int(float(v)) for v in fields[2].split("_")], dtype=np.int8)
            times = np.fromstring(fields[6], sep="_", dtype=np.int64)
            assert len(candidates) == len(labels) and len(past) == len(queries) == len(actions)
            assert len(times) == len(past) + 1
            records.append((session_id, fields[0], candidates, labels, past, queries, actions, times))
            needed.update(candidates); needed.update(past)
    metadata, names = {}, {}
    candidate_ids = {wid for record in records for wid in record[2]}
    with (data_dir / "product_meta_data.txt").open(encoding="utf-8") as handle:
        next(handle)
        for line in handle:
            wid = line.split("\t", 1)[0]
            if wid not in needed:
                continue
            fields = line.rstrip("\r\n").split("\t")
            metadata[wid] = tuple(int(fields[j]) if fields[j] not in ("", "-1") else None for j in (2, 12, 4, 6, 8, 10))
            if wid in candidate_ids:
                names[wid] = (fields[1], fields[3], fields[9])
    hist_ids = np.load(data_dir / "processed/eda_history_item_ids.npy", mmap_mode="r")
    hist_counts = np.load(data_dir / "processed/eda_history_item_counts.npy", mmap_mode="r")
    feature_parts, sessions = [], []
    for session_id, query, candidates, labels, past, queries, actions, times in records:
        query_terms = token_set(query)
        has_query = np.asarray([q != "-1" for q in queries])
        scores, known, _, _ = match_counts(candidates, past, has_query, metadata)
        row = {"session_id": session_id, "hist_len": len(past), "hist_share_no_query": (~has_query).mean(),
               "hist_metadata_coverage": sum(wid in metadata for wid in past) / len(past),
               "time_since_last_raw": times[-1], "time_since_last_h_assumed": times[-1] / 3600,
               "history_span_days_assumed": times[1:-1].sum() / 86400, "query_len_chars": len(query),
               "query_len_terms": len(tokenize(query)), "query_distinct_terms": len(query_terms), "slate_len": len(candidates)}
        for action in ("CLICK", "CART", "ORD", "FLW"):
            row[f"hist_n_{action.lower()}"] = actions.count(action)
        similarities = [overlap_features(query_terms, token_set(q))[2] for q in queries if q != "-1"]
        row["history_query_max_jaccard"] = max(similarities, default=0)
        row["history_query_any_overlap"] = row["history_query_max_jaccard"] > 0
        row["history_query_same_terms"] = any(token_set(q) == query_terms for q in queries if q != "-1")
        sessions.append(row)
        candidate_array = np.asarray(candidates, dtype=np.int64)
        indices = np.minimum(np.searchsorted(hist_ids, candidate_array), len(hist_ids) - 1)
        popularity = np.where(hist_ids[indices] == candidate_array, hist_counts[indices], 0)
        ordered_products = {p for p, a in zip(past, actions) if a == "ORD"}
        pair = pd.DataFrame({"session_id": session_id, "label": labels, "item_hist_popularity_eda": popularity,
                             "item_cold_eda": popularity == 0, "item_in_catalogue": [wid in metadata for wid in candidates],
                             "item_seen_before": scores["all"][:, 0] > 0,
                             "item_ordered_before": [wid in ordered_products for wid in candidates]})
        for source in SOURCES:
            for j, level in enumerate(LEVELS):
                pair[f"aff_{source}_{level}"] = np.where(known[:, j], scores[source][:, j], np.nan)
        text_rows = []
        for wid in candidates:
            if wid not in names:
                text_rows.append((np.nan,) * 5)
                continue
            title, brand, category = (token_set(text) for text in names[wid])
            shared, coverage, jaccard = overlap_features(query_terms, title)
            text_rows.append((shared if title else np.nan, coverage if title else np.nan, jaccard if title else np.nan,
                              bool(query_terms & brand) if brand else np.nan, bool(query_terms & category) if category else np.nan))
        pair[["query_title_shared_terms", "query_title_coverage", "query_title_jaccard", "query_brand_match", "query_cate3_match"]] = pd.DataFrame(text_rows)
        feature_parts.append(pair)
    return pd.DataFrame(sessions).set_index("session_id"), pd.concat(feature_parts, ignore_index=True)
