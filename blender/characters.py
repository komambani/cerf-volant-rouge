# -*- coding: utf-8 -*-
"""CVR01 - generateur de personnages riggés (Awa et Tano). Version 2.

Corrige les defauts mesures sur la planche v1 :
  - proportions d'adulte etire -> canon enfant (5,2 / 4,9 tetes)
  - cou de girafe -> cou court
  - yeux sans pupille (regard mort) -> sclere + iris + pupille + 2 reflets
  - pas de bouche -> bouche presente
  - menton en bosse rapportee -> machoire sculptee dans le crane
  - nattes en boules flottantes -> vraies nattes descendantes + frange
  - bras finissant en moignon -> mains en moufle avec pouce
  - vetements troues -> rayons derives du corps avec marge, jamais egaux

    blender -b -P blender/characters.py -- --out blender/cvr01_persos.blend
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "doc"))
import cvr01_model as M  # noqa: E402


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h, a=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), a)


# ---------------------------------------------------------------------------
# Fiches : couleurs du champ C, proportions anime enfant.
#
# Le canon en tetes est LA decision de style. Un enfant stylise lisible tient
# en 5 a 5,5 tetes ; a 6 tetes il devient un adulte miniature (defaut v1).
# Tano, plus jeune, a la tete relativement plus grosse : 4,9.
# ---------------------------------------------------------------------------
FICHES = {
    "Awa": dict(
        taille=1.48, tetes=5.2,
        peau="#6B3F2A", cheveux="#1A1012", perles="#E8822E",
        haut="#F4C542", bas="#243A73", chaussures="#F2EFE9",
        bracelet="#E8822E", sac=None,
        oeil_blanc="#FBF8F2", oeil_iris="#5A3418", oeil_pupille="#140C08",
        bouche="#8A3F38",
        carrure=0.96, ratio_jambes=0.455, forme_visage="ovale",
        coiffure="nattes", bas_long=True,
    ),
    "Tano": dict(
        taille=1.34, tetes=4.9,
        peau="#8A5538", cheveux="#17100E", perles=None,
        haut="#2E9B67", bas="#D8B980", chaussures="#6A4328",
        bracelet=None, sac="#C94335",
        oeil_blanc="#FBF8F2", oeil_iris="#7A4A22", oeil_pupille="#160D09",
        bouche="#8E4A40",
        carrure=1.06, ratio_jambes=0.430, forme_visage="rond",
        coiffure="courte", bas_long=False,
    ),
}


def mat_cel(nom, hex_c, cull=False):
    key = "MAT_%s" % nom
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfDiffuse")
    b.inputs["Color"].default_value = hexcol(hex_c)
    b.inputs["Roughness"].default_value = 1.0
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = hexcol(hex_c)
    m.use_backface_culling = cull
    return m


def mat_emi(nom, hex_c, force=1.0, cull=False):
    key = "MAT_%s" % nom
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = hexcol(hex_c)
    e.inputs["Strength"].default_value = force
    nt.links.new(e.outputs["Emission"], out.inputs["Surface"])
    m.diffuse_color = hexcol(hex_c)
    m.use_backface_culling = cull
    return m


# ---------------------------------------------------------------------------
# Squelette. Unite = hauteur de tete (hd). Le personnage regarde vers -Y.
# Toutes les cotes sont en fraction de la taille T : changer T suffit.
# ---------------------------------------------------------------------------
def squelette(f):
    T = f["taille"]
    hd = T / f["tetes"]
    c = f["carrure"]

    z_cheville = 0.075 * T
    z_genou = T * f["ratio_jambes"] * 0.52
    z_hanche = T * f["ratio_jambes"]
    z_taille = z_hanche + 0.085 * T
    z_poitrine = z_hanche + 0.175 * T
    z_epaule = z_hanche + 0.245 * T
    z_cou = z_epaule + 0.022 * T          # cou court : defaut v1 corrige
    z_menton = z_cou + 0.030 * T

    lx_ep = 0.098 * T * c
    lx_ha = 0.070 * T * c
    z_coude = z_epaule - 0.115 * T
    z_poignet = z_epaule - 0.225 * T
    # Pose de repos : les bras s'ECARTENT en descendant (coude 1.20, poignet
    # 1.32 de la demi-carrure). Colles au buste ils fusionnaient visuellement
    # avec le torse et les mains touchaient les cuisses (defaut v11).
    ECART_C, ECART_P = 1.26, 1.46

    return dict(
        hd=hd, T=T,
        bassin=Vector((0, 0, z_hanche)),
        taille=Vector((0, 0, z_taille)),
        poitrine=Vector((0, 0, z_poitrine)),
        cou=Vector((0, 0, z_cou)),
        tete_bas=Vector((0, 0, z_menton)),
        tete_centre=Vector((0, -0.004 * T, z_menton + 0.46 * hd)),
        # Haut du torse, au niveau des epaules mais sur l'axe : sans ce point
        # le vetement sautait de la poitrine au cou et le Skin tendait un plan
        # incline jusqu'aux epaules -> silhouette en cintre (defaut v11).
        haut_torse=Vector((0, 0, z_epaule)),
        epaule=lambda s: Vector((s * lx_ep, 0, z_epaule)),
        coude=lambda s: Vector((s * lx_ep * ECART_C, 0.008 * T, z_coude)),
        poignet=lambda s: Vector((s * lx_ep * ECART_P, 0.018 * T, z_poignet)),
        main=lambda s: Vector((s * lx_ep * (ECART_P + 0.06), 0.022 * T, z_poignet - 0.052 * T)),
        hanche=lambda s: Vector((s * lx_ha, 0, z_hanche)),
        genou=lambda s: Vector((s * lx_ha * 0.94, -0.006 * T, z_genou)),
        cheville=lambda s: Vector((s * lx_ha * 0.90, 0, z_cheville)),
        pied=lambda s: Vector((s * lx_ha * 0.90, -0.052 * T, z_cheville * 0.55)),
        z_epaule=z_epaule, z_hanche=z_hanche, z_cheville=z_cheville,
        z_poignet=z_poignet,
    )


ALERTES = []            # pieges Skin detectes a la construction (voir plus bas)
REPESEES = []           # pieces rigides repesees sur leur os d'appartenance
REORDONNES = []         # objets dont le contour a ete remis apres l'armature
MEMBRES_REPESES = []    # maillages dont les membres ont ete reponses par axe


def mesh_chaines(nom, chaines, mat):
    """Maillage organique : chaines de points + Skin + Subsurf.
    Les points partages entre chaines sont fusionnes (bras soudes au torse)."""
    me = bpy.data.meshes.new(nom)
    ob = bpy.data.objects.new(nom, me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    sk = bm.verts.layers.skin.verify()
    idx = {}

    def cle(p):
        return (round(p.x, 4), round(p.y, 4), round(p.z, 4))

    for ch in chaines:
        prev = None
        for p, r in ch:
            k = cle(p)
            v = idx.get(k)
            if v is None:
                v = bm.verts.new(p)
                idx[k] = v
            v[sk].radius = (r, r)
            if prev is not None and prev != v and not bm.edges.get((prev, v)):
                bm.edges.new((prev, v))
            prev = v
    bm.verts.index_update()
    # Diagnostic Skin, pose APRES construction de toutes les aretes.
    #
    # Honnetete sur sa valeur predictive : ce signal est INDICATIF, pas un
    # verdict. Mesure v16 : l'ourlet du t-shirt sort a 133,7 mm de rayon sur
    # une arete de 44,4 mm et se rend parfaitement -- c'est un disque large en
    # bout de chaine, cas normal. Le cas vraiment destructeur (bras perdus en
    # v12-v13) cumulait deux conditions : extremite a rayon surdimensionne ET
    # membre ETROIT en aval. Seule la mesure de volume des membres
    # (verif_persos.py, controles 4f et 4g) tranche pour de bon.
    for v in bm.verts:
        if len(v.link_edges) != 1:
            continue
        e = v.link_edges[0]
        autre = e.other_vert(v)
        lg = (autre.co - v.co).length
        r = v[sk].radius[0]
        # Seuil resserre : on ne signale que les extremites FINES, celles qui
        # appartiennent a un membre. Une extremite large (ourlet, ceinture) est
        # un bout de volume, pas un membre a avaler.
        if r > lg * 0.95 and r < 0.060:
            ALERTES.append(
                "%s : extremite fine a (%.3f,%.3f,%.3f) rayon %.1f mm > arete "
                "%.1f mm -- a verifier par la mesure de volume"
                % (nom, v.co.x, v.co.y, v.co.z, r * 1000, lg * 1000))
    bm.to_mesh(me)
    bm.free()

    m = ob.modifiers.new("Skin", "SKIN")
    m.use_smooth_shade = True
    s = ob.modifiers.new("Subsurf", "SUBSURF")
    s.levels, s.render_levels = 1, 2
    me.materials.append(mat)
    if me.skin_vertices:
        me.skin_vertices[0].data[0].use_root = True
    return ob


def sphere(nom, r, loc, mat, scale=(1, 1, 1), rot=(0, 0, 0), smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=14,
                                         radius=r, location=loc)
    ob = bpy.context.active_object
    ob.name = nom
    ob.scale = scale
    ob.rotation_euler = rot
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = smooth
    return ob


def contour(ob, ep):
    """Inverted hull. use_backface_culling=True est indispensable : sans lui
    l'objet devient une silhouette noire (voir build_scene.py)."""
    m = mat_emi("CONTOUR", "#0A0608", 1.0, cull=True)
    ob.data.materials.append(m)
    i = len(ob.data.materials) - 1
    md = ob.modifiers.new("Contour", "SOLIDIFY")
    md.thickness = ep
    md.offset = 1.0
    md.use_flip_normals = True
    md.use_rim = False
    md.material_offset = i
    md.material_offset_rim = i
    return md


