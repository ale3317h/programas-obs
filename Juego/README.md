# Juego IA — "¿Es IA o no es IA?"

Juego para 4 participantes (cámaras en las 4 esquinas de una pantalla central): se muestra un video, cada uno vota si piensa que **es IA o no es IA**, se revela con **redoble de tambores** y se restan vidas a los que fallan.

## Cómo usarlo

1. Ejecutar: `python juego_ia_control.py`
2. En OBS: Fuente → Navegador → "Archivo local" → `juego-ia-obs-local.html` (o `http://127.0.0.1:8768/overlay`), 1920×1080.
3. Flujo: elegir **nivel del video** (Fácil / Medio / Difícil / Muy difícil / Extremo) → el equipo vota (cámara por cámara: Es IA / No es IA / Sin voto) → **REVELAR** (redoble N segundos, configurable) → se marcan aciertos y fallas → **Siguiente video**.

## Qué tiene

- **4 jugadores con cámaras:** nombre editable, corazones (vidas), voto individual y resultado (ACERTÓ / FALLÓ −1 vida).
- **Vidas globales:** Spinbox "Vidas" + botón "Aplicar a todos". Botones ± por jugador.
- **Fases con estado claro** en la ventana: VOTANDO → REVELANDO... → REVELADO (el botón REVELAR se deshabilita en las otras fases).
- **Resultado grupal:** si la mayoría acertó suena "acierto"; si no, "error". Empate = error.
- **Sonidos con volumen dual** (parlantes PC / OBS) por sonido: `redoble`, `acierto`, `error`. Se puede elegir el archivo a mano si el nombre no coincide.
- **Ajuste fino del overlay:** deslizadores para acomodar el marco del video central (X, Y, ancho, alto) y el título, en caso de que la cámara no calce.

## Archivos

| Archivo | Qué es |
|---|---|
| `juego_ia_control.py` | El programa (ventana de control + servidor + audio MCI). |
| `juego-ia-obs-local.html` | Overlay para OBS (marco del video, tarjetas de jugadores, vidas). |
| `juego_ia_config.json` | Volúmenes, rutas de audio y calibración del overlay (se guarda solo). |
| `sonidos_ia/` | `rufando-os-tambores.mp3` (redoble), `correct.mp3`, `buzzer-error.mp3`. Se detectan por nombre (claves: redoble/tambor, correct/bien/win, error/fail/wrong) o por elección manual. |

## Detalles técnicos

- Puerto: **8768** (reservado para este juego: Debate 8765, Ruleta 8766, Preguntas 8769; puede estar abierto a la vez que todos).
- Endpoints: `/state` (JSON), `/sonido/<nombre>`, `/overlay`.
- El overlay oculta la respuesta hasta la fase "revelado" (el motor filtra `resp` en `/state`).
- Sin dependencias externas: `tkinter` + `http.server` + `winmm` (ctypes).
