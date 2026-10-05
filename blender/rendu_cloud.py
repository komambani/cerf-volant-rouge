#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rend CVR01 sur les runners GitHub, rapatrie, verifie, monte. Une commande.

    python blender/rendu_cloud.py                      # film complet + MP4
    python blender/rendu_cloud.py --debut 601 --fin 720 --tranches 4
    python blender/rendu_cloud.py --samples 64         # plus de qualite, meme cout local : zero
    python blender/rendu_cloud.py --run 1234567890     # reprendre/rapatrier un run existant

Le rendu tourne dans .github/workflows/rendu.yml (Blender 4.5.9 Linux, EEVEE
Next sous Xvfb + Mesa llvmpipe). Ce script ne fait que piloter via `gh` :
aucune cle, aucun compte de ferme, aucune interface graphique.

Il pousse le .blend courant s'il differe du depot (le runner rend ce qui est
sur GitHub, pas ce qui est sur le disque), relance une fois les tranches en
echec, et ne declare le succes qu'apres avoir controle chaque PNG rapatrie
(presence, taille, dimensions lues dans l'en-tete).

Sorties :
    blender/renders/frames_cloud/img_####.png
    exports/CVR01_le_cerf_volant_rouge_cloud.mp4   (plage complete a 100 %)
"""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
DEPOT = "komambani/cerf-volant-rouge"
WORKFLOW = "rendu.yml"
FILM = "blender/cvr01_film.blend"
TOTAL = 1800
LARGEUR, HAUTEUR = 1920, 1080
DEST = os.path.join(ICI, "renders", "frames_cloud")
SORTIE_MP4 = os.path.join(RACINE, "exports", "CVR01_le_cerf_volant_rouge_cloud.mp4")


def gh(*args, check=True):
    r = subprocess.run(("gh",) + args, capture_output=True, text=True,
                       cwd=RACINE, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError("gh %s : %s" % (" ".join(args[:3]), r.stderr.strip()[:400]))
    return r


def git(*args, check=True):
    r = subprocess.run(("git",) + args, capture_output=True, text=True, cwd=RACINE)
    if check and r.returncode != 0:
        raise RuntimeError("git %s : %s" % (" ".join(args[:2]), r.stderr.strip()[:400]))
    return r


def log(msg):
    print(time.strftime("%H:%M:%S ") + msg, flush=True)


def synchroniser_depot():
    """Le runner rend la version GitHub : pousser le .blend et le workflow s'ils ont change."""
    a_pousser = [p for p in (FILM, ".github/workflows/rendu.yml")
                 if git("status", "--porcelain", "--", p).stdout.strip()]
    if a_pousser:
        log("depot : %s modifie(s) localement -> commit + push" % ", ".join(a_pousser))
        git("add", "--", *a_pousser)
        git("commit", "-m", "chore(rendu): version rendue sur runners GitHub", "--", *a_pousser)
    git("fetch", "-q", "origin")
    avance = git("rev-list", "--count", "origin/main..HEAD").stdout.strip()
    if avance != "0":
        log("depot : %s commit(s) locaux -> push" % avance)
        git("push", "-q", "origin", "HEAD:main")
    retard = git("rev-list", "--count", "HEAD..origin/main").stdout.strip()
    if retard != "0":
        raise RuntimeError("le depot distant a %s commit(s) absents en local : "
                           "faire un pull avant de rendre" % retard)


def runs_existants():
    r = gh("run", "list", "--workflow", WORKFLOW, "-L", "20", "--json", "databaseId,status")
    return json.loads(r.stdout)


def lancer(a):
    occupes = [x["databaseId"] for x in runs_existants()
               if x["status"] in ("queued", "in_progress", "waiting", "pending")]
    if occupes:
        raise RuntimeError("un rendu tourne deja (run %s) : attendre ou --run %s"
                           % (occupes[0], occupes[0]))
    avant = {x["databaseId"] for x in runs_existants()}
    gh("workflow", "run", WORKFLOW, "--ref", "main",
       "-f", "debut=%d" % a.debut, "-f", "fin=%d" % a.fin,
       "-f", "tranches=%d" % a.tranches, "-f", "samples=%d" % a.samples,
       "-f", "pourcentage=%d" % a.pourcentage)
    for _ in range(30):
        time.sleep(4)
        nouveaux = [x["databaseId"] for x in runs_existants() if x["databaseId"] not in avant]
        if nouveaux:
            return nouveaux[0]
    raise RuntimeError("le run lance n'apparait pas dans la liste apres 2 min")


def attendre(run_id):
    t0 = time.time()
    dernier = ""
    while True:
        info = json.loads(gh("run", "view", str(run_id), "--json",
                             "status,conclusion,jobs").stdout)
        jobs = [j for j in info["jobs"] if j["name"].startswith("rendu")]
        etats = {}
        for j in jobs:
            k = j["conclusion"] or j["status"]
            etats[k] = etats.get(k, 0) + 1
        ligne = "run %s : %s | %s" % (run_id, info["status"],
                                      ", ".join("%s=%d" % kv for kv in sorted(etats.items())))
        if ligne != dernier:
            log(ligne + "  (%.0f min)" % ((time.time() - t0) / 60))
            dernier = ligne
        if info["status"] == "completed":
            return info["conclusion"], jobs
        time.sleep(60)


def dims_png(chemin):
    with open(chemin, "rb") as f:
        tete = f.read(24)
    if tete[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", tete[16:24])


def rapatrier(run_id, debut, fin, pourcentage):
    os.makedirs(DEST, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="cvr01_dl_", dir=os.environ.get("TMPDIR") or None)
    try:
        log("rapatriement des artefacts du run %s ..." % run_id)
        gh("run", "download", str(run_id), "-D", tmp, "-p", "images-*")
        n = 0
        for racine, _, fichiers in os.walk(tmp):
            for f in fichiers:
                if f.startswith("img_") and f.endswith(".png"):
                    shutil.move(os.path.join(racine, f), os.path.join(DEST, f))
                    n += 1
        log("%d image(s) rapatriee(s) dans %s" % (n, DEST))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    attendu = (LARGEUR * pourcentage // 100, HAUTEUR * pourcentage // 100)
    fautes = []
    for k in range(debut, fin + 1):
        p = os.path.join(DEST, "img_%04d.png" % k)
        if not os.path.isfile(p):
            fautes.append("%04d absente" % k)
        elif os.path.getsize(p) < 20000:
            fautes.append("%04d vide (%d o)" % (k, os.path.getsize(p)))
        elif dims_png(p) != attendu:
            fautes.append("%04d dimensions %s au lieu de %s" % (k, dims_png(p), attendu))
    return fautes


def monter():
    env = dict(os.environ, CVR01_FRAMES=DEST, CVR01_SORTIE=SORTIE_MP4)
    log("montage MP4 (montage.py) ...")
    r = subprocess.run((sys.executable, os.path.join(ICI, "montage.py")), cwd=RACINE, env=env)
    return r.returncode == 0


def main():
    p = argparse.ArgumentParser(description="Rendu CVR01 sur runners GitHub")
    p.add_argument("--debut", type=int, default=1)
    p.add_argument("--fin", type=int, default=TOTAL)
    p.add_argument("--tranches", type=int, default=20, help="runners paralleles, 1-20")
    p.add_argument("--samples", type=int, default=0, help="0 = valeur du .blend (16)")
    p.add_argument("--pourcentage", type=int, default=100)
    p.add_argument("--run", type=int, default=0, help="suivre/rapatrier un run deja lance")
    p.add_argument("--sans-montage", action="store_true")
    a = p.parse_args()
    if not (1 <= a.debut <= a.fin <= TOTAL):
        sys.exit("ERREUR plage %d-%d hors de 1-%d" % (a.debut, a.fin, TOTAL))

    gh("auth", "status")
    t0 = time.time()
    if a.run:
        run_id = a.run
        log("reprise du run %s" % run_id)
    else:
        synchroniser_depot()
        run_id = lancer(a)
        log("rendu lance : run %s, images %d-%d, %d tranche(s)  "
            "https://github.com/%s/actions/runs/%s"
            % (run_id, a.debut, a.fin, a.tranches, DEPOT, run_id))

    conclusion, jobs = attendre(run_id)
    if conclusion != "success":
        echecs = [j["name"] for j in jobs if j["conclusion"] not in ("success", "skipped")]
        log("tranche(s) en echec : %s -> relance unique" % ", ".join(echecs))
        gh("run", "rerun", str(run_id), "--failed")
        time.sleep(20)
        conclusion, jobs = attendre(run_id)
        if conclusion != "success":
            echecs = [j["name"] for j in jobs if j["conclusion"] != "success"]
            log("ERREUR echec persistant : %s" % ", ".join(echecs))
            log("journal : gh run view %s --log-failed" % run_id)
            # on rapatrie quand meme les tranches reussies : rien n'est perdu

    fautes = rapatrier(run_id, a.debut, a.fin, a.pourcentage)
    if fautes:
        log("ERREUR %d image(s) en defaut : %s" % (len(fautes), "; ".join(fautes[:8])))
        sys.exit(1)
    log("controle : %d/%d images presentes et conformes" % (a.fin - a.debut + 1, a.fin - a.debut + 1))

    complet = a.debut == 1 and a.fin == TOTAL and a.pourcentage == 100
    if complet and not a.sans_montage:
        if not monter():
            log("ERREUR montage")
            sys.exit(1)
        log("FILM=OK %s" % SORTIE_MP4)
    log("RENDU_CLOUD=OK en %.0f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\ninterrompu -- le rendu continue sur GitHub ; reprendre avec --run <id>")
        sys.exit(130)
    except Exception as e:
        print("ERREUR %s" % e)
        sys.exit(2)
