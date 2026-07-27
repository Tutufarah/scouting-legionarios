import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from mplsoccer import Pitch, Radar
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

DATA_DIR = Path(__file__).resolve().parent / "data"

RADAR_PARAMS = ["Finalizacion", "Creacion", "Pase", "Regate", "Defensa", "Fisico"]
RADAR_COLS = ["finalizacion", "creacion", "pase", "regate", "defensa", "fisico"]
COLOR_A = "#1a78cf"
COLOR_B = "#d70232"

st.set_page_config(page_title="Scouting Bolivia", page_icon="⚽", layout="wide")


def firma_datos():
    """Huella de los CSV para invalidar la cache cuando cambian en disco.
    Sin esto habria que reiniciar la app cada vez que se actualizan los datos."""
    return tuple(
        (ruta.name, ruta.stat().st_mtime_ns)
        for ruta in sorted(DATA_DIR.glob("*.csv"))
    )


@st.cache_data
def cargar_datos(firma):
    jugadores = pd.read_csv(DATA_DIR / "jugadores.csv")
    partidos = pd.read_csv(DATA_DIR / "partidos.csv", parse_dates=["fecha"])
    toques = pd.read_csv(DATA_DIR / "toques.csv")
    return jugadores, partidos, toques


def dibujar_radar(jugador_a, jugador_b=None):
    low = [0] * len(RADAR_PARAMS)
    high = [100] * len(RADAR_PARAMS)

    radar = Radar(RADAR_PARAMS, low, high, round_int=[True] * len(RADAR_PARAMS),
                  num_rings=4, ring_width=1, center_circle_radius=1)

    fig, ax = radar.setup_axis(figsize=(6, 6))
    radar.draw_circles(ax=ax, facecolor="#f2f2f2", edgecolor="#cccccc")

    valores_a = [jugador_a[c] for c in RADAR_COLS]
    if jugador_b is not None:
        valores_b = [jugador_b[c] for c in RADAR_COLS]
        radar.draw_radar_compare(valores_a, valores_b, ax=ax,
                                  kwargs_radar={"facecolor": COLOR_A, "alpha": 0.6},
                                  kwargs_compare={"facecolor": COLOR_B, "alpha": 0.5})
        ax.legend(
            handles=[
                Patch(facecolor=COLOR_A, alpha=0.6, label=jugador_a["nombre"]),
                Patch(facecolor=COLOR_B, alpha=0.5, label=jugador_b["nombre"]),
            ],
            loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8,
        )
    else:
        radar.draw_radar(valores_a, ax=ax,
                          kwargs_radar={"facecolor": COLOR_A, "alpha": 0.65})

    radar.draw_range_labels(ax=ax, fontsize=8)
    radar.draw_param_labels(ax=ax, fontsize=10)
    fig.patch.set_alpha(0)
    return fig


def dibujar_heatmap(toques_jugador):
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#0e1117", line_color="#5a5a5a")
    fig, ax = pitch.draw(figsize=(7, 5))
    fig.patch.set_alpha(0)

    if len(toques_jugador) >= 5:
        pitch.kdeplot(toques_jugador["x"], toques_jugador["y"], ax=ax,
                       cmap="Reds", fill=True, levels=100, alpha=0.75, zorder=0.5)
    pitch.scatter(toques_jugador["x"], toques_jugador["y"], ax=ax,
                  s=8, color="white", alpha=0.3)
    return fig


def dibujar_heatmap_partido(toques_partido):
    """Mapa de calor de un solo partido: con pocos toques, una rejilla lee
    mejor que un KDE, que tiende a inventar suavizado donde no hay datos."""
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#0e1117", line_color="#5a5a5a",
                  line_zorder=2)
    fig, ax = pitch.draw(figsize=(4, 2.8))
    fig.patch.set_alpha(0)

    if len(toques_partido) > 0:
        stats = pitch.bin_statistic(toques_partido["x"], toques_partido["y"],
                                     statistic="count", bins=(6, 4))
        # las zonas sin toques quedan transparentes para que se vea el campo,
        # igual que en el mapa acumulado
        stats["statistic"] = np.where(stats["statistic"] == 0, np.nan, stats["statistic"])
        cmap = plt.get_cmap("Reds").copy()
        cmap.set_bad(alpha=0)
        pitch.heatmap(stats, ax=ax, cmap=cmap, edgecolors="#0e1117", alpha=0.9)
    pitch.scatter(toques_partido["x"], toques_partido["y"], ax=ax,
                  s=6, color="white", alpha=0.45, zorder=3)
    return fig


def etiqueta_marcador(partido):
    """Marcador siempre en orden 'equipo del jugador - rival'."""
    return f"{partido['goles_favor']}-{partido['goles_contra']}"


ICONO_RESULTADO = {"Victoria": "🟢", "Empate": "⚪", "Derrota": "🔴"}


jugadores_df, partidos_df, toques_df = cargar_datos(firma_datos())

st.title("⚽ Scouting - Futbolistas Bolivianos en el Exterior")
st.caption(
    "Prototipo con datos de PRUEBA (ficticios), generados aleatoriamente. "
    "No representa jugadores ni estadisticas reales."
)

with st.sidebar:
    st.header("Filtros")
    posiciones = sorted(jugadores_df["posicion"].unique())
    filtro_posicion = st.multiselect("Posicion", posiciones, default=posiciones)

    paises = sorted(jugadores_df["pais_liga"].unique())
    filtro_pais = st.multiselect("Pais / Liga", paises, default=paises)

    rango_edad = st.slider(
        "Edad",
        int(jugadores_df["edad"].min()), int(jugadores_df["edad"].max()),
        (int(jugadores_df["edad"].min()), int(jugadores_df["edad"].max())),
    )

