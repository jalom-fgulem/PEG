"""
Generador del fichero SUENLACE para importación en A3Con (Wolters Kluwer).
Especificación: enlace contable de entrada, registros de 256 bytes.
"""

import os
from datetime import datetime
from typing import Optional
from app import mock_data  # 🔧 PERSONALIZAR: cambiar a acceso real a BD
from app.services.pegs_service import _analiticas as ANALITICAS

# 🔧 PERSONALIZAR: código de empresa en A3Con
# 00006 = empresa de prueba | 00005 = empresa real
CODIGO_EMPRESA_PRUEBA = "00006"
CODIGO_EMPRESA_REAL   = "00005"

LONGITUD_REGISTRO = 256
RETORNO_CARRO = "\r\n"  # ASCII 13 + ASCII 10


def _pad_left(valor: str, longitud: int, relleno: str = "0") -> str:
    """Alinea a la derecha completando con ceros (campos numéricos)."""
    return str(valor).zfill(longitud)[:longitud]


def _pad_right(valor: str, longitud: int, relleno: str = " ") -> str:
    """Alinea a la izquierda completando con espacios (campos alfanuméricos)."""
    return str(valor or "").ljust(longitud)[:longitud]


def _importe_a3(importe: float) -> str:
    """Formatea importe al patrón A3Con: +NNNNNNNNNN.DD (14 chars)."""
    signo = "+" if importe >= 0 else "-"
    entero = int(abs(importe))
    decimal = round(abs(importe) % 1 * 100)
    return f"{signo}{str(entero).zfill(10)}.{str(decimal).zfill(2)}"


def _fecha_a3(fecha) -> str:
    """Convierte fecha al formato aaaammdd."""
    if isinstance(fecha, str):
        # Intentar parsear si viene como string
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                fecha = datetime.strptime(fecha, fmt)
                break
            except ValueError:
                continue
    if hasattr(fecha, "strftime"):
        return fecha.strftime("%Y%m%d")
    return datetime.today().strftime("%Y%m%d")


def _registro_cabecera_factura(
    peg: dict,
    servicio: dict,
    proveedor: dict,
    codigo_empresa: str,
    numero_registro: int = 1,
) -> str:
    """
    Tipo 1: Alta cabecera de apunte con IVA (factura recibida).
    Posiciones según especificación SUENLACE.DAT.
    """
    linea = ""
    linea += "4"                                          # pos 1: Tipo formato (constante 4)
    linea += _pad_left(codigo_empresa, 5)                 # pos 2-6: Código empresa
    linea += _fecha_a3(peg.get("fecha_factura") or peg.get("fecha_creacion", datetime.today()))  # pos 7-14: Fecha apunte
    linea += "1"                                          # pos 15: Tipo registro (1=factura)
    linea += _pad_right(servicio.get("cuenta_proveedor", "4000000"), 12)  # pos 16-27: Cuenta proveedor
    linea += _pad_right(proveedor.get("razon_social", ""), 30)             # pos 28-57: Descripción cuenta
    linea += "2"                                          # pos 58: Tipo factura (2=compras)
    linea += _pad_right(peg.get("referencia_factura", str(peg["id_peg"])), 10)  # pos 59-68: Nº factura
    linea += "I"                                          # pos 69: Línea de apunte (I=inicio)
    desc = f"PEG {peg.get('codigo_peg','')}"
    linea += _pad_right(desc, 30)                         # pos 70-99: Descripción apunte
    importe_total = float(peg.get("importe_total", 0))
    linea += _importe_a3(importe_total)                   # pos 100-113: Importe total
    linea += " " * 62                                     # pos 114-175: Reserva
    nif = proveedor.get("cif_nif", "")
    linea += _pad_right(nif, 14)                          # pos 176-189: NIF proveedor
    linea += _pad_right(proveedor.get("razon_social", ""), 40)  # pos 190-229: Nombre
    linea += _pad_right(proveedor.get("codigo_postal", ""), 5)   # pos 230-234: CP
    linea += "  "                                         # pos 235-236: Reserva
    linea += _fecha_a3(peg.get("fecha_factura") or datetime.today())  # pos 237-244: Fecha operación
    linea += _fecha_a3(peg.get("fecha_factura") or datetime.today())  # pos 245-252: Fecha factura
    linea += "E"                                          # pos 253: Moneda (E=Euros)
    linea += "N"                                          # pos 254: Indicador generado
    assert len(linea) == 254, f"Cabecera factura: longitud {len(linea)} != 254"
    return linea + RETORNO_CARRO


