"""
RegexExtractor.py
-----------------
Pure-regex extraction backend that implements the same interface as
ReportExtractor / OpenAIReportExtractor.

Usage:
    from RegexExtractor import RegexExtractor
    re_ext = RegexExtractor()
    re_ext.extract_structured_data(patient, keys=["BIRADS"], use_regex=True)

Or set `use_regex=True` on the existing extractor wrappers – see
`extract_structured_data` below.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

import lib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FLAGS = re.IGNORECASE | re.UNICODE


def _norm(text: str) -> str:
    """Normalize unicode (NFC) and collapse whitespace."""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def _roman_to_int(roman: str) -> Optional[int]:
    """Convert a Roman numeral string (I–VI) to int, else None."""
    mapping = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
    return mapping.get(roman.upper().strip())


# ---------------------------------------------------------------------------
# Per-field regex extractors
# Each function receives the full report text (str) and returns the extracted
# value or None.
# ---------------------------------------------------------------------------

# ── BIRADS ──────────────────────────────────────────────────────────────────

_BIRADS_RE = re.compile(
    r"""
    BI[-\s]?RADS                    # "BI-RADS" / "BIRADS" / "BI RADS"
    \s*[:\-]?\s*                    # optional separator
    (?:
        (VI|V|IV[abc]?|IV|III|II|I) # Roman VI..I  (longest first to avoid I matching IV)
        |
        ([0-6])                     # Arabic 0-6
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_ROMAN_MAP = {"I": 1, "II": 2, "III": 3, "IV": 4, "IVA": 4, "IVB": 4, "IVC": 4, "V": 5, "VI": 6}


def extract_BIRADS(text: str) -> Optional[int]:
    for m in _BIRADS_RE.finditer(text):
        roman, arabic = m.group(1), m.group(2)
        if roman:
            base = re.sub(r"[abc]$", "", roman, flags=re.IGNORECASE).upper()
            val = _ROMAN_MAP.get(base)
            if val is not None:
                return val
        if arabic is not None:
            return int(arabic)
    return None


# ── FamilyHistory ────────────────────────────────────────────────────────────

# Positive signals
_FAM_POS_RE = re.compile(
    r"""
    (?:
        θετικ[όο]ν?\s+(?:οικογενειακ[όο]ν?\s+)?ιστορικ[όο]ν?  # θετικό ιστορικό / οικογενειακό ιστορικό
        | θετικ[όο]ν?\s+ιστορικ[όο]ν?
        | positive\s+(?:family\s+)?histor
    )
    """,
    FLAGS | re.VERBOSE,
)

# Negative signals
_FAM_NEG_RE = re.compile(
    r"""
    (?:
        (?:αρνητικ[όο]ν?|αναφερ[όο]μεν[οη]\s+αρνητικ[όο]ν?)\s+(?:οικογενειακ[όο]ν?\s+)?ιστορικ[όο]ν?
        | χωρ[ίι][ςσ]\s+(?:οικογενειακ[όο]ν?\s+)?ιστορικ[όο]ν?
        | δεν\s+αναφ[έε]ρεται\s+(?:οικογενειακ[όο]ν?\s+)?ιστορικ[όο]ν?
        | negative\s+(?:family\s+)?histor
        | no\s+(?:family\s+)?histor
    )
    """,
    FLAGS | re.VERBOSE,
)


def extract_FamilyHistory(text: str) -> Optional[str]:
    if _FAM_POS_RE.search(text):
        return "Yes"
    if _FAM_NEG_RE.search(text):
        return "No"
    return None


# ── ACR (Breast Density) ─────────────────────────────────────────────────────

_ACR_RE = re.compile(
    r"""
    ACR\s*[:\-]?\s*
    ([ABCD])                        # first grade
    (?:\s*[-–]\s*([ABCD]))?         # optional range  e.g. C-D
    """,
    FLAGS | re.VERBOSE,
)


def extract_ACR(text: str) -> Optional[str]:
    m = _ACR_RE.search(text)
    if m:
        g1, g2 = m.group(1).upper(), m.group(2)
        if g2:
            return f"{g1}-{g2.upper()}"
        return g1
    return None


# ── BPE ─────────────────────────────────────────────────────────────────────

_BPE_RE = re.compile(
    r"""
    (?:
        # English terms in parentheses or bare
        \b(minimal|mild|moderate|marked)\s+BPE\b
        | \bBPE\b.*?\b(minimal|mild|moderate|marked)\b
        # Greek terms
        | \b(μηδαμιν[ήη]|ήπι[αα]|μ[έε]τρι[αα]|[έε]ντον[ήη])\b
            .*?(?:ενί[σς]χυ[σς][ηη]|BPE)
        | (?:ενί[σς]χυ[σς][ηη]|BPE)
            .*?\b(μηδαμιν[ήη]|ήπι[αα]|μ[έε]τρι[αα]|[έε]ντον[ήη])\b
    )
    """,
    FLAGS | re.VERBOSE,
)

_BPE_GREEK_MAP = {
    "μηδαμιν": "Minimal",
    "ηπι": "Mild",      # ήπια -> stripped accents start with "ηπι"
    "μετρι": "Moderate",
    "μέτρι": "Moderate",
    "εντον": "Marked",
    "έντον": "Marked",
}

_BPE_EN_MAP = {
    "minimal": "Minimal",
    "mild": "Mild",
    "moderate": "Moderate",
    "marked": "Marked",
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def extract_BPE(text: str) -> Optional[str]:
    # First try exact English term adjacent to BPE
    en_adj = re.search(
        r"\b(minimal|mild|moderate|marked)\s+BPE\b|\bBPE\b\s*[:\-]?\s*(minimal|mild|moderate|marked)\b",
        text, FLAGS
    )
    if en_adj:
        raw = (en_adj.group(1) or en_adj.group(2)).lower()
        return _BPE_EN_MAP[raw]

    # Try Greek term near BPE keyword (within 120 chars)
    greek_term = re.search(
        r"\b(μηδαμιν[ήη]|ήπι[αα]|μ[έε]τρι[αα]|[έε]ντον[ήη])\b",
        text, FLAGS
    )
    if greek_term:
        stripped = _strip_accents(greek_term.group(1).lower())
        for prefix, val in _BPE_GREEK_MAP.items():
            if stripped.startswith(_strip_accents(prefix)):
                return val
    return None


# ── MASS ─────────────────────────────────────────────────────────────────────

# Positive mass keywords
_MASS_POS_RE = re.compile(
    r"""
    \b(?:
        μ[άα]ζα | σχηματισμ[όο]ς | χωροκατακτητικ[ήη]\s+εξεργασ[ίι]α
        | συμπαγ[ήη][ςσ]\s+(?:ενισχυ[όο]μεν[ήη]\s+)?αλλο[ίι]ωσ[ηη]
        | ενισχυ[όο]μεν[ήη]\s+βλ[άα]βη
        | αλλο[ίι]ωσ[ηη]\s+διαμ[έε]τρου  # αλλοίωση with size
        | ωοειδ[ήη][ςσ]\s+αλλο[ίι]ωσ[ηη]  # ωοειδής αλλοίωση
        | οζ[ώω]δη[ςσ]?\s+αλλο[ίι]ωσ[ηη]  # οζώδης αλλοίωση
        | αλλο[ίι]ωσ[ηη].*?ινοαδ[έε]νωμα  # αλλοίωση ... ινοαδένωμα
        | solid\s+(?:enhancing\s+)?(?:mass|lesion)
        | enhancing\s+(?:mass|lesion)
        | space[-\s]occupying\s+lesion
        | \bmass\b
    )\b
    """,
    FLAGS | re.VERBOSE,
)

# Negative mass keywords
_MASS_NEG_RE = re.compile(
    r"""
    \b(?:
        δεν\s+(?:παρατηρε[ίι]ται|αναδεικν[ύυ]εται)\s+
            (?:μ[άα]ζα|συμπαγ[ήη][ςσ]\s+αλλο[ίι]ωσ[ηη]|σχηματισμ[όο][σς]|βλ[άα]βη)
        | no\s+(?:solid\s+)?mass\s+(?:is\s+)?(?:seen|identified|detected|noted)
    )\b
    """,
    FLAGS | re.VERBOSE,
)

# Exclusions: NME-only, cysts, BPE - things that must NOT trigger MASS
_MASS_EXCL_RE = re.compile(
    r"""
    \b(?:
        μη\s+μαζ[όο]μορφ[ήη]\s+ε[νν]ί[σς]χυ[σς][ηη]   # NME
        | κ[ύυ]στ[ηη]                                    # cyst
        | BPE
        | αποτιτ[αα]ν[ώω]σ[εε]ι[σς]                     # calcifications
        | ectasia
        | scar | clip | artifact
    )\b
    """,
    FLAGS | re.VERBOSE,
)


def extract_MASS(text: str) -> Optional[str]:
    if _MASS_NEG_RE.search(text):
        return "No"
    if _MASS_POS_RE.search(text):
        return "Yes"
    return "No"  # default No per post-process logic


# ── massDiameter / nmeDiameter ───────────────────────────────────────────────

_DIAM_RE = re.compile(
    r"""
    (?:
        (?:μ[άα]ζα|αλλο[ίι]ωσ[ηη]|σχηματισμ[όο][σς]|βλ[άα]βη|NME|
           μη\s+μαζ[όο]μορφ[ήη])
        .*?
    )?
    διαμ[έε]τρου?           # keyword: "διαμέτρου" / "διαμέτρου"
    \s*
    (\d+(?:[.,]\d+)?)        # number (group 1)
    \s*
    (mm|cm|χιλ(?:ιοστ[άα])?\.?|εκ(?:ατοστ[άα])?\.?)  # unit (group 2)
    """,
    FLAGS | re.VERBOSE,
)

# Also catch bare "<number> mm" after a lesion word
_DIAM_BARE_RE = re.compile(
    r"""
    \b(\d+(?:[.,]\d+)?)\s*(mm|cm|χιλ(?:ιοστ[άα])?\.?|εκ(?:ατοστ[άα])?\.?)\b
    """,
    FLAGS | re.VERBOSE,
)


def _parse_diameter(text: str, lesion_keyword_re: re.Pattern) -> Optional[float]:
    """
    Find the first diameter measurement near a lesion keyword.
    Returns value in mm (float) or None.
    """
    _UNIT_MM = re.compile(r"^(mm|χιλ)", FLAGS)
    _UNIT_CM = re.compile(r"^(cm|εκ)", FLAGS)

    # Search near lesion keyword
    lk = lesion_keyword_re.search(text)
    if lk:
        window = text[lk.start(): lk.start() + 300]
        m = _DIAM_RE.search(window) or _DIAM_BARE_RE.search(window)
        if m:
            num_str = m.group(1).replace(",", ".")
            unit = m.group(2)
            try:
                num = float(num_str)
            except ValueError:
                return None
            if _UNIT_CM.match(unit):
                num *= 10.0
            return num

    # Fallback: global search
    m = _DIAM_RE.search(text)
    if m:
        num_str = m.group(1).replace(",", ".")
        unit = m.group(2)
        try:
            num = float(num_str)
        except ValueError:
            return None
        if _UNIT_CM.match(unit):
            num *= 10.0
        return num
    return None


_MASS_KW = re.compile(
    r"\b(?:μ[άα]ζα|σχηματισμ[όο][σς]|συμπαγ[ήη][ςσ]\s+αλλο[ίι]ωσ[ηη]|solid\s+(?:mass|lesion)|mass)\b",
    FLAGS,
)
_NME_KW = re.compile(
    r"\b(?:μη\s+μαζ[όο]μορφ[ήη]|NME|non[-\s]mass(?:\s+enhancement)?)\b",
    FLAGS,
)


def extract_massDiameter(text: str) -> Optional[str]:
    val = _parse_diameter(text, _MASS_KW)
    if val is None:
        return None
    # Return as "<number> mm" string; post_process converts to float
    return f"{val} mm"


def extract_nmeDiameter(text: str) -> Optional[str]:
    val = _parse_diameter(text, _NME_KW)
    if val is None:
        return None
    return f"{val} mm"


# ── massMargins / nmeMargins ─────────────────────────────────────────────────

_MARGINS_CLEAR_RE = re.compile(
    r"\b(?:σαφ[ήη][ςσ]?\s+(?:[όο]ρια|περιγρ[αά]μματα)|well[-\s]?defined|circumscribed)\b",
    FLAGS,
)
_MARGINS_ILL_RE = re.compile(
    r"\b(?:ασαφ[ήη][ςσ]?\s+(?:[όο]ρια|περιγρ[αά]μματα)|ill[-\s]?defined|spiculated|irregular)\b",
    FLAGS,
)


def _extract_margins(text: str) -> Optional[str]:
    if _MARGINS_CLEAR_RE.search(text):
        return "σαφή"   # post_process maps -> 'C'
    if _MARGINS_ILL_RE.search(text):
        return "ασαφή"  # post_process maps -> 'NC'
    return None


def extract_massMargins(text: str) -> Optional[str]:
    return _extract_margins(text)


def extract_nmeMargins(text: str) -> Optional[str]:
    return _extract_margins(text)


# ── massInternalEnhancement / nmeInternalEnhancement ────────────────────────

_ENH_HO_RE = re.compile(
    r"\b(?:ομοιογεν[ήη][ςσ]?\s+(?:ε[νν]ί[σς]χυ[σς][ηη]|σκιαγρ[αά]φ[ήη][σς][ηη])|homogeneous(?:\s+enhancement)?)\b",
    FLAGS,
)
_ENH_HE_RE = re.compile(
    r"\b(?:ανομοιογεν[ήη][ςσ]?\s+(?:ε[νν]ί[σς]χυ[σς][ηη]|σκιαγρ[αά]φ[ήη][σς][ηη])|heterogeneous(?:\s+enhancement)?)\b",
    FLAGS,
)


def _extract_internal_enhancement(text: str) -> Optional[str]:
    if _ENH_HO_RE.search(text):
        return "ομοιογενής"   # post_process -> 'HO'
    if _ENH_HE_RE.search(text):
        return "ανομοιογενής" # post_process -> 'HE'
    return None


def extract_massInternalEnhancement(text: str) -> Optional[str]:
    return _extract_internal_enhancement(text)


def extract_nmeInternalEnhancement(text: str) -> Optional[str]:
    return _extract_internal_enhancement(text)


# ── NME ─────────────────────────────────────────────────────────────────────

_NME_POS_RE = re.compile(
    r"""
    \b(?:
        μη\s+μαζ[όο]μορφ[ήη](?:\s+\w+){0,4}?\s*ε[νν]ί[σς]χυ[σς][ηη]
        | περιοχ[ήη]\s+μη\s+μαζομορφ[ήη][σς]?\s*σκιαγρ[αά]φ[ήη][σς][ηη][σς]?\s+ε[νν]ί[σς]χυ[σς][ηη]
        | non[-\s]mass(?:\s+enhancement)?
        | NME
    )\b
    """,
    FLAGS | re.VERBOSE,
)

_NME_NEG_RE = re.compile(
    r"""
    \b(?:
        δεν\s+(?:παρατηρε[ίι]ται|αναδεικν[ύυ]εται)\s+(?:μη\s+μαζ[όο]μορφ[ήη]|NME)
        | no\s+(?:non[-\s]mass|NME)
    )\b
    """,
    FLAGS | re.VERBOSE,
)


def extract_NME(text: str) -> Optional[str]:
    if _NME_NEG_RE.search(text):
        return "No"
    if _NME_POS_RE.search(text):
        return "Yes"
    return "No"


# ── NonEnhancingFindings ─────────────────────────────────────────────────────

_NEF_POS_RE = re.compile(
    r"""
    \b(?:
        κ[ύυ]στ[ηη] | κ[ύυ]στ[εε]ι[σς] | κυστικ[ήη][ςσ]?\s+αλλο[ίι]ωσ[ηη]
        | cyst | cysts
        | αποτιτ[αά]ν[ώω]σ[εε]ι[σς] | calcification
        | ectasia | πορεκτ[αά]σι[αα]
        | scar | ουλ[ήη] | clip | artifact
    )\b
    """,
    FLAGS | re.VERBOSE,
)

_NEF_NEG_RE = re.compile(
    r"""
    \b(?:
        δεν\s+(?:παρατηρε[ίι]ται|αναδεικν[ύυ]εται)\s+
            (?:κ[ύυ]στ|αποτιτ|ectasia|scar)
        | no\s+(?:cyst|calcification|non[-\s]enhancing)
    )\b
    """,
    FLAGS | re.VERBOSE,
)


def extract_NonEnhancingFindings(text: str) -> Optional[str]:
    if _NEF_NEG_RE.search(text):
        return "No"
    if _NEF_POS_RE.search(text):
        return "Yes"
    return None


# ── CurveMorphology ──────────────────────────────────────────────────────────

_CURVE_RE = re.compile(
    r"""
    (?:
        αιμοδυναμικ[ήη]\s+καμπ[ύυ]λ[ηη]\s+τ[ύυ]που\s*  # Greek: "αιμοδυναμική καμπύλη τύπου"
        | τ[ύυ]που\s+                                     # short form: "τύπου"
        | [Tt]ype\s*                                       # English: "Type"
        | kinetic\s+curve\s+type\s*
    )
    (III|II|I|3|2|1)                                      # type value (longest first)
    """,
    FLAGS | re.VERBOSE,
)

_CURVE_MAP = {
    "I": "1", "II": "2", "III": "3",
    "1": "1", "2": "2", "3": "3",
}


def extract_CurveMorphology(text: str) -> Optional[str]:
    found = set()
    for m in _CURVE_RE.finditer(text):
        val = _CURVE_MAP.get(m.group(1).upper())
        if val:
            found.add(val)
    if not found:
        return None
    return ",".join(sorted(found))


# ── ADC ──────────────────────────────────────────────────────────────────────

_ADC_NUM_RE = re.compile(
    r"""
    ADC\s*[=:\-]?\s*
    (\d+(?:[.,]\d+)?)           # numeric value
    \s*
    (?:
        [x×]\s*10\s*[\^⁻-]?\s*[-⁻]?\s*3   # ×10⁻³ or x10^-3
        | ×10⁻³
    )?
    \s*(?:mm\s*[²2]\s*/\s*s)?  # optional unit
    """,
    FLAGS | re.VERBOSE,
)

# Unit-scale: some reports use 10⁻⁶ (μm²/s) → need to convert (/1000)
_ADC_MICRO_RE = re.compile(
    r"""
    ADC\s*[=:\-]?\s*
    (\d+(?:[.,]\d+)?)
    \s*[x×]\s*10\s*[-⁻]?\s*6   # ×10⁻⁶ scale
    """,
    FLAGS | re.VERBOSE,
)


def extract_ADC(text: str) -> Optional[float]:
    # Check ×10⁻⁶ scale first (μm²/s) → convert to ×10⁻³
    m6 = _ADC_MICRO_RE.search(text)
    if m6:
        try:
            val = float(m6.group(1).replace(",", ".")) / 1000.0
            return val
        except ValueError:
            pass

    m = _ADC_NUM_RE.search(text)
    if m:
        try:
            val = float(m.group(1).replace(",", "."))
            # Heuristic: raw values like "900" are in 10⁻⁶; values < 10 are already ×10⁻³
            if val > 10:
                val /= 1000.0
            return val
        except ValueError:
            pass

    # Qualitative fallback
    if re.search(r"χωρ[ίι][σς]\s+περιορισμ[όο]\s+δι[άα]χυσ[ηη]|ελε[ύυ]θερη\s+δι[άα]χυσ[ηη]", text, FLAGS):
        return None  # NR – will be set in post_process
    if re.search(r"(?:με\s+)?περιορισμ[όο]\s+δι[άα]χυσ[ηη]|περιορισμ[έε]νη\s+δι[άα]χυσ[ηη]", text, FLAGS):
        return None  # R – qualitative, returned as None; caller can extend

    return None


# ── LATERALITY ───────────────────────────────────────────────────────────────

_LAT_LEFT_RE = re.compile(
    r"\b(?:αριστερ[όο][σς]?\s+μαστ[όο][σς]?|αριστερο[ύυ]\s+μαστ[ούυ]|left\s+breast|αλλοιώσεις\s+αριστερά|αριστερά)\b",
    FLAGS,
)
_LAT_RIGHT_RE = re.compile(
    r"\b(?:δεξι[όο][σς]?\s+μαστ[όο][σς]?|δεξιο[ύυ]\s+μαστ[ούυ]|right\s+breast|αλλοιώσεις\s+δεξιά|δεξιά)\b",
    FLAGS,
)
_LAT_BILATERAL_RE = re.compile(
    r"\b(?:αμφοτερ[όο]πλευρα|αμφοτ[έε]ρου[σς]\s+τους\s+μαστ[ούυ][σς]?|αμφ[όο]τερ[αοε]|bilateral|both\s+breast)\b",
    FLAGS,
)


def extract_LATERALITY(text: str) -> Optional[str]:
    # Explicit bilateral phrase wins immediately
    if _LAT_BILATERAL_RE.search(text):
        return "BILATERAL"
    left = bool(_LAT_LEFT_RE.search(text))
    right = bool(_LAT_RIGHT_RE.search(text))
    if left and right:
        return "BILATERAL"
    if left or right:
        return "UNILATERAL"
    return None


# ---------------------------------------------------------------------------
# Dispatcher map
# ---------------------------------------------------------------------------

_EXTRACTORS = {
    "BIRADS":                  extract_BIRADS,
    "FamilyHistory":           extract_FamilyHistory,
    "ACR":                     extract_ACR,
    "BPE":                     extract_BPE,
    "MASS":                    extract_MASS,
    "massDiameter":            extract_massDiameter,
    "massMargins":             extract_massMargins,
    "massInternalEnhancement": extract_massInternalEnhancement,
    "NME":                     extract_NME,
    "nmeDiameter":             extract_nmeDiameter,
    "nmeMargins":              extract_nmeMargins,
    "nmeInternalEnhancement":  extract_nmeInternalEnhancement,
    "NonEnhancingFindings":    extract_NonEnhancingFindings,
    "CurveMorphology":         extract_CurveMorphology,
    "ADC":                     extract_ADC,
    "LATERALITY":              extract_LATERALITY,
}


# ---------------------------------------------------------------------------
# RegexExtractor  –  drop-in replacement for ReportExtractor
# ---------------------------------------------------------------------------

class RegexExtractor:
    """
    Stateless regex-based extractor.  Implements the same
    `extract_structured_data(Patient, keys, ...)` interface used by
    ReportExtractor so it can be swapped in without any other code changes.

    Pass `use_regex=True` to `extract_structured_data`; omitting the flag or
    passing `False` raises NotImplementedError (you should use the LLM
    extractor instead).
    """

    # No __init__ arguments needed – no model to load.
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Gate helpers (mirror ReportExtractor logic)
    # ------------------------------------------------------------------

    @staticmethod
    def _skip_mass_field(key: str, Patient) -> bool:
        return key in ("massDiameter", "massMargins", "massInternalEnhancement") and not Patient.mass_gate

    @staticmethod
    def _skip_nme_field(key: str, Patient) -> bool:
        return key in ("nmeDiameter", "nmeMargins", "nmeInternalEnhancement") and not Patient.nme_gate

    # ------------------------------------------------------------------
    # Main extraction method
    # ------------------------------------------------------------------

    def extract_structured_data(
        self,
        Patient,
        keys: list[str],
        include_fewshots: bool = False,  # kept for API parity; unused
        use_regex: bool = True,
    ):
        """
        Extract fields listed in `keys` from `Patient.report_text` using regex.

        Args:
            Patient:          The Patient instance to populate.
            keys:             List of field names to extract (same as LLM extractor).
            include_fewshots: Ignored (kept for API compatibility).
            use_regex:        Must be True; raises NotImplementedError otherwise.

        Returns:
            The updated Patient instance (same reference).
        """
        if not use_regex:
            raise NotImplementedError(
                "use_regex=False is not supported by RegexExtractor. "
                "Use ReportExtractor or OpenAIReportExtractor instead."
            )

        text = _norm(Patient.report_text)
        obj: dict = {}

        for key in keys:
            # ----- gate checks -----
            if self._skip_mass_field(key, Patient):
                obj[key] = None
                continue
            if self._skip_nme_field(key, Patient):
                obj[key] = None
                continue

            # ----- extract -----
            extractor = _EXTRACTORS.get(key)
            if extractor is None:
                print(f"[RegexExtractor] WARNING: no regex extractor for key '{key}'. Returning None.")
                obj[key] = None
            else:
                obj[key] = extractor(text)

        # ----- apply gate updates -----
        if "MASS" in keys:
            if obj.get("MASS") is None:
                obj["MASS"] = "No"
            Patient.mass_gate = obj["MASS"] == "Yes"

        if "NME" in keys:
            if obj.get("NME") is None:
                obj["NME"] = "No"
            Patient.nme_gate = obj["NME"] == "Yes"

        # Re-apply gate overrides after the gate fields are decided
        for key in keys:
            if self._skip_mass_field(key, Patient):
                obj[key] = None
            if self._skip_nme_field(key, Patient):
                obj[key] = None

        # ----- set attributes -----
        for key in keys:
            setattr(Patient, key, obj.get(key, None))

        Patient.post_process()
        return Patient
