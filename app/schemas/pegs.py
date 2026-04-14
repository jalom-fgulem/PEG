from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from enum import Enum


class EstadoPeg(str, Enum):
    PENDIENTE  = "PENDIENTE"
    VALIDADO   = "VALIDADO"
    EN_REMESA  = "EN_REMESA"
    PAGADO     = "PAGADO"
    INCIDENCIA = "INCIDENCIA"


class LineaIVA(BaseModel):
    tipo_iva: float        # 0, 5, 10, 21
    base_imponible: float

    @property
    def importe_iva(self) -> float:
        return round(self.base_imponible * self.tipo_iva / 100, 2)

    @property
    def total_linea(self) -> float:
        return round(self.base_imponible + self.importe_iva, 2)


class PegCrear(BaseModel):
    id_servicio: int
    id_proyecto: Optional[int] = None
    id_proveedor: int
    id_peg_tipo: int
    numero_documento: str
    fecha_documento: date
    fecha_recepcion: date
    fecha_vencimiento: Optional[date] = None
    descripcion_gasto: str
    observaciones: Optional[str] = None
    id_forma_pago_prevista: int
    lineas: List[LineaIVA]
    tiene_irpf: bool = False
    tipo_irpf: float = 0.0   # 0, 7, 15, 19
    importe_irpf: float = 0.0
    id_analitica: Optional[int] = None
    creado_por: int = 1  # TODO: reemplazar por usuario de sesión


class PegCambioEstado(BaseModel):
    id_peg_estado_destino: int
    comentario: Optional[str] = None
    realizado_por: int = 1  # TODO: reemplazar por usuario de sesión