def _registro_detalle_iva(
    peg: dict,
    linea_iva: dict,
    servicio: dict,
    codigo_empresa: str,
    es_ultima: bool,
    es_primera: bool,
    tiene_irpf: bool,
) -> str:
    """
    Tipo 9: Detalle de apunte con IVA.
    Una línea por cada tramo de IVA del PEG.
    """
    fecha = _fecha_a3(peg.get("fecha_factura") or datetime.today())
    linea = ""
    linea += "4"                                          # pos 1
    linea += _pad_left(codigo_empresa, 5)                 # pos 2-6
    linea += fecha                                        # pos 7-14
    linea += "9"                                          # pos 15: tipo registro
    linea += _pad_right(servicio.get("cuenta_gasto", "6000000"), 12)    # pos 16-27: cuenta gasto
    desc_cuenta = f"Gasto {servicio.get('nombre','')}"
    linea += _pad_right(desc_cuenta, 30)                  # pos 28-57
    linea += "C"                                          # pos 58: tipo importe (C=cargo)
    linea += _pad_right(peg.get("referencia_factura", str(peg["id_peg"])), 10)  # pos 59-68
    marcador = "U" if es_ultima else "M"
    linea += marcador                                     # pos 69: M o U
    desc = f"PEG {peg.get('codigo_peg','')}"
    linea += _pad_right(desc, 30)                         # pos 70-99
    linea += "01"                                         # pos 100-101: subtipo (01=interior IVA)
    base = float(linea_iva.get("base_imponible", 0))
    linea += _importe_a3(base)                            # pos 102-115: base imponible
    pct_iva = float(linea_iva.get("porcentaje_iva", 0))
    linea += f"{pct_iva:05.2f}"                           # pos 116-120: % IVA
    cuota_iva = float(linea_iva.get("cuota_iva", 0))
    linea += _importe_a3(cuota_iva)                       # pos 121-134: cuota IVA
    linea += "00.00"                                      # pos 135-139: % recargo (sin recargo)
    linea += _importe_a3(0)                               # pos 140-153: cuota recargo
    # IRPF: solo en la última línea y si el PEG tiene retención
    pct_irpf = 0.0
    cuota_irpf = 0.0
    if es_ultima and tiene_irpf:
        pct_irpf = float(peg.get("porcentaje_irpf", 0))
        cuota_irpf = float(peg.get("importe_irpf", 0))
    linea += f"{pct_irpf:05.2f}"                          # pos 154-158: % retención
    linea += _importe_a3(cuota_irpf)                      # pos 159-172: cuota retención
    linea += "01"                                         # pos 173-174: impreso 347
    linea += "S"                                          # pos 175: operación sujeta IVA
    linea += "N"                                          # pos 176: modelo 415 (no aplica)
    linea += " "                                          # pos 177: criterio caja
    linea += " " * 14                                     # pos 178-191: reserva
    cuenta_iva = servicio.get("cuenta_iva_soportado", "4720000")
    linea += _pad_right(cuenta_iva, 12)                   # pos 192-203: cuenta IVA
    linea += " " * 12                                     # pos 204-215: cuenta recargo
    cuenta_ret = servicio.get("cuenta_tesoreria", "4751000") if tiene_irpf else " " * 12
    if tiene_irpf and es_ultima:
        linea += _pad_right(cuenta_ret, 12)               # pos 216-227: cuenta retención
    else:
        linea += " " * 12
    linea += " " * 12                                     # pos 228-239: cuenta IVA 2
    linea += " " * 12                                     # pos 240-251: cuenta recargo 2
    linea += " "                                          # pos 252: tiene registro analítico
    linea += "E"                                          # pos 253: moneda
    linea += "N"                                          # pos 254: indicador generado
    assert len(linea) == 254, f"Detalle IVA: longitud {len(linea)} != 254"
    return linea + RETORNO_CARRO


