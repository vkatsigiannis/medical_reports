# pip install "transformers>=4.44" accelerate "outlines[transformers]>=1.2.0" "pydantic>=2"

#######################################################################################################################################################################################################################################################
# birads, exam_date, bpe, adc, perfusion_curve, acr, maza, nme_presence, mass_margins, nme_margins, radial_spiculations, mass_enhancement_pattern, nme_enhancement_pattern, non_enhancing_septa, nme_linear, nme_segmental, nme_regional, nme_bilateral
#######################################################################################################################################################################################################################################################

### mass gating (if exists mass, then enhancement_pattern search for margins, radial_spiculations, enhancement_pattern, non_enhancing_septa)
### nme gating (if exists nme, then enhancement_pattern search for margins, radial_spiculations, enhancement_pattern, non_enhancing_septa)

import os, re, json, outlines, torch, unicodedata
from pathlib import Path
import csv
from datetime import datetime
from typing import Optional, Literal
from pydantic import Field, create_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils.logging import set_verbosity_error
from save_utils import save_to_csv, save_to_json, save_to_xml



# ---- GPU + quiet optional compilers (still uses CUDA) ----
os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"
os.environ["PYTORCH_TRITON_DISABLE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"


os.environ["CUDA_VISIBLE_DEVICES"] = "5"

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / ".hf_cache"
CACHE_DIR.mkdir(exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)

os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

set_verbosity_error()
assert torch.cuda.is_available(), "CUDA GPU not found."

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
# MODEL_ID = "ilsp/Llama-Krikri-8B-Instruct"


# ======================= MODEL ========================
hf_model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    dtype=torch.float16,
    cache_dir=str(CACHE_DIR),
    trust_remote_code=True,
    device_map="auto",
    temperature=0.0,
)
hf_tok = AutoTokenizer.from_pretrained(MODEL_ID,
                                       use_fast=False,
                                       cache_dir=str(CACHE_DIR),
                                    trust_remote_code=True)
model = outlines.from_transformers(hf_model, hf_tok)

MASS_POS_VALUES = ("συμπαγής αλλοίωση", "χωροκατακτητική εξεργασία")



def _llm_gate_value(report_text: str, key: Literal["maza", "nme_presence"]) -> Optional[str]:
    GateModel = make_model([key])
    gate_prompt = apply_chat_template(build_prompt(report_text, [key]))
    gate_out = model(gate_prompt, GateModel, max_new_tokens=160, do_sample=False)
    gate_obj = GateModel.model_validate_json(gate_out).model_dump()
    return gate_obj.get(key)



