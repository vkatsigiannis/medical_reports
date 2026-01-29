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

        A) POSITIVE ⇒ Yes if the text describes a focal SOLID lesion. Count as mass when ANY of:
        • «μάζα», «σχηματισμός», «βλάβη/ενισχυόμενη βλάβη», «συμπαγής αλλοίωση», «συμπαγής ενισχυόμενη αλλοίωση»,
            «χωροκατακτητική εξεργασία», English: mass / solid mass / enhancing mass / space-occupying lesion.
        • «αλλοίωση» used as a focal lesion with mass-like cues:
            - has size/diameter (π.χ. «αλλοίωση διαμέτρου …»), OR
            - has mass morphology (σαφή/ασαφή ή λοβωτά/ωοειδή όρια, οζώδης/οζίδιο), OR
            - is tied to solid pathology (π.χ. «ινοαδένωμα», «κακοήθεια»).
            Examples that COUNT: «αλλοίωση διαμέτρου 7 χιλ.», «ωοειδής αλλοίωση 1,3 εκ.», «αλλοίωση … συμβατή με ινοαδένωμα».
        • English/Greek mixed phrasing like “solid/enhancing lesion” is also Yes.

        B) NEGATIVE ⇒ No only with explicit negation of mass:
        • «δεν παρατηρείται/δεν αναδεικνύεται μάζα/συμπαγής αλλοίωση/σχηματισμός/βλάβη», English: “no (solid) mass is seen”.

        C) EXCLUSIONS (do NOT count by themselves):
        • «μη μαζόμορφη ενίσχυση / NME» without solid mass wording.
        • Κύστη/κύστεις/κυστικές αλλοιώσεις without solid mass wording.
        • BPE/background only («ενίσχυση παρεγχύματος», BPE Minimal/Mild/Moderate/Marked).
        • Μόνο αποτιτανώσεις, clip/scar, artifact, duct ectasia, ή καθαρά τεχνικές αναφορές.

        D) Conflicts: Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections.

        E) Ambiguity rule: If the ONLY evidence is the bare word «αλλοίωση» with NO size/morphology/solid term and it could be NME,
        return No. Otherwise treat focal, sized ή μορφολογικά περιγεγραμμένη «αλλοίωση» as mass.

        Output exactly one of: "Yes" or "No"."""
        )

    _field_spec = (Optional[Literal["Yes", "No"]])
    _field_stub = '"MASS": <Yes|No>'

class massDiameter:
    _prompt = ("""- Διάμετρος μάζας (massDiameter): Output = number in millimeters, or null.
        Decision order (apply strictly):
        1) Scope: This field applies ONLY to solid masses (e.g., «μάζα», «συμπαγής αλλοίωση», solid/enhancing mass).
            If the report mentions ONLY NME or ONLY cysts without a solid mass → return null.
        2) Unit handling:
            • Accept mm/χιλ. and cm/εκ. Normalize to mm (1.0 cm = 10.0 mm). Handle Greek decimal comma (7,5 → 7.5).
        3) Multiple dimensions (e.g., 7.5 × 6 × 8 mm):
            • Return the LARGEST single dimension in mm.
        4) Ranges (e.g., 7–8 mm or 7–8 χιλ.):
            • Return the UPPER bound in mm.
        5) Multiple masses:
            • If a target/index lesion is identified (e.g., by location/clip/biopsy/ΣΥΜΠΕΡΑΣΜΑ), use its diameter.
            • Otherwise, return the LARGEST suspicious solid mass diameter.
        6) Historical context:
            • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections; otherwise prefer CURRENT exam over prior.
        7) If the dynamic sequence wasn’t performed or the mass is not dimensioned, return null.
        Output exactly one JSON number (millimeters) or null (no quotes).
    """
        )
    _field_spec = (Optional[float], None)
    _field_stub = '"massDiameter": <number (mm) or null>'

class massMargins:
    _prompt = ("""- Όρια μάζας (massMargins): Allowed values: σαφή | ασαφή | null.

    Εφαρμογή ΜΟΝΟ σε MASS (συμπαγή μάζα). Αν δεν υπάρχει μάζα ή δεν περιγράφονται όρια → null.

    Κανόνες (εφάρμοσε με αυτή τη σειρά):
    1) σαφή ⇒ όταν τα όρια της μάζας δηλώνονται καθαρά, π.χ.:
        «σαφή όρια», «καλά περιγεγραμμένη», «well-circumscribed/clear margins».
    2) ασαφή ⇒ όταν τα όρια δηλώνονται ακαθόριστα/δυσδιάκριτα, π.χ.:
        «ασαφή όρια», «ακαθόριστα/δυσδιάκριτα/θολά όρια», «ill-defined/indistinct margins».
    3) Αγνόησε χαρακτηρισμούς που δεν δηλώνουν καθαρά σαφή/ασαφή (π.χ. «λοβωτά», «ωοειδής») αν δεν συνοδεύονται
        από ρητή δήλωση για σαφή/ασαφή όρια.
    4) Πολλαπλές μάζες: αν υπάρχει target/index, χρησιμοποίησε τα δικά της όρια· αλλιώς επί διαφωνίας επέλεξε «ασαφή».
    5) Προτεραιότητα: ΣΥΜΠΕΡΑΣΜΑ/Conclusion > ΕΥΡΗΜΑΤΑ/Findings.

    Output exactly one of: «σαφή», «ασαφή», ή null."""
        )

    _field_spec = (Optional[Literal["σαφή", "ασαφή"]], None)
    _field_stub = '"massMargins": <σαφή|ασαφή or null>'

class massInternalEnhancement:
    _prompt = (
        """- Εσωτερικό πρότυπο ενίσχυσης μάζας (massInternalEnhancement): Allowed values: ομοιογενής | ανομοιογενής | null.

        Εφαρμογή ΜΟΝΟ σε MASS (συμπαγή μάζα). Αν δεν υπάρχει μάζα ή δεν περιγράφεται εσωτερικό πρότυπο ενίσχυσης → null.

        Κανόνες (εφάρμοσε με αυτή τη σειρά):
        1) ομοιογενής ⇒ όταν δηλώνεται ρητά ομοιογενής/ομοιόμορφη ενίσχυση (Greek/English: «ομοιογενής», homogeneous, uniform).
        2) ανομοιογενής ⇒ όταν δηλώνεται ρητά ανομοιογενής/ετερογενής ενίσχυση (Greek/English: «ανομοιογενής», «ετερογενής», heterogeneous).
        3) Αγνόησε μοτίβα που δεν περιγράφουν εσωτερική ομοιογένεια/ανομοιογένεια (π.χ. «περιφερική/δακτυλιοειδής», NME terms).
        4) Πολλαπλές μάζες: αν υπάρχει target/index, χρησιμοποίησε το πρότυπο της· αλλιώς, επί διαφωνίας, επίλεξε «ανομοιογενής».
        5) Προτεραιότητα: ΣΥΜΠΕΡΑΣΜΑ/Conclusion > ΕΥΡΗΜΑΤΑ/Findings.

        Output exactly ένα από: «ομοιογενής», «ανομοιογενής», ή null.
        """
    )
    _field_spec = (Optional[Literal["ομοιογενής", "ανομοιογενής"]], None)
    _field_stub = '"massInternalEnhancement": <ομοιογενής|ανομοιογενής or null>'



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
    # _field_spec = (Optional[Literal["Yes", "No"]], None)
    _field_spec = (Optional[Literal["Yes", "No"]])
    _field_stub = '"NME": <Yes|No>'

class nmeDiameter:
    _prompt = ("""- Διάμετρος/Έκταση NME (nmeDiameter): Output = number in millimeters, or null.
        Decision order (apply strictly):
        1) Scope: Applies ONLY to non-mass enhancement (NME), e.g. «μη μαζόμορφη ενίσχυση», 
            «περιοχή μη μαζομορφής σκιαγραφικής ενίσχυσης». If the report mentions ONLY mass or ONLY cysts → null.
        2) Units:
            • Accept mm/χιλ. and cm/εκ. Normalize to mm (1.0 cm = 10.0 mm).
            • Handle Greek decimal comma (π.χ. 7,5 → 7.5).
        3) Multiple dimensions (e.g., 15 × 8 × 20 mm):
            • Return the LARGEST single dimension in mm.
        4) Ranges (e.g., 1–1,3 cm):
            • Return the UPPER bound in mm.
        5) Multiple NME regions:
            • If a target/index region is identified (by location/biopsy/ΣΥΜΠΕΡΑΣΜΑ), use its size.
            • Otherwise, return the LARGEST NME extent.
        6) Text without a numeric size (e.g., only “segmental/linear/regional” distribution):
            • Return null.
        7) Historical context:
            • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections; otherwise prefer CURRENT exam over prior.

        Output exactly one JSON number (millimeters) or null (no quotes).
    """
        )
    _field_spec = (Optional[float], None)
    _field_stub = '"nmeDiameter": <number (mm) or null>'

class nmeMargins:
    _prompt = (
        """- Όρια NME (nmeMargins): Allowed values: σαφή | ασαφή | null.

        Εφαρμογή ΜΟΝΟ σε NME (μη μαζόμορφη ενίσχυση). Αν δεν υπάρχει NME ή δεν περιγράφονται όρια → null.

        Κανόνες (εφάρμοσε με αυτή τη σειρά):
        1) σαφή ⇒ όταν τα όρια της περιοχής NME δηλώνονται καθαρά, π.χ.:
            «σαφή όρια», «καλά περιγεγραμμένη περιοχή», English: well-defined/clear/distinct margins.
        2) ασαφή ⇒ όταν τα όρια δηλώνονται ακαθόριστα/δυσδιάκριτα, π.χ.:
            «ασαφή/ακαθόριστα/δυσδιάκριτα/θολά όρια», English: ill-defined/indistinct/poorly marginated.
        3) ΜΗ χαρακτηριστικά ορίων (μη τα χρησιμοποιείς μόνοι τους): «γραμμοειδής/τμηματική/περιοχική/περιφερική κατανομή»
            ή περιγραφές μοτίβου ενίσχυσης χωρίς σαφή αναφορά σε όρια.
        4) Πολλαπλές NME περιοχές: αν υπάρχει target/index, χρησιμοποίησε τα δικά της όρια· αλλιώς, επί διαφωνίας, επίλεξε «ασαφή».
        5) Προτεραιότητα: ΣΥΜΠΕΡΑΣΜΑ/Conclusion > ΕΥΡΗΜΑΤΑ/Findings.

        Output exactly ένα από: «σαφή», «ασαφή», ή null.
        """
    )
    _field_spec = (Optional[Literal["σαφή", "ασαφή"]], None)
    _field_stub = '"nmeMargins": <σαφή|ασαφή or null>'

class nmeInternalEnhancement:
    _prompt = (
        """- Εσωτερικό πρότυπο ενίσχυσης NME (nmeInternalEnhancement): Allowed values: ομοιογενής | ανομοιογενής | null.

        Εφαρμογή ΜΟΝΟ σε NME (μη μαζόμορφη ενίσχυση). Αν δεν υπάρχει NME ή δεν περιγράφεται εσωτερικό πρότυπο → null.

        Κανόνες (εφάρμοσε με αυτή τη σειρά):
        1) ομοιογενής ⇒ ρητή αναφορά σε ομοιογενή/ομοιόμορφη ενίσχυση (homogeneous/uniform).
        2) ανομοιογενής ⇒ ρητή αναφορά σε ανομοιογενή/ετερογενή ενίσχυση (heterogeneous).
        3) Αγνόησε όρους ΚΑΤΑΝΟΜΗΣ (γραμμοειδής/τμηματική/περιοχική/περιφερική) ή «clumped/clustered ring»,
            εκτός αν συνοδεύονται από ρητή δήλωση ομοιογένειας/ανομοιογένειας.
        4) Πολλαπλές NME περιοχές: αν υπάρχει target/index, χρησιμοποίησε αυτήν· αλλιώς, επί διαφωνίας, επίλεξε «ανομοιογενής».
        5) Προτεραιότητα: ΣΥΜΠΕΡΑΣΜΑ/Conclusion > ΕΥΡΗΜΑΤΑ/Findings.

        Output exactly ένα από: «ομοιογενής», «ανομοιογενής», ή null.
        """
    )
    _field_spec = (Optional[Literal["ομοιογενής", "ανομοιογενής"]], None)
    _field_stub = '"nmeInternalEnhancement": <ομοιογενής|ανομοιογενής or null>'



class NonEnhancingFindings:
    _prompt = (
        """- Μη ενισχυόμενα ευρήματα = κύστεις (NonEnhancingFindings): Allowed values: Yes / No.

    Decision order (apply strictly):
    A) POSITIVE ⇒ Yes if the CURRENT report states the presence of cysts / cystic lesions, e.g.:
    • «κύστη», «κύστεις», «κυστική αλλοίωση/ες», «κυστικός/ή/ό», English: “cyst(s)”, “simple cyst”, “cystic lesion”.
    • Treat simple/τυπικές κύστεις as non-enhancing even if “μη ενισχυόμενη” is not written.
    • If there is a negation FOLLOWED BY a remainder/except clause for the rest of the exam (π.χ. «… από τον λοιπό έλεγχο»),
        treat as Yes (there is a described cyst, the rest is negative).

    B) NEGATIVE ⇒ No only if there is an explicit plain negation without remainder clause, e.g.:
    • «Δεν παρατηρούνται/αναδεικνύονται κύστεις/κυστικές αλλοιώσεις», English: “no cysts”.
    • Or the report lists only enhancing findings (mass/NME) and nowhere mentions cysts.



    • Prefer ΣΥΜΠΕΡΑΣΜΑ if τμήματα διαφωνούν. Προτεραιότητα στην τρέχουσα εξέταση.
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


