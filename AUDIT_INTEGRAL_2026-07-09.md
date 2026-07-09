# 🔍 AUDIT INTÉGRAL — Nexome (OSINT Terminal + Magazine de debunking)

**Date :** 2026-07-09
**Commit audité :** d32e98f — « Correction bug tests et implementation du role inverse didactique »
**Auditeur (IA/modèle) :** Claude Fable 5 (skill `audit-integral` adapté)
**Périmètre :** audit intégral pré-commercialisation, adapté à Nexome (le skill vise à l'origine Pronos Alliance ; méthodologie et sévérités réutilisées).
**Limites de l'audit :** pas d'exécution réseau réelle des outils OSINT (Tor, scraping) ni de charge ; front-end analysé statiquement (pas de rendu navigateur) ; le sous-dossier `website/` (243 Mo, distribution Python embarquée, dépôt git distinct) n'a pas été audité en profondeur — c'est un artefact de déploiement.

---

## 1. Verdict global

> **GO CONDITIONNEL**

Nexome est un projet sain et déjà mûr côté ingénierie : 53 tests passent, aucun secret n'est commité, la chaîne de fallback LLM est robuste et le front-end échappe correctement le HTML. Rien ne bloque un usage **personnel / interne**. Pour une **commercialisation** (mise entre les mains de tiers payants), trois points doivent être traités : le désalignement des blocs d'un dossier publié (bug visible), la portabilité cassée de l'architecture d'agents (skills gitignorés), et le cadrage juridique RGPD des fonctions OSINT qui ciblent des personnes. Aucun critique de sécurité exploitable n'a été trouvé.

| # | Axe | Note /5 | Bloquants ouverts |
|---|-----|:------:|:-----------------:|
| 1 | Sécurité & secrets | 4 / 5 | 0 |
| 2 | Code, archi & tests | 4 / 5 | 0 |
| 3 | Pipeline de publication | 3 / 5 | 1 (🟠) |
| 4 | Contenu debunking & sourçage | 4 / 5 | 0 |
| 5 | Front-end, perf & a11y | 3.5 / 5 | 0 |
| 6 | Légal, RGPD & OSINT | 2.5 / 5 | 1 (🟠) |
| 7 | Données & intégrité fichiers | 3.5 / 5 | 0 |
| 8 | Ops & déploiement | 3 / 5 | 0 |
| 9 | Architecture agents & skills | 3 / 5 | 1 (🟠) |

**Décompte :** 🔴 Critiques : 0 · 🟠 Majeurs : 4 · 🟡 Mineurs : 6 · 🟢 Observations : 5

---

## 2. Top priorités (ordonné par gravité × effort)

| # | Sév | Finding | Axe | Effort | Action |
|---|-----|---------|-----|--------|--------|
| 1 | 🟠 | Désalignement des blocs fr/es/en (dossier « bâtisseurs ») | Pipeline | S | Ajouter/scinder 1 bloc pour repasser à 37/37/37 |
| 2 | 🟠 | Skills du projet gitignorés → routing cassé au clone | Agents | S | Retirer `.agents/skills/` du `.gitignore` et committer |
| 3 | 🟠 | Fonctions OSINT ciblant des personnes sans cadre RGPD | Légal | M | Mentions légales, base légale, exclusion mineurs, avertissement |
| 4 | 🟠 | Chemin de secret cross-projet en dur (`.minimax-agent`) | Sécurité | S | Retirer le fallback ; n'utiliser que `.env` local / env |
| 5 | 🟡 | `memory_temp.md` (état transitoire) suivi par git | Agents | S | Ajouter au `.gitignore` |
| 6 | 🟡 | `main.py` monolithique (1189 lignes) | Code | M | Découper en modules (tools/, llm/, app) |

---

## 3. Points forts confirmés

- **Tests réels et verts** : 53 tests passent (`pytest`), contre 4 auparavant (cf. commit 573897f). Couvre outils OSINT, génération d'illustrations et publication.
- **Aucun secret commité** : `.env` non suivi par git, aucun `sk-ant-…`/`AIza…` en dur dans les fichiers versionnés. Seule clé locale : `GEMINI_API_KEY` dans `.env` non tracké.
- **Front-end défensif** : `escHtml()` appliqué systématiquement au rendu des cartes ; la synthèse Sherlock échappe `&<>` **avant** d'appliquer le markdown (`templates/index.html:1502`) → pas d'injection HTML via la sortie du LLM.
- **Robustesse LLM** : chaîne de fallback Anthropic → Gemini → LLM local → routage regex autonome (`_smart_route`), l'app reste utilisable même sans clé API.
- **Serveur bien cadré** : liaison `127.0.0.1` uniquement, CORS restreint à localhost, méthodes limitées à GET/POST.
- **Contrat de publication documenté et respecté à 90 %** : `didactic.json` valides, toutes les images référencées présentes dans `website/images/`.
- **Architecture agentique formalisée** (AGENTS.md v2, mémoire 3 niveaux, `opencode.json` avec permissions `ask`) — rare et précieux à ce stade.

---

## 4. Findings détaillés par axe

### Axe 1 — Sécurité & secrets

**🟠 Chemin de secret cross-projet codé en dur**
- **Emplacement** : `main.py:40-42, 68-71, 94-97`
- **Constat** : les trois loaders de clés retombent sur `Path.home()/".minimax-agent"/"projects"/"5"/".env"`. L'app lit donc potentiellement le `.env` d'un **autre** projet de la machine.
- **Risque** : couplage caché à un projet tiers ; si Nexome est distribué/exécuté ailleurs, comportement imprévisible et lecture de secrets non liés à Nexome. Fuite possible de la clé d'un autre projet dans les logs d'erreur.
- **Recommandation** : supprimer ce fallback ; ne conserver que la variable d'environnement et le `.env` local. Effort S.

**🟡 CORS autorise l'origine `"null"`**
- **Emplacement** : `main.py:1156`
- **Constat** : `allow_origins=[…, "null"]`. L'origine `null` est envoyée par les pages ouvertes en `file://` et certains iframes sandbox.
- **Risque** : faible en usage localhost, mais élargit inutilement la surface si l'app est un jour exposée.
- **Recommandation** : retirer `"null"` sauf besoin explicite d'ouvrir le HTML en `file://`. Effort S.

**🟢 Proxy Tor sur port 9150 (Tor Browser), pas 9050 (daemon)** — cohérent avec un usage poste de travail ; le documenter pour éviter les faux « Tor injoignable » en prod serveur.

### Axe 2 — Code, architecture & tests

**🟡 `main.py` monolithique (1189 lignes)**
- **Constat** : config, prompt système, définition des outils, implémentations, adaptateurs Gemini/OpenAI, streaming SSE et app FastAPI dans un seul fichier.
- **Risque** : maintenance et revue plus difficiles ; un autre contributeur (humain ou IA) doit tout charger en contexte — à rebours du principe d'injection courte prôné par AGENTS.md.
- **Recommandation** : découper en `tools.py`, `llm_adapters.py`, `app.py`. Effort M.

**🟢 Suite de tests solide** (`test_osint_tools.py`, `test_generate_illustrations.py`, `test_publish_dossiers.py`) — bon filet de non-régression, à maintenir.

### Axe 3 — Pipeline de publication

**🟠 Désalignement des blocs fr/es/en**
- **Emplacement** : `documents_debunking/le_secret_des_batisseurs.{fr,es,en}.md`
- **Constat** : fr = **37** blocs, es = **36**, en = **36** (découpe sur `\n\n`). `publish_dossiers.py` associe les blocs par index → à partir du bloc manquant, toutes les traductions es/en sont décalées d'un cran. (L'autre dossier, « mirage », est correctement à 39/39/39.)
- **Risque** : sur le site publié, les paragraphes espagnols/anglais d'un article vedette ne correspondent plus au texte français affiché — défaut visible par tout lecteur bilingue.
- **Recommandation** : identifier le bloc surnuméraire du fr (probablement une image ou un titre isolé) et rétablir 37/37/37. C'est exactement le contrôle « compter les blocs » du skill `nexome-publication`. Effort S.

