"""
PretrainedExtractor.py
----------------------
GLiNER (zero-shot NER) + Extractive QA cascade.

Strategy:
  1. GLiNER runs first on the full report (single forward pass).
  2. For any field GLiNER returned None, QA fills in as fallback.
  3. Gating + post-processing applied once at the end.

Drop-in replacement for RegexExtractor / ReportExtractor.
"""

from __future__ import annotations
from typing import Optional

from GLiNERExtractor import GLiNERExtractor
from QAExtractor import QAExtractor


class PretrainedExtractor:
    """GLiNER primary + QA fallback, both fully pretrained."""

    def __init__(
        self,
        gliner_model: str = GLiNERExtractor.DEFAULT_MODEL,
        qa_model: str = QAExtractor.DEFAULT_MODEL,
        gliner_threshold: float = 0.3,
        qa_threshold: float = 0.2,
        device: Optional[int] = None,
    ):
        self.gliner = GLiNERExtractor(
            model_name=gliner_model,
            threshold=gliner_threshold,
        )
        self.qa = QAExtractor(
            model_name=qa_model,
            threshold=qa_threshold,
            device=device,
        )

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
        include_fewshots: bool = False,
        use_regex: bool = False,
    ):
        text = Patient.report_text

        # 1. GLiNER inference (cached per Patient)
        if not hasattr(Patient, "_gliner_cache"):
            Patient._gliner_cache = self.gliner._build_cache(text)
        cache = Patient._gliner_cache

        # 2. Per-field extraction with fallback
        for key in keys:
            if self._skip_mass_field(key, Patient):
                setattr(Patient, key, None)
                continue
            if self._skip_nme_field(key, Patient):
                setattr(Patient, key, None)
                continue

            # GLiNER first
            val = self.gliner.extract_value(key, cache)

            # QA fallback if GLiNER missed
            if val is None:
                val = self.qa.extract_value(key, text)

            setattr(Patient, key, val)

        # 3. Update gates
        if "MASS" in keys:
            val = getattr(Patient, "MASS", None) or "No"
            setattr(Patient, "MASS", val)
            Patient.mass_gate = (val == "Yes")
        if "NME" in keys:
            val = getattr(Patient, "NME", None) or "No"
            setattr(Patient, "NME", val)
            Patient.nme_gate = (val == "Yes")

        # 4. Re-apply gates
        for key in keys:
            if self._skip_mass_field(key, Patient):
                setattr(Patient, key, None)
            if self._skip_nme_field(key, Patient):
                setattr(Patient, key, None)

        # 5. Post-process once
        Patient.post_process()
        return Patient
