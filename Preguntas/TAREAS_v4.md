# TAREAS v4 · Chicos VS Chicas (reemplaza a `tareas_otras_IA-3.md`)

> **Cómo usar este archivo:** pasale a cada IA SOLO (1) el bloque "CONTEXTO COMÚN" y (2) su sección. No hace falta que lea el resto. Responder en español, entregar archivos COMPLETOS, tocar solo los archivos propios, hacer copia `.bak` antes de editar.

---

## CONTEXTO COMÚN (leer todas)

**Qué es:** programa para OBS en el puerto 8769. Motor Python (tkinter) sirve `/state` (JSON), `/sonido/<n>`, `/foto/<n>.jpg`, y los overlays HTML lo leen cada pocos ms.

**Estado real de los archivos (por fecha del zip, hay desincronía):**

| Archivo | Estado |
|---|---|
| `preguntas_control (1).py` (motor) | **El más nuevo y completo.** Ya tiene: redoble, DOBLE O NADA (+3/−1, clave `saltar`), rondas `ambos`, Matemáticas, Iniciar tiempo, y **rebote en muerte súbita** (campo `"rebote": true` en la ronda). |
| `preguntas_banco.json` | Actualizado. La ronda `final` ya trae `sigue_si_acierta: true` y `rebote: true`. |
| `CONTRATO.md` | **VIEJO** (v2). No conoce nada de lo nuevo. |
| `preguntas-obs-local.html` | **VIEJO.** Sigue con "Saltar" (inicial `S`), sin redoble, sin `revelando`, sin Matemáticas, sin rebote. |
| `overlay-comodines.html` | Viejo: tiene SALTAR violeta ("sin puntos ni rebote"), colores no amarillos. |
| `overlay-reglas.html` | Regla 5 todavía habla del Saltar viejo. |
| `tarjetas/` | 16 PNG, las de `saltar` son del Saltar viejo. **No existen** las `amarillo_*`. |
| `fotos/` | **No existe** la carpeta. |
| `sonidos/rufando-os-tambores.mp3` | Existe (es el redoble). |

**Reglas que cambian en esta versión (valen para todas):**

1. **DOBLE O NADA reemplaza a SALTAR.** Acierta = +3, falla = −1 (nunca baja de 0). La **clave técnica sigue siendo `saltar`** (en `usados`, `comodines_validos`, `panel.comodin`, nombres de PNG). Solo cambia el texto visible y el ícono (X2). Ya no existe "saltar la pregunta".
2. **Muerte súbita CON REBOTE (solo en la ronda `final`):**
   - Acierta → **sigue el mismo equipo** con la pregunta siguiente.
   - Falla → **la MISMA pregunta pasa al otro equipo** y el **cronómetro se reinicia** (10 s). La respuesta no se muestra todavía.
   - Si el segundo también falla → se revela la respuesta, no suma nadie, y se sigue con la próxima.
   - **Ninguna otra ronda rebota** (ni r1, r2, r3, mate, r4, desempate).
3. **REDOBLE DE TAMBORES en TODAS las revelaciones de la respuesta correcta**, sin excepción: rondas normales, por temas, `ambos`, Matemáticas, muerte súbita (incluido cuando acierta o cuando fallan los dos), desempate. Orden fijo: clic → fase `revelando` (suena redoble, reloj pausado, sin respuesta) → fase `revelada` (respuesta + sonido acierto/error). El único momento SIN redoble es el rebote intermedio (falla el primero y la respuesta aún no se revela).
4. Orden de rondas: `r1, r2, r3, mate, r4, final, desempate`.

**Campos de `/state` (los que importan):**

