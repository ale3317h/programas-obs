#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida preguntas_banco.json contra el CONTRATO v4.

Uso:
    python validar_banco.py                 # valida el banco de esta carpeta
    python validar_banco.py ruta.json       # valida otro archivo
    python validar_banco.py --strict        # los avisos tambien hacen fallar

Sale con:
    0 = el banco sirve (puede tener avisos, si no es --strict)
    1 = errores (el motor no lo podria cargar, o no cumple el contrato)
    2 = no pudo importar el motor

La validacion de estructura (tipos, opciones, ids, textos largos) la hace el
propio motor con cargar_banco(); aca se agregan los chequeos del contrato:
orden de rondas, rebote solo en la final, Matematica por aproximacion,
reservas para "cambiar", 3 temas en r3, comodines por ronda y conteos.
"""
import argparse
import os
import sys

sys.dont_write_bytecode = True          # no ensuciar la carpeta con __pycache__
AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

ORDEN = ["r1", "r2", "r3", "mate", "r4", "final", "desempate"]
COMODINES_ESPERADOS = {
    "r1": {"llamada", "saltar", "cambiar", "5050"},
    "r2": {"llamada", "saltar", "cambiar", "5050"},
    "r3": {"llamada", "saltar", "cambiar"},
    "mate": set(),
    "r4": {"llamada", "saltar", "cambiar"},
    "final": set(),
    "desempate": set(),
}
# Conteos con los que estan armados el guion y las tarjetas (banco del 18/10).
CONTEOS_ESPERADOS = {
    "r1": (8, 2),
    "r2": (8, 2),
    "mate": (7, 3),
    "r4": (5, 2),
    "final": (6, 0),
    "desempate": (4, 0),
}
TEMAS_R3 = 3
PREGUNTAS_POR_TEMA = 4
RESERVAS_POR_TEMA = 3


def conteo(ronda):
    """-> (preguntas, reservas) de una ronda, sumando temas si es por_tema."""
    if ronda["orden"] == "por_tema":
        return (sum(len(t["preguntas"]) for t in ronda["temas"]),
                sum(len(t["reservas"]) for t in ronda["temas"]))
    return len(ronda["preguntas"]), len(ronda["reservas"])


def textos(ronda):
    """-> lista de textos de pregunta de una ronda (para buscar repetidas)."""
    if ronda["orden"] == "por_tema":
        return [p["q"] for t in ronda["temas"] for p in t["preguntas"]]
    return [p["q"] for p in ronda["preguntas"]]


def main():
    ap = argparse.ArgumentParser(description="Valida el banco de Preguntas (contrato v4).")
    ap.add_argument("ruta", nargs="?", default=os.path.join(AQUI, "preguntas_banco.json"))
    ap.add_argument("--strict", action="store_true", help="los avisos tambien hacen fallar")
    a = ap.parse_args()

    try:
        from preguntas_control import cargar_banco
    except Exception as e:                                  # pragma: no cover
        print("ERROR: no pude importar preguntas_control.py:", e)
        return 2

    print("Banco:", a.ruta)
    try:
        banco, avisos_motor = cargar_banco(a.ruta)
    except ValueError as e:
        print("ERROR:", e)
        print("\nResultado: NO SIRVE (el motor no lo puede cargar).")
        return 1

    avisos = list(avisos_motor)
    rondas = banco["rondas"]
    por_id = {r["id"]: r for r in rondas}
    ids = [r["id"] for r in rondas]

    # ---- orden de rondas ----
    if ids != ORDEN:
        avisos.append("orden de rondas %s (el esperado es %s)" % (ids, ORDEN))

    # ---- final: rebote y sigue_si_acierta ----
    final = por_id.get("final")
    if final:
        if not final["rebote"]:
            avisos.append("final: falta \"rebote\": true (la final rebota la pregunta fallada)")
        if not final["sigue_si_acierta"]:
            avisos.append("final: falta \"sigue_si_acierta\": true (el que acierta sigue)")
    else:
        avisos.append("falta la ronda \"final\"")

    # ---- rebote solo en la final ----
    for r in rondas:
        if r["id"] != "final" and r.get("rebote"):
            avisos.append("%s: \"rebote\" solo va en la final (el motor lo ignora)" % r["id"])

    # ---- Matematica: ambos + aproximacion + num ----
    mate = por_id.get("mate")
    if mate:
        if mate["responden"] != "ambos":
            avisos.append("mate: deberia tener \"responden\": \"ambos\"")
        if not mate["aproximacion"]:
            avisos.append("mate: deberia tener \"aproximacion\": true")
        for p in mate["preguntas"]:
            if "num" not in p:
                avisos.append("mate, %s: falta \"num\" (la comparacion por aproximacion lo necesita)" % p["id"])
    else:
        avisos.append("falta la ronda \"mate\" (Matematicas)")

    # ---- r3: 3 temas de 4 + 3 ----
    r3 = por_id.get("r3")
    if r3:
        if r3["orden"] != "por_tema":
            avisos.append("r3: deberia tener \"orden\": \"por_tema\"")
        if len(r3["temas"]) != TEMAS_R3:
            avisos.append("r3: se esperan %d temas (hay %d)" % (TEMAS_R3, len(r3["temas"])))
        for t in r3["temas"]:
            if len(t["preguntas"]) != PREGUNTAS_POR_TEMA or len(t["reservas"]) != RESERVAS_POR_TEMA:
                avisos.append("r3/%s: se esperan %d preguntas + %d reservas (hay %d + %d)"
                              % (t["nombre"], PREGUNTAS_POR_TEMA, RESERVAS_POR_TEMA,
                                 len(t["preguntas"]), len(t["reservas"])))
    else:
        avisos.append("falta la ronda \"r3\"")

    # ---- comodines por ronda ----
    for r in rondas:
        esp = COMODINES_ESPERADOS.get(r["id"])
        if esp is not None and set(r["comodines"]) != esp:
            avisos.append("%s: comodines %s (el contrato dice %s)"
                          % (r["id"], sorted(r["comodines"]), sorted(esp)))

    # ---- reservas para "cambiar" ----
    for r in rondas:
        if "cambiar" not in r["comodines"]:
            continue
        if r["orden"] == "por_tema":
            for t in r["temas"]:
                if not t["reservas"]:
                    avisos.append("r3/%s: tiene el comodin cambiar pero no reservas" % t["nombre"])
        elif not r["reservas"]:
            avisos.append("%s: tiene el comodin cambiar pero no reservas" % r["id"])

    # ---- conteos esperados (guion/tarjetas) ----
    for rid, (pq, rs) in CONTEOS_ESPERADOS.items():
        r = por_id.get(rid)
        if not r:
            continue
        if rid == "r3":
            continue
        hoy = conteo(r)
        if hoy != (pq, rs):
            avisos.append("%s: tiene %d preguntas + %d reservas (el guion espera %d + %d)"
                          % (rid, hoy[0], hoy[1], pq, rs))

    # ---- preguntas repetidas (texto identico en todo el banco) ----
    vistos = {}
    for r in rondas:
        for q in textos(r):
            clave = " ".join(q.lower().split())
            if clave in vistos:
                avisos.append("pregunta repetida: \"%s\" (tambien en %s)" % (q[:60], vistos[clave]))
            else:
                vistos[clave] = r["id"]

    # ---- resumen ----
    print()
    print("%-4s %-22s %-9s %5s %8s %5s %4s  %s" %
          ("id", "nombre", "tipo", "preg", "reservas", "seg", "pts", "comodines"))
    print("-" * 96)
    total_p = total_r = 0
    for r in rondas:
        p, q = conteo(r)
        total_p += p
        total_r += q
        extra = []
        if r["id"] == "mate":
            extra.append("ambos/aprox")
        if r.get("rebote"):
            extra.append("rebote")
        if r.get("sigue_si_acierta"):
            extra.append("sigue")
        if r["orden"] == "por_tema":
            extra.append("%d temas" % len(r["temas"]))
        print("%-4s %-22s %-9s %5d %8d %5d %4d  %s%s" %
              (r["id"], r["nombre"][:22], r["tipo"], p, q, r["seg"], r["puntos"],
               ",".join(r["comodines"]) or "-",
               ("  [" + ", ".join(extra) + "]") if extra else ""))
    print("-" * 96)
    print("%-4s %-22s %-9s %5d %8d" % ("", "TOTAL", "", total_p, total_r))
    print("Entradas totales: %d (preguntas + reservas)" % (total_p + total_r))

    if avisos:
        print("\nAvisos (%d):" % len(avisos))
        for x in avisos:
            print("  ! " + x)
    else:
        print("\nSin avisos: el banco cumple el contrato v4.")

    ok = not avisos or not a.strict
    print("\nResultado: %s" % ("OK" if ok else "REVISAR (avisos con --strict)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
