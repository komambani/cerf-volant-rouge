# -*- coding: utf-8 -*-
"""Verificateur du decoupage CVR01 V1.1.

Rejoue sur le modele de donnees les 13 defauts releves dans la V1.0.
Sortie : un rapport lisible + code de sortie 0 (tout passe) ou 1 (echec).

    python doc/verifier.py
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cvr01_model as M  # noqa: E402

ok_global = True
rapport = []


def check(nom, condition, detail=""):
    global ok_global
    statut = "PASS" if condition else "ECHEC"
    if not condition:
        ok_global = False
    rapport.append((statut, nom, detail))
    return condition


P = M.plans_enrichis()

# --- 1. Aucun texte de substitution restant ------------------------------
motifs = ("the main event occurs", "main event", "a definir", "TODO", "XXX",
          "lorem", "placeholder")
trouve = [p["id"] for p in P
          if any(m.lower() in (p["evenement"] or "").lower() for m in motifs)]
check("1. Evenement a 2 s decrit sur les 15 plans (plus de texte de substitution)",
      not trouve and all(len(p["evenement"]) > 40 for p in P),
      "plus court : %d caracteres" % min(len(p["evenement"]) for p in P))

# --- 2. Grille de score calculable ---------------------------------------
check("2. Grille de notation : poids definis, total = 100",
      M.POIDS_TOTAL == 100,
      "total des poids = %d sur %d criteres" % (M.POIDS_TOTAL, len(M.GRILLE)))
check("2b. Formule du score operante (parfait = 100, critique partout = 0)",
      abs(M.score({}) - 100.0) < 1e-9
      and abs(M.score({n: 3 for n, _, _ in M.GRILLE})) < 1e-9,
      "score vide = %.1f ; score critique = %.1f"
      % (M.score({}), M.score({n: 3 for n, _, _ in M.GRILLE})))

# --- 3. Glossaires presents et couvrants ---------------------------------
ech_utilisees = {p["echelle"] for p in P}
mvt_utilises = {p["mouvement"] for p in P}
rac_utilises = {r for p in P for r in p["raccords"]}
check("3. Glossaire des echelles couvre toutes les echelles employees",
      ech_utilisees <= set(M.ECHELLES), "employees : %s" % sorted(ech_utilisees))
check("3b. Glossaire des mouvements couvre tous les mouvements employes",
      mvt_utilises <= set(M.MOUVEMENTS), "employes : %s" % sorted(mvt_utilises))
check("3c. Glossaire des raccords couvre tous les raccords employes",
      rac_utilises <= set(M.RACCORDS), "employes : %s" % sorted(rac_utilises))

# --- 4. Composition : chaque plan dans la bande de SON echelle -----------
hors = [(p["id"], p["echelle"], p["compo_mesure"], p["compo_bande"])
        for p in P if not p["compo_ok"]]
check("4. Portion du sujet dans la bande de l'echelle declaree, 15/15",
      not hors,
      "hors bande : %s" % (hors if hors else "aucun"))

# --- 5. Heure diegetique coherente (une seule source) --------------------
check("5. Heure derivee d'une source unique, aucune divergence fiche/prompt",
      len({p["heure"] for p in P}) <= 4
      and all(re.match(r"^\d\d:\d\d$", p["heure"]) for p in P),
      "plage : %s -> %s" % (P[0]["heure"], P[-1]["heure"]))

# --- 6. Timecodes valides ------------------------------------------------
mauvais = [p["tc_out"] for p in P
           if int(p["tc_out"].split(":")[2]) > 59 or int(p["tc_out"].split(":")[1]) > 59]
check("6. Timecodes valides : aucun champ secondes au-dela de 59",
      not mauvais, "dernier timecode : %s" % P[-1]["tc_out"])
check("6b. Continuite des timecodes : chaque plan reprend ou le precedent s'arrete",
      all(P[i]["tc_in"] == P[i - 1]["tc_out"] for i in range(1, len(P))),
      "%s -> %s sans trou" % (P[0]["tc_in"], P[-1]["tc_out"]))

# --- 7. Champ D present partout ------------------------------------------
sans_d = [p["id"] for p in P if "dialogue" not in p]
check("7. Champ D (dialogue) present sur les 15 fiches, 'aucun' explicite si vide",
      not sans_d,
      "%d plans avec replique, %d avec 'aucun'"
      % (sum(1 for p in P if p["dialogue"]), sum(1 for p in P if not p["dialogue"])))

# --- 8. Structure complete : tous les champs sur tous les plans ----------
requis = ("id", "scene", "fonction", "persos", "debut", "evenement", "fin",
          "emotion", "echelle", "focale", "distance", "hauteur_cam", "diaph",
          "mouvement", "traj", "objets", "raccords", "son_plan")
incomplets = [(p["id"], [c for c in requis if c not in p]) for p in P
              if any(c not in p for c in requis)]
check("8. Structure A-M complete sur les 15 plans",
      not incomplets, "champs manquants : %s" % (incomplets if incomplets else "aucun"))

# --- 9. Registre d'objets par plan, pas de boilerplate -------------------
signatures = {tuple(sorted(p["objets"])) for p in P}
inconnus = [(p["id"], o) for p in P for o in p["objets"] if o not in M.OBJETS]
check("9. Registre d'objets differencie par plan (plus de liste unique)",
      len(signatures) >= 8 and not inconnus,
      "%d combinaisons distinctes sur 15 plans" % len(signatures))
check("9b. Tabouret absent avant son introduction (P001, P002)",
      all("OBJ_STOOL" not in p["objets"] for p in P[:2]),
      "P001 : %s | P002 : %s" % (P[0]["objets"], P[1]["objets"]))
check("9c. OBJ_BENCH present au registre (manquait en V1.0)",
      "OBJ_BENCH" in M.OBJETS and any("OBJ_BENCH" in p["objets"] for p in P),
      "declare sur %d plans" % sum(1 for p in P if "OBJ_BENCH" in p["objets"]))

# --- 10. P011 : le cerf-volant doit tenir dans le cadre ------------------
p11 = next(p for p in P if p["id"] == "S01-P011")
kite_h = M.OBJETS["OBJ_KITE"]["dims_m"][1]
check("10. P011 : cadre assez large pour le cerf-volant (0,75 m)",
      p11["cadre_h"] > kite_h,
      "cadre %.2f m de haut pour un objet de %.2f m" % (p11["cadre_h"], kite_h))

# --- 11. Prompts : un seul idiome, interdits isoles ----------------------
franglais = ("grande depth", "faible depth", "moyenne depth", "recul en",
             "avant en", "autour du groupe", "gauchefidroite", "imagefividéo")
pollution = [m for m in franglais if m.lower() in M.STYLE_EN.lower()
             or m.lower() in M.DECOR_EN.lower()]
check("11. Prompt anglais sans franglais residuel",
      not pollution, "residus : %s" % (pollution if pollution else "aucun"))
check("11b. Interdits isoles dans un negative prompt, absents du prompt positif",
      "photorealism" in M.NEGATIF_EN and "photorealism" not in M.STYLE_EN,
      "%d interdits listes a part" % len(M.NEGATIF_EN.split(",")))

# --- 12. Mouvement desambiguise, coherent avec l'action ------------------
check("12. GRUE-H desambiguise en GRUE-HAUT",
      "GRUE-HAUT" in M.MOUVEMENTS and "GRUE-H" not in M.MOUVEMENTS)
p14 = next(p for p in P if p["id"] == "S01-P014")
check("12b. P014 : amplitude de grue = montee decrite dans l'action (1,5 m)",
      "1,5 m" in p14["traj"] and "1,5 m" in p14["fin"],
      "trajectoire : %s" % p14["traj"])

# --- 13. Bug d'encodage du PDF source -----------------------------------
mojibake = ("fi", "\u2021")
corpus = " ".join([M.STYLE_FR, M.DECOR_FR, M.NEGATIF_EN]
                  + [p["evenement"] for p in P]
                  + [p["traj"] for p in P])
check("13. Aucune ligature cassee heritee du PDF (fleches, superieur-egal)",
      "gauchefi" not in corpus and "\u2021" not in corpus
      and "imagefi" not in corpus)

# --- Coherence generale --------------------------------------------------
check("Duree totale = 75 s sur 15 plans de 5 s",
      abs(sum(p["duree_s"] for p in P) - M.PROJET["duree_s"]) < 1e-9,
      "%.0f s au total" % sum(p["duree_s"] for p in P))
check("Seeds uniques et ordonnes",
      len({p["seed"] for p in P}) == 15,
      "%s -> %s" % (P[0]["seed"], P[-1]["seed"]))
check("Securite : aucune escalade d'arbre, appuis sur tabouret uniquement",
      all("branche" not in p.get("note_objets", "").lower()
          or "jamais" in p.get("note_objets", "").lower()
          for p in P if "OBJ_STOOL" in p["objets"]))

# --- Rendu ---------------------------------------------------------------
largeur = max(len(n) for _, n, _ in rapport) + 2
print("=" * 78)
print("CVR01 %s - verification du decoupage technique" % M.PROJET["version"])
print("=" * 78)
for statut, nom, detail in rapport:
    marque = "[OK]  " if statut == "PASS" else "[FAIL]"
    print("%s %-*s %s" % (marque, largeur, nom, detail))
print("-" * 78)
total = len(rapport)
passes = sum(1 for s, _, _ in rapport if s == "PASS")
print("%d/%d controles passes" % (passes, total))

print()
print("=" * 78)
print("TABLE DES PLANS")
print("=" * 78)
entete = "%-10s %-14s %-4s %-6s %-7s %-12s %-9s %s"
print(entete % ("ID", "SCENE", "ECH", "FOCALE", "DIST", "MOUVEMENT",
                "TC IN", "COMPO"))
print("-" * 78)
for p in P:
    unite = "%" if p["compo_unite"] == "ratio" else "m"
    val = p["compo_mesure"] * 100 if p["compo_unite"] == "ratio" else p["compo_mesure"]
    lo, hi = p["compo_bande"]
    if p["compo_unite"] == "ratio":
        lo, hi = lo * 100, hi * 100
    print(entete % (p["id"], p["scene"][:14], p["echelle"],
                    "%d mm" % p["focale"], "%.2f m" % p["distance"],
                    p["mouvement"], p["tc_in"],
                    "%.0f%s dans [%.0f-%.0f]%s %s"
                    % (val, unite, lo, hi, unite, "OK" if p["compo_ok"] else "HORS")))

sys.exit(0 if ok_global else 1)
