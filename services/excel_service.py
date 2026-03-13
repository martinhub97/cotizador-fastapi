import pandas as pd
import os

class ExcelDataStore:
    df_salidas = pd.DataFrame()
    df_fab = pd.DataFrame()
    df_pc = pd.DataFrame()
    df_ci = pd.DataFrame()
    df_rec = pd.DataFrame()

excel_store = ExcelDataStore()

def load_excel_data():
    # Detectamos la carpeta donde está este archivo y buscamos el Excel en la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_archivo = os.path.join(base_dir, 'Inventario Equipamientos.xlsm')
    
    print(f"Cargando Excel a memoria desde: {ruta_archivo}...")
    try:
        excel_store.df_salidas = pd.read_excel(ruta_archivo, sheet_name='Salidas de inventario (Dep)')
        excel_store.df_fab = pd.read_excel(ruta_archivo, sheet_name='FAB (Adm)')
        excel_store.df_pc = pd.read_excel(ruta_archivo, sheet_name='Líneas de PC (Compras)')
        excel_store.df_ci = pd.read_excel(ruta_archivo, sheet_name='Costos iniciales')
        try:
            excel_store.df_rec = pd.read_excel(ruta_archivo, sheet_name='Recepciones de PC (Dep)')
        except Exception:
            excel_store.df_rec = pd.DataFrame(columns=['Fecha', 'Número de PC', 'Código de artículo'])
        print("Excel cargado exitosamente en memoria.")
    except Exception as e:
        print(f"Error crítico cargando Excel: {e}")
