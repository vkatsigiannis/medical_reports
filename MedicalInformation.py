from typing import Optional, Literal
from pydantic import Field

class Birads:
    _prompt = ("- BIRADS category as an integer 0..6. Accept I/II/III/IV/V/VI and map to 1..6.")
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (Arabic numeral in ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        «ΣΥΜΠΕΡΑΣΜΑ: BI-RADS 2. Καλοήθη ευρήματα.»
        Output:
        2

        Example 2 (Roman numeral)
        Text:
        «ΣΥΜΠΕΡΑΣΜΑ: BI-RADS II.»
        Output:
        2

        Example 3 (Subcategory 4a -> 4)
        Text:
        «ΣΥΜΠΕΡΑΣΜΑ: BI-RADS IVa. Συνιστάται βιοψία.»
        Output:
        4

        Example 4 (Higher category)
        Text:
        «ΣΥΜΠΕΡΑΣΜΑ: BI-RADS 5. Υψηλή υποψία κακοήθειας.»
        Output:
        5

        Example 5 (Known malignancy)
        Text:
        «ΣΥΜΠΕΡΑΣΜΑ: BI-RADS 6 (γνωστή κακοήθεια).»
        Output:
        6
    """)
    _field_spec = (Optional[int], Field(None, ge=0, le=6))
    _field_stub = '"BIRADS": <0..6 or null>'


class FamilyHistory:
    _prompt = ("- Ιστορικό Ca (Family / Οικογενειακό): Allowed: Yes / No.\n"
        "Rules:\n"
        "  • Yes only if the report explicitly states the PATIENT has a history of cancer "
        "(e.g., «θετικό (οικογενειακό) ιστορικό καρκίνου …», ««θετικό (οικογενειακό) ιστορικό Ca …», s/p treatment for cancer).\n"
        "  • No only if there is an explicit negation of PERSONAL cancer history "
        "(e.g., «χωρίς/αρνητικό (οικογενειακό) ιστορικό καρκίνου», «δεν αναφέρεται  (οικογενειακό) ιστορικό καρκίνου»).")
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΕΝΔΕΙΞΗ)
        Text:
        «ΕΝΔΕΙΞΗ: ...
                 Αρνητικό οικογενειακό ιστορικό.»
        Output:
        "No"

        Example 2 (in ΕΝΔΕΙΞΗ)
        Text:
        «ΕΝΔΕΙΞΗ: ...
                 Αναφερόμενο αρνητικό οικογενειακό ιστορικό.»
        Output:
        "No"

        Example 3 (in ΕΝΔΕΙΞΗ)
        Text:
        «ΕΝΔΕΙΞΗ: ...
                 Θετικό οικογενειακό ιστορικό (Ca ωοθηκών, θεία από την πλευρά της μητέρας).»
        Output:
        "Yes"

        Example 4 (in ΕΝΔΕΙΞΗ)
        Text:
        «ΕΝΔΕΙΞΗ: ...
                 Θετικό οικογενειακό ιστορικό (μητέρα-Ca μαστού αμφοτεροπλεύρως).»
        Output:
        "Yes"

        Example 5 (in ΕΝΔΕΙΞΗ)
        Text:
        «ΕΝΔΕΙΞΗ: ...
                 Θετικό οικογενειακό ιστορικό (Ca μαστού δεξιά από την πλευρά της μητέρας, Ca ωοθηκών θεία από την πλευρά της μητέρας)»
        Output:
        "No"
    """)
    _field_spec = (Optional[Literal["Yes", "No"]], None)
    _field_stub = '"FamilyHistory": <Yes|No or null>'

