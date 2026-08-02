"""
Scouting Legionarios Bolivianos — panel de analisis con datos reales.

Los datos de jugador vienen de `database.py` y las estadisticas de SofaScore a
traves de `sofascore_api.py`. Nada aqui usa los CSV de prueba: el prototipo con
datos ficticios quedo en `app_prototipo_datos_prueba.py`.
"""
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch, Radar

from database import (
    POSICIONES_VALIDAS,
    obtener_todos_los_jugadores,
    obtener_jugadores_por_posicion,
    obtener_jugador_por_id,
)
from sofascore_api import (
    get_player_stats,
    get_player_heatmap,
    get_player_last_matches,
    get_next_matches,
    obtener_season_id,
    convertir_a_statsbomb,
    fecha_snapshot,
    estado_conexion,
)

st.set_page_config(
    page_title="Scouting Legionarios Bolivianos",
    page_icon="🇧🇴",
    layout="wide",
    initial_sidebar_state="expanded",
)

FONDO = "#0E1117"
PANEL = "#161A25"
BORDE = "#252B3B"
TEXTO = "#E6EAF3"
TEXTO_TENUE = "#8A93A8"
VERDE_NEON = "#00FF87"
AMARILLO = "#FFD166"
ROJO = "#FF5A5F"

# Colores de la bandera, reservados para la franja de identidad. No se usan
# para datos: el verde neon sigue siendo el acento de la interfaz y los tres
# colores de estado (verde/ambar/rojo) tienen que leerse sin competencia.
ROJO_BO = "#D52B1E"
AMARILLO_BO = "#F9E300"
VERDE_BO = "#007A33"

CUERPO_TECNICO = "Oscar Villegas"
ESLOGAN = "Construyendo el gol del futuro"

NOMBRE_POSICION = {
    "POR": "Portero",
    "DF": "Defensa",
    "MC": "Mediocampista",
    "ED": "Extremo",
    "DEL": "Delantero",
}

COLOR_RESULTADO = {
    "Victoria": VERDE_NEON,
    "Empate": TEXTO_TENUE,
    "Derrota": ROJO,
}

COLOR_ESTADO = {
    "Jugo": VERDE_NEON,
    "Banquillo": AMARILLO,
    "No convocado": ROJO,
}

DIAS_SEMANA = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]

