# -*- coding: utf-8 -*-
"""CVR01 - modele de donnees verifie du decoupage technique V1.1.

Source de verite UNIQUE du projet. Toutes les fiches, chronologies, prompts,
scenes Blender et grilles de notation sont generees depuis ce fichier.
Aucune valeur ne doit etre saisie deux fois : si un chiffre apparait dans le
document final, il vient d'ici.

Capteur de reference : full-frame 36 x 24 mm.
    hauteur de cadre (m) = 24 * distance(m) / focale(mm)
    largeur de cadre (m) = 36 * distance(m) / focale(mm)
"""

PROJET = dict(
    id="CVR01",
    titre="LE CERF-VOLANT ROUGE",
    version="V1.1",
    duree_s=75,
    nb_plans=15,
    fps=24,
    largeur=1920,
    hauteur=1080,
    ar="16:9",
    heure_debut="17:42:00",
    lut="CVR01_SUNSET_ANIME_V1",
    logline=(
        "Au coucher du soleil, Awa et Tano liberent un cerf-volant rouge "
        "coince dans un manguier, puis le font redecoller."
    ),
)

SENSOR_H_MM = 24.0
SENSOR_W_MM = 36.0

# ---------------------------------------------------------------------------
# 2. BIBLE
# ---------------------------------------------------------------------------
STYLE_FR = (
    "Animation 2D stylisee premium, anime contemporain africain, line art propre "
    "a variation legere, cel-shading minimal en aplats, couleurs saturees, "
    "lumiere graphique cinematographique, proportions cartoon legerement "
    "exagerees, visages expressifs, perspective ludique, materiaux simplifies, "
    "non photorealiste."
)
STYLE_EN = (
    "premium stylized 2D cel-shaded animation, contemporary African anime, clean "
    "line art with slight weight variation, minimal cel-shading in flat colour "
    "areas, saturated palette, graphic cinematic lighting, slightly exaggerated "
    "cartoon proportions, expressive faces, playful perspective, simplified "
    "materials, non-photorealistic"
)
# Interdits = negative prompt. En V1.0 cette liste etait collee dans le prompt
# positif, ce qui revenait a DEMANDER les defauts. Elle est isolee ici.
NEGATIF_EN = (
    "blur, artifacts, digital noise, flicker, deformed anatomy, deformed hands, "
    "extra fingers, fused limbs, face drift, age drift, hairstyle drift, costume "
    "change, object duplication, object disappearance, unstable background, "
    "readable text, watermark, logo, subtitles, unrequested zoom, cut, camera "
    "shake, additional camera movement, photorealism, realistic skin texture, "
    "extra people, vehicles, signage, wrong kite colour, wrong kite shape, "
    "missing kite tail, unsafe climbing"
)

DECOR_FR = (
    "Cour de quartier residentielle en Afrique de l'Ouest au coucher du soleil : "
    "grand manguier au centre, mur bas en terre ocre au fond, petite maison bleue "
    "a gauche, banc en bois sous l'arbre, sol compact rouge-brun. Aucun vehicule, "
    "aucune foule, aucune enseigne lisible."
)
DECOR_EN = (
    "West African residential courtyard at sunset: large mango tree at the centre, "
    "low ochre earth wall at the back, small blue house on the left, wooden bench "
    "under the tree, compact red-brown ground. No vehicles, no crowd, no readable "
    "signage."
)

