"""
PREGUNTAS + COMODINES - Control para OBS (sin wifi, todo en 127.0.0.1:8769)        [motor v2 - contrato v2]

1) Ejecuta este archivo:  python preguntas_control.py
2) OBS: Fuente > Navegador > "Archivo local" > preguntas-obs-local.html  (1920x1080, posicion 0,0)
   Orden de capas (abajo -> arriba): fondo (fondo_referencia.jpg o tu video), las 3 camaras, y ESTE overlay.
   Tildar "Controlar el audio mediante OBS".
3) Las preguntas viven en  preguntas_banco.json  (banco v2: rondas -> preguntas + reservas; la ronda por temas trae "temas").
   Editalo con el Bloc de notas y apreta "Recargar banco" en el programa. Si hay un error, el programa dice cual y
   conserva el banco anterior.  Esquema completo: CONTRATO.md.
4) Sonidos en la carpeta "sonidos", tarjetas en "tarjetas" (tarjetas/{chicos|chicas}_{llamada|saltar|cambiar|5050}_{activa|apagada}.png).
   Usa el puerto 8769 (Debate 8765, Ruleta 8766, Comodines viejo 8767, Juego 8768): puede estar abierto a la vez que todos.

Novedades v3: redoble antes de revelar; DOBLE O NADA en lugar de Saltar (acierto +3 / error -1); rondas "responden": "ambos"
(resultado de cada equipo por separado); Matematicas por aproximacion (gana el mas cercano); rondas "sin_tiempo"; se puede
devolver la LLAMADA si no funciono; preguntas con "seg" propio.
Rebote: en la ronda de Capciosas (r4) y en la muerte subita (ronda final), si el equipo que responde FALLA, la misma pregunta
pasa al otro equipo con el reloj de nuevo (sin revelar); si fallan los dos, se revela y no suma nadie. En la final (sigue_si_acierta)
el que acierta sigue respondiendo y, si fallan los dos, la siguiente pregunta la empieza otra vez el que empezo (el que va perdiendo).
En r4, si el primero falla y el otro acierta, se lleva el punto; al terminar, la siguiente arranca por turnos.
Toda revelacion pasa antes por el redoble, salvo la muerte subita (ronda final), que revela directo sin tambores.

Flujo en vivo:  elegir RONDA (en la ronda por temas: cada equipo elige su tema) -> indicar quien empieza (Chicos / Chicas)
                -> Siguiente pregunta -> Mostrar opciones -> Iniciar tiempo -> [Elegir la respuesta del equipo]
                -> Revelar -> (acierto/error se marca solo si elegiste; si no, con los botones) -> Siguiente.
Comodines (teclas 1-4 chicos, 5-8 chicas), 1 por pregunta y solo los que valen en la ronda:
   50/50 saca dos opciones incorrectas, DOBLE O NADA (clave "saltar") si acierta suma 3 y si falla resta 1, CAMBIAR usa una reserva,
   LLAMADA arranca 30 s y despues vuelve el reloj de la pregunta. Si no se puede aplicar NO se gasta y se avisa el motivo.
"""
import ctypes, json, math, os, random, re, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError:           # solo para poder probar el motor sin pantalla
    tk = filedialog = messagebox = None

PORT = 8769
BASE = os.path.dirname(os.path.abspath(__file__))
SND = os.path.join(BASE, "sonidos")
IMG = os.path.join(BASE, "tarjetas")
FOTOS = os.path.join(BASE, "fotos")          # fotos de los temas: tema_minecraft.jpg, tema_cultura.jpg, tema_cine.jpg (opcional)
OVERLAYS = {"/reglas": "overlay-reglas.html", "/comodines": "overlay-comodines.html", "/categorias": "overlay-categorias.html"}   # una escena de OBS cada uno
BANCO_FILE = os.path.join(BASE, "preguntas_banco.json")
CFG_FILE = os.path.join(BASE, "preguntas_config.json")
CFG_VERSION = 4
LOCK = threading.RLock()

EQUIPOS = (("chicos", "CHICOS", "#1E5BFF"), ("chicas", "CHICAS", "#E6007E"))
COMODINES = (("llamada", "LLAMADA A UN AMIGO"), ("saltar", "DOBLE O NADA"), ("cambiar", "CAMBIAR PREGUNTA"), ("5050", "50/50"))
SONIDOS = ("usar", "reactivar", "inicio", "campana", "tictac", "acierto", "error", "redoble")
EXT = (".mp3", ".wav", ".ogg", ".m4a")
CLAVES = {"usar": ("usar", "used"), "reactivar": ("reactiv", "reset"), "inicio": ("inicio",), "campana": ("campana", "bell"),
          "tictac": ("tic",), "acierto": ("correct", "acierto"), "error": ("error", "buzzer"), "redoble": ("redoble", "drum", "tambor", "rufando")}
LLAMADA_SEG = 30      # duracion de la llamada a un amigo
REDOBLE_COLA = 0.3    # pausa extra despues de que termina el redoble, antes de mostrar la respuesta
REDOBLE_SIN_DURACION = 3.0   # si no se puede medir el audio (ogg, m4a...) se espera esto
DOBLE_ACIERTO = 3     # DOBLE O NADA (clave "saltar" en /state): si el equipo acierta suma 3 ...
DOBLE_ERROR = 1       # ... y si falla resta 1 (el marcador no baja de 0)
MAX_Q, MAX_R, MAX_OPC, MAX_NOMBRE = 90, 36, 28, 24     # largos recomendados (solo avisa: para que entren en el overlay)
TIC_DESDE = 10        # el tic-tac suena en los ultimos N segundos
CAL_DEF = {"size": 150, "dy": 0, "chicos_dx": 0, "chicas_dx": 0, "pan_dy": 0, "pan_h": 280, "guia": 0}
CAL_RANGO = {"size": (90, 220), "dy": (-80, 80), "chicos_dx": (-150, 150), "chicas_dx": (-150, 150), "pan_dy": (-60, 60), "pan_h": (200, 300), "guia": (0, 1)}
ESTADOS = ("hecha", "saltada", "cambiada", "usada")
NOMBRE_COM = dict(COMODINES)
CLAVES_COM = tuple(k for k, _ in COMODINES)
NOMBRES_TARJETAS = ["%s_%s_%s.png" % (e, k, v) for e, _, _ in EQUIPOS for k, _ in COMODINES for v in ("activa", "apagada")]
HEX = re.compile(r"#[0-9a-fA-F]{6}")
os.makedirs(SND, exist_ok=True)


def otro(eq): return "chicas" if eq == "chicos" else "chicos"

def _num(txt):
    """'1.234,5' / '1234.5' / 'x = 8' -> float, o None si no hay numero (formato argentino: punto de miles, coma decimal)."""
    if isinstance(txt, (int, float)) and not isinstance(txt, bool): return float(txt)
    m = re.search(r"-?\d[\d.,]*", str(txt or "").replace(" ", "").replace("\u2212", "-"))
    if not m: return None
    t = m.group(0).rstrip(".,")
    if "," in t and "." in t: t = t.replace(".", "").replace(",", ".")
    elif "," in t: t = t.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t): t = t.replace(".", "")           # "10.080" -> 10080
    try: return float(t)
    except ValueError: return None
def _fmt(v): return "%.10g" % v


# ============================ sonido en los parlantes de la PC ============================
# Todos los sonidos salen por el MISMO dispositivo MCI ("mpegvideo", con
# alternativa sin tipo si falla): asi Windows los rutea al mismo endpoint.
# Antes los .wav se abrian con "waveaudio" y los .mp3 con "mpegvideo" y el
# redoble (redoble.wav) terminaba en otro dispositivo/salida (audiodg).
_mci_lock = threading.RLock()
def _mci(cmd):
    try:
        with _mci_lock:
            ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    except Exception:
        pass

def _mci_err(cmd):
    """Como _mci pero devuelve el codigo de error (0 = ok)."""
    try:
        with _mci_lock:
            return ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    except Exception:
        return -1

def _abrir_mismo_dispositivo(ruta, alias):
    """Abre SIEMPRE por el mismo dispositivo que el resto de los sonidos."""
    _mci("close " + alias)
    if _mci_err('open "%s" type mpegvideo alias %s' % (ruta, alias)) == 0:
        return
    _mci('open "%s" alias %s' % (ruta, alias))

def play_local(ruta, vol, alias):
    """Suena por los parlantes de Windows (sin bloquear la ventana). vol 0-100."""
    if not ruta or vol <= 0: return
    def _run():
        _abrir_mismo_dispositivo(ruta, alias)
        _mci("setaudio %s volume to %d" % (alias, vol * 10))
        _mci("play " + alias)
    threading.Thread(target=_run, daemon=True).start()

_DUR = {}
_BR1 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)      # MPEG1 capa III (kbps)
_BR2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)          # MPEG2 / 2.5 capa III
_SRATE = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}
def _dur_mp3(ruta):
    with open(ruta, "rb") as f: d = f.read()
    n = len(d); pos = 0
    if d[:3] == b"ID3" and n >= 10: pos = 10 + ((d[6] & 0x7f) << 21 | (d[7] & 0x7f) << 14 | (d[8] & 0x7f) << 7 | (d[9] & 0x7f))
    while pos + 4 <= n:
        if d[pos] == 0xFF and (d[pos + 1] & 0xE0) == 0xE0:
            ver, layer = (d[pos + 1] >> 3) & 3, (d[pos + 1] >> 1) & 3
            bi, si = d[pos + 2] >> 4, (d[pos + 2] >> 2) & 3
            if ver != 1 and layer == 1 and 0 < bi < 15 and si < 3:
                mpeg1 = ver == 3; br = (_BR1 if mpeg1 else _BR2)[bi] * 1000; sr = _SRATE[ver][si]
                mono = (d[pos + 3] >> 6) & 3 == 3
                off = pos + 4 + ((17 if mono else 32) if mpeg1 else (9 if mono else 17))
                if d[off:off + 4] in (b"Xing", b"Info") and int.from_bytes(d[off + 4:off + 8], "big") & 1:      # VBR: cantidad de frames
                    return int.from_bytes(d[off + 8:off + 12], "big") * (1152 if mpeg1 else 576) / float(sr)
                audio = n - pos - (128 if d[-128:-125] == b"TAG" else 0)                                     # CBR: bytes / bitrate
                return audio * 8.0 / br
        pos += 1
    return 0.0
def _dur_mci(ruta):
    try:
        buf = ctypes.create_unicode_buffer(64); w = ctypes.windll.winmm
        with _mci_lock:
            w.mciSendStringW("close pq_dur", None, 0, None)
            if w.mciSendStringW('open "%s" type mpegvideo alias pq_dur' % ruta, None, 0, None):
                if w.mciSendStringW('open "%s" alias pq_dur' % ruta, None, 0, None): return 0.0
            w.mciSendStringW("set pq_dur time format milliseconds", None, 0, None)
            w.mciSendStringW("status pq_dur length", buf, 64, None); w.mciSendStringW("close pq_dur", None, 0, None)
        return int(buf.value) / 1000.0
    except Exception: return 0.0
def duracion_sonido(ruta):
    """Segundos que dura el audio (0.0 si no se puede saber). Se mide una vez por archivo."""
    try: key = (ruta, os.path.getmtime(ruta))
    except Exception: return 0.0
    if key not in _DUR:
        d = 0.0
        try:
            if ruta.lower().endswith(".wav"):
                import wave
                with wave.open(ruta) as w: d = w.getnframes() / float(w.getframerate())
            elif ruta.lower().endswith(".mp3"): d = _dur_mp3(ruta)
        except Exception: d = 0.0
        _DUR[key] = d if d > 0 else _dur_mci(ruta)
    return _DUR[key]

_tic_sonando = False
def tic_local(debe, ruta, vol):
    """Arranca / corta el tic-tac en bucle por los parlantes."""
    global _tic_sonando
    if debe and vol > 0 and ruta and not _tic_sonando:
        _tic_sonando = True
        _abrir_mismo_dispositivo(ruta, "pq_tic")
        _mci("setaudio pq_tic volume to %d" % (vol * 10)); _mci("play pq_tic repeat")
    elif _tic_sonando and not (debe and vol > 0 and ruta):
        _tic_sonando = False
        _mci("stop pq_tic"); _mci("close pq_tic")


# ============================ banco de preguntas (v2) ============================
def tarjetas_faltantes():
    """Nombres de las 16 tarjetas que no estan en la carpeta tarjetas (diagnostico de 'no se ven los comodines')."""
    return [n for n in NOMBRES_TARJETAS if not os.path.isfile(os.path.join(IMG, n))]

def _preg(p, tipo, rid, ctx, avisos):
    """Devuelve la pregunta limpia, o None (con un aviso) si no sirve."""
    if not isinstance(p, dict): avisos.append("%s: no es un objeto" % ctx); return None
    q = p.get("q")
    if not isinstance(q, str) or not q.strip(): avisos.append("%s: falta el texto \"q\"" % ctx); return None
    out = {"id": str(p.get("id") or "").strip(), "q": q.strip()}
    if tipo == "opciones":
        o = p.get("o")
        if not isinstance(o, list) or len(o) != 4: avisos.append("%s: \"o\" tiene que tener 4 opciones" % ctx); return None
        o = [str(x).strip() for x in o]
        if any(not x for x in o): avisos.append("%s: hay una opcion vacia" % ctx); return None
        c = p.get("c")
        if isinstance(c, bool) or not isinstance(c, int) or not 0 <= c < 4: avisos.append("%s: \"c\" (la correcta) tiene que ser un numero de 0 a 3" % ctx); return None
        out["o"] = o; out["c"] = c
    else:
        r = p.get("r")
        if not isinstance(r, str) or not r.strip(): avisos.append("%s: falta la respuesta \"r\"" % ctx); return None
        out["r"] = r.strip()
        if "o" in p: avisos.append("%s: es abierta y trae \"o\" (se ignoran las opciones)" % ctx)
    if isinstance(p.get("nota"), str) and p["nota"].strip(): out["nota"] = p["nota"].strip()
    if isinstance(p.get("especial"), str) and p["especial"].strip(): out["especial"] = p["especial"].strip()
    sq = p.get("seg")                                    # segundos propios de esta pregunta (si no, los de la ronda)
    if sq is not None:
        if isinstance(sq, int) and not isinstance(sq, bool) and 5 <= sq <= 600: out["seg"] = sq
        else: avisos.append("%s: \"seg\" tiene que ser un numero entero (5 a 600): se usa el de la ronda" % ctx)
    nm = p.get("num")                                    # respuesta numerica (rondas por aproximacion)
    if nm is not None:
        if isinstance(nm, (int, float)) and not isinstance(nm, bool): out["num"] = nm
        else: avisos.append("%s: \"num\" tiene que ser un numero (se ignora)" % ctx)
    if len(out["q"]) > MAX_Q: avisos.append("%s: pregunta muy larga (%d caracteres, recomendado %d): acortala para que entre en pantalla" % (ctx, len(out["q"]), MAX_Q))
    if "r" in out and len(out["r"]) > MAX_R: avisos.append("%s: respuesta muy larga (%d caracteres, recomendado %d): dejala corta y pasa el detalle a \"nota\"" % (ctx, len(out["r"]), MAX_R))
    for x in out.get("o", []):
        if len(x) > MAX_OPC: avisos.append("%s: opcion muy larga (%d caracteres, recomendado %d): \"%s\"" % (ctx, len(x), MAX_OPC, x[:30]))
    eq = p.get("equipo")
    if rid == "r2" and eq not in ("chicos", "chicas"): avisos.append("%s: falta \"equipo\" (chicos o chicas)" % ctx); return None
    if eq in ("chicos", "chicas"): out["equipo"] = eq
    return out

