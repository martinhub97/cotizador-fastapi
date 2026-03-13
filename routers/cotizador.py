from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import CotizacionRequest, CotizacionResponse
from services.cotizador_svc import procesar_cotizacion

router = APIRouter(
    prefix="/api/v1/cotizar",
    tags=["Cotizador"]
)

@router.post("/", response_model=CotizacionResponse)
def cotizar_items(req: CotizacionRequest, db: Session = Depends(get_db)):
    try:
        return procesar_cotizacion(req, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
