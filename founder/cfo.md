# Note du CFO : Maison Corsaire

Les montants en « $ » du rapport de l'outil sont des euros, hors taxes. **La plupart des coûts sont des estimations** : seuls le liquide (prix Metro) et l'habillage (plafond de 4,20 € donné par toi) sont des chiffres réels. Le détail est dans `founder/cfo-sources.md`.

## La marge
- Le prix moyen est de **25,85 € HT** par bouteille. C'est un mélange de 70 % de vente directe (33 € TTC, soit 27,50 € HT) et de 30 % de vente aux pros (22 € HT). Ce mélange est une estimation.
- Le coût par bouteille est de **20,73 €** : liquide 9,00, habillage 4,20, façonnage 4,00 (estimé), frais de carte 0,35, cotisations micro-entreprise 3,18.
- **Chaque bouteille laisse 5,12 €** (20 %) pour payer les frais fixes.
- **Vendue à un pro à 22 € HT, une bouteille ne laisse que 1,74 €.** Le canal pro ne rapporte presque rien à ces coûts.

## Le seuil
- Les frais fixes estimés sont de 135 € par mois.
- **Il faut vendre environ 316 bouteilles par an pour couvrir les frais.** Ton objectif de 100 à 200 bouteilles est en dessous : l'année 1 perd environ 880 € avec 144 bouteilles, et environ 1 900 € en comptant les 1 040 € de dépenses de démarrage.
- **Il faut prévoir environ 1 900 € de trésorerie**, et plus encore si tu commandes l'habillage par lots.

## Ce qui change le plus le résultat (scénarios complets dans `founder/cfo-scenarios.txt`)
| scénario | contribution par bouteille | seuil par an | résultat année 1 |
| --- | ---: | ---: | ---: |
| Base (144 bouteilles, mix 70/30) | 5,12 € | 316 | -883 € |
| Façonnage à 2 € au lieu de 4 € | 7,12 € | 228 | -595 € |
| Sans façonnage (production propre agréée) | 9,12 € | 178 | -306 € |
| 100 % vente directe à 33 € TTC | 6,57 € | 247 | -674 € |
| **Vente directe, façonnage à 2 €, 200 bouteilles** | **8,57 €** | **189** | **+94 €** |
| 100 % pros à 22 € HT | 1,74 € | 931 | -1 369 € |

**Le chiffre à surveiller est le prix du façonnage.** Il pèse plus que le prix de vente : chaque euro de façonnage en moins ajoute environ 145 € au résultat de l'année 1.

## Trois façons d'améliorer la marge
1. **Négocier le façonnage à 2 € ou moins** (Éric ou KEVAS), ou obtenir ton propre agrément : la contribution passe de 5,12 € à 7,12 €, voire 9,12 €.
2. **Vendre surtout en direct** (coffrets, commandes, salons) plutôt qu'aux pros : la contribution passe à 6,57 € par bouteille.
3. **Revoir le prix pro.** À 22 € HT, chaque bouteille vendue à un pro ne rapporte presque rien. Voir `founder/pricing.md`.

## Les conditions du conseil sur l'argent
- [ ] Coût de revient compatible avec le prix : **oui en vente directe, non en vente aux pros** à ces coûts.
- [ ] Coût d'acquisition qui laisse une marge : **à vérifier**. Il reste 5 à 8 € par bouteille, ce qui laisse très peu pour la publicité.

**À l'échelle de 100 à 200 bouteilles, Maison Corsaire est une activité d'appoint, pas encore une entreprise rentable.** Ce n'est pas un échec : c'est le bon moment pour le savoir, avant de commander des centaines d'habillages.

Pas un conseil financier, fiscal ou juridique. Un comptable doit vérifier les cotisations, la TVA et les accises (notamment le complément éventuel sur le produit fini) avant de vendre.

---

# Unit economics: Maison Corsaire

Every number below comes from the input file. Nothing is looked up or guessed.

## One bouteille

| line | per bouteille |
| --- | ---: |
| Price | $25.85 |
| Liquide (rhum HSE 5,88 € + matières, moyenne des 3 cuvées) | -$9.00 |
| Habillage (bouteille, bouchon gravé, étiquettes, capsule) : plafond donné par le fondateur | -$4.20 |
| Façonnage chez un entrepositaire agréé (ESTIMATION) | -$4.00 |
| Frais de carte bancaire sur la vente directe (ESTIMATION) | -$0.35 |
| Cotisations sociales micro-entreprise, 12,3 % du CA (ESTIMATION) | -$3.18 |
| **Contribution** (what each bouteille leaves to pay the fixed costs) | **$5.12** (20%) |

## The margin that matters

Fixed costs: $135 a month (Assurance RC pro (ESTIMATION) $25, Salons et emplacements, environ 3 par an (ESTIMATION) $60, Déplacements et livraisons (ESTIMATION) $30, Banque, nom de domaine, outils (ESTIMATION) $20).

- **Break-even: 1 bouteilles a day.** Below that you lose money every month.
- **Profit margin at your plan** (0 a day): **-24%** of every sale, after every cost.

## Year 1, month by month

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

## What if

| scenario | margin at plan | break-even a day | year 1 profit |
| --- | ---: | ---: | ---: |
| Base plan | -24% | 1 | -$883 |
| Price -10% | -37% | 2 | -$1,255 |
| Volume -20% | -35% | 1 | -$1,030 |
| Unit costs +15% | -36% | 3 | -$1,330 |

## Red flags

- Year 1 loses money on operations (-$883).
- The startup spend is not earned back within year 1.