PERSOS = {
    "Awa": dict(
        fr=(
            "Awa, fille africaine de 12 ans, 1,48 m, corpulence fine et athletique, "
            "peau brun fonce chaud #6B3F2A ; visage ovale legerement triangulaire, "
            "yeux grands en amande brun tres fonce, nez court droit, bouche moyenne ; "
            "cheveux noirs boucles serres en deux nattes basses avec perles orange ; "
            "t-shirt jaune #F4C542, pantalon cargo indigo #243A73, baskets blanches "
            "a lacets orange ; bracelet tissu orange au poignet gauche."
        ),
        en=(
            "Awa, 12-year-old African girl, 1.48 m, slim athletic build, warm dark "
            "brown skin #6B3F2A; oval slightly triangular face, large very dark brown "
            "almond eyes, short straight nose, medium mouth; black tightly curled hair "
            "in two low braids with orange beads; yellow t-shirt #F4C542, indigo cargo "
            "trousers #243A73, white sneakers with orange laces; orange fabric bracelet "
            "on the left wrist"
        ),
        taille_m=1.48,
    ),
    "Tano": dict(
        fr=(
            "Tano, garcon africain de 10 ans, 1,34 m, corpulence compacte et souple, "
            "peau brun moyen chaud #8A5538 ; visage rond doux, grands yeux ronds brun "
            "fonce, nez court large, bouche large ; cheveux noirs en boucles courtes "
            "serrees ; chemise verte #2E9B67, short beige #D8B980, sandales brunes "
            "#6A4328 ; petit sac en toile rouge #C94335 cote droit."
        ),
        en=(
            "Tano, 10-year-old African boy, 1.34 m, compact supple build, warm medium "
            "brown skin #8A5538; soft round face, large round dark brown eyes, short "
            "wide nose, wide mouth; black short tight curls; green shirt #2E9B67, beige "
            "shorts #D8B980, brown sandals #6A4328; small red canvas bag #C94335 on the "
            "right side"
        ),
        taille_m=1.34,
    ),
}

# ---------------------------------------------------------------------------
# Registre d'objets. V1.0 declarait les 4 memes objets sur les 15 plans, ce qui
# faisait apparaitre le tabouret avant son introduction et le devidoir dans un
# insert de mains. Ici chaque plan declare SA liste (champ I par plan).
# ---------------------------------------------------------------------------
OBJETS = {
    "OBJ_KITE": dict(
        fr=("cerf-volant triangulaire rouge #D83A32, 75 cm de haut, 55 cm de large, "
            "papier mat, bord jaune #F0C94A de 3 cm, queue 2,5 m avec 6 rubans bleus #2E7EDB"),
        en=("triangular red kite #D83A32, 75 cm tall, 55 cm wide, matte paper, 3 cm "
            "yellow border #F0C94A, 2.5 m tail with six blue ribbons #2E7EDB"),
        dims_m=(0.55, 0.75),
    ),
    "OBJ_REEL": dict(
        fr=("devidoir manuel en bois clair #B87942, diametre 9 cm, poignee noire "
            "#211D1A, ficelle blanche 1,5 mm"),
        en=("hand reel in light wood #B87942, 9 cm diameter, black handle #211D1A, "
            "white 1.5 mm string"),
        dims_m=(0.09, 0.09),
    ),
    "OBJ_STOOL": dict(
        fr="tabouret bois brun #70472F, 42 cm de haut, assise 30x30 cm",
        en="brown wooden stool #70472F, 42 cm tall, 30x30 cm seat",
        dims_m=(0.30, 0.42),
    ),
    "OBJ_BRANCH": dict(
        fr="branche basse du manguier, diametre 7 cm, a 2,25 m du sol",
        en="low branch of the mango tree, 7 cm diameter, 2.25 m above the ground",
        dims_m=(2.40, 0.07),
    ),
    # Manquait au registre V1.0 alors que le decor le decrit.
    "OBJ_BENCH": dict(
        fr="banc en bois #8A6240, 1,40 m de long, assise a 42 cm du sol, sous le manguier",
        en="wooden bench #8A6240, 1.40 m long, seat 42 cm above the ground, under the mango tree",
        dims_m=(1.40, 0.42),
    ),
}

