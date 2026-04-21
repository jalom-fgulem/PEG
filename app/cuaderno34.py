"""
cuaderno34.py
Generador de fichero bancario Cuaderno 34 — formato XML ISO 20022
Estándar: pain.001.001.09 — SEPA Credit Transfer
Guía AEB/CECA/UNACC v1.0 RB 2023 (vigente desde 17/03/2024)
"""

import io
import uuid
from datetime import date, datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.auth import require_rol
from app.services import mock_bancos, remesas_service

router = APIRouter(tags=["remesas"])

ORDENANTE_NIF    = "G24356644"
ORDENANTE_NOMBRE = "FUNDACION GENERAL UNIVERSIDAD DE LEON Y EMPRESA"
ORDENANTE_CIUDAD = "LEON"
NS = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"


def limpiar_iban(iban: str | None) -> str:
    if not iban:
        return ""
    return iban.replace(" ", "")


def limpiar_texto(texto: str, max_len: int) -> str:
    if not texto:
        return ""
    tabla = str.maketrans("ÁÉÍÓÚáéíóúÑñÇç", "AEIOUaeiouNnCc")
    return texto.translate(tabla)[:max_len]


def importe_str(valor: float) -> str:
    return f"{valor:.2f}"


def msg_id_unico() -> str:
    return uuid.uuid4().hex[:35]


def construir_xml(remesa: dict, pegs: list[dict], banco: dict) -> bytes:
    """
    remesa : dict con id, referencia, fecha_pago
    pegs   : lista de dicts con id, referencia, iban, importe_total, proveedor_nombre
    banco  : dict con alias, bic, iban (de mock_bancos)
    """
    num_remesa    = str(remesa.get("referencia", remesa["id"]))
    fecha_pago    = remesa["fecha_pago"]
    now           = datetime.now()
    total_importe = sum(p["importe_total"] for p in pegs)
    num_ops       = len(pegs)

    iban_ordenante = limpiar_iban(banco.get("iban", ""))
    bic_ordenante  = banco.get("bic", "NOTPROVIDED")
    sufijo         = banco.get("sufijo", "")
    nif_sufijo     = f"{ORDENANTE_NIF}{sufijo}".strip()

    root = Element("CstmrCdtTrfInitn")
    root.set("xmlns", NS)

    # ── CABECERA ──────────────────────────────────────────────────────────────
    grp_hdr = SubElement(root, "GrpHdr")
    SubElement(grp_hdr, "MsgId").text    = msg_id_unico()
    SubElement(grp_hdr, "CreDtTm").text  = now.strftime("%Y-%m-%dT%H:%M:%S")
    SubElement(grp_hdr, "NbOfTxs").text  = str(num_ops)
    SubElement(grp_hdr, "CtrlSum").text  = importe_str(total_importe)

    initg_pty = SubElement(grp_hdr, "InitgPty")
    SubElement(initg_pty, "Nm").text = limpiar_texto(ORDENANTE_NOMBRE, 70)
    othr = SubElement(SubElement(SubElement(initg_pty, "Id"), "OrgId"), "Othr")
    SubElement(othr, "Id").text = nif_sufijo[:35]
    SubElement(SubElement(othr, "SchmeNm"), "Prtry").text = "NIF"

    # ── BLOQUE DE PAGO ────────────────────────────────────────────────────────
    pmt_inf = SubElement(root, "PmtInf")
    SubElement(pmt_inf, "PmtInfId").text  = f"PMTINF-{num_remesa}"[:35]
    SubElement(pmt_inf, "PmtMtd").text    = "TRF"
    SubElement(pmt_inf, "BtchBookg").text = "true"
    SubElement(pmt_inf, "NbOfTxs").text   = str(num_ops)
    SubElement(pmt_inf, "CtrlSum").text   = importe_str(total_importe)

    SubElement(SubElement(SubElement(pmt_inf, "PmtTpInf"), "SvcLvl"), "Cd").text = "SEPA"

    SubElement(SubElement(pmt_inf, "ReqdExctnDt"), "Dt").text = (
        fecha_pago.strftime("%Y-%m-%d") if hasattr(fecha_pago, "strftime")
        else str(fecha_pago)
    )

    dbtr = SubElement(pmt_inf, "Dbtr")
    SubElement(dbtr, "Nm").text = limpiar_texto(ORDENANTE_NOMBRE, 70)
    pstl = SubElement(dbtr, "PstlAdr")
    SubElement(pstl, "TwnNm").text = ORDENANTE_CIUDAD
    SubElement(pstl, "Ctry").text  = "ES"

    SubElement(SubElement(SubElement(pmt_inf, "DbtrAcct"), "Id"), "IBAN").text = iban_ordenante

    dbtr_agt = SubElement(pmt_inf, "DbtrAgt")
    fin_id   = SubElement(dbtr_agt, "FinInstnId")
    if bic_ordenante and bic_ordenante != "NOTPROVIDED":
        SubElement(fin_id, "BICFI").text = bic_ordenante
    else:
        SubElement(SubElement(fin_id, "Othr"), "Id").text = "NOTPROVIDED"

    SubElement(pmt_inf, "ChrgBr").text = "SLEV"

    # ── TRANSFERENCIAS INDIVIDUALES ───────────────────────────────────────────
    for peg in pegs:
        concepto   = limpiar_texto(f"REMESA {num_remesa} {peg.get('referencia', str(peg['id']))}", 140)
        end_to_end = limpiar_texto(f"{num_remesa}-{peg.get('referencia', peg['id'])}", 35)
        instr_id   = limpiar_texto(str(peg.get("referencia", peg["id"])), 35)

        tx     = SubElement(pmt_inf, "CdtTrfTxInf")
        pmt_id = SubElement(tx, "PmtId")
        SubElement(pmt_id, "InstrId").text    = instr_id
        SubElement(pmt_id, "EndToEndId").text = end_to_end

        instd = SubElement(SubElement(tx, "Amt"), "InstdAmt")
        instd.set("Ccy", "EUR")
        instd.text = importe_str(peg["importe_total"])

        cdtr = SubElement(tx, "Cdtr")
        SubElement(cdtr, "Nm").text = limpiar_texto(peg["proveedor_nombre"], 70)
        SubElement(SubElement(cdtr, "PstlAdr"), "Ctry").text = "ES"

        SubElement(
            SubElement(SubElement(tx, "CdtrAcct"), "Id"), "IBAN"
        ).text = limpiar_iban(peg["iban"])

        SubElement(SubElement(tx, "RmtInf"), "Ustrd").text = concepto

    # ── SERIALIZACIÓN ─────────────────────────────────────────────────────────
    xml_str    = tostring(root, encoding="unicode")
    xml_pretty = minidom.parseString(
        f'<?xml version="1.0" encoding="UTF-8"?>{xml_str}'
    ).toprettyxml(indent="  ", encoding="UTF-8")

    return xml_pretty


