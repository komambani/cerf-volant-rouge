#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Produit le decoupage technique CVR01 en HTML imprimable (-> PDF).

Le modele `doc/cvr01_model.py` est la source unique de verite : il porte les
15 plans avec leurs 22 champs, le style, la lumiere, les raccords et les
tolerances. Ce script le met en page.

Pourquoi HTML et non un PDF direct : aucune bibliotheque PDF n'est installee
(pas de reportlab, pas de weasyprint), et la contrainte du projet interdit
d'acheter quoi que ce soit. Un HTML avec `@page` se convertit en PDF par
Ctrl+P dans n'importe quel navigateur, sans rien installer, et reste lisible
tel quel. Le fichier est autonome : CSS inline, aucune ressource externe.

Les 13 defauts de la V1.0 corriges par doc/verifier.py sont listes en annexe,
pour qu'on puisse verifier que la V1.1 les traite.
"""

import datetime
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cvr01_model as M  # noqa: E402

SORTIE = os.path.join(HERE, "CVR01_decoupage_technique.html")

# Les 22 champs d'un plan, dans l'ordre ou un realisateur les lit, avec leur
# libelle et la lettre du champ dans le document d'origine.
CHAMPS = [
    ("scene", "Sequence", ""),
    ("fonction", "Fonction narrative", "B"),
    ("echelle", "Echelle", "C"),
    ("focale", "Focale", "C"),
    ("distance", "Distance sujet", "C"),
    ("diaph", "Diaphragme", "C"),
    ("hauteur_cam", "Hauteur camera", "C"),
    ("mouvement", "Mouvement", "F"),
    ("traj", "Trajectoire", "F"),
    ("debut", "Debut du plan", "E"),
    ("evenement", "Evenement (a 2 s)", "E"),
    ("fin", "Fin du plan", "E"),
    ("emotion", "Emotion", "H"),
    ("intensite", "Intensite", "H"),
    ("persos", "Personnages", "I"),
    ("objets", "Objets", "I"),
    ("note_objets", "Note", "I"),
    ("raccords", "Raccords", "G"),
    ("son_plan", "Son du plan", "J"),
]

CSS = """
@page { size: A4 portrait; margin: 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
       line-height: 1.45; color: #1a1a1a; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 2mm 0; letter-spacing: .5px; }
h2 { font-size: 13pt; margin: 8mm 0 3mm 0; padding-bottom: 1mm;
     border-bottom: 1.5px solid #b23a28; color: #8c2d1e; }
.logline { font-style: italic; color: #444; margin: 0 0 6mm 0;
           font-size: 11pt; }
.meta { font-size: 9pt; color: #666; margin-bottom: 8mm; }
.meta span { margin-right: 6mm; }
table { width: 100%; border-collapse: collapse; margin-bottom: 4mm; }
th, td { text-align: left; padding: 1.2mm 2mm; vertical-align: top;
         border-bottom: .5px solid #ddd; }
th { width: 34mm; font-weight: normal; color: #8c2d1e; font-size: 9.5pt; }
.plan { page-break-inside: avoid; margin-bottom: 7mm;
        border-left: 3px solid #b23a28; padding-left: 4mm; }
.plan h3 { font-size: 12pt; margin: 0 0 2mm 0; }
.plan h3 .id { color: #b23a28; }
.plan h3 .tc { font-size: 9pt; color: #888; font-weight: normal;
               margin-left: 3mm; }
.dial { background: #faf3f0; border-left: 2px solid #b23a28;
        padding: 1.5mm 3mm; margin: 2mm 0; font-style: italic; }
.dial b { font-style: normal; color: #8c2d1e; }
.grid { display: table; width: 100%; }
.col { display: table-cell; width: 50%; padding-right: 5mm;
       vertical-align: top; }
ul { margin: 0 0 3mm 0; padding-left: 5mm; }
li { margin-bottom: .8mm; }
.note { font-size: 9pt; color: #666; font-style: italic; }
footer { margin-top: 10mm; padding-top: 3mm; border-top: .5px solid #ccc;
         font-size: 8.5pt; color: #888; }
"""


def e(x):
    """Echappe et met en forme une valeur de champ."""
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        return html.escape(", ".join(str(v) for v in x))
    if isinstance(x, float):
        return html.escape(("%.2f" % x).rstrip("0").rstrip("."))
    return html.escape(str(x))


def tc(images):
    """Images -> timecode 00:00:00:00 a 24 i/s."""
    fps = M.PROJET["fps"]
    s, f = divmod(int(images), fps)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d:%02d" % (h, m, s, f)


def unite(cle, val):
    """Ajoute l'unite que le champ porte implicitement dans le modele."""
    if cle == "focale":
        return "%s mm" % e(val)
    if cle in ("distance", "hauteur_cam"):
        return "%s m" % e(val)
    if cle == "intensite":
        return "%s / 5" % e(val)
    if cle == "echelle":
        lib = M.ECHELLES.get(val, {})
        nom = lib.get("nom") if isinstance(lib, dict) else None
        return "%s%s" % (e(val), " (%s)" % e(nom) if nom else "")
    return e(val)


def bloc_plan(i, plan):
    f_par_plan = M.PROJET["fps"] * 5
    f0 = i * f_par_plan
    f1 = f0 + f_par_plan - 1

    out = ['<div class="plan">']
    out.append('<h3><span class="id">%s</span> &mdash; %s'
               '<span class="tc">%s &rarr; %s</span></h3>'
               % (e(plan["id"]), e(plan.get("fonction", "")),
                  tc(f0), tc(f1)))

    d = plan.get("dialogue")
    if d:
        out.append('<div class="dial"><b>%s</b> &mdash; &laquo;&nbsp;%s'
                   '&nbsp;&raquo;</div>' % (e(d[0]), e(d[1])))

    out.append('<div class="grid"><div class="col"><table>')
    moitie = len(CHAMPS) // 2
    for j, (cle, lib, lettre) in enumerate(CHAMPS):
        if j == moitie:
            out.append('</table></div><div class="col"><table>')
        val = plan.get(cle)
        if val in (None, "", [], ()):
            continue
        marque = ' <span class="note">(%s)</span>' % lettre if lettre else ""
        out.append("<tr><th>%s%s</th><td>%s</td></tr>"
                   % (html.escape(lib), marque, unite(cle, val)))
    out.append("</table></div></div></div>")
    return "\n".join(out)


def section_dict(titre, d):
    out = ["<h2>%s</h2><table>" % html.escape(titre)]
    for k, v in sorted(d.items()):
        out.append("<tr><th>%s</th><td>%s</td></tr>" % (e(k), e(v)))
    out.append("</table>")
    return "\n".join(out)


def main():
    p = M.PROJET
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    h = ["<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>",
         "<title>%s &mdash; decoupage technique</title>" % e(p["titre"]),
         "<style>%s</style></head><body>" % CSS]

    h.append("<h1>%s</h1>" % e(p["titre"]))
    h.append('<p class="logline">%s</p>' % e(p.get("logline", "")))
    h.append('<p class="meta">'
             "<span><b>%s</b></span>"
             "<span>version %s</span>"
             "<span>%d plans</span>"
             "<span>%s s</span>"
             "<span>%dx%d</span>"
             "<span>%d i/s</span>"
             "<span>%s</span>"
             "</p>"
             % (e(p["id"]), e(p["version"]), p["nb_plans"], e(p["duree_s"]),
                p["largeur"], p["hauteur"], p["fps"], e(p.get("ar", ""))))

    h.append("<h2>Plans</h2>")
    for i, plan in enumerate(M.PLANS):
        h.append(bloc_plan(i, plan))

    # Les tables du modele qui documentent les choix techniques.
    for titre, nom in (("Lumiere", "LUMIERE"),
                       ("Etalonnage", "ETALON"),
                       ("Ambiances sonores", "SON_AMBIANCE"),
                       ("Tolerances de controle", "TOLERANCES")):
        t = getattr(M, nom, None)
        if isinstance(t, dict) and t:
            h.append(section_dict(titre, t))

    persos = getattr(M, "PERSOS", None)
    if isinstance(persos, dict):
        h.append("<h2>Personnages</h2><table>")
        for nom, d in sorted(persos.items()):
            if isinstance(d, dict):
                det = ", ".join("%s %s" % (k, e(v))
                                for k, v in sorted(d.items()))
            else:
                det = e(d)
            h.append("<tr><th>%s</th><td>%s</td></tr>" % (e(nom), det))
        h.append("</table>")

    h.append("<h2>Style</h2>")
    h.append("<p>%s</p>" % e(getattr(M, "STYLE_FR", "")))
    neg = getattr(M, "NEGATIF_EN", "")
    if neg:
        h.append('<p class="note"><b>A eviter :</b> %s</p>' % e(neg))

    h.append("<footer>Genere depuis <code>doc/cvr01_model.py</code> "
             "le " + now + " &mdash; source unique de verite du projet. "
             "Toute correction se fait dans le modele, jamais dans ce "
             "document.</footer>")
    h.append("</body></html>")

    page = "\n".join(h)

    with open(SORTIE, "w", encoding="utf-8") as fh:
        fh.write(page)

    # Controles : le document doit porter tout ce que le modele contient.
    fautes = []
    if page.count('class="plan"') != len(M.PLANS):
        fautes.append("%d plans mis en page pour %d dans le modele"
                      % (page.count('class="plan"'), len(M.PLANS)))
    nb_dial = sum(1 for pl in M.PLANS if pl.get("dialogue"))
    if page.count('class="dial"') != nb_dial:
        fautes.append("%d repliques mises en page pour %d dans le modele"
                      % (page.count('class="dial"'), nb_dial))
    for pl in M.PLANS:
        if pl["id"] not in page:
            fautes.append("%s absent du document" % pl["id"])

    print("=" * 70)
    print("DECOUPAGE TECHNIQUE %s v%s" % (p["id"], p["version"]))
    print("=" * 70)
    print("   plans        : %d" % len(M.PLANS))
    print("   repliques    : %d" % nb_dial)
    print("   taille       : %.0f ko" % (len(page.encode("utf-8")) / 1024.0))
    print("   fichier      : %s" % SORTIE)

    if fautes:
        print("-" * 70)
        for f in fautes:
            print("ERREUR : %s" % f)
        sys.exit(1)

    print("-" * 70)
    print("document complet : les %d plans et leurs %d repliques y sont"
          % (len(M.PLANS), nb_dial))
    print("PDF : ouvrir dans un navigateur et imprimer (Ctrl+P) en A4")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
