# CONTRATO — Chicos VS Chicas (Preguntas + Comodines)

Carpeta: `D:\Mi unidad\Herramientas_OBS\Programa para Programas\Preguntas` · Puerto **8769**.
Este contrato es la única fuente de verdad entre motor (`preguntas_control.py`), overlay (`preguntas-obs-local.html`), banco (`preguntas_banco.json`) y tarjetas (`tarjetas/`).
**Nadie edita este archivo.** Si algo no alcanza, se pide en `CAMBIOS_CONTRATO.md` (se agrega al final, con tu nombre de IA).

## 0. Dueños (cada IA toca SOLO lo suyo)

| Archivo | Dueña |
|---|---|
| `CONTRATO.md`, `preguntas_banco.json`, `validar_banco.py` | IA-1 (Datos) |
| `preguntas-obs-local.html`, `_test/mock_estado.py` | IA-2 (Overlay) |
| `preguntas_control.py`, `preguntas_config.json` | IA-3 (Motor) |
| `tarjetas/*.png`, `generar_tarjetas.py`, `REPORTE_QA.md` | IA-4 (Arte + QA) |

Nadie toca `..\Debate`, `..\Ruleta`, `..\Juego` ni `sonidos/`. Copia `.bak` antes de editar. Cada IA deja `ESTADO_IA-N.md`.

## 1. Banco v2 (`preguntas_banco.json`)

```json
{
  "version": 2,
  "titulo": "",
  "rondas": [ <ronda>, ... ]
}
```

`titulo` puede ser `""` (vacío válido: no se muestra nada).

### Ronda
| Campo | Valor |
|---|---|
| `id` | `r1`, `r2`, `r3`, `r4`, `final`, `desempate` |
| `nombre` | Texto para mostrar |
| `color` | Hex del neón de la ronda |
| `tipo` | `"opciones"` (A–D) o `"abierta"` (sin opciones) |
| `puntos` | Puntos por acierto (1 o 2) |
| `seg` | Segundos por pregunta (20 normal, 10 final) |
| `comodines` | Claves de comodín que SÍ valen en la ronda |
| `orden` | `"alterno"` (turnos alternados) o `"por_tema"` (solo r3) |
| `preguntas` | Lista (en el orden en que se juegan). En r3 no existe: ver `temas` |
| `reservas` | Lista para el comodín Cambiar |

Comodines por ronda: r1 y r2 → `llamada, saltar, cambiar, 5050`. r3 y r4 → `llamada, saltar, cambiar` (abiertas: no hay 50/50). `final` y `desempate` → `[]`.

### Pregunta
```json
{ "id": "r1-01", "q": "texto",
  "o": ["A","B","C","D"], "c": 2,          // solo tipo "opciones"; c = índice (0 = A)
  "r": "texto de la respuesta",            // solo "abierta"; se muestra al revelar
  "nota": "solo conductor",                // opcional; NUNCA va al overlay
  "equipo": "chicas" }                     // solo r2: qué equipo la responde
```
- Reservas: mismo formato, `id` con `R`: `r1-R1`.
- **r2**: lista ya intercalada (chicas, chicos, chicas, chicos…). Las reservas llevan `equipo`; Cambiar usa la reserva del mismo equipo.
- **r3**: en lugar de `preguntas` trae `"temas": [ {id, nombre, color, preguntas:[4], reservas:[3]} ]`. Cada equipo elige 1 tema y responde sus 4 preguntas; las 3 reservas son las "5", "6" y la reserva del PDF (en ese orden).
- **desempate**: D4 lleva `"especial": "lista"` (nombrar 5 países en 10 s: el conductor marca Acierto/Error).

## 2. `/state` v2 (GET `http://127.0.0.1:8769/state`)

Se mantienen todos los campos actuales (`rev, qid, visible, turno, puntos, usados, aviso, cal, vol, p_*, tic_desde, fase, elegida, ocultas, resultado`). Cambian o se agregan:

