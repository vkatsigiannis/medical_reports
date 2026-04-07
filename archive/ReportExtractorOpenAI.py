import json
from typing import Any

from openai import OpenAI
from pydantic import create_model

import lib
from ReportExtractor import Patient  # if you keep Patient in same file, remove this import

from typing import Optional, Literal
from pydantic import Field, create_model

import os, re, json, outlines, torch, unicodedata
from pathlib import Path

from datetime import datetime

from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils.logging import set_verbosity_error

import lib
import csv


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
        

        _DIAM_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(mm|cm)\s*$", flags=re.IGNORECASE)
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
            
            

        # --- Post-process massDiameter: "<number> mm|cm" -> float mm (value only) ---
        if hasattr(self, 'massDiameter'):
            massDiameter_value = getattr(self, 'massDiameter', None)

            if massDiameter_value is None:
                setattr(self, 'massDiameter', None)
            else:
                # Expect strings like "12 mm" or "1.2 cm"
                if isinstance(massDiameter_value, str):
                    m = _DIAM_RE.match(massDiameter_value)
                    if not m:
                        setattr(self, 'massDiameter', None)
                    else:
                        num_str, unit = m.group(1), m.group(2).lower()
                        num_str = num_str.replace(",", ".")
                        try:
                            num = float(num_str)
                        except ValueError:
                            setattr(self, 'massDiameter', None)
                        else:
                            if unit == "cm":
                                num *= 10.0
                            # store numeric value only (mm)
                            setattr(self, 'massDiameter', num)
                else:
                    # If model returns unexpected type
                    setattr(self, 'massDiameter', massDiameter_value)


            
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
        
        if hasattr(self, 'LATERALITY'):
            LATERALITY_value = getattr(self, 'LATERALITY', None)
            # print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if LATERALITY_value is None: setattr(self, 'LATERALITY', None)
            if LATERALITY_value == 'UNILATERAL': setattr(self, 'LATERALITY', 'UNI')
            if LATERALITY_value == 'BILATERAL': setattr(self, 'LATERALITY', 'BIL')

        
        if hasattr(self, 'nmeMargins'):
            nmeMargins_value = getattr(self, 'nmeMargins', None)
            # print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if nmeMargins_value is None: setattr(self, 'nmeMargins', None)
            if nmeMargins_value == 'σαφή': setattr(self, 'nmeMargins', 'C')
            if nmeMargins_value == 'ασαφή': setattr(self, 'nmeMargins', 'NC')
        
        # --- Post-process nmeDiameter: "<number> mm|cm" -> float mm (value only) ---
        if hasattr(self, 'nmeDiameter'):
            nmeDiameter_value = getattr(self, 'nmeDiameter', None)

            if nmeDiameter_value is None:
                setattr(self, 'nmeDiameter', None)
            else:
                # Expect strings like "18 mm" or "1.3 cm"
                if isinstance(nmeDiameter_value, str):
                    m = _DIAM_RE.match(nmeDiameter_value)
                    if not m:
                        setattr(self, 'nmeDiameter', None)
                    else:
                        num_str, unit = m.group(1), m.group(2).lower()
                        num_str = num_str.replace(",", ".")
                        try:
                            num = float(num_str)
                        except ValueError:
                            setattr(self, 'nmeDiameter', None)
                        else:
                            if unit == "cm":
                                num *= 10.0
                            # store numeric value only (mm)
                            setattr(self, 'nmeDiameter', num)
                else:
                    # If model returns unexpected type
                    setattr(self, 'nmeDiameter', nmeDiameter_value)
        
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



def _openai_strict_schema(schema: dict) -> dict:
    """
    OpenAI Structured Outputs (strict=True) requires:
      - every object has additionalProperties: false
      - every object has required listing ALL keys in properties
    Also strips some Pydantic-emitted keys that can trigger 400s (e.g., "default").
    """

    def walk(node: Any):
        if isinstance(node, dict):
            # strip common schema keys that aren't needed for validation and can break strict mode
            for k in ("title", "default", "examples"):
                if k in node:
                    del node[k]

            # recurse typical schema containers
            for k in ("anyOf", "allOf", "oneOf"):
                if k in node and isinstance(node[k], list):
                    for item in node[k]:
                        walk(item)

            if "items" in node:
                walk(node["items"])

            for defs_key in ("$defs", "definitions"):
                if defs_key in node and isinstance(node[defs_key], dict):
                    for v in node[defs_key].values():
                        walk(v)

            # enforce strict object rules
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                props = node["properties"]
                node["required"] = list(props.keys())
                node["additionalProperties"] = False
                for v in props.values():
                    walk(v)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    schema = json.loads(json.dumps(schema))  # deep copy
    walk(schema)
    return schema


