#!/usr/bin/env python3
"""
Obsidian CerebroDigital → TheBrain 15 (Brain.db directo)
IMPORTANTE: Cierra TheBrain antes de ejecutar este script.

Brain destino: Obsidian (B02)
Brain ID: 6ebf89cd-5a58-45b4-984e-becca8a80ef0
"""

import os
import re
import uuid
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

VAULT_PATH  = "/Users/mesquite/Documents/CerebroDigital"
BRAIN_DB    = "/Users/mesquite/Library/Application Support/Brains/U01/B02/Brain.db"
BRAIN_ID    = "6ebf89cd-5a58-45b4-984e-becca8a80ef0"
NOTES_DIR   = "/Users/mesquite/Library/Application Support/Brains/U01/B02/Notes"

# Backup automático
BACKUP_DB = BRAIN_DB + ".backup"
shutil.copy2(BRAIN_DB, BACKUP_DB)
print(f"Backup creado: {BACKUP_DB}")

# ── Helpers ──────────────────────────────────────────────────────────────────

def new_id():
    return str(uuid.uuid4())

def now_ms():
    return int(datetime.now().timestamp() * 1000)

def clean_content(content):
    cleaned = re.sub(r'^---\n.*?\n---\n?', '', content, flags=re.DOTALL)
    return cleaned.strip()

# Colores por sección (formato INTEGER ARGB signed int32)
def argb(r, g, b):
    """Convierte RGB a ARGB signed int32 (alpha=0xFF)."""
    v = (0xFF << 24) | (r << 16) | (g << 8) | b
    if v > 0x7FFFFFFF:
        v -= 0x100000000
    return v

def section_color(rel_path):
    p = str(rel_path)
    if '00-command' in p: return argb(0xF9, 0x73, 0x16)  # Naranja
    if '01-proyectos' in p: return argb(0x00, 0xA8, 0x59)  # Verde
    if '02-personal' in p: return argb(0x3B, 0x82, 0xF6)   # Azul
    if '03-okrs' in p: return argb(0xA8, 0x55, 0xF7)       # Morado
    if '03-recursos' in p: return argb(0x00, 0xB4, 0xD8)   # Cian
    if '04-kanban' in p: return argb(0xFF, 0xB7, 0x03)     # Amarillo
    if '05-weekly' in p: return argb(0x00, 0xC8, 0x96)     # Verde claro
    if '06-templates' in p: return argb(0x88, 0x88, 0x88)  # Gris
    if '07-yo' in p: return argb(0xEC, 0x48, 0x99)        # Rosa
    if '08-logros' in p: return argb(0xFF, 0x47, 0x57)    # Rojo
    return argb(0xCC, 0xCC, 0xCC)

# ── Connect DB ───────────────────────────────────────────────────────────────

conn = sqlite3.connect(BRAIN_DB)
cur  = conn.cursor()

# Get root thought (first thought = brain root)
cur.execute("SELECT Id FROM Thoughts WHERE ACType=1 ORDER BY CreationDateTime LIMIT 1")
row = conn.execute("SELECT Id, Name FROM Thoughts WHERE Name='Obsidian' LIMIT 1").fetchone()
ROOT_ID = row[0] if row else None
print(f"Root thought: {ROOT_ID} ({row[1] if row else 'not found'})")

# ── Insert functions ─────────────────────────────────────────────────────────

def insert_thought(name, parent_id=None, color=0xFF_CCCCCC, actype=1, kind=1):
    tid  = new_id()
    ts   = now_ms()
    cur.execute("""
        INSERT INTO Thoughts
          (Id, ACType, BrainId, CreationDateTime, ModificationDateTime,
           Kind, Name, ForegroundColor, BackgroundColor)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (tid, actype, BRAIN_ID, ts, ts, kind, name[:140], color, 0))

    if parent_id:
        insert_link(parent_id, tid, relation=1)  # 1 = parent→child

    return tid

def insert_link(id_a, id_b, relation=1):
    lid = new_id()
    ts  = now_ms()
    cur.execute("""
        INSERT INTO Links
          (Id, BrainId, CreationDateTime, ModificationDateTime,
           Direction, Kind, Meaning, Relation, Thickness,
           PositionAToB, PositionBToA, ThoughtIdA, ThoughtIdB)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (lid, BRAIN_ID, ts, ts, 1, 1, 1, relation, 1, 0.0, 0.0, id_a, id_b))

def write_note(thought_id, content):
    os.makedirs(NOTES_DIR, exist_ok=True)
    note_path = os.path.join(NOTES_DIR, f"{thought_id}.md")
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(content)

# ── Build thoughts from vault ─────────────────────────────────────────────────

# Create "CerebroDigital" root node under Obsidian root
CD_ROOT = insert_thought("CerebroDigital", parent_id=ROOT_ID, color=argb(0x00, 0xA8, 0x59))
print(f"CerebroDigital root: {CD_ROOT}")

folder_ids   = {".": CD_ROOT}
name_to_id   = {"cerebrodigital": CD_ROOT}
thought_count = 0
note_count    = 0

for root, dirs, files in os.walk(VAULT_PATH):
    dirs[:] = sorted([d for d in dirs if not d.startswith('.')])
    rel_root = os.path.relpath(root, VAULT_PATH)

    if rel_root == ".":
        parent_id = CD_ROOT
    else:
        parent_id = folder_ids.get(rel_root, CD_ROOT)

    # Sub-folders
    for d in dirs:
        sub_rel = os.path.join(rel_root, d) if rel_root != "." else d
        color   = section_color(sub_rel)
        tid     = insert_thought(d, parent_id=parent_id, color=color)
        folder_ids[sub_rel] = tid
        name_to_id[d.lower()] = tid
        thought_count += 1

    # .md files
    for fname in sorted(files):
        if not fname.endswith('.md'):
            continue
        note_name = fname[:-3]
        fpath = os.path.join(root, fname)
        color = argb(0xBB, 0xBB, 0xBB)  # gris neutro para notas

        tid = insert_thought(note_name, parent_id=parent_id, color=color)
        name_to_id[note_name.lower()] = tid
        thought_count += 1

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read()
            content = clean_content(raw)
            if content:
                write_note(tid, content)
                note_count += 1
        except Exception as e:
            print(f"  Warning: {fname}: {e}")

# Pass 2: wikilinks → jump links
print("Procesando wikilinks...")
jump_count = 0
for root, dirs, files in os.walk(VAULT_PATH):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in files:
        if not fname.endswith('.md'):
            continue
        source = name_to_id.get(fname[:-3].lower())
        if not source:
            continue
        try:
            with open(os.path.join(root, fname), 'r', encoding='utf-8') as f:
                raw = f.read()
            for wl in re.findall(r'\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]', raw):
                target = name_to_id.get(wl.lower())
                if target and target != source:
                    insert_link(source, target, relation=3)  # 3 = jump link
                    jump_count += 1
        except:
            pass

conn.commit()
conn.close()

print(f"\nListo!")
print(f"  Thoughts creados : {thought_count}")
print(f"  Notas escritas   : {note_count}")
print(f"  Jump links       : {jump_count}")
print(f"\nAbre TheBrain 15 y navega al nodo 'CerebroDigital'.")
