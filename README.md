# obsidian-to-thebrain

Scripts para importar un vault de **Obsidian** a **TheBrain 15** en macOS.

---

## Scripts

### `obsidian_to_thebrain.py` — Recomendado

Escribe directamente en la base de datos SQLite de TheBrain (`Brain.db`). Es el método más confiable.

**Antes de ejecutar:** Cierra TheBrain completamente.

```bash
python3 obsidian_to_thebrain.py
```

**Qué hace:**
- Crea un backup automático de `Brain.db` antes de cualquier cambio
- Importa carpetas como thoughts con color por sección del vault
- Importa archivos `.md` como thoughts en gris neutro con el contenido completo como nota
- Resuelve `[[wikilinks]]` como jump links entre thoughts

---

### `obsidian_to_opml.py`

Genera dos archivos de exportación alternativos:
- `CerebroDigital.opml` — estructura jerárquica
- `CerebroDigital.csv` — lista plana con padre

### `obsidian_to_brain.py`

Genera un archivo XML con el formato de exportación de TheBrain.

---

## Configuración

Edita las constantes al inicio de `obsidian_to_thebrain.py`:

```python
VAULT_PATH = "/ruta/a/tu/vault"
BRAIN_DB   = "/ruta/a/Brain.db"   # ~/Library/Application Support/Brains/U01/B0X/Brain.db
BRAIN_ID   = "tu-brain-uuid"      # SELECT Id FROM Brains LIMIT 1
NOTES_DIR  = "/ruta/a/Notes"      # misma carpeta que Brain.db
```

Para encontrar tu `BRAIN_ID`:

```bash
sqlite3 ~/Library/Application\ Support/Brains/U01/B02/Brain.db "SELECT Id FROM Brains LIMIT 1;"
```

---

## Colores por sección

Las carpetas reciben un color según su prefijo. Las notas son gris neutro.

| Sección | Color |
|---------|-------|
| `00-command-center` | Naranja |
| `01-proyectos` | Verde |
| `02-personal` | Azul |
| `03-okrs` | Morado |
| `03-recursos` | Cian |
| `04-kanban` | Amarillo |
| `05-weekly` | Verde claro |
| `06-templates` | Gris |
| `07-yo` | Rosa |
| `08-logros` | Rojo |

---

## Notas técnicas

- TheBrain 15 almacena los brains en SQLite en `~/Library/Application Support/Brains/U01/`
- Los colores se guardan como enteros ARGB **con signo** (signed int32). Valores `0xFF______` deben convertirse restando `0x100000000`.
- Las notas se guardan como archivos `.md` en la carpeta `Notes/` junto a `Brain.db`, con el nombre `{thoughtId}.md`.
- Links: `Relation=1` = parent-child, `Relation=3` = jump link.
