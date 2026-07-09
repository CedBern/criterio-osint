# RÈGLES DE DÉVELOPPEMENT — LOOP ENGINEERING V2 (PARLONS IA)

Ce sous-projet suit l'architecture agentique définie à la racine du dépôt : **lire `../../.agents/AGENTS.md`** (boucle en 4 blocs avec freins et rollback, vérification objective/HITL, routing vers les skills, mémoire à 3 niveaux `memory.md` / `memory_temp.md` / `exchange.md`).

Rappels spécifiques à `website/` :
* Ne jamais supprimer les placeholders `<!-- FEATURED_START/END -->` et `<!-- DOSSIERS_START/END -->` d'`index.html` (utilisés par `publish_dossiers.py`).
* Non-régression obligatoire : sélecteur global de langue, boutons de traduction par paragraphe, glossaire cliquable, quiz, styles de la modal.
* Toute image référencée par un dossier doit exister dans `images/`.
* Encodage UTF-8, HTML/CSS intègres.
