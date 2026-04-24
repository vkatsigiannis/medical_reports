"""
report_extract_vPretrained.py
-----------------------------
Run pretrained zero-shot extraction on a folder of Greek breast-MRI reports.

Switch EXTRACTOR_TYPE between:
    - "gliner"    : GLiNER zero-shot NER only
    - "qa"        : Extractive QA only (XLM-RoBERTa SQuAD2)
    - "combined"  : GLiNER + QA cascade (recommended)

Install:
    pip install -r requirements_pretrained.txt
"""

import os
from pathlib import Path

import lib
from Patient import Patient


if __name__ == "__main__":

    # ============================ CONFIG ============================
    EXTRACTOR_TYPE = "combined"          # "gliner" | "qa" | "combined"
    INPUT_DIR      = "txt/"
    OUTPUT_CSV     = f"reports_extracted_{EXTRACTOR_TYPE}.csv"
    GT_XLSX        = "GT_gpt5_2_1.xlsx"
    DEVICE         = None                # None → auto (cuda if available)
    VERBOSE        = False               # per-patient field print-out
    # ================================================================

    # Optionally limit to a GPU
    # os.environ["CUDA_VISIBLE_DEVICES"] = "5"

    # Remove stale output so we don't append to an old file
    if os.path.exists(OUTPUT_CSV):
        os.remove(OUTPUT_CSV)

    # Build extractor
    if EXTRACTOR_TYPE == "gliner":
        from GLiNERExtractor import GLiNERExtractor
        extractor = GLiNERExtractor()
    elif EXTRACTOR_TYPE == "qa":
        from QAExtractor import QAExtractor
        extractor = QAExtractor(device=DEVICE)
    elif EXTRACTOR_TYPE == "combined":
        from PretrainedExtractor import PretrainedExtractor
        extractor = PretrainedExtractor(device=DEVICE)
    else:
        raise ValueError(f"Unknown EXTRACTOR_TYPE: {EXTRACTOR_TYPE!r}")

    # List reports
    report_paths = sorted(os.listdir(INPUT_DIR))
    report_paths = report_paths[:]  # limit for testing
    print(f"Processing {len(report_paths)} reports with '{EXTRACTOR_TYPE}' extractor…")

    # Field groups (match your existing pipeline order)
    groups = [
        ["BIRADS"],
        ["FamilyHistory"],
        ["ACR"],
        ["BPE"],
        ["MASS"],
        ["massInternalEnhancement"],
        ["massMargins"],
        ["massDiameter"],
        ["NME"],
        ["nmeInternalEnhancement"],
        ["nmeMargins"],
        ["nmeDiameter"],
        ["NonEnhancingFindings"],
        ["CurveMorphology"],
        ["LATERALITY"],
    ]
    ORDERED_FIELDS = ["ID"] + [k for grp in groups for k in grp]

    # ---------------- Main loop ----------------
    for i, report_path in enumerate(report_paths, 1):
        pat_id, report_text = lib.get_report_data(report_path)
        patient = Patient(report_text)
        patient.ID = pat_id

        for group in groups:
            extractor.extract_structured_data(
                Patient=patient,
                keys=group,
                include_fewshots=False,
            )

        if VERBOSE:
            print(f"[{i}/{len(report_paths)}] {pat_id}")
            for attr in ORDERED_FIELDS:
                if attr not in ("report_text", "mass_gate", "nme_gate"):
                    print(f"  {attr}: {getattr(patient, attr)}")
            print()

        patient.save_to_csv(ORDERED_FIELDS, csv_path=OUTPUT_CSV)

    print(f"\nWrote: {OUTPUT_CSV}")

    # ---------------- Evaluation ----------------
    if os.path.exists(GT_XLSX):
        df = lib.evaluate_categorical_metrics(
            path_pred=OUTPUT_CSV,
            path_gt=GT_XLSX,
            metrics=("AccAll", "AccPresent", "AccNull", "GoldCoverage"),
        )
        print("\n=== Evaluation ===")
        print(df.to_string(index=False))
    else:
        print(f"\nSkipping evaluation — ground-truth file not found: {GT_XLSX}")
