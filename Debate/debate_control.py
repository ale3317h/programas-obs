# -*- coding: utf-8 -*-
"""
Control Productor - Debate Centro de Estudiantes 2026
Un solo programa en Python. Sin 2 Chromes.

Uso:
  python debate_control.py

Hace 2 cosas:
  1) Abre la ventana de CONTROL (productor)
  2) Levanta un servidor en http://127.0.0.1:8765
     - /overlay -> lo que se muestra en OBS (placa inferior, fondo transparente)
     - /state   -> JSON que lee el overlay cada 250ms
     - /sonido/campana -> campana-de-box.mp3 (audio por OBS + parlantes Windows)
     - /sonido/tictac  -> TIC TAC SONIDO.mp3 en loop (audio por OBS + parlantes Windows)
     - /ping (POST)    -> el overlay avisa que esta vivo y si el audio esta bloqueado

En OBS agregás como Fuente Navegador:
  URL = http://127.0.0.1:8765/overlay
  1920 x 1080
  IMPORTANTE: en la fuente Navegador tildar "Controlar el audio mediante OBS".
  Despues en el Mezclador de audio subir el volumen de esa fuente y en
  "Propiedades de audio avanzadas" poner Monitoreo en "Monitor y salida"
  si queres oirlo en sala y que salga al stream.
Solo stdlib: tkinter + http.server + winmm (MCI). Sin pip.
"""
import ctypes
import json
import os
import threading
import tkinter as tk
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONIDOS_DIR = os.path.join(BASE_DIR, "sonidos para programa de navegador")
CAMPANA_FILE = os.path.join(SONIDOS_DIR, "campana-de-box.mp3")
TICTAC_FILE = os.path.join(SONIDOS_DIR, "TIC TAC SONIDO.mp3")

def _buscar_inicio():
    # El sonido de inicio es el archivo que tenga "inici"/"start"/"comienzo"/"arranque" en el nombre
    # pero NO de la ruleta (ej: "Inicia ruleta..." es del giro, no del reloj).
    # Ej: "sonido inicio reloj.mp3". Si todavía no lo pusiste, devuelve la ruta esperada
    # (el servidor responde 404 y el overlay lo ignora sin romperse).
    try:
        for n in os.listdir(SONIDOS_DIR):
            ln = n.lower()
            if ln.endswith((".mp3", ".wav", ".ogg", ".m4a")) and "ruleta" not in ln and (
                "inici" in ln or "start" in ln or "comienzo" in ln or "arranque" in ln
            ):
                return os.path.join(SONIDOS_DIR, n)
    except Exception:
        pass
    return os.path.join(SONIDOS_DIR, "inicio-reloj.mp3")

INICIO_FILE = _buscar_inicio()

LOGO_NOMBRES = ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp", "logo.gif")
LOGO_MIMES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".webp": "image/webp", ".gif": "image/gif"}

def _buscar_logo():
    # Logo del recuadro izquierdo: archivo "logo.png" (o jpg/webp/gif)
    # al lado del programa. Búsqueda en vivo, sin reiniciar.
    try:
        for n in LOGO_NOMBRES:
            r = os.path.join(BASE_DIR, n)
            if os.path.exists(r):
                return r
    except Exception:
        pass
    return os.path.join(BASE_DIR, "logo.png")

# ---------------- Estado compartido ----------------
state = {
    "badge": "BIENVENIDA",
    "titulo": "Bienvenida a todas las listas",
    "sub": "Reglas • Elecciones miércoles 30/09",
    "total": 30,
    "restante": 30,
    "base": 30,
    "corriendo": False,
    "visible": True,
    "rev": 1,  # cada cambio de titulo/sub/tiempo lo incrementa -> dispara animación en overlay
    "ding": 0,  # cada "Probar sonido" lo incrementa -> el overlay suena
    "play_campana": 0,  # campana-de-box.mp3 (fin de tiempo / botón)
    "play_inicio": 0,  # sonido de inicio: suena cada vez que arranca la cuenta
    "tic_on": False,  # forzar TIC TAC aunque el contador esté parado
    "tic_auto": True,  # True = el tic-tac sigue solo al contador (corre/corta)
}
lock = threading.Lock()

def bump_rev():
    state["rev"] += 1

# ---------------- Overlay HTML (sirve Python y también el .html suelto) ----------------

