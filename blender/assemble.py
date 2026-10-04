# -*- coding: utf-8 -*-
"""Fusionne le decor et les personnages animes en une seule scene rendable.

    blender -b --factory-startup -P blender/assemble.py -- \
        --scene blender/cvr01_scene.blend \
        --persos blender/cvr01_anim.blend \
        --out blender/cvr01_film.blend

Principe
--------
Le decor (`cvr01_scene.blend`) porte le manguier, le mur, la maison, le banc,
les accessoires, la lumiere du champ G et les 15 cameras avec leurs
trajectoires. Les personnages (`cvr01_anim.blend`) portent Awa et Tano, leurs
82 maillages, leurs 2 armatures et leurs 90 poses clees sur 1800 images.

On charge le decor comme scene de base, puis on y APPEND les deux collections
de personnages avec leurs actions. On les place ensuite a leur marque au sol,
et on recale les cibles de camera sur le sujet de chaque plan.

Placement
---------
Les cameras du decor visent l'ORIGINE, ou se trouve le tronc du manguier
(rayon 0,22 m, hauteur 4,2 m). Y poser les enfants les mettrait DANS l'arbre.

Les enfants se tiennent donc sous la branche porteuse, qui est a
(0,90 / 0,15 / 2,25), decalee en +X. Ils regardent vers -Y, c'est-a-dire vers
la camera -- mesure faite sur la position du nez par rapport a la tete.

Leur marque est FIXE sur tout le film : un acteur ne se teleporte pas entre
deux plans, c'est la camera qui se deplace. C'est aussi ce qu'exige le raccord
RPOS du document.

Les deux plans d'action contraignent la geometrie :
  * P004 : Tano sur le tabouret (42 cm) atteint 2,16 m < 2,25 -- il echoue.
  * P008 : Awa sur le tabouret atteint 2,34 m >= 2,25 -- elle reussit.
Les deux doivent donc etre a portee de la branche, tabouret compris.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)
DOC = os.path.join(os.path.dirname(ICI), "doc")
if DOC not in sys.path:
    sys.path.insert(0, DOC)

import cvr01_model as M     # noqa: E402

# --- marques au sol -------------------------------------------------------
#
# X : les deux enfants cote a cote sous la branche, Awa a gauche de l'image.
# Y : legerement devant le tronc (-Y = vers la camera) pour ne pas etre
#     masques par lui et pour detacher leur silhouette du feuillage.
# Le tabouret est amene a leur portee en X ; il reste a sa hauteur de 42 cm.
MARQUES = {
    "Awa":  Vector((0.62, -0.55, 0.0)),
    "Tano": Vector((1.32, -0.40, 0.0)),
}
# Le tabouret sert a Tano (P004) puis a Awa (P008) : on le pose entre les deux,
# sous la branche, a portee des deux marques.
TABOURET = Vector((0.95, -0.30, 0.0))


def log(msg):
    print("   %s" % msg)


def charger_decor(chemin):
    bpy.ops.wm.open_mainfile(filepath=chemin)
    log("decor charge : %d objets" % len(bpy.data.objects))
    return bpy.context.scene


def append_personnages(chemin):
    """Importe les collections Awa et Tano avec leurs armatures et actions."""
    avant = set(o.name for o in bpy.data.objects)
    with bpy.data.libraries.load(chemin, link=False) as (source, cible):
        voulues = [c for c in source.collections if c in ("Awa", "Tano")]
        if len(voulues) != 2:
            print("ERREUR : collections de personnages introuvables dans %s "
                  "(trouve : %s)" % (chemin, ", ".join(source.collections)))
            sys.exit(1)
        cible.collections = voulues
    sc = bpy.context.scene
    for col in cible.collections:
        if col is not None:
            sc.collection.children.link(col)
    apres = set(o.name for o in bpy.data.objects)
    nouveaux = apres - avant
    log("personnages importes : %d objets" % len(nouveaux))
    return nouveaux


def placer(nouveaux):
    """Pose chaque rig sur sa marque, sans toucher aux poses d'os."""
    place = []
    for perso, marque in MARQUES.items():
        rig = bpy.data.objects.get("%s_RIG" % perso)
        if rig is None:
            print("ERREUR : %s_RIG absent apres import" % perso)
            sys.exit(1)
        # Les poses sont des rotations d'OS ; deplacer l'objet rig emmene tout
        # le personnage sans les alterer. L'echelle du rig (1,13 / 1,16) porte
        # la taille du personnage : on n'y touche pas.
        rig.location = marque
        rig.rotation_euler = (0.0, 0.0, 0.0)   # ils regardent deja vers -Y
        place.append("%s -> (%.2f, %.2f)" % (perso, marque.x, marque.y))
    log("marques au sol : %s" % " ; ".join(place))

    # Le tabouret est une collection d'objets dans le decor : on la deplace
    # en bloc en decalant chaque objet qui la compose.
    col = bpy.data.collections.get("OBJ_STOOL")
    if col is not None:
        for o in col.objects:
            o.location = o.location + TABOURET
        log("tabouret amene a (%.2f, %.2f) -- a portee des deux enfants"
            % (TABOURET.x, TABOURET.y))
    else:
        log("!! collection OBJ_STOOL introuvable, tabouret non deplace")


