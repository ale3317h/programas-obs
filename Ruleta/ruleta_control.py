# -*- coding: utf-8 -*-
"""
Ruleta Juego - Programa de control (Debate 2026)
Un solo programa en Python, sin dependencias. Sin pip.

Uso:
  python ruleta_control.py

Hace 2 cosas:
  1) Abre la ventana de CONTROL de la ruleta.
  2) Levanta un servidor en http://127.0.0.1:8766 (interno de la PC, no usa wifi):
       /overlay        -> sirve ruleta-obs-local.html (lo que se ve en OBS)
       /state          -> JSON que lee el overlay (cada 70 ms)
       /sonido/ruleta  -> SONIDOS JUNTOS.mp3 (giro + win en un solo archivo)

En OBS: fuente Navegador 1920x1080
  - URL http://127.0.0.1:8766/overlay        (recomendado)
  - o "Archivo local": ruleta-obs-local.html (funciona igual)

SINCRONIA AUDIO <-> ANIMACION
  El mp3 es el reloj maestro. Al apretar GIRAR, Python fija ruleta_t0 = ahora + 0.35 s
  (la hora exacta en la que arranca el mp3). El overlay dibuja todo como funcion de
  T = ahora - ruleta_t0, y Python dispara el audio de la PC en ese mismo instante.
  Linea de tiempo del mp3 (medida): lanzamiento 0.15 s, tics hasta 6.3 s,
  silencio 7.0 s, golpe de WIN 7.08 s.

Solo stdlib: tkinter + http.server + winmm (MCI).
"""
import ctypes
import json
import os
import queue
import random
import threading
import time
import tkinter as tk
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tkinter import colorchooser

