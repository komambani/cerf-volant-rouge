# -*- coding: utf-8 -*-
"""CVR01 - construction de la scene Blender depuis le modele de donnees.

Genere LOC_MANGUIER (decor), la lumiere du champ G, et les 15 cameras avec
leurs trajectoires chiffrees exactes issues du champ E de chaque fiche.

    blender -b -P blender/build_scene.py -- --out blender/cvr01_scene.blend

Repere : Blender Z-up, 1 unite = 1 metre. Origine du monde = pied du manguier.
La camera regarde vers -Y a l'azimut 0 (axe 0 degre du document).
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

# --------------------------------------------------------------------------
# Palette : hex du document -> lineaire Blender
# --------------------------------------------------------------------------
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h, alpha=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


PAL = dict(
    sol="#A8573C",          # sol compact rouge-brun
    mur="#C98A4B",          # mur bas en terre ocre
    maison="#3C7BA8",       # petite maison bleue
    maison_toit="#8A5538",
    tronc="#6B4A33",
    feuillage_1="#2F6B3A",  # anime : deux aplats, pas de degrade
    feuillage_2="#3E8A49",
    banc=M.OBJETS["OBJ_BENCH"]["fr"].split("#")[1][:6],
    tabouret="70472F",
    kite="D83A32",
    kite_bord="F0C94A",
    kite_queue="2E7EDB",
    devidoir="B87942",
    ciel="#F28C6B",         # couleur cle 1 du champ H
)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat_cel(nom, hex_couleur, specular=0.0):
    """Materiau cel-shading : aplat pur, aucune reflexion speculaire.
    Emission pilotee par la lumiere via diffuse uniquement -> look anime."""
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
    bsdf.inputs["Color"].default_value = hexcol(hex_couleur)
    bsdf.inputs["Roughness"].default_value = 1.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = hexcol(hex_couleur)
    return m


def add_mesh(nom, verts, faces, mat):
    me = bpy.data.meshes.new(nom)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(nom, me)
    ob.data.materials.append(mat)
    bpy.context.collection.objects.link(ob)
    return ob


def add_box(nom, size, loc, mat, rot=(0, 0, 0)):
    """size = dimensions reelles en metres (largeur, profondeur, hauteur)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = nom
    # primitive_cube_add(size=1) fait 1 m de cote : l'echelle est la dimension
    # voulue, pas sa moitie (bug corrige : le decor sortait a 50 %).
    ob.scale = (size[0], size[1], size[2])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    return ob


def add_cyl(nom, r, h, loc, mat, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h,
                                        location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = nom
    ob.data.materials.append(mat)
    return ob


def add_sphere(nom, r, loc, mat, scale=(1, 1, 1), segs=16):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=loc)
    ob = bpy.context.active_object
    ob.name = nom
    ob.scale = scale
    ob.data.materials.append(mat)
    # Flat shading : indispensable au cel-shading
    for poly in ob.data.polygons:
        poly.use_smooth = False
    return ob