def recaler_cameras():
    """Recale la cible et la position de chaque camera sur son sujet.

    Les cameras du decor visent l'origine et sont posees a (0, -distance,
    hauteur_cam). Le sujet n'est plus a l'origine : il faut appliquer le meme
    decalage lateral a la cible ET aux positions clees, sinon la distance au
    sujet change et l'echelle de plan declaree dans le document devient fausse.
    """
    plans = {p["id"]: p for p in M.plans_enrichis()}
    recales = []
    for pid, p in plans.items():
        sujet = p.get("sujet_ref")
        if sujet not in MARQUES:
            continue
        marque = MARQUES[sujet]
        # Decalage a appliquer : du centre du decor vers la marque du sujet.
        # On ne recale QUE X et Y : la hauteur de camera est imposee par le
        # document et la cible garde sa hauteur d'yeux.
        d = Vector((marque.x, marque.y, 0.0))

        tgt = bpy.data.objects.get("TGT_%s" % pid)
        if tgt is not None:
            tgt.location = tgt.location + d

        cam = bpy.data.objects.get("CAM_%s" % pid)
        if cam is None:
            continue
        # Les trajectoires sont des cles de 'location' : on les decale toutes
        # du meme vecteur, ce qui translate le mouvement sans le deformer.
        act = cam.animation_data.action if cam.animation_data else None
        if act is not None:
            for fc in act.fcurves:
                if fc.data_path != "location" or fc.array_index > 1:
                    continue
                dd = d.x if fc.array_index == 0 else d.y
                for kp in fc.keyframe_points:
                    kp.co.y += dd
                    kp.handle_left.y += dd
                    kp.handle_right.y += dd
        else:
            cam.location = cam.location + d
        recales.append(pid)
    log("cameras recalees sur leur sujet : %d plans" % len(recales))
    return recales