**🟡 Couverture d'article codée en dur**
- **Emplacement** : `publish_dossiers.py:144-145` (`get_cover_image` → toujours `Piramides_de_Guiza.jpg`)
- **Risque** : tout nouveau dossier hérite de la couverture des pyramides ; incohérence visuelle dès le 2ᵉ sujet.
- **Recommandation** : dériver la couverture du 1ᵉʳ `![]` du dossier ou d'un champ `cover` dans `didactic.json`. Effort S.

**🟢 Détection d'erreurs silencieuses** : un `didactic.json` invalide publie sans glossaire/quiz sans alerter — les deux JSON actuels sont valides, mais ajouter un `print` d'avertissement rendrait le pipeline plus sûr.

### Axe 4 — Contenu debunking & sourçage

**🟢 Sourçage exemplaire** : le dossier « bâtisseurs » cite l'étude primaire (Ghoneim et al. 2024, DOI 10.1038/s43247-024-01379-7), chiffres concrets, citation attribuée. Conforme à la philosophie `debunk-dossier`.

**🟡 Vérifier la parité de sourçage du 2ᵉ dossier** — s'assurer que « mirage de la connexion globale » ferme aussi sur une section Sources avec DOI/références vérifiables (non recontrôlé ligne à ligne ici).

### Axe 5 — Front-end, perf & a11y

