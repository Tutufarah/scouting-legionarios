"""
Cliente para las estadisticas de SofaScore.

IMPORTANTE — sobre el transporte HTTP:
SofaScore bloquea a `requests` con un 403 en TODAS las peticiones, y no se
arregla poniendo un User-Agent de navegador: el filtro mira la huella TLS de la
conexion, no la cabecera. Se comprobo sin cabeceras, solo con User-Agent y con
el juego completo (UA + Accept + Referer + Origin): 403 en los tres casos.

Por eso el modulo usa `curl_cffi`, que imita la huella TLS de Chrome y si pasa
(devuelve 200 y los mismos datos que el navegador). Se mantiene `requests` como
alternativa por si en otra red o mas adelante deja de hacer falta.

    pip install curl_cffi requests

Las coordenadas del mapa de calor vienen en escala 0-100. La app dibuja con
mplsoccer en escala StatsBomb (120 x 80), asi que hay que convertirlas con
`convertir_a_statsbomb()` antes de pintarlas.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import requests

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_DISPONIBLE = True
except ImportError:  # el modulo sigue importable aunque falte la dependencia
    CURL_CFFI_DISPONIBLE = False

BASE_URL = "https://api.sofascore.com/api/v1"
TTL_UNA_SEMANA = 604800  # 7 dias
TIMEOUT = 20

_SNAPSHOT = None          # copia local en memoria
_SNAPSHOT_HUELLA = None   # estado del archivo con el que se cargo

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

# Valores por defecto cuando no hay datos o falla la peticion.
# Los contadores van a 0 y `rating` a None: un 0 de rating se leeria como
# "jugo horrible", que no es lo mismo que "no hay dato".
# `expected_goals` y `expected_assists` van a None y no a 0 porque hay ligas que
# simplemente no publican xG (por ejemplo la LigaPro de Ecuador). Un 0 diria
# "no genera ocasiones", cuando lo cierto es "esta liga no mide xG".
ESTADISTICAS_POR_DEFECTO = {
    "rating": None,
    "appearances": 0,
    "matches_started": 0,
    "minutes_played": 0,
    "goals": 0,
    "assists": 0,
    "expected_goals": None,
    "expected_assists": None,
    "key_passes": 0,
    "big_chances_created": 0,
    "total_shots": 0,
    "shots_on_target": 0,
    "shots_off_target": 0,
    "accurate_passes": 0,
    "total_passes": 0,
    "accurate_passes_pct": None,
    "accurate_final_third_passes": 0,
    "accurate_long_balls": 0,
    "accurate_crosses": 0,
    "successful_dribbles": 0,
    "successful_dribbles_pct": None,
    "tackles": 0,
    "tackles_won": 0,
    "interceptions": 0,
    "clearances": 0,
    "ball_recovery": 0,
    "blocks": 0,
    "possession_won_att_third": 0,
    "possession_lost": 0,
    "total_duels_won": 0,
    "duels_won_pct": None,
    "ground_duels_won_pct": None,
    "aerial_duels_won_pct": None,
    "touches": 0,
    "fouls": 0,
    "was_fouled": 0,
    "kilometers_covered": 0.0,
    "yellow_cards": 0,
    "red_cards": 0,
    # porteros
    "saves": 0,
    "saves_inside_box": 0,
    "goals_conceded": 0,
    "clean_sheets": 0,
    "high_claims": 0,
    "successful_runs_out": 0,
    "penalties_saved": 0,
}

# Traduccion de las claves de SofaScore a las nuestras.
MAPA_ESTADISTICAS = {
    "rating": "rating",
    "appearances": "appearances",
    "matchesStarted": "matches_started",
    "minutesPlayed": "minutes_played",
    "goals": "goals",
    "assists": "assists",
    "expectedGoals": "expected_goals",
    "expectedAssists": "expected_assists",
    "keyPasses": "key_passes",
    "bigChancesCreated": "big_chances_created",
    "totalShots": "total_shots",
    "shotsOnTarget": "shots_on_target",
    "shotsOffTarget": "shots_off_target",
    "accuratePasses": "accurate_passes",
    "totalPasses": "total_passes",
    "accuratePassesPercentage": "accurate_passes_pct",
    "accurateFinalThirdPasses": "accurate_final_third_passes",
    "accurateLongBalls": "accurate_long_balls",
    "accurateCrosses": "accurate_crosses",
    "successfulDribbles": "successful_dribbles",
    "successfulDribblesPercentage": "successful_dribbles_pct",
    "tackles": "tackles",
    "tacklesWon": "tackles_won",
    "interceptions": "interceptions",
    "clearances": "clearances",
    "ballRecovery": "ball_recovery",
    "outfielderBlocks": "blocks",
    "possessionWonAttThird": "possession_won_att_third",
    "possessionLost": "possession_lost",
    "totalDuelsWon": "total_duels_won",
    "totalDuelsWonPercentage": "duels_won_pct",
    "groundDuelsWonPercentage": "ground_duels_won_pct",
    "aerialDuelsWonPercentage": "aerial_duels_won_pct",
    "touches": "touches",
    "fouls": "fouls",
    "wasFouled": "was_fouled",
    "kilometersCovered": "kilometers_covered",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "saves": "saves",
    "savedShotsFromInsideTheBox": "saves_inside_box",
    "goalsConceded": "goals_conceded",
    "cleanSheet": "clean_sheets",
    "highClaims": "high_claims",
    "successfulRunsOut": "successful_runs_out",
    "penaltySave": "penalties_saved",
}


def _cargar_snapshot() -> dict:
    """Copia local de las respuestas, usada si la red falla.

    Busca el archivo en `data/` y tambien junto al codigo, y se queda con el
    MAS RECIENTE de los dos. El motivo es practico: al subir la copia por la
    web de GitHub arrastrando carpetas, los archivos de subcarpetas acaban a
    veces en la raiz del repositorio. Si solo se mirara en `data/`, la app
    seguiria sirviendo datos viejos sin dar ningun error, que es justo el fallo
    silencioso que hay que evitar.

    Se lee una sola vez y se guarda en memoria. Si no hay archivo, la app
    funciona igual: simplemente no hay respaldo.
    """
    global _SNAPSHOT, _SNAPSHOT_HUELLA

    base = Path(__file__).resolve().parent
    candidatos = [
        base / "data" / "snapshot_sofascore.json",
        base / "snapshot_sofascore.json",
    ]

    # Huella de los archivos en disco. Si cambia, se vuelve a leer: si no, un
    # proceso que siga vivo tras subir datos nuevos seguiria con los viejos.
    huella = tuple(
        (str(r), r.stat().st_mtime_ns, r.stat().st_size) if r.exists() else (str(r), 0, 0)
        for r in candidatos
    )
    if _SNAPSHOT is not None and huella == _SNAPSHOT_HUELLA:
        return _SNAPSHOT

    mejor = {"respuestas": {}, "generado": None}
    for ruta in candidatos:
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            continue
        # se compara la fecha de generacion como texto ISO, que ordena bien
        if (datos.get("generado") or "") > (mejor.get("generado") or ""):
            mejor = datos

    _SNAPSHOT = mejor
    _SNAPSHOT_HUELLA = huella
    return _SNAPSHOT


def fecha_snapshot() -> str | None:
    """Cuando se genero la copia local, para poder avisarlo en pantalla."""
    return _cargar_snapshot().get("generado")


def _version_datos() -> str:
    """Etiqueta de la version de los datos, usada como clave de cache.

    Todas las funciones cacheadas la reciben como primer argumento. Sin esto,
    la cache de 7 dias seguia devolviendo lo calculado con la copia anterior
    aunque se subiera una nueva: la app mostraba la fecha nueva en la barra
    lateral pero los numeros viejos en las tablas.
    """
    return fecha_snapshot() or "sin-copia"


@st.cache_data(ttl=3600, show_spinner=False)
def estado_conexion() -> dict:
    """Comprueba si desde aqui se puede consultar SofaScore en directo.

    Hace una peticion real y ligera SIN pasar por la copia, para poder decir en
    pantalla si lo que se ve son datos frescos o los guardados. Es la diferencia
    entre que la app se actualice sola o haya que subir datos nuevos a mano.

    Se recuerda una hora para no repetir la comprobacion en cada recarga.
    """
    url = f"{BASE_URL}/player/1159656"  # ficha ligera, siempre existe

    if CURL_CFFI_DISPONIBLE:
        try:
            r = curl_requests.get(url, headers=HEADERS, impersonate="chrome", timeout=10)
            if r.ok:
                return {"en_vivo": True, "detalle": "conexion directa con SofaScore"}
            motivo = f"SofaScore respondio HTTP {r.status_code}"
        except Exception as exc:
            motivo = f"{type(exc).__name__}"
    else:
        motivo = "curl_cffi no instalado"

    return {"en_vivo": False, "detalle": motivo}


def _pedir_json(ruta: str) -> tuple[dict | None, str | None]:
    """Hace GET y devuelve (datos, error). Nunca lanza excepcion.

    Intenta primero con curl_cffi porque es el unico que atraviesa el filtro
    anti-bot; si no esta instalado, cae a requests. Si la red falla del todo
    —lo habitual al publicar en un servidor, porque SofaScore bloquea muchas
    IPs de centros de datos— usa la copia de `data/snapshot_sofascore.json`.
    """
    url = f"{BASE_URL}/{ruta.lstrip('/')}"

    if CURL_CFFI_DISPONIBLE:
        try:
            respuesta = curl_requests.get(
                url, headers=HEADERS, impersonate="chrome", timeout=TIMEOUT
            )
            if respuesta.status_code == 404:
                return None, "sin datos en SofaScore (404)"
            if respuesta.ok:
                return respuesta.json(), None
            error_curl = f"HTTP {respuesta.status_code} via curl_cffi"
        except Exception as exc:
            error_curl = f"{type(exc).__name__}: {exc}"
    else:
        error_curl = "curl_cffi no instalado"

    # Alternativa con requests. Hoy SofaScore la rechaza con 403, pero se deja
    # por si el bloqueo cambia o se usa detras de un proxy que si pase.
    error_requests = None
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if respuesta.status_code == 404:
            return None, "sin datos en SofaScore (404)"
        if respuesta.ok:
            return respuesta.json(), None
        error_requests = f"HTTP {respuesta.status_code}"
    except Exception as exc:
        error_requests = f"{type(exc).__name__}: {exc}"

    # Ultimo recurso: la copia local.
    guardado = _cargar_snapshot().get("respuestas", {}).get(ruta)
    if isinstance(guardado, dict) and guardado.get("__sin_datos__"):
        return None, "sin datos en SofaScore (404)"
    if guardado is not None:
        return guardado, None

    return None, f"{error_curl}; requests: {error_requests}"


def obtener_season_id(player_id, tournament_id) -> tuple[int | None, str | None, str | None]:
    """Temporada mas reciente del jugador en ese torneo. Ver `_obtener_season_id`."""
    return _obtener_season_id(_version_datos(), player_id, tournament_id)


@st.cache_data(ttl=TTL_UNA_SEMANA, show_spinner=False)
def _obtener_season_id(version_datos, player_id, tournament_id) -> tuple[int | None, str | None, str | None]:
    """Resuelve la temporada mas reciente del jugador en ese torneo.

    Devuelve (season_id, etiqueta_del_anio, error).

    Se ordena por `id` de temporada y no por el anio porque el formato del anio
    cambia segun la liga: en Rusia o Bulgaria es "26/27" y en MLS o Ecuador
    "2026", asi que compararlos como texto da resultados incorrectos. El id, en
    cambio, siempre crece con el tiempo.
    """
    datos, error = _pedir_json(f"player/{player_id}/statistics/seasons")
    if error:
        return None, None, error
    if not datos:
        return None, None, "respuesta vacia"

    for bloque in datos.get("uniqueTournamentSeasons", []):
        if str(bloque.get("uniqueTournament", {}).get("id")) != str(tournament_id):
            continue
        temporadas = bloque.get("seasons") or []
        if not temporadas:
            return None, None, "el torneo no tiene temporadas"
        reciente = max(temporadas, key=lambda s: s.get("id", 0))
        return reciente.get("id"), reciente.get("year"), None

    return None, None, f"el jugador no registra datos en el torneo {tournament_id}"


def get_player_stats(player_id, tournament_id, season_id=None) -> dict:
    """Estadisticas de la temporada. Ver `_get_player_stats`."""
    return _get_player_stats(_version_datos(), player_id, tournament_id, season_id)


@st.cache_data(ttl=TTL_UNA_SEMANA, show_spinner=False)
def _get_player_stats(version_datos, player_id, tournament_id, season_id=None) -> dict:
    """Estadisticas del jugador en la temporada actual de ese torneo.

    Devuelve siempre un diccionario con la misma forma. Si algo falla, trae los
    valores por defecto con `ok=False` y el motivo en `error`.

    `ok` existe para poder distinguir "la API fallo" de "el jugador no ha
    jugado": ambos casos dan ceros, pero significan cosas muy distintas y en un
    informe de scouting confundirlos es grave.
    """
    resultado = {
        "ok": False,
        "error": None,
        "player_id": player_id,
        "tournament_id": tournament_id,
        "season_id": season_id,
        "season_year": None,
        **ESTADISTICAS_POR_DEFECTO,
    }

    if season_id is None:
        season_id, anio, error = obtener_season_id(player_id, tournament_id)
        resultado["season_id"] = season_id
        resultado["season_year"] = anio
        if error:
            resultado["error"] = error
            return resultado

    datos, error = _pedir_json(
        f"player/{player_id}/unique-tournament/{tournament_id}"
        f"/season/{season_id}/statistics/overall"
    )
    if error:
        resultado["error"] = error
        return resultado

    estadisticas = (datos or {}).get("statistics") or {}
    if not estadisticas:
        resultado["error"] = "la temporada no tiene estadisticas"
        return resultado

    for clave_sofascore, clave_nuestra in MAPA_ESTADISTICAS.items():
        if clave_sofascore in estadisticas:
            resultado[clave_nuestra] = estadisticas[clave_sofascore]

    if isinstance(resultado["rating"], (int, float)):
        resultado["rating"] = round(float(resultado["rating"]), 2)

    resultado["ok"] = True
    return resultado


def get_player_heatmap(player_id, tournament_id, season_id=None) -> dict:
    """Mapa de calor de la temporada. Ver `_get_player_heatmap`."""
    return _get_player_heatmap(_version_datos(), player_id, tournament_id, season_id)


@st.cache_data(ttl=TTL_UNA_SEMANA, show_spinner=False)
def _get_player_heatmap(version_datos, player_id, tournament_id, season_id=None) -> dict:
    """Coordenadas del mapa de calor de la temporada.

    Devuelve las listas `x`, `y` y `count` (peso de cada punto), en escala
    0-100. Ante cualquier fallo entrega listas vacias y `ok=False`.
    """
    resultado = {
        "ok": False,
        "error": None,
        "player_id": player_id,
        "tournament_id": tournament_id,
        "season_id": season_id,
        "season_year": None,
        "x": [],
        "y": [],
        "count": [],
        "total_puntos": 0,
    }

    if season_id is None:
        season_id, anio, error = obtener_season_id(player_id, tournament_id)
        resultado["season_id"] = season_id
        resultado["season_year"] = anio
        if error:
            resultado["error"] = error
            return resultado

    datos, error = _pedir_json(
        f"player/{player_id}/unique-tournament/{tournament_id}"
        f"/season/{season_id}/heatmap/overall"
    )
    if error:
        resultado["error"] = error
        return resultado

    puntos = (datos or {}).get("points") or []
    if not puntos:
        resultado["error"] = "la temporada no tiene mapa de calor"
        return resultado

    for punto in puntos:
        if punto.get("x") is None or punto.get("y") is None:
            continue
        resultado["x"].append(punto["x"])
        resultado["y"].append(punto["y"])
        resultado["count"].append(punto.get("count", 1))

    resultado["total_puntos"] = len(resultado["x"])
    resultado["ok"] = resultado["total_puntos"] > 0
    if not resultado["ok"]:
        resultado["error"] = "no se pudo leer ninguna coordenada"
    return resultado


def get_player_last_matches(player_id, limite: int = 6) -> dict:
    """Ultimos partidos del jugador. Ver `_get_player_last_matches`."""
    return _get_player_last_matches(_version_datos(), player_id, limite)


def participacion_en_partido(event_id, player_id) -> dict:
    """Como participo el jugador en ese partido, segun la ALINEACION.

    No se usa el resumen de `events/last` para esto porque miente. Casos reales
    comprobados con Oscar Lopez:

      - Getafe-Monaco (06/08/2026): fue TITULAR y salio al minuto 63, pero el
        resumen venia vacio y se clasificaba como "No convocado".
      - Getafe-Tottenham (08/08/2026): entro al 81 y el resumen decia
        1 minuto jugado.

    Por eso los minutos se calculan a partir de los cambios (`incidents`), que
    es el dato duro: quien entro, quien salio y en que minuto.

    Devuelve estado, minutos, y los minutos de entrada/salida cuando los hay.
    """
    vacio = {"estado": None, "minutos": 0, "titular": False,
             "entro_min": None, "salio_min": None, "rating": None}

    alineaciones, error = _pedir_json(f"event/{event_id}/lineups")
    if error or not alineaciones:
        return vacio

    ficha = None
    for lado in ("home", "away"):
        for jugador in (alineaciones.get(lado) or {}).get("players") or []:
            if (jugador.get("player") or {}).get("id") == player_id:
                ficha = jugador
                break
        if ficha:
            break

    if ficha is None:
        # no aparece en la lista de convocados
        return {**vacio, "estado": "No convocado"}

    estadisticas = ficha.get("statistics") or {}
    es_suplente = bool(ficha.get("substitute"))
    resultado = {
        "estado": None,
        "minutos": 0,
        "titular": not es_suplente,
        "entro_min": None,
        "salio_min": None,
        "rating": estadisticas.get("rating"),
    }

    incidencias, _ = _pedir_json(f"event/{event_id}/incidents")
    minutos_incidencias = []
    for inc in (incidencias or {}).get("incidents", []):
        if inc.get("time") is not None:
            minutos_incidencias.append(inc["time"])
        if inc.get("incidentType") != "substitution":
            continue
        minuto = inc.get("time")
        if (inc.get("playerIn") or {}).get("id") == player_id:
            resultado["entro_min"] = minuto
        elif (inc.get("playerOut") or {}).get("id") == player_id:
            resultado["salio_min"] = minuto

    # Minuto en que acaba el partido: 90 salvo que haya prorroga, cosa que se
    # detecta porque hay cambios mas alla del 90 (eliminatorias europeas, copas).
    fin = max([90] + minutos_incidencias) if minutos_incidencias else 90

    if es_suplente:
        if resultado["entro_min"] is None:
            resultado["estado"] = "Banquillo"
            resultado["minutos"] = 0
        else:
            resultado["estado"] = "Jugo"
            resultado["minutos"] = max(0, fin - resultado["entro_min"])
    else:
        resultado["estado"] = "Jugo"
        resultado["minutos"] = (
            resultado["salio_min"] if resultado["salio_min"] is not None else fin
        )

    # Solo si no hubo cambios se acepta el minutaje que reporta SofaScore.
    if resultado["entro_min"] is None and resultado["salio_min"] is None:
        informados = estadisticas.get("minutesPlayed")
        if informados:
            resultado["minutos"] = informados

    return resultado


@st.cache_data(ttl=TTL_UNA_SEMANA, show_spinner=False)
def _get_player_last_matches(version_datos, player_id, limite: int = 6) -> dict:
    """Ultimos partidos del jugador, jugara o no, con fecha y nota.

    Incluye todas las competiciones (liga, copas y seleccion), no solo el
    torneo del filtro: para valorar el momento de forma importa todo lo que
    disputo el equipo. Cada partido trae de que competicion es.

    Cada partido se clasifica en tres estados, tomados de la alineacion real
    del encuentro (ver `participacion_en_partido`):

      - "Jugo"          : fue titular o entro desde el banquillo.
      - "Banquillo"     : estuvo convocado y no entro.
      - "No convocado"  : el equipo jugo y el no figuro en la citacion.

    Devuelve ademas `media_rating`, el promedio de las notas de los partidos
    que si jugo dentro de esos ultimos partidos.
    """
    resultado = {"ok": False, "error": None, "partidos": [],
                 "media_rating": None, "jugados": 0, "banquillo": 0, "no_convocado": 0}

    datos, error = _pedir_json(f"player/{player_id}/events/last/0")
    if error:
        resultado["error"] = error
        return resultado

    eventos = (datos or {}).get("events") or []
    estadisticas = (datos or {}).get("statisticsMap") or {}
    equipo_por_evento = (datos or {}).get("playedForTeamMap") or {}
    en_banquillo = (datos or {}).get("onBenchMap") or {}

    # Se ordenan primero y se recortan a los que se van a mostrar: consultar la
    # alineacion cuesta dos peticiones por partido y no tiene sentido hacerlo
    # con toda la temporada.
    terminados = [e for e in eventos
                  if (e.get("status") or {}).get("type") == "finished"]
    terminados.sort(key=lambda e: e.get("startTimestamp") or 0, reverse=True)
    terminados = terminados[:limite]

    partidos = []
    for evento in terminados:
        id_evento = str(evento.get("id"))
        stats_partido = estadisticas.get(id_evento) or {}

        # La alineacion manda; el resumen solo se usa si aquella no esta.
        detalle = participacion_en_partido(evento.get("id"), player_id)
        if detalle["estado"]:
            estado = detalle["estado"]
            minutos = detalle["minutos"]
            nota = detalle["rating"] if detalle["rating"] is not None else stats_partido.get("rating")
            entro_min = detalle["entro_min"]
            salio_min = detalle["salio_min"]
            titular = detalle["titular"]
        else:
            minutos = stats_partido.get("minutesPlayed") or 0
            if minutos:
                estado = "Jugo"
            elif en_banquillo.get(id_evento):
                estado = "Banquillo"
            else:
                estado = "No convocado"
            nota = stats_partido.get("rating")
            entro_min = salio_min = None
            titular = bool(minutos)

        local = (evento.get("homeTeam") or {}).get("name") or "?"
        visitante = (evento.get("awayTeam") or {}).get("name") or "?"
        goles_local = (evento.get("homeScore") or {}).get("current")
        goles_visitante = (evento.get("awayScore") or {}).get("current")

        # Con el equipo en el que jugo se sabe si fue local o visitante y, por
        # tanto, si el marcador fue victoria o derrota PARA EL.
        id_equipo = equipo_por_evento.get(id_evento)
        es_local = id_equipo == (evento.get("homeTeam") or {}).get("id")

        if goles_local is None or goles_visitante is None:
            resultado_txt, gf, gc = "—", None, None
        else:
            gf = goles_local if es_local else goles_visitante
            gc = goles_visitante if es_local else goles_local
            resultado_txt = "Victoria" if gf > gc else ("Derrota" if gf < gc else "Empate")

        partidos.append({
            "event_id": evento.get("id"),
            "timestamp": evento.get("startTimestamp"),
            "competicion": (evento.get("tournament") or {}).get("name") or "—",
            "local": local,
            "visitante": visitante,
            "goles_local": goles_local,
            "goles_visitante": goles_visitante,
            "es_local": es_local,
            "goles_favor": gf,
            "goles_contra": gc,
            "resultado": resultado_txt,
            "estado": estado,
            "rating": nota,
            "minutos": minutos,
            "titular": titular,
            "entro_min": entro_min,
            "salio_min": salio_min,
        })

    partidos.sort(key=lambda p: p["timestamp"] or 0, reverse=True)
    ultimos = partidos
    resultado["partidos"] = ultimos

    notas = [p["rating"] for p in ultimos if p["estado"] == "Jugo" and p["rating"] is not None]
    resultado["media_rating"] = round(sum(notas) / len(notas), 2) if notas else None
    resultado["jugados"] = sum(1 for p in ultimos if p["estado"] == "Jugo")
    resultado["banquillo"] = sum(1 for p in ultimos if p["estado"] == "Banquillo")
    resultado["no_convocado"] = sum(1 for p in ultimos if p["estado"] == "No convocado")
    resultado["minutos_totales"] = sum(p["minutos"] for p in ultimos)

    resultado["ok"] = bool(ultimos)
    if not resultado["ok"]:
        resultado["error"] = "no hay partidos recientes"
    return resultado


def get_next_matches(club_id, limite: int = 4) -> dict:
    """Proximos partidos del club. Ver `_get_next_matches`."""
    return _get_next_matches(_version_datos(), club_id, limite)


@st.cache_data(ttl=TTL_UNA_SEMANA, show_spinner=False)
def _get_next_matches(version_datos, club_id, limite: int = 4) -> dict:
    """Proximos partidos del club, con fecha y condicion de local o visitante.

    Se pide por CLUB y no por jugador: SofaScore no expone un calendario futuro
    a nivel de jugador (`player/{id}/events/next` devuelve 404), y ademas quien
    tiene calendario es el equipo. Por eso `database.py` guarda `club_id`.

    Un jugador sin equipo (`club_id` a None) no tiene proximos partidos, y eso
    se informa como tal en vez de como un error.
    """
    resultado = {"ok": False, "error": None, "partidos": []}

    if not club_id:
        resultado["error"] = "el jugador no tiene club actual"
        return resultado

    datos, error = _pedir_json(f"team/{club_id}/events/next/0")
    if error:
        resultado["error"] = error
        return resultado

    eventos = (datos or {}).get("events") or []
    partidos = []
    for evento in eventos:
        local = evento.get("homeTeam") or {}
        visitante = evento.get("awayTeam") or {}
        es_local = local.get("id") == club_id
        rival = visitante if es_local else local

        partidos.append({
            "event_id": evento.get("id"),
            "timestamp": evento.get("startTimestamp"),
            "competicion": (evento.get("tournament") or {}).get("name") or "—",
            "rival": rival.get("name") or "?",
            "local": local.get("name") or "?",
            "visitante": visitante.get("name") or "?",
            "es_local": es_local,
            "condicion": "Local" if es_local else "Visitante",
        })

    partidos.sort(key=lambda p: p["timestamp"] or 0)
    resultado["partidos"] = partidos[:limite]
    resultado["ok"] = bool(resultado["partidos"])
    if not resultado["ok"]:
        resultado["error"] = "sin partidos programados"
    return resultado


def convertir_a_statsbomb(xs, ys) -> tuple[list, list]:
    """Pasa coordenadas de SofaScore (0-100) a StatsBomb (120 x 80).

    El eje Y SE INVIERTE. Los dos sistemas numeran las bandas al reves:

      - SofaScore: la banda izquierda del equipo que ataca son valores de `y`
        ALTOS. Se comprobo con casos de control: Roberto Carlos Fernandez
        (lateral/interior izquierdo) da y≈68, mientras que Yomar Rocha y Diego
        Medina, ambos laterales DERECHOS, dan y≈23 y y≈15.
      - StatsBomb/mplsoccer: `y=0` se dibuja ARRIBA (el eje del grafico va de 84
        a -4), y atacando hacia la derecha la banda izquierda es justamente la
        parte de arriba, o sea `y` BAJO.

    Sin invertir, a un zurdo por izquierda el mapa lo pintaba por la derecha.
    """
    return [x * 1.2 for x in xs], [(100 - y) * 0.8 for y in ys]


if __name__ == "__main__":
    from database import obtener_todos_los_jugadores

    print(f"curl_cffi disponible: {CURL_CFFI_DISPONIBLE}\n")

    for jugador in obtener_todos_los_jugadores():
        stats = get_player_stats(jugador["sofascore_id"], jugador["tournament_id"])
        mapa = get_player_heatmap(jugador["sofascore_id"], jugador["tournament_id"])

        estado = "OK " if stats["ok"] else "-- "
        rating = stats["rating"] if stats["rating"] is not None else "s/d"
        print(
            f"{estado}{jugador['name']:<26} {str(stats['season_year'] or '?'):<7} "
            f"rating={str(rating):<5} PJ={stats['appearances']:<3} "
            f"min={stats['minutes_played']:<5} G={stats['goals']} A={stats['assists']}  "
            f"heatmap={mapa['total_puntos']} pts"
        )
        if stats["error"]:
            print(f"     stats: {stats['error']}")
        if mapa["error"]:
            print(f"     heatmap: {mapa['error']}")
