# pip install "transformers>=4.44" accelerate "outlines[transformers]>=1.2.0" "pydantic>=2"
import os, torch
from pathlib import Path
from transformers.utils.logging import set_verbosity_error

import lib
from ReportExtractor import ReportExtractor, Patient
from ReportExtractorOpenAI import ReportExtractorOpenAI

if __name__ == "__main__":

    os.environ["CUDA_VISIBLE_DEVICES"] = "5"
    os.environ["OPENAI_API_KEY"] = "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"

    import openai

    # Setting the API key
    openai.api_key = os.environ['OPENAI_API_KEY']
    openai.api_key = "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"

    # Perform tasks using OpenAI API
    # print(openai.Model.list()) # List all OpenAI models

    # ======================= CONFIG =======================
    MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct" 
    # MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"
    MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
    # MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct" # requires access
    # MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"
    # MODEL_ID = "Qwen/Qwen2.5-32B-Instruct"
    # MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"
    # MODEL_ID = "microsoft/Phi-3.5-mini-instruct" # AttributeError: 'DynamicCache' object has no attribute 'seen_tokens'
    # MODEL_ID = "nvidia/Mistral-NeMo-12B-Instruct"
    # MODEL_ID = "mistralai/Mistral-Nemo-Instruct-2407"
    MODEL_ID = "ilsp/Llama-Krikri-8B-Instruct"


    # report_paths = ["pat0001.txt", "pat0002.txt", "pat0003.txt"]
    # report_paths = ["pat0002.txt", "pat0003.txt"]
    # report_paths = ["pat0002.txt"]
    # report_paths = ["pat0006.txt"]
    all_reports = os.listdir("txt/")
    all_reports.sort()

    report_paths = all_reports

    # report_paths = os.listdir("txt/")[0:4]
    # report_paths = all_reports[667:668]
    report_paths = all_reports[0:]
    # report_paths = all_reports[663:]
    # report_paths = os.listdir("txt/")[666:668]
    # report_paths = os.listdir(r"txt/541_728/")[0:4]
    report_paths.sort()
    # report_path = report_paths[:50]
    print(f"Processing {len(report_paths)} reports...")

    extract_information = True
    # extract_information = False

    if extract_information:

        re = ReportExtractor(MODEL_ID)
        # # re = ReportExtractorOpenAI(MODEL_ID="gpt-4.1")
        # # re = ReportExtractorOpenAI(MODEL_ID="gpt-5.2")
        # re = ReportExtractorOpenAI(MODEL_ID="gpt-5-pro")
        # for report_path in report_paths:
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
                # re.extract_structured_data(Patient=patient, keys=group, include_fewshots=False)
                re.extract_structured_data(Patient=patient, keys=group, include_fewshots=True)
                # results.append(result)
                # print("Extraction result:", result)
            # merged_results = lib.merge_dicts(results)
            # print("Merged result:", merged_results)
            # print(patient.mass_gate, patient.nme_gate, patient.LATERALITY, patient.BIRADS, patient.ADC)
            # for attr in vars(patient):
            ORDERED_FIELDS = ["ID"] + [k for grp in groups for k in grp]

            for attr in ORDERED_FIELDS:
                if attr not in ["report_text", "mass_gate", "nme_gate"]:
                    print(f"{attr}: {getattr(patient, attr)}")
            
            patient.save_to_csv(ORDERED_FIELDS, csv_path="reports_extracted_test_728reports_Krikri_8B_fewshots.csv")
            # patient.save_to_csv(ORDERED_FIELDS, csv_path="reports_extracted_temp.csv")
            # save_to_json_path = f"json/{pat_id}.json"
            # patient.save_to_json(ORDERED_FIELDS, json_path=save_to_json_path)
            # print('\n')
            

    # lib.model_performace(path_pred="GT_gpt5_2_1.csv", path_gt='GT - edit.xlsx', per_class_breakdown=True)
    # lib.model_performace(path_pred="reports_extracted_0_728.csv", path_gt='GT_gpt5_2_1.xlsx', per_class_breakdown=True)


    df = lib.evaluate_categorical_metrics(
    path_pred="reports_extracted_test_728reports_Krikri_8B_fewshots.csv",
    path_gt="GT_gpt5_2_1.xlsx",
    metrics=("AccAll", "AccPresent", "AccNull", "GoldCoverage"),
    )
    print(df)