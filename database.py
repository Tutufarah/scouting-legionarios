"""
Base de datos de legionarios: futbolistas bolivianos que juegan en el exterior.

A diferencia de los CSV de `data/`, que son datos de PRUEBA generados al azar,
este archivo contiene datos REALES verificados uno por uno contra la API publica
de SofaScore (nombre, club, nacionalidad boliviana, posicion y torneo).

`sofascore_id` y `tournament_id` son los identificadores que usa SofaScore y son
la clave para consultar estadisticas mas adelante. Si alguno estuviera mal, la
app traeria datos de otro jugador sin dar ningun error, asi que conviene
revalidarlos con `verificar_ids()` cuando haya traspasos.
"""
from typing import Optional

# Posiciones admitidas en `main_position`.
#   POR = portero            DF  = defensa
#   MC  = mediocampista      ED  = extremo
#   DEL = delantero
POSICIONES_VALIDAS = ("POR", "DF", "MC", "ED", "DEL")

# Cada jugador incluye, en comentario, la posicion detallada que reporta
# SofaScore, que es mas fina que las categorias de `main_position`.
#
# `puesto` es la posicion concreta dentro del once (LI, DFC, MCD, ED...),
# mas fina que `main_position`, y es la que coloca a cada jugador en su
# sitio del campo en la vista de cancha.
#
# `club_id` es el equipo en SofaScore y se guarda aparte porque hace falta
# para pedir el calendario de proximos partidos. No se deduce de la ficha del
# jugador porque a veces esta desactualizada (a Viscarra y a Cuellar SofaScore
# les asigna todavia su club anterior).
LEGIONARIOS: list[dict] = [
    {
        "id": "daniel-lino",
        "name": "Daniel Lino",
        "current_club": "Comerciantes Unidos",
        "club_id": 213609,
        "league_name": "Liga 1",
        "main_position": "DF",
        "puesto": "LI",  # SofaScore: DL
        "sofascore_id": 1184194,
        "tournament_id": 406,
    },
    {
        "id": "daniel-ribera",
        "name": "Daniel Ribera",
        "current_club": "Talleres de Córdoba Reserve",
        "club_id": 251006,
        "league_name": "Campeonato de Reserva de Primera División",
        "main_position": "DEL",
        "puesto": "DC",  # SofaScore: ?
        "sofascore_id": 1464251,
        "tournament_id": 18817,
        # OJO: posicion fijada por el cuerpo tecnico (SofaScore no la reporta)
    },
    {
        "id": "diego-arroyo",
        "name": "Diego Arroyo",
        "current_club": "Shakhtar Donetsk",
        "club_id": 3313,
        "league_name": "Ukrainian Premier League",
        "main_position": "DF",
        "puesto": "DFC",  # SofaScore: DC
        "sofascore_id": 1510240,
        "tournament_id": 218,
    },
    {
        "id": "diego-medina",
        "name": "Diego Medina",
        "current_club": "FC CSKA 1948 Sofia",
        "club_id": 252080,
        "league_name": "Parva Liga",
        "main_position": "DF",
        "puesto": "LD",  # SofaScore: DR
        "sofascore_id": 1114079,
        "tournament_id": 247,
    },
    {
        "id": "efrain-morales",
        "name": "Efraín Morales",
        "current_club": "CF Montréal",
        "club_id": 22006,
        "league_name": "MLS",
        "main_position": "DF",
        "puesto": "DFC",  # SofaScore: DC
        "sofascore_id": 1035650,
        "tournament_id": 242,
    },
    {
        "id": "enzo-monteiro",
        "name": "Enzo Monteiro",
        "current_club": "Cheongju FC",
        "club_id": 314293,
        "league_name": "K League 2",
        "main_position": "DEL",
        "puesto": "DC",  # SofaScore: ST
        "sofascore_id": 1525129,
        "tournament_id": 777,
    },
    {
        "id": "gabriel-villamil",
        "name": "Gabriel Villamil",
        "current_club": "LDU Quito",
        "club_id": 5257,
        "league_name": "LigaPro Serie A",
        "main_position": "MC",
        "puesto": "MCO",  # SofaScore: MC/AM
        "sofascore_id": 964296,
        "tournament_id": 240,
    },
    {
        "id": "geronimo-govea",
        "name": "Gerónimo Govea",
        "current_club": "Montevideo Wanderers",
        "club_id": 3240,
        "league_name": "Liga AUF Uruguaya",
        "main_position": "POR",
        "puesto": "POR",  # SofaScore: GK
        "sofascore_id": 2057454,
        "tournament_id": 278,
    },
    {
        "id": "guillermo-viscarra",
        "name": "Guillermo Viscarra",
        "current_club": "Alianza Lima",
        "club_id": 2311,
        "league_name": "Liga 1",
        "main_position": "POR",
        "puesto": "POR",  # SofaScore: GK
        "sofascore_id": 331437,
        "tournament_id": 406,
        # OJO: SofaScore no lo lista en la plantilla de Alianza, pero si tiene estadisticas en Liga 1 2026
    },
    {
        "id": "hector-cuellar",
        "name": "Héctor Cuéllar",
        "current_club": "FC CSKA 1948 Sofia",
        "club_id": 252080,
        "league_name": "Parva Liga",
        "main_position": "MC",
        "puesto": "MCD",  # SofaScore: MC/DM
        "sofascore_id": 1495631,
        "tournament_id": 247,
        # OJO: la ficha de SofaScore aun dice Always Ready, pero figura en la plantilla del CSKA y ya tiene partidos en Parva Liga 26/27
    },
    {
        "id": "jose-martinez",
        "name": "José Martínez",
        "current_club": "FC CSKA 1948 Sofia",
        "club_id": 252080,
        "league_name": "Parva Liga",
        "main_position": "ED",
        "puesto": "ED",  # SofaScore: RW
        "sofascore_id": 1017482,
        "tournament_id": 247,
    },
    {
        "id": "leonardo-justiniano",
        "name": "Leonardo Justiniano",
        "current_club": "Rayong FC",
        "club_id": 254730,
        "league_name": "Thai League 1",
        "main_position": "DF",
        "puesto": "DFC",  # SofaScore: DC
        "sofascore_id": 1017466,
        "tournament_id": 1032,
    },
    {
        "id": "lucas-macazaga",
        "name": "Lucas Macazaga",
        "current_club": "SD Ponferradina",
        "club_id": 6195,
        "league_name": "Primera Federación",
        "main_position": "DF",
        "puesto": "LD",  # SofaScore: DR
        "sofascore_id": 1994814,
        "tournament_id": 17073,
    },
    {
        "id": "luis-haquin",
        "name": "Luis Haquín",
        "current_club": "Sin club actual",
        "club_id": None,
        "league_name": "Saudi 1st Division (ultima registrada)",
        "main_position": "DF",
        "puesto": "DFC",  # SofaScore: DC
        "sofascore_id": 876304,
        "tournament_id": 2120,
        # OJO: sin equipo: no hay proximos partidos y las cifras son de su ultima temporada registrada
    },
    {
        "id": "lysander-lucas-urena",
        "name": "Lysander Ariel Lucas Ureña",
        "current_club": "São Paulo U17",
        "club_id": 342890,
        "league_name": "U17 Campeonato Brasileiro",
        "main_position": "DF",
        "puesto": "DFC",  # SofaScore: DC
        "sofascore_id": 2365146,
        "tournament_id": 22794,
    },
    {
        "id": "marcelo-torrez",
        "name": "Marcelo Torrez",
        "current_club": "Santos U20",
        "club_id": 199299,
        "league_name": "U20 Campeonato Brasileiro",
        "main_position": "DF",
        "puesto": "DFC",  # SofaScore: DC
        "sofascore_id": 1484122,
        "tournament_id": 9233,
    },
    {
        "id": "miguel-terceros",
        "name": "Miguel Terceros",
        "current_club": "Santos",
        "club_id": 1968,
        "league_name": "Brasileirão Betano",
        "main_position": "ED",
        "puesto": "ED",  # SofaScore: RW
        "sofascore_id": 1159656,
        "tournament_id": 325,
    },
    {
        "id": "moises-paniagua",
        "name": "Moisés Paniagua",
        "current_club": "Wydad Casablanca",
        "club_id": 36268,
        "league_name": "Botola Pro",
        "main_position": "ED",
        "puesto": "EI",  # SofaScore: LW
        "sofascore_id": 1424737,
        "tournament_id": 937,
    },
    {
        "id": "oscar-lopez",
        "name": "Oscar Lopez",
        "current_club": "Mallorca B",
        "club_id": 34997,
        "league_name": "Tercera Federación, Group 11",
        "main_position": "MC",
        "puesto": "MC",  # SofaScore: ?
        "sofascore_id": 1994823,
        "tournament_id": 11360,
    },
    {
        "id": "quimey-vasco",
        "name": "Quimey Vasco",
        "current_club": "Gimnasia y Esgrima U20",
        "club_id": 498451,
        "league_name": "Torneo Juvenil Superliga",
        "main_position": "MC",
        "puesto": "MC",  # SofaScore: ?
        "sofascore_id": 2549065,
        "tournament_id": 27239,
    },
    {
        "id": "ramiro-vaca",
        "name": "Ramiro Vaca",
        "current_club": "Wydad Casablanca",
        "club_id": 36268,
        "league_name": "Botola Pro",
        "main_position": "MC",
        "puesto": "MCO",  # SofaScore: MC/AM
        "sofascore_id": 876307,
        "tournament_id": 937,
    },
    {
        "id": "roberto-carlos-fernandez",
        "name": "Roberto Carlos Fernández",
        "current_club": "Akron Togliatti",
        "club_id": 285689,
        "league_name": "Russian Premier League",
        "main_position": "DF",
        "puesto": "LI",  # SofaScore: DL/ML
        "sofascore_id": 986778,
        "tournament_id": 203,
    },
    {
        "id": "yomar-rocha",
        "name": "Yomar Rocha",
        "current_club": "Akron Togliatti",
        "club_id": 285689,
        "league_name": "Russian Premier League",
        "main_position": "DF",
        "puesto": "LD",  # SofaScore: DR
        "sofascore_id": 1390571,
        "tournament_id": 203,
    },
]


