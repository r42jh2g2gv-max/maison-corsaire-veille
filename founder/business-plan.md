# Maison Corsaire · Business plan

**Verdict: Not yet**

- ✓ Each bouteille earns $5.12 before fixed costs (20% contribution).
- ✗ Year 1 operating LOSS: $883.
- ✓ 5 of 20 simulated buyers buy (25%, the bar is 25%).

| key number | |
| --- | ---: |
| Price | $25.85 a bouteille |
| Profit margin at plan | -24% per bouteille |
| Break-even | 1 bouteilles a day |
| Year 1 operating profit | $-883 |
| Startup spend | $1,040 |
| Cash needed before it pays for itself | $1,923 |
| Startup money earned back | not in year 1 |
| Buyer panel | 5 buy · 15 pass |

## The idea

- Ce que c'est : une marque de rhum arrangé artisanal (rhum agricole HSE AOC Martinique macéré avec purées de fruits et épices, filtré). Entreprise créée en janvier 2026 (EI, Rosny-sur-Seine), recettes en test, packaging et charte prêts, pas encore de vente au public. Une première commande : 5 coffrets de 3 bouteilles pour Noël.
- Pour qui : deux clientèles. Les particuliers qui achètent sur les marchés, les salons et en local. Les professionnels : cavistes, bars et restaurants.
- Ce qu'elle vend, à quel prix : trois cuvées « Trois vents » en 70 cl (Noroît cassis-bergamote-vanille, Zéphyr coco-citron vert-tonka, Suroît passion-orange-caramel), 33 € TTC au public, 22 € HT aux professionnels.
- Où et comment : vente directe sur les marchés, les salons et en local, plus la revente par les cavistes, bars et restaurants. Pas de vente en ligne prévue pour l'instant. Zone : les Yvelines (78), en Île-de-France.
- Ce qui le distingue (selon le fondateur) : un rhum arrangé moins sucré, aux arômes francs et assumés.
- Budget et contraintes : budget non communiqué. Statut d'entrepositaire agréé à régler (piste : façonnage chez un professionnel agréé). Vente sur les marchés à vérifier (art. L3322-6 CSP). Détails : founder/drive-notes.md. Les concurrents cités par le fondateur sont Rhum Ti'ced, Mama Sama et Arhumatic.

## Summary

**Maison Corsaire** fait trois rhums arrangés artisanaux, la gamme « Trois vents » (Noroît, Zéphyr, Suroît), à partir de rhum agricole AOC Martinique, dans les Yvelines. Ils sont vendus 35 € la bouteille et 95 € le coffret de trois. La cible : les particuliers qui veulent goûter avant d'acheter ou qui cherchent un cadeau, puis les bars et restaurants créoles du nord des Yvelines.

**Verdict : pas encore rentable.** Ce verdict est calculé par `compile.py` à partir des chiffres, pas décidé à la main. Les trois chiffres qui le fondent :
- chaque bouteille laisse **5,12 €** une fois payés ses propres coûts (environ 8 € à 35 € en vente directe) ;
- il faut vendre **316 bouteilles par an** pour couvrir les frais, alors que l'objectif est de 100 à 200 ;
- l'année 1 perd **883 €** avec 144 bouteilles, et environ 1 900 € en comptant le démarrage.

La plupart des coûts sont estimés. Le chiffre qui pèse le plus est le prix du façonnage : estimé à 4 €, il serait plutôt de 3,50 € selon mon calcul. S'il descend à 2,50 € et que tu vends 200 bouteilles en direct à 35 €, l'année 1 devient positive (environ +290 €).

**Sur quoi le panel et le conseil sont d'accord :** sans une différence prouvée, la marque n'est qu'un rhum arrangé de plus. Et ce qui fait acheter, c'est **la dégustation**.

**Là où ils divergent :** le conseil (lens Offres) voulait enrichir l'offre. Le retest a donné **15 % d'acheteurs avec l'offre enrichie, contre 25 % avec la première**. Le plan s'appuie sur la première version, la plus simple, plus le coffret. Côté cadeaux, le panel ne convainc personne, mais le seul vrai client a acheté 5 coffrets.

**Le plus grand risque :** la production. Sans entrepositaire agréé ni façonnier signé avant le 9 novembre, les coffrets ne seront pas prêts pour Noël. Juste derrière viennent la vente sur les marchés, peut-être interdite (article L3322-6 du Code de la santé publique), et le taux de sucre de tes recettes (environ 115 à 180 g/L), qui ne permet pas d'afficher « moins sucré » pour l'instant.

**Ce qu'il faut pour démarrer :** environ 1 900 € de trésorerie (estimation du CFO), un devis de façonnage signé, et deux ventes privées les 14 et 28 novembre comme premier test réel.

**À faire cette semaine :** obtenir un devis écrit de façonnage (Éric ou KEVAS) et l'accord écrit des douanes sur ce schéma, avant le vendredi 30 octobre.

*Le panel est fait d'acheteurs simulés, et les chiffres sont des projections. De vrais clients et de vrais devis doivent les confirmer. Ce n'est pas un conseil financier, juridique ou fiscal.*

## What the board said

### Le vote

**2 FUND IF, 1 PASS. Note moyenne : 3,7/10.**

| lens | note | vote |
| --- | ---: | --- |
| Offres | 4/10 | FUND IF |
| Monopole | 3/10 | PASS |
| Produit | 4/10 | FUND IF |

Mémos complets : `founder/board/offers.md`, `monopoly.md`, `product.md`.

### Les risques soulevés par plus d'un membre

1. **Aucune différence identifiée (les 3 membres).** Rien ne dit pourquoi choisir Maison Corsaire plutôt que Rhum Ti'ced, Mama Sama ou Arhumatic. Sans goût signature, recette introuvable ailleurs ou secret, le produit devient une commodité et la seule arme qui reste est le prix.
2. **Une marge inconnue (les 3).** Le coût de revient d'une bouteille (rhum, fruits, bouteille, étiquette, droits d'accise) et le prix aux professionnels ne sont pas fixés. Il est impossible de dire si 30 à 40 € laisse de la marge, surtout après la remise caviste.
3. **Trop de fronts à la fois (Produit et Monopole).** Particuliers et professionnels, marchés, salons, cavistes, bars et restaurants : chaque canal demande une expérience et un prix différents, et la vente directe coûte du temps à chaque bouteille.
4. **Aucune preuve (Offres et Produit).** Pas de recette arrêtée, pas de production, pas de client. Un caviste n'a aucune raison de donner une place en rayon à une marque inconnue.
5. **La production et la réglementation pas encore cadrées (Produit et Monopole).** L'approvisionnement en rhum, le labo ou la sous-traitance, le statut d'entrepositaire agréé, les accises et l'étiquetage ne sont pas connus.

### Les désaccords

- **Le lens Monopole vote PASS.** Selon lui, aucune barrière n'empêche un copieur de faire pareil au sixième mois. Il changerait de vote avec un secret vérifiable et un petit marché nommé à dominer.
- **Les lens Offres et Produit jugent qu'un produit de plaisir peut marcher** sans monopole s'il a une offre forte et une expérience maîtrisée. La dégustation sur place est leur atout commun.
- **Le lens Offres veut ajouter** des éléments autour de la bouteille (coffret, dégustation, édition limitée). **Le lens Produit veut retirer** : une ou deux recettes, un client, un canal. Les deux se concilient : une offre riche, sur un périmètre étroit.

### Les conditions, à cocher au fil du parcours

- [ ] **Une promesse en une phrase**, avec un goût signature, qui distingue Maison Corsaire des trois concurrents sur autre chose que le prix → `/founder-competitors`, puis `/founder-consumer`
- [ ] **Un secret ou un avantage vérifiable** : recette, ingrédient, source de rhum, ancrage local → fondateur, puis `/founder-competitors`
- [ ] **Un segment principal choisi** (particulier plaisir, cadeau ou pro CHR) et **un canal de lancement**, le reste mis de côté jusqu'aux premières ventes → `/founder-consumer`, `/founder-marketing`
- [ ] **Un petit marché nommé** (une ville, une région) où viser une part dominante → fondateur, puis `/founder-competitors`
- [ ] **Une ou deux recettes au lancement**, pas plus → `/founder-offer`
- [ ] **Une pile d'offre** : au moins un élément au-delà de la bouteille qui coûte peu et vaut beaucoup, plus une garantie pour les pros (reprise des invendus, support de dégustation) → `/founder-offer`
- [ ] **Un coût de revient par bouteille, accises comprises**, compatible avec 30 à 40 € public et un prix pro viable → `/founder-cfo`
- [ ] **Un coût d'acquisition des 100 premiers clients** qui laisse une marge positive → `/founder-consumer`, `/founder-cfo`
- [ ] **La production et la réglementation validées** (statut, accises, étiquetage, approvisionnement) avant toute promesse commerciale → `/founder-ops`
- [ ] **Un parcours client écrit** de bout en bout pour le canal choisi, avec un responsable pour chaque passage de relais → `/founder-ops`, `/founder-launch`

### La version la plus forte que le conseil voit

Ce n'est pas tout à fait ce qui a été présenté. La version la plus forte de Maison Corsaire n'est pas « un rhum arrangé de plus, vendu partout à tout le monde ». C'est **une marque locale à forte identité, avec une ou deux recettes signature, lancée sur un seul territoire et un seul canal**. Les marchés et les salons servent d'abord à faire goûter, à apprendre et à prouver la demande. Les ventes obtenues en dégustation deviennent ensuite l'argument pour entrer chez quelques cavistes et bars de la même zone. Le nom « Corsaire » donne une histoire (le récit maritime et pirate, l'édition limitée « butin ») qui peut porter une offre cadeau et des éditions saisonnières. Mais une histoire ne remplace pas un goût que l'on redemande : c'est ce goût qu'il faut prouver en premier. Si aucune différence réelle n'apparaît face aux trois concurrents, le lens Monopole a raison et il vaut mieux le savoir avant d'acheter la première cuve.

