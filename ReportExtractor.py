from typing import Optional, Literal
from pydantic import Field, create_model

import os, re, json, outlines, torch, unicodedata
from pathlib import Path

from datetime import datetime

from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils.logging import set_verbosity_error

import lib
import csv

os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"
os.environ["PYTORCH_TRITON_DISABLE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / ".hf_cache"
CACHE_DIR.mkdir(exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)

os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

set_verbosity_error()
assert torch.cuda.is_available(), "CUDA GPU not found."

class Patient:
    def __init__(self, report_text: str):
        
        self.report_text = report_text
        self.mass_gate, self.nme_gate = True, True

        # for key in ["LATERALITY", "MASS", "NME", "LITERACY"]:
        #     setattr(self, key, None)

    # def clear_attributes(self):
    #     for attr in list(self.__dict__.keys()):
    #         delattr(self, attr)
        
    #     return self
    
    def post_process(self):
        if hasattr(self, 'FamilyHistory'):
            if getattr(self, 'FamilyHistory', None) is None:
                setattr(self, 'FamilyHistory', 'No')
        
        if hasattr(self, 'ADC'):
            adc_value = getattr(self, 'ADC', None)
            print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if adc_value is None: setattr(self, 'ADC', None)
            else:
                if adc_value >= 1.4: setattr(self, 'ADC', "NR")
                elif 1.0 < adc_value < 1.4: setattr(self, 'ADC', "I")
                elif adc_value <= 1.0: setattr(self, 'ADC', "R")
                else: setattr(self, 'ADC', None)
            
        if hasattr(self, 'massMargins'):
            massMargins_value = getattr(self, 'massMargins', None)
            # print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if massMargins_value is None: setattr(self, 'massMargins', None)
            if massMargins_value == 'σαφή': setattr(self, 'massMargins', 'C')
            if massMargins_value == 'ασαφή': setattr(self, 'massMargins', 'NC')
        
        if hasattr(self, 'massInternalEnhancement'):
            massInternalEnhancement_value = getattr(self, 'massInternalEnhancement', None)
            # print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if massInternalEnhancement_value is None: setattr(self, 'massInternalEnhancement', None)
            if massInternalEnhancement_value == 'ομοιογενής': setattr(self, 'massInternalEnhancement', 'HO')
            if massInternalEnhancement_value == 'ανομοιογενής': setattr(self, 'massInternalEnhancement', 'HE')

        
        if hasattr(self, 'nmeMargins'):
            nmeMargins_value = getattr(self, 'nmeMargins', None)
            # print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if nmeMargins_value is None: setattr(self, 'nmeMargins', None)
            if nmeMargins_value == 'σαφή': setattr(self, 'nmeMargins', 'C')
            if nmeMargins_value == 'ασαφή': setattr(self, 'nmeMargins', 'NC')
        
        if hasattr(self, 'nmeInternalEnhancement'):
            nmeInternalEnhancement_value = getattr(self, 'nmeInternalEnhancement', None)
            # print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if nmeInternalEnhancement_value is None: setattr(self, 'nmeInternalEnhancement', None)
            if nmeInternalEnhancement_value == 'ομοιογενής': setattr(self, 'nmeInternalEnhancement', 'HO')
            if nmeInternalEnhancement_value == 'ανομοιογενής': setattr(self, 'nmeInternalEnhancement', 'HE')

        return self

        
    def adc_category(adc_value: float) -> str:
        """
        Categorize ADC value according to thresholds:
        • NON RESTRICTED (NR)  => ADC ≥ 1.4 ×10⁻³ mm²/s
        • INTERMEDIATE (I)     => 1.0 < ADC < 1.4 ×10⁻³ mm²/s
        • RESTRICTION (R)      => ADC ≤ 1.0 ×10⁻³ mm²/s
        Args:
        adc_value (float): ADC value in 10⁻³ mm²/s units.
        Returns:
        str: Category ("NR", "I", or "R")
        """
        if adc_value >= 1.4:
            return "NR"
        elif 1.0 < adc_value < 1.4:
            return "I"
        elif adc_value <= 1.0:
            return "R"
        else:
            return None

        
        

    def save_to_csv(self, ORDERED_FIELDS, csv_path: str):
        """
        Args:
            csv_path (str): Path to the CSV file.
        """

        fieldnames = getattr(self, '__dict__').keys()

        to_remove = ['report_text', 'mass_gate', 'nme_gate']
        fieldnames = [k for k in fieldnames if k not in to_remove]
        fieldnames = ORDERED_FIELDS

        # print(fieldnames)
        

        row = {k: getattr(self, k) for k in fieldnames}
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


class ReportExtractor(Patient):
    def __init__(self, MODEL_ID):
        """
        Initializes the ReportExtractor with a list of keys.
        Args:
            keys (list[str]): A list of string keys used to configure field extraction.
        Attributes:
            keys (list[str]): Stores the provided keys.
            FIELDS_SPEC (dict): Specification for fields, including type and validation rules.
            _PROMPT_FIELD_RULES (dict): Mapping of keys to their corresponding prompt rules, 
                constructed by merging prompt rules from classes obtained via lib.get_class_by_key.
        """
        self.MODEL_ID = MODEL_ID
        self.hf_model = AutoModelForCausalLM.from_pretrained(
            self.MODEL_ID,
            dtype=torch.float16,
            cache_dir=str(CACHE_DIR),
            trust_remote_code=True,
            device_map="auto",
            temperature=0.0,
        )
        self.hf_tok = AutoTokenizer.from_pretrained(self.MODEL_ID,
                                            use_fast=False,
                                            cache_dir=str(CACHE_DIR),
                                            trust_remote_code=True)
        self.model = outlines.from_transformers(self.hf_model, self.hf_tok)
        print("Model loaded:", self.MODEL_ID)       
    
    def set_keys(self, keys: list[str], include_fewshots: bool = False):

        self.include_fewshots = include_fewshots
        
        self.keys = keys

        for key in self.keys: setattr(Patient, key, None)


        # print("Extracting fields:", self.keys, getattr(Patient, key))

        self.FIELDS_SPEC = {
            **{k: lib.get_class_by_key(k)._field_spec for k in self.keys},
        }
        
        self._PROMPT_FIELD_RULES = {
            **{k: lib.get_class_by_key(k)._prompt + lib.get_class_by_key(k)._fewshots if self.include_fewshots else lib.get_class_by_key(k)._prompt for k in self.keys},
        }

    def build_prompt(self, report: str) -> str:
        lines = [
            "Task: Read the medical report (may be in Greek) and extract ONLY the following if present:"
            # "Task: Read the breast MRI report (Greek/English) and extract ONLY the requested fields.",
            # "Global rules:",
            # "- Output JSON only. No prose.",
            # "- Return null unless there is an explicit cue in the text. Do not infer.",
            # "- Follow each field’s rule exactly."
            ]
        for k in self.keys:
            lines.append(self._PROMPT_FIELD_RULES[k])
        fields_stub = []
        for k in self.keys:
            fields_stub = [lib.get_class_by_key(k)._field_stub for k in self.keys]

        lines += [
            "Output ONLY JSON:",
            "{ " + ", ".join(fields_stub) + " }",
            "If an item is missing, return null. No extra keys.\n",
            f'Report:\n"""\n{report}\n"""\nJSON:'
        ]
        return "\n".join(lines)

    def apply_chat_template(self, text: str) -> str:
        if hasattr(self.hf_tok, "apply_chat_template"):
            return self.hf_tok.apply_chat_template(
                [{"role": "user", "content": text}],
                tokenize=False,
                add_generation_prompt=True,
            )
        return text

    def make_model(self):
        fields = {k: self.FIELDS_SPEC[k] for k in self.keys}
        return create_model("ExtractSelected", **fields)

    def extract_structured_data(self, Patient, keys: list[str], include_fewshots: bool = False) -> dict:
        self.set_keys(keys, include_fewshots=include_fewshots)

        if 'massDiameter' == self.keys[0] and not self.mass_gate:
            self.massDiameter = None
        if 'massMargins' == self.keys[0] and not self.mass_gate:
            self.massMargins = None
        if 'massInternalEnhancement' == self.keys[0] and not self.mass_gate:
            self.massInternalEnhancement = None
            # return Patient
        
        if 'nmeDiameter' == self.keys[0] and not self.nme_gate:
            self.nmeDiameter = None
        if 'nmeMargins' == self.keys[0] and not self.nme_gate:
            self.nmeMargins = None
        if 'nmeInternalEnhancement' == self.keys[0] and not self.nme_gate:
            self.nmeInternalEnhancement = None
            # return Patient


        DynModel = self.make_model()
        main_prompt = self.apply_chat_template(self.build_prompt(Patient.report_text))
        out = self.model(main_prompt, DynModel, max_new_tokens=320, do_sample=False)
        obj = DynModel.model_validate_json(out).model_dump()

        # if 'FamilyHistory' in self.keys:
        #     if obj.get('FamilyHistory') is None: obj['FamilyHistory'] = 'No'
        if 'MASS' in self.keys:
            if obj.get('MASS') is None: obj['MASS'] = 'No'
            self.mass_gate = True if obj.get('MASS', None)=='Yes' else False
            # self.mass_gate = True if obj.get('MASS', None)=='Yes' else False
        if 'NME' in self.keys:
            if obj.get('NME') is None: obj['NME'] = 'No'
            self.nme_gate = True if obj.get('NME', None)=='Yes' else False
        
        if 'massDiameter' in self.keys and not self.mass_gate:
            self.massDiameter = None

        if 'nmeDiameter' in self.keys and not self.nme_gate:
            self.nmeDiameter = None

        # if 'LATERALITY' in self.keys:
        #     Patient.LATERALITY = obj.get('LATERALITY', None)
        # Patient.LATERALITY = obj.get(k)

        for key in self.keys:
            setattr(Patient, key, obj.get(key, None))
        # Patient.LATERALITY = 

        Patient.post_process()

        # result = {k: obj.get(k) for k in self.keys}

        return Patient

