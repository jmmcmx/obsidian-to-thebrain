#!/usr/bin/env python3
"""
Agrega una nota individual de Obsidian a TheBrain 15 sin reimportar todo el vault.

Uso:
    python3 add_note.py <ruta_al_archivo.md> <nombre_carpeta_padre>

Ejemplo:
    python3 add_note.py "08-logros-fracasos/CAF Encuentro 2015.md" "08-logros-fracasos"

IMPORTANTE: Cierra TheBrain antes de ejecutar.
"""

import os
import re
import sys
import uuid
import sqlite3
import shutil
from datetime import datetime

VAULT_PATH = "/Users/mesquite/Documents/CerebroDigital"
BRAIN_DB   = "/Users/mesquite/Library/Application Support/Brains/U01/B02/Brain.db"
BRAIN_ID   = "6ebf89cd-5a58-45b4-984e-becca8a80ef0"
NOTES_DIR  = "/Users/mesquite/Library/Application Support/Brains/U01/B02/Notes"

# ── Helpers ───────────────────────────────────────────────────────────────────

def argb(r, g, b):
    """RGB → ARGB signed int32 (alpha=0xFF)."""
    v = (0xFF << 24) | (r << 16) | (g << 8) | b
    if v > 0x7FFFFFFF:
        v -= 0x100000000
    return v

SECTION_COLORS = {
    "00-command": argb(0xF9, 0x73, 0x16),
    "01-proyect": argb(0x00, 0xA8, 0x59),
    "02-persona": argb(0x3B, 0x82, 0xF6),
    "03-okrs":    argb(0xA8, 0x55, 0xF7),
    "03-recurso": argb(0x00, 0xB4, 0xD8),
    "04-kanban":  argb(0xFF, 0xB7, 0x03),
    "05-weekly":  argb(0x00, 0xC8, 0x96),
    "06-templat": argb(0x88, 0x88, 0x88),
    "07-yo":      argb(0xEC, 0x48, 0x99),
    "08-logros":  argb(0xFF, 0x47, 0x57),
}

def note_color(rel_path: str) -> int:
    for prefix, color in SECTION_COLORS.items():
        if prefix in str(rel_path):
            return color
    return argb(0xBB, 0xBB, 0xBB)

def clean_content(content: str) -> str:
    return re.sub(r'^---\n.*?\n---\n?', '', content, flags=re.DOTALL).strip()

def now_ms() -> int:
    return int(datetime.now().timestamp() * 1000)

# ── Main ──────────────────────────────────────────────────────────────────────

def add_note(note_rel_path: str, parent_name: str):
    """
    note_rel_path : ruta relativa desde la raíz del vault (ej. "08-logros-fracasos/Mi nota.md")
    parent_name   : nombre exacto del thought padre en TheBrain (ej. "08-logros-fracasos")
    """
    note_abs = os.path.join(VAULT_PATH, note_rel_path)
    if not os.path.exists(note_abs):
        print(f"❌ Archivo no encontrado: {note_abs}")
        sys.exit(1)

    note_name = os.path.basename(note_abs)
    if note_name.endswith(".md"):
        note_name = note_name[:-3]

    # Backup
    backup = BRAIN_DB + ".backup"
    shutil.copy2(BRAIN_DB, backup)
    print(f"Backup: {backup}")

    conn = sqlite3.connect(BRAIN_DB)
    cur  = conn.cursor()

    # Buscar thought padre
    cur.execute("SELECT Id FROM Thoughts WHERE Name=? LIMIT 1", (parent_name,))
    row = cur.fetchone()
    if not row:
        print(f"❌ Thought padre '{parent_name}' no encontrado en TheBrain.")
        conn.close()
        sys.exit(1)
    parent_id = row[0]
    print(f"Padre encontrado: {parent_id} ({parent_name})")

    # Verificar si ya existe
    cur.execute("SELECT Id FROM Thoughts WHERE Name=? LIMIT 1", (note_name,))
    existing = cur.fetchone()
    if existing:
        print(f"⚠️  Ya existe un thought con ese nombre: {existing[0]}")
        print("   Usa update_note.py para actualizar una nota existente.")
        conn.close()
        sys.exit(1)

    # Insertar thought
    tid   = str(uuid.uuid4())
    lid   = str(uuid.uuid4())
    ts    = now_ms()
    color = note_color(note_rel_path)

    cur.execute("""
        INSERT INTO Thoughts
          (Id, ACType, BrainId, CreationDateTime, ModificationDateTime, Kind, Name, ForegroundColor, BackgroundColor)
        VALUES (?,1,?,?,?,1,?,?,0)
    """, (tid, BRAIN_ID, ts, ts, note_name[:140], color))

    cur.execute("""
        INSERT INTO Links
          (Id, BrainId, CreationDateTime, ModificationDateTime,
           Direction, Kind, Meaning, Relation, Thickness, PositionAToB, PositionBToA, ThoughtIdA, ThoughtIdB)
        VALUES (?,?,?,?,1,1,1,1,1,0.0,0.0,?,?)
    """, (lid, BRAIN_ID, ts, ts, parent_id, tid))

    # Escribir nota
    with open(note_abs, "r", encoding="utf-8") as f:
        raw = f.read()
    content = clean_content(raw)
    if content:
        os.makedirs(NOTES_DIR, exist_ok=True)
        with open(os.path.join(NOTES_DIR, f"{tid}.md"), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Nota escrita: {tid}.md")

    conn.commit()
    conn.close()

    print(f"\n✅ Listo!")
    print(f"   Thought : {note_name}")
    print(f"   ID      : {tid}")
    print(f"   Padre   : {parent_name}")
    print(f"\nAbre TheBrain y navega a '{parent_name}'.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 add_note.py <ruta_relativa.md> <nombre_padre>")
        print('Ejemplo: python3 add_note.py "08-logros-fracasos/Mi nota.md" "08-logros-fracasos"')
        sys.exit(1)
    add_note(sys.argv[1], sys.argv[2])
