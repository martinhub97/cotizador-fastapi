import pandas as pd
import numbers
import os        
import re        
import datetime
s
HISTORIC_DOLAR = 830.25  # ya tenías esto
ruta_archivo2 = r'C:\Users\marti\OneDrive - Colcarmerbus S.A\Escritorio\Conjuntos\Inventario Equipamientos.xlsm'
df = pd.read_excel(ruta_archivo2)
df_salidas = pd.read_excel(ruta_archivo2, sheet_name='Salidas de inventario (Dep)')
df_fab = pd.read_excel(ruta_archivo2, sheet_name='FAB (Adm)')
df_pc = pd.read_excel(ruta_archivo2, sheet_name='Líneas de PC (Compras)')
df_ci = pd.read_excel(ruta_archivo2, sheet_name='Costos iniciales')
try:
    df_rec = pd.read_excel(ruta_archivo2, sheet_name='Recepciones de PC (Dep)')
except Exception:
    df_rec = pd.DataFrame(columns=['Fecha', 'Número de PC', 'Código de artículo'])

def cotizador(items, dolar_hoy=None, inflacion=0.0, return_map=False):
    """
    items: iterable de códigos (tuple/list)
    dolar_hoy: si se pasa (float) se usa para ajustar precios antiguos a dólar
    inflacion: tasa de inflación mensual (ej. 0.05 para un 5%) a aplicar a precios menores a 3 meses
    return_map: si True devuelve (precios_finales, codigos_padres, cache_source)
    """
    cache = {}               # cache de precio unitario por código (ya ajustado si viene de df_ci)
    cache_source = {}        # origen original ('pc', 'ci', 'computed', 'Nada')
    cache_original = {}      # costo unitario sistema (sin ajustar)
    cache_date = {}          # fecha del costo
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
        # devuelve el precio unitario YA AJUSTADO si corresponde (float) o 'Nada'
        if code is None:
            cache[code] = 'Nada'
            cache_source[code] = 'Nada'
            return 'Nada'
        if code in cache:
            return cache[code]
        if code in recursion_stack:
            cache[code] = 'Nada'
            cache_source[code] = 'Nada'
            return 'Nada'
        recursion_stack.add(code)

        # 1) df_pc: preferir filas con costo unitario numérico
        resultado_pc = df_pc[df_pc['Código de artículo'] == code]
        if not resultado_pc.empty:
            resultado_pc_local = resultado_pc.copy()
            resultado_pc_local['__costo_num'] = pd.to_numeric(resultado_pc_local.get('Costo unitario', pd.Series([])), errors='coerce')
            filas_con_costo = resultado_pc_local[resultado_pc_local['__costo_num'].notna()]
            row = None
            if not filas_con_costo.empty:
                row = pick_latest_row(filas_con_costo, 'Número')
            if row is not None:
                precio_raw = pd.to_numeric(row.get('Costo unitario', None), errors='coerce')
                if not pd.isna(precio_raw):
                    precio = float(precio_raw)
                    # Buscar la fecha de esta compra
                    fecha_compra = pd.NaT
                    numero_pc = row.get('Número', '')
                    if not df_rec.empty:
                        matching_rec = df_rec[(df_rec['Número de PC'] == numero_pc) & (df_rec['Código de artículo'] == code)]
                        if not matching_rec.empty:
                            fs = matching_rec.iloc[0].get('Fecha')
                            if pd.notna(fs):
                                fecha_compra = pd.to_datetime(fs, errors='coerce')
                    
                    if pd.notna(fecha_compra):
                        cache_original[code] = float(precio_raw)
                        cache_date[code] = fecha_compra
                        dias_diff = (pd.Timestamp.now() - fecha_compra).days
                        meses_diff = dias_diff / 30.44
                        if meses_diff < 3:
                            precio = precio * ((1 + inflacion) ** meses_diff)
                        else:
                            if dolar_hoy is not None:
                                precio = (precio / HISTORIC_DOLAR) * float(dolar_hoy)
                    else:
                        cache_original[code] = float(precio_raw)
                        cache_date[code] = "Sin Fecha"
                        # Si no hay fecha, se asume viejo (>3 meses) y se usa dolar
                        if dolar_hoy is not None:
                            precio = (precio / HISTORIC_DOLAR) * float(dolar_hoy)

                    precio = float(round(precio, 2))
                    cache[code] = precio
                    cache_source[code] = 'pc'
                    recursion_stack.remove(code)
                    return precio

        # 2) df_ci: si existe, tomar el valor y AJUSTARLO si dolar_hoy fue pasado
        resultado_ci = df_ci[df_ci['Código de artículo'] == code]
        if not resultado_ci.empty:
            resultado_ci_local = resultado_ci.copy()
            resultado_ci_local['__costo_num'] = pd.to_numeric(resultado_ci_local.get('Costo unitario', pd.Series([])), errors='coerce')
            filas_con_costo_ci = resultado_ci_local[resultado_ci_local['__costo_num'].notna()]
            row = None
            if not filas_con_costo_ci.empty:
                row = pick_latest_row(filas_con_costo_ci, 'Número')
            if row is not None:
                precio_raw = pd.to_numeric(row.get('Costo unitario', None), errors='coerce')
                if not pd.isna(precio_raw):
                    # Aquí aplicamos la conversión SÓLO para df_ci si se pasó dolar_hoy
                    cache_original[code] = float(precio_raw)
                    cache_date[code] = "Sin Fecha"
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

        # 3) expandir por df_fab -> df_salidas
        resultado_fab = df_fab[df_fab['Código de artículo'] == code]
        if not resultado_fab.empty:
            fila_fab = pick_latest_row(resultado_fab, 'Número')
            if fila_fab is None:
                cache[code] = 'Nada'
                cache_source[code] = 'Nada'
                recursion_stack.remove(code)
                return 'Nada'
            numero = fila_fab.get('Número', None)
            finalizada = get_finalizada_from_row(fila_fab)
            if pd.isna(numero) or numero is None or finalizada in (None, 0):
                cache[code] = 'Nada'
                cache_source[code] = 'Nada'
                recursion_stack.remove(code)
                return 'Nada'
            filtro_pedido = df_salidas['Pedido'].astype(str).str.startswith(str(numero), na=False)
            res_salidas = df_salidas[filtro_pedido]
            if res_salidas.empty:
                cache[code] = 'Nada'
                cache_source[code] = 'Nada'
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
                # resolver el precio del hijo REUTILIZANDO el mismo dolar_hoy (acceso vía cierre)
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
                recursion_stack.remove(code)
                return float(unitario_padre)
            else:
                cache[code] = 'Nada'
                cache_source[code] = 'Nada'
                recursion_stack.remove(code)
                return 'Nada'

        # 4) nada
        cache[code] = 'Nada'
        cache_source[code] = 'Nada'
        recursion_stack.remove(code)
        return 'Nada'

    # main loop: resolver cada item (inicialmente se pasa dolar_hoy a través del cierre)
    for codigo in items:
        unitario = resolve_unitario(codigo, set())
        precios_finales.append((codigo, unitario))

    if return_map:
        return precios_finales, codigos_padres, cache_source, cache_original, cache_date
    return precios_finales


