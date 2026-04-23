# ============================================================
#  Minimal changes to report_extract_v3.py to enable regex mode
#  Only the lines that differ from the original are shown.
# ============================================================

# 1. Import at the top (add alongside the existing imports):
from RegexExtractor import RegexExtractor

# 2. Toggle flag (add near the top of __main__):
use_regex = True   # ← set False to use the LLM extractor as before

# 3. Replace the extractor construction block:
#    Original:  re = ReportExtractor(MODEL_ID)
#    New:
if use_regex:
    re = RegexExtractor()
else:
    re = ReportExtractor(MODEL_ID)   # loads GPU model only when needed

# 4. In the per-report loop, pass use_regex= to extract_structured_data:
#    Original:  re.extract_structured_data(Patient=patient, keys=group, include_fewshots=False)
#    New:
for group in groups:
    re.extract_structured_data(Patient=patient, keys=group,
                                include_fewshots=False,
                                use_regex=use_regex)

# ── Complete minimal diff shown below for clarity ──────────────────────────

DIFF = """
--- report_extract_v3.py (original)
+++ report_extract_v3.py (patched)

+from RegexExtractor import RegexExtractor

 if __name__ == "__main__":
+    use_regex = True   # set False to use LLM

-    re = ReportExtractor(MODEL_ID)
+    if use_regex:
+        re = RegexExtractor()
+    else:
+        re = ReportExtractor(MODEL_ID)

     for group in groups:
-        re.extract_structured_data(Patient=patient, keys=group, include_fewshots=False)
+        re.extract_structured_data(Patient=patient, keys=group,
+                                    include_fewshots=False,
+                                    use_regex=use_regex)
"""
print(DIFF)
