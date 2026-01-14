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
        self.MASS_gate, self.NME_gate = True, True

        # for key in ["LATERALITY", "MASS", "NME", "LITERACY"]:
        #     setattr(self, key, None)

    def save_to_csv(self, csv_path: str):
        """
        Args:
            csv_path (str): Path to the CSV file.
        """

        fieldnames = getattr(self, '__dict__').keys()
        to_remove = ['report_text', 'MASS_gate', 'NME_gate']
        fieldnames = [k for k in fieldnames if k not in to_remove]

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
    
    def set_keys(self, keys: list[str]):
        
        self.keys = keys

        self.FIELDS_SPEC = {
            **{k: lib.get_class_by_key(k)._field_spec for k in self.keys},
        }
        
        self._PROMPT_FIELD_RULES = {
            **{k: lib.get_class_by_key(k)._prompt for k in self.keys},
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

    def extract_structured_data(self, Patient, keys: list[str]) -> dict:
        self.set_keys(keys)

        if 'MassDiameter' == self.keys[0] and not self.MASS_gate:
            self.MassDiameter = None
            return Patient
        
        if 'NMEDiameter' == self.keys[0] and not self.NME_gate:
            self.NMEDiameter = None
            return Patient


        DynModel = self.make_model()
        main_prompt = self.apply_chat_template(self.build_prompt(Patient.report_text))
        out = self.model(main_prompt, DynModel, max_new_tokens=320, do_sample=False)
        obj = DynModel.model_validate_json(out).model_dump()

        if 'MASS' in self.keys:
            self.MASS_gate = True if obj.get('MASS', None)=='Yes' else False
        if 'NME' in self.keys:
            self.NME_gate = True if obj.get('NME', None)=='Yes' else False
        
        if 'MassDiameter' in self.keys and not self.MASS_gate:
            self.MASS_Diameter = None

        if 'NMEDiameter' in self.keys and not self.NME_gate:
            self.NMEDiameter = None

        # if 'LATERALITY' in self.keys:
        #     Patient.LATERALITY = obj.get('LATERALITY', None)
        # Patient.LATERALITY = obj.get(k)

        for key in self.keys:
            setattr(Patient, key, obj.get(key, None))
        # Patient.LATERALITY = 

        # result = {k: obj.get(k) for k in self.keys}

        return Patient

