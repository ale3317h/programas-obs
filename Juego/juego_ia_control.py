"""
JUEGO "¿ES IA O NO ES IA?" - Control para OBS (sin wifi, todo en 127.0.0.1:8766)
1) Ejecutá este archivo (python juego_ia_control.py)
2) OBS: Fuente > Navegador > "Archivo local" > juego-ia-obs-local.html (1920x1080)
3) Sonidos: poné en la carpeta "sonidos_ia" => redoble.mp3 / acierto.mp3 / error.mp3
"""
import ctypes, json, os, threading, tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8766
BASE = os.path.dirname(os.path.abspath(__file__))
SND = os.path.join(BASE, "sonidos_ia")
os.makedirs(SND, exist_ok=True)
LOCK = threading.Lock()
CFG_FILE = os.path.join(BASE, "juego_ia_config.json")
SONIDOS = ("redoble", "acierto", "error")
VOL = {n: {"pc": 70, "obs": 100} for n in SONIDOS}   # pc = parlantes de la PC, obs = overlay en OBS
CAL = {"mx": 0, "my": 0, "mw": 0, "mh": 0, "ty": 0}   # ajuste fino del marco y del titulo
try:
    _d = json.load(open(CFG_FILE))
    CAL.update({k: int(x) for k, x in _d.get("_cal", {}).items() if k in CAL})
    for n, v in _d.items():
        if n in VOL:
            VOL[n].update({k: int(v[k]) for k in ("pc", "obs") if k in v})
            if v.get("ruta"): VOL[n]["ruta"] = v["ruta"]
except Exception: pass
def guardar_cfg():
    try: json.dump({**VOL, "_cal": CAL}, open(CFG_FILE, "w"))
    except Exception: pass

_mci_lock = threading.RLock()
def play_local(nombre):
    """Suena por los parlantes de Windows con el volumen 'pc' de ese sonido."""
    ruta = sonido(nombre); vol = VOL[nombre]["pc"]
    if not ruta or vol <= 0: return
    def _run():
        try:
            m = ctypes.windll.winmm.mciSendStringW; al = "ia_" + nombre
            with _mci_lock:
                m("close " + al, None, 0, None)
                m('open "%s" type mpegvideo alias %s' % (ruta, al), None, 0, None)
                m("setaudio %s volume to %d" % (al, vol * 10), None, 0, None)
                m("play " + al, None, 0, None)
        except Exception: pass
    threading.Thread(target=_run, daemon=True).start()
ST = {"rev": 0, "visible": True, "titulo": "¿ES IA O NO ES IA?", "vmax": 3, "fase": "votando",
      "resp": None, "p_redoble": 0, "p_acierto": 0, "p_error": 0, "vol": VOL, "cal": CAL, "nivel": 0, "grupo": None,
      "jug": [{"n": f"Jugador {i+1}", "v": 3, "vo": None, "res": None} for i in range(4)]}

def bump():
    with LOCK: ST["rev"] += 1

CLAVES = {"redoble": ("redoble", "tambor", "drum"), "acierto": ("acierto", "correct", "bien", "win", "ok"),
          "error": ("error", "fail", "wrong", "mal", "incorrect")}
EXT = (".mp3", ".wav", ".ogg", ".m4a")
def sonido(nombre):
    """1) archivo elegido a mano  2) nombre exacto  3) cualquier archivo cuyo nombre contenga la palabra clave."""
    ruta = VOL[nombre].get("ruta")
    if ruta and os.path.exists(ruta): return ruta
    for e in EXT:
        r = os.path.join(SND, nombre + e)
        if os.path.exists(r): return r
    try:
        for fn in sorted(os.listdir(SND)):
            if fn.lower().endswith(EXT) and any(k in fn.lower() for k in CLAVES[nombre]): return os.path.join(SND, fn)
    except Exception: pass

