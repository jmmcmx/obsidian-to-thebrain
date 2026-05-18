#!/usr/bin/env python3
"""
Obsidian Vault → TheBrain 15 XML Import
Convierte CerebroDigital al formato XML de TheBrain.

Estructura:
- Cada carpeta → un Thought (nodo padre)
- Cada archivo .md → un Thought con su contenido como nota
- [[wikilinks]] → Jump links entre thoughts
- Tags YAML frontmatter → Tag thoughts en TheBrain
"""

import os
import re
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from pathlib import Path

VAULT_PATH = "/Users/mesquite/Documents/CerebroDigital"
OUTPUT_PATH = "/Users/mesquite/Documents/CerebroDigital_TheBrain.xml"

# Colores por sección del vault
SECTION_COLORS = {
    "00-command-center": "#F97316",
    "01-proyectos":      "#00A859",
    "02-personal":       "#3B82F6",
    "03-okrs":           "#A855F7",
    "03-recursos":       "#00B4D8",
    "04-kanban":         "#FFB703",
    "05-weekly":         "#00C896",
    "06-templates":      "#888888",
    "07-yo":             "#EC4899",
    "08-logros-fracasos":"#FF4757",
}

def new_id():
    return str(uuid.uuid4()).upper()

def now_str():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def get_color(rel_path):
    parts = Path(rel_path).parts
    if parts:
        for key, color in SECTION_COLORS.items():
            if parts[0].startswith(key[:3]):
                return color
    return "#CCCCCC"

def extract_frontmatter_tags(content):
    """Extrae tags del frontmatter YAML de Obsidian."""
    tags = []
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        tag_match = re.search(r'tags:\s*\[([^\]]+)\]', fm)
        if tag_match:
            raw = tag_match.group(1)
            tags = [t.strip().strip('"').strip("'") for t in raw.split(',')]
        tag_match2 = re.search(r'tags:\n((?:\s*-\s*.+\n?)+)', fm)
        if tag_match2:
            lines = tag_match2.group(1).strip().split('\n')
            tags = [l.strip().lstrip('- ').strip() for l in lines]
    return [t for t in tags if t]

def extract_wikilinks(content):
    """Extrae [[wikilinks]] del contenido."""
    return re.findall(r'\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]', content)

def clean_content(content):
    """Limpia el contenido para TheBrain (quita frontmatter YAML)."""
    cleaned = re.sub(r'^---\n.*?\n---\n?', '', content, flags=re.DOTALL)
    return cleaned.strip()

# ── Build structure ──────────────────────────────────────────────────────────

thoughts   = {}   # id → {name, color, rel_path}
links      = []   # (parent_id, child_id, relation)
notes      = {}   # thought_id → markdown content
tags_map   = {}   # tag_name → thought_id
name_to_id = {}   # normalized_name → thought_id (for wikilink resolution)

# Root thought
ROOT_ID = new_id()
thoughts[ROOT_ID] = {"name": "CerebroDigital", "color": "#00A859", "rel_path": ""}
name_to_id["cerebro digital"] = ROOT_ID
name_to_id["cerebrodigital"]  = ROOT_ID

vault = Path(VAULT_PATH)

# Pass 1: folders and files → thoughts
folder_ids = {}  # rel_path → thought_id

