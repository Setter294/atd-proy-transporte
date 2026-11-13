"""Filtrado de datos: deja los datos de todas las fuentes con las mismas columnas y el mismo formato.

Cada fuente devuelve los datos a su manera:
  - nombres: "210_CALLE_CAMPOS_CRESPO", "2 - Metro Callao", "GRAN VIA CORTS CATALANES, 760"
  - líneas: "L1" en Barcelona, "1" en Madrid, 6 (un número) en Valencia
  - tiempo: minutos en unas fuentes y segundos en otras; a veces sin dato (None)
  - repetidos y estaciones con el dato congelado
Aquí se homogeneiza todo con lo visto en la UD3: cadenas (strip, split), expresiones regulares (re),
fechas (datetime) y pandas (DataFrame, drop_duplicates, fillna).
"""
import re
from datetime import datetime, timedelta

import pandas as pd

COLUMNAS_BICIS = ["ciudad", "id", "estacion", "bicis", "anclajes_libres", "actualizado"]
COLUMNAS_LLEGADAS = ["ciudad", "medio", "parada", "linea", "destino", "minutos"]
PALABRAS_PEQUENAS = {"de", "del", "la", "las", "los", "el", "y", "i", "en", "dels", "els", "les"}
MAXIMA_ANTIGUEDAD = timedelta(hours=1)


def limpiar_nombre(texto):
    """'210_CALLE_CAMPOS_CRESPO' -> 'Calle Campos Crespo';  '2 - Metro Callao' -> 'Metro Callao'."""
    texto = str(texto).strip()
    texto = re.sub(r"^\d+[a-zA-Z]?\s*[_\-·]\s*", "", texto)   # número delante: "210_", "106B - "
    texto = texto.replace("_", " ")
    texto = re.sub(r"\s+", " ", texto)                  # varios espacios seguidos -> uno
    palabras = []
    for i, palabra in enumerate(texto.lower().split()):
        if i > 0 and palabra in PALABRAS_PEQUENAS:
            palabras.append(palabra)                    # "de", "la"... en minúscula
        elif re.fullmatch(r"[ivx]{2,}", palabra):
            palabras.append(palabra.upper())            # números romanos: "Pio XII"
        else:
            palabras.append(palabra[:1].upper() + palabra[1:])
    return " ".join(palabras)


def limpiar_linea(valor, medio):
    """Metro: siempre con L delante ('1' -> 'L1'). Bus: sin ceros a la izquierda ('014' -> '14')."""
    linea = str(valor).strip().upper()
    if medio == "metro" and not linea.startswith(("L", "ML", "R")):
        linea = "L" + linea
    if medio == "bus":
        linea = linea.lstrip("0") or linea
    return linea


def bicis(registros, ciudad):
    """Estaciones de bici de cualquier ciudad -> tabla con COLUMNAS_BICIS."""
    df = pd.DataFrame(registros)
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_BICIS)
    df["ciudad"] = ciudad
    df["id"] = df["id"].astype(str)                     # Valencia da números y Madrid/Barcelona texto
    df["estacion"] = df["nombre"].map(limpiar_nombre)
    df["bicis"] = df["bicis"].fillna(0).astype(int)
    df["anclajes_libres"] = df["anclajes_libres"].fillna(0).astype(int)

    # La misma regla en las tres ciudades: fuera las estaciones con el dato de hace más de 1 hora.
    df = df[datetime.now() - df["actualizado"] <= MAXIMA_ANTIGUEDAD].copy()
    df = df.drop_duplicates(subset="id")             # por id: hay estaciones distintas con el mismo nombre

    df["actualizado"] = df["actualizado"].dt.strftime("%d/%m/%Y %H:%M")
    return df[COLUMNAS_BICIS].sort_values("estacion")


def llegadas(registros, ciudad, medio):
    """Próximos buses o trenes de cualquier ciudad -> tabla con COLUMNAS_LLEGADAS."""
    filas = []
    for r in registros:
        minutos = r.get("minutos")
        if minutos is None and r.get("segundos") is not None:     # Metrovalencia da segundos
            minutos = r["segundos"] // 60
        filas.append({
            "parada": r.get("parada") or r.get("estacion"),
            "linea": r["linea"], "destino": r["destino"], "minutos": minutos,
        })
    df = pd.DataFrame(filas)
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS_LLEGADAS)
    df["ciudad"] = ciudad
    df["medio"] = medio
    df["parada"] = df["parada"].map(limpiar_nombre)
    df["destino"] = df["destino"].map(limpiar_nombre)
    df["linea"] = df["linea"].map(lambda l: limpiar_linea(l, medio))

    df = df.dropna(subset=["minutos"]).copy()           # sin hora de llegada no sirve para comparar
    df["minutos"] = df["minutos"].astype(int).clip(lower=0)    # "ya ha llegado" = 0, nunca negativo
    df = df.drop_duplicates()
    return df[COLUMNAS_LLEGADAS].sort_values(["parada", "minutos"])
