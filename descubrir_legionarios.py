"""
Descubre futbolistas bolivianos que juegan FUERA de Bolivia.

Recorre las convocatorias de las selecciones bolivianas en SofaScore (absoluta,
Sub-23, Sub-20 y Sub-17), mira en que club juega cada uno y se queda con los que
militan en un club de otro pais.

    venv/bin/python utils/descubrir_legionarios.py

Escribe `data/legionarios_detectados.json` y muestra un resumen por pantalla.
El resultado es un PUNTO DE PARTIDA, no una lista cerrada: solo encuentra a
quienes han sido convocados alguna vez por una seleccion boliviana. Un jugador
boliviano en el exterior que nunca fue convocado no aparecera aqui, y hay que
anadirlo a mano con `utils/buscar_jugador.py`.
"""
import json
import time
import unicodedata
from pathlib import Path

from curl_cffi import requests as cr

BASE = "https://api.sofascore.com/api/v1"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.sofascore.com/",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SELECCIONES = {
    4746: "Absoluta",
    328245: "Sub-23",
    33756: "Sub-20",
    48991: "Sub-20",
    48828: "Sub-17",
    215437: "Sub-17",
}

MAPA_POSICION = {
    "GK": "POR", "DC": "DF", "DL": "DF", "DR": "DF", "DM": "MC",
    "MC": "MC", "ML": "ED", "MR": "ED", "AM": "MC",
    "LW": "ED", "RW": "ED", "ST": "DEL",
}


def pedir(ruta, reintentos=2):
    for intento in range(reintentos + 1):
        try:
            r = cr.get(f"{BASE}/{ruta}", headers=HEADERS, impersonate="chrome", timeout=25)
            if r.status_code == 404:
                return None
            if r.ok:
                return r.json()
        except Exception:
            pass
        if intento < reintentos:
            time.sleep(1.2)
    return None


def sin_tildes(texto):
    base = "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    )
    return base.lower().replace(" ", "-").replace(".", "").replace("'", "")


def recoger_convocados():
    """Une los jugadores de todas las selecciones, sin repetir."""
    encontrados = {}
    for team_id, categoria in SELECCIONES.items():
        datos = pedir(f"team/{team_id}/players")
        if not datos:
            print(f"  · seleccion {team_id}: sin respuesta")
            continue
        jugadores = datos.get("players") or []
        print(f"  · {categoria} (id {team_id}): {len(jugadores)} convocados")
        for entrada in jugadores:
            jugador = entrada.get("player") or {}
            pid = jugador.get("id")
            if not pid:
                continue
            if pid not in encontrados:
                encontrados[pid] = {"id": pid, "categorias": set()}
            encontrados[pid]["categorias"].add(categoria)
    return encontrados


def pais_del_club(club_id, club_desde_jugador):
    """Pais del club, resolviendolo desde su ficha.

    En los filiales y juveniles ("Club Bolivar U20", "Santos U20") el objeto que
    viene dentro del jugador suele traer el pais vacio, y si se da por bueno un
    None se cuela un club boliviano como si fuera del exterior. Por eso se
    consulta la ficha del equipo, que si lo trae.
    """
    pais = (club_desde_jugador.get("country") or {}).get("name")
    if pais:
        return pais
    equipo = pedir(f"team/{club_id}") or {}
    return ((equipo.get("team") or {}).get("country") or {}).get("name")


def analizar(pid):
    """Ficha del jugador con su club actual y el pais de ese club."""
    datos = pedir(f"player/{pid}")
    if not datos:
        return None
    jugador = datos.get("player") or {}
    club = jugador.get("team") or {}

    # Si su equipo es una seleccion, no dice nada de donde juega.
    if club.get("national"):
        return None

    club_id = club.get("id")
    nombre_club = club.get("name")
    # "No team" es el marcador de SofaScore para un jugador sin equipo actual.
    if not club_id or not nombre_club or nombre_club.strip().lower() == "no team":
        return None

    return {
        "sofascore_id": pid,
        "name": jugador.get("name"),
        "nacionalidad": (jugador.get("country") or {}).get("alpha2"),
        "current_club": nombre_club,
        "club_id": club_id,
        "pais_club": pais_del_club(club_id, club),
        "posicion_basica": jugador.get("position"),
    }


def completar(ficha):
    """Anade torneo, liga y posicion detallada."""
    equipo = pedir(f"team/{ficha['club_id']}") or {}
    torneo = (equipo.get("team") or {}).get("primaryUniqueTournament") or {}
    ficha["tournament_id"] = torneo.get("id")
    ficha["league_name"] = torneo.get("name")

    caracteristicas = pedir(f"player/{ficha['sofascore_id']}/characteristics") or {}
    posiciones = caracteristicas.get("positions") or []
    ficha["posiciones_sofascore"] = posiciones
    ficha["main_position"] = MAPA_POSICION.get(posiciones[0], "MC") if posiciones else "MC"
    ficha["id"] = sin_tildes(ficha["name"])
    return ficha


if __name__ == "__main__":
    print("Recogiendo convocatorias de las selecciones bolivianas...")
    convocados = recoger_convocados()
    print(f"\n{len(convocados)} jugadores distintos. Revisando en que club juega cada uno...\n")

    legionarios, locales, sin_club, dudosos = [], [], [], []

    for numero, (pid, meta) in enumerate(convocados.items(), 1):
        ficha = analizar(pid)
        if not ficha:
            sin_club.append(pid)
            continue

        # solo bolivianos con club fuera de Bolivia
        if ficha["nacionalidad"] != "BO":
            continue

        if ficha["pais_club"] == "Bolivia":
            locales.append(ficha)
            continue

        if not ficha["pais_club"]:
            # Sin pais no se puede afirmar que juegue fuera; se reporta aparte
            # en vez de colarlo en la lista buena.
            dudosos.append(ficha)
            continue

        ficha["categorias"] = sorted(meta["categorias"])
        legionarios.append(completar(ficha))
        print(f"  [{numero:>3}/{len(convocados)}] {ficha['name']:<28} "
              f"{ficha['current_club']:<26} {ficha['pais_club']}")

    legionarios.sort(key=lambda f: (f.get("pais_club") or "", f.get("name") or ""))

    DATA_DIR.mkdir(exist_ok=True)
    destino = DATA_DIR / "legionarios_detectados.json"
    destino.write_text(json.dumps(legionarios, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"LEGIONARIOS DETECTADOS: {len(legionarios)}")
    print(f"Juegan en Bolivia: {len(locales)} · sin club actual en SofaScore: {len(sin_club)}")

    if dudosos:
        print(f"\nPARA REVISAR A MANO ({len(dudosos)}): su club no declara pais.")
        for f in dudosos:
            print(f"  - {f['name']} · {f['current_club']} (id {f['sofascore_id']})")

    print(f"\nGuardado en: {destino}")