# ---------------------------------------------------------------------------
def rayons(f, S):
    """Rayons du corps, en un seul endroit.

    corps() et vetements() lisent CE dictionnaire : un vetement est toujours
    construit sur les MEMES articulations que le corps, avec une marge. C'est
    ce qui rend les trous structurellement impossibles (defaut v1 et v2, ou
    les deux chaines avaient des points et des rayons differents).
    """
    T, c = S["T"], f["carrure"]
    # Rayons du corps. Le cou et le haut du torse sont des aretes COURTES :
    # leur rayon doit rester inferieur a leur longueur, sinon le Skin explose
    # (regle apprise en v12-v14, bras perdus puis emmanchure dechiree).
    return dict(
        cou=0.030 * T,
        poitrine=0.082 * T * c,
        taille=0.070 * T * c,
        bassin=0.078 * T * c,
        epaule=0.046 * T * c,
        bras=0.026 * T * c,
        avbras=0.022 * T * c,
        cuisse=0.042 * T * c,
        genou=0.033 * T,
        mollet=0.028 * T,
        pied=0.028 * T,
    )


def corps(nom, f, S):
    T = S["T"]
    peau = mat_cel("PEAU_%s" % nom, f["peau"])
    R = rayons(f, S)

    # haut_torse fait partie de la chaine du TRONC : c'est ce qui le rend
    # soudable. Les bras s'y rattachent ensuite et ne forment plus une ile.
    ch = [[
        (S["bassin"], R["bassin"]), (S["taille"], R["taille"]),
        (S["poitrine"], R["poitrine"]), (S["haut_torse"], R["poitrine"] * 0.92),
        (S["cou"], R["cou"]), (S["tete_bas"], R["cou"] * 1.02),
    ]]
    for s in (-1, 1):
        # Le bras part du vertex PARTAGE haut_torse : les chaines se soudent par
        # coordonnees identiques (voir mesh_chaines). En v12/v13 le depart etait
        # un point decale, donc un sommet a UNE SEULE arete -> le bras devenait
        # une ile flottante, et son rayon de racine (100 mm) depassait la
        # longueur de l'arete (80 mm) : le Skin produisait une boule qui avalait
        # le membre. Mesure : 0,6 mm de chair sur un avant-bras de 35 mm.
        ch.append([
            (S["haut_torse"], R["poitrine"] * 0.92), (S["epaule"](s), R["epaule"]),
            (S["coude"](s), R["bras"]), (S["poignet"](s), R["avbras"]),
        ])
        ch.append([
            (S["bassin"], R["bassin"]), (S["hanche"](s), R["cuisse"]),
            (S["genou"](s), R["genou"]), (S["cheville"](s), R["mollet"]),
            (S["pied"](s), R["pied"]),
        ])
    ob = mesh_chaines("%s_CORPS" % nom, ch, peau)

    # Mains en moufle : les bras finissaient en moignon en v1.
    P = [ob]
    for s in (-1, 1):
        p = S["main"](s)
        P.append(sphere("%s_MAIN%d" % (nom, s), 0.036 * T, p, peau,
                        scale=(0.80, 0.62, 1.05)))
        P.append(sphere("%s_POUCE%d" % (nom, s), 0.015 * T,
                        p + Vector((-s * 0.026 * T, -0.012 * T, 0.012 * T)),
                        peau, scale=(0.7, 0.7, 1.0)))
    return P


