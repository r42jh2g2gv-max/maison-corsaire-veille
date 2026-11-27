// FORGE — fiche technique des exercices (consignes clés, erreurs à éviter) + vidéo + alternatives.
import { S, esc, $, sheet } from './ui.js';
import { exById, alternatives } from './data.js';

// [position / exécution, points clés, erreur fréquente]
const TECH = {
  bench: ['Allongé, yeux sous la barre, omoplates serrées et basses, pieds ancrés au sol.', 'Descends la barre au bas des pectoraux, coudes à ~45°, pousse en ligne légèrement vers les yeux.', 'Fesses qui décollent, coudes à 90° du corps (épaules en danger).'],
  db_bench: ['Haltères au-dessus de la poitrine, omoplates serrées.', 'Descends contrôlé jusqu’à l’étirement des pecs, remonte en rapprochant légèrement les haltères.', 'Rebondir en bas, haltères trop écartés.'],
  incline_db: ['Banc à 30°, omoplates serrées, haltères au-dessus du haut des pecs.', 'Descente lente (2–3 s), coudes sous les poignets.', 'Banc trop incliné (devient un exercice d’épaules).'],
  incline_bench: ['Banc à 30°, barre au-dessus de la clavicule.', 'Descends au haut de la poitrine, coudes rentrés.', 'Arquer excessivement le dos.'],
  dips: ['Mains sur les barres, épaules basses, buste légèrement penché.', 'Descends jusqu’à bras à 90°, remonte sans verrouiller brutalement.', 'Descendre trop bas avec épaules qui roulent en avant.'],
  pushup: ['Mains un peu plus larges que les épaules, corps gainé de la tête aux talons.', 'Poitrine près du sol, coudes à ~45°, pousse le sol.', 'Bassin qui s’affaisse, tête qui plonge.'],
  decline_pushup: ['Pieds surélevés sur un banc, corps gainé.', 'Descends la poitrine vers le sol, coudes à 45°.', 'Bassin cassé.'],
  cable_fly: ['Poulies hautes, un pied devant, buste légèrement penché.', 'Bras légèrement fléchis et fixes, ramène les mains devant le bas des pecs.', 'Plier les coudes (devient un développé).'],
  barbell_row: ['Buste penché à ~45°, dos plat, genoux fléchis.', 'Tire la barre vers le nombril en serrant les omoplates.', 'Se relever pour tricher, dos rond.'],
  db_row: ['Main et genou sur le banc, dos plat.', 'Tire l’haltère vers la hanche, coude près du corps.', 'Rotation du buste, tirer avec le biceps.'],
  cable_row: ['Assis, dos droit, poitrine haute.', 'Tire la poignée vers le ventre, omoplates serrées, retour contrôlé.', 'Balancer le buste d’avant en arrière.'],
  inverted_row: ['Sous une barre ou une table, corps gainé, talons au sol.', 'Tire la poitrine vers la barre, omoplates serrées.', 'Bassin qui tombe.'],
  face_pull: ['Poulie à hauteur des yeux, corde, prise pouces vers l’arrière.', 'Tire vers le visage en écartant les mains, coudes hauts.', 'Charge trop lourde, buste qui recule.'],
  pullup: ['Prise pronation un peu plus large que les épaules, bras tendus.', 'Abaisse les épaules puis tire le menton au-dessus de la barre, descente contrôlée.', 'Balancer, demi-amplitude.'],
  chinup: ['Prise supination largeur d’épaules.', 'Tire la poitrine vers la barre, coudes vers les hanches.', 'Ne pas descendre complètement.'],
  lat_pulldown: ['Cuisses bloquées, prise large, buste légèrement incliné.', 'Tire la barre vers le haut de la poitrine, coudes vers le bas.', 'Tirer derrière la nuque, se pencher trop en arrière.'],
  band_pulldown: ['Élastique accroché en hauteur, à genoux.', 'Tire vers la poitrine en abaissant les épaules.', 'Hausser les épaules.'],
  ohp: ['Debout, barre sur les clavicules, fessiers et abdos serrés.', 'Pousse la barre au-dessus de la tête, la tête passe sous la barre en fin.', 'Cambrer le bas du dos.'],
  db_ohp: ['Assis ou debout, haltères à hauteur d’oreilles.', 'Pousse vers le haut sans cogner les haltères, descente contrôlée.', 'Dos cambré, coudes trop en arrière.'],
  pike_pushup: ['Fesses hautes en V inversé, mains largeur d’épaules.', 'Descends le sommet du crâne vers le sol entre les mains.', 'Coudes qui s’ouvrent à 90°.'],
  lateral_raise: ['Debout, haltères le long du corps, légère flexion des coudes.', 'Monte les bras sur les côtés jusqu’aux épaules, petits doigts légèrement hauts.', 'Élan avec le buste, hausser les trapèzes.'],
  rear_delt: ['Buste penché, dos plat, haltères sous les épaules.', 'Ouvre les bras sur les côtés en serrant l’arrière des épaules.', 'Tirer avec le dos, charge trop lourde.'],
  db_curl: ['Debout, coudes collés au corps.', 'Monte en tournant la paume vers le haut, descente lente.', 'Balancer le buste, coudes qui avancent.'],
  hammer_curl: ['Prise neutre (pouces vers le haut), coudes fixes.', 'Monte jusqu’à l’épaule, descente 2 s.', 'Élan.'],
  ez_curl: ['Barre EZ prise serrée, coudes au corps.', 'Fléchis sans bouger les coudes, contrôle la descente.', 'Dos cambré pour aider.'],
  tri_pushdown: ['Face à la poulie haute, coudes collés aux côtes.', 'Tends complètement les bras, remonte jusqu’à 90°.', 'Coudes qui bougent, buste au-dessus de la charge.'],
  oh_tri: ['Haltère ou corde au-dessus de la tête, coudes vers le plafond.', 'Descends derrière la tête puis tends les bras.', 'Coudes qui s’écartent.'],
  diamond_pushup: ['Mains rapprochées sous la poitrine (index et pouces en losange).', 'Coudes le long du corps, poitrine vers les mains.', 'Bassin qui tombe.'],
  bench_dips: ['Mains sur un banc derrière toi, jambes devant.', 'Descends jusqu’à bras à 90°, pousse avec les triceps.', 'Descendre trop bas (épaules).'],
  back_squat: ['Barre sur les trapèzes, pieds largeur d’épaules, pointes légèrement ouvertes.', 'Descends hanches en arrière, genoux dans l’axe des pieds, au moins cuisses parallèles. Pousse le sol.', 'Genoux qui rentrent, talons qui décollent, dos rond en bas.'],
  front_squat: ['Barre sur l’avant des épaules, coudes hauts.', 'Descends buste droit, genoux vers l’avant.', 'Coudes qui tombent.'],
  goblet_squat: ['Haltère contre la poitrine, pieds un peu écartés.', 'Descends entre les talons, buste droit, coudes entre les genoux.', 'Talons qui décollent.'],
  leg_press: ['Dos plaqué, pieds largeur d’épaules au milieu du plateau.', 'Descends jusqu’à 90° aux genoux, pousse avec les talons.', 'Fesses qui décollent, genoux verrouillés en haut.'],
  bss: ['Pied arrière sur un banc, pied avant à ~1 m.', 'Descends le genou arrière vers le sol, buste légèrement penché, pousse avec la jambe avant.', 'Genou avant qui rentre, pied avant trop près.'],
  lunge: ['Grand pas en avant, buste droit.', 'Les deux genoux à 90°, pousse avec le talon avant.', 'Genou avant qui dépasse beaucoup et rentre.'],
  bw_squat: ['Pieds largeur d’épaules, bras devant.', 'Tempo : 3 s pour descendre, 1 s en bas, 1 s pour remonter.', 'Talons qui décollent.'],
  pistol: ['Sur une jambe, l’autre tendue devant, tiens un support.', 'Descends le plus bas possible en contrôlant.', 'Genou qui rentre.'],
  leg_ext: ['Dos calé, rouleau sur le bas des tibias.', 'Tends les jambes, marque 1 s en haut, descente lente.', 'Élan.'],
  deadlift: ['Barre contre les tibias, pieds largeur de hanches, dos plat, épaules au-dessus de la barre.', 'Pousse le sol, la barre frôle les jambes, verrouille hanches et genoux ensemble.', 'Dos rond, barre éloignée du corps.'],
  rdl: ['Debout, barre en main, genoux légèrement fléchis.', 'Recule les hanches, barre le long des cuisses jusqu’à mi-tibia, dos plat, remonte en serrant les fessiers.', 'Plier les genoux (devient un squat), dos rond.'],
  db_rdl: ['Haltères devant les cuisses, genoux souples.', 'Hanches en arrière, dos plat, étirement des ischios.', 'Dos rond.'],
  sl_rdl: ['Sur une jambe, haltère dans la main opposée.', 'Bascule le buste, jambe libre tendue derrière, hanches à niveau.', 'Hanche qui s’ouvre.'],
  leg_curl: ['Rouleau au-dessus des talons, hanches calées.', 'Ramène les talons vers les fesses, descente lente.', 'Hanches qui décollent.'],
  nordic: ['À genoux, chevilles bloquées.', 'Descends le buste en avant le plus lentement possible, rattrape-toi avec les mains.', 'Casser au niveau des hanches.'],
  hip_thrust: ['Haut du dos sur un banc, barre (avec mousse) sur les hanches.', 'Pousse les hanches vers le haut jusqu’à l’alignement, serre les fessiers 1 s.', 'Cambrer le bas du dos au lieu de serrer les fessiers.'],
  glute_bridge: ['Allongé, un pied au sol, l’autre jambe en l’air.', 'Monte le bassin en poussant dans le talon, serre le fessier.', 'Cambrer.'],
  calf_raise: ['Avant des pieds sur une marche.', 'Monte au maximum, tiens 1 s, descends talons sous la marche.', 'Rebondir.'],
  plank: ['Avant-bras au sol, coudes sous les épaules.', 'Corps droit, serre fessiers et abdos, respire.', 'Fesses trop hautes ou bassin qui tombe.'],
  side_plank: ['Sur le côté, coude sous l’épaule.', 'Bassin haut, corps aligné.', 'Bassin qui descend.'],
  hanging_raise: ['Suspendu à la barre, épaules engagées.', 'Monte les genoux (ou jambes tendues) en enroulant le bassin.', 'Balancer.'],
  ab_wheel: ['À genoux, roue sous les épaules.', 'Roule en avant en gardant le dos plat, reviens en contractant les abdos.', 'Dos qui se creuse.'],
  dead_bug: ['Sur le dos, bras vers le plafond, genoux à 90°.', 'Allonge bras et jambe opposés, bas du dos collé au sol.', 'Dos qui décolle.'],
  pallof: ['De profil à la poulie, poignée contre la poitrine.', 'Tends les bras devant toi sans laisser le buste tourner.', 'Rotation du buste.'],
  farmer: ['Charges lourdes dans chaque main, épaules basses.', 'Marche à petits pas, buste droit, gainé.', 'Se pencher d’un côté.'],
  run: ['Zone 2 : tu dois pouvoir parler en phrases complètes.', 'Petites foulées, atterrissage sous le corps.', 'Partir trop vite.'],
  bike: ['Selle à hauteur de hanche, jambe presque tendue en bas.', 'Cadence 80–95 tours/min en zone 2.', 'Selle trop basse.'],
  rower: ['Ordre : jambes → buste → bras, retour bras → buste → jambes.', 'La poussée des jambes fait 60 % du travail.', 'Tirer d’abord avec les bras.'],
  incline_walk: ['Tapis incliné 8–12 %, vitesse 5–6 km/h.', 'Ne pas tenir les barres.', 'Se suspendre aux poignées.'],
  brisk_walk: ['Pas rapides, bras actifs.', 'Tu es un peu essoufflé mais peux parler.', ''],
  rope: ['Petits sauts sur l’avant des pieds, poignets qui tournent.', 'Coudes près du corps.', 'Sauter trop haut.'],
  hiit_bike: ['Effort : à fond, récupération : très facile.', 'Garde la même intensité sur tous les rounds.', 'Partir trop fort au 1er round.'],
  hiit_run: ['Sprint à ~90 %, récupération en marchant.', 'Échauffe-toi 5 min avant.', ''],
  hiit_rower: ['Effort intense, cadence 28–32.', 'Pousse fort avec les jambes.', ''],
  burpee_emom: ['Chaque minute : X burpees, repos le reste de la minute.', 'Poitrine au sol, saut avec mains au-dessus de la tête.', ''],
  kb_swing: ['Pieds largeur d’épaules, kettlebell entre les jambes.', 'Le mouvement vient des hanches (comme un saut), bras relâchés.', 'Squatter, tirer avec les bras.'],
  mountain: ['Position de pompe, corps gainé.', 'Ramène les genoux vers la poitrine en alternant, vite.', 'Fesses hautes.'],
};