# ======================= PROMPT =======================
_PROMPT_FIELD_RULES = {
    "breast": (
        '- Exam laterality summary ("breast"): Return exactly one of Left, Right, or Both.\n'
        "Rules:\n"
        "  • Prefer EXPLICIT, SIDE-SPECIFIC localization of findings/actions (e.g., αλλοίωση/μάζα/NME/clip/βιοψία/"
        "    περιορισμός διάχυσης/ενίσχυση with αριστερό/δεξιό μαστό, or LEFT/RIGHT breast with clockface).\n"
        "  • Ignore generic/bilateral background phrases (π.χ. «αμφοτερόπλευρα», ACR/BPE) unless the report explicitly "
        "    states the EXAM covered both breasts (e.g., «εξέταση/έλεγχος αμφοτέρων των μαστών», "
        "    «bilateral breast MRI performed»). Generic bilateral background alone does not make it Both.\n"
        "  • If there is explicit left-only evidence ⇒ Left; right-only ⇒ Right; explicit evidence for both sides or "
        "    explicit statement that both breasts were examined ⇒ Both.\n"
        "  • If sections disagree, prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion. Default is null if no explicit evidence.\n"
    ),
    "left_breast": (
        "- Laterality (LEFT): Return true only if there is at least one EXPLICIT, SIDE-SPECIFIC "
        "mention that localizes a finding/action to the left breast (e.g., αλλοίωση/κύστη/μάζα/"
        "μη μαζόμορφη ενίσχυση/clip/βιοψία/περιορισμός διάχυσης/ενίσχυση/ώρα ρολογιού) with clear "
        "reference to the αριστερό μαστό. Include generic/bilateral/background phrases such as "
        "«αμφοτερόπλευρα/αμφω/σε αμφότερους τους μαστούς», ACR/BPE density, symmetry or general statements. "
        "If sections disagree, prefer ΣΥΜΠΕΡΑΣΜΑ. "
        "Default is True."
    ),
    "right_breast": (
        "- Laterality (RIGHT): Return true only if there is at least one EXPLICIT, SIDE-SPECIFIC "
        "mention that localizes a finding/action to the right breast (as above for δεξιό μαστό). "
        "Include generic/bilateral/background phrases (αμφοτερόπλευρα/αμφω/both breasts), ACR/BPE density, "
        "If sections disagree, prefer ΣΥΜΠΕΡΑΣΜΑ. "
        "Default is True."
    ),

    "enhancement_presence": (
        '- Ύπαρξη Ενίσχυσης (περιοχές παθολογικής σκιαγραφικής ενίσχυσης): '
        'Return «υπάρχει» if the report explicitly mentions pathological enhancement areas, '
        'including phrases like «περιοχή/ες μη μαζομορφής σκιαγραφικής ενίσχυσης» or '
        '«περιοχές παθολογικής σκιαγραφικής ενίσχυσης». '
        'Return «δεν υπάρχει» only with explicit negation (π.χ. «Δεν παρατηρούνται …»). '
        'IGNORE background/BPE statements such as «ενίσχυση παρεγχύματος / BPE» unless an explicit area/region of enhancement is stated. '
        'Prefer ΣΥΜΠΕΡΑΣΜΑ if conflicting.'
    ),



    "birads": "- BI-RADS category as an integer 0..6. Accept I/II/III/IV/V/VI and map to 1..6.",
    "exam_date": "- Exam date. Prefer YYYY-MM-DD. Normalize 31/03/2024 → 2024-03-31 when unambiguous.",
    "bpe": "- Background Parenchymal Enhancement (BPE). Allowed: Minimal, Mild, Moderate, Marked. "
           "Greek: ΜΗΔΑΜΙΝΗ→Minimal, ΗΠΙΑ→Mild, ΜΕΤΡΙΑ→Moderate, ΕΝΤΟΝΗ→Marked.",
    "adc": "- ADC (Δείκτης διάχυσης νερού). Allowed: «χωρίς περιορισμό» ή «με περιορισμό». "
           "Rules: χωρίς περιορισμό αν αναφέρεται «χωρίς περιορισμένη διάχυση» ή «ελεύθερη διάχυση». "
           "με περιορισμό αν αναφέρεται «με περιορισμένη διάχυση» ή «περιορισμένη διάχυση».",
    "perfusion_curve": "- αιμοδυναμική καμπύλη. Allowed: Τύπος I / Τύπος II / Τύπος III.",
    "acr": "- Πυκνότητα μαστού ACR. Allowed: A / B / C / D ή συνδυασμοί. "
           "Αν υπάρχουν πολλαπλά, επέστρεψέ τα ενωμένα με '-' διατηρώντας τη σειρά (π.χ. C-D).",
    "maza": "if text mentions «συμπαγ(…) αλλοίωσ(…)», «χωροκατακτητικ(…) εξεργασ(…)», «μάζα/μαζομορφ(…)» "
        "or «ενισχυόμενη βλάβη», or a focal «αλλοίωση … διαμέτρου/μεγέθους …» → set accordingly. ",
    # "maza": "- Μάζα (αναφέρεται ως «μάζα» ή «ενισχυόμενη βλάβη»). "
    #         "Allowed: συμπαγής αλλοίωση / χωροκατακτητική εξεργασία / δεν υπάρχει. "
    #         "Δήλωση παρουσίας αλλοίωσης και είδους. Αν δεν παρατηρείται, επέστρεψε «δεν υπάρχει».",
    "nme_presence": "- Μη μαζόμορφη ενίσχυση. Allowed: υπάρχει / δεν υπάρχει. "
                    "Δήλωση παρουσίας ή απουσίας μη μαζόμορφης ενίσχυσης.",
    # "margins": "- Σαφή ή ασαφή όρια μάζας ή μη μαζόμορφης ενίσχυσης.. Allowed: σαφή / ασαφή."
            # "set «σαφή» or «ασαφή» only if the report states σαφή/καθαρά όρια or ασαφή/ακαθόριστα/θολά όρια."
            # "  Return null unless the text explicitly states σαφή/καθαρά όρια or ασαφή/ακαθόριστα/θολά όρια,\n"
            # "  or English 'well-defined/ill-defined margins'. Do NOT infer from shape terms like "
            # "  λοβωτή/λοβιακή, ομαλά, circumscribed, spiculated, παραμετρικά κριτήρια κ.λπ.",
    "mass_margins": "- Σαφή ή ασαφή όρια μάζας, δηλαδή «συμπαγ(…) αλλοίωσ(…)», «χωροκατακτητικ(…) εξεργασ(…)», «μάζα/μαζομορφ(…)» "
            "or «ενισχυόμενη βλάβη», or a focal «αλλοίωση … διαμέτρου/μεγέθους …» .. Allowed: σαφή / ασαφή."
            "set «σαφή» or «ασαφή» only if the report states σαφή/καθαρά όρια or ασαφή/ακαθόριστα/θολά όρια."
            "  Return null unless the text explicitly states σαφή/καθαρά όρια or ασαφή/ακαθόριστα/θολά όρια,\n"
            "  or English 'well-defined/ill-defined margins'. Do NOT infer from shape terms like"
            "  λοβωτή/λοβιακή, ομαλά, circumscribed, spiculated, παραμετρικά κριτήρια κ.λπ. Only for masses.",
    "nme_margins": "- Σαφή ή ασαφή όρια για Μη μαζόμορφη ενίσχυση. Allowed: σαφή / ασαφή."
            "set «σαφή» or «ασαφή» only if the report states σαφή/καθαρά όρια or ασαφή/ακαθόριστα/θολά όρια."
            "  Return null unless the text explicitly states σαφή/καθαρά όρια or ασαφή/ακαθόριστα/θολά όρια,\n"
            "  or English 'well-defined/ill-defined margins'. Do NOT infer from shape terms like"
            "  λοβωτή/λοβιακή, ομαλά, circumscribed, spiculated, παραμετρικά κριτήρια κ.λπ. Only when μη μαζόμορφη ενίσχυση υπάρχει.",
    "radial_spiculations": "- Ακτινωτές προσεκβολές αλλοίωσης (μόνο για μάζες). Allowed: υπάρχει / δεν υπάρχει. "
            "Return null unless the report explicitly mentions ακτινωτές προσεκβολές / spiculations "
            "and there is mass evidence.",
    # "enhancement_pattern": "- Πρότυπο ενίσχυσης (αναφέρεται ως «ενίσχυση» ή «πρότυπο ενίσχυσης»). "
    #         "Allowed: ομοιογενής / ανομοιογενής / περιφερική. "
    #         "Επέστρεψε «περιφερική» μόνο όταν υπάρχει μάζα. "
    #         "Ομοιογενής/ανομοιογενής ισχύουν και για μη μαζόμορφη ενίσχυση."
    #          "Return null unless the text explicitly states",
    "mass_enhancement_pattern": "- Πρότυπο ενίσχυσης για μάζα, δηλαδή «συμπαγ(…) αλλοίωσ(…)», «χωροκατακτητικ(…) εξεργασ(…)», «μάζα/μαζομορφ(…)» "
            "or «ενισχυόμενη βλάβη», or a focal «αλλοίωση … διαμέτρου/μεγέθους …» (αναφέρεται ως «ενίσχυση» ή «πρότυπο ενίσχυσης» για μάζα). "
            "Allowed: ομοιογενής / ανομοιογενής / περιφερική. "
             "Return null unless the text explicitly states the pattern.",
    "nme_enhancement_pattern": "- Πρότυπο ενίσχυσης για Μη μαζόμορφη ενίσχυση (αναφέρεται ως «ενίσχυση» ή «πρότυπο ενίσχυσης» για Μη μαζόμορφη ενίσχυση). "
            "Allowed: ομοιογενής / ανομοιογενής. "
             "Return null unless the text explicitly states",
    "non_enhancing_septa": "- Μη ενισχυόμενα διαφραγμάτια (μόνο για μάζες). Allowed: υπάρχει / δεν υπάρχει.\n"
            "  Θέσε «υπάρχει» ΜΟΝΟ αν το κείμενο περιέχει ρητά τις φράσεις "
            "  «μη ενισχυόμενα διαφραγμάτια» ή αγγλικά «non-enhancing septation(s)».\n"
            "  Θέσε «δεν υπάρχει» αν αναφέρεται ρητά «χωρίς διαφραγμάτια», «δεν παρατηρούνται διαφραγμάτια» "
            "  ή «enhancing septations». Αν δεν υπάρχει ρητή αναφορά, επιστρέφεις null. "
            "  Αν δεν υπάρχει μάζα, επιστρέφεις null.",
    "nme_linear": "- Κατανομή NME: γραμμοειδής. Allowed: υπάρχει / δεν υπάρχει. "
            "Return null unless the text explicitly states the distribution type.",
    "nme_segmental": "- Κατανομή NME: τμηματική. Allowed: υπάρχει / δεν υπάρχει.\n"
        "  ΘΕΤΙΚΟ μόνο αν αναφέρεται ρητά «τμηματική κατανομή» (ή EN: «segmental distribution»).\n"
        "  ΑΡΝΗΤΙΚΟ όταν υπάρχει ρητή άρνηση για τμηματική ή λοβιακή κατανομή στο παρέγχυμα, "
        "  π.χ. «Δεν παρατηρούνται περιοχές παθολογικής σκιαγραφικής ενίσχυσης με λοβιακή ή τμηματική κατανομή».\n"
        "  Αν δεν υπάρχει ρητή αναφορά, επέστρεψε null. Προτίμησε το ΣΥΜΠΕΡΑΣΜΑ σε περίπτωση σύγκρουσης.",
    "nme_regional": "- Κατανομή NME: περιοχική. Allowed: υπάρχει / δεν υπάρχει. "
            "Return null unless the text explicitly states the distribution type.",
    "nme_bilateral": "- Κατανομή NME: αμφοτερόπλευρη. Allowed: υπάρχει / δεν υπάρχει. "
            "Return null unless the text explicitly states the distribution type.",

}