# ---------------- Overlay HTML (sirve Python y también el .html suelto) ----------------
OVERLAY_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>OVERLAY - Debate 2026</title>
<style>
  html,body{margin:0;padding:0;background:transparent !important;width:1920px;height:1080px;overflow:hidden;font-family:'Segoe UI',Arial,sans-serif;}
  #placa{
    position:absolute;left:60px;bottom:50px;width:1800px;height:186px;overflow:hidden;box-sizing:border-box;
    background:#000000;
    border:3px solid #38bdf8;border-radius:16px;
    display:flex;align-items:center;padding:24px 28px 16px;gap:26px;
    box-shadow:0 10px 40px rgba(0,0,0,.65),0 0 28px rgba(56,189,248,.4);
    transition:opacity .3s, transform .3s;
  }
  #placa.oculta{opacity:0;transform:translateY(30px);}
  #col-izq{flex-shrink:0;width:210px;height:64px;display:flex;align-items:center;justify-content:center;}
  #logo{width:210px;height:64px;object-fit:contain;display:block;}
  #contenido{flex:1;min-width:0;overflow:visible;display:flex;flex-direction:column;justify-content:center;}
  #titulo{font-size:54px;font-weight:900;color:#ffffff;line-height:1.15;text-shadow:0 2px 8px rgba(0,0,0,.7);white-space:normal;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;word-break:break-word;padding-bottom:8px;margin-bottom:-4px;}
  #sub{font-size:27px;color:#dbeafe;font-weight:700;margin-top:2px;text-shadow:0 1px 6px rgba(0,0,0,.7);white-space:normal;overflow:hidden;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;word-break:break-word;line-height:1.25;padding-bottom:4px;}
  #timer{
    font-size:86px;font-weight:900;font-variant-numeric:tabular-nums;flex-shrink:0;
    color:#ffffff !important;background:#000000;border-radius:14px;
    padding:0 20px;width:340px;text-align:center;border:3px solid #f1f5f9;line-height:1.1;
    box-shadow:0 0 8px rgba(255,255,255,.55),0 0 20px rgba(147,197,253,.35),inset 0 0 10px rgba(255,255,255,.12);
    text-shadow:0 0 8px rgba(255,255,255,.8),0 0 20px rgba(147,197,253,.7),0 0 34px rgba(59,130,246,.5);
  }
  #timer.amarillo{color:#fde047 !important;border-color:#facc15 !important;
    box-shadow:0 0 7px rgba(250,204,21,.65),0 0 18px rgba(250,204,21,.4),0 0 34px rgba(250,204,21,.28),inset 0 0 10px rgba(250,204,21,.18) !important;
    text-shadow:0 0 6px rgba(254,249,195,.85),0 0 16px rgba(250,204,21,.65),0 0 32px rgba(234,179,8,.45) !important;
    animation:timerNeon 1.1s ease-in-out infinite !important;}
  #timer.rojo{color:#f87171 !important;border-color:#ef4444 !important;
    box-shadow:0 0 7px rgba(255,45,45,.7),0 0 18px rgba(255,45,45,.45),0 0 38px rgba(255,45,45,.3),inset 0 0 10px rgba(255,45,45,.2) !important;
    text-shadow:0 0 6px rgba(255,150,150,.85),0 0 16px rgba(255,45,45,.65),0 0 32px rgba(255,0,0,.45) !important;
    animation:timerNeon 1.1s ease-in-out infinite !important;}
  @keyframes timerNeon{0%,100%{filter:brightness(1.15);}50%{filter:brightness(.92);}}
  @keyframes blink{50%{opacity:.55}}
  #barra-track{position:absolute;top:10px;left:16px;right:16px;height:9px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:99px;z-index:4;overflow:visible;box-shadow:inset 0 1px 5px rgba(0,0,0,.9);}
  #barra{position:absolute;top:0;left:0;height:100%;width:100%;min-width:0;background:#ffffff;border-radius:99px;transition:width 1s linear,background .3s;
    box-shadow:0 0 6px #fff,0 0 14px rgba(255,255,255,.95),0 0 28px rgba(147,197,253,.9),0 0 55px rgba(59,130,246,.7);
    animation:neonPulse 1.8s ease-in-out infinite;}
  #barra::before{content:'';position:absolute;top:100%;left:0;width:100%;height:12px;background:linear-gradient(180deg,rgba(255,255,255,.15),transparent);filter:blur(4px);pointer-events:none;}
  #barra.amarilla::before{background:linear-gradient(180deg,rgba(250,204,21,.18),transparent);}
  #barra.roja::before{background:linear-gradient(180deg,rgba(255,45,45,.25),transparent);}
  #barra.amarilla{background:#fde047 !important;
    box-shadow:0 0 6px #fef9c3,0 0 14px rgba(253,224,71,.95),0 0 28px rgba(250,204,21,.9),0 0 55px rgba(234,179,8,.7) !important;}
  #barra.roja{background:#ff2d2d !important;min-width:0 !important;animation:neonRojo .8s ease-in-out infinite !important;}
  #barra.vacia{opacity:0 !important;animation:none !important;}
  @keyframes neonPulse{0%,100%{filter:brightness(1);}50%{filter:brightness(1.28);}}
  @keyframes neonRojo{0%,100%{opacity:1;filter:brightness(1.2);box-shadow:0 0 8px #fecaca,0 0 18px #ff2d2d,0 0 38px rgba(255,45,45,.9),0 0 70px rgba(255,0,0,.7);}50%{opacity:.7;filter:brightness(.9);box-shadow:0 0 4px #ff2d2d,0 0 10px rgba(255,45,45,.7),0 0 22px rgba(255,0,0,.5);}}
  /* Animación al cambiar titulo/sub/tiempo */
  .animar{animation:subirFade .55s ease;}
  @keyframes subirFade{0%{opacity:0;transform:translateY(22px) scale(.98);}100%{opacity:1;transform:translateY(0) scale(1);}}
  .flash{animation:flashBorde .6s ease;}
  @keyframes flashBorde{0%{box-shadow:0 0 0 6px #22c55e;}100%{box-shadow:0 10px 40px rgba(0,0,0,.65);}}
</style>
</head>
<body>
<div id="placa" class="oculta">
  <div id="barra-track"><div id="barra"></div></div>
  <div id="col-izq">
    <img id="logo" alt="logo">
  </div>
  <div id="contenido" style="flex:1">
    <div id="titulo">Bienvenida</div>
    <div id="sub">Todas las listas</div>
  </div>
  <div id="timer">00:30</div>
</div>
<script>
const VERS='v8';
const URL_STATE='http://127.0.0.1:8765/state';
const URL_CAMPANA='http://127.0.0.1:8765/sonido/campana';
const URL_TICTAC='http://127.0.0.1:8765/sonido/tictac';
const URL_INICIO='http://127.0.0.1:8765/sonido/inicio';
const URL_PING='http://127.0.0.1:8765/ping';
const KEY_OLD='debate2026_simple';
let lastRev=-1, lastTimer='', prevRest=null, lastDing=-1, lastCamp=-1, lastInicio=-1, audioOK=false;
// Audios reales: se controlan desde el mezclador de OBS (fuente Navegador)
const audioCampana=new Audio(URL_CAMPANA); audioCampana.preload='auto'; audioCampana.volume=1.0;
const audioTic=new Audio(URL_TICTAC); audioTic.preload='auto'; audioTic.volume=1.0; audioTic.loop=true;
const audioInicio=new Audio(URL_INICIO); audioInicio.preload='auto'; audioInicio.volume=1.0;
const logoEl=document.getElementById('logo');
const URL_LOGO='http://127.0.0.1:8765/logo';
let logoFails=0;
logoEl.onerror=()=>{ logoEl.style.display='none'; };
logoEl.onload=()=>{ logoEl.style.display='block'; logoFails=0; };
logoEl.src=URL_LOGO;
// Tic-tac sin cortes: loop gapless con Web Audio + fallback HTMLAudio
let actx=null, ticBuf=null, ticSrc=null, ticCargando=false;
function ctxAudio(){
  try{
    if(!actx){ const C=window.AudioContext||window.webkitAudioContext; if(!C) return null; actx=new C(); }
    if(actx.state==='suspended'){ try{const r=actx.resume(); if(r&&r.catch)r.catch(()=>{});}catch(e){} }
    return actx;
  }catch(e){ return null; }
}
function asegurarTic(){
  const c=ctxAudio(); if(!c||ticBuf||ticCargando) return;
  ticCargando=true;
  fetch(URL_TICTAC,{cache:'force-cache'}).then(r=>{ if(!r.ok) throw 0; return r.arrayBuffer(); })
    .then(ab=>c.decodeAudioData(ab)).then(b=>{ ticBuf=b; ticCargando=false; })
    .catch(()=>{ ticCargando=false; });
}
function ticStartWA(){
  const c=ctxAudio(); if(!c||!ticBuf) return false;
  try{
    if(ticSrc) return true;
    try{audioTic.pause();}catch(e){}
    ticSrc=c.createBufferSource(); ticSrc.buffer=ticBuf; ticSrc.loop=true;
    ticSrc.connect(c.destination); ticSrc.start(0); return true;
  }catch(e){ return false; }
}
function ticStopWA(){
  try{ if(ticSrc){ try{ticSrc.stop(0);}catch(e){} try{ticSrc.disconnect();}catch(e){} ticSrc=null; } }catch(e){}
}
asegurarTic();
let audioBloqueado=true, campEstado='?', ticEstado='?';
audioCampana.addEventListener('error', ()=>{ campEstado='error-carga'; try{ audioCampana.src=URL_CAMPANA+'?t='+Date.now(); audioCampana.load(); }catch(e){} });
audioInicio.addEventListener('error', ()=>{ try{ audioInicio.src=URL_INICIO+'?t='+Date.now(); audioInicio.load(); }catch(e){} });
function reintentarCampana(){
  // Si el <audio> precargado quedo en error o bloqueado, un elemento fresco
  // con cache-buster suele destrabarlo en CEF/Chrome.
  try{ const a=new Audio(URL_CAMPANA+'?t='+Date.now()); a.volume=1.0;
    const p=a.play(); if(p&&p.then) p.then(()=>{ campEstado='ok-reintento'; }).catch(()=>{});
  }catch(e){}
}
function desbloquearAudio(){
  try{
    ctxAudio();
    asegurarTic();
    // Intento silencioso para liberar autoplay en Chrome/CEF (OBS).
    [audioCampana, audioInicio, audioTic].forEach(a=>{
      try{
        a.muted=true;
        const p=a.play();
        if(p&&p.then)p.then(()=>{ try{a.pause();a.currentTime=0;}catch(e){} a.muted=false; audioBloqueado=false; }).catch(()=>{ try{a.pause();}catch(e){} a.muted=false; });
        else { a.muted=false; audioBloqueado=false; }
      }catch(e){ try{a.muted=false;}catch(_){} }
    });
  }catch(e){}
}
try{
  ['pointerdown','keydown','touchstart','mousedown'].forEach(ev=>window.addEventListener(ev, desbloquearAudio, {passive:true}));
  // Reintento periodico por si OBS cargo la pagina sin gesto del usuario.
  const _unlockTimer=setInterval(()=>{ if(!audioBloqueado){ try{clearInterval(_unlockTimer);}catch(e){} return; } desbloquearAudio(); }, 2000);
}catch(e){}
function sonarCampana(){
  // Audio automático para OBS: sin carteles, sin click. La fuente Navegador
  // debe tener "Controlar el audio mediante OBS".
  // NOTA: el mismo sonido tambien sale por parlantes Windows desde Python (MCI),
  // asi aunque el navegador bloquee autoplay igual se escucha en sala.
  try{ ctxAudio(); }catch(e){}
  try{
    audioCampana.muted=false;
    try{ audioCampana.currentTime=0; }catch(e){}
    const p=audioCampana.play();
    if(p&&p.then) p.then(()=>{ campEstado='ok'; }).catch(()=>{ campEstado='bloqueado'; reintentarCampana(); });
    else campEstado='ok';
  }catch(e){ campEstado='error'; reintentarCampana(); }
}
function sonarInicio(){
  // Mismo canal que la campana: sale por la fuente Navegador en OBS.
  // Duplicado en Windows via Python para oirlo en sala.
  try{ ctxAudio(); }catch(e){}
  try{
    audioInicio.muted=false;
    try{ audioInicio.currentTime=0; }catch(e){}
    const p=audioInicio.play();
    if(p&&p.catch) p.catch(()=>{ try{ const a=new Audio(URL_INICIO+'?t='+Date.now()); a.volume=1.0; const q=a.play(); if(q&&q.catch)q.catch(()=>{}); }catch(e){} });
  }catch(e){}
}
function aplicarTic(on){
  asegurarTic();
  try{
    if(on){
      if(ticStartWA()){ ticEstado='ok'; return; } // gapless: termina uno y empieza el otro sin bache
      if(audioTic.paused){ audioTic.muted=false; const p=audioTic.play(); if(p&&p.then)p.then(()=>{ticEstado='ok';}).catch(()=>{ticEstado='bloqueado';}); }
      else ticEstado='ok';
    }
    else { ticEstado='off'; ticStopWA(); try{audioTic.pause();}catch(e){} }
  }catch(e){}
}
// Beacon: avisa al programa que el overlay esta vivo y si el audio esta
// bloqueado, para diagnosticar la campana desde la ventana de control.
setInterval(()=>{
  try{ fetch(URL_PING,{method:'POST',headers:{'Content-Type':'text/plain'},
    body:JSON.stringify({vers:VERS,bloqueado:audioBloqueado,camp:campEstado,tic:ticEstado})}).catch(()=>{}); }catch(e){}
},2000);
function pintar(s){
  const esNuevo = s.rev !== lastRev;
  // Fin de cronómetro: antes >0 y ahora 0 -> campana en OBS
  if(prevRest!==null && prevRest>0 && s.restante===0){ sonarCampana(); }
  prevRest=s.restante;
  // Botón "Probar sonido" del control (compat)
  if(s.ding!==undefined && s.ding!==lastDing){ if(lastDing!==-1){ sonarCampana(); } lastDing=s.ding; }
  // Botón campana
  if(s.play_campana!==undefined && s.play_campana!==lastCamp){ if(lastCamp!==-1){ sonarCampana(); } lastCamp=s.play_campana; }
  // Inicio de cuenta: cada vez que se pulsa INICIAR suena el sonido de inicio
  if(s.play_inicio!==undefined && s.play_inicio!==lastInicio){ if(lastInicio!==-1){ sonarInicio(); } lastInicio=s.play_inicio; }
  // Tic-tac: con tilde solo ultimos 10s, sin tilde siempre que corre.
  // A 0:00 siempre corta (ahi suena la campana), igual que en la app.
  const autoOK = s.tic_auto!==false;
  const debeSonarTic = s.restante>0 && (!!s.tic_on || (!!s.corriendo && (autoOK ? s.restante<=10 : true)));
  aplicarTic(debeSonarTic);
  lastRev = s.rev;
  document.getElementById('titulo').textContent=s.titulo||'';
  document.getElementById('sub').textContent=s.sub||'';
  if(logoEl.style.display==='none'){ if(++logoFails%20===0){ logoEl.src=URL_LOGO+'?t='+Date.now(); } }
  const t=document.getElementById('timer');
  const m=String(Math.floor(s.restante/60)).padStart(2,'0');
  const sec=String(s.restante%60).padStart(2,'0');
  const txt=m+':'+sec;
  if(txt!==lastTimer){t.textContent=txt;lastTimer=txt;}
  const barra=document.getElementById('barra');
  const pct=s.total?(s.restante/s.total):1;
  /* timer sincronizado con la barrita: blanco -> amarillo -> rojo */
  t.classList.remove('amarillo','rojo');
  if(s.total&&pct<=0.25){ t.classList.add('rojo'); }
  else if(s.total&&pct<=0.5){ t.classList.add('amarillo'); }
  barra.style.width=(pct*100)+'%';
  barra.classList.remove('amarilla','roja','vacia');
  barra.style.boxShadow='';
  if(pct<=0){
    barra.classList.add('vacia');
    barra.style.background='transparent';
  }else if(!s.total||pct>0.5){
    barra.style.background='#ffffff';
  }else if(pct>0.25){
    barra.classList.add('amarilla');
    barra.style.background='#fde047';
  }else{
    barra.classList.add('roja');
    barra.style.background='#ff2d2d';
  }
  document.getElementById('placa').classList.toggle('oculta',!s.visible);
  if(esNuevo){
    const c=document.getElementById('contenido');
    const p=document.getElementById('placa');
    c.classList.remove('animar');void c.offsetWidth;c.classList.add('animar');
    p.classList.remove('flash');void p.offsetWidth;p.classList.add('flash');
    // Sin beep acá: el cambio de título es solo visual. El único sonido es fin de tiempo.
  }
}
async function leer(){
  try{
    const r=await fetch(URL_STATE,{cache:'no-store'});
    if(!r.ok)throw 0;
    pintar(await r.json());return;
  }catch(e){}
  try{ // fallback: control viejo por localStorage
    const raw=localStorage.getItem(KEY_OLD);
    if(raw){pintar(JSON.parse(raw));return;}
  }catch(e){}
  // Sin mensaje en pantalla: si no hay datos el overlay queda transparente.
}
setInterval(leer,250);leer();
</script>
</body>
</html>
"""

# ---------------- Audio local Windows (parlantes sala, sin pip) ----------------
# Dual: cada sonido sale por OBS (overlay HTML) Y por Windows (winmm MCI).
# Asi se escucha en el stream y en la sala aunque OBS este muteado.
# OJO: todo MCI pasa por _mci_lock y el tic arranca/para de forma SINCRONICA.
# (Antes el tic se abria en un hilo: si el stop llegaba antes del open,
# el "play repeat" quedaba sonando para siempre. Ese era el bug.)
_mci_lock = threading.RLock()


def _mci(cmd):
    try:
        with _mci_lock:
            ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    except Exception:
        pass


def reproducir_local(ruta, alias="debate_campana"):
    """Reproduce un mp3/wav por parlantes Windows sin bloquear la GUI."""
    def _run():
        try:
            if not ruta or not os.path.exists(ruta):
                return
            with _mci_lock:
                ctypes.windll.winmm.mciSendStringW("close " + alias, None, 0, None)
                ctypes.windll.winmm.mciSendStringW('open "%s" alias %s' % (ruta, alias), None, 0, None)
                ctypes.windll.winmm.mciSendStringW("play " + alias, None, 0, None)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


def detener_local(alias):
    _mci("stop " + alias)
    _mci("close " + alias)


def silenciar_todo_local():
    for _a in ("debate_tic", "debate_campana", "debate_inicio"):
        _mci("stop " + _a)
        _mci("close " + _a)


_tic_local_sonando = False
_tic_lock = threading.Lock()


def _tic_ruta():
    try:
        if os.path.exists(TICTAC_FILE):
            return TICTAC_FILE
    except Exception:
        pass
    return TICTAC_FILE


def _tic_debe_sonar():
    try:
        with lock:
            s = dict(state)
        if s.get("restante", 0) <= 0:
            return False  # a 0:00 el tic siempre corta (ahi suena la campana)
        if s.get("tic_on"):
            return True
        if not s.get("corriendo"):
            return False
        if s.get("tic_auto", True) is False:
            return True  # sin tilde: tic siempre mientras el cronometro corre
        return s.get("restante", 0) <= 10  # con tilde: solo ultimos 10s
    except Exception:
        return False


def actualizar_tic_local():
    """Arranca/para el tic-tac en parlantes Windows segun el estado (sincronico)."""
    global _tic_local_sonando
    debe = _tic_debe_sonar()
    with _tic_lock:
        if debe and not _tic_local_sonando:
            ruta = _tic_ruta()
            if os.path.exists(ruta):
                _mci("stop debate_tic")
                _mci("close debate_tic")
                _mci('open "%s" alias debate_tic' % ruta)
                _mci("play debate_tic repeat")
                _tic_local_sonando = True
        elif not debe and _tic_local_sonando:
            _tic_local_sonando = False
            _mci("stop debate_tic")
            _mci("close debate_tic")


def parar_tic_local():
    global _tic_local_sonando
    with _tic_lock:
        _tic_local_sonando = False
    _mci("stop debate_tic")
    _mci("close debate_tic")


# ---------------- Estado OBS (beacon del overlay) ----------------
# El overlay avisa cada 2s (POST /ping) si esta vivo y si el audio esta
# bloqueado por autoplay. La GUI lo muestra para diagnosticar la campana.
OVERLAY_VERS = "v8"
obs_status = {"t": 0.0, "vers": "", "bloqueado": None, "camp": "", "tic": "", "err": ""}
obs_lock = threading.Lock()


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
    ext = os.path.splitext(ruta)[1].lower()
    ctype = _AUDIO_MIMES.get(ext, "audio/mpeg")
    rango = handler.headers.get("Range")
    inicio, fin = 0, size - 1
    estado = 200
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
            inicio, fin = 0, size - 1
            estado = 200
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
    def do_POST(self):
        # Beacon del overlay: dice si esta vivo y si el audio esta bloqueado.
        if self.path.split("?")[0] == "/ping":
            try:
                largo = int(self.headers.get("Content-Length") or 0)
            except Exception:
                largo = 0
            try:
                raw = self.rfile.read(min(max(largo, 0), 4096)) if largo > 0 else b""
                info = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(info, dict):
                    info = {}
            except Exception:
                info = {}
            try:
                import time as _t
                with obs_lock:
                    obs_status["t"] = _t.time()
                    for _k in ("vers", "bloqueado", "camp", "tic", "err"):
                        if _k in info:
                            obs_status[_k] = info[_k]
            except Exception:
                pass
            body = b'{"ok":true}'
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                pass
            return
        self.send_response(404)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", "0")
        self.end_headers()
    def _atender(self, solo_headers=False):
        if self.path.startswith("/sonido/campana"):
            _servir_mp3(self, CAMPANA_FILE, solo_headers=solo_headers)
            return
        if self.path.startswith("/sonido/tictac"):
            _servir_mp3(self, TICTAC_FILE, solo_headers=solo_headers)
            return
        if self.path.startswith("/sonido/inicio"):
            # Búsqueda en vivo: si agregaste el mp3 con el programa abierto, lo toma sin reiniciar.
            _servir_mp3(self, _buscar_inicio())
            return
        if self.path.split("?")[0] == "/logo":
            ruta = _buscar_logo()
            try:
                with open(ruta, "rb") as f:
                    body = f.read()
            except FileNotFoundError:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                if not solo_headers:
                    try:
                        self.wfile.write(b"logo no encontrado: pone logo.png al lado del programa")
                    except Exception:
                        pass
                return
            ext = os.path.splitext(ruta)[1].lower()
            self.send_response(200)
            self.send_header("Content-Type", LOGO_MIMES.get(ext, "image/png"))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=60")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not solo_headers:
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
            return
        if self.path.startswith("/state"):
            with lock:
                data = dict(state)
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not solo_headers:
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
        elif self.path.startswith("/overlay"):
            body = OVERLAY_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not solo_headers:
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
        else:
            body = b'<meta charset="utf-8"><h2>Debate 2026 OK</h2><p>Overlay: <a href="/overlay">/overlay</a> | Estado: <a href="/state">/state</a></p>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not solo_headers:
                try:
                    self.wfile.write(body)
                except Exception:
                    pass

def iniciar_servidor():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def beep():
    # Compat: antes estaba desactivado. Ahora suena local (Windows) + OBS.
    try:
        reproducir_local(CAMPANA_FILE, alias="debate_campana")
    except Exception:
        pass

# ---------------- GUI Productor ----------------
# (badge_overlay, titulo_overlay, sub_overlay, seg, etiqueta_boton)
BLOQUES = [
    ("APERTURA / CIERRE", "#475569", [
        ("BIENVENIDA", "Bienvenida a todas las listas", "Reglas • Elecciones miércoles 30/09", 0, "★ Bienvenida"),
        ("CIERRE", "Cierre – Votación miércoles 30/09", "Gracias a todas las listas", 0, "■ Cierre"),
    ]),
    ("PRESENTACIÓN • 30s", "#1d4ed8", [
        ("PRESENTACIÓN L3", "Lista N°3 – Presentación", "30 segundos", 30, "L3\nPresentación"),
        ("PRESENTACIÓN L5", "Lista N°5 – Presentación", "30 segundos", 30, "L5\nPresentación"),
        ("PRESENTACIÓN L7", "Lista N°7 – Presentación", "30 segundos", 30, "L7\nPresentación"),
    ]),
    ("PROPUESTAS • 60s", "#15803d", [
        ("PROPUESTAS L3", "Lista N°3 – Propuestas", "1 minuto", 60, "L3\nPropuestas"),
        ("PROPUESTAS L5", "Lista N°5 – Propuestas", "1 minuto", 60, "L5\nPropuestas"),
        ("PROPUESTAS L7", "Lista N°7 – Propuestas", "1 minuto", 60, "L7\nPropuestas"),
    ]),
    ("MANO A MANO", "#b45309", [
        ("MANO A MANO", "Pregunta", "15 segundos • Sin réplica", 15, "❓ Pregunta\n15s"),
        ("MANO A MANO", "Respuesta", "45 segundos • Sin réplica", 45, "💬 Respuesta\n45s"),
        ("RÉPLICA", "Réplica Lista N°_", "45 segundos", 45, "↩ Réplica\n45s"),
    ]),
    ("DISCURSO • 60s", "#0e7490", [
        ("DISCURSO L3", "Lista N°3 – Discurso", "1 minuto", 60, "L3\nDiscurso"),
        ("DISCURSO L5", "Lista N°5 – Discurso", "1 minuto", 60, "L5\nDiscurso"),
        ("DISCURSO L7", "Lista N°7 – Discurso", "1 minuto", 60, "L7\nDiscurso"),
    ]),
]

class App:
    def __init__(self, root):
        self.root = root
        root.title("Control Productor – Debate 2026 v6 (OBS+PC)")
        root.configure(bg="#0b1220")
        root.geometry("970x900")
        # Scroll general: todo el contenido va dentro de "cuerpo"
        self.canvas = tk.Canvas(root, bg="#0b1220", highlightthickness=0)
        self.vsb = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        cuerpo = tk.Frame(self.canvas, bg="#0b1220")
        self._cuerpo_id = self.canvas.create_window((0, 0), window=cuerpo, anchor="nw")
        cuerpo.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._cuerpo_id, width=e.width))

        def _rueda(e):
            try:
                self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
            except Exception:
                pass
        self.canvas.bind_all("<MouseWheel>", _rueda)

        tk.Label(cuerpo, text="🎛️ CONTROL Productor – Debate 2026 v6 (OBS+PC)",
                 bg="#0b1220", fg="white", font=("Segoe UI", 16, "bold")).pack(pady=(10, 2))
        # Estado de sonidos: confirma que corre la versión nueva
        self.lbl_snd = tk.Label(cuerpo, text="Sonidos MP3: ...",
                 bg="#0b1220", fg="#94a3b8", font=("Segoe UI", 10, "bold"))
        self.lbl_snd.pack()
        self.actualizar_sonidos()
        # Estado del overlay en OBS (beacon cada 2s): dice si la campana llega.
        self.lbl_obs = tk.Label(cuerpo, text="OBS: ○ sin señal",
                 bg="#0b1220", fg="#94a3b8", font=("Segoe UI", 10, "bold"))
        self.lbl_obs.pack()
        url = f"http://127.0.0.1:{PORT}/overlay"
        fila = tk.Frame(cuerpo, bg="#0b1220"); fila.pack()
        tk.Label(fila, text="OBS local (sin wifi): marcá 'Archivo local' y elegí debate-obs-local.html",
                 bg="#0b1220", fg="#4ade80", font=("Segoe UI", 10, "bold")).pack()
        fila2 = tk.Frame(cuerpo, bg="#0b1220"); fila2.pack(pady=2)
        tk.Label(fila2, text="Respaldo: " + url,
                 bg="#0b1220", fg="#93c5fd", font=("Segoe UI", 9)).pack(side="left")
        tk.Button(fila2, text="Copiar URL", command=lambda: (root.clipboard_clear(), root.clipboard_append(url)),
                  bg="#38bdf8", font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)
        tk.Button(fila2, text="Abrir overlay", command=self.abrir_overlay,
                  bg="#facc15", font=("Segoe UI", 9, "bold")).pack(side="left")

        # 1. Títulos
        c1 = tk.LabelFrame(cuerpo, text="1. TÍTULO EN PANTALLA", bg="#111c33", fg="#facc15",
                           font=("Segoe UI", 11, "bold"))
        c1.pack(fill="x", padx=12, pady=8)
        for nombre_bloque, color_bloque, items in BLOQUES:
            fila_b = tk.Frame(c1, bg="#111c33")
            fila_b.pack(fill="x", padx=8, pady=(6, 0))
            tk.Label(fila_b, text=nombre_bloque, bg="#111c33", fg="#93c5fd",
                     font=("Segoe UI", 9, "bold"), width=20, anchor="w").pack(side="left")
            for (b, t, s, seg, etiqueta) in items:
                tk.Button(fila_b, text=etiqueta, width=16, height=2,
                          bg=color_bloque, fg="white", activebackground=color_bloque,
                          activeforeground="white", font=("Segoe UI", 10, "bold"),
                          justify="center",
                          command=lambda b=b, t=t, s=s, seg=seg: self.poner_preset(b, t, s, seg)
                          ).pack(side="left", padx=4, pady=2)

        f2 = tk.Frame(c1, bg="#111c33"); f2.pack(fill="x", padx=8, pady=(0, 8))
        self.e_titulo = tk.Entry(f2, font=("Segoe UI", 11), bg="#020617", fg="white", insertbackground="white")
        self.e_titulo.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.e_titulo.insert(0, "Título personalizado...")
        self.e_sub = tk.Entry(f2, font=("Segoe UI", 11), bg="#020617", fg="white", insertbackground="white")
        self.e_sub.pack(side="left", fill="x", expand=True, padx=4)
        self.e_sub.insert(0, "Subtítulo...")
        tk.Button(f2, text="Poner ✓", bg="#facc15", font=("Segoe UI", 10, "bold"),
                  command=self.poner_custom).pack(side="left", padx=4)

        # 2. Tiempo
        c2 = tk.LabelFrame(cuerpo, text="2. TIEMPO", bg="#111c33", fg="#facc15", font=("Segoe UI", 11, "bold"))
        c2.pack(fill="x", padx=12, pady=4)
        ft = tk.Frame(c2, bg="#111c33"); ft.pack(pady=6)
        for txt, seg in [("15s pregunta", 15), ("30s presentación", 30), ("45s réplica", 45), ("60s discurso", 60)]:
            tk.Button(ft, text=txt, bg="#38bdf8", font=("Segoe UI", 10, "bold"),
                      command=lambda v=seg: self.set_tiempo(v)).pack(side="left", padx=4)
        self.e_seg = tk.Entry(ft, width=6, font=("Segoe UI", 11), bg="#020617", fg="white", justify="center")
        self.e_seg.pack(side="left", padx=(10, 4)); self.e_seg.insert(0, "30")
        tk.Button(ft, text="Cargar", bg="#475569", fg="white", font=("Segoe UI", 10, "bold"),
                  command=lambda: self.set_tiempo(int(self.e_seg.get() or 30))).pack(side="left")

        # Timer GRANDE: blanco sobre negro (arregla negro sobre negro)
        self.lbl_timer = tk.Label(c2, text="00:30", bg="#000000", fg="#ffffff",
                                  font=("Segoe UI", 52, "bold"), width=7)
        self.lbl_timer.pack(pady=4)

        fc = tk.Frame(c2, bg="#111c33"); fc.pack(pady=4)
        self.btn_play = tk.Button(fc, text="▶ INICIAR", bg="#22c55e", fg="#052e16",
                                  font=("Segoe UI", 13, "bold"), width=12, command=self.toggle)
        self.btn_play.pack(side="left", padx=4)
        tk.Button(fc, text="↺", bg="#475569", fg="white", font=("Segoe UI", 13, "bold"),
                  command=self.reiniciar).pack(side="left", padx=4)
        tk.Button(fc, text="+5s", bg="#f59e0b", font=("Segoe UI", 13, "bold"),
                  command=lambda: self.ajustar(5)).pack(side="left", padx=4)
        tk.Button(fc, text="-5s", bg="#475569", fg="white", font=("Segoe UI", 11, "bold"),
                  command=lambda: self.ajustar(-5)).pack(side="left", padx=4)
        self.btn_vis = tk.Button(fc, text="👁 OCULTAR", bg="#334155", fg="white",
                                 font=("Segoe UI", 11, "bold"), command=self.toggle_vis)
        self.btn_vis.pack(side="left", padx=4)
        tk.Button(fc, text="🔊 Probar sonido (OBS+PC)", bg="#a78bfa", fg="#1e1b4b",
                  font=("Segoe UI", 11, "bold"), command=self.probar_sonido).pack(side="left", padx=4)

        # 3. Sonidos (DUAL: salen por la fuente Navegador en OBS Y por parlantes Windows)
        cS = tk.LabelFrame(cuerpo, text="3. SONIDOS (salen por OBS + parlantes Windows)", bg="#111c33", fg="#facc15",
                           font=("Segoe UI", 11, "bold"))
        cS.pack(fill="x", padx=12, pady=4)
        fS = tk.Frame(cS, bg="#111c33"); fS.pack(pady=6)
        tk.Button(fS, text="🔔 Campana fin", bg="#facc15", fg="#111",
                  font=("Segoe UI", 11, "bold"), command=self.sonar_campana).pack(side="left", padx=4)
        tk.Button(fS, text="⏵ Probar inicio", bg="#22c55e", fg="#052e16",
                  font=("Segoe UI", 11, "bold"), command=self.probar_inicio).pack(side="left", padx=4)
        self.tic_auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(fS, text="Tic-tac solo últimos 10s", variable=self.tic_auto_var,
                       bg="#111c33", fg="#4ade80", selectcolor="#111c33",
                       font=("Segoe UI", 10, "bold"), command=self.toggle_tic_auto).pack(side="left", padx=4)
        self.btn_tic = tk.Button(fS, text="⏱ Forzar tic: OFF", bg="#334155", fg="white",
                                 font=("Segoe UI", 10, "bold"), command=self.toggle_tic)
        self.btn_tic.pack(side="left", padx=4)
        tk.Button(fS, text="🔇 Silenciar todo", bg="#ef4444", fg="white",
                  font=("Segoe UI", 10, "bold"), command=self.silenciar_todo).pack(side="left", padx=4)
        tk.Label(fS, text="Campana a 0:00 • Tic: ✓=últimos 10s / ☐=siempre",
                 bg="#111c33", fg="#94a3b8", font=("Segoe UI", 9)).pack(side="left", padx=8)

        # Vista previa + confirmación
        c3 = tk.LabelFrame(cuerpo, text="VISTA PREVIA + CONFIRMACIÓN", bg="#111c33", fg="#facc15",
                           font=("Segoe UI", 11, "bold"))
        c3.pack(fill="x", padx=12, pady=4)
        self.prev = tk.Frame(c3, bg="#020617"); self.prev.pack(fill="x", padx=8, pady=8)
        self.prev_badge = tk.Label(self.prev, text="BIENVENIDA", bg="#38bdf8", fg="#111",
                                   font=("Segoe UI", 13, "bold"))
        self.prev_badge.pack(anchor="w", padx=10, pady=(8, 0))
        self.prev_titulo = tk.Label(self.prev, text="", bg="#020617", fg="white",
                                    font=("Segoe UI", 17, "bold"), wraplength=700, justify="left")
        self.prev_titulo.pack(anchor="w", padx=10)
        self.prev_sub = tk.Label(self.prev, text="", bg="#020617", fg="#bfdbfe", font=("Segoe UI", 13))
        self.prev_sub.pack(anchor="w", padx=10, pady=(0, 8))
        self.status = tk.Label(cuerpo, text="Listo. Tocá un título y después INICIAR.",
                               bg="#0b1220", fg="#94a3b8", font=("Segoe UI", 11, "bold"))
        self.status.pack(pady=4)

        root.bind("<space>", lambda e: self.toggle())
        self.tick()
        self.refrescar()

    def actualizar_sonidos(self):
        # Re-busca el sonido de inicio (por si lo agregaste con el programa abierto)
        # y actualiza la etiqueta de estado. Devuelve True si está el inicio.
        global INICIO_FILE
        INICIO_FILE = _buscar_inicio()
        try:
            c_ok = os.path.exists(CAMPANA_FILE)
            t_ok = os.path.exists(TICTAC_FILE)
            i_ok = os.path.exists(INICIO_FILE)
            c_kb = os.path.getsize(CAMPANA_FILE) // 1024 if c_ok else 0
            t_kb = os.path.getsize(TICTAC_FILE) // 1024 if t_ok else 0
            i_kb = os.path.getsize(INICIO_FILE) // 1024 if i_ok else 0
            if i_ok:
                i_txt = f"✓ inicio ({os.path.basename(INICIO_FILE)} {i_kb}KB)"
            else:
                i_txt = "✗ inicio (poné un mp3 con 'inicio' en el nombre)"
            snd_txt = f"{'✓' if c_ok else '✗'} campana ({c_kb}KB)  {'✓' if t_ok else '✗'} tic-tac ({t_kb}KB)  {i_txt}"
            snd_fg = "#4ade80" if (c_ok and t_ok and i_ok) else "#f87171"
        except Exception:
            snd_txt, snd_fg = "Sonidos MP3: ?", "#94a3b8"
            i_ok = False
        try:
            self.lbl_snd.config(text="Sonidos MP3: " + snd_txt, fg=snd_fg)
        except Exception:
            pass
        return i_ok

    def abrir_overlay(self):
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}/overlay")

    def confirm(self, msg):
        # Confirmación visible: verde + ✓ por 1.6s
        self.status.config(text="✓ " + msg, fg="#052e16", bg="#22c55e")
        self.prev.config(bg="#052e16")
        self.root.after(1600, lambda: (self.status.config(bg="#0b1220", fg="#94a3b8"),
                                       self.prev.config(bg="#020617")))

    def poner_preset(self, b, t, s, seg):
        with lock:
            state["badge"] = b; state["titulo"] = t; state["sub"] = s
            if seg:
                state["total"] = seg; state["restante"] = seg; state["base"] = seg
            state["corriendo"] = False
            bump_rev()
        self.confirm(f"Enviado al overlay: {b} | {t}" + (f" • {seg}s" if seg else ""))
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def poner_custom(self):
        t = self.e_titulo.get().strip(); s = self.e_sub.get().strip()
        with lock:
            if t and not t.startswith("Título"):
                state["titulo"] = t
            if s and not s.startswith("Subtítulo"):
                state["sub"] = s
            # OJO: no se toca state["corriendo"] -> cambiar título/sub
            # en vivo NO detiene el reloj
            bump_rev()
        self.confirm("Título personalizado enviado ✓")
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def set_tiempo(self, v):
        v = max(5, min(600, int(v)))
        with lock:
            state["total"] = v; state["restante"] = v; state["base"] = v; state["corriendo"] = False
            bump_rev()
        self.confirm(f"Tiempo cargado: {v}s ✓")
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def toggle(self):
        arranco = False
        with lock:
            if state["corriendo"]:
                state["corriendo"] = False
            else:
                if state["restante"] <= 0:
                    b = state.get("base", state["total"])
                    state["restante"] = b; state["total"] = b
                state["corriendo"] = True
                state["play_inicio"] = state.get("play_inicio", 0) + 1
                arranco = True
        if arranco:
            # DUAL: inicio suena en OBS (play_inicio) y en parlantes Windows (MCI).
            try:
                reproducir_local(_buscar_inicio(), alias="debate_inicio")
            except Exception:
                pass
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def reiniciar(self):
        with lock:
            b = state.get("base", state["total"])
            state["restante"] = b; state["total"] = b; state["corriendo"] = False
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def ajustar(self, d):
        termino = False
        with lock:
            estaba = bool(state["corriendo"] and state["restante"] > 0)
            state["restante"] = max(0, state["restante"] + d)
            state["total"] = max(state["total"], state["restante"])
            # OJO: no tocamos state["base" ] -> ↺ vuelve al tiempo cargado, sin los +5/-5
            if state["restante"] <= 0:
                state["corriendo"] = False
                termino = estaba
        if termino:
            try:
                parar_tic_local()
            except Exception:
                pass
            try:
                reproducir_local(CAMPANA_FILE, alias="debate_campana")
            except Exception:
                pass
            self.confirm("⏰ ¡TIEMPO!")
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def toggle_vis(self):
        with lock:
            state["visible"] = not state["visible"]
            bump_rev()
        self.refrescar()

    def probar_sonido(self):
        self.sonar_campana()

    def probar_inicio(self):
        hay = self.actualizar_sonidos()
        if not hay:
            self.confirm("✗ Sin archivo de inicio (mp3 con 'inicio' en el nombre)")
            self.status.config(fg="#f87171", bg="#0b1220")
            return
        with lock:
            state["play_inicio"] = state.get("play_inicio", 0) + 1
        # DUAL: OBS + parlantes Windows.
        try:
            reproducir_local(_buscar_inicio(), alias="debate_inicio")
        except Exception:
            pass
        self.confirm("⏵ Inicio en OBS + parlantes (mirál el mezclador)")
        self.refrescar()

    def sonar_campana(self):
        with lock:
            # Solo play_campana: antes se subian ding Y play_campana y el overlay
            # sonaba dos veces superpuestas.
            state["play_campana"] += 1
        # DUAL: campana en OBS (play_campana) y en parlantes Windows (MCI).
        try:
            reproducir_local(CAMPANA_FILE, alias="debate_campana")
        except Exception:
            pass
        self.confirm("🔔 Campana en OBS + parlantes (mirál el mezclador)")
        self.refrescar()

    def toggle_tic(self):
        with lock:
            state["tic_on"] = not state["tic_on"]
        self.confirm("⏱ Tic-tac manual " + ("FORZADO (suena aunque esté pausado)" if state["tic_on"] else "off (queda solo el auto)"))
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def toggle_tic_auto(self):
        with lock:
            state["tic_auto"] = bool(self.tic_auto_var.get())
            # Si se apaga el auto y el contador está parado, cortar forzosamente
            if not state["tic_auto"] and not state["tic_on"] and not state["corriendo"]:
                pass
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def silenciar_todo(self):
        # Corte de emergencia: para tic/campana/inicio locales y desactiva el forzado.
        with lock:
            state["tic_on"] = False
            state["corriendo"] = False
        try:
            parar_tic_local()
        except Exception:
            pass
        try:
            silenciar_todo_local()
        except Exception:
            pass
        self.confirm("🔇 Todo silenciado (tic OFF, audio local cortado)")
        self.refrescar()
        try:
            actualizar_tic_local()
        except Exception:
            pass

    def refrescar(self):
        with lock:
            s = dict(state)
        m, r = divmod(s["restante"], 60)
        txt = f"{m:02d}:{r:02d}"
        self.lbl_timer.config(text=txt,
                              fg="#ff6b6b" if (s["restante"] <= 10 and s["total"] > 0) else "#ffffff")
        self.btn_play.config(text="⏸ PAUSAR" if s["corriendo"] else "▶ INICIAR")
        self.btn_vis.config(text="👁 OCULTAR" if s["visible"] else "👁 MOSTRAR")
        self.btn_tic.config(text="⏱ Forzar tic: ON" if s.get("tic_on") else "⏱ Forzar tic: OFF",
                            bg="#22c55e" if s.get("tic_on") else "#334155")
        try:
            self.tic_auto_var.set(bool(s.get("tic_auto", True)))
        except Exception:
            pass
        self.prev_badge.config(text=s["badge"])
        self.prev_titulo.config(text=s["titulo"])
        self.prev_sub.config(text=s["sub"])
        self._refrescar_obs()

    def _refrescar_obs(self):
        # Semáforo del overlay: sin señal / overlay viejo / audio bloqueado / OK.
        try:
            import time as _t
            with obs_lock:
                o = dict(obs_status)
            hace = _t.time() - o.get("t", 0)
            if not o.get("t"):
                txt, fg = "OBS: ○ sin señal — recargá la fuente Navegador en OBS", "#94a3b8"
            elif hace > 6:
                txt, fg = "OBS: ○ sin señal (>6s) — ¿cerraste el overlay o el OBS?", "#f87171"
            elif o.get("vers") and o.get("vers") != OVERLAY_VERS:
                txt, fg = ("OBS: ● conectado pero overlay VIEJO (%s) — recargá la fuente (Interactuar → Ctrl+R)"
                           % o.get("vers")), "#facc15"
            elif o.get("bloqueado") or (isinstance(o.get("camp"), str) and "bloq" in o.get("camp")):
                txt, fg = ("OBS: ● conectado — audio BLOQUEADO por el navegador: abrí el overlay y hacé 1 clic "
                           "(o en OBS: Interactuar → clic), con la campana sonando"), "#facc15"
            elif o.get("camp", "") in ("ok", "ok-reintento"):
                txt, fg = "OBS: ● conectado — audio OK (campana verificada)", "#4ade80"
            else:
                txt, fg = "OBS: ● conectado — esperando 1er sonido para verificar audio…", "#93c5fd"
            self.lbl_obs.config(text=txt, fg=fg)
        except Exception:
            pass

    def tick(self):
        termino = False
        with lock:
            if state["corriendo"] and state["restante"] > 0:
                state["restante"] -= 1
                if state["restante"] == 0:
                    state["corriendo"] = False
                    termino = True
        if termino:
            # Primero cortar el tic local y despues la campana dual.
            # (El overlay dispara su campana al ver la transicion a 0.)
            try:
                parar_tic_local()
            except Exception:
                pass
            try:
                reproducir_local(CAMPANA_FILE, alias="debate_campana")
            except Exception:
                pass
            self.confirm("⏰ ¡TIEMPO!")
        try:
            actualizar_tic_local()
        except Exception:
            pass
        self.refrescar()
        self.root.after(1000, self.tick)


def main():
    iniciar_servidor()
    print(f"Servidor overlay en http://127.0.0.1:{PORT}/overlay")
    root = tk.Tk()
    try:
        import ctypes as _ct
        _ct.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    def _cerrar():
        try:
            with lock:
                state["tic_on"] = False
                state["corriendo"] = False
            parar_tic_local()
            silenciar_todo_local()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
    try:
        root.protocol("WM_DELETE_WINDOW", _cerrar)
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
