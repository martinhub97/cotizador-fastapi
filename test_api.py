import urllib.request
import json
import base64

url = "http://127.0.0.1:8000/api/v1/cotizar/"
data = json.dumps({
  "codigos_items": ["E10502200280000"],
  "dolar_hoy": 1200.0,
  "inflacion": 0.05,
  "conjunto_nombre": "Prueba FastAPI",
  "subconjunto_nombre": "Eléctrico",
  "guardar_db": True,
  "exportar_excel": True
}).encode("utf-8")

req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    print("Enviando petición POST a la API de FastAPI (con DB y Excel)...")
    with urllib.request.urlopen(req) as f:
        print("Status Code:", f.status)
        resp_dict = json.loads(f.read().decode('utf-8'))
        
        # Extraemos y guardamos el excel
        b64_file = resp_dict.pop("archivo_descargable", None)
        if b64_file:
            with open("reporte_test.xlsx", "wb") as f_out:
                f_out.write(base64.b64decode(b64_file))
            print("Excel 'reporte_test.xlsx' guardado con éxito.")
            
        print("Respuesta restante:", json.dumps(resp_dict, indent=2))
except Exception as e:
    print("Error contactando la API:", e)
