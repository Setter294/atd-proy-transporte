"""Programa principal del proyecto: une todos los módulos en un único flujo.

Flujo:  usuario elige ciudad y medio  ->  módulo de la ciudad pide los datos a su API
        ->  filtrado.py los homogeneiza  ->  tiempo.py avisa si llueve (bicis)
        ->  se enseña una tabla y se guarda en un CSV  ->  vuelta al menú

Ejecutar (desde esta carpeta):  python3 main.py                 (menú)
                               python3 main.py Valencia bici   (una consulta directa, sin menú)
Cada módulo también funciona solo:  python3 Valencia/valencia.py
"""
import os
import sys
import time
from datetime import datetime

import filtrado
from Barcelona import barcelona          # cada ciudad está en su carpeta
from Madrid import madrid
from Tiempo import tiempo
from Valencia import valencia

CIUDADES = ["Valencia", "Madrid", "Barcelona"]
MEDIOS = ["bici", "bus", "metro"]
NOMBRES = {
    "Valencia": {"bici": "Valenbisi", "bus": "EMT Valencia", "metro": "Metrovalencia"},
    "Madrid": {"bici": "BiciMAD", "bus": "EMT Madrid", "metro": "Metro de Madrid"},
    "Barcelona": {"bici": "Bicing", "bus": "Bus TMB", "metro": "Metro TMB"},
}
CARPETA_CSV = "datos"


# ============================================================ 1. Obtener los datos (módulos de cada ciudad)
def obtener(ciudad, medio):
    """Llama al módulo de la ciudad y devuelve la lista de datos tal como la da la fuente."""
    datos = []
    if ciudad == "Valencia":
        if medio == "bici":
            datos = valencia.valenbisi()
        elif medio == "bus":
            for parada in valencia.PARADAS_EMT:
                time.sleep(1)                   # como mucho 1 petición por segundo
                datos += valencia.emt(parada)
        else:
            datos, incidencias = valencia.metro(valencia.ESTACIONES_METRO)
            for texto in incidencias:
                print("  Incidencia de FGV:", texto)

    elif ciudad == "Madrid":
        if medio == "bici":
            datos = madrid.bicimad()
        elif medio == "bus":
            token = madrid.emt_login()
            for parada in madrid.PARADAS_EMT if token else []:
                time.sleep(1)
                datos += madrid.emt(parada, token)
        else:
            for codigo, nombre in madrid.ESTACIONES_METRO.items():
                time.sleep(1)
                for tren in madrid.metro(codigo):
                    tren["parada"] = nombre     # el CRTM no repite el nombre en cada tren
                    datos.append(tren)

    else:   # Barcelona
        if medio == "bici":
            datos = barcelona.bicing()
        else:
            claves = barcelona.leer_claves()
            if medio == "bus":
                for parada in barcelona.PARADAS_BUS:
                    time.sleep(1)
                    datos += barcelona.bus(parada, claves)
            else:
                for codigos, nombre in barcelona.ESTACIONES_METRO.items():
                    time.sleep(1)
                    for tren in barcelona.metro(codigos, claves):
                        tren["parada"] = nombre
                        datos.append(tren)
    return datos


# ============================================================ 2. Consulta completa
def consultar(ciudad, medio):
    fuente = NOMBRES[ciudad][medio]
    print(f"\nPidiendo los datos de {fuente}...")
    datos = obtener(ciudad, medio)

    # Filtrado: mismas columnas y formato para todas las fuentes.
    if medio == "bici":
        tabla = filtrado.bicis(datos, ciudad)
    else:
        tabla = filtrado.llegadas(datos, ciudad, medio)
    print(f"{fuente}: {len(datos)} datos recibidos, {len(tabla)} tras el filtrado.")

    # Si vas a coger la bici y llueve, aviso.
    if medio == "bici":
        t = tiempo.tiempo(ciudad)
        if t and t["llueve"]:
            print(f"  ¡AVISO! Está lloviendo en {ciudad} ({t['precipitacion']} mm). Quizá mejor bus o metro.")
        elif t:
            print(f"  Tiempo en {ciudad}: {t['temperatura']} °C, no llueve.")

    if tabla.empty:
        print("  No hay datos ahora mismo.")
        return
    print(tabla.head(20).to_string(index=False))
    if len(tabla) > 20:
        print(f"  ... y {len(tabla) - 20} filas más")

    # Guardar en CSV, con la fecha en el nombre para no machacar consultas anteriores.
    os.makedirs(CARPETA_CSV, exist_ok=True)
    fichero = f"{CARPETA_CSV}/{ciudad.lower()}_{medio}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    tabla.to_csv(fichero, index=False, encoding="utf-8")
    print(f"Guardado en {fichero}")


# ============================================================ 3. Menú (interacción con el usuario)
def elegir(pregunta, opciones):
    """Enseña las opciones numeradas y devuelve la elegida (None si el usuario escribe 0)."""
    while True:
        print(f"\n{pregunta}")
        for i, opcion in enumerate(opciones, start=1):
            print(f"  {i}. {opcion}")
        print("  0. Salir")
        respuesta = input("> ").strip()
        if respuesta == "0":
            return None
        if respuesta.isdigit() and 1 <= int(respuesta) <= len(opciones):
            return opciones[int(respuesta) - 1]
        print("Opción no válida, escribe uno de los números.")


def main():
    print("Transporte público en tiempo real: Valencia, Madrid y Barcelona")
    while True:
        ciudad = elegir("¿Qué ciudad?", CIUDADES)
        if ciudad is None:
            break
        medio = elegir(f"¿Qué quieres ver en {ciudad}?", [NOMBRES[ciudad][m] for m in MEDIOS])
        if medio is None:
            break
        medio = MEDIOS[[NOMBRES[ciudad][m] for m in MEDIOS].index(medio)]
        consultar(ciudad, medio)
    print("¡Hasta luego!")


if __name__ == "__main__":
    if len(sys.argv) == 3:              # python3 main.py Valencia bici
        consultar(sys.argv[1].title(), sys.argv[2].lower())
    else:
        main()