export function exInfoSheet(exId, onSwap) {
  const ex = exById(exId, S.custom);
  const t = TECH[exId];
  const alts = alternatives(exId, S.profile?.equipment || 'salle', S.custom);
  const q = encodeURIComponent(ex.name + ' technique exécution');
  const w = sheet(`<h3>${esc(ex.name)}</h3><p class="muted">${esc(ex.muscle)}</p>
    ${t ? `<div class="tech"><div><b>📍 Position</b><p>${esc(t[0])}</p></div><div><b>✅ Points clés</b><p>${esc(t[1])}</p></div>${t[2] ? `<div><b>⚠️ À éviter</b><p>${esc(t[2])}</p></div>` : ''}</div>`
      : '<p class="small muted">Pas encore de fiche pour cet exercice.</p>'}
    <a class="btn ghost block" href="https://www.youtube.com/results?search_query=${q}" target="_blank" rel="noopener">▶ Voir la technique en vidéo</a>
    ${onSwap && alts.length ? `<h3 class="sec">Machine prise ? Équivalents</h3>${alts.map(a => `<button class="pick" data-alt="${a.id}"><b>${esc(a.name)}</b><small>${esc(a.muscle)}</small></button>`).join('')}` : ''}`);
  if (onSwap) w.addEventListener('click', (e) => { const b = e.target.closest('[data-alt]'); if (!b) return; w.close(); onSwap(exById(b.dataset.alt, S.custom)); });
  return w;
}