# --------------------------------------------------------------------------
# DECOR : LOC_MANGUIER
# --------------------------------------------------------------------------
def build_decor():
    col = bpy.data.collections.new("DECOR")
    bpy.context.scene.collection.children.link(col)
    prev = bpy.context.view_layer.active_layer_collection
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children["DECOR"]

    m_sol = mat_cel("MAT_SOL", PAL["sol"])
    m_mur = mat_cel("MAT_MUR", PAL["mur"])
    m_maison = mat_cel("MAT_MAISON", PAL["maison"])
    m_toit = mat_cel("MAT_TOIT", PAL["maison_toit"])
    m_tronc = mat_cel("MAT_TRONC", PAL["tronc"])
    m_feuille1 = mat_cel("MAT_FEUILLAGE_A", PAL["feuillage_1"])
    m_feuille2 = mat_cel("MAT_FEUILLAGE_B", PAL["feuillage_2"])
    m_banc = mat_cel("MAT_BANC", "#8A6240")

    # Sol : 40 x 40 m, origine au pied de l'arbre
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    sol = bpy.context.active_object
    sol.name = "SOL"
    sol.data.materials.append(m_sol)

    # Mur bas en terre ocre, au fond (Y positif = loin de la camera)
    add_box("MUR_FOND", (24, 0.35, 1.30), (0, 9.0, 0.65), m_mur)

    # Petite maison bleue a gauche
    add_box("MAISON_CORPS", (4.5, 4.0, 2.60), (-7.5, 5.0, 1.30), m_maison)
    add_box("MAISON_TOIT", (5.1, 4.6, 0.25), (-7.5, 5.0, 2.72), m_toit)

    # Manguier : tronc + branche basse a 2,25 m (OBJ_BRANCH) + canopee
    add_cyl("TRONC", 0.22, 4.2, (0, 0, 2.1), m_tronc)
    # La branche porteuse : diametre 7 cm, a 2,25 m du sol, horizontale
    br = add_cyl("OBJ_BRANCH", 0.035, 2.4, (0.9, 0.15, 2.25), m_tronc,
                 rot=(0, math.radians(90), 0))
    br["cvr01_role"] = "branche porteuse du cerf-volant"
    # Deux amorces de branches secondaires, pour la silhouette
    add_cyl("BRANCHE_SEC_A", 0.05, 1.8, (-0.8, -0.3, 2.9), m_tronc,
            rot=(0, math.radians(72), math.radians(20)))
    add_cyl("BRANCHE_SEC_B", 0.045, 1.6, (0.5, 0.7, 3.3), m_tronc,
            rot=(math.radians(-18), math.radians(68), 0))
    # Canopee : amas dense d'icospheres aplaties, lisible en aplats.
    # Trois strates pour donner du volume et des trouees de ciel.
    canopee = [
        # strate basse, large
        ((0.0, 0.0, 4.35), 2.35, m_feuille1),
        ((-1.85, 0.50, 4.05), 1.70, m_feuille2),
        ((1.80, -0.40, 4.20), 1.75, m_feuille2),
        ((0.40, 1.70, 4.25), 1.55, m_feuille1),
        ((-0.60, -1.75, 3.95), 1.50, m_feuille2),
        ((-2.30, -1.10, 4.30), 1.25, m_feuille1),
        ((2.20, 1.15, 4.10), 1.30, m_feuille1),
        # strate mediane
        ((1.05, 0.65, 5.25), 1.45, m_feuille1),
        ((-1.25, 0.85, 5.10), 1.35, m_feuille2),
        ((0.15, -1.05, 5.35), 1.30, m_feuille2),
        ((-0.35, 1.45, 5.55), 1.15, m_feuille1),
        # cime
        ((0.30, 0.10, 6.15), 1.20, m_feuille2),
        ((-0.75, -0.45, 6.30), 0.95, m_feuille1),
    ]
    for i, (loc, r, mat) in enumerate(canopee):
        ob = add_sphere("FEUILLAGE_%02d" % i, r, loc, mat, scale=(1.0, 1.0, 0.58))
        # Legere rotation : casse la repetition des facettes
        ob.rotation_euler = (math.radians(i * 23 % 40), 0, math.radians(i * 57 % 360))

    # Banc en bois sous l'arbre (OBJ_BENCH, manquait au registre V1.0)
    add_box("OBJ_BENCH_ASSISE", (1.40, 0.34, 0.05), (-2.1, 1.05, 0.42), m_banc)
    for dx in (-0.60, 0.60):
        add_box("OBJ_BENCH_PIED%+d" % (1 if dx > 0 else -1),
                (0.07, 0.30, 0.42), (-2.1 + dx, 1.05, 0.21), m_banc)

    bpy.context.view_layer.active_layer_collection = prev
    return col


