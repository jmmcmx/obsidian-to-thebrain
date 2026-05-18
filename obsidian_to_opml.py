#!/usr/bin/env python3
"""
Obsidian Vault → OPML + CSV para TheBrain 15
Genera dos archivos:
  1. CerebroDigital.opml  — estructura jerárquica (File > Import > OPML)
  2. CerebroDigital.csv   — lista plana de thoughts con padre (para importación CSV)
"""

import os
import re
import csv
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

VAULT_PATH  = "/Users/mesquite/Documents/CerebroDigital"
OPML_OUT    = "/Users/mesquite/Documents/CerebroDigital.opml"
CSV_OUT     = "/Users/mesquite/Documents/CerebroDigital.csv"

def clean_content(content):
    """Quita frontmatter YAML y limpia el texto."""
    cleaned = re.sub(r'^---\n.*?\n---\n?', '', content, flags=re.DOTALL)
    return cleaned.strip()

def sanitize(text):
    """Escapa caracteres especiales para XML."""
    return (text or "").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# ── OPML ─────────────────────────────────────────────────────────────────────

def build_opml():
    opml = Element("opml", version="2.0")
    head = SubElement(opml, "head")
    title = SubElement(head, "title")
    title.text = "CerebroDigital"
    body = SubElement(opml, "body")

    root_outline = SubElement(body, "outline", text="CerebroDigital")

    vault = Path(VAULT_PATH)

    def process_dir(parent_el, dir_path):
        entries = sorted(os.scandir(dir_path), key=lambda e: (e.is_file(), e.name))
        for entry in entries:
            if entry.name.startswith('.'):
                continue
            if entry.is_dir():
                folder_el = SubElement(parent_el, "outline", text=entry.name)
                process_dir(folder_el, entry.path)
            elif entry.is_file() and entry.name.endswith('.md'):
                note_name = entry.name[:-3]
                try:
                    with open(entry.path, 'r', encoding='utf-8') as f:
                        raw = f.read()
                    content = clean_content(raw)
                    # OPML note attribute has content (first 500 chars for preview)
                    preview = content[:500].replace('\n', ' ').strip()
                    SubElement(parent_el, "outline",
                               text=note_name,
                               note=sanitize(preview),
                               _note=sanitize(content))
                except Exception as e:
                    SubElement(parent_el, "outline", text=note_name)

    process_dir(root_outline, VAULT_PATH)

    # Pretty print
    xml_str = tostring(opml, encoding="unicode")
    pretty  = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="UTF-8")
    with open(OPML_OUT, "wb") as f:
        f.write(pretty)
    print(f"OPML generado: {OPML_OUT}")


# ── CSV ──────────────────────────────────────────────────────────────────────
# Formato TheBrain CSV:
# Name | Type | Parent | Label | Note

def build_csv():
    rows = [["Name", "Type", "Parent", "Label", "Note"]]

    # Root
    rows.append(["CerebroDigital", "Normal", "", "vault", "Mi segundo cerebro digital"])

    vault = Path(VAULT_PATH)

    for root, dirs, files in os.walk(VAULT_PATH):
        dirs[:] = sorted([d for d in dirs if not d.startswith('.')])
        rel_root = os.path.relpath(root, VAULT_PATH)

        if rel_root == ".":
            parent_name = "CerebroDigital"
        else:
            parent_name = os.path.basename(root)

        # Folders
        for d in dirs:
            if d.startswith('.'):
                continue
            rows.append([d, "Normal", parent_name, "carpeta", ""])

        # Files
        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            note_name = fname[:-3]
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    raw = f.read()
                content = clean_content(raw)
                # CSV note: first 1000 chars
                note_preview = content[:1000].replace('\n', ' ').strip()
            except:
                note_preview = ""
            rows.append([note_name, "Normal", parent_name, "nota", note_preview])

    with open(CSV_OUT, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"CSV generado: {CSV_OUT}")
    print(f"  Filas: {len(rows) - 1}")


# ── Run ───────────────────────────────────────────────────────────────────────

print("Generando archivos para TheBrain 15...\n")
build_opml()
build_csv()

print("\nCómo importar en TheBrain 15:")
print("  OPML → File > Import > From OPML  → CerebroDigital.opml")
print("  CSV  → File > Import > From CSV   → CerebroDigital.csv")
print("\nEl OPML preserva la jerarquía completa.")
print("El CSV es más simple pero más compatible.")
