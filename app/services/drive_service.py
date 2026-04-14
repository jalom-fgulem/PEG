import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _upload_dir() -> Path:
    base = os.getenv("UPLOAD_DIR", "uploads/pegs")
    return Path(base)


def get_or_create_peg_folder(peg_codigo: str) -> str:
    """Crea uploads/pegs/{peg_codigo}/ si no existe. Devuelve la ruta absoluta."""
    folder = _upload_dir() / peg_codigo
    folder.mkdir(parents=True, exist_ok=True)
    logger.info("Carpeta PEG: %s", folder.resolve())
    return str(folder.resolve())


def upload_file(
    peg_codigo: str, filename: str, file_bytes: bytes, mime_type: str
) -> dict:
    """Guarda el archivo en disco y devuelve metadatos básicos.

    Returns:
        {"drive_file_id": str, "nombre": str, "size": int}

    Raises:
        ValueError: si el tipo MIME no está permitido o el tamaño supera 10 MB.
    """
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Tipo MIME '{mime_type}' no permitido. "
            f"Permitidos: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(
            f"El archivo supera el tamaño máximo de 10 MB "
            f"({len(file_bytes) / 1024 / 1024:.2f} MB)"
        )

    folder = Path(get_or_create_peg_folder(peg_codigo))

    # Evitar colisiones de nombre
    dest = folder / filename
    if dest.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while dest.exists():
            dest = folder / f"{stem}_{counter}{suffix}"
            counter += 1
        final_name = dest.name
    else:
        final_name = filename

    dest.write_bytes(file_bytes)
    logger.info("Archivo guardado: %s (%d bytes)", dest, len(file_bytes))

    return {
        "drive_file_id": f"{peg_codigo}/{final_name}",
        "nombre": final_name,
        "size": len(file_bytes),
    }


def get_download_url(drive_file_id: str) -> str:
    """Devuelve la URL local de descarga del archivo."""
    return f"/adjuntos/files/{drive_file_id}"


def delete_file(drive_file_id: str) -> bool:
    """Elimina el archivo del disco. Devuelve True si tuvo éxito."""
    try:
        path = _upload_dir() / drive_file_id
        path.unlink()
        logger.info("Archivo eliminado: %s", path)
        return True
    except FileNotFoundError:
        logger.warning("Archivo no encontrado al eliminar: %s", drive_file_id)
        return False
    except Exception as exc:
        logger.error("Error al eliminar '%s': %s", drive_file_id, exc)
        return False
