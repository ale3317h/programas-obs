# CONTRATO — Chicos VS Chicas (Preguntas + Comodines) — v4

Carpeta: `G:\Mi unidad\Herramientas_OBS\Programa para Programas\Preguntas` · Puerto **8769**.
Este contrato es la única fuente de verdad entre motor (`preguntas_control.py`), overlay (`preguntas-obs-local.html`), banco (`preguntas_banco.json`), tarjetas (`tarjetas/`) y fotos (`fotos/`).
**Nadie edita este archivo de prepo.** Si algo no alcanza, se pide en `CAMBIOS_CONTRATO.md` (se agrega al final, con el nombre de quien lo pide).

> **Regla de oro:** la clave técnica del comodín "Doble o nada" es **`saltar`** (nombre histórico, para no romper motor/overlay/banco). **No se renombra.** Lo que ve el público es "DOBLE O NADA".

## 0. Dueños (cada IA toca SOLO lo suyo)

| Archivo | Dueño |
|---|---|
| `CONTRATO.md`, `preguntas_banco.json`, `validar_banco.py` | IA-1 (Datos) |
| `preguntas-obs-local.html` | IA-2 (Overlay) |
| `preguntas_control.py`, `preguntas_config.json` | IA-3 (Motor) |
| `tarjetas/*.png`, `generar_tarjetas.py`, `REPORTE_QA.md` | IA-4 (Arte + QA) |
| `overlay-reglas.html`, `overlay-comodines.html`, `overlay-categorias.html` | IA-5 (Overlays secundarios) |