def _lista_preg(lista, tipo, rid, nombre, clase, vistos, avisos):
    res = []
    if lista is None: return res
    if not isinstance(lista, list): avisos.append("%s: \"%s\" no es una lista" % (nombre, clase)); return res
    for i, p in enumerate(lista):
        q = _preg(p, tipo, rid, "%s, %s %d" % (nombre, clase[:-1], i + 1), avisos)
        if q is None: continue
        if not q["id"]:
            q["id"] = "%s-%s%d" % (rid, "R" if clase == "reservas" else "", i + 1)
            avisos.append("%s, %s %d: no tiene \"id\" (se usa %s)" % (nombre, clase[:-1], i + 1, q["id"]))
        if q["id"] in vistos:
            avisos.append("%s, %s %d: id repetido \"%s\" (se usa igual, pero comparte el avance con la otra)" % (nombre, clase[:-1], i + 1, q["id"]))
            q["id"] += "~%d" % len(vistos)
        vistos.add(q["id"]); res.append(q)
    return res

def cargar_banco(ruta=BANCO_FILE):
    """-> (banco, avisos). Si el archivo no sirve levanta ValueError (y el banco anterior queda como estaba)."""
    try:
        with open(ruta, encoding="utf-8-sig") as f: d = json.load(f)
    except FileNotFoundError:
        raise ValueError("No encuentro " + os.path.basename(ruta))
    except Exception as e:
        raise ValueError("El JSON tiene un error: %s" % e)
    if not isinstance(d, dict): raise ValueError("El banco tiene que ser un objeto {version, titulo, rondas}")
    if d.get("version") != 2: raise ValueError("El banco tiene que ser version 2 (dice: %r)" % d.get("version"))
    if not isinstance(d.get("rondas"), list): raise ValueError("Falta la lista \"rondas\"")
    avisos, rondas, vistos, rids = [], [], set(), set()
    for ri, r in enumerate(d["rondas"]):
        if not isinstance(r, dict): raise ValueError("Ronda %d: no es un objeto" % (ri + 1))
        rid = r.get("id")
        if not isinstance(rid, str) or not rid.strip(): raise ValueError("Ronda %d: falta el \"id\"" % (ri + 1))
        rid = rid.strip()
        if rid in rids: raise ValueError("Ronda \"%s\": id repetido" % rid)
        rids.add(rid)
        for k in ("nombre", "color", "tipo", "puntos", "seg", "comodines", "orden"):
            if k not in r: raise ValueError("Ronda \"%s\": falta \"%s\"" % (rid, k))
        tipo, orden = r["tipo"], r["orden"]
        if tipo not in ("opciones", "abierta"): raise ValueError("Ronda \"%s\": \"tipo\" tiene que ser opciones o abierta" % rid)
        if orden not in ("alterno", "por_tema"): raise ValueError("Ronda \"%s\": \"orden\" tiene que ser alterno o por_tema" % rid)
        for k, lo, hi in (("puntos", 1, 99), ("seg", 1, 3600)):
            v = r[k]
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi: raise ValueError("Ronda \"%s\": \"%s\" tiene que ser un numero entero (%d a %d)" % (rid, k, lo, hi))
        if not isinstance(r["comodines"], list): raise ValueError("Ronda \"%s\": \"comodines\" tiene que ser una lista" % rid)
        nombre = str(r["nombre"]).strip() or rid
        col = r["color"] if isinstance(r["color"], str) and HEX.fullmatch(r["color"]) else "#38bdf8"
        if col != r["color"]: avisos.append("%s: color invalido (se usa %s)" % (nombre, col))
        com = []
        for k in r["comodines"]:
            if k not in CLAVES_COM: avisos.append("%s: comodin desconocido \"%s\" (se ignora)" % (nombre, k))
            elif k == "5050" and tipo == "abierta": avisos.append("%s: 50/50 no vale en abiertas (se ignora)" % nombre)
            elif k not in com: com.append(k)
        ron = {"id": rid, "nombre": nombre, "color": col, "tipo": tipo, "puntos": r["puntos"], "seg": r["seg"], "comodines": com, "orden": orden,
               "preguntas": [], "reservas": [], "temas": []}
        ron["sigue_si_acierta"] = r.get("sigue_si_acierta") is True                        # muerte subita: el que acierta sigue respondiendo
        ron["sin_tiempo"] = r.get("sin_tiempo") is True                                    # ronda sin reloj (ej. Cultura general)
        ron["responden"] = "ambos" if r.get("responden") == "ambos" and orden != "por_tema" else "turno"      # "ambos": contestan los dos equipos a la vez
        ron["rebote"] = r.get("rebote") is True and orden != "por_tema" and rid != "r2" and ron["responden"] == "turno"
        if r.get("rebote") is True and not ron["rebote"]: avisos.append("%s: \"rebote\" solo vale en rondas por turno (no r2 ni por temas): se ignora" % nombre)
        if r.get("responden") not in (None, "turno", "ambos"): avisos.append("%s: \"responden\" tiene que ser turno o ambos (se usa turno)" % nombre)
        ron["aproximacion"] = r.get("aproximacion") is True and ron["responden"] == "ambos" and tipo == "abierta"      # gana el mas cercano al numero
        if r.get("aproximacion") is True and not ron["aproximacion"]: avisos.append("%s: \"aproximacion\" necesita responden=ambos y tipo abierta (se ignora)" % nombre)
        if len(nombre) > MAX_NOMBRE: avisos.append("%s: nombre de ronda muy largo (%d caracteres, recomendado %d)" % (nombre, len(nombre), MAX_NOMBRE))
        if orden == "por_tema":
            temas = r.get("temas")
            if not isinstance(temas, list) or not temas: raise ValueError("Ronda \"%s\": falta la lista \"temas\"" % rid)
            tids = set()
            for ti, t in enumerate(temas):
                if not isinstance(t, dict) or not isinstance(t.get("id"), str) or not t["id"].strip(): raise ValueError("Ronda \"%s\", tema %d: falta el \"id\"" % (rid, ti + 1))
                tid = t["id"].strip()
                if tid in tids: raise ValueError("Ronda \"%s\": tema \"%s\" repetido" % (rid, tid))
                tids.add(tid)
                tn = str(t.get("nombre") or tid).strip()
                if len(tn) > MAX_NOMBRE: avisos.append("%s: nombre de tema muy largo (%d caracteres, recomendado %d)" % (tn, len(tn), MAX_NOMBRE))
                tc = t.get("color") if isinstance(t.get("color"), str) and HEX.fullmatch(t.get("color")) else col
                ctx = "%s/%s" % (nombre, tn)
                tema = {"id": tid, "nombre": tn, "color": tc,
                        "preguntas": _lista_preg(t.get("preguntas"), tipo, rid, ctx, "preguntas", vistos, avisos),
                        "reservas": _lista_preg(t.get("reservas"), tipo, rid, ctx, "reservas", vistos, avisos)}
                if len(tema["preguntas"]) != 4 or len(tema["reservas"]) != 3: avisos.append("%s: el tema deberia tener 4 preguntas + 3 reservas (tiene %d + %d)" % (ctx, len(tema["preguntas"]), len(tema["reservas"])))
                ron["temas"].append(tema)
            if len(ron["temas"]) < 3: avisos.append("%s: con menos de 3 temas la eleccion no funciona bien" % nombre)
        else:
            ron["preguntas"] = _lista_preg(r.get("preguntas"), tipo, rid, nombre, "preguntas", vistos, avisos)
            ron["reservas"] = _lista_preg(r.get("reservas"), tipo, rid, nombre, "reservas", vistos, avisos)
            if not ron["preguntas"]: avisos.append("%s: no tiene preguntas validas" % nombre)
        rondas.append(ron)
    if not any(r["preguntas"] or any(t["preguntas"] for t in r["temas"]) for r in rondas): raise ValueError("El banco no tiene ninguna pregunta valida")
    t = d.get("titulo")
    return {"titulo": t.strip() if isinstance(t, str) else "", "rondas": rondas}, avisos