def _laterality_fewshots() -> str:
    # Short, high-signal examples; JSON only; bilingual cues.
    return (
        "Examples:\n"
        "Report:\n"
        "\"\"\"\n"
        "ACR C αμφοτερόπλευρα. Στην 10η ώρα του αριστερού μαστού αναδεικνύεται οζώδης αλλοίωση 7 χιλ.\n"
        "Δεν αναφέρονται εστιακά ευρήματα στον δεξιό μαστό.\n"
        "\"\"\"\n"
        "JSON: {\"left_breast\": true, \"right_breast\": false}\n\n"

        "Report:\n"
        "\"\"\"\n"
        "Bilateral background enhancement mild. Solid enhancing mass in the LEFT breast at 2 o'clock.\n"
        "\"\"\"\n"
        "JSON: {\"left_breast\": true, \"right_breast\": false}\n\n"

        "Report:\n"
        "\"\"\"\n"
        "Στον δεξιό μαστό: χωρίς παθολογικά ευρήματα. Αριστερά: κύστη 5 χιλ.\n"
        "\"\"\"\n"
        "JSON: {\"left_breast\": true, \"right_breast\": true}\n\n"

        "Report:\n"
        "\"\"\"\n"
        "Αμφοτερόπλευρα πυκνοί μαστοί (ACR D). Δεν υπάρχει καμία πλευρική εντόπιση ευρημάτων.\n"
        "\"\"\"\n"
        "JSON: {\"left_breast\": false, \"right_breast\": false}\n"
    )

def _breast_fewshots() -> str:
    return (
        "Examples:\n"
        "Report:\n"
        "\"\"\"\n"
        "ACR C αμφοτερόπλευρα. Στην 10η ώρα του αριστερού μαστού αναδεικνύεται οζώδης αλλοίωση 7 χιλ.\n"
        "Δεν αναφέρονται εστιακά ευρήματα στον δεξιό μαστό.\n"
        "\"\"\"\n"
        "JSON: {\"breast\": \"Left\"}\n\n"

        "Report:\n"
        "\"\"\"\n"
        "Bilateral breast MRI performed. Findings are symmetric without focal lesions.\n"
        "\"\"\"\n"
        "JSON: {\"breast\": \"Both\"}\n\n"

        "Report:\n"
        "\"\"\"\n"
        "Στον δεξιό μαστό: κύστη 6 χιλ. Αριστερά: χωρίς παθολογικά ευρήματα.\n"
        "\"\"\"\n"
        "JSON: {\"breast\": \"Both\"}\n\n"

        "Report:\n"
        "\"\"\"\n"
        "Στο αριστερό μαστό παρατηρείται NME τμηματικής κατανομής. Καμία ρητή αναφορά για τον δεξιό μαστό.\n"
        "\"\"\"\n"
        "JSON: {\"breast\": \"Left\"}\n"
    )


def build_prompt(report: str, prompt_keys: list[str]) -> str:
    lines = [
        "Task: Read the medical report (may be in Greek) and extract ONLY the following if present:"
        # "Task: Read the breast MRI report (Greek/English) and extract ONLY the requested fields.",
        # "Global rules:",
        # "- Output JSON only. No prose.",
        # "- Return null unless there is an explicit cue in the text. Do not infer.",
        # "- Follow each field’s rule exactly."
        ]
    for k in prompt_keys:
        lines.append(_PROMPT_FIELD_RULES[k])

    fields_stub = []
    if "breast" in prompt_keys: fields_stub.append('"breast": <Left|Right|Both or null>')

    if "left_breast" in prompt_keys:  fields_stub.append('"left_breast": <true|false>')
    if "right_breast" in prompt_keys: fields_stub.append('"right_breast": <true|false>')

    if "enhancement_presence" in prompt_keys: fields_stub.append('"enhancement_presence": <υπάρχει|δεν υπάρχει or null>')


    if "birads" in prompt_keys: fields_stub.append('"birads": <0..6 or null>')
    if "exam_date" in prompt_keys: fields_stub.append('"exam_date": <YYYY-MM-DD or raw or null>')
    if "bpe" in prompt_keys: fields_stub.append('"bpe": <Minimal|Mild|Moderate|Marked or null>')
    if "adc" in prompt_keys: fields_stub.append('"adc": <χωρίς περιορισμό|με περιορισμό or null>')
    if "perfusion_curve" in prompt_keys: fields_stub.append('"perfusion_curve": <Τύπος I|Τύπος II|Τύπος III or null>')
    if "acr" in prompt_keys: fields_stub.append('"acr": <A|B|C|D or combos like A-B or null>')
    if "maza" in prompt_keys: fields_stub.append('"maza": <συμπαγής αλλοίωση|χωροκατακτητική εξεργασία|δεν υπάρχει or null>')
    if "nme_presence" in prompt_keys: fields_stub.append('"nme_presence": <υπάρχει|δεν υπάρχει or null>')
    # if "margins" in prompt_keys: fields_stub.append('"margins": <σαφή|ασαφή or null>')
    if "mass_margins" in prompt_keys: fields_stub.append('"mass_margins": <σαφή|ασαφή or null>')
    if "nme_margins" in prompt_keys: fields_stub.append('"nme_margins": <σαφή|ασαφή or null>')
    if "radial_spiculations" in prompt_keys: fields_stub.append('"radial_spiculations": <υπάρχει|δεν υπάρχει or null>')
    # if "enhancement_pattern" in prompt_keys: fields_stub.append('"enhancement_pattern": <ομοιογενής|ανομοιογενής|περιφερική or null>')
    if "mass_enhancement_pattern" in prompt_keys: fields_stub.append('"mass_enhancement_pattern": <ομοιογενής|ανομοιογενής|περιφερική or null>')
    if "nme_enhancement_pattern" in prompt_keys: fields_stub.append('"nme_enhancement_pattern": <ομοιογενής|ανομοιογενής or null>')
    if "non_enhancing_septa" in prompt_keys: fields_stub.append('"non_enhancing_septa": <υπάρχει|δεν υπάρχει or null>')
    if "nme_linear" in prompt_keys: fields_stub.append('"nme_linear": <υπάρχει|δεν υπάρχει or null>')
    if "nme_segmental" in prompt_keys: fields_stub.append('"nme_segmental": <υπάρχει|δεν υπάρχει or null>')
    if "nme_regional" in prompt_keys: fields_stub.append('"nme_regional": <υπάρχει|δεν υπάρχει or null>')
    if "nme_bilateral" in prompt_keys: fields_stub.append('"nme_bilateral": <υπάρχει|δεν υπάρχει or null>')

    
    
    if ("left_breast" in prompt_keys) or ("right_breast" in prompt_keys):
        lines.append(_laterality_fewshots())
    if ("breast" in prompt_keys):
        lines.append(_breast_fewshots())
    

    lines += [
        "Output ONLY JSON:",
        "{ " + ", ".join(fields_stub) + " }",
        "If an item is missing, return null. No extra keys.\n",
        "Return null/false unless there is explicit textual evidence per field. Do not infer.\n"
        f'Report:\n"""\n{report}\n"""\nJSON:'
    ]
    return "\n".join(lines)