| Campo | Valores / uso |
|---|---|
| `fase` | `opciones` / `revelando` (redoble, sin `respuesta` ni `correcta`) / `revelada` |
| `p_redoble` | número; cuando cambia, reproducir `/sonido/redoble` |
| `timer.activo` | `false` = ocultar reloj |
| `ronda.responden` | `turno` / `ambos` (sin aro de turno si `ambos`) |
| `ronda.aproximacion` | Matemáticas: gana el más cercano |
| `ronda.rebote` | `true` solo en `final` |
| `rebote` | `null` o `"chicos"`/`"chicas"` = equipo que **falló** y rebotó la pregunta al otro (mostrar insignia "REBOTE"; `turno` ya es el otro) |
| `aviso` | `{n, l1, txt, col}` cartel emergente; `n` cambia = mostrar. Rebote lo usa: `l1:"FALLO CHICOS"`, `txt:"REBOTE"` |
| `resultados` | en `ambos`: `{chicos, chicas}` con `null`/`"acierto"`/`"error"` |
| `intentos` | Matemáticas: `{chicos, chicas, gana}` (`gana`: `chicos`/`chicas`/`ambos`/`null`) |
| `doble` | `null`/`"chicos"`/`"chicas"`; activo ⇒ `ronda.puntos` = 3 |
| `panel` | `{regla, comodin, equipo, categorias}`; `equipo` siempre `null` (se muestran las dos tarjetas) |
| `seleccion_tema.elige` | puede ser `null` |

**Para poder jugar/probar aunque otra IA no haya terminado:**
- El motor funciona solo (con el banco). Los overlays se prueban con `_test/mock_estado.py` o abriendo el HTML con un `/state` de ejemplo.
- Si falta una imagen/foto/sonido, **el overlay debe usar un fallback** (arte propio, o no mostrar nada) y nunca romperse.
- Nadie renombra claves ni campos. Si algo falta, se pide en `CAMBIOS_CONTRATO.md` al final.

---

## IA-1 · Datos y documentos
**Archivos:** `CONTRATO.md`, `validar_banco.py`, `preguntas_banco.json`, el guion (PDF).

1. **CONTRATO.md:** reescribirlo a v4 con todo el CONTEXTO COMÚN (reglas 1–4, tabla de `/state`, panel, rondas nuevas, `saltar`=DOBLE O NADA, sonido `redoble`, rebote). Dejar **escrito expresamente** que la muerte súbita **va con rebote** (la versión anterior decía que no).
2. **Esquema del banco:** documentar campos opcionales. Ronda: `sin_tiempo`, `responden` (`turno`/`ambos`), `aproximacion`, `sigue_si_acierta`, `rebote` (solo vale en rondas por turno que no sean `r2` ni por temas). Pregunta: `seg` (5–600), `num` (respuesta numérica).
3. **validar_banco.py:** aceptar esos campos y las rondas nuevas (`mate`; r3 = 3 temas de 4 preguntas + 3 reservas). Avisar textos largos: pregunta >90 caracteres, respuesta >36, opción >28, nombre de ronda o tema >24. Avisar si `rebote` está en una ronda donde no vale.
4. **Guion (PDF):** reemplazar Saltar por Doble o nada y la regla 5; Cultura general 20 s con "Iniciar tiempo"; agregar Matemáticas (carpetas y quién gana); Capciosas: responden los dos al terminar el tiempo; **Gran final con rebote** (acierta sigue, falla pasa la misma pregunta al otro con reloj nuevo, si fallan los dos se revela y se sigue); aclarar que **siempre hay redoble antes de revelar**; actualizar tablas de Cine y Cultura y arte.
5. **Errores del guion:** la ficha dice "3 de desempate" pero hay 4 (D1–D4); en la ronda 4 dice que las preguntas 6 y 7 aceptan aproximado, pero solo la 6 tiene rango (480–520).
6. **Contenido:** "¿país más poblado?" (India) puede cambiar → reformular o fechar; pasar las de Matemáticas a estimaciones (ej. "¿cuántos habitantes tiene…?") para que no acierten los dos siempre.

## IA-2 · Overlay principal
**Archivo:** `preguntas-obs-local.html` (es la versión más desactualizada: empezar por revisar que lea bien el `/state` actual).