# ============================ motor del juego (sin pantalla) ============================
class Motor:
    def __init__(self):
        self.banco = {"titulo": "", "rondas": []}; self.avisos_banco = []
        self.vol = {n: {"pc": 70, "obs": 100} for n in SONIDOS}
        self.cal = dict(CAL_DEF)
        self.usados = {e: {k: False for k, _ in COMODINES} for e, _, _ in EQUIPOS}
        self.puntos = {e: 0 for e, _, _ in EQUIPOS}
        self.progreso = {}                     # id de pregunta -> hecha / saltada / cambiada / usada
        self.titulo = ""; self.visible = True; self.turno = None      # titulo vacio es valido: no existe titulo por defecto
        self.alternar = True; self.auto_inicio = False          # el reloj arranca con el boton "Iniciar tiempo"
        self.seg_ovr = {}                      # id de ronda -> segundos elegidos a mano (si no, manda "seg" de la ronda)
        self.ronda_i = 0; self.primera = True  # primera = todavia no se jugo ninguna pregunta de esta ronda
        self.sel = {}                          # id de ronda por temas -> {"primero", "elige", "tema": {equipo: id de tema}}
        self.actual = None; self.slot = 0      # actual = (ronda_i, id_tema|None, "preguntas"|"reservas", indice); slot = numero que se muestra
        self.uso_q = None                      # comodin usado en la pregunta en pantalla (solo 1 por pregunta)
        self.fase = "inicio"                   # inicio -> pregunta -> opciones -> revelada   (en abiertas "opciones" = pregunta ya con reloj)
        self.ocultas = []; self.elegida = None; self.resultado = None
        self.revelando = None                  # None, o la hora (monotonic) en que termina el redoble previo a revelar
        self.ultimo_res = None                 # resultado de la ultima pregunta con turno (para la muerte subita)
        self.inicio_q = None                   # equipo que EMPEZO a responder la pregunta en pantalla (antes de un rebote)
        self.rebote = None                     # equipo que FALLO y rebotó la pregunta al otro (r4 y muerte subita)
        self.pend_res = None                   # resultado que se aplica recien cuando termina el redoble
        self.doble = None                      # equipo que jugo DOBLE O NADA en la pregunta en pantalla
        self.res_eq = {}; self.delta_q = {}    # rondas "ambos": resultado de cada equipo / puntos que le dio (para poder corregir)
        self.intentos = None                   # aproximacion: lo que mostro cada carpeta y quien gano
        self.devolver = None                   # equipo al que se le puede devolver la LLAMADA (termino y no funciono)
        self.qid = 0; self.rev = 0
        self.pulso = {n: 0 for n in SONIDOS}
        self.aviso = {"n": 0, "l1": "", "txt": "", "col": "#ffffff"}
        self.panel = {"regla": None, "comodin": None, "equipo": None}      # pantallas informativas de OBS (overlay-reglas / overlay-comodines); no se guarda
        self.r_total = 20; self.r_resto = 20.0; self.r_fin = None; self.r_etiqueta = "TIEMPO"; self.llamada = None
        try: self.banco, self.avisos_banco = cargar_banco()
        except ValueError as e: self.avisos_banco = ["No se pudo leer el banco: %s" % e]
        self.titulo = self.banco["titulo"]
        self.cargar_cfg()
        self._entrar_ronda(reset_turno=False)

    # ---------- persistencia ----------
    def _ids(self):
        ids = set()
        for r in self.banco["rondas"]:
            for q in r["preguntas"] + r["reservas"]: ids.add(q["id"])
            for t in r["temas"]:
                for q in t["preguntas"] + t["reservas"]: ids.add(q["id"])
        return ids

    def cargar_cfg(self):
        """Lee preguntas_config.json. Un config viejo (sin version 3) se migra: lo que no encaja se descarta sin romper."""
        try:
            with open(CFG_FILE, encoding="utf-8") as f: d = json.load(f)
            if not isinstance(d, dict): return
        except Exception: return
        nuevo = d.get("v") in (3, CFG_VERSION)
        try:
            for n, v in (d.get("vol") or {}).items():
                if n in self.vol and isinstance(v, dict):
                    for k in ("pc", "obs"):
                        if isinstance(v.get(k), (int, float)): self.vol[n][k] = max(0, min(100, int(v[k])))
                    if isinstance(v.get("ruta"), str): self.vol[n]["ruta"] = v["ruta"]
            for k, v in (d.get("cal") or {}).items():
                if k in CAL_DEF and isinstance(v, int) and not isinstance(v, bool): self.cal[k] = self._rango(k, v)
            for e, ks in (d.get("usados") or {}).items():
                if e in self.usados and isinstance(ks, dict):
                    for k, b in ks.items():
                        if k in self.usados[e]: self.usados[e][k] = bool(b)
            for e, n in (d.get("puntos") or {}).items():
                if e in self.puntos and isinstance(n, int) and not isinstance(n, bool): self.puntos[e] = max(0, n)
            ids = self._ids()      # el avance viejo usaba otras claves (huellas): lo que no coincide con un id del banco v2 se descarta
            self.progreso = {k: v for k, v in (d.get("progreso") or {}).items() if k in ids and v in ESTADOS}
            t = d.get("titulo")
            if isinstance(t, str):
                t = t.strip()
                if nuevo or t.upper().replace("Á", "A") != "MAS WACHIN": self.titulo = t       # "" se respeta; el viejo valor por defecto no vuelve
            if d.get("turno") in self.puntos: self.turno = d["turno"]
            if d.get("ultimo_res") in ("acierto", "error"): self.ultimo_res = d["ultimo_res"]
            for k in ("alternar", "auto_inicio"):
                if k == "auto_inicio" and d.get("v") != CFG_VERSION: continue          # config viejo: el reloj ya no arranca solo
                if isinstance(d.get(k), bool): setattr(self, k, d[k])
            if nuevo:
                rids = [r["id"] for r in self.banco["rondas"]]
                if d.get("ronda") in rids: self.ronda_i = rids.index(d["ronda"])
                if isinstance(d.get("primera"), bool): self.primera = d["primera"]
                for rid, v in (d.get("seg_ovr") or {}).items():
                    if rid in rids and isinstance(v, int) and not isinstance(v, bool): self.seg_ovr[rid] = max(1, min(3600, v))
                for rid, s in (d.get("sel") or {}).items():
                    r = next((r for r in self.banco["rondas"] if r["id"] == rid and r["orden"] == "por_tema"), None)
                    if r and self._sel_valida(r, s): self.sel[rid] = {"primero": s.get("primero"), "elige": s.get("elige"), "tema": dict(s.get("tema") or {})}
        except Exception: pass

    def _sel_valida(self, r, s):
        try:
            tids = {t["id"] for t in r["temas"]}
            return (isinstance(s, dict) and s.get("primero") in (None, "chicos", "chicas") and s.get("elige") in (None, "chicos", "chicas")
                    and isinstance(s.get("tema"), dict) and all(e in self.puntos and t in tids for e, t in s["tema"].items())
                    and len(set(s["tema"].values())) == len(s["tema"]))
        except Exception: return False

    def guardar(self):
        try:
            rd = self._r()
            tmp = CFG_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"v": CFG_VERSION, "vol": self.vol, "cal": self.cal, "usados": self.usados, "puntos": self.puntos, "progreso": self.progreso,
                           "titulo": self.titulo, "turno": self.turno, "alternar": self.alternar, "auto_inicio": self.auto_inicio, "ultimo_res": self.ultimo_res,
                           "ronda": rd["id"] if rd else None, "primera": self.primera, "seg_ovr": self.seg_ovr, "sel": self.sel}, f, ensure_ascii=False)
            os.replace(tmp, CFG_FILE)
        except Exception: pass

    @staticmethod
    def _rango(k, v):
        lo, hi = CAL_RANGO[k]; return max(lo, min(hi, int(v)))
    def _bump(self): self.rev += 1

    # ---------- sonidos ----------
    def ruta_sonido(self, n):
        r = self.vol[n].get("ruta")
        if r and os.path.exists(r): return r
        for e in EXT:
            f = os.path.join(SND, n + e)
            if os.path.exists(f): return f
        try:
            for fn in sorted(os.listdir(SND)):
                if fn.lower().endswith(EXT) and any(k in fn.lower() for k in CLAVES[n]): return os.path.join(SND, fn)
        except Exception: pass
        return None
    def sonar(self, n):
        with LOCK: self.pulso[n] += 1; self._bump()
        play_local(self.ruta_sonido(n), self.vol[n]["pc"], "pq_" + n)
    def set_vol(self, n, k, v):
        with LOCK: self.vol[n][k] = max(0, min(100, int(float(v)))); self._bump()
        self.guardar()
    def set_ruta(self, n, ruta):
        with LOCK: self.vol[n]["ruta"] = ruta; self._bump()
        self.guardar()

    # ---------- acceso al banco ----------
    def _r(self):
        try: return self.banco["rondas"][self.ronda_i]
        except Exception: return None
    def _tema(self, r, tid):
        return next((t for t in r["temas"] if t["id"] == tid), None)
    def _lista(self, r, tid, tipo):
        if r["orden"] == "por_tema":
            t = self._tema(r, tid)
            if t is None: raise KeyError(tid)
            return t[tipo]
        return r[tipo]
    def _q(self):
        if not self.actual: return None
        try:
            ri, tid, tipo, i = self.actual
            return self._lista(self.banco["rondas"][ri], tid, tipo)[i]
        except Exception: return None
    def seg(self, r=None):
        r = r or self._r()
        return self.seg_ovr.get(r["id"], r["seg"]) if r else 20
    def _seg_actual(self):
        """Segundos de la pregunta en pantalla: los suyos (campo seg) o los de la ronda."""
        q = self._q()
        return q["seg"] if q and q.get("seg") else self.seg()
    def sin_tiempo(self):
        r = self._r(); return bool(r and r.get("sin_tiempo"))
    def _limpiar_q(self):
        self.revelando = None; self.doble = None; self.res_eq = {}; self.delta_q = {}; self.intentos = None; self.devolver = None
        self.rebote = None; self.pend_res = None
    def reservas_libres(self, lista):
        return sum(q["id"] not in self.progreso for q in lista)
    def _ids_ronda(self, r):
        return [q["id"] for q in r["preguntas"] + r["reservas"]] + [q["id"] for t in r["temas"] for q in t["preguntas"] + t["reservas"]]
    def ronda_jugada(self, r):
        return any(i in self.progreso for i in self._ids_ronda(r))
    def _pend(self, lista, excepto=None):
        return [i for i, q in enumerate(lista) if q["id"] not in self.progreso and i != excepto]
    def _responde(self):
        """Quien responde la pregunta en pantalla: en r2 lo dice la pregunta; en el resto, el turno."""
        q = self._q(); r = self._r()
        if q and r and r["id"] == "r2" and q.get("equipo"): return q["equipo"]
        return self.turno

    # ---------- rondas y eleccion de tema (r3) ----------
    def _reset_pregunta(self):
        self._fin_llamada(False)
        self.actual = None; self.slot = 0; self.fase = "inicio"; self.ocultas = []; self.elegida = None; self.resultado = None; self.uso_q = None
        self._limpiar_q()
        self.qid += 1
        self.r_total = self.seg(); self.r_resto = float(self.r_total); self.r_fin = None; self.r_etiqueta = "TIEMPO"

    def _sel_iniciar(self, r):
        s = {"primero": None, "elige": None, "tema": {}}
        a, b = self.puntos["chicos"], self.puntos["chicas"]
        if a != b: s["primero"] = s["elige"] = "chicos" if a > b else "chicas"      # va ganando: elige primero (si empatan lo marca el conductor)
        self.sel[r["id"]] = s

    def _entrar_ronda(self, reset_turno):
        self._reset_pregunta()
        r = self._r()
        if not r: return
        jugada = self.ronda_jugada(r)
        self.primera = not jugada; self.ultimo_res = None
        if r["orden"] == "por_tema" and r["id"] not in self.sel: self._sel_iniciar(r)
        if reset_turno and not jugada:
            self.turno = None                                   # empieza quien indique el conductor
            if r["id"] == "final":                              # la final empieza el que va perdiendo
                a, b = self.puntos["chicos"], self.puntos["chicas"]
                if a != b: self.turno = "chicos" if a < b else "chicas"

    def elegir_ronda(self, i):
        with LOCK:
            if not 0 <= i < len(self.banco["rondas"]): return False, "Esa ronda no existe (¿recargaste el banco?)"
            if i == self.ronda_i: return True, ""
            self.ronda_i = i; self._entrar_ronda(reset_turno=True); self._bump()
        self.guardar(); return True, ""

    def set_primero(self, eq):
        """Empate al empezar la ronda por temas: el conductor marca quien elige primero."""
        with LOCK:
            r = self._r(); s = self.sel.get(r["id"]) if r else None
            if not s: return False, "Esta ronda no es de elegir tema"
            if eq not in self.puntos: return False, "Equipo desconocido"
            if s["tema"]: return False, "Ya hay un tema elegido: usa \"Rehacer selección\""
            s["primero"] = s["elige"] = eq; self._bump()
        self.guardar(); return True, ""

    def elegir_tema(self, tid):
        with LOCK:
            r = self._r(); s = self.sel.get(r["id"]) if r else None
            if not s: return False, "Esta ronda no es de elegir tema"
            if len(s["tema"]) >= 2: return False, "Los dos equipos ya eligieron (para cambiar: \"Rehacer selección\")"
            if not s["elige"]: return False, "Empate: primero marca quien elige primero (Chicos o Chicas)"
            if self._tema(r, tid) is None: return False, "Ese tema no existe"
            if tid in s["tema"].values(): return False, "Ese tema ya lo eligio el otro equipo"
            s["tema"][s["elige"]] = tid
            if len(s["tema"]) == 1: s["elige"] = otro(s["elige"])
            else: s["elige"] = None; self.turno = s["primero"]; self.primera = True      # empieza quien eligio primero
            self._bump()
        self.guardar(); return True, ""

    def rehacer_seleccion(self):
        with LOCK:
            r = self._r()
            if not r or r["orden"] != "por_tema": return False, "Esta ronda no es de elegir tema"
            if self.ronda_jugada(r): return False, "La ronda ya empezo: usa \"Reiniciar avance\" para volver a elegir"
            self._reset_pregunta(); self._sel_iniciar(r); self.turno = None; self.primera = True; self._bump()
        self.guardar(); return True, ""

    def sel_completa(self, r=None):
        r = r or self._r(); s = self.sel.get(r["id"]) if r else None
        return bool(s) and len(s["tema"]) == 2
    def dueno_tema(self, r, tid):
        s = self.sel.get(r["id"]) if r else None
        return next((e for e, t in (s["tema"] if s else {}).items() if t == tid), None)

    # ---------- preguntas ----------
    def _cargar(self, ri, tid, tipo, idx, turno=None, slot=None):
        r = self.banco["rondas"][ri]; q = self._lista(r, tid, tipo)[idx]
        self._fin_llamada(False)
        self.actual = (ri, tid, tipo, idx)
        self.slot = slot if slot else idx + 1
        self.fase = "pregunta"; self.ocultas = []; self.elegida = None; self.resultado = None; self.uso_q = None; self.qid += 1; self._limpiar_q()
        if tipo == "reservas" and q["id"] not in self.progreso: self.progreso[q["id"]] = "usada"
        self.r_total = q.get("seg") or self.seg(r); self.r_resto = float(self.r_total); self.r_fin = None; self.r_etiqueta = "TIEMPO"
        if r.get("responden") == "ambos": self.turno = None          # responden los dos: no hay aro de turno
        elif turno: self.turno = turno
        self.inicio_q = self.turno
        self._bump(); self.guardar()

    def _candidata(self, saltando=False, skipper=None):
        """Que pregunta sigue y quien la responde -> (candidata, equipo, motivo). Sin cargar nada."""
        r = self._r()
        if not r: return None, None, "No hay ronda elegida"
        if r["orden"] == "por_tema":
            s = self.sel.get(r["id"])
            if not s or len(s["tema"]) < 2: return None, None, "Primero elegi los temas (cada equipo elige uno)"
            if saltando: orden = [otro(skipper)]
            elif self.primera or self.turno not in self.puntos: orden = [s["primero"]]
            elif self.alternar: orden = [otro(self.turno)]
            else: orden = [self.turno]
            if not saltando: orden.append(otro(orden[0]))
            for eq in orden:
                t = self._tema(r, s["tema"][eq]); pend = self._pend(t["preguntas"], self.actual[3] if self.actual and self.actual[1] == t["id"] and self.actual[2] == "preguntas" else None)
                if pend: return (self.ronda_i, t["id"], "preguntas", pend[0]), eq, ""
            return None, None, "No quedan preguntas para el otro equipo" if saltando else "No quedan preguntas pendientes en esta ronda"
        cur = self.actual[3] if self.actual and self.actual[2] == "preguntas" else None
        pend = self._pend(r["preguntas"], cur)
        r2 = r["id"] == "r2"
        if saltando and r2: pend = [i for i in pend if r["preguntas"][i].get("equipo") == otro(skipper)]
        if not pend: return None, None, "No quedan preguntas para saltar" if saltando else "No quedan preguntas pendientes en esta ronda"
        ref = self.slot - 1 if self.actual else -1
        i = ([p for p in pend if p > ref] or pend)[0]
        if r2: eq = r["preguntas"][i]["equipo"]
        elif saltando: eq = otro(skipper)
        elif r.get("responden") == "ambos": eq = None
        elif self.turno not in self.puntos: return None, None, "Indica quien empieza (Chicos / Chicas) antes de cargar la pregunta"
        # muerte subita: si acerto sigue el mismo equipo (el que acerto, aunque haya sido en el rebote); si fallaron los dos, empieza
        # de nuevo el que EMPEZO la pregunta anterior (inicio_q), que es el que venia perdiendo
        elif r.get("sigue_si_acierta") and not self.primera: eq = self.turno if self.ultimo_res == "acierto" else (self.inicio_q or self.turno)
        elif self.primera or not self.alternar: eq = self.turno
        else: eq = otro(self.turno)
        return (self.ronda_i, None, "preguntas", i), eq, ""

    def siguiente(self):
        with LOCK:
            cand, eq, motivo = self._candidata()
            if not cand: return False, motivo
            self._cargar(*cand, turno=eq); self.primera = False
        self.guardar(); return True, ""
    def cargar(self, tid, tipo, idx):
        """Carga a mano una pregunta o reserva de la ronda actual (doble clic en la lista)."""
        with LOCK:
            r = self._r()
            try: q = self._lista(r, tid, tipo)[idx]
            except Exception: return False, "Esa pregunta no existe (¿recargaste el banco?)"
            eq = q.get("equipo") if r["id"] == "r2" else (self.dueno_tema(r, tid) if r["orden"] == "por_tema" else None)
            self._cargar(self.ronda_i, tid, tipo, idx, turno=eq); self.primera = False
        self.guardar(); return True, ""
    def mostrar_opciones(self):
        with LOCK:
            if not self._q(): return False, "Primero carga una pregunta"
            if self.revelando is not None: return False, "Se esta revelando la respuesta"
            if self.fase != "pregunta": return False, "La pregunta ya esta en juego"
            self.fase = "opciones"; self._bump()
            if self.auto_inicio and not self.llamada: self.reloj_start()
            return True, ""
    def elegir(self, i):
        with LOCK:
            q = self._q()
            if not q or "o" not in q: return False, "Esta pregunta es abierta: no hay opciones para elegir"
            if self.revelando is not None: return False, "Se esta revelando la respuesta"
            if self.fase != "opciones": return False, "Mostra las opciones antes de elegir (y antes de revelar)"
            if not 0 <= i < len(q["o"]) or i in self.ocultas: return False, "Esa opcion no esta disponible"
            self.elegida = None if self.elegida == i else i; self._bump(); return True, ""
    def _es_muerte(self, r=None):
        """Muerte subita = solo la ronda final (sigue_si_acierta, id "final"). Ahi se revela directo, sin redoble de tambores.
        Otras rondas con rebote (r4) SI llevan redoble."""
        r = r if r is not None else self._r()
        if not r: return False
        return bool(r.get("id") == "final" or r.get("sigue_si_acierta"))

    def revelar(self):
        """Rondas normales: suena el redoble COMPLETO (espera lo que dura el audio + una colita; fase "revelando",
        reloj pausado) y recien despues pasa a "revelada" y suena acierto/error. Un segundo clic durante la espera
        revela ya (y corta el redoble). MUERTE SUBITA (ronda final): revela directo, sin tambores."""
        with LOCK:
            q = self._q()
            if not q: return False, "Primero carga una pregunta"
            if self.fase == "revelada": return False, "Ya esta revelada"
            if self.revelando is not None: self._revelar_ya(cortar=True); return True, ""
            self._iniciar_revelado(); return True, ""
    def _iniciar_revelado(self, pend=None):
        """UNICO camino hacia la fase "revelada": redoble -> revelando -> (tick) _revelar_ya. `pend` = resultado que se aplica al terminar.
        Excepcion: MUERTE SUBITA revela directo sin tambores."""
        self._fin_llamada(True); self.reloj_pause(); self.pend_res = pend
        if self._es_muerte(): self._revelar_ya(); return                     # muerte subita: respuesta directa, sin redoble
        ruta = self.ruta_sonido("redoble")
        if not ruta: self._revelar_ya(); return                                       # sin audio de redoble: revela directo
        dur = min(30.0, duracion_sonido(ruta) or REDOBLE_SIN_DURACION)
        self.revelando = time.monotonic() + dur + REDOBLE_COLA
        self.sonar("redoble"); self._bump()
    def _revelar_ya(self, cortar=False):
        q = self._q()
        if cortar and self.revelando is not None: _mci("stop pq_redoble")              # solo si lo cortan a mano; si no, el redoble termina solo
        self.revelando = None; pend, self.pend_res = self.pend_res, None
        if not q: return
        self._fin_llamada(True); self.reloj_pause(); self.devolver = None
        self.fase = "revelada"; self.progreso[q["id"]] = "hecha"; self._bump()
        r = self._r()
        if pend and r.get("responden") != "ambos": self._resolver(pend)                  # resultado marcado antes del redoble (muerte subita)
        elif self.elegida is not None and "c" in q and r.get("responden") != "ambos":       # acierto/error recien al revelar
            self._resolver("acierto" if self.elegida == q["c"] else "error")
        self.guardar()
    def marcar(self, res):
        with LOCK:
            r = self._r()
            if r and r.get("responden") == "ambos": return False, "Responden los dos equipos: marca el resultado de cada uno con sus botones"
            if r and r.get("rebote") and self.fase in ("pregunta", "opciones") and self.revelando is None and not self.resultado:
                return self._marcar_rebote(res)
            if self.revelando is not None: return False, "Se esta revelando la respuesta"
            if self.fase != "revelada": return False, "Primero revela la respuesta"
            if self.resultado: return False, "Esta pregunta ya tiene resultado (para corregir usa el marcador +/-)"
            self._resolver(res); self.guardar(); return True, ""
    def _marcar_rebote(self, res):
        """Rondas con rebote (r4 Capciosas y muerte subita final). Acierto -> se revela (suma el que acerto). Primer error ->
        la MISMA pregunta pasa al otro equipo con el reloj de nuevo y SIN revelar. Segundo error (fallaron los dos) -> se revela,
        no suma nadie. En la final revela directo (sin tambores); en r4 revela con redoble."""
        eq = self._responde()
        if eq not in self.puntos: return False, "Indica quien responde (Chicos / Chicas) antes de marcar"
        if res == "acierto" or self.rebote:
            self._iniciar_revelado(pend=res); self.guardar(); return True, ""
        self.rebote = eq; self.turno = otro(eq); self.elegida = None
        self._fin_llamada(True); self.r_fin = None; self.r_resto = float(self.r_total)           # el cronometro se reinicia
        self.aviso = {"n": self.aviso["n"] + 1, "l1": "FALLO " + eq.upper(), "txt": "REBOTE", "col": {"chicos": "#4f8dff", "chicas": "#ff4fb8"}[eq]}
        self.sonar("error"); self._bump(); self.guardar()
        if self.auto_inicio: self.reloj_start()
        return True, "Fallo %s: la misma pregunta rebota a %s (reloj de nuevo, sin revelar)" % (eq.upper(), self.turno.upper())
    def _dar(self, eq, res):
        """Aplica el resultado a un equipo. Normal: acierto = puntos de la ronda. DOBLE O NADA: acierto +3, error -1 (nunca baja de 0)."""
        r = self._r(); antes = self.puntos[eq]
        if self.doble == eq: d = DOBLE_ACIERTO if res == "acierto" else -DOBLE_ERROR
        else: d = r["puntos"] if res == "acierto" else 0
        self.puntos[eq] = max(0, antes + d); self.delta_q[eq] = self.puntos[eq] - antes
    def _resolver(self, res):
        self.resultado = res; self.ultimo_res = res
        eq = self._responde()
        if eq in self.puntos and self._r(): self._dar(eq, res)
        self.sonar("acierto" if res == "acierto" else "error")
    def marcar_eq(self, eq, res, sonido=True):
        """Rondas donde responden los dos: resultado de CADA equipo por separado (se puede corregir marcando de nuevo)."""
        with LOCK:
            r = self._r()
            if not r or r.get("responden") != "ambos": return False, "Esta ronda no es de responder los dos equipos"
            if self.fase != "revelada": return False, "Primero revela la respuesta"
            if eq not in self.puntos or res not in ("acierto", "error"): return False, "Resultado desconocido"
            prev = self.res_eq.get(eq)
            if prev == res: return False, "%s ya estaba marcado como %s" % (eq.upper(), res)
            if prev: self.puntos[eq] -= self.delta_q.get(eq, 0)          # deshace lo marcado antes
            self.res_eq[eq] = res; self._dar(eq, res)
            if sonido: self.sonar("acierto" if res == "acierto" else "error")
            self._bump(); self.guardar(); return True, ""
    def aproximar(self, txt_chicos, txt_chicas):
        """Matematicas por aproximacion: con lo que mostro cada carpeta, el mas cercano a la respuesta se lleva el punto."""
        with LOCK:
            r = self._r(); q = self._q()
            if not (r and r.get("aproximacion") and q): return False, "Esta ronda no es de aproximacion"
            if self.fase != "revelada": return False, "Primero revela la respuesta"
            obj = _num(q["num"]) if q.get("num") is not None else _num(q.get("r"))
            if obj is None: return False, "Esta pregunta no tiene un numero de respuesta (campo \"num\" en el banco): marca a mano"
            g = {"chicos": _num(txt_chicos), "chicas": _num(txt_chicas)}
            for eq, v in g.items():
                if v is None: return False, "%s: escribi el numero que mostro la carpeta" % eq.upper()
            d = {eq: abs(v - obj) for eq, v in g.items()}
            if d["chicos"] < d["chicas"]: gana = ["chicos"]
            elif d["chicas"] < d["chicos"]: gana = ["chicas"]
            else: gana = ["chicos", "chicas"] if d["chicos"] == 0 else []         # empate exacto: suman los dos; empate a la misma distancia: nadie
            for eq in self.puntos: self.marcar_eq(eq, "acierto" if eq in gana else "error", sonido=False)
            self.intentos = {"chicos": _fmt(g["chicos"]), "chicas": _fmt(g["chicas"]), "gana": "ambos" if len(gana) == 2 else (gana[0] if gana else None)}
            self.sonar("acierto" if gana else "error"); self._bump(); self.guardar()
            det = "CHICOS a %s, CHICAS a %s de la respuesta (%s)" % (_fmt(d["chicos"]), _fmt(d["chicas"]), _fmt(obj))
            if len(gana) == 1: return True, "Gana %s: %s" % (gana[0].upper(), det)
            if gana: return True, "Los dos acertaron exacto: suman los dos (%s)" % det
            return True, "Empate a la misma distancia: no suma nadie (%s). Podes marcar a mano." % det
    def cerrar(self):
        with LOCK:
            self._reset_pregunta(); self._bump(); return True, ""
    def recargar_banco(self):
        try: nuevo, avisos = cargar_banco()
        except ValueError as e: return False, str(e), []
        with LOCK:
            rid = self._r()["id"] if self._r() else None
            self.banco = nuevo; self.avisos_banco = avisos; self.seg_ovr = {}        # los segundos a mano se descartan: manda el banco
            rids = [r["id"] for r in nuevo["rondas"]]
            self.ronda_i = rids.index(rid) if rid in rids else 0
            for k in list(self.sel):
                r = next((r for r in nuevo["rondas"] if r["id"] == k and r["orden"] == "por_tema"), None)
                if not r or not self._sel_valida(r, self.sel[k]): del self.sel[k]
            self.progreso = {k: v for k, v in self.progreso.items() if k in self._ids()}
            self._entrar_ronda(reset_turno=False); self._bump()
        self.guardar()
        n = sum(len(r["preguntas"]) + sum(len(t["preguntas"]) for t in r["temas"]) for r in nuevo["rondas"])
        return True, "Banco recargado: %d rondas, %d preguntas" % (len(nuevo["rondas"]), n), avisos
    def reiniciar_progreso(self):
        with LOCK:
            self.progreso = {}; self.sel = {}; self.turno = None; self.seg_ovr = {}
            self._entrar_ronda(reset_turno=False); self._bump()
        self.guardar()

    # ---------- comodines ----------
    def _aviso(self, eq, k):
        txt = {"llamada": "LLAMADA", "saltar": "DOBLE O NADA", "cambiar": "CAMBIO", "5050": "50/50"}[k]
        col = {"chicos": "#4f8dff", "chicas": "#ff4fb8"}[eq]
        self.aviso = {"n": self.aviso["n"] + 1, "l1": eq.upper() + " USAN", "txt": txt, "col": col}
    def usar(self, eq, k):
        """Aplica el comodin sobre la pregunta en pantalla y lo marca USADO. Si no se puede, NO se gasta -> (ok, motivo)."""
        with LOCK:
            if eq not in self.usados or k not in self.usados[eq]: return False, "Comodin desconocido"
            nom = NOMBRE_COM[k]
            if self.usados[eq][k]: return False, "%s: %s ya esta usado (no se gasto nada)" % (eq.upper(), nom)
            q = self._q(); r = self._r()
            if q is None or self.fase not in ("pregunta", "opciones") or self.revelando is not None: return False, "No hay una pregunta en juego: %s NO se gasto" % nom
            if k not in r["comodines"]: return False, "%s no vale en %s: NO se gasto" % (nom, r["nombre"])
            if self.uso_q: return False, "Ya se uso un comodin en esta pregunta (solo 1 por pregunta): NO se gasto %s" % nom
            quien = self._responde()
            if quien in self.puntos and quien != eq:
                return False, "Ahora responde %s: el comodin de %s NO se gasto (si el turno esta mal, corregilo con los botones de Turno)" % (quien.upper(), eq.upper())
            if k == "5050":
                if "o" not in q: return False, "El 50/50 es solo para preguntas con opciones: NO se gasto"
                if self.ocultas: return False, "A esta pregunta ya se le aplico 50/50"
                malas = [i for i in range(len(q["o"])) if i != q["c"]]
                self.ocultas = sorted(random.sample(malas, len(malas) - 1))       # quedan la correcta + 1 incorrecta
                if self.elegida in self.ocultas: self.elegida = None
                self.uso_q = k
            elif k == "saltar":      # DOBLE O NADA: si el equipo acierta suma 3, si falla resta 1 (cambia el valor de ESTA pregunta)
                self.doble = eq; self.uso_q = k
            elif k == "cambiar":
                ri, tid, tipo, idx = self.actual
                libres = [j for j, x in enumerate(self._lista(r, tid, "reservas")) if x["id"] not in self.progreso and (r["id"] != "r2" or x.get("equipo") == q.get("equipo"))]
                if not libres: return False, "No quedan reservas %s: NO se gasto" % ("de ese equipo" if r["id"] == "r2" else "del tema" if r["orden"] == "por_tema" else "en esta ronda")
                self.progreso[q["id"]] = "cambiada"; self._cargar(ri, tid, "reservas", libres[0], slot=self.slot); self.uso_q = k
            elif k == "llamada":
                if self.llamada: return False, "Ya hay una llamada en curso"
                self.llamada = {"total": self.r_total, "resto": self._resto_exacto(), "corriendo": self.r_fin is not None, "eq": eq}
                self.r_fin = None; self.r_total = LLAMADA_SEG; self.r_resto = float(LLAMADA_SEG); self.r_etiqueta = "LLAMADA A UN AMIGO"
                self.uso_q = k; self.reloj_start()
            self.usados[eq][k] = True; self._aviso(eq, k); self.sonar("usar"); self._bump(); self.guardar()
            return True, ""
    def reactivar(self, eq, k):
        with LOCK:
            if not self.usados.get(eq, {}).get(k): return False, "Ese comodin ya esta disponible"
            self.usados[eq][k] = False
            if self.uso_q == k: self.uso_q = None                       # libera el "1 por pregunta": se puede volver a usar en esta misma pregunta
            if k == "saltar" and self.doble == eq: self.doble = None
            if k == "llamada" and self.devolver == eq: self.devolver = None
            self._bump()
        self.sonar("reactivar"); self.guardar(); return True, "%s: %s disponible otra vez" % (eq.upper(), NOMBRE_COM[k])
    def devolver_llamada(self):
        """La llamada termino y no funciono (no contesto, se corto): se devuelve el comodin para usarlo de nuevo en esta pregunta."""
        with LOCK:
            eq = self.devolver
            if not eq: return False, "No hay una llamada para devolver"
            self.devolver = None
        return self.reactivar(eq, "llamada")
    def reiniciar_comodines(self, equipos):
        with LOCK:
            hubo = any(self.usados[e][k] for e in equipos for k, _ in COMODINES)
            for e in equipos:
                for k, _ in COMODINES: self.usados[e][k] = False
            self._bump()
        if hubo: self.sonar("reactivar"); self.guardar()
        return hubo

    # ---------- reloj (por hora real: no se atrasa) ----------
    def _resto_exacto(self):
        return max(0.0, self.r_fin - time.monotonic()) if self.r_fin is not None else self.r_resto
    def restante(self): return int(math.ceil(self._resto_exacto() - 1e-9))
    def corriendo(self): return self.r_fin is not None
    def reloj_start(self):
        with LOCK:
            if self.r_fin is not None or self.revelando is not None: return       # durante el redoble el reloj queda pausado
            if self.sin_tiempo() and not self.llamada: return                      # ronda sin tiempo
            if self.r_resto <= 0: self.r_resto = float(self.r_total)
            if self.r_resto >= self.r_total - 1e-6: self.sonar("inicio")
            self.r_fin = time.monotonic() + self.r_resto; self._bump()
    def reloj_pause(self):
        with LOCK:
            if self.r_fin is not None: self.r_resto = self._resto_exacto(); self.r_fin = None; self._bump()
    def reloj_alternar(self):
        """Boton "Iniciar tiempo" de la fila En pantalla: arranca o pausa el reloj de la pregunta."""
        with LOCK:
            if not self._q(): return False, "Primero carga una pregunta"
            if self.revelando is not None: return False, "Se esta revelando la respuesta"
            if self.fase == "revelada": return False, "La pregunta ya esta revelada"
            if self.sin_tiempo() and not self.llamada: return False, "Esta ronda no tiene tiempo"
            self.reloj_pause() if self.r_fin is not None else self.reloj_start(); return True, ""
    def reloj_toggle(self):
        with LOCK: self.reloj_pause() if self.r_fin is not None else self.reloj_start()
    def reloj_reset(self):
        with LOCK: self.r_fin = None; self.r_resto = float(self.r_total); self._bump()
    def reloj_set(self, v):
        """Segundos de la ronda actual a mano (se recuerdan para esa ronda)."""
        with LOCK:
            v = max(1, min(3600, int(v))); r = self._r()
            if r:
                if v == r["seg"]: self.seg_ovr.pop(r["id"], None)         # igual al banco: no hace falta recordarlo
                else: self.seg_ovr[r["id"]] = v
            if not self.llamada: self.r_total = v; self.r_resto = float(v); self.r_fin = None
            self._bump()
        self.guardar()
    def reloj_ajustar(self, d):
        with LOCK:
            resto = max(0.0, self._resto_exacto() + d)
            self.r_total = max(self.r_total, int(math.ceil(resto)))
            if self.r_fin is not None: self.r_fin = time.monotonic() + resto
            else: self.r_resto = resto
            self._bump()
    def _fin_llamada(self, restaurar):
        if not self.llamada: return
        g = self.llamada; self.llamada = None; self.r_fin = None; self.r_etiqueta = "TIEMPO"
        if restaurar:
            self.r_total = g["total"]; self.r_resto = g["resto"]
            if g["corriendo"] and g["resto"] > 0: self.r_fin = time.monotonic() + g["resto"]
        else: self.r_total = self._seg_actual(); self.r_resto = float(self.r_total)
        self._bump()
    def terminar_llamada(self):
        with LOCK:
            if not self.llamada: return False, "No hay llamada en curso"
            self.devolver = self.llamada.get("eq"); self._fin_llamada(True); return True, ""
    def tick(self):
        """La ventana lo llama varias veces por segundo: detecta que el reloj llego a 0 (suena la campana UNA vez)."""
        with LOCK:
            if self.revelando is not None and time.monotonic() >= self.revelando - 1e-9:
                self._revelar_ya(); return True
            if self.r_fin is not None and time.monotonic() >= self.r_fin - 1e-9:
                self.r_fin = None; self.r_resto = 0.0
                self.sonar("campana")
                if self.llamada: self.devolver = self.llamada.get("eq"); self._fin_llamada(True)
                self._bump(); return True
        return False
    def debe_tic(self):
        with LOCK: return self.r_fin is not None and 0 < self.restante() <= TIC_DESDE
    def actualizar_tic_local(self): tic_local(self.debe_tic(), self.ruta_sonido("tictac"), self.vol["tictac"]["pc"])

    # ---------- marcador / turno / varios ----------
    def punto(self, eq, d):
        with LOCK:
            if eq in self.puntos: self.puntos[eq] = max(0, self.puntos[eq] + d); self._bump()
        self.guardar()
    def marcador_a_cero(self):
        with LOCK:
            for e in self.puntos: self.puntos[e] = 0
            self._bump()
        self.guardar()
    def set_turno(self, eq):
        with LOCK: self.turno = eq if eq in self.puntos else None; self._bump()
        self.guardar()
    def set_titulo(self, t):
        with LOCK: self.titulo = t.strip(); self._bump()          # vacio permitido: no hay titulo por defecto
        self.guardar()
    def toggle_visible(self):
        with LOCK: self.visible = not self.visible; self._bump()
    def set_flag(self, k, v):
        with LOCK: setattr(self, k, bool(v))
        self.guardar()
    def set_cal(self, k, v):
        with LOCK: self.cal[k] = self._rango(k, float(v)); self._bump()
        self.guardar()
    def fabrica_cal(self):
        with LOCK: self.cal = dict(CAL_DEF); self._bump()
        self.guardar()

    # ---------- pantallas informativas de OBS (overlay-reglas.html / overlay-comodines.html) ----------
    def set_regla(self, n):
        """Resalta la regla n (1..5) en overlay-reglas. La misma otra vez, o None = quitar el resaltado."""
        with LOCK:
            self.panel["regla"] = n if (n in (1, 2, 3, 4, 5) and self.panel["regla"] != n) else None; self._bump()
    def set_panel_comodin(self, k):
        """Muestra el comodin k grande en overlay-comodines. El mismo otra vez, o None = ocultar."""
        with LOCK:
            self.panel["comodin"] = k if (k in CLAVES_COM and self.panel["comodin"] != k) else None; self._bump()
    def set_panel_equipo(self, eq):
        """Con que equipo se muestra el comodin: "chicos" / "chicas" = una tarjeta; None = las dos."""
        with LOCK: self.panel["equipo"] = eq if eq in self.puntos else None; self._bump()

    # ---------- lo que ve el overlay (NUNCA incluye respuesta / correcta / nota antes de revelar; la nota nunca sale) ----------
    def estado(self):
        with LOCK:
            r = self._r(); q = self._q() if r else None; f = fi = self.fase if q else "inicio"
            if q and self.revelando is not None: f = "revelando"          # suspenso: opciones iguales, sin respuesta ni correcta
            tipo = r["tipo"] if q else None
            tema = ronda = preg = None; correcta = respuesta = equipo_preg = seleccion = categorias = None
            if r:
                tid = self.actual[1] if q else None
                t = self._tema(r, tid) if (q and r["orden"] == "por_tema") else None
                if q: total = len(self._lista(r, tid, "preguntas"))
                else: total = (max(len(x["preguntas"]) for x in r["temas"]) * 2) if r["orden"] == "por_tema" and r["temas"] else len(r["preguntas"])
                ronda = {"id": r["id"], "nombre": r["nombre"], "color": r["color"], "n": self.slot if q else 0, "total": total,
                         "puntos": DOBLE_ACIERTO if (self.doble and r["responden"] != "ambos") else r["puntos"], "reserva": bool(q and self.actual[2] == "reservas"),
                         "responden": r["responden"], "aproximacion": r["aproximacion"], "rebote": r["rebote"]}
                if t: tema = {"nombre": t["nombre"], "color": t["color"], "equipo": self.dueno_tema(r, t["id"])}
                if q:
                    ops = [] if tipo == "abierta" else (list(q["o"]) if fi in ("opciones", "revelada") else [""] * len(q["o"]))
                    preg = {"texto": q["q"], "opciones": ops}
                    if f == "revelada":
                        correcta = q["c"] if tipo == "opciones" else None
                        respuesta = q["o"][q["c"]] if tipo == "opciones" else q["r"]
                    equipo_preg = q.get("equipo") if r["id"] == "r2" else (tema["equipo"] if tema else None)
                s = self.sel.get(r["id"]) if r["orden"] == "por_tema" else None
                if s:
                    ocupados = set(s["tema"].values()); completo = len(s["tema"]) == 2
                    categorias = {"elige": s["elige"], "temas": [{"id": x["id"], "nombre": x["nombre"], "color": x["color"],
                                  "estado": self.dueno_tema(r, x["id"]) if x["id"] in ocupados else ("sin_usar" if completo else "libre")} for x in r["temas"]]}
                    if len(s["tema"]) < 2 or f == "inicio":
                        seleccion = {"elige": categorias["elige"], "temas": [{k: v for k, v in t.items() if k != "id"} for t in categorias["temas"]]}   # igual que antes (contrato v2)
            sin = self.sin_tiempo() and not self.llamada
            rms = 0 if sin else max(0, int(round(self._resto_exacto() * 1000)))
            tt = 0 if sin else self.r_total
            ambos = bool(q and r["responden"] == "ambos")
            st = {"rev": self.rev, "qid": self.qid, "visible": self.visible, "titulo": self.titulo, "titulo_visible": self.titulo != "",
                  "fase": f, "tipo": tipo, "ronda": ronda, "tema": tema, "equipo_pregunta": equipo_preg, "preg": preg,
                  "ocultas": list(self.ocultas) if fi in ("opciones", "revelada") else [], "elegida": self.elegida, "correcta": correcta, "respuesta": respuesta,
                  "resultado": self.resultado, "comodines_validos": list(r["comodines"]) if r else [], "seleccion_tema": seleccion,
                  "doble": self.doble, "rebote": self.rebote if q else None, "resultados": ({e: self.res_eq.get(e) for e in self.puntos} if ambos else None),
                  "intentos": dict(self.intentos) if (self.intentos and f == "revelada") else None,
                  "panel": {"regla": self.panel["regla"], "comodin": self.panel["comodin"], "equipo": None, "categorias": categorias},
                  "turno": self.turno, "puntos": dict(self.puntos),
                  "usados": {e: dict(v) for e, v in self.usados.items()}, "aviso": dict(self.aviso),
                  "timer": {"total": tt, "restante": int(math.ceil(rms / 1000.0 - 1e-9)), "total_ms": tt * 1000, "restante_ms": rms,
                            "t_ms": int(time.time() * 1000), "corriendo": self.corriendo(), "etiqueta": self.r_etiqueta, "llamada": bool(self.llamada), "activo": not sin},
                  "tic_desde": TIC_DESDE, "cal": dict(self.cal), "vol": {n: {"pc": v["pc"], "obs": v["obs"]} for n, v in self.vol.items()}}
            for n, v in self.pulso.items(): st["p_" + n] = v
            return st

    def datos_conductor(self):
        """Lo que ve SOLO el conductor en la ventana (respuesta y nota de la pregunta en pantalla). No sale por /state."""
        with LOCK:
            q = self._q()
            if not q: return None
            return {"respuesta": q["o"][q["c"]] if "o" in q else q["r"], "correcta": q.get("c"), "nota": q.get("nota", ""), "especial": q.get("especial", ""), "num": q.get("num")}


