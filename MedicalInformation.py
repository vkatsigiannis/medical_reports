from typing import Optional, Literal
from pydantic import Field

class Birads:
    _prompt = ("- BIRADS category as an integer 0..6. Accept I/II/III/IV/V/VI and map to 1..6.")
    _field_spec = (Optional[int], Field(None, ge=0, le=6))
    _field_stub = '"BIRADS": <0..6 or null>'

class FamilyHistory:
    _prompt = ("- Ιστορικό Ca (Family / Οικογενειακό): Allowed: Yes / No.\n"
        "Rules:\n"
        "  • Yes only if the report explicitly states the PATIENT has a history of cancer "
        "(e.g., «θετικό (οικογενειακό) ιστορικό καρκίνου …», ««θετικό (οικογενειακό) ιστορικό Ca …», s/p treatment for cancer).\n"
        "  • No only if there is an explicit negation of PERSONAL cancer history "
        "(e.g., «χωρίς/αρνητικό (οικογενειακό) ιστορικό καρκίνου», «δεν αναφέρεται  (οικογενειακό) ιστορικό καρκίνου»).")
    _field_spec = (Optional[Literal["Yes", "No"]], None)
    _field_stub = '"FamilyHistory": <Yes|No or null>'

class ACR:
    # Breast Density
    _prompt = ("- Πυκνότητα μαστού ACR. Allowed: A / B / C / D ή συνδυασμοί. "
           "Αν υπάρχουν πολλαπλά, επέστρεψέ τα ενωμένα με '-' διατηρώντας τη σειρά (π.χ. C-D).")
    _field_spec = (Optional[str], None)
    _field_stub = '"ACR": <A|B|C|D or combos like C-D or null>'

class BPE:
    _prompt = ("- Background Parenchymal Enhancement (BPE). Allowed: Minimal, Mild, Moderate, Marked. "
           "Greek: ΜΗΔΑΜΙΝΗ→Minimal, ΗΠΙΑ→Mild, ΜΕΤΡΙΑ→Moderate, ΕΝΤΟΝΗ→Marked.")
    _field_spec = (Optional[Literal["Minimal", "Mild", "Moderate", "Marked"]], None)
    _field_stub = '"BPE": <Minimal|Mild|Moderate|Marked or null>'


class MASS:
    _prompt = ("""- Μάζα (MASS): Allowed values: Yes / No.
        Decision order (apply strictly):
        A) POSITIVE ⇒ Yes if there is an EXPLICIT, SOLID mass/lesion mention, e.g.:
            • «μάζα», «συμπαγής αλλοίωση», «συμπαγής ενισχυόμενη αλλοίωση»,
            «ενισχυόμενη μάζα/βλάβη», «χωροκατακτητική εξεργασία»,
            or English: “mass”, “solid mass”, “solid enhancing mass”, “space-occupying lesion”.
            • «οζώδης αλλοίωση» counts as Yes ONLY when clearly described as solid/enhancing
            or explicitly equated with a mass (e.g., ινοαδένωμα ως συμπαγής αλλοίωση).
        B) NEGATIVE ⇒ No if there is an explicit NEGATION of mass, e.g.:
            • «δεν παρατηρείται/δεν αναδεικνύεται μάζα/συμπαγής αλλοίωση»,
            English: “no (solid) mass is seen”.
        C) EXCLUSIONS (do NOT count as mass by themselves):
            • «μη μαζόμορφη ενίσχυση» (NME) without a solid mass statement.
            • «κύστη/κύστεις/κυστικές αλλοιώσεις» without solid mass wording.
            • BPE/background («ενίσχυση παρεγχύματος», BPE Minimal/Mild/Moderate/Marked).
            • Calcifications only, clip, scar, artifact, duct ectasia, technical notes.
        D) Conflicts: Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections.
        E) If evidence is ambiguous (e.g., “οζώδης” without “μάζα/συμπαγής/ενισχυόμενη”), return No.
        Output exactly one of: "Yes" or "No"."""
        )
    _field_spec = (Optional[Literal["Yes", "No"]], None)
    _field_stub = '"MASS": <Yes|No>'