# ADC → numeric value in ×10⁻³ mm²/s (float) or null
class ADC:
    _prompt = (
        """- Δείκτης διάχυσης νερού, ADC (ADC): Output = number in ×10⁻³ mm²/s, or null.
        Parsing/normalization (apply strictly):
        • Accept: "ADC 1,6 x10⁻³ mm²/s", "ADC 1.6×10^-3", "ADC=0.0016 mm²/s", "ADC 900×10⁻⁶ mm²/s".
        • Normalize Greek comma to dot.
        • If value is given with ×10⁻³ mm²/s → return the coefficient (e.g., 1.6).
        • If value is given in mm²/s with NO exponent → multiply by 1000 (e.g., 0.0016 → 1.6).
        • If value is given in ×10⁻⁶ mm²/s → divide by 1000 (e.g., 900×10⁻⁶ → 0.9).

        Multiple values:
        • If a target/index lesion is identified, use its ADC; otherwise return the lowest (worst) ADC reported.

        Qualitative-only text:
        • If only qualitative wording exists (e.g., "χωρίς περιορισμό διάχυσης", "ελεύθερη/περιορισμένη διάχυση") with NO number → return null.

        Context:
        • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections. If DWI/ADC not performed → null.

        Output ONLY a JSON number (no units) or null.
"""
    )
    _field_spec = (Optional[float], None)
    _field_stub = '"ADC": <number (×10⁻³ mm²/s) or null>'



