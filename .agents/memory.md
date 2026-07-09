# MÉMOIRE PERSISTANTE — Projet Nexome

> Lue au début de chaque session par tout agent IA. N'y consigner que ce qui a valeur de règle durable : décisions validées par Cédric, critères de succès appris (HITL), pièges découverts. Ne jamais nettoyer ce fichier ; le réorganiser si besoin.

## Décisions validées par l'utilisateur
- Philosophie éditoriale : le debunking remplace le mythe par une découverte plus fascinante ; empathie avec le croyant, jamais de mépris.
- Site : sélecteur global de langue, boutons de traduction par paragraphe, glossaire cliquable et quiz sont des fonctionnalités validées → non-régression obligatoire.
- Public es : espagnol neutre latino-américain (lecteurs de Mérida, Mexique).

## Critères de succès appris (HITL)
- (ajouter ici chaque consigne donnée par l'utilisateur lors d'une revue, au format : contexte → critère)

## Pièges connus du dépôt
- `publish_dossiers.py` associe les blocs fr/es/en par index (`\n\n`) : un bloc en trop décale toutes les traductions suivantes.
- `get_cover_image()` est codé en dur (Piramides_de_Guiza.jpg) : tout nouveau dossier hérite de cette couverture.
- JSON didactique invalide = publication silencieuse sans glossaire/quiz.
- L'article vedette est choisi par mtime du `.fr.md`.
- `.agents/skills/` est gitignoré (`.gitignore:7`) : les skills existent en local mais NE sont PAS versionnés → l'orchestrateur route vers des fichiers absents d'un clone frais.
- `main.py` a un fallback de clé cross-projet (`~/.minimax-agent/...`) et encode un profil de santé utilisateur en clair (main.py:149).
- `main.py` est monolithique (1189 lignes).
- Le front-end échappe correctement le HTML (escHtml + échappement avant markdown ligne 1502) — bon, à préserver.

## Résultat audit 2026-07-09 (AUDIT_INTEGRAL_2026-07-09.md)
- Verdict initial : GO CONDITIONNEL. 0 critique, 4 majeurs, 6 mineurs.

## Corrections post-audit appliquées + vérifiées (2026-07-09)
- Blocs réalignés : 37/37/37 et 39/39/39. ✓
- `main.py` découpé en `config.py` / `llm.py` / `tools.py` ; 53 tests toujours verts, imports OK. ✓
- Fallback secret `~/.minimax-agent` et profil de santé (HPI/TDAH) retirés du code. ✓
- Pages légales ajoutées (`mentions_legales`, `confidentialite`, `cgu`) servies par une route à liste blanche `/{page}` (pas de traversée de chemin). ✓
- Image au nom corrompu renommée ; `memory_temp.md` dé-suivi + gitignoré. ✓
- **DÉCISION UTILISATEUR** : les skills `.agents/skills/` restent HORS git (distribués séparément en .skill). L'orchestrateur AGENTS.md route donc vers des fichiers non présents dans un clone — assumé.
- Reste ouvert (non bloquant) : chantier RGPD à finaliser côté contenu des 3 pages légales + base légale des outils OSINT ciblant des personnes ; validation juridique recommandée.

## Préférences de travail de l'utilisateur
- Réponses concises et directes.
- Skills et documentation du projet en français, portables (utilisables par n'importe quelle IA).
