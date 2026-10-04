# -*- coding: utf-8 -*-
"""Valide l'inverted hull (contour anime) et mesure le vrai temps par image.

Grease Pencil v3 ne rend pas en headless sur GPU integre : il produit un aplat
noir plein cadre (diagnostique dans blender/diag_gp.py et diag_perf.py).
L'inverted hull est la technique classique du cel-shading : on duplique la
geometrie, on retourne les normales, on la grossit legerement et on lui donne
un materiau noir non eclaire. Rapide, fiable, independant du moteur.
"""
import bpy
import os
import time

sc = bpy.context.scene
OUT = os.path.join(r"C:\Users\Utilisateur\CVR01", "renders", "test")

# Le Line Art Grease Pencil est retire
gp = bpy.data.objects.get("LINE_ART")
if gp:
    bpy.data.objects.remove(gp, do_unlink=True)


def mat_contour():
    m = bpy.data.materials.new("MAT_CONTOUR")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emi = nt.nodes.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = (0.012, 0.008, 0.010, 1.0)
    emi.inputs["Strength"].default_value = 1.0
    nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])
    m.use_backface_culling = False
    return m


def ajouter_contour(ob, mat, epaisseur=0.012):
    """Solidify en mode normales inversees + materiau noir sur les backfaces."""
    if ob.type != "MESH":
        return None
    if len(ob.data.materials) == 0:
        return None
    ob.data.materials.append(mat)
    idx = len(ob.data.materials) - 1
    m = ob.modifiers.new("Contour", "SOLIDIFY")
    m.thickness = epaisseur
    m.offset = 1.0
    m.use_flip_normals = True
    m.use_rim = False
    m.material_offset = idx
    m.material_offset_rim = idx
    return m


mc = mat_contour()
cibles = [o for o in sc.objects
          if o.type == "MESH" and not o.name.startswith("SOL")]
for o in cibles:
    ajouter_contour(o, mc)
print("contours ajoutes sur %d objets" % len(cibles))


def mesure(nom, pct, samples):
    sc.render.resolution_percentage = pct
    sc.eevee.taa_render_samples = samples
    sc.render.filepath = os.path.join(OUT, nom)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    im = bpy.data.images.load(sc.render.filepath + ".png")
    px = list(im.pixels)
    k = len(px) // 4
    mo = sum(px[i * 4] + px[i * 4 + 1] + px[i * 4 + 2] for i in range(k)) / (3.0 * k)
    bpy.data.images.remove(im)
    print("RES %-24s %3d%% %2ds  %6.1f s  lum %.4f  %s"
          % (nom, pct, samples, dt, mo, "NOIR" if mo < 0.01 else "OK"))
    return dt


print("\n=== validation du contour ===")
mesure("h1_hull_25", 25, 4)

print("\n=== temps reel par image (apres compilation des shaders) ===")
mesure("h2_warm_100", 100, 16)      # inclut la compilation
t = mesure("h3_steady_100", 100, 16)  # mesure utile
print("\n>>> TEMPS PAR IMAGE A 1080p/16 samples : %.1f s" % t)
print(">>> 1800 images = %.1f heures" % (t * 1800 / 3600.0))

t8 = mesure("h4_steady_8s", 100, 8)
print(">>> a 8 samples : %.1f s/image, %.1f heures" % (t8, t8 * 1800 / 3600.0))