PORT = 8766
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONIDOS_DIR = os.path.join(BASE_DIR, "sonidos para programa de navegador")
OVERLAY_FILE = os.path.join(BASE_DIR, "ruleta-obs-local.html")
RULETA_FILE = os.path.join(BASE_DIR, "ruleta_items.json")
TITULO_FILE = os.path.join(BASE_DIR, "ruleta_titulo.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "ruleta_config.json")   # volumenes

LEAD = 0.35          # segundos entre apretar GIRAR y el arranque del mp3 (amague de la rueda)
DURACION = 9.6       # segundos que dura todo el giro (hasta que se puede girar de nuevo)
ALIAS = "ruleta_comb"

RULETA_DEFAULT = [
    ("Pregunta sorpresa", "#d60f0f"),
    ("Mímica", "#f7f3ec"),
    ("Verdadero o falso", "#1d4ed8"),
    ("Réplica express", "#facc15"),
    ("Pregunta del público", "#16a34a"),
    ("Dato curioso", "#9333ea"),
    ("Adivinanza", "#f97316"),
    ("Comodín", "#161616"),
]
RULETA_COLORES = ["#d60f0f", "#f7f3ec", "#1d4ed8", "#facc15",
                  "#16a34a", "#9333ea", "#f97316", "#161616"]


# ---------------- Archivos de sonido ----------------
def _buscar_ruleta_juntos():
    # Audio combinado giro+win en UN solo archivo (cualquier mp3 con "juntos" en el nombre).
    try:
        for n in sorted(os.listdir(SONIDOS_DIR)):
            ln = n.lower()
            if ln.endswith((".mp3", ".wav", ".ogg", ".m4a")) and "juntos" in ln:
                return os.path.join(SONIDOS_DIR, n)
    except Exception:
        pass
    return os.path.join(SONIDOS_DIR, "SONIDOS JUNTOS.mp3")


# ---------------- Sectores ----------------
def _cargar_items():
    # Sectores editables: se guardan en ruleta_items.json. Min 2, max 12.
    try:
        with open(RULETA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = []
        for x in data:
            if not x or len(x) < 2:
                continue
            t, c = str(x[0])[:30], str(x[1])
            if not t.strip():
                continue
            if not (c.startswith("#") and len(c) == 7):
                c = "#d60f0f"
            items.append([t, c])
        if 2 <= len(items) <= 12:
            return items
    except Exception:
        pass
    return [list(x) for x in RULETA_DEFAULT]


def _cargar_titulo():
    # Titulo de arriba (ej: "El mas villero es..."): se guarda en ruleta_titulo.txt
    try:
        with open(TITULO_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()[:60]
    except Exception:
        return ""


def _guardar_titulo(t):
    try:
        with open(TITULO_FILE, "w", encoding="utf-8") as f:
            f.write(t)
    except Exception:
        pass


def _cargar_cfg():
    d = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        pass
    def vol(k):
        try:
            return max(0, min(100, int(d.get(k, 100))))
        except Exception:
            return 100
    return {"vol_pc": vol("vol_pc"), "vol_obs": vol("vol_obs")}


def _guardar_cfg(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass


CFG = _cargar_cfg()


def _guardar_items(items):
    try:
        with open(RULETA_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
    except Exception:
        pass


def _fg_para(h):
    try:
        r = int(h[1:3], 16); g = int(h[3:5], 16); b = int(h[5:7], 16)
        return "#111111" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#ffffff"
    except Exception:
        return "#ffffff"


# ---------------- Estado compartido ----------------
state = {
    "ruleta_visible": False,
    "ruleta_giro": 0,          # cada GIRAR lo incrementa -> el overlay anima
    "ruleta_t0": 0.0,          # hora (time.time) a la que arranca el mp3 = T0 de la animacion
    "ruleta_idx": 0,           # sector ganador
    "ruleta_txt": "",
    "ruleta_color": "#ff2a2a",
    "ruleta_r1": 0.5,          # semillas para que overlay elija DONDE frena dentro del sector
    "ruleta_r2": 0.5,
    "ruleta_r3": 0.5,
    "ruleta_sonido_obs": True,  # el overlay reproduce el mp3 (OBS)
    "ruleta_vol_obs": CFG["vol_obs"] / 100.0,   # volumen del audio dentro de OBS (0..1)
    "ruleta_probar": 0,        # +1 = el overlay reproduce el mp3 de prueba
    "ruleta_stop": 0,          # +1 = el overlay corta el audio ya
    "ruleta_items": _cargar_items(),
    "ruleta_titulo": _cargar_titulo(),   # texto que se ve arriba de la ruleta (vacio = oculto)
    "rev": 1,
}
lock = threading.Lock()


def girando():
    with lock:
        return time.time() < state.get("ruleta_t0", 0.0) + DURACION


# ---------------- Audio local Windows (winmm MCI) ----------------
class AudioPC(threading.Thread):
    """Reproduce el mp3 por los parlantes de la PC.

    POR QUE UN HILO PROPIO: el dispositivo MCI (mpegvideo) queda atado al hilo que lo abre
    (crea una ventana oculta ahi). Si ese hilo termina, el 'play' desde otro hilo falla en
    silencio. Por eso TODO lo de MCI (abrir, play, stop, volumen) pasa por este unico hilo,
    que vive mientras viva el programa. Los errores quedan en self.error y se ven en pantalla.
    """

    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self.q = queue.Queue()
        self.ruta = None
        self.ok = False
        self.vol = CFG.get("vol_pc", 100)
        self.pending = None
        self.error = ""
        self.start()

    # ---- API (se puede llamar desde cualquier hilo) ----
    def cargar(self, ruta):
        self.q.put(("load", ruta))

    def reproducir(self, ruta, t0):
        self.q.put(("play", ruta, t0))

    def parar(self):
        self.q.put(("stop",))

    def volumen(self, v):
        self.vol = max(0, min(100, int(v)))
        self.q.put(("vol",))

    # ---- internos (solo corren en este hilo) ----
    def _mci(self, cmd, silencioso=False):
        try:
            buf = ctypes.create_unicode_buffer(260)
            err = ctypes.windll.winmm.mciSendStringW(cmd, buf, 259, None)
        except Exception as e:
            if not silencioso:
                self.error = "este equipo no tiene winmm/MCI (%s)" % e
            return -1
        if err and not silencioso:
            eb = ctypes.create_unicode_buffer(260)
            try:
                ctypes.windll.winmm.mciGetErrorStringW(err, eb, 259)
            except Exception:
                pass
            self.error = "%s (codigo %d)" % (eb.value or "error MCI", err)
        return err

    def _aplicar_vol(self):
        self._mci("setaudio %s volume to %d" % (ALIAS, self.vol * 10), True)

    def _abrir(self, ruta):
        self._mci("close " + ALIAS, True)
        self.ok = False
        cand = [ruta]
        try:   # nombre corto 8.3: evita problemas con espacios / acentos / unidades virtuales
            n = ctypes.windll.kernel32.GetShortPathNameW(ruta, None, 0)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                ctypes.windll.kernel32.GetShortPathNameW(ruta, b, n + 1)
                if b.value and b.value != ruta:
                    cand.append(b.value)
        except Exception:
            pass
        for r in cand:
            for tipo in ("type mpegvideo ", ""):
                if self._mci('open "%s" %salias %s' % (r, tipo, ALIAS), True) == 0:
                    self.ok = True
                    self.ruta = ruta
                    self.error = ""
                    self._aplicar_vol()
                    return True
        # nada funciono: se repite UNA vez mostrando el error real
        if self._mci('open "%s" type mpegvideo alias %s' % (ruta, ALIAS)) == 0:
            self.ok = True
            self.ruta = ruta
            self.error = ""
            self._aplicar_vol()
            return True
        return False

    def _cargar(self, ruta):
        if not ruta or not os.path.exists(ruta):
            self.error = "no encuentro el mp3: %s" % (ruta or "?")
            self.ok = False
            return False
        if self.ok and self.ruta == ruta:
            return True
        return self._abrir(ruta)

    def _play(self):
        self._aplicar_vol()
        self._mci("seek %s to start" % ALIAS, True)
        if self._mci("play " + ALIAS) == 0:
            self.error = ""
            return
        if self.ruta and self._abrir(self.ruta):          # reabre y reintenta una vez
            self._mci("play " + ALIAS)

    def _cmd(self, c):
        if c[0] == "load":
            self._cargar(c[1])
        elif c[0] == "play":
            if self._cargar(c[1]):
                self._mci("stop " + ALIAS, True)
                self.pending = c[2]
            else:
                self.pending = None
        elif c[0] == "stop":
            self.pending = None
            self._mci("stop " + ALIAS, True)
        elif c[0] == "vol":
            self._aplicar_vol()

    def run(self):
        while True:
            try:
                if self.pending is not None:
                    falta = self.pending - time.time()
                    if falta <= 0.012:
                        while time.time() < self.pending:    # ultimos ms: espera activa (< 2 ms de error)
                            pass
                        self.pending = None
                        self._play()
                        continue
                    espera = min(0.2, falta - 0.012)
                else:
                    espera = 0.5
                try:
                    c = self.q.get(timeout=espera)
                except queue.Empty:
                    continue
                self._cmd(c)
            except Exception as e:
                self.error = "audio: %s" % e


AUDIO = AudioPC()


# ---------------- Servidor HTTP ----------------
_AUDIO_MIMES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
                ".m4a": "audio/mp4", ".mp4": "audio/mp4"}


def _servir_mp3(handler, ruta, solo_headers=False):
    # Soporta Range (bytes=) para que <audio> de Chrome/CEF (OBS) no falle.
    try:
        size = os.path.getsize(ruta)
    except OSError:
        handler.send_response(404)
        handler.send_header("Content-Type", "text/plain; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        if not solo_headers:
            try:
                handler.wfile.write(b"mp3 no encontrado")
            except Exception:
                pass
        return
    ctype = _AUDIO_MIMES.get(os.path.splitext(ruta)[1].lower(), "audio/mpeg")
    rango = handler.headers.get("Range")
    inicio, fin, estado = 0, size - 1, 200
    if rango and rango.strip().startswith("bytes="):
        try:
            espec = rango.strip()[6:].split(",")[0].strip()
            if espec.startswith("-"):
                suf = int(espec[1:] or 0)
                if suf > 0:
                    inicio = max(0, size - suf)
            elif espec.endswith("-"):
                inicio = int(espec[:-1] or 0)
            else:
                a, b = espec.split("-", 1)
                inicio = int(a or 0)
                fin = int(b or (size - 1))
            inicio = max(0, min(inicio, size - 1))
            fin = max(inicio, min(fin, size - 1))
            if inicio != 0 or fin != size - 1:
                estado = 206
        except Exception:
            inicio, fin, estado = 0, size - 1, 200
    largo = fin - inicio + 1
    try:
        handler.send_response(estado)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Accept-Ranges", "bytes")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Cache-Control", "public, max-age=3600")
        if estado == 206:
            handler.send_header("Content-Range", "bytes %d-%d/%d" % (inicio, fin, size))
        handler.send_header("Content-Length", str(largo))
        handler.end_headers()
        if solo_headers:
            return
        with open(ruta, "rb") as f:
            f.seek(inicio)
            resto = largo
            while resto > 0:
                trozo = f.read(min(65536, resto))
                if not trozo:
                    break
                handler.wfile.write(trozo)
                resto -= len(trozo)
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self._atender(solo_headers=True)

    def do_GET(self):
        self._atender(solo_headers=False)

    def _enviar(self, body, ctype, solo_headers, cors=True):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if cors:
            self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not solo_headers:
            try:
                self.wfile.write(body)
            except Exception:
                pass

    def _atender(self, solo_headers=False):
        p = self.path
        if p.startswith("/sonido/ruleta"):
            _servir_mp3(self, _buscar_ruleta_juntos(), solo_headers=solo_headers)
        elif p.startswith("/state"):
            with lock:
                data = dict(state)
            self._enviar(json.dumps(data).encode("utf-8"), "application/json", solo_headers)
        elif p.startswith("/overlay"):
            try:
                with open(OVERLAY_FILE, "rb") as f:
                    body = f.read()
            except OSError:
                body = ("<meta charset='utf-8'><h3>Falta ruleta-obs-local.html junto a ruleta_control.py</h3>").encode("utf-8")
            self._enviar(body, "text/html; charset=utf-8", solo_headers)
        else:
            body = ('<meta charset="utf-8"><h2>Ruleta 2026 OK</h2>'
                    '<p>Overlay: <a href="/overlay">/overlay</a> | Estado: <a href="/state">/state</a></p>').encode("utf-8")
            self._enviar(body, "text/html; charset=utf-8", solo_headers, cors=False)


def iniciar_servidor():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ---------------- GUI Control ----------------
BG = "#0b0f1a"
CARD = "#141b2d"
CARD2 = "#1b2440"
TXT = "#e6ebf5"
MUTED = "#8a96b0"
RED = "#ef4444"
GREEN = "#22c55e"
YELLOW = "#facc15"
BLUE = "#38bdf8"


class App:
    def __init__(self, root):
        self.root = root
        root.title("Control Ruleta – Debate 2026")
        root.configure(bg=BG)
        # Tamaño chico por defecto y minimo muy bajo (ajustado a la escala de pantalla / DPI)
        try:
            f = max(1.0, root.winfo_fpixels("1i") / 96.0)
        except Exception:
            f = 1.0
        ancho = int(560 * f)
        alto = int(min(640 * f, max(300, root.winfo_screenheight() - 100)))
        root.geometry("%dx%d" % (ancho, alto))
        root.minsize(int(320 * f), int(200 * f))
        root.resizable(True, True)

        # Contenedor con scroll: todo el panel va dentro de self.body
        outer = tk.Frame(root, bg=BG)
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0, yscrollincrement=24)
        vsb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = body = tk.Frame(self.canvas, bg=BG)
        self._win = self.canvas.create_window((0, 0), window=body, anchor="nw")
        self._wraps = []     # (label, margen): se les ajusta el salto de linea al ancho de la ventana
        body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._al_cambiar_ancho)
        root.bind_all("<MouseWheel>", self._rueda_mouse)
        root.bind_all("<Button-4>", self._rueda_mouse)   # Linux
        root.bind_all("<Button-5>", self._rueda_mouse)

        self.var_pc = tk.BooleanVar(value=True)
        self.var_obs = tk.BooleanVar(value=True)
        self._nuevo_color = RULETA_COLORES[0]
        self._btns_paleta = []
        PX = 12   # margen lateral de las tarjetas (compacto)

        def wrap(lbl, margen):
            self._wraps.append((lbl, margen))
            return lbl

        # --- encabezado ---
        tk.Label(body, text="Control de la ruleta", bg=BG, fg=TXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=PX, pady=(10, 0))
        self.lbl_snd = wrap(tk.Label(body, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w", justify="left"), 2 * PX)
        self.lbl_snd.pack(fill="x", padx=PX)
        self.lbl_err = wrap(tk.Label(body, text="", bg=BG, fg="#f87171", font=("Segoe UI", 9, "bold"),
                                     anchor="w", justify="left"), 2 * PX)
        self.lbl_err.pack(fill="x", padx=PX)
        self._cfg_job = None

        # --- acciones principales ---
        acc = tk.Frame(body, bg=CARD); acc.pack(fill="x", padx=PX, pady=(8, 0))
        top = tk.Frame(acc, bg=CARD); top.pack(fill="x", padx=10, pady=(10, 2))
        self.btn_girar = tk.Button(top, text="GIRAR", bg=GREEN, fg="#04260f", activebackground="#4ade80",
                                   font=("Segoe UI", 16, "bold"), relief="flat", bd=0, padx=22, pady=6,
                                   cursor="hand2", command=self.girar)
        self.btn_girar.pack(side="left")
        self.btn_vis = tk.Button(top, text="Mostrar", bg=CARD2, fg=TXT, activebackground="#26325a",
                                 activeforeground=TXT, font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                                 padx=14, pady=8, cursor="hand2", command=self.toggle_vis)
        self.btn_vis.pack(side="left", padx=8)
        tk.Label(acc, text="Barra espaciadora = girar", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=10)

        self.lbl_result = tk.Label(acc, text="—", bg="#000000", fg="#ffffff",
                                   font=("Segoe UI", 20, "bold"), pady=6)
        self.lbl_result.pack(fill="x", padx=10, pady=(6, 6))
        self.status = wrap(tk.Label(acc, text="Listo. Tocá GIRAR.", bg=CARD, fg=MUTED,
                                    font=("Segoe UI", 10, "bold"), anchor="w", justify="left"), 2 * PX + 20)
        self.status.pack(fill="x", padx=10, pady=(0, 8))

        # --- titulo de arriba ---
        tit = tk.Frame(body, bg=CARD); tit.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(tit, text="Título de arriba (se ve en pantalla)", bg=CARD, fg=TXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        ft = tk.Frame(tit, bg=CARD); ft.pack(fill="x", padx=10)
        self.e_titulo = tk.Entry(ft, font=("Segoe UI", 11), width=8, bg="#070a12", fg=TXT,
                                 insertbackground=TXT, relief="flat")
        self.e_titulo.pack(side="left", fill="x", expand=True, ipady=5)
        with lock:
            self.e_titulo.insert(0, state.get("ruleta_titulo", ""))
        self.e_titulo.bind("<Return>", lambda e: self.aplicar_titulo())
        tk.Button(ft, text="Aplicar", bg=GREEN, fg="#04260f", relief="flat", bd=0, padx=12, pady=4,
                  font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.aplicar_titulo).pack(side="left", padx=(8, 0))
        tk.Button(ft, text="Borrar", bg=CARD2, fg=TXT, relief="flat", bd=0, padx=10, pady=4,
                  font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.borrar_titulo).pack(side="left", padx=(6, 0))
        wrap(tk.Label(tit, text="Ej: El más villero es…   El marco se ajusta solo al largo del texto. Enter = aplicar.",
                      bg=CARD, fg=MUTED, font=("Segoe UI", 9), anchor="w", justify="left"), 2 * PX + 20
             ).pack(fill="x", padx=10, pady=(4, 8))

        # --- sonido ---
        snd = tk.Frame(body, bg=CARD); snd.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(snd, text="Sonido", bg=CARD, fg=TXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        def mk_vol(texto, valor, cmd):
            sc = tk.Scale(snd, from_=0, to=100, orient="horizontal", label=texto, bg=CARD, fg=TXT,
                          troughcolor="#070a12", activebackground=BLUE, highlightthickness=0, bd=0,
                          sliderrelief="flat", font=("Segoe UI", 9, "bold"), showvalue=True)
            sc.set(valor)
            sc.config(command=cmd)          # el callback se conecta DESPUES de poner el valor inicial
            sc.pack(fill="x", padx=10, pady=(0, 2))
            return sc

        tk.Checkbutton(snd, text="Parlantes de la PC", variable=self.var_pc, bg=CARD, fg=TXT, selectcolor=CARD2,
                       activebackground=CARD, activeforeground=TXT, font=("Segoe UI", 10, "bold"),
                       highlightthickness=0, bd=0, anchor="w").pack(fill="x", padx=10)
        self.sc_pc = mk_vol("Volumen parlantes PC", CFG["vol_pc"], self._vol_pc)
        tk.Checkbutton(snd, text="Dentro de OBS (overlay)", variable=self.var_obs, command=self._sync_obs, bg=CARD, fg=TXT,
                       selectcolor=CARD2, activebackground=CARD, activeforeground=TXT, font=("Segoe UI", 10, "bold"),
                       highlightthickness=0, bd=0, anchor="w").pack(fill="x", padx=10)
        self.sc_obs = mk_vol("Volumen en OBS", CFG["vol_obs"], self._vol_obs)
        fs = tk.Frame(snd, bg=CARD); fs.pack(fill="x", padx=10, pady=(4, 10))
        tk.Button(fs, text="Probar sonido", bg=CARD2, fg=TXT, relief="flat", bd=0, padx=10, pady=4,
                  font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.probar).pack(side="left")
        tk.Button(fs, text="Silenciar", bg=RED, fg="white", relief="flat", bd=0, padx=10, pady=4,
                  font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.silenciar).pack(side="left", padx=8)

        # --- OBS ---
        url = "http://127.0.0.1:%d/overlay" % PORT
        obs = tk.Frame(body, bg=CARD); obs.pack(fill="x", padx=PX, pady=(8, 0))
        tk.Label(obs, text="OBS: fuente Navegador 1920×1080", bg=CARD, fg=TXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(obs, text=url, bg=CARD, fg="#93c5fd", font=("Consolas", 10), anchor="w").pack(fill="x", padx=10)
        fo = tk.Frame(obs, bg=CARD); fo.pack(fill="x", padx=10, pady=(4, 2))
        tk.Button(fo, text="Copiar", bg=BLUE, fg="#06263b", relief="flat", bd=0, padx=10, pady=3,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  command=lambda: (root.clipboard_clear(), root.clipboard_append(url), self.confirm("URL copiada"))
                  ).pack(side="left")
        tk.Button(fo, text="Abrir en navegador", bg=YELLOW, fg="#2b2200", relief="flat", bd=0, padx=10, pady=3,
                  font=("Segoe UI", 9, "bold"), cursor="hand2", command=self.abrir_overlay).pack(side="left", padx=8)
        wrap(tk.Label(obs, text="También sirve “Archivo local”: ruleta-obs-local.html (misma carpeta).",
                      bg=CARD, fg=MUTED, font=("Segoe UI", 9), anchor="w", justify="left"), 2 * PX + 20
             ).pack(fill="x", padx=10, pady=(0, 8))

        # --- sectores ---
        sec = tk.Frame(body, bg=CARD); sec.pack(fill="x", padx=PX, pady=(8, 12))
        tk.Label(sec, text="Sectores (se guardan solos)", bg=CARD, fg=TXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        self.fFilas = tk.Frame(sec, bg=CARD); self.fFilas.pack(fill="x", padx=10)
        fAdd = tk.Frame(sec, bg=CARD); fAdd.pack(fill="x", padx=10, pady=(8, 2))
        self.e_sector = tk.Entry(fAdd, font=("Segoe UI", 11), width=8, bg="#070a12", fg=TXT,
                                 insertbackground=TXT, relief="flat")
        self.e_sector.pack(side="left", fill="x", expand=True, ipady=5)
        self.e_sector.insert(0, "Nuevo sector...")
        self.e_sector.bind("<FocusIn>", lambda e: self.e_sector.get().startswith("Nuevo sector") and self.e_sector.delete(0, "end"))
        tk.Button(fAdd, text="Agregar", bg=BLUE, fg="#06263b", relief="flat", bd=0, padx=12, pady=4,
                  font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.agregar_sector).pack(side="left", padx=(8, 0))
        fCol = tk.Frame(sec, bg=CARD); fCol.pack(fill="x", padx=10, pady=(6, 10))
        self.fPaleta = tk.Frame(fCol, bg=CARD); self.fPaleta.pack(side="left")
        for c in RULETA_COLORES:
            b = tk.Button(self.fPaleta, text=" ", width=2, bg=c, activebackground=c, relief="flat", bd=0,
                          cursor="hand2", font=("Segoe UI", 8, "bold"), command=lambda c=c: self._sel_color(c))
            b.pack(side="left", padx=1)
            self._btns_paleta.append(b)
        tk.Button(fCol, text="Otro…", bg=CARD2, fg=TXT, relief="flat", bd=0, padx=8, pady=3,
                  font=("Segoe UI", 9, "bold"), cursor="hand2", command=self.elegir_color).pack(side="left", padx=6)
        self._marcar_paleta()
        self._dibujar_sectores()

        root.bind("<space>", self._tecla_espacio)
        self.actualizar_sonidos()
        self.refrescar()
        self._tick()
        # Abre el mp3 una vez al iniciar para que el primer giro tampoco tenga latencia.
        AUDIO.cargar(_buscar_ruleta_juntos())

    # ---- helpers de UI ----
    def _al_cambiar_ancho(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)
        for lbl, m in self._wraps:
            try:
                lbl.config(wraplength=max(120, e.width - m - 20))
            except Exception:
                pass

    def _rueda_mouse(self, e):
        # Scroll con la rueda del mouse (solo si el contenido es mas alto que la ventana)
        try:
            bb = self.canvas.bbox("all")
            if not bb or bb[3] <= self.canvas.winfo_height():
                return
            n = getattr(e, "num", None)
            d = -1 if n == 4 else (1 if n == 5 else (-1 if e.delta > 0 else 1))
            self.canvas.yview_scroll(d * 3, "units")
        except Exception:
            pass

    def _tecla_espacio(self, e):
        if isinstance(self.root.focus_get(), tk.Entry):
            return
        self.girar()

    def _tick(self):
        # Mantiene el boton y el estado al dia mientras gira.
        try:
            e = AUDIO.error
            self.lbl_err.config(text=("⚠ Sonido de la PC: " + e) if e else "")
        except Exception:
            pass
        try:
            g = girando()
            self.btn_girar.config(state="disabled" if g else "normal",
                                  bg="#2c3a55" if g else GREEN,
                                  text="GIRANDO…" if g else "GIRAR")
        except Exception:
            pass
        self.root.after(150, self._tick)

    def _sel_color(self, c):
        self._nuevo_color = c
        self._marcar_paleta()

    def elegir_color(self):
        r = colorchooser.askcolor(color=self._nuevo_color, title="Color del sector")
        if r and r[1]:
            self._nuevo_color = r[1].lower()
            self._marcar_paleta()

    def _marcar_paleta(self):
        for b in self._btns_paleta:
            on = (b.cget("bg") == self._nuevo_color)
            b.config(text="●" if on else " ",
                     fg="#111111" if b.cget("bg") in ("#f7f3ec", "#facc15") else "#ffffff")

    def _preservar_scroll(self, fn):
        # Redibujar la lista destruye y recrea las filas: sin esto el scroll saltaba al inicio.
        try:
            off = self.canvas.canvasy(0)
        except Exception:
            off = 0
        fn()
        try:
            self.root.update_idletasks()
            bb = self.canvas.bbox("all")
            self.canvas.configure(scrollregion=bb)
            if bb and bb[3] > 0:
                self.canvas.yview_moveto(max(0.0, min(1.0, off / float(bb[3]))))
        except Exception:
            pass

    def _dibujar_sectores(self):
        for w in self.fFilas.winfo_children():
            w.destroy()
        with lock:
            items = [list(x) for x in state.get("ruleta_items", [])]
        for i, (t, c) in enumerate(items):
            f = tk.Frame(self.fFilas, bg=CARD); f.pack(fill="x", pady=1)
            sw = tk.Label(f, text="  ", bg=c, cursor="hand2"); sw.pack(side="left", padx=(0, 6))
            sw.bind("<Button-1>", lambda e, i=i: self.cambiar_color(i))
            tk.Label(f, text="%d.  %s" % (i + 1, t), bg=CARD, fg=TXT, font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(side="left", fill="x", expand=True)
            for txt, cmd in (("▲", lambda i=i: self.mover_sector(i, -1)), ("▼", lambda i=i: self.mover_sector(i, 1)),
                             ("✕", lambda i=i: self.quitar_sector(i))):
                tk.Button(f, text=txt, bg="#7f1d1d" if txt == "✕" else CARD2, fg="white", relief="flat", bd=0,
                          width=3, font=("Segoe UI", 9, "bold"), cursor="hand2", command=cmd).pack(side="left", padx=2)

    def _guardar_y_refrescar(self, items, msg):
        with lock:
            state["ruleta_items"] = items
            # El resultado anterior ya no corresponde a estos sectores: se borra (el overlay
            # redibuja la rueda limpia, sin resaltado ni cartel viejo).
            state["ruleta_idx"] = -1
            state["ruleta_txt"] = ""
            state["ruleta_color"] = "#ff2a2a"
            state["rev"] += 1
        _guardar_items(items)
        self._preservar_scroll(self._dibujar_sectores)
        self.refrescar()
        self.confirm(msg)

    def aplicar_titulo(self):
        t = self.e_titulo.get().strip()[:60]
        with lock:
            state["ruleta_titulo"] = t
            state["rev"] += 1
        _guardar_titulo(t)
        self.confirm("Título actualizado: " + t if t else "Título borrado (se oculta)")

    def borrar_titulo(self):
        self.e_titulo.delete(0, "end")
        self.aplicar_titulo()

    def _bloqueado(self):
        if girando():
            self.confirm("Esperá a que termine el giro", ok=False)
            return True
        return False

    def agregar_sector(self):
        if self._bloqueado():
            return
        t = self.e_sector.get().strip()
        if not t or t.startswith("Nuevo sector"):
            self.confirm("Escribí el texto del sector", ok=False)
            return
        with lock:
            items = [list(x) for x in state.get("ruleta_items", [])]
        if len(items) >= 12:
            self.confirm("Máximo 12 sectores", ok=False)
            return
        items.append([t[:30], self._nuevo_color])
        self.e_sector.delete(0, "end")
        self._guardar_y_refrescar(items, "Sector agregado: " + t)
        self.e_sector.focus_set()          # para seguir cargando sectores seguidos

    def quitar_sector(self, i):
        if self._bloqueado():
            return
        with lock:
            items = [list(x) for x in state.get("ruleta_items", [])]
        if len(items) <= 2:
            self.confirm("Mínimo 2 sectores", ok=False)
            return
        sacado = items.pop(i)
        self._guardar_y_refrescar(items, "Quitado: " + sacado[0])

    def mover_sector(self, i, d):
        if self._bloqueado():
            return
        with lock:
            items = [list(x) for x in state.get("ruleta_items", [])]
        j = i + d
        if 0 <= j < len(items):
            items[i], items[j] = items[j], items[i]
            self._guardar_y_refrescar(items, "Sector movido")

    def cambiar_color(self, i):
        if self._bloqueado():
            return
        with lock:
            items = [list(x) for x in state.get("ruleta_items", [])]
        r = colorchooser.askcolor(color=items[i][1], title="Color de “%s”" % items[i][0])
        if r and r[1]:
            items[i][1] = r[1].lower()
            self._guardar_y_refrescar(items, "Color cambiado")

    def actualizar_sonidos(self):
        try:
            f = _buscar_ruleta_juntos()
            if os.path.exists(f):
                self.lbl_snd.config(text="Sonido: %s (%d KB, giro + win)" % (os.path.basename(f), os.path.getsize(f) // 1024), fg="#4ade80")
            else:
                self.lbl_snd.config(text="Sonido: falta un mp3 con “juntos” en el nombre dentro de “sonidos para programa de navegador”", fg="#f87171")
        except Exception:
            self.lbl_snd.config(text="Sonido: ?", fg=MUTED)

    def abrir_overlay(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:%d/overlay" % PORT)

    def confirm(self, msg, ok=True):
        self.status.config(text=("✓ " if ok else "⚠ ") + msg, fg="#052e16" if ok else "#450a0a",
                           bg=GREEN if ok else "#fca5a5")
        self.root.after(1800, lambda: self.status.config(bg=CARD, fg=MUTED))

    # ---- acciones ----
    def girar(self):
        if girando():
            return
        self.actualizar_sonidos()
        with lock:
            items = [list(x) for x in state.get("ruleta_items", [])] or [list(x) for x in RULETA_DEFAULT]
            idx = random.randrange(len(items))
            t0 = time.time() + LEAD
            state.update({
                "ruleta_idx": idx, "ruleta_txt": items[idx][0], "ruleta_color": items[idx][1],
                "ruleta_items": items, "ruleta_t0": t0,
                "ruleta_r1": random.random(), "ruleta_r2": random.random(), "ruleta_r3": random.random(),
                "ruleta_sonido_obs": bool(self.var_obs.get()),
                "ruleta_giro": state.get("ruleta_giro", 0) + 1,
                "ruleta_visible": True,
            })
            state["rev"] += 1
        if self.var_pc.get():
            AUDIO.reproducir(_buscar_ruleta_juntos(), t0)
        self.confirm("Girando… sale: " + items[idx][0])
        self.refrescar()

    def probar(self):
        self.actualizar_sonidos()
        ruta = _buscar_ruleta_juntos()
        hecho = []
        if self.var_pc.get():
            AUDIO.reproducir(ruta, time.time() + 0.05)
            hecho.append("parlantes de la PC")
        if self.var_obs.get():
            with lock:
                state["ruleta_sonido_obs"] = True
                state["ruleta_probar"] = state.get("ruleta_probar", 0) + 1
            hecho.append("OBS")
        if hecho:
            self.confirm("Probando en " + " y en ".join(hecho))
        else:
            self.confirm("Activá parlantes de la PC o OBS", ok=False)

    def _vol_pc(self, v):
        CFG["vol_pc"] = int(float(v))
        AUDIO.volumen(CFG["vol_pc"])          # se aplica en vivo, incluso mientras suena
        self._cfg_pendiente()

    def _vol_obs(self, v):
        CFG["vol_obs"] = int(float(v))
        with lock:
            state["ruleta_vol_obs"] = CFG["vol_obs"] / 100.0     # el overlay lo lee y lo aplica en vivo
        self._cfg_pendiente()

    def _cfg_pendiente(self):
        try:
            self.root.after_cancel(self._cfg_job)
        except Exception:
            pass
        self._cfg_job = self.root.after(500, lambda: _guardar_cfg(CFG))

    def _sync_obs(self):
        with lock:
            state["ruleta_sonido_obs"] = bool(self.var_obs.get())

    def toggle_vis(self):
        with lock:
            state["ruleta_visible"] = not state.get("ruleta_visible", False)
        self.refrescar()

    def silenciar(self):
        AUDIO.parar()
        with lock:
            state["ruleta_stop"] = state.get("ruleta_stop", 0) + 1
        self.confirm("Silenciado")

    def refrescar(self):
        with lock:
            s = dict(state)
        try:
            c = s.get("ruleta_color") or "#ff2a2a"
            txt = s.get("ruleta_txt") or "—"
            self.lbl_result.config(text=txt, fg=_fg_para(c) if s.get("ruleta_txt") else "#ffffff",
                                   bg=c if s.get("ruleta_txt") else "#000000")
            self.btn_vis.config(text="Ocultar" if s.get("ruleta_visible") else "Mostrar")
        except Exception:
            pass


def main():
    iniciar_servidor()
    print("Servidor ruleta en http://127.0.0.1:%d/overlay" % PORT)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
