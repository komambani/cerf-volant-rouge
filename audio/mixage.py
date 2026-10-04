#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mixage de CVR01 : 3 ambiances + 13 repliques -> une bande son unique.

Le decoupage impose les niveaux (champ J), mais un mixage n'est pas une
addition : si le vent, la musique et une replique sonnent en meme temps au
niveau nominal, la voix passe dessous. On applique donc un DUCKING -- la
musique et les ambiances baissent automatiquement pendant que quelqu'un
parle, et remontent apres.

C'est ce que fait un monteur son a la main sur chaque replique. Ici c'est
calcule a partir de la table produite par repliques.py, donc c'est exact au
millieme de seconde et ca se refait tout seul si une replique bouge.
"""

import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(HERE)

SR = 48000
DUREE = 75.0

# Attenuation appliquee aux fonds pendant une replique, en dB.
DUCK_MUSIQUE = -9.0
DUCK_AMBIANCE = -4.0
# Temps de descente et de remontee : assez vif pour degager la voix, assez
# lent pour ne pas s'entendre comme une pompe.
T_DESCENTE = 0.12
T_REMONTEE = 0.45


def lire(chemin):
    """WAV -> tableau float stereo (n, 2), reechantillonne si besoin."""
    with wave.open(chemin, "rb") as w:
        n = w.getnframes()
        sr = w.getframerate()
        ch = w.getnchannels()
        brut = np.frombuffer(w.readframes(n), dtype=np.int16)
    x = brut.astype(np.float64) / 32768.0
    x = x.reshape(-1, ch)
    if ch == 1:
        x = np.repeat(x, 2, axis=1)
    if sr != SR:
        # Reechantillonnage lineaire : suffisant ici, les fichiers voix
        # sortent deja a 48 kHz, c'est un garde-fou.
        m = int(round(x.shape[0] * SR / float(sr)))
        t = np.linspace(0, x.shape[0] - 1, m)
        x = np.stack([np.interp(t, np.arange(x.shape[0]), x[:, c])
                      for c in range(2)], axis=1)
    return x


def rms_db(x):
    r = float(np.sqrt(np.mean(np.square(x))))
    return -np.inf if r <= 0 else 20.0 * np.log10(r)


def enveloppe_ducking(evenements, n):
    """Courbe de gain (1.0 = plein niveau) creusee a chaque replique."""
    g = np.ones(n)
    nd = max(1, int(T_DESCENTE * SR))
    nr = max(1, int(T_REMONTEE * SR))
    for t0, dur in evenements:
        i0 = int(t0 * SR)
        i1 = int((t0 + dur) * SR)
        a = max(0, i0 - nd)
        b = min(n, i1 + nr)
        if a >= b:
            continue
        creux = np.ones(b - a)
        # descente
        d = i0 - a
        if d > 0:
            creux[:d] = np.linspace(1.0, 0.0, d)
        # plateau
        creux[d:i1 - a] = 0.0
        # remontee
        r = b - i1
        if r > 0:
            creux[i1 - a:] = np.linspace(0.0, 1.0, r)
        g[a:b] = np.minimum(g[a:b], creux)
    return g


def appliquer_duck(x, g, duck_db):
    """g vaut 1 hors replique et 0 au creux ; duck_db est l'attenuation."""
    gain = 10.0 ** (duck_db / 20.0)
    facteur = gain + (1.0 - gain) * g
    return x * facteur[:, None]


