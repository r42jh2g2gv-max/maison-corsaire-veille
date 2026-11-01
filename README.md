# maison-corsaire-veille

**Corentin**, l'agent de veille concurrentielle de Maison Corsaire.

Chaque semaine, Corentin visite les sites des concurrents, repère ce qui a
changé (prix, nouveautés, messages marketing), complète par des recherches
web et envoie un rapport avec ses recommandations. Sa mission et sa routine
sont décrites dans [CORENTIN.md](CORENTIN.md).

## Installation
```bash
pip install -r requirements.txt
cp competitors.example.json competitors.json   # puis remplir avec vos concurrents
```

Chaque concurrent a les champs suivants :
- `name` : son nom ;
- `instagram` : son compte Instagram ;
- `website` : son site ;
- `pages` : d'autres pages à surveiller (nouveautés, boutique, soldes…) ;
- `notes` : pourquoi on le surveille.

## Utilisation
```bash
python corentin.py competitors  # vérifier la liste
python corentin.py collect      # collecter les changements
python corentin.py report       # rapport des 7 derniers jours
python server.py                # serveur MCP (outils pour Claude)
```

Outils MCP : `list_competitors`, `get_competitor`, `collect_now`,
`add_observation`, `search_observations`, `weekly_report`.

La première collecte prend une « photo » de chaque page. Les changements sont
détectés à partir de la deuxième collecte.

## Tests
```bash
python -m pytest tests
```