# Metricas del desglose por 90 minutos. tipo "pct" son porcentajes, que no se
# normalizan por minutos.
METRICAS_TABLA = [
    ("Goles", "goals", "p90"),
    ("Asistencias", "assists", "p90"),
    ("xG", "expected_goals", "p90"),
    ("xA", "expected_assists", "p90"),
    ("Remates", "total_shots", "p90"),
    ("Remates a puerta", "shots_on_target", "p90"),
    ("Pases clave", "key_passes", "p90"),
    ("Ocasiones claras creadas", "big_chances_created", "p90"),
    ("Pases completados", "accurate_passes", "p90"),
    ("Pases último tercio", "accurate_final_third_passes", "p90"),
    ("Centros completados", "accurate_crosses", "p90"),
    ("Regates completados", "successful_dribbles", "p90"),
    ("Toques", "touches", "p90"),
    ("Recuperaciones", "ball_recovery", "p90"),
    ("Entradas", "tackles", "p90"),
    ("Entradas ganadas", "tackles_won", "p90"),
    ("Intercepciones", "interceptions", "p90"),
    ("Despejes", "clearances", "p90"),
    ("Bloqueos", "blocks", "p90"),
    ("Duelos ganados", "total_duels_won", "p90"),
    ("Balones perdidos", "possession_lost", "p90"),
    ("Faltas cometidas", "fouls", "p90"),
    ("Faltas recibidas", "was_fouled", "p90"),
    ("Acierto de pase", "accurate_passes_pct", "pct"),
    ("Duelos ganados", "duels_won_pct", "pct"),
    ("Duelos terrestres", "ground_duels_won_pct", "pct"),
    ("Duelos aereos", "aerial_duels_won_pct", "pct"),
    ("Regates completados", "successful_dribbles_pct", "pct"),
]

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {FONDO}; }}

    html, body, [class*="css"] {{
        font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
        letter-spacing: 0.01em;
    }}

    section[data-testid="stSidebar"] {{
        background-color: {PANEL};
        border-right: 1px solid {BORDE};
    }}

    .tarjeta {{
        position: relative;
        background: linear-gradient(160deg, {PANEL} 0%, #11151F 100%);
        border: 1px solid {BORDE};
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 16px;
        /* sombra en dos capas: uno de contacto y otro de profundidad */
        box-shadow: 0 1px 1px rgba(0,0,0,0.6), 0 14px 34px rgba(0,0,0,0.45);
    }}
    /* filo superior que da relieve sin anadir un borde visible */
    .tarjeta::before {{
        content: "";
        position: absolute;
        top: 0; left: 16px; right: 16px;
        height: 1px;
        background: linear-gradient(90deg,
            transparent, rgba(255,255,255,0.10), transparent);
    }}

    /* ── identidad ── */
    /* La bandera va como sello corto, no como banda a todo lo ancho: a pagina
       completa competia con los datos, que son lo que hay que mirar. */
    .franja-bo {{
        width: 132px;
        height: 3px;
        border-radius: 2px;
        background: linear-gradient(90deg,
            {ROJO_BO} 0%, {ROJO_BO} 33.3%,
            {AMARILLO_BO} 33.3%, {AMARILLO_BO} 66.6%,
            {VERDE_BO} 66.6%, {VERDE_BO} 100%);
    }}
    /* regla completa: el sello a la izquierda y una linea tenue de continuacion */
    .regla-identidad {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .regla-identidad .linea {{
        flex: 1;
        height: 1px;
        background: {BORDE};
    }}

    /* tarjeta de metrica propia, para igualar a las de Streamlit */
    .metrica {{
        background: {PANEL};
        border: 1px solid {BORDE};
        border-radius: 12px;
        padding: 12px 14px;
    }}
    .metrica .etiqueta-metrica {{
        color: {TEXTO_TENUE};
        font-size: 0.64rem;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        margin-bottom: 4px;
        /* la etiqueta se parte en dos lineas antes que recortarse: en columnas
           estrechas "Asistencias" se quedaba en "A" */
        white-space: normal;
        overflow-wrap: anywhere;
        line-height: 1.25;
        min-height: 1.6em;
    }}
    .metrica .valor-metrica {{
        color: {TEXTO};
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.2;
        white-space: nowrap;
    }}

    /* ── cancha con los jugadores por puesto ── */
    .cancha {{
        position: relative;
        width: 100%;
        aspect-ratio: 14 / 10;
        min-height: 560px;
        background:
            repeating-linear-gradient(90deg,
                rgba(255,255,255,0.014) 0 6%, transparent 6% 12%),
            linear-gradient(120deg, #0B2A1D 0%, #0A2318 55%, #081912 100%);
        border: 1px solid {BORDE};
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 1px 1px rgba(0,0,0,0.6), 0 18px 40px rgba(0,0,0,0.5);
    }}
    .cancha svg {{ position: absolute; inset: 0; width: 100%; height: 100%; }}

    /* tarjeta de un puesto: titulo del sitio y los jugadores apilados */
    .puesto {{
        position: absolute;
        transform: translate(-50%, -50%);
        /* ancho acotado: si una tarjeta crece con un nombre largo se come el
           sitio de la de al lado y se pisan */
        min-width: 166px;
        max-width: 196px;
        background: rgba(9,14,21,0.90);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 10px;
        overflow: hidden;
        backdrop-filter: blur(3px);
        box-shadow: 0 8px 22px rgba(0,0,0,0.55);
    }}
    .puesto-titulo {{
        padding: 5px 10px 4px 10px;
        color: rgba(230,234,243,0.55);
        font-size: 0.56rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        background: rgba(255,255,255,0.05);
        border-bottom: 1px solid rgba(255,255,255,0.10);
        white-space: nowrap;
    }}

    a.fila-puesto {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
        padding: 6px 10px;
        text-decoration: none !important;
        border-bottom: 1px solid rgba(255,255,255,0.07);
        transition: background 0.12s ease;
    }}
    a.fila-puesto:last-child {{ border-bottom: none; }}
    a.fila-puesto:hover {{ background: rgba(0,255,135,0.12); }}
    a.fila-puesto .nombre-jugador {{
        color: {TEXTO};
        font-size: 0.74rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    a.fila-puesto .nota-jugador {{ flex-shrink: 0; }}
    a.fila-puesto .nota-jugador {{
        font-size: 0.70rem;
        font-weight: 700;
    }}

    .masthead {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 24px;
        margin: 2px 0 10px 0;
    }}
    .masthead-titulo {{
        color: {TEXTO};
        font-size: 1.02rem;
        font-weight: 800;
        letter-spacing: 0.20em;
        text-transform: uppercase;
        line-height: 1.2;
    }}
    .masthead-eslogan {{
        color: {VERDE_NEON};
        font-size: 0.76rem;
        font-style: italic;
        letter-spacing: 0.05em;
        margin-top: 3px;
        opacity: 0.85;
    }}
    .masthead-ct {{
        text-align: right;
        white-space: nowrap;
    }}
    .masthead-ct .rol {{
        color: {TEXTO_TENUE};
        font-size: 0.62rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
    }}
    .masthead-ct .nombre {{
        color: {TEXTO};
        font-size: 0.92rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }}

    .etiqueta {{
        color: {TEXTO_TENUE};
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        margin-bottom: 4px;
    }}
    .valor {{ color: {TEXTO}; font-size: 1.06rem; font-weight: 600; }}

    .rating-num {{
        font-size: 3.7rem;
        font-weight: 800;
        line-height: 1.05;
        margin: 2px 0 0 0;
        /* sin esto el numero se parte y el ultimo decimal cae a la linea de
           abajo: "6.30" se leia como "6.3" con un "0" suelto debajo */
        white-space: nowrap;
    }}
    .rating-pie {{ color: {TEXTO_TENUE}; font-size: 0.78rem; margin-top: 6px; }}

    .chip {{
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        border: 1px solid {BORDE};
        color: {TEXTO_TENUE};
    }}

    .titulo-seccion {{
        color: {TEXTO};
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        margin: 0 0 10px 2px;
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid {BORDE};
        border-radius: 12px;
        overflow: hidden;
    }}

    /* las metricas de Streamlit, con el mismo lenguaje que las tarjetas */
    div[data-testid="stMetric"] {{
        background: {PANEL};
        border: 1px solid {BORDE};
        border-radius: 12px;
        padding: 12px 14px;
    }}
    div[data-testid="stMetricLabel"] p {{
        color: {TEXTO_TENUE} !important;
        font-size: 0.66rem !important;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 1.55rem !important;
        font-weight: 700;
    }}

    /* pestañas: subrayado fino en vez del recuadro por defecto */
    button[data-baseweb="tab"] {{
        font-size: 0.74rem !important;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-weight: 700;
    }}

    /* separadores mas discretos */
    hr {{ border-color: {BORDE} !important; opacity: 0.7; }}

    #MainMenu, footer {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def color_rating(rating):
    """Verde sobre 7.0, amarillo entre 6.5 y 6.9, rojo por debajo.

    Un NaN (partido sin nota, por banquillo o no convocatoria) tiene que salir
    en gris: si cayera en el ultimo caso se pintaria de rojo y pareceria una
    actuacion pesima en vez de una ausencia.
    """
    if rating is None or (isinstance(rating, float) and math.isnan(rating)):
        return TEXTO_TENUE
    if rating > 7.0:
        return VERDE_NEON
    if rating >= 6.5:
        return AMARILLO
    return ROJO


def color_nota_texto(texto):
    """Color de una nota que ya viene formateada como texto ("6.70", "—")."""
    try:
        return color_rating(float(texto))
    except (TypeError, ValueError):
        return TEXTO_TENUE


def tarjeta_metrica(etiqueta, valor, color=None):
    """Tarjeta de metrica con la etiqueta completa.

    Se usa en lugar de `st.metric` porque en columnas estrechas Streamlit
    recorta la etiqueta a la primera letra ("Asistencias" quedaba en "A").
    """
    tono = color or TEXTO
    return (
        f"<div class='metrica'>"
        f"<div class='etiqueta-metrica'>{etiqueta}</div>"
        f"<div class='valor-metrica' style='color:{tono}'>{valor}</div>"
        f"</div>"
    )


def por_90(valor, minutos):
    """Normaliza una metrica a 90 minutos. None si no hay dato o no jugo."""
    if valor is None or not minutos:
        return None
    return valor / minutos * 90


# Metricas del radar por posicion. Cada entrada es
# (etiqueta, clave, tipo, maximo_de_referencia)
#   tipo "p90"  -> se normaliza a 90 minutos
#   tipo "pct"  -> ya es un porcentaje, se usa tal cual sobre 100
#
# Los maximos son valores de referencia razonables para un futbolista de elite
# en esa metrica, NO percentiles de la liga: con 6 jugadores en la base no hay
# muestra para calcular percentiles reales.
RADAR_POR_POSICION = {
    "POR": [
        # A un portero no se le mide con duelos ni despejes. "Porterias a cero"
        # va en porcentaje sobre los partidos jugados, y no se usa "goles
        # encajados" porque en un radar cuanto mas lejos del centro mejor, y ahi
        # seria al reves.
        ("Paradas", "saves", "p90", 5.0),
        ("Paradas en area", "saves_inside_box", "p90", 4.0),
        ("Porterias a cero %", "clean_sheets_pct", "pct", 100),
        ("Salidas ganadas", "successful_runs_out", "p90", 1.5),
        ("Blocajes altos", "high_claims", "p90", 2.0),
        ("Acierto pase %", "accurate_passes_pct", "pct", 100),
    ],
    "DF": [
        ("Duelos ganados %", "duels_won_pct", "pct", 100),
        ("Intercepciones", "interceptions", "p90", 4.0),
        ("Despejes", "clearances", "p90", 8.0),
        ("Entradas ganadas", "tackles_won", "p90", 4.0),
        ("Acierto pase %", "accurate_passes_pct", "pct", 100),
        ("Pases clave", "key_passes", "p90", 1.5),
    ],
    "MC": [
        ("Acierto pase %", "accurate_passes_pct", "pct", 100),
        ("Recuperaciones", "ball_recovery", "p90", 8.0),
        ("Conducciones", "successful_dribbles", "p90", 3.0),
        ("Pases clave", "key_passes", "p90", 3.0),
        ("Pases último tercio", "accurate_final_third_passes", "p90", 14.0),
        ("Duelos ganados %", "duels_won_pct", "pct", 100),
    ],
    "ED": [
        ("Goles", "goals", "p90", 0.8),
        ("xG", "expected_goals", "p90", 0.8),
        ("Remates", "total_shots", "p90", 4.0),
        ("Regates", "successful_dribbles", "p90", 4.0),
        ("Pases clave", "key_passes", "p90", 3.0),
        ("Duelos ganados %", "duels_won_pct", "pct", 100),
    ],
}
RADAR_POR_POSICION["DEL"] = RADAR_POR_POSICION["ED"]


def valores_radar(stats, posicion):
    """Devuelve (etiquetas, valores_0_100, detalle, metricas_sin_dato).

    Las metricas que la liga no publica (xG en Ecuador, por ejemplo) se
    devuelven aparte para poder avisarlo en pantalla en vez de pintar un 0 que
    se leeria como bajo rendimiento.
    """
    definicion = RADAR_POR_POSICION.get(posicion, RADAR_POR_POSICION["MC"])
    minutos = stats.get("minutes_played") or 0

    # Metricas derivadas que la API no entrega ya calculadas.
    derivadas = {}
    partidos = stats.get("appearances") or 0
    if partidos:
        derivadas["clean_sheets_pct"] = (stats.get("clean_sheets") or 0) / partidos * 100

    etiquetas, valores, detalle, sin_dato = [], [], [], []

    for etiqueta, clave, tipo, maximo in definicion:
        bruto = derivadas.get(clave, stats.get(clave))

        if tipo == "pct":
            crudo = bruto
        else:
            crudo = por_90(bruto, minutos)

        if crudo is None:
            sin_dato.append(etiqueta)
            normalizado = 0.0
            crudo_txt = "s/d"
        else:
            normalizado = float(np.clip(crudo / maximo * 100, 0, 100))
            crudo_txt = f"{crudo:.2f}" if tipo == "p90" else f"{crudo:.1f}%"

        etiquetas.append(etiqueta)
        valores.append(normalizado)
        detalle.append(crudo_txt)

    return etiquetas, valores, detalle, sin_dato


def dibujar_radar(etiquetas, valores):
    radar = Radar(
        etiquetas,
        [0] * len(etiquetas),
        [100] * len(etiquetas),
        num_rings=4,
        ring_width=1,
        center_circle_radius=1,
    )
    fig, ax = radar.setup_axis(figsize=(5.4, 5.4))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    radar.draw_circles(ax=ax, facecolor="#1A1F2E", edgecolor=BORDE, lw=0.8)
    # `kwargs_rings` es obligatorio: son los anillos que se pintan ENCIMA del
    # radar y, si no se pasan, matplotlib los rellena de azul por defecto y
    # tapan el verde.
    radar.draw_radar(
        valores,
        ax=ax,
        kwargs_radar={"facecolor": VERDE_NEON, "alpha": 0.55,
                      "edgecolor": VERDE_NEON, "linewidth": 2.0},
        kwargs_rings={"facecolor": FONDO, "alpha": 0.20, "edgecolor": "none"},
    )
    radar.draw_range_labels(ax=ax, fontsize=6.5, color=TEXTO_TENUE)
    radar.draw_param_labels(ax=ax, fontsize=9.5, color=TEXTO)
    return fig


# Sitio de cada puesto sobre el campo, en porcentaje (x = avance hacia la
# porteria rival, y = de arriba abajo). La cancha va en horizontal y se ataca
# hacia la derecha, como una pizarra tactica.
SITIO_PUESTO = {
    # el portero va en 11 y no pegado a la linea de fondo: su tarjeta se
    # centra sobre el punto y a menos de eso se salia del campo
    "POR": (8, 50, "Portero"),
    "LI": (24, 17, "Lateral izquierdo"),
    "DFC": (24, 50, "Defensa central"),
    "LD": (24, 83, "Lateral derecho"),
    "MCD": (41, 50, "Mediocentro defensivo"),
    "MC": (48, 26, "Mediocentro"),
    "MCO": (52, 62, "Mediapunta"),
    "EI": (72, 16, "Extremo izquierdo"),
    "ED": (72, 84, "Extremo derecho"),
    "DC": (85, 50, "Delantero centro"),
}

# Si un jugador no tuviera puesto concreto, cae en el sitio de su linea.
SITIO_POR_DEFECTO = {"POR": "POR", "DF": "DFC", "MC": "MC", "ED": "ED", "DEL": "DC"}


def dibujar_cancha_jugadores(jugadores_con_nota) -> str:
    """Pizarra tactica con cada jugador en su puesto.

    Cada puesto es una tarjeta apilada, al estilo de los onces ideales: si hay
    varios jugadores para el mismo sitio, se listan uno debajo de otro
    ordenados por su momento de forma.

    Cada nombre es un enlace a `?jugador=<id>`, que la app lee al cargar para
    abrir esa ficha.
    """
    lineas_svg = """
    <svg viewBox="0 0 140 100" preserveAspectRatio="none">
      <g fill="none" stroke="rgba(255,255,255,0.16)" stroke-width="0.30">
        <rect x="1.5" y="1.5" width="137" height="97"/>
        <line x1="70" y1="1.5" x2="70" y2="98.5"/>
        <circle cx="70" cy="50" r="11"/>
        <rect x="1.5" y="26" width="15" height="48"/>
        <rect x="1.5" y="38" width="6" height="24"/>
        <rect x="123.5" y="26" width="15" height="48"/>
        <rect x="132.5" y="38" width="6" height="24"/>
      </g>
    </svg>
    """

    # se agrupan los jugadores por puesto
    por_puesto = {}
    for jugador in jugadores_con_nota:
        clave = jugador.get("puesto") or SITIO_POR_DEFECTO.get(
            jugador["main_position"], "MC"
        )
        por_puesto.setdefault(clave, []).append(jugador)

    bloques = [lineas_svg]
    for puesto, (x, y, titulo) in SITIO_PUESTO.items():
        del_puesto = por_puesto.get(puesto)
        if not del_puesto:
            continue

        del_puesto.sort(
            key=lambda j: j["nota"] if j["nota"] is not None else -1, reverse=True
        )

        filas = []
        for jugador in del_puesto:
            nota = jugador.get("nota")
            color = color_rating(nota)
            nota_txt = f"{nota:.1f}" if isinstance(nota, (int, float)) else "s/d"
            filas.append(
                f"<a class='fila-puesto' href='?jugador={jugador['id']}' "
                f"target='_self' title='{jugador['name']} · {jugador['current_club']}'>"
                f"<span class='nombre-jugador'>{jugador['name']}</span>"
                f"<span class='nota-jugador' style='color:{color}'>{nota_txt}</span>"
                f"</a>"
            )

        bloques.append(
            f"<div class='puesto' style='left:{x}%;top:{y}%'>"
            f"<div class='puesto-titulo'>{titulo}</div>"
            f"{''.join(filas)}"
            f"</div>"
        )

    return f"<div class='cancha'>{''.join(bloques)}</div>"


def mapa_calor_cmap():
    """Degradado oscuro -> verde neon -> amarillo -> rojo."""
    return LinearSegmentedColormap.from_list(
        "scouting_neon",
        ["#0E1117", "#0B3D2E", VERDE_NEON, AMARILLO, ROJO],
    )


def dibujar_heatmap(xs, ys, pesos):
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color=FONDO,
        line_color="#39405420",
        linewidth=1.1,
        line_zorder=3,
    )
    fig, ax = pitch.draw(figsize=(7.2, 5))
    fig.patch.set_alpha(0)

    if len(xs) >= 5:
        pitch.kdeplot(
            xs, ys, ax=ax,
            weights=pesos,
            cmap=mapa_calor_cmap(),
            fill=True,
            levels=120,
            thresh=0.02,
            bw_adjust=0.72,
            alpha=0.92,
            zorder=1,
        )
    # flecha de sentido de ataque
    ax.annotate(
        "", xy=(112, -4.5), xytext=(8, -4.5),
        arrowprops=dict(arrowstyle="-|>", color=TEXTO_TENUE, lw=1.2),
        annotation_clip=False,
    )
    ax.text(60, -8.5, "S E N T I D O   D E   A T A Q U E", color=TEXTO_TENUE,
            fontsize=6.5, ha="center", va="top")
    return fig


# ───────────────────────── barra lateral ─────────────────────────

with st.sidebar:
    st.markdown(
        f"""
        <div class='franja-bo' style='margin-bottom:14px'></div>
        <div style='font-size:1.0rem;font-weight:800;letter-spacing:0.14em;
             color:{TEXTO};line-height:1.25'>SCOUTING<br>LEGIONARIOS</div>
        <div style='color:{TEXTO_TENUE};font-size:0.68rem;letter-spacing:0.14em;
             text-transform:uppercase;margin-top:6px'>Bolivianos en el exterior</div>
        <hr style='border-color:{BORDE};margin:16px 0'>
        """,
        unsafe_allow_html=True,
    )

    # Si se llega desde un nombre de la cancha, viene ?jugador=<id> en la URL.
    # Se pasa a session_state y se limpia la URL en el acto: si se dejara, en
    # cada recarga volveria a imponer ese jugador y el selector quedaria muerto.
    desde_cancha = st.query_params.get("jugador")
    if desde_cancha:
        elegido_por_cancha = obtener_jugador_por_id(desde_cancha)
        if elegido_por_cancha:
            st.session_state["jugador_sel"] = elegido_por_cancha["name"]
            # el filtro se abre para que el jugador siempre este entre las
            # opciones, venga de la posicion que venga
            st.session_state["filtro_pos"] = "Todas"
        st.query_params.clear()

    filtro_posicion = st.selectbox(
        "Posicion",
        ["Todas"] + list(POSICIONES_VALIDAS),
        format_func=lambda p: p if p == "Todas" else f"{p} · {NOMBRE_POSICION[p]}",
        key="filtro_pos",
    )

    if filtro_posicion == "Todas":
        candidatos = obtener_todos_los_jugadores()
    else:
        candidatos = obtener_jugadores_por_posicion(filtro_posicion)

    if not candidatos:
        st.warning("No hay jugadores en esa posicion.")
        st.stop()

    nombres = {j["name"]: j for j in candidatos}
    # Si el jugador guardado ya no encaja con el filtro, se vuelve al primero
    # para que el selector no reciba un valor que no esta entre sus opciones.
    if st.session_state.get("jugador_sel") not in nombres:
        st.session_state["jugador_sel"] = next(iter(nombres))

    nombre_elegido = st.selectbox("Jugador", list(nombres), key="jugador_sel")
    jugador = nombres[nombre_elegido]

    st.markdown(f"<hr style='border-color:{BORDE}'>", unsafe_allow_html=True)

    # Selector de temporada: en Rusia y Bulgaria la 26/27 acaba de arrancar y
    # trae 1 partido, mientras que la anterior tiene la campaña completa.
    season_id_actual, anio_actual, error_temporada = obtener_season_id(
        jugador["sofascore_id"], jugador["tournament_id"]
    )
    season_elegida = season_id_actual
    if error_temporada:
        st.error(f"Temporada: {error_temporada}")
    else:
        st.caption(f"Temporada en curso: **{anio_actual}**")
        usar_otra = st.text_input(
            "season_id manual (opcional)",
            value="",
            placeholder=str(season_id_actual or ""),
            help="Para consultar una temporada anterior con la campaña completa.",
        ).strip()
        if usar_otra:
            if usar_otra.isdigit():
                season_elegida = int(usar_otra)
            else:
                st.warning("El season_id debe ser un numero.")

    st.markdown(f"<hr style='border-color:{BORDE}'>", unsafe_allow_html=True)

    if st.button("🔄 Forzar actualizacion de datos", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Los datos se guardan en cache 7 dias.")

    # Semaforo de origen de los datos: en verde la app se actualiza sola; en
    # ambar hay que refrescar la copia a mano y volver a subirla.
    conexion = estado_conexion()
    generado = fecha_snapshot()

    if conexion["en_vivo"]:
        st.markdown(
            f"<div style='color:{VERDE_NEON};font-size:0.78rem;font-weight:600'>"
            f"🟢 Datos en vivo de SofaScore</div>"
            f"<div style='color:{TEXTO_TENUE};font-size:0.7rem'>"
            f"Se actualizan solos cada 7 dias.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='color:{AMARILLO};font-size:0.78rem;font-weight:600'>"
            f"🟡 Sin acceso directo a SofaScore</div>"
            f"<div style='color:{TEXTO_TENUE};font-size:0.7rem'>"
            f"Mostrando la copia del {generado[:10] if generado else '—'}. "
            f"Para refrescarla hay que regenerarla y volver a subirla.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <hr style='border-color:{BORDE};margin:20px 0 14px 0'>
        <div style='color:{TEXTO_TENUE};font-size:0.60rem;letter-spacing:0.22em;
             text-transform:uppercase'>Cuerpo tecnico</div>
        <div style='color:{TEXTO};font-size:0.90rem;font-weight:700;
             letter-spacing:0.03em;margin-top:2px'>{CUERPO_TECNICO}</div>
        <div style='color:{VERDE_NEON};font-size:0.70rem;font-style:italic;
             opacity:0.8;margin-top:6px'>{ESLOGAN}</div>
        """,
        unsafe_allow_html=True,
    )


# Etiqueta de la temporada: si se pidio una manual no conocemos su nombre,
# asi que se muestra el id para que quede claro que dato se esta viendo.
etiqueta_temporada = (
    anio_actual if season_elegida == season_id_actual else f"id {season_elegida}"
) or "—"


# ───────────────────────── datos ─────────────────────────

stats = get_player_stats(
    jugador["sofascore_id"], jugador["tournament_id"], season_elegida
)
heatmap = get_player_heatmap(
    jugador["sofascore_id"], jugador["tournament_id"], season_elegida
)

st.markdown(
    f"""
    <div class='masthead'>
      <div>
        <div class='masthead-titulo'>Scouting Legionarios</div>
        <div class='masthead-eslogan'>{ESLOGAN}</div>
      </div>
      <div class='masthead-ct'>
        <div class='rol'>Cuerpo tecnico</div>
        <div class='nombre'>{CUERPO_TECNICO}</div>
      </div>
    </div>
    <div class='regla-identidad'>
      <div class='franja-bo'></div>
      <div class='linea'></div>
    </div>
    <div style='height:18px'></div>
    """,
    unsafe_allow_html=True,
)

tab_ficha, tab_cancha, tab_plantel = st.tabs(
    ["  Ficha individual  ", "  Cancha  ", "  Todos los jugadores  "]
)

with tab_ficha:
    st.markdown(
        f"<div style='font-size:1.6rem;font-weight:800;color:{TEXTO};"
        f"letter-spacing:0.02em'>{jugador['name']}</div>"
        f"<div style='color:{TEXTO_TENUE};font-size:0.8rem;margin-bottom:14px'>"
        f"{jugador['current_club']} · {jugador['league_name']} · "
        f"temporada {etiqueta_temporada}</div>",
        unsafe_allow_html=True,
    )

    if not stats["ok"]:
        st.error(f"No se pudieron cargar las estadisticas: {stats['error']}")

    col_ficha, col_radar, col_calor = st.columns([1, 1.25, 1.35], gap="large")

    # ── Columna 1: ficha tecnica y rating ──
    with col_ficha:
        st.markdown("<div class='titulo-seccion'>Ficha tecnica</div>", unsafe_allow_html=True)

        rating = stats["rating"]
        color = color_rating(rating)
        rating_txt = f"{rating:.2f}" if rating is not None else "s/d"

        st.markdown(
            f"""
            <div class='tarjeta'>
              <div class='etiqueta'>Rating SofaScore</div>
              <div class='rating-num' style='color:{color};
                   text-shadow:0 0 26px {color}55'>{rating_txt}</div>
              <div class='rating-pie'>{stats['appearances']} partidos ·
                   {stats['minutes_played']} min</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class='tarjeta'>
              <div class='etiqueta'>Club</div><div class='valor'>{jugador['current_club']}</div>
              <div style='height:12px'></div>
              <div class='etiqueta'>Liga</div><div class='valor'>{jugador['league_name']}</div>
              <div style='height:12px'></div>
              <div class='etiqueta'>Posicion</div>
              <div class='valor'>{NOMBRE_POSICION.get(jugador['main_position'], jugador['main_position'])}
                <span class='chip'>{jugador['main_position']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        for columna, etiqueta, valor in (
            (c1, "Goles", stats["goals"]),
            (c2, "Asistencias", stats["assists"]),
            (c3, "De titular", stats["matches_started"]),
        ):
            columna.markdown(tarjeta_metrica(etiqueta, valor), unsafe_allow_html=True)

    # ── Columna 2: radar ──
    with col_radar:
        st.markdown(
            f"<div class='titulo-seccion'>Radar · {NOMBRE_POSICION.get(jugador['main_position'], '')}</div>",
            unsafe_allow_html=True,
        )
        etiquetas, valores, detalle, sin_dato = valores_radar(stats, jugador["main_position"])

        if stats["minutes_played"]:
            st.pyplot(dibujar_radar(etiquetas, valores), width="stretch")
            st.caption(
                "Escala 0-100 sobre maximos de referencia fijos, no percentiles de la liga."
            )
            if sin_dato:
                st.info(f"Sin dato en esta liga: {', '.join(sin_dato)} (se dibujan a 0).")
        else:
            st.warning("El jugador no registra minutos en esta temporada.")

    # ── Columna 3: mapa de calor ──
    with col_calor:
        st.markdown("<div class='titulo-seccion'>Mapa de calor</div>", unsafe_allow_html=True)

        if heatmap["ok"]:
            xs, ys = convertir_a_statsbomb(heatmap["x"], heatmap["y"])
            st.pyplot(dibujar_heatmap(xs, ys, heatmap["count"]), width="stretch")
            st.caption(
                f"{heatmap['total_puntos']} posiciones registradas · "
                "banda izquierda arriba, banda derecha abajo."
            )
        else:
            st.warning(f"Sin mapa de calor: {heatmap['error']}")

    # ───────────────────── ultimos 6 partidos ─────────────────────

    st.markdown(f"<hr style='border-color:{BORDE};margin-top:8px'>", unsafe_allow_html=True)
    st.markdown("<div class='titulo-seccion'>Ultimos 6 partidos</div>", unsafe_allow_html=True)

    ultimos = get_player_last_matches(jugador["sofascore_id"])

    if not ultimos["ok"]:
        st.warning(f"Sin partidos recientes: {ultimos['error']}")
    else:
        media = ultimos["media_rating"]
        color_media = color_rating(media)

        r1, r2, r3, r4, r5 = st.columns(5)
        r1.markdown(
            tarjeta_metrica(
                "Media ultimos 6",
                media if media is not None else "s/d",
                color_media,
            ),
            unsafe_allow_html=True,
        )
        for columna, etiqueta, valor, tono in (
            (r2, "Jugados", ultimos["jugados"], VERDE_NEON),
            (r3, "Banquillo", ultimos["banquillo"], AMARILLO),
            (r4, "No convocado", ultimos["no_convocado"], ROJO),
            (r5, "Minutos", ultimos["minutos_totales"], None),
        ):
            columna.markdown(
                tarjeta_metrica(etiqueta, valor, tono), unsafe_allow_html=True
            )

        filas_partidos = []
        for p in ultimos["partidos"]:
            fecha = datetime.fromtimestamp(p["timestamp"], tz=timezone.utc)
            marcador = f"{p['goles_local']}-{p['goles_visitante']}"
            filas_partidos.append({
                "Fecha": fecha.strftime("%d/%m/%Y"),
                "Competicion": p["competicion"],
                "Partido": f"{p['local']} {marcador} {p['visitante']}",
                "Cond.": "Local" if p["es_local"] else "Visitante",
                "Resultado": p["resultado"],
                "Estado": p["estado"].replace("Jugo", "Jugó"),
                "Min": p["minutos"],
                "Nota": p["rating"],
            })

        tabla_partidos = pd.DataFrame(filas_partidos)
        # La nota pasa a texto: dejandola numerica, Streamlit se come el decimal
        # final (6.70 se veia 6.7) y los partidos sin nota salian vacios sin
        # distinguirse de un dato que falta.
        tabla_partidos["Nota"] = pd.to_numeric(
            tabla_partidos["Nota"], errors="coerce"
        ).map(lambda v: "—" if pd.isna(v) else f"{v:.2f}")

        estilo_partidos = (
            tabla_partidos.style
            .map(lambda v: f"color:{color_nota_texto(v)};font-weight:700",
                 subset=["Nota"])
            .map(lambda v: f"color:{COLOR_RESULTADO.get(v, TEXTO)}", subset=["Resultado"])
            .map(
                lambda v: f"color:{COLOR_ESTADO.get(v.replace('Jugó', 'Jugo'), TEXTO)};"
                          "font-weight:600",
                subset=["Estado"],
            )
        )

        st.dataframe(estilo_partidos, width="stretch", hide_index=True)
        st.caption(
            "Los ultimos 6 partidos del equipo, sin importar la competicion "
            "(liga, copas y seleccion). Se marca si jugo, si fue al banquillo sin "
            "entrar o si no fue convocado. La media solo promedia los que jugo."
        )

    # ───────────────────── proximos 4 partidos ─────────────────────

    st.markdown(f"<hr style='border-color:{BORDE};margin-top:8px'>", unsafe_allow_html=True)
    st.markdown("<div class='titulo-seccion'>Proximos 4 partidos</div>", unsafe_allow_html=True)

    proximos = get_next_matches(jugador.get("club_id"))

    if not proximos["ok"]:
        st.warning(f"Sin calendario: {proximos['error']}")
    else:
        filas_proximos = []
        for p in proximos["partidos"]:
            fecha = datetime.fromtimestamp(p["timestamp"], tz=timezone.utc)
            filas_proximos.append({
                "Fecha": fecha.strftime("%d/%m/%Y"),
                "Dia": DIAS_SEMANA[fecha.weekday()],
                "Competicion": p["competicion"],
                "Condicion": p["condicion"],
                "Rival": p["rival"],
                "Partido": f"{p['local']} vs {p['visitante']}",
            })

        tabla_proximos = pd.DataFrame(filas_proximos)
        st.dataframe(
            tabla_proximos.style.map(
                lambda v: f"color:{VERDE_NEON if v == 'Local' else AMARILLO};font-weight:600",
                subset=["Condicion"],
            ),
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "Calendario del club, en horario UTC. Que el partido este programado no "
            "garantiza que el jugador vaya a ser convocado."
        )

    # ───────────────────── desglose por 90 ─────────────────────

    st.markdown(f"<hr style='border-color:{BORDE};margin-top:8px'>", unsafe_allow_html=True)
    st.markdown("<div class='titulo-seccion'>Desglose por 90 minutos</div>", unsafe_allow_html=True)

    minutos = stats.get("minutes_played") or 0
    filas = []
    for etiqueta, clave, tipo in METRICAS_TABLA:
        bruto = stats.get(clave)
        if tipo == "pct":
            filas.append({
                "Metrica": etiqueta,
                "Total": "—",
                "Por 90": "s/d" if bruto is None else f"{bruto:.1f}%",
            })
        else:
            p90 = por_90(bruto, minutos)
            filas.append({
                "Metrica": etiqueta,
                "Total": "s/d" if bruto is None else f"{bruto:g}",
                "Por 90": "s/d" if p90 is None else f"{p90:.2f}",
            })

    tabla = pd.DataFrame(filas)
    mitad = (len(tabla) + 1) // 2
    izq, der = st.columns(2, gap="large")
    izq.dataframe(tabla.iloc[:mitad], width="stretch", hide_index=True)
    der.dataframe(tabla.iloc[mitad:], width="stretch", hide_index=True)

    st.caption(
        f"Fuente: SofaScore · jugador {jugador['sofascore_id']} · "
        f"torneo {jugador['tournament_id']} · temporada {stats.get('season_id') or '—'}. "
        "Los porcentajes no se normalizan por 90 minutos."
    )


# ───────────────────── pestaña: cancha ─────────────────────

with tab_cancha:
    st.markdown(
        "<div class='titulo-seccion'>Plantel por puesto</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Toca un nombre para abrir su ficha. El numero es su media de los "
        "ultimos 6 partidos y el filo de color, como viene de rendimiento."
    )

    with st.spinner("Cargando el plantel..."):
        jugadores_cancha = []
        for j in obtener_todos_los_jugadores():
            u = get_player_last_matches(j["sofascore_id"])
            jugadores_cancha.append({**j, "nota": u["media_rating"]})

    # dentro de cada linea, primero los de mejor momento
    jugadores_cancha.sort(
        key=lambda j: j["nota"] if j["nota"] is not None else -1, reverse=True
    )

    st.markdown(dibujar_cancha_jugadores(jugadores_cancha), unsafe_allow_html=True)


# ───────────────────── pestaña: todos los jugadores ─────────────────────

with tab_plantel:
    st.markdown(
        "<div class='titulo-seccion'>Todos los legionarios registrados</div>",
        unsafe_allow_html=True,
    )

    jugadores_todos = obtener_todos_los_jugadores()

    with st.spinner(f"Consultando SofaScore para {len(jugadores_todos)} jugadores..."):
        filas_plantel = []
        for j in jugadores_todos:
            s = get_player_stats(j["sofascore_id"], j["tournament_id"])
            u = get_player_last_matches(j["sofascore_id"])
            filas_plantel.append({
                # la columna Abrir es un enlace a la propia app; al pulsarlo
                # llega ?jugador=<id> y se abre su ficha, igual que en la cancha
                "Abrir": f"?jugador={j['id']}",
                "Jugador": j["name"],
                "Pos": j["main_position"],
                "Club": j["current_club"],
                "Liga": j["league_name"],
                "Temp.": s.get("season_year") or "—",
                "PJ": s["appearances"],
                "Min": s["minutes_played"],
                "G": s["goals"],
                "A": s["assists"],
                "Nota temp.": s["rating"],
                "Media 6": u["media_rating"],
                "Jug.": u["jugados"],
                "Banq.": u["banquillo"],
                "No conv.": u["no_convocado"],
                "Min 6": u["minutos_totales"],
            })

    plantel = pd.DataFrame(filas_plantel)
    for columna in ("Nota temp.", "Media 6"):
        plantel[columna] = pd.to_numeric(plantel[columna], errors="coerce")

    # Se ordena por la media de los ultimos 6 y no por la nota de temporada:
    # para ver quien esta en forma AHORA, lo reciente manda.
    plantel = plantel.sort_values("Media 6", ascending=False, na_position="last")

    # Ya ordenado, las notas pasan a texto. Si se dejan numericas Streamlit las
    # reinterpreta y se come el cero final: 7.30 se veia como 7.3.
    for columna in ("Nota temp.", "Media 6"):
        plantel[columna] = plantel[columna].map(
            lambda v: "—" if pd.isna(v) else f"{v:.2f}"
        )

    st.dataframe(
        plantel.style.map(
            lambda v: f"color:{color_nota_texto(v)};font-weight:700",
            subset=["Nota temp.", "Media 6"],
        ),
        width="stretch",
        hide_index=True,
        column_config={
            "Abrir": st.column_config.LinkColumn(
                "Ficha", display_text="Ver perfil", width="small"
            ),
        },
    )

    con_datos = int(plantel["Media 6"].notna().sum())
    st.caption(
        f"{len(plantel)} legionarios · {con_datos} con minutos en sus ultimos 6 partidos. "
        "Ordenados por la media de los ultimos 6, que refleja el momento actual mejor "
        "que la nota acumulada de temporada. "
        "**Jug./Banq./No conv.** son los ultimos 6 partidos de su equipo."
    )

    st.info(
        "Lista obtenida de las convocatorias de las selecciones bolivianas "
        "(absoluta, Sub-23, Sub-20 y Sub-17). No incluye a bolivianos en el "
        "exterior que nunca hayan sido convocados: esos hay que anadirlos a mano "
        "con `utils/buscar_jugador.py`."
    )

plt.close("all")