## The competition

Recherche du 27 octobre 2026, à partir de sources publiques seulement. Limite importante : dans cet environnement, les sites des marques et des revendeurs n'ont pas pu être ouverts directement (le réseau bloque l'accès). Tous les faits ci-dessous viennent des extraits renvoyés par un moteur de recherche, et chacun a son lien. Les prix sont des relevés à des dates différentes : vérifie-les avant de t'en servir. Le détail ligne par ligne est dans `founder/competitors.csv`.

### 1. Qui est là

| concurrent | type | où / canal | prix 70 cl | ce qui le distingue |
| --- | --- | --- | ---: | --- |
| [Les Rhums de Ced (Ti Ced)](https://www.vinatis.com/maisons/les-rhums-de-ced) | direct | Loire-Atlantique ; cavistes ([listé chez Nicolas](https://nicolas.com/en/OTHERS/PUNCH-RHUM-SCHRUBB-TI-CED/p/498418.html)) | [29,90](https://www.extime.com/en/paris/product/les-rhums-de-ced-ananas-victoria-101628516) à [36,90 €](https://www.rhumattitude.com/en/cave/les-rhums-de-ced-ti-arrange-ananas-passion-bio-21/) | Fruits frais de saison, rhum agricole AOC, médailles. **Gamme « Les Délicats », lancée en 2025, [moins alcoolisée et moins sucrée](https://www.rhumattitude.com/en/cave/ti-ced-les-delicats-orange-citron-18/)** |
| [Mama Sama](https://mama-sama.fr/mama-sama-rhums-arranges-artisanaux-bordeaux/nos-rhums-arranges-planteurs-mama-sama-bordeaux/) | direct | Mérignac (33) ; épiceries fines, cavistes | [38,00](https://boutique.vinotheque-troyes.com/a-base-de-rhum/4055-rhum-arrange-mama-sama-caneles-de-bordeaux-70-cl-32-3770018228099.html) à [39,90 €](https://mille-et-une-bieres.fr/saint-memmie/nos-spiritueux/42226-rhum-arrange-mama-sama-cannele-bordelais-70cl-32--3770018228099.html) | Ancrage local fort (le [Canelé](https://www.rhumattitude.com/en/cave/mama-sama-canele-32/)), rhum de Marie-Galante, [sirop de sucre roux maison](https://mama-sama.fr/mama-sama-rhums-arranges-artisanaux-bordeaux/nos-rhums-arranges-planteurs-mama-sama-bordeaux/) |
| Arhumatic | direct | France ; cavistes, sites spécialisés | [32,90](https://www.rum-x.com/rums/9368/arhumatic-menthe) à [48,90 €](https://www.rhumattitude.com/en/cave/arhumatic-poire-rotie-poivre-piperata-pira-28) | Recettes de « mixologue » (poire rôtie-poivre, ananas rôti-basilic), base rhum Damoiseau ; [créée en 2014](https://punchdrink.com/articles/rhum-arrange-caribbean-flavored-rum-arhumatic/) |
| [La Fabrique de l'Arrangé](https://www.excellencerhum.com/en/911_la-fabrique-de-l-arrange) | direct | **Île-de-France** (ville non précisée) | non trouvé | Rhum de Martinique ; gamme [« Signatures » à 45°](https://www.rhumattitude.com/en/cave/la-fabrique-de-larrange-signatures-poire-et-cacao-torrefie-45/) ; adossée à un groupe (rhums HSE) |
| [KEVAS](https://www.salon-agriculture.com/en/recherche/exhibitor/KEVAS) | direct | **Coubert (77)**, Salon de l'Agriculture | non trouvé | Rhum de La Réunion, fruits et épices |
| [Rhum & KO](https://www.rhumattitude.com/en/marque/rhum-ko/) | direct | sites spécialisés | non trouvé | **Se présente comme « peu sucrés et légèrement épicés »** |
| [Isautier Arrangé](https://www.promocatalogues.fr/offres/isautier/carrefour) | indirect | grande distribution | [21,90 €](https://www.promocatalogues.fr/offres/isautier/carrefour) (Carrefour, déc. 2025) | Prix bas, partout |
| [Isautier Arhumatik](https://www.rhumattitude.com/en/cave/isautier-arhumatik-passion-24) | indirect | grande distribution | [23,11 €](https://www.promocatalogues.fr/offres/isautier/carrefour) (Carrefour) | Jus et pulpes de fruits, 24°. À ne pas confondre avec Arhumatic |
| [Rivière du Mât Arrangé](https://www.rum-x.com/rums/5560/riviere-du-mat-arrange-ananas-caramelise) | indirect | grande distribution | non trouvé | Grande marque réunionnaise |
| [Rhum arrangé maison](https://www.demotivateur.fr/food/rhum-arrange-12702) | substitut | chez soi | rhum blanc + fruits | Le plus gros « concurrent » : beaucoup de gens le font eux-mêmes |

Autres substituts pour la même occasion (offrir ou partager une bouteille à l'apéritif) : le punch ou le planteur, et les autres spiritueux artisanaux offerts en cadeau (gin, whisky). Je ne les ai pas chiffrés.

**Dans les Yvelines mêmes, je n'ai trouvé aucun producteur de rhum arrangé artisanal** ([recherche](https://rumx.com/en/knowledge/rhum-arrange/)). Les deux producteurs franciliens trouvés sont La Fabrique de l'Arrangé (ville non précisée) et KEVAS (Seine-et-Marne). L'absence de résultat n'est pas une preuve : il peut exister de petits producteurs sans présence en ligne. À vérifier sur les marchés.

### 2. La fourchette de prix (70 cl, rhums arrangés artisanaux)

Sur 12 prix publics relevés pour Ti Ced, Mama Sama et Arhumatic :

- **Plus bas : 29,90 €** (Ti Ced). Les promotions descendent à 28,80 € (Mama Sama chez [Cashvin](https://www.cashvin.com/produit/mama-sama-canele-bordelais/)).
- **Médiane : environ 37,50 €.**
- **Plus haut : 48,90 €** (Arhumatic chez Rhum Attitude).
- **Grande distribution : environ 22 €** (Isautier, Arhumatik).

Ta cible, 30 à 40 €, est **en plein cœur du marché artisanal**. Elle ne laisse pas de place pour se distinguer par le prix, ni vers le bas ni vers le haut.

### 3. La carte de positionnement

Deux axes qui comptent pour cet acheteur : **le niveau de sucre** (doux et liquoreux, ou sec et aromatique) et **la proximité** (une marque d'ici, que l'on rencontre, ou une marque nationale vendue en ligne et en rayon).

```
                        PROXIMITÉ (marque locale, rencontrée)
                                     ^
                                     |
                       Mama Sama     |
                   (ancrage Bordeaux,|
                     sucre roux)     |     [ PLACE LIBRE ]
                                     |     local Yvelines
                    KEVAS (77)       |     + moins sucré
                                     |     + arômes francs
DOUX / SUCRÉ  <----------------------+----------------------->  SEC / AROMATIQUE
                                     |
       Isautier                      |          Ti Ced Les Délicats
       Rivière du Mât                |          Rhum & KO
       Arhumatik                     |
                                     |   Arhumatic
          Ti Ced (gamme classique)   |   La Fabrique (Signatures 45°)
                                     |
                                     v
                        MARQUE NATIONALE (en ligne, en rayon)
```

Les positions sur l'axe du sucre sont des estimations tirées des descriptions et des avis cités plus bas. Aucune marque ne publie son taux de sucre dans ce qui a été trouvé.

### 4. Ce que leurs clients reprochent

Les avis sont **minces** : très peu d'avis clients sur les marques artisanales sont accessibles, et aucun thème n'atteint trois avis sur une même marque artisanale. À lire comme des pistes, pas comme des preuves.

1. **Trop sucré (le thème le plus net, mais visé surtout à la grande distribution).**
   - Rivière du Mât : « Comme toute cette gamme, ce rhum arrangé est malheureusement beaucoup trop sucré. » ([RumX](https://www.rum-x.com/rums/5560/riviere-du-mat-arrange-ananas-caramelise))
   - Isautier : des commentaires parlent de versions « blindées de sucre » et d'un café-vanille « archi sucré et écoeurant » ([forum HardWare.fr](https://forum.hardware.fr/hfr/Discussions/Cuisine/rhum-arrange-sujet_16785_5.htm)) ; « vraiment trop sucré » pour le Gingembre Citron ([RumX](https://www.rum-x.com/rums/2058/isautier-arrange-gingembre-citron)).
   - Une critique note que les arrangés à la vanille sont « parfois écoeurant, parce que trop sucré » ([macommune.info](https://www.macommune.info/jai-teste-rhums-arranges-delis/)).
2. **Une note faible pour Mama Sama**, sur un seul avis : 4,3/10 sur la Trilogie Vanille ([RumX](https://www.rum-x.com/rums/13304/bellevue-mama-sama-larrange-trilogie-vanille)). Thème mince.
3. **Ti Ced est bien noté** : 16,1/20 sur 12 avis ([Vinatis](https://www.vinatis.com/maisons/les-rhums-de-ced)). Aucun reproche récurrent n'a été trouvé.
4. **Trop dilué** : un voyageur signale un arrangé trop coupé à l'eau ([Routard](https://www.routard.com/forums/t/rhum-arrange-coupe-a-leau/18244)). Thème mince.

Pour Arhumatic, KEVAS, La Fabrique et Rhum & KO, je n'ai trouvé aucun avis client.

### 5. La place libre

**Ta différence (« moins sucré, arômes assumés ») répond à la plainte la plus répétée du marché, mais elle n'est plus neuve.** Ti Ced a lancé en 2025 sa gamme « Les Délicats », avec « moins de sirop de sucre de canne », et Rhum & KO se présente déjà comme « peu sucrés ». Dire seulement « moins sucré » ne suffira pas.

Ce que personne ne semble faire, d'après ce qui a été trouvé :

1. **Une marque de rhum arrangé des Yvelines.** Aucun producteur trouvé dans le 78. Mama Sama montre que l'ancrage local marche (le Canelé de Bordeaux, vendu dans une [épicerie historique bordelaise](https://www.echoppe-delalune-bordeaux.com/product/rhum-arrange-au-cannele/)). Un équivalent yvelinois serait un ingrédient ou un récit du 78 (pomme ou poire du Vexin et de la plaine de Versailles, miel local, l'histoire « corsaire ») : c'est une piste à vérifier, pas un fait.
2. **Le sucre écrit sur l'étiquette.** Aucune marque trouvée n'affiche son taux de sucre en g/L. Le chiffre sur la bouteille (« 40 g/L » par exemple, contre un arrangé classique) rendrait la promesse vérifiable au lieu d'être un slogan. Tu dois d'abord mesurer et comparer tes propres recettes. `/founder-ops` dira ce qu'impose la réglementation de l'étiquetage.
3. **La dégustation en face à face, sur un territoire précis.** Les marques nationales vendent en rayon et en ligne. Sur un marché des Yvelines, tu peux faire goûter, et le « moins sucré » se prouve en une gorgée, ce que la page d'un site ne peut pas faire.

Ces trois points ensemble forment une position : **le rhum arrangé des Yvelines, peu sucré, avec le sucre écrit sur l'étiquette, que l'on goûte avant d'acheter.**

### 6. La menace

- **Ti Ced** est le plus dangereux. Il a déjà la gamme moins sucrée, des médailles, de bons avis et une présence chez les cavistes (dont [Nicolas](https://nicolas.com/en/OTHERS/PUNCH-RHUM-SCHRUBB-TI-CED/p/498418.html), une chaîne présente partout). Un caviste des Yvelines qui veut un arrangé moins sucré a déjà une réponse.
- **La Fabrique de l'Arrangé** est francilienne et adossée à un groupe. Elle pourrait jouer la carte « Île-de-France » plus vite que toi.
- **N'importe quel artisan** peut écrire « moins sucré ». Ce qui ne se copie pas facilement : une recette à base d'ingrédients du 78, des relations avec les marchés et les cavistes locaux, et une clientèle qui t'a rencontré.

### Questions ouvertes pour la suite

- Quel taux de sucre visent tes recettes, et quel est celui des concurrents ? Il faut le mesurer, aucune source ne le donne → toi, puis `/founder-ops`.
- Les cavistes des Yvelines ont-ils déjà Ti Ced ou d'autres arrangés en rayon ? Il faut une visite de 5 à 10 caves → à faire sur le terrain.
- Les prix de La Fabrique de l'Arrangé, KEVAS et Rhum & KO n'ont pas été trouvés.
- Prochains salons locaux : le [Salon des Vins et des Saveurs de Jouy-en-Josas](https://agenda-des-sorties.com/detail.php?id=344015), les 21 et 22 novembre 2026, avec 40 exposants. C'est le terrain pour voir la concurrence en vrai et repérer les organisateurs.

## The buyer panel

**5 buy · 15 pass** (25% buy) out of 20 simulated buyers. Seed 78, so the same cards can be dealt again.

These are simulated buyers, not customers. Use this to find objections and weak spots, then confirm the big ones with real people before you spend.

### By segment

| group | buyers | buy rate |
| --- | ---: | ---: |
| Jeune retraité | 5 | 40%  (thin) |
| Jeune actif | 6 | 33%  (thin) |
| Cadre ou parent actif | 9 | 11% |

### By buying behaviour

| group | buyers | buy rate |
| --- | ---: | ---: |
| Flâneur de marché | 4 | 75%  (thin) |
| Évite le sucre | 3 | 67%  (thin) |
| Cherche un cadeau | 5 | 0%  (thin) |
| Amateur de rhum | 3 | 0%  (thin) |
| Prix d'abord | 3 | 0%  (thin) |
| Fait son arrangé maison | 2 | 0%  (thin) |

### By income

| group | buyers | buy rate |
| --- | ---: | ---: |
| $45,000 to $86,000 | 7 | 43%  (thin) |
| under $45,000 | 6 | 33%  (thin) |
| $86,000 and up | 7 | 0%  (thin) |

### Why they pass

| reason | buyers | in their words |
| --- | ---: | --- |
| price | 8 | "35 euros la bouteille, c'est presque le double de ce que je paie en grande surface, et je sais faire macérer des fruits dans un rhum blanc moi-même pour bien moins cher. Je goûterai peut-être au stand, mais je repartirai sans." (P003) · "Je goûterais volontiers sur le stand, et si c'est bon ça peut me plaire sur le moment, mais 35 euros pour un rhum arrangé avec mes revenus, c'est trop. À ce prix je préfère m'acheter un vrai rhum vieux." (P006) |
| quality | 3 | "Je l'offrirais, je ne le boirais pas moi-même, et mes amis aiment le rhum arrangé bien doux et fruité. Un rhum moins sucré, j'ai peur que ça fasse fort et sec, et à 35 euros je ne veux pas offrir quelque chose qui reste au fond du placard." (P001) · "J'achète du rhum arrangé pour l'offrir, et les gens à qui je l'offre aiment justement le côté doux et fruité. Un rhum moins sucré, je crains qu'il paraisse fort et sec, et je ne vais pas prendre le risque sur un cadeau à 35 euros sans occasion précise ce mois-ci." (P008) |
| trust | 2 | "Je ne connais pas cette marque et on ne me dit pas quel rhum il y a dans la bouteille. Je goûterais volontiers sur le stand, mais 35 euros pour un arrangé inconnu, avec ma retraite, je préfère acheter un bon agricole que je connais ou faire mon arrangé moi-même." (P002) · "Quand j'offre une bouteille, je veux que l'hôte reconnaisse ce qu'il reçoit. Un rhum arrangé dont personne n'a entendu parler, à 35 euros, c'est un pari risqué pour un cadeau, même si je l'ai goûté sur le stand." (P010) |
| habit | 2 | "Je fais mes propres bocaux avec un rhum blanc à 15 euros et des fruits, et j'en ai toujours deux ou trois qui macèrent à la maison. Je goûterais volontiers au stand par curiosité, mais 35 euros pour quelque chose que je sais faire, non." (P011) · "Je fais mon propre arrangé avec du rhum blanc et des fruits, et j'ai déjà une bouteille entamée à la maison. Je goûterais volontiers au stand par curiosité, mais 35 euros pour quelque chose que je fais moi-même, non." (P017) |

### Why they buy

| reason | buyers | in their words |
| --- | ---: | --- |
| quality | 5 | "D'habitude je fais mon rhum arrangé moi-même parce que ceux du commerce sont écoeurants, mais si je goûte sur le stand et que c'est vraiment peu sucré, j'en prends une bouteille comme cadeau de fin d'année. Pour moi ce serait un cadeau, pas pour ma consommation : à ce prix-là je continue à faire le mien." (P004) · "Je ne connais pas la marque, mais si je goûte sur le stand et que c'est vraiment moins sucré et franc, je craque pour une bouteille à sortir à l'apéro du week-end avec les amis. À 35 euros, c'est un coup de cœur que je peux me permettre." (P005) |

### What would flip a no

- Le goûter sur le stand et le trouver doux et rond malgré tout, avec une jolie bouteille ou un coffret cadeau, juste avant un anniversaire ou les fêtes.
- Que le producteur me dise clairement quel rhum agricole il utilise et d'où il vient, et qu'au goût sur le stand ce soit vraiment franc et peu sucré ; là je pourrais en prendre une pour offrir.
- Un format plus petit autour de 15-20 euros pour offrir, ou une dégustation qui me prouve que c'est vraiment meilleur que ce que je fais moi-même.
- Une petite bouteille de 20 ou 35 cl autour de 15 euros, pour craquer sur le stand sans me ruiner.
- Goûter sur le stand et trouver ça rond et fruité, pas brûlant, juste avant un anniversaire ou un dîner, avec une jolie présentation cadeau.
- Le goûter sur le stand et le trouver vraiment rond et agréable, juste avant un anniversaire ou les fêtes, avec une jolie bouteille qui fait cadeau.
- Un coffret ou un emballage cadeau soigné avec une petite carte qui raconte la maison, et une dégustation sur le stand qui me plaise vraiment juste avant un dîner ou un anniversaire.
- Une association fruits-épices vraiment originale que je ne saurais pas reproduire, à offrir en cadeau, autour de 25 euros.
- Savoir que la base est un vrai rhum agricole identifié (distillerie nommée) et que la dégustation me bluffe vraiment, ou un format plus petit autour de 20 euros pour essayer ou offrir.
- Savoir que la base est un vrai rhum agricole AOC Martinique nommé sur l'étiquette, avec un prix autour de 25-28 euros, ou un format 35 cl pour offrir.
- Une teneur en sucre précise affichée sur la bouteille, vraiment basse, et une dégustation qui confirme, avec un prix autour de 25 euros.
- Un vrai coffret ou un emballage cadeau soigné inclus, avec une histoire locale à raconter, ou une petite bouteille de 35 cl autour de 20 euros pour offrir sans trop dépenser.

Buyers say they would buy **1.0 times** in the first month on average.

20 buyers gave all four price answers. Run founder-pricing's van_westendorp.py on the answers folder.

## Pricing

### Ce que disent les trois sources

| source | ce qu'elle dit |
| --- | --- |
| Panel (20 acheteurs simulés) | Fourchette acceptable de 15 à 35 €, point d'indifférence vers 25 €. Prix médians : « cher » à 30 €, « trop cher » à 40 €. 33 € se situe dans le haut de la fourchette. (`founder/pricing-curve.md`) |
| Concurrents (prix publics réels) | Les arrangés artisanaux 70 cl se vendent de 29,90 à 48,90 €, médiane environ 37,50 €. Mama Sama est entre 38 et 39,90 €, KEVAS entre 37 et 45 € (Drive). Isautier est à environ 22 € en grande surface. (`founder/competitors.md`) |
| CFO | Coût d'une bouteille : environ 20,73 € HT, dont 17,55 € de coûts directs et 3,18 € de cotisations. À 33 € TTC, elle laisse 6,57 €. À 22 € HT chez un pro, 1,74 €. (`founder/cfo.md`) |

Les acheteurs simulés trouvent 33 € cher, mais le vrai marché vend plus cher que ça. Quand les deux se contredisent, les prix réels comptent plus qu'un panel simulé. Le panel dit surtout autre chose : **une marque inconnue doit justifier son prix** par la dégustation, l'étiquette (rhum AOC Martinique écrit dessus, sucre mesuré) et un bel objet à offrir.

### 1. Le prix public

**Je recommande 35 € TTC** (29,17 € HT) pour la bouteille de 70 cl, au lieu de 33 €.
- Ça reste sous la médiane des concurrents (37,50 €) et sous KEVAS (37 à 45 €).
- C'est le haut de la fourchette du panel, à justifier par la dégustation et l'étiquette.
- La marge en vente directe passe d'environ 6,57 € à environ 8,03 € par bouteille. Calcul : 29,17 € moins 17,55 € de coûts directs, moins 3,59 € de cotisations.

Si tu préfères garder 33 €, c'est défendable : c'est un prix d'entrée pour une marque nouvelle. Mais chaque bouteille te rapporte alors environ 1,46 € de moins.

### 2. Le problème du prix pro

**Un caviste vend environ deux fois son prix d'achat HT.** Si tu lui vends à 22 € HT, il affichera la bouteille entre 40 et 47 € TTC, alors que tu la vends toi-même 33 €. Il ne te suivra pas. Et à 22 € HT, il ne te reste que 1,74 € par bouteille.

Le prix pro et le prix public ne peuvent pas tenir ensemble à ces coûts. Il y a deux façons d'en sortir :
- **Les bars et restaurants**, qui servent au verre. Ils ne revendent pas la bouteille à côté de toi, donc il n'y a pas de conflit de prix. Leur vendre autour de 22 à 24 € HT reste possible si le façonnage descend à environ 2 €.
- **Les cavistes plus tard**, une fois le coût de revient baissé, avec un prix public aligné vers 39 à 42 € TTC dans leur boutique. Pour l'instant, pas de cavistes.

### 3. L'échelle de prix (à tester, rien n'est encore chiffré)

| niveau | produit | prix indicatif | à quoi il sert |
| --- | --- | ---: | --- |
| Essai | Flacon de 20 cl | 12 à 14 € TTC | La demande n°1 du panel : essayer ou offrir sans risque. **Coût à chiffrer** avant d'y aller : le flacon et son habillage coûtent proportionnellement plus cher. |
| Cœur | Bouteille de 70 cl | 35 € TTC | Le produit principal. |
| Cadeau | Coffret « Trois vents », 3 × 70 cl | environ 95 € TTC | Ton seul client réel a acheté des coffrets. Le prix fait environ 10 % de moins que trois bouteilles, et le coffret donne une histoire à offrir. Coût du coffret à chiffrer. |

### 4. L'offre de lancement

**Pas de remise.** Le panel n'en demande pas, et elle habituerait les clients à attendre les promotions. Mieux vaut un avantage réel et daté : par exemple, le coffret commandé avant le 10 décembre livré à temps pour Noël, ou la gravure d'un prénom sur le bandeau. `/founder-offer` le détaillera.

### 5. Ce qu'il faut tester avec de vrais acheteurs

- **33 € ou 35 €** : propose les deux prix à des groupes différents de ton entourage et de tes premiers contacts.
- **Le coffret à 95 €** : est-ce que les gens le prennent au lieu d'une bouteille seule ?
- **Le flacon de 20 cl** : seulement si le coût de revient laisse une marge.

### Les doutes sur le prix que le panel a exprimés, mot pour mot
1. « 35 euros la bouteille, c'est presque le double de ce que je paie en grande surface » (P003)
2. « À ce prix je préfère m'acheter un vrai rhum vieux. » (P006)
3. « Un rhum arrangé dont personne n'a entendu parler, à 35 euros, c'est un pari risqué pour un cadeau » (P010)

Ce sont des réponses d'acheteurs simulés : elles servent à choisir ce qu'on teste, pas à prouver quoi que ce soit.

## The offer

Méthode : le lens Offres (`founder-board/lenses.md`). C'est un résumé, dans nos mots, d'un cadre publié, pas les propos de son auteur.

### 1. Les obstacles entre l'acheteur et son achat
Ils viennent du panel, des concurrents et du Drive.

**Avant l'achat**
1. « 35 €, c'est presque le double de la grande surface. »
2. « À ce prix, je prends un vrai rhum vieux. »
3. « Je ne connais pas la marque. »
4. « Je le fais moi-même pour moins cher. »
5. « Moins sucré, ça va être fort et sec. »
6. « Moins sucré, ça ne veut rien dire sans un chiffre. »
7. « On ne me dit pas quel rhum il y a dedans. »
8. « Je ne vais jamais dans les salons où on peut goûter. »
9. « Je ne peux pas goûter avant d'acheter. »
10. « C'est risqué à offrir : la personne aime le rhum bien doux. »
11. « Il me faut un vrai objet cadeau, pas une bouteille seule. »
12. « Je n'ai pas d'occasion ce mois-ci. »
13. « Une bouteille de 70 cl, c'est trop pour essayer. »

**Pendant l'achat**
14. « Je n'ai pas de liquide. »
15. « Le coffret arrivera-t-il avant Noël ? »

**Après l'achat**
16. « Et si la personne n'aime pas ? »
17. « Je n'en boirai pas une bouteille entière. »
18. « Comment je le sers ? »
19. « Une bouteille filtrée, sans fruits dedans, ça ne fait pas fait maison. »

### 2. Les solutions retenues
Valeur pour l'acheteur notée de 1 à 5, coût pour toi noté de 1 à 5.

| solution | répond aux obstacles | valeur | coût | décision |
| --- | --- | :-: | :-: | --- |
| **Dégustation là où sont les acheteurs** : chez les cavistes, épiceries fines et bars partenaires, chez des particuliers (ventes privées), et sur les marchés si la mairie l'autorise | 5, 8, 9, 10 | 5 | 2 | **Gardée : c'est le cœur de l'offre** |
| Flacon découverte de 20 cl | 1, 13, 17 | 4 | 3 | Gardée, **à condition que le coût de revient le permette** |
| Coffret « Trois vents » (3 × 70 cl) avec une carte qui raconte la Maison | 3, 10, 11 | 4 | 2 | Gardée |
| Rhum de base nommé sur l'étiquette (HSE, AOC Martinique) | 2, 7 | 4 | 1 | Gardée |
| Taux de sucre mesuré et affiché | 6 | 4 | 2 | **Seulement si le chiffre est bas** (voir le point 5) |
| Échange de la cuvée sous 30 jours | 16 | 2 | 2 | **Retirée** : le panel n'y a pas cru (« gênant de demander un échange pour un cadeau ») |
| Carte de service (glaçons, tonic, une idée de cocktail) dans le coffret | 18 | 3 | 1 | Gardée, en restant dans les limites de la loi Évin |
| Livraison avant Noël garantie pour une commande avant le 10 décembre | 12, 15 | 3 | 1 | Gardée : c'est une vraie date |
| Paiement par carte et virement | 14 | 2 | 1 | Gardé |

### 3. L'offre
- **Le produit** : « Trois vents », trois rhums arrangés au rhum agricole AOC Martinique, qu'on goûte avant d'acheter.
- **Ce qu'on peut acheter** : la bouteille de 70 cl à 35 €, le coffret Trois vents à 95 €, le flacon de 20 cl à 13 € (à valider par son coût).
- **Les bonus** : la carte qui raconte la Maison et la carte de service dans le coffret, et le prénom écrit à la main sur le bandeau du coffret. Ce dernier bonus coûte surtout du temps.
- **La garantie** : aucune promesse d'échange. La vraie garantie, c'est de goûter avant d'acheter.
- **L'urgence, réelle** : la livraison avant Noël pour les commandes passées avant le 10 décembre, et le premier lot limité (lots de 40 bouteilles par cuvée).
- **Le nom** : « Coffret Trois vents ».

### 4. L'équation de valeur (de 1 à 10, avant puis après)
| élément | avant | après | ce qui le fait bouger |
| --- | :-: | :-: | --- |
| Résultat rêvé (« un bel apéro », « un cadeau qui plaît ») | 6 | 7 | Le coffret et la carte qui raconte la Maison |
| Probabilité perçue d'y arriver | 3 | 5 | La dégustation, le rhum nommé, le sucre affiché s'il est bas |
| Délai | 7 | 7 | Inchangé |
| Effort et risque | 4 | 6 | Le flacon de 20 cl et la dégustation près de chez soi |

### 5. Le retest sur le panel (mêmes 20 acheteurs, même tirage)

| | première offre (`pitch-v1.md`) | offre enrichie (`pitch.md`) |
| --- | :-: | :-: |
| Achètent | **5 / 20 (25 %)** | **3 / 20 (15 %)** |
| Flâneurs de marché | 3 / 4 | 2 / 4 |
| Évitent le sucre | 2 / 3 | 1 / 3 |
| Cherchent un cadeau | 0 / 5 | 0 / 5 |

**L'offre enrichie a fait moins bien.** Les réponses des acheteurs montrent pourquoi :
1. **La dégustation est passée du « stand de marché près de chez vous » aux « salons et ventes privées ».** Plusieurs acheteurs ont répondu qu'ils ne vont jamais dans les salons. La dégustation proche est ce qui fait acheter. C'est d'autant plus important que la vente sur les marchés n'est pas encore confirmée.
2. **Écrire « 31 % vol. » dans l'argumentaire** a renforcé la peur d'un rhum « fort et sec » chez ceux qui offrent. Ce degré doit figurer sur l'étiquette, mais il n'a pas besoin d'être mis en avant dans l'argumentaire.
3. **Promettre le sucre « sur l'étiquette » sans donner de chiffre** a été lu comme du marketing. Deux acheteurs veulent **moins de 20 g/L**. D'après tes recettes, tes cuvées tournent autour de **115 à 180 g/L de sucre ajouté**. Afficher le chiffre se retournerait contre toi. Il faut d'abord mesurer. Si le chiffre est élevé, ne mets pas « moins sucré » en avant : mets les arômes francs (cassis, bergamote).
4. **Le flacon de 20 cl a bien marché.** Un acheteur l'a pris, et presque tous ceux qui ont dit non citent le flacon comme ce qui les ferait changer d'avis après une dégustation.
5. **Les gens qui offrent ne sont pas convaincus par le panel**, ni avec l'offre enrichie, ni sans. Pourtant ton seul vrai client a acheté 5 coffrets. Sur ce point, le vrai client compte plus que le panel.

Ce sont des acheteurs simulés, et 20 réponses seulement. Les écarts portent sur 1 ou 2 personnes. Ce sont des pistes, pas des preuves.

### Ce qu'il faut retenir pour la suite
- **Garder** : le coffret, le rhum nommé, le flacon de 20 cl (si son coût le permet), la date limite pour Noël.
- **Retirer** : l'échange sous 30 jours, et le « 31 % » mis en avant dans le discours.
- **À décider après la mesure en laboratoire** : afficher le sucre ou non, et garder « moins sucré » comme promesse ou passer aux « arômes francs ».
- **La priorité absolue** : trouver des lieux de dégustation fixes et légaux (cavistes, épiceries fines, bars, ventes privées), puisque le marché n'est pas confirmé.
- **À faire avant de lancer le flacon** : calculer son coût de revient (flacon, bouchon, étiquette, façonnage). Ensuite, relancer `/founder-cfo`.

## The numbers

Les montants en « $ » du rapport de l'outil sont des euros, hors taxes. **La plupart des coûts sont des estimations** : seuls le liquide (prix Metro) et l'habillage (plafond de 4,20 € donné par toi) sont des chiffres réels. Le détail est dans `founder/cfo-sources.md`.

### Estimation du façonnage (27 octobre 2026)

Aucun tarif public de façonnage de rhum arrangé n'a été trouvé. Voici une estimation raisonnée, **à remplacer par un vrai devis** :
- Ce que le partenaire ferait : filtrer, mettre en bouteille, poser l'étiquette et la capsule, par lots d'environ 40 bouteilles, sous son agrément d'entrepositaire. Tu fournis le rhum, les matières et l'habillage.
- Un lot de 40 bouteilles demande environ 2 à 4 heures de travail, payées 35 à 45 € de l'heure. Le partenaire ajoute une part pour son agrément, sa comptabilité matières et son stockage. Cela donne **2,50 à 5 € par bouteille, avec 3,50 € comme valeur centrale.**
- Si le partenaire fait aussi la macération (7 jours dans ses cuves), le prix sera plutôt dans le haut de la fourchette.

| façonnage | 33 € TTC, mix 70/30 | 35 € TTC, mix 70/30 | 35 € TTC, 100 % direct, 200 bouteilles |
| ---: | ---: | ---: | ---: |
| 2,50 € | seuil 245 bouteilles, -667 € | seuil 212, -518 € | seuil 170, **+286 €** |
| **3,50 €** | seuil 288, -811 € | seuil 244, -662 € | seuil 190, **+86 €** |
| 5,00 € | seuil 393, -1 027 € | seuil 315, -878 € | seuil 230, -214 € |

Les montants sont le résultat d'exploitation de l'année 1, avant les 1 040 € de démarrage. Détail dans `founder/cfo-faconnage.txt`.

**En résumé : avec un façonnage autour de 3,50 € et 100 à 200 bouteilles, l'année 1 est à l'équilibre au mieux,** et seulement en vendant surtout en direct à 35 €. **N'accepte pas un devis au-dessus de 4 € par bouteille sans revoir le plan.**

### La marge (base de calcul : façonnage à 4 €)
- Le prix moyen est de **25,85 € HT** par bouteille. C'est un mélange de 70 % de vente directe (33 € TTC, soit 27,50 € HT) et de 30 % de vente aux pros (22 € HT). Ce mélange est une estimation.
- Le coût par bouteille est de **20,73 €** : liquide 9,00, habillage 4,20, façonnage 4,00 (estimé), frais de carte 0,35, cotisations micro-entreprise 3,18.
- **Chaque bouteille laisse 5,12 €** (20 %) pour payer les frais fixes.
- **Vendue à un pro à 22 € HT, une bouteille ne laisse que 1,74 €.** Le canal pro ne rapporte presque rien à ces coûts.

### Le seuil
- Les frais fixes estimés sont de 135 € par mois.
- **Il faut vendre environ 316 bouteilles par an pour couvrir les frais.** Ton objectif de 100 à 200 bouteilles est en dessous : l'année 1 perd environ 880 € avec 144 bouteilles, et environ 1 900 € en comptant les 1 040 € de dépenses de démarrage.
- **Il faut prévoir environ 1 900 € de trésorerie**, et plus encore si tu commandes l'habillage par lots.

### Ce qui change le plus le résultat (scénarios complets dans `founder/cfo-scenarios.txt`)
| scénario | contribution par bouteille | seuil par an | résultat année 1 |
| --- | ---: | ---: | ---: |
| Base (144 bouteilles, mix 70/30) | 5,12 € | 316 | -883 € |
| Façonnage à 2 € au lieu de 4 € | 7,12 € | 228 | -595 € |
| Sans façonnage (production propre agréée) | 9,12 € | 178 | -306 € |
| 100 % vente directe à 33 € TTC | 6,57 € | 247 | -674 € |
| **Vente directe, façonnage à 2 €, 200 bouteilles** | **8,57 €** | **189** | **+94 €** |
| 100 % pros à 22 € HT | 1,74 € | 931 | -1 369 € |

**Le chiffre à surveiller est le prix du façonnage.** Il pèse plus que le prix de vente : chaque euro de façonnage en moins ajoute environ 145 € au résultat de l'année 1.

### Trois façons d'améliorer la marge
1. **Négocier le façonnage à 2 € ou moins** (Éric ou KEVAS), ou obtenir ton propre agrément : la contribution passe de 5,12 € à 7,12 €, voire 9,12 €.
2. **Vendre surtout en direct** (coffrets, commandes, salons) plutôt qu'aux pros : la contribution passe à 6,57 € par bouteille.
3. **Revoir le prix pro.** À 22 € HT, chaque bouteille vendue à un pro ne rapporte presque rien. Voir `founder/pricing.md`.

### Les conditions du conseil sur l'argent
- [ ] Coût de revient compatible avec le prix : **oui en vente directe, non en vente aux pros** à ces coûts.
- [ ] Coût d'acquisition qui laisse une marge : **à vérifier**. Il reste 5 à 8 € par bouteille, ce qui laisse très peu pour la publicité.

**À l'échelle de 100 à 200 bouteilles, Maison Corsaire est une activité d'appoint, pas encore une entreprise rentable.** Ce n'est pas un échec : c'est le bon moment pour le savoir, avant de commander des centaines d'habillages.

Pas un conseil financier, fiscal ou juridique. Un comptable doit vérifier les cotisations, la TVA et les accises (notamment le complément éventuel sur le produit fini) avant de vendre.

---

## Unit economics: Maison Corsaire

Every number below comes from the input file. Nothing is looked up or guessed.

### One bouteille

| line | per bouteille |
| --- | ---: |
| Price | $25.85 |
| Liquide (rhum HSE 5,88 € + matières, moyenne des 3 cuvées) | -$9.00 |
| Habillage (bouteille, bouchon gravé, étiquettes, capsule) : plafond donné par le fondateur | -$4.20 |
| Façonnage chez un entrepositaire agréé (ESTIMATION) | -$4.00 |
| Frais de carte bancaire sur la vente directe (ESTIMATION) | -$0.35 |
| Cotisations sociales micro-entreprise, 12,3 % du CA (ESTIMATION) | -$3.18 |
| **Contribution** (what each bouteille leaves to pay the fixed costs) | **$5.12** (20%) |

### The margin that matters

Fixed costs: $135 a month (Assurance RC pro (ESTIMATION) $25, Salons et emplacements, environ 3 par an (ESTIMATION) $60, Déplacements et livraisons (ESTIMATION) $30, Banque, nom de domaine, outils (ESTIMATION) $20).

- **Break-even: 1 bouteilles a day.** Below that you lose money every month.
- **Profit margin at your plan** (0 a day): **-24%** of every sale, after every cost.

### Year 1, month by month

| month | bouteilles a day | revenue | profit | cumulative (after $1,040 startup) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | $517 | -$33 | -$1,073 |
| 2 | 1 | $905 | $44 | -$1,028 |
| 3 | 0 | $130 | -$109 | -$1,138 |
| 4 | 0 | $155 | -$104 | -$1,242 |
| 5 | 0 | $207 | -$94 | -$1,336 |
| 6 | 0 | $207 | -$94 | -$1,430 |
| 7 | 0 | $258 | -$84 | -$1,514 |
| 8 | 0 | $310 | -$74 | -$1,587 |
| 9 | 0 | $258 | -$84 | -$1,671 |
| 10 | 0 | $207 | -$94 | -$1,765 |
| 11 | 0 | $258 | -$84 | -$1,849 |
| 12 | 0 | $310 | -$74 | -$1,923 |

- **Year 1 operating profit: -$883** on $3,723 of revenue.
- After the $1,040 startup spend: -$1,923.
- Startup money earned back: not within year 1.
- Cash you need before it pays for itself: **$1,923**.

### What if

| scenario | margin at plan | break-even a day | year 1 profit |
| --- | ---: | ---: | ---: |
| Base plan | -24% | 1 | -$883 |
| Price -10% | -37% | 2 | -$1,255 |
| Volume -20% | -35% | 1 | -$1,030 |
| Unit costs +15% | -36% | 3 | -$1,330 |

### Red flags

- Year 1 loses money on operations (-$883).
- The startup spend is not earned back within year 1.

## Marketing

Ce plan s'appuie sur le panel (`founder/panel/results.md` et `panel-v2`), les concurrents (`competitors.md`), le prix (`pricing.md`), les chiffres (`cfo.md`) et le Drive (liste de prospects, charte graphique).

### La règle de base : la loi Évin
En France, la communication sur l'alcool est encadrée. Elle peut parler de l'origine, de la composition, du degré, du mode de fabrication et de la façon de consommer. Il faut le message sanitaire obligatoire (« L'abus d'alcool est dangereux pour la santé, à consommer avec modération »). On ne montre pas de fête, de séduction ni de réussite associées à l'alcool. Tout ce qui suit respecte ces limites, mais ce n'est pas un avis juridique.

### 1. Le positionnement

Trois versions possibles :
1. « Pour les habitants des Yvelines qui trouvent les rhums arrangés écœurants, Maison Corsaire est le rhum arrangé aux arômes francs, au rhum agricole AOC Martinique, qu'on goûte avant d'acheter, contrairement aux arrangés de grande surface. »
2. « Pour ceux qui cherchent un cadeau qui ait une histoire, Maison Corsaire est le coffret de trois rhums arrangés artisanaux des Yvelines, contrairement à une bouteille anonyme de rayon. »
3. « Pour les bars et restaurants créoles des Yvelines, Maison Corsaire est l'arrangé local à servir au verre, contrairement aux marques nationales. »

**Je recommande la n°1 pour le grand public, et la n°2 pour la saison de Noël.**
- Pour la n°1 : dans le panel, les acheteurs qui ont dit oui sont les flâneurs de marché et ceux qui évitent le sucre. Tous ont acheté **après une dégustation**, pour le goût franc.
- Pour la n°2 : le panel ne convainc pas les gens qui offrent, mais ton seul vrai client a acheté 5 coffrets. C'est le vrai client qui compte.
- J'ai écrit « arômes francs » plutôt que « moins sucré » tant que le taux de sucre n'est pas mesuré (voir `offer.md`, point 5).

### 2. Les canaux

| canal | pourquoi il colle | coût | comment savoir s'il marche |
| --- | --- | --- | --- |
| **Ventes privées et dégustations chez des particuliers** (toi, des amis, des collègues) | La dégustation fait vendre, et c'est légal à domicile (à confirmer avec ton statut) | Quasi nul | Bouteilles vendues par soirée |
| **Bars, restaurants et épiceries fines de ta liste** (Drive : Rhumerie du Dokistan à Meulan, Kaz d'Épices à Poissy, Le Jardin Créole à Maule, AKA SOSO aux Mureaux, L'Épicurien et Aux Fins Délices à Mantes…) | Un point de dégustation fixe et légal. Le service au verre évite le conflit de prix avec la vente directe | Échantillons, environ 10 € par visite | Établissements qui commandent, bouteilles par mois |
| **Instagram** (visuels Canva déjà prêts dans le Drive) | Montrer la fabrication, les ingrédients, le rhum : tout ce que la loi Évin permet | Ton temps | Messages reçus, commandes de coffrets |
| **Bouche-à-oreille autour des 5 coffrets de Noël** | Chaque coffret offert est une dégustation chez quelqu'un d'autre | Une carte dans le coffret | Commandes qui disent « on me l'a offert » |
| Salons locaux (par exemple le Salon des Vins et des Saveurs de Jouy-en-Josas, 21 et 22 novembre) | Beaucoup d'acheteurs d'un coup | Prix du stand, à demander | Ventes et contacts récoltés |

**Ce qu'on ne fait pas :**
- **La publicité payante.** Une bouteille ne rapporte que 6 à 8 €, donc tu ne peux pas payer davantage pour gagner un client (voir la partie 5).
- **Les marchés, tant que la mairie n'a pas répondu** (article L3322-6 du Code de la santé publique).
- **Les cavistes, pour l'instant**, à cause du conflit entre ton prix public et ton prix pro (voir `pricing.md`).

### 3. Dix accroches (adaptées à la loi Évin)
1. « Rhum agricole AOC Martinique, cassis, bergamote. C'est tout. » (Noroît, étiquette ou post)
2. « Goûtez avant d'acheter. » (vente privée, panneau de dégustation)
3. « Trois vents, trois rhums arrangés. » (coffret)
4. « Filtré, sans fruits dans la bouteille : il ne reste que l'arôme. » (réponse à « ça ne fait pas fait maison »)
5. « 7 jours de macération, 14 jours de repos. » (fabrication, Reel en coulisses)
6. « Fait dans les Yvelines. » (local, réponse à « je ne connais pas la marque »)
7. « Coco, citron vert, fève tonka râpée à la main. » (Zéphyr)
8. « Commandé avant le 10 décembre, livré avant Noël. » (urgence réelle)
9. « Un coffret, trois cuvées, une carte qui raconte la Maison. » (réponse à « il me faut un vrai objet cadeau »)
10. « Le flacon de 20 cl pour découvrir. » (réponse à « 70 cl, c'est trop pour essayer », si le flacon est validé)

Chaque visuel porte le message sanitaire. Il ne montre ni personne en train de boire, ni fête.

### 4. La campagne de 30 jours
J = samedi 14 novembre 2026, vente privée de lancement. **Ce lancement suppose que la production et le statut soient réglés** (voir `ops.md` et `launch.md`). Sinon, toutes les dates glissent.

| date | canal | quoi |
| --- | --- | --- |
| sam. 31 oct. (J-14) | Instagram | Premier post : la carte marine « L'art du rhum arrangé » et l'histoire des Trois vents |
| lun. 2 nov. | Téléphone | Appeler Kaz d'Épices, Le Jardin Créole et AKA SOSO pour proposer une dégustation |
| mer. 4 nov. | Instagram | Les coulisses : la purée de cassis, la bergamote passée au chinois (accroche n°1) |
| sam. 7 nov. (J-7) | Le pub de ton ami | Répétition générale : dégustation, discours, prix. Noter les réactions |
| dim. 8 nov. | Instagram | Story « Goûtez avant d'acheter » et invitation à la vente privée (accroche n°2) |
| mer. 11 nov. | Sur place | Visite de la Rhumerie du Dokistan à Meulan, avec échantillons |
| **sam. 14 nov. (J)** | **Vente privée** | **Lancement chez toi ou chez un ami : dégustation des 3 cuvées, coffret à 95 €, bouteille à 35 €** |
| dim. 15 nov. | Instagram | Merci, et le coffret avec la date limite du 10 décembre (accroche n°8) |
| mer. 18 nov. | Instagram | Zéphyr et la fève tonka (accroche n°7) |
| sam. 21 nov. | Salon ou 2e vente privée | Jouy-en-Josas si un stand est possible, sinon une vente privée chez un collègue |
| mer. 25 nov. | Téléphone | Relancer les établissements visités. Proposer une bouteille de démonstration pour le service au verre |
| sam. 28 nov. | Vente privée | 3e soirée, chez un client de la première |
| lun. 30 nov. (J+16) | Bilan | Compter les bouteilles vendues, les contacts, les établissements. Décider de la suite |
| jeu. 10 déc. | Clôture | Dernières commandes de coffrets pour Noël |

**Quand il n'y a rien de nouveau à dire :** les coulisses (filtration, gravure des bouchons, pose des bandeaux), les ingrédients un par un, les lots numérotés.

### 5. Le budget et les chiffres
- **Budget proposé : environ 150 €.** Environ 100 € d'échantillons (une bouteille partagée en flacons de dégustation) et 50 € d'impressions (cartes, panneau « Goûtez avant d'acheter »).
- **Combien tu peux dépenser pour gagner un client :** une bouteille à 35 € laisse environ 8 € (`pricing.md`). Un coffret à 95 € laisse environ 17 € : 79,17 € HT, moins 3 × 17,55 € de coûts directs, moins 12,3 % de cotisations, et avant le coût du coffret lui-même. **Tu ne peux donc pas dépenser plus de 8 à 17 € pour gagner un client**, ce qui exclut la publicité payante.
- **Les trois chiffres à suivre chaque semaine :**
  1. Les bouteilles vendues par dégustation. **Sous 3, change le lieu ou le discours.**
  2. Les établissements qui acceptent une dégustation. **Sous 2 sur 10 appels, revois le prix pro ou l'argumentaire.**
  3. Les commandes de coffrets avant le 10 décembre. **Sous 10 au 30 novembre, relance tout ton réseau.**

### Les règles
- Pas de faux avis, de faux témoignages ni de « vu dans ».
- **Les réponses du panel servent à la recherche. Ne les utilise jamais comme des citations de clients.**
- N'écris pas « moins sucré » tant que le taux de sucre n'est pas mesuré et comparé.

## Brand

**La marque existe déjà en grande partie** dans le Drive : le nom, la gamme « Trois vents » (Noroît, Zéphyr, Suroît), le logo (tricorne, maison à rose des vents, vague), la charte graphique finalisée le 27 octobre 2026, la fiche packaging et les visuels Instagram sur Canva. Cette étape ne refait donc pas le travail : elle vérifie ce qui protège la marque et l'accorde avec le positionnement de `marketing.md`.

### 1. Le nom : les vérifications à faire avant de déposer
Le dépôt de la marque n'est pas encore fait. Ta propre note sur KEVAS le relève : ils ont déposé la leur en février 2026.

- **Le risque de conflit est réel.** Il existe une cuvée **« Le Corsaire » chez Neisson**, une maison de rhum agricole de Martinique ([RumX](https://www.rum-x.com/rums/3905/neisson-rhum-vieux-le-corsaire)). Il existe aussi un **Corsair Spiced Rum** aux États-Unis ([Corsair Distillery](https://www.americanrumreport.com/corsair-distillery)). Je n'ai trouvé aucune marque « Maison Corsaire » dans les spiritueux, mais je n'ai pas pu consulter les registres officiels.
- **À faire toi-même :**
  - **INPI** : cherche « Corsaire » et « Maison Corsaire » en **classe 33** (boissons alcoolisées) sur data.inpi.fr.
  - **EUIPO** : fais la même recherche sur euipo.europa.eu (base eSearch), puisque Neisson pourrait avoir une marque européenne.
  - Cherche aussi les noms Noroît, Zéphyr et Suroît en classe 33.
- **Le nom de domaine** (maisoncorsaire.fr ou .com) et les comptes Instagram et TikTok : je n'ai pas pu vérifier, le réseau de cet environnement bloque ces sites. À contrôler toi-même.
- **Ce n'est pas un avis juridique.** Si l'INPI montre une marque proche en classe 33, consulte un conseil en propriété industrielle avant de déposer ou d'imprimer. Rien n'est protégé tant que le dépôt n'est pas fait.

### 2. La promesse, l'accroche et le ton
- **La promesse**, en une ligne : *des rhums arrangés au rhum agricole AOC Martinique, aux arômes francs, que l'on goûte avant d'acheter.*
- **Trois accroches possibles** :
  1. « Trois vents. Une même Maison. » (déjà dans ta charte, à garder)
  2. « Le goût du détail. » (déjà sur un visuel Canva)
  3. « Rhum agricole, fruits, patience. »
- **Le ton, en trois mots** :
  - **Sobre** : on décrit les ingrédients, pas d'adjectifs à la chaîne. Pas « une explosion de saveurs exotiques ».
  - **Chaleureux** : tutoiement sur Instagram, vouvoiement sur l'étiquette. Pas de jargon de sommelier.
  - **Précis** : des chiffres et des faits (7 jours, AOC Martinique). Pas de promesse vague comme « le meilleur rhum arrangé ».
- **Avant et après**, sur une phrase de `pitch.md` :
  - Avant : « Du rhum macéré avec des fruits et des épices, volontairement moins sucré que les rhums arrangés classiques, aux arômes francs. »
  - Après : « Rhum agricole AOC Martinique, cassis, bergamote, vanille. Sept jours de macération, puis on filtre. Goûtez-le avant de choisir. »

### 3. L'identité visuelle
Elle est déjà définie dans ta charte : cuivre #C86428, or #D99A3D, ivoire #F7F1E7, noir #111111, un fond par cuvée (bordeaux, vert forêt, brun), Playfair Display et Montserrat. Deux vérifications :
- **La lisibilité.** Le cuivre #C86428 sur ivoire est trop pâle pour du petit texte. C'est pour ça que ta charte prévoit déjà #A04E1B pour le texte courant. Garde cette règle. Les mentions obligatoires de l'étiquette arrière doivent être en noir ou dans ce cuivre foncé.
- **Les polices.** Playfair Display et Montserrat sont gratuites (licence SIL Open Font) : aucun problème de droits.

### 4. Les cinq premiers contacts avec le client
1. **La vente privée ou la dégustation** : un panneau « Goûtez avant d'acheter » aux couleurs de la charte, et les trois bouteilles alignées dans l'ordre des vents.
2. **Le coffret** : la carte qui raconte la Maison (trois vents, trois cuvées) et la carte de service.
3. **La confirmation de commande** : un message court avec le numéro de lot et la date de livraison.
4. **Le premier post Instagram** : la carte marine, déjà prête dans le Drive.
5. **La réponse à la première réclamation** : remercier, demander la cuvée et le lot, proposer une solution sous 48 heures.

## Operations

### 1. Le cycle de production (fiches du Drive)
Pour un lot d'environ 40 bouteilles par cuvée :
1. Réception du rhum HSE et des purées (Metro).
2. J0 : dissoudre le sucre dans les purées, puis ajouter le rhum.
3. Agiter chaque jour.
4. Ajouter les zestes ou la tonka à J4 ou J5.
5. J7 : goûter, puis filtrer au sac nylon.
6. Laisser reposer 14 jours.
7. J21 : doser l'arôme et le sel, passer au filtre papier, contrôler à l'alcoomètre.
8. Mise en bouteille, bouchon, sticker, bandeau, capsule.
9. Noter le lot dans la comptabilité matières.
10. Stocker à 18-20 °C à l'abri de la lumière.

Le client voit les étapes 8 et 10, c'est-à-dire la bouteille, et la dégustation.

**Il faut 3 semaines entre le début de la macération et une bouteille prête.** Pour livrer avant le 19 décembre, les lots doivent démarrer au plus tard vers le 23 novembre.

### 2. Les fournisseurs
| poste | aujourd'hui | à faire |
| --- | --- | --- |
| Rhum HSE 55° AOC | Metro, 14,69 €/L HT, droits acquittés | Demander à un distributeur agréé le prix en droits suspendus. Ça n'a d'intérêt que si tu deviens entrepositaire agréé |
| Purées Boiron et Ponthier, sucre, sel, arômes | Metro (prix dans le Drive) | Il manque le prix du sirop de caramel, de l'orange bio, de l'arôme tonka et de la vergeoise |
| Bouteille 70 cl | bouteilles-et-bocaux.com, réf. 100029470 | Confirmer le prix et le minimum de commande. Ton plafond d'habillage est de 4,20 € |
| Bouchon tête bois gravé MC | non renseigné | Devis et délai de gravure |
| Stickers, bandeaux, étiquettes arrière | non renseigné | Devis. L'adhésif doit résister à l'humidité |
| **Façonnage, sous agrément** | Éric (bar à cocktails, environ 50 minutes, Louviers ?) ou KEVAS (Coubert, environ 100 km) | **Obtenir un devis écrit.** Estimation : 3,50 €, au-dessus de 4 € il faut revoir le plan (`cfo.md`). Avec KEVAS : un engagement de confidentialité et de non-concurrence d'abord (ta propre note) |

Quand un prix réel remplace une estimation, mets à jour `founder/numbers.json` et relance `/founder-cfo`.

### 3. Les personnes
C'est toi seul, avec le partenaire de façonnage. Rythme proposé pour 150 bouteilles par an :
- **En novembre et décembre**, environ 6 heures par semaine : 2 heures de production et de logistique, 2 à 3 heures de dégustations et de ventes privées, 1 heure pour Instagram.
- **De janvier à octobre**, environ 2 heures par semaine.

Il n'y a pas de salaire. Le temps est le vrai coût. Tes cotisations de micro-entreprise sont estimées dans `cfo.md`, à vérifier avec l'URSSAF.

### 4. Les routines
**R1. Vente privée ou dégustation**
1. Préparer 3 bouteilles ouvertes, les verres de dégustation, le panneau, le terminal de paiement, le registre des ventes et l'affiche d'interdiction de vente aux mineurs.
2. Faire goûter dans l'ordre Zéphyr, puis Noroît, puis Suroît, en petites doses.
3. Présenter en une phrase par cuvée : les ingrédients et le rhum.
4. Proposer le coffret, puis la bouteille.
5. Encaisser et noter la vente (cuvée, lot, quantité).
6. Demander à l'hôte qui pourrait accueillir la prochaine soirée.

**R2. Commande de coffret**
1. Confirmer par écrit la cuvée, la date de livraison et le paiement.
2. Préparer le coffret avec ses cartes.
3. Livrer ou remettre en main propre.
4. Noter la sortie dans la comptabilité matières.

**R3. Réclamation**
1. Remercier.
2. Demander la cuvée, le lot et le problème.
3. Goûter une bouteille du même lot.
4. Proposer une solution sous 48 heures.
5. Noter ce qui s'est passé.

**R4. Réassort mensuel**
1. Compter le stock par cuvée.
2. Si une cuvée passe sous 10 bouteilles, lancer un lot.
3. Commander les matières, puis l'habillage.
4. Réserver un créneau de façonnage.

### 5. Les outils
- **Paiement** : un terminal SumUp ou équivalent. Vérifie le taux sur le site du fournisseur, j'ai estimé environ 1,75 %.
- **Facturation et registre des ventes** : un tableur, ou un outil gratuit de facturation pour micro-entreprise.
- **Comptabilité matières** : tes tableurs « entrées » et « sorties et ventes » du Drive, à remplir à chaque lot.
- **Commandes** : un formulaire simple (Google Forms) pour les coffrets, avec une case « j'ai 18 ans ou plus ».

### 6. Licences, autorisations et assurance (à confirmer)
Les règles changent selon le lieu et dans le temps. Fais tout confirmer par l'administration concernée. Ce n'est pas un avis juridique.
- [ ] **Statut d'entrepositaire agréé**, ou façonnage chez un entrepositaire agréé. D'après tes notes, les douanes ont répondu le 24 septembre que le statut est nécessaire. Contact : Pôle d'action économique Paris-Ouest, 09 70 27 23 94.
- [ ] **Complément d'accises sur le produit fini** : à confirmer par écrit avec les douanes.
- [ ] **Vente sur les marchés** (article L3322-6 du Code de la santé publique) : attendre la réponse de la mairie de Rosny.
- [ ] **Licence de vente à emporter** : déjà obtenue (grande licence à emporter), d'après tes notes.
- [ ] **Déclaration à la DDPP** pour une activité alimentaire, et vérification de ton bail si tu produis à domicile.
- [ ] **Étiquetage** : dénomination, volume, degré, lot, nom de l'embouteilleur, logo femme enceinte, allergènes. **Vérifie aussi la dénomination légale si le sucre dépasse 100 g/L** (catégorie « liqueur » du règlement UE 2019/787).
- [ ] **Assurance responsabilité civile professionnelle**, qui couvre aussi les produits.
- [ ] **Affiche d'interdiction de vente aux mineurs** sur chaque point de vente, et contrôle de l'âge pour la vente en ligne.
- [ ] **Dépôt de marque à l'INPI** (voir `brand.md`).

### 7. Les risques
| risque | probabilité | gravité | plan |
| --- | :-: | :-: | --- |
| Pas d'agrément ni de façonnier à temps pour Noël | élevée | élevée | Choisir Éric ou KEVAS cette semaine. Prévenir le client des 5 coffrets s'il y a un retard |
| Vente sur les marchés refusée | moyenne | moyenne | Ventes privées, bars et épiceries fines (`marketing.md`) |
| Taux de sucre mesuré élevé (plus de 100 g/L) | élevée, d'après tes recettes | moyenne | Ne pas écrire « moins sucré ». Mettre en avant les arômes. Vérifier la dénomination légale |
| Devis de façonnage au-dessus de 4 € | moyenne | élevée | Revoir le plan (`cfo.md`), négocier par gros lots, ou viser ton propre agrément |
| Conflit de marque autour de « Corsaire » | moyenne | élevée | Faire la recherche INPI et EUIPO avant d'imprimer plus d'étiquettes |
| Rupture de purée chez Metro | faible | moyenne | Commander directement chez Boiron, garder un stock de 2 lots |
| Lot raté (goût, trouble) | moyenne | moyenne | Goûter à J7, ne pas mettre en bouteille, noter le lot |
| Casse ou fuite d'une bouteille | faible | faible | Emballage avec séparateurs, bouteilles de remplacement en stock |
| Mauvais avis public | faible | moyenne | Routine R3, réponse sous 48 heures |
| Mois creux (de janvier à mars) | élevée | faible | Frais fixes au plus bas. Prospecter les bars pendant cette période |

## Launch plan

### 1. Tester avant de dépenser
Le premier test réel est déjà en cours : **une commande payée de 5 coffrets pour Noël.** Le test suivant ne coûte presque rien.

- **Le test :** deux ventes privées avec dégustation (le samedi 14 et le samedi 28 novembre), plus la répétition au pub de ton ami le samedi 7 novembre.
- **Ce qui compte comme réussite, fixé à l'avance :**
  - **au moins 30 bouteilles vendues** ou **10 coffrets commandés** d'ici le jeudi 10 décembre ;
  - **au moins 1 établissement sur 10 appelés** qui accepte une dégustation ou une bouteille de démonstration.
- **La comparaison avec le panel :** les acheteurs simulés ont dit oui à 15 à 25 %. Si moins de 1 personne sur 6 achète après avoir goûté en vente privée, fais confiance aux vraies personnes : retourne à `/founder-offer` (dégustation, flacon) ou à `/founder-pricing`.
- **Avant tout volume, mesure en laboratoire le sucre et le degré** des 3 cuvées. Environ 300 €, estimés dans `cfo.md`.

### 2. Le compte à rebours
Aujourd'hui, nous sommes le mardi 27 octobre 2026. L'objectif est de livrer les coffrets avant Noël. **Le chemin critique est marqué ★** : si une de ces tâches glisse, tout le reste glisse.

| semaine | tâche | responsable | date limite |
| --- | --- | --- | --- |
| 27 oct. – 1er nov. | ★ Choisir le partenaire de façonnage, obtenir le devis et signer (confidentialité comprise) | toi | ven. 30 oct. |
| | ★ Obtenir l'accord écrit des douanes sur le schéma choisi (accises, comptabilité matières) | toi | ven. 30 oct. |
| | Recherche INPI et EUIPO sur « Corsaire », puis déposer la marque si la voie est libre | toi | dim. 1er nov. |
| | Premier post Instagram | toi | sam. 31 oct. |
| 2 – 8 nov. | ★ Commander l'habillage pour 3 lots de 40 (bouteilles, bouchons gravés, stickers, bandeaux, capsules) en vérifiant les délais | toi | lun. 2 nov. |
| | Envoyer les 3 cuvées au laboratoire (sucre, degré) | toi | mer. 4 nov. |
| | Appeler les établissements de la liste du Drive | toi | à partir du lun. 2 nov. |
| | Répétition au pub de ton ami | toi et ton ami | sam. 7 nov. |
| 9 – 15 nov. | ★ Lancer la macération des 3 lots pilotes (J0) | toi ou le façonnier | lun. 9 nov. |
| | Assurance responsabilité civile pro signée | toi | ven. 13 nov. |
| | **Vente privée de lancement** (avec les échantillons des tests en cours) | toi | **sam. 14 nov.** |
| 16 – 22 nov. | J7 : goûter et filtrer les lots pilotes | toi ou le façonnier | lun. 16 nov. |
| | Résultats du laboratoire : décider du discours (« moins sucré » ou « arômes francs ») et de l'étiquette arrière | toi | ven. 20 nov. |
| | Salon de Jouy-en-Josas ou 2e vente privée | toi | sam. 21 nov. |
| 23 – 29 nov. | ★ Si plus de commandes que prévu, lancer un 2e lot (date limite pour livrer avant Noël) | toi | lun. 23 nov. |
| | 3e vente privée | toi | sam. 28 nov. |
| 30 nov. – 6 déc. | ★ Mise en bouteille et habillage des lots pilotes (J21) | façonnier | lun. 30 nov. |
| | Bilan du test (voir la partie 1) | toi | lun. 30 nov. |
| 7 – 13 déc. | Livrer les 5 coffrets commandés, et les autres | toi | à partir du lun. 7 déc. |
| | Clôture des commandes pour Noël | toi | jeu. 10 déc. |
| 14 – 20 déc. | Dernières livraisons | toi | sam. 19 déc. |

**Si l'agrément ou le façonnage n'est pas prêt le 9 novembre, les coffrets ne seront pas prêts pour Noël.** Préviens alors le client tout de suite, et propose-lui une livraison début janvier ou un remboursement.

**La vente privée du 14 novembre se fait avant que les lots pilotes soient en bouteille.** Ce jour-là, tu fais goûter et tu prends des commandes à livrer en décembre. Tu ne vends rien sur place. Vérifie avec les douanes ce qui est permis avant d'avoir le statut (c'est la question n°8 de ta fiche d'appel).

### 3. Le jour du lancement : samedi 14 novembre, vente privée
| heure | quoi |
| --- | --- |
| 14 h 00 | Installation : les 3 cuvées en dégustation, les verres, le panneau, l'affiche « mineurs », le terminal de paiement, le bon de commande pour les coffrets |
| 14 h 30 | Story Instagram : la table prête, sans personne en train de boire |
| 15 h 00 | Arrivée des invités. Dégustation dans l'ordre Zéphyr, Noroît, Suroît |
| 15 h 30 – 18 h 00 | Commandes : coffret à 95 €, bouteille à 35 €, livraison en décembre |
| 18 h 00 | Demander qui accueille la prochaine soirée. Noter les noms |
| 18 h 30 | Compter les commandes et noter les objections entendues mot pour mot |
| En cas de problème | Terminal en panne : virement ou chèque, un QR code imprimé à l'avance. Un échantillon trouble : ne pas le servir, le dire franchement |

### 4. Les 30 premiers jours
**À suivre chaque semaine :**
- les bouteilles et coffrets commandés, à comparer avec les 316 bouteilles par an qu'il faut pour couvrir les frais (`cfo.md`), soit environ 26 par mois ;
- les établissements contactés et ceux qui acceptent ;
- les messages Instagram reçus.

**Les points d'étape :**
- **Jour 7 (sam. 21 nov.) :** combien d'acheteurs après dégustation, et quelle objection revient le plus ?
- **Jour 14 (sam. 28 nov.) :** au moins 15 bouteilles commandées ? Sinon, change le lieu ou le discours.
- **Jour 30 (lun. 14 déc.) :** le test est-il réussi (voir la partie 1) ? Quel est le vrai coût du façonnage ? Ensuite, relance `/founder-cfo` avec les vrais chiffres et décide de 2027.

_The panel is simulated buyers and the numbers are projections from your inputs. Confirm demand with real customers and costs with real quotes before you spend. Not financial, legal or tax advice._
