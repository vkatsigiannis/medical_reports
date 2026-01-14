import csv
import os
from typing import Optional, Literal
from pydantic import Field, create_model

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
        'NME': NME,
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



def save_to_csv(pat_id: str, data: dict, csv_path: str = "reports_extracted.csv") -> None:
    """
    Save one JSON dict as a row in CSV.
    First column: patID
    Columns: patID + all FIELDS_SPEC keys
    Handles Greek characters correctly for Excel.
    """
    fieldnames = ["patID"] + list(data.keys())
    row = {"patID": pat_id}

    # keep Greek text as-is; empty string for nulls
    for k in data.keys():
        v = data.get(k, None)
        row[k] = "" if v is None else v

    file_exists = os.path.exists(csv_path)

    # Use UTF-8 BOM on first write so Excel auto-detects encoding
    if not file_exists:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)
    else:
        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(row)