# ---------------------------------------------------------------------------
# 3. GLOSSAIRE DES ECHELLES  (absent de la V1.0)
# Chaque echelle porte sa bande de controle, ce qui remplace le "sujet 25-65 %"
# unique qui etait mathematiquement impossible a tenir sur 15 echelles.
# mode "ratio"  : portion de la hauteur du cadre occupee par le sujet debout
# mode "cadre_m": hauteur de cadre visee en metres (gros plans et inserts)
# ---------------------------------------------------------------------------
ECHELLES = {
    "TPG": dict(nom="Tres plan general", mode="ratio",   bande=(0.10, 0.15),
                desc="le lieu domine, le sujet est petit et lisible"),
    "PG":  dict(nom="Plan general",      mode="ratio",   bande=(0.45, 0.60),
                desc="silhouette entiere avec de l'air autour"),
    "PE":  dict(nom="Plan d'ensemble",   mode="ratio",   bande=(0.20, 0.45),
                desc="action lisible dans son espace"),
    "PA":  dict(nom="Plan americain",    mode="cadre_m", bande=(1.20, 1.70),
                desc="cadre a mi-cuisse, laisse de la place a l'action haute"),
    "PM":  dict(nom="Plan moyen",        mode="ratio",   bande=(0.70, 0.80),
                desc="silhouette entiere juste contenue"),
    "PT":  dict(nom="Plan taille",       mode="cadre_m", bande=(0.95, 1.25),
                desc="cadre a la taille"),
    "PR":  dict(nom="Plan rapproche",    mode="cadre_m", bande=(0.65, 0.85),
                desc="cadre a la poitrine"),
    "GP":  dict(nom="Gros plan",         mode="cadre_m", bande=(0.25, 0.35),
                desc="visage ou detail isole"),
    # Bande elargie : un insert doit pouvoir contenir l'objet qu'il montre.
    # Le cerf-volant mesure 0,75 m, donc la borne haute monte a 1,10 m.
    "INS": dict(nom="Insert",            mode="cadre_m", bande=(0.45, 1.10),
                desc="detail d'objet ou de mains ; le cadre doit contenir l'objet montre"),
}

# 4. GLOSSAIRE DES MOUVEMENTS (absent de la V1.0)
MOUVEMENTS = {
    "FIX":        "Camera fixe : aucune translation, aucune rotation.",
    "TRAV-AV":    "Travelling avant : la camera avance sur son axe optique.",
    "TRAV-AR":    "Travelling arriere : la camera recule sur son axe optique.",
    "TRAV-LAT-D": "Travelling lateral droite : translation sur l'axe X vers +X.",
    "TRAV-LAT-G": "Travelling lateral gauche : translation sur l'axe X vers -X.",
    "TRAV-CIR":   "Travelling circulaire : orbite a rayon constant autour du sujet.",
    "TILT-H":     "Tilt haut : rotation verticale de la camera vers le haut.",
    "PAN-G":      "Panoramique gauche : rotation horizontale vers la gauche.",
    "RACK":       "Rack focus : bascule de point, camera immobile.",
    "STEAD":      "Steadicam : suivi stabilise d'un sujet en deplacement.",
    # V1.0 ecrivait "GRUE-H" pour un mouvement vertical : -H lisible comme
    # "haut" ou "horizontale". Desambiguise.
    "GRUE-HAUT":  "Grue montante : translation verticale vers +Z.",
}

# 7. GLOSSAIRE DES RACCORDS (absent de la V1.0)
RACCORDS = {
    "RPOS":  "Raccord de position : le sujet occupe la meme position relative d'un plan au suivant.",
    "RLUM":  "Raccord de lumiere : direction, temperature et contraste identiques.",
    "RAXE":  "Raccord d'axe : respect de la ligne des 180 degres, cote A.",
    "RREG":  "Raccord de regard : la direction du regard reste coherente entre deux plans.",
    "RMOUV": "Raccord de mouvement : une action commencee se poursuit a la meme vitesse.",
    "RCOUP": "Raccord de coupe : l'action est coupee sur un geste en cours, jamais a l'arret.",
}

# ---------------------------------------------------------------------------
# 11. GRILLE DE NOTATION  (la formule V1.0 etait incalculable : aucun critere,
# aucun poids). Total des poids = 100.
#   ecart pondere = somme(poids_i * ecart_i)        avec ecart_i dans 0..3
#   score         = 100 * (1 - ecart_pondere / (3 * 100))
#   plan verrouille si score >= 90 ET aucun ecart de 3 sur deux series
# ---------------------------------------------------------------------------
GRILLE = [
    ("Identite personnages",         18, "visage, age, coiffure, costume, codes hex"),
    ("Action",                       15, "etat a 0 s, evenement a 2 s, etat a 5 s"),
    ("Decor et continuite spatiale", 12, "manguier, mur, maison, banc, sol, positions relatives"),
    ("Camera",                       12, "echelle, focale, distance, trajectoire chiffree"),
    ("Objets",                       12, "presence, forme, dimensions, couleurs du registre du plan"),
    ("Lumiere et colorimetrie",      10, "azimut, elevation, 3600 K, contraste 4:1, LUT"),
    ("Composition",                   8, "tiers, portion sujet, marge tete, horizon"),
    ("Absence d'artefacts",            8, "liste des interdits de la Bible"),
    ("Securite",                      5, "aucune escalade dangereuse representee"),
]
ECHELLE_ECART = [
    (0, "conforme"),
    (1, "ecart mineur, dans les tolerances du champ M"),
    (2, "ecart hors tolerance"),
    (3, "defaut critique : echec automatique du plan"),
]