class NME:
    _prompt = ("""- Μη μαζόμορφη ενίσχυση (NME): Allowed values: Yes / No.
        Decision order (apply strictly):
        A) POSITIVE ⇒ Yes if an EXPLICIT non-mass enhancement area is stated, e.g.:
            • «περιοχή/ες μη μαζομορφής σκιαγραφικής ενίσχυσης», «μη μαζόμορφη ενίσχυση»,
            English: “non-mass enhancement”, “NME”.
            • Distribution terms tied to an AREA/REGION count as NME: «γραμμοειδής», «τμηματική»,
            «περιοχική/regional», «δίκην πόρου/ductal», «εστιακή/segmental» when linked to a described area.
        B) NEGATIVE ⇒ No for an explicit negation with NO remainder/except clause, e.g.:
            • «Δεν παρατηρείται/Δεν παρατηρούνται μη μαζόμορφη (σκιαγραφική) ενίσχυση/NME.»
            • English: “No non-mass enhancement is seen.”
        C) REMAINDER/EXCEPT ⇒ Yes if a negation is FOLLOWED by a clause that limits it to
            “the rest of the exam”, e.g.:
            • «… από τον λοιπό έλεγχο», «… από τον έλεγχο του λοιπού μαζικού παρεγχύματος/μαστικού αδένα»,
            «… από τον έλεγχο των μαστικών χώρων», «… κατά τα λοιπά», «… στον υπόλοιπο έλεγχο».
            This implies the rest is negative apart from a described NME area (possibly stated earlier).
        D) EXCLUSIONS (do NOT count as NME by themselves):
            • BPE/background only («ενίσχυση παρεγχύματος», BPE Minimal/Mild/Moderate/Marked) without a specific area.
            • Pure mass wording («μάζα», «συμπαγής αλλοίωση») without explicit NME.
            • Cysts, calcifications, clip/scar, artifacts, duct ectasia, technical notes.
        E) Conflicts: Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections.
        F) Ambiguity: If wording is vague (e.g., distribution terms without an area) ⇒ No.
        Output exactly one of: "Yes" or "No"."""
        )
    _field_spec = (Optional[Literal["Yes", "No"]], None)
    _field_stub = '"NME": <Yes|No>'

class NonEnhancingFindings:
    _prompt = ("""- Μη ενισχυόμενα ευρήματα (NonEnhancingFindings): Allowed values: Yes / No.
        Decision order (apply strictly):
        A) POSITIVE ⇒ Yes if ANY non-enhancing lesion is explicitly present:
            • Cysts: «κύστη», «κύστεις», «κυστική/ες αλλοίωση/ες», English: “cyst(s)”, “simple cyst”.
            Treat simple cysts as non-enhancing even if “non-enhancing” is not stated.
            • Any lesion described as non-enhancing: «μη ενισχυόμενη», «χωρίς (σκιαγραφική) ενίσχυση»,
            English: “non-enhancing”, “no contrast enhancement”.
        B) NEGATIVE ⇒ No if there is an explicit negation of such findings:
            • «Δεν παρατηρούνται/αναδεικνύονται κύστεις/κυστικές αλλοιώσεις»,
            «δεν υπάρχει μη ενισχυόμενη βλάβη», English: “no cysts”, “no non-enhancing lesion”.
            • If only enhancing findings are reported (masses or NME) and no cysts/non-enhancing lesion is mentioned.
        C) EXCLUSIONS (do NOT count as non-enhancing by themselves):
            • NME/«μη μαζόμορφη ενίσχυση» (this is enhancing).
            • Solid/enhancing mass.
            • BPE/background («ενίσχυση παρεγχύματος», BPE Minimal/Mild/Moderate/Marked).
            • Calcifications only, clip/scar, artifacts, duct ectasia, technical notes.
        D) Conflicts: Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections.
            Output exactly one of: "Yes" or "No"."""
        )
    _field_spec = (Optional[Literal["Yes", "No"]], None)
    _field_stub = '"NonEnhancingFindings": <Yes|No>'

