# Publicar la app para que la vea otra persona

Objetivo: un link que tu colega pueda abrir desde su trabajo, sin instalar nada
y sin que tu Mac tenga que estar encendida.

Se usa **Streamlit Community Cloud**, que es gratuito.

---

## Paso 1 — Crear una cuenta de GitHub (5 minutos, gratis)

1. Entra en <https://github.com/signup>.
2. Registrate con tu correo y elige un nombre de usuario.
3. Confirma el correo que te envian.

Si ya tienes cuenta, salta al paso 2.

## Paso 2 — Crear el repositorio

1. Entra en <https://github.com/new>.
2. En **Repository name** escribe: `scouting-legionarios`
3. Dejalo en **Public**.
4. **No** marques ninguna casilla de "Add a README" ni ".gitignore".
5. Pulsa **Create repository**.

GitHub te mostrara una pagina con comandos. Ignorala: los de abajo ya estan
listos.

## Paso 3 — Subir el proyecto

Copia tu nombre de usuario de GitHub y ejecuta esto en la Terminal, cambiando
`TU-USUARIO` por el tuyo:

```bash
cd "/Users/tutufarah/Desktop/Tutu /scouting-bolivia" && git remote add origin https://github.com/TU-USUARIO/scouting-legionarios.git && git branch -M main && git push -u origin main
```

Te pedira usuario y contraseña. **La contraseña normal no funciona**: hay que
crear un token en <https://github.com/settings/tokens> → *Generate new token
(classic)* → marca la casilla **repo** → *Generate*. Copia ese token y pegalo
cuando pida la contraseña.

## Paso 4 — Publicar la app

1. Entra en <https://share.streamlit.io> y pulsa **Sign in with GitHub**.
2. Pulsa **Create app** → **Deploy a public app from GitHub**.
3. Rellena:
   - **Repository**: `TU-USUARIO/scouting-legionarios`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Abre **Advanced settings** y en **Python version** elige **3.13**.
5. Pulsa **Deploy**.

Tarda unos 3-5 minutos la primera vez. Cuando termine tendras un link tipo:

```
https://scouting-legionarios.streamlit.app
```

Ese es el que le pasas a tu colega. Funciona desde cualquier computadora o
telefono, sin instalar nada.

---

## Actualizar los datos mas adelante

La app publicada consulta SofaScore en vivo. Si el servidor no pudiera llegar a
SofaScore (ver mas abajo), tira de la copia guardada. Para refrescar esa copia:

```bash
cd "/Users/tutufarah/Desktop/Tutu /scouting-bolivia" && venv/bin/python utils/generar_snapshot.py && git add -A && git commit -m "Actualizar datos" && git push
```

Streamlit Cloud detecta el cambio y republica sola en un par de minutos.

Lo mismo cuando agregues jugadores a `database.py`.

---

## Cosas que conviene saber

**SofaScore bloquea muchas IPs de servidores.** Puede que desde Streamlit Cloud
no se pueda consultar en vivo. Por eso la app lleva `data/snapshot_sofascore.json`,
una copia de todas las respuestas: si la consulta en vivo falla, usa esa copia y
tu colega ve los datos igual. En la barra lateral aparece de que fecha es.
Si notas que los numeros no cambian, es que esta tirando de la copia: vuelve a
ejecutar el comando de actualizacion de arriba.

**El link es publico.** Cualquiera que lo tenga puede abrirlo, incluida la lista
de jugadores que estan siguiendo. No lleva contraseña. Si mas adelante lo
quieres restringido, Streamlit permite invitar por correo en la configuracion
de la app (opcion *Settings → Sharing*).

**Si el despliegue falla** por versiones de librerias, abre `requirements.txt` y
borra los numeros de version, dejando solo los nombres:

```
streamlit
mplsoccer
pandas
numpy
requests
curl_cffi
```

Guarda, haz `git add -A && git commit -m "Aflojar versiones" && git push` y
Streamlit reintentara.