def apply_chat_template(text: str) -> str:
    if hasattr(hf_tok, "apply_chat_template"):
        return hf_tok.apply_chat_template(
            [{"role": "user", "content": text}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return text

# =================== REGEX HELPERS ====================
def _deaccent_lower(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

def _to_iso(d: datetime) -> str: return d.strftime("%Y-%m-%d")

# numerals
_ROMAN = {"I":1, "II":2, "III":3, "IV":4, "V":5, "VI":6, "0":0, "1":1, "2":2, "3":3, "4":4, "5":5, "6":6}

# =================== FIELD REGEXES ====================
# BI-RADS
_BIRADS_RE = re.compile(r"\bBI[-\s]?RADS\s*[:\-]?\s*(0|1|2|3|4|5|6|VI|IV|V|III|II|I)\b", flags=re.IGNORECASE)

def regex_birads(text: str) -> Optional[int]:
    m = _BIRADS_RE.search(text)
    if not m:
        return None
    token = m.group(1).upper()
    token = {"vi":"VI","iv":"IV","v":"V","iii":"III","ii":"II","i":"I"}.get(token.lower(), token)
    return _ROMAN.get(token)

# Exam date
_DATE_NUMERIC = r"(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2})"
_DATE_LABELED_RE = re.compile(
    rf"(?i)(exam|study|report|date|ημερομηνία|ημ/νία|ημερομηνία εξέτασης|ημ\.?\s*εξέτασης|ημερομηνία ελέγχου)"
    rf"[^\dA-Za-zΑ-Ωα-ω]{{0,15}}({_DATE_NUMERIC})"
)
_GREEK_MONTHS = {
    "ιανουαριου":1,"φεβρουαριου":2,"μαρτιου":3,"απριλιου":4,"μαιου":5,"μαΐου":5,
    "ιουνιου":6,"ιουλιου":7,"αυγουστου":8,"σεπτεμβριου":9,"οκτωβριου":10,"νοεμβριου":11,"δεκεμβριου":12
}
_DATE_GREEK_TEXT_RE = re.compile(r"(\d{1,2})\s+([Α-ΩA-ΩΪΫάέήίόύώϊΐϋΰα-ω]+)\s+(\d{4})")

def _norm_numeric_date(s: str) -> Optional[str]:
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y"):
        try:
            dt = datetime.strptime(s, fmt)
            if "%y" in fmt:
                y = dt.year
                dt = dt.replace(year=2000 + (y % 100) if y % 100 < 50 else 1900 + (y % 100))
            return _to_iso(dt)
        except ValueError:
            continue
    return None

def _norm_greek_text_date(day: str, month_txt: str, year: str) -> Optional[str]:
    key = re.sub(r"[^\w]", "", month_txt, flags=re.UNICODE).lower()
    m = _GREEK_MONTHS.get(key)
    if not m:
        return None
    try:
        dt = datetime(int(year), m, int(day))
        return _to_iso(dt)
    except ValueError:
        return None

def regex_exam_date(text: str) -> Optional[str]:
    m = _DATE_LABELED_RE.search(text)
    if m:
        iso = _norm_numeric_date(m.group(2))
        return iso or m.group(2)
    m2 = _DATE_GREEK_TEXT_RE.search(text)
    if m2:
        iso = _norm_greek_text_date(m2.group(1), m2.group(2), m2.group(3))
        if iso:
            return iso
    m3 = re.search(_DATE_NUMERIC, text)
    if m3:
        iso = _norm_numeric_date(m3.group(0))
        return iso or m3.group(0)
    return None

# BPE
_BPE_EN = re.compile(
    r"\b(?:bpe|background\s+parenchymal\s+enhancement)\b[^\n\r]{0,50}?\b(minimal|mild|moderate|marked)\b",
    flags=re.IGNORECASE
)
_BPE_GR1 = re.compile(r"(μηδαμινη|ηπια|μετρια|εντονη)[^\n\r]{0,40}?ενισχυση\s+παρεγχυματος")
_BPE_GR2 = re.compile(r"ενισχυση\s+παρεγχυματος[^\n\r]{0,40}?(μηδαμινη|ηπια|μετρια|εντονη)")

def regex_bpe(text: str) -> Optional[str]:
    m_en = _BPE_EN.search(text)
    if m_en:
        token = m_en.group(1).lower()
        return {"minimal":"Minimal","mild":"Mild","moderate":"Moderate","marked":"Marked"}[token]
    t = _deaccent_lower(text)
    for rex in (_BPE_GR1, _BPE_GR2):
        m = rex.search(t)
        if m:
            token = m.group(1)
            return {"μηδαμινη":"Minimal","ηπια":"Mild","μετρια":"Moderate","εντονη":"Marked"}[token]
    return None

# ADC — phrases widened; outputs: "χωρίς περιορισμό" | "με περιορισμό"
_ADC_EN = re.compile(r"\badc\b[^\n\r]{0,30}\b(high|low)\b", flags=re.IGNORECASE)
_ADC_GR1 = re.compile(r"\badc\b[^\n\r]{0,30}\b(υψηλο|χαμηλο)\b")
_ADC_GR2 = re.compile(r"(δεικτης\s+διαχυσης\s+νερου)[^\n\r]{0,40}\b(υψηλο|χαμηλο)\b")
_ADC_NO_RESTRICTION = re.compile(r"ελευθερη\s+διαχυση|χωρις[^\n\r]{0,40}?περιορισμ\w+")
_ADC_RESTRICTION    = re.compile(r"\bμε[^\n\r]{0,40}?περιορισμ\w+|\bπεριορισμ\w+\s+διαχυση\b")

def regex_adc(text: str) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)
    if _ADC_NO_RESTRICTION.search(t):
        return "χωρίς περιορισμό"
    if _ADC_RESTRICTION.search(t):
        return "με περιορισμό"
    m = _ADC_EN.search(raw)
    if m:
        return "χωρίς περιορισμό" if m.group(1).lower() == "high" else "με περιορισμό"
    for rex in (_ADC_GR1, _ADC_GR2):
        m = rex.search(t)
        if m:
            token = m.group(1 if rex is _ADC_GR1 else 2)
            return "χωρίς περιορισμό" if token == "υψηλο" else "με περιορισμό"
    return None

# Perfusion curve — αιμοδυναμική καμπύλη τύπος/τύπου I/II/III (accept Greek 'ι', digits)
def _romanize_token(tok: str) -> Optional[str]:
    t = _deaccent_lower(tok.strip()).replace("ι", "i")
    return {"i":"I","ii":"II","iii":"III","1":"I","2":"II","3":"III"}.get(t)

_PERF_EN = re.compile(
    r"(?:perfusion|kinetic|time[-\s]*intensity|contrast[-\s]*enhancement)[^\n\r]{0,50}?type\s*(I{1,3}|1|2|3)",
    flags=re.IGNORECASE
)
_PERF_GR = re.compile(
    r"(αιμοδυναμικη\s+καμπυλη|κινητικη\s+καμπυλη|δυναμικη\s+προσληψη)[^\n\r]{0,50}?τυπ(?:ος|ου)\s*[:\-]?\s*([iι]{1,3}|1|2|3)"
)

def regex_perfusion(text: str) -> Optional[str]:
    m_en = _PERF_EN.search(text)
    if m_en:
        rnum = _romanize_token(m_en.group(1));  return f"Τύπος {rnum}" if rnum else None
    t = _deaccent_lower(text)
    m_gr = _PERF_GR.search(t)
    if m_gr:
        rnum = _romanize_token(m_gr.group(2));  return f"Τύπος {rnum}" if rnum else None
    return None


# ACR density
_GREEK_ACR_MAP = {"α":"A","β":"B","γ":"C","δ":"D","Α":"A","Β":"B","Γ":"C","Δ":"D"}
_ACR_RE = re.compile(r"\bacr\b[^\n\r]{0,12}?([A-DΑ-Δa-dα-δ](?:\s*[-/]\s*[A-DΑ-Δa-dα-δ])*)", flags=re.IGNORECASE)

def _normalize_acr_letters(s: str) -> Optional[str]:
    letters = re.findall(r"[A-Da-dΑ-Δα-δ]", s)
    out, seen = [], set()
    for ch in letters:
        ch = _GREEK_ACR_MAP.get(ch, ch).upper()
        if ch in {"A","B","C","D"} and ch not in seen:
            seen.add(ch); out.append(ch)
    return "-".join(out) if out else None

def regex_acr(text: str) -> Optional[str]:
    m = _ACR_RE.search(text)
    if m:
        return _normalize_acr_letters(m.group(1))
    m2 = re.search(r"\(?\s*acr\s*[:\-]?\s*([A-DΑ-Δa-dα-δ](?:\s*[-/]\s*[A-DΑ-Δa-δa-d])*)\s*\)?", text, flags=re.IGNORECASE)
    if m2:
        return _normalize_acr_letters(m2.group(1))
    return None

# --- Μάζα (μάζα ή ενισχυόμενη βλάβη) ---
_MZ_NEG = re.compile(
    r"(?:\bδεν\s+παρατηρειται|\bαπουσια|\bχωρις)\s+"
    r"(?:μαζ\w+|μαζομορφ\w+|συμπαγ\w+\s+αλλοιωσ\w+|ενισχυομεν\w+\s+βλαβ\w+|"
    r"χωροκατακτητικ\w+\s+εξεργασ\w+)"
)
_MZ_NON_MASS = re.compile(
    r"\bμη\s+μαζ[οο]μορφ\w+\s+(?:ενισχυ\w+|βλαβ\w+|σκιαγραφ\w+\s+ενισχυ\w+)"
)
_MZ_EXPANSIVE = re.compile(r"χωροκατακτητικ\w+\s+εξεργασ\w+")
_MZ_SOLID = re.compile(r"συμπαγ\w+\s+αλλοιωσ\w+")
_MZ_MASS_WORD = re.compile(r"\bμαζ[ααςες]\b|\bμαζομορφ\w+")
_MZ_ENH_LESION = re.compile(r"ενισχυομεν\w+\s+βλαβ\w+")
# treat "σχηματισμός" as mass
_MZ_FORMATION = re.compile(r"σχηματισμ\w+")
# treat "αλλοίωση" with explicit size as mass (e.g., διαμέτρου 7 χιλ., 1,3 εκ.)
_MZ_LESION_WITH_SIZE = re.compile(
    r"αλλοιωσ\w+[^\n\r]{0,60}?(?:διαμετρ\w+|μεγεθ\w+|(?:\b\d+(?:[.,]\d+)?)\s*(?:χιλ|εκ)\b)"
)


def regex_maza(text: str) -> Optional[str]:
    t = _deaccent_lower(text)
    # explicit negatives first
    if _MZ_NEG.search(t):
        return "δεν υπάρχει"

    # strong positives
    if _MZ_EXPANSIVE.search(t):
        return "χωροκατακτητική εξεργασία"
    if (_MZ_SOLID.search(t) or _MZ_MASS_WORD.search(t) or
        _MZ_ENH_LESION.search(t) or _MZ_FORMATION.search(t) or
        _MZ_LESION_WITH_SIZE.search(t)):
        return "συμπαγής αλλοίωση"

    # non-mass mention only counts as negative if no positive evidence
    if _MZ_NON_MASS.search(t):
        return "δεν υπάρχει"

    return None


# --- ΜΗ ΜΑΖΟΜΟΡΦΗ ΕΝΙΣΧΥΣΗ (presence) ---
_NME_EN_NEG = re.compile(r"\bno\s+non[-\s]?mass(?:[-\s]?like)?\s+enhancement\b", flags=re.IGNORECASE)
_NME_EN_POS = re.compile(r"\bnon[-\s]?mass(?:[-\s]?like)?\s+enhancement\b|\bnme\b", flags=re.IGNORECASE)
# de-accented Greek; handle genitives and variants
_NME_GR_NEG = re.compile(
    r"(?:\bδεν\s+παρατηρειται|\bαπουσια|\bχωρις)\s+μη\s+μαζ[οο]μορφ\w+\s+(?:ενισχυ\w+|σκιαγραφ\w+\s+ενισχυ\w+|παραμαγνητικ\w+\s+ενισχυ\w+)"
)
_NME_GR_POS1 = re.compile(
    r"\bμη\s+μαζ[οο]μορφ\w+\s+(?:ενισχυ\w+|σκιαγραφ\w+\s+ενισχυ\w+|παραμαγνητικ\w+\s+ενισχυ\w+)"
)
_NME_GR_POS2 = re.compile(
    r"\bμη\s+μαζ\w+\s+μορφ\w*\b[^\n\r]{0,60}?(?:ενισχυ\w+|σκιαγραφ\w+\s+ενισχυ\w+|παραμαγνητικ\w+\s+ενισχυ\w+)"
)

def regex_nme_presence(text: str) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)
    if _NME_EN_NEG.search(raw) or _NME_GR_NEG.search(t):
        return "δεν υπάρχει"
    if _NME_EN_POS.search(raw) or _NME_GR_POS1.search(t) or _NME_GR_POS2.search(t):
        return "υπάρχει"
    return None

# --- Σαφή ή ασαφή όρια ---
_ORIA_EN_SAFI  = re.compile(r"\bwell[-\s]?defined\s+margins?\b", flags=re.IGNORECASE)
_ORIA_EN_ASAFI = re.compile(r"\bill[-\s]?defined\s+margins?\b|\bindistinct\s+margins?\b", flags=re.IGNORECASE)

# de-accented Greek, πιάσε «σαφή/ασαφή/καθαρά/ακαθόριστα/θολά … όρια» και «όρια … σαφή/ασαφή …»
_ORIA_GR_SAFI1  = re.compile(r"(σαφη|καθαρα)[^\n\r]{0,10}?ορια")
_ORIA_GR_SAFI2  = re.compile(r"ορια[^\n\r]{0,10}?(σαφη|καθαρα)")
_ORIA_GR_SAFI3  = re.compile(r"(σαφων|καθαρων)[^\n\r]{0,10}?οριων")
_ORIA_GR_ASAFI1 = re.compile(r"(ασαφη|ακαθοριστα|θολα)[^\n\r]{0,10}?ορια")
_ORIA_GR_ASAFI2 = re.compile(r"ορια[^\n\r]{0,10}?(ασαφη|ακαθοριστα|θολα)")
_ORIA_GR_ASAFI3 = re.compile(r"(ασαφων|ακαθοριστων|θολων)[^\n\r]{0,10}?οριων")

def regex_margins(text: str) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)
    # English πρώτα
    if _ORIA_EN_ASAFI.search(raw): return "ασαφή"
    if _ORIA_EN_SAFI.search(raw):  return "σαφή"
    # Greek
    if _ORIA_GR_ASAFI1.search(t) or _ORIA_GR_ASAFI2.search(t) or _ORIA_GR_ASAFI3.search(t): return "ασαφή"
    if _ORIA_GR_SAFI1.search(t)  or _ORIA_GR_SAFI2.search(t)  or _ORIA_GR_SAFI3.search(t):  return "σαφή"
    return None