def _registro_vencimiento(
    peg: dict,
    servicio: dict,
    proveedor: dict,
    codigo_empresa: str,
    fecha_pago: str,
) -> str:
    """
    Tipo V: Alta de vencimiento (pago por transferencia).
    """
    linea = ""
    linea += "4"                                          # pos 1
    linea += _pad_left(codigo_empresa, 5)                 # pos 2-6
    linea += _fecha_a3(fecha_pago)                        # pos 7-14: fecha vencimiento
    linea += "V"                                          # pos 15: tipo registro
    cuenta_prov = servicio.get("cuenta_proveedor", "4000000")
    linea += _pad_right(cuenta_prov, 12)                  # pos 16-27
    linea += _pad_right(proveedor.get("razon_social", ""), 30)  # pos 28-57
    linea += "P"                                          # pos 58: tipo vencimiento (P=pago)
    linea += _pad_right(peg.get("referencia_factura", str(peg["id_peg"])), 10)  # pos 59-68
    linea += " "                                          # pos 69: indicador ampliación
    desc = f"Pago PEG {peg.get('codigo_peg','')}"
    linea += _pad_right(desc, 30)                         # pos 70-99
    importe_neto = float(peg.get("importe_total", 0)) - float(peg.get("importe_irpf", 0))
    linea += _importe_a3(importe_neto)                    # pos 100-113: importe vencimiento
    linea += _fecha_a3(peg.get("fecha_factura") or datetime.today())  # pos 114-121: fecha factura
    cuenta_tes = servicio.get("cuenta_tesoreria", "5720000")
    linea += _pad_right(cuenta_tes, 12)                   # pos 122-133: cuenta tesorería
    linea += "  "                                         # pos 134-135: forma de pago
    linea += "  "                                         # pos 136-137: nº vencimiento
    linea += " " * 115                                    # pos 138-252: reserva
    linea += "E"                                          # pos 253: moneda
    linea += "N"                                          # pos 254: indicador generado
    assert len(linea) == 254, f"Vencimiento: longitud {len(linea)} != 254"
    return linea + RETORNO_CARRO


def _registro_analitica(
    peg: dict,
    linea_iva: dict,
    servicio: dict,
    codigo_empresa: str,
    num_linea: int,
    es_unica: bool,
    analitica: dict,
    importe_linea: float,
    porcentaje: float,
) -> str:
    """
    Tipo D: Alta distribución analítica del apunte.
    Se genera una vez por cada entrada de lineas_analitica × linea_iva.
    """
    fecha = _fecha_a3(peg.get("fecha_factura") or datetime.today())
    linea = ""
    linea += "4"                                          # pos 1
    linea += _pad_left(codigo_empresa, 5)                 # pos 2-6
    linea += fecha                                        # pos 7-14
    linea += "D"                                          # pos 15
    linea += _pad_right(servicio.get("cuenta_gasto", "6000000"), 12)  # pos 16-27
    linea += _pad_right(servicio.get("nombre", ""), 30)   # pos 28-57
    linea += " "                                          # pos 58: reserva
    linea += _importe_a3(importe_linea)                   # pos 59-72: importe total línea
    linea += _pad_left(str(num_linea), 3)                 # pos 73-75: nº línea apunte
    linea += "I"                                          # pos 76: marcador distribución
    nivel_1 = _pad_right(str(analitica.get("nivel_1", "")), 4)
    nivel_2 = _pad_right(str(analitica.get("nivel_2", "")), 4)
    linea += nivel_1                                      # pos 77-80: código centro
    linea += nivel_2                                      # pos 81-84: código departamento
    linea += " " * 4                                      # pos 85-88: código división
    linea += " " * 4                                      # pos 89-92: código sección
    linea += _pad_right(analitica.get("descripcion", ""), 30)  # pos 93-122
    linea += " " * 30                                     # pos 123-152: descripción departamento
    linea += " " * 30                                     # pos 153-182: descripción división
    linea += " " * 30                                     # pos 183-212: descripción sección
    linea += _importe_a3(importe_linea)                   # pos 213-226: importe distribución
    linea += f"{porcentaje:06.2f}"                        # pos 227-232: porcentaje
    linea += " " * 20                                     # pos 233-252: reserva
    linea += "E"                                          # pos 253: moneda
    linea += "N"                                          # pos 254: indicador generado
    assert len(linea) == 254, f"Analítica: longitud {len(linea)} != 254"
    return linea + RETORNO_CARRO