MOTOR = None

# ============================ servidor local ============================
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, ctype, body):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        try: self.wfile.write(body)
        except Exception: pass
    def do_OPTIONS(self): self._send(204, "text/plain", b"")
    def do_POST(self): self._send(200, "text/plain", b"ok")
    def do_GET(self):
        try: self._get()
        except Exception: self._send(500, "text/plain", b"error")
    def _get(self):
        p = unquote(self.path.split("?")[0])
        if p == "/state": return self._send(200, "application/json", json.dumps(MOTOR.estado()).encode())
        if p.startswith("/sonido/"):
            n = p.split("/")[-1]; r = MOTOR.ruta_sonido(n) if n in SONIDOS else None
            if not r: return self._send(404, "text/plain", b"no")
            ct = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}.get(os.path.splitext(r)[1].lower(), "audio/mpeg")
            with open(r, "rb") as f: return self._send(200, ct, f.read())
        if p.startswith("/img/"):
            n = p[5:]; f = os.path.join(IMG, n)       # {equipo}_{clave}_{activa|apagada}.png  (solo minusculas, numeros y _)
            if not re.fullmatch(r"[a-z0-9_]+\.png", n) or not os.path.isfile(f): return self._send(404, "text/plain", ("no existe tarjetas/" + n).encode())
            with open(f, "rb") as fh: return self._send(200, "image/png", fh.read())
        if p.startswith(("/foto/", "/fotos/")):       # fotos de los temas (opcional): fotos/tema_minecraft.jpg ...
            n = p.split("/")[-1]; f = os.path.join(FOTOS, n)
            if not re.fullmatch(r"[a-z0-9_]+\.(jpg|jpeg|png|webp)", n) or not os.path.isfile(f): return self._send(404, "text/plain", b"no hay foto")
            ct = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[os.path.splitext(n)[1]]
            with open(f, "rb") as fh: return self._send(200, ct, fh.read())
        if p in OVERLAYS:                              # http://127.0.0.1:8769/reglas  /comodines  /categorias  (alternativa a "Archivo local")
            f = os.path.join(BASE, OVERLAYS[p])
            if not os.path.isfile(f): return self._send(404, "text/plain", ("falta " + OVERLAYS[p]).encode())
            with open(f, "rb") as fh: return self._send(200, "text/html; charset=utf-8", fh.read())
        if p in ("/overlay", "/"):
            with open(os.path.join(BASE, "preguntas-obs-local.html"), "rb") as f: return self._send(200, "text/html; charset=utf-8", f.read())
        self._send(404, "text/plain", b"no")


