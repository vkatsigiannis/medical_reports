"""
QAExtractor.py
--------------
Zero-shot extraction via multilingual Extractive QA (XLM-RoBERTa SQuAD2).
Output is guaranteed to be a verbatim substring → no hallucination.

Drop-in replacement for RegexExtractor / ReportExtractor.

Install:
    pip install transformers torch
"""

from __future__ import annotations
from typing import Optional

try:
    import torch
    from transformers import pipeline
except ImportError as e:
    raise ImportError(
        "transformers/torch not installed. Run: pip install transformers torch"
    ) from e

# Reuse parsers from GLiNERExtractor
from GLiNERExtractor import (
    _parse_birads, _parse_acr, _parse_bpe, _parse_diameter,
    _parse_margins, _parse_enhancement, _parse_curve, _parse_adc,
    _parse_laterality, _parse_family_history, _strip_accents,
)


# Per-field Greek questions (match source language → better QA scores)
_QUESTIONS = {
    "BIRADS":                  "Ποια είναι η κατηγορία BI-RADS;",
    "ACR":                     "Ποια είναι η πυκνότητα μαστού ACR;",
    "BPE":                     "Ποια είναι η ενίσχυση υποστρώματος BPE;",
    "MASS":                    "Υπάρχει μάζα ή συμπαγής αλλοίωση;",
    "NME":                     "Υπάρχει μη μαζόμορφη ενίσχυση;",
    "NonEnhancingFindings":    "Υπάρχουν κύστεις ή κυστικές αλλοιώσεις;",
    "massDiameter":            "Ποια είναι η διάμετρος της μάζας;",
    "nmeDiameter":             "Ποια είναι η διάμετρος της μη μαζόμορφης ενίσχυσης;",
    "massMargins":             "Ποια είναι τα όρια της μάζας;",
    "massInternalEnhancement": "Ποιο είναι το εσωτερικό πρότυπο ενίσχυσης της μάζας;",
    "nmeMargins":              "Ποια είναι τα όρια της μη μαζόμορφης ενίσχυσης;",
    "nmeInternalEnhancement":  "Ποιο είναι το εσωτερικό πρότυπο ενίσχυσης της NME;",
    "CurveMorphology":         "Ποιος είναι ο τύπος της αιμοδυναμικής καμπύλης;",
    "ADC":                     "Ποια είναι η τιμή ADC;",
    "LATERALITY":              "Σε ποιον μαστό εντοπίζονται τα ευρήματα;",
    "FamilyHistory":           "Ποιο είναι το οικογενειακό ιστορικό καρκίνου;",
}


_PARSERS = {
    "BIRADS":                  _parse_birads,
    "ACR":                     _parse_acr,
    "BPE":                     _parse_bpe,
    "massDiameter":            _parse_diameter,
    "nmeDiameter":             _parse_diameter,
    "massMargins":             _parse_margins,
    "massInternalEnhancement": _parse_enhancement,
    "nmeMargins":              _parse_margins,
    "nmeInternalEnhancement":  _parse_enhancement,
    "CurveMorphology":         _parse_curve,
    "ADC":                     _parse_adc,
    "LATERALITY":              _parse_laterality,
    "FamilyHistory":           _parse_family_history,
}

_PRESENCE_FIELDS = {"MASS", "NME", "NonEnhancingFindings"}


def _yes_no_from_answer(answer: str, score: float, threshold: float) -> str:
    if score < threshold or not answer.strip():
        return "No"
    s = _strip_accents(answer)
    negations = ("δεν ", "αρνητ", "χωρις", "ουδεν", "negative", "not ", "no ")
    padded = f" {s} "
    if any(k in padded for k in negations):
        return "No"
    return "Yes"


class QAExtractor:
    """Extractive QA extractor using multilingual SQuAD2."""

    DEFAULT_MODEL = "deepset/xlm-roberta-large-squad2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        threshold: float = 0.2,
        device: Optional[int] = None,
        max_answer_len: int = 30,
    ):
        if device is None:
            device = 0 if torch.cuda.is_available() else -1
        print(f"[QAExtractor] Loading {model_name} on device {device}…")
        self.pipe = pipeline(
            "question-answering",
            model=model_name,
            device=device,
        )
        self.threshold = threshold
        self.max_answer_len = max_answer_len
        print("[QAExtractor] Loaded.")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def _ask(self, field: str, context: str) -> dict:
        return self.pipe(
            {"question": _QUESTIONS[field], "context": context},
            handle_impossible_answer=True,
            max_answer_len=self.max_answer_len,
        )

    def extract_value(self, field: str, context: str):
        if field not in _QUESTIONS:
            return None
        out = self._ask(field, context)
        answer = out.get("answer", "") or ""
        score = float(out.get("score", 0.0))

        if field in _PRESENCE_FIELDS:
            return _yes_no_from_answer(answer, score, self.threshold)

        if score < self.threshold or not answer.strip():
            return None

        parser = _PARSERS.get(field)
        return parser(answer) if parser else answer.strip()

    # ------------------------------------------------------------------
    # Gating
    # ------------------------------------------------------------------

    @staticmethod
    def _skip_mass_field(key: str, Patient) -> bool:
        return (key in ("massDiameter", "massMargins", "massInternalEnhancement")
                and not Patient.mass_gate)

    @staticmethod
    def _skip_nme_field(key: str, Patient) -> bool:
        return (key in ("nmeDiameter", "nmeMargins", "nmeInternalEnhancement")
                and not Patient.nme_gate)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_structured_data(
        self,
        Patient,
        keys: list[str],
        include_fewshots: bool = False,  # API parity
        use_regex: bool = False,         # API parity
    ):
        context = Patient.report_text

        for key in keys:
            if self._skip_mass_field(key, Patient):
                setattr(Patient, key, None)
                continue
            if self._skip_nme_field(key, Patient):
                setattr(Patient, key, None)
                continue
            setattr(Patient, key, self.extract_value(key, context))

        if "MASS" in keys:
            val = getattr(Patient, "MASS", None) or "No"
            setattr(Patient, "MASS", val)
            Patient.mass_gate = (val == "Yes")
        if "NME" in keys:
            val = getattr(Patient, "NME", None) or "No"
            setattr(Patient, "NME", val)
            Patient.nme_gate = (val == "Yes")

        for key in keys:
            if self._skip_mass_field(key, Patient):
                setattr(Patient, key, None)
            if self._skip_nme_field(key, Patient):
                setattr(Patient, key, None)

        Patient.post_process()
        return Patient
