# -*- coding: utf-8 -*-
"""Diagnostic du rendu noir : etat reel de la scene au moment du rendu."""
import bpy
import os
import sys
from mathutils import Vector

sc = bpy.context.scene
print("\n" + "=" * 70)
print("DIAGNOSTIC CVR01")
print("=" * 70)

print("moteur        :", sc.render.engine)
print("camera active :", sc.camera.name if sc.camera else "AUCUNE")
print("frame courante:", sc.frame_current)
print("view transform:", sc.view_settings.view_transform)
print("look          :", sc.view_settings.look)
print("exposure      :", sc.view_settings.exposure)
print("gamma         :", sc.view_settings.gamma)
print("world         :", sc.world.name if sc.world else "AUCUN")

sc.frame_set(1)
cam = sc.camera
print("\n--- CAMERA a la frame 1 ---")
print("nom      :", cam.name)
print("location :", tuple(round(v, 3) for v in cam.matrix_world.translation))
d = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
print("direction :", tuple(round(v, 3) for v in d))
print("focale   :", cam.data.lens, "mm  sensor:", cam.data.sensor_width)
print("clip     :", cam.data.clip_start, "->", cam.data.clip_end)
print("dof      :", cam.data.dof.use_dof, "fstop", cam.data.dof.aperture_fstop,
      "focus_obj", cam.data.dof.focus_object.name if cam.data.dof.focus_object else None,
      "focus_dist", round(cam.data.dof.focus_distance, 3))
print("contraintes:", [(c.type, c.influence, c.target.name if getattr(c, 'target', None) else None)
                       for c in cam.constraints])

print("\n--- LUMIERES ---")
for o in sc.objects:
    if o.type == "LIGHT":
        print("  %-20s %-6s energy=%8.2f  loc=%s  hide_render=%s"
              % (o.name, o.data.type, o.data.energy,
                 tuple(round(v, 1) for v in o.location), o.hide_render))

print("\n--- OBJETS VISIBLES DANS LE CHAMP ---")
vis = [o for o in sc.objects if o.type == "MESH" and not o.hide_render]
print("meshes rendus :", len(vis))
for o in vis[:6]:
    print("   %-24s loc=%s dims=%s"
          % (o.name, tuple(round(v, 2) for v in o.location),
             tuple(round(v, 2) for v in o.dimensions)))

print("\n--- GREASE PENCIL ---")
for o in sc.objects:
    if o.type in ("GPENCIL", "GREASEPENCIL"):
        print("  %s type=%s hide_render=%s loc=%s dims=%s"
              % (o.name, o.type, o.hide_render,
                 tuple(round(v, 2) for v in o.location),
                 tuple(round(v, 2) for v in o.dimensions)))
        for m in o.modifiers:
            print("     modifier:", m.type, m.name)

print("\n--- COLLECTIONS ---")
def walk(c, ind=0):
    print("  " * (ind + 1), c.name, "hide_render=", c.hide_render,
          "objets=", len(c.objects))
    for ch in c.children:
        walk(ch, ind + 1)
walk(sc.collection)

print("\n--- VIEW LAYER ---")
vl = sc.view_layers[0]
print("nom:", vl.name, "use:", vl.use)
for lc in vl.layer_collection.children:
    print("   layer_collection", lc.name, "exclude=", lc.exclude,
          "hide_viewport=", lc.hide_viewport, "holdout=", lc.holdout,
          "indirect_only=", lc.indirect_only)
print("=" * 70)