# ============================ ventana de control ============================
BG, PANEL, PANEL2, TXT, MUTED = "#0b1220", "#131d33", "#1b2842", "#f1f5f9", "#7f8ea8"
AZUL, VERDE, ROJO, AMBAR, GRIS = "#2563eb", "#16a34a", "#dc2626", "#f59e0b", "#4b5563"
FONT = "Segoe UI"

def btn(parent, text, cmd, bg=PANEL2, fg=TXT, size=11, padx=14, pady=7):
    """Boton plano (Label) con hover: se ve igual en cualquier sistema."""
    l = tk.Label(parent, text=text, bg=bg, fg=fg, font=(FONT, size, "bold"), padx=padx, pady=pady, cursor="hand2")
    l._bg = bg
    def sel(c): l._bg = c; l.config(bg=c)
    l.set = lambda bg=None, fg=None, text=None: (sel(bg) if bg else None, l.config(fg=fg) if fg else None, l.config(text=text) if text is not None else None)
    def enter(e):
        h = l._bg.lstrip("#"); r, g, b = (int(h[k:k + 2], 16) for k in (0, 2, 4))
        l.config(bg="#%02x%02x%02x" % tuple(min(255, int(v * 1.18) + 8) for v in (r, g, b)))
    l.bind("<Enter>", enter); l.bind("<Leave>", lambda e: l.config(bg=l._bg))
    l.bind("<Button-1>", lambda e: cmd())
    return l