# --------------------------------------------------------------------------
# PROPS : tabouret, devidoir, cerf-volant
# --------------------------------------------------------------------------
def build_props():
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection
    col = bpy.data.collections.new("PROPS")
    bpy.context.scene.collection.children.link(col)
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children["PROPS"]

    m_tab = mat_cel("MAT_TABOURET", "#70472F")
    m_kite = mat_cel("MAT_KITE", "#D83A32")
    m_bord = mat_cel("MAT_KITE_BORD", "#F0C94A")
    m_queue = mat_cel("MAT_KITE_QUEUE", "#2E7EDB")
    m_dev = mat_cel("MAT_DEVIDOIR", "#B87942")
    m_poignee = mat_cel("MAT_DEVIDOIR_POIGNEE", "#211D1A")
    m_ficelle = mat_cel("MAT_FICELLE", "#F2EDE4")

    # OBJ_STOOL : 42 cm de haut, assise 30 x 30 cm
    tab = bpy.data.collections.new("OBJ_STOOL")
    col.children.link(tab)
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children["PROPS"].children["OBJ_STOOL"]
    add_box("STOOL_ASSISE", (0.30, 0.30, 0.035), (0, 0, 0.4025), m_tab)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_box("STOOL_PIED_%d%d" % (sx, sy), (0.035, 0.035, 0.385),
                    (sx * 0.12, sy * 0.12, 0.1925), m_tab)
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children["PROPS"]

    # OBJ_KITE : triangle 55 x 75 cm, bord jaune 3 cm, queue 2,5 m / 6 rubans
    kw, kh = M.OBJETS["OBJ_KITE"]["dims_m"]
    verts = [(-kw / 2, 0, -kh / 2), (kw / 2, 0, -kh / 2), (0, 0, kh / 2)]
    kite = add_mesh("OBJ_KITE_TOILE", verts, [(0, 1, 2)], m_kite)
    sol_mod = kite.modifiers.new("Solidify", "SOLIDIFY")
    sol_mod.thickness = 0.004
    # Bord jaune : meme triangle legerement elargi, derriere la toile
    s = 1.0 + (2 * 0.03) / kh
    vb = [(v[0] * s, 0.003, v[2] * s) for v in verts]
    add_mesh("OBJ_KITE_BORD", vb, [(0, 1, 2)], m_bord)
    # Queue : 6 rubans sur 2,5 m
    for i in range(6):
        z = -kh / 2 - 0.05 - i * (2.5 / 6.0)
        add_box("KITE_RUBAN_%d" % i, (0.05, 0.004, 0.16), (0, 0, z), m_queue)
    # Regroupement
    kcol = bpy.data.collections.new("OBJ_KITE")
    col.children.link(kcol)
    for nom in ["OBJ_KITE_TOILE", "OBJ_KITE_BORD"] + \
               ["KITE_RUBAN_%d" % i for i in range(6)]:
        ob = bpy.data.objects[nom]
        for c in ob.users_collection:
            c.objects.unlink(ob)
        kcol.objects.link(ob)

    # OBJ_REEL : diametre 9 cm, poignee noire, ficelle blanche 1,5 mm
    add_cyl("REEL_CORPS", 0.045, 0.11, (0, 0, 0), m_dev,
            rot=(0, math.radians(90), 0), verts=12)
    add_cyl("REEL_POIGNEE", 0.012, 0.16, (0, 0, 0), m_poignee,
            rot=(0, math.radians(90), 0), verts=8)
    rcol = bpy.data.collections.new("OBJ_REEL")
    col.children.link(rcol)
    for nom in ("REEL_CORPS", "REEL_POIGNEE"):
        ob = bpy.data.objects[nom]
        for c in ob.users_collection:
            c.objects.unlink(ob)
        rcol.objects.link(ob)

    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection
    return col


