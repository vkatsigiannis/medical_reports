import csv
import os
from typing import Optional, Literal
from pydantic import Field, create_model
import pandas as pd

from MedicalInformation import *

def get_report_data(report_path: str) -> tuple[str, str]:
    print(f"Processing report: {report_path}")
    pat_id = os.path.splitext(os.path.basename(report_path))[0]
    with open(os.path.join("txt/", report_path), "r", encoding="utf-8") as f:
        report_text = f.read()
    return pat_id, report_text

def get_class_by_key(key):
    classes = {
        'BIRADS': Birads,
        'FamilyHistory': FamilyHistory,
        'ACR': ACR,
        'BPE': BPE,

        'MASS': MASS,
        'massDiameter': massDiameter,
        'massMargins': massMargins,
        'massInternalEnhancement': massInternalEnhancement,

        'NME': NME,
        'nmeDiameter': nmeDiameter,
        'nmeMargins': nmeMargins,
        'nmeInternalEnhancement': nmeInternalEnhancement,

        'NonEnhancingFindings': NonEnhancingFindings,
        'CurveMorphology': CurveMorphology,
        'ADC': ADC,
        'LATERALITY': LATERALITY,
        # add more mappings here as needed
    }
    return classes.get(key)

def merge_dicts(dicts: list[dict]) -> dict:
    result = {}
    for d in dicts:
        result.update(d)
    return result



# def model_performace(
#     path_pred: str,
#     path_gt: str = "GT - edit.xlsx",
#     *,
#     per_class_breakdown: bool = False,
# ) -> None:
#     print("Evaluating model performance...")
#     gt_df = pd.read_excel(path_gt)
#     pred_df = pd.read_csv(path_pred)

#     # Normalize id column name
#     pred_df = pred_df.rename(columns={pred_df.columns[0]: "patID"})
#     gt_df   = gt_df.rename(columns={gt_df.columns[0]: "patID"})

#     # Merge on patID
#     merged = pd.merge(pred_df, gt_df, on="patID", suffixes=("_pred", "_gt"))
#     total = len(merged)

#     results = {}
#     per_class = {}  # col -> {class -> (correct, actual)}

#     for col in pred_df.columns:
#         if col == "patID":
#             continue
#         pred_col = f"{col}_pred"
#         gt_col   = f"{col}_gt"
#         if pred_col not in merged.columns or gt_col not in merged.columns:
#             continue

#         a_raw = merged[pred_col]
#         b_raw = merged[gt_col]

#         # NA positions equal
#         both_na = a_raw.isna() & b_raw.isna()

#         # Case-insensitive compare on normalized strings
#         a = a_raw.astype("string").str.strip().str.casefold()
#         b = b_raw.astype("string").str.strip().str.casefold()

#         eq = a.eq(b)  # booleans with <NA> where either side is NA
#         matches = (eq.fillna(False) | both_na).sum()

#         results[col] = {
#             "matches": int(matches),
#             "total": int(total),
#             "accuracy": (matches / total) if total > 0 else None,
#         }

#         if per_class_breakdown:
#             stats = {}

#             # Non-NA classes
#             notna_mask = b.notna()
#             classes = b[notna_mask].dropna().unique()
#             for c in classes:
#                 actual_mask  = notna_mask & (b == c)
#                 correct_mask = actual_mask & (a == b)
#                 correct = int(correct_mask.sum())
#                 actual  = int(actual_mask.sum())
#                 stats[str(c).upper()] = (correct, actual)

#             # NONE (GT missing)
#             none_actual  = int(b.isna().sum())
#             none_correct = int(both_na.sum())  # pred missing AND GT missing
#             stats["NONE"] = (none_correct, none_actual)

#             per_class[col] = stats

#     # Print results
#     for col, res in results.items():
#         acc = f"{res['accuracy']:.2%}" if res["accuracy"] is not None else "n/a"
#         print(f"{col}: {res['matches']}/{res['total']} matches, accuracy={acc}")
#         if per_class_breakdown and col in per_class:
#             stats = per_class[col]
#             if stats:
#                 parts = [f'{cls}: {c}/{a}' for cls, (c, a) in stats.items()]
#                 print("  per-class:", "; ".join(parts))

#     # Optional heads for debugging
#     print(gt_df.head())
#     print(pred_df.head())


#             writer.writeheader()
#             writer.writerow(row)
#     else:
#         with open(csv_path, "a", encoding="utf-8", newline="") as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writerow(row)


import pandas as pd
from typing import Iterable, Optional, Sequence, Dict, Any

DEFAULT_MISSING_STRINGS = {
    "", "none", "null", "nan", "n/a", "na", "<na>", "εκκρεμεί"
}

