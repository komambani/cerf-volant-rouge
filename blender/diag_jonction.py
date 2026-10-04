# -*- coding: utf-8 -*-
"""Ecart radial haut / bas a la jonction, mesure sur la geometrie evaluee.

Le but : savoir si le pantalon passe VRAIMENT par-dessus l'ourlet du t-shirt
sur toute la zone de recouvrement. La dentelle apparait partout ou l'ecart
devient negatif ou quasi nul.
"""
import bpy
import sys
import os
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characters as C  # noqa: E402


def pts_monde(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ob.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def rayon_tranche(pts, centre_x, z, tol):
    """Rayon horizontal max autour de l'axe du tronc, dans une tranche en z.
    On exclut les points trop lateraux (bras) en bornant |x - centre|."""
    best = None
    for p in pts:
        if abs(p.z - z) > tol:
            continue
        dx = p.x - centre_x
        if abs(dx) > 0.16:          # au-dela : bras ou mains
            continue
        r = (dx * dx + p.y * p.y) ** 0.5
        if best is None or r > best:
            best = r
    return best


for nom in ("Awa", "Tano"):
    haut = bpy.data.objects["%s_HAUT" % nom]
    bas = bpy.data.objects["%s_BAS" % nom]
    arm = bpy.data.objects["%s_RIG" % nom]
    cx = arm.location.x
    ph, pb = pts_monde(haut), pts_monde(bas)

    zh = [p.z for p in ph]
    zb = [p.z for p in pb]
    z_lo, z_hi = max(min(zh), min(zb)), min(max(zh), max(zb))
    print("\n" + "=" * 68)
    print("JONCTION HAUT / BAS - %s" % nom)
    print("haut : z %.3f -> %.3f     bas : z %.3f -> %.3f"
          % (min(zh), max(zh), min(zb), max(zb)))
    print("zone de recouvrement : %.3f -> %.3f  (%.0f mm)"
          % (z_lo, z_hi, (z_hi - z_lo) * 1000))
    print("=" * 68)
    print("%-9s %9s %9s %10s" % ("z (m)", "r_haut", "r_bas", "ecart mm"))
    tol = 0.010
    n = 12
    mauvais = 0
    for i in range(n + 1):
        z = z_lo + (z_hi - z_lo) * i / float(n)
        rh = rayon_tranche(ph, cx, z, tol)
        rb = rayon_tranche(pb, cx, z, tol)
        if rh is None or rb is None:
            continue
        d = (rb - rh) * 1000
        flag = ""
        if d < 2.0:
            flag = "  <-- DENTELLE"
            mauvais += 1
        print("%-9.3f %9.4f %9.4f %+10.1f%s" % (z, rh, rb, d, flag))
    print("tranches problematiques : %d" % mauvais)