# --------------------------------------------------------------------------
# LUMIERE : champ G, identique sur les 15 plans (RLUM)
#   soleil azimut 245 deg, elevation 12 deg, 3600 K, contraste 4:1,
#   appoint ciel 20 %, rim gauche 15 %
# --------------------------------------------------------------------------
def kelvin_to_rgb(k):
    """Approximation de Tanner Helland, suffisante pour 3600 K."""
    t = k / 100.0
    if t <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
    else:
        r = 329.698727446 * ((t - 60) ** -0.1332047592)
        g = 288.1221695283 * ((t - 60) ** -0.0755148492)
    if t >= 66:
        b = 255.0
    elif t <= 19:
        b = 0.0
    else:
        b = 138.5177312231 * math.log(t - 10) - 305.0447927307
    clamp = lambda v: max(0.0, min(255.0, v)) / 255.0
    return (srgb_to_linear(clamp(r)), srgb_to_linear(clamp(g)),
            srgb_to_linear(clamp(b)), 1.0)


def build_light():
    L = M.LUMIERE
    col = bpy.data.collections.new("LUMIERE")
    bpy.context.scene.collection.children.link(col)
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children["LUMIERE"]

    # Soleil principal. Azimut 245 deg (mesure depuis le nord, sens horaire),
    # elevation 12 deg. Converti en rotation Blender.
    az = math.radians(L["azimut"])
    el = math.radians(L["elevation"])
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 8))
    sun = bpy.context.active_object
    sun.name = "SOLEIL_PRINCIPAL"
    sun.data.energy = 4.0
    sun.data.color = kelvin_to_rgb(L["kelvin"])[:3]
    # Soleil doux : angle large, ombres non coupantes
    sun.data.angle = math.radians(2.5)
    sun.rotation_euler = (math.pi / 2 - el, 0, -az)
    sun["cvr01_azimut"] = L["azimut"]
    sun["cvr01_elevation"] = L["elevation"]
    sun["cvr01_kelvin"] = L["kelvin"]

    # Appoint ciel 20 % : lumiere d'aire large venue du zenith, teintee ciel
    bpy.ops.object.light_add(type="AREA", location=(0, 0, 12))
    fill = bpy.context.active_object
    fill.name = "APPOINT_CIEL"
    fill.data.shape = "DISK"
    fill.data.size = 24.0
    fill.data.energy = 4.0 * L["appoint_ciel"] / 100.0 * 60
    fill.data.color = hexcol(PAL["ciel"])[:3]

    # Rim gauche 15 % : contre-jour qui detache les silhouettes
    bpy.ops.object.light_add(type="AREA", location=(-7, 5, 3.2))
    rim = bpy.context.active_object
    rim.name = "RIM_GAUCHE"
    rim.data.shape = "RECTANGLE"
    rim.data.size, rim.data.size_y = 6.0, 3.0
    rim.data.energy = 4.0 * 0.15 * 90
    rim.data.color = kelvin_to_rgb(4200)[:3]
    rim.rotation_euler = (math.radians(75), 0, math.radians(-125))

    # Ciel de fond : degrade de coucher de soleil, pas un aplat.
    # Les trois couleurs cles du champ H structurent le ciel.
    w = bpy.data.worlds.new("CVR01_WORLD")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    geo = nt.nodes.new("ShaderNodeTexCoord")
    mapr = nt.nodes.new("ShaderNodeMapRange")

    ramp.color_ramp.interpolation = "EASE"
    e = ramp.color_ramp.elements
    e[0].position = 0.0
    e[0].color = hexcol("#E8623C")          # horizon chaud
    e[1].position = 1.0
    e[1].color = hexcol("#704B68")          # zenith violet, couleur cle 2
    m = ramp.color_ramp.elements.new(0.42)
    m.color = hexcol(PAL["ciel"])           # bande orange, couleur cle 1
    m2 = ramp.color_ramp.elements.new(0.68)
    m2.color = hexcol("#A8617A")

    mapr.inputs["From Min"].default_value = -0.25
    mapr.inputs["From Max"].default_value = 0.75
    nt.links.new(geo.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.6
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w

    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection
    return col


# --------------------------------------------------------------------------
# CAMERAS : une par plan, trajectoire exacte du champ E
# --------------------------------------------------------------------------
def interp_mode(courbe_nom, kf, mode):
    """ease-in-out / ease-out / constant du document -> interpolation Blender."""
    if mode == "constant":
        kf.interpolation = "LINEAR"
    elif mode == "ease-out":
        kf.interpolation = "SINE"
        kf.easing = "EASE_OUT"
    else:  # ease-in-out
        kf.interpolation = "SINE"
        kf.easing = "EASE_IN_OUT"


def easing_de(traj):
    t = traj.lower()
    if "ease-in-out" in t:
        return "ease-in-out"
    if "ease-out" in t:
        return "ease-out"
    return "constant"


def build_cameras():
    col = bpy.data.collections.new("CAMERAS")
    bpy.context.scene.collection.children.link(col)
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children["CAMERAS"]

    fps = M.PROJET["fps"]
    plans = M.plans_enrichis()
    cams = []

    for p in plans:
        n_img = int(round(p["duree_s"] * fps))
        f0 = (p["index"] - 1) * n_img + 1
        f1 = f0 + n_img - 1

        cam_data = bpy.data.cameras.new("CAM_%s" % p["id"])
        cam_data.lens = p["focale"]
        cam_data.sensor_width = M.SENSOR_W_MM
        cam_data.sensor_fit = "HORIZONTAL"
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = float(p["diaph"].split("/")[1])

        cam = bpy.data.objects.new("CAM_%s" % p["id"], cam_data)
        bpy.context.collection.objects.link(cam)

        # Cible : le sujet du plan, a hauteur d'yeux, a l'origine du decor.
        # La camera est placee a 'distance' du sujet, sur -Y (axe 0 degre).
        h_sujet = M.hauteur_sujet_m(p)
        cible = Vector((0.0, 0.0, min(h_sujet * 0.62, p["hauteur_cam"])))
        pos0 = Vector((0.0, -p["distance"], p["hauteur_cam"]))

        # Empty cible : la camera y est contrainte, ce qui garantit l'axe 0 deg
        tgt = bpy.data.objects.new("TGT_%s" % p["id"], None)
        tgt.empty_display_size = 0.12
        tgt.location = cible
        bpy.context.collection.objects.link(tgt)
        con = cam.constraints.new("TRACK_TO")
        con.target = tgt
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"

        mvt, traj = p["mouvement"], p["traj"]
        ease = easing_de(traj)
        cam.location = pos0
        cam_data.dof.focus_object = tgt

        # --- trajectoires, une branche par code du glossaire ---
        if mvt == "FIX":
            cam.keyframe_insert("location", frame=f0)

        elif mvt == "TRAV-AV":          # avance de 1,5 m sur l'axe optique
            cam.location = pos0
            cam.keyframe_insert("location", frame=f0)
            cam.location = pos0 + Vector((0, 1.5, 0))
            cam.keyframe_insert("location", frame=f1)

        elif mvt == "TRAV-AR":          # recule de 2 m
            cam.location = pos0
            cam.keyframe_insert("location", frame=f0)
            cam.location = pos0 - Vector((0, 2.0, 0))
            cam.keyframe_insert("location", frame=f1)

        elif mvt == "TRAV-LAT-D":       # 2 m vers +X
            cam.location = pos0 - Vector((1.0, 0, 0))
            cam.keyframe_insert("location", frame=f0)
            cam.location = pos0 + Vector((1.0, 0, 0))
            cam.keyframe_insert("location", frame=f1)

        elif mvt == "TRAV-LAT-G":       # 1,5 m vers -X
            cam.location = pos0 + Vector((0.75, 0, 0))
            cam.keyframe_insert("location", frame=f0)
            cam.location = pos0 - Vector((0.75, 0, 0))
            cam.keyframe_insert("location", frame=f1)

        elif mvt == "TRAV-CIR":         # orbite 25 deg, rayon = distance
            rayon = p["distance"]
            a0, a1 = math.radians(-12.5), math.radians(12.5)
            for fr, a in ((f0, a0), (f1, a1)):
                cam.location = Vector((rayon * math.sin(a), -rayon * math.cos(a),
                                       p["hauteur_cam"]))
                cam.keyframe_insert("location", frame=fr)

        elif mvt == "GRUE-HAUT":        # 1,5 m vertical
            cam.location = pos0
            cam.keyframe_insert("location", frame=f0)
            cam.location = pos0 + Vector((0, 0, 1.5))
            cam.keyframe_insert("location", frame=f1)

        elif mvt == "STEAD":            # suivi lateral 5 m a 1 m/s
            cam.location = pos0 - Vector((2.5, 0, 0))
            cam.keyframe_insert("location", frame=f0)
            cam.location = pos0 + Vector((2.5, 0, 0))
            cam.keyframe_insert("location", frame=f1)
            tgt.location = cible - Vector((2.5, 0, 0))
            tgt.keyframe_insert("location", frame=f0)
            tgt.location = cible + Vector((2.5, 0, 0))
            tgt.keyframe_insert("location", frame=f1)

        elif mvt == "TILT-H":           # +18 deg, camera immobile
            con.influence = 0.0         # tilt pilote a la main
            cam.rotation_euler = (math.radians(90 - 9), 0, 0)
            cam.keyframe_insert("rotation_euler", frame=f0)
            cam.rotation_euler = (math.radians(90 + 9), 0, 0)
            cam.keyframe_insert("rotation_euler", frame=f1)
            cam.keyframe_insert("location", frame=f0)

        elif mvt == "PAN-G":            # -25 deg horizontal
            con.influence = 0.0
            cam.rotation_euler = (math.radians(90), 0, math.radians(12.5))
            cam.keyframe_insert("rotation_euler", frame=f0)
            cam.rotation_euler = (math.radians(90), 0, math.radians(-12.5))
            cam.keyframe_insert("rotation_euler", frame=f1)
            cam.keyframe_insert("location", frame=f0)

        elif mvt == "RACK":             # bascule de point entre 1 s et 2 s
            cam.keyframe_insert("location", frame=f0)
            cam_data.dof.focus_object = None
            cam_data.dof.focus_distance = p["distance"] + 0.45   # la branche
            cam_data.dof.keyframe_insert("focus_distance", frame=f0 + fps)
            cam_data.dof.focus_distance = p["distance"]          # la main
            cam_data.dof.keyframe_insert("focus_distance", frame=f0 + 2 * fps)

        # Easing sur toutes les courbes du plan
        for holder in (cam, cam_data, tgt):
            ad = holder.animation_data
            if ad and ad.action:
                for fc in ad.action.fcurves:
                    for kf in fc.keyframe_points:
                        interp_mode(fc.data_path, kf, ease)

        # Metadonnees tracables depuis le document
        cam["cvr01_plan"] = p["id"]
        cam["cvr01_echelle"] = p["echelle"]
        cam["cvr01_mouvement"] = mvt
        cam["cvr01_traj"] = traj
        cam["cvr01_frame_in"] = f0
        cam["cvr01_frame_out"] = f1
        cam["cvr01_tc_in"] = p["tc_in"]
        cam["cvr01_seed"] = p["seed"]
        cams.append((p, cam, f0, f1))

    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection
    return cams


# --------------------------------------------------------------------------
# MARQUEURS : liaison camera <-> plage d'images, pour un rendu continu
# --------------------------------------------------------------------------
def bind_markers(cams):
    sc = bpy.context.scene
    for p, cam, f0, f1 in cams:
        mk = sc.timeline_markers.new("MK_%s" % p["id"], frame=f0)
        mk.camera = cam


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = M.PROJET["largeur"]
    sc.render.resolution_y = M.PROJET["hauteur"]
    sc.render.resolution_percentage = 100
    sc.render.fps = M.PROJET["fps"]
    sc.frame_start = 1
    sc.frame_end = int(round(M.PROJET["duree_s"] * M.PROJET["fps"]))

    ee = sc.eevee
    ee.taa_render_samples = 16
    ee.use_shadows = True
    try:
        ee.use_raytracing = False      # cel-shading : pas de GI necessaire
    except AttributeError:
        pass

    # Sortie : PNG 16 bits, espace lineaire -> l'etalonnage se fait dans Resolve
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "16"
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"   # le LUT est applique en aval

    # Passes utiles au compositing Resolve
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    vl.use_pass_normal = True
    vl.use_pass_object_index = True


def mat_contour():
    """Materiau du contour : noir pur, non eclaire, visible seulement de dos.

    use_backface_culling = True est la cle de l'inverted hull : sans lui, la
    face AVANT de la coque grossie est visible et les objets deviennent des
    silhouettes noires (mesure : 20 % de pixels noirs avec, 7 % sans).
    """
    m = bpy.data.materials.new("MAT_CONTOUR")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emi = nt.nodes.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = (0.012, 0.008, 0.010, 1.0)
    emi.inputs["Strength"].default_value = 1.0
    nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])
    m.use_backface_culling = True
    return m


