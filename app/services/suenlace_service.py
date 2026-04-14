"""
Generador del fichero SUENLACE para importación en A3Con (Wolters Kluwer).
Especificación: enlace contable de entrada, registros de 256 bytes.
"""

import os
from datetime import datetime
from typing import Optional
from app.services import mock_data  # 🔧 PERSONALIZAR: cambiar a acceso real a BD

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
) -> str:
    """
    Tipo D: Alta distribución analítica del apunte.
    Solo se genera si el PEG tiene id_analitica asignada.
    """
    analitica = None
    if peg.get("id_analitica"):
        analitica = mock_data.get_analitica_por_id(peg["id_analitica"])
    if not analitica:
        return ""

    fecha = _fecha_a3(peg.get("fecha_factura") or datetime.today())
    linea = ""
    linea += "4"                                          # pos 1
    linea += _pad_left(codigo_empresa, 5)                 # pos 2-6
    linea += fecha                                        # pos 7-14
    linea += "D"                                          # pos 15
    linea += _pad_right(servicio.get("cuenta_gasto", "6000000"), 12)  # pos 16-27
    linea += _pad_right(servicio.get("nombre", ""), 30)   # pos 28-57
    linea += " "                                          # pos 58: reserva
    base = float(linea_iva.get("base_imponible", 0))
    linea += _importe_a3(base)                            # pos 59-72: importe total
    linea += _pad_left(str(num_linea), 3)                 # pos 73-75: nº línea apunte
    marcador_dist = "I" if es_unica else "I"              # única línea de distribución
    linea += marcador_dist                                # pos 76
    # Códigos analíticos: nivel_1 (4 chars) y nivel_2 si existe
    nivel_1 = _pad_right(str(analitica.get("codigo_nivel_1", "")), 4)
    nivel_2 = _pad_right(str(analitica.get("codigo_nivel_2", "")), 4)
    linea += nivel_1                                      # pos 77-80: código centro
    linea += nivel_2                                      # pos 81-84: código departamento
    linea += " " * 4                                      # pos 85-88: código división
    linea += " " * 4                                      # pos 89-92: código sección
    linea += _pad_right(analitica.get("nombre_nivel_1", ""), 30)    # pos 93-122
    linea += _pad_right(analitica.get("nombre_nivel_2", ""), 30)    # pos 123-152
    linea += " " * 30                                     # pos 153-182: descripción división
    linea += " " * 30                                     # pos 183-212: descripción sección
    linea += _importe_a3(base)                            # pos 213-226: importe distribución
    linea += "100.00"                                     # pos 227-232: porcentaje (100%)
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

        # Registros tipo D — analítica (uno por línea IVA si tiene analítica)
        if peg.get("id_analitica"):
            for idx, liva in enumerate(lineas_iva):
                contenido_d = _registro_analitica(
                    peg, liva, servicio, codigo_empresa,
                    num_linea=idx + 2,   # +2 porque la línea 1 es el registro tipo 1
                    es_unica=len(lineas_iva) == 1,
                )
                if contenido_d:
                    lineas.append(contenido_d)

    contenido = "".join(lineas)
    return contenido, nombre_fichero
