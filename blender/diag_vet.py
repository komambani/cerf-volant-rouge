# -*- coding: utf-8 -*-
"""Pourquoi l'ourlet du haut est-il dechiquete ?

Hypothese : le Skin modifier produit une enveloppe par interpolation entre
sommets. Quand le DERNIER sommet d'une chaine est au meme endroit qu'un
sommet du corps avec un rayon a peine superieur, les deux surfaces
s'entrecroisent et l'ourlet devient une dentelle (z-fighting geometrique).

On mesure l'ecart radial reel entre le haut et le corps a plusieurs hauteurs.
"""
import bpy
import sys
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def rayon_a_hauteur(ob, z, tol=0.012):
    """Rayon horizontal max du maillage evalue, dans une tranche en z."""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ob.matrix_world
    best = None
    for v in me.vertices:
        p = mw @ v.co
        if abs(p.z - z) < tol:
            r = (p.x ** 2 + p.y ** 2) ** 0.5
            if best is None or r > best:
                best = r
    ev.to_mesh_clear()
    return best


for nom in ("Awa", "Tano"):
    corps = bpy.data.objects.get("%s_CORPS" % nom)
    haut = bpy.data.objects.get("%s_HAUT" % nom)
    bas = bpy.data.objects.get("%s_BAS" % nom)
    if not corps or not haut:
        continue
    print("\n" + "=" * 68)
    print("ECART RADIAL vetement / corps -", nom)
    print("=" * 68)
    zs = [(corps.matrix_world @ Vector(c)).z for c in corps.bound_box]
    z0, z1 = min(zs), max(zs)
    print("%-8s %10s %10s %10s" % ("z (m)", "corps", "haut", "ecart mm"))
    for i in range(14):
        z = z0 + (z1 - z0) * (0.30 + 0.045 * i)
        rc = rayon_a_hauteur(corps, z)
        rh = rayon_a_hauteur(haut, z)
        if rc is None or rh is None:
            continue
        d = (rh - rc) * 1000
        flag = "  <-- CROISEMENT" if d < 1.0 else ""
        print("%-8.3f %10.4f %10.4f %+10.1f%s" % (z, rc, rh, d, flag))

    print("\n--- geometrie des chaines ---")
    for ob in (corps, haut, bas):
        if ob is None:
            continue
        n = len(ob.data.vertices)
        print("%-14s sommets de chaine : %d" % (ob.name, n))