def estado():
    with LOCK:
        d = json.loads(json.dumps(ST))
    if d["fase"] != "revelado": d["resp"] = None   # no filtra la respuesta antes de tiempo
    return d

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, ctype, body):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self): self._send(204, "text/plain", b"")
    def do_POST(self): self._send(200, "text/plain", b"ok")
    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/state": return self._send(200, "application/json", json.dumps(estado()).encode())
        if p.startswith("/sonido/"):
            r = sonido(p.split("/")[-1])
            if not r: return self._send(404, "text/plain", b"no")
            ct = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}.get(os.path.splitext(r)[1].lower(), "audio/mpeg")
            return self._send(200, ct, open(r, "rb").read())
        if p == "/overlay":
            f = os.path.join(BASE, "juego-ia-obs-local.html")
            return self._send(200, "text/html; charset=utf-8", open(f, "rb").read())
        self._send(404, "text/plain", b"no")

BG, PANEL, PANEL2, TXT, MUTED = "#0b1220", "#131d33", "#1b2842", "#f1f5f9", "#7f8ea8"
AZUL, VERDE, ROJO, AMBAR = "#2563eb", "#16a34a", "#dc2626", "#f59e0b"
FONT = "Segoe UI"

def btn(parent, text, cmd, bg=PANEL2, fg=TXT, size=11, bold=True, padx=14, pady=7):
    """Boton plano (Label) con hover: se ve igual en cualquier sistema."""
    l = tk.Label(parent, text=text, bg=bg, fg=fg, font=(FONT, size, "bold" if bold else "normal"),
                 padx=padx, pady=pady, cursor="hand2")
    l._bg = bg
    def sel(c): l._bg = c; l.config(bg=c)
    l.set = lambda bg=None, fg=None, text=None: (sel(bg) if bg else None, l.config(fg=fg) if fg else None, l.config(text=text) if text else None)
    def enter(e):
        h = l._bg.lstrip("#"); r, g, b = (int(h[k:k+2], 16) for k in (0, 2, 4))
        l.config(bg="#%02x%02x%02x" % tuple(min(255, int(v * 1.18) + 8) for v in (r, g, b)))
    l.bind("<Enter>", enter); l.bind("<Leave>", lambda e: l.config(bg=l._bg))
    l.bind("<Button-1>", lambda e: cmd())
    return l