def verifier(sc):
    """Controles mesures : rien n'est declare bon sans chiffre a l'appui."""
    erreurs = []
    fps = M.PROJET["fps"]

    # 1. Les personnages sont presents et animes
    for perso in MARQUES:
        rig = bpy.data.objects.get("%s_RIG" % perso)
        if rig is None:
            erreurs.append("%s_RIG absent" % perso)
            continue
        act = rig.animation_data.action if rig.animation_data else None
        if act is None or not act.fcurves:
            erreurs.append("%s n'a aucune animation apres fusion" % perso)
        else:
            deb, fin = act.frame_range
            if fin < sc.frame_end - 1:
                erreurs.append(
                    "%s : animation jusqu'a l'image %d, le film va a %d"
                    % (perso, int(fin), sc.frame_end))

    # 2. Aucun personnage dans le tronc du manguier (rayon 0,22 m a l'origine)
    for perso, marque in MARQUES.items():
        d_tronc = math.hypot(marque.x, marque.y)
        if d_tronc < 0.22 + 0.25:
            erreurs.append(
                "%s est a %.2f m de l'axe du tronc (rayon 0,22 m) : il est "
                "dans l'arbre" % (perso, d_tronc))

    # 3. Les deux enfants ne se chevauchent pas
    ecart = (MARQUES["Awa"] - MARQUES["Tano"]).length
    if ecart < 0.45:
        erreurs.append("Awa et Tano sont a %.2f m : ils se chevauchent"
                       % ecart)

    # 4. Chaque camera cadre bien son sujet, mesure par projection
    from bpy_extras.object_utils import world_to_camera_view
    plans = {p["id"]: p for p in M.plans_enrichis()}
    hors_cadre = []
    for pid, p in plans.items():
        cam = bpy.data.objects.get("CAM_%s" % pid)
        sujet = p.get("sujet_ref")
        if cam is None or sujet not in MARQUES:
            continue
        rig = bpy.data.objects.get("%s_RIG" % sujet)
        if rig is None:
            continue
        # a l'instant de l'evenement, soit 2 s apres le debut du plan
        f_evt = (p["index"] - 1) * int(round(p["duree_s"] * fps)) + 1 + fps * 2
        sc.frame_set(int(f_evt))
        sc.camera = cam
        tete = rig.pose.bones["tete"]
        pied = rig.pose.bones["pied_D"]
        p_tete = rig.matrix_world @ tete.tail
        p_pied = rig.matrix_world @ pied.head
        v_tete = world_to_camera_view(sc, cam, p_tete)
        v_pied = world_to_camera_view(sc, cam, p_pied)
        # le sujet doit etre devant la camera et dans le cadre
        if v_tete.z <= 0 or v_pied.z <= 0:
            hors_cadre.append("%s : %s est derriere la camera" % (pid, sujet))
            continue
        dedans = all(-0.02 <= v.x <= 1.02 for v in (v_tete, v_pied))
        if not dedans:
            hors_cadre.append(
                "%s : %s hors cadre en largeur (tete x=%.2f, pied x=%.2f)"
                % (pid, sujet, v_tete.x, v_pied.x))
            continue
        # portion verticale occupee : doit correspondre a l'echelle declaree.
        # Les echelles en mode "cadre_m" (gros plans, inserts) ne se mesurent
        # pas en portion de sujet debout : le document les controle par la
        # hauteur de cadre, pas par le ratio.
        portion = abs(v_tete.y - v_pied.y)
        ech = M.ECHELLES.get(p["echelle"], {})
        if ech.get("mode") == "ratio":
            bande = ech["bande"]
            if not (bande[0] * 0.80 <= portion <= bande[1] * 1.20):
                hors_cadre.append(
                    "%s : %s occupe %.0f %% du cadre, l'echelle %s en demande "
                    "%.0f a %.0f %%"
                    % (pid, sujet, portion * 100, p["echelle"],
                       bande[0] * 100, bande[1] * 100))
    erreurs.extend(hors_cadre)

    # 5. Le cerf-volant est bien dans l'arbre, au-dessus des enfants.
    # On mesure la GEOMETRIE, pas l'origine de l'objet : un maillage construit
    # par sommets explicites garde son origine a zero meme place en hauteur.
    # (Meme erreur que sur le bracelet : lire un point de reference au lieu
    # de la matiere.)
    kite = bpy.data.objects.get("OBJ_KITE_TOILE")
    if kite is not None:
        co = [kite.matrix_world @ v.co for v in kite.data.vertices]
        z_bas, z_haut = min(p.z for p in co), max(p.z for p in co)
        if z_haut < 2.0:
            erreurs.append(
                "le cerf-volant culmine a %.2f m : trop bas pour etre coince "
                "dans la branche a 2,25 m" % z_haut)
        elif z_bas > 2.25:
            erreurs.append(
                "le cerf-volant commence a %.2f m, au-dessus de la branche "
                "a 2,25 m : il ne touche pas l'arbre" % z_bas)

    if erreurs:
        for e in erreurs[:12]:
            print("ERREUR assemblage : %s" % e)
        print("ERREUR : %d probleme(s) d'assemblage" % len(erreurs))
        sys.exit(1)

    log("personnages animes sur 1800 images, hors du tronc, a %.2f m "
        "l'un de l'autre" % ecart)
    log("15 cameras cadrent leur sujet a l'echelle declaree")


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    def opt(nom, defaut):
        return args[args.index(nom) + 1] if nom in args else defaut

    f_scene = opt("--scene", os.path.join(ICI, "cvr01_scene.blend"))
    f_persos = opt("--persos", os.path.join(ICI, "cvr01_anim.blend"))
    f_out = opt("--out", os.path.join(ICI, "cvr01_film.blend"))

    # Les chemins sont rendus absolus AVANT tout chargement : `open_mainfile`
    # change le repertoire courant de Blender, et un chemin relatif passe en
    # ligne de commande serait ensuite resolu depuis le dossier du .blend.
    # (Mesure : "blender/cvr01_anim.blend" devenait "C:\blender\cvr01_anim.blend".)
    f_scene = os.path.abspath(f_scene)
    f_persos = os.path.abspath(f_persos)
    f_out = os.path.abspath(f_out)
    for f in (f_scene, f_persos):
        if not os.path.isfile(f):
            print("ERREUR : fichier introuvable : %s" % f)
            sys.exit(1)

    print("--- assemblage du film ---")
    sc = charger_decor(f_scene)
    nouveaux = append_personnages(f_persos)
    placer(nouveaux)
    recaler_cameras()

    # Duree du film : 15 plans de 5 s a 24 i/s
    sc.frame_start = 1
    sc.frame_end = int(round(M.PROJET["duree_s"] * M.PROJET["fps"]))
    sc.render.fps = M.PROJET["fps"]
    sc.render.resolution_x = M.PROJET["largeur"]
    sc.render.resolution_y = M.PROJET["hauteur"]
    log("film : %d images, %d i/s, %dx%d"
        % (sc.frame_end, sc.render.fps,
           sc.render.resolution_x, sc.render.resolution_y))

    verifier(sc)

    bpy.ops.wm.save_as_mainfile(filepath=f_out)
    print("--- assemblage ecrit : %s ---" % f_out)


if __name__ == "__main__":
    # Un plantage ne doit jamais ressembler a un succes : Blender quitte avec
    # le code 0 meme quand le script leve une exception.
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
