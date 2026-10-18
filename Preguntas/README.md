# Preguntas — "Chicos vs Chicas" (juego de preguntas con comodines)

Juego de preguntas para dos equipos (**Chicos** vs **Chicas**) con marcador neón, 7 rondas, comodines, redoble de tambores antes de revelar, muerte súbita con rebote y elección de temas. Es el programa más desarrollado de la suite y la **base del próximo formato semanal con temáticas rotativas** (nerds vs turros, maestros vs profes, química vs informática, etc.).

## Cómo usarlo (flujo en vivo)

1. Ejecutar: `python preguntas_control.py`
2. En OBS: Fuente → Navegador → `http://127.0.0.1:8769/overlay` (o "Archivo local" → `preguntas-obs-local.html`), 1920×1080.
   Orden de capas en OBS: **fondo** (imagen o video) → **las 3 cámaras** → **este overlay** (arriba del todo). Tildar "Controlar el audio mediante OBS".
3. Flujo por pregunta:
   - Elegir **RONDA** (en "Elige tu tema": cada equipo elige su tema).
   - Indicar **quién empieza** (Chicos / Chicas / Ninguno).
   - **Siguiente pregunta** → **Mostrar opciones** → **Iniciar tiempo**.
   - Elegir la respuesta del equipo (o marcar a mano) → **Revelar** (suena el **redoble**, reloj pausado; segundo clic revela ya) → resultado + puntos → siguiente.
4. **Comodines** (teclas 1–4 Chicos, 5–8 Chicas): 1 por pregunta y solo los válidos en la ronda. Si no se puede aplicar, **no se gasta** y el programa dice por qué.
   - **LLAMADA A UN AMIGO:** 30 s y después vuelve el reloj de la pregunta. Si no funcionó, se puede **devolver** (botón "Devolver").
   - **DOBLE O NADA** (clave técnica `saltar`): acierto **+3**, error **−1** (nunca baja de 0).
   - **CAMBIAR PREGUNTA:** usa una reserva de la ronda (en r2 del mismo equipo; en r3 del mismo tema).
   - **50/50:** deja la correcta + 1 incorrecta (solo rondas con opciones A–D).

## Las 7 rondas (banco actual)

| Ronda | id | Tipo | Pts | Tiempo | Comodines | Notas |
|---|---|---|---|---|---|---|
| Cultura general | `r1` | opciones | 1 | 20 s | los 4 | — |
| Territorio enemigo | `r2` | opciones | 2 | 20 s | los 4 | Cada pregunta la responde un equipo fijo |
| Elige tu tema | `r3` | abierta | 1 | 20 s | llamada, doble, cambiar | 3 temas (Minecraft, Cine, Cultura); cada equipo elige uno |
| Matemáticas | `mate` | abierta | 1 | 40 s | ninguno | Responden los dos; gana **el más cercano** (aproximación) |
| Capciosas y lógica | `r4` | abierta | 1 | 30 s | llamada, doble, cambiar | **Con rebote:** si falla, la misma pregunta pasa al otro |
| Gran final | `final` | abierta | 2 | 10 s | ninguno | Muerte súbita: acierta → sigue; falla → rebota; fallan los dos → se revela. Revela **sin** redoble |
| Desempate | `desempate` | abierta | 1 | 10 s | ninguno | Solo si empatan |

## Qué tiene

- **Marcador neón** arriba (Chicos azul / Chicas rosa) con pop animado al sumar.
- **Aro de turno** alrededor de la cámara del equipo que responde (en rondas "ambos" no hay aro).
- **Redoble de tambores** en todas las revelaciones (fase `revelando`: suspenso con el reloj pausado). Única excepción: la final revela directo.
- **Rebote** en Capciosas y final: falla → la misma pregunta al otro equipo con reloj nuevo y **sin revelar**; fallan los dos → se revela y no suma nadie.
- **Elección de temas** (ronda r3): el que va ganando elige primero; si hay empate, el conductor marca quién empieza.
- **Banco de preguntas en JSON** editable con el Bloc de notas + botón "Recargar banco" (conserva el anterior si hay error y dice cuál).
- **Avance persistente** (`preguntas_config.json`): puntos, comodines usados, preguntas hechas, ronda, elección de temas, volumen y calibración. Si se cierra y vuelve a abrir, sigue donde estaba.
- **Guion del conductor** generado desde el banco real: `Guion_conductor_ACTUALIZADO.md`.
- **Pantallas informativas** de OBS aparte: reglas (`/reglas`), comodín grande (`/comodines`), categorías (`/categorias`), cada una en su escena.
- **Guía de cámaras** para acomodar el overlay sobre las cámaras reales (deslizadores de posición/tamaño en la ventana).
- **Teclado:** 1–4 comodines Chicos, 5–8 comodines Chicas (solo USAN; reactivar es con botón, para no errarle en vivo).

## Archivos

| Archivo | Qué es |
|---|---|
| `preguntas_control.py` | El programa: motor del juego + ventana del productor + servidor en :8769 + audio MCI. Todo en un archivo (~1500 líneas). |
| `preguntas-obs-local.html` | Overlay principal (marcador, pregunta, opciones, tarjetas de comodines, reloj, paneles). |
| `preguntas_banco.json` | Banco v2 de preguntas (rondas → preguntas + reservas). |
| `preguntas_config.json` | Estado guardado (puntos, avance, volumen, calibración). Se regenera solo. |
| `CONTRATO.md` | Contrato técnico entre motor, overlay y banco (esquema de `/state`, reglas de juego). |
| `TAREAS_v4.md` | Plan de trabajo v4 (tareas por IA / pendientes). |
| `Guion_conductor_ACTUALIZADO.md` | Guion del conductor con todas las respuestas (documento privado). |
| `CONTEXTO_PARA_IAs.md` | Notas de la última sesión de desarrollo (cambios Doble o Nada, fix del redoble en OBS, etc.). |
| `overlay-reglas.html`, `overlay-comodines.html`, `overlay-categorias.html` | Overlays secundarios (escenas aparte en OBS). |
| `generar_tarjetas.py` | Script que genera las tarjetas PNG de comodines (neón Chicos/Chicas). |
| `sonidos/` | usar, reactivar, inicio, campana, tictac, acierto, error, **redoble**. |
| `tarjetas/` | 16 PNG: `{chicos|chicas}_{llamada|saltar|cambiar|5050}_{activa|apagada}.png`. |
| `Novedades - Doble o nada (productor).pdf` | Ficha resumen de los cambios recientes. |

## Detalles técnicos

- Puerto: **8769** (Debate 8765, Ruleta/Juego 8766): puede estar abierto a la vez que todos.
- Endpoints: `/state` (JSON con todo el estado; **nunca** incluye respuesta/correcta antes de `revelada`), `/sonido/<n>`, `/img/<tarjeta>.png`, `/foto/<tema>.jpg`, `/overlay`, `/reglas`, `/comodines`, `/categorias`.
- El reloj corre por hora real (`time.monotonic`): no se atrasa aunque la ventana se congele.
- Duración del redoble medida del propio mp3 (Xing/VBR o CBR) para esperar lo justo antes de revelar.
- Calibración del overlay (`cal`): tamaño de tarjetas, posición de comodines por equipo, panel inferior.
- Sin dependencias externas: `tkinter` + `http.server` + `winmm` (ctypes).

## Pendientes conocidos

- Bugs y pulido para la emisión en vivo (comodidad del productor) antes de encarar el formato semanal con temáticas.
- Estado de tareas: ver `TAREAS_v4.md` y `CONTEXTO_PARA_IAs.md`.