# --- Ακτινωτές προσεκβολές (spiculations) ---
_SPIC_EN_NEG = re.compile(r"\bno\s+spiculations?\b|\bnon[-\s]?spiculated\b", flags=re.IGNORECASE)
_SPIC_EN_POS = re.compile(r"\bspiculated\b|\bspiculation[s]?\b|\bradial\s+spicul\w+\b", flags=re.IGNORECASE)

# Greek (de-accented): ακτινωτ- προσεκβολ-
_SPIC_GR_NEG = re.compile(r"(?:\bδεν\s+παρατηρειτ\w+|\bχωρις|\bαπουσια)\s+ακτινωτ\w+\s+προσεκβολ\w+")
_SPIC_GR_POS = re.compile(r"\bακτινωτ\w+\s+προσεκβολ\w+")

def regex_radial_spiculations(text: str) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)
    if _SPIC_EN_NEG.search(raw) or _SPIC_GR_NEG.search(t):
        return "δεν υπάρχει"
    if _SPIC_EN_POS.search(raw) or _SPIC_GR_POS.search(t):
        return "υπάρχει"
    return None

# --- Πρότυπο ενίσχυσης ---
# English helpers
_ENH_EN_HOM = re.compile(r"\b(homogeneous|uniform)\s+(?:contrast\s+)?enhancement\b|\benhancement\s+is\s+homogeneous\b", re.IGNORECASE)
_ENH_EN_HET = re.compile(r"\b(heterogeneous|non[-\s]?uniform)\s+(?:contrast\s+)?enhancement\b|\benhancement\s+is\s+heterogeneous\b", re.IGNORECASE)
_ENH_EN_PERI = re.compile(r"\b(peripheral\s+enhanc\w+|rim[-\s]?enhanc\w+)\b", re.IGNORECASE)

