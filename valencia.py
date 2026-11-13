"""Valencia: cómo se obtienen los datos de Valenbisi, la EMT y Metrovalencia.

Solo usa lo visto en clase: requests (GET, cabeceras, parámetros, JSON) y BeautifulSoup (XML).
Ejecutar:  python3 valencia.py
"""
import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# Algunas webs no contestan a programas que no se identifican como un navegador.
CABECERAS = {"User-Agent": "Mozilla/5.0"}


# ============================================================ 1. Valenbisi (JSON)
# API del Geoportal del Ayuntamiento. Con where=1=1 devuelve TODAS las estaciones en una petición.
URL_VALENBISI = "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/228/query"


def valenbisi():
    parametros = {"where": "1=1", "outFields": "*", "f": "geojson"}
    respuesta = requests.get(URL_VALENBISI, params=parametros, headers=CABECERAS, timeout=30)
    if respuesta.status_code != 200:
        print("Valenbisi ha respondido con el código", respuesta.status_code)
        return []

    datos = respuesta.json()
    ahora = datetime.now()
    estaciones = []
    for estacion in datos["features"]:
        p = estacion["properties"]
        longitud, latitud = estacion["geometry"]["coordinates"]      # GeoJSON: primero la longitud
        actualizado = datetime.strptime(p["updated_at"], "%d/%m/%Y %H:%M:%S")
        # Las estaciones fuera de servicio siguen saliendo con su último dato, congelado: se descartan.
        if ahora - actualizado > timedelta(hours=1):
            continue
        estaciones.append({
            "numero": p["number"], "nombre": p["name"],
            "bicis": p["available"], "anclajes_libres": p["free"], "total": p["total"],
            "actualizado": actualizado, "latitud": latitud, "longitud": longitud,
        })
    return estaciones


# ============================================================ 2. EMT (XML con BeautifulSoup)
# Es la petición que hace la propia web de la EMT para enseñar los próximos buses de una parada.
URL_EMT = "https://www.emtvalencia.es/EMT/mapfunctions/MapUtilsPetitions.php"
CABECERAS_EMT = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.emtvalencia.es"}
PARADAS_EMT = [1750, 2261]      # Fausto Elio - Universitat Politècnica y Xàtiva - Estació del Nord


def minutos(texto):
    """'6 min.' -> 6;  'Pròxim' / 'Próximo' -> 0;  cualquier otra cosa -> None."""
    numero = re.search(r"\d+", texto)
    if numero:
        return int(numero.group())
    if "pr" in texto.lower():
        return 0
    return None


def emt(parada):
    parametros = {"sec": "getSAE", "parada": parada, "adaptados": "false"}
    respuesta = requests.get(URL_EMT, params=parametros, headers=CABECERAS_EMT, timeout=10)
    if respuesta.status_code != 200:
        print("La EMT ha respondido con el código", respuesta.status_code)
        return []

    respuesta.encoding = "utf-8"        # si no, los acentos salen mal
    soup = BeautifulSoup(respuesta.text, "xml")      # es XML, no HTML: se usa el lector de XML
    buses = []
    for bus in soup.find_all("bus"):
        linea = bus.find("linea").get_text(strip=True)
        if not linea:                   # <bus> vacío: "SENSE ESTIMACIONS" (no hay buses ahora)
            continue
        texto = bus.find("minutos").get_text(strip=True)
        buses.append({
            "parada": parada, "linea": linea,
            "destino": bus.find("destino").get_text(strip=True),
            "minutos": minutos(texto), "texto": texto,
        })
    return buses


# ============================================================ 3. Metrovalencia (JSON con sesión)
# API que usa la app de FGV. Primero hay que pedir "estaciones": abre la sesión y deja unas cookies
# que las siguientes peticiones necesitan. Por eso se usa requests.Session(), que guarda las cookies
# y reutiliza la misma conexión (conexión persistente de HTTP/1.1).
URL_FGV = "https://www.fgv.es/fgv/app/es/api/v1/V/"
ESTACIONES_METRO = [12, 17]     # Benimaclet y Àngel Guimerà (el estacion_id_FGV)


def metro(ids):
    sesion = requests.Session()
    sesion.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})

    respuesta = sesion.get(URL_FGV + "estaciones", timeout=10)
    if respuesta.status_code != 200:
        print("FGV ha respondido con el código", respuesta.status_code)
        return [], []
    nombres = {e["estacion_id_FGV"]: e["nombre"] for e in respuesta.json()}

    trenes = []
    for id_estacion in ids:
        time.sleep(1)                   # como mucho 1 petición por segundo a FGV
        respuesta = sesion.get(URL_FGV + f"horarios-prevision-3/{id_estacion}", timeout=10)
        if respuesta.status_code == 404:
            print("FGV no tiene previsión ahora para", nombres.get(id_estacion))
            continue
        if respuesta.status_code != 200:
            print("FGV ha respondido con el código", respuesta.status_code)
            continue
        for prevision in respuesta.json()["previsiones"]:
            for tren in prevision["trains"]:
                trenes.append({
                    "estacion": nombres.get(id_estacion), "linea": prevision["line"],
                    "destino": tren["destino"], "segundos": tren["seconds"], "tren": tren["vehicle"],
                })

    time.sleep(1)
    respuesta = sesion.get(URL_FGV + "incidencias", timeout=10)
    incidencias = []
    if respuesta.status_code == 200:
        # Los textos vienen en varios idiomas: nos quedamos con el castellano.
        for texto in respuesta.json()["incidencias_translations"]:
            if texto["locale"] == "ES":
                incidencias.append(texto["descripcion"])
    return trenes, incidencias


# ============================================================ prueba
if __name__ == "__main__":
    estaciones = valenbisi()
    print(f"Valenbisi: {len(estaciones)} estaciones con datos recientes. Las 3 primeras:")
    for e in estaciones[:3]:
        print(f"  {e['nombre']}: {e['bicis']} bicis, {e['anclajes_libres']} anclajes libres")

    for parada in PARADAS_EMT:
        time.sleep(1)                   # como mucho 1 petición por segundo a la EMT
        print(f"\nEMT, parada {parada}:")
        for bus in emt(parada):
            print(f"  línea {bus['linea']} a {bus['destino']}: {bus['texto']}")

    trenes, incidencias = metro(ESTACIONES_METRO)
    print("\nMetrovalencia:")
    for t in trenes:
        print(f"  {t['estacion']}: L{t['linea']} a {t['destino']} en {t['segundos']} s (tren {t['tren']})")
    print("Incidencias:", incidencias or "ninguna")