# ---------------------------------------------------------------------------
# Lumiere (champ G) et etalonnage (champ H), communs aux 15 plans.
# Justification du gel : 75 s d'action = le soleil parcourt environ 0,3 degre.
# ---------------------------------------------------------------------------
LUMIERE = dict(azimut=245, elevation=12, qualite="doux", kelvin=3600,
               contraste="4:1", appoint_ciel=20, rim="gauche 15%")
ETALON = dict(couleurs=("#F28C6B", "#704B68", "#D83A32"), saturation=78,
              grain="fin", nettete="piquee", lut=PROJET["lut"])
SON_AMBIANCE = dict(vent_db=-28, oiseaux_db=-34,
                    musique="marimba/percussions 92 BPM", musique_dbfs=-24,
                    voix_crete_dbfs=-12, cible_programme_lufs=-16)
TOLERANCES = dict(cadrage="+/-5%", position="+/-5%", duree="+/-0,2 s",
                  couleur="+/-300 K", score_min=90, defaut_critique="aucun")
IA = dict(mode="image -> video", generations=3, force_reference=0.82,
          upscale="x2 apres verrouillage")

# ---------------------------------------------------------------------------
# LES 15 PLANS
#
# Les trois corrections structurelles portees par cette table :
#   1. "evenement" : la V1.0 ecrivait "At 2 s: the main event occurs" sur les 15
#      prompts. Le texte de substitution n'avait jamais ete remplace : le modele
#      recevait un debut, une fin, et un trou au milieu. Chaque plan decrit
#      maintenant son beat a 2 s.
#   2. "objets" : registre par plan au lieu des 4 memes objets partout.
#   3. "distance" : ajustee pour que la portion du sujet tombe dans la bande de
#      l'echelle declaree (verifie par doc/verifier.py).
# ---------------------------------------------------------------------------
PLANS = [
    dict(
        id="S01-P001", scene="Decouverte", fonction="etablir le lieu et l'objectif",
        persos=["Awa", "Tano"], sujet_ref="Awa",
        debut="Le cerf-volant est coince dans le feuillage du manguier",
        evenement="Une rafale fait claquer la queue du cerf-volant ; les deux enfants "
                  "s'immobilisent au premier plan et levent la tete vers la cime",
        fin="Le cerf-volant reste visible au-dessus des enfants",
        emotion="Surprise", intensite=4,
        dialogue=("Awa", "Il est encore la !"),
        echelle="TPG", focale=24, distance=12.0, hauteur_cam=3.0, diaph="f/8",
        mouvement="TRAV-AV",
        traj="1,5 m avant en 5 s, 0,3 m/s, ease-in-out",
        objets=["OBJ_KITE", "OBJ_BRANCH", "OBJ_BENCH", "OBJ_REEL"],
        note_objets="le devidoir repose au sol sous l'arbre, relie au cerf-volant par la ficelle",
        raccords=["RPOS", "RLUM", "RAXE"],
        son_plan="rafale de vent breve a 2 s",
    ),
    dict(
        id="S01-P002", scene="Decouverte", fonction="reveler le probleme",
        persos=["Awa"], sujet_ref="Awa",
        debut="Awa leve les yeux vers l'arbre",
        evenement="Son regard remonte la ficelle et s'arrete net : la ficelle fait deux "
                  "tours serres autour de la branche basse",
        fin="Le cerf-volant tremble dans les branches",
        emotion="Inquietude", intensite=4,
        dialogue=None,
        # V1.0 declarait PG a 8 m en 28 mm, soit 22 % du cadre : hors de toute
        # bande PG. Reclasse en PE, qui est l'intention reelle du plan.
        echelle="PE", focale=28, distance=6.0, hauteur_cam=2.0, diaph="f/5.6",
        mouvement="TILT-H",
        traj="+18 degres en 5 s, 3,6 degres/s, ease-out",
        objets=["OBJ_KITE", "OBJ_BRANCH", "OBJ_BENCH"],
        note_objets="le tabouret n'est pas encore dans le champ",
        raccords=["RREG", "RLUM", "RAXE"],
        son_plan="froissement de feuillage",
    ),
    dict(
        id="S01-P003", scene="Premier essai", fonction="introduire une premiere solution",
        persos=["Tano"], sujet_ref="Tano",
        debut="Tano prend le devidoir et avance",
        evenement="Tano enroule deux tours de ficelle autour de sa main et prend appui "
                  "sur sa jambe arriere",
        fin="Il prepare une traction douce",
        emotion="Determination", intensite=4,
        dialogue=("Tano", "Je peux tirer doucement."),
        echelle="PM", focale=50, distance=3.7, hauteur_cam=1.35, diaph="f/4",
        mouvement="TRAV-LAT-D",
        traj="2 m droite en 5 s, 0,4 m/s, constant",
        objets=["OBJ_REEL", "OBJ_KITE", "OBJ_BRANCH", "OBJ_STOOL"],
        note_objets="le tabouret est visible en bord de cadre, pas encore utilise",
        raccords=["RPOS", "RMOUV", "RLUM"],
        son_plan="ficelle qui crisse",
    ),
    dict(
        id="S01-P004", scene="Premier essai", fonction="montrer l'echec controle",
        persos=["Tano"], sujet_ref="Tano",
        debut="Tano monte sur le tabouret et tend la ficelle",
        evenement="Il tire : la branche plie de quelques centimetres, la ficelle saute "
                  "d'un cran et le tabouret oscille sous ses pieds",
        fin="La ficelle glisse de la branche sans se liberer",
        emotion="Concentration", intensite=4,
        dialogue=("Tano", "Elle ne vient pas."),  # champ D absent en V1.0
        echelle="PM", focale=50, distance=4.9, hauteur_cam=1.35, diaph="f/4",
        mouvement="TRAV-AV",
        traj="1,5 m avant en 5 s, 0,3 m/s, ease-in-out",
        objets=["OBJ_STOOL", "OBJ_REEL", "OBJ_KITE", "OBJ_BRANCH"],
        note_objets="Tano a les deux pieds sur l'assise, jamais sur une branche",
        raccords=["RMOUV", "RLUM", "RAXE"],
        son_plan="craquement de bois sourd a 2 s",
        sujet_bonus_m=0.42,  # hauteur du tabouret, comptee dans la portion sujet
    ),
    dict(
        id="S01-P005", scene="Premier essai", fonction="eviter une action dangereuse",
        persos=["Awa"], sujet_ref="Awa",
        debut="Awa tend la main vers Tano",
        evenement="Elle voit le tabouret vaciller ; sa main s'ouvre paume en avant et "
                  "se fige",
        fin="Elle lui fait signe d'arreter",
        emotion="Vigilance", intensite=4,
        dialogue=("Awa", "Doucement !"),
        echelle="PR", focale=70, distance=2.1, hauteur_cam=1.35, diaph="f/3.2",
        mouvement="PAN-G",
        traj="-25 degres en 5 s, 5 degres/s, ease-in-out",
        objets=["OBJ_KITE"],
        note_objets="le cerf-volant reste visible en arriere-plan, hors du plan de nettete",
        raccords=["RREG", "RLUM", "RAXE"],
        son_plan="respiration courte",
    ),
    dict(
        id="S01-P006", scene="Idee", fonction="faire naitre une solution",
        persos=["Awa", "Tano"], sujet_ref="Awa",
        debut="Awa observe la branche basse",
        evenement="Son regard suit la ficelle depuis le noeud jusqu'a la branche basse "
                  "et s'arrete : le trajet est accessible depuis le sol",
        fin="Elle pointe une trajectoire plus sure",
        emotion="Reflexion", intensite=4,
        dialogue=("Awa", "On peut passer par cette branche."),
        echelle="PT", focale=50, distance=2.3, hauteur_cam=1.30, diaph="f/3.5",
        mouvement="TRAV-CIR",
        traj="25 degres autour du groupe, rayon 2,3 m, 5 s, vitesse constante",
        objets=["OBJ_KITE", "OBJ_BRANCH", "OBJ_STOOL", "OBJ_BENCH"],
        raccords=["RREG", "RPOS", "RLUM"],
        son_plan="musique : la percussion se suspend sur un temps",
    ),
    dict(
        id="S01-P007", scene="Idee", fonction="preparer la seconde tentative",
        persos=["Awa"], sujet_ref="Awa",
        debut="Awa deplace le tabouret sous la branche",
        evenement="Elle pose le tabouret et appuie du pied sur l'assise pour tester "
                  "sa stabilite",
        fin="Le tabouret est correctement place et stable",
        emotion="Confiance", intensite=4,
        dialogue=("Awa", "La, il est stable."),  # champ D absent en V1.0
        echelle="PM", focale=50, distance=4.1, hauteur_cam=1.35, diaph="f/4",
        mouvement="TRAV-LAT-G",
        traj="1,5 m gauche en 5 s, 0,3 m/s, constant",
        objets=["OBJ_STOOL", "OBJ_BRANCH", "OBJ_KITE"],
        raccords=["RMOUV", "RPOS", "RLUM"],
        son_plan="bois pose sur sol sec",
    ),
    dict(
        id="S01-P008", scene="Action", fonction="atteindre la ficelle",
        persos=["Awa"], sujet_ref="Awa",
        debut="Awa monte sur le tabouret et tend le bras",
        evenement="Elle se hisse sur la pointe des pieds ; ses doigts passent a quelques "
                  "centimetres de la ficelle, puis la frolent",
        fin="Sa main atteint la ficelle",
        emotion="Effort", intensite=4,
        dialogue=("Awa", "Presque..."),  # champ D absent en V1.0
        echelle="PM", focale=50, distance=5.2, hauteur_cam=1.35, diaph="f/4",
        mouvement="TRAV-AV",
        traj="1,5 m avant en 5 s, 0,3 m/s, ease-in-out",
        objets=["OBJ_STOOL", "OBJ_BRANCH", "OBJ_KITE", "OBJ_REEL"],
        note_objets="le devidoir est pose au sol ; Awa garde les deux pieds sur l'assise",
        raccords=["RMOUV", "RPOS", "RLUM"],
        son_plan="tissu qui frotte",
        sujet_bonus_m=0.42,
    ),
    dict(
        id="S01-P009", scene="Action", fonction="liberer la ficelle",
        persos=["Awa"], sujet_ref="Awa",
        debut="Awa saisit la ficelle",
        evenement="La bascule de point passe de la branche a la main ; ses doigts "
                  "decrochent la boucle du premier tour",
        fin="La ficelle se detend et se libere",
        emotion="Concentration", intensite=4,
        dialogue=("Awa", "Je l'ai !"),
        echelle="GP", focale=85, distance=1.05, hauteur_cam=1.30, diaph="f/2.8",
        mouvement="RACK",
        traj="bascule de point branche -> main entre 1 s et 2 s, camera fixe",
        objets=["OBJ_BRANCH", "OBJ_KITE"],
        note_objets="cadrage sur la main et la branche ; le cerf-volant n'est present "
                    "que par la ficelle tendue",
        raccords=["RPOS", "RLUM", "RMOUV"],
        son_plan="ficelle qui se detend, note de marimba isolee",
    ),
    dict(
        id="S01-P010", scene="Action", fonction="recuperer le cerf-volant",
        persos=["Awa", "Tano"], sujet_ref="Tano",
        debut="Le cerf-volant commence a tomber",
        evenement="Libere, le cerf-volant pivote sur sa pointe et glisse le long du "
                  "feuillage ; Tano plonge d'un pas de cote sous sa trajectoire",
        fin="Tano le recupere a deux mains",
        emotion="Suspense", intensite=4,
        dialogue=("Tano", "Attrape !"),
        echelle="PA", focale=50, distance=3.0, hauteur_cam=1.30, diaph="f/4",
        mouvement="TRAV-AR",
        traj="2 m recul en 5 s, 0,4 m/s, ease-out",
        objets=["OBJ_KITE", "OBJ_REEL", "OBJ_BENCH"],
        raccords=["RMOUV", "RCOUP", "RLUM"],
        son_plan="froissement de papier, pas rapides",
    ),
    dict(
        id="S01-P011", scene="Reussite", fonction="montrer l'objet sauve",
        persos=["Tano"], sujet_ref="Tano",
        debut="Les mains tiennent le cerf-volant",
        evenement="Les pouces lissent une pliure du papier pres du bord jaune ; la "
                  "pliure disparait",
        fin="Le papier se stabilise",
        emotion="Soulagement", intensite=4,
        dialogue=("Tano", "Il n'est pas dechire."),  # champ D absent en V1.0
        # V1.0 : 70 mm a 0,8 m = 0,27 m de cadre pour un objet de 0,75 m. Le
        # cerf-volant ne pouvait pas tenir dans le plan. Recule a 2,80 m, ce qui
        # donne 0,96 m de cadre : les mains, le bord jaune et toute la toile.
        echelle="INS", focale=70, distance=2.80, hauteur_cam=1.10, diaph="f/4",
        mouvement="FIX", traj="aucun",
        objets=["OBJ_KITE"],
        note_objets="le cerf-volant entier tenu a deux mains, bord jaune et "
                    "attache de queue visibles",
        raccords=["RPOS", "RLUM"],
        son_plan="papier qui se detend",
    ),
    dict(
        id="S01-P012", scene="Reussite", fonction="partager le succes",
        persos=["Awa", "Tano"], sujet_ref="Awa",
        debut="Ils regardent le cerf-volant",
        evenement="Leurs regards quittent le cerf-volant au meme instant et se croisent",
        fin="Ils echangent un sourire",
        emotion="Joie", intensite=4,
        dialogue=("Awa", "On l'a !"),
        echelle="PM", focale=50, distance=4.1, hauteur_cam=1.35, diaph="f/4",
        mouvement="TRAV-CIR",
        traj="25 degres autour du groupe, rayon 4,1 m, 5 s, vitesse constante",
        objets=["OBJ_KITE", "OBJ_REEL"],
        raccords=["RREG", "RPOS", "RLUM"],
        son_plan="musique : la percussion reprend pleine",
    ),
    dict(
        id="S01-P013", scene="Nouveau depart", fonction="tester le cerf-volant",
        persos=["Awa", "Tano"], sujet_ref="Awa",
        debut="Awa tient le devidoir, Tano tient le cerf-volant",
        evenement="Awa lance le depart d'un signe de tete ; les deux enfants s'elancent "
                  "ensemble vers l'espace ouvert",
        fin="Ils courent vers l'espace ouvert",
        emotion="Excitation", intensite=4,
        dialogue=("Tano", "Pret ?"),
        echelle="PG", focale=28, distance=3.5, hauteur_cam=2.0, diaph="f/5.6",
        mouvement="STEAD",
        traj="suivi lateral 5 m a 1 m/s, distance au sujet maintenue a 3,5 m",
        objets=["OBJ_KITE", "OBJ_REEL"],
        raccords=["RMOUV", "RAXE", "RLUM"],
        son_plan="pas sur sol sec, souffle",
    ),
    dict(
        id="S01-P014", scene="Nouveau depart", fonction="faire decoller le cerf-volant",
        persos=["Awa", "Tano"], sujet_ref="Awa",
        debut="Le cerf-volant quitte les mains de Tano",
        evenement="La ficelle se tend d'un coup, le vent prend la toile et la queue se "
                  "deploie entierement",
        fin="Il monte de 1,5 m au-dessus des mains de Tano",
        emotion="Emerveillement", intensite=4,
        dialogue=("Awa", "Vas-y !"),
        echelle="PE", focale=35, distance=6.0, hauteur_cam=1.45, diaph="f/5.6",
        # V1.0 : "GRUE-H, 2 m vertical" alors que l'action dit "monte de 1,5 m".
        mouvement="GRUE-HAUT",
        traj="1,5 m vertical en 5 s, 0,3 m/s, ease-out",
        objets=["OBJ_KITE", "OBJ_REEL"],
        raccords=["RMOUV", "RCOUP", "RLUM"],
        son_plan="claquement de toile, montee de marimba",
    ),
    dict(
        id="S01-P015", scene="Nouveau depart", fonction="conclusion visuelle",
        persos=["Awa", "Tano"], sujet_ref="Awa",
        debut="Le cerf-volant vole au-dessus du manguier",
        evenement="Le cerf-volant franchit la cime du manguier et entre dans le ciel "
                  "ouvert, sa queue dessinant une courbe lente",
        fin="Les enfants restent petits au bas du cadre",
        emotion="Fierte", intensite=4,
        dialogue=None,
        echelle="TPG", focale=24, distance=12.0, hauteur_cam=3.0, diaph="f/8",
        mouvement="TRAV-AR",
        traj="2 m recul en 5 s, 0,4 m/s, ease-out",
        objets=["OBJ_KITE", "OBJ_BENCH"],
        raccords=["RPOS", "RLUM", "RAXE"],
        son_plan="vent large, musique en resolution",
    ),
]

