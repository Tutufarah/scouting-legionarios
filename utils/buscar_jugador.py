"""
Resuelve los IDs de SofaScore de un jugador para poder anadirlo a database.py.

Con el nombre (y opcionalmente el club) busca en SofaScore, filtra por
nacionalidad boliviana e imprime la entrada lista para pegar en LEGIONARIOS.

    # por nombre
    venv/bin/python utils/buscar_jugador.py "Boris Cespedes"

    # si el nombre no aparece, se busca por plantilla del club:
    # SofaScore a veces usa el apodo (Miguel Terceros figura como "Miguelito")
    venv/bin/python utils/buscar_jugador.py --club "Servette"

Verifica siempre el club que imprime antes de dar el id por bueno: hay muchos
homonimos y un id equivocado trae las estadisticas de otra persona sin avisar.
"""
import sys
import unicodedata

from curl_cffi import requests as cr

BASE = "https://api.sofascore.com/api/v1"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.sofascore.com/",
}

# Traduccion de la posicion detallada de SofaScore a las cuatro categorias
# que usa database.py.
MAPA_POSICION = {
    "GK": "POR", "DC": "DF", "DL": "DF", "DR": "DF", "DM": "MC",
    "MC": "MC", "ML": "ED", "MR": "ED", "AM": "MC",
    "LW": "ED", "RW": "ED", "ST": "DEL",
}


def pedir(ruta):
    respuesta = cr.get(f"{BASE}/{ruta}", headers=HEADERS, impersonate="chrome", timeout=25)
    if not respuesta.ok:
        return None
    return respuesta.json()


def sin_tildes(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    ).lower()


def datos_torneo(team_id):
    equipo = pedir(f"team/{team_id}") or {}
    torneo = (equipo.get("team") or {}).get("primaryUniqueTournament") or {}
    return torneo.get("id"), torneo.get("name")


def posicion_detallada(player_id):
    car = pedir(f"player/{player_id}/characteristics") or {}
    posiciones = car.get("positions") or []
    return posiciones


def describir(jugador):
    pid = jugador["id"]
    equipo = jugador.get("team") or {}
    tid, liga = datos_torneo(equipo.get("id")) if equipo.get("id") else (None, None)
    posiciones = posicion_detallada(pid)
    principal = MAPA_POSICION.get(posiciones[0], "MC") if posiciones else "MC"
    pais = (jugador.get("country") or {}).get("name")

    print(f"\n  {jugador.get('name')}  ({pais})")
    print(f"    club     : {equipo.get('name')}")
    print(f"    liga     : {liga}  (tournament_id={tid})")
    print(f"    posicion : {'/'.join(posiciones) or '?'}  ->  {principal}")
    print("    entrada para database.py:")
    print(f"""    {{
        "id": "{sin_tildes(jugador.get('name','')).replace(' ', '-')}",
        "name": "{jugador.get('name')}",
        "current_club": "{equipo.get('name')}",
        "league_name": "{liga}",
        "main_position": "{principal}",
        "sofascore_id": {pid},
        "tournament_id": {tid},
    }},""")


def buscar_por_nombre(nombre):
    datos = pedir(f"search/all?q={nombre}")
    if not datos:
        print("La busqueda fallo.")
        return

    jugadores = [
        r["entity"] for r in datos.get("results", [])
        if r.get("type") == "player"
        and ((r["entity"].get("team") or {}).get("sport") or {}).get("slug") == "football"
    ]
    bolivianos = [j for j in jugadores if (j.get("country") or {}).get("alpha2") == "BO"]

    if bolivianos:
        print(f"Bolivianos encontrados para '{nombre}':")
        for j in bolivianos:
            describir(j)
    elif jugadores:
        print(f"NINGUN boliviano para '{nombre}'. Otros resultados (revisar a mano):")
        for j in jugadores[:5]:
            pais = (j.get("country") or {}).get("name")
            print(f"  - {j.get('name')} ({pais}) · {(j.get('team') or {}).get('name')}")
        print("\nSi el jugador existe pero no sale, prueba con --club \"<su club>\":")
        print("SofaScore a veces lo registra con apodo.")
    else:
        print(f"Sin resultados para '{nombre}'.")


def buscar_por_club(club):
    datos = pedir(f"search/all?q={club}")
    if not datos:
        print("La busqueda fallo.")
        return

    equipos = [
        r["entity"] for r in datos.get("results", [])
        if r.get("type") == "team" and (r["entity"].get("sport") or {}).get("slug") == "football"
    ]
    if not equipos:
        print(f"No se encontro el club '{club}'.")
        return

    for equipo in equipos[:3]:
        plantilla = pedir(f"team/{equipo['id']}/players") or {}
        bolivianos = [
            p["player"] for p in plantilla.get("players", [])
            if ((p.get("player") or {}).get("country") or {}).get("alpha2") == "BO"
        ]
        pais = (equipo.get("country") or {}).get("name")
        print(f"\n=== {equipo.get('name')} ({pais}) — {len(bolivianos)} boliviano(s) ===")
        for jugador in bolivianos:
            jugador["team"] = {"id": equipo["id"], "name": equipo.get("name")}
            describir(jugador)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    if sys.argv[1] == "--club":
        if len(sys.argv) < 3:
            print("Falta el nombre del club.")
            raise SystemExit(1)
        buscar_por_club(" ".join(sys.argv[2:]))
    else:
        buscar_por_nombre(" ".join(sys.argv[1:]))
