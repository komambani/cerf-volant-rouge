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

    return dict(
        hd=hd, T=T,
        bassin=Vector((0, 0, z_hanche)),
        taille=Vector((0, 0, z_taille)),
        poitrine=Vector((0, 0, z_poitrine)),
        cou=Vector((0, 0, z_cou)),
        tete_bas=Vector((0, 0, z_menton)),
        tete_centre=Vector((0, -0.004 * T, z_menton + 0.46 * hd)),
        epaule=lambda s: Vector((s * lx_ep, 0, z_epaule)),
        coude=lambda s: Vector((s * lx_ep * 1.20, 0.008 * T, z_coude)),
        poignet=lambda s: Vector((s * lx_ep * 1.32, 0.018 * T, z_poignet)),
        main=lambda s: Vector((s * lx_ep * 1.36, 0.022 * T, z_poignet - 0.052 * T)),
        hanche=lambda s: Vector((s * lx_ha, 0, z_hanche)),
        genou=lambda s: Vector((s * lx_ha * 0.94, -0.006 * T, z_genou)),
        cheville=lambda s: Vector((s * lx_ha * 0.90, 0, z_cheville)),
        pied=lambda s: Vector((s * lx_ha * 0.90, -0.052 * T, z_cheville * 0.55)),
        z_epaule=z_epaule, z_hanche=z_hanche, z_cheville=z_cheville,
        z_poignet=z_poignet,
    )


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
    return dict(
        cou=0.040 * T,
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

    ch = [[
        (S["bassin"], R["bassin"]), (S["taille"], R["taille"]),
        (S["poitrine"], R["poitrine"]), (S["cou"], R["cou"]),
        (S["tete_bas"], R["cou"] * 1.02),
    ]]
    for s in (-1, 1):
        ch.append([
            (S["poitrine"], R["poitrine"]), (S["epaule"](s), R["epaule"]),
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
    # Le t-shirt recouvre la ceinture du pantalon sur TOUTE la zone commune, a
    # rayon constant. Mesure v7 : en laissant l'ourlet se retrecir vers le haut
    # pendant que la ceinture s'elargissait, le sens de recouvrement s'inversait
    # en cours de jonction (+34 mm puis -46 mm) et les surfaces se croisaient.
    # Ici l'ourlet reste large jusqu'au-dessus de la ceinture : un seul sens.
    #
    # Le rayon de l'ourlet est derive de la piece la plus large qu'il doit
    # couvrir : non pas la ceinture, mais les CUISSES du bas, qui s'ecartent
    # lateralement a la hanche. Mesure v9 : chez Tano l'ourlet (0,1702) et la
    # cuisse (0,1703) se touchaient a 0,1 mm, alors que la ceinture, elle,
    # avait bien ses 12 mm de jeu. Le point de contact n'etait pas celui que
    # je corrigeais.
    JEU = 0.012             # 12 mm de jeu franc, en absolu (pas en %)
    demi_ecart_hanches = abs(S["hanche"](1).x)
    r_bas_max = demi_ecart_hanches + R["cuisse"] * MARGE
    r_ourlet = r_bas_max + JEU
    z_haut_ceinture = S["bassin"] + (S["taille"] - S["bassin"]) * 0.55
    ch = [[
        (S["bassin"] - Vector((0, 0, 0.030 * T)), r_ourlet),
        (z_haut_ceinture + Vector((0, 0, 0.020 * T)), r_ourlet),
        (S["taille"], R["taille"] * MARGE),
        (S["poitrine"], R["poitrine"] * MARGE),
        (S["cou"] - Vector((0, 0, 0.020 * T)), R["cou"] * 1.35),
    ]]
    for s in (-1, 1):
        e, co = S["epaule"](s), S["coude"](s)
        # La manche s'arrete a mi-bras et suit le bras : pas de poncho.
        ch.append([
            (S["poitrine"], R["poitrine"] * MARGE),
            (e, R["epaule"] * MARGE),
            (e + (co - e) * 0.50, R["bras"] * MARGE * 1.12),
        ])
    P.append(mesh_chaines("%s_HAUT" % nom, ch, haut))

    # --- Bas : reste SOUS le t-shirt sur toute la zone commune. Son rayon est
    # fixe par celui de l'ourlet moins le jeu, defini plus haut.
    r_ceinture = r_ourlet - JEU
    ch = [[(z_haut_ceinture, r_ceinture),
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
        sm = mat_cel("SAC_%s" % nom, f["sac"])
        p = Vector((R["bassin"] * 1.15, 0.030 * T, S["z_hanche"] + 0.030 * T))
        P.append(sphere("%s_SAC" % nom, 0.058 * T, p, sm,
                        scale=(0.70, 0.44, 0.84)))
        P.append(mesh_chaines("%s_SANGLE" % nom, [[
            (Vector((-0.040 * T, 0.015 * T, S["z_epaule"] + 0.010 * T)),
             0.008 * T),
            (p + Vector((0, 0, 0.040 * T)), 0.008 * T),
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
    print("enregistre : %s" % os.path.abspath(out))


if __name__ == "__main__":
    main()
