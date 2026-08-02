"""
Genera datos de PRUEBA (ficticios) para el prototipo de scouting.
No representa jugadores reales ni estadisticas reales.
Ejecutar una sola vez: python utils/generate_data.py
"""
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

SEED = 42
rng = np.random.default_rng(SEED)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

POSITIONS = ["Portero", "Defensa", "Mediocampista", "Delantero"]

RADAR_COLS = ["finalizacion", "creacion", "pase", "regate", "defensa", "fisico"]

# Fecha del partido mas reciente; el resto se cuentan hacia atras, uno por semana.
FECHA_BASE = date(2026, 7, 26)
N_ULTIMOS_PARTIDOS = 6

RIVALES = [
    "Deportivo Norte", "Atletico Rivera", "CD Monteverde", "Racing del Sur",
    "Union Ferroviaria", "Sportivo Litoral", "CA Independiente Sur",
    "Nacional Pampas", "Real Vertiente", "CD Costa Brava",
]

CLUBES = [
    ("Club Andino FC", "Argentina"),
    ("Deportivo Altiplano", "Chile"),
    ("Real Cordillera", "España"),
    ("Sporting Yungas", "México"),
    ("Atletico Salar", "Brasil"),
    ("CD Titicaca", "Uruguay"),
    ("Union Amazonia", "Ecuador"),
    ("Estrella del Illimani", "Paraguay"),
    ("Halcones del Chaco", "Estados Unidos"),
    ("FC Potosi Internacional", "Portugal"),
]

NOMBRES = [
    "Mateo Quispe", "Bruno Choque", "Ariel Mamani", "Diego Flores",
    "Rodrigo Yujra", "Fernando Apaza", "Gabriel Vargas", "Ismael Rojas",
    "Leonardo Ticona", "Samuel Guzman", "Ivan Callisaya", "Marco Poma",
    "Alan Chura", "Erick Zambrana", "Nestor Illanes", "Adrian Machaca",
    "Renzo Cardozo", "Tomas Sirpa",
]

def clip100(x):
    return int(np.clip(x, 5, 99))

def generar_jugadores():
    filas = []
    for i, nombre in enumerate(NOMBRES):
        pos = POSITIONS[i % 4] if i >= 4 else POSITIONS[i]
        pos = rng.choice(POSITIONS, p=[0.15, 0.30, 0.30, 0.25]) if i >= 4 else pos
        club, pais = CLUBES[rng.integers(0, len(CLUBES))]
        edad = int(rng.integers(19, 32))
        partidos = int(rng.integers(8, 34))

        base = rng.normal(55, 15, size=6)
        finalizacion, creacion, pase, regate, defensa, fisico = base

        if pos == "Delantero":
            finalizacion += 25; regate += 10; defensa -= 20
        elif pos == "Mediocampista":
            creacion += 20; pase += 15; defensa += 5
        elif pos == "Defensa":
            defensa += 30; fisico += 10; finalizacion -= 25; regate -= 10
        elif pos == "Portero":
            defensa += 20; pase -= 10; finalizacion -= 40; regate -= 30; creacion -= 20

        filas.append({
            "id": i + 1,
            "nombre": nombre,
            "posicion": pos,
            "club": club,
            "pais_liga": pais,
            "edad": edad,
            "partidos_jugados": partidos,
            "finalizacion": clip100(finalizacion),
            "creacion": clip100(creacion),
            "pase": clip100(pase),
            "regate": clip100(regate),
            "defensa": clip100(defensa),
            "fisico": clip100(fisico),
        })
    return pd.DataFrame(filas)

def punto_base_por_posicion(pos):
    # coordenadas estilo StatsBomb (120 x 80), atacando hacia x=120
    if pos == "Portero":
        return 10, 40
    if pos == "Defensa":
        return 35, 40
    if pos == "Mediocampista":
        return 62, 40
    return 95, 40  # Delantero

def media_global(row):
    """Nivel medio del jugador (0-100) para condicionar la puntuacion por partido."""
    return np.mean([row[c] for c in RADAR_COLS])