def obtener_todos_los_jugadores() -> list[dict]:
    """Devuelve todos los legionarios.

    Entrega copias para que quien consuma la lista no altere `LEGIONARIOS`
    por accidente.
    """
    return [jugador.copy() for jugador in LEGIONARIOS]


def obtener_jugador_por_id(player_id: str) -> Optional[dict]:
    """Busca un jugador por su `id`. Devuelve None si no existe."""
    if not player_id:
        return None
    clave = player_id.strip().lower()
    for jugador in LEGIONARIOS:
        if jugador["id"] == clave:
            return jugador.copy()
    return None


def obtener_jugadores_por_posicion(posicion: str) -> list[dict]:
    """Devuelve los jugadores de una posicion ("DF", "MC", "ED", "DEL").

    Lanza ValueError si la posicion no es valida: un filtro mal escrito debe
    avisar, no devolver una lista vacia que parezca "no hay jugadores".
    """
    if not posicion:
        raise ValueError(f"Posicion vacia. Validas: {', '.join(POSICIONES_VALIDAS)}")

    clave = posicion.strip().upper()
    if clave not in POSICIONES_VALIDAS:
        raise ValueError(
            f"Posicion '{posicion}' no valida. Validas: {', '.join(POSICIONES_VALIDAS)}"
        )

    return [j.copy() for j in LEGIONARIOS if j["main_position"] == clave]


