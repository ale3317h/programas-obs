# Ruleta — Ruleta giratoria para elegir dinámicas

Ruleta animada para elegir al azar la dinámica, el invitado o la temática (sectores con texto y color). El giro y el efecto de victoria van **sincronizados con un solo mp3 maestro** (giro + "win" en un archivo), así el audio y la animación nunca se desfasan.

## Cómo usarlo

1. Ejecutar: `python ruleta_control.py`
2. En OBS: Fuente → Navegador → `http://127.0.0.1:8766/overlay` (o "Archivo local" → `ruleta-obs-local.html`), 1920×1080.
3. Botón **GIRAR** (o barra espaciadora). Espera a que termine el giro para volver a girar.
4. "Mostrar/Ocultar" saca la ruleta de pantalla sin cerrar el programa.

## Qué tiene

- **Sectores editables:** 2 a 12, con texto (máx. 30 caracteres) y color. Se guardan solos en `ruleta_items.json`. Botones ▲▼ para ordenar, ✕ para quitar, paleta de colores + selector libre.
- **Título de arriba** configurable (ej. "El más villero es…"): el marco se ajusta solo al largo del texto. Enter = aplicar.
- **Audio maestro sincronizado:** al apretar GIRAR, el programa fija el instante exacto en que arranca el mp3 y el overlay dibuja la animación como función de ese tiempo. Línea de tiempo medida del mp3: lanzamiento 0.15 s, tics hasta 6.3 s, silencio 7.0 s, golpe de WIN 7.08 s.
- **Sonido dual:** parlantes de la PC (volumen aparte) y/OBS (volumen aparte). Probar sonido y Silenciar.
- El **mp3 "juntos"** se busca solo: cualquier archivo con "juntos" en el nombre dentro de la carpeta de sonidos.

## Archivos

| Archivo | Qué es |
|---|---|
| `ruleta_control.py` | El programa (ventana de control + servidor en :8766 + audio MCI con espera activa para precisión). |
| `ruleta-obs-local.html` | Overlay de la ruleta para OBS. |
| `ruleta_items.json` | Sectores guardados (texto + color). |
| `ruleta_titulo.txt` | Título de arriba. |
| `ruleta_config.json` | Volúmenes (PC / OBS). |
| `sonidos para programa de navegador/SONIDOS JUNTOS.mp3` | Audio maestro giro+win. |

## Detalles técnicos

- Puerto: **8766**. Endpoints: `/overlay`, `/state` (JSON, el overlay lee cada ~70 ms), `/sonido/ruleta`.
- El audio de la PC corre en un hilo propio dedicado a MCI (el dispositivo queda atado al hilo que lo abre; por eso no se comparte con la GUI).
- LEAD = 0.35 s de amague antes de que arranque el mp3; DURACIÓN = 9.6 s hasta poder volver a girar.
- Sin dependencias externas: `tkinter` + `http.server` + `winmm` (ctypes).
