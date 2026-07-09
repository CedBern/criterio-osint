# Criterio / Nexome — Revue numérique de debunking (site public)

Ce dépôt sert **uniquement à publier le site** (magazine de fact-checking et
d'investigation géoarchéologique) via **GitHub Pages**.

- **Le site publié** vit sur la branche `main` (dossier `website/`), déployé
  automatiquement par `website/.github/workflows/static.yml`.
- **Les sources & la fabrique du site** (contenu des dossiers, scripts de
  génération) vivent sur la branche `master` :
  - `documents_debunking/` — articles trilingues (fr/es/en) + `*.didactic.json`
  - `publish_dossiers.py` — génère `website/index.html` (magazine multilingue)
  - `generate_illustrations.py` — illustrations SVG à la charte
  - `instagram_carousel/` — déclinaisons réseaux sociaux
  - `.agents/` — orchestration agentique (Loop Engineering) pour la maintenance

## Ce qui n'est PAS ici (volontairement)

L'**application OSINT interne** (« Sherlock », terminal FastAPI privé) a été
sortie de ce dépôt public : elle n'a aucun rôle dans la publication du site et
n'a pas vocation à être exposée. Elle est maintenue dans un dépôt privé séparé.

## Publier une mise à jour du site

1. Éditer/ajouter un dossier dans `documents_debunking/` (voir la checklist du
   skill `nexome-publication` : blocs `\n\n` alignés fr/es/en, `didactic.json`
   valide, images présentes).
2. `python publish_dossiers.py` — régénère `website/index.html`.
3. Committer côté `website/` (branche `main`) → GitHub Pages redéploie seul.

## Licence contenu

Les articles s'appuient sur des sources primaires citées (DOI). Voir `.licenses/`.
