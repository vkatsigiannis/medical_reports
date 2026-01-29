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
        'MassDiameter': MassDiameter,
        'NME': NME,
        'NMEDiameter': NMEDiameter,
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


import pandas as pd

import pandas as pd

def model_performace(
    path_pred: str,
    path_gt: str = "GT - edit.xlsx",
    *,
    per_class_breakdown: bool = False,
) -> None:
    print("Evaluating model performance...")
    gt_df = pd.read_excel(path_gt)
    pred_df = pd.read_csv(path_pred)

    # Normalize id column name
    pred_df = pred_df.rename(columns={pred_df.columns[0]: "patID"})
    gt_df   = gt_df.rename(columns={gt_df.columns[0]: "patID"})

    # Merge on patID
    merged = pd.merge(pred_df, gt_df, on="patID", suffixes=("_pred", "_gt"))
    total = len(merged)

    results = {}
    per_class = {}  # col -> {class -> (correct, actual)}

    for col in pred_df.columns:
        if col == "patID":
            continue
        pred_col = f"{col}_pred"
        gt_col   = f"{col}_gt"
        if pred_col not in merged.columns or gt_col not in merged.columns:
            continue

        a_raw = merged[pred_col]
        b_raw = merged[gt_col]

        # NA positions equal
        both_na = a_raw.isna() & b_raw.isna()

        # Case-insensitive compare on normalized strings
        a = a_raw.astype("string").str.strip().str.casefold()
        b = b_raw.astype("string").str.strip().str.casefold()

        eq = a.eq(b)  # booleans with <NA> where either side is NA
        matches = (eq.fillna(False) | both_na).sum()

        results[col] = {
            "matches": int(matches),
            "total": int(total),
            "accuracy": (matches / total) if total > 0 else None,
        }

        if per_class_breakdown:
            stats = {}

            # Non-NA classes
            notna_mask = b.notna()
            classes = b[notna_mask].dropna().unique()
            for c in classes:
                actual_mask  = notna_mask & (b == c)
                correct_mask = actual_mask & (a == b)
                correct = int(correct_mask.sum())
                actual  = int(actual_mask.sum())
                stats[str(c).upper()] = (correct, actual)

            # NONE (GT missing)
            none_actual  = int(b.isna().sum())
            none_correct = int(both_na.sum())  # pred missing AND GT missing
            stats["NONE"] = (none_correct, none_actual)

            per_class[col] = stats

    # Print results
    for col, res in results.items():
        acc = f"{res['accuracy']:.2%}" if res["accuracy"] is not None else "n/a"
        print(f"{col}: {res['matches']}/{res['total']} matches, accuracy={acc}")
        if per_class_breakdown and col in per_class:
            stats = per_class[col]
            if stats:
                parts = [f'{cls}: {c}/{a}' for cls, (c, a) in stats.items()]
                print("  per-class:", "; ".join(parts))

    # Optional heads for debugging
    print(gt_df.head())
    print(pred_df.head())


#             writer.writeheader()
#             writer.writerow(row)
#     else:
#         with open(csv_path, "a", encoding="utf-8", newline="") as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writerow(row)