df_filtrado = jugadores_df[
    jugadores_df["posicion"].isin(filtro_posicion)
    & jugadores_df["pais_liga"].isin(filtro_pais)
    & jugadores_df["edad"].between(*rango_edad)
]

st.subheader(f"Jugadores encontrados: {len(df_filtrado)}")
st.dataframe(
    df_filtrado[
        ["nombre", "posicion", "club", "pais_liga", "edad", "partidos_jugados"] + RADAR_COLS
    ].rename(columns={
        "nombre": "Nombre", "posicion": "Posicion", "club": "Club",
        "pais_liga": "Pais/Liga", "edad": "Edad", "partidos_jugados": "PJ",
        "finalizacion": "Finalizacion", "creacion": "Creacion", "pase": "Pase",
        "regate": "Regate", "defensa": "Defensa", "fisico": "Fisico",
    }),
    width="stretch",
    hide_index=True,
)

st.divider()
st.subheader("Analisis individual")

if df_filtrado.empty:
    st.warning("No hay jugadores que cumplan los filtros seleccionados.")
    st.stop()

col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    nombre_a = st.selectbox("Jugador principal", df_filtrado["nombre"].tolist())
with col_sel2:
    opciones_b = ["(ninguno)"] + [n for n in df_filtrado["nombre"].tolist() if n != nombre_a]
    nombre_b = st.selectbox("Comparar con", opciones_b)

jugador_a = jugadores_df[jugadores_df["nombre"] == nombre_a].iloc[0]
jugador_b = None if nombre_b == "(ninguno)" else jugadores_df[jugadores_df["nombre"] == nombre_b].iloc[0]

col_info, col_radar, col_heat = st.columns([1, 1.4, 1.4])

with col_info:
    st.markdown(f"### {jugador_a['nombre']}")
    st.write(f"**Posicion:** {jugador_a['posicion']}")
    st.write(f"**Club:** {jugador_a['club']}")
    st.write(f"**Liga/Pais:** {jugador_a['pais_liga']}")
    st.write(f"**Edad:** {jugador_a['edad']}")
    st.write(f"**Partidos jugados:** {jugador_a['partidos_jugados']}")
    if jugador_b is not None:
        st.markdown("---")
        st.markdown(f"### {jugador_b['nombre']}")
        st.write(f"**Posicion:** {jugador_b['posicion']}")
        st.write(f"**Club:** {jugador_b['club']}")
        st.write(f"**Liga/Pais:** {jugador_b['pais_liga']}")

with col_radar:
    st.markdown("**Radar de rendimiento**")
    fig_radar = dibujar_radar(jugador_a, jugador_b)
    st.pyplot(fig_radar, width="stretch")

with col_heat:
    st.markdown("**Mapa de calor acumulado** (ultimos 6 partidos, ataca hacia la derecha)")
    toques_a = toques_df[toques_df["jugador_id"] == jugador_a["id"]]
    fig_heat = dibujar_heatmap(toques_a)
    st.pyplot(fig_heat, width="stretch")

st.divider()
st.subheader(f"Ultimos 6 partidos - {jugador_a['nombre']}")

partidos_a = (
    partidos_df[partidos_df["jugador_id"] == jugador_a["id"]]
    .sort_values("fecha", ascending=False)
    .head(6)
)

victorias = int((partidos_a["resultado"] == "Victoria").sum())
empates = int((partidos_a["resultado"] == "Empate").sum())
derrotas = int((partidos_a["resultado"] == "Derrota").sum())

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Puntuacion media", f"{partidos_a['puntuacion'].mean():.1f}")
m2.metric("Minutos", int(partidos_a["minutos"].sum()))
m3.metric("Goles", int(partidos_a["goles_jugador"].sum()))
m4.metric("Asistencias", int(partidos_a["asistencias_jugador"].sum()))
m5.metric("Balance (V-E-D)", f"{victorias}-{empates}-{derrotas}")

tabla_partidos = pd.DataFrame({
    "Fecha": partidos_a["fecha"].dt.strftime("%d/%m/%Y"),
    "Rival": partidos_a["rival"],
    "Condicion": partidos_a["condicion"],
    "Marcador": partidos_a.apply(etiqueta_marcador, axis=1),
    "Resultado": partidos_a["resultado"].map(lambda r: f"{ICONO_RESULTADO[r]} {r}"),
    "Puntuacion": partidos_a["puntuacion"],
    "Min": partidos_a["minutos"],
    "Goles": partidos_a["goles_jugador"],
    "Asist": partidos_a["asistencias_jugador"],
})
st.dataframe(
    tabla_partidos,
    width="stretch",
    hide_index=True,
    column_config={
        "Puntuacion": st.column_config.NumberColumn("Puntuacion", format="%.1f"),
    },
)

st.markdown("**Mapa de calor por partido** (del mas reciente al mas antiguo)")

partidos_lista = list(partidos_a.itertuples(index=False))
for inicio in range(0, len(partidos_lista), 3):
    cols = st.columns(3)
    for col, partido in zip(cols, partidos_lista[inicio:inicio + 3]):
        with col:
            fecha_txt = partido.fecha.strftime("%d/%m")
            condicion_txt = "vs" if partido.condicion == "Local" else "@"
            st.markdown(
                f"{ICONO_RESULTADO[partido.resultado]} **{fecha_txt} · {condicion_txt} "
                f"{partido.rival}** · {partido.goles_favor}-{partido.goles_contra} "
                f"· nota {partido.puntuacion}"
            )
            toques_partido = toques_df[toques_df["partido_id"] == partido.partido_id]
            st.pyplot(dibujar_heatmap_partido(toques_partido), width="stretch")

plt.close("all")
