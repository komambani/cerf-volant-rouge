# -*- coding: utf-8 -*-
"""Poses et animation des 15 plans, derivees du decoupage technique.

Principe, identique a celui du reste du projet : AUCUNE pose n'est inventee
ici. Chaque plan du document porte trois etats (debut / evenement a 2 s / fin),
une emotion et une intensite ; ce fichier traduit ces champs en rotations d'os
et en positions de rig. Changer le document change l'animation.

    blender -b blender/cvr01_persos.blend -P blender/poses.py -- \
        --scene blender/cvr01_scene.blend --out blender/cvr01_anim.blend
"""
import bpy
import sys
import os
import math
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "doc"))

import cvr01_model as M          # noqa: E402

FPS = 24
DUREE_PLAN = 5.0                 # s
F_PAR_PLAN = int(FPS * DUREE_PLAN)   # 120


# ---------------------------------------------------------------------------
# Vocabulaire de poses : une pose = un dictionnaire os -> rotation (degres).
# Les noms d'os viennent de armature() dans characters.py.
# ---------------------------------------------------------------------------
NEUTRE = {}

# Limites anatomiques sur l'axe X, en degres. Elles bornent le produit
# pose x intensite : un bras humain ne depasse pas la verticale vers l'avant,
# un coude ne se plie que dans un sens, un genou non plus.
LIMITES = {
    "bras_D": (-168.0, 60.0),
    "bras_G": (-168.0, 60.0),
    "avbras_D": (-145.0, 0.0),      # le coude ne s'inverse pas
    "avbras_G": (-145.0, 0.0),
    "epaule_D": (-30.0, 30.0),      # la clavicule bouge peu
    "epaule_G": (-30.0, 30.0),
    "cuisse_D": (-95.0, 40.0),
    "cuisse_G": (-95.0, 40.0),
    "tibia_D": (0.0, 140.0),        # le genou ne plie que vers l'arriere
    "tibia_G": (0.0, 140.0),
    "pied_D": (-35.0, 45.0),
    "pied_G": (-35.0, 45.0),
    "cou": (-40.0, 35.0),
    "tete": (-35.0, 30.0),
    "colonne": (-25.0, 30.0),
    "poitrine": (-20.0, 25.0),
}

# IMPORTANT : ces noms doivent correspondre EXACTEMENT a ceux crees par
# armature() dans characters.py. En v1 de ce fichier j'avais invente des noms
# de convention Rigify ("epaule.R", "torse") qui n'existaient pas : les poses
# etaient silencieusement ignorees et seuls "cou" et "tete" bougeaient.
#
# Os reels : racine, bassin, colonne, poitrine, cou, tete,
#            epaule_G/D, bras_G/D, avbras_G/D, main_G/D,
#            cuisse_G/D, tibia_G/D, pied_G/D, ik_main_G/D, ik_pied_G/D.
#
# SENS DE ROTATION, mesure sur le rig (ne pas deviner) :
#   colonne, poitrine, cou, tete  pointent vers le HAUT (dir Z = +1,00)
#       -> rotation X NEGATIVE = bascule en arriere = regarder vers le haut.
#   bras_*, avbras_*, cuisse_*, tibia_*  pointent vers le BAS (dir Z = -0,98)
#       -> rotation X POSITIVE fait monter le membre VERS L'ARRIERE,
#          rotation X NEGATIVE le fait monter VERS L'AVANT.
#       Mesure (v3 de ce fichier) : bras_D a +78 donne dy +143 mm, donc la main
#       passe DERRIERE le dos ; a -78 elle passe devant. Le personnage regarde
#       vers -Y (c'est le cote du visage, cf. characters.py).
#   Un bras leve droit au-dessus de la tete passe par l'avant : -165 en X.
#   epaule_* (la clavicule) pointe vers le haut-dehors (+0,80 / +0,60) :
#       X POSITIF LEVE l'epaule (+30 -> main 120 mm plus haut),
#       X NEGATIF l'AFFAISSE (-30 -> main 74 mm plus bas, pose de deception).
#       Mesure isolee os par os, apres m'etre trompe deux fois de suite en
#       raisonnant sur la direction du bone au lieu de mesurer.

