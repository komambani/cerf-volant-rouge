#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repliques de CVR01 : synthese SAPI puis transposition en voix d'enfant.

Une seule voix francaise est installee sur cette machine (Microsoft Hortense,
feminine adulte). Il faut deux enfants : Awa, 12 ans, et Tano, 10 ans, un
garcon. La methode est celle du doublage d'animation quand la distribution
manque : on transpose.

Transposer naivement avec `asetrate` monte la hauteur ET raccourcit le son
(effet Mickey). On transpose donc en deux temps :

    asetrate  -> monte hauteur et tempo ensemble
    atempo    -> ramene la duree d'origine

Le timbre reste celui d'une voix retrecie, ce qui est exactement le but : un
larynx d'enfant est plus petit. Awa monte de 16 %, Tano de 26 % -- un garcon
de 10 ans a une voix plus haute qu'une fille de 12 avant la mue.

Le document (champ D) fait foi pour le texte et pour le plan d'ancrage : la
replique est calee sur l'instant de l'evenement, a 2 s du debut du plan.
"""

import os
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(RACINE, "doc"))

import cvr01_model as M  # noqa: E402

FPS = 24
F_PAR_PLAN = 120
SR = 48000

# Transposition par personnage : (facteur de hauteur, debit SAPI).
# Le debit SAPI va de -10 a 10 ; un enfant parle vite et un peu fort.
VOIX = {
    "Awa": (1.16, 1),
    "Tano": (1.26, 2),
}

PS = ("powershell", "-NoProfile", "-Command")


def sapi(texte, chemin, debit):
    """Fait dire une phrase par la voix francaise, dans un WAV."""
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.SelectVoice('Microsoft Hortense Desktop'); "
        "$s.Rate = %d; "
        "$s.SetOutputToWaveFile('%s'); "
        "$s.Speak('%s'); "
        "$s.Dispose()"
    ) % (debit, chemin.replace("\\", "\\\\"), texte.replace("'", "''"))
    r = subprocess.run(PS + (script,), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("SAPI a echoue : %s" % (r.stderr or r.stdout)[:200])
    if not os.path.isfile(chemin) or os.path.getsize(chemin) < 1000:
        raise RuntimeError("SAPI n'a rien ecrit dans %s" % chemin)


def duree_wav(chemin):
    with wave.open(chemin, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def transpose(entree, sortie, facteur):
    """Monte la hauteur sans changer la duree.

    `asetrate` reinterprete le flux a une nouvelle frequence : il faut donc
    partir de la frequence REELLE du fichier, pas d'une constante. Mesure
    (v2) : SAPI ecrit en 22 050 Hz, et calculer asetrate sur 48 000
    divisait toutes les durees par 2,25 -- « Il est encore la ! » passait de
    1,67 s a 0,74 s, inaudible.

    `atempo` n'accepte qu'un facteur entre 0,5 et 2 : au-dela il faut
    chainer. Ici le facteur reste proche de 1, un seul suffit.
    """
    with wave.open(entree, "rb") as w:
        sr_in = w.getframerate()

    filtre = ("asetrate=%d,aresample=%d,atempo=%.6f,"
              "highpass=f=90,acompressor=threshold=0.12:ratio=3:attack=12"
              ":release=180,aformat=channel_layouts=stereo"
              % (int(sr_in * facteur), SR, 1.0 / facteur))
    r = subprocess.run(
        ("ffmpeg", "-v", "error", "-y", "-i", entree,
         "-af", filtre, "-ar", str(SR), "-ac", "2", sortie),
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg : %s" % r.stderr[:300])


def main():
    brut = os.path.join(HERE, "_brut")
    voix = os.path.join(HERE, "voix")
    os.makedirs(brut, exist_ok=True)
    os.makedirs(voix, exist_ok=True)

    print("=" * 70)
    print("REPLIQUES CVR01 (champ D du decoupage)")
    print("=" * 70)

    lignes = []
    fautes = []

    for i, plan in enumerate(M.PLANS):
        d = plan.get("dialogue")
        if not d:
            continue
        perso, texte = d
        if perso not in VOIX:
            fautes.append("%s : personnage inconnu %s" % (plan["id"], perso))
            continue

        facteur, debit = VOIX[perso]
        f_brut = os.path.join(brut, "%s.wav" % plan["id"])
        f_voix = os.path.join(voix, "%s_%s.wav" % (plan["id"], perso))

        sapi(texte, f_brut, debit)
        d_brut = duree_wav(f_brut)
        transpose(f_brut, f_voix, facteur)
        d_voix = duree_wav(f_voix)

        # La replique est calee sur l'evenement du plan, a 2 s du debut.
        # On la fait DEMARRER un peu avant pour que la syllabe accentuee
        # tombe sur l'image de l'evenement plutot que 300 ms apres.
        t_evt = (i * F_PAR_PLAN + FPS * 2) / float(FPS)
        t_debut = max(i * F_PAR_PLAN / float(FPS) + 0.15,
                      t_evt - d_voix * 0.45)

        # Une replique ne doit pas deborder sur le plan suivant.
        t_fin_plan = (i + 1) * F_PAR_PLAN / float(FPS)
        if t_debut + d_voix > t_fin_plan - 0.1:
            fautes.append("%s : %.2f s de parole ne tient pas dans le plan"
                          % (plan["id"], d_voix))

        # La transposition doit preserver la duree a 5 % pres, sinon le
        # calage calcule ici ne correspond a rien.
        if abs(d_voix - d_brut) > max(0.05, d_brut * 0.05):
            fautes.append("%s : duree %.2f -> %.2f s (transposition fausse)"
                          % (plan["id"], d_brut, d_voix))

        lignes.append((plan["id"], perso, texte, t_debut, d_voix))
        print("   %-9s %-5s %5.2f s a %6.2f s   \"%s\""
              % (plan["id"], perso, d_voix, t_debut, texte))

    print("-" * 70)
    if fautes:
        for f in fautes:
            print("ERREUR : %s" % f)
        sys.exit(1)

    # Table de montage : le monteur (et le script de mixage) lisent ca.
    table = os.path.join(HERE, "voix", "montage.txt")
    with open(table, "w", encoding="utf-8") as fh:
        fh.write("# plan  personnage  debut_s  duree_s  fichier\n")
        for pid, perso, texte, t0, dur in lignes:
            fh.write("%s\t%s\t%.3f\t%.3f\t%s_%s.wav\n"
                     % (pid, perso, t0, dur, pid, perso))

    print("%d repliques, 2 voix transposees (Awa x%.2f, Tano x%.2f)"
          % (len(lignes), VOIX["Awa"][0], VOIX["Tano"][0]))
    print("table de montage : %s" % table)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