def tete(nom, f, S):
    T = S["T"]
    peau = mat_cel("PEAU_%s" % nom, f["peau"])
    chev = mat_cel("CHEVEUX_%s" % nom, f["cheveux"])
    blanc = mat_cel("OEIL_BLANC", f["oeil_blanc"])
    iris = mat_cel("IRIS_%s" % nom, f["oeil_iris"])
    pup = mat_cel("PUPILLE_%s" % nom, f["oeil_pupille"])
    refl = mat_emi("REFLET", "#FFFFFF", 1.6)
    bou = mat_cel("BOUCHE_%s" % nom, f["bouche"])

    # Unite du visage. Le crane est calibre a 78,5 % du canon brut (la mesure
    # v3 donnait 4,08 tetes pour 5,20 vise). TOUS les traits se placent sur
    # cette meme unite : en v4 seul le crane avait ete reduit et la frange
    # s'est retrouvee en bourrelet au-dessus du front.
    hd = S["hd"] * 0.785
    c = S["tete_bas"] + Vector((0, -0.004 * T, 0.46 * hd))

    P = []
    r = 0.47 * hd
    sc = (0.95, 0.99, 1.04) if f["forme_visage"] == "ovale" else (1.03, 1.01, 0.97)

    # Crane. La machoire n'est plus une sphere rapportee (bosse visible en v1)
    # mais un affinement du bas du crane, applique au maillage lui-meme.
    t = sphere("%s_TETE" % nom, r, c, peau, scale=sc)
    for v in t.data.vertices:
        if v.co.z < 0:
            k = min(1.0, -v.co.z / r)
            v.co.x *= 1.0 - 0.30 * k * k
            v.co.y *= 1.0 - 0.16 * k * k
            v.co.z *= 1.0 + 0.16 * k
    P.append(t)

    # --- Yeux : sclere + iris + pupille + 2 reflets. Sans pupille le regard
    # est mort (defaut v1). Les reflets sont la signature de l'anime.
    y = -0.395 * hd
    ec = 0.185 * hd
    z = -0.01 * hd
    if f["forme_visage"] == "ovale":
        r_o, sc_o, incl = 0.122 * hd, (1.00, 0.42, 1.18), 7.0
    else:
        r_o, sc_o, incl = 0.133 * hd, (1.00, 0.42, 1.06), 3.0

    for s in (-1, 1):
        b = c + Vector((s * ec, y, z))
        rz = math.radians(-s * incl)
        P.append(sphere("%s_SCLERE%d" % (nom, s), r_o, b, blanc,
                        scale=sc_o, rot=(0, 0, rz)))
        P.append(sphere("%s_IRIS%d" % (nom, s), r_o * 0.66,
                        b + Vector((0, -0.030 * hd, -0.012 * hd)), iris,
                        scale=(1.0, 0.46, 1.06), rot=(0, 0, rz)))
        P.append(sphere("%s_PUPILLE%d" % (nom, s), r_o * 0.34,
                        b + Vector((0, -0.047 * hd, -0.012 * hd)), pup,
                        scale=(1.0, 0.42, 1.08)))
        P.append(sphere("%s_REFL_A%d" % (nom, s), r_o * 0.21,
                        b + Vector((s * 0.040 * hd, -0.056 * hd, 0.043 * hd)),
                        refl, scale=(1.0, 0.35, 1.0)))
        P.append(sphere("%s_REFL_B%d" % (nom, s), r_o * 0.10,
                        b + Vector((-s * 0.038 * hd, -0.052 * hd, -0.040 * hd)),
                        refl, scale=(1.0, 0.35, 1.0)))
        # Paupiere superieure : un SEUL trait sombre au-dessus de l'oeil.
        # Le sourcil separe faisait double barre en v5 ; la paupiere joue les
        # deux roles, posee juste au bord haut de la sclere.
        P.append(sphere("%s_PAUPIERE%d" % (nom, s), r_o * 1.00,
                        b + Vector((0, -0.020 * hd, 0.100 * hd)), chev,
                        scale=(1.04, 0.42, 0.20), rot=(0, 0, rz)))

    P.append(sphere("%s_NEZ" % nom, 0.050 * hd,
                    c + Vector((0, y * 1.03, -0.135 * hd)), peau,
                    scale=(0.85, 0.80, 0.62)))

    # Bouche : absente en v1. Petite, peu saturee, legerement courbee.
    P.append(sphere("%s_BOUCHE" % nom, 0.070 * hd,
                    c + Vector((0, y * 1.00, -0.285 * hd)), bou,
                    scale=(0.95, 0.16, 0.20)))

    for s in (-1, 1):
        P.append(sphere("%s_OREILLE%d" % (nom, s), 0.100 * hd,
                        c + Vector((s * r * 0.95, 0.015 * hd, -0.035 * hd)),
                        peau, scale=(0.40, 0.82, 1.00)))

    # --- Chevelure ---
    if f["coiffure"] == "nattes":
        P.append(sphere("%s_CHEV_CAL" % nom, r * 1.08,
                        c + Vector((0, 0.055 * hd, 0.115 * hd)), chev,
                        scale=(sc[0], sc[1] * 0.96, sc[2] * 0.90)))
        # Frange : arc de meches posees HAUT sur le front, qui degage les yeux.
        # En v2 elle descendait jusqu'aux sourcils et formait un casque opaque.
        for k in range(7):
            u = (k - 3) / 3.0
            P.append(sphere("%s_FRANGE%d" % (nom, k), 0.105 * hd,
                            c + Vector((u * 0.33 * hd,
                                        -0.30 * hd + abs(u) * 0.07 * hd,
                                        0.395 * hd - abs(u) * 0.040 * hd)),
                            chev, scale=(0.70, 0.52, 0.68),
                            rot=(0, math.radians(u * 16), 0)))
        # Nattes : chaine CONTINUE (comme le corps), pas des spheres separees.
        # En v3 chaque segment etait une sphere isolee : elles se chevauchaient
        # et formaient deux moignons au lieu d'une tresse qui descend.
        perles = mat_cel("PERLES_%s" % nom, f["perles"])
        for s in (-1, 1):
            anc = c + Vector((s * r * 0.58, r * 0.72, -0.05 * hd))
            n = 9
            pts = []
            for k in range(n):
                u = k / float(n - 1)
                # Courbe : part de l'arriere du crane, longe la nuque, descend
                p = anc + Vector((s * (0.02 + 0.16 * u) * hd,
                                  (0.10 + 0.26 * u - 0.30 * u * u) * hd,
                                  -(0.10 + 2.30 * u) * hd))
                pts.append((p, 0.075 * hd * (1.0 - 0.52 * u)))
            P.append(mesh_chaines("%s_NATTE%d" % (nom, s), [pts], chev))
            P.append(sphere("%s_PERLE%d" % (nom, s), 0.042 * hd,
                            pts[-1][0] + Vector((0, 0, -0.10 * hd)), perles))
    else:
        P.append(sphere("%s_CHEV_CAL" % nom, r * 1.10,
                        c + Vector((0, 0.03 * hd, 0.09 * hd)), chev,
                        scale=(sc[0], sc[1], sc[2] * 0.90)))
        import random
        rnd = random.Random(7)
        for k in range(14):
            a = 2 * math.pi * k / 14.0
            rr = r * (0.70 + 0.10 * rnd.random())
            P.append(sphere("%s_BOUCLE%d" % (nom, k), 0.135 * hd,
                            c + Vector((math.cos(a) * rr,
                                        math.sin(a) * rr * 0.86 + 0.04 * hd,
                                        (0.26 + rnd.uniform(-0.04, 0.10)) * hd)),
                            chev, scale=(1.0, 1.0, 0.76)))
    return P


