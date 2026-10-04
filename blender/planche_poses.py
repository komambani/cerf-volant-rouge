# -*- coding: utf-8 -*-
"""Planche de controle des poses : une vignette par plan, a l'instant de
l'evenement (2 s), la ou la pose est la plus lisible.

    blender -b blender/cvr01_anim.blend -P blender/planche_poses.py
"""
import bpy
import os
import sys
import math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "doc"))
import cvr01_model as M          # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "renders", "poses")
os.makedirs(OUT, exist_ok=True)

FPS = 24
F_PAR_PLAN = FPS * 5


def nettoyer_cameras():
    for ob in list(bpy.data.objects):
        if ob.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(ob, do_unlink=True)


def decor_neutre():
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.80, 0.82, 0.85, 1.0)
    bg.inputs[1].default_value = 1.1


def lumieres():
    for nom, pos, ene, taille in (
        ("KEY", (-2.2, -3.0, 3.0), 420, 4.0),
        ("FILL", (2.6, -2.4, 1.6), 150, 5.0),
        ("RIM", (0.6, 3.2, 2.6), 260, 3.0),
    ):
        d = bpy.data.lights.new(nom, type="AREA")
        d.energy = ene
        d.size = taille
        ob = bpy.data.objects.new(nom, d)
        bpy.context.collection.objects.link(ob)
        ob.location = pos
        direction = Vector((0, 0, 1.0)) - Vector(pos)
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(cible, dist=4.2, haut=1.1, az=18.0):
    cam_d = bpy.data.cameras.new("CAM")
    cam_d.lens = 50
    cam = bpy.data.objects.new("CAM", cam_d)
    bpy.context.collection.objects.link(cam)
    a = math.radians(az)
    cam.location = (cible.x + dist * math.sin(a),
                    cible.y - dist * math.cos(a),
                    haut)
    d = cible - Vector(cam.location)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def main():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = 540
    sc.render.resolution_y = 760
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    try:
        sc.eevee.taa_render_samples = 12
    except Exception:
        pass

    nettoyer_cameras()
    decor_neutre()
    lumieres()

    rigs = {n: bpy.data.objects.get("%s_RIG" % n) for n in ("Awa", "Tano")}
    cam = camera(Vector((0, 0, 0.85)))

    print("=" * 70)
    print("PLANCHE DES POSES : %d plans" % len(M.PLANS))
    print("=" * 70)

    for i, plan in enumerate(M.PLANS):
        pid = plan["id"]
        f_evt = 1 + i * F_PAR_PLAN + FPS * 2
        sc.frame_set(f_evt)

        # On cadre sur le personnage de reference du plan (champ sujet_ref)
        ref = plan.get("sujet_ref") or plan["persos"][0]
        arm = rigs.get(ref)
        cible = Vector((arm.location.x, 0, 0.85)) if arm else Vector((0, 0, 0.85))
        a = math.radians(18.0)
        cam.location = (cible.x + 4.2 * math.sin(a),
                        cible.y - 4.2 * math.cos(a), 1.10)
        d = cible - Vector(cam.location)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

        chemin = os.path.join(OUT, "%s_evt.png" % pid)
        sc.render.filepath = chemin
        bpy.ops.render.render(write_still=True)
        print("POSE %-10s i%-5d %-14s -> %s"
              % (pid, f_evt, plan["emotion"], os.path.basename(chemin)))

    print("-" * 70)
    print("planches dans %s" % OUT)


if __name__ == "__main__":
    main()
