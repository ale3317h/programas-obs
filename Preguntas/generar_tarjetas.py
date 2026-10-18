#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_tarjetas.py  -  Chicos VS Chicas (IA-4 Arte)

Genera las 16 tarjetas de comodines (1024x1024, PNG, REDONDAS, transparente
fuera del circulo) en la carpeta  tarjetas/  que esta junto a este script.

Nombres (CONTRATO.md, seccion 4):
    {chicos|chicas}_{llamada|saltar|cambiar|5050}_{activa|apagada}.png

Requisitos: Python 3 + Pillow  (pip install pillow). Sin internet.
Uso:  python generar_tarjetas.py
"""
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OUT = 1024          # tamano final
SS = 2              # supersampling (se dibuja a 2048 y se reduce: bordes suaves)
S = OUT * SS
C = S // 2          # centro

EQUIPOS = {
    # main = color del neon, light = color claro (nucleo del trazo)
    "chicos": {"main": (30, 91, 255), "light": (56, 189, 248)},   # #1E5BFF / #38bdf8
    "chicas": {"main": (230, 0, 126), "light": (255, 43, 176)},   # #E6007E / #ff2bb0
}
COMODINES = ["llamada", "saltar", "cambiar", "5050"]

R_CLIP = int(S * 0.495)    # nada se dibuja fuera de este circulo
R_RING = int(S * 0.455)    # radio central del aro neon
W_RING = int(S * 0.030)    # grosor del aro
W = int(S * 0.062)         # grosor de trazo de los iconos


# ----------------------------------------------------------------- utilidades
def mezclar(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def capa():
    """Mascara 'L' vacia donde se dibuja la forma de un icono."""
    return Image.new("L", (S, S), 0)


def linea(d, p, q, w=W, fill=255):
    d.line([p, q], fill=fill, width=w)
    r = w / 2
    for x, y in (p, q):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def polilinea(d, pts, w=W, fill=255):
    for i in range(len(pts) - 1):
        linea(d, pts[i], pts[i + 1], w, fill)


def arco(d, cx, cy, r, a0, a1, w=W, fill=255):
    """Arco con puntas redondas. Angulos en grados, sentido horario (como PIL)."""
    ro = r + w / 2    # PIL dibuja el grosor hacia adentro: usamos el radio exterior
    d.arc([cx - ro, cy - ro, cx + ro, cy + ro], a0, a1, fill=fill, width=int(w))
    rr = w / 2
    for a in (a0, a1):
        x = cx + r * math.cos(math.radians(a))
        y = cy + r * math.sin(math.radians(a))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=fill)


def poligono_redondo(d, pts, w=int(W * 0.7), fill=255):
    """Poligono relleno con esquinas redondeadas (relleno + contorno redondo)."""
    d.polygon(pts, fill=fill)
    polilinea(d, list(pts) + [pts[0]], w, fill)


def rotar(m, grados, centro=(C, C)):
    return m.rotate(grados, resample=Image.BICUBIC, center=centro)


def mover(m, dx, dy):
    return ImageChops.offset(m, int(dx), int(dy))


def fuente(tam):
    """Fuente gruesa: busca varias (Windows / Linux / Mac); si no, la de Pillow."""
    candidatas = [
        "arialbd.ttf", "Arial Bold.ttf", "segoeuib.ttf", "calibrib.ttf",
        "verdanab.ttf", "impact.ttf",
        "DejaVuSans-Bold.ttf", "Poppins-Bold.ttf", "LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for nombre in candidatas:
        try:
            return ImageFont.truetype(nombre, tam)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:
        return ImageFont.load_default()


# -------------------------------------------------------------------- iconos
# Los iconos se disenan en unidades de 1024x1024 (D = unidades -> pixeles de trabajo).
def D(v):
    return int(round(v * SS))


def P(x, y):
    return (D(x), D(y))


def suavizar(m, radio):
    """Redondea esquinas y empalmes (desenfoque + umbral): forma organica, sin picos."""
    chica = m.resize((S // 2, S // 2), Image.BILINEAR).filter(ImageFilter.GaussianBlur(radio))
    chica = chica.point(lambda v: 255 if v > 128 else 0)
    return chica.resize((S, S), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))


def centrar(m, cx=512, cy=512):
    """Mueve la forma para que el centro de su caja quede en (cx, cy) de 1024."""
    bb = m.getbbox()
    if not bb:
        return m
    return mover(m, D(cx) - (bb[0] + bb[2]) // 2, D(cy) - (bb[1] + bb[3]) // 2)


# Silueta del telefono clasico (auricular + 3 ondas), vectorizada: 4 poligonos en un
# cuadro de 1000 unidades centrado en (0,0). Auricular = el poligono grande; ondas = los otros 3.
TELEFONO = [[[-19,-220],[-28,-208],[-29,-195],[-25,-185],[-18,-178],[-6,-174],[16,-173],[42,-168],[69,-158],[94,-144],[124,-117],[142,-93],[157,-61],[166,-20],[167,6],[171,16],[185,26],[197,26],[205,22],[211,15],[216,0],[216,-26],[212,-60],[204,-87],[190,-115],[175,-138],[156,-161],[134,-181],[109,-197],[84,-209],[57,-219],[12,-226],[-4,-226]],[[-420,-315],[-442,-294],[-454,-276],[-470,-247],[-484,-207],[-491,-163],[-491,-133],[-486,-111],[-483,-81],[-469,-34],[-453,4],[-406,93],[-370,145],[-343,180],[-276,257],[-216,314],[-169,354],[-112,396],[-62,428],[-21,450],[16,468],[62,484],[89,492],[131,499],[179,500],[200,494],[218,492],[244,483],[285,462],[309,444],[332,418],[353,378],[361,347],[361,307],[354,290],[317,262],[242,217],[184,192],[157,186],[137,188],[121,197],[84,262],[75,274],[61,286],[52,288],[37,284],[0,260],[-84,183],[-175,92],[-244,16],[-268,-15],[-276,-32],[-278,-49],[-272,-62],[-252,-77],[-193,-109],[-182,-121],[-177,-135],[-177,-153],[-183,-176],[-201,-219],[-239,-287],[-271,-335],[-284,-349],[-290,-352],[-342,-353],[-374,-345],[-404,-329]],[[-31,-357],[-41,-342],[-40,-328],[-31,-316],[-16,-310],[55,-307],[108,-290],[163,-261],[196,-236],[219,-212],[251,-170],[273,-130],[281,-107],[291,-74],[296,-30],[296,0],[300,12],[306,19],[317,25],[326,25],[337,19],[343,13],[346,0],[345,-64],[337,-104],[320,-151],[304,-184],[283,-216],[254,-252],[226,-278],[187,-308],[149,-329],[111,-345],[87,-352],[68,-354],[45,-361],[-20,-361]],[[-47,-486],[-50,-479],[-50,-465],[-45,-455],[-37,-449],[-30,-448],[36,-447],[67,-440],[83,-440],[103,-433],[118,-431],[162,-415],[210,-392],[241,-374],[283,-343],[323,-304],[343,-281],[366,-249],[398,-193],[414,-154],[431,-97],[433,-69],[440,-33],[440,14],[444,24],[454,33],[463,34],[474,33],[484,24],[491,7],[491,-33],[485,-68],[485,-90],[479,-112],[477,-130],[460,-181],[427,-251],[401,-292],[377,-323],[340,-363],[291,-404],[242,-435],[190,-461],[143,-478],[89,-492],[58,-494],[29,-500],[-25,-500],[-37,-495]]]


def icono_llamada():
    """Telefono clasico relleno (auricular grueso) con 3 ondas de sonido."""
    m = capa()
    d = ImageDraw.Draw(m)
    esc = 0.64                                  # tamano del icono dentro del circulo
    for poli in TELEFONO:
        d.polygon([P(512 + x * esc, 512 + y * esc) for x, y in poli], fill=255)
    m = suavizar(m, D(4) / 2)                 # esquinas y puntas redondeadas, bordes limpios
    return centrar(m)


def icono_saltar():
    """Dos chevrones huecos (>>), borde grueso y esquinas redondeadas, centrados."""
    m = capa()
    d = ImageDraw.Draw(m)
    # chevron base (coordenadas del modelo, 512x512): cola plana arriba y abajo, punta a la derecha
    base = [(30, 65), (100, 65), (285, 245), (100, 425), (30, 425), (190, 245)]
    K = 1.30
    for dx in (0, 200):
        pts = [P(512 + (x + dx - 255) * K, 512 + (y - 245) * K) for x, y in base]
        polilinea(d, pts + [pts[0], pts[1]], w=D(26))
    return mover(centrar(m), D(32), 0)   # empujon optico: las puntas pesan menos que las colas


def punta_flecha(d, x, y, ang_deg, tam=D(130), w=D(34)):
    """Triangulo de flecha con base en (x,y) apuntando hacia ang_deg."""
    a = math.radians(ang_deg)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    p0 = (x + ux * tam * 0.95, y + uy * tam * 0.95)
    p1 = (x + nx * tam * 0.8, y + ny * tam * 0.8)
    p2 = (x - nx * tam * 0.8, y - ny * tam * 0.8)
    poligono_redondo(d, [p0, p1, p2], w=w)


def icono_cambiar():
    """Dos flechas circulares (ciclo)."""
    m = capa()
    d = ImageDraw.Draw(m)
    r = 232
    for base in (0, 180):
        a0, a1 = base + 205, base + 328
        arco(d, D(512), D(512), D(r), a0, a1, w=D(54))
        ex = 512 + r * math.cos(math.radians(a1))
        ey = 512 + r * math.sin(math.radians(a1))
        punta_flecha(d, D(ex), D(ey), a1 + 90, tam=D(118))
    return m


def icono_5050():
    """'50' arriba-izquierda, '50' abajo-derecha y una barra diagonal en medio."""
    m = capa()
    d = ImageDraw.Draw(m)
    f = fuente(D(330))
    for (cx, cy) in ((385, 375), (640, 655)):
        d.text(P(cx, cy), "50", font=f, fill=255, anchor="mm",
               stroke_width=D(5), stroke_fill=255)
    linea(d, P(735, 205), P(290, 820), w=D(34))
    return m


ICONOS = {"llamada": icono_llamada, "saltar": icono_saltar,
          "cambiar": icono_cambiar, "5050": icono_5050}


# ------------------------------------------------------------------ render
def pintar(img, mascara, color):
    """Pinta 'color' sobre img usando 'mascara' (L) como transparencia."""
    capa_c = Image.new("RGBA", (S, S), tuple(color) + (255,))
    capa_c.putalpha(mascara)
    img.alpha_composite(capa_c)


def glow(img, mascara, color, radios=(34, 15, 6), fuerza=(1.0, 1.0, 1.0)):
    """Suma resplandor neon del color dado alrededor de la mascara.
    El desenfoque se hace a 1/4 de resolucion (rapido) y se reescala."""
    chica = mascara.resize((S // 4, S // 4), Image.BILINEAR)
    for rad, k in zip(radios, fuerza):
        b = chica.filter(ImageFilter.GaussianBlur(rad / 2))
        b = b.point(lambda v, k=k: min(255, int(v * 2.6 * k)))
        pintar(img, b.resize((S, S), Image.BILINEAR), color)


def neon(img, mascara, main, light):
    glow(img, mascara, main)
    pintar(img, mascara, mezclar(light, (255, 255, 255), 0.55))


def circulo_mascara(r):
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([C - r, C - r, C + r, C + r], fill=255)
    return m


def aro_mascara():
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([C - R_RING, C - R_RING, C + R_RING, C + R_RING],
                              outline=255, width=W_RING)
    return m


def tarjeta(equipo, comodin, activa):
    col = EQUIPOS[equipo]
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # fondo negro redondo
    pintar(img, circulo_mascara(R_RING + W_RING // 2), (0, 0, 0))
    icono = ICONOS[comodin]()

    if activa:
        neon(img, aro_mascara(), col["main"], col["light"])
        neon(img, icono, col["main"], col["light"])
    else:
        gris_aro, gris_ico, gris_x = (58, 58, 62), (78, 78, 84), (150, 150, 156)
        pintar(img, aro_mascara(), gris_aro)
        pintar(img, icono, gris_ico)
        # X grande, clara, con borde oscuro para separarla del icono
        x = capa()
        dx = ImageDraw.Draw(x)
        o = int(S * 0.155)
        linea(dx, (C - o, C - o), (C + o, C + o), w=int(W * 1.2))
        linea(dx, (C - o, C + o), (C + o, C - o), w=int(W * 1.2))
        borde = x.filter(ImageFilter.GaussianBlur(10)).point(lambda v: 255 if v > 20 else 0)
        pintar(img, borde, (8, 8, 10))
        pintar(img, x, gris_x)

    # recorte final: transparente fuera del circulo
    recorte = circulo_mascara(R_CLIP)
    a = ImageChops.multiply(img.getchannel("A"), recorte)
    img.putalpha(a)
    return img.resize((OUT, OUT), Image.LANCZOS)


def main():
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tarjetas")
    os.makedirs(carpeta, exist_ok=True)
    n = 0
    for equipo in EQUIPOS:
        for comodin in COMODINES:
            for estado in ("activa", "apagada"):
                nombre = f"{equipo}_{comodin}_{estado}.png"
                tarjeta(equipo, comodin, estado == "activa").save(
                    os.path.join(carpeta, nombre), optimize=True)
                n += 1
                print("OK", nombre)
    print(f"\nListo: {n} tarjetas en {carpeta}")


if __name__ == "__main__":
    sys.exit(main())
