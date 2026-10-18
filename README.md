# Programas para OBS

Suite de 4 programas de control en vivo para transmisiones por OBS Studio (eventos, debates y juegos). Cada programa es una app de Python (tkinter) que levanta un **servidor local** en `127.0.0.1` y un **overlay HTML** que se agrega como Fuente Navegador en OBS (1920×1080, fondo transparente).

## Cómo funciona (patrón común a los 4)

```
┌─────────────────────┐        HTTP local (sin wifi)        ┌──────────────────────┐
│  Control (productor) │  ──── /state (JSON, cada pocos ms) ──▶  Overlay en OBS      │
│  ventana Python      │  ◀──  /sonido/*.mp3  (audio)       │  Fuente Navegador     │
│  (lo que ve el       │  ◀──  /img, /foto    (imágenes)    │  1920x1080 transparente│
│   productor en su PC)│                                     │                       │
└─────────────────────┘                                     └──────────────────────┘
```

- **Sin internet, sin pip:** solo la librería estándar de Python (`tkinter`, `http.server`, `ctypes`/winmm para audio).
- **Audio dual:** cada sonido puede salir por OBS (overlay) **y** por los parlantes de la PC en simultáneo, para escucharlo en la sala aunque OBS esté muteado.
- **En OBS:** agregar Fuente → Navegador → "Archivo local" (o la URL `http://127.0.0.1:<puerto>/overlay`) → 1920×1080, posición 0,0, y **tildar "Controlar el audio mediante OBS"**.

## Los 4 programas

| Programa | Carpeta | Puerto | Para qué sirve |
|---|---|---|---|
| **Debate** | `Debate/` | 8765 | Placa inferior con título, subtítulo, logo y **cronómetro con barra neón** para debates (presentaciones, propuestas, réplicas, discursos). Presets por bloques, campana de box al llegar a 0:00, tic-tac. |
| **Ruleta** | `Ruleta/` | 8766 | **Ruleta giratoria** que elige la dinámica o el invitado (sectores editables con colores). Giro + efecto de victoria sincronizados con un mp3 maestro. |
| **Juego IA** | `Juego/` | 8768 | **"¿Es IA o no es IA?"** con 4 jugadores en cámaras: votan, se revela con redoble y se restan vidas. |
| **Preguntas** | `Preguntas/` | 8769 | **"Chicos vs Chicas"**: juego de preguntas completo con 7 rondas, comodines, muerte súbita con rebote, redoble de tambores, marcador neón y elección de temas. Es el más desarrollado. |

## Requisitos

- Windows (el audio usa winmm/MCI nativo).
- Python 3.10+ (probado en 3.12 y 3.14). El único módulo necesario es el que ya viene: `tkinter`.
- OBS Studio (cualquier versión reciente).

## Cómo se organizan los cambios (historial de versiones)

Cada programa se subió como **commit separado** en Git. Cada vez que se toque algo, se hace un commit nuevo con mensaje claro, así se puede volver atrás a cualquier versión anterior:

```bash
git log --oneline          # ver el historial
git checkout <commit>      # volver a una versión vieja
```

Las carpetas `__pycache__/`, los `.bak` y las copias manuales quedan fuera del repo (ver `.gitignore`).

## Planes

- **Preguntas / Chicos vs Chicas:** base para un formato **semanal con temáticas rotativas** (nerds vs turros, maestros vs profes, química vs informática, etc.). Antes de armar eso hay que corregir bugs y pulir la experiencia del productor en vivo.

---

*Cada carpeta tiene su propio `README.md` con detalles de uso, archivos y configuración.*
