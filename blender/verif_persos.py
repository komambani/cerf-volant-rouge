# -*- coding: utf-8 -*-
"""Verificateur de personnages : mesure les defauts au lieu de les juger a l'oeil.

Rejoue sur la geometrie evaluee tous les defauts rencontres de la v1 a la v4.
Sortie 0 si tout passe, 1 sinon.

    blender -b blender/cvr01_persos.blend -P blender/verif_persos.py
"""
import bpy
import sys
import os
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characters as C  # noqa: E402

ECHECS = []
TOTAL = [0]


def check(nom, ok, detail=""):
    TOTAL[0] += 1
    print("  [%s] %-52s %s" % ("OK" if ok else "!!", nom, detail))
    if not ok:
        ECHECS.append(nom)
    return ok


def mesh_monde(ob):
    """Sommets en coordonnees monde, apres modificateurs."""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ob.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def englobant(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return (min(p.x for p in pts), max(p.x for p in pts),
            min(p.y for p in pts), max(p.y for p in pts),
            min(p.z for p in pts), max(p.z for p in pts))


def couverture_verticale(vet, corps_z0, corps_z1):
    """Fraction du tronc couverte par le vetement."""
    _, _, _, _, z0, z1 = englobant(vet)
    return (z1 - z0) / (corps_z1 - corps_z0)


print("\n" + "=" * 72)
print("VERIFICATION DES PERSONNAGES")
print("=" * 72)

for nom in ("Awa", "Tano"):
    f = C.FICHES[nom]
    print("\n--- %s ---" % nom)
    pieces = [o for o in bpy.data.objects
              if o.type == "MESH" and o.name.startswith(nom + "_")]
    check("%s : maillages presents" % nom, len(pieces) >= 20,
          "%d maillages" % len(pieces))

    # 1. Taille exacte (champ C)
    h = C.hauteur_reelle(pieces)
    check("%s : taille au mm" % nom, abs(h - f["taille"]) < 0.002,
          "%.3f m (vise %.3f)" % (h, f["taille"]))

    # 2. Canon enfant : defaut v1 (adulte etire) et v3 (tete trop grosse)
    ht, canon = C.canon_mesure(nom, pieces)
    check("%s : canon enfant" % nom, abs(canon - f["tetes"]) < 0.45,
          "%.2f tetes (vise %.2f)" % (canon, f["tetes"]))

    # 3. Le ventre doit etre couvert : defaut v4
    corps = bpy.data.objects["%s_CORPS" % nom]
    haut = bpy.data.objects["%s_HAUT" % nom]
    bas = bpy.data.objects["%s_BAS" % nom]
    _, _, _, _, hz0, hz1 = englobant(haut)
    _, _, _, _, bz0, bz1 = englobant(bas)
    recouvre = bz1 - hz0
    check("%s : haut et bas se recouvrent" % nom, recouvre > 0.0,
          "recouvrement %.1f mm" % (recouvre * 1000))

    # 4. Pas de peau nue entre les deux vetements
    peau_nue = hz0 - bz1
    check("%s : pas de ventre nu" % nom, peau_nue < 0.001,
          "ecart %.1f mm" % (peau_nue * 1000))

    # 4b. Dentelle a la jonction = z-fighting : deux surfaces quasi confondues
    # que le moteur n'arrive pas a departager, d'ou le bord en dents de scie.
    #
    # Le critere n'est PAS un sens de recouvrement constant : sous l'ourlet,
    # le pantalon doit evidemment depasser (c'est l'aspect normal d'un bas de
    # t-shirt), et exiger un signe constant faisait echouer une geometrie
    # correcte (v8). Ce qui compte est l'ECART ABSOLU : tant que les deux
    # surfaces sont separees de quelques millimetres, le rendu est propre.
    def pts_monde(ob):
        deps = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        mw = ob.matrix_world
        p = [mw @ v.co for v in me.vertices]
        ev.to_mesh_clear()
        return p

    def rayon_tranche(pts, cx, z, tol=0.008):
        best = None
        for p in pts:
            if abs(p.z - z) > tol or abs(p.x - cx) > 0.16:
                continue
            r = ((p.x - cx) ** 2 + p.y ** 2) ** 0.5
            if best is None or r > best:
                best = r
        return best

    arm = bpy.data.objects["%s_RIG" % nom]
    cx = arm.location.x
    ph, pb = pts_monde(haut), pts_monde(bas)
    z_lo = max(min(p.z for p in ph), min(p.z for p in pb))
    z_hi = min(max(p.z for p in ph), max(p.z for p in pb))
    SEUIL = 3.0            # mm : en deca, les deux surfaces z-fightent
    N = 24
    serres = []
    mini = None
    for i in range(N + 1):
        z = z_lo + (z_hi - z_lo) * i / float(N)
        rh = rayon_tranche(ph, cx, z)
        rb = rayon_tranche(pb, cx, z)
        # On ignore les bouts de chaine, ou le Skin ferme la surface en pointe
        if rh is None or rb is None or rh < 0.02 or rb < 0.02:
            continue
        d = abs(rh - rb) * 1000
        mini = d if mini is None else min(mini, d)
        if d < SEUIL:
            serres.append((z, d))
    check("%s : jonction sans z-fighting" % nom, not serres,
          "ecart min %.1f mm sur la zone commune (seuil %.0f)"
          % (mini if mini is not None else -1, SEUIL))

    # 5. Yeux complets : sclere + iris + pupille + reflets (defaut v1)
    for part in ("SCLERE", "IRIS", "PUPILLE", "REFL_A"):
        n = len([o for o in pieces if part in o.name])
        check("%s : %s x2" % (nom, part.lower()), n == 2, "%d trouve(s)" % n)

    # 6. Bouche presente (defaut v1)
    check("%s : bouche" % nom,
          any("BOUCHE" in o.name for o in pieces))

    # 7. Mains presentes (defaut v1 : bras en moignon)
    nm = len([o for o in pieces if "_MAIN" in o.name])
    check("%s : deux mains" % nom, nm == 2, "%d trouvee(s)" % nm)

    # 8. Un seul trait sombre par oeil : la paupiere. Le sourcil separe faisait
    # double barre (defaut v5) ; il a ete fusionne dans la paupiere.
    npaup = len([o for o in pieces if "PAUPIERE" in o.name])
    nsour = len([o for o in pieces if "SOURCIL" in o.name])
    check("%s : paupieres x2, pas de double barre" % nom,
          npaup == 2 and nsour == 0,
          "%d paupiere(s), %d sourcil(s)" % (npaup, nsour))

    # 9. Nattes descendantes, pas des moignons (defaut v3)
    nattes = [o for o in pieces if "NATTE" in o.name]
    if nattes:
        zn0 = min(englobant(o)[4] for o in nattes)
        zn1 = max(englobant(o)[5] for o in nattes)
        longueur = zn1 - zn0
        check("%s : nattes descendantes" % nom, longueur > 0.22 * f["taille"],
              "longueur %.1f cm" % (longueur * 100))

    # 10. Cou court : defaut v1 (cou de girafe)
    S = C.squelette(f)
    lcou = (S["tete_bas"] - S["cou"]).length
    check("%s : cou court" % nom, lcou < 0.055 * f["taille"],
          "%.1f mm" % (lcou * 1000))

    # 11. Contour sur chaque piece (inverted hull)
    sans = [o.name for o in pieces
            if not any(m.name == "Contour" for m in o.modifiers)]
    check("%s : contour partout" % nom, not sans,
          "manquant: %s" % ", ".join(sans[:3]) if sans else "")

    # 12. Armature complete avec IK
    arm = bpy.data.objects["%s_RIG" % nom]
    check("%s : armature" % nom, len(arm.data.bones) == 24,
          "%d os" % len(arm.data.bones))
    iks = sum(1 for b in arm.pose.bones
              for ct in b.constraints if ct.type == "IK")
    check("%s : 4 chaines IK" % nom, iks == 4, "%d IK" % iks)

# Difference de taille : point narratif (Tano echoue en P004, Awa reussit P008)
ha = C.FICHES["Awa"]["taille"]
ht_ = C.FICHES["Tano"]["taille"]
print("\n--- narration ---")
check("ecart de taille Awa/Tano", abs((ha - ht_) - 0.14) < 0.001,
      "%.0f cm" % ((ha - ht_) * 100))
# Tano sur le tabouret de 42 cm doit rester SOUS la branche a 2,25 m
atteinte_tano = ht_ * 1.30 + 0.42
check("Tano sur tabouret n'atteint pas la branche", atteinte_tano < 2.25,
      "%.2f m < 2.25 m" % atteinte_tano)
atteinte_awa = ha * 1.30 + 0.42
check("Awa sur tabouret atteint la branche", atteinte_awa >= 2.25,
      "%.2f m >= 2.25 m" % atteinte_awa)

print("\n" + "=" * 72)
if ECHECS:
    print("ECHEC : %d/%d controles" % (len(ECHECS), TOTAL[0]))
    for e in ECHECS:
        print("   - %s" % e)
    sys.exit(1)
print("SUCCES : %d/%d controles" % (TOTAL[0], TOTAL[0]))
print("=" * 72)
