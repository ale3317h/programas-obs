# Cambios y versiones — Preguntas (Chicos vs Chicas)

Cada versión tiene su **tag** y su **release** con el ZIP descargable del programa.
La fuente de verdad del juego es `preguntas_banco.json`; el guion se genera/verifica contra el banco.

## v1.2.1 — 20/10/2026 — Revertido el cambio de URL del overlay

**Se volvió atrás el cambio de la v1.2.0.** En la prueba de OBS en la PC real
el overlay **no se veía** con la URL adaptativa, así que se restauró el
`preguntas-obs-local.html` **byte a byte** a como estaba antes (el que funciona,
58544 bytes, hash `667239CB...`). La línea vuelve a ser:

```js
const B='http://127.0.0.1:8769';
```

- No se toca ningún otro archivo.
- La v1.2.0 queda **sin efecto**: usar v1.2.1 (o la v1.1.0) para el HTML.

## v1.2.0 — 20/10/2026 — Overlay visible siempre (URL base adaptativa)

**El problema real de "no se ve el HTML en OBS":** el overlay tenía la dirección
del motor **fija** (`const B='http://127.0.0.1:8769'`). Si OBS (o el navegador)
abría la fuente desde otra dirección, el overlay se quedaba sin datos y no se
veía nada. Por eso también "no tomaba los cambios".

**Arreglo (una línea, mínima):** ahora usa el puerto/dirección desde la que se
abrió, con 8769 de reserva:

```js
const B=(location.protocol==='http:'||location.protocol==='https:')
        ?(location.origin||'http://127.0.0.1:8769'):'http://127.0.0.1:8769';
```

- No se tocó nada más del HTML (ni CSS, ni fases, ni estructura).
- El HTML está en **UTF-16 con BOM** (ojo al editarlo: si se guarda en UTF-8
  puede fallar). Se edita respetando la codificación.
- **Probado con el motor real:** `http://127.0.0.1:8769/` carga el overlay
  completo (título, aros, tarjetas de comodines, cartel, reloj), sin errores de
  consola y sin pedidos fallidos. También probado el juego completo: r1, r2 (el
  equipo lo manda la pregunta), r3 por temas, Matemáticas por aproximación,
  comodines (doble o nada +3/−1, 50/50, llamada, cambiar con reserva) y el
  **rebote de la final** (falla CHICOS → rebota a CHICAS con el reloj de nuevo).

### Cómo lo tiene que abrir OBS

- Fuente Navegador → **URL**: `http://127.0.0.1:8769/` (1920x1080).
- Escenas informativas: `/reglas`, `/comodines`, `/categorias`.
- **No** usar "Archivo local": OBS cachea el archivo y los cambios no se ven.

## v1.1.0 — 20/10/2026 — Contrato v4 + validador del banco

- **`CONTRATO.md` reescrito a v4** (estaba en v2 y hablaba del "Saltar" viejo):
  - reglas actuales: doble o nada (+3/−1), redoble, Matemáticas (`mate`) con
    `responden: ambos` + aproximación, **r4 sin rebote y por turnos**, final
    10 s con **rebote** y `sigue_si_acierta`, desempate;
  - tabla completa de `/state` (incluye `revelando`, `doble`, `rebote`,
    `resultados`, `intentos`, `panel`, `timer` con llamada, `p_*`, `cal`, `vol`);
  - rutas HTTP, tarjetas, amarillas, fotos de temas y config v4;
  - **regla para OBS: usar `http://127.0.0.1:8769/`**, no el archivo local
    (el motor sirve todo con `Cache-Control: no-store`);
  - conteos reales del banco: **68 entradas** (50 preguntas + 18 reservas).
- **`validar_banco.py` nuevo**: reutiliza la validación real del motor
  (`cargar_banco`) y agrega los chequeos del contrato (orden de rondas,
  rebote solo en la final, Matemática por aproximación, reservas para
  "cambiar", 3 temas en r3, comodines por ronda, conteos del guion y
  preguntas repetidas).
  - `python validar_banco.py` → el banco actual pasa **sin avisos**.
  - `python validar_banco.py --strict` → los avisos también hacen fallar.
- El HTML y el motor **no se tocaron** en esta versión.

## v1.0.0 — 20/10/2026 — Base estable (documentación al día)

- **HTML del overlay**: se mantiene el estado que funciona (`b3fdf8f`, restaurado el 19/10).
  El intento de "Volver al título / Volver a la pregunta" (18/10) dejó el overlay sin verse en OBS
  y fue revertido por completo (HTML y motor). Este release parte de esa base sana.
- **CONTEXTO_PARA_IAs.md**: §3 (fondo negro de los X2) y §4 (guion del conductor) cerrados,
  con el detalle de la verificación. Queda anotado que **r4 (Capciosas) NO rebota** según el banco del 18/10.
- **Guion_conductor_ACTUALIZADO.md**: resincronizado con `preguntas_banco.json` del 18/10:
  - rebote **solo en la final** (se quitó de Matemáticas y de r4),
  - Matemáticas toma las preguntas por estimación ("luz del Sol", "días de clase"),
  - reservas de r4 actualizadas (sin la reserva vieja),
  - sección nueva **"Avisos del conductor entre rondas"**,
  - aviso de la final reescrito: **sin comodines, 10 s por pregunta, seguidas y sin pausas,
    y si falla el que responde la misma pregunta rebota al otro con el reloj nuevo**.
- **preguntas_config.json**: estado de la última ejecución (volúmenes y calibración usados).

> Para OBS: usar como Fuente Navegador **`http://127.0.0.1:8769/`** (el motor sirve el overlay
> con `Cache-Control: no-store`), no el archivo local. Así los cambios se ven siempre.