# ---------- buscador corregido para evitar AttributeError en columnas ----------
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
    for df in (df_pc, df_ci, df_fab):
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

def buscador(pedido_a_buscar, dolar_hoy=None, inflacion=0.0, output_dir='.', export_excel=True):
    filtro = df_salidas['Pedido'] == pedido_a_buscar
    resultados = df_salidas[filtro]
    codigos_encontrados = resultados['Código de artículo']

    if codigos_encontrados.empty:
        print(f"\nNo se encontró el Pedido '{pedido_a_buscar}'.")
        return None

    cantidades_por_codigo = (pd.to_numeric(resultados['Cantidad'], errors='coerce')
                             .fillna(0).abs()
                             .groupby(resultados['Código de artículo'])
                             .sum())

    codigos_unicos_array = codigos_encontrados.unique()
    items = tuple(codigos_unicos_array)
    precios_obtenidos, mapa, source_map, original_map, date_map = cotizador(items, dolar_hoy=dolar_hoy, inflacion=inflacion, return_map=True)

    # convertir nombres de columnas a str antes de usar .lower()
    posibles_desc_cols_salidas = [c for c in resultados.columns if 'descr' in str(c).lower() or 'desc' in str(c).lower()]
    if not posibles_desc_cols_salidas:
        for cand in ['Descripción', 'Descripcion', 'DESCRIPCIÓN', 'Desc', 'descripcion']:
            if cand in resultados.columns:
                posibles_desc_cols_salidas.append(cand)

    final_rows = []
    for codigo, precio in precios_obtenidos:
        descripcion = ""
        if not resultados.empty and posibles_desc_cols_salidas:
            filas_hijo = resultados[resultados['Código de artículo'] == codigo]
            if not filas_hijo.empty:
                for col in posibles_desc_cols_salidas:
                    for _, r in filas_hijo.iterrows():
                        val = clean_text(r.get(col, ""))
                        if val and not val.lstrip().startswith('='):
                            descripcion = val
                            break
                    if descripcion:
                        break
        if not descripcion:
            descripcion = get_descripcion_robusta(codigo)

        origen = source_map.get(codigo, 'Nada')
        precio_final = precio
        if isinstance(precio, numbers.Real) and origen == 'ci':
            # Costos iniciales no tienen fecha, asumimos viejos -> dólar
            if dolar_hoy is not None:
                precio_final = round((float(precio) / HISTORIC_DOLAR) * float(dolar_hoy), 2)

        cantidad_utilizada = float(cantidades_por_codigo.get(codigo, 0.0))
        costo_total = "Nada"
        if isinstance(precio_final, numbers.Real):
            costo_total = round(cantidad_utilizada * float(precio_final), 2)
            
        costo_sistema = original_map.get(codigo, "Nada")
        fecha_costo = date_map.get(codigo, "Sin Fecha")
        if isinstance(fecha_costo, pd.Timestamp):
            fecha_costo = fecha_costo.strftime('%Y-%m-%d')
            
        final_rows.append((codigo, descripcion, cantidad_utilizada, costo_sistema, fecha_costo, precio_final, costo_total))

    df_out = pd.DataFrame(final_rows, columns=['Codigo', 'Descripcion', 'Cantidad Utilizada', 'Costo unitario sistema', 'Fecha del costo', 'Precio actualizado', 'Costo Total'])
    if export_excel:
        safe = re.sub(r'[^0-9A-Za-z_.-]', '_', str(pedido_a_buscar))[:100]
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cotizacion_{safe}_{ts}.xlsx"
        path = os.path.join(output_dir, filename)
        os.makedirs(output_dir, exist_ok=True)
        df_out.to_excel(path, index=False)
        print(f"\nResultados de la cotización guardados en: {path}")
        return path

    return df_out
