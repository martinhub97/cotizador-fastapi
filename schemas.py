from pydantic import BaseModel
from typing import List, Optional

class CotizacionRequest(BaseModel):
    codigos_items: List[str]
    dolar_hoy: float
    inflacion: float
    conjunto_nombre: Optional[str] = None
    subconjunto_nombre: Optional[str] = None
    guardar_db: bool = False
    exportar_excel: bool = False

class ItemCotizadoResponse(BaseModel):
    codigo: str
    descripcion: str
    cantidad_utilizada: float
    costo_unitario_sistema: Optional[float] = None
    fecha_costo: str
    precio_actualizado: Optional[float] = None
    costo_total: Optional[float] = None

class CotizacionResponse(BaseModel):
    mensaje: str
    conjunto: Optional[str]
    subconjunto: Optional[str]
    items: List[ItemCotizadoResponse]
    archivo_descargable: Optional[str] = None
