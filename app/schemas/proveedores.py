from pydantic import BaseModel, EmailStr
from typing import Optional


class ProveedorBase(BaseModel):
    tipo_persona: str
    cif_nif: str
    razon_social: str
    nombre_comercial: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    iban: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None
    codigo_postal: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = "ES"
    cuenta_cliente: Optional[str] = None


class ProveedorCrear(ProveedorBase):
    pass


class Proveedor(ProveedorBase):
    id_proveedor: int
