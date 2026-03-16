from fastapi import APIRouter, File, UploadFile, HTTPException
import os
import shutil
from services.excel_service import load_excel_data
from services.argenstats_svc import argenstats_svc
from schemas import ArgenStatsParamsResponse
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Administracion"]
)

@router.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    # Validar que sea un archivo de Excel válido
    if not file.filename.endswith(('.xlsx', '.xlsm')):
        raise HTTPException(status_code=400, detail="El archivo no es un Excel válido (.xlsx o .xlsm)")

    # Detectar la ruta base donde debe ir el archivo "Inventario Equipamientos.xlsm"
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_archivo_destino = os.path.join(base_dir, 'Inventario Equipamientos.xlsm')

    try:
        # Guardar el nuevo archivo sobreescribiendo el viejo
        with open(ruta_archivo_destino, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Opcional: podrías verificar aquí que el archivo no esté corrupto intentando leer los sheets, 
        # pero confiaremos en que el usuario sube el formato correcto por rendimiento.

        # Forzar recarga del dataframe pandas en memoria
        load_excel_data(force_reload=True)

        return {"mensaje": "Inventario actualizado y recargado exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.get("/params", response_model=ArgenStatsParamsResponse)
async def get_argenstats_params():
    try:
        dolar = argenstats_svc.get_dolar_hoy()
        
        # Calcular inflación de los últimos 3 meses (desde hace 90 días a hoy)
        fin = datetime.now()
        inicio = fin - timedelta(days=90)
        inf_factor = argenstats_svc.get_inflation_factor(inicio, fin)
        
        return {
            "dolar": dolar,
            "inflacion_3m": inf_factor,
            "mensaje": "Parámetros obtenidos exitosamente de ArgenStats."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener parámetros de ArgenStats: {str(e)}")