@router.get("/remesas/{remesa_id}/cuaderno34")
def endpoint_cuaderno34(
    remesa_id: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa_obj = remesas_service.obtener_remesa(remesa_id)
    if not remesa_obj:
        raise HTTPException(404, "Remesa no encontrada")
    if remesa_obj.get("estado") not in ("GENERADA", "CERRADA"):
        raise HTTPException(400, "Solo se puede generar el archivo bancario de remesas en estado Generada o Cerrada")

    banco = mock_bancos.obtener_banco(remesa_obj.get("id_banco", 1))
    if not banco:
        raise HTTPException(400, "La remesa no tiene banco asignado")

    from app.services import pegs_service
    ids_peg = remesa_obj.get("pagos", [])
    pegs_obj = [p for p in pegs_service._pegs if p["id_peg"] in ids_peg]
    if not pegs_obj:
        raise HTTPException(400, "La remesa no tiene PEGs para generar el fichero")

    pegs = []
    sin_iban = []
    for p in pegs_obj:
        proveedor = pegs_service._proveedor_por_id(p["id_proveedor"])
        if not proveedor.get("iban"):
            sin_iban.append(p.get("codigo_peg", str(p["id_peg"])))
        pegs.append({
            "id":               p["id_peg"],
            "referencia":       p.get("codigo_peg", str(p["id_peg"])),
            "iban":             proveedor.get("iban") or "",
            "importe_total":    float(p.get("importe_total", 0)),
            "proveedor_nombre": proveedor.get("razon_social", ""),
        })
    if sin_iban:
        raise HTTPException(400, f"Los siguientes PEGs no tienen IBAN registrado: {', '.join(sin_iban)}")

    try:
        xml_bytes = construir_xml(
            {
                "id":         remesa_obj["id_remesa"],
                "referencia": remesa_obj.get("codigo_remesa", str(remesa_obj["id_remesa"])),
                "fecha_pago": remesa_obj.get("fecha_cierre") or date.today(),
            },
            pegs,
            banco,
        )
    except Exception as e:
        raise HTTPException(500, f"Error generando el fichero: {e}")

    nombre_fichero = f"C34_REM{remesa_id:04d}_{date.today().strftime('%Y%m%d')}.xml"

    return StreamingResponse(
        io.BytesIO(xml_bytes),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )
