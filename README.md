![Banner del proyecto](.assets/image_9e4333f8.jpg)


# Transporte público en tiempo real: Valencia, Madrid y Barcelona

Proyecto de **Adquisición y Transmisión de Datos** (Grado en Ciencia de Datos, UPV).
Obtiene en tiempo real las bicis compartidas, los autobuses y el metro de tres ciudades, y el tiempo,
usando solo lo visto en clase: `requests` y `BeautifulSoup` para la adquisición, y cadenas, `re`,
`datetime` y `pandas` para el filtrado.

<div align="center">

![Licencia](https://shields.io)
![Estado](https://shields.io)
![Python](https://shields.io)
![GitHub](https://shields.io)

</div>


## Flujo

```
usuario (menú de main.py)
  -> módulo de la ciudad (Valencia/, Madrid/, Barcelona/)  -> API de cada fuente
  -> filtrado.py: mismas columnas y formato para todas las fuentes
  -> Tiempo/tiempo.py: si eliges bici y llueve, aviso
  -> tabla en pantalla + CSV en datos/  -> vuelta al menú
```

| Archivo | Qué hace |
|---|---|
| `main.py` | Programa principal: menú, llamada al módulo, filtrado, aviso de lluvia, tabla y CSV |
| `filtrado.py` | Homogeneiza nombres, líneas, minutos e ids; quita repetidos y estaciones sin datos recientes |
| `Valencia/valencia.py` | Valenbisi (JSON), EMT (XML con BeautifulSoup) y Metrovalencia (API de FGV con sesión) |
| `Madrid/madrid.py` | BiciMAD (GBFS), Metro (API del Consorcio de Transportes) y EMT (MobilityLabs: login y POST) |
| `Barcelona/barcelona.py` | Bicing (GBFS) y autobuses y metro de TMB (API con clave) |
| `Tiempo/tiempo.py` | Temperatura y si llueve en cada ciudad (Open-Meteo, sin clave) |

## Cómo se ejecuta

```bash
pip install -r requirements.txt
python main.py                  # menú
python main.py Valencia bici    # una consulta directa
python Valencia/valencia.py     # un módulo solo
```

Los autobuses de Madrid y los de Barcelona y su metro necesitan claves: copia `.env.ejemplo` como `.env`
(en esta misma carpeta) y rellénalo. El `.env` no se sube nunca a git.
