# -*- coding: utf-8 -*-
"""Calibrage du critere "visage degage" sur la VRAIE pose.

Pourquoi ce fichier : les sondages ecrits a la main dans --python-expr ne
reglaient que `bras_*`, `avbras_*` et `epaule_*`. La pose reelle incline aussi
`colonne`, `cou` et `tete` -- et c'est cette bascule qui deplace le visage par
rapport aux bras. Resultat : un balayage annoncait "score 0" sur des angles
que le film refusait ensuite. On applique donc ici le dictionnaire de POSES
tel quel, avec le meme facteur d'intensite et les memes limites anatomiques
que `poses.py`.

Usage :
    blender -b cvr01_persos.blend -P calib_visage.py -- \
        --perso Tano --pose bras_leves --bz 85,95,105 --bx -140,-150
"""
import os
import sys
import math

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view as w2c

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import poses as P  # noqa: E402

IGNORE = ("TETE", "CHEV", "FRANGE", "BOUCLE", "OEIL", "IRIS", "PUPILLE",
          "SCLERE", "REFL", "NEZ", "OREILLE", "PAUPIERE", "BOUCHE",
          "NATTE", "PERLE")

SEUIL_SOMMETS = 20
ECART_MAXI = 62.0
COUDE_MINI = 12.0


def raz(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)


def appliquer(arm, pose, k):
    """Meme regle que poses.py : produit pose x intensite, borne par LIMITES."""
    raz(arm)
    for os_nom, (rx, ry, rz) in pose.items():
        if os_nom not in arm.pose.bones:
            print("ERREUR : os inconnu %s" % os_nom)
            sys.exit(2)
        lim = P.LIMITES.get(os_nom)
        vx = rx * k
        if lim:
            vx = max(lim[0], min(lim[1], vx))
        arm.pose.bones[os_nom].rotation_euler = (
            math.radians(vx), math.radians(ry * k), math.radians(rz * k))
    bpy.context.view_layer.update()


def plan_de(nom_pose, perso):
    """Le plan du document ou cette pose est jouee par ce personnage."""
    for p in P.M.PLANS:
        if perso not in p["persos"]:
            continue
        if nom_pose in str(P.CHOREGRAPHIE.get(p["id"], "")):
            return p
    return {"id": "(defaut)", "focale": 50, "distance": 4.0,
            "hauteur_cam": 1.35}


def score(arm, nom, cam, sc, plan):
    """Sommets recouvrant le visage, vus depuis la camera du plan."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    tete = arm.matrix_world @ arm.pose.bones["tete"].head
    sommet = arm.matrix_world @ arm.pose.bones["tete"].tail
    centre = tete.lerp(sommet, 0.62)
    r_crane = (sommet - tete).length * 0.62
    cam.data.lens = float(plan["focale"])
    cam.location = (tete.x, tete.y - float(plan["distance"]),
                    float(plan["hauteur_cam"]))
    d = tete - Vector(cam.location)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    pt = w2c(sc, cam, tete)
    ps = w2c(sc, cam, sommet)
    rc = max(((ps.x - pt.x) ** 2 + (ps.y - pt.y) ** 2) ** 0.5, 0.02)
    cx = pt.x + (ps.x - pt.x) * 0.62
    cy = pt.y + (ps.y - pt.y) * 0.62
    rx, ry = rc * 0.46, rc * 0.42
    pire, coupable = 0, ""
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith(nom):
            continue
        if any(k in o.name.upper() for k in IGNORE):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        n = 0
        for v in me.vertices:
            p = o.matrix_world @ v.co
            if (p - centre).length < r_crane:
                continue
            pp = w2c(sc, cam, p)
            if ((pp.x - cx) / rx) ** 2 + ((pp.y - cy) / ry) ** 2 < 1.0 \
                    and pp.z < pt.z - 0.02:
                n += 1
        ev.to_mesh_clear()
        # Un objet n'est rapporte que s'il peut DEPASSER le seuil (mesure v27 :
        # 628 sommets annonces pour Tano_POUCE-1, qui en a 628 au total --
        # le total sortait a la place du decompte, alors que ce pouce est a
        # l'ecran en x=0,154, a l'oppose de la main).
        if n > pire and n > SEUIL_SOMMETS:
            pire, coupable = n, o.name
    return pire, coupable

def silhouette(arm):
    """Angle bras/axe du corps et flexion du coude, cote droit."""
    axe = (arm.pose.bones["tete"].head
           - arm.pose.bones["bassin"].head).normalized()
    pb_b = arm.pose.bones["bras_D"]
    pb_a = arm.pose.bones["avbras_D"]
    v_bras = pb_b.tail - pb_b.head
    ecart = math.degrees(math.acos(
        max(-1.0, min(1.0, v_bras.normalized().dot(axe)))))
    ecart = min(ecart, 180.0 - ecart)
    v_av = pb_a.tail - pb_a.head
    coude = math.degrees(math.acos(max(-1.0, min(1.0,
        v_bras.normalized().dot(v_av.normalized())))))
    return ecart, coude


def lisibilite(arm, z0):
    """La pose reste-t-elle un geste lisible ? (montee et ecart des mains)"""
    mD = arm.matrix_world @ arm.pose.bones["main_D"].head
    mG = arm.matrix_world @ arm.pose.bones["main_G"].head
    return (mD.z - z0) * 1000.0, (mD - mG).length * 1000.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

    def opt(nom, defaut):
        return argv[argv.index(nom) + 1] if nom in argv else defaut

    perso = opt("--perso", "Tano")
    nom_pose = opt("--pose", "bras_leves")
    bxs = [float(x) for x in opt("--bx", "-118").split(",")]
    bzs = [float(x) for x in opt("--bz", "30").split(",")]
    avs = [float(x) for x in opt("--av", "-52").split(",")]
    intensite = float(opt("--intensite", "4"))
    k = 0.55 + 0.15 * intensite

    sc = bpy.context.scene
    cd = bpy.data.cameras.new("CAL")
    cd.lens = 50
    cam = bpy.data.objects.new("CAL", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam

    arm = bpy.data.objects["%s_RIG" % perso]
    raz(arm)
    bpy.context.view_layer.update()
    z0 = (arm.matrix_world @ arm.pose.bones["main_D"].head).z

    plan = plan_de(nom_pose, perso)
    base = dict(P.POSES[nom_pose])
    print("calibrage %s / %s / intensite %.0f (k=%.2f)"
          % (perso, nom_pose, intensite, k))
    print("   vue du plan %s : focale %d, distance %.1f m, hauteur %.2f m"
          % (plan["id"], int(plan["focale"]), float(plan["distance"]),
             float(plan["hauteur_cam"])))
    print("   pose complete : %s" % ", ".join(sorted(base)))
    print("   seuils : recouvrement <= %d sommets, ecart bras/corps <= %.0f "
          "deg, coude >= %.0f deg" % (SEUIL_SOMMETS, ECART_MAXI, COUDE_MINI))
    print("   %-22s %7s %6s %6s %8s %7s  %s"
          % ("angles", "recouv", "ecart", "coude", "montee", "ecartM", "etat"))
    for bx in bxs:
        for bz in bzs:
            for av in avs:
                pose = dict(base)
                for cote, signe in (("D", 1.0), ("G", -1.0)):
                    cle = "bras_%s" % cote
                    if cle in pose:
                        pose[cle] = (bx, pose[cle][1], abs(bz) * signe)
                    cla = "avbras_%s" % cote
                    if cla in pose:
                        pose[cla] = (av, pose[cla][1], pose[cla][2])
                appliquer(arm, pose, k)
                s, qui = score(arm, perso, cam, sc, plan)
                ec, co = silhouette(arm)
                montee, ecartM = lisibilite(arm, z0)
                if s > SEUIL_SOMMETS:
                    etat = "recouvre:%s" % qui
                elif ec > ECART_MAXI:
                    etat = "en croix"
                elif co < COUDE_MINI:
                    etat = "coude raide"
                else:
                    etat = "OK"
                print("   X=%-5.0f Z=%-4.0f av=%-5.0f %7d %6.0f %6.0f %8.0f "
                      "%7.0f  %s"
                      % (bx, bz, av, s, ec, co, montee, ecartM, etat))


main()
