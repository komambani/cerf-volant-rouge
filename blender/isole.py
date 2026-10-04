# -*- coding: utf-8 -*-
"""Isole la cause du rendu noir : Line Art ? EEVEE sans GPU ? Lumiere ?"""
import bpy
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "renders", "test")
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.frame_set(1)
sc.render.resolution_percentage = 25          # vignettes rapides
sc.eevee.taa_render_samples = 4


def tir(nom):
    sc.render.filepath = os.path.join(OUT, nom)
    bpy.ops.render.render(write_still=True)
    import struct
    # Mesure de la luminance moyenne du resultat
    img = bpy.data.images.load(sc.render.filepath + ".png")
    px = list(img.pixels)
    n = len(px) // 4
    moy = sum(px[i * 4] + px[i * 4 + 1] + px[i * 4 + 2] for i in range(n)) / (3.0 * n)
    print("RESULTAT %-22s luminance moyenne = %.5f  %s"
          % (nom, moy, "NOIR" if moy < 0.01 else "IMAGE OK"))
    bpy.data.images.remove(img)
    return moy


print("\n" + "=" * 70)
print("TEST A : scene complete telle quelle")
tir("A_complet")

print("\nTEST B : Line Art masque")
gp = bpy.data.objects.get("LINE_ART")
if gp:
    gp.hide_render = True
tir("B_sans_lineart")

print("\nTEST C : sans Line Art + World plus fort")
sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 3.0
tir("C_world_fort")

print("\nTEST D : sans DOF")
for cam in bpy.data.cameras:
    cam.dof.use_dof = False
tir("D_sans_dof")

print("\nTEST E : Workbench (moteur de reference, sans EEVEE)")
sc.render.engine = "BLENDER_WORKBENCH"
tir("E_workbench")

print("=" * 70)
