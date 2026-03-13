import pandas as pd
import os

class ExcelDataStore:
    def __init__(self):
        self.df_pc = pd.DataFrame()
        self.df_ci = pd.DataFrame()
        self.df_fab = pd.DataFrame()
        self.df_rec = pd.DataFrame()
        self.df_salidas = pd.DataFrame()
        self.is_loaded = False

excel_store = ExcelDataStore()

def load_excel_data():
    if excel_store.is_loaded:
        return
        
    # Detectamos la carpeta donde está este archivo y buscamos el Excel en la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_archivo = os.path.join(base_dir, 'Inventario Equipamientos.xlsm')
    
    if not os.path.exists(ruta_archivo):
        print(f"ERROR: No se encontró el archivo Excel en {ruta_archivo}")
        return

    print(f"Cargando Excel a memoria (en segundo plano) desde: {ruta_archivo}...")
    try:
        excel_store.df_pc = pd.read_excel(ruta_archivo, sheet_name='Líneas de PC (Compras)')
        excel_store.df_ci = pd.read_excel(ruta_archivo, sheet_name='Costo indirecto (Items)')
        excel_store.df_fab = pd.read_excel(ruta_archivo, sheet_name='Fabricación')
        excel_store.df_rec = pd.read_excel(ruta_archivo, sheet_name='Recepciones')
        excel_store.df_salidas = pd.read_excel(ruta_archivo, sheet_name='Salida artículos')
        excel_store.is_loaded = True
        print("Excel cargado exitosamente en memoria.")
    except Exception as e:
        print(f"Error crítico cargando Excel: {e}")