def ajouter_contour(ob, mat, epaisseur=0.015):
    """Inverted hull : coque dupliquee, normales retournees, materiau noir.

    Remplace le Line Art Grease Pencil, qui ne rend pas en headless sur GPU
    integre (il produit un aplat noir plein cadre : voir blender/diag_gp.py).
    Cette technique est celle du cel-shading classique : fiable, rapide, et
    independante du moteur de rendu.
    """
    if ob.type != "MESH" or not ob.data.materials:
        return None
    ob.data.materials.append(mat)
    idx = len(ob.data.materials) - 1
    m = ob.modifiers.new("Contour", "SOLIDIFY")
    m.thickness = epaisseur
    m.offset = 1.0
    m.use_flip_normals = True
    m.use_rim = False
    m.material_offset = idx
    m.material_offset_rim = idx
    return m


def setup_contours():
    """Applique le contour a tous les meshes sauf le sol (pas de silhouette)."""
    mat = mat_contour()
    n = 0
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH" and not ob.name.startswith("SOL"):
            if ajouter_contour(ob, mat):
                n += 1
    return n


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(HERE, "cvr01_scene.blend")

    clear_scene()
    build_decor()
    build_props()
    build_light()
    cams = build_cameras()
    bind_markers(cams)
    setup_render()
    n_contours = setup_contours()

    sc = bpy.context.scene
    sc.camera = cams[0][1]

    print("")
    print("=" * 70)
    print("CVR01 - scene construite")
    print("=" * 70)
    print("moteur          : %s" % sc.render.engine)
    print("resolution      : %dx%d @ %d i/s"
          % (sc.render.resolution_x, sc.render.resolution_y, sc.render.fps))
    print("images          : %d -> %d (%d au total)"
          % (sc.frame_start, sc.frame_end, sc.frame_end - sc.frame_start + 1))
    print("objets          : %d" % len(bpy.data.objects))
    print("cameras         : %d" % len(cams))
    print("line art        : inverted hull sur %d objets" % n_contours)
    print("-" * 70)
    for p, cam, f0, f1 in cams:
        print("%-10s %-4s %3d mm  %5.2f m  %-11s img %4d-%4d  %s"
              % (p["id"], p["echelle"], p["focale"], p["distance"],
                 p["mouvement"], f0, f1, p["tc_in"]))
    print("-" * 70)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print("scene enregistree : %s" % os.path.abspath(out))


if __name__ == "__main__":
    main()