```json
{
  "titulo": "",                 // puede ser vacío
  "titulo_visible": false,      // false si titulo == ""
  "fase": "inicio|pregunta|opciones|revelada",   // en abiertas "opciones" = pregunta ya con reloj
  "tipo": "opciones|abierta|null",
  "ronda": {"id":"r2","nombre":"TERRITORIO ENEMIGO","color":"#a78bfa","n":3,"total":8,"puntos":2,"reserva":false},
  "tema": {"nombre":"Minecraft","color":"#22c55e","equipo":"chicos"},   // solo r3, sino null
  "equipo_pregunta": "chicas",  // quién responde (r2/r3), sino null
  "preg": {"texto":"…","opciones":["…","…","…","…"]},  // opciones=[] si abierta; "" hasta fase opciones
  "correcta": 2,                // índice, SOLO revelada y tipo opciones
  "respuesta": "Ankara",        // SOLO revelada (en opciones = texto de la correcta); antes SIEMPRE null
  "resultado": "acierto|error|null",
  "comodines_validos": ["llamada","saltar","cambiar"],   // los que valen en la ronda actual
  "seleccion_tema": null,       // o {"elige":"chicos","temas":[{"nombre":"…","color":"#…","estado":"libre|chicos|chicas|sin_usar"}]}
  "timer": {"total":20,"restante":14,"total_ms":20000,"restante_ms":13420,"t_ms":1760000000000,
            "corriendo":true,"etiqueta":"TIEMPO","llamada":false}
}
```

**Nunca** se envía `respuesta`, `correcta` ni `nota` antes de `revelada`.

### Texto del cartel bajo la cámara central (lo arma el overlay)
- Línea 1: `tema.nombre` si hay tema; si no, `ronda.nombre` (MAYÚSCULAS).
- Línea 2: `n / total` + `· RESERVA` si corresponde + `· VALE {puntos} PT` (`PTS` si > 1).
- Color: el del tema o el de la ronda.

### Reloj fluido (regla compartida)
- Motor: `restante_ms` exacto (≥ 0), `total_ms`, `corriendo`.
- Overlay: al recibir cada `/state` guarda `performance.now()` y estima `restante_ms - (performance.now() - recibido)` en cada `requestAnimationFrame`. Dígitos = `ceil(est/1000)`. Barra = `est/total_ms` sin `transition` de ancho.
- **Prohibido** sacar y volver a poner clases de color en cada lectura (reinicia la animación y cambia el tono). La clase se toca solo al **cruzar 50 % (amarillo) o 25 % (rojo)**.

## 3. Reglas de juego (las implementa el motor)
1. Acierto suma `ronda.puntos` al equipo que respondió. Error o tiempo agotado: se revela y sigue la siguiente; el otro equipo no responde esa.
2. Turnos alternados (`turno` = quien responde). Empieza quien indica el conductor (botones Chicos / Chicas / Ninguno).
3. **Comodines**: 1 por pregunta; solo los de `comodines_validos`; si no se puede aplicar, no se gasta y se avisa.
   - *Saltar*: descarta sin puntos ni rebote; pasa al otro equipo con la pregunta siguiente.
   - *Cambiar*: usa la reserva (r2: del mismo equipo; r3: del mismo tema); hay que responderla.
   - *50/50*: solo `tipo` opciones; deja la correcta + 1 incorrecta.
   - *Llamada*: 30 s, después el reloj de la pregunta continúa donde estaba.
4. **r3**: el equipo que va ganando elige tema primero (empate: lo marca el conductor), el otro elige entre los 3 restantes. Se alternan preguntas empezando por quien eligió primero; cada equipo recibe la siguiente de **su** tema.
5. Final: 10 s, sin comodines, 2 pts. Empieza el que va perdiendo.
6. Título vacío: el motor guarda `""` tal cual. No existe valor por defecto "MÁS WACHIN".

## 4. Tarjetas
`tarjetas/{chicos|chicas}_{llamada|saltar|cambiar|5050}_{activa|apagada}.png` — 1024×1024, redondas, transparente fuera del círculo. Servidas en `/img/<nombre>.png`. Los nombres no cambian.

## 5. Zona de cámaras (fija, 1920×1080)
`chicos {x:66,y:141,w:651,h:635}` · `mid {x:760,y:141,w:398,h:635}` · `chicas {x:1202,y:141,w:651,h:635}` · panel inferior desde y=792. El overlay puede usar `cal` (calibración) del estado.
