"""
Guarda una copia de las respuestas de SofaScore para todos los legionarios.

Sirve de red de seguridad al publicar la app: SofaScore bloquea muchas IPs de
servidores en la nube, asi que si desde el servidor no se puede consultar la
API, la app tira de esta copia y el que la abra sigue viendo datos (los del dia
en que se genero, avisando de la fecha).

    venv/bin/python utils/generar_snapshot.py

Conviene volver a ejecutarlo y subir el archivo cada vez que se quieran
refrescar los datos publicados.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from database import obtener_todos_los_jugadores  # noqa: E402
from sofascore_api import _pedir_json, obtener_season_id  # noqa: E402

DESTINO = RAIZ / "data" / "snapshot_sofascore.json"


def rutas_de_partidos(player_id, limite=6):
    """Alineacion e incidencias de los ultimos partidos del jugador.

    Hacen falta para saber si fue titular, si entro desde el banquillo y en que
    minuto. El resumen de `events/last` no es fiable para eso.
    """
    datos, error = _pedir_json(f"player/{player_id}/events/last/0")
    if error or not datos:
        return []

    terminados = [e for e in (datos.get("events") or [])
                  if (e.get("status") or {}).get("type") == "finished"]
    terminados.sort(key=lambda e: e.get("startTimestamp") or 0, reverse=True)

    rutas = []
    for evento in terminados[:limite]:
        rutas.append(f"event/{evento['id']}/lineups")
        rutas.append(f"event/{evento['id']}/incidents")
    return rutas


def podar(ruta, datos, ids_legionarios):
    """Recorta la respuesta a lo que la app realmente lee.

    Una alineacion trae las fichas completas de los 40 jugadores del partido y
    la copia se iba a 12 MB. Guardando solo a los legionarios (y de las
    incidencias, solo los cambios) baja a una fraccion, sin perder nada de lo
    que se muestra.
    """
    if ruta.endswith("/lineups") and isinstance(datos, dict):
        podada = {}
        for lado in ("home", "away"):
            bloque = datos.get(lado) or {}
            jugadores = [
                j for j in (bloque.get("players") or [])
                if (j.get("player") or {}).get("id") in ids_legionarios
            ]
            podada[lado] = {"players": jugadores}
        return podada

    if ruta.endswith("/incidents") and isinstance(datos, dict):
        cambios = [
            i for i in (datos.get("incidents") or [])
            if i.get("incidentType") == "substitution"
        ]
        return {"incidents": cambios}

    return datos


def rutas_de(jugador):
    """Las rutas que la app pide para un jugador."""
    rutas = [f"player/{jugador['sofascore_id']}/events/last/0"]
    rutas.extend(rutas_de_partidos(jugador["sofascore_id"]))

    if jugador.get("club_id"):
        rutas.append(f"team/{jugador['club_id']}/events/next/0")

    rutas.append(f"player/{jugador['sofascore_id']}/statistics/seasons")

    season_id, _, error = obtener_season_id(
        jugador["sofascore_id"], jugador["tournament_id"]
    )
    if season_id and not error:
        base = (f"player/{jugador['sofascore_id']}"
                f"/unique-tournament/{jugador['tournament_id']}/season/{season_id}")
        rutas.append(f"{base}/statistics/overall")
        rutas.append(f"{base}/heatmap/overall")

    return rutas


if __name__ == "__main__":
    jugadores = obtener_todos_los_jugadores()
    ids_legionarios = {j["sofascore_id"] for j in jugadores}
    respuestas = {}
    fallos = []

    for numero, jugador in enumerate(jugadores, 1):
        print(f"[{numero:>2}/{len(jugadores)}] {jugador['name']}")
        for ruta in rutas_de(jugador):
            datos, error = _pedir_json(ruta)
            if error:
                fallos.append((ruta, error))
                # Un 404 es informacion util: significa que SofaScore no tiene
                # eso (por ejemplo, una liga sin calendario publicado). Se
                # guarda como tal para que la app lo diga con claridad en vez
                # de mostrar un error de red que confunde.
                if "404" in error:
                    respuestas[ruta] = {"__sin_datos__": True}
                continue
            respuestas[ruta] = podar(ruta, datos, ids_legionarios)

    contenido = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "jugadores": len(jugadores),
        "respuestas": respuestas,
    }
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")

    tamano = DESTINO.stat().st_size / 1024 / 1024
    print(f"\nGuardadas {len(respuestas)} respuestas en {DESTINO.name} ({tamano:.1f} MB)")
    if fallos:
        print(f"Fallaron {len(fallos)} rutas (normal si el jugador no tiene datos):")
        for ruta, error in fallos[:10]:
            print(f"  - {ruta}: {error}")