def panel(parent, titulo, color="#38bdf8", side=None, expand=False):
    o = tk.Frame(parent, bg=PANEL)
    if side: o.pack(side=side, fill="both", expand=expand, padx=(14, 4) if side == "left" else (4, 14), pady=(0, 10))
    else: o.pack(fill="x", padx=14, pady=(0, 10))
    tk.Label(o, text=titulo.upper(), bg=PANEL, fg=color, font=(FONT, 9, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
    c = tk.Frame(o, bg=PANEL); c.pack(fill="both", expand=True, padx=12, pady=(0, 10))
    return c

class App:
    def __init__(self, root, m):
        self.m = m; self.root = root; self._setting = True; self._lista_key = None; self._ll_vis = False
        self._dev_vis = False; self._ambos_vis = False; self._aprox_vis = True; self._qid_ui = -1
        self._ops_vis = True; self._rondas_key = None; self._sel_key = None; self.vista_tema = None
        root.title("Preguntas y Comodines - Control"); root.configure(bg=BG)
        root.minsize(700, 520); root.geometry("940x980")
        outer = tk.Frame(root, bg=BG); outer.pack(fill="both", expand=True)
        sb = tk.Scrollbar(outer, orient="vertical"); sb.pack(side="right", fill="y")
        self.cv = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollcommand=sb.set, yscrollincrement=30)
        self.cv.pack(side="left", fill="both", expand=True); sb.config(command=self.cv.yview)
        body = tk.Frame(self.cv, bg=BG); self.win = self.cv.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))
        root.bind_all("<MouseWheel>", lambda e: self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        root.bind_all("<Button-4>", lambda e: self.cv.yview_scroll(-1, "units"))
        root.bind_all("<Button-5>", lambda e: self.cv.yview_scroll(1, "units"))
        root.bind_all("<Key>", self.tecla)
        root.protocol("WM_DELETE_WINDOW", self.cerrar_app)

        self.armar_cabecera(body); self.armar_ronda(body); self.armar_pantalla(body); self.armar_reloj_marcador(body); self.armar_comodines(body); self.armar_pantallas(body)
        self.armar_banco(body); self.armar_sonidos(body); self.armar_posicion(body)
        self._setting = False
        self.refrescar()
        falt = tarjetas_faltantes()
        if falt: self.mensaje("Faltan %d tarjetas en la carpeta \"tarjetas\" (ej: %s): por eso no se ven los comodines en OBS" % (len(falt), falt[0]), False)
        elif m.avisos_banco: self.mensaje("Banco: " + m.avisos_banco[0] + (" (+%d mas)" % (len(m.avisos_banco) - 1) if len(m.avisos_banco) > 1 else ""), False)
        self.tick()

    # ----- utilidades -----
    def mensaje(self, txt, ok=True):
        self.lbl_msg.config(text=txt, fg="#86efac" if ok else "#fca5a5")
    def hacer(self, fn, *a, **k):
        """Ejecuta una accion del motor y muestra el motivo si no se pudo."""
        r = fn(*a, **k); ok, msg = r[0], r[1]
        if msg: self.mensaje(msg, ok)
        elif ok: self.mensaje("")
        self.refrescar(); return r
    def tecla(self, e):
        w = self.root.focus_get()
        if isinstance(w, (tk.Entry, tk.Spinbox, tk.Text)): return      # no dispara comodines mientras escribis un numero o texto
        if e.char and e.char in "12345678":
            i = int(e.char) - 1; self.usar(EQUIPOS[i // 4][0], COMODINES[i % 4][0])
    def cerrar_app(self):
        try: self.m.guardar(); tic_local(False, None, 0)
        finally: self.root.destroy()

    # ----- cabecera -----
    def armar_cabecera(self, body):
        h = tk.Frame(body, bg=BG); h.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(h, text="PREGUNTAS", bg=BG, fg=TXT, font=(FONT, 17, "bold")).pack(side="left")
        self.vis = btn(h, "OVERLAY VISIBLE", self.toggle_vis, VERDE, size=9, pady=5); self.vis.pack(side="right")
        self.cuenta = tk.Label(h, text="", font=(FONT, 10, "bold"), bg=PANEL2, fg=TXT, padx=12, pady=5); self.cuenta.pack(side="right", padx=8)
        self.lbl_msg = tk.Label(body, text="", bg=BG, fg="#86efac", font=(FONT, 10, "bold"), anchor="w", wraplength=860, justify="left")
        self.lbl_msg.pack(fill="x", padx=16, pady=(0, 6))
    def toggle_vis(self): self.m.toggle_visible(); self.refrescar()

    # ----- ronda (y eleccion de tema en la ronda por temas) -----
    def armar_ronda(self, body):
        c = panel(body, "Ronda", "#a78bfa")
        self.frondas = tk.Frame(c, bg=PANEL); self.frondas.pack(fill="x")
        self.lbl_ronda = tk.Label(c, text="", bg=PANEL, fg=MUTED, font=(FONT, 9, "bold"), anchor="w", justify="left", wraplength=860); self.lbl_ronda.pack(fill="x", pady=(6, 0))
        self.ftema = tk.Frame(c, bg=PANEL2)       # solo se ve en la ronda por temas
    def rebuild_rondas(self):
        for w in self.frondas.winfo_children(): w.destroy()
        for i, r in enumerate(self.m.banco["rondas"]):
            b = btn(self.frondas, r["nombre"], lambda i=i: self.sel_ronda(i), PANEL2, size=9, pady=4, padx=8)
            b.grid(row=i // 3, column=i % 3, sticky="ew", padx=2, pady=2); self.frondas.columnconfigure(i % 3, weight=1); b._i = i
    def sel_ronda(self, i):
        m = self.m
        if i != m.ronda_i and m.fase in ("pregunta", "opciones") and not messagebox.askyesno("Ronda", "Hay una pregunta en juego.\n¿Cambiar de ronda igual? (la pregunta se cierra)"): return
        self.hacer(m.elegir_ronda, i)
    def rebuild_tema(self):
        """Eleccion de tema de la ronda por temas: quien elige, los temas y como van quedando."""
        m = self.m; r = m._r(); s = m.sel.get(r["id"]) if r and r["orden"] == "por_tema" else None
        key = (m.ronda_i, json.dumps(s, sort_keys=True), m.puntos["chicos"], m.puntos["chicas"]) if s else None
        if key == self._sel_key: return
        self._sel_key = key
        for w in self.ftema.winfo_children(): w.destroy()
        if not s: self.ftema.pack_forget(); return
        self.ftema.pack(fill="x", pady=(8, 0))
        if len(s["tema"]) == 2: txt = "Temas elegidos. Empieza %s (elegio primero). Los otros dos temas no se usan." % s["primero"].upper()
        elif s["elige"]: txt = "ELIGE %s (%s)" % (s["elige"].upper(), "va ganando, elige primero" if len(s["tema"]) == 0 and s["primero"] == s["elige"] and m.puntos["chicos"] != m.puntos["chicas"] else "elige entre los que quedan")
        else: txt = "EMPATE: marca quien elige primero (cara o cruz en camara)"
        tk.Label(self.ftema, text=txt, bg=PANEL2, fg=AMBAR, font=(FONT, 10, "bold"), anchor="w").pack(fill="x", padx=8, pady=(6, 2))
        if not s["elige"] and not s["tema"]:
            f = tk.Frame(self.ftema, bg=PANEL2); f.pack(fill="x", padx=8, pady=2)
            for eq, nom, col in EQUIPOS: btn(f, "Elige primero: " + nom, lambda eq=eq: self.hacer(m.set_primero, eq), col, "white", size=9, pady=4, padx=10).pack(side="left", padx=(0, 6))
        f = tk.Frame(self.ftema, bg=PANEL2); f.pack(fill="x", padx=8, pady=4)
        for i, t in enumerate(r["temas"]):
            due = m.dueno_tema(r, t["id"]); libre = due is None
            etq = t["nombre"] + ("" if libre else "  (%s)" % due.upper()) if not (libre and len(s["tema"]) == 2) else t["nombre"] + "  (sin usar)"
            col = t["color"] if libre and len(s["tema"]) < 2 else (dict((e, c) for e, _, c in EQUIPOS)[due] if due else GRIS)
            b = btn(f, etq, lambda tid=t["id"]: self.hacer(m.elegir_tema, tid), col, "white", size=9, pady=5, padx=8)
            b.grid(row=0, column=i, sticky="ew", padx=2); f.columnconfigure(i, weight=1)
        btn(self.ftema, "Rehacer selección", lambda: self.hacer(m.rehacer_seleccion), PANEL, MUTED, size=8, pady=2, padx=8).pack(anchor="e", padx=8, pady=(0, 6))

    # ----- en pantalla -----
    def armar_pantalla(self, body):
        c = panel(body, "En pantalla", "#f472b6")
        self.lbl_sec = tk.Label(c, text="", bg=PANEL, fg=MUTED, font=(FONT, 10, "bold"), anchor="w", justify="left", wraplength=860); self.lbl_sec.pack(fill="x")
        self.lbl_q = tk.Label(c, text="", bg=PANEL, fg=TXT, font=(FONT, 15, "bold"), wraplength=820, justify="left", anchor="w"); self.lbl_q.pack(fill="x", pady=(2, 6))
        self.fops = tk.Frame(c, bg=PANEL); self.fops.pack(fill="x")
        self.ops = []
        for i in range(4):
            f = tk.Frame(self.fops, bg=PANEL2); f.pack(fill="x", pady=2)
            k = tk.Label(f, text="ABCD"[i], bg=BG, fg="#38bdf8", font=(FONT, 12, "bold"), width=2); k.pack(side="left", padx=(6, 8), pady=5)
            t = tk.Label(f, text="", bg=PANEL2, fg=TXT, font=(FONT, 12), anchor="w", wraplength=560, justify="left"); t.pack(side="left", fill="x", expand=True)
            b = btn(f, "Elegir", lambda i=i: self.hacer(self.m.elegir, i), BG, size=9, pady=3, padx=10); b.pack(side="right", padx=6)
            self.ops.append({"f": f, "k": k, "t": t, "b": b})
        # solo para el conductor (NO sale por /state): respuesta y nota
        self.fcond = tk.Frame(c, bg="#2a2208"); self.fcond.pack(fill="x", pady=(6, 0))
        self.lbl_resp = tk.Label(self.fcond, text="", bg="#2a2208", fg="#fde047", font=(FONT, 12, "bold"), anchor="w", justify="left", wraplength=840); self.lbl_resp.pack(fill="x", padx=8, pady=(4, 0))
        self.lbl_nota = tk.Label(self.fcond, text="", bg="#2a2208", fg="#fcd34d", font=(FONT, 10), anchor="w", justify="left", wraplength=840); self.lbl_nota.pack(fill="x", padx=8, pady=(0, 4))
        r = tk.Frame(c, bg=PANEL); r.pack(fill="x", pady=(8, 2))
        btn(r, "▶ Siguiente pregunta", lambda: self.hacer(self.m.siguiente), AZUL, "white", size=10, pady=6).pack(side="left", padx=(0, 6))
        self.b_mostrar = btn(r, "Mostrar opciones", lambda: self.hacer(self.m.mostrar_opciones), "#7c3aed", "white", size=10, pady=6); self.b_mostrar.pack(side="left", padx=(0, 6))
        self.b_tiempo = btn(r, "▶ Iniciar tiempo", lambda: self.hacer(self.m.reloj_alternar), AMBAR, "#111", size=10, pady=6); self.b_tiempo.pack(side="left", padx=(0, 6))
        btn(r, "Revelar respuesta", lambda: self.hacer(self.m.revelar), VERDE, "white", size=10, pady=6).pack(side="left", padx=(0, 6))
        # rondas donde responden los dos equipos: resultado de cada equipo por separado (y Matematicas: gana el mas cercano)
        self.f_ambos = tk.Frame(c, bg=PANEL2); self.amb = {}
        for eq, nombre, col in EQUIPOS:
            f = tk.Frame(self.f_ambos, bg=PANEL2); f.pack(fill="x", padx=8, pady=2)
            tk.Label(f, text=nombre, bg=PANEL2, fg=col, font=(FONT, 10, "bold"), width=8, anchor="w").pack(side="left")
            bo = btn(f, "✔ Acierto", lambda eq=eq: self.hacer(self.m.marcar_eq, eq, "acierto"), PANEL, size=10, pady=4); bo.pack(side="left", padx=(0, 6))
            be = btn(f, "✖ Error", lambda eq=eq: self.hacer(self.m.marcar_eq, eq, "error"), PANEL, size=10, pady=4); be.pack(side="left", padx=(0, 6))
            lb = tk.Label(f, text="", bg=PANEL2, fg=MUTED, font=(FONT, 9, "bold")); lb.pack(side="left", padx=8)
            self.amb[eq] = {"ok": bo, "err": be, "lbl": lb}
        self.f_aprox = tk.Frame(self.f_ambos, bg=PANEL2); self.f_aprox.pack(fill="x", padx=8, pady=(4, 6))
        tk.Label(self.f_aprox, text="Lo que mostró cada carpeta →", bg=PANEL2, fg=MUTED, font=(FONT, 9)).pack(side="left")
        self.var_gc = tk.StringVar(); self.var_gh = tk.StringVar()
        for nombre, col, var in (("CHICOS", "#4f8dff", self.var_gc), ("CHICAS", "#ff4fb8", self.var_gh)):
            tk.Label(self.f_aprox, text=nombre + ":", bg=PANEL2, fg=col, font=(FONT, 9, "bold")).pack(side="left", padx=(10, 2))
            e = tk.Entry(self.f_aprox, textvariable=var, width=9, font=(FONT, 11), bg=BG, fg=TXT, insertbackground=TXT, relief="flat"); e.pack(side="left", ipady=3)
            e.bind("<Return>", lambda ev: self.calcular_aprox())
        btn(self.f_aprox, "Calcular ganador (el más cercano)", self.calcular_aprox, VERDE, "white", size=9, pady=4, padx=10).pack(side="left", padx=10)
        r2 = tk.Frame(c, bg=PANEL); r2.pack(fill="x", pady=(4, 0)); self.fr_res = r2
        self.b_ok = btn(r2, "✔ Acierto (+1)", lambda: self.hacer(self.m.marcar, "acierto"), PANEL2, size=10, pady=5); self.b_ok.pack(side="left", padx=(0, 6))
        self.b_err = btn(r2, "✖ Error", lambda: self.hacer(self.m.marcar, "error"), PANEL2, size=10, pady=5); self.b_err.pack(side="left", padx=(0, 6))
        self.b_volver = btn(r2, "Volver al título", lambda: self.hacer(self.m.cerrar), PANEL2, size=10, pady=5); self.b_volver.pack(side="left", padx=(0, 6))
        self.lbl_res = tk.Label(r2, text="", bg=PANEL, fg=MUTED, font=(FONT, 10, "bold")); self.lbl_res.pack(side="left", padx=10)
        t = tk.Frame(c, bg=PANEL); t.pack(fill="x", pady=(8, 0))
        tk.Label(t, text="Título de abajo (puede quedar vacío):", bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(side="left")
        self.var_tit = tk.StringVar(value=self.m.titulo)
        e = tk.Entry(t, textvariable=self.var_tit, font=(FONT, 11), bg=BG, fg=TXT, insertbackground=TXT, relief="flat", width=30); e.pack(side="left", padx=8, ipady=3)
        e.bind("<Return>", lambda ev: self.aplicar_titulo())
        btn(t, "Aplicar", self.aplicar_titulo, PANEL2, size=9, pady=3, padx=10).pack(side="left")
    def calcular_aprox(self): self.hacer(self.m.aproximar, self.var_gc.get(), self.var_gh.get())
    def aplicar_titulo(self): self.m.set_titulo(self.var_tit.get()); self.mensaje("Título actualizado" if self.m.titulo else "Título vacío: no se muestra nada"); self.refrescar()

    # ----- reloj + marcador -----
    def armar_reloj_marcador(self, body):
        fila = tk.Frame(body, bg=BG); fila.pack(fill="x")
        c = panel(fila, "Reloj (el del Debate)", "#fde047", side="left", expand=True)
        self.lbl_t = tk.Label(c, text="00:20", bg=BG, fg="#fff", font=(FONT, 34, "bold"), width=6); self.lbl_t.pack(side="left", padx=(0, 12))
        col = tk.Frame(c, bg=PANEL); col.pack(side="left", fill="x", expand=True)
        r1 = tk.Frame(col, bg=PANEL); r1.pack(fill="x")
        self.b_play = btn(r1, "▶ INICIAR", lambda: self.hacer(self._r, self.m.reloj_toggle), VERDE, "white", size=10, pady=5); self.b_play.pack(side="left", padx=(0, 4))
        btn(r1, "Reiniciar", lambda: self.hacer(self._r, self.m.reloj_reset), PANEL2, size=9, pady=5, padx=8).pack(side="left", padx=2)
        btn(r1, "-10", lambda: self.hacer(self._r, self.m.reloj_ajustar, -10), PANEL2, size=9, pady=5, padx=8).pack(side="left", padx=2)
        btn(r1, "+10", lambda: self.hacer(self._r, self.m.reloj_ajustar, 10), PANEL2, size=9, pady=5, padx=8).pack(side="left", padx=2)
        r2 = tk.Frame(col, bg=PANEL); r2.pack(fill="x", pady=(6, 0))
        self.lbl_seg = tk.Label(r2, text="Segundos de esta ronda:", bg=PANEL, fg=MUTED, font=(FONT, 9)); self.lbl_seg.pack(side="left")
        self.sp = tk.Spinbox(r2, from_=5, to=600, width=5, font=(FONT, 10), bg=BG, fg=TXT, buttonbackground=PANEL2, insertbackground=TXT, relief="flat")
        self.sp.delete(0, "end"); self.sp.insert(0, str(self.m.seg())); self.sp.pack(side="left", padx=6)
        self.sp.bind("<Return>", lambda e: self.aplicar_seg()); self.sp.bind("<FocusOut>", lambda e: self.aplicar_seg())
        btn(r2, "Aplicar", self.aplicar_seg, PANEL2, size=9, pady=2, padx=8).pack(side="left")
        self.b_ll = btn(col, "Terminar llamada", lambda: self.hacer(self.m.terminar_llamada), AMBAR, "#111", size=9, pady=3)
        self.b_dev = btn(col, "", lambda: self.hacer(self.m.devolver_llamada), "#0ea5e9", "white", size=9, pady=4)
        self.v_alt = tk.BooleanVar(value=self.m.alternar); self.v_aut = tk.BooleanVar(value=self.m.auto_inicio)
        for txt, v, k in (("Alternar turno en cada pregunta nueva", self.v_alt, "alternar"), ("Arrancar el reloj al mostrar las opciones", self.v_aut, "auto_inicio")):
            tk.Checkbutton(col, text=txt, variable=v, bg=PANEL, fg=TXT, selectcolor=BG, activebackground=PANEL, activeforeground=TXT, font=(FONT, 9),
                           command=lambda v=v, k=k: self.m.set_flag(k, v.get())).pack(anchor="w", pady=(4, 0))
        c = panel(fila, "Marcador y turno", "#60a5fa", side="left")
        self.lbl_p = {}
        for eq, nombre, col in EQUIPOS:
            f = tk.Frame(c, bg=PANEL); f.pack(fill="x", pady=2)
            tk.Label(f, text=nombre, bg=PANEL, fg=col, font=(FONT, 10, "bold"), width=8, anchor="w").pack(side="left")
            btn(f, "−", lambda eq=eq: self.hacer(self._p, eq, -1), PANEL2, size=11, pady=1, padx=9).pack(side="left")
            l = tk.Label(f, text="0", bg=BG, fg="#fff", font=(FONT, 16, "bold"), width=3); l.pack(side="left", padx=4); self.lbl_p[eq] = l
            btn(f, "+", lambda eq=eq: self.hacer(self._p, eq, 1), PANEL2, size=11, pady=1, padx=9).pack(side="left")
        btn(c, "Marcador a 0", self.marcador_cero, PANEL2, MUTED, size=8, pady=2, padx=8).pack(anchor="w", pady=(4, 0))
        tk.Label(c, text="Turno = quien responde (aro en la cámara)", bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(8, 2))
        f = tk.Frame(c, bg=PANEL); f.pack(fill="x"); self.b_turno = {}
        for eq, t in (("chicos", "Chicos"), ("chicas", "Chicas"), (None, "Ninguno")):
            b = btn(f, t, lambda eq=eq: self.hacer(self._t, eq), PANEL2, size=9, pady=4, padx=8); b.pack(side="left", padx=(0, 4)); self.b_turno[eq] = b
    def _r(self, fn, *a): fn(*a); return True, ""
    def _p(self, eq, d): self.m.punto(eq, d); return True, ""
    def _t(self, eq): self.m.set_turno(eq); return True, ""
    def marcador_cero(self):
        if messagebox.askyesno("Marcador", "¿Poner el marcador de los dos equipos en 0?"): self.m.marcador_a_cero(); self.refrescar()
    def aplicar_seg(self):
        try: v = int(self.sp.get())
        except ValueError: self.mensaje("Los segundos tienen que ser un numero", False); self.sp.delete(0, "end"); self.sp.insert(0, str(self.m.seg())); return
        if v != self.m.seg(): self.m.reloj_set(v); self.refrescar()

    # ----- comodines -----
    def armar_comodines(self, body):
        fila = tk.Frame(body, bg=BG); fila.pack(fill="x"); self.rows = {}
        for ei, (eq, nombre, col) in enumerate(EQUIPOS):
            c = panel(fila, "Comodines " + nombre, col, side="left" if ei == 0 else "right", expand=True)
            top = tk.Frame(c, bg=PANEL); top.pack(fill="x", pady=(0, 4))
            tk.Label(top, text="Teclas %d-%d" % (ei * 4 + 1, ei * 4 + 4), bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(side="left")
            btn(top, "Reiniciar", lambda eq=eq: self.reiniciar(eq), PANEL2, size=9, pady=2, padx=8).pack(side="right")
            for ki, (k, t) in enumerate(COMODINES):
                f = tk.Frame(c, bg=PANEL2, highlightthickness=2, highlightbackground=PANEL2); f.pack(fill="x", pady=2)
                tk.Label(f, text=str(ei * 4 + ki + 1), bg=BG, fg=col, font=(FONT, 11, "bold"), width=2).pack(side="left", padx=(6, 8), pady=6)
                tk.Label(f, text=t, bg=PANEL2, fg=TXT, font=(FONT, 10, "bold")).pack(side="left")
                b = btn(f, "USAR", lambda eq=eq, k=k: self.alternar(eq, k), col, "white", size=10, padx=12, pady=4); b.pack(side="right", padx=6, pady=4)
                chip = tk.Label(f, text="", font=(FONT, 8, "bold"), padx=6, pady=2); chip.pack(side="right", padx=2)
                self.rows[(eq, k)] = {"f": f, "b": b, "chip": chip, "col": col}
        c = panel(body, "General")
        btn(c, "Reiniciar TODOS los comodines", self.reiniciar_todo, ROJO, "white", size=10, pady=5).pack(side="left")
        tk.Label(c, text="Las teclas solo USAN; reactivar es con el botón gris, para no errarle en vivo. 1 comodín por pregunta.", bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(side="left", padx=12)
    def usar(self, eq, k):
        ok, msg = self.m.usar(eq, k)          # si no se puede aplicar, NO se gasta y el motor dice por que
        self.mensaje(msg if msg else "%s: %s usado" % (eq.upper(), NOMBRE_COM[k]), ok); self.refrescar()
    def alternar(self, eq, k):
        if self.m.usados[eq][k]: self.hacer(self.m.reactivar, eq, k)
        else: self.usar(eq, k)
    def reiniciar(self, eq): self.m.reiniciar_comodines([eq]); self.refrescar()
    def reiniciar_todo(self):
        if messagebox.askyesno("Comodines", "¿Reactivar los 8 comodines de los dos equipos?"): self.m.reiniciar_comodines([e for e, _, _ in EQUIPOS]); self.refrescar()

    # ----- pantallas informativas de OBS: reglas resaltada y comodin grande (cada una es otra escena de OBS) -----
    def armar_pantallas(self, body):
        c = panel(body, "Pantallas de OBS: reglas y comodín grande", "#facc15")
        tk.Label(c, text="Escenas aparte en OBS (overlay-reglas.html, overlay-comodines.html). Acá elegís qué regla se resalta o qué comodín se muestra (en amarillo). Apretar el mismo botón otra vez lo quita.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w", justify="left", wraplength=860).pack(fill="x", pady=(0, 6))
        def fila(titulo):
            f = tk.Frame(c, bg=PANEL); f.pack(fill="x", pady=3)
            tk.Label(f, text=titulo, bg=PANEL, fg=TXT, font=(FONT, 9, "bold"), width=17, anchor="w").pack(side="left")
            return f
        f = fila("REGLA RESALTADA"); self.b_regla = {}
        for n in range(1, 6):
            b = btn(f, str(n), lambda n=n: self.pan_regla(n), PANEL2, size=11, padx=16, pady=5); b.pack(side="left", padx=3); self.b_regla[n] = b
        btn(f, "Quitar", lambda: self.pan_regla(None), GRIS, size=10, padx=12, pady=5).pack(side="left", padx=(10, 0))
        f = fila("COMODÍN GRANDE"); self.b_pcom = {}
        for k, t in COMODINES:
            b = btn(f, {"llamada": "Llamada a un amigo", "saltar": "Doble o nada", "cambiar": "Cambiar pregunta", "5050": "50/50"}[k], lambda k=k: self.pan_comodin(k), PANEL2, size=10, padx=10, pady=5); b.pack(side="left", padx=3); self.b_pcom[k] = b
        btn(f, "Ocultar", lambda: self.pan_comodin(None), GRIS, size=10, padx=12, pady=5).pack(side="left", padx=(10, 0))
        tk.Label(c, text="El comodín grande siempre muestra las dos tarjetas (Chicos y Chicas), en amarillo.", bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", pady=(2, 0))
    def pan_regla(self, n): self.m.set_regla(n); self.refrescar_pantallas()
    def pan_comodin(self, k):
        if k is None:                                                       # Ocultar: siempre quita, nunca alterna
            with LOCK: self.m.panel["comodin"] = None; self.m._bump()
        else: self.m.set_panel_comodin(k)
        self.refrescar_pantallas()
    def refrescar_pantallas(self):
        with LOCK: p = dict(self.m.panel)
        AM = "#facc15"
        for n, b in self.b_regla.items(): b.set(AM if p["regla"] == n else PANEL2, "#111827" if p["regla"] == n else TXT)
        for k, b in self.b_pcom.items(): b.set(AM if p["comodin"] == k else PANEL2, "#111827" if p["comodin"] == k else TXT)

    # ----- banco -----
    def armar_banco(self, body):
        c = panel(body, "Preguntas y reservas de la ronda", "#4ade80")
        self.ftemas_v = tk.Frame(c, bg=PANEL); self.ftemas_v.pack(fill="x", pady=(0, 6))
        cols = tk.Frame(c, bg=PANEL); cols.pack(fill="x")
        self.lbs = {}
        for tipo, titulo, h in (("preguntas", "Preguntas (doble clic = cargar)", 8), ("reservas", "Reservas (doble clic = cargar a mano)", 8)):
            f = tk.Frame(cols, bg=PANEL); f.pack(side="left", fill="both", expand=True, padx=(0, 6))
            tk.Label(f, text=titulo, bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w")
            lb = tk.Listbox(f, height=h, exportselection=False, bg=BG, fg=TXT, selectbackground=AZUL, font=(FONT, 10), relief="flat", activestyle="none", highlightthickness=0)
            lb.pack(fill="x"); lb.bind("<Double-Button-1>", lambda e, t=tipo: self.cargar_sel(t)); self.lbs[tipo] = lb
        r = tk.Frame(c, bg=PANEL); r.pack(fill="x", pady=(8, 0))
        btn(r, "Cargar la pregunta elegida", lambda: self.cargar_sel("preguntas"), AZUL, "white", size=9, pady=4).pack(side="left", padx=(0, 6))
        btn(r, "Recargar banco", self.recargar, PANEL2, size=9, pady=4).pack(side="left", padx=(0, 6))
        btn(r, "Abrir banco (editar)", self.abrir_banco, PANEL2, size=9, pady=4).pack(side="left", padx=(0, 6))
        btn(r, "Reiniciar avance", self.reiniciar_avance, ROJO, "white", size=9, pady=4).pack(side="left")
        self.lbl_banco = tk.Label(c, text="", bg=PANEL, fg=MUTED, font=(FONT, 8), anchor="w", justify="left", wraplength=820); self.lbl_banco.pack(fill="x", pady=(6, 0))
    def vista(self):
        """-> (ronda, id de tema que se muestra en las listas)"""
        m = self.m; r = m._r()
        if r and r["orden"] == "por_tema":
            ids = [t["id"] for t in r["temas"]]
            if self.vista_tema not in ids: self.vista_tema = ids[0] if ids else None
            return r, self.vista_tema
        return r, None
    def sel_tema_vista(self, tid): self.vista_tema = tid; self.refrescar()
    def cargar_sel(self, tipo):
        sel = self.lbs[tipo].curselection()
        if not sel: self.mensaje("Elegi una pregunta de la lista", False); return
        r, tid = self.vista()
        if r and r["orden"] == "por_tema" and not self.m.sel_completa(r): self.mensaje("Primero elegi los temas (cada equipo elige uno)", False); return
        try: q = self.m._lista(r, tid, tipo)[sel[0]]
        except Exception: self.mensaje("Esa pregunta no existe", False); return
        if self.m.progreso.get(q["id"]) == "hecha" and not messagebox.askyesno("Preguntas", "Esa pregunta ya se jugó.\n¿Cargarla de nuevo? (si la volves a resolver suma punto otra vez)"): return
        self.hacer(self.m.cargar, tid, tipo, sel[0])
    def recargar(self):
        ok, msg, avisos = self.m.recargar_banco(); self._rondas_key = None
        if not ok: self.mensaje(msg, False); messagebox.showerror("Banco de preguntas", msg + "\n\nSe mantiene el banco anterior."); self.refrescar(); return
        self.mensaje(msg, True)
        if avisos: messagebox.showwarning("Banco de preguntas", "Se ignoraron o avisaron %d cosas:\n\n" % len(avisos) + "\n".join(avisos[:12]))
        self.refrescar()
    def abrir_banco(self):
        try: os.startfile(BANCO_FILE)
        except Exception: self.mensaje("Abrí a mano: " + BANCO_FILE, False)
    def reiniciar_avance(self):
        if messagebox.askyesno("Preguntas", "¿Marcar todas las preguntas y reservas como pendientes otra vez?\n(también se borra la elección de temas)"): self.m.reiniciar_progreso(); self.refrescar()

    # ----- sonidos -----
    def armar_sonidos(self, body):
        c = panel(body, "Sonidos y volumen  (carpeta sonidos)")
        c.columnconfigure(3, weight=1); c.columnconfigure(4, weight=1)
        for col, t in ((3, "PARLANTES PC"), (4, "OBS")): tk.Label(c, text=t, bg=PANEL, fg=MUTED, font=(FONT, 8, "bold")).grid(row=0, column=col, sticky="w", padx=8)
        self.sdots = {}
        for r_, n in enumerate(SONIDOS, 1):
            d = tk.Label(c, text="●", bg=PANEL, font=(FONT, 12)); d.grid(row=r_, column=0, pady=2); self.sdots[n] = d
            tk.Label(c, text=n.capitalize(), bg=PANEL, fg=TXT, font=(FONT, 10, "bold"), width=10, anchor="w").grid(row=r_, column=1)
            bf = tk.Frame(c, bg=PANEL); bf.grid(row=r_, column=2, padx=6)
            btn(bf, "Probar", lambda n=n: self.m.sonar(n), PANEL2, size=9, pady=2, padx=8).pack(side="left")
            btn(bf, "Elegir...", lambda n=n: self.elegir(n), PANEL2, size=9, pady=2, padx=8).pack(side="left", padx=(4, 0))
            for col, k in ((3, "pc"), (4, "obs")):
                sc = tk.Scale(c, from_=0, to=100, orient="horizontal", length=100, bg=PANEL, fg=TXT, troughcolor=BG, highlightthickness=0, bd=0,
                              activebackground="#38bdf8", font=(FONT, 8), command=lambda v, n=n, k=k: None if self._setting else self.m.set_vol(n, k, v))
                sc.set(self.m.vol[n][k]); sc.grid(row=r_, column=col, padx=8, sticky="ew")
        self.info = tk.Label(c, text="", bg=PANEL, fg=MUTED, font=(FONT, 8), justify="left", wraplength=820); self.info.grid(row=len(SONIDOS) + 1, column=0, columnspan=5, sticky="w", pady=(6, 0))
    def elegir(self, n):
        p = filedialog.askopenfilename(title="Archivo para " + n, initialdir=SND, filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a")])
        if p: self.m.set_ruta(n, p); self.refrescar()

    # ----- posicion -----
    def armar_posicion(self, body):
        c = panel(body, "Posición del overlay")
        self.cscales = {}
        g = tk.Frame(c, bg=PANEL); g.pack(fill="x"); g.columnconfigure(1, weight=1)
        for r_, (k, t) in enumerate((("size", "Tamaño de las tarjetas"), ("dy", "Comodines: subir / bajar"), ("chicos_dx", "Comodines chicos: izq / der"),
                                      ("chicas_dx", "Comodines chicas: izq / der"), ("pan_dy", "Panel de abajo: subir / bajar"), ("pan_h", "Panel de abajo: alto"))):
            lo, hi = CAL_RANGO[k]
            tk.Label(g, text=t, bg=PANEL, fg=TXT, font=(FONT, 10), width=28, anchor="w").grid(row=r_, column=0)
            sc = tk.Scale(g, from_=lo, to=hi, orient="horizontal", bg=PANEL, fg=TXT, troughcolor=BG, highlightthickness=0, bd=0, activebackground="#38bdf8", font=(FONT, 9),
                          command=lambda v, k=k: None if self._setting else (self.m.set_cal(k, v)))
            sc.set(self.m.cal[k]); sc.grid(row=r_, column=1, sticky="ew", padx=8); self.cscales[k] = sc
        r = tk.Frame(c, bg=PANEL); r.pack(fill="x", pady=(8, 0))
        self.v_guia = tk.BooleanVar(value=bool(self.m.cal["guia"]))
        tk.Checkbutton(r, text="Mostrar guía de cámaras (para alinear)", variable=self.v_guia, bg=PANEL, fg=TXT, selectcolor=BG, activebackground=PANEL, activeforeground=TXT, font=(FONT, 9),
                       command=lambda: self.m.set_cal("guia", int(self.v_guia.get()))).pack(side="left")
        btn(r, "Restaurar de fábrica", self.fabrica, AMBAR, "#111", size=9, pady=4).pack(side="right")
    def fabrica(self):
        self.m.fabrica_cal(); self._setting = True
        try:
            for k, sc in self.cscales.items(): sc.set(self.m.cal[k])
            self.v_guia.set(False)
        finally: self._setting = False
        self.refrescar()

    # ----- refresco -----
    def refrescar_reloj(self):
        if hasattr(self, "b_tiempo"): self.b_tiempo.set(text="⏸ Pausar tiempo" if self.m.corriendo() else "▶ Iniciar tiempo")
        if self.m.sin_tiempo() and not self.m.llamada:
            self.lbl_t.config(text="--:--", fg=MUTED); self.b_play.set(text="SIN TIEMPO"); return
        r = self.m.restante(); self.lbl_t.config(text="%02d:%02d" % divmod(r, 60), fg="#ff6b6b" if r <= TIC_DESDE and self.m.r_total > 0 else "#ffffff")
        self.b_play.set(text="⏸ PAUSAR" if self.m.corriendo() else "▶ INICIAR")
    def _mostrar_opciones_ui(self, ver):
        if ver == self._ops_vis: return
        self._ops_vis = ver
        for o in self.ops: o["f"].pack_forget()
        if ver:
            for o in self.ops: o["f"].pack(fill="x", pady=2)
    def refrescar(self):
        m = self.m
        self.refrescar_pantallas()
        with LOCK:
            r = m._r(); q = m._q() if r else None; fase = m.fase if q else "inicio"; actual = m.actual
            usados = {k: dict(v) for k, v in m.usados.items()}; cond = m.datos_conductor()
        if self._rondas_key != id(m.banco): self._rondas_key = id(m.banco); self.rebuild_rondas()
        self.vis.set(VERDE if m.visible else GRIS, text="OVERLAY VISIBLE" if m.visible else "OVERLAY OCULTO")
        self.cuenta.config(text="%d de 8 comodines" % sum(not v for ee in usados.values() for v in ee.values()))
        # ronda
        for w in self.frondas.winfo_children():
            i = getattr(w, "_i", None)
            if i is not None: w.set(AZUL if i == m.ronda_i else PANEL2, "white")
        if r:
            nombres = [NOMBRE_COM[k] for k in r["comodines"]]
            extra = (" · responden los dos" if r.get("responden") == "ambos" else "") + (" · gana el más cercano" if r.get("aproximacion") else "") + (" · si aciertan, siguen ellos" if r.get("sigue_si_acierta") else "") + (" · con rebote" if r.get("rebote") else "")
            self.lbl_ronda.config(text="%s  ·  %s  ·  vale %d pt  ·  %s%s  ·  comodines: %s" % (
                r["nombre"].upper(), "con opciones A-D" if r["tipo"] == "opciones" else "abierta (sin opciones)", r["puntos"],
                "SIN TIEMPO" if r.get("sin_tiempo") else "%d s" % m.seg(), extra, ", ".join(nombres) if nombres else "NINGUNO"))
        else: self.lbl_ronda.config(text="El banco no tiene rondas")
        self.rebuild_tema()
        # en pantalla
        abierta = bool(r and r["tipo"] == "abierta")
        self._mostrar_opciones_ui(not abierta)
        if q:
            ri, tid, tipo, idx = actual; t = m._tema(r, tid) if tid else None
            lista = m._lista(r, tid, "preguntas")
            eq = m._responde()
            if r.get("responden") == "ambos": quien = "  ·  responden LOS DOS"
            else: quien = ("  ·  responde %s" % eq.upper()) if eq else "  ·  (sin turno: no suma)"
            if m.rebote: quien += "  ·  🔁 REBOTE: fallo %s, ahora responde %s" % (m.rebote.upper(), (m.turno or "?").upper())
            if m.doble: quien += "  ·  ⚡ DOBLE O NADA de %s (+%d / −%d)" % (m.doble.upper(), DOBLE_ACIERTO, DOBLE_ERROR)
            self.lbl_sec.config(text="%s%s  ·  %s  ·  vale %d pt%s  ·  fase: %s" % (
                r["nombre"].upper(), ("  ·  " + t["nombre"].upper()) if t else "", "RESERVA (en lugar de la %d)" % m.slot if tipo == "reservas" else "pregunta %d de %d" % (idx + 1, len(lista)),
                r["puntos"], quien, "revelando (redoble)..." if m.revelando is not None else fase))
            self.lbl_q.config(text=q["q"])
            txt_resp = ("RESPUESTA: " + cond["respuesta"]) if abierta else ""
            if cond["especial"] == "lista": txt_resp += ("   " if txt_resp else "") + "[LISTA: marca Acierto o Error a mano]"
            self.lbl_resp.config(text=txt_resp); self.lbl_nota.config(text=("NOTA: " + cond["nota"]) if cond["nota"] else "")
        else:
            self.lbl_sec.config(text="Mostrando el título" if m.titulo else "Sin pregunta en pantalla"); self.lbl_q.config(text="(ninguna pregunta cargada)")
            self.lbl_resp.config(text=""); self.lbl_nota.config(text="")
        (self.fcond.pack(fill="x", pady=(6, 0)) if (q and (abierta or (cond and cond["nota"]))) else self.fcond.pack_forget())
        self.b_mostrar.set(text="Iniciar pregunta" if abierta else "Mostrar opciones")
        for i, o in enumerate(self.ops):
            if q and "o" in q and i < len(q["o"]):
                oculta = i in m.ocultas; correcta = q["c"] == i; bgc = "#5b4a00" if m.elegida == i else PANEL2
                o["t"].config(text=q["o"][i] + ("   ← CORRECTA" if correcta else "") + ("   (sacada por 50/50)" if oculta else ""),
                              fg="#86efac" if correcta else (MUTED if oculta else TXT), bg=bgc); o["f"].config(bg=bgc)
                o["b"].set(text="Elegida" if m.elegida == i else "Elegir")
            else:
                o["t"].config(text="", bg=PANEL2); o["f"].config(bg=PANEL2); o["b"].set(text="Elegir")
        reb = bool(r and r.get("rebote"))                                    # con rebote (r4 y final): se marca ANTES de revelar
        hay_res = (fase == "revelada" and not m.resultado) or (reb and fase in ("pregunta", "opciones") and m.revelando is None and not m.resultado)
        pts = DOBLE_ACIERTO if m.doble else (r["puntos"] if r else 1)
        self.b_ok.set(bg=VERDE if hay_res else PANEL2, fg="white" if hay_res else MUTED, text="✔ Acierto (+%d)" % pts)
        self.b_err.set(bg=ROJO if hay_res else PANEL2, fg="white" if hay_res else MUTED,
                       text=("✖ Error (−%d)" % DOBLE_ERROR) if m.doble else (("✖ Error (fallan los dos)" if m.rebote else "✖ Error → REBOTE al otro") if (reb and fase != "revelada") else "✖ Error"))
        ambos = bool(r and r.get("responden") == "ambos"); aprox = bool(r and r.get("aproximacion"))
        if ambos != self._ambos_vis:
            self._ambos_vis = ambos
            if ambos: self.b_ok.pack_forget(); self.b_err.pack_forget(); self.f_ambos.pack(fill="x", pady=(4, 0), before=self.fr_res)
            else: self.f_ambos.pack_forget(); self.b_ok.pack(side="left", padx=(0, 6), before=self.b_volver); self.b_err.pack(side="left", padx=(0, 6), before=self.b_volver)
        if aprox != self._aprox_vis:
            self._aprox_vis = aprox
            if aprox: self.f_aprox.pack(fill="x", padx=8, pady=(4, 6))
            else: self.f_aprox.pack_forget()
        if m.qid != self._qid_ui: self._qid_ui = m.qid; self.var_gc.set(""); self.var_gh.set("")
        for eq, w in self.amb.items():
            res = m.res_eq.get(eq); act = fase == "revelada"
            w["ok"].set(VERDE if res == "acierto" else ("#14532d" if act else PANEL), "white" if (act or res) else MUTED, "✔ Acierto (+%d)" % (DOBLE_ACIERTO if m.doble == eq else (r["puntos"] if r else 1)))
            w["err"].set(ROJO if res == "error" else ("#7f1d1d" if act else PANEL), "white" if (act or res) else MUTED, "✖ Error (−%d)" % DOBLE_ERROR if m.doble == eq else "✖ Error")
            w["lbl"].config(text={"acierto": "acierto marcado", "error": "error marcado"}.get(res or "", ""))
        dev = m.devolver
        if bool(dev) != self._dev_vis:
            self._dev_vis = bool(dev)
            if dev:
                self.b_dev.set(text="↩ La llamada no funcionó: devolver el comodín (%s)" % dev.upper()); self.b_dev.pack(anchor="w", pady=(6, 0))
                self.mensaje("Terminó la llamada. Si no contestó, apretá \"devolver el comodín\" y la podés usar de nuevo.", True)
            else: self.b_dev.pack_forget()
        self.lbl_res.config(text={"acierto": "Acierto marcado", "error": "Error marcado"}.get(m.resultado or "", "") + (" (sin turno: no suma)" if m.resultado == "acierto" and not m._responde() else ""))
        # reloj / marcador / turno
        self.refrescar_reloj()
        self.lbl_seg.config(text="Segundos de %s:" % (r["nombre"] if r else "la ronda"))
        if self.root.focus_get() is not self.sp and self.sp.get() != str(m.seg()): self.sp.delete(0, "end"); self.sp.insert(0, str(m.seg()))
        if bool(m.llamada) != self._ll_vis:
            self._ll_vis = bool(m.llamada)
            if self._ll_vis: self.b_ll.pack(anchor="w", pady=(6, 0))
            else: self.b_ll.pack_forget()
        for eq, l in self.lbl_p.items(): l.config(text=str(m.puntos[eq]))
        for eq, b in self.b_turno.items(): b.set(AZUL if m.turno == eq else PANEL2, "white")
        # comodines: libre / usado / no vale en esta ronda
        validos = r["comodines"] if r else []
        for (eq, k), row in self.rows.items():
            u = usados[eq][k]; vale = k in validos
            row["f"].config(highlightbackground=GRIS if (u or not vale) else row["col"])
            row["chip"].config(text="USADO" if u else ("LIBRE" if vale else "NO VALE"), bg="#3A3A3A" if (u or not vale) else VERDE, fg="#FF2D2D" if u else ("#9ca3af" if not vale else "white"))
            row["b"].set(GRIS if (u or not vale) else row["col"], "#e5e7eb" if (u or not vale) else "white", "Reactivar" if u else "USAR")
        # listas
        rr, tid = self.vista()
        if rr and rr["orden"] == "por_tema":
            key = (m.ronda_i, tid, id(m.banco))
            if getattr(self, "_vt_key", None) != key:
                self._vt_key = key
                for w in self.ftemas_v.winfo_children(): w.destroy()
                for i, t in enumerate(rr["temas"]):
                    b = btn(self.ftemas_v, t["nombre"], lambda x=t["id"]: self.sel_tema_vista(x), PANEL2, size=9, pady=4, padx=8)
                    b.grid(row=0, column=i, sticky="ew", padx=2); self.ftemas_v.columnconfigure(i, weight=1); b._t = t["id"]
            for w in self.ftemas_v.winfo_children(): w.set(AZUL if getattr(w, "_t", None) == tid else PANEL2, "white")
        else:
            if getattr(self, "_vt_key", None) is not None:
                self._vt_key = None
                for w in self.ftemas_v.winfo_children(): w.destroy()
        self.rebuild_lista()
        for n, d in self.sdots.items(): d.config(fg="#22c55e" if m.ruta_sonido(n) else "#ef4444")
        self.info.config(text="  |  ".join("%s: %s" % (n, os.path.basename(m.ruta_sonido(n)) if m.ruta_sonido(n) else "NO ENCONTRADO") for n in SONIDOS))
        if rr:
            try: libres = m.reservas_libres(m._lista(rr, tid, "reservas"))
            except Exception: libres = 0
            falt = tarjetas_faltantes()
            self.lbl_banco.config(text="Ronda %s: las reservas libres de %s alimentan el comodín CAMBIAR PREGUNTA (%d)." % (rr["nombre"], "este tema" if tid else "la ronda", libres) +
                                  (("   ⚠ Faltan %d tarjetas en la carpeta tarjetas (ej: %s)" % (len(falt), falt[0])) if falt else ""))
    def rebuild_lista(self):
        m = self.m; r, tid = self.vista()
        if not r: return
        try: listas = {t: m._lista(r, tid, t) for t in ("preguntas", "reservas")}
        except Exception: return
        marca = {"hecha": "✔", "saltada": "»", "cambiada": "↻", "usada": "•"}
        key = (m.ronda_i, tid, tuple(m.progreso.get(q["id"]) for t in ("preguntas", "reservas") for q in listas[t]), m.actual, id(m.banco))
        if key == self._lista_key: return
        self._lista_key = key
        for tipo in ("preguntas", "reservas"):
            lb = self.lbs[tipo]; sel = lb.curselection(); lb.delete(0, "end")
            for i, q in enumerate(listas[tipo]):
                st = m.progreso.get(q["id"]); ahora = m.actual == (m.ronda_i, tid, tipo, i)
                lb.insert("end", "%s %d. %s" % ("▶" if ahora else (marca.get(st, "○")), i + 1, q["q"][:80]))
            if sel and sel[0] < lb.size(): lb.selection_set(sel[0])
    def tick(self):
        try:
            if self.m.tick(): self.refrescar()
            else: self.refrescar_reloj()
            self.m.actualizar_tic_local()
        except Exception: pass
        self.root.after(150, self.tick)


def main():
    global MOTOR
    if tk is None: raise SystemExit("Falta tkinter (viene con Python para Windows).")
    MOTOR = Motor()
    try: srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    except OSError:
        r = tk.Tk(); r.withdraw()
        messagebox.showerror("Preguntas", "El puerto %d ya esta en uso.\nProbablemente Preguntas ya esta abierto en otra ventana." % PORT)
        raise SystemExit
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    r = tk.Tk(); App(r, MOTOR); r.mainloop()

if __name__ == "__main__":
    main()
