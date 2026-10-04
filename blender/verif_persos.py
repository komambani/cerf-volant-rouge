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


def _verifier():
    for nom in ("Awa", "Tano"):
        _un_personnage(nom)


def _un_personnage(nom):
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

    # 4c. L'ourlet ne doit pas BALLONNER : un t-shirt tombe le long du corps.
    # Defaut v10 : pour eviter les cuisses, l'ourlet avait ete elargi a leur
    # diametre et formait un bourrelet. Le tissu ne depasse pas 35 % du rayon
    # du tronc nu a la meme hauteur.
    corps_pts = pts_monde(corps)
    z_ourlet_mes = min(p.z for p in ph)
    r_tissu = rayon_tranche(ph, cx, z_ourlet_mes + 0.012)
    r_peau = rayon_tranche(corps_pts, cx, z_ourlet_mes + 0.012)
    if r_tissu and r_peau:
        bouffant = r_tissu / r_peau
        check("%s : ourlet pres du corps" % nom, bouffant < 1.35,
              "tissu %.1f %% du tronc nu" % (bouffant * 100))
    # 4d. Les bras doivent etre DEGAGES du buste : en v11 ils pendaient colles
    # au torse, les mains touchaient les cuisses, la silhouette fusionnait.
    S = C.squelette(f)
    R = C.rayons(f, S)
    bras_x = abs(S["poignet"](1).x)
    buste_x = R["poitrine"] * 1.16
    check("%s : bras degages du buste" % nom, bras_x > buste_x * 1.08,
          "poignet a %.0f %% du demi-buste" % (bras_x / buste_x * 100))

    # 4e. Le sac ne doit pas occuper la place du bras (defaut v11 : la main de
    # Tano traversait le sac porte a la hanche).
    sac = bpy.data.objects.get("%s_SAC" % nom)
    mains = [o for o in pieces if "_MAIN" in o.name]
    if sac and mains:
        def centre_xy(o):
            b = englobant(o)
            return Vector(((b[0] + b[1]) / 2, (b[2] + b[3]) / 2))
        cs = centre_xy(sac)
        dmin = min((cs - centre_xy(m)).length for m in mains)
        check("%s : sac degage des mains" % nom, dmin > 0.055,
              "%.0f mm de la main la plus proche" % (dmin * 1000))

    # 4f. LE BRAS DOIT AVOIR DU VOLUME. Controle le plus important du lot : en
    # v12 le verificateur a affiche 43/43 alors que les deux personnages
    # n'avaient PLUS DE BRAS (reduits a un fil noir). Aucun controle ne
    # mesurait la chair des membres ; compter les maillages ne suffit pas,
    # l'objet CORPS existait toujours. On mesure donc le rayon perpendiculaire
    # a l'axe coude-poignet, qui doit rester proche du rayon theorique.
    corps_pts = pts_monde(corps)
    arm_ob = bpy.data.objects["%s_RIG" % nom]
    k = arm_ob.scale.x
    off = arm_ob.location

    def en_monde(p):
        return Vector((p.x * k + off.x, p.y * k + off.y, p.z * k + off.z))

    for s, cote in ((-1, "gauche"), (1, "droit")):
        co = en_monde(S["coude"](s))
        po = en_monde(S["poignet"](s))
        axe = (po - co).normalized()
        rayons_mes = []
        for u in (0.30, 0.50, 0.70):
            centre = co + (po - co) * u
            proches = []
            for q in corps_pts:
                v = q - centre
                t = v.dot(axe)
                if abs(t) < 0.010:
                    d = (v - axe * t).length
                    if d < 0.075:          # au-dela : torse ou jambe
                        proches.append(d)
            if proches:
                rayons_mes.append(sum(proches) / len(proches))
        r_theo = R["avbras"] * k
        if rayons_mes:
            r_moy = sum(rayons_mes) / len(rayons_mes)
            check("%s : avant-bras %s a du volume" % (nom, cote),
                  r_moy > r_theo * 0.45,
                  "rayon %.1f mm (theorique %.1f)" % (r_moy * 1000,
                                                     r_theo * 1000))
        else:
            check("%s : avant-bras %s a du volume" % (nom, cote), False,
                  "AUCUN sommet autour de l'axe : le bras n'existe pas")

    # 4g. Meme controle pour les JAMBES : meme structure de chaine, donc meme
    # risque de degenerescence du Skin.
    for s, cote in ((-1, "gauche"), (1, "droit")):
        g = en_monde(S["genou"](s))
        cv = en_monde(S["cheville"](s))
        axe = (cv - g).normalized()
        rs = []
        for u in (0.30, 0.55):
            centre = g + (cv - g) * u
            proches = []
            for q in corps_pts:
                v = q - centre
                t = v.dot(axe)
                if abs(t) < 0.010:
                    d = (v - axe * t).length
                    if d < 0.090:
                        proches.append(d)
            if proches:
                rs.append(sum(proches) / len(proches))
        r_theo = R["mollet"] * k
        check("%s : mollet %s a du volume" % (nom, cote),
              bool(rs) and (sum(rs) / len(rs)) > r_theo * 0.45,
              ("rayon %.1f mm (theorique %.1f)"
               % ((sum(rs) / len(rs)) * 1000, r_theo * 1000)) if rs
              else "AUCUN sommet autour de l'axe")

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
# Le corps du verificateur est enveloppe : une exception Python (nom non defini,
# objet absent) doit se lire comme un ECHEC franc, pas disparaitre dans le log
# en laissant la sortie ressembler a un succes partiel (defaut v12 : un
# NameError interrompait la boucle, le dernier controle affiche restait [OK]).
try:
    _verifier()
except Exception as exc:
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 72)
    print("ECHEC : le verificateur lui-meme a plante -> %s" % exc)
    print("=" * 72)
    sys.exit(2)

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