1. **Saltar → DOBLE O NADA:** cambiar inicial/nombre/textos (`KEYS` sigue con `saltar`). Insignia "DOBLE O NADA" (ícono X2) cuando `doble` ≠ `null`, más "VALE 3 PT" (viene en `ronda.puntos`). Verificar que el aviso emergente "DOBLE O NADA" entre en su recuadro. Tarjetas: usar `tarjetas/{equipo}_saltar_{activa|apagada}.png`.
2. **Fase `revelando`:** mostrar la pregunta como en `opciones`, sin respuesta ni correcta, con suspenso breve (la casilla de respuesta tiembla). Recién con `revelada` aparece la respuesta con destello. **Debe funcionar igual en todas las rondas, incluida la final.**
3. **Redoble:** reproducir `/sonido/redoble` cuando cambie `p_redoble`, igual que los otros sonidos.
4. **REBOTE (final):** cuando `rebote` ≠ `null`: insignia "REBOTE" visible, aro de turno pasa al otro equipo, el reloj reinicia (ya llega en `timer`), la misma pregunta se queda en pantalla **sin respuesta**. Mostrar el `aviso` ("FALLO X / REBOTE") con el mecanismo de avisos que ya exista.
5. **Rótulo "TIEMPO"** más grande sobre el reloj.
6. **`timer.activo = false`:** ocultar el reloj.
7. **Rondas `ambos`** (Matemáticas y Capciosas): sin aro de turno; mostrar `resultados` de cada equipo al marcar.
8. **Matemáticas:** con `intentos`, mostrar lo que mostró cada carpeta, la respuesta correcta y quién gana ("el más cercano").
9. **Textos largos:** ajuste automático en pregunta (máx. 3 líneas), opciones A–D, respuesta (máx. 3 líneas, centrada) y cartel de ronda/tema. Probar con las respuestas más largas del banco. Nada desborda.
10. **Cámara de chicas desfasada:** el marco y los círculos de comodines de CHICAS quedan corridos del cuadro verde. Posicionar con las coordenadas del contrato y `cal` (en config: `chicas_dx: 10`) y verificar con la guía de cámaras que sea simétrico con chicos.

## IA-5 · Overlays secundarios (tarea nueva, para repartir trabajo)
**Archivos:** `overlay-comodines.html`, `overlay-reglas.html`, `overlay-categorias.html`. **No cambiar los colores de los otros HTML.**

