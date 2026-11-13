"""Madrid: cómo se obtienen los datos de BiciMAD, el Metro y los autobuses de la EMT.

Solo usa lo visto en clase: requests (GET, POST, cabeceras, parámetros, JSON).
Ejecutar:  python3 madrid.py
La EMT pide claves: van en el fichero .env (EMT_MADRID_CLIENT_ID y EMT_MADRID_PASSKEY), nunca en el código.
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


# ============================================================ 1. BiciMAD (JSON, estándar GBFS)
# GBFS es un estándar de bicis compartidas: un índice (gbfs.json) dice dónde está cada dato.
#   station_information -> datos fijos de cada estación (nombre, posición)
#   station_status      -> estado ahora mismo (bicis y anclajes libres)
URL_BICIMAD = "https://madrid.publicbikesystem.net/customer/gbfs/v2/gbfs.json"


def bicimad():
    respuesta = requests.get(URL_BICIMAD, headers=CABECERAS, timeout=20)
    if respuesta.status_code != 200:
        print("BiciMAD ha respondido con el código", respuesta.status_code)
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


# ============================================================ 2. Metro de Madrid (JSON)
# API que usa la web del Consorcio de Transportes (CRTM) para enseñar los próximos trenes. Sin clave.
URL_CRTM = "https://www.crtm.es/widgets/api/GetStopsTimes.php"
ESTACIONES_METRO = {"4_12": "Sol", "4_120": "Nuevos Ministerios"}   # código del CRTM: 4 = Metro


def metro(codigo):
    parametros = {"codStop": codigo, "type": 1, "orderBy": 2, "stopTimesByIti": 3}
    respuesta = requests.get(URL_CRTM, params=parametros, headers=CABECERAS, timeout=10)
    if respuesta.status_code != 200:
        print("El CRTM ha respondido con el código", respuesta.status_code)
        return []

    datos = respuesta.json()["stopTimes"]
    ahora = datetime.fromisoformat(datos["actualDate"])     # la hora del servidor
    tiempos = datos["times"]["Time"] if datos.get("times") else []
    if isinstance(tiempos, dict):       # si solo viene un tren, no viene en una lista
        tiempos = [tiempos]

    trenes = []
    for t in tiempos:
        llegada = datetime.fromisoformat(t["time"])
        trenes.append({
            "linea": t["line"]["shortDescription"], "destino": t["destination"],
            "minutos": int((llegada - ahora).total_seconds() // 60),
        })
    return trenes


# ============================================================ 3. Autobuses EMT Madrid (JSON, con clave)
# API MobilityLabs. Primero un login con las claves, que devuelve un "token"; ese token va en la
# cabecera de las demás peticiones. Los próximos buses se piden con POST (como en las APIs REST).
URL_EMT = "https://openapi.emtmadrid.es/"
PARADAS_EMT = [72, 3036]        # Cibeles - Casa de América y Camino Viejo de Leganés


def emt_login():
    claves = leer_claves()
    cabeceras = {"X-ClientId": claves["EMT_MADRID_CLIENT_ID"], "passKey": claves["EMT_MADRID_PASSKEY"]}
    respuesta = requests.get(URL_EMT + "v2/mobilitylabs/user/login/", headers=cabeceras, timeout=10)
    if respuesta.status_code != 200:
        print("El login de la EMT ha respondido con el código", respuesta.status_code)
        return None
    return respuesta.json()["data"][0]["accessToken"]


def emt(parada, token):
    cabeceras = {"accessToken": token}
    cuerpo = {"cultureInfo": "ES", "Text_StopRequired_YN": "N",
              "Text_EstimationsRequired_YN": "Y", "Text_IncidencesRequired_YN": "N"}
    url = URL_EMT + f"v2/transport/busemtmad/stops/{parada}/arrives/"
    respuesta = requests.post(url, headers=cabeceras, json=cuerpo, timeout=10)
    if respuesta.status_code != 200:
        print("La EMT ha respondido con el código", respuesta.status_code)
        return []

    buses = []
    for bus in respuesta.json()["data"][0]["Arrive"]:
        segundos = bus["estimateArrive"]        # 999999 = la EMT no sabe cuándo llega (muy lejos)
        buses.append({
            "parada": parada, "linea": bus["line"], "destino": bus["destination"],
            "minutos": None if segundos >= 999999 else segundos // 60,
        })
    return buses


# ============================================================ prueba
if __name__ == "__main__":
    estaciones = bicimad()
    print(f"BiciMAD: {len(estaciones)} estaciones. Las 3 primeras:")
    for e in estaciones[:3]:
        print(f"  {e['nombre']}: {e['bicis']} bicis, {e['anclajes_libres']} anclajes libres")

    for codigo, nombre in ESTACIONES_METRO.items():
        time.sleep(1)                   # como mucho 1 petición por segundo al CRTM
        print(f"\nMetro, {nombre}:")
        for t in metro(codigo):
            print(f"  L{t['linea']} a {t['destino']}: {t['minutos']} min")

    token = emt_login()
    if token:
        for parada in PARADAS_EMT:
            time.sleep(1)               # como mucho 1 petición por segundo a la EMT
            print(f"\nEMT Madrid, parada {parada}:")
            for bus in emt(parada, token):
                minutos = "más de 45 min" if bus["minutos"] is None else f"{bus['minutos']} min"
                print(f"  línea {bus['linea']} a {bus['destino']}: {minutos}")
