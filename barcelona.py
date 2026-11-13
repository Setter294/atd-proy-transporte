"""Barcelona: cómo se obtienen los datos del Bicing y de los autobuses y el metro de TMB.

Solo usa lo visto en clase: requests (GET, cabeceras, parámetros, JSON).
Ejecutar:  python3 barcelona.py
TMB pide claves: van en el fichero .env (TMB_APP_ID y TMB_APP_KEY), nunca en el código.
"""
import time
from datetime import datetime

import requests

CABECERAS = {"User-Agent": "Mozilla/5.0"}


def leer_claves(fichero=".env"):
    """Lee las líneas CLAVE=valor del fichero .env y las devuelve en un diccionario."""
    claves = {}
    with open(fichero, encoding="utf-8") as f:
        for linea in f:
            if "=" in linea and not linea.startswith("#"):
                clave, valor = linea.strip().split("=", 1)
                claves[clave] = valor
    return claves


# ============================================================ 1. Bicing (JSON, estándar GBFS)
# El mismo estándar que BiciMAD en Madrid: un índice (gbfs.json) dice dónde está cada dato.
#   station_information -> datos fijos de cada estación (nombre, posición)
#   station_status      -> estado ahora mismo (bicis y anclajes libres)
URL_BICING = "https://barcelona.publicbikesystem.net/customer/gbfs/v2/gbfs.json"


def bicing():
    respuesta = requests.get(URL_BICING, headers=CABECERAS, timeout=20)
    if respuesta.status_code != 200:
        print("Bicing ha respondido con el código", respuesta.status_code)
        return []
    # El índice trae la lista de datos por idioma; cogemos el castellano.
    urls = {}
    for feed in respuesta.json()["data"]["es"]["feeds"]:
        urls[feed["name"]] = feed["url"]

    informacion = requests.get(urls["station_information"], headers=CABECERAS, timeout=20).json()
    estado = requests.get(urls["station_status"], headers=CABECERAS, timeout=20).json()

    # Nombre de cada estación, para juntarlo con su estado por el station_id.
    nombres = {}
    for e in informacion["data"]["stations"]:
        nombres[e["station_id"]] = e["name"]

    estaciones = []
    for s in estado["data"]["stations"]:
        estaciones.append({
            "nombre": nombres.get(s["station_id"]),
            "bicis": s["num_bikes_available"], "anclajes_libres": s["num_docks_available"],
            "actualizado": datetime.fromtimestamp(s["last_reported"]),   # segundos desde 1970
        })
    return estaciones


# ============================================================ 2 y 3. TMB: autobuses y metro (JSON, con clave)
# API oficial de TMB. Las claves van como parámetros de la URL (app_id y app_key),
# igual que la api_key del ejemplo de AEMET de clase.
URL_TMB = "https://api.tmb.cat/v1/"
PARADAS_BUS = [2559, 256]       # Pg Joan de Borbó - Moll de Catalunya y Moll de la Fusta
ESTACIONES_METRO = {"126,326": "Catalunya", "216,523": "Sagrada Família"}   # un código por línea


def bus(parada, claves):
    parametros = {"app_id": claves["TMB_APP_ID"], "app_key": claves["TMB_APP_KEY"]}
    respuesta = requests.get(URL_TMB + f"ibus/stops/{parada}", params=parametros, timeout=10)
    if respuesta.status_code != 200:
        print("TMB (bus) ha respondido con el código", respuesta.status_code)
        return []

    buses = []
    for b in respuesta.json()["data"]["ibus"]:
        buses.append({"parada": parada, "linea": b["line"], "destino": b["destination"],
                      "minutos": b["t-in-min"]})
    return buses


def metro(codigos, claves):
    parametros = {"estacions": codigos, "app_id": claves["TMB_APP_ID"], "app_key": claves["TMB_APP_KEY"]}
    respuesta = requests.get(URL_TMB + "itransit/metro/estacions", params=parametros, timeout=10)
    if respuesta.status_code != 200:
        print("TMB (metro) ha respondido con el código", respuesta.status_code)
        return []

    datos = respuesta.json()
    ahora = datos["timestamp"]          # hora del servidor, en milisegundos desde 1970
    trenes = []
    # Anidado: línea -> estación -> trayecto (sentido) -> próximos trenes.
    for linea in datos["linies"]:
        for estacion in linea["estacions"]:
            for trayecto in estacion["linies_trajectes"]:
                for tren in trayecto["propers_trens"]:
                    segundos = (tren["temps_arribada"] - ahora) / 1000
                    trenes.append({"linea": trayecto["nom_linia"], "destino": trayecto["desti_trajecte"],
                                   "minutos": int(segundos // 60)})
    return trenes


# ============================================================ prueba
if __name__ == "__main__":
    estaciones = bicing()
    print(f"Bicing: {len(estaciones)} estaciones. Las 3 primeras:")
    for e in estaciones[:3]:
        print(f"  {e['nombre']}: {e['bicis']} bicis, {e['anclajes_libres']} anclajes libres")

    claves = leer_claves()
    for parada in PARADAS_BUS:
        time.sleep(1)                   # como mucho 1 petición por segundo a TMB
        print(f"\nBus TMB, parada {parada}:")
        for b in bus(parada, claves):
            print(f"  línea {b['linea']} a {b['destino']}: {b['minutos']} min")

    for codigos, nombre in ESTACIONES_METRO.items():
        time.sleep(1)
        print(f"\nMetro TMB, {nombre}:")
        for t in metro(codigos, claves):
            print(f"  {t['linea']} a {t['destino']}: {t['minutos']} min")
