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

def model_performace(path_pred: str, path_gt: str = "GT - edit.xlsx") -> None:
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

        # Case-insensitive compare on normalized strings for non-NA
        a = a_raw.astype("string").str.strip().str.casefold()
        b = b_raw.astype("string").str.strip().str.casefold()

        eq = a.eq(b)                    # boolean with <NA> where either side is NA
        matches = (eq.fillna(False) | both_na).sum()

        results[col] = {
            "matches": int(matches),
            "total": int(total),
            "accuracy": (matches / total) if total > 0 else None,
        }

    for col, res in results.items():
        acc = f"{res['accuracy']:.2%}" if res["accuracy"] is not None else "n/a"
        print(f"{col}: {res['matches']}/{res['total']} matches, accuracy={acc}")

    print(gt_df.head())
    print(pred_df.head())

# def model_performace(path_pred: str, path_gt='GT - edit.xlsx') -> None:
#     # Read the GT Excel file into a pandas DataFrame

#     print("Evaluating model performance...")
#     gt_df = pd.read_excel(path_gt)
#     pred_df = pd.read_csv(path_pred)



#     # Ensure patient ID columns are named the same
#     pred_id_col = pred_df.columns[0]
#     gt_id_col = gt_df.columns[0]
#     pred_df = pred_df.rename(columns={pred_id_col: "patID"})
#     gt_df = gt_df.rename(columns={gt_id_col: "patID"})

#     # Merge on patID
#     merged = pd.merge(pred_df, gt_df, on="patID", suffixes=("_pred", "_gt"))

#     # For each column in prediction (excluding patID), compare with GT
#     results = {}
#     # print(merged.columns)
#     for col in pred_df.columns:
#         if col == "patID":
#             continue
#         pred_col = f"{col}_pred"
#         gt_col = f"{col}_gt"
#         # if pred_col in merged.columns and gt_col in merged.columns:
#             # pred_vals = merged[pred_col].astype("string").str.lower().replace(None, "")
#             # gt_vals = merged[gt_col].astype("string").str.lower().replace(None, "")
#             # matches = ((pred_vals == gt_vals) | ((pred_vals == "") & (gt_vals == ""))).sum()
#             # total = len(merged)
#             # results[col] = {"matches": matches, "total": total, "accuracy": matches / total if total > 0 else None}
#         if pred_col in merged.columns and gt_col in merged.columns:
#             matches = (merged[pred_col].astype("string").str.lower() == merged[gt_col].astype("string").str.lower()).sum()
#             total = len(merged)
#             results[col] = {"matches": matches, "total": total, "accuracy": matches / total if total > 0 else None}

#     # Print results
#     for col, res in results.items():
#         print(f"{col}: {res['matches']}/{res['total']} matches, accuracy={res['accuracy']:.2%}")


#     print(gt_df.head())    
#     print(pred_df.head())
    


# def save_to_csv(pat_id: str, data: dict, csv_path: str = "reports_extracted.csv") -> None:
#     """
#     Save one JSON dict as a row in CSV.
#     First column: patID
#     Columns: patID + all FIELDS_SPEC keys
#     Handles Greek characters correctly for Excel.
#     """
#     fieldnames = ["patID"] + list(data.keys())
#     row = {"patID": pat_id}

#     # keep Greek text as-is; empty string for nulls
#     for k in data.keys():
#         v = data.get(k, None)
#         row[k] = "" if v is None else v

#     file_exists = os.path.exists(csv_path)

#     # Use UTF-8 BOM on first write so Excel auto-detects encoding
#     if not file_exists:
#         with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerow(row)
#     else:
#         with open(csv_path, "a", encoding="utf-8", newline="") as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writerow(row)