**🟡 Rendu markdown maison par regex** (`renderFinalAnswerCard`, `templates/index.html:1500-1516`)
- **Constat** : échappement correct puis regex ; robuste pour l'XSS mais fragile pour le markdown complexe (tableaux, listes imbriquées, liens).
- **Risque** : faible (cosmétique) — certaines synthèses riches s'afficheront imparfaitement.
- **Recommandation** : si le besoin grandit, passer à `marked` + `DOMPurify`. Effort M.

**🟢 A11y / perf non mesurées** ici (pas de rendu navigateur) — recommander un passage Lighthouse sur `website/index.html` avant lancement public.

### Axe 6 — Légal, RGPD & OSINT

> Signalement de risque, pas un conseil juridique. Faire valider par un professionnel.

**🟠 Outils OSINT ciblant des personnes sans cadre de conformité**
- **Emplacement** : `main.py` — `airbnb_radar_search` (nom + localisation), `multi_osint_search`, `scrape_mercadolibre`, routage sur nom de personne.
- **Constat** : l'app compile des informations sur des personnes/vendeurs identifiables via Tor, sans mentions légales, base légale, ni exclusion des mineurs. Le prompt système encode aussi un **profil de santé de l'utilisateur** (« 2E (HPI/TDAH) ») en clair (`main.py:149`).
- **Risque** : en usage personnel c'est acceptable ; **commercialisé**, la collecte de données personnelles de tiers déclenche des obligations RGPD/LFPDPPP (Mexique) — base légale, information des personnes, droit à l'effacement — et un risque réputationnel (outil de « profilage »). Le contournement anti-bot (Tor sur MercadoLibre) peut violer des CGU.
- **Recommandation** : (1) décider explicitement du positionnement (outil perso vs produit) ; (2) si produit : mentions légales, base légale documentée, avertissement d'usage licite, exclusion des données de mineurs ; (3) sortir le profil de santé du code source. Effort M. **À faire valider juridiquement.**

### Axe 7 — Données & intégrité fichiers

