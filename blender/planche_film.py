# -*- coding: utf-8 -*-
"""Rend une image temoin par plan depuis le film assemble.

    blender -b blender/cvr01_film.blend -P blender/planche_film.py -- \
        [--out renders/film] [--samples 16] [--echelle 50]

Une image a l'instant de l'evenement (2 s apres le debut du plan), avec LA
camera du plan. C'est la premiere fois que decor, personnages, accessoires,
lumiere et cadrage sont vus ensemble : ces 15 images sont la planche de
validation avant de lancer les 1800 images du film.
"""

import os
import sys

import bpy

ICI = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(ICI), "doc")
for d in (ICI, DOC):
    if d not in sys.path:
        sys.path.insert(0, d)

import cvr01_model as M     # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

    def opt(nom, defaut):
        return args[args.index(nom) + 1] if nom in args else defaut

    out = os.path.abspath(opt("--out", os.path.join(
        os.path.dirname(ICI), "renders", "film")))
    samples = int(opt("--samples", "16"))
    echelle = int(opt("--echelle", "50"))
    os.makedirs(out, exist_ok=True)

    sc = bpy.context.scene
    fps = M.PROJET["fps"]

    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.eevee.taa_render_samples = samples
    sc.render.resolution_percentage = echelle
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False

    print("--- planche du film assemble ---")
    print("   moteur EEVEE Next, %d samples, %d %% de 1920x1080"
          % (samples, echelle))

    faits = []
    for p in M.plans_enrichis():
        pid = p["id"]
        cam = bpy.data.objects.get("CAM_%s" % pid)
        if cam is None:
            print("   !! CAM_%s absente, plan saute" % pid)
            continue
        n_img = int(round(p["duree_s"] * fps))
        f_evt = (p["index"] - 1) * n_img + 1 + fps * 2
        sc.camera = cam
        sc.frame_set(int(f_evt))
        sc.render.filepath = os.path.join(out, "%s_evt.png" % pid)
        bpy.ops.render.render(write_still=True)
        faits.append(pid)
        print("   %s  image %4d  %s  %s %d mm a %.2f m"
              % (pid, f_evt, ",".join(p["persos"]), p["echelle"],
                 p["focale"], p["distance"]))

    print("--- %d images ecrites dans %s ---" % (len(faits), out))
    if len(faits) != M.PROJET["nb_plans"]:
        print("ERREUR : %d plans rendus sur %d"
              % (len(faits), M.PROJET["nb_plans"]))
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