class ACR:
    # Breast Density
    _prompt = ("- Πυκνότητα μαστού ACR. Allowed: A / B / C / D ή συνδυασμοί. "
           "Αν υπάρχουν πολλαπλά, επέστρεψέ τα ενωμένα με '-' διατηρώντας τη σειρά (π.χ. C-D).")
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Πυκνοί μαστοί με σημαντική αύξηση του ινώδους και του αδενικού στοιχείου αμφοτερόπλευρα (ACR D).
»
        Output:
        "D"

        Example 2 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Πυκνοί μαστοί με έντονη αύξηση του ινοαδενικού στοιχείου (ACR: D)»
        Output:
        "D"

        Example 3 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Πυκνοί μαστοί με κατά τόπους έντονη αύξηση του ινοαδενικού στοιχείου (ACR C–D).»
        Output:
        "C-D"

        Example 4 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Μαστοί με κατά τόπους έντονη αύξηση των ινοαδενικών στοιχείων (ACR B-C)»
        Output:
        "B-C"

        Example 5 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Λιποβριθείς μαστοί με ήπια αύξηση του ινοαδενικού στοιχείου, με οπισθοθηλαία κυρίως εντόπιση (ACR: A-B).»
        Output:
        "A-B"
    """)
    _field_spec = (Optional[str], None)
    _field_stub = '"ACR": <A|B|C|D or combos like C-D or null>'

class BPE:
    _prompt = ("- Background Parenchymal Enhancement (BPE). Allowed: Minimal, Mild, Moderate, Marked. "
           "Greek: ΜΗΔΑΜΙΝΗ→Minimal, ΗΠΙΑ→Mild, ΜΕΤΡΙΑ→Moderate, ΕΝΤΟΝΗ→Marked.")
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Έντονη ενίσχυση του φυσικού υποστρώματος (marked BPE), βελτιωμένη συγκριτικά με την προηγούμενη Μαγνητική Τομογραφία, κατά τόπους οζώδη και μικροοζώδη μορφολογία.»
        Output:
        "Marked"

        Example 2 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Μηδαμινή ενίσχυση του μαζικού υποστρώματος (minimal BPE).»
        Output:
        "Minimal"

        Example 3 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Ήπια ενίσχυση του μαζικού υποστρώματος (mild BPE), με κατά τόπους οζώδη μορφολογία.»
        Output:
        "Mild"

        Example 4 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Μέτρια ενίσχυση του μαζικού υποστρώματος (moderate BPE).»
        Output:
        "Moderate"
        Output:
        "Yes"

        Example 5 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 (καμία αναφορά σε BPE)
                 ...»
        Output:
        null
    """)
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
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        ΣΥΜΠΕΡΑΣΜΑ: ...
                 - Αλλοίωση στον προδρομικό άξονα της 10ης ώρας του αριστερού μαστού, διαμέτρου 7,5 χιλ., με απεικονιστικά χαρακτηριστικά συμβατά με ινοαδένωμα.»
        Output:
        "Yes"

        Example 2 (in ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        ΣΥΜΠΕΡΑΣΜΑ: ...
                 - Δεν παρατηρούνται περιοχές παθολογικής σκιαγραφικής ενίσχυσης με λοβιακή ή τμηματική κατανομή.»
        Output:
        "No"

        Example 3 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 Χωρίς περιοχές παθολογικής ενίσχυσης από τον έλεγχο των μαστών.
»
        Output:
        "No"

        Example 4 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Στον προβολικό άξονα της 3ης ώρας του αριστερού μαστού και σε επιφανειακή θέση ελέγχεται αλλοίωση με ελαφρώς λοβωτά όρια, διαμέτρου 1,3 εκ.
                 ...»
        Output:
        "Yes"

        Example 5 (in ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        ΣΥΜΠΕΡΑΣΜΑ: ...
                 (καμία αναφορά σε μάζα)
                 ...»
        Output:
        "No"
    """)
    _field_spec = (Optional[Literal["Yes", "No"]])
    _field_stub = '"MASS": <Yes|No>'

    
class massDiameter:
    _prompt = ("""
        - Διάμετρος μάζας (massDiameter): Output = STRING with value+unit, or null.
        Allowed unit formats (output must match exactly one):
        • "<number> mm"
        • "<number> cm"
        where <number> may be integer or decimal (dot or comma allowed in input, but output must use dot).

        Goal (STRICT):
        Extract the primary diameter of a SOLID MASS exactly as stated in the report, preserving the ORIGINAL unit (mm or cm).
        Do NOT convert units. If unclear or not stated, return null.

        Decision order (apply strictly):
        1) Scope:
        This field applies ONLY if a solid mass is present (e.g., «μάζα», «ογκίδιο», «συμπαγής αλλοίωση», «οζώδης αλλοίωση»).
        If the report mentions ONLY NME/μη μαζική ενίσχυση or ONLY cysts/κύστεις without a solid mass → return null.

        2) Evidence priority:
        Prefer «ΣΥΜΠΕΡΑΣΜΑ». If missing/empty, use «ΕΥΡΗΜΑΤΑ / ΠΕΡΙΓΡΑΦΗ».
        Prefer CURRENT exam measurements over prior comparisons (e.g., "σε σχέση με προηγούμενη").

        3) Unit handling (NO conversion):
        Accept only mm/χιλ./χιλιοστά and cm/εκ./εκατοστά.
        Keep the unit as written in the report:
        • If the report states cm/εκ. → output in cm.
        • If the report states mm/χιλ. → output in mm.
        Normalize only the numeric formatting:
        • Convert Greek decimal comma to dot in OUTPUT (7,5 → 7.5).
        Do not change the numeric value due to unit conversion.

        4) Multiple dimensions:
        If dimensions are given as A×B×C (or A x B x C, with any separators like "×", "x", "Χ", "*"):
        • Set diameter = A only (the FIRST number).
        • Preserve the unit as stated for that set of dimensions.
        Examples:
            - "7,5 × 6 × 8 mm" → "7.5 mm"
            - "1,2 x 0,8 cm" → "1.2 cm"

        5) Single dimension:
        If a single measurement is given (e.g., "μάζα 9 mm", "ογκίδιο 1,1 εκ.") → output that value+unit.

        6) Ranges:
        If a range is given (e.g., "7–8 mm", "0,7–0,8 εκ.") → output the UPPER bound with the SAME unit.
        Example: "7–8 mm" → "8 mm"; "0,7–0,8 εκ." → "0.8 cm"

        7) Multiple masses:
        • If a target/index lesion is identified (location, clip, biopsy site, or explicitly prioritized in «ΣΥΜΠΕΡΑΣΜΑ»), use its diameter.
        • Otherwise, select the most suspicious solid mass described in «ΣΥΜΠΕΡΑΣΜΑ».
        • If still multiple, select the largest diameter (based on the extracted A value) BUT keep its original unit.

        8) If dynamic sequence wasn’t performed, or no size is provided for a solid mass → return null.

        Output format (STRICT):
        Return exactly one JSON string like "12 mm" or "1.2 cm", or null.
        No extra keys. No extra text.
        """
        )
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Αλλοίωση στον προδρομικό άξονα της 10ης ώρας του αριστερού μαστού, διαμέτρου 7,5 χιλ., με απεικονιστικά χαρακτηριστικά συμβατά με ινοαδένωμα.»
        Output:
        "7,5 mm"

        Example 2 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Στον προβολικό άξονα της 3ης ώρας του αριστερού μαστού και σε επιφανειακή θέση ελέγχεται αλλοίωση με ελαφρώς λοβωτά όρια, διαμέτρου 1,3 εκ.»
        Output:
        "1,3 cm"

        Example 3 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                Στο κάτω έξω τεταρτημόριο του δεξιού μαστού (7η ώρα) και 6,6 εκ. οπισθοθηλαία παρατηρείται η γνωστή μιτωτική εξεργασία, διαστάσεων 3,1 εκ. x 2,8 εκ. x 2,5 εκ.
        Output:
        "3,1 cm"

        Example 4 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Παρουσία ολιγάριθμων μασχαλιαίων λεμφαδένων άμφω, καλοηθούς μορφολογίας. Παρατηρείται αριστερός μασχαλιαίος λεμφαδένας βραχείας διαμέτρου 9 χιλ., με εστιακή πάχυνση του φλοιού 4 χιλ.»
        Output:
        "9 mm"

        Example 5 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                  Έτερη εστία αυξημένης ενίσχυσης διαμέτρου 8 χιλ. με παρόμοιους αιμοδυναμικούς χαρακτήρες παρατηρείται στον προσθολοϊκό άξονα της 12ης ώρας.»
        Output:
        "8 mm"
    """)
    _field_spec = (Optional[str], None)
    _field_stub = '"massDiameter": <string (mm or cm) or null>'

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
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Στο κέντρο του δεξιού μαστού και 3 εκ. οπισθοθηλαία παρατηρείται ωοειδής αλλοίωση με σαφή όρια διαμέτρου 7,8 χιλ.»
        Output:
        "σαφή"

        Example 2 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Στο κέντρο του δεξιού μαστού και 10 εκ. οπισθοθηλαία παρατηρείται οζώμορφη αλλοίωση, διαμέτρου 7 χιλ.»
        Output:
        "σαφή"

        Example 3 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                παρατηρείται αλλοίωση με ασαφή όρια και ακτινωτές προσεκβολές,»
        Output:
        "ασαφή"

        Example 4 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 • Παρουσία ολιγάριθμων μασχαλιαίων λεμφαδένων άμφω, καλοηθούς μορφολογίας. Παρατηρείται αριστερός μασχαλιαίος λεμφαδένας βραχείας διαμέτρου 9 χιλ., με εστιακή πάχυνση του φλοιού 4 χιλ.»
        Output:
        "ασαφή"

        Example 5 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                • Στον προβολικό άξονα της 3ης ώρας του αριστερού μαστού και σε επιφανειακή θέση ελέγχεται αλλοίωση με ελαφρώς λοβωτά όρια, διαμέτρου 1,3 εκ.»
        Output:
        null
    """)
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
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 παρατηρείται η γνωστή μιτωτική εξεργασία, διαστάσεων 3,1 εκ. x 2,8 εκ. x 2,5 εκ., που παρουσιάζει περιοχές νέκρωσης και περιφερική ανομοιόμορφη ενίσχυση»
        Output:
        "ανομοιογενής"

        Example 2 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 παρατηρείται ωοειδής αλλοίωση με σαφή όρια διαμέτρου 7,8 χιλ. που παρουσιάζει ομοιογενή σκιαγραφική ενίσχυση»
        Output:
        "ομοιογενής"

        Example 3 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                παρατηρείται μαζομορφής αλλοίωση, με ασαφή όρια και ακτινωτές προσεκβολές»
        Output:
        "ανομοιογενής"

        Example 4 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 ελέγχεται αλλοίωση με ελαφρώς λοβωτά όρια, διαμέτρου 1,3 εκ., με ήπια σκιαγραφική ενίσχυση και αιμοδυναμική καμπύλη τύπου I, χωρίς περιορισμό στις εικόνες μοριακής διάχυσης»
        Output:
        null

        Example 5 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                παρατηρείται οζώμορφη αλλοίωση, διαμέτρου 7 χιλ., με παρουσία εσωτερικού μη ενισχυόμενου διαφραγματίου»
        Output:
        null
    """)
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
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        ΣΥΜΠΕΡΑΣΜΑ: ...
                 παρατηρείται περιοχή μη μάζας μορφής παραμαγνητικής ενίσχυσης»
        Output:
        "Yes"

        Example 2 (in ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        ΣΥΜΠΕΡΑΣΜΑ: ...
                 ελέγχεται κυστική αλλοίωση με ασαφώς λοβωτά όρια, χωρίς σκιαγραφική ενίσχυση»
        Output:
        "Yes"

        Example 3 (in ΕΥΡΗΜΑΤΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 παρατηρείται ταινιοειδής περιοχή αυξημένης ενίσχυσης διαμέτρου 11 χιλ.»
        Output:
        "Yes"

        Example 4 (in ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        ΕΥΡΗΜΑΤΑ: ...
                 - Δεν παρατηρούνται περιοχές παθολογικής σκιαγραφικής ενίσχυσης με λοβιακή ή τμηματική κατανομή.»
        Output:
        "No"

        Example 5 (in ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        ΣΥΜΠΕΡΑΣΜΑ: ...
                 χωρίς παθολογική σκιαγραφική ενίσχυση στην περιοχή,
                 ...»
        Output:
        "No"
    """)
    _field_spec = (Optional[Literal["Yes", "No"]])
    _field_stub = '"NME": <Yes|No>'

class nmeDiameter:
    _prompt = ("""
        - Διάμετρος/Έκταση NME (nmeDiameter): Output = STRING with value+unit, or null.
        Allowed unit formats (output must match exactly one):
        • "<number> mm"
        • "<number> cm"
        where <number> may be integer or decimal (dot or comma allowed in input, but output must use dot).

        Goal (STRICT):
        Extract the primary extent/diameter of NME exactly as stated in the report, preserving the ORIGINAL unit (mm or cm).
        Do NOT convert units. If unclear or not stated, return null.

        Decision order (apply strictly):
        1) Scope:
        Applies ONLY if NME is present, e.g.:
        • «μη μαζική ενίσχυση»
        • «μη μαζόμορφη ενίσχυση»
        • «περιοχή μη μαζομορφής σκιαγραφικής ενίσχυσης»
        If the report mentions ONLY mass/μάζα or ONLY cysts/κύστεις without NME → return null.

        2) Evidence priority:
        Prefer «ΣΥΜΠΕΡΑΣΜΑ». If missing/empty, use «ΕΥΡΗΜΑΤΑ / ΠΕΡΙΓΡΑΦΗ».
        Prefer CURRENT exam measurements over prior comparisons.

        3) Unit handling (NO conversion):
        Accept only mm/χιλ./χιλιοστά and cm/εκ./εκατοστά.
        Keep the unit as written in the report:
        • If the report states cm/εκ. → output in cm.
        • If the report states mm/χιλ. → output in mm.
        Normalize only the numeric formatting in OUTPUT:
        • Convert Greek decimal comma to dot (7,5 → 7.5).
        Do not change the numeric value due to unit conversion.

        4) Multiple dimensions:
        If NME extent is given as A×B×C (or A x B x C, with any separators like "×", "x", "Χ", "*"):
        • Set diameter/extent = A only (the FIRST number).
        • Preserve the unit as stated for that set of dimensions.
        Examples:
            - "15 × 8 × 20 mm" → "15 mm"
            - "1,5 x 0,8 cm" → "1.5 cm"

        5) Single dimension:
        If a single measurement is given (e.g., "NME 18 mm", "έκταση 1,2 εκ.") → output that value+unit.

        6) Ranges:
        If a range is given (e.g., "1–1,3 cm", "7–8 χιλ.") → output the UPPER bound with the SAME unit.
        Examples:
            - "1–1,3 cm" → "1.3 cm"
            - "7–8 mm" → "8 mm"

        7) Multiple NME regions:
        • If a target/index region is identified (location, biopsy site, or explicitly prioritized in «ΣΥΜΠΕΡΑΣΜΑ»), use its extent.
        • Otherwise, select the most suspicious NME described in «ΣΥΜΠΕΡΑΣΜΑ».
        • If still multiple, select the largest extent (based on the extracted A value) BUT keep its original unit.

        8) Text without numeric size:
        If only distribution terms are given (e.g., «τμηματική/γραμμική/περιοχική») without numbers → return null.

        Output format (STRICT):
        Return exactly one JSON string like "18 mm" or "1.3 cm", or null.
        No extra keys. No extra text.
        """
        )
    _fewshots = ("""
        FEW-SHOT EXAMPLES

        Example 1 (in ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        (ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ): ...
                 παρατηρείται ταινιοειδής περιοχή αυξημένης ενίσχυσης διαμέτρου 11 χιλ.»
        Output:
        "11 mm"

        Example 2 (in ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        (ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ): ...
                 παρατηρούνται δύο περιοχές μη μαζόμορφης σκιαγραφικής ενίσχυσης διαμέτρου 1,2 εκ.»
        Output:
        "1,2 cm"

        Example 3 (in ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        (ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ): ...
                Στον άξονα της 6ης ώρας του αριστερού μαστού παρατηρείται ταινιοειδούς μορφολογίας μη μαζόμορφη ενίσχυση προσθιοπίσθιας διαμέτρου 7 χιλ.»
        Output:
        "7 mm"

        Example 4 (in ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        (ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ): ...
                 Στην 2η–3η ώρα του αριστερού μαστού και 1,7 εκ. οπισθοθηλαία παρατηρείται εστιακή περιοχή παθολογικής ενίσχυσης, μεγίστης προσθιοπίσθιας διαμέτρου 8 χιλ.»
        Output:
        "8 mm"

        Example 5 (in ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ)
        Text:
        (ΕΥΡΗΜΑΤΑ or ΣΥΜΠΕΡΑΣΜΑ): ...
                  - Παρατηρούνται στικτές εστίες ενίσχυσης, διαμέτρου ολίγων χιλιοστών, σε αμφότερους τους μαστούς, εύρημα που συνήθως περισσότερο υπέρ εστιών αδένωσης.»
        Output:
        null
    """)
    _field_spec = (Optional[str], None)
    _field_stub = '"nmeDiameter": <string (mm or cm) or null>'

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
    _field_spec = (Literal["Yes", "No"])
    # _field_spec = (Optional[Literal["Yes", "No"]], None)
    _field_stub = '"NonEnhancingFindings": <Yes|No>'


# class NonEnhancingFindings:
#     _prompt = (
#     """
# You are an information extraction system for breast MRI reports (Greek).
# Return ONLY one token: "Yes" or "No". No extra text.

# Field: NonEnhancingFindings (κύστεις / κυστικές αλλοιώσεις)

# STRICT RULE:
# Return "Yes" ONLY if the CURRENT exam text explicitly mentions cysts/cystic lesions.
# If cyst terms are not explicitly present -> return "No". Do not guess.

# EVIDENCE PRIORITY:
# 1) Use «ΣΥΜΠΕΡΑΣΜΑ» first.
# 2) If missing/empty, use «ΕΥΡΗΜΑΤΑ / ΠΕΡΙΓΡΑΦΗ».
# Ignore «ΙΣΤΟΡΙΚΟ / ΕΝΔΕΙΞΗ» unless it describes a CURRENT imaging finding.

# YES triggers (explicit cyst terminology):
# - «κύστη», «κύστεις»
# - «κυστική αλλοίωση», «κυστικές αλλοιώσεις»
# - «κυστικός σχηματισμός»
# - «απλή κύστη», «απλές κύστεις», «τυπικές κύστεις»
# Still "Yes" if described as: «μικρές/λίγες/διάσπαρτες/αμφοτερόπλευρες».

# NO triggers:
# - Explicit negation of cysts AND no cyst term anywhere else:
#   «δεν αναδεικνύονται/παρατηρούνται κύστεις», «χωρίς κύστεις», «ουδεμία κύστη/κυστική αλλοίωση».

# IMPORTANT Greek report pattern:
# If ANY cyst term appears anywhere, do NOT change to "No" because of later phrases like
# «κατά τα λοιπά», «λοιπός έλεγχος» (these mean "otherwise unremarkable").

# DO NOT count as cysts:
# - «εκτασία/διάταση πόρων» alone
# - «σερώμα/αιμάτωμα/συλλογή» unless explicitly called «κύστη/κυστική αλλοίωση»
# - Only MASS/NME/BPE/ACR statements without cyst terms
# """
#         )
#     _field_spec = (Optional[Literal["Yes", "No"]], None)
#     _field_stub = '"NonEnhancingFindings": <Yes|No>'


# class CurveMorphology:
#     _prompt = ("""- Αιμοδυναμική καμπύλη (CurveMorphology): Allowed values: 1 / 2 / 3.
#         Decision order (apply strictly):
#         1) Return 1 if the text explicitly states Type I (π.χ. «αιμοδυναμική καμπύλη τύπου I/Ι») or synonyms:
#             persistent/continuous increase, no washout, steadily increasing curve.
#         2) Return 2 if Type II (π.χ. «τύπου II/ΙΙ») or synonyms:
#             plateau/stabilization after initial rise.
#         3) Return 3 if Type III (π.χ. «τύπου III/ΙΙΙ») or synonyms:
#             washout/decay after early enhancement.
#         Ambiguity and conflicts:
#         • Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion; otherwise use the curve tied to the target/index lesion.
#         • If multiple lesions have different curves and no target is named, choose the most suspicious (3 > 2 > 1).
#         • If dynamic sequence not performed or curve not characterized, return null.
#         Output exactly one of: 1, 2, 3, or null.
#         """
#         )
#     _field_spec = (Optional[Literal[1, 2, 3]], None)
#     _field_stub = '"CurveMorphology": <1|2|3 or null>'

class CurveMorphology:
    _prompt = ("""- Αιμοδυναμική καμπύλη (CurveMorphology): Allowed values: "1" | "2" | "3" | "1,2" | "1,3" | "2,3".

        Decision order (apply strictly):
        A) Detect explicit curve type mentions (ONLY when explicitly stated):
        - Type 1 if text states: «αιμοδυναμική καμπύλη τύπου I/Ι», «τύπου 1», “Type I”, “type 1”
            or synonyms tied to a lesion: persistent / continuous increase / steadily increasing / no washout.
        - Type 2 if text states: «τύπου II/ΙΙ», «τύπου 2», “Type II”, “type 2”
            or synonyms: plateau / stabilization after initial rise.
        - Type 3 if text states: «τύπου III/ΙΙΙ», «τύπου 3», “Type III”, “type 3”
            or synonyms: washout / decay after early enhancement.

        B) Multi-lesion rule (composite outputs):
        - If the CURRENT report explicitly states more than one different curve type for different lesions/areas,
            output the UNIQUE set of types found, sorted ascending, joined with a comma:
            {1 and 2} -> 1,2
            {1 and 3} -> 1,3
            {2 and 3} -> 2,3

        C) Target/index preference:
        - Prefer ΣΥΜΠΕΡΑΣΜΑ/Conclusion over other sections.
        - If ΣΥΜΠΕΡΑΣΜΑ specifies a curve for the key finding, use that set from ΣΥΜΠΕΡΑΣΜΑ.
        - Otherwise, use curves tied to described lesions/areas in the current exam.

        D) Exclusions / non-evidence:
        - If the report says only “άτυπη/ύποπτη αιμοδυναμική συμπεριφορά” WITHOUT specifying type I/II/III
            or without kinetic synonyms above -> return null.
        - If dynamic contrast sequence not performed / not described -> null.

        Output exactly ONE of: "1", "2", "3", "1,2", "1,3", "2,3", or null.
    """)

    _field_spec = (Optional[Literal["1", "2", "3", "1,2", "1,3", "2,3"]], None)
    _field_stub = '"CurveMorphology": <"1"|"2"|"3"|"1,2"|"1,3"|"2,3" or null>'

# ADC → numeric value in ×10⁻³ mm²/s (float) or null
class ADC:
    _prompt = (
        """- Δείκτης διάχυσης νερού, ADC (ADC): Output = number in ×10⁻³ mm²/s, or null.
        Parsing/normalization (apply strictly):
        • Accept: "ADC 1,6 x10⁻³ mm²/s", "ADC 1.6×10^-3", "ADC=0.0016 mm²/s", "ADC 900×10⁻⁶ mm²/s".

        Multiple values:
        • If a target/index lesion is identified, use its ADC; otherwise return the lowest (worst) ADC reported.

        Qualitative-only text:
        • If only qualitative wording exists (e.g., "χωρίς περιορισμό διάχυσης", "ελεύθερη/περιορισμένη διάχυση") with NO number → return qualitative wording.

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
    _prompt = ("""- Πλάγια εντόπιση ευρημάτων (LATERALITY): Allowed values: UNILATERAL | BILATERAL | null.

        Ορισμοί:
        - BILATERAL = αμφοτερόπλευρα = ευρήματα και από τους δύο μαστούς (αριστερό + δεξιό).
        - UNILATERAL = μονόπλευρα = ευρήματα από τον έναν μαστό μόνο (είτε αριστερό είτε δεξιό).

        Σκοπός:
        Να βρεθεί η πλάγια εντόπιση των ΠΡΑΓΜΑΤΙΚΩΝ ευρημάτων/βλαβών της ΤΡΕΧΟΥΣΑΣ εξέτασης (όχι background).

        Τι μετράει ως “εύρημα/βλάβη”:
        - MASS: «μάζα», «συμπαγής αλλοίωση», «σχηματισμός», «ενισχυόμενη βλάβη», «χωροκατακτητική εξεργασία»,
        ή «αλλοίωση» όταν είναι εστιακή και έχει μέγεθος/μορφολογία (π.χ. «αλλοίωση διαμέτρου …»).
        - NME: «μη μαζόμορφη ενίσχυση», «περιοχή μη μαζομορφής σκιαγραφικής ενίσχυσης».
        - Κύστεις/μη ενισχυόμενα: «κύστη», «κύστεις», «κυστικές αλλοιώσεις», «πιθανή κύστη».
        - Οποιαδήποτε ρητά εντοπισμένη εστία/περιοχή παθολογίας σε αριστερό ή δεξιό μαστό.

        Decision order (apply strictly):
        A) Εντόπισε πλευρές με ΕΥΡΗΜΑΤΑ στην τρέχουσα εξέταση:
        - LEFT evidence: «αριστερός μαστός/αριστερού μαστού», “left breast”, “L”.
        - RIGHT evidence: «δεξιός μαστός/δεξιού μαστού», “right breast”, “R”.
        - BILATERAL wording: «αμφοτερόπλευρα», «και στους δύο μαστούς», «αμφότερους τους μαστούς»

        B) Απόφαση:
        - BILATERAL αν υπάρχει ≥1 εύρημα στον αριστερό ΚΑΙ ≥1 εύρημα στον δεξιό μαστό,
            ή υπάρχει ρητή φράση “αμφοτερόπλευρα” που αφορά ευρήματα.
        - UNILATERAL αν υπάρχει εύρημα μόνο στη μία πλευρά και καμία βλάβη/εύρημα δεν εντοπίζεται στην άλλη πλευρά
            (είτε επειδή δεν αναφέρεται τίποτα, είτε υπάρχει ρητή άρνηση).

        C) “Κατά τα λοιπά / από τον λοιπό έλεγχο”:
        - Αν υπάρχει άρνηση τύπου «Δεν παρατηρούνται … κατά τα λοιπά / από τον λοιπό έλεγχο …»,
            θεώρησε ότι “ο υπόλοιπος έλεγχος είναι αρνητικός”, όχι ότι όλα είναι αρνητικά.
            Κράτησε τη laterality από τα θετικά ευρήματα που περιγράφονται αλλού.

        D) Προτεραιότητα ενότητας:
        - ΣΥΜΠΕΡΑΣΜΑ/Conclusion > ΕΥΡΗΜΑΤΑ/Findings > λοιπά.

        E) Αν δεν υπάρχει ΚΑΝΕΝΑ εύρημα/βλάβη στην τρέχουσα εξέταση (μόνο background/τεχνικά) → null.

        Output exactly one of: UNILATERAL, BILATERAL, or null.
        """)
    _field_spec = (Optional[Literal["UNILATERAL", "BILATERAL"]], None)
    _field_stub = '"LATERALITY": <UNILATERAL|BILATERAL or null>'

