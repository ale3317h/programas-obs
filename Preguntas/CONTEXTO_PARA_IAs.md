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

## 3. Fondo negro de los X2 (A MEDIAS — terminar)
- Problema: los X2 neón venían con fondo negro cuadrado opaco (alpha 255 en esquinas); los iconos viejos son transparentes fuera del círculo → en OBS se veía un cuadradote negro sobre las cámaras.
- Hecho: se corrió `D:\Temp\opencode\fix_bg.py`: máscara circular (opaco hasta r=490, corte suave hasta r=507, igual huella que los iconos viejos cuyo recorte es ~0.495×1024) aplicada a las 2 activas + apagadas regeneradas desde las activas recortadas.
- PENDIENTE: 1) verificar visualmente las 4 tarjetas, 2) actualizar los embeds `chicos_saltar`/`chicas_saltar` en `overlay-comodines.html` con las versiones recortadas (convertir a WebP lossless base64 como en §1), 3) borrar temp (`fix_bg.py`, `diag_bg.py`, `diag_ring.py`, `mask_debug.png` en `D:\Temp\opencode\`).

## 4. Guion del conductor (PENDIENTE)
- El usuario quiere actualizar el guion con todos los cambios, resumido y sin relleno: el conductor debe saber **cuándo valen los comodines por ronda**, con avisos tipo "en la siguiente ronda no valen, úsenlos".
- Cambios a reflejar: Saltar→Doble o nada (+3/−1), validez por ronda (leer `comodines` de cada ronda en `preguntas_banco.json`; 50/50 solo en opciones; Final sin comodines), redoble arreglado.
- Pistas: existe `D:\Google Drive\Herramientas_OBS\Chicos_VS_Chicas_CONDUCTOR_sin_rebote.pdf`. No se encontró fuente `.docx` editable (buscar antes de regenerar; el usuario pegó el contenido del PDF en el chat).

## Datos útiles
- Sonidos en `sonidos/`: `redoble.wav` (+ `rufando-os-tambores.mp3` alternativo por CLAVES). OBS necesita "Controlar el audio mediante OBS" tildado.
- No dejar `.bak` sueltos en la carpeta del programa (ya se limpió el de `overlay-comodines.html`).
- Ante pedido ambiguo del usuario, preguntar antes de asumir (ej. qué es "los 2 html": son `preguntas-obs-local.html` vía tarjetas + `overlay-comodines.html` con embeds).
