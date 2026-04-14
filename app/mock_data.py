# Adjuntos de PEGs almacenados en Drive.
# En producción esta lista será reemplazada por una tabla en BD.
peg_adjuntos: list[dict] = [
    {
        "id_documento": 1,
        "id_peg": 1,
        "tipo": "FACTURA",
        "nombre_archivo": "factura_veterinaria_001.pdf",
        "ruta": "media/pegs/1/factura_veterinaria_001.pdf",
        "fecha_subida": "2026-01-20",
    },
    {
        "id_documento": 2,
        "id_peg": 2,
        "tipo": "PRESUPUESTO",
        "nombre_archivo": "presupuesto_idiomas.jpg",
        "ruta": "media/pegs/2/presupuesto_idiomas.jpg",
        "fecha_subida": "2026-02-10",
    },
]

_next_adj_id = 3


def next_adj_id() -> int:
    global _next_adj_id
    current = _next_adj_id
    _next_adj_id += 1
    return current


def siguiente_cuenta_cliente() -> str:
    """
    Calcula la siguiente cuenta cliente disponible del grupo 4.
    Busca el máximo numérico entre todas las cuentas cliente
    de todos los proveedores y devuelve el siguiente.
    Base: 4100001
    """
    from app.services.proveedores_service import proveedores_db as PROVEEDORES
    BASE = 4100001
    maximo = BASE - 1
    for p in PROVEEDORES:
        cuenta = p.get("cuenta_cliente", "")
        if cuenta and cuenta.isdigit():
            val = int(cuenta)
            if val > maximo:
                maximo = val
    return str(maximo + 1)