Nadie toca `..\Debate`, `..\Ruleta`, `..\Juego` ni `sonidos/`.
**Backups:** fuera de la carpeta del programa (`%TEMP%\opencode\`). **No se dejan `.bak`** en la carpeta.

## 1. El juego (lo que implementa el motor)

Orden: **r1 → r2 → r3 → Matemáticas (`mate`) → r4 Capciosas → final → desempate**.

1. **Turnos:** r1, r2, r4, final y desempate alternan. Empieza quien indica el conductor (botones Chicos / Chicas).
2. **Matemáticas (`mate`):** responden **los dos equipos a la vez** (`"responden": "ambos"`) y se juega **por aproximación** (`"aproximacion": true`): gana el más cercano al número (`num`). Sin comodines. 40 s (si una pregunta trae `seg` propio, usa ese).
3. **r4 Capciosas y lógica:** turno alternado (responde el equipo que indica el conductor), 30 s, comodines llamada / doble o nada / cambiar. **No rebota** y **no responden los dos**: el banco del 18/10 tiene `"orden": "alterno"` y no trae `responden`.
4. **Acierto:** suma `ronda.puntos` (3 mientras se juega DOBLE O NADA). **Error o tiempo agotado:** se revela y sigue la siguiente; el otro equipo no responde esa pregunta (salvo rebote de la final).
5. **Comodines:** uno por pregunta, solo los de `comodines_validos`; si no se puede aplicar, **no se gasta** y se avisa.
   - **Llamada a un amigo** (`llamada`): 30 s de reloj aparte; al terminar, el reloj de la pregunta sigue donde estaba.
   - **Doble o nada** (`saltar`): si acierta **+3**, si falla **−1** (el marcador nunca baja de 0). Cumplido el tiempo, pasa a la pregunta siguiente. En la final no vale.
   - **Cambiar** (`cambiar`): usa una reserva (r2: del mismo equipo; r3: del mismo tema). La reserva hay que responderla.
   - **50/50** (`5050`): solo en rondas de opciones; deja la correcta + una incorrecta.
   - Por ronda: r1/r2 → las 4; r3/r4 → llamada, doble o nada, cambiar; `mate`, `final` y `desempate` → **ninguno**.
6. **Rebote (solo la final):** si el que responde falla, **la misma pregunta rebota al otro equipo con el reloj de nuevo** (10 s). El overlay muestra `FALLO {EQUIPO}` + `REBOTE` en el color del que falló y el turno pasa al otro. La final además trae `"sigue_si_acierta": true`: el que acierta sigue respondiendo.
7. **Redoble:** en las rondas normales suena el audio `redoble` completo y recién ahí se revela (fase `revelando`), con `REDOBLE_COLA = 0.3 s` de cola. Si el audio no tiene duración medible, se esperan `3.0 s`. En la final **no** se usa.
8. **Final:** 10 s por pregunta, **sin comodines**, 2 pts, preguntas seguidas y sin pausas, con rebote.
9. **Desempate:** 10 s, 1 pt, sin comodines. La D4 es `"especial": "lista"` (nombrar 5 países en 10 s; el conductor marca Acierto/Error).
10. **Título:** puede ser `""` (vacío válido). No hay valor por defecto.

## 2. Banco (`preguntas_banco.json`) — formato v2

```json
{
  "version": 2,
  "titulo": "",
  "rondas": [ <ronda>, ... ]
}
```

`titulo` puede ser `""` (no se muestra nada).

### Ronda

| Campo | Valor |
|---|---|
| `id` | `r1`, `r2`, `r3`, `mate`, `r4`, `final`, `desempate` |
| `nombre` | Texto para mostrar (máx. recomendado 24) |
| `color` | Hex del neón de la ronda |
| `tipo` | `"opciones"` (A–D) o `"abierta"` (sin opciones) |
| `puntos` | Puntos por acierto |
| `seg` | Segundos por pregunta (20 normal, 40 mate, 30 r4, 10 final/desempate) |
| `comodines` | Claves que **sí** valen en la ronda |
| `orden` | `"alterno"` o `"por_tema"` (solo r3) |
| `preguntas` | Lista en orden de juego (en r3 no existe: ver `temas`) |
| `reservas` | Lista para el comodín Cambiar |
| `responden` | Opcional. `"ambos"` = contestan los dos equipos a la vez (solo `mate`) |
| `aproximacion` | Opcional. `true` = gana el más cercano al `num` (solo `mate`) |
| `rebote` | Opcional. `true` = la pregunta fallada rebota al otro (solo `final`) |
| `sigue_si_acierta` | Opcional. `true` = el que acierta sigue respondiendo (solo `final`) |
| `sin_tiempo` | Opcional. `true` = ronda sin reloj |

Restricciones que valida el motor: `responden: "ambos"` no vale en `por_tema`; `rebote` solo vale en rondas por turno que no sean r2 ni por temas; `aproximacion` necesita `responden: "ambos"` + `tipo: "abierta"`; 50/50 no vale en abiertas.

### Pregunta

```json
{ "id": "r1-01", "q": "texto",
  "o": ["A","B","C","D"], "c": 2,          // solo tipo "opciones"; c = índice (0 = A)
  "r": "texto de la respuesta",            // solo "abierta"; se muestra al revelar
  "nota": "solo conductor",                // opcional; NUNCA va al overlay
  "equipo": "chicas",                      // solo r2: qué equipo la responde
  "seg": 60,                               // opcional: segundos propios (5–600)
  "num": 150000000,                        // opcional: respuesta numérica (mate)
  "especial": "lista" }                    // opcional: caso especial (desempate)
```

- **Reservas:** mismo formato, `id` con `R`: `r1-R1`.
- **r2:** lista ya intercalada (chicas, chicos, chicas, chicos…); cada pregunta y cada reserva llevan `equipo`. Cambiar usa la reserva del mismo equipo.
- **r3:** en lugar de `preguntas` trae `"temas": [ {id, nombre, color, preguntas:[4], reservas:[3]} ]`. Cada equipo elige 1 tema y responde sus 4 preguntas; las 3 reservas son las "5", "6" y una extra. El banco actual trae 3 temas: `minecraft`, `cine`, `cultura`.
- **mate:** `r` es el número como texto y `num` el valor numérico para comparar. El motor muestra los intentos de ambos.
- **final:** 6 preguntas, `rebote: true`, `sigue_si_acierta: true`, sin reservas.
- **desempate:** 4 preguntas; la D4 lleva `"especial": "lista"`.

### Conteo actual (banco del 18/10)

| Ronda | Preguntas | Reservas | Comodines |
|---|---|---|---|
| r1 Cultura general | 8 | 2 | 4 |
| r2 Territorio enemigo | 8 | 2 | 4 |
| r3 Elige tu tema | 3 temas × 4 | 3 temas × 3 | 3 |
| mate Matemáticas | 7 | 3 | — |
| r4 Capciosas y lógica | 5 | 2 | 3 |
| final Gran final | 6 | — | — |
| desempate | 4 | — | — |
| **Total** | **50** | **18** | **68 entradas** |

## 3. Rutas HTTP (GET)

| Ruta | Devuelve |
|---|---|
| `/state` | JSON del estado (ver §4) |
| `/sonido/<n>` | Audio del sonido `n` (`usar`, `reactivar`, `inicio`, `campana`, `tictac`, `acierto`, `error`, `redoble`) |
| `/img/<nombre>.png` | Tarjeta (`tarjetas/`) |
| `/foto/<nombre>` (o `/fotos/`) | Foto de tema (`fotos/`), si existe |
| `/` y `/overlay` | **Overlay principal** (`preguntas-obs-local.html`) |
| `/reglas` | `overlay-reglas.html` |
| `/comodines` | `overlay-comodines.html` |
| `/categorias` | `overlay-categorias.html` |

Todas las respuestas llevan `Cache-Control: no-store` y `Access-Control-Allow-Origin: *`.

> **Para OBS:** usar como Fuente Navegador **`http://127.0.0.1:8769/`** (y `/reglas`, `/comodines`, `/categorias` para las otras escenas). **No** usar el archivo local: el navegador de OBS cachea el archivo y los cambios "no se ven". Con la URL del motor siempre se sirve la versión actual.

## 4. `/state` (v4)

```json
{
  "rev": 12, "qid": 4, "visible": true,
  "titulo": "¿QUIÉN SABE MÁS?", "titulo_visible": true,
  "fase": "inicio|pregunta|opciones|revelando|revelada",
  "tipo": "opciones|abierta|null",
  "ronda": {"id":"final","nombre":"Gran final","color":"#f59e0b","n":2,"total":6,
            "puntos":3,"reserva":false,"responden":"turno","aproximacion":false,"rebote":true},
  "tema": {"nombre":"Minecraft","color":"#22c55e","equipo":"chicos"},
  "equipo_pregunta": "chicas",
  "preg": {"texto":"…","opciones":["…","…","…","…"]},
  "ocultas": [3], "elegida": 2,
  "correcta": 2, "respuesta": "Canberra",
  "resultado": "acierto|error|null",
  "comodines_validos": ["llamada","saltar","cambiar"],
  "seleccion_tema": null,
  "doble": "chicos",
  "rebote": "chicas",
  "resultados": {"chicos":"acierto","chicas":"error"},
  "intentos": {"chicos": 120000000, "chicas": 150000000},
  "panel": {"regla": null, "comodin": null, "equipo": null, "categorias": null},
  "turno": "chicas",
  "puntos": {"chicos": 4, "chicas": 2},
  "usados": {"chicos": {"llamada":false,"saltar":true,"cambiar":false,"5050":false}},
  "aviso": {"n": 3, "l1": "FALLO CHICAS", "txt": "REBOTE", "col": "#ff4fb8"},
  "timer": {"total":10,"restante":7,"total_ms":10000,"restante_ms":6812,
            "t_ms":1760000000000,"corriendo":true,"etiqueta":"TIEMPO",
            "llamada":false,"llamada_eq":null,"activo":true},
  "tic_desde": 1760000000000,
  "cal": {"size":150,"dy":0,"chicos_dx":0},
  "vol": {"usar": {"pc":30,"obs":39}},
  "p_redoble": 2
}
```

Notas:
- **Privacidad:** `respuesta`, `correcta` y `nota` **nunca** salen antes de `fase: "revelada"`. La nota solo la ve el conductor (`datos_conductor()`).
- `rebote` = equipo que **falló** y rebotó la pregunta; `turno` ya es el otro.
- `doble` = equipo que está jugando DOBLE O NADA (mientras dura, `ronda.puntos` = 3).
- `intentos` solo aparece en `fase: "revelada"` y en rondas `responden: ambos`.
- `ocultas` (índices que tapa el 50/50) solo en `opciones`/`revelada`.
- `aviso`: `n` cambia con cada aviso; `l1` línea chica, `txt` texto grande, `col` color.
- `timer.activo = false` → el overlay no muestra reloj (rondas `sin_tiempo`).
- `p_<sonido>`: contador de pulsos para disparar el audio una sola vez por evento.

## 5. Overlay principal (`preguntas-obs-local.html`)

- **Fases:** `inicio` (título/tarjetas), `pregunta` (se lee la pregunta), `opciones` (aparecen A–D y arranca el reloj), `revelando` (redoble, sin respuesta), `revelada` (respuesta + resultado).
- **Cartel bajo la cámara central:** línea 1 = tema o ronda en MAYÚSCULAS; línea 2 = `n / total` + `· RESERVA` si corresponde + `· VALE {puntos} PT` (`PTS` si > 1). Color = tema o ronda.
- **Reloj fluido:** el overlay guarda `performance.now()` al recibir cada `/state` y estima `restante_ms` en cada `requestAnimationFrame`. Dígitos = `ceil(est/1000)`. Barra = `est/total_ms` **sin** `transition` de ancho. El color se toca solo al cruzar **50 %** (amarillo) o **25 %** (rojo).
- **Tarjetas:** `tarjetas/{chicos|chicas}_{llamada|saltar|cambiar|5050}_{activa|apagada}.png`, 1024×1024, redondas, transparentes fuera del círculo. Se sirven en `/img/<nombre>.png`; los nombres **no cambian**.
- **Doble o nada:** la tarjeta y el panel usan la clave `saltar`, pero el texto visible es **DOBLE O NADA**. La X2 reemplaza al ícono viejo de "saltar".
- **Amarillas (opcional):** `tarjetas/amarillo_{llamada|saltar|cambiar|5050}_activa.png` para `overlay-comodines.html`. Si no existen, el overlay usa su propio arte (no rompe).
- **Fotos de tema (opcional):** `fotos/tema_minecraft.jpg`, `tema_cine.jpg`, `tema_cultura.jpg` (1280×720, < 300 KB). Se piden a `/foto/tema_<tema>.jpg`; si faltan, queda el arte propio.
- **Regla para cambios:** el overlay actual **es el que funciona**. Cualquier cambio se hace mínimo, se prueba primero en un navegador con un mock de `/state` y después en OBS. No se reescribe completo ni se toca la estructura de fases sin probar. (El intento de "Volver al título" del 18/10 dejó el overlay invisible y se revirtió entero.)

## 6. Config (`preguntas_config.json`, versión 4)

| Clave | Contenido |
|---|---|
| `v` | `4` |
| `vol` | `{sonido: {pc, obs}}` — volumen de cada sonido para la PC y para OBS |
| `cal` | `{size, dy, chicos_dx}` — calibración de las cámaras |
| `usados` | Comodines gastados por equipo |
| `puntos` | Marcador |
| `progreso` | Preguntas ya jugadas (`id → "hecha"`) |
| `titulo` | Título en pantalla |
| `turno`, `alternar`, `primera` | Turnos |
| `auto_inicio`, `ultimo_res`, `ronda`, `seg_ovr`, `sel` | Estado de la partida |

El motor guarda la config en cada cambio. Si el archivo no existe o está roto, arranca con valores de fábrica.

## 7. Validación

- `python validar_banco.py` → `0` si el banco sirve (puede haber avisos), `1` si hay errores.
- `python validar_banco.py --strict` → también falla si hay avisos (textos largos, ids repetidos, etc.).
- El motor valida al cargar (`cargar_banco()`): los errores duros (`ValueError`) impiden jugar; los avisos se muestran pero el banco se usa.
- Largos recomendados: pregunta ≤ 90, respuesta ≤ 36, opción ≤ 28, nombre de ronda/tema ≤ 24.

## 8. Cambios de v3 a v4

1. Se documenta la ronda **`mate`** (Matemáticas): `responden: ambos`, `aproximacion`, `num`, 40 s.
2. Se documenta el **rebote** (solo `final`) y `sigue_si_acierta`.
3. Se actualiza la tabla de **comodines por ronda** (r4 ya no tiene 50/50; mate/final/desempate sin comodines).
4. Se actualiza la fase **`revelando`** (redoble) y el `timer` con `llamada`, `llamada_eq`, `activo`, `etiqueta`.
5. Se documentan `panel`, `doble`, `resultados`, `intentos`, `p_*`, `tic_desde`, `fotos/` y las tarjetas amarillas.
6. Se corrigen los conteos reales del banco (68 entradas: 50 preguntas + 18 reservas).
7. Se agrega `validar_banco.py` y la regla de **usar la URL del motor** (no el archivo) en OBS.
8. Se aclara que **r4 no rebota** y que en r4 responde un equipo por turno (no los dos).
