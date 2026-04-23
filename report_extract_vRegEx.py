# pip install "transformers>=4.44" accelerate "outlines[transformers]>=1.2.0" "pydantic>=2"
import os
from pathlib import Path

import lib
from Patient import Patient           # lightweight — no torch/outlines needed
from RegexExtractor import RegexExtractor


if __name__ == "__main__":

    # os.environ["CUDA_VISIBLE_DEVICES"] = "5"

    # ======================= CONFIG =======================
    # MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
    # MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"
    # MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
    # MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"  # requires access
    MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"
    # MODEL_ID = "Qwen/Qwen2.5-32B-Instruct"
    # MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"
    # MODEL_ID = "microsoft/Phi-3.5-mini-instruct"
    # MODEL_ID = "nvidia/Mistral-NeMo-12B-Instruct"
    # MODEL_ID = "mistralai/Mistral-Nemo-Instruct-2407"
    # MODEL_ID = "ilsp/Llama-Krikri-8B-Instruct"

    all_reports = os.listdir("txt/")
    all_reports.sort()

    report_paths = all_reports

    report_paths = os.listdir("txt/")[0:]
    report_paths.sort()
    print(f"Processing {len(report_paths)} reports...")

    extract_information = True
    use_regex = True   # ← set False to use the LLM extractor (requires GPU + outlines)

    if extract_information:

        if use_regex:
            extractor = RegexExtractor()
        else:
            # Heavy imports only when actually needed
            import openai
            openai.api_key = os.environ.get("OPENAI_API_KEY", "")
            from ReportExtractor import ReportExtractor
            extractor = ReportExtractor(MODEL_ID)

        for report_path in report_paths:

            pat_id, report_text = lib.get_report_data(report_path)
            patient = Patient(report_text)
            patient.ID = pat_id

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
                    # ["ADC"],
                    ["LATERALITY"],
                ]

            for group in groups:
                extractor.extract_structured_data(
                    Patient=patient,
                    keys=group,
                    include_fewshots=False,
                    use_regex=use_regex,
                )

            ORDERED_FIELDS = ["ID"] + [k for grp in groups for k in grp]

            for attr in ORDERED_FIELDS:
                if attr not in ["report_text", "mass_gate", "nme_gate"]:
                    print(f"{attr}: {getattr(patient, attr)}")

            patient.save_to_csv(ORDERED_FIELDS, csv_path="reports_extracted_RegEx.csv")

    # ── Evaluation ────────────────────────────────────────────────────────
    eval_pred = "reports_extracted_RegEx.csv"
    eval_gt   = "GT_gpt5_2_1.xlsx"

    if os.path.exists(eval_pred) and os.path.exists(eval_gt):
        df = lib.evaluate_categorical_metrics(
            path_pred=eval_pred,
            path_gt=eval_gt,
            metrics=("AccAll", "AccPresent", "AccNull", "GoldCoverage"),
        )
        print(df)
    else:
        missing = [f for f in (eval_pred, eval_gt) if not os.path.exists(f)]
        print(f"Skipping evaluation — missing file(s): {missing}")