def main():
    voix_dir = os.path.join(HERE, "voix")
    table = os.path.join(voix_dir, "montage.txt")
    if not os.path.isfile(table):
        print("ERREUR : %s absent -- lancer repliques.py d'abord" % table)
        sys.exit(1)

    n = int(DUREE * SR)
    print("=" * 70)
    print("MIXAGE CVR01 : %.0f s, %d Hz" % (DUREE, SR))
    print("=" * 70)

    # --- repliques ---------------------------------------------------------
    piste_voix = np.zeros((n, 2))
    evenements = []
    nb = 0
    with open(table, encoding="utf-8") as fh:
        for ligne in fh:
            if ligne.startswith("#") or not ligne.strip():
                continue
            pid, perso, t0, dur, nom = ligne.split("\t")
            t0 = float(t0)
            chemin = os.path.join(voix_dir, nom.strip())
            if not os.path.isfile(chemin):
                print("ERREUR : %s absent" % chemin)
                sys.exit(1)
            v = lire(chemin)
            i = int(t0 * SR)
            j = min(i + v.shape[0], n)
            piste_voix[i:j] += v[:j - i]
            evenements.append((t0, float(dur)))
            nb += 1
    print("   repliques        : %d placees" % nb)

    # Les voix sont la priorite : -16 dBFS, nettement au-dessus des fonds.
    act = rms_db(piste_voix)
    if np.isfinite(act):
        piste_voix *= 10.0 ** ((-16.0 - act) / 20.0)

    # --- fonds, avec ducking ----------------------------------------------
    g = enveloppe_ducking(evenements, n)
    creux = float(np.mean(g < 0.5))
    print("   ducking          : %.0f %% du film sous attenuation"
          % (creux * 100.0))

    melange = piste_voix.copy()
    for nom, duck in (("musique.wav", DUCK_MUSIQUE),
                      ("vent.wav", DUCK_AMBIANCE),
                      ("oiseaux.wav", DUCK_AMBIANCE)):
        chemin = os.path.join(HERE, nom)
        if not os.path.isfile(chemin):
            print("ERREUR : %s absent -- lancer ambiances.py d'abord" % nom)
            sys.exit(1)
        x = lire(chemin)
        if x.shape[0] < n:
            x = np.pad(x, ((0, n - x.shape[0]), (0, 0)))
        x = x[:n]
        melange += appliquer_duck(x, g, duck)
        print("   %-16s : ajoutee (ducking %.0f dB)" % (nom, duck))

    # --- fondus d'ouverture et de fermeture --------------------------------
    nf = int(1.2 * SR)
    melange[:nf] *= np.linspace(0, 1, nf)[:, None]
    melange[-nf:] *= np.linspace(1, 0, nf)[:, None]

    # --- limiteur final ----------------------------------------------------
    pic = float(np.max(np.abs(melange)))
    if pic > 0.97:
        melange *= 0.97 / pic
        print("   limiteur         : -%.1f dB pour tenir sous 0 dBFS"
              % (20 * np.log10(pic / 0.97)))

    sortie = os.path.join(HERE, "cvr01_mix.wav")
    data = (np.clip(melange, -1, 1) * 32767).astype(np.int16)
    with wave.open(sortie, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())

    # --- controles ---------------------------------------------------------
    fautes = []
    mes = rms_db(melange)
    pic_db = 20 * np.log10(max(float(np.max(np.abs(melange))), 1e-9))
    print("-" * 70)
    print("   niveau global    : %.1f dBFS RMS, crete %.1f dBFS"
          % (mes, pic_db))

    if pic_db > -0.2:
        fautes.append("crete a %.2f dBFS : ecretage" % pic_db)
    if mes < -30.0:
        fautes.append("mixage trop faible (%.1f dBFS)" % mes)
    if mes > -12.0:
        fautes.append("mixage trop fort (%.1f dBFS)" % mes)

    # Chaque replique doit ressortir du fond : on compare le niveau du
    # melange pendant la replique a celui des 0,5 s qui precedent.
    sous_mixees = 0
    for t0, dur in evenements:
        i = int(t0 * SR)
        j = int((t0 + dur) * SR)
        avant = melange[max(0, i - int(0.5 * SR)):i]
        if avant.size and j > i:
            if rms_db(melange[i:j]) - rms_db(avant) < 3.0:
                sous_mixees += 1
    if sous_mixees:
        fautes.append("%d replique(s) ne ressortent pas du fond"
                      % sous_mixees)
    else:
        print("   intelligibilite  : 13/13 repliques au-dessus du fond")

    if fautes:
        for f in fautes:
            print("ERREUR : %s" % f)
        sys.exit(1)

    print("   bande son ecrite : %s" % sortie)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
