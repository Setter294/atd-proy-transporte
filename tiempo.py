"""El tiempo en Valencia: temperatura y si llueve, con la API de Open-Meteo (gratis y sin clave).

Solo usa lo visto en clase: requests (GET, parámetros, JSON).
Ejecutar:  python3 tiempo.py
"""
from datetime import datetime

import requests

URL = "https://api.open-meteo.com/v1/forecast"

# Códigos del tiempo (estándar WMO) que significan llovizna, lluvia, chubascos o tormenta.
CODIGOS_LLUVIA = list(range(51, 68)) + list(range(80, 83)) + list(range(95, 100))


def tiempo():
    parametros = {
        "latitude": 39.4699, "longitude": -0.3763,           # plaza del Ayuntamiento de Valencia
        "current": "temperature_2m,precipitation,weather_code",
        "timezone": "Europe/Madrid",
    }
    respuesta = requests.get(URL, params=parametros, timeout=10)
    if respuesta.status_code != 200:
        print("Open-Meteo ha respondido con el código", respuesta.status_code)
        return None

    actual = respuesta.json()["current"]
    precipitacion = actual["precipitation"]          # mm en los últimos 15 minutos
    codigo = actual["weather_code"]
    return {
        "hora": datetime.fromisoformat(actual["time"]),  # "2026-11-13T09:00"
        "temperatura": actual["temperature_2m"],
        "precipitacion": precipitacion,
        "codigo": codigo,
        "llueve": precipitacion > 0 or codigo in CODIGOS_LLUVIA,
    }


# ============================================================ prueba
if __name__ == "__main__":
    t = tiempo()
    if t:
        print(f"Valencia a las {t['hora']:%H:%M}: {t['temperatura']} °C, "
              f"{t['precipitacion']} mm, código {t['codigo']}")
        print("Está lloviendo" if t["llueve"] else "No llueve")
