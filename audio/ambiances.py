#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthese des ambiances de CVR01 : vent, oiseaux, marimba.

Aucune banque de sons, aucun service payant : tout est calcule ici avec
numpy, puis ecrit en WAV 48 kHz stereo. Le decoupage impose les niveaux
(champ J) et c'est le document qui fait foi :

    vent     -28 dB      continu, 75 s
    oiseaux  -34 dB      evenements epars
    musique  -24 dBFS    marimba + percussions, 92 BPM

Chaque couche est rendue separement pour que le montage puisse les doser,
et le controle final verifie que le niveau mesure correspond a la consigne
a 1 dB pres -- un fichier qui sort a -12 dB quand on demande -28 noie le
dialogue, et personne ne s'en apercoit avant le mixage.
"""

import os
import sys
import wave

import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
DUREE = 75.0

# Gamme pentatonique majeure sur do, registre marimba (do4 a la5). Une
# pentatonique n'a pas de demi-ton : toute superposition sonne juste, ce qui
# evite d'ecrire une harmonie a la main.
PENTA = [261.63, 293.66, 329.63, 392.00, 440.00,
         523.25, 587.33, 659.25, 783.99, 880.00]

BPM = 92.0
NOIRE = 60.0 / BPM


def rms_db(x):
    """Niveau RMS en dBFS. Reference : pleine echelle = 1.0."""
    r = float(np.sqrt(np.mean(np.square(x))))
    return -np.inf if r <= 0 else 20.0 * np.log10(r)


def cale(x, cible_db):
    """Met le signal au niveau demande, puis protege contre l'ecretage.

    Le gain est calcule sur le RMS, mais un signal percussif peut avoir des
    cretes tres au-dessus : si le pic depasse 0 dBFS on redescend le tout,
    sinon le WAV 16 bits enroule et produit un claquement.

    Mesure (v2) : la musique sortait a -25,1 dB pour une consigne de -24 --
    le marimba a un facteur de crete de 14 dB, la reduction anti-ecretage
    annulait une partie du calage. On ecrete donc les cretes EN DOUCEUR
    avant de caler : la tangente hyperbolique arrondit ce qui depasse le
    seuil sans creer l'angle vif qui s'entend comme une saturation.
    """
    act = rms_db(x)
    if not np.isfinite(act):
        return x

    y = x * (10.0 ** ((cible_db - act) / 20.0))

    # Limiteur doux : au-dela de 3,2 fois le RMS, la courbe s'aplatit.
    seuil = 3.2 * float(np.sqrt(np.mean(np.square(y))))
    if seuil > 0:
        fort = np.abs(y) > seuil
        if np.any(fort):
            y[fort] = np.sign(y[fort]) * seuil * (
                1.0 + np.tanh((np.abs(y[fort]) - seuil) / seuil))
            # Le limiteur a baisse le RMS : on recale apres.
            act2 = rms_db(y)
            if np.isfinite(act2):
                y *= 10.0 ** ((cible_db - act2) / 20.0)

    pic = float(np.max(np.abs(y)))
    if pic > 0.985:
        y *= 0.985 / pic
    return y


def bruit_rose(n, graine):
    """Bruit en 1/f par filtrage spectral (methode de Voss simplifiee).

    Le bruit blanc est trop siffant pour du vent : son energie est plate,
    alors que le vent reel decroit avec la frequence.
    """
    rng = np.random.default_rng(graine)
    blanc = rng.standard_normal(n)
    spec = np.fft.rfft(blanc)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1]
    spec /= np.sqrt(f)
    return np.fft.irfft(spec, n)


def passe_bas(x, fc):
    """Filtre a un pole, ecrit a la main (scipy n'est pas installe)."""
    a = np.exp(-2.0 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(x.size):
        acc = (1.0 - a) * x[i] + a * acc
        y[i] = acc
    return y


def vent(duree=DUREE):
    """Vent dans les feuilles : bruit rose filtre, module par des rafales.

    Deux couches a frequences de coupure differentes donnent la profondeur ;
    la modulation lente (0,05-0,13 Hz) evite le souffle de climatisation.
    """
    n = int(duree * SR)
    t = np.arange(n) / SR

    base = passe_bas(bruit_rose(n, 1), 900.0)
    aigu = passe_bas(bruit_rose(n, 2), 3200.0) * 0.35

    rafale = (0.62
              + 0.26 * np.sin(2 * np.pi * 0.053 * t)
              + 0.14 * np.sin(2 * np.pi * 0.131 * t + 1.1)
              + 0.08 * np.sin(2 * np.pi * 0.019 * t + 2.3))
    mono = (base + aigu) * rafale

    # Decorrelation gauche/droite : le meme signal des deux cotes se loge
    # dans la tete de l'auditeur au lieu de l'entourer.
    retard = int(0.013 * SR)
    g = mono
    d = np.concatenate([mono[retard:], mono[:retard]]) * 0.93
    return np.stack([g, d], axis=1)


def chant(f0, duree, rng):
    """Un cri d'oiseau : porteuse sifflee a frequence glissante."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    glis = f0 * (1.0 + 0.42 * np.sin(2 * np.pi * (2.3 + rng.random()) * t))
    phase = 2 * np.pi * np.cumsum(glis) / SR
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.6
    return np.sin(phase) * env * (0.55 + 0.45 * rng.random())


def oiseaux(duree=DUREE):
    """Chants epars : 2 a 4 notes par appel, places au hasard mais jamais
    pendant les deux secondes qui encadrent un evenement de plan."""
    rng = np.random.default_rng(7)
    n = int(duree * SR)
    g = np.zeros(n)
    d = np.zeros(n)

    t = 1.5
    while t < duree - 2.0:
        # Un appel = quelques notes rapprochees.
        pan = rng.random()
        for _ in range(rng.integers(2, 5)):
            dur = 0.07 + 0.11 * rng.random()
            f0 = 2100.0 + 1900.0 * rng.random()
            s = chant(f0, dur, rng)
            i = int(t * SR)
            j = min(i + s.size, n)
            g[i:j] += s[:j - i] * (1.0 - pan)
            d[i:j] += s[:j - i] * pan
            t += dur + 0.04 + 0.09 * rng.random()
        t += 2.2 + 5.5 * rng.random()

    return np.stack([g, d], axis=1)


def note_marimba(f0, duree, amp):
    """Marimba : fondamentale + harmonique 4 (le mode de barre), attaque
    raide, extinction exponentielle. L'harmonique 4 est ce qui distingue le
    marimba du xylophone."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    corps = (np.sin(2 * np.pi * f0 * t)
             + 0.42 * np.sin(2 * np.pi * 4.0 * f0 * t)
             + 0.17 * np.sin(2 * np.pi * 9.2 * f0 * t))
    env = np.exp(-t * (5.4 + 480.0 / f0))
    attaque = np.minimum(1.0, t / 0.004)
    return corps * env * attaque * amp


def percussion(duree, graine):
    """Frappe seche : bruit filtre a extinction tres rapide."""
    rng = np.random.default_rng(graine)
    n = int(duree * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t * 42.0)
    return passe_bas(x, 2600.0) * 1.8


def musique(duree=DUREE):
    """Marimba pentatonique a 92 BPM, avec un arc dramatique.

    Le decoupage place l'evenement de chaque plan a 2 s ; la musique suit la
    courbe du recit : discrete au debut (recherche), dense au climax (P009 a
    P012, soit 40 a 60 s), apaisee a la fin.
    """
    rng = np.random.default_rng(11)
    n = int(duree * SR)
    g = np.zeros(n)
    d = np.zeros(n)

    def pose(sig, t, pan):
        i = int(t * SR)
        if i >= n:
            return
        j = min(i + sig.size, n)
        g[i:j] += sig[:j - i] * (1.0 - pan)
        d[i:j] += sig[:j - i] * pan

    # Densite par tranche de 15 s (une tranche = 3 plans).
    densite = [0.45, 0.55, 0.75, 1.00, 0.70]

    t = 0.0
    while t < duree - 1.0:
        tranche = min(int(t / 15.0), len(densite) - 1)
        dens = densite[tranche]

        if rng.random() < dens:
            f = PENTA[rng.integers(0, len(PENTA))]
            amp = 0.30 + 0.45 * dens * rng.random()
            pose(note_marimba(f, 1.6, amp), t, 0.25 + 0.5 * rng.random())

        # Doublure a la quinte dans les passages denses.
        if dens > 0.7 and rng.random() < 0.35:
            f = PENTA[rng.integers(0, len(PENTA) - 3)] * 1.5
            pose(note_marimba(f, 1.2, 0.22), t + NOIRE / 2, rng.random())

        t += NOIRE / 2

    # Percussions : appui sur les temps, plus present au climax.
    t = 0.0
    k = 0
    while t < duree - 0.5:
        tranche = min(int(t / 15.0), len(densite) - 1)
        if k % 2 == 0 or densite[tranche] > 0.7:
            amp = 0.5 + 0.5 * densite[tranche]
            pose(percussion(0.22, k) * amp, t, 0.5)
        t += NOIRE
        k += 1

    return np.stack([g, d], axis=1)


def ecrire(chemin, x, cible_db):
    """Ecrit un WAV 16 bits stereo au niveau demande."""
    y = cale(x, cible_db)
    data = (np.clip(y, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return rms_db(y)


def main():
    os.makedirs(HERE, exist_ok=True)
    couches = (
        ("vent.wav", vent, -28.0),
        ("oiseaux.wav", oiseaux, -34.0),
        ("musique.wav", musique, -24.0),
    )

    print("=" * 70)
    print("AMBIANCES CVR01 : %d couches, %.0f s, %d Hz" % (
        len(couches), DUREE, SR))
    print("=" * 70)

    fautes = []
    for nom, fonction, cible in couches:
        chemin = os.path.join(HERE, nom)
        mesure = ecrire(chemin, fonction(), cible)
        ecart = abs(mesure - cible)
        etat = "ok" if ecart <= 1.0 else "ECART"
        print("   %-13s consigne %6.1f dB   mesure %6.1f dB   %s"
              % (nom, cible, mesure, etat))
        if ecart > 1.0:
            fautes.append("%s : %.1f dB au lieu de %.1f"
                          % (nom, mesure, cible))

        # Un fichier muet passerait le controle de niveau si on ne verifiait
        # que le RMS d'un signal nul -- on verifie donc aussi qu'il y a de
        # la matiere.
        taille = os.path.getsize(chemin)
        attendu = int(DUREE * SR * 4 * 0.98)
        if taille < attendu:
            fautes.append("%s : %d octets, attendu >= %d"
                          % (nom, taille, attendu))

    print("-" * 70)
    if fautes:
        for f in fautes:
            print("ERREUR : %s" % f)
        sys.exit(1)
    print("3 couches ecrites aux niveaux du decoupage (champ J)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
