import pandas as pd
import numbers
import os
import re
import datetime
import io
from sqlalchemy.orm import Session
from schemas import CotizacionRequest, CotizacionResponse, ItemCotizadoResponse
import models
from services.excel_service import excel_store
from services.argenstats_svc import argenstats_svc

HISTORIC_DOLAR = 830.25

def clean_text(s):
    if s is None:
        return ""
    try:
        if pd.isna(s):
            return ""
    except Exception:
        pass
    s = str(s).strip()
    s = s.replace('\xa0', ' ')
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s

def get_descripcion_robusta(code):
    posibles_cols_desc = ['Descripción', 'Descripcion', 'DESCRIPCIÓN', 'Desc', 'descripcion', 'descripcion ']
    for df in (excel_store.df_pc, excel_store.df_ci, excel_store.df_fab):
        sub = df[df['Código de artículo'] == code]
        if sub.empty:
            continue
        if 'Número' in sub.columns:
            sufijo = sub['Número'].astype(str).str.extract(r'(\d+)$')[0]
            if sufijo.notna().any():
                sub_temp = sub.copy()
                sub_temp['_sort_num'] = pd.to_numeric(sufijo, errors='coerce').fillna(-1)
                row = sub_temp.sort_values('_sort_num', ascending=False).iloc[0]
            else:
                row = sub.iloc[-1]
        else:
            row = sub.iloc[-1]
        cols = [c for c in row.index if any(p.lower() in str(c).lower() for p in ['descr', 'desc'])]
        for c in cols:
            val = clean_text(row.get(c, ""))
            if val and not val.lstrip().startswith('='):
                return val
    return ""