class CurveMorphology:
    _prompt = ("""- Αιμοδυναμική καμπύλη (CurveMorphology): Allowed values: 1 / 2 / 3.
        Decision order (apply strictly):
        1) Return 1 if the text explicitly states Type I (π.χ. «αιμοδυναμική καμπύλη τύπου I/Ι») or synonyms:
            persistent/continuous increase, no washout, steadily increasing curve.
        2) Return 2 if Type II (π.χ. «τύπου II/ΙΙ») or synonyms:
            plateau/stabilization after initial rise.
        3) Return 3 if Type III (π.χ. «τύπου III/ΙΙΙ») or synonyms:
            washout/decay after early enhancement.
        Ambiguity and conflicts:
        • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion; otherwise use the curve tied to the target/index lesion.
        • If multiple lesions have different curves and no target is named, choose the most suspicious (3 > 2 > 1).
        • If dynamic sequence not performed or curve not characterized, return null.
        Output exactly one of: 1, 2, 3, or null.
        """
        )
    _field_spec = (Optional[Literal[1, 2, 3]], None)
    _field_stub = '"CurveMorphology": <1|2|3 or null>'

class ADC:
    _prompt = ("""- Δείκτης διάχυσης νερού, ADC (ADC): Allowed values: NR | I | R.
        Thresholds (use numeric ADC when present; normalize 1,2 ↔ 1.2):
            • NON RESTRICTED (NR)  => ADC ≥ 1.4 ×10⁻³ mm²/s
            • INTERMEDIATE (I)     => 1.0 < ADC < 1.4 ×10⁻³ mm²/s
            • RESTRICTION (R)      => ADC ≤ 1.0 ×10⁻³ mm²/s
        Qualitative-only cues (when no number is given):
            • «χωρίς περιορισμό διάχυσης», «ελεύθερη διάχυση»  ⇒ NR
            • «με περιορισμό διάχυσης», «περιορισμένη διάχυση» ⇒ R
            • «ενδιάμεση/οριακή διάχυση» ⇒ I (only if explicitly stated)
        Multiple lesions:
            • If target/index lesion is named, use its ADC.
            • If not, choose the worst category in descending risk: R > I > NR.
        Context:
            • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections.
            • If DWI/ADC not performed or not characterized, return null.
        Output exactly one of: NR, I, R, or null.
        """
        )
    _field_spec = (Optional[Literal["NR", "I", "R"]], None)
    _field_stub = '"ADC": <NR|I|R or null>'

class LATERALITY:
    _prompt = ("""- Πλάγια εντόπιση ευρημάτων (LATERALITY): Allowed values: UNI | BIL.
        Decision order (apply strictly):
        A) BIL ⇒ if the CURRENT report explicitly localizes FINDINGS on BOTH breasts, or uses a bilateral phrase
            that clearly refers to findings/lesions (not background), e.g.:
            • «αμφοτερόπλευρες κύστεις», «αμφοτερόπλευρες αλλοιώσεις», «bilateral lesions/findings».
            • Left and Right side–specific findings in the same exam.
        B) UNI ⇒ if the CURRENT report localizes ≥1 finding to ONLY ONE breast (left or right) and does not
            localize any finding to the other side (negations on the other side reinforce UNI).
        C) EXCLUSIONS (do NOT count as findings for laterality):
            • BPE/background only («ενίσχυση παρεγχύματος / BPE» Minimal/Mild/Moderate/Marked).
            • Density ACR (A/B/C/D) or symmetry statements without a focal lesion/area.
            • Technical notes, artifacts, clip/scar without active lesion, calcifications alone (unless described as a lesion category).
        D) Conflicts:
            • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections; otherwise prefer ΕΥΡΗΜΑΤΑ/Findings.
            • If multiple lesions exist, decide by union of sides: findings on both ⇒ BIL; only one side ⇒ UNI.
        E) If no FINDINGS are described anywhere in the CURRENT report, return null.
        Output exactly one of: UNI, BIL, or null.
        """
        )
    _field_spec = (Optional[Literal["UNI", "BIL"]], None)
    _field_stub = '"LATERALITY": <UNI|BIL or null>'


