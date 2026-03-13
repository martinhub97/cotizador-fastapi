from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from database import engine, Base
import models
from routers.cotizador import router as cotizador_router
from services.excel_service import load_excel_data

# Crear tablas en BD al iniciar
try:
    models.Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Advertencia iniciando BDD: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cargar DataFrames en memoria al iniciar
    load_excel_data()
    yield
    # Limpiar recursos al apagar
    pass

app = FastAPI(
    title="Cotizador Agus API",
    description="API escalable para cotización de inventarios y conjuntos.",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(cotizador_router)

@app.get("/")
def read_root():
    return FileResponse("static/index.html")