def cotizador(items, dolar_hoy=None, inflacion_manual=None):
    if dolar_hoy and float(dolar_hoy) > 0:
        valor_dolar = float(dolar_hoy)
    else:
        valor_dolar = argenstats_svc.get_dolar_hoy()
    
    cache = {}               
    cache_source = {}        
    cache_original = {}      
    cache_date = {}          
    cache_metodo = {} # <-- NUEVO: Diccionario para guardar el método de ajuste
    codigos_padres = {}
    precios_finales = []

    posibles_cols_cant_final = ['Cantidad finalizada', 'Cantidad_finalizada', 'Cantidad Finalizada', 'Cant Finalizada']

    def pick_latest_row(df, sort_col='Número'):
        if df is None or df.empty:
            return None
        if sort_col in df.columns:
            sufijo = df[sort_col].astype(str).str.extract(r'(\d+)$')[0]
            if sufijo.notna().any():
                df_temp = df.copy()
                df_temp['_sort_num'] = pd.to_numeric(sufijo, errors='coerce').fillna(-1)
                return df_temp.sort_values('_sort_num', ascending=False).iloc[0]
            else:
                return df.sort_values(sort_col, ascending=False).iloc[0]
        else:
            return df.iloc[-1] if not df.empty else None

    def get_finalizada_from_row(row):
        for col in posibles_cols_cant_final:
            if col in row.index:
                try:
                    val = pd.to_numeric(row[col], errors='coerce')
                    if pd.isna(val):
                        return None
                    return float(val)
                except Exception:
                    return None
        return None

    def resolve_unitario(code, recursion_stack):
        if code is None:
            cache[code] = 'Nada'
            cache_metodo[code] = 'Nada'
            return 'Nada'
        if code in cache:
            return cache[code]
        if code in recursion_stack:
            cache[code] = 'Nada'
            cache_metodo[code] = 'Nada'
            return 'Nada'
        recursion_stack.add(code)

        # 1) df_pc
        resultado_pc = excel_store.df_pc[excel_store.df_pc['Código de artículo'] == code]
        if not resultado_pc.empty:
            resultado_pc_local = resultado_pc.copy()
            resultado_pc_local['__costo_num'] = pd.to_numeric(resultado_pc_local.get('Costo unitario', pd.Series(dtype=float)), errors='coerce')
            filas_con_costo = resultado_pc_local[resultado_pc_local['__costo_num'].notna()]
            row = None
            if not filas_con_costo.empty:
                row = pick_latest_row(filas_con_costo, 'Número')
            if row is not None:
                precio_raw = pd.to_numeric(row.get('Costo unitario', None), errors='coerce')
                if not pd.isna(precio_raw):
                    precio = float(precio_raw)
                    fecha_compra = pd.NaT
                    numero_pc = row.get('Número', '')
                    if not excel_store.df_rec.empty:
                        matching_rec = excel_store.df_rec[(excel_store.df_rec['Número de PC'] == numero_pc) & (excel_store.df_rec['Código de artículo'] == code)]
                        if not matching_rec.empty:
                            fs = matching_rec.iloc[0].get('Fecha')
                            if pd.notna(fs):
                                fecha_compra = pd.to_datetime(fs, errors='coerce')
                    
                    if pd.notna(fecha_compra):
                        cache_original[code] = float(precio_raw)
                        cache_date[code] = fecha_compra
                        dias_diff = (pd.Timestamp.now() - fecha_compra).days
                        meses_diff = dias_diff / 30.44
                        
                        # --- NUEVA LÓGICA DE MESES ---
                        if meses_diff < 1:
                            # Menos de 1 mes: No se toca
                            precio = precio_raw
                            cache_metodo[code] = "Sin actualizar"
                        elif meses_diff < 3:
                            # 1 a 3 meses: Inflación
                            if inflacion_manual and float(inflacion_manual) > 0:
                                factor = (1 + float(inflacion_manual)) ** meses_diff
                            else:
                                factor = argenstats_svc.get_inflation_factor(fecha_compra, pd.Timestamp.now())
                            precio = precio * factor
                            cache_metodo[code] = "Inflación"
                        else:
                            # Más de 3 meses: Dólar
                            precio = (precio / HISTORIC_DOLAR) * valor_dolar
                            cache_metodo[code] = "Dólar"
                    else:
                        cache_original[code] = float(precio_raw)
                        cache_date[code] = "Sin Fecha"
                        precio = (precio / HISTORIC_DOLAR) * valor_dolar
                        cache_metodo[code] = "Dólar"

                    precio = float(round(precio, 2))
                    cache[code] = precio
                    cache_source[code] = 'pc'
                    recursion_stack.remove(code)
                    return precio

        # 2) df_ci
        resultado_ci = excel_store.df_ci[excel_store.df_ci['Código de artículo'] == code]
        if not resultado_ci.empty:
            resultado_ci_local = resultado_ci.copy()
            resultado_ci_local['__costo_num'] = pd.to_numeric(resultado_ci_local.get('Costo unitario', pd.Series(dtype=float)), errors='coerce')
            filas_con_costo_ci = resultado_ci_local[resultado_ci_local['__costo_num'].notna()]
            row = None
            if not filas_con_costo_ci.empty:
                row = pick_latest_row(filas_con_costo_ci, 'Número')
            if row is not None:
                precio_raw = pd.to_numeric(row.get('Costo unitario', None), errors='coerce')
                if not pd.isna(precio_raw):
                    cache_original[code] = float(precio_raw)
                    cache_date[code] = "Sin Fecha"
                    cache_metodo[code] = "Dólar (Costo Inicial)" # Asumimos Dólar para los iniciales
                    if dolar_hoy is not None:
                        precio_ajustado = round((float(precio_raw) / HISTORIC_DOLAR) * float(dolar_hoy), 2)
                        cache[code] = precio_ajustado
                        cache_source[code] = 'ci'
                        recursion_stack.remove(code)
                        return precio_ajustado
                    else:
                        precio_val = float(round(precio_raw, 2))
                        cache[code] = precio_val
                        cache_source[code] = 'ci'
                        recursion_stack.remove(code)
                        return precio_val

        # 3) df_fab -> df_salidas
        resultado_fab = excel_store.df_fab[excel_store.df_fab['Código de artículo'] == code]
        if not resultado_fab.empty:
            fila_fab = pick_latest_row(resultado_fab, 'Número')
            if fila_fab is None:
                cache[code] = 'Nada'
                cache_metodo[code] = 'Nada'
                recursion_stack.remove(code)
                return 'Nada'
            numero = fila_fab.get('Número', None)
            finalizada = get_finalizada_from_row(fila_fab)
            if pd.isna(numero) or numero is None or finalizada in (None, 0):
                cache[code] = 'Nada'
                cache_metodo[code] = 'Nada'
                recursion_stack.remove(code)
                return 'Nada'
            
            filtro_pedido = excel_store.df_salidas['Pedido'].astype(str).str.startswith(str(numero), na=False)
            res_salidas = excel_store.df_salidas[filtro_pedido]
            if res_salidas.empty:
                cache[code] = 'Nada'
                cache_metodo[code] = 'Nada'
                recursion_stack.remove(code)
                return 'Nada'

            cantidades = (pd.to_numeric(res_salidas['Cantidad'], errors='coerce').fillna(0).abs()
                          .groupby(res_salidas['Código de artículo'])
                          .sum())

            codigos_padres[code] = []
            suma_contribuciones = 0.0
            suma_originales = 0.0
            any_numeric = False

            for hijo, qty in cantidades.items():
                precio_unit_hijo = resolve_unitario(hijo, recursion_stack)
                orig_hijo = cache_original.get(hijo, 'Nada')

                if isinstance(precio_unit_hijo, numbers.Real):
                    contrib = round(float(precio_unit_hijo) * float(qty), 2)
                    suma_contribuciones += contrib
                    any_numeric = True
                    
                    if isinstance(orig_hijo, numbers.Real):
                        suma_originales += round(float(orig_hijo) * float(qty), 2)
                else:
                    contrib = 'Nada'

                codigos_padres[code].append((hijo, float(qty), precio_unit_hijo, contrib))

            if any_numeric:
                unitario_padre = round(suma_contribuciones / float(finalizada), 2)
                orig_padre = round(suma_originales / float(finalizada), 2)
                cache[code] = float(unitario_padre)
                cache_original[code] = float(orig_padre)
                cache_date[code] = "FAB (Calculado)"
                cache_source[code] = 'computed'
                cache_metodo[code] = "Calculado (Sub-ítems)"
                recursion_stack.remove(code)
                return float(unitario_padre)
            else:
                cache[code] = 'Nada'
                cache_metodo[code] = 'Nada'
                recursion_stack.remove(code)
                return 'Nada'

        # 4) nada
        cache[code] = 'Nada'
        cache_metodo[code] = 'Nada'
        recursion_stack.remove(code)
        return 'Nada'

    for codigo in items:
        unitario = resolve_unitario(codigo, set())
        precios_finales.append((codigo, unitario))

    # Devolvemos también el diccionario cache_metodo
    return precios_finales, codigos_padres, cache_source, cache_original, cache_date, cache_metodo


