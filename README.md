# Scouting - Futbolistas Bolivianos en el Exterior

Prototipo en Streamlit para explorar jugadores, filtrarlos y visualizar su rendimiento.

> Los datos incluidos son **ficticios**, generados aleatoriamente. No representan jugadores ni estadisticas reales.

## Estructura

```
scouting-bolivia/
├── app.py                   # App de Streamlit
├── data/
│   ├── jugadores.csv        # Perfil + metricas (0-100) por jugador
│   ├── partidos.csv         # Ultimos 6 partidos de cada jugador
│   └── toques.csv           # Coordenadas de toques, por partido
├── utils/
│   └── generate_data.py     # Regenera los CSV de prueba
├── requirements.txt
└── venv/                    # Entorno virtual
```

## Como ejecutar

```bash
cd "/Users/tutufarah/Desktop/Tutu /scouting-bolivia" && venv/bin/streamlit run app.py
```

Se abre en http://localhost:8501

## Que incluye

- **Lista de jugadores** en tabla, con descarga a CSV.
- **Filtros** en la barra lateral: posicion, pais/liga y rango de edad.
- **Radar de rendimiento** (mplsoccer) sobre 6 metricas: finalizacion, creacion, pase, regate, defensa, fisico. Permite comparar dos jugadores en el mismo grafico.
- **Mapa de calor acumulado** de los ultimos 6 partidos (mplsoccer `Pitch` + KDE), con el ataque hacia la derecha.
- **Ultimos 6 partidos**: resumen (puntuacion media, minutos, goles, asistencias, balance V-E-D), tabla con fecha, rival, local/visitante, marcador, resultado y puntuacion, y un **mapa de calor por partido** en rejilla de zonas.

En las etiquetas de cada partido, `vs` indica local y `@` visitante. El marcador va siempre en orden *equipo del jugador - rival*.

## Regenerar datos de prueba

```bash
cd "/Users/tutufarah/Desktop/Tutu /scouting-bolivia" && venv/bin/python utils/generate_data.py
```

## Siguiente paso: datos reales

Para pasar de prueba a produccion, reemplaza los CSV manteniendo las columnas:

- `jugadores.csv`: `id, nombre, posicion, club, pais_liga, edad, partidos_jugados, finalizacion, creacion, pase, regate, defensa, fisico` (metricas en escala 0-100).
- `partidos.csv`: `partido_id, jugador_id, jornada, fecha, rival, condicion, goles_favor, goles_contra, resultado, puntuacion, minutos, goles_jugador, asistencias_jugador`.
  - `fecha` en formato `AAAA-MM-DD`; `condicion` es `Local` o `Visitante`; `resultado` es `Victoria`, `Empate` o `Derrota`; `puntuacion` va de 1 a 10.
  - `goles_favor` / `goles_contra` son del equipo del jugador, no del rival.
- `toques.csv`: `partido_id, jugador_id, x, y` en coordenadas StatsBomb (cancha de 120 x 80).

La app detecta los cambios en los CSV por su fecha de modificacion, asi que basta recargar el navegador — no hace falta reiniciar el servidor.
