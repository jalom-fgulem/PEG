from datetime import datetime

_MENSAJES: list[dict] = []
_next_id = 1


def crear_mensaje(
    id_emisor: int | None,
    id_destinatario: int,
    asunto: str,
    cuerpo: str,
    tipo: str = "MANUAL",
    evento: str | None = None,
    entidad_tipo: str | None = None,
    entidad_id: int | None = None,
) -> dict:
    global _next_id
    m = {
        "id_mensaje": _next_id,
        "id_emisor": id_emisor,
        "id_destinatario": id_destinatario,
        "asunto": asunto,
        "cuerpo": cuerpo,
        "fecha": datetime.now(),
        "leido": False,
        "archivado": False,
        "tipo": tipo,
        "evento": evento,
        "entidad_tipo": entidad_tipo,
        "entidad_id": entidad_id,
    }
    _MENSAJES.append(m)
    _next_id += 1
    return m


def listar_recibidos(
    id_usuario: int,
    solo_no_leidos: bool = False,
    incluir_archivados: bool = False,
) -> list[dict]:
    result = [m for m in _MENSAJES if m["id_destinatario"] == id_usuario]
    if not incluir_archivados:
        result = [m for m in result if not m["archivado"]]
    if solo_no_leidos:
        result = [m for m in result if not m["leido"]]
    return sorted(result, key=lambda m: m["fecha"], reverse=True)


def listar_enviados(id_usuario: int) -> list[dict]:
    return sorted(
        [m for m in _MENSAJES if m["id_emisor"] == id_usuario],
        key=lambda m: m["fecha"],
        reverse=True,
    )


def obtener_mensaje(id_mensaje: int) -> dict | None:
    return next((m for m in _MENSAJES if m["id_mensaje"] == id_mensaje), None)


def marcar_leido(id_mensaje: int, id_usuario: int) -> bool:
    m = obtener_mensaje(id_mensaje)
    if m and m["id_destinatario"] == id_usuario:
        m["leido"] = True
        return True
    return False


def archivar(id_mensaje: int, id_usuario: int) -> bool:
    m = obtener_mensaje(id_mensaje)
    if m and m["id_destinatario"] == id_usuario:
        m["archivado"] = not m["archivado"]
        return True
    return False


def eliminar(id_mensaje: int, id_usuario: int) -> bool:
    global _MENSAJES
    m = obtener_mensaje(id_mensaje)
    if m and (m["id_destinatario"] == id_usuario or m["id_emisor"] == id_usuario):
        _MENSAJES = [x for x in _MENSAJES if x["id_mensaje"] != id_mensaje]
        return True
    return False


def contar_no_leidos(id_usuario: int) -> int:
    return sum(
        1 for m in _MENSAJES
        if m["id_destinatario"] == id_usuario
        and not m["leido"]
        and not m["archivado"]
    )
