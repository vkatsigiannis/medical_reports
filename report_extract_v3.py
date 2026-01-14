# pip install "transformers>=4.44" accelerate "outlines[transformers]>=1.2.0" "pydantic>=2"
import os, torch
from pathlib import Path
from transformers.utils.logging import set_verbosity_error

import lib
from ReportExtractor import ReportExtractor, Patient

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
    re = ReportExtractor(MODEL_ID)
    for report_path in report_paths:
        
        pat_id, report_text = lib.get_report_data(report_path)
        patient = Patient(report_text)
        patient.ID = pat_id
    
        groups = [
                # ["BIRADS"], 
                # ["FamilyHistory"],
                # ["ACR"],
                # ["BPE"],
                # ["MASS"],
                # ["MassDiameter"],
                ["NME"],
                ["NMEDiameter"],
                # ["NonEnhancingFindings"],
                # ["CurveMorphology"],
                # ["ADC"],
                # ["LATERALITY"],
            ]

        for group in groups:
            re.extract_structured_data(Patient=patient, keys=group)
            # results.append(result)
            # print("Extraction result:", result)
        # merged_results = lib.merge_dicts(results)
        # print("Merged result:", merged_results)
        # print(patient.MASS_gate, patient.NME_gate, patient.LATERALITY, patient.BIRADS, patient.ADC)
        for attr in vars(patient):
            if attr not in ["report_text", "MASS_gate", "NME_gate"]:
                print(f"{attr}: {getattr(patient, attr)}")
        
        patient.save_to_csv(csv_path="reports_extracted_test.csv")
        print('\n')