def generar_suenlace_remesa(
    id_remesa: int,
    empresa: str = "real",  # "real" o "prueba"
) -> tuple[str, str]:
    """
    Genera el contenido del fichero SUENLACE para una remesa cerrada.

    Devuelve: (contenido_fichero: str, nombre_fichero: str)
    El nombre sigue el patrón: RM{numero_remesa}{aaaammdd}.DAT
    Ej: RM3220250407.DAT
    """
    codigo_empresa = CODIGO_EMPRESA_REAL if empresa == "real" else CODIGO_EMPRESA_PRUEBA

    # Obtener remesa
    remesa = mock_data.get_remesa_por_id(id_remesa)
    if not remesa:
        raise ValueError(f"Remesa {id_remesa} no encontrada")
    if remesa.get("codigo_estado") not in ("CERRADA", "PAGADO"):
        raise ValueError("Solo se puede exportar una remesa cerrada")

    fecha_pago = remesa.get("fecha_cierre") or datetime.today()
    numero_remesa = remesa.get("numero_remesa", id_remesa)
    fecha_fichero = _fecha_a3(fecha_pago)
    nombre_fichero = f"RM{numero_remesa}{fecha_fichero}.DAT"

    lineas = []
    pegs_remesa = mock_data.get_pegs_por_remesa(id_remesa)

    for peg in pegs_remesa:
        servicio  = mock_data.get_servicio_por_id(peg["id_servicio"])
        proveedor = mock_data.get_proveedor_por_id(peg["id_proveedor"])
        lineas_iva = peg.get("lineas_iva", [])
        tiene_irpf = float(peg.get("importe_irpf", 0)) > 0

        if not lineas_iva:
            # PEG sin líneas IVA: crear una línea ficticia con el total
            lineas_iva = [{"base_imponible": peg.get("importe_total", 0),
                           "porcentaje_iva": 0, "cuota_iva": 0}]

        # Registro tipo 1 — cabecera factura
        lineas.append(_registro_cabecera_factura(
            peg, servicio, proveedor, codigo_empresa
        ))

        # Registros tipo 9 — detalle IVA (uno por línea)
        for idx, liva in enumerate(lineas_iva):
            es_primera = idx == 0
            es_ultima  = idx == len(lineas_iva) - 1
            lineas.append(_registro_detalle_iva(
                peg, liva, servicio, codigo_empresa,
                es_ultima=es_ultima,
                es_primera=es_primera,
                tiene_irpf=tiene_irpf,
            ))

        # Registro tipo V — vencimiento
        lineas.append(_registro_vencimiento(
            peg, servicio, proveedor, codigo_empresa, fecha_pago
        ))

        # Registros tipo D — una entrada por cada (linea_analitica × linea_iva)
        for linea_anal in peg.get("lineas_analitica", []):
            analitica = next(
                (a for a in ANALITICAS if a["id_analitica"] == linea_anal["id_analitica"]),
                None,
            )
            if not analitica:
                continue
            for idx, liva in enumerate(lineas_iva):
                importe_base = float(liva.get("base_imponible", 0))
                importe_linea = round(importe_base * linea_anal["porcentaje"] / 100, 2)
                contenido_d = _registro_analitica(
                    peg, liva, servicio, codigo_empresa,
                    num_linea=idx + 2,
                    es_unica=len(lineas_iva) == 1,
                    analitica=analitica,
                    importe_linea=importe_linea,
                    porcentaje=linea_anal["porcentaje"],
                )
                if contenido_d:
                    lineas.append(contenido_d)

    contenido = "".join(lineas)
    return contenido, nombre_fichero


def _generar_bloques_gasto_directo(
    gasto: dict,
    servicio: dict,
    proveedor: dict,
    codigo_empresa: str,
    fecha_pago: str,
) -> list[str]:
    """
    Genera los registros SUENLACE (1, 9, V, D) para un gasto directo.
    Reutiliza exactamente la misma lógica que los PEGs.
    El gasto se adapta al formato que esperan las funciones de registro.
    """
    # Adaptar campos del gasto directo al esquema que usan las funciones internas
    peg_compat = {
        "id_peg": gasto["id_gasto"],
        "codigo_peg": gasto["codigo"],
        "referencia_factura": gasto.get("referencia_factura") or str(gasto["id_gasto"]),
        "fecha_factura": gasto.get("fecha_documento"),
        "importe_total": gasto["importe_total"],
        "importe_irpf": gasto.get("irpf", 0),
        "lineas_analitica": gasto.get("lineas_analitica", []),
    }

    lineas_iva_raw = gasto.get("lineas_iva", [])
    if not lineas_iva_raw:
        lineas_iva_raw = [{"porcentaje_iva": 0, "base": gasto["importe_total"], "cuota": 0}]

    # Normalizar nombres de campos (el gasto usa "base"/"cuota", los registros esperan
    # "base_imponible"/"cuota_iva")
    lineas_iva = [
        {
            "base_imponible": l.get("base_imponible", l.get("base", 0)),
            "porcentaje_iva": l.get("porcentaje_iva", 0),
            "cuota_iva":      l.get("cuota_iva", l.get("cuota", 0)),
        }
        for l in lineas_iva_raw
    ]

    tiene_irpf = float(gasto.get("irpf", 0)) > 0
    bloques: list[str] = []

    bloques.append(_registro_cabecera_factura(
        peg_compat, servicio, proveedor, codigo_empresa
    ))

    for idx, liva in enumerate(lineas_iva):
        bloques.append(_registro_detalle_iva(
            peg_compat, liva, servicio, codigo_empresa,
            es_ultima=idx == len(lineas_iva) - 1,
            es_primera=idx == 0,
            tiene_irpf=tiene_irpf,
        ))

    bloques.append(_registro_vencimiento(
        peg_compat, servicio, proveedor, codigo_empresa, fecha_pago
    ))

    for linea_anal in peg_compat["lineas_analitica"]:
        analitica = next(
            (a for a in ANALITICAS if a["id_analitica"] == linea_anal["id_analitica"]),
            None,
        )
        if not analitica:
            continue
        for idx, liva in enumerate(lineas_iva):
            importe_base  = float(liva.get("base_imponible", 0))
            importe_linea = round(importe_base * linea_anal["porcentaje"] / 100, 2)
            bloques.append(_registro_analitica(
                peg_compat, liva, servicio, codigo_empresa,
                num_linea=idx + 2,
                es_unica=len(lineas_iva) == 1,
                analitica=analitica,
                importe_linea=importe_linea,
                porcentaje=linea_anal["porcentaje"],
            ))

    return bloques


def generar_suenlace_remesa_directa(
    id_remesa_directa: int,
    empresa: str = "real",
) -> tuple[str, str]:
    """
    Genera el fichero SUENLACE para una remesa directa cerrada.

    Devuelve: (contenido_fichero: str, nombre_fichero: str)
    El nombre sigue el patrón: RM{numero}D{aaaammdd}.DAT
    La 'D' distingue remesa Directa de remesa normal.
    """
    from app.mock_data import GASTOS_DIRECTOS, REMESAS_DIRECTAS
    from app.services.pegs_service import _servicios
    from app.services.proveedores_service import proveedores_db

    codigo_empresa = CODIGO_EMPRESA_REAL if empresa == "real" else CODIGO_EMPRESA_PRUEBA

    remesa = next((r for r in REMESAS_DIRECTAS if r["id_remesa_directa"] == id_remesa_directa), None)
    if not remesa:
        raise ValueError(f"Remesa directa {id_remesa_directa} no encontrada")
    if remesa["estado"] not in ("CERRADA",):
        raise ValueError("Solo se puede exportar una remesa directa cerrada")

    fecha_cierre  = remesa.get("fecha_cierre") or datetime.today().strftime("%Y-%m-%d")
    fecha_fichero = _fecha_a3(fecha_cierre)
    numero        = remesa.get("numero", id_remesa_directa)
    nombre_fichero = f"RM{numero}D{fecha_fichero}.DAT"

    servicios_map   = {s["id_servicio"]: s for s in _servicios}
    proveedores_map = {p["id_proveedor"]: p for p in proveedores_db}

    gastos = [g for g in GASTOS_DIRECTOS if g.get("remesa_directa_id") == id_remesa_directa]

    lineas: list[str] = []
    for gasto in gastos:
        servicio  = servicios_map.get(gasto.get("servicio_id"), {})
        proveedor = proveedores_map.get(gasto.get("proveedor_id"), {})
        lineas.extend(_generar_bloques_gasto_directo(
            gasto, servicio, proveedor, codigo_empresa, fecha_cierre
        ))

    return "".join(lineas), nombre_fichero


