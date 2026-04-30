from datetime import datetime
from typing import Literal

_HISTORIAL: list[dict] = []
_next_id = 1

# Etiquetas legibles por acción
LABELS = {
    "CREADA":           "Remesa creada",
    "GENERADA":         "Cuaderno 34 generado",
    "PDF_GENERADO":     "PDF generado",
    "PDF_DESCARGADO":   "PDF descargado",
    "A3CON_EXPORTADO":  "Exportación A3Con",
    "CERRADA":          "Remesa cerrada",
    "PEG_AÑADIDA":      "PEG añadida",
    "PEG_QUITADA":      "PEG quitada",
    "GASTO_AÑADIDO":    "Gasto añadido",
    "GASTO_QUITADO":    "Gasto quitado",
}

ICONS = {
    "CREADA":          "📂",
    "GENERADA":        "⚙️",
    "PDF_GENERADO":    "🖨",
    "PDF_DESCARGADO":  "⬇",
    "A3CON_EXPORTADO": "📤",
    "CERRADA":         "✅",
    "PEG_AÑADIDA":     "➕",
    "PEG_QUITADA":     "➖",
    "GASTO_AÑADIDO":   "➕",
    "GASTO_QUITADO":   "➖",
}


def registrar_evento(
    tipo_remesa: Literal["RT", "RD"],
    id_remesa: int,
    accion: str,
    usuario: str,
    detalle: str = "",
    fecha: str | None = None,
    hora: str | None = None,
) -> dict:
    global _next_id
    ahora = datetime.now()
    evento = {
        "id_evento":   _next_id,
        "tipo_remesa": tipo_remesa,
        "id_remesa":   id_remesa,
        "accion":      accion,
        "label":       LABELS.get(accion, accion),
        "icono":       ICONS.get(accion, "·"),
        "usuario":     usuario,
        "fecha":       fecha or ahora.strftime("%Y-%m-%d"),
        "hora":        hora or ahora.strftime("%H:%M"),
        "detalle":     detalle,
    }
    _HISTORIAL.append(evento)
    _next_id += 1
    return evento


def obtener_historial(tipo_remesa: str, id_remesa: int) -> list[dict]:
    return [e for e in _HISTORIAL
            if e["tipo_remesa"] == tipo_remesa and e["id_remesa"] == id_remesa]


# ── Seed: eventos iniciales para los datos mock ────────────────────────────────

def _seed():
    # RT – Transferencias
    registrar_evento("RT", 1, "CREADA",   "José Carlos Alonso", fecha="2026-01-20", hora="09:00")

    registrar_evento("RT", 2, "CREADA",   "José Carlos Alonso", fecha="2026-02-28", hora="10:15")
    registrar_evento("RT", 2, "GENERADA", "José Carlos Alonso", "Cuaderno 34 generado", fecha="2026-03-01", hora="11:30")
    registrar_evento("RT", 2, "PDF_GENERADO", "José Carlos Alonso", fecha="2026-03-01", hora="11:31")

    registrar_evento("RT", 3, "CREADA",   "José Carlos Alonso", fecha="2026-03-15", hora="08:45")
    registrar_evento("RT", 3, "GENERADA", "José Carlos Alonso", "Cuaderno 34 generado", fecha="2026-03-18", hora="14:00")
    registrar_evento("RT", 3, "PDF_GENERADO", "José Carlos Alonso", fecha="2026-03-18", hora="14:01")
    registrar_evento("RT", 3, "A3CON_EXPORTADO", "José Carlos Alonso", fecha="2026-03-19", hora="09:20")
    registrar_evento("RT", 3, "CERRADA",  "José Carlos Alonso", "3 PEGs marcados como PAGADO", fecha="2026-03-20", hora="10:00")
    registrar_evento("RT", 3, "PDF_DESCARGADO", "José Carlos Alonso", fecha="2026-03-20", hora="10:02")

    # RD – Directas
    registrar_evento("RD", 1, "CREADA",   "José Carlos Alonso", fecha="2026-03-31", hora="12:00")


_seed()
