"""
Generador del número de factura interna de FGULEM.
Formato: F{digito_año}{correlativo_3_cifras}{mes_3_letras}
Ejemplo: F6042ABR  →  factura nº 42 de abril de 2026
El correlativo es único para toda la fundación.
"""

from datetime import datetime
from app.services import pegs_service as mock_data

MESES = {
    1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR",
    5: "MAY", 6: "JUN", 7: "JUL", 8: "AGO",
    9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"
}


def _digito_anio(anio: int) -> str:
    """2026→'6', 2027→'7', 2030→'0', etc."""
    return str(anio % 10)


def _siguiente_correlativo(anio: int, mes: int) -> int:
    """
    Devuelve el siguiente correlativo para el mes y año dados.
    El contador se reinicia cada mes — es independiente por mes.
    """
    pegs = mock_data.listar_pegs_todos()
    mes_str = MESES[mes]
    digito_anio = str(anio % 10)
    maximo = 0
    for peg in pegs:
        nf = peg.get("numero_factura_interno")
        if not nf or not isinstance(nf, str) or len(nf) != 8:
            continue
        # Formato: F{digito_año}{correlativo_3}{mes_3}
        # Ejemplo: F6042ABR
        if nf[0] != "F":
            continue
        if nf[1] != digito_anio:
            continue
        if nf[5:] != mes_str:
            continue
        try:
            correlativo = int(nf[2:5])
            if correlativo > maximo:
                maximo = correlativo
        except ValueError:
            pass
    return maximo + 1


def generar_numero_factura(fecha: datetime | None = None) -> str:
    """
    Genera el siguiente número de factura interno.
    fecha: datetime de referencia (por defecto hoy).
    """
    if fecha is None:
        fecha = datetime.now()
    digito_anio = _digito_anio(fecha.year)
    correlativo = str(_siguiente_correlativo(
        fecha.year, fecha.month)).zfill(3)
    mes = MESES[fecha.month]
    return f"F{digito_anio}{correlativo}{mes}"


def validar_formato(numero: str) -> bool:
    """Valida que un string tiene formato correcto de factura interna."""
    if len(numero) != 8:
        return False
    if numero[0] != "F":
        return False
    if not numero[1].isdigit():
        return False
    if not numero[2:5].isdigit():
        return False
    if numero[5:] not in MESES.values():
        return False
    return True
