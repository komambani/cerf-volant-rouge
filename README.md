# CVR01 — Le Cerf-Volant Rouge

Court-métrage animé 2.5D cel-shaded. 75 s, 15 plans, 16:9 1920×1080, 24 i/s.

> Au coucher du soleil, Awa et Tano libèrent un cerf-volant rouge coincé dans un
> manguier, puis le font redécoller.

Pipeline **100 % gratuite** : Blender 4.5 LTS (EEVEE + Line Art) pour la 3D et
les caméras, DaVinci Resolve Studio pour le compositing et l'étalonnage.
Aucun service de génération vidéo payant.

---

## État du projet

| Étape | État |
|---|---|
| Découpage technique V1.1 corrigé | ✅ 24/24 contrôles passés |
| Modèle de données vérifiable | ✅ `doc/cvr01_model.py` |
| Vérificateur automatique | ✅ `doc/verifier.py` |
| Scène Blender + 15 caméras | 🔜 |
| Planches de référence | 🔜 |
| Rendu des 15 plans | 🔜 |
| Montage / étalonnage / son | 🔜 |

## Démarrage rapide

```bash
python doc/verifier.py        # rejoue les 13 défauts de la V1.0 sur le modèle
python doc/generer_doc.py     # régénère le découpage complet en Markdown
```

Le vérificateur sort en code 1 si un seul contrôle échoue : le document ne peut
pas se contredire sans que le dépôt le signale.

---

## Pourquoi un modèle de données et pas un document

Le découpage V1.0 (`doc/source/`) portait 13 défauts, dont 3 bloquants. Presque
tous venaient de la même cause : **la même valeur saisie plusieurs fois à la
main**. L'heure diégétique divergeait entre la fiche et le prompt sur 3 plans ;
les timecodes dépassaient 59 secondes ; la contrainte « sujet 25–65 % » était
recopiée sur 15 échelles de plan où elle était géométriquement impossible.

Ici, `doc/cvr01_model.py` est la **source de vérité unique**. Timecodes, heures,
géométrie de cadre, seeds, prompts et scènes Blender en sont *dérivés*. Une
valeur n'existe qu'une fois, donc elle ne peut plus se contredire.

### Les 13 défauts de la V1.0 et leur correction

| # | Défaut V1.0 | Correction V1.1 |
|---|---|---|
| 1 | **Bloquant.** Les 15 prompts contenaient littéralement `At 2 s: the main event occurs` — texte de substitution jamais remplacé. Le modèle recevait un début, une fin, et un trou au milieu. | Les 15 beats à t=2 s sont décrits (champ `evenement`). |
| 2 | **Bloquant.** Score de fidélité `100 × (1 − écart pondéré / (3 × poids total))` — ni critères ni poids définis. Le gate « IA ≥ 90 % » était inévaluable. | 9 critères pondérés, total 100 (`GRILLE`), échelle d'écart 0–3, fonction `score()` testée. |
| 3 | **Bloquant.** Aucun glossaire. 26 codes (`TPG`, `TRAV-CIR`, `RCOUP`…) non définis ; sections 3, 4, 7 et 11 absentes. | 3 glossaires complets : échelles, mouvements, raccords. |
| 4 | Contradiction interne : « sujet 25–65 % » imposé aux 15 plans. Calcul réel : P001 = 12 %, P009 = 582 %. Un seul plan conforme sur 15. | Chaque échelle porte **sa** bande de contrôle ; distances ajustées ; 15/15 conformes, vérifié. |
| 5 | Heure fiche ≠ heure prompt sur P004, P008, P012. | Heure dérivée de `PROJET["heure_debut"]` + offset. Une seule source. |
| 6 | Timecodes invalides : `00:00:60`, `00:00:65`, `00:00:70`, `00:00:75`. | Fonction `timecode()`. Le film finit à `00:01:15`. |
| 7 | Champ D (dialogue) **absent** — pas « aucun », absent — sur P004, P007, P008, P011, P015. | Présent sur 15/15. 4 répliques ajoutées, 2 plans explicitement muets. |
| 8 | Sections 9–10 et 12 vides sur 14 plans (titre sans contenu). | Générées pour les 15 plans. |
| 9 | Chronologies décoratives : mêmes objets déclarés sur les 15 plans. Le tabouret existait avant son introduction, le dévidoir dans un insert de mains. | Registre d'objets **par plan** : 10 combinaisons distinctes. |
| 10 | P011 : insert 70 mm à 0,8 m = 0,27 m de cadre pour un cerf-volant de 0,75 m. Objet plus grand que le cadre. | Reculé à 2,80 m → 0,96 m de cadre. Vérifié par assertion. |
| 11 | Franglais dans les prompts (`grande depth of field`, `2 m recul en 5 s`) et interdits collés dans le prompt **positif** — ce qui revenait à demander les défauts. | Prompt EN propre + `NEGATIF_EN` isolé (32 interdits). |
| 12 | `GRUE-H` ambigu (haut ou horizontale ?) ; amplitude 2 m alors que l'action dit 1,5 m. | `GRUE-HAUT`, amplitude alignée sur l'action. |
| 13 | Bug de ligature du PDF : `→` sorti en `fi`, `≥` en `‡`. Un copier-coller injectait `gauchefidroite` dans les prompts. | Modèle en texte propre ; contrôle anti-régression. |

Deux bonus trouvés en passant : `OBJ_BENCH` manquait au registre alors que le
décor le décrit, et la cible audio programme (LUFS) n'existait pas.

### Un détail du document d'origine, conservé

Tano (1,34 m) sur un tabouret de 42 cm atteint ≈ 2,21 m — juste sous la branche
à 2,25 m. Son échec en P004 est **physiquement justifié**, et Awa (1,48 m) y
arrive en P008. Involontaire ou non, c'est juste : la contrainte est désormais
explicite dans le modèle (`sujet_bonus_m`).

---

## Structure

```
doc/
  cvr01_model.py     source de vérité unique : 15 plans, bible, glossaires, grille
  verifier.py        rejoue les 13 défauts — exit 1 si un seul échoue
  source/            le PDF V1.0 d'origine, pour archive
blender/             scène, décor, rigs, caméras, scripts de rendu
refs/                planches de référence personnages et décor
renders/             sorties par plan (git-ignoré)
exports/             masters (git-ignoré)
```

## Contraintes de production

Machine : i5-8350U, 8 Go RAM, Intel UHD 620, pas de GPU dédié. Donc **EEVEE
uniquement**, Cycles exclu. Rendu visé : 1 à 3 s/image, soit 30 à 90 min pour
les 1800 images du film.

Conséquence assumée : **animation limitée** (poses tenues, parallaxe, smears),
pas d'interpolation pleine à 24 i/s. C'est la tradition anime, pas un
contournement.

## Licence

Code de pipeline : MIT. Contenu créatif (scénario, personnages, découpage) :
tous droits réservés.
