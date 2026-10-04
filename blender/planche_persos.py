# -*- coding: utf-8 -*-
"""Planche de controle des personnages : face, profil, trois-quarts, visage."""
import bpy
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "renders", "persos")
os.makedirs(OUT, exist_ok=True)

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 1000, 1400
sc.eevee.taa_render_samples = 16
sc.view_settings.view_transform = "Standard"

# Fond neutre clair : on juge les silhouettes, pas l'ambiance
w = bpy.data.worlds.new("W")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.78, 0.80, 0.83, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.1
sc.world = w

# Eclairage de planche : trois points, neutre
bpy.ops.object.light_add(type="AREA", location=(-2.2, -3.0, 3.0))
k = bpy.context.active_object
k.data.size, k.data.energy = 4.0, 420
k.rotation_euler = (math.radians(52), 0, math.radians(-36))

bpy.ops.object.light_add(type="AREA", location=(2.6, -2.2, 2.0))
fl = bpy.context.active_object
fl.data.size, fl.data.energy = 3.5, 160
fl.rotation_euler = (math.radians(70), 0, math.radians(48))

bpy.ops.object.light_add(type="AREA", location=(0, 3.2, 2.6))
rm = bpy.context.active_object
rm.data.size, rm.data.energy = 3.0, 220
rm.rotation_euler = (math.radians(115), 0, 0)

cam_data = bpy.data.cameras.new("CAM_PLANCHE")
cam_data.lens = 85
cam_data.sensor_width = 36
cam = bpy.data.objects.new("CAM_PLANCHE", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam

tgt = bpy.data.objects.new("TGT", None)
sc.collection.objects.link(tgt)
con = cam.constraints.new("TRACK_TO")
con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"


def cadrer(centre, dist, angle_deg, haut=0.0):
    a = math.radians(angle_deg)
    tgt.location = centre
    cam.location = centre + Vector((math.sin(a) * dist, -math.cos(a) * dist, haut))
    bpy.context.view_layer.update()


def tir(nom):
    sc.render.filepath = os.path.join(OUT, nom)
    bpy.ops.render.render(write_still=True)
    print("PLANCHE", nom)


def isoler(nom_perso):
    for c in sc.collection.children:
        if c.name in ("Awa", "Tano"):
            for o in c.objects:
                o.hide_render = (c.name != nom_perso)


for nom, taille in (("Awa", 1.48), ("Tano", 1.34)):
    isoler(nom)
    arm = bpy.data.objects["%s_RIG" % nom]
    base = Vector((arm.location.x, 0, 0))
    centre = base + Vector((0, 0, taille * 0.52))

    for ang, tag in ((0, "face"), (35, "34"), (90, "profil")):
        cadrer(centre, 4.2, ang)
        tir("%s_%s" % (nom, tag))

    # Gros plan visage : c'est la que se joue l'identite
    tete = base + Vector((0, 0, taille * 0.915))
    cam_data.lens = 135
    cadrer(tete, 1.5, 0)
    tir("%s_visage" % nom)
    cadrer(tete, 1.5, 32)
    tir("%s_visage34" % nom)
    cam_data.lens = 85

# Les deux ensemble : verifie la difference de taille, point narratif cle
for c in sc.collection.children:
    if c.name in ("Awa", "Tano"):
        for o in c.objects:
            o.hide_render = False
sc.render.resolution_x, sc.render.resolution_y = 1400, 1200
cadrer(Vector((0, 0, 0.78)), 4.6, 0)
tir("duo_face")
cadrer(Vector((0, 0, 0.78)), 4.6, 30)
tir("duo_34")
print("planches terminees")