# class ADC:
#     _prompt = ("""- Δείκτης διάχυσης νερού, ADC (ADC): Allowed values: NR | I | R.
#         Thresholds (use numeric ADC when present; normalize 1,2 ↔ 1.2):
#             • NON RESTRICTED (NR)  => ADC ≥ 1.4 ×10⁻³ mm²/s
#             • INTERMEDIATE (I)     => 1.0 < ADC < 1.4 ×10⁻³ mm²/s
#             • RESTRICTION (R)      => ADC ≤ 1.0 ×10⁻³ mm²/s
#         Qualitative-only cues (when no number is given):
#             • «χωρίς περιορισμό διάχυσης», «ελεύθερη διάχυση»  ⇒ NR
#             • «με περιορισμό διάχυσης», «περιορισμένη διάχυση» ⇒ R
#             • «ενδιάμεση/οριακή διάχυση» ⇒ I (only if explicitly stated)
#         Multiple lesions:
#             • If target/index lesion is named, use its ADC.
#             • If not, choose the worst category in descending risk: R > I > NR.
#         Context:
#             • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections.
#             • If DWI/ADC not performed or not characterized, return null.
#         Output exactly one of: NR, I, R, or null.
#         """
#         )
#     _field_spec = (Optional[Literal["NR", "I", "R"]], None)
#     _field_stub = '"ADC": <NR|I|R or null>'

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