def generar_partidos_y_toques(jugadores_df, n_partidos=N_ULTIMOS_PARTIDOS):
    filas_partidos = []
    filas_toques = []
    partido_uid = 0

    for _, row in jugadores_df.iterrows():
        cx, cy = punto_base_por_posicion(row["posicion"])
        nivel = media_global(row)

        for j in range(n_partidos):
            partido_uid += 1
            # jornada 1 = la mas antigua, jornada n = la mas reciente
            jornada = j + 1
            fecha = FECHA_BASE - timedelta(days=7 * (n_partidos - jornada))

            rival = RIVALES[rng.integers(0, len(RIVALES))]
            condicion = "Local" if rng.random() < 0.5 else "Visitante"

            ventaja = 0.35 if condicion == "Local" else -0.15
            goles_favor = int(rng.poisson(max(0.2, 1.25 + ventaja)))
            goles_contra = int(rng.poisson(max(0.2, 1.25 - ventaja)))

            if goles_favor > goles_contra:
                resultado = "Victoria"
            elif goles_favor < goles_contra:
                resultado = "Derrota"
            else:
                resultado = "Empate"

            # a un portero rara vez lo sustituyen
            if row["posicion"] == "Portero":
                minutos = int(rng.choice([90, 90, 90, 90, 90, 90, 45]))
            else:
                minutos = int(rng.choice([90, 90, 90, 82, 75, 68, 45, 30]))

            # puntuacion 1-10 anclada al nivel del jugador, con ruido por partido
            # y un pequeño empujon segun el resultado del equipo
            bonus_resultado = {"Victoria": 0.35, "Empate": 0.0, "Derrota": -0.35}[resultado]
            puntuacion = nivel / 100 * 4.5 + 4.2 + bonus_resultado + rng.normal(0, 0.55)
            puntuacion = round(float(np.clip(puntuacion, 3.0, 9.8)), 1)

            if row["posicion"] == "Delantero":
                goles_jug = int(rng.poisson(0.45))
                asist_jug = int(rng.poisson(0.22))
            elif row["posicion"] == "Mediocampista":
                goles_jug = int(rng.poisson(0.15))
                asist_jug = int(rng.poisson(0.30))
            elif row["posicion"] == "Defensa":
                goles_jug = int(rng.poisson(0.06))
                asist_jug = int(rng.poisson(0.08))
            else:
                goles_jug = 0
                asist_jug = 0

            # un jugador no puede marcar ni asistir mas goles de los que hizo su
            # equipo, y no puede asistirse a si mismo: goles + asistencias <= GF
            goles_jug = min(goles_jug, goles_favor)
            asist_jug = min(asist_jug, goles_favor - goles_jug)

            filas_partidos.append({
                "partido_id": partido_uid,
                "jugador_id": row["id"],
                "jornada": jornada,
                "fecha": fecha.isoformat(),
                "rival": rival,
                "condicion": condicion,
                "goles_favor": goles_favor,
                "goles_contra": goles_contra,
                "resultado": resultado,
                "puntuacion": puntuacion,
                "minutos": minutos,
                "goles_jugador": goles_jug,
                "asistencias_jugador": asist_jug,
            })

            # toques del partido: proporcionales a los minutos jugados,
            # con el foco desplazado levemente respecto de su zona habitual
            n_toques = int(rng.integers(28, 62) * minutos / 90)
            desvio_x = rng.normal(0, 5)
            desvio_y = rng.normal(0, 4)
            xs = np.clip(rng.normal(cx + desvio_x, 12, n_toques), 0, 120)
            ys = np.clip(rng.normal(cy + desvio_y, 15, n_toques), 0, 80)
            for x, y in zip(xs, ys):
                filas_toques.append({
                    "partido_id": partido_uid,
                    "jugador_id": row["id"],
                    "x": round(float(x), 1),
                    "y": round(float(y), 1),
                })

    return pd.DataFrame(filas_partidos), pd.DataFrame(filas_toques)


if __name__ == "__main__":
    jugadores = generar_jugadores()
    jugadores.to_csv(DATA_DIR / "jugadores.csv", index=False)

    partidos, toques = generar_partidos_y_toques(jugadores)
    partidos.to_csv(DATA_DIR / "partidos.csv", index=False)
    toques.to_csv(DATA_DIR / "toques.csv", index=False)

    print(f"Generado data/jugadores.csv ({len(jugadores)} filas)")
    print(f"Generado data/partidos.csv ({len(partidos)} filas)")
    print(f"Generado data/toques.csv ({len(toques)} filas)")