if __name__ == "__main__":
    # Este bloque se ejecuta solo cuando corres el archivo directamente
    print("\n" + "="*50)
    print("INICIANDO PRUEBA DE COTIZACIÓN")
    print("="*50)
    
    # Parámetros de prueba
    codigo_a_probar = 'E10502200280000'
    dolar_valor = 1200
    inflacion_valor = 0.05
    
    print(f"Probando artículo: {codigo_a_probar}")
    print(f"Dólar: {dolar_valor} | Inflación: {inflacion_valor}")
    print("-" * 50)

    # Intentamos primero como artículo (cotizador) para ver su desglose
    precios, mapa, sources, cache_orig, cache_date = cotizador([codigo_a_probar], dolar_hoy=dolar_valor, inflacion=inflacion_valor, return_map=True)
    
    for cod, precio in precios:
        desc = get_descripcion_robusta(cod)
        origen = sources.get(cod, 'Desconocido')
        costo_sist = cache_orig.get(cod, 'Nada')
        fecha_c = cache_date.get(cod, 'Sin Fecha')
        if isinstance(fecha_c, pd.Timestamp):
            fecha_c = fecha_c.strftime('%Y-%m-%d')
            
        print(f"CÓDIGO: {cod}")
        print(f"DESCRIPCIÓN: {desc}")
        print(f"COSTO UNITARIO SISTEMA: {costo_sist}")
        print(f"FECHA DEL COSTO: {fecha_c}")
        print(f"PRECIO ACTUALIZADO: {precio}")
        print(f"ORIGEN DE COSTO: {origen}")
        
        if cod in mapa:
            print("\nDESGLOSE DE COMPONENTES:")
            for hijo, cant, p_hijo, contrib in mapa[cod]:
                print(f"  - {hijo} | Cant: {cant} | Unit: {p_hijo} | Subtotal: {contrib}")
    
    print("\n" + "="*50)