POSES = {
    # --- regarder vers le haut (le cerf-volant est dans l'arbre) ---
    "regarde_haut": {
        "cou": (-22, 0, 0),
        "tete": (-16, 0, 0),
        "colonne": (-6, 0, 0),
    },
    "regarde_haut_fort": {
        "cou": (-30, 0, 0),
        "tete": (-22, 0, 0),
        "colonne": (-10, 0, 0),
        "poitrine": (-6, 0, 0),
    },
    # --- tendre le bras vers la ficelle (vers l'avant-haut) ---
    # epaule_* POSITIF leve la clavicule (mesure : +30 -> main 120 mm plus
    # haut). J'avais mis du negatif, qui l'affaisse : l'epaule descendait
    # pendant que le bras montait.
    "tend_bras_d": {
        "bras_D": (-105, 0, 12),
        "avbras_D": (-22, 0, 0),
        "epaule_D": (8, 0, 0),
        "cou": (-20, 0, 0),
        "tete": (-14, 0, 0),
        "colonne": (-8, 0, 4),
    },
    # Le bras s'eleve vers la ficelle en restant pres de l'axe du corps :
    # a 80 deg d'ecartement il partait a l'horizontale et la tete d'Awa
    # disparaissait derriere l'epaule. 26 deg suffisent a degager la figure.
    "tend_bras_d_max": {
        "bras_D": (-128, 0, 26),
        "avbras_D": (-22, 0, 0),
        "epaule_D": (18, 0, 0),
        "cou": (-26, 0, 0),
        "tete": (-18, 0, 0),
        "colonne": (-12, 0, 8),
        "poitrine": (-8, 0, 5),
        "bras_G": (-18, 0, -10),
    },
    # --- tirer sur la ficelle : mains devant la POITRINE, pas le menton ---
    # Mesure (v18) : a -78 deg les mains arrivaient a hauteur de visage et le
    # recouvraient a 46 % du rayon. On tire une corde bras plus bas, coudes
    # au corps -- c'est aussi plus juste anatomiquement.
    "tire_ficelle": {
        "bras_D": (-52, 0, 26),
        "avbras_D": (-62, 0, 0),
        "bras_G": (-52, 0, -26),
        "avbras_G": (-62, 0, 0),
        "colonne": (6, 0, 0),
        "cou": (-14, 0, 0),
    },
    "tire_ficelle_fort": {
        "bras_D": (-44, 0, 30),
        "avbras_D": (-84, 0, 0),
        "bras_G": (-44, 0, -30),
        "avbras_G": (-84, 0, 0),
        "colonne": (14, 0, 0),
        "poitrine": (6, 0, 0),
        "cou": (-8, 0, 0),
        "cuisse_D": (-14, 0, 0),
    },
    # --- deception / echec : epaules tombantes, dos rond, bras inertes ---
    # Mesure isolee du rig (v5) -- le sens de epaule_* est l'INVERSE de ce que
    # j'avais suppose deux fois de suite :
    #     epaule_D X = -30 -> main 74 mm PLUS BAS
    #     epaule_D X = +30 -> main 120 mm plus haut
    #     bras_D   X =  -8 -> main 2 mm plus bas, 52 mm en avant
    # La deception combine donc epaule_* NEGATIF (l'epaule s'affaisse) et un
    # bras legerement en avant. Le dos rond vient de colonne/poitrine positifs.
    "epaules_basses": {
        "epaule_D": (-16, 0, 0),
        "epaule_G": (-16, 0, 0),
        "bras_D": (-6, 0, 4),
        "bras_G": (-6, 0, -4),
        "colonne": (9, 0, 0),
        "poitrine": (6, 0, 0),
        "cou": (14, 0, 0),
        "tete": (10, 0, 0),
    },
    # --- joie, bras leves de part et d'autre de la tete ---
    # Les grands ecartements (85-100 deg) degagent le visage mais donnent des
    # bras en croix, coudes pointant vers l'exterieur : a l'image Tano a l'air
    # d'un epouvantail, pas d'un enfant joyeux. Un bras leve humain reste
    # PRES DE L'AXE DU CORPS, coude flechi, main a hauteur de tempe.
    # L'ecartement sert a degager la figure, pas a faire une croix : 30 deg
    # suffisent si les bras ne montent pas jusqu'a la verticale.
    # Bras leves de soulagement. Mesures (v38-v41). Le levier n'est pas l'axe
    # Z : balayage a -58 deg d'elevation, ecart entre les mains = 125 mm a
    # Z=0, 25 mm a Z=30, 46 mm a Z=52, 120 mm a Z=90. La courbe PASSE PAR UN
    # MINIMUM : le Z croise les bras devant le torse avant de les rouvrir --
    # a l'image, Tano avait les bras croises sur la poitrine. C'est l'axe Y
    # qui ouvre : 46 mm a Y=0, 254 mm a Y=-25, 481 mm a Y=-45, en gardant la
    # main sous le menton (z=0,846 contre 1,121 pour le menton).
    "bras_leves": {
        "bras_D": (-58, -42, 18),
        "bras_G": (-58, 42, -18),
        "avbras_D": (-16, 0, 0),
        "avbras_G": (-16, 0, 0),
        "epaule_D": (16, 0, 0),
        "epaule_G": (16, 0, 0),
        "colonne": (-8, 0, 0),
        "cou": (-14, 0, 0),
        "tete": (-8, 0, 0),
    },
    # --- tendre un objet a quelqu'un, a hauteur de poitrine ---
    "tend_objet": {
        "bras_D": (-58, 0, 20),
        "avbras_D": (-26, 0, 0),
        "colonne": (0, 0, 8),
        "cou": (-6, 0, -10),
        "tete": (-4, 0, -8),
    },
    # --- recevoir, mains en avant a hauteur de poitrine ---
    "recoit": {
        "bras_D": (-52, 0, 18),
        "bras_G": (-52, 0, -18),
        "avbras_D": (-34, 0, 0),
        "avbras_G": (-34, 0, 0),
        "cou": (-8, 0, 0),
        "colonne": (-4, 0, 0),
    },
    # --- marche / course, phase de contact ---
    "pas_avant": {
        "cuisse_D": (-30, 0, 0),
        "tibia_D": (14, 0, 0),
        "cuisse_G": (22, 0, 0),
        "tibia_G": (-32, 0, 0),
        "bras_D": (18, 0, 0),
        "bras_G": (-16, 0, 0),
        "colonne": (-5, 0, 0),
    },
    "pas_arriere": {
        "cuisse_D": (24, 0, 0),
        "tibia_D": (-34, 0, 0),
        "cuisse_G": (-28, 0, 0),
        "tibia_G": (12, 0, 0),
        "bras_D": (-17, 0, 0),
        "bras_G": (19, 0, 0),
        "colonne": (-5, 0, 0),
    },
    # --- monte sur le tabouret, se hisse sur la pointe des pieds ---
    "sur_pointes": {
        "cuisse_D": (-7, 0, 0),
        "cuisse_G": (-7, 0, 0),
        "tibia_D": (12, 0, 0),
        "tibia_G": (12, 0, 0),
        "pied_D": (28, 0, 0),
        "pied_G": (28, 0, 0),
        "colonne": (-8, 0, 0),
        "cou": (-18, 0, 0),
        "tete": (-12, 0, 0),
    },
    # --- surprise, recul, mains qui remontent devant ---
    "sursaut": {
        "colonne": (8, 0, 0),
        "poitrine": (5, 0, 0),
        "cou": (-10, 0, 0),
        "tete": (-6, 0, 0),
        "bras_D": (-34, 0, 18),
        "bras_G": (-34, 0, -18),
        "avbras_D": (-48, 0, 0),
        "avbras_G": (-48, 0, 0),
    },
}


