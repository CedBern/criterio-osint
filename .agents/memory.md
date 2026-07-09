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

## Préférences de travail de l'utilisateur
- Réponses concises et directes.
- Skills et documentation du projet en français, portables (utilisables par n'importe quelle IA).