# ---------------------------------------------------------------------------
# Derives calculees. Aucune de ces valeurs n'est saisie a la main.
# ---------------------------------------------------------------------------
def duree_plan(_plan=None):
    return PROJET["duree_s"] / PROJET["nb_plans"]


def timecode(secondes):
    """HH:MM:SS. La V1.0 ecrivait 00:00:60 a 00:00:75, invalides."""
    s = int(round(secondes))
    return "%02d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def heure_diegetique(secondes):
    """Heure dans la fiction, derivee de PROJET['heure_debut'] + offset."""
    h, m, s = (int(x) for x in PROJET["heure_debut"].split(":"))
    total = h * 3600 + m * 60 + s + int(round(secondes))
    return "%02d:%02d" % (total // 3600, (total % 3600) // 60)


def cadre_m(focale, distance):
    """(largeur, hauteur) du cadre en metres a cette distance."""
    return (SENSOR_W_MM * distance / focale, SENSOR_H_MM * distance / focale)


def hauteur_sujet_m(plan):
    base = PERSOS[plan["sujet_ref"]]["taille_m"]
    return base + plan.get("sujet_bonus_m", 0.0)


def controle_composition(plan):
    """Verifie le plan contre la bande de SON echelle.
    Retourne (ok, mesure, bande, unite)."""
    ech = ECHELLES[plan["echelle"]]
    _, h_cadre = cadre_m(plan["focale"], plan["distance"])
    lo, hi = ech["bande"]
    if ech["mode"] == "ratio":
        mesure = hauteur_sujet_m(plan) / h_cadre
        return (lo <= mesure <= hi, mesure, ech["bande"], "ratio")
    return (lo <= h_cadre <= hi, h_cadre, ech["bande"], "m")


def plans_enrichis():
    """Les 15 plans avec timecodes, heures et geometrie resolus."""
    out, t = [], 0.0
    for i, p in enumerate(PLANS, start=1):
        d = duree_plan(p)
        q = dict(p)
        q["index"] = i
        q["duree_s"] = d
        q["t_debut"] = t
        q["t_fin"] = t + d
        q["tc_in"] = timecode(t)
        q["tc_out"] = timecode(t + d)
        q["heure"] = heure_diegetique(t)
        q["cadre_l"], q["cadre_h"] = cadre_m(p["focale"], p["distance"])
        ok, mesure, bande, unite = controle_composition(p)
        q["compo_ok"], q["compo_mesure"] = ok, mesure
        q["compo_bande"], q["compo_unite"] = bande, unite
        q["seed"] = "%s_%04d" % (PROJET["id"], i)
        out.append(q)
        t += d
    return out


POIDS_TOTAL = sum(w for _, w, _ in GRILLE)


def score(ecarts):
    """ecarts : dict critere -> 0..3. Formule du document, rendue calculable."""
    pondere = sum(w * ecarts.get(nom, 0) for nom, w, _ in GRILLE)
    return 100.0 * (1.0 - pondere / (3.0 * POIDS_TOTAL))
