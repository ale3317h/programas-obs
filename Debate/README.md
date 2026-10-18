# Debate — Control del Productor (Centro de Estudiantes 2026)

Placa inferior en pantalla con **título, subtítulo, logo y cronómetro** para moderar un debate en vivo. El productor maneja todo desde una ventana de Python; lo que se ve en stream es un overlay transparente que se apila sobre las cámaras.

## Cómo usarlo

1. Ejecutar: `python debate_control.py`
2. En OBS: Fuente → Navegador → `http://127.0.0.1:8765/overlay` (o "Archivo local" → `debate-obs-local.html`), 1920×1080, **tildar "Controlar el audio mediante OBS"**.
3. Desde la ventana de control: elegir un preset (o título propio), cargar tiempo, **INICIAR**. El cronómetro corre y la barra cambia de blanco → amarillo → rojo. A 0:00 suena la **campana de box**.

## Qué tiene

- **Presets por bloques:** Bienvenida/Cierre, Presentación (30s), Propuestas (60s), Mano a mano (Pregunta 15s / Respuesta 45s / Réplica 45s), Discurso (60s). Botones fáciles de apretar en vivo.
- **Título personalizado** libre (título + subtítulo) sin cortar el reloj.
- **Cronómetro** con barra de progreso neón; ±5s, reinicio, pausa.
- **Sonido dual (OBS + parlantes de la PC):** campana de fin de tiempo, sonido de inicio al arrancar, tic-tac en los últimos 10 s (Web Audio para loop sin cortes). Botón "Silenciar todo" como corte de emergencia.
- **Semáforo de OBS:** el overlay avisa cada 2s (`/ping`) si está vivo y si el audio quedó bloqueado; se ve en la ventana del productor.
- **Logo** configurable: poner `logo.png` al lado del `.py` (busca en vivo, sin reiniciar).

## Archivos

| Archivo | Qué es |
|---|---|
| `debate_control.py` | El programa (ventana de control + servidor en :8765 + audio MCI). Todo en un solo archivo. |
| `debate-obs-local.html` | Overlay para OBS (respaldo si se usa "Archivo local" en vez del servidor). |
| `sonidos para programa de navegador/` | `campana-de-box.mp3`, `TIC TAC SONIDO.mp3`, `sonido inicio reloj.mp3`. |

## Detalles técnicos

- Puerto: **8765**. Endpoints: `/overlay`, `/state` (JSON, el overlay lee cada 250 ms), `/sonido/{campana,tictac,inicio}`, `/logo`, `/ping` (POST, beacon del overlay).
- El tic-tac local (parlantes) se sincroniza con el estado del reloj desde Python; el bug viejo de "el tic queda sonando para siempre" ya está corregido (todo MCI pasa por un `RLock`).
- Sin dependencias externas: `tkinter` + `http.server` + `winmm` (ctypes).
