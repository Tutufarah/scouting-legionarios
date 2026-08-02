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


def rutas_de(jugador):
    """Las rutas que la app pide para un jugador."""
    rutas = [f"player/{jugador['sofascore_id']}/events/last/0"]

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
    respuestas = {}
    fallos = []

    for numero, jugador in enumerate(jugadores, 1):
        print(f"[{numero:>2}/{len(jugadores)}] {jugador['name']}")
        for ruta in rutas_de(jugador):
            datos, error = _pedir_json(ruta)
            if error:
                fallos.append((ruta, error))
                continue
            respuestas[ruta] = datos

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