# ---------------------------------------------------------------------------
# Traduction document -> poses. Table de correspondance explicite : chaque
# plan nomme ses trois etats. Les mots-cles viennent des champs debut /
# evenement / fin du decoupage.
# ---------------------------------------------------------------------------
CHOREGRAPHIE = {
    # Qui est au plan vient du document (champ `persos`), pas de mon idee de
    # la scene : valider_choregraphie() refuse toute divergence dans les deux
    # sens. En v6 j'avais anime Awa sur P003 et P011, Tano sur P002, P005 et
    # P007, alors que ces plans sont des plans a un seul personnage.
    "S01-P001": {"Awa": ("regarde_haut", "sursaut", "regarde_haut_fort"),
                 "Tano": ("regarde_haut", "sursaut", "regarde_haut")},
    "S01-P002": {"Awa": ("regarde_haut", "regarde_haut_fort",
                         "regarde_haut_fort")},
    "S01-P003": {"Tano": ("NEUTRE", "sur_pointes", "tend_bras_d")},
    "S01-P004": {"Tano": ("sur_pointes", "tire_ficelle_fort",
                          "epaules_basses")},
    "S01-P005": {"Awa": ("NEUTRE", "regarde_haut", "regarde_haut_fort")},
    "S01-P006": {"Awa": ("regarde_haut", "regarde_haut_fort", "NEUTRE"),
                 "Tano": ("epaules_basses", "NEUTRE", "regarde_haut")},
    "S01-P007": {"Awa": ("NEUTRE", "pas_avant", "pas_avant")},
    "S01-P008": {"Awa": ("sur_pointes", "tend_bras_d_max", "tend_bras_d")},
    "S01-P009": {"Awa": ("tend_bras_d", "tire_ficelle", "tire_ficelle_fort")},
    "S01-P010": {"Awa": ("tire_ficelle_fort", "tire_ficelle", "NEUTRE"),
                 "Tano": ("regarde_haut", "regarde_haut_fort", "sursaut")},
    "S01-P011": {"Tano": ("NEUTRE", "bras_leves", "bras_leves")},
    "S01-P012": {"Awa": ("bras_leves", "tend_objet", "tend_objet"),
                 "Tano": ("NEUTRE", "recoit", "recoit")},
    "S01-P013": {"Awa": ("NEUTRE", "pas_avant", "pas_arriere"),
                 "Tano": ("NEUTRE", "pas_arriere", "pas_avant")},
    "S01-P014": {"Awa": ("regarde_haut", "regarde_haut_fort",
                         "regarde_haut_fort"),
                 "Tano": ("regarde_haut", "regarde_haut_fort",
                          "regarde_haut_fort")},
    "S01-P015": {"Awa": ("NEUTRE", "regarde_haut", "regarde_haut"),
                 "Tano": ("NEUTRE", "regarde_haut", "regarde_haut")},
}


def valider_os(arm):
    """Tout nom d'os cite dans POSES doit exister dans le rig.

    Sans ce controle, une pose visant un os inexistant est silencieusement
    ignoree : c'est exactement ce qui s'est produit en v1 de ce fichier
    (noms Rigify "epaule.R"/"torse" au lieu de "bras_D"/"colonne"), et les
    personnages restaient au garde-a-vous alors que le log annoncait
    "90 poses posees". Une animation vide qui se declare reussie est le pire
    des resultats.
    """
    reels = {b.name for b in arm.pose.bones}
    cites = set()
    for pose in POSES.values():
        cites |= set(pose.keys())
    manquants = sorted(cites - reels)
    if manquants:
        print("=" * 70)
        print("ERREUR : %d os cites dans POSES n'existent pas dans %s"
              % (len(manquants), arm.name))
        for m in manquants:
            print("   - %s" % m)
        print("os reels : %s" % ", ".join(sorted(reels)))
        print("=" * 70)
        sys.exit(1)
    return len(cites)