**`overlay-comodines.html`**
1. Todo en **amarillo** (#FACC15, claro #FFF3A0) con brillo y resaltado: aro, título, recuadro y chip.
2. Mostrar **siempre las dos tarjetas** (Chicos y Chicas). Ignorar `panel.equipo`.
3. Reemplazar SALTAR (hoy violeta, "sin puntos ni rebote") por **DOBLE O NADA**. Ícono `tarjetas/amarillo_saltar_activa.png` (si no existe, ícono X2 propio). Texto: "Si responde bien suma 3 puntos. Si responde mal resta 1." Chip: "BIEN +3 · MAL −1". Título de escena: DOBLE O NADA.
4. Texto largo que se achique para entrar en el recuadro.

**`overlay-reglas.html`**
- Regla 5 (comodines): Doble o nada reemplaza a Saltar. Revisar que ninguna regla nombre el Saltar viejo. Si hay una regla de la muerte súbita, que diga **con rebote**.

**`overlay-categorias.html`**
- Llegan solo 3 temas (Minecraft, Cine y series, Cultura y arte). Fotos opcionales por `GET /foto/tema_<id>.jpg` (ids `minecraft`, `cine`, `cultura`); si no existe la foto, usar el arte propio.

## IA-3 · Motor
**Archivos:** `preguntas_control.py` (el del zip se llama `preguntas_control (1).py`: renombrar), `preguntas_config.json`.

El rebote ya existe, pero **hay un hueco con el redoble**. Hoy `_marcar_rebote` llama directo a `_revelar_ya()` (línea ~675) cuando acierta el primero o cuando falla el segundo, **saltándose el redoble**.

1. **Redoble en todos los caminos de revelado:** auditar todo lugar que ponga `fase = "revelada"` (hoy: `revelar()`, `_revelar_ya()`, `_marcar_rebote`, `tick`) y asegurar que **el único camino a "revelada" pase por el redoble** (`revelar()` → `revelando` → `tick` → `_revelar_ya`). Para la muerte súbita: en `_marcar_rebote`, cuando corresponda revelar (acierta, o falla el segundo), guardar el resultado pendiente (`self.pend_res = res`), iniciar el redoble igual que `revelar()`, y aplicar el resultado en `_revelar_ya()` al terminar. Incrementar `p_redoble` cada vez. Una sola excepción sin redoble: el rebote intermedio (falla el primero).
2. Verificar en la final: acierta → mismo equipo con la siguiente; falla → misma pregunta al otro, `reloj_reset`, `auto_inicio` respetado; fallan los dos → redoble, revela, nadie suma, y la siguiente la responde el equipo que **no** empezó esta (o el que corresponda según `sigue_si_acierta`; dejarlo documentado en un comentario).
3. Confirmar que `rebote` en `/state` vuelve a `null` al pasar de pregunta, y que no se puede rebotar en r1, r2, r3, mate, r4 ni desempate.
4. Botones del panel del conductor: en la final con rebote que se vea claro "✖ Error → REBOTE al otro" y luego "✖ Error (fallan los dos)" (ya está en el código; solo comprobarlo).
5. Sigue pendiente que el usuario lo vea corriendo en su PC (tkinter no estaba disponible para la prueba): dejar un `python -m py_compile` limpio y una lista corta de qué probar a mano.

## IA-4 · Arte y sonidos
**Archivos:** `tarjetas/*.png`, `generar_tarjetas.py`, `fotos/`, `REPORTE_QA.md`.

1. **Tarjetas `saltar`** (4 PNG: `{chicos|chicas}_saltar_{activa|apagada}.png`): rehacerlas con el ícono **DOBLE O NADA (X2)** en el mismo estilo neón del resto. **Mantener los nombres.** Hoy las del zip son las viejas (el generador todavía dibuja `icono_saltar` viejo).
2. **Versión amarilla** de las cuatro (llamada, doble o nada, cambiar, 50/50): `amarillo_{llamada|saltar|cambiar|5050}_activa.png` para `overlay-comodines.html`. Prioridad: `amarillo_saltar_activa.png` (la usa IA-5).
3. **Fotos de los temas** en la carpeta nueva `fotos/`: `tema_minecraft.jpg`, `tema_cine.jpg`, `tema_cultura.jpg`; ~1280×720, <300 KB, licencia libre, sin marcas ni logos. Anotar fuente y licencia en `REPORTE_QA.md`.
4. **Sonido:** `rufando-os-tambores.mp3` ya está en `sonidos/`. Comprobar que suena bien como redoble (duración razonable, sin silencio largo al final, volumen parecido a los demás) y anotarlo. No tocar otros sonidos.

---

## Orden sugerido y dependencias

Todas pueden trabajar **a la vez**. Lo único que une a unas con otras:

| Quién espera a quién | Qué |
|---|---|
| IA-5 ← IA-4 | `amarillo_saltar_activa.png` (tiene fallback propio, no bloquea) |
| IA-2 / IA-5 ← IA-3 | solo los nombres de campos del CONTEXTO COMÚN (ya fijados) |
| IA-1 ← todas | refleja el resultado en CONTRATO y guion (puede ir al final) |

**Prueba rápida para el usuario cuando quiera jugar un tramo:** arrancar el motor, cargar r1 → revelar (debe sonar el redoble y recién después mostrarse la respuesta). Para la final: marcar Error con el primer equipo → debe aparecer REBOTE y el reloj reiniciarse; marcar Acierto con el segundo → redoble y revelar.
