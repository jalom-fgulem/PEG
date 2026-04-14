from app.schemas.proveedores import ProveedorCrear

proveedores_db = [
    {
        "id_proveedor": 1,
        "tipo_persona": "JURIDICA",
        "cif_nif": "B12345678",
        "razon_social": "Proveedor Ejemplo SL",
        "nombre_comercial": "Proveedor Ejemplo",
        "email": "proveedor@ejemplo.com",
        "telefono": "987000000",
        "iban": "ES7620770024003102575766",
        "servicios": [1, 2, 3],
        "direccion": "Calle Mayor 10, 2º",
        "localidad": "León",
        "codigo_postal": "24001",
        "provincia": "León",
        "cuenta_cliente": "",
    },
    {
        "id_proveedor": 2,
        "tipo_persona": "FISICA",
        "cif_nif": "12345678Z",
        "razon_social": "María Pérez",
        "nombre_comercial": None,
        "email": "maria@ejemplo.com",
        "telefono": "600000000",
        "iban": None,
        "servicios": [2],
        "direccion": "Avenida de Asturias 45, 1º B",
        "localidad": "Ponferrada",
        "codigo_postal": "24400",
        "provincia": "León",
        "cuenta_cliente": "",
    },
    {
        "id_proveedor": 3,
        "tipo_persona": "JURIDICA",
        "cif_nif": "B76543210",
        "razon_social": "Veterinaria Técnica del Noroeste SL",
        "nombre_comercial": "VetTécnica Noroeste",
        "email": "contacto@vettecnica.com",
        "telefono": "987111222",
        "iban": "ES1111111111111111111111",
        "servicios": [1],
        "direccion": "Polígono Industrial El Jano, nave 7",
        "localidad": "Benavente",
        "codigo_postal": "49600",
        "provincia": "Zamora",
        "cuenta_cliente": "4100003",
    },
    {
        "id_proveedor": 4,
        "tipo_persona": "JURIDICA",
        "cif_nif": "B99887766",
        "razon_social": "Traducciones León SL",
        "nombre_comercial": "TraducLéon",
        "email": "info@traduccionesleon.com",
        "telefono": "987333444",
        "iban": "ES2222222222222222222222",
        "servicios": [2, 3],
        "direccion": "Calle Ancha 22, 1º",
        "localidad": "León",
        "codigo_postal": "24003",
        "provincia": "León",
        "cuenta_cliente": "",
    },
]


def listar_proveedores():
    return proveedores_db


def get_proveedores_por_servicio(id_servicio: int):
    return [p for p in proveedores_db if id_servicio in p.get("servicios", [])]


def obtener_proveedor(id_proveedor: int):
    for proveedor in proveedores_db:
        if proveedor["id_proveedor"] == id_proveedor:
            return proveedor
    return None


def crear_proveedor(data: ProveedorCrear):
    nuevo_id = max([p["id_proveedor"] for p in proveedores_db], default=0) + 1
    proveedor = {
        "id_proveedor": nuevo_id,
        **data.model_dump(),
    }
    proveedores_db.append(proveedor)
    return proveedor


def actualizar_iban(id_proveedor: int, iban: str | None) -> bool:
    proveedor = obtener_proveedor(id_proveedor)
    if not proveedor:
        return False
    proveedor["iban"] = iban or None
    return True


def actualizar_proveedor(id_proveedor: int, datos: dict) -> bool:
    proveedor = obtener_proveedor(id_proveedor)
    if not proveedor:
        return False
    for campo in ("tipo_persona", "cif_nif", "razon_social", "nombre_comercial", "email", "telefono", "iban",
                  "direccion", "localidad", "codigo_postal", "provincia", "cuenta_cliente"):
        if campo in datos:
            proveedor[campo] = datos[campo] or None
    return True