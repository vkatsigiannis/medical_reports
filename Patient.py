"""
Patient.py
----------
Standalone Patient class extracted from ReportExtractor.py.
No heavy dependencies (no outlines, torch, transformers).
"""

import os
import re
import csv
import json


class Patient:
    def __init__(self, report_text: str):
        self.report_text = report_text
        self.mass_gate, self.nme_gate = True, True

    def post_process(self):

        _DIAM_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(mm|cm)\s*$", flags=re.IGNORECASE)

        if hasattr(self, 'FamilyHistory'):
            if getattr(self, 'FamilyHistory', None) is None:
                self.FamilyHistory = 'No'

        if hasattr(self, 'ADC'):
            adc_value = getattr(self, 'ADC', None)
            print(f"Post-processing ADC value: {adc_value}, the type is {type(adc_value)}")
            if adc_value is None:
                self.ADC = None
            elif adc_value >= 1.4:
                self.ADC = "NR"
            elif 1.0 < adc_value < 1.4:
                self.ADC = "I"
            elif adc_value <= 1.0:
                self.ADC = "R"
            else:
                self.ADC = None

        # --- Post-process massDiameter: "<number> mm|cm" -> float mm ---
        if hasattr(self, 'massDiameter'):
            massDiameter_value = getattr(self, 'massDiameter', None)
            if massDiameter_value is None:
                self.massDiameter = None
            elif isinstance(massDiameter_value, str):
                m = _DIAM_RE.match(massDiameter_value)
                if not m:
                    self.massDiameter = None
                else:
                    num_str, unit = m.group(1), m.group(2).lower()
                    num_str = num_str.replace(",", ".")
                    try:
                        num = float(num_str)
                    except ValueError:
                        self.massDiameter = None
                    else:
                        if unit == "cm":
                            num *= 10.0
                        self.massDiameter = num

        if hasattr(self, 'massMargins'):
            val = getattr(self, 'massMargins', None)
            if val == 'σαφή':
                self.massMargins = 'C'
            elif val == 'ασαφή':
                self.massMargins = 'NC'

        if hasattr(self, 'massInternalEnhancement'):
            val = getattr(self, 'massInternalEnhancement', None)
            if val == 'ομοιογενής':
                self.massInternalEnhancement = 'HO'
            elif val == 'ανομοιογενής':
                self.massInternalEnhancement = 'HE'

        if hasattr(self, 'LATERALITY'):
            val = getattr(self, 'LATERALITY', None)
            if val == 'UNILATERAL':
                self.LATERALITY = 'UNI'
            elif val == 'BILATERAL':
                self.LATERALITY = 'BIL'

        if hasattr(self, 'nmeMargins'):
            val = getattr(self, 'nmeMargins', None)
            if val == 'σαφή':
                self.nmeMargins = 'C'
            elif val == 'ασαφή':
                self.nmeMargins = 'NC'

        # --- Post-process nmeDiameter: "<number> mm|cm" -> float mm ---
        if hasattr(self, 'nmeDiameter'):
            nmeDiameter_value = getattr(self, 'nmeDiameter', None)
            if nmeDiameter_value is None:
                self.nmeDiameter = None
            elif isinstance(nmeDiameter_value, str):
                m = _DIAM_RE.match(nmeDiameter_value)
                if not m:
                    self.nmeDiameter = None
                else:
                    num_str, unit = m.group(1), m.group(2).lower()
                    num_str = num_str.replace(",", ".")
                    try:
                        num = float(num_str)
                    except ValueError:
                        self.nmeDiameter = None
                    else:
                        if unit == "cm":
                            num *= 10.0
                        self.nmeDiameter = num

        if hasattr(self, 'nmeInternalEnhancement'):
            val = getattr(self, 'nmeInternalEnhancement', None)
            if val == 'ομοιογενής':
                self.nmeInternalEnhancement = 'HO'
            elif val == 'ανομοιογενής':
                self.nmeInternalEnhancement = 'HE'

        return self

    @staticmethod
    def adc_category(adc_value: float) -> str:
        """
        Categorize ADC value according to thresholds:
        • NON RESTRICTED (NR)  => ADC >= 1.4 x10^-3 mm^2/s
        • INTERMEDIATE (I)     => 1.0 < ADC < 1.4
        • RESTRICTION (R)      => ADC <= 1.0
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
            ORDERED_FIELDS: List of field names to write.
            csv_path (str): Path to the CSV file.
        """
        fieldnames = ORDERED_FIELDS
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

    def save_to_json(self, ORDERED_FIELDS, json_path: str):
        """
        Save the current object as one JSON record inside a JSON array file.
        """
        fieldnames = ORDERED_FIELDS
        row = {k: getattr(self, k, None) for k in fieldnames}

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
                except json.JSONDecodeError:
                    data = []
        else:
            data = []

        data.append(row)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
