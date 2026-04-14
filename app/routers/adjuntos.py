import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, Response

from app.core.auth import require_login, require_rol
from app.services import drive_service
from app import mock_data

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Adjuntos"])


# ──────────────────────────────────────────────────────────────────────────────
# GET /adjuntos/files/{file_path}  — servir archivos locales
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/adjuntos/files/{file_path:path}")
def servir_adjunto(
    file_path: str,
    usuario: dict = Depends(require_login),
):
    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads/pegs"))
    ruta = upload_dir / file_path
    if not ruta.exists() or not ruta.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(str(ruta))

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ──────────────────────────────────────────────────────────────────────────────
# GET /pegs/{peg_id}/adjuntos
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/pegs/{peg_id}/adjuntos")
def listar_adjuntos(
    peg_id: int,
    usuario: dict = Depends(require_login),
):
    adjuntos = [a for a in mock_data.peg_adjuntos if a["peg_id"] == peg_id]
    resultado = [
        {
            **a,
            "url": drive_service.get_download_url(a["drive_file_id"]),
            "fecha_subida": a["fecha_subida"].isoformat(),
        }
        for a in adjuntos
    ]
    return JSONResponse(resultado)


# ──────────────────────────────────────────────────────────────────────────────
# POST /pegs/{peg_id}/adjuntos
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/pegs/{peg_id}/adjuntos", status_code=201)
async def subir_adjunto(
    peg_id: int,
    archivo: UploadFile = File(...),
    usuario: dict = Depends(require_login),
):
    # Validar tipo MIME
    if archivo.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Tipo de archivo no permitido: '{archivo.content_type}'. "
                "Solo se admiten PDF, JPEG y PNG."
            ),
        )

    file_bytes = await archivo.read()

    # Validar tamaño
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail=(
                f"El archivo supera el tamaño máximo de 10 MB "
                f"({len(file_bytes) / 1024 / 1024:.2f} MB)."
            ),
        )

    # Extraer codigo_peg a partir del peg_id para nombrar la carpeta en Drive
    from app.services.pegs_service import obtener_peg
    peg = obtener_peg(peg_id)
    if not peg:
        raise HTTPException(status_code=404, detail="PEG no encontrada")

    peg_codigo = peg["codigo_peg"]

    try:
        resultado = drive_service.upload_file(
            peg_codigo=peg_codigo,
            filename=archivo.filename,
            file_bytes=file_bytes,
            mime_type=archivo.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Error al subir adjunto a Drive: %s", exc)
        raise HTTPException(status_code=500, detail="Error al subir el archivo a Drive")

    nuevo = {
        "id": mock_data.next_adj_id(),
        "peg_id": peg_id,
        "drive_file_id": resultado["drive_file_id"],
        "nombre_archivo": resultado["nombre"],
        "mime_type": archivo.content_type,
        "size_bytes": resultado["size"],
        "subido_por": usuario["username"],
        "fecha_subida": datetime.now(),
    }
    mock_data.peg_adjuntos.append(nuevo)

    return JSONResponse(
        {
            **nuevo,
            "url": drive_service.get_download_url(nuevo["drive_file_id"]),
            "fecha_subida": nuevo["fecha_subida"].isoformat(),
        },
        status_code=201,
    )


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /pegs/{peg_id}/adjuntos/{adj_id}
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/pegs/{peg_id}/adjuntos/{adj_id}", status_code=204)
def eliminar_adjunto(
    peg_id: int,
    adj_id: int,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    adjunto = next(
        (a for a in mock_data.peg_adjuntos if a["id"] == adj_id and a["peg_id"] == peg_id),
        None,
    )
    if not adjunto:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")

    eliminado = drive_service.delete_file(adjunto["drive_file_id"])
    if not eliminado:
        logger.warning(
            "No se pudo eliminar de Drive el archivo %s; se eliminará igualmente del registro.",
            adjunto["drive_file_id"],
        )

    mock_data.peg_adjuntos.remove(adjunto)
    return Response(status_code=204)
