# CONTEXTO PARA IAs — Sesión X2 / Doble o nada (2026-10-16)

Carpeta de trabajo: `D:\Google Drive\Herramientas_OBS\Programa para Programas\Preguntas (1)\`
Todo lo de esta sesión pasó ahí, salvo temp scripts en `D:\Temp\opencode\`.

## Estado general
- Motor: `preguntas_control.py` (puerto 8769). Overlays: `preguntas-obs-local.html` (juego, carga tarjetas vía `/img/`), `overlay-comodines.html` (comodín grande, imágenes **incrustadas** en base64 WebP + texto en `var COM`), `overlay-reglas.html`, `overlay-categorias.html`.
- REGLA DE ORO: la clave del comodín sigue siendo `"saltar"` en motor, `/state`, `usados`, tarjetas y `KEYS` del overlay. Solo cambió el NOMBRE visible a "Doble o nada". **Nunca renombres la clave.**
- Motor ya traía `DOBLE_ACIERTO = 3`, `DOBLE_ERROR = 1` (nunca baja de 0), `COMODINES = (..., ("saltar", "DOBLE O NADA"), ...)`. No se tocó el `.py` por los iconos.

## 1. Saltar → Doble o nada (HECHO)
- `tarjetas/chicos_saltar_activa.png` = X2 neón azul; `tarjetas/chicas_saltar_activa.png` = X2 neón rosa. Fuentes originales en `lol/` (archivos UUID `e84b6d97...` = azul/chicos, `c33acf61...` = rosa/chicas; eran de 1254px, se bajaron a 1024x1024 RGBA).
- Apagadas generadas con receta (misma que las otras apagadas): gris = luminancia × 78/255; X con `W = 1024*0.062*1.2`, `O = 1024*0.155`, blur 5, borde (8,8,10), relleno (150,150,156).
- `overlay-comodines.html`: `COM.saltar` = `{c:"#a78bfa",l:"#ddd2ff" (intactos), t:"Doble o nada", chip:"ACIERTO +3 / ERROR -1", x:"Si aciertas te llevas <b>3 puntos</b> y si fallas te resta <b>1 punto</b>."}`. IMGS `chicos_saltar`/`chicas_saltar` reemplazadas por WebP lossless base64 de las activas. Verificado: resto del archivo idéntico.
- PDFs: `Novedades - Doble o nada (productor).pdf` (resumen simple, con fotos) quedó en la carpeta.

## 2. Bug sonido redoble (HECHO)
- Síntoma: redoble sonaba en PC pero no en OBS; demás sonidos OK.
- Causa: `preguntas-obs-local.html` solo conocía 6 sonidos; `redoble` faltaba en las 2 listas (líneas ~200 y ~247). El motor sí manda `p_redoble` y suena local por MCI.
- Fix: agregado `'redoble'` a ambas listas. Tras el cambio hay que **recargar las fuentes de navegador en OBS**.

## 3. Fondo negro de los X2 (HECHO — cerrado 20/10)
- Problema: los X2 neón venían con fondo negro cuadrado opaco (alpha 255 en esquinas); los iconos viejos son transparentes fuera del círculo → en OBS se veía un cuadradote negro sobre las cámaras.
- Hecho: se corrió `fix_bg.py`: máscara circular (opaco hasta r=490, corte suave hasta r=507) aplicada a las 2 activas + apagadas regeneradas desde las activas recortadas.
- Cerrado (20/10, verificación numérica con Pillow): las 4 tarjetas tienen esquinas alpha 0, opaco adentro de r≈500, corte suave 505-512, transparente desde r=515 (misma huella que los iconos viejos). **Los embeds `chicos_saltar`/`chicas_saltar` de `overlay-comodines.html` YA eran las versiones recortadas**: cero diferencia de píxel en zona visible contra los PNG actuales (solo ruido RGB en píxeles transparentes). No hizo falta regenerar nada.
- Los temp a borrar (`fix_bg.py`, `diag_bg.py`, `diag_ring.py`, `mask_debug.png` en `D:\Temp\opencode\`) no existen en esta máquina (D: no existe acá): nada que borrar.

## 4. Guion del conductor (HECHO — cerrado 20/10)
- `Guion_conductor_ACTUALIZADO.md` resincronizado contra `preguntas_banco.json` (banco del 18/10, posterior al guion del 16/10). Verificado: 68 preguntas banco ↔ guion, 0 faltantes.
- Cambios reflejados:
  - **REBOTE SOLO EN LA FINAL.** El banco del 18/10 ya no tiene `"rebote": true` en r4 → el guion decía "r4 con rebote" y quedó corregido (ficha, reglas, escaleta, §8, notas de producción). El motor obedece el campo del JSON (`ron["rebote"] = r.get("rebote") is True and ...`), así que r4 hoy NO rebota. ⚠️ Si el productor quiere que r4 rebote de nuevo: agregar `"rebote": true` a la ronda r4 del banco y avisar (el guion habría que revertir esa parte).
  - "¿Cuántos segundos tarda la luz del Sol?" y "¿Cuántos días de clase mínimo?" **pasaron de r4 a Matemáticas** (mate tiene 7 preguntas, r4 quedó con 5); la de la luz del Sol tiene `seg: 60` (mate) y la de los gatos tiene `seg: 60` (r4) — anotado en el guion.
  - Reserva r4 "¿Cuántos minutos tiene un día?" ya no existe en el banco → quitada del guion.
  - **Avisos del conductor entre rondas** (pedido del productor): nueva sección en §2 con frases para cada transición ("última ronda con 50/50", "Matemáticas sin comodines, si les quedó alguno usenlo ahora o se pierde", "la final sin comodines y sin redoble").
  - DOBLE O NADA (+3/−1, clave `saltar`), 50/50 solo en opciones (r1/r2), final sin comodines y sin redoble: ya estaban y siguen correctos.
- Backup del guion previo: `C:\Users\hg\AppData\Local\Temp\opencode\Guion_conductor_ACTUALIZADO.md.bak`.

## Datos útiles
- Sonidos en `sonidos/`: `redoble.wav` (+ `rufando-os-tambores.mp3` alternativo por CLAVES). OBS necesita "Controlar el audio mediante OBS" tildado.
- No dejar `.bak` sueltos en la carpeta del programa (ya se limpió el de `overlay-comodines.html`).
- Ante pedido ambiguo del usuario, preguntar antes de asumir (ej. qué es "los 2 html": son `preguntas-obs-local.html` vía tarjetas + `overlay-comodines.html` con embeds).
