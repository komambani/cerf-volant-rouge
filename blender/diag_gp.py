# -*- coding: utf-8 -*-
"""Inspecte le materiau Grease Pencil et mesure le cout du Line Art."""
import bpy
import os
import time

sc = bpy.context.scene
gp = bpy.data.objects.get("LINE_ART")
print("\n" + "=" * 70)
print("MATERIAUX GREASE PENCIL")
print("=" * 70)
print("objet:", gp.name, "type:", gp.type)
print("nb materiaux:", len(gp.data.materials))
for i, ms in enumerate(gp.data.materials):
    print("\n[%d] %s" % (i, ms.name if ms else "None"))
    if ms and ms.grease_pencil:
        g = ms.grease_pencil
        for attr in ("show_stroke", "show_fill", "mode", "color", "fill_color",
                     "stroke_style", "fill_style"):
            if hasattr(g, attr):
                print("     %-14s = %s" % (attr, getattr(g, attr)))

print("\nMODIFICATEURS")
for m in gp.modifiers:
    print("  ", m.type, m.name)
    for attr in ("thickness", "use_contour", "use_crease", "source_type",
                 "target_layer", "target_material", "use_fuzzy_intersections"):
        if hasattr(m, attr):
            v = getattr(m, attr)
            print("     %-22s = %s" % (attr, getattr(v, "name", v)))

print("\nCOUCHES (layers)")
for L in gp.data.layers:
    print("   %-18s hide=%s opacity=%.2f blend=%s"
          % (L.name, L.hide, getattr(L, "opacity", -1),
             getattr(L, "blend_mode", "?")))

# --- Mesure du cout reel du Line Art -------------------------------------
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "renders", "test")
sc.render.resolution_percentage = 25
sc.eevee.taa_render_samples = 4


def chrono(nom):
    sc.render.filepath = os.path.join(OUT, nom)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    img = bpy.data.images.load(sc.render.filepath + ".png")
    px = list(img.pixels)
    n = len(px) // 4
    moy = sum(px[i * 4] + px[i * 4 + 1] + px[i * 4 + 2] for i in range(n)) / (3.0 * n)
    bpy.data.images.remove(img)
    print("  %-26s %6.1f s   luminance %.4f  %s"
          % (nom, dt, moy, "NOIR" if moy < 0.01 else "OK"))
    return dt, moy


print("\n" + "=" * 70)
print("COUT DU LINE ART (25%, 4 samples)")
print("=" * 70)
gp.hide_render = True
chrono("c_sans_lineart")
gp.hide_render = False
chrono("c_avec_lineart")
print("=" * 70)