for root, dirs, files in os.walk(VAULT_PATH):
    # Skip .obsidian
    dirs[:] = [d for d in sorted(dirs) if not d.startswith('.')]

    rel_root = os.path.relpath(root, VAULT_PATH)
    if rel_root == ".":
        folder_ids["."] = ROOT_ID
        continue

    folder_name = os.path.basename(root)
    tid = new_id()
    color = get_color(rel_root)
    thoughts[tid] = {"name": folder_name, "color": color, "rel_path": rel_root}
    folder_ids[rel_root] = tid
    name_to_id[folder_name.lower()] = tid

    # Link to parent folder
    parent_rel = os.path.relpath(os.path.dirname(root), VAULT_PATH)
    parent_id = folder_ids.get(parent_rel if parent_rel != "." else ".", ROOT_ID)
    links.append((parent_id, tid, "1"))

    # .md files in this folder
    for fname in sorted(files):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(root, fname)
        note_name = fname[:-3]  # strip .md
        rel_file  = os.path.relpath(fpath, VAULT_PATH)

        ftid  = new_id()
        color = get_color(rel_root)
        thoughts[ftid] = {"name": note_name, "color": color, "rel_path": rel_file}
        name_to_id[note_name.lower()] = ftid

        links.append((tid, ftid, "1"))

        # Read content
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read()
            file_tags = extract_frontmatter_tags(raw)
            content   = clean_content(raw)
            notes[ftid] = content

            # Register tags
            for tag in file_tags:
                if tag not in tags_map:
                    tag_id = new_id()
                    tags_map[tag] = tag_id
                    thoughts[tag_id] = {"name": tag, "color": "#FFB703", "rel_path": "", "is_tag": True}
                links.append((tags_map[tag], ftid, "2"))  # jump link tag→note

        except Exception as e:
            print(f"  Warning: could not read {fpath}: {e}")

# Pass 2: resolve [[wikilinks]] as jump links
print(f"Thoughts: {len(thoughts)}, Links: {len(links)}, Notes: {len(notes)}, Tags: {len(tags_map)}")

for root, dirs, files in os.walk(VAULT_PATH):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in files:
        if not fname.endswith(".md"):
            continue
        note_name = fname[:-3]
        source_id = name_to_id.get(note_name.lower())
        if not source_id:
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read()
            wikilinks = extract_wikilinks(raw)
            for wl in wikilinks:
                target_id = name_to_id.get(wl.lower())
                if target_id and target_id != source_id:
                    # Avoid duplicate jump links
                    pair = (source_id, target_id, "2")
                    if pair not in links:
                        links.append(pair)
        except:
            pass

# ── Build XML ────────────────────────────────────────────────────────────────

brain = ET.Element("BRAIN")
brain.set("DBVERSION", "15")
brain.set("EXPORTDATE", now_str())

thoughts_el = ET.SubElement(brain, "THOUGHTS")
links_el    = ET.SubElement(brain, "LINKS")
notes_el    = ET.SubElement(brain, "NOTES")

ts = now_str()

for tid, t in thoughts.items():
    th = ET.SubElement(thoughts_el, "THOUGHT")
    th.set("ID", tid)
    th.set("NAME", t["name"])
    th.set("ACTYPE", "4" if t.get("is_tag") else "1")
    th.set("FOREGROUNDCOLOR", t["color"])
    th.set("BACKGROUNDCOLOR", "")
    th.set("CREATIONDATETIME", ts)
    th.set("MODIFICATIONDATETIME", ts)
    th.set("LABEL", "")

for parent_id, child_id, relation in links:
    lk = ET.SubElement(links_el, "LINK")
    lk.set("THOUGHTIDONE", parent_id)
    lk.set("THOUGHTIDTWO", child_id)
    lk.set("RELATION", relation)
    lk.set("ACTYPE", "1")
    lk.set("CREATIONDATETIME", ts)
    lk.set("MODIFICATIONDATETIME", ts)

for tid, content in notes.items():
    nt = ET.SubElement(notes_el, "NOTE")
    nt.set("THOUGHTID", tid)
    nt.set("NOTETYPE", "1")
    nt.text = content

# ── Write pretty XML ─────────────────────────────────────────────────────────

xml_str = ET.tostring(brain, encoding="unicode")
pretty  = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="UTF-8")

with open(OUTPUT_PATH, "wb") as f:
    f.write(pretty)

print(f"\nExportado: {OUTPUT_PATH}")
print(f"  Thoughts : {len(thoughts)}")
print(f"  Links    : {len(links)}")
print(f"  Notes    : {len(notes)}")
print(f"  Tags     : {len(tags_map)}")
print("\nPara importar en TheBrain 15:")
print("  File → Import → From XML → selecciona CerebroDigital_TheBrain.xml")