def _normalize_series(
    s: pd.Series,
    *,
    casefold: bool = True,
    strip: bool = True,
) -> pd.Series:
    # Keep NA as NA; normalize strings only
    out = s.astype("string")
    if strip:
        out = out.str.strip()
    if casefold:
        out = out.str.casefold()
    return out

def _is_missing(
    s_norm: pd.Series,
    *,
    missing_strings: set[str],
) -> pd.Series:
    # Missing if pandas NA OR normalized string matches missing set
    return s_norm.isna() | s_norm.isin(missing_strings)

def evaluate_categorical_metrics(
    path_pred: str,
    path_gt: str,
    *,
    id_col_pred: Optional[str] = None,   # if None -> first column
    id_col_gt: Optional[str] = None,     # if None -> first column
    metrics: Sequence[str] = ("AccAll", "AccPresent", "AccNull", "GoldCoverage"),
    casefold: bool = True,
    strip: bool = True,
    missing_strings: Optional[set[str]] = None,
    fields: Optional[Sequence[str]] = None,  # evaluate only these fields (without suffixes)
) -> pd.DataFrame:
    """
    Computes per-field metrics for categorical extraction.

    Metrics:
      - AccAll:     exact match over all rows (counts both-missing as match)
      - AccPresent: exact match conditioned on GT present (non-missing)
      - AccNull:    correct-null conditioned on GT missing
      - GoldCoverage: prediction present conditioned on GT present

    Notes:
      - Treats None/NaN/""/"null"/"none"/... as missing (configurable).
      - Compares normalized strings (strip + casefold).
    """
    metrics_set = set(metrics)
    allowed = {"AccAll", "AccPresent", "AccNull", "GoldCoverage"}
    unknown = metrics_set - allowed
    if unknown:
        raise ValueError(f"Unknown metrics: {sorted(unknown)}. Allowed: {sorted(allowed)}")

    missing_strings = set(missing_strings or DEFAULT_MISSING_STRINGS)
    # normalize missing strings to the same normalization rules used for values
    if strip:
        missing_strings = {x.strip() for x in missing_strings}
    if casefold:
        missing_strings = {x.casefold() for x in missing_strings}

    pred_df = pd.read_csv(path_pred)
    gt_df = pd.read_excel(path_gt)

    if id_col_pred is None:
        id_col_pred = pred_df.columns[0]
    if id_col_gt is None:
        id_col_gt = gt_df.columns[0]

    pred_df = pred_df.rename(columns={id_col_pred: "patID"})
    gt_df   = gt_df.rename(columns={id_col_gt: "patID"})

    merged = pd.merge(pred_df, gt_df, on="patID", suffixes=("_pred", "_gt"))
    total = len(merged)

    # Decide which fields to evaluate
    if fields is None:
        # all prediction columns except patID
        fields = [c for c in pred_df.columns if c != "patID"]

    rows: list[Dict[str, Any]] = []

    for col in fields:
        pred_col = f"{col}_pred"
        gt_col   = f"{col}_gt"
        if pred_col not in merged.columns or gt_col not in merged.columns:
            continue

        a_raw = merged[pred_col]
        b_raw = merged[gt_col]

        a = _normalize_series(a_raw, casefold=casefold, strip=strip)
        b = _normalize_series(b_raw, casefold=casefold, strip=strip)

        pred_missing = _is_missing(a, missing_strings=missing_strings)
        gt_missing   = _is_missing(b, missing_strings=missing_strings)

        pred_present = ~pred_missing
        gt_present   = ~gt_missing

        # Exact match where both present
        eq_present = (a == b) & pred_present & gt_present
        # Both missing counts as match (for AccAll)
        both_missing = pred_missing & gt_missing

        out: Dict[str, Any] = {"field": col, "N": int(total)}

        if "AccAll" in metrics_set:
            num = int((eq_present | both_missing).sum())
            out["AccAll"] = (num / total) if total else None

        if "AccPresent" in metrics_set:
            denom = int(gt_present.sum())
            num = int((eq_present).sum())
            out["AccPresent"] = (num / denom) if denom else None
            out["GT_present_n"] = denom  # useful for debugging

        if "AccNull" in metrics_set:
            denom = int(gt_missing.sum())
            num = int((both_missing).sum())
            out["AccNull"] = (num / denom) if denom else None
            out["GT_null_n"] = denom

        if "GoldCoverage" in metrics_set:
            denom = int(gt_present.sum())
            num = int((pred_present & gt_present).sum())
            out["GoldCoverage"] = (num / denom) if denom else None

        rows.append(out)

    return pd.DataFrame(rows).sort_values("field").reset_index(drop=True)