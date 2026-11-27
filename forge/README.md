# FORGE — corps sur mesure

Application web installable (PWA) de suivi sportif et nutritionnel, en français.
Ouvre `forge/index.html` via GitHub Pages, puis « Ajouter à l’écran d’accueil ».

- **Programme hybride généré** (2 à 6 séances/semaine, salle / maison / poids du corps) : force, hypertrophie, HIIT, endurance zone 2, gainage.
  Périodisation 12 semaines (accumulation → intensification → réalisation, décharge toutes les 4 semaines).
- **Séance en direct** : charges, reps, chrono de repos automatique (bip + vibration), minuteur d’intervalles HIIT, chrono gainage et cardio,
  double progression (charge proposée selon la séance précédente), records, écran maintenu allumé.
- **Programme modifiable** : séries, reps, repos, ordre, remplacement d’exercice, exercices perso.
- **Progrès** : 1RM estimé, volume, cardio, séances par semaine, records ; poids, mensurations, % masse grasse (US Navy), masse maigre, objectifs ;
  photos avant/après avec comparateur.
- **Nutrition** : cibles calculées (Mifflin-St Jeor / Katch-McArdle), journal par repas, recherche Open Food Facts, scanner code-barres,
  eau, recettes Cookidoo/Thermomix, calculateur.
- **Coach Claude** : via l’abonnement claude.ai (copier/coller du contexte) ou intégré avec une clé API Anthropic
  (adaptation du programme, bilan, menu Thermomix, estimation d’un repas, photo de repas).
- **Appareils** : capteur cardio Bluetooth (Web Bluetooth), import GPX/TCX (Strava, Garmin, Apple Santé via HealthFit…).

Toutes les données restent sur l’appareil (IndexedDB) ; sauvegarde/restauration JSON dans Profil.

## Nouveautés v2
- **Programmes modifiables** : nom, durée, progression par blocs on/off, jours (ordre, copie, suppression), programme vide, bibliothèque « Mes programmes ».
- **Calories par objectif** : perte de poids, sèche, recomposition, maintien, prise de muscle ; glucides plus hauts les jours d’entraînement ; ajustement automatique selon la tendance du poids.
- **Calories par photo** : coach intégré (clé API) ou partage vers l’app Claude (abonnement), correction des grammes avant ajout.
- **Apple Watch / Apple Santé** via l’app Raccourcis (pas, calories actives, FC repos, VFC, poids → FORGE ; journal → Santé).
- **Thermomix / Cookidoo** : import d’une recette Cookidoo par copier-coller, export au format « Mes créations » pour l’envoyer sur le Thermomix.
- **Menu de la semaine** : plats maison ou tout prêts, portions calculées selon les calories du jour, « mangé » → journal, liste de courses et batch cooking.
