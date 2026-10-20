# Cambios y versiones — Preguntas (Chicos vs Chicas)

Cada versión tiene su **tag** y su **release** con el ZIP descargable del programa.
La fuente de verdad del juego es `preguntas_banco.json`; el guion se genera/verifica contra el banco.

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