**🟡 Nom de fichier image corrompu commité**
- **Emplacement** : `instagram_carousel/Articulo 1/¨Paragraphe 2.png` (git l'affiche en octets échappés `\302\250`).
- **Risque** : caractère non-ASCII en tête de nom → problèmes de portabilité cross-OS et d'URL. Cosmétique mais salissant.
- **Recommandation** : renommer proprement. Effort S.

**🟢 UTF-8 respecté** dans les dossiers et JSON ; encodages lus explicitement en `utf-8` dans le code.

### Axe 8 — Ops & déploiement

**🟡 `website/` = 243 Mo avec distribution Python embarquée**
- **Constat** : le sous-projet de déploiement embarque un interpréteur Python complet (`website/Python/…`) et a son propre `.git`. Correctement exclu du dépôt principal (`.gitignore:5-6`).
- **Risque** : lourdeur, tests parasites (les `lastfailed` pointaient vers `website/Python/.../idlelib/…`), confusion sur la source de vérité du site.
- **Recommandation** : documenter que `website/` est un artefact de build ; garder l'exécution des tests scoped hors `website/` (`--ignore=website`). Effort S.

**🟢 Démarrage reproductible** (`START.bat` + `requirements.txt` épinglés) — bon pour un repreneur.

### Axe 9 — Architecture agents & skills

**🟠 Skills du projet non versionnés → portabilité cassée**
- **Emplacement** : `.gitignore:7` (`.agents/skills/`) vs `.agents/AGENTS.md:54-62`
- **Constat** : les 9 fichiers `.agents/skills/*.md` existent en local mais sont **gitignorés** (confirmé via `git check-ignore`). Or l'orchestrateur `AGENTS.md`, lui, est versionné et route vers ces fichiers.
- **Risque** : un clone frais, une autre machine ou une IA collaboratrice reçoit un orchestrateur qui pointe vers des fichiers **absents du dépôt**. Cela contredit l'objectif affiché (« utilisable par toute IA ») et casse le routing dès qu'on sort de cette machine.
- **Recommandation** : retirer `.agents/skills/` du `.gitignore` et committer les skills (ce sont de la doc, pas des secrets). Effort S.

**🟡 `memory_temp.md` suivi par git**
- **Constat** : la mémoire temporaire « auto-nettoyante » est versionnée (`git ls-files` la liste).
- **Risque** : bruit de commits et conflits de merge sur un fichier par nature volatil.
- **Recommandation** : l'ajouter au `.gitignore` (garder `memory.md` et `exchange.md` selon le besoin). Effort S.

**🟢 `opencode.json`** charge `AGENTS.md` et met l'agent `plan` en permissions `ask` (edit/bash) — bon garde-fou.

---

## 5. Checklist GO / NO-GO commercialisation

### 🔴 Bloquant (doit être ✅ pour lancer un produit)
- [x] Aucun secret réel commité
- [x] Pas d'injection HTML/XSS via sortie LLM (échappement vérifié)
- [x] Serveur non exposé (bind 127.0.0.1)
- [ ] Cadre RGPD/LFPDPPP des fonctions OSINT ciblant des personnes (Axe 6)
- [ ] Profil de santé utilisateur retiré du code source
- [ ] Blocs fr/es/en alignés sur tous les dossiers publiés (Axe 3)
- [x] Build/lancement reproductible ; tests critiques passent (53/53)

### 🟡 Souhaitable (améliore mais non bloquant)
- [ ] Skills versionnés pour la portabilité (Axe 9)
- [ ] `memory_temp.md` sorti du versionnement
- [ ] Fallback secret cross-projet supprimé
- [ ] Couverture d'article dynamique
- [ ] `main.py` découpé en modules
- [ ] Passage Lighthouse/a11y sur le site
- [ ] Nom de fichier image corrompu renommé

---

## 6. Plan d'action recommandé

**Avant toute diffusion externe (sprint bloquant, ~½ journée) :**
1. Réaligner `le_secret_des_batisseurs` à 37/37/37 et republier.
2. Retirer `.agents/skills/` du `.gitignore`, committer les skills.
3. Supprimer le fallback `.minimax-agent` et sortir le profil de santé du prompt.
4. Décider du positionnement OSINT (perso vs produit) ; si produit, ouvrir le chantier RGPD.

**Sous 30 jours :**
- `memory_temp.md` gitignoré ; couverture d'article dynamique ; avertissement sur `didactic.json` invalide.
- Passage Lighthouse/a11y ; renommage du fichier image corrompu.

**Backlog qualité :**
- Découpage de `main.py` ; migration éventuelle vers `marked`+`DOMPurify` ; documentation `website/` comme artefact de build ; contrôle de parité de sourçage sur chaque nouveau dossier (automatisable dans `test_publish_dossiers.py`).

---

*Audit conduit selon la méthodologie `audit-integral` (adaptée de Pronos Alliance à Nexome). Les findings de sévérité 🟠 ont été confirmés dans le code/les fichiers (chemin + ligne cités). Points marqués « à faire valider juridiquement » : signalement de risque, non un avis juridique.*