# Greek (de-accented), match around «ενίσχυ-»
_ENH_GR_HOM1 = re.compile(r"\bομοιογεν\w+[^\n\r]{0,20}?ενισχυ\w+")
_ENH_GR_HOM2 = re.compile(r"ενισχυ\w+[^\n\r]{0,20}?ομοιογεν\w+")
_ENH_GR_HET1 = re.compile(r"\bανομοιογεν\w+[^\n\r]{0,20}?ενισχυ\w+")
_ENH_GR_HET2 = re.compile(r"ενισχυ\w+[^\n\r]{0,20}?ανομοιογεν\w+")
_ENH_GR_PERI1 = re.compile(r"\bπεριφερικ\w+[^\n\r]{0,20}?ενισχυ\w+")
_ENH_GR_PERI2 = re.compile(r"ενισχυ\w+[^\n\r]{0,20}?περιφερικ\w+")
_ENH_GR_RIM   = re.compile(r"\bδακτυλιοειδ\w+[^\n\r]{0,20}?ενισχυ\w+")

def regex_enhancement_pattern(text: str, maza_ev: Optional[str]) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)

    # homogeneous / heterogeneous (allowed for masses or NME)
    if _ENH_EN_HET.search(raw) or _ENH_GR_HET1.search(t) or _ENH_GR_HET2.search(t):
        return "ανομοιογενής"
    if _ENH_EN_HOM.search(raw) or _ENH_GR_HOM1.search(t) or _ENH_GR_HOM2.search(t):
        return "ομοιογενής"

    # peripheral/rim — only if there is mass evidence
    if maza_ev in ("συμπαγής αλλοίωση", "χωροκατακτητική εξεργασία"):
        if (_ENH_EN_PERI.search(raw) or _ENH_GR_PERI1.search(t) or
            _ENH_GR_PERI2.search(t) or _ENH_GR_RIM.search(t)):
            return "περιφερική"

    return None

# --- Μη ενισχυόμενα διαφραγμάτια (non-enhancing septations) ---
# English
_SEPT_EN_POS = re.compile(r"\bnon[-\s]?enhanc\w+\s+septation\w*\b", re.IGNORECASE)
_SEPT_EN_NEG = re.compile(r"\b(?:no\s+septation\w*|enhanc\w+\s+septation\w*)\b", re.IGNORECASE)  # no septations OR enhancing septations

# Greek (de-accented)
_SEPT_GR_POS1 = re.compile(r"\bμη\s+ενισχυομεν\w+\s+διαφραγμ\w+")
_SEPT_GR_POS2 = re.compile(r"\bδιαφραγμ\w+[^\n\r]{0,10}?μη\s+ενισχυ\w+")
_SEPT_GR_NEG1 = re.compile(r"(?:\bδεν\s+παρατηρειτ\w+|\bχωρις|\bαπουσια)\s+διαφραγμ\w+")
_SEPT_GR_NEG2 = re.compile(r"\bενισχυομεν\w+\s+διαφραγμ\w+")  # explicitly enhancing

def regex_non_enhancing_septa(text: str) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)
    # negatives first to avoid false positives
    if _SEPT_EN_NEG.search(raw) or _SEPT_GR_NEG1.search(t) or _SEPT_GR_NEG2.search(t):
        return "δεν υπάρχει"
    if _SEPT_EN_POS.search(raw) or _SEPT_GR_POS1.search(t) or _SEPT_GR_POS2.search(t):
        return "υπάρχει"
    return None

# ---- NME distribution types ----
# English
_NME_LIN_EN_POS = re.compile(r"\blinear\b", re.IGNORECASE)
_NME_SEG_EN_POS = re.compile(r"\bsegmental\b", re.IGNORECASE)
_NME_REG_EN_POS = re.compile(r"\bregional\b", re.IGNORECASE)
_NME_BIL_EN_POS = re.compile(r"\bbilateral\b", re.IGNORECASE)
_NME_EN_NEG_TPL = r"\b(?:no|without)\s+{word}\b"

# Greek (de-accented)
_NME_LIN_GR = re.compile(r"\bgrammoeid\w+|\bγραμμοειδ\w+")
_NME_SEG_GR = re.compile(r"\bτμηματικ\w+")
_NME_REG_GR = re.compile(r"\bπεριοχικ\w+")
_NME_BIL_GR = re.compile(r"\bαμφοτεροπλευρ\w+")
_NME_GR_NEG_TPL = r"(?:\bδεν\s+παρατηρειτ\w+|\bχωρις|\bαπουσια)[^\n\r]{{0,10}}{word}"


def _nme_type_regex(text: str, kind: str) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)

    if kind == "linear":
        en_pos, gr_pos = _NME_LIN_EN_POS, _NME_LIN_GR
        en_neg = re.compile(_NME_EN_NEG_TPL.format(word=r"linear"), re.IGNORECASE)
        gr_neg = re.compile(_NME_GR_NEG_TPL.format(word=r"γραμμοειδ\w+"))
    elif kind == "segmental":
        en_pos, gr_pos = _NME_SEG_EN_POS, _NME_SEG_GR
        en_neg = re.compile(_NME_EN_NEG_TPL.format(word=r"segmental"), re.IGNORECASE)
        gr_neg = re.compile(_NME_GR_NEG_TPL.format(word=r"τμηματικ\w+"))
    elif kind == "regional":
        en_pos, gr_pos = _NME_REG_EN_POS, _NME_REG_GR
        en_neg = re.compile(_NME_EN_NEG_TPL.format(word=r"regional"), re.IGNORECASE)
        gr_neg = re.compile(_NME_GR_NEG_TPL.format(word=r"περιοχικ\w+"))
    elif kind == "bilateral":
        en_pos, gr_pos = _NME_BIL_EN_POS, _NME_BIL_GR
        en_neg = re.compile(_NME_EN_NEG_TPL.format(word=r"bilateral"), re.IGNORECASE)
        gr_neg = re.compile(_NME_GR_NEG_TPL.format(word=r"αμφοτεροπλευρ\w+"))
    else:
        return None

    # negatives first
    if en_neg.search(raw) or gr_neg.search(t):
        return "δεν υπάρχει"
    if en_pos.search(raw) or gr_pos.search(t):
        return "υπάρχει"
    return None

# --- Ύπαρξη Ενίσχυσης (pathologic enhancement areas) ---
_ENHP_EN_POS = re.compile(
    r"\b(pathologic(?:al)?\s+(?:contrast\s+)?enhancement|areas?\s+of\s+pathologic(?:al)?\s+enhancement)\b",
    flags=re.IGNORECASE
)
# Greek (de-accented): match «(περιοχές )?παθολογικής σκιαγραφικής ενίσχυσης»
_ENHP_GR_POS = re.compile(r"(?:περιοχε\w+\s+)?παθολογικ\w+\s+σκιαγραφ\w+\s+ενισχυ\w+")
# Explicit negations around the same concept
_ENHP_GR_NEG = re.compile(
    r"(?:\bδεν\s+παρατηρειτ\w+|\bχωρις|\bαπουσια)[^\n\r]{0,20}(?:περιοχε\w+\s+)?παθολογικ\w+\s+σκιαγραφ\w+\s+ενισχυ\w+"
)
_ENHP_EN_NEG = re.compile(r"\bno\s+(?:areas?\s+of\s+)?pathologic(?:al)?\s+(?:contrast\s+)?enhancement\b", re.IGNORECASE)