def generar_suenlace_remesa_bancaria(
    id_rd: int,
    empresa: str = "real",
) -> tuple[str, str]:
    """
    Genera el fichero SUENLACE para una remesa directa bancaria.

    Asiento por cada línea analítica:
      DEBE  → cuenta de gasto (grupo 6) de la línea
      HABER → cuenta de tesorería del banco (grupo 57)
      Analítica: servicio_proyecto con porcentaje 100 % por línea

    Nombre del fichero: RDB{id_rd}{aaaammdd}.DAT
    """
    from app.services.mock_remesas_directas import obtener_remesa_directa
    from app.services.mock_bancos import obtener_banco

    codigo_empresa = CODIGO_EMPRESA_REAL if empresa == "real" else CODIGO_EMPRESA_PRUEBA

    rd = obtener_remesa_directa(id_rd)
    if not rd:
        raise ValueError(f"Remesa directa bancaria {id_rd} no encontrada")

    banco = obtener_banco(rd["id_banco"]) or {}
    cuenta_tesoreria = banco.get("cuenta_contable", "5720000")

    fecha_rd       = rd.get("fecha_creacion") or datetime.today().strftime("%Y-%m-%d")
    fecha_fichero  = _fecha_a3(fecha_rd)
    nombre_fichero = f"RDB{id_rd}{fecha_fichero}.DAT"

    # Si no hay líneas usamos una sola con el total
    lineas = rd.get("lineas") or [{
        "cuenta_gasto":      rd.get("cuenta_gasto", "6200000"),
        "servicio_proyecto": "",
        "porcentaje":        100.0,
        "importe":           rd["importe_total"],
        "descripcion_linea": rd.get("descripcion", ""),
    }]

    registros: list[str] = []

    for idx, linea in enumerate(lineas):
        cuenta_gasto = linea.get("cuenta_gasto") or rd.get("cuenta_gasto", "6200000")
        desc         = linea.get("descripcion_linea") or rd.get("descripcion", "")
        importe      = float(linea.get("importe", 0))
        srv_proy     = str(linea.get("servicio_proyecto", "") or "").strip()

        # Dict compatible con las funciones de registro existentes
        peg_like = {
            "id_peg":             id_rd,
            "codigo_peg":         f"RDB-{id_rd}-{idx + 1}",
            "referencia_factura": f"RDB{id_rd}L{idx + 1}",
            "fecha_factura":      fecha_rd,
            "importe_total":      importe,
            "importe_irpf":       0.0,
        }
        # cuenta_proveedor = HABER (tesorería banco, grupo 57)
        # cuenta_gasto     = DEBE  (gasto, grupo 6)
        servicio_like = {
            "cuenta_proveedor":    cuenta_tesoreria,
            "cuenta_gasto":        cuenta_gasto,
            "nombre":              desc,
            "cuenta_iva_soportado": "4720000",
            "cuenta_tesoreria":    cuenta_tesoreria,
        }
        proveedor_like = {
            "razon_social": banco.get("alias", "BANCO"),
            "cif_nif":      "",
            "codigo_postal": "",
        }
        liva = {
            "base_imponible": importe,
            "porcentaje_iva": 0.0,
            "cuota_iva":      0.0,
        }

        registros.append(_registro_cabecera_factura(
            peg_like, servicio_like, proveedor_like, codigo_empresa,
        ))
        registros.append(_registro_detalle_iva(
            peg_like, liva, servicio_like, codigo_empresa,
            es_ultima=True, es_primera=True, tiene_irpf=False,
        ))
        registros.append(_registro_vencimiento(
            peg_like, servicio_like, proveedor_like, codigo_empresa, fecha_rd,
        ))

        if srv_proy:
            analitica_like = {
                "nivel_1":     srv_proy[:4],
                "nivel_2":     "",
                "descripcion": srv_proy[:30],
            }
            registros.append(_registro_analitica(
                peg_like, liva, servicio_like, codigo_empresa,
                num_linea=2,
                es_unica=True,
                analitica=analitica_like,
                importe_linea=importe,
                porcentaje=100.0,
            ))

    return "".join(registros), nombre_fichero