def vetements(nom, f, S):
    """Vetements construits sur les MEMES articulations que le corps.

    Chaque point reprend la position exacte du corps et son rayon x MARGE :
    un trou devient geometriquement impossible. En v2 les chaines passaient par
    des points intermediaires (0.55 du chemin) qui ne tombaient pas sur le
    genou -> le tissu passait sous la peau et on voyait la jambe au travers.
    """
    T = S["T"]
    R = rayons(f, S)
    haut = mat_cel("HAUT_%s" % nom, f["haut"])
    bas = mat_cel("BAS_%s" % nom, f["bas"])
    chm = mat_cel("CHAUSS_%s" % nom, f["chaussures"])
    P = []
    MARGE = 1.16

    # --- Haut : torse + manches courtes qui suivent le bras ---
    # L'ourlet s'arrete AU-DESSUS des cuisses, a mi-chemin bassin-taille, et
    # garde le rayon du tronc : un t-shirt tombe le long du corps, il n'enveloppe
    # pas les hanches. En v10, pour eviter le contact avec les cuisses, l'ourlet
    # avait ete elargi a leur diametre -> il ballonnait en bourrelet.
    # Ici c'est la HAUTEUR qui evite les cuisses, pas la largeur.
    JEU = 0.012             # 12 mm de jeu franc, en absolu (pas en %)
    z_ourlet = S["bassin"] + (S["taille"] - S["bassin"]) * 0.42
    r_ourlet = R["bassin"] * MARGE * 1.04
    ch = [[
        (z_ourlet, r_ourlet),
        (z_ourlet + Vector((0, 0, 0.030 * T)), r_ourlet),
        (S["taille"], R["taille"] * MARGE),
        (S["poitrine"], R["poitrine"] * MARGE),
        (S["haut_torse"], R["poitrine"] * MARGE * 0.94),
        (S["cou"] - Vector((0, 0, 0.012 * T)), R["cou"] * 1.12),
    ]]
    for s in (-1, 1):
        e, co = S["epaule"](s), S["coude"](s)
        # La manche part de haut_torse (vertex partage avec le tronc) et va
        # DIRECTEMENT a l'epaule. Le point intermediaire a 55 % cree par la v11
        # donnait une arete de 14,8 mm portant un rayon de 127 mm : le Skin
        # explosait en eclats de tissu sur le deltoide (emmanchure dechiree).
        # Regle generale : jamais de rayon superieur a la longueur de l'arete.
        ch.append([
            (S["haut_torse"], R["poitrine"] * MARGE * 0.94),
            (e, R["epaule"] * MARGE),
            (e + (co - e) * 0.52, R["bras"] * MARGE * 1.10),
        ])
    P.append(mesh_chaines("%s_HAUT" % nom, ch, haut))

    # --- Bas : sa ceinture monte au-dessus de l'ourlet du t-shirt et reste
    # plus etroite que lui, de sorte que l'ourlet la recouvre sans la toucher.
    r_ceinture = r_ourlet - JEU
    z_ceinture = z_ourlet + Vector((0, 0, 0.045 * T))
    ch = [[(z_ceinture, r_ceinture),
           (S["bassin"], r_ceinture)]]
    for s in (-1, 1):
        h, g, cv = S["hanche"](s), S["genou"](s), S["cheville"](s)
        if f["bas_long"]:
            jambe = [(h, R["cuisse"] * MARGE),
                     (g, R["genou"] * MARGE),
                     (cv + Vector((0, 0, 0.010 * T)), R["mollet"] * MARGE)]
        else:
            # Short : s'arrete au-dessus du genou, ourlet franc
            mi = h + (g - h) * 0.72
            jambe = [(h, R["cuisse"] * MARGE),
                     (mi, R["cuisse"] * MARGE * 0.92)]
        ch.append([(S["bassin"], r_ceinture)] + jambe)
    P.append(mesh_chaines("%s_BAS" % nom, ch, bas))

    # --- Chaussures : enveloppent cheville et pied du corps ---
    for s in (-1, 1):
        cv, pd = S["cheville"](s), S["pied"](s)
        P.append(mesh_chaines("%s_CHAUSS%d" % (nom, s), [[
            (cv, R["mollet"] * MARGE * 1.04),
            (pd, R["pied"] * MARGE * 1.02),
        ]], chm))

    if f.get("bracelet"):
        br = mat_cel("BRACELET_%s" % nom, f["bracelet"])
        P.append(sphere("%s_BRACELET" % nom, R["avbras"] * 1.45,
                        S["poignet"](-1), br, scale=(1.0, 1.0, 0.26)))
    if f.get("sac"):
        # Le sac est porte DANS LE DOS (+Y), pas sur la hanche : a la hanche il
        # occupait la place du bras et la main le traversait (defaut v11).
        sm = mat_cel("SAC_%s" % nom, f["sac"])
        p = Vector((R["bassin"] * 0.42, 0.105 * T, S["z_hanche"] + 0.095 * T))
        P.append(sphere("%s_SAC" % nom, 0.058 * T, p, sm,
                        scale=(0.78, 0.40, 0.92)))
        P.append(mesh_chaines("%s_SANGLE" % nom, [[
            (Vector((-0.045 * T, -0.010 * T, S["z_epaule"] + 0.008 * T)),
             0.008 * T),
            (Vector((0.010 * T, 0.045 * T, S["z_epaule"] - 0.030 * T)),
             0.008 * T),
            (p + Vector((0, -0.010 * T, 0.045 * T)), 0.008 * T),
        ]], sm))
    return P


