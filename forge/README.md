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
