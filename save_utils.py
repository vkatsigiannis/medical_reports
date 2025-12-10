# -*- coding: utf-8 -*-
import os
import json
import csv
import xml.etree.ElementTree as ET
from typing import Dict, Any


import os, csv

def _read_csv_header(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            r = csv.reader(f)
            return next(r, None)
    except Exception:
        return None

def _migrate_csv_add_patid(path: str) -> bool:
    """
    If an existing CSV lacks 'patID' in its header, rewrite it so the header is:
      ['patID', <old headers...>]
    Older rows get empty patID.
    """
    header = _read_csv_header(path)
    if not header or "patID" in header:
        return False

    new_fieldnames = ["patID"] + [h for h in header if h != "patID"]

    # read all rows
    with open(path, "r", encoding="utf-8") as src:
        reader = csv.DictReader(src)
        rows = list(reader)

    # write temp with BOM so Excel handles Greek
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=new_fieldnames)
        writer.writeheader()
        for r in rows:
            new_row = {"patID": ""}
            for h in header:
                new_row[h] = r.get(h, "")
            writer.writerow(new_row)

    os.replace(tmp, path)
    return True

def save_to_csv(pat_id: str, data: dict, csv_path: str = "reports_extracted.csv") -> None:
    """
    Append one row to CSV with patID first.
    - If file doesn't exist: create with header ['patID'] + data keys (in their current order), BOM for Excel.
    - If file exists: reuse its header; if it lacks 'patID', auto-migrate once.
    - Unknown keys are ignored to keep schema stable.
    """
    file_exists = os.path.exists(csv_path)
    header = _read_csv_header(csv_path) if file_exists else None

    if header and "patID" not in header:
        _migrate_csv_add_patid(csv_path)
        header = _read_csv_header(csv_path)

    if header:
        fieldnames = header
        mode, encoding = "a", "utf-8"
    else:
        fieldnames = ["patID"] + list(data.keys())
        mode, encoding = "w", "utf-8-sig"  # BOM on first write

    # Build row aligned to fieldnames only
    row = {k: "" for k in fieldnames}
    if "patID" in fieldnames:
        row["patID"] = pat_id
    for k in fieldnames:
        if k == "patID":
            continue
        if k in data:
            v = data[k]
            row[k] = "" if v is None else v

    with open(csv_path, mode, encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerow(row)



def save_to_json(pat_id: str, data: Dict[str, Any], json_path: str = "reports_extracted.json") -> None:
    """
    Nested JSON of form:
    {
      "<patID>": { ...features... },
      ...
    }
    Merges if the file exists.
    """
    payload = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

    payload[pat_id] = data

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_to_xml(pat_id: str, data: Dict[str, Any], xml_path: str = "reports_extracted.xml") -> None:
    """
    XML structure:
      <reports>
        <patient id="pat0002">
          <birads>3</birads>
          <exam_date>2025-07-24</exam_date>
          ...
        </patient>
      </reports>

    - Writes/merges per patID.
    - Greek preserved via UTF-8.
    - Element order follows sorted(data.keys()) for determinism.
    """
    # Load or create root
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            if root.tag != "reports":
                root = ET.Element("reports")
                tree = ET.ElementTree(root)
        except Exception:
            root = ET.Element("reports")
            tree = ET.ElementTree(root)
    else:
        root = ET.Element("reports")
        tree = ET.ElementTree(root)

    # Replace existing patient node if present
    existing = None
    for p in root.findall("patient"):
        if p.get("id") == pat_id:
            existing = p
            break
    if existing is not None:
        root.remove(existing)

    # Create patient node
    patient_el = ET.SubElement(root, "patient", id=pat_id)

    # Stable order
    for k in sorted(data.keys()):
        el = ET.SubElement(patient_el, k)
        v = data.get(k, None)
        el.text = "" if v is None else str(v)

    # Pretty print (3.9+)
    try:
        ET.indent(tree, space="  ")
    except Exception:
        pass

    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