def armature(nom, f, S):
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    a = bpy.context.active_object
    a.name = "%s_RIG" % nom
    a.data.name = "%s_ARM" % nom
    eb = a.data.edit_bones
    for b in list(eb):
        eb.remove(b)

    def os_(n, h, t, par=None, con=False):
        b = eb.new(n)
        b.head, b.tail = h, t
        if par:
            b.parent = eb[par]
            b.use_connect = con
        return b

    os_("racine", Vector((0, 0, 0)), Vector((0, -0.14, 0)))
    os_("bassin", S["bassin"], S["taille"], "racine")
    os_("colonne", S["taille"], S["poitrine"], "bassin", True)
    os_("poitrine", S["poitrine"], S["cou"], "colonne", True)
    os_("cou", S["cou"], S["tete_bas"], "poitrine", True)
    os_("tete", S["tete_bas"], Vector((0, 0, S["T"])), "cou", True)

    for s, k in ((-1, "G"), (1, "D")):
        os_("epaule_%s" % k, S["poitrine"], S["epaule"](s), "poitrine")
        os_("bras_%s" % k, S["epaule"](s), S["coude"](s), "epaule_%s" % k, True)
        os_("avbras_%s" % k, S["coude"](s), S["poignet"](s), "bras_%s" % k, True)
        os_("main_%s" % k, S["poignet"](s), S["main"](s), "avbras_%s" % k, True)
        os_("ik_main_%s" % k, S["poignet"](s),
            S["poignet"](s) + Vector((0, 0, -0.10)), "racine")
        os_("cuisse_%s" % k, S["hanche"](s), S["genou"](s), "bassin")
        os_("tibia_%s" % k, S["genou"](s), S["cheville"](s), "cuisse_%s" % k, True)
        os_("pied_%s" % k, S["cheville"](s), S["pied"](s), "tibia_%s" % k, True)
        os_("ik_pied_%s" % k, S["cheville"](s),
            S["cheville"](s) + Vector((0, -0.10, 0)), "racine")

    bpy.ops.object.mode_set(mode="POSE")

    # Un os de CIBLE IK ne doit jamais deformer le maillage. Il reste a sa
    # place pendant que le membre bouge : tout sommet pese sur lui est tire
    # entre deux ancrages. Mesure (v8) : les mains d'Awa s'etiraient sur
    # 64 cm de haut et celles de Tano sur 89 cm -- c'etaient elles, les
    # "plaques noires" que j'ai d'abord prises pour les nattes puis pour un
    # depassement d'articulation.
    for b in a.data.bones:
        if b.name.startswith("ik_"):
            b.use_deform = False

    for k in ("G", "D"):
        for b, t in (("avbras_%s" % k, "ik_main_%s" % k),
                     ("tibia_%s" % k, "ik_pied_%s" % k)):
            ct = a.pose.bones[b].constraints.new("IK")
            ct.target, ct.subtarget, ct.chain_count = a, t, 2
            ct.influence = 0.0        # IK disponible, desactive par defaut
    bpy.ops.object.mode_set(mode="OBJECT")
    return a


