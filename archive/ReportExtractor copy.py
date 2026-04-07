from typing import Optional, Literal
from pydantic import Field, create_model

import os, re, json, outlines, torch, unicodedata
from pathlib import Path

from datetime import datetime

from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils.logging import set_verbosity_error

import lib

os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"
os.environ["PYTORCH_TRITON_DISABLE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / ".hf_cache"
CACHE_DIR.mkdir(exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)

os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

set_verbosity_error()
assert torch.cuda.is_available(), "CUDA GPU not found."

class ReportExtractor:
    def __init__(self, MODEL_ID, keys: list[str]):
        """
        Initializes the ReportExtractor with a list of keys.
        Args:
            keys (list[str]): A list of string keys used to configure field extraction.
        Attributes:
            keys (list[str]): Stores the provided keys.
            FIELDS_SPEC (dict): Specification for fields, including type and validation rules.
            _PROMPT_FIELD_RULES (dict): Mapping of keys to their corresponding prompt rules, 
                constructed by merging prompt rules from classes obtained via lib.get_class_by_key.
        """
        hf_model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch.float16,
            cache_dir=str(CACHE_DIR),
            trust_remote_code=True,
            device_map="auto",
            temperature=0.0,
        )
        self.hf_tok = AutoTokenizer.from_pretrained(MODEL_ID,
                                            use_fast=False,
                                            cache_dir=str(CACHE_DIR),
                                            trust_remote_code=True)
        self.model = outlines.from_transformers(hf_model, self.hf_tok)
        print("Model loaded:", MODEL_ID)

        self.keys = keys

        self.FIELDS_SPEC = {
            **{k: lib.get_class_by_key(k)._field_spec for k in self.keys},
        }
        
        self._PROMPT_FIELD_RULES = {
            **{k: lib.get_class_by_key(k)._prompt for k in self.keys},
            # "birads": Birads().prompt,
        }

    def build_prompt(self, report: str, prompt_keys: list[str]) -> str:
        lines = [
            "Task: Read the medical report (may be in Greek) and extract ONLY the following if present:"
            # "Task: Read the breast MRI report (Greek/English) and extract ONLY the requested fields.",
            # "Global rules:",
            # "- Output JSON only. No prose.",
            # "- Return null unless there is an explicit cue in the text. Do not infer.",
            # "- Follow each field’s rule exactly."
            ]
        for k in prompt_keys:
            lines.append(self._PROMPT_FIELD_RULES[k])
        fields_stub = []
        for k in self.keys:
            fields_stub = [lib.get_class_by_key(k)._field_stub for k in self.keys]

        lines += [
            "Output ONLY JSON:",
            "{ " + ", ".join(fields_stub) + " }",
            "If an item is missing, return null. No extra keys.\n",
            f'Report:\n"""\n{report}\n"""\nJSON:'
        ]
        return "\n".join(lines)

    def apply_chat_template(self, text: str) -> str:
        if hasattr(self.hf_tok, "apply_chat_template"):
            return self.hf_tok.apply_chat_template(
                [{"role": "user", "content": text}],
                tokenize=False,
                add_generation_prompt=True,
            )
        return text

    def make_model(self):
        fields = {k: self.FIELDS_SPEC[k] for k in self.keys}
        return create_model("ExtractSelected", **fields)

    def extract_structured_data(self, report_text: str) -> dict:
        # --- main LLM pass only on requested keys ---
        DynModel = self.make_model()
        main_prompt = self.apply_chat_template(self.build_prompt(report_text, self.keys))
        out = self.model(main_prompt, DynModel, max_new_tokens=320, do_sample=False)
        obj = DynModel.model_validate_json(out).model_dump()

        return {k: obj.get(k) for k in self.keys}