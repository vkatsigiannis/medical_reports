"""
GLiNERExtractor.py
------------------
Zero-shot NER extraction using GLiNER. No training required.

Drop-in replacement for RegexExtractor / ReportExtractor.
Same interface: extract_structured_data(Patient, keys, ...).

Install:
    pip install gliner
"""

from __future__ import annotations
import re
import unicodedata
from typing import Optional

try:
    from gliner import GLiNER
except ImportError as e:
    raise ImportError("GLiNER not installed. Run: pip install gliner") from e


# ── Entity label descriptions (natural language works better than codes) ────
_LABELS = [
    "BIRADS category number",
    "ACR breast density grade letter",
    "BPE background parenchymal enhancement level",
    "breast mass lesion",
    "non-mass enhancement NME lesion",
    "cyst cystic lesion",
    "mass diameter size measurement",
    "NME diameter size measurement",
    "mass margins description",
    "mass internal enhancement pattern",
    "NME margins description",
    "NME internal enhancement pattern",
    "kinetic curve type",
    "ADC value measurement",
    "laterality side left right bilateral",
    "family history of cancer",
]

_LABEL_TO_FIELD = {
    "BIRADS category number":                       "BIRADS",
    "ACR breast density grade letter":              "ACR",
    "BPE background parenchymal enhancement level": "BPE",
    "breast mass lesion":                           "MASS",
    "non-mass enhancement NME lesion":              "NME",
    "cyst cystic lesion":                           "NonEnhancingFindings",
    "mass diameter size measurement":               "massDiameter",
    "NME diameter size measurement":                "nmeDiameter",
    "mass margins description":                     "massMargins",
    "mass internal enhancement pattern":            "massInternalEnhancement",
    "NME margins description":                      "nmeMargins",
    "NME internal enhancement pattern":             "nmeInternalEnhancement",
    "kinetic curve type":                           "CurveMorphology",
    "ADC value measurement":                        "ADC",
    "laterality side left right bilateral":         "LATERALITY",
    "family history of cancer":                     "FamilyHistory",
}


# ── Value parsers (convert raw span text to expected schema value) ──────────

_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


def _parse_birads(span: str) -> Optional[int]:
    m = re.search(r"\b([0-6])\b", span)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(VI|V|IV|III|II|I)\b", span, re.IGNORECASE)
    if m:
        return _ROMAN.get(m.group(1).upper())
    return None


def _parse_acr(span: str) -> Optional[str]:
    m = re.search(r"\b([ABCD])(?:\s*[-–]\s*([ABCD]))?\b", span, re.IGNORECASE)
    if m:
        g1 = m.group(1).upper()
        return f"{g1}-{m.group(2).upper()}" if m.group(2) else g1
    return None


_BPE_MAP = {
    "minimal": "Minimal", "μηδαμινη": "Minimal",
    "mild": "Mild", "ηπια": "Mild",
    "moderate": "Moderate", "μετρια": "Moderate",
    "marked": "Marked", "εντονη": "Marked",
}


def _parse_bpe(span: str) -> Optional[str]:
    s = _strip_accents(span)
    for key, val in _BPE_MAP.items():
        if key in s:
            return val
    return None


def _parse_diameter(span: str) -> Optional[str]:
    """Return '<num> mm' or '<num> cm'; Patient.post_process converts to float mm."""
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(mm|cm|χιλ|εκ)",
        span, re.IGNORECASE,
    )
    if not m:
        return None
    num = m.group(1).replace(",", ".")
    unit = m.group(2).lower()
    if unit.startswith(("cm", "εκ")):
        return f"{num} cm"
    return f"{num} mm"


def _parse_margins(span: str) -> Optional[str]:
    s = _strip_accents(span)
    if "ασαφ" in s or "ill" in s or "indistinct" in s or "spiculat" in s or "irregular" in s:
        return "ασαφή"
    if "σαφ" in s or "well" in s or "circumscribed" in s or "distinct" in s:
        return "σαφή"
    return None


def _parse_enhancement(span: str) -> Optional[str]:
    s = _strip_accents(span)
    if "ανομοιογεν" in s or "heterogen" in s:
        return "ανομοιογενής"
    if "ομοιογεν" in s or "homogen" in s:
        return "ομοιογενής"
    return None