def verificar_ids() -> list[str]:
    """Revisa la coherencia interna de la lista y devuelve los problemas hallados.

    No consulta la red: comprueba que no haya ids repetidos, campos faltantes
    ni posiciones fuera del catalogo.
    """
    problemas = []
    campos = ("id", "name", "current_club", "league_name",
              "main_position", "sofascore_id", "tournament_id")

    vistos_id = set()
    vistos_sofascore = set()

    for jugador in LEGIONARIOS:
        nombre = jugador.get("name", "(sin nombre)")

        for campo in campos:
            if campo not in jugador:
                problemas.append(f"{nombre}: falta el campo '{campo}'")

        if jugador.get("main_position") not in POSICIONES_VALIDAS:
            problemas.append(
                f"{nombre}: posicion '{jugador.get('main_position')}' fuera del catalogo"
            )

        if jugador.get("id") in vistos_id:
            problemas.append(f"{nombre}: id duplicado '{jugador.get('id')}'")
        vistos_id.add(jugador.get("id"))

        if jugador.get("sofascore_id") in vistos_sofascore:
            problemas.append(
                f"{nombre}: sofascore_id duplicado '{jugador.get('sofascore_id')}'"
            )
        vistos_sofascore.add(jugador.get("sofascore_id"))

    return problemas


if __name__ == "__main__":
    print(f"Legionarios cargados: {len(obtener_todos_los_jugadores())}\n")

    for j in obtener_todos_los_jugadores():
        print(f"  {j['name']:<26} {j['main_position']:<4} "
              f"{j['current_club']:<18} {j['league_name']:<22} "
              f"sofascore={j['sofascore_id']} torneo={j['tournament_id']}")

    print("\nPor posicion:")
    for pos in POSICIONES_VALIDAS:
        encontrados = obtener_jugadores_por_posicion(pos)
        nombres = ", ".join(j["name"] for j in encontrados) or "-"
        print(f"  {pos:<4} ({len(encontrados)}): {nombres}")

    print("\nBusqueda por id:")
    print("  miguel-terceros ->", (obtener_jugador_por_id("miguel-terceros") or {}).get("current_club"))
    print("  no-existe       ->", obtener_jugador_por_id("no-existe"))

    fallos = verificar_ids()
    print("\nVerificacion:", "sin problemas" if not fallos else f"{len(fallos)} problema(s)")
    for f in fallos:
        print("  -", f)
