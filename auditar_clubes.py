"""
Revisa si algun legionario cambio de club.

    venv/bin/python utils/auditar_clubes.py

Conviene ejecutarlo ANTES de generar la copia de datos, sobre todo en mercado
de pases: si un jugador ficha por otro equipo y no se actualiza `database.py`,
la app sigue mostrando la liga y el calendario del club anterior sin dar ningun
error.

IMPORTANTE sobre el criterio: se avisa en cuanto la ficha de SofaScore
discrepa del club guardado, aunque sus ultimos partidos sigan siendo del club
viejo. Justo despues de un traspaso eso es lo normal —todavia no debuto— y una
version anterior de este script daba por bueno el club antiguo por ese motivo,
dejando pasar el fichaje de Diego Arroyo al Hapoel Petach Tikva.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi import requests as cr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from database import obtener_todos_los_jugadores  # noqa: E402

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.sofascore.com/",
}


def pedir(ruta):
    try:
        r = cr.get("https://api.sofascore.com/api/v1/" + ruta,
                   headers=HEADERS, impersonate="chrome", timeout=25)
        return r.json() if r.ok else None
    except Exception:
        return None


if __name__ == "__main__":
    print(f"Auditoria del {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC\n")
    sospechosos = []

    for jugador in obtener_todos_los_jugadores():
        ficha = (pedir(f"player/{jugador['sofascore_id']}") or {}).get("player") or {}
        club = ficha.get("team") or {}
        nombre_club = club.get("name") or "?"

        # "No team" es el marcador de SofaScore para un jugador sin equipo y no
        # significa que se haya ido: a varios internacionales les aparece asi.
        sin_dato = nombre_club.strip().lower() == "no team"
        coincide = sin_dato or club.get("id") == jugador.get("club_id")

        print(f"{'   ' if coincide else '>> '}{jugador['name'][:26]:<27}"
              f"base={jugador['current_club'][:22]:<24} ficha={nombre_club[:24]}")

        if not coincide:
            sospechosos.append((jugador, club))

    print()
    if not sospechosos:
        print("Ningun cambio de club detectado.")
    else:
        print(f"POSIBLES TRASPASOS ({len(sospechosos)}):\n")
        for jugador, club in sospechosos:
            equipo = (pedir(f"team/{club.get('id')}") or {}).get("team") or {}
            torneo = equipo.get("primaryUniqueTournament") or {}
            print(f"  {jugador['name']}")
            print(f"     guardado : {jugador['current_club']} (club_id {jugador.get('club_id')}, "
                  f"torneo {jugador.get('tournament_id')})")
            print(f"     SofaScore: {equipo.get('name')} · "
                  f"{(equipo.get('country') or {}).get('name')} "
                  f"(club_id {club.get('id')}, torneo {torneo.get('id')} - {torneo.get('name')})")
            print()