def procesar_cotizacion(req: CotizacionRequest, db: Session):
    from services.excel_service import load_excel_data
    load_excel_data()

    # Recibimos el nuevo mapa de métodos
    precios_obtenidos, mapa, source_map, original_map, date_map, metodo_map = cotizador(
        items=req.codigos_items, 
        dolar_hoy=req.dolar_hoy, 
        inflacion_manual=req.inflacion
    )

    items_res = []
    
    for codigo, precio in precios_obtenidos:
        descripcion = get_descripcion_robusta(codigo)
        cantidad_utilizada = 1.0
        origen = source_map.get(codigo, 'Nada')
        
        precio_final = precio
        if isinstance(precio, numbers.Real) and origen == 'ci':
            if req.dolar_hoy is not None:
                precio_final = round((float(precio) / HISTORIC_DOLAR) * float(req.dolar_hoy), 2)

        costo_total = None
        if isinstance(precio_final, numbers.Real):
            costo_total = round(cantidad_utilizada * float(precio_final), 2)
            
        costo_sistema = original_map.get(codigo, 'Nada')
        fecha_costo = date_map.get(codigo, "Sin Fecha")
        if isinstance(fecha_costo, pd.Timestamp):
            fecha_costo = fecha_costo.strftime('%Y-%m-%d')
            
        # Obtenemos el método de ajuste
        metodo = metodo_map.get(codigo, "-")

        def parse_to_float(val):
            return float(val) if isinstance(val, numbers.Real) else None

        item_data = ItemCotizadoResponse(
            codigo=codigo,
            descripcion=descripcion,
            cantidad_utilizada=cantidad_utilizada,
            costo_unitario_sistema=parse_to_float(costo_sistema),
            fecha_costo=str(fecha_costo),
            precio_actualizado=parse_to_float(precio_final),
            costo_total=parse_to_float(costo_total),
            metodo_ajuste=metodo  # Agregamos al response
        )
        items_res.append(item_data)

    if req.guardar_db and req.conjunto_nombre and req.subconjunto_nombre:
        conjunto = db.query(models.Conjunto).filter(models.Conjunto.nombre == req.conjunto_nombre).first()
        if not conjunto:
            conjunto = models.Conjunto(nombre=req.conjunto_nombre)
            db.add(conjunto)
            db.commit()
            db.refresh(conjunto)
            
        subconjunto = db.query(models.Subconjunto).filter(
            models.Subconjunto.nombre == req.subconjunto_nombre,
            models.Subconjunto.conjunto_id == conjunto.id
        ).first()
        if not subconjunto:
            subconjunto = models.Subconjunto(nombre=req.subconjunto_nombre, conjunto_id=conjunto.id)
            db.add(subconjunto)
            db.commit()
            db.refresh(subconjunto)

        for it in items_res:
            nueva_tarea = models.TareaCotizada(
                codigo_articulo=it.codigo,
                descripcion=it.descripcion,
                costo_unitario_sistema=it.costo_unitario_sistema,
                fecha_costo=it.fecha_costo,
                precio_actualizado=it.precio_actualizado,
                costo_total=it.costo_total,
                subconjunto_id=subconjunto.id,
                dolar_usado=req.dolar_hoy,
                inflacion_usada=req.inflacion
            )
            db.add(nueva_tarea)
        db.commit()

    archivo_descargable = None
    if req.exportar_excel:
        import base64
        df_out = pd.DataFrame([it.model_dump() for it in items_res])
        # Actualizamos las columnas del Excel para incluir el Método
        df_out.columns = ['Codigo', 'Descripcion', 'Cantidad Utilizada', 'Costo unitario sistema', 'Fecha del costo', 'Precio actualizado', 'Costo Total', 'Metodo de Ajuste']
        buffer = io.BytesIO()
        df_out.to_excel(buffer, index=False)
        buffer.seek(0)
        archivo_descargable = base64.b64encode(buffer.read()).decode()

    return CotizacionResponse(
        mensaje="Cotización realizada con éxito.",
        conjunto=req.conjunto_nombre,
        subconjunto=req.subconjunto_nombre,
        items=items_res,
        archivo_descargable=archivo_descargable
    )