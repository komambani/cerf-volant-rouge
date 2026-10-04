# -*- coding: utf-8 -*-
"""Teste l'espace d'epaisseur du trait et le cout reel des lumieres."""
import bpy
import os
import time

sc = bpy.context.scene
gp = bpy.data.objects.get("LINE_ART")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "renders", "test")
sc.render.resolution_percentage = 25
sc.eevee.taa_render_samples = 4


def mesure(nom):
    sc.render.filepath = os.path.join(OUT, nom)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    img = bpy.data.images.load(sc.render.filepath + ".png")
    px = list(img.pixels)
    n = len(px) // 4
    moy = sum(px[i * 4] + px[i * 4 + 1] + px[i * 4 + 2] for i in range(n)) / (3.0 * n)
    bpy.data.images.remove(img)
    print("  %-30s %6.1f s  luminance %.4f  %s"
          % (nom, dt, moy, "NOIR" if moy < 0.01 else "OK"))
    return dt, moy


print("\n=== attributs d'epaisseur disponibles ===")
d = gp.data
for a in dir(d):
    if "thick" in a.lower() or "space" in a.lower() or "depth" in a.lower():
        print("   data.%s = %s" % (a, getattr(d, a, "?")))
for L in d.layers:
    for a in dir(L):
        if "thick" in a.lower() or "radius" in a.lower() or "space" in a.lower():
            print("   layer.%s = %s" % (a, getattr(L, a, "?")))
mod = [m for m in gp.modifiers if m.type == "LINEART"][0]
for a in dir(mod):
    if "thick" in a.lower() or "space" in a.lower() or "scale" in a.lower():
        print("   mod.%s = %s" % (a, getattr(mod, a, "?")))

print("\n=== TEST EPAISSEUR ===")
if hasattr(d, "stroke_thickness_space"):
    print("stroke_thickness_space actuel :", d.stroke_thickness_space)
    d.stroke_thickness_space = "SCREENSPACE"
    print("-> bascule en SCREENSPACE")
mesure("e1_screenspace")

mod.thickness = 1
mesure("e2_thickness1")

if hasattr(d, "pixel_factor"):
    d.pixel_factor = 0.1
    mesure("e3_pixelfactor")

print("\n=== COUT DES LUMIERES (line art masque) ===")
gp.hide_render = True
mesure("L0_toutes_lumieres")

fill = bpy.data.objects["APPOINT_CIEL"]
rim = bpy.data.objects["RIM_GAUCHE"]
sun = bpy.data.objects["SOLEIL_PRINCIPAL"]

fill.hide_render = True
mesure("L1_sans_appoint_ciel")
fill.hide_render = False

rim.hide_render = True
mesure("L2_sans_rim")
rim.hide_render = False

sc.eevee.use_shadows = False
mesure("L3_sans_ombres")
sc.eevee.use_shadows = True

fill.data.size = 6.0
rim.data.size, rim.data.size_y = 2.0, 1.5
mesure("L4_lumieres_petites")