def regex_enhancement_presence(text: str) -> Optional[str]:
    raw = text
    t = _deaccent_lower(raw)
    # negatives first
    if _ENHP_EN_NEG.search(raw) or _ENHP_GR_NEG.search(t):
        return "δεν υπάρχει"
    if _ENHP_EN_POS.search(raw) or _ENHP_GR_POS.search(t):
        return "υπάρχει"
    return None



# ================== DYNAMIC SCHEMA ====================
FIELDS_SPEC = {
    "breast": (Optional[Literal["Left", "Right", "Both"]]),
    "left_breast":  (bool, Field(False)),
    "right_breast": (bool, Field(False)),

    "enhancement_presence": (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),

    "birads": (Optional[int], Field(None, ge=0, le=6)),
    "exam_date": (Optional[str], None),
    "bpe": (Optional[Literal["Minimal", "Mild", "Moderate", "Marked"]], None),
    "adc": (Optional[Literal["χωρίς περιορισμό", "με περιορισμό"]], None),
    "perfusion_curve": (Optional[Literal["Τύπος I", "Τύπος II", "Τύπος III"]], None),
    "acr": (Optional[str], None),
    "maza": (Optional[Literal["συμπαγής αλλοίωση", "χωροκατακτητική εξεργασία", "δεν υπάρχει"]], None),
    "nme_presence": (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),
    # "margins": (Optional[Literal["σαφή", "ασαφή"]], None),
    "mass_margins": (Optional[Literal["σαφή", "ασαφή"]], None),
    "nme_margins": (Optional[Literal["σαφή", "ασαφή"]], None),
    "radial_spiculations": (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),
    # "enhancement_pattern": (Optional[Literal["ομοιογενής", "ανομοιογενής", "περιφερική"]], None),
    "mass_enhancement_pattern": (Optional[Literal["ομοιογενής", "ανομοιογενής", "περιφερική"]], None),
    "nme_enhancement_pattern": (Optional[Literal["ομοιογενής", "ανομοιογενής"]], None),
    "non_enhancing_septa": (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),
    "nme_linear":    (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),
    "nme_segmental": (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),
    "nme_regional":  (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),
    "nme_bilateral": (Optional[Literal["υπάρχει", "δεν υπάρχει"]], None),
}

def make_model(keys: list[str]):
    fields = {k: FIELDS_SPEC[k] for k in keys}
    return create_model("ExtractSelected", **fields)

def extract_all(report_text: str, prompt_keys: list[str], use_regex_fallback: bool = True) -> dict:
    # which fields require gating?
    gated_mass_fields = {"mass_margins", "radial_spiculations", "non_enhancing_septa", "mass_enhancement_pattern"}
    gated_nme_fields  = {"nme_margins", "nme_enhancement_pattern"}

    need_mass_gate = any(k in prompt_keys for k in gated_mass_fields)
    need_nme_gate  = any(k in prompt_keys for k in gated_nme_fields)

    # --- LLM-only gates via separate minimal calls ---
    MASS_POS_VALUES = ("συμπαγής αλλοίωση", "χωροκατακτητική εξεργασία")
    maza_llm = _llm_gate_value(report_text, "maza") if need_mass_gate else None
    mass_flag = maza_llm in MASS_POS_VALUES if need_mass_gate else False

    nme_llm = _llm_gate_value(report_text, "nme_presence") if need_nme_gate else None
    nme_flag = (nme_llm == "υπάρχει") if need_nme_gate else False

    # --- main LLM pass only on requested keys ---
    DynModel = make_model(prompt_keys)
    main_prompt = apply_chat_template(build_prompt(report_text, prompt_keys))
    out = model(main_prompt, DynModel, max_new_tokens=320, do_sample=False)
    obj = DynModel.model_validate_json(out).model_dump()

    # --- optional regex fills for NON-gated fields only ---
    if use_regex_fallback:
        if "birads" in prompt_keys and obj.get("birads") is None:
            obj["birads"] = regex_birads(report_text)
        if "exam_date" in prompt_keys and (obj.get("exam_date") in (None, "")):
            obj["exam_date"] = regex_exam_date(report_text) or obj["exam_date"]
        if "bpe" in prompt_keys and obj.get("bpe") is None:
            obj["bpe"] = regex_bpe(report_text) or obj["bpe"]
        if "perfusion_curve" in prompt_keys and obj.get("perfusion_curve") is None:
            obj["perfusion_curve"] = regex_perfusion(report_text) or obj["perfusion_curve"]
        if "nme_presence" in prompt_keys:
            ev = regex_nme_presence(report_text)
            if ev is not None:
                obj["nme_presence"] = ev
            elif obj.get("nme_presence") not in ("υπάρχει", "δεν υπάρχει"):
                obj["nme_presence"] = None
        if "enhancement_presence" in prompt_keys:
            ev = regex_enhancement_presence(report_text)
            if ev is not None:
                obj["enhancement_presence"] = ev
            elif obj.get("enhancement_presence") not in ("υπάρχει", "δεν υπάρχει"):
                obj["enhancement_presence"] = None


    # --- ADC: controlled by use_regex_fallback (like ACR) ---
    if "adc" in prompt_keys:
        val = obj.get("adc")  # LLM output

        if use_regex_fallback:
            # Prefer regex evidence from report
            ev = regex_adc(report_text)  # "χωρίς περιορισμό" / "με περιορισμό" / None
            if ev is not None:
                obj["adc"] = ev
            else:
                # If no regex evidence, keep only a valid LLM value, else null
                if val not in ("χωρίς περιορισμό", "με περιορισμό"):
                    obj["adc"] = None
        else:
            # No regex: accept only a valid LLM label, else null
            if val not in ("χωρίς περιορισμό", "με περιορισμό"):
                obj["adc"] = None

    # --- ACR: controlled by use_regex_fallback ---
    if "acr" in prompt_keys:
        val = obj.get("acr")

        if use_regex_fallback:
            # Prefer explicit regex evidence from the report
            ev = regex_acr(report_text)
            if ev is not None:
                obj["acr"] = ev
            else:
                # If LLM proposed something, normalize and validate it
                if isinstance(val, str):
                    norm = _normalize_acr_letters(val)
                    obj["acr"] = norm if norm is not None else None
                else:
                    obj["acr"] = None
        else:
            # No regex usage: only accept a valid, normalizable LLM value
            if isinstance(val, str):
                norm = _normalize_acr_letters(val)
                obj["acr"] = norm if norm is not None else None
            else:
                obj["acr"] = None


    # ------- MASS-GATED -------
    if "mass_margins" in prompt_keys:
        if not mass_flag:
            obj["mass_margins"] = None
        else:
            if use_regex_fallback:
                val = regex_margins(report_text)
                obj["mass_margins"] = val if val is not None else obj.get("mass_margins")
            else:
                if obj.get("mass_margins") not in ("σαφή", "ασαφή"):
                    obj["mass_margins"] = None

    if "radial_spiculations" in prompt_keys:
        if not mass_flag:
            obj["radial_spiculations"] = None
        else:
            if use_regex_fallback:
                val = regex_radial_spiculations(report_text)
                obj["radial_spiculations"] = val if val is not None else obj.get("radial_spiculations")
            else:
                if obj.get("radial_spiculations") not in ("υπάρχει", "δεν υπάρχει"):
                    obj["radial_spiculations"] = None

    if "non_enhancing_septa" in prompt_keys:
        if not mass_flag:
            obj["non_enhancing_septa"] = None
        else:
            if use_regex_fallback:
                val = regex_non_enhancing_septa(report_text)
                obj["non_enhancing_septa"] = val if val is not None else None
            else:
                if obj.get("non_enhancing_septa") not in ("υπάρχει", "δεν υπάρχει"):
                    obj["non_enhancing_septa"] = None

    if "mass_enhancement_pattern" in prompt_keys:
        if not mass_flag:
            obj["mass_enhancement_pattern"] = None
        else:
            if use_regex_fallback:
                val = regex_enhancement_pattern(report_text, "συμπαγής αλλοίωση")
                obj["mass_enhancement_pattern"] = val if val is not None else obj.get("mass_enhancement_pattern")
            else:
                if obj.get("mass_enhancement_pattern") not in ("ομοιογενής", "ανομοιογενής", "περιφερική"):
                    obj["mass_enhancement_pattern"] = None

    # ------- NME-GATED -------
    if "nme_margins" in prompt_keys:
        if not nme_flag:
            obj["nme_margins"] = None
        else:
            if use_regex_fallback:
                val = regex_margins(report_text)
                obj["nme_margins"] = val if val is not None else obj.get("nme_margins")
            else:
                if obj.get("nme_margins") not in ("σαφή", "ασαφή"):
                    obj["nme_margins"] = None

    if "nme_enhancement_pattern" in prompt_keys:
        if not nme_flag:
            obj["nme_enhancement_pattern"] = None
        else:
            if use_regex_fallback:
                val = regex_enhancement_pattern(report_text, None)  # never emit 'περιφερική' for NME
                obj["nme_enhancement_pattern"] = val if val in ("ομοιογενής", "ανομοιογενής") else None
            else:
                if obj.get("nme_enhancement_pattern") not in ("ομοιογενής", "ανομοιογενής"):
                    obj["nme_enhancement_pattern"] = None
    

    # ------- NME-DISTRIBUTION FLAGS (require NME per LLM) -------
    if "nme_linear" in prompt_keys:
        if not nme_flag:
            obj["nme_linear"] = None
        else:
            if use_regex_fallback:
                val = _nme_type_regex(report_text, "linear")
                obj["nme_linear"] = val if val is not None else None
            else:
                if obj.get("nme_linear") not in ("υπάρχει", "δεν υπάρχει"):
                    obj["nme_linear"] = None

    if "nme_segmental" in prompt_keys:
        if nme_flag:
            if use_regex_fallback:
                val = _nme_type_regex(report_text, "segmental")
                obj["nme_segmental"] = val if val is not None else None
            else:
                if obj.get("nme_segmental") not in ("υπάρχει", "δεν υπάρχει"):
                    obj["nme_segmental"] = None
        else:
            # NME gate is negative: allow explicit NEGATION to survive, otherwise null
            if use_regex_fallback:
                neg = _nme_type_regex(report_text, "segmental")
                obj["nme_segmental"] = "δεν υπάρχει" if neg == "δεν υπάρχει" else None
            else:
                if obj.get("nme_segmental") != "δεν υπάρχει":
                    obj["nme_segmental"] = None


    if "nme_regional" in prompt_keys:
        if not nme_flag:
            obj["nme_regional"] = None
        else:
            if use_regex_fallback:
                val = _nme_type_regex(report_text, "regional")
                obj["nme_regional"] = val if val is not None else None
            else:
                if obj.get("nme_regional") not in ("υπάρχει", "δεν υπάρχει"):
                    obj["nme_regional"] = None

    if "nme_bilateral" in prompt_keys:
        if not nme_flag:
            obj["nme_bilateral"] = None
        else:
            if use_regex_fallback:
                val = _nme_type_regex(report_text, "bilateral")
                obj["nme_bilateral"] = val if val is not None else None
            else:
                if obj.get("nme_bilateral") not in ("υπάρχει", "δεν υπάρχει"):
                    obj["nme_bilateral"] = None


    return {k: obj.get(k) for k in prompt_keys}