def hauteur_reelle(pieces):
    """Hauteur du personnage mesuree sur la geometrie, en metres."""
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in pieces for c in o.bound_box]
    return max(zs) - min(zs)


def canon_mesure(nom, pieces):
    """Canon reel en tetes : hauteur totale / hauteur de tete COIFFEE.

    Mesurer sur le crane nu (%s_TETE) sous-estime la tete, car la calotte et
    la frange depassent : on lisait 4.46 pour un canon vise a 5.20. On prend
    donc l'englobant de la tete et de tout ce qui la couvre.
    """
    cles = ("_TETE", "_CHEV_CAL", "_FRANGE", "_BOUCLE", "_OREILLE")
    zs = []
    for o in pieces:
        if any(k in o.name for k in cles):
            zs += [(o.matrix_world @ Vector(c)).z for c in o.bound_box]
    if not zs:
        return None, None
    ht = max(zs) - min(zs)
    h = hauteur_reelle(pieces)
    return ht, (h / ht if ht > 1e-9 else None)


def construire_personnage(nom, position=(0, 0, 0)):
    f = FICHES[nom]
    S = squelette(f)
    col = bpy.data.collections.new(nom)
    bpy.context.scene.collection.children.link(col)
    prev = bpy.context.view_layer.active_layer_collection
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children[nom]

    P = corps(nom, f, S) + tete(nom, f, S) + vetements(nom, f, S)
    for p in P:
        contour(p, 0.0026 * S["T"])

    arm = armature(nom, f, S)
    bpy.ops.object.select_all(action="DESELECT")
    for o in P:
        o.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    # ARMATURE_AUTO pese par PROXIMITE geometrique, pas par appartenance.
    # Mesure (v8) : les nattes d'Awa, qui descendent dans le dos jusqu'au bas
    # des reins, se retrouvaient pesees sur cuisse_D/cuisse_G (poids 4,0) et
    # epaule_D/epaule_G (3,0) -- aucun poids sur `tete`. Des qu'elle levait ou
    # tendait les bras, ses nattes partaient avec et s'etiraient en longues
    # plaques noires en travers du torse.
    #
    # Une piece rigide solidaire d'une partie du corps doit etre pesee sur
    # l'os de cette partie, pas sur l'os le plus proche. On corrige donc
    # explicitement apres coup.
    RATTACHEMENT = (
        ("NATTE", "tete"), ("PERLE", "tete"), ("CHEV", "tete"),
        ("FRANGE", "tete"), ("BOUCLE", "tete"),
        ("SAC", "colonne"), ("SANGLE", "colonne"),
        # Toute la face suit la tete. Mesure (v32) : le nez gardait 80 de
        # poids sur `cou` et le Skin l'etirait de 43 a 188 mm des que le cou
        # pivotait. Une piece rigide sur une articulation est une bombe a
        # retardement.
        ("NEZ", "tete"), ("OEIL", "tete"), ("IRIS", "tete"),
        ("PUPILLE", "tete"), ("SCLERE", "tete"), ("REFL", "tete"),
        ("PAUPIERE", "tete"), ("BOUCHE", "tete"), ("OREILLE", "tete"),
    )
    # Pieces rigides de membre : le bracelet suit le main, cote oppose au
    # bras de pose (mesure v33 : main_G=184,7 / avbras_G=129,3 au repos, et
    # la Skin l'etirait de 9,8 a 19,3 mm des que le poignet bougeait). Il est
    # pose APRES la repesee par axe des membres, sinon celle-ci lui remet un
    # poids partage avec l'avant-bras.
    RATTACHEMENT_MEMBRES = (("BRACELET", "main_G"),)
    for o in P:
        cible = None
        for motif, os_nom in RATTACHEMENT:
            if motif in o.name.upper():
                cible = os_nom
                break
        if cible is None or cible not in arm.data.bones:
            continue
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
        vg = o.vertex_groups.new(name=cible)
        vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")
        REPESEES.append("%s -> %s" % (o.name, cible))

    # Repeser les membres par PROJECTION sur l'axe de l'os.
    #
    # ARMATURE_AUTO attribue chaque sommet a l'os le plus PROCHE, ce qui est
    # faux pour un membre : un sommet du torse proche de l'epaule prend
    # `bras_*` et part avec le bras. Mesure (v31) sur Tano au repos :
    # 72 sommets de Tano_CORPS et de Tano_HAUT etaient peses sur `bras_D` avec
    # une altitude de 0,96 a 1,11 m, alors que l'os `bras_D` va de 0,75 a
    # 0,90 m -- ils etaient 20 cm trop haut. Le buste entier suivait le bras,
    # ce qui donnaient des membres segmentes, disjoints, des mains spheres
    # detachees et une chair deformee de 39 % (cotes d'aretes). L'image
    #montrait des bras en "<bats jointes", pas un probleme de pose.
    #
    # On repart de zero et on attribue chaque sommet a l'os de membre dont il
    # est le plus proche SUR LA CHAINE, avec une transition douce aux
    # articulations : deux os voisins se partagent le sommet au prorata des
    # distances, comme le fait n'importequelle ponderation correcte.
    MEMBRES = ("epaule_", "bras_", "avbras_", "main_", "cuisse_", "tibia_",
               "pied_")
    for o in P:
        if o.type != "MESH":
            continue
        noms_obj = o.name.upper()
        # Les pieces rigides de tete et de dos ont deja ete pesees ci-dessus.
        if any(m in noms_obj for m in ("NATTE", "PERLE", "CHEV", "FRANGE",
                                      "BOUCLE", "SAC", "SANGLE", "TETE")):
            continue
        # Toute piece de la face suit la TETE, jamais le cou. Mesure (v32) :
        # apres la repesee par axe ci-dessous, le nez gardait 80 de poids sur
        # `cou` et 230 sur `tete` ; le Skin l'etire alors de 43 a 188 mm
        # (+4,3) des que le cou pivote -- piece rigide sur une articulation.
        if any(m in noms_obj for m in ("NEZ", "OEIL", "IRIS", "PUPILLE",
                                       "SCLERE", "REFL", "PAUPIERE",
                                       "BOUCHE", "OREILLE", "BRACELET")):
            continue
        # Chaine des os du membre, dans l'ordre
        chaine = []
        for cote in ("_D", "_G"):
            for tronc in ("epaule", "bras", "avbras", "main", "cuisse",
                          "tibia", "pied"):
                nom_os = tronc + cote
                if nom_os in arm.data.bones:
                    chaine.append(nom_os)
        segments = []
        for nom_os in chaine:
            pb = arm.pose.bones[nom_os]
            segments.append((nom_os, pb.head.copy(), pb.tail.copy()))
        if not segments:
            continue
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
        groupes = dict((nom_os, o.vertex_groups.new(name=nom_os))
                       for nom_os, _, _ in segments)
        lg = [groupes[n] for n, _, _ in segments]
        n_rep = 0
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            poids = []
            for nom_os, h, t in segments:
                # distance du sommet au segment [h, t]
                ab = t - h
                L2 = ab.length_squared
                u = 0.0 if L2 < 1e-12 else max(0.0, min(1.0,
                      (p - h).dot(ab) / L2))
                poids.append((p - (h + ab * u)).length)
            # Les deux os les plus proches partagent le sommet
            ordre = sorted(range(len(poids)), key=lambda i: poids[i])
            i1, i2 = ordre[0], ordre[1]
            d1, d2 = poids[i1], poids[i2]
            # au-dela de la demi-longueur de l'os, on ne melange plus
            demi = (segments[i1][2] - segments[i1][1]).length * 0.5
            if d2 > demi or d2 < 1e-9:
                lg[i1].add([v.index], 1.0, "REPLACE")
            else:
                total = d1 + d2
                lg[i1].add([v.index], d2 / total, "REPLACE")
                lg[i2].add([v.index], d1 / total, "REPLACE")
                n_rep += 1
        MEMBRES_REPESES.append("%s : %d sommets partages" % (o.name, n_rep))

    # Pieces rigides de membre : accessoires ponctuels poses APRES la repesee par
    # axe, sinon celle-ci leur remet un poids partage avec l'os voisin.
    #
    # Le suffixe porte le cote : `_1` pour la droite, `-1` pour la gauche
    # (verifie : Awa_MAIN1 pese sur `main_D`, Awa_MAIN-1 sur `main_G`).
    # Mesure (v36) : le pouce gardait 39 points de poids sur `cuisse_D` --
    # residu de l'attribution automatique que la repesee par axe n'a pas
    # nettoye, le pouce n'etant pas sur la chaine des os de membre.
    def os_cible(nom_obj):
        n = nom_obj.upper()
        cote = "_G" if n.endswith("-1") else "_D"
        for motif in ("POUCE", "MAIN", "ONGL", "PAUME"):
            if motif in n:
                return "main" + cote
        for motif, os_nom in RATTACHEMENT_MEMBRES:
            if motif in n:
                return os_nom
        return None

    for o in P:
        os_nom = os_cible(o.name)
        if os_nom is None or os_nom not in arm.data.bones:
            continue
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
        o.vertex_groups.new(name=os_nom).add(
            range(len(o.data.vertices)), 1.0, "REPLACE")
        REPESEES.append("%s -> %s (apres axe)" % (o.name, os_nom))

    # CONTROLE : aucune piece rigide ne doit etre posee sur une articulation.
    #
    # Le meme defaut a ete decouvert trois fois, sur trois articulations
    # differentes : les nattes sur les cuisses (v8), le nez sur le cou (v32,
    # Skin l'etrait de 43 a 188 mm) et le bracelet entre main et avant-bras
    # (v33, +97 %). Le principe est unique et se verifie une fois pour toutes.
    #
    # On ne verifie QUE les pieces rigides -- celles listees dans RATTACHEMENT,
    # attachees volontairement a un seul os. Une ligature qui suit deux os est
    # normale et ne doit pas etre signalee ; c'est ce qui a rendu le premier
    # essai de ce controle inutilisable.
    ALERTES_PIECES = []
    for o in P:
        if o.type != "MESH" or not o.vertex_groups:
            continue
        attendu = None
        # Un objet peut correspondre a plusieurs motifs : on ne retient que
        # les os CIBLES qui sont reellement presents dans ses groupes, et on
        # exige qu'il n'en reste qu'un. (v34 : Awa_BRACELET portait encore
        # avbras_G en plus de main_G ; le controle s'arretait sur le premier
        # motif trouve et signalait un objet deja repare.)
        noms_obj = o.name.upper()
        presents = [os_nom for motif, os_nom in RATTACHEMENT
                    + RATTACHEMENT_MEMBRES if motif in noms_obj]
        if not presents:
            continue
        groupes_reels = set(g.name for g in o.vertex_groups)
        attendus = [c for c in presents if c in groupes_reels]
        if len(attendus) == 1:
            attendu = attendus[0]
        elif not attendus and len(groupes_reels) == 1:
            # aucun motif n'a ete pose (objet oublie dans la table) mais
            # l'objet ne pese que sur un os : on accepte et on le signale
            attendu = next(iter(groupes_reels))
        if attendu is None:
            continue
        lg = dict((g.index, g.name) for g in o.vertex_groups)
        poids = {}
        for v in o.data.vertices:
            for g in v.groups:
                n = lg[g.group]
                poids[n] = poids.get(n, 0.0) + g.weight
        presents = sorted(poids)
        if len(presents) != 1 or presents[0] != attendu:
            ALERTES_PIECES.append(
                "%s : attendu %s seul, trouve %s"
                % (o.name, attendu, ", ".join(presents) or "aucun os"))

    if ALERTES_PIECES:
        for a in ALERTES_PIECES[:10]:
            print("   !! %s" % a)
        print("   %d piece(s) rigide(s) mal attachee(s)" % len(ALERTES_PIECES))
        sys.exit(3)

    # Ordre des modificateurs : le contour (coque inversee) doit etre calcule
    # SUR LA POSE, donc APRES l'armature. parent_set() ajoute ARMATURE en fin
    # de pile, derriere le SOLIDIFY pose a la construction -- le contour etait
    # donc fige au repos puis deforme avec le maillage. Mesure (v9) : 82
    # objets dans ce cas ; des qu'un membre pliait fort, la coque inversee
    # traversait la surface et apparaissait en plaques noires le long du
    # torse et des bras.
    for o in P:
        noms = [m.type for m in o.modifiers]
        if "SOLIDIFY" not in noms or "ARMATURE" not in noms:
            continue
        if noms.index("SOLIDIFY") > noms.index("ARMATURE"):
            continue
        sol = [m for m in o.modifiers if m.type == "SOLIDIFY"][0]
        with bpy.context.temp_override(object=o):
            bpy.ops.object.modifier_move_to_index(
                modifier=sol.name, index=len(o.modifiers) - 1)
        REORDONNES.append(o.name)

    # Normalisation : le canon en tetes donne la silhouette, pas la taille
    # exacte (crane et chevelure depassent le dernier point articulaire).
    # On mesure la geometrie et on corrige a l'echelle -> champ C au mm.
    h = hauteur_reelle(P)
    if h > 1e-6:
        k = f["taille"] / h
        arm.scale = (k, k, k)
        bpy.context.view_layer.update()

    # Les pieces sont parentees a l'armature : deplacer l'armature suffit.
    # Toucher piece.location ecraserait la position des spheres (tete, yeux,
    # cheveux), qui portent leur position dans location (bug v1).
    arm.location = Vector(position)
    bpy.context.view_layer.update()

    arm["cvr01_perso"] = nom
    arm["cvr01_taille"] = f["taille"]
    bpy.context.view_layer.active_layer_collection = prev
    return arm, P


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.eevee.taa_render_samples = 16

    awa, pa = construire_personnage("Awa", (-0.42, 0, 0))
    tano, pt = construire_personnage("Tano", (0.42, 0, 0))

    print("\n" + "=" * 70)
    print("CVR01 - personnages v2")
    print("=" * 70)
    for n, a, P in (("Awa", awa, pa), ("Tano", tano, pt)):
        f = FICHES[n]
        h = hauteur_reelle(P)
        ht, canon = canon_mesure(n, P)
        print("%-6s taille %.3f m (vise %.3f, ecart %+.1f mm)"
              % (n, h, f["taille"], (h - f["taille"]) * 1000))
        print("       tete coiffee %.3f m -> canon %.2f tetes (vise %.2f)"
              % (ht, canon, f["tetes"]))
        print("       maillages %2d   os %2d" % (len(P), len(a.data.bones)))

    out = os.path.join(HERE, "cvr01_persos.blend")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print("-" * 70)
    # Bilan des pieges Skin : un rayon superieur a la longueur de son arete
    # produit une boule qui avale le membre. Ce diagnostic a coute trois
    # versions (bras disparus en v12-v13, emmanchure dechiree en v14) ; il est
    # desormais affiche A LA CONSTRUCTION, avant tout rendu.
    if ALERTES:
        print("ALERTES SKIN : %d arete(s) a rayon surdimensionne" % len(ALERTES))
        for a in ALERTES:
            print("  !! %s" % a)
    else:
        print("alertes skin : aucune")
    print("enregistre : %s" % os.path.abspath(out))


if __name__ == "__main__":
    # Un plantage ne doit jamais ressembler a un succes : Blender quitte avec
    # le code 0 meme si le script leve une exception (v31 : un NameError sur
    # une variable mal orthographiee a laisse BUILD=0 dans la sortie).
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