def _parse_curve(span: str) -> Optional[str]:
    types = set()
    for m in re.finditer(r"\b(III|II|I|[1-3])\b", span, re.IGNORECASE):
        g = m.group(1).upper()
        if g in ("I", "1"):    types.add("1")
        elif g in ("II", "2"):  types.add("2")
        elif g in ("III", "3"): types.add("3")
    if not types:
        return None
    return ",".join(sorted(types))


def _parse_adc(span: str) -> Optional[float]:
    m = re.search(r"(\d+(?:[.,]\d+)?)", span)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    # Heuristic: raw values >10 are in ×10⁻⁶ (μm²/s) → convert to ×10⁻³
    if val > 10:
        val /= 1000.0
    return val


def _parse_laterality(span: str) -> Optional[str]:
    s = _strip_accents(span)
    if "αμφοτ" in s or "bilat" in s or "both" in s:
        return "BILATERAL"
    if "αριστερ" in s or "δεξι" in s or "left" in s or "right" in s:
        return "UNILATERAL"
    return None


def _parse_family_history(span: str) -> Optional[str]:
    s = _strip_accents(span)
    if "αρνητ" in s or "χωρις" in s or "δεν " in s or " no " in f" {s} " or "negative" in s:
        return "No"
    if "θετικ" in s or "positive" in s or " yes" in f" {s} ":
        return "Yes"
    return None


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

# Fields where presence of a detected span → "Yes"
_PRESENCE_FIELDS = {"MASS", "NME", "NonEnhancingFindings"}


# ─── Extractor ──────────────────────────────────────────────────────────────

class GLiNERExtractor:
    """Zero-shot clinical extractor using GLiNER."""

    DEFAULT_MODEL = "urchade/gliner_multi-v2.1"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        threshold: float = 0.3,
    ):
        print(f"[GLiNERExtractor] Loading {model_name}…")
        self.model = GLiNER.from_pretrained(model_name)
        self.threshold = threshold
        print("[GLiNERExtractor] Loaded.")

    # ------------------------------------------------------------------
    # Core inference (cached on Patient to avoid re-running per group)
    # ------------------------------------------------------------------

    def _build_cache(self, text: str) -> dict[str, list[dict]]:
        entities = self.model.predict_entities(
            text, _LABELS, threshold=self.threshold, flat_ner=True,
        )
        by_field: dict[str, list[dict]] = {}
        for ent in entities:
            field = _LABEL_TO_FIELD.get(ent["label"])
            if field is None:
                continue
            by_field.setdefault(field, []).append(ent)
        return by_field

    def extract_value(self, field: str, cache: dict[str, list[dict]]):
        """Extract and parse value for one field from the GLiNER cache."""
        spans = cache.get(field, [])

        if field in _PRESENCE_FIELDS:
            return "Yes" if spans else "No"

        parser = _PARSERS.get(field)
        if parser is None:
            return None

        # Try highest-score span first; fall through if parse fails
        for ent in sorted(spans, key=lambda e: -e["score"]):
            val = parser(ent["text"])
            if val is not None:
                return val
        return None

    # ------------------------------------------------------------------
    # Gating helpers (mirror RegexExtractor)
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
        # Cache GLiNER inference across multiple group calls on same Patient
        if not hasattr(Patient, "_gliner_cache"):
            Patient._gliner_cache = self._build_cache(Patient.report_text)
        cache = Patient._gliner_cache

        for key in keys:
            if self._skip_mass_field(key, Patient):
                setattr(Patient, key, None)
                continue
            if self._skip_nme_field(key, Patient):
                setattr(Patient, key, None)
                continue
            setattr(Patient, key, self.extract_value(key, cache))

        # Update gates
        if "MASS" in keys:
            val = getattr(Patient, "MASS", None) or "No"
            setattr(Patient, "MASS", val)
            Patient.mass_gate = (val == "Yes")
        if "NME" in keys:
            val = getattr(Patient, "NME", None) or "No"
            setattr(Patient, "NME", val)
            Patient.nme_gate = (val == "Yes")

        # Re-apply gates post-hoc
        for key in keys:
            if self._skip_mass_field(key, Patient):
                setattr(Patient, key, None)
            if self._skip_nme_field(key, Patient):
                setattr(Patient, key, None)

        Patient.post_process()
        return Patient