def panel(parent, titulo):
    o = tk.Frame(parent, bg=PANEL); o.pack(fill="x", padx=14, pady=(0, 10))
    tk.Label(o, text=titulo.upper(), bg=PANEL, fg="#38bdf8", font=(FONT, 9, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
    c = tk.Frame(o, bg=PANEL); c.pack(fill="x", padx=12, pady=(0, 10))
    return c

def entry(parent, width, size=12):
    return tk.Entry(parent, width=width, font=(FONT, size), bg=BG, fg=TXT, insertbackground="white",
                    relief="flat", highlightthickness=1, highlightbackground="#2b3b5c", highlightcolor="#38bdf8")

NIVELES = [("Fácil", "#22c55e"), ("Medio", "#f97316"), ("Difícil", "#ef4444"), ("Muy difícil", "#ef4444"), ("Extremo", "#ef4444")]

class App:
    def __init__(self, root):
        self.root = root; self._modo = None
        root.title("¿Es IA o no es IA? - Control"); root.configure(bg=BG)
        root.resizable(True, True); root.minsize(520, 420); root.geometry("820x880")
        outer = tk.Frame(root, bg=BG); outer.pack(fill="both", expand=True)
        sb = tk.Scrollbar(outer, orient="vertical"); sb.pack(side="right", fill="y")
        self.cv = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollcommand=sb.set, yscrollincrement=30)
        self.cv.pack(side="left", fill="both", expand=True); sb.config(command=self.cv.yview)
        body = tk.Frame(self.cv, bg=BG); self.win = self.cv.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", self.on_resize)
        root.bind_all("<MouseWheel>", lambda e: self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        root.bind_all("<Button-4>", lambda e: self.cv.yview_scroll(-1, "units"))
        root.bind_all("<Button-5>", lambda e: self.cv.yview_scroll(1, "units"))
        # Cabecera
        h = tk.Frame(body, bg=BG); h.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(h, text="¿ES IA O NO ES IA?", bg=BG, fg=TXT, font=(FONT, 17, "bold")).pack(side="left")
        self.vis = btn(h, "OVERLAY VISIBLE", self.toggle_vis, VERDE, size=9, pady=5); self.vis.pack(side="right")
        self.fase_l = tk.Label(h, text="", font=(FONT, 10, "bold"), padx=12, pady=5); self.fase_l.pack(side="right", padx=8)

        # Ajustes
        c = panel(body, "Ajustes")
        tk.Label(c, text="Título", bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(anchor="w")
        self.tit = entry(c, 10); self.tit.insert(0, ST["titulo"]); self.tit.pack(fill="x", ipady=4, pady=(2, 8))
        self.tit.bind("<KeyRelease>", lambda e: self.set("titulo", self.tit.get()))
        r2 = tk.Frame(c, bg=PANEL); r2.pack(fill="x")
        tk.Label(r2, text="Vidas", bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(side="left")
        self.vmax = tk.Spinbox(r2, from_=1, to=9, width=3, font=(FONT, 12), bg=BG, fg=TXT, buttonbackground=PANEL2, relief="flat", insertbackground="white")
        self.vmax.delete(0, "end"); self.vmax.insert(0, 3); self.vmax.pack(side="left", padx=6, ipady=3)
        btn(r2, "Aplicar a todos", self.aplicar_vidas, size=9, pady=5).pack(side="left", padx=(0, 20))
        tk.Label(r2, text="Redoble (seg)", bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(side="left")
        self.dur = tk.Spinbox(r2, from_=1, to=30, increment=0.5, width=4, font=(FONT, 12), bg=BG, fg=TXT, buttonbackground=PANEL2, relief="flat", insertbackground="white")
        self.dur.delete(0, "end"); self.dur.insert(0, 4.6); self.dur.pack(side="left", padx=6, ipady=3)

        # Cada video
        c = panel(body, "Cada video")
        tk.Label(c, text="Nivel del video  (verde / naranja / rojo titilando)", bg=PANEL, fg=TXT, font=(FONT, 11, "bold")).pack(anchor="w")
        nr = tk.Frame(c, bg=PANEL); nr.pack(anchor="w", pady=(4, 12)); self.nbs = []
        for i, (t, col) in enumerate(NIVELES):
            b = btn(nr, t, lambda i=i: self.set("nivel", i), PANEL2, size=10, padx=11, pady=6); b.pack(side="left", padx=(0, 6)); self.nbs.append(b)
        st = tk.Frame(c, bg=PANEL); st.pack(fill="x"); self.groups = []
        for k in range(3):
            g = tk.Frame(st, bg=PANEL); self.groups.append(g)
        tk.Label(self.groups[0], text="1  El video es...", bg=PANEL, fg=TXT, font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 6))
        r1 = tk.Frame(self.groups[0], bg=PANEL); r1.pack(anchor="w")
        self.bia = btn(r1, "ES IA", lambda: self.resp("ia"), size=13, padx=28, pady=10); self.bia.pack(side="left", padx=(0, 8))
        self.bno = btn(r1, "NO ES IA", lambda: self.resp("no"), size=13, padx=22, pady=10); self.bno.pack(side="left")
        tk.Label(self.groups[1], text="2  Revelar", bg=PANEL, fg=TXT, font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 6))
        self.brev = btn(self.groups[1], "REVELAR", self.revelar, AMBAR, "#111", size=14, padx=26, pady=10); self.brev.pack(anchor="w")
        tk.Label(self.groups[2], text="3  Siguiente", bg=PANEL, fg=TXT, font=(FONT, 11, "bold")).pack(anchor="w", pady=(0, 6))
        self.bsig = btn(self.groups[2], "Siguiente video  >", self.siguiente, AZUL, "white", size=13, padx=22, pady=10); self.bsig.pack(anchor="w")
        self.hint = tk.Label(c, text="", bg=PANEL, fg=AMBAR, font=(FONT, 10)); self.hint.pack(anchor="w", pady=(8, 0))

        # Jugadores (2 columnas si hay lugar, 1 si la ventana es angosta)
        c = panel(body, "Jugadores")
        c.columnconfigure(0, weight=1, uniform="p"); c.columnconfigure(1, weight=1, uniform="p")
        self.cards, self.cframes = [], []
        pos = ["Arriba izquierda", "Abajo izquierda", "Arriba derecha", "Abajo derecha"]
        for i in range(4):
            cf = tk.Frame(c, bg=PANEL2, highlightthickness=2, highlightbackground=PANEL2); self.cframes.append(cf)
            top = tk.Frame(cf, bg=PANEL2); top.pack(fill="x", padx=10, pady=(8, 2))
            tk.Label(top, text=f"CÁMARA {i+1} · {pos[i]}", bg=PANEL2, fg=MUTED, font=(FONT, 8, "bold")).pack(side="left")
            res = tk.Label(top, text="", bg=PANEL2, font=(FONT, 9, "bold")); res.pack(side="right")
            e = entry(cf, 10, 13); e.insert(0, ST["jug"][i]["n"]); e.pack(fill="x", padx=10, ipady=4)
            e.bind("<KeyRelease>", lambda ev, i=i: self.setj(i, "n", self.cards[i]["e"].get()))
            vr = tk.Frame(cf, bg=PANEL2); vr.pack(fill="x", padx=10, pady=8)
            hearts = tk.Frame(vr, bg=PANEL2); hearts.pack(side="left")
            btn(vr, "+", lambda i=i: self.vida(i, 1), BG, size=11, padx=9, pady=1).pack(side="right")
            btn(vr, "-", lambda i=i: self.vida(i, -1), BG, size=11, padx=9, pady=1).pack(side="right", padx=4)
            vb = tk.Frame(cf, bg=PANEL2); vb.pack(fill="x", padx=10, pady=(0, 10)); bs = {}
            for k, t in (("ia", "Es IA"), ("no", "No es IA"), (None, "Sin voto")):
                b = btn(vb, t, lambda i=i, k=k: self.voto(i, k), BG, size=10, padx=10, pady=6); b.pack(side="left", padx=(0, 5)); bs[k] = b
            self.cards.append({"f": cf, "e": e, "res": res, "hearts": hearts, "bs": bs})

        # Sonidos y volumenes
        c = panel(body, "Sonidos y volumen  (carpeta sonidos_ia)")
        c.columnconfigure(3, weight=1); c.columnconfigure(4, weight=1)
        for col, t in ((3, "PARLANTES PC"), (4, "OBS")):
            tk.Label(c, text=t, bg=PANEL, fg=MUTED, font=(FONT, 8, "bold")).grid(row=0, column=col, sticky="w", padx=8)
        self.sdots = {}
        for r_, n in enumerate(SONIDOS, 1):
            d = tk.Label(c, text="●", bg=PANEL, font=(FONT, 12)); d.grid(row=r_, column=0, pady=3); self.sdots[n] = d
            tk.Label(c, text=n.capitalize(), bg=PANEL, fg=TXT, font=(FONT, 11, "bold"), width=8, anchor="w").grid(row=r_, column=1)
            bf = tk.Frame(c, bg=PANEL); bf.grid(row=r_, column=2, padx=6)
            btn(bf, "Probar", lambda n=n: self.disparar(n), PANEL2, size=10, pady=3, padx=8).pack(side="left")
            btn(bf, "Elegir...", lambda n=n: self.elegir(n), PANEL2, size=10, pady=3, padx=8).pack(side="left", padx=(4, 0))
            for col, k in ((3, "pc"), (4, "obs")):
                sc = tk.Scale(c, from_=0, to=100, orient="horizontal", length=100, bg=PANEL, fg=TXT, troughcolor=BG,
                              highlightthickness=0, bd=0, activebackground="#38bdf8", font=(FONT, 9),
                              command=lambda v, n=n, k=k: self.volumen(n, k, v))
                sc.set(VOL[n][k]); sc.grid(row=r_, column=col, padx=8, sticky="ew")
        self.info = tk.Label(c, text="", bg=PANEL, fg=MUTED, font=(FONT, 8), justify="left", wraplength=700)
        self.info.grid(row=4, column=0, columnspan=5, sticky="w", pady=(6, 0))

        # Ajuste fino del overlay
        c = panel(body, "Ajuste fino del overlay  (si el marco no calza con la pantalla del medio)")
        c.columnconfigure(1, weight=1); self.cscales = {}
        for r_, (k, t) in enumerate((("mx", "Marco X"), ("my", "Marco Y"), ("mw", "Marco ancho"), ("mh", "Marco alto"), ("ty", "Título Y"))):
            tk.Label(c, text=t, bg=PANEL, fg=TXT, font=(FONT, 10), width=11, anchor="w").grid(row=r_, column=0)
            sc = tk.Scale(c, from_=-80, to=80, orient="horizontal", bg=PANEL, fg=TXT, troughcolor=BG, highlightthickness=0, bd=0,
                          activebackground="#38bdf8", font=(FONT, 9), command=lambda v, k=k: self.calib(k, v))
            sc.set(CAL[k]); sc.grid(row=r_, column=1, sticky="ew", padx=8); self.cscales[k] = sc
        btn(c, "Reiniciar ajuste", self.calib_reset, PANEL2, size=9, pady=4).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.refrescar()

    def on_resize(self, e):
        self.cv.itemconfigure(self.win, width=e.width); self.reflow(e.width)
    def reflow(self, w):
        modo = (w >= 740, w >= 640)
        if modo == self._modo: return
        self._modo = modo; dos, ancho = modo
        for i, cf in enumerate(self.cframes):
            cf.grid(row=(i % 2 if dos else i), column=(i // 2 if dos else 0), padx=((0, 10) if (dos and i < 2) else 0), pady=(0, 10), sticky="nsew")
        for k, g in enumerate(self.groups):
            g.grid(row=(0 if ancho else k), column=(k if ancho else 0), sticky="w", padx=((0, 24) if ancho else 0), pady=(0, 0) if ancho else (0, 10))
    def calib(self, k, v):
        CAL[k] = int(float(v)); guardar_cfg(); bump()
    def calib_reset(self):
        for sc in self.cscales.values(): sc.set(0)

    def elegir(self, n):
        p = filedialog.askopenfilename(title="Archivo para " + n, initialdir=SND, filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a")])
        if p: VOL[n]["ruta"] = p; guardar_cfg(); self.refrescar()
    def volumen(self, n, k, v):
        VOL[n][k] = int(float(v)); guardar_cfg(); bump()
    def disparar(self, n):
        with LOCK: ST["p_" + n] += 1
        bump(); play_local(n)
    def set(self, k, v):
        with LOCK: ST[k] = v
        bump(); self.refrescar()
    def setj(self, i, k, v):
        with LOCK: ST["jug"][i][k] = v
        bump()
    def aplicar_vidas(self):
        n = int(self.vmax.get())
        with LOCK:
            ST["vmax"] = n
            for j in ST["jug"]: j["v"] = n
        bump(); self.refrescar()
    def vida(self, i, d):
        with LOCK: ST["jug"][i]["v"] = max(0, min(ST["vmax"], ST["jug"][i]["v"] + d))
        bump(); self.refrescar()
    def voto(self, i, v):
        if ST["fase"] == "revelado": return
        self.setj(i, "vo", v); self.refrescar()
    def resp(self, r):
        if ST["fase"] == "revelado": return
        self.set("resp", r)
    def toggle_vis(self):
        self.set("visible", not ST["visible"])
    def revelar(self):
        if ST["resp"] is None: self.hint.config(text="Primero elegí si el video ES IA o NO ES IA (paso 1)."); return
        if ST["fase"] != "votando": return
        with LOCK: ST["fase"] = "redoble"
        bump(); self.disparar("redoble"); self.refrescar(); self.root.after(int(float(self.dur.get()) * 1000), self.finalizar)
    def finalizar(self):
        nc = nw = 0
        with LOCK:
            ST["fase"] = "revelado"
            for j in ST["jug"]:
                if j["vo"] is None: continue
                if j["vo"] == ST["resp"]: j["res"] = "ok"; nc += 1
                else: j["res"] = "mal"; nw += 1; j["v"] = max(0, j["v"] - 1)
            ST["grupo"] = None if not (nc + nw) else ("ok" if nc > nw else "mal")   # empate = mal
        bump(); self.refrescar()
        # Suena UN solo sonido: gana la mayoria. Empate = error (igual que el color rojo). Sin votos = nada.
        if nc + nw: self.disparar("acierto" if nc > nw else "error")
    def siguiente(self):
        with LOCK:
            ST["fase"] = "votando"; ST["resp"] = None; ST["grupo"] = None
            for j in ST["jug"]: j["vo"] = None; j["res"] = None
        bump(); self.refrescar()

    def refrescar(self):
        fase = ST["fase"]
        col = {"votando": ("VOTANDO", AZUL), "redoble": ("REVELANDO...", AMBAR), "revelado": ("REVELADO", VERDE)}[fase]
        self.fase_l.config(text=col[0], bg=col[1], fg="#111" if fase == "redoble" else "white")
        self.vis.set(VERDE if ST["visible"] else "#6b7280", text="OVERLAY VISIBLE" if ST["visible"] else "OVERLAY OCULTO")
        for i, b in enumerate(self.nbs): b.set(NIVELES[i][1] if ST["nivel"] == i else PANEL2, "white")
        self.bia.set(VERDE if ST["resp"] == "ia" else PANEL2, "white")
        self.bno.set(ROJO if ST["resp"] == "no" else PANEL2, "white")
        self.brev.set(AMBAR if fase == "votando" else "#4b5563", "#111" if fase == "votando" else "#cbd5e1",
                      "REVELAR" if fase == "votando" else ("Revelando..." if fase == "redoble" else "Ya revelado"))
        self.bsig.set(AZUL if fase == "revelado" else PANEL2, "white")
        if ST["resp"] is not None or fase != "votando": self.hint.config(text="")
        for i, c in enumerate(self.cards):
            j = ST["jug"][i]
            c["f"].config(highlightbackground={"ok": VERDE, "mal": ROJO}.get(j["res"], PANEL2))
            c["res"].config(text={"ok": "ACERTÓ", "mal": "FALLÓ  -1 vida"}.get(j["res"], ""), fg=VERDE if j["res"] == "ok" else "#f87171")
            for w in c["hearts"].winfo_children(): w.destroy()
            for k in range(ST["vmax"]):
                tk.Label(c["hearts"], text="♥", font=(FONT, 18), bg=PANEL2, fg="#ff3b5c" if k < j["v"] else "#3b475f").pack(side="left")
            for k, b in c["bs"].items():
                on = j["vo"] == k and k is not None
                b.set((AZUL if on else BG), "white" if on else "#9fb0cc")
        for n, d in self.sdots.items(): d.config(fg="#22c55e" if sonido(n) else "#ef4444")
        self.info.config(text="  |  ".join(f"{n}: {os.path.basename(sonido(n)) if sonido(n) else 'NO ENCONTRADO'}" for n in SONIDOS))

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    r = tk.Tk(); App(r); r.mainloop()
