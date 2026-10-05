#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Montage de CVR01 : 1800 images + bande son -> un MP4 diffusable.

Le decoupage impose 75 s a 24 i/s en 1920x1080. Le montage n'est donc pas
un choix creatif ici : les plans sont deja a leur place dans le rendu, la
camera a change au bon moment. Ce script assemble, encode, et surtout
VERIFIE que le resultat correspond au document.

Un encodage qui « reussit » peut produire un fichier a la mauvaise cadence,
sans audio, ou tronque : on mesure donc le fichier produit avec ffprobe au
lieu de faire confiance au code de retour de ffmpeg.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(HERE) if os.path.basename(HERE) == "blender" else HERE
sys.path.insert(0, os.path.join(RACINE, "doc"))

import cvr01_model as M  # noqa: E402

FPS = 24
F_PAR_PLAN = 120
LARGEUR = M.PROJET["largeur"]
HAUTEUR = M.PROJET["hauteur"]

# Surchargeables pour le rendu cloud (rendu_cloud.py) sans toucher au rendu local.
FRAMES = os.environ.get("CVR01_FRAMES") or os.path.join(RACINE, "blender", "renders", "frames")
SON = os.path.join(RACINE, "audio", "cvr01_mix_r128.wav")
EXPORTS = os.path.join(RACINE, "exports")


def ffprobe(chemin):
    r = subprocess.run(
        ("ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", chemin),
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffprobe : %s" % r.stderr[:200])
    return json.loads(r.stdout)


def main():
    attendu = F_PAR_PLAN * len(M.PLANS)

    print("=" * 70)
    print("MONTAGE CVR01 : %d plans, %d images, %d i/s"
          % (len(M.PLANS), attendu, FPS))
    print("=" * 70)

    # --- les images sont-elles toutes la ? --------------------------------
    if not os.path.isdir(FRAMES):
        print("ERREUR : %s absent -- le rendu n'a pas commence" % FRAMES)
        sys.exit(1)

    images = sorted(f for f in os.listdir(FRAMES)
                    if f.startswith("img_") and f.endswith(".png"))
    print("   images rendues   : %d / %d" % (len(images), attendu))

    if len(images) < attendu:
        print("ERREUR : rendu incomplet, %d images manquantes"
              % (attendu - len(images)))
        sys.exit(1)

    # Une image noire ou tronquee passe inapercue dans un comptage : on
    # verifie que personne n'est anormalement petit.
    tailles = [os.path.getsize(os.path.join(FRAMES, f)) for f in images]
    median = sorted(tailles)[len(tailles) // 2]
    suspectes = [images[i] for i, t in enumerate(tailles)
                 if t < median * 0.25]
    if suspectes:
        print("ERREUR : %d image(s) anormalement petites (ex. %s)"
              % (len(suspectes), ", ".join(suspectes[:3])))
        sys.exit(1)
    print("   taille mediane   : %.0f ko, aucune image tronquee"
          % (median / 1024.0))

    # --- la bande son ------------------------------------------------------
    if not os.path.isfile(SON):
        print("ERREUR : %s absent -- lancer audio/mixage.py" % SON)
        sys.exit(1)
    info_son = ffprobe(SON)
    d_son = float(info_son["format"]["duration"])
    d_image = attendu / float(FPS)
    print("   bande son        : %.2f s (image : %.2f s)" % (d_son, d_image))
    if abs(d_son - d_image) > 0.5:
        print("ERREUR : son et image desynchronises de %.2f s"
              % abs(d_son - d_image))
        sys.exit(1)

    # --- encodage ----------------------------------------------------------
    os.makedirs(EXPORTS, exist_ok=True)
    sortie = (os.environ.get("CVR01_SORTIE")
              or os.path.join(EXPORTS, "CVR01_le_cerf_volant_rouge.mp4"))

    # yuv420p et le niveau 4.0 : lisibles par tout lecteur, y compris les
    # telephones et les navigateurs. CRF 18 est visuellement sans perte sur
    # de l'aplat cel-shade.
    cmd = (
        "ffmpeg", "-v", "error", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(FRAMES, "img_%04d.png"),
        "-i", SON,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        "-shortest",
        sortie,
    )
    print("-" * 70)
    print("   encodage en cours (x264 CRF 18 + AAC 192k)...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERREUR ffmpeg : %s" % r.stderr[:400])
        sys.exit(1)

    # --- controle du fichier produit ---------------------------------------
    info = ffprobe(sortie)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)

    duree = float(info["format"]["duration"])
    taille = int(info["format"]["size"])
    num, den = v["r_frame_rate"].split("/")
    cadence = float(num) / float(den)

    print("-" * 70)
    print("   fichier          : %s" % sortie)
    print("   duree            : %.2f s (attendu %.2f)" % (duree, d_image))
    print("   image            : %sx%s, %.2f i/s, %s"
          % (v["width"], v["height"], cadence, v["codec_name"]))
    if a:
        print("   son              : %s %s Hz, %s canaux"
              % (a["codec_name"], a["sample_rate"], a["channels"]))
    print("   taille           : %.1f Mo" % (taille / 1048576.0))

    fautes = []
    if a is None:
        fautes.append("aucune piste audio dans le MP4")
    if int(v["width"]) != LARGEUR or int(v["height"]) != HAUTEUR:
        fautes.append("resolution %sx%s au lieu de %dx%d"
                      % (v["width"], v["height"], LARGEUR, HAUTEUR))
    if abs(cadence - FPS) > 0.01:
        fautes.append("cadence %.3f i/s au lieu de %d" % (cadence, FPS))
    if abs(duree - d_image) > 0.3:
        fautes.append("duree %.2f s au lieu de %.2f" % (duree, d_image))
    nb = int(v.get("nb_frames") or 0)
    if nb and nb != attendu:
        fautes.append("%d images dans le MP4 au lieu de %d" % (nb, attendu))

    if fautes:
        for f in fautes:
            print("ERREUR : %s" % f)
        sys.exit(1)

    print("-" * 70)
    print("film conforme au decoupage : %d plans, %.0f s, %dx%d, %d i/s"
          % (len(M.PLANS), duree, LARGEUR, HAUTEUR, FPS))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
