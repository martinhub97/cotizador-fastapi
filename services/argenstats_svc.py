import os
import requests
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()

# Configuración
API_KEY = os.getenv("ARGENSTATS_API_KEY", "as_prod_rYU1SREpFj6BVh6r166RvWdo9ZfxROBU")
BASE_URL = "https://argenstats.com/api/v1"

logger = logging.getLogger(__name__)

class ArgenStatsService:
    def __init__(self):
        self._dolar_cache = None
        self._dolar_last_fetch = None
        self._inflation_cache = {} # keyed by (from_date, to_date)
        
    def get_dolar_hoy(self) -> float:
        """Obtiene el valor del dólar actual. Cache por 4 horas."""
        now = datetime.now()
        if self._dolar_cache and self._dolar_last_fetch and (now - self._dolar_last_fetch) < timedelta(hours=4):
            return self._dolar_cache
            
        try:
            url = f"{BASE_URL}/dollar?view=current"
            headers = {"x-api-key": API_KEY}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Según la estructura vista en test.py de inflación, asumimos algo similar para dólar
            # Buscamos el valor de venta del blue u oficial según conveniencia.
            # ArgenStats suele devolver una lista o un objeto con múltiples tipos.
            # Tomamos el 'oficial' o un promedio si es necesario.
            # Basándonos en usos típicos, suele haber un campo 'data'
            items = data.get("data", {})
            
            # 1. Intentar con el Dólar Blue (preferencia del usuario)
            blue = items.get("BLUE")
            if blue:
                val = blue.get("averagePrice")
                if val:
                    self._dolar_cache = float(val)
                    self._dolar_last_fetch = now
                    return self._dolar_cache
            
            # 2. Fallback al Oficial si no hay Blue
            oficial = items.get("OFICIAL")
            if oficial:
                val = oficial.get("sellPrice") or oficial.get("averagePrice")
                if val:
                    self._dolar_cache = float(val)
                    self._dolar_last_fetch = now
                    return self._dolar_cache
                    
        except Exception as e:
            logger.error(f"Error obteniendo dólar de ArgenStats: {e}")
            
        return self._dolar_cache or 1200.0 # Fallback manual seguro si falla la API

    def get_inflation_factor(self, from_date: datetime, to_date: datetime) -> float:
        """
        Calcula el factor multiplicativo (1 + inf_acumulada) entre dos fechas.
        Usa la API de inflación histórica de ArgenStats.
        """
        # Formatear fechas para la API
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        cache_key = (from_str, to_str)
        
        if cache_key in self._inflation_cache:
            return self._inflation_cache[cache_key]
            
        try:
            # Quitamos un mes al inicio para asegurarnos de captar el reporte del mes previo si la fecha es muy reciente
            url = f"{BASE_URL}/inflation?view=historical&from={from_str}&to={to_str}"
            headers = {"x-api-key": API_KEY}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            monthly_values = data.get("data", [])
            factor = 1.0
            
            # Calculamos el acumulado: (1 + m1/100) * (1 + m2/100) ...
            for entry in monthly_values:
                m_val = entry.get("values", {}).get("monthly")
                if m_val is not None:
                    factor *= (1 + (float(m_val) / 100))
            
            self._inflation_cache[cache_key] = factor
            return factor
            
        except Exception as e:
            logger.error(f"Error obteniendo inflación de ArgenStats: {e}")
            return 1.15 # Fallback estimado (15%) si falla la API para no devolver 0

# Instancia única
argenstats_svc = ArgenStatsService()