def reduce_to_laterality_view(merged: dict) -> dict:
    """Map laterality evidence into {"Left": bool, "Right": bool}."""
    lb = merged.get("left_breast")
    rb = merged.get("right_breast")
    br = merged.get("breast")
    return {
        "Left":  bool((lb is True) or (br in ("Left", "Both"))),
        "Right": bool((rb is True) or (br in ("Right", "Both"))),
    }





def extract_and_merge(
    report_text: str,
    key_groups: list[list[str]],
    use_regex_fallback: bool = True,
) -> dict:
    """
    Run multiple independent extractions with different PROMPT_KEYS
    and merge results into a single JSON object.

    - key_groups: list of PROMPT_KEYS lists, e.g.
        [
          ["birads", "exam_date"],
          ["maza", "mass_margins"],
          ["nme_presence", "nme_margins"],
        ]
    - For overlapping keys:
        last non-null value wins.
    """
    merged: dict = {}

    for keys in key_groups:
        if not keys:
            continue
        partial = extract_all(report_text, keys, use_regex_fallback=use_regex_fallback)
        for k, v in partial.items():
            # overwrite only if:
            # - key not set yet, or
            # - new value is not None
            if k not in merged or v is not None:
                merged[k] = v

    # ensure all mentioned keys exist (null if never set)
    all_keys = {k for group in key_groups for k in group}
    for k in all_keys:
        merged.setdefault(k, None)

    return merged



# ======================== MAIN ========================
if __name__ == "__main__":
    report_paths = ["pat0001.txt", "pat0002.txt", "pat0003.txt"]
    report_paths = ["pat0002.txt"]
    report_paths = ["pat0001.txt", "pat0002.txt", "pat0003.txt", "pat0004.txt", "pat0005.txt", "pat0006.txt"]
    # report_paths = os.listdir("txt/")
    report_paths.sort()
    print(f"Processing {len(report_paths)} reports...")
    for report_path in report_paths:
        print(f"Processing report: {report_path}")
        with open(os.path.join("txt/", report_path), "r", encoding="utf-8") as f:
            report_text = f.read()
            


        groups = [
            # ["birads"],
            ["enhancement_presence"],
            # ["breast"],
            # ["left_breast"], ["right_breast"],
            # ["cysts_left", "cysts_right"],
            # ["maza"], ["mass_margins"], ["radial_spiculations"], ["adc"]
            # ["mass_enhancement_pattern"], ["non_enhancing_septa"],
            # ["nme_presence"], ["nme_margins"], ["nme_enhancement_pattern"],
            # ["nme_linear"], ["nme_segmental"], ["nme_regional"], ["nme_bilateral"],
            # ["bpe"], ["perfusion_curve"],
        ]

        # identify the breast of interest
        # breast_details = extract_and_merge(
        #     report_text,
        #     key_groups=[["breast"], ["left_breast"], ["right_breast"]],
        #     use_regex_fallback=False,
        # )
        # breast_location = reduce_to_laterality_view(breast_details)
        # print(breast_location)

        

        data = extract_and_merge(report_text, groups, use_regex_fallback=False)
        print(data)
        # data = project_with_laterality(data)

        # pat_id = os.path.splitext(os.path.basename(report_path))[0]
        # save_to_csv(pat_id, data, csv_path="reports_extracted.csv")
        # save_to_json(pat_id, data, json_path="reports_extracted.json")
        # save_to_xml(pat_id, data, xml_path="reports_extracted.xml")
        # print(f"Extracted data for {pat_id}: {data}")

        pat_id = os.path.splitext(os.path.basename(report_path))[0]
        save_to_csv(pat_id, data, csv_path="reports_extracted.csv")
        save_to_json(pat_id, data, json_path="reports_extracted.json")
        save_to_xml(pat_id, data, xml_path="reports_extracted.xml")
        # print(f"Extracted data for {pat_id}: {data}")
