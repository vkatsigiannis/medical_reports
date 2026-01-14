# pip install "transformers>=4.44" accelerate "outlines[transformers]>=1.2.0" "pydantic>=2"
import os, torch
from pathlib import Path
from transformers.utils.logging import set_verbosity_error

import lib
from ReportExtractor import ReportExtractor

if __name__ == "__main__":

    os.environ["CUDA_VISIBLE_DEVICES"] = "5"

    # ======================= CONFIG =======================
    MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct" 
    # MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"
    # MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
    # MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct" # requires access
    # MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"
    # MODEL_ID = "Qwen/Qwen2.5-32B-Instruct"
    # MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"
    # MODEL_ID = "microsoft/Phi-3.5-mini-instruct" # AttributeError: 'DynamicCache' object has no attribute 'seen_tokens'
    # MODEL_ID = "nvidia/Mistral-NeMo-12B-Instruct"
    # MODEL_ID = "mistralai/Mistral-Nemo-Instruct-2407"
    # MODEL_ID = "ilsp/Llama-Krikri-8B-Instruct"


    report_paths = ["pat0001.txt", "pat0002.txt", "pat0003.txt"]
    report_paths = ["pat0002.txt", "pat0003.txt"]
    # report_paths = ["pat0002.txt"]
    # report_paths = os.listdir("txt/")
    # report_paths.sort()
    # report_path = report_paths[:5]
    print(f"Processing {len(report_paths)} reports...")
    for report_path in report_paths:
        print(f"Processing report: {report_path}")
        pat_id = os.path.splitext(os.path.basename(report_path))[0]
        with open(os.path.join("txt/", report_path), "r", encoding="utf-8") as f:
            report_text = f.read()
    
        groups = [
                # ["BIRADS"], 
                # ["FamilyHistory"],
                # ["ACR"],
                # ["BPE"],
                # ["MASS"],
                # ["NME"],
                # ["NonEnhancingFindings"],
                # ["CurveMorphology"],
                # ["ADC"],
                ["LATERALITY"],
            ]

        # result = extract_all(report_text, groups[0])
        results = []
        for group in groups:
            print(f" Extracting fields: {group}")
            re = ReportExtractor(MODEL_ID, keys=group)

            result = re.extract_structured_data(report_text)
            results.append(result)
            print("Extraction result:", result)
        merged_results = lib.merge_dicts(results)
        print("Merged result:", merged_results)
        lib.save_to_csv(pat_id, merged_results, csv_path="reports_extracted_test.csv")