def valider_choregraphie():
    """La choregraphie ne doit animer que les personnages presents au plan.

    Le document est la source de verite : son champ `persos` dit qui est dans
    le cadre. En v6 ma choregraphie donnait une pose a Awa sur P011 alors que
    le document ne liste que Tano -- Awa restait donc au garde-a-vous dans un
    plan ou je croyais l'avoir animee, et aucun controle ne le voyait.
    """
    fautes = []
    for plan in M.PLANS:
        pid = plan["id"]
        presents = set(plan["persos"])
        cites = set(CHOREGRAPHIE.get(pid, {}))
        for intrus in sorted(cites - presents):
            fautes.append("%s : la choregraphie anime %s, absent du plan "
                          "(presents : %s)"
                          % (pid, intrus, ", ".join(sorted(presents))))
        for oublie in sorted(presents - cites):
            fautes.append("%s : %s est au plan mais n'a aucune pose"
                          % (pid, oublie))
    if fautes:
        print("=" * 70)
        for f in fautes:
            print("ERREUR choregraphie : %s" % f)
        print("=" * 70)
        sys.exit(1)
    print("choregraphie : %d plans, personnages conformes au document"
          % len(M.PLANS))


def appliquer(arm, pose_nom, frame, intensite=4):
    """Pose les os et insere une cle.

    L'intensite du document (1-5) module l'amplitude, mais le resultat est
    BORNE aux limites anatomiques : sans cela, une pose large multipliee par
    une forte intensite sort de l'articulation. Mesure v6 : bras_leves a -165
    deg x 1,15 donnait -190 deg, soit un bras qui depasse la verticale et
    repart derriere le dos -- a l'image, les bras de Tano devenaient des
    plaques noires repliees sur le torse.
    """
    k = 0.55 + 0.15 * max(1, min(5, intensite))     # 0.70 a 1.30
    pose = {} if pose_nom == "NEUTRE" else POSES[pose_nom]
    for pb in arm.pose.bones:
        rot = pose.get(pb.name)
        pb.rotation_mode = "XYZ"
        if rot is None:
            pb.rotation_euler = Euler((0, 0, 0), "XYZ")
        else:
            lim = LIMITES.get(pb.name, (-170.0, 170.0))
            vals = []
            for idx, a in enumerate(rot):
                v = a * k
                if idx == 0:                     # l'axe X porte la flexion
                    v = max(lim[0], min(lim[1], v))
                vals.append(math.radians(v))
            pb.rotation_euler = Euler(tuple(vals), "XYZ")
        pb.keyframe_insert("rotation_euler", frame=frame)