class ReportExtractorOpenAI:
    """
    Drop-in replacement for your HF/outlines ReportExtractor that uses OpenAI Responses API
    with Structured Outputs (json_schema + strict).

    Expected call site (your script):
        re.extract_structured_data(Patient=patient, keys=group, include_fewshots=False)
    """

    def __init__(self, MODEL_ID: str, *, api_key: str | None = None, base_url: str | None = None):
        self.MODEL_ID = MODEL_ID
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def set_keys(self, keys: list[str], include_fewshots: bool = False):
        self.include_fewshots = include_fewshots
        self.keys = keys

        # keep your existing behavior (optional)
        for key in self.keys:
            setattr(Patient, key, None)

        self.FIELDS_SPEC = {k: lib.get_class_by_key(k)._field_spec for k in self.keys}
        self._PROMPT_FIELD_RULES = {
            k: (lib.get_class_by_key(k)._prompt + lib.get_class_by_key(k)._fewshots)
            if self.include_fewshots
            else lib.get_class_by_key(k)._prompt
            for k in self.keys
        }

    def build_prompt(self, report: str) -> str:
        lines = ["Task: Read the medical report (may be in Greek) and extract ONLY the following if present:"]
        for k in self.keys:
            lines.append(self._PROMPT_FIELD_RULES[k])

        fields_stub = [lib.get_class_by_key(k)._field_stub for k in self.keys]
        lines += [
            "Output ONLY JSON:",
            "{ " + ", ".join(fields_stub) + " }",
            "If an item is missing, return null. No extra keys.\n",
            f'Report:\n"""\n{report}\n"""\nJSON:',
        ]
        return "\n".join(lines)

    def make_model(self):
        fields = {k: self.FIELDS_SPEC[k] for k in self.keys}
        return create_model("ExtractSelected", **fields)

    def extract_structured_data(
        self,
        Patient=None,                 # keep keyword compatibility with your script
        keys: list[str] | None = None,
        include_fewshots: bool = False,
        max_output_tokens: int = 256,
        **kwargs,
    ):
        patient = Patient
        if patient is None:
            raise ValueError("extract_structured_data requires Patient=...")

        if not keys:
            return patient

        self.set_keys(keys, include_fewshots=include_fewshots)

        if not Patient.mass_gate:
            if 'massDiameter' == self.keys[0]: setattr(Patient, 'massDiameter', None)
            if 'massMargins' == self.keys[0]: setattr(Patient, 'massMargins', None)
            if 'massInternalEnhancement' == self.keys[0]: setattr(Patient, 'massInternalEnhancement', None)

            if 'massDiameter' == self.keys[0] or 'massMargins' == self.keys[0] or 'massInternalEnhancement' == self.keys[0]:
                Patient.post_process()

                return Patient
            
        if not Patient.nme_gate:
            if 'nmeDiameter' == self.keys[0]: setattr(Patient, 'nmeDiameter', None)
            if 'nmeMargins' == self.keys[0]: setattr(Patient, 'nmeMargins', None)
            if 'nmeInternalEnhancement' == self.keys[0]: setattr(Patient, 'nmeInternalEnhancement', None)

            if 'nmeDiameter' == self.keys[0] or 'nmeMargins' == self.keys[0] or 'nmeInternalEnhancement' == self.keys[0]:
                Patient.post_process()

                return Patient

        DynModel = self.make_model()
        schema = _openai_strict_schema(DynModel.model_json_schema())

        resp = self.client.responses.create(
            model=self.MODEL_ID,
            input=self.build_prompt(patient.report_text),
            max_output_tokens=max_output_tokens,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "extract_selected",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        data = json.loads(resp.output_text)
        obj = DynModel.model_validate(data).model_dump()

        if 'MASS' in self.keys:
            if obj.get('MASS') is None: obj['MASS'] = 'No'
            Patient.mass_gate = True if obj.get('MASS', None)=='Yes' else False
        if 'NME' in self.keys:
            if obj.get('NME') is None: obj['NME'] = 'No'
            Patient.nme_gate = True if obj.get('NME', None)=='Yes' else False
        
        
        if 'massDiameter' == self.keys[0] and not Patient.mass_gate:
            obj['massDiameter'] = None
        if 'massMargins' == self.keys[0] and not Patient.mass_gate:
            obj['massMargins'] = None
        if 'massInternalEnhancement' == self.keys[0] and not Patient.mass_gate:
            obj['massInternalEnhancement'] = None
            # return Patient
        
        if 'nmeDiameter' == self.keys[0] and not Patient.nme_gate:
            obj['nmeDiameter'] = None
            # Patient.nmeDiameter = None
        if 'nmeMargins' == self.keys[0] and not Patient.nme_gate:
            obj['nmeMargins'] = None
        if 'nmeInternalEnhancement' == self.keys[0] and not Patient.nme_gate:
            obj['nmeInternalEnhancement'] = None

        # assign extracted fields
        for k in self.keys:
            setattr(patient, k, obj.get(k, None))

        patient.post_process()
        return patient