def lisser(arm):
    """Interpolation Bezier + ease : une animation lineaire a l'air mecanique."""
    ad = arm.animation_data
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_IN_OUT"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.join(HERE, "cvr01_anim.blend")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]

    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = F_PAR_PLAN * len(M.PLANS)

    rigs = {n: bpy.data.objects.get("%s_RIG" % n) for n in ("Awa", "Tano")}
    manquants = [n for n, r in rigs.items() if r is None]
    if manquants:
        print("ERREUR : rig absent pour %s" % ", ".join(manquants))
        sys.exit(1)

    for arm in rigs.values():
        n_os = valider_os(arm)
    print("os cites dans POSES : %d, tous presents dans le rig" % n_os)
    valider_choregraphie()

    # Ordre des modificateurs : le contour doit etre calcule sur la pose.
    # Un SOLIDIFY avant l'ARMATURE fige la coque inversee au repos, elle est
    # ensuite deformee avec le maillage et ressort en plaques noires.
    mauvais = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        t = [m.type for m in o.modifiers]
        if "SOLIDIFY" in t and "ARMATURE" in t \
                and t.index("SOLIDIFY") < t.index("ARMATURE"):
            mauvais.append(o.name)
    if mauvais:
        print("ERREUR : %d objet(s) ont le contour AVANT l'armature "
              "(ex. %s)" % (len(mauvais), ", ".join(mauvais[:4])))
        sys.exit(1)
    print("contours : calcules apres l'armature sur tous les objets")

    # Amplitude reelle de chaque pose : distance parcourue par la main et par
    # la tete entre la pose neutre et la pose posee. Une pose qui ne deplace
    # rien n'est pas une pose, meme si le log annonce qu'elle est posee.
    ref = rigs["Awa"]

    def position_mains(a):
        return [a.matrix_world @ a.pose.bones[b].head
                for b in ("main_D", "main_G", "tete")]

    appliquer(ref, "NEUTRE", 1)
    bpy.context.view_layer.update()
    p0 = position_mains(ref)
    tete0 = ref.matrix_world @ ref.pose.bones["tete"].head
    print("-" * 70)
    print("%-20s %8s %8s %8s   %s"
          % ("pose", "main_D", "main_G", "tete", "controle de direction"))
    mortes = []
    fautes = []
    # Direction attendue de la main droite, mesuree en mm (dz positif = plus
    # haut que la pose neutre, dy negatif = devant le personnage).
    # "Ca bouge" ne suffit pas : en v2 les bras partaient en ARRIERE et
    # traversaient la tete, avec une amplitude de 676 mm qui passait le
    # controle de pose morte. On verifie donc le SENS, pas seulement la norme.
    ATTENDU = {
        "bras_leves": ("dz", +0.20, "main au-dessus de l'epaule"),
        "tend_bras_d_max": ("dz", +0.15, "main haute, bras tendu"),
        "tend_bras_d": ("dz", +0.05, "main en haut"),
        "tire_ficelle": ("dy", -0.08, "mains devant le corps"),
        "tire_ficelle_fort": ("dy", -0.08, "mains devant le corps"),
        "recoit": ("dy", -0.10, "mains en avant"),
        "tend_objet": ("dy", -0.10, "main tendue en avant"),
        "epaules_basses": ("dz", -0.01, "mains plus basses"),
        "sursaut": ("dy", -0.04, "mains qui remontent devant"),
    }
    for nom_pose in sorted(POSES):
        appliquer(ref, nom_pose, 1)
        bpy.context.view_layer.update()
        p1 = position_mains(ref)
        d = [(p1[i] - p0[i]).length * 1000 for i in range(3)]
        mort = max(d) < 15.0
        if mort:
            mortes.append(nom_pose)
        note = ""
        att = ATTENDU.get(nom_pose)
        if att:
            axe, seuil, libelle = att
            delta = (p1[0] - p0[0]).z if axe == "dz" else (p1[0] - p0[0]).y
            ok = delta >= seuil if seuil > 0 else delta <= seuil
            note = "%s %+.0f mm %s" % (axe, delta * 1000, "OK" if ok else "FAUX")
            if not ok:
                fautes.append("%s (%s, attendu %s %+.0f mm, obtenu %+.0f)"
                              % (nom_pose, libelle, axe, seuil * 1000,
                                 delta * 1000))
        # La main ne doit jamais traverser la tete.
        for i in (0, 1):
            if (p1[i] - tete0).length < 0.075:
                fautes.append("%s : main %s dans la tete (%.0f mm)"
                              % (nom_pose, "D" if i == 0 else "G",
                                 (p1[i] - tete0).length * 1000))
        print("%-20s %8.0f %8.0f %8.0f   %s%s"
              % (nom_pose, d[0], d[1], d[2], note,
                 "  <-- POSE MORTE" if mort else ""))
    if mortes or fautes:
        print("-" * 70)
        for m in mortes:
            print("ERREUR pose morte : %s" % m)
        for e in fautes:
            print("ERREUR direction  : %s" % e)
        sys.exit(1)
    print("-" * 70)

    # On repart d'une action propre : les cles de test ci-dessus ne doivent pas
    # rester dans l'animation finale.
    for arm in rigs.values():
        if arm.animation_data and arm.animation_data.action:
            bpy.data.actions.remove(arm.animation_data.action)
        arm.animation_data_clear()

    print("=" * 70)
    print("ANIMATION DES %d PLANS (%d i/s, %d images par plan)"
          % (len(M.PLANS), FPS, F_PAR_PLAN))
    print("=" * 70)

    poses_posees = 0
    for i, plan in enumerate(M.PLANS):
        pid = plan["id"]
        f0 = 1 + i * F_PAR_PLAN
        f_evt = f0 + int(FPS * 2.0)          # l'evenement est a 2 s, champ E
        f1 = f0 + F_PAR_PLAN - 1
        choreo = CHOREGRAPHIE.get(pid, {})
        inten = plan.get("intensite", 3)

        for nom, arm in rigs.items():
            if nom in plan["persos"] and nom in choreo:
                d, e, fin = choreo[nom]
            else:
                # Personnage absent du plan : il garde la pose neutre, mais on
                # cle quand meme pour qu'il ne derive pas depuis le plan
                # precedent.
                d = e = fin = "NEUTRE"
            appliquer(arm, d, f0, inten)
            appliquer(arm, e, f_evt, inten)
            appliquer(arm, fin, f1, inten)
            poses_posees += 3

        print("%-10s %-14s i%4d-%4d  evt i%4d  intensite %d  %s"
              % (pid, plan["emotion"], f0, f1, f_evt, inten,
                 " / ".join("%s:%s>%s>%s" % (n, *choreo[n])
                            for n in sorted(choreo))))

    for arm in rigs.values():
        lisser(arm)

    # Controle FINAL sur la timeline : jusqu'ici je validais le vocabulaire des
    # poses sur un rig isole, hors animation. Deux defauts majeurs sont passes
    # ainsi (Awa jamais animee sur P011, Tano a -190 deg). On relit donc les
    # angles REELLEMENT evalues image par image, interpolation comprise.
    print("-" * 70)
    depassements = []
    etires = []
    dg = bpy.context.evaluated_depsgraph_get()
    sc.frame_set(1)
    for i in range(len(M.PLANS)):
        for f in (1 + i * F_PAR_PLAN, 1 + i * F_PAR_PLAN + FPS,
                  1 + i * F_PAR_PLAN + FPS * 2, 1 + i * F_PAR_PLAN + FPS * 3,
                  i * F_PAR_PLAN + F_PAR_PLAN):
            sc.frame_set(f)
            for nom, arm in rigs.items():
                for pb in arm.pose.bones:
                    lim = LIMITES.get(pb.name)
                    if not lim:
                        continue
                    deg = math.degrees(pb.rotation_euler.x)
                    marge = 6.0          # tolerance d'overshoot Bezier
                    if deg < lim[0] - marge or deg > lim[1] + marge:
                        depassements.append(
                            "%s i%d %s : %.0f deg hors [%.0f, %.0f]"
                            % (nom, f, pb.name, deg, lim[0], lim[1]))
    if depassements:
        for d in depassements[:12]:
            print("ERREUR timeline : %s" % d)
        print("ERREUR : %d depassement(s) d'articulation sur la timeline"
              % len(depassements))
        sys.exit(1)
    print("timeline : angles dans les limites anatomiques sur %d images testees"
          % (len(M.PLANS) * 5))

    # Etirement des pieces rigides : une main, une perle ou un oeil ne change
    # pas de taille quand le personnage bouge. On mesure la diagonale de leur
    # boite englobante ANIMEE et on la compare a celle du repos. C'est le
    # controle qui manquait quand les mains s'etiraient sur 89 cm sans que
    # rien ne proteste.
    PIECES = ("MAIN", "PERLE", "IRIS", "PUPILLE", "SCLERE", "NEZ", "OREILLE")

    def diag_objets(frame):
        sc.frame_set(frame)
        dgl = bpy.context.evaluated_depsgraph_get()
        dgl.update()
        out = {}
        for o in bpy.data.objects:
            if o.type != "MESH":
                continue
            if not any(p in o.name.upper() for p in PIECES):
                continue
            ev = o.evaluated_get(dgl)
            me = ev.to_mesh()
            if me.vertices:
                pts = [o.matrix_world @ v.co for v in me.vertices]
                d = Vector((max(p.x for p in pts) - min(p.x for p in pts),
                            max(p.y for p in pts) - min(p.y for p in pts),
                            max(p.z for p in pts) - min(p.z for p in pts)))
                out[o.name] = d.length
            ev.to_mesh_clear()
        return out

    repos = diag_objets(1)
    for i in range(len(M.PLANS)):
        anime = diag_objets(1 + i * F_PAR_PLAN + FPS * 2)
        for nom_o, d1 in anime.items():
            d0 = repos.get(nom_o, 0.0)
            if d0 > 1e-6 and d1 > d0 * 1.60:
                etires.append("%s i%d : %.0f mm au lieu de %.0f (x%.1f)"
                              % (nom_o, 1 + i * F_PAR_PLAN + FPS * 2,
                                 d1 * 1000, d0 * 1000, d1 / d0))
    if etires:
        for e in etires[:10]:
            print("ERREUR etirement : %s" % e)
        print("ERREUR : %d piece(s) rigide(s) deformee(s) par l'animation"
              % len(etires))
        sys.exit(1)
    print("pieces rigides : %d objets, aucun etirement sur les 15 plans"
          % len(repos))

    # Visage degage, mesure A L'ECRAN et non dans l'espace.
    #
    # Trois versions perdues avec un critere 3D : il exigeait un ecart lateral
    # de 200 mm que seuls des bras presque horizontaux atteignaient -- les
    # personnages finissaient crucifies, et le controle passait au vert sur
    # des poses inutilisables. Ce qui compte est la projection : une main
    # peut etre a 10 cm de la tete dans l'espace et ne rien masquer si la
    # camera la voit a cote.
    #
    # Le fichier des personnages n'a PAS de camera : la premiere version de ce
    # controle faisait `break` en silence et annoncait "15 plans degages"
    # sans avoir rien mesure. On construit donc une camera de controle, a la
    # place du spectateur, et l'absence de camera est une ERREUR, jamais un
    # succes.
    from bpy_extras.object_utils import world_to_camera_view as w2c

    cam = sc.camera
    if cam is None:
        cd = bpy.data.cameras.new("CAM_CTRL")
        cd.lens = 50
        cam = bpy.data.objects.new("CAM_CTRL", cd)
        sc.collection.objects.link(cam)
        sc.camera = cam
        print("controle visage : camera de controle creee (le fichier des "
              "personnages n'en a pas)")

    masques = []
    def nom_plan(o, rigs):
        """Le personnage auquel appartient un objet ('Awa_HAUT' -> 'Awa')."""
        for p in rigs:
            if o.name.startswith(p + "_"):
                return p
        return "?"

    # Pire decompte deja rapporte, par personnage : evite qu'un objet innocent
    # herite du total de ses sommets quand son propre decompte vaut 0 (v28).
    # Initialise pour TOUS les rigs : sinon un personnage absent du plan
    # courant leve un KeyError, et Blender quitte avec le code 0 en
    # laissant croire a un succes (v29).
    rapportes = dict.fromkeys(rigs, 0)
    # Pieces de tete : elles sont normalement devant le visage, on les exclut.
    IGNORE_VISAGE = ("TETE", "CHEV", "FRANGE", "BOUCLE", "OEIL", "IRIS",
                     "PUPILLE", "SCLERE", "REFL", "NEZ", "OREILLE",
                     "PAUPIERE", "BOUCHE", "NATTE", "PERLE")
    # Le depsgraph est relu A CHAQUE IMAGE : capture une seule fois avant la
    # boucle, il evalue la geometrie du REPOS et non celle du plan. Mesure
    # (v37) : le controle comptait 21 sommets sur Tano_CORPS a P011, alors
    # qu'une mesure a l'image 1249 n'en trouve que 2 -- il jugeait le
    # personnage debout bras le long du corps, dont le buste tombe
    # naturellement dans l'ellipse d'une camera visant la tete.
    for i, plan in enumerate(M.PLANS):
        f = 1 + i * F_PAR_PLAN + FPS * 2
        sc.frame_set(f)
        # `frame_set` seul ne recalcule pas les matrices de pose : sans ce
        # `view_layer.update()`, `pose.bones[...].head` renvoie encore la
        # position de l'image precedente. Mesure (v37) : le controle comptait
        # 21 sommets sur Tano_CORPS a P011 quand une mesure directe a l'image
        # 1249 n'en trouve que 2 -- il placait l'ellipse du visage sur une
        # pose perimee, puis comparait la geometrie a jour a cette ellipse.
        bpy.context.view_layer.update()
        dg_v = bpy.context.evaluated_depsgraph_get()
        dg_v.update()
        # Parametres de prise de vue du plan, lus dans le document : c'est la
        # seule source de verite, changer le decoupage change le controle.
        cam.data.lens = float(plan["focale"])
        dist = float(plan["distance"])
        h_cam = float(plan["hauteur_cam"])
        for nom, arm in rigs.items():
            if nom not in plan["persos"]:
                continue
            tete = arm.matrix_world @ arm.pose.bones["tete"].head
            sommet = arm.matrix_world @ arm.pose.bones["tete"].tail
            # Boite du VISAGE a l'ecran : une ellipse centree entre le menton
            # et le sommet du crane. Mesure (v19) : les mains de "tire_ficelle"
            # sont a dx 0,062 / dy 0,010 d'un rayon de crane de 0,248 -- a
            # hauteur de menton, nettement SOUS les yeux. Un test circulaire
            # autour de `tete.head` (qui est le BAS du crane) les comptait
            # comme recouvrantes. On vise donc le milieu du visage.
            #
            # La camera est celle du PLAN, pas un angle invente. Mesure (v25)
            # sur les 15 cameras du decoupage : aucune ne s'ecarte de plus de
            # 15,1 deg de l'axe du personnage (P003 ; P005, P006 et P012 a
            # 12,5 ; les onze autres pile de face). Les precedentes versions
            # jugeaient a 28 deg -- plus extreme que tout ce que le film
            # montre -- et refusaient des poses correctes.
            if True:
                cam.location = (tete.x, tete.y - dist, h_cam)
                d = tete - Vector(cam.location)
                cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
                bpy.context.view_layer.update()
                pt = w2c(sc, cam, tete)
                ps = w2c(sc, cam, sommet)
                rc = max(((ps.x - pt.x) ** 2
                          + (ps.y - pt.y) ** 2) ** 0.5, 0.02)
                cx = pt.x + (ps.x - pt.x) * 0.62
                cy = pt.y + (ps.y - pt.y) * 0.62
                rx, ry = rc * 0.46, rc * 0.42
                # Seuil calibre sur des cas dont je connais la reponse (v23,
                # apres exclusion du crane) :
                #     P002 sain   6 sommets     P008 casse   39
                #     P007 sain   0             P011 casse  345
                #     P009 sain   0
                # 20 separe les deux familles avec de la marge des deux cotes.
                seuil_sommets = 20
                # Centre et rayon du crane dans l'espace, pour ecarter la tete
                # du personnage de son propre decompte. Mesure (v23) : les 96
                # sommets accuses sur Tano_CORPS etaient a z 1,215-1,301 et
                # 7 a 17 cm devant l'os `tete` -- c'etait SA FIGURE. Le corps
                # est un maillage Skin unique qui porte aussi le crane, donc
                # filtrer par nom d'objet ne suffit pas : on filtre par
                # position, tout sommet a l'interieur du volume de la tete
                # appartient a la tete.
                centre = tete.lerp(sommet, 0.62)
                r_crane = (sommet - tete).length * 0.62
                for o in bpy.data.objects:
                    if o.type != "MESH" or not o.name.startswith(nom):
                        continue
                    if any(k in o.name.upper() for k in IGNORE_VISAGE):
                        continue
                    ev = o.evaluated_get(dg_v)
                    me = ev.to_mesh()
                    n = 0
                    for v in me.vertices:
                        p = o.matrix_world @ v.co
                        if (p - centre).length < r_crane:
                            continue
                        pp = w2c(sc, cam, p)
                        if ((pp.x - cx) / rx) ** 2 \
                                + ((pp.y - cy) / ry) ** 2 < 1.0 \
                                and pp.z < pt.z - 0.02:
                            n += 1
                    ev.to_mesh_clear()
                    # Un objet n'est rapporte que si son propre decompte
                    # depasse le seuil. Sans cette garde (v28), une piece dont
                    # le decompte vaut 0 herite du total de ses sommets quand
                    # aucun objet n'est en cause : c'est ainsi que P011 etait
                    # refuse en boucle avec 21 sommets, nombre qui ne venait
                    # d'aucun decompte reel.
                    if n > seuil_sommets and n > rapportes[nom]:
                        rapportes[nom] = n
                        masques.append(
                            "%s %s : %s recouvre le visage (%d sommets, "
                            "focale %d a %.1f m)"
                            % (nom, plan["id"], o.name, n,
                               int(plan["focale"]), dist))

    # Bras et jambes ne doivent pas se deformer : le Skin gonfle le maillage
    # autour des os et les membres doivent suivre le squelette, pas l'inverse.
    #
    # On mesure la longueur MOYENNE DES ARETES, pas la diagonale. Mesure
    # (v31) : la diagonale d'un objet augmente des qu'un membre s'ecarte du
    # corps -- Awa_HAUT passait de 0,507 a 0,562 m a P008 parce qu'elle tendait
    # le bras, sans qu'aucune chair ne bouge. Les cotes d'aretes, elles, ne
    # changent que si la matiere se deforme reellement : c'est ce qui a
    # denonce Tano_CORPS a 0,0354 -> 0,0491 m, soit +39 %, avec des membres
    # segmentes et disjoints a l'image.
    etires = []
    for i, plan in enumerate(M.PLANS):
        f_evt = 1 + i * F_PAR_PLAN + FPS * 2
        sc.frame_set(f_evt)
        dg_evt = bpy.context.evaluated_depsgraph_get()
        dg_evt.update()
        pose_arete = {}
        for o in bpy.data.objects:
            if o.type != "MESH":
                continue
            if not any(o.name.startswith(p + "_") for p in rigs):
                continue
            ev = o.evaluated_get(dg_evt)
            me = ev.to_mesh()
            if me.edges:
                pose_arete[o.name] = sum(
                    (me.vertices[e.vertices[0]].co
                     - me.vertices[e.vertices[1]].co).length
                    for e in me.edges) / len(me.edges)
            ev.to_mesh_clear()
        sc.frame_set(1)
        dg_rep = bpy.context.evaluated_depsgraph_get()
        dg_rep.update()
        for o in bpy.data.objects:
            if o.type != "MESH" or o.name not in pose_arete:
                continue
            ev = o.evaluated_get(dg_rep)
            me = ev.to_mesh()
            if me.edges:
                repos = sum(
                    (me.vertices[e.vertices[0]].co
                     - me.vertices[e.vertices[1]].co).length
                    for e in me.edges) / len(me.edges)
                if repos > 0.001 and pose_arete[o.name] / repos > 1.12 \
                        and repos > 0.010:
                    # Le seuil ignore les petites pieces. Mesure (v35) :
                    # Awa_BOUCHE (aretes de 3,6 mm) et Awa_PAUPIERE1 (7,1 mm)
                    # sont signalees a +16 % et +25 % alors qu'elles pesent a
                    # 100 % sur `tete` et ne bougent pas -- du bruit de mesure
                    # sur une piece de quelques millimetres. Sous 1 cm, un
                    # pourcentage n'a pas de sens.
                    etires.append(
                        "%s %s : %s -- cotes d'aretes %+.0f %% "
                        "(%.4f -> %.4f m)"
                        % (nom_plan(o, rigs), plan["id"], o.name,
                           100.0 * (pose_arete[o.name] / repos - 1.0),
                           repos, pose_arete[o.name]))
            ev.to_mesh_clear()
    if etires:
        for m in etires[:10]:
            print("ERREUR deformation : %s" % m)
        print("ERREUR : %d maillage(s) se deforment sous la Skin"
              % len(etires))
        sys.exit(1)
    print("membres : cotes d'aretes stables sur les 15 plans")

    if masques:
        for m in masques[:10]:
            print("ERREUR visage : %s" % m)
        print("ERREUR : %d plan(s) ou une main masque le visage" % len(masques))
        sys.exit(1)
    print("visages : degages a l'ecran sur les 15 plans")

    # Silhouette lisible : le controle precedent ne verifie qu'UNE chose, que
    # rien ne passe devant la figure. Il a laisse passer des bras en croix
    # (Tano en epouvantail) et une tete noyee derriere l'epaule (Awa), parce
    # qu'aucune de ces deux fautes n'est un recouvrement. On mesure donc ce
    # qu'un dessinateur regarde en premier : l'angle du bras par rapport au
    # buste, et la flexion du coude.
    raides = []
    for i, plan in enumerate(M.PLANS):
        f = 1 + i * F_PAR_PLAN + FPS * 2
        sc.frame_set(f)
        for nom, arm in rigs.items():
            if nom not in plan["persos"]:
                continue
            axe = (arm.pose.bones["tete"].head
                   - arm.pose.bones["bassin"].head).normalized()
            for cote in ("D", "G"):
                pb_b = arm.pose.bones["bras_%s" % cote]
                pb_a = arm.pose.bones["avbras_%s" % cote]
                v_bras = (pb_b.tail - pb_b.head)
                if v_bras.length < 1e-6:
                    continue
                # angle du bras a l'axe du corps : 90 deg = bras en croix
                ecart = math.degrees(math.acos(
                    max(-1.0, min(1.0, v_bras.normalized().dot(axe)))))
                ecart = min(ecart, 180.0 - ecart)
                v_av = (pb_a.tail - pb_a.head)
                coude = math.degrees(math.acos(max(-1.0, min(1.0,
                    v_bras.normalized().dot(v_av.normalized())))))
                leve = (pb_b.tail - pb_b.head).dot(axe) > 0.30 * v_bras.length
                if leve and ecart > 62.0:
                    raides.append(
                        "%s %s : bras_%s en croix (%.0f deg de l'axe du "
                        "corps, maxi 62)" % (nom, plan["id"], cote, ecart))
                if leve and coude < 12.0:
                    raides.append(
                        "%s %s : bras_%s tendu raide (coude flechi de "
                        "%.0f deg, mini 12)" % (nom, plan["id"], cote, coude))
    if raides:
        for m in raides[:10]:
            print("ERREUR silhouette : %s" % m)
        print("ERREUR : %d bras en croix ou raides" % len(raides))
        sys.exit(1)
    print("silhouettes : bras pres du corps et coudes flechis sur les "
          "15 plans")

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print("-" * 70)
    print("%d poses posees sur %d plans" % (poses_posees, len(M.PLANS)))
    print("duree totale : %d images = %.0f s" % (sc.frame_end,
                                                 sc.frame_end / float(FPS)))
    print("enregistre : %s" % os.path.abspath(out))


if __name__ == "__main__":
    # Un plantage ne doit JAMAIS ressembler a un succes : Blender quitte avec
    # le code 0 meme quand le script leve une exception. Sans ce try, un
    # KeyError interruption un controle et le shell annoncait POSES=0, comme
    # si tout avait passe (v29).
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
