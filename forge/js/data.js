// FORGE — bibliothèque d'exercices, aliments de base et générateur de programme hybride.

// eq : s = salle complète, m = maison (haltères, banc, barre de traction, élastiques), p = poids du corps
// kind : force | hyper | iso | core | cardio | hiit
// unit : kg (charge) | pdc (poids du corps, lest optionnel) | time (secondes) | cardio (minutes/distance)
export const EXERCISES = [
  // — Poussée horizontale
  { id: 'bench', name: 'Développé couché barre', muscle: 'Pectoraux', eq: 's', kind: 'force', unit: 'kg', inc: 2.5, met: 5 },
  { id: 'db_bench', name: 'Développé couché haltères', muscle: 'Pectoraux', eq: 'sm', kind: 'hyper', unit: 'kg', inc: 2, met: 5 },
  { id: 'incline_db', name: 'Développé incliné haltères', muscle: 'Pectoraux', eq: 'sm', kind: 'hyper', unit: 'kg', inc: 2, met: 5 },
  { id: 'incline_bench', name: 'Développé incliné barre', muscle: 'Pectoraux', eq: 's', kind: 'force', unit: 'kg', inc: 2.5, met: 5 },
  { id: 'dips', name: 'Dips', muscle: 'Pectoraux', eq: 'sm', kind: 'hyper', unit: 'pdc', inc: 2.5, met: 6 },
  { id: 'pushup', name: 'Pompes', muscle: 'Pectoraux', eq: 'smp', kind: 'hyper', unit: 'pdc', inc: 0, met: 6 },
  { id: 'decline_pushup', name: 'Pompes pieds surélevés', muscle: 'Pectoraux', eq: 'smp', kind: 'hyper', unit: 'pdc', inc: 0, met: 6 },
  { id: 'cable_fly', name: 'Écarté poulie vis-à-vis', muscle: 'Pectoraux', eq: 's', kind: 'iso', unit: 'kg', inc: 2.5, met: 4 },
  // — Tirage horizontal
  { id: 'barbell_row', name: 'Rowing barre', muscle: 'Dos', eq: 's', kind: 'force', unit: 'kg', inc: 2.5, met: 5 },
  { id: 'db_row', name: 'Rowing haltère un bras', muscle: 'Dos', eq: 'sm', kind: 'hyper', unit: 'kg', inc: 2, met: 5 },
  { id: 'cable_row', name: 'Tirage horizontal poulie', muscle: 'Dos', eq: 's', kind: 'hyper', unit: 'kg', inc: 2.5, met: 5 },
  { id: 'inverted_row', name: 'Rowing inversé (table / barre)', muscle: 'Dos', eq: 'smp', kind: 'hyper', unit: 'pdc', inc: 0, met: 5 },
  { id: 'face_pull', name: 'Face pull', muscle: 'Épaules', eq: 'sm', kind: 'iso', unit: 'kg', inc: 2.5, met: 4 },
  // — Tirage vertical
  { id: 'pullup', name: 'Tractions', muscle: 'Dos', eq: 'smp', kind: 'force', unit: 'pdc', inc: 2.5, met: 8 },
  { id: 'chinup', name: 'Tractions supination', muscle: 'Dos', eq: 'smp', kind: 'hyper', unit: 'pdc', inc: 2.5, met: 8 },
  { id: 'lat_pulldown', name: 'Tirage vertical poulie', muscle: 'Dos', eq: 's', kind: 'hyper', unit: 'kg', inc: 2.5, met: 5 },
  { id: 'band_pulldown', name: 'Tirage vertical élastique', muscle: 'Dos', eq: 'm', kind: 'hyper', unit: 'kg', inc: 0, met: 4 },
  // — Poussée verticale
  { id: 'ohp', name: 'Développé militaire barre', muscle: 'Épaules', eq: 's', kind: 'force', unit: 'kg', inc: 2.5, met: 5 },
  { id: 'db_ohp', name: 'Développé épaules haltères', muscle: 'Épaules', eq: 'sm', kind: 'hyper', unit: 'kg', inc: 2, met: 5 },
  { id: 'pike_pushup', name: 'Pompes piquées (pike)', muscle: 'Épaules', eq: 'smp', kind: 'hyper', unit: 'pdc', inc: 0, met: 6 },
  { id: 'lateral_raise', name: 'Élévations latérales', muscle: 'Épaules', eq: 'sm', kind: 'iso', unit: 'kg', inc: 1, met: 4 },
  { id: 'rear_delt', name: 'Oiseau (deltoïde postérieur)', muscle: 'Épaules', eq: 'sm', kind: 'iso', unit: 'kg', inc: 1, met: 4 },
  // — Bras
  { id: 'db_curl', name: 'Curl haltères', muscle: 'Biceps', eq: 'sm', kind: 'iso', unit: 'kg', inc: 1, met: 4 },
  { id: 'hammer_curl', name: 'Curl marteau', muscle: 'Biceps', eq: 'sm', kind: 'iso', unit: 'kg', inc: 1, met: 4 },
  { id: 'ez_curl', name: 'Curl barre EZ', muscle: 'Biceps', eq: 's', kind: 'iso', unit: 'kg', inc: 2.5, met: 4 },
  { id: 'tri_pushdown', name: 'Extension triceps poulie', muscle: 'Triceps', eq: 's', kind: 'iso', unit: 'kg', inc: 2.5, met: 4 },
  { id: 'oh_tri', name: 'Extension triceps au-dessus de la tête', muscle: 'Triceps', eq: 'sm', kind: 'iso', unit: 'kg', inc: 1, met: 4 },
  { id: 'diamond_pushup', name: 'Pompes diamant', muscle: 'Triceps', eq: 'smp', kind: 'iso', unit: 'pdc', inc: 0, met: 6 },
  { id: 'bench_dips', name: 'Dips sur banc', muscle: 'Triceps', eq: 'smp', kind: 'iso', unit: 'pdc', inc: 0, met: 5 },
  // — Jambes
  { id: 'back_squat', name: 'Squat barre', muscle: 'Quadriceps', eq: 's', kind: 'force', unit: 'kg', inc: 5, met: 6 },
  { id: 'front_squat', name: 'Front squat', muscle: 'Quadriceps', eq: 's', kind: 'force', unit: 'kg', inc: 2.5, met: 6 },
  { id: 'goblet_squat', name: 'Goblet squat', muscle: 'Quadriceps', eq: 'sm', kind: 'hyper', unit: 'kg', inc: 2, met: 6 },
  { id: 'leg_press', name: 'Presse à cuisses', muscle: 'Quadriceps', eq: 's', kind: 'hyper', unit: 'kg', inc: 10, met: 5 },
  { id: 'bss', name: 'Squat bulgare', muscle: 'Quadriceps', eq: 'smp', kind: 'hyper', unit: 'kg', inc: 2, met: 6 },
  { id: 'lunge', name: 'Fentes marchées', muscle: 'Quadriceps', eq: 'smp', kind: 'hyper', unit: 'kg', inc: 2, met: 6 },
  { id: 'bw_squat', name: 'Squat poids du corps tempo 3-1-1', muscle: 'Quadriceps', eq: 'smp', kind: 'hyper', unit: 'pdc', inc: 0, met: 5 },
  { id: 'pistol', name: 'Pistol squat assisté', muscle: 'Quadriceps', eq: 'smp', kind: 'force', unit: 'pdc', inc: 0, met: 6 },
  { id: 'leg_ext', name: 'Leg extension', muscle: 'Quadriceps', eq: 's', kind: 'iso', unit: 'kg', inc: 5, met: 4 },
  { id: 'deadlift', name: 'Soulevé de terre', muscle: 'Ischios / Dos', eq: 's', kind: 'force', unit: 'kg', inc: 5, met: 6 },
  { id: 'rdl', name: 'Soulevé de terre roumain', muscle: 'Ischios', eq: 's', kind: 'hyper', unit: 'kg', inc: 2.5, met: 6 },
  { id: 'db_rdl', name: 'Soulevé roumain haltères', muscle: 'Ischios', eq: 'sm', kind: 'hyper', unit: 'kg', inc: 2, met: 6 },
  { id: 'sl_rdl', name: 'Soulevé roumain unijambe', muscle: 'Ischios', eq: 'smp', kind: 'hyper', unit: 'kg', inc: 2, met: 5 },
  { id: 'leg_curl', name: 'Leg curl', muscle: 'Ischios', eq: 's', kind: 'iso', unit: 'kg', inc: 5, met: 4 },
  { id: 'nordic', name: 'Nordic curl (assisté)', muscle: 'Ischios', eq: 'smp', kind: 'iso', unit: 'pdc', inc: 0, met: 5 },
  { id: 'hip_thrust', name: 'Hip thrust', muscle: 'Fessiers', eq: 'sm', kind: 'hyper', unit: 'kg', inc: 5, met: 5 },
  { id: 'glute_bridge', name: 'Pont fessier unijambe', muscle: 'Fessiers', eq: 'smp', kind: 'hyper', unit: 'pdc', inc: 0, met: 4 },
  { id: 'calf_raise', name: 'Mollets debout', muscle: 'Mollets', eq: 'smp', kind: 'iso', unit: 'kg', inc: 2.5, met: 4 },
  // — Gainage
  { id: 'plank', name: 'Planche', muscle: 'Abdos', eq: 'smp', kind: 'core', unit: 'time', inc: 0, met: 4 },
  { id: 'side_plank', name: 'Planche latérale', muscle: 'Abdos', eq: 'smp', kind: 'core', unit: 'time', inc: 0, met: 4 },
  { id: 'hanging_raise', name: 'Relevés de jambes suspendu', muscle: 'Abdos', eq: 'smp', kind: 'core', unit: 'pdc', inc: 0, met: 4 },
  { id: 'ab_wheel', name: 'Roulette abdominale', muscle: 'Abdos', eq: 'sm', kind: 'core', unit: 'pdc', inc: 0, met: 4 },
  { id: 'dead_bug', name: 'Dead bug', muscle: 'Abdos', eq: 'smp', kind: 'core', unit: 'pdc', inc: 0, met: 3 },
  { id: 'pallof', name: 'Pallof press', muscle: 'Abdos', eq: 'sm', kind: 'core', unit: 'kg', inc: 2.5, met: 3 },
  { id: 'farmer', name: 'Marche du fermier', muscle: 'Corps entier', eq: 'sm', kind: 'core', unit: 'kg', inc: 2, met: 6 },
  // — Cardio / conditioning
  { id: 'run', name: 'Course à pied', muscle: 'Cardio', eq: 'smp', kind: 'cardio', unit: 'cardio', met: 9 },
  { id: 'bike', name: 'Vélo', muscle: 'Cardio', eq: 'smp', kind: 'cardio', unit: 'cardio', met: 7 },
  { id: 'rower', name: 'Rameur', muscle: 'Cardio', eq: 's', kind: 'cardio', unit: 'cardio', met: 7 },
  { id: 'incline_walk', name: 'Marche inclinée tapis', muscle: 'Cardio', eq: 's', kind: 'cardio', unit: 'cardio', met: 6 },
  { id: 'brisk_walk', name: 'Marche rapide', muscle: 'Cardio', eq: 'smp', kind: 'cardio', unit: 'cardio', met: 4.5 },
  { id: 'rope', name: 'Corde à sauter', muscle: 'Cardio', eq: 'smp', kind: 'cardio', unit: 'cardio', met: 11 },
  { id: 'hiit_bike', name: 'Fractionné vélo / air bike', muscle: 'HIIT', eq: 'sm', kind: 'hiit', unit: 'time', met: 10 },
  { id: 'hiit_run', name: 'Fractionné course', muscle: 'HIIT', eq: 'smp', kind: 'hiit', unit: 'time', met: 11 },
  { id: 'hiit_rower', name: 'Fractionné rameur', muscle: 'HIIT', eq: 's', kind: 'hiit', unit: 'time', met: 10 },
  { id: 'burpee_emom', name: 'Burpees (EMOM)', muscle: 'HIIT', eq: 'smp', kind: 'hiit', unit: 'time', met: 10 },
  { id: 'kb_swing', name: 'Kettlebell swing', muscle: 'HIIT', eq: 'sm', kind: 'hiit', unit: 'time', met: 9 },
  { id: 'mountain', name: 'Mountain climbers', muscle: 'HIIT', eq: 'smp', kind: 'hiit', unit: 'time', met: 8 },
];

export const MUSCLES = ['Pectoraux', 'Dos', 'Épaules', 'Biceps', 'Triceps', 'Quadriceps', 'Ischios', 'Ischios / Dos', 'Fessiers', 'Mollets', 'Abdos', 'Corps entier', 'Cardio', 'HIIT'];

// Créneaux : liste ordonnée de candidats, on prend le premier compatible avec le matériel.
const SLOT = {
  hpush_f: ['bench', 'db_bench', 'decline_pushup'],
  hpush_h: ['incline_db', 'db_bench', 'pushup'],
  vpush_f: ['ohp', 'db_ohp', 'pike_pushup'],
  vpush_h: ['db_ohp', 'pike_pushup'],
  hpull_f: ['barbell_row', 'db_row', 'inverted_row'],
  hpull_h: ['cable_row', 'db_row', 'inverted_row'],
  vpull_f: ['pullup', 'inverted_row'],
  vpull_h: ['lat_pulldown', 'chinup', 'band_pulldown', 'inverted_row'],
  squat_f: ['back_squat', 'goblet_squat', 'pistol'],
  squat_h: ['leg_press', 'goblet_squat', 'bw_squat'],
  hinge_f: ['deadlift', 'db_rdl', 'sl_rdl'],
  hinge_h: ['rdl', 'db_rdl', 'sl_rdl'],
  single: ['bss', 'lunge'],
  hamcurl: ['leg_curl', 'nordic'],
  glute: ['hip_thrust', 'glute_bridge'],
  calf: ['calf_raise'],
  lateral: ['lateral_raise', 'pike_pushup'],
  rear: ['face_pull', 'rear_delt', 'inverted_row'],
  biceps: ['ez_curl', 'db_curl', 'chinup'],
  biceps2: ['hammer_curl', 'db_curl', 'chinup'],
  triceps: ['tri_pushdown', 'oh_tri', 'diamond_pushup'],
  triceps2: ['oh_tri', 'diamond_pushup', 'bench_dips'],
  fly: ['cable_fly', 'dips', 'decline_pushup'],
  core1: ['hanging_raise', 'ab_wheel', 'dead_bug'],
  core2: ['plank', 'side_plank'],
  core3: ['pallof', 'farmer', 'side_plank', 'dead_bug'],
  z2: ['incline_walk', 'bike', 'run', 'brisk_walk'],
  z2_long: ['run', 'bike', 'rower', 'brisk_walk'],
  hiit: ['hiit_rower', 'hiit_bike', 'hiit_run', 'burpee_emom'],
  metcon: ['kb_swing', 'burpee_emom', 'mountain'],
  rope: ['rope', 'mountain'],
};

// Prescriptions de base par rôle (bloc 1).
const ROLE = {
  force: { sets: 4, repMin: 4, repMax: 6, rest: 150 },
  hyper: { sets: 3, repMin: 8, repMax: 12, rest: 90 },
  iso: { sets: 3, repMin: 12, repMax: 15, rest: 60 },
  core: { sets: 3, repMin: 10, repMax: 15, rest: 45, secs: 40 },
  cardio: { minutes: 35, zone: 2 },
  hiit: { rounds: 8, work: 30, restWork: 90 },
};

const DAY_TEMPLATES = {
  upper_force: { name: 'Haut du corps — Force', focus: 'Force', slots: [['hpush_f', 'force'], ['vpull_f', 'force'], ['vpush_f', 'hyper'], ['hpull_f', 'hyper'], ['triceps', 'iso'], ['core1', 'core']] },
  lower_force: { name: 'Bas du corps — Force', focus: 'Force', slots: [['squat_f', 'force'], ['hinge_f', 'force'], ['single', 'hyper'], ['calf', 'iso'], ['core2', 'core']] },
  upper_hyper: { name: 'Haut du corps — Volume + HIIT', focus: 'Muscle & tonus', slots: [['hpush_h', 'hyper'], ['vpull_h', 'hyper'], ['hpull_h', 'hyper'], ['lateral', 'iso'], ['biceps', 'iso'], ['triceps2', 'iso'], ['hiit', 'hiit']] },
  lower_hyper: { name: 'Bas du corps — Volume + Endurance', focus: 'Muscle & endurance', slots: [['hinge_h', 'hyper'], ['squat_h', 'hyper'], ['glute', 'hyper'], ['hamcurl', 'iso'], ['calf', 'iso'], ['z2', 'cardio']] },
  full_force: { name: 'Full body — Force', focus: 'Force', slots: [['squat_f', 'force'], ['hpush_f', 'force'], ['hpull_f', 'force'], ['hinge_h', 'hyper'], ['core1', 'core']] },
  full_hyper: { name: 'Full body — Volume + HIIT', focus: 'Muscle & tonus', slots: [['single', 'hyper'], ['hpush_h', 'hyper'], ['vpull_h', 'hyper'], ['lateral', 'iso'], ['biceps2', 'iso'], ['triceps', 'iso'], ['hiit', 'hiit']] },
  full_c: { name: 'Full body — Métabolique', focus: 'Force & cardio', slots: [['hinge_f', 'force'], ['hpush_h', 'hyper'], ['hpull_h', 'hyper'], ['single', 'hyper'], ['core3', 'core'], ['metcon', 'hiit']] },
  push: { name: 'Push — Pecs, épaules, triceps', focus: 'Muscle', slots: [['hpush_f', 'force'], ['vpush_h', 'hyper'], ['hpush_h', 'hyper'], ['lateral', 'iso'], ['triceps', 'iso'], ['hiit', 'hiit']] },
  pull: { name: 'Pull — Dos, biceps', focus: 'Muscle', slots: [['vpull_f', 'force'], ['hpull_f', 'hyper'], ['vpull_h', 'hyper'], ['rear', 'iso'], ['biceps', 'iso'], ['biceps2', 'iso'], ['core1', 'core']] },
  legs: { name: 'Legs — Jambes, fessiers', focus: 'Force & muscle', slots: [['squat_f', 'force'], ['hinge_h', 'hyper'], ['single', 'hyper'], ['hamcurl', 'iso'], ['calf', 'iso'], ['core2', 'core']] },
  cardio_z2: { name: 'Endurance zone 2 + Gainage', focus: 'Cardio & endurance', slots: [['z2_long', 'cardio'], ['core3', 'core'], ['core2', 'core']] },
  hiit_day: { name: 'HIIT + Gainage', focus: 'Cardio & sèche', slots: [['hiit', 'hiit'], ['metcon', 'hiit'], ['core1', 'core'], ['core2', 'core'], ['z2', 'cardio']] },
  conditioning: { name: 'Conditioning — Circuit métabolique', focus: 'Cardio & sèche', slots: [['metcon', 'hiit'], ['single', 'hyper'], ['pushup_any', 'hyper'], ['rear', 'iso'], ['rope', 'cardio'], ['core1', 'core']] },
  arms_shoulders: { name: 'Épaules & bras — Pump', focus: 'Tonus', slots: [['vpush_h', 'hyper'], ['lateral', 'iso'], ['rear', 'iso'], ['fly', 'iso'], ['biceps2', 'iso'], ['triceps', 'iso'], ['z2', 'cardio']] },
};
SLOT.pushup_any = ['pushup', 'decline_pushup'];

// Programmes prédéfinis : liste de séances selon le nombre de jours.
export const PRESETS = {
  hybride: { label: 'Hybride complet', desc: 'Force + muscle + HIIT + endurance. Le plus polyvalent pour un corps complet.', split: (n) => ({ 1: ['full_c'], 2: ['full_force', 'full_hyper'], 3: ['full_force', 'full_hyper', 'cardio_z2'], 4: ['upper_force', 'lower_force', 'upper_hyper', 'lower_hyper'], 5: ['upper_force', 'lower_force', 'cardio_z2', 'upper_hyper', 'lower_hyper'], 6: ['upper_force', 'lower_force', 'conditioning', 'upper_hyper', 'lower_hyper', 'cardio_z2'], 7: ['upper_force', 'lower_force', 'conditioning', 'upper_hyper', 'lower_hyper', 'cardio_z2', 'hiit_day'] })[n] },
  fullbody: { label: 'Full body', desc: 'Tout le corps à chaque séance. Idéal avec 2 à 3 jours ou peu de temps.', split: (n) => Array.from({ length: n }, (_, i) => ['full_force', 'full_hyper', 'full_c'][i % 3]) },
  upperlower: { label: 'Haut / Bas', desc: 'Haut du corps et bas du corps en alternance. Excellent pour la force et le muscle.', split: (n) => Array.from({ length: n }, (_, i) => ['upper_force', 'lower_force', 'upper_hyper', 'lower_hyper', 'cardio_z2', 'conditioning', 'hiit_day'][i]) },
  ppl: { label: 'Push / Pull / Legs', desc: 'Pousser, tirer, jambes. Pour maximiser la prise de muscle avec 3 ou 6 jours.', split: (n) => n <= 2 ? ['full_force', 'full_hyper'].slice(0, n) : Array.from({ length: n }, (_, i) => ['push', 'pull', 'legs', 'push', 'pull', 'legs', 'cardio_z2'][i]) },
  seche: { label: 'Sèche / brûle-graisse', desc: 'Musculation pour garder le muscle + beaucoup de cardio et de circuits.', split: (n) => ['full_force', 'conditioning', 'full_hyper', 'cardio_z2', 'hiit_day', 'lower_hyper', 'cardio_z2'].slice(0, n) },
  endurance: { label: 'Endurance + renfo', desc: 'Priorité cardio (course, vélo, rameur) avec 2 séances de renforcement.', split: (n) => ['cardio_z2', 'full_force', 'hiit_day', 'cardio_z2', 'full_hyper', 'cardio_z2', 'hiit_day'].slice(0, n) },
};

export const WEEKDAY_LONG = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];

export const exById = (id, custom = []) => EXERCISES.find(e => e.id === id) || custom.find(e => e.id === id);

function eqAllowed(ex, equipment) {
  const want = equipment === 'salle' ? 's' : equipment === 'maison' ? 'm' : 'p';
  if (want === 's') return true; // en salle tout est faisable
  return ex.eq.includes(want);
}

function pick(slot, equipment, used) {
  const list = SLOT[slot] || [];
  for (const id of list) {
    const ex = exById(id);
    if (ex && eqAllowed(ex, equipment) && !used.has(id)) return ex;
  }
  for (const id of list) { const ex = exById(id); if (ex && eqAllowed(ex, equipment)) return ex; }
  return null;
}

export function makeItem(ex, role) {
  const r = ROLE[role] || ROLE.hyper;
  const base = { exId: ex.id, role };
  if (role === 'cardio') return { ...base, minutes: r.minutes, zone: r.zone };
  if (role === 'hiit') return { ...base, rounds: r.rounds, work: r.work, restWork: r.restWork };
  if (role === 'core' && ex.unit === 'time') return { ...base, sets: r.sets, secs: r.secs, rest: r.rest };
  return { ...base, sets: r.sets, repMin: r.repMin, repMax: r.repMax, rest: r.rest };
}

// ————— Durée estimée —————
export function itemMinutes(it) {
  if (it.role === 'cardio') return +it.minutes || 0;
  if (it.role === 'hiit') return ((+it.rounds || 0) * ((+it.work || 0) + (+it.restWork || 0))) / 60 + 1;
  const sets = +it.sets || 0;
  const work = it.secs ? +it.secs : (((+it.repMin || 8) + (+it.repMax || 12)) / 2) * 3.5;
  return (sets * (work + (+it.rest || 60))) / 60 + (it.role === 'force' ? 2.5 : 1); // + séries d'approche / installation
}
export const WARMUP = 7;
// Durée de la semaine la plus chargée du cycle (les blocs 2 et 3 ajoutent des séries) : c'est ce maximum qui doit tenir.
const BLOCK_INFOS = [{ block: 1 }, { block: 2 }, { block: 3 }];
export function itemsMinutes(items, periodize = true) {
  const infos = periodize ? BLOCK_INFOS : [{ off: true }];
  return Math.round(Math.max(...infos.map(info => WARMUP + items.reduce((a, it) => a + itemMinutes(applyBlock(it, info)), 0))));
}
export const dayMinutes = (day, periodize = true) => itemsMinutes(day.items, periodize);

// Ajuste une séance pour tenir dans le temps maximum.
function fitDay(items, budget, isCardioDay, goal, { grow = true, periodize = true } = {}) {
  const est = () => itemsMinutes(items, periodize);
  if (isCardioDay) {
    const other = items.filter(i => i.role !== 'cardio').reduce((a, it) => a + itemMinutes(it), 0);
    const c = items.find(i => i.role === 'cardio');
    if (c) {
      const want = Math.max(15, Math.min(75, Math.round((budget - WARMUP - other) / (periodize ? 1.15 : 1) / 5) * 5));
      c.minutes = grow ? want : Math.min(c.minutes, want);
      while (est() > budget && c.minutes > 10) c.minutes -= 5;
    }
    while (est() > budget && items.filter(i => i.role === 'core').length > 1) items.splice(items.findLastIndex(i => i.role === 'core'), 1);
    return items;
  }
  if (budget <= 40) for (const i of items) { // séance express : repos courts, enchaînements
    if (i.role === 'force') { i.sets = Math.min(i.sets, 3); i.rest = 90; }
    if (i.role === 'hyper' || i.role === 'iso') { i.sets = Math.min(i.sets, 3); i.rest = 50; }
    if (i.role === 'core') i.rest = 30;
  }
  const steps = [
    () => { const c = items.find(i => i.role === 'cardio' && i.minutes > 8); if (c) { c.minutes = Math.max(8, c.minutes - 5); return true; } },
    () => { const h = items.find(i => i.role === 'hiit' && i.rounds > 6); if (h) { h.rounds -= 2; return true; } },
    () => { if (items.filter(i => i.role === 'iso').length > 1) { items.splice(items.findLastIndex(i => i.role === 'iso'), 1); return true; } },
    () => { const x = items.find(i => (i.role === 'hyper' || i.role === 'iso') && i.rest > 60); if (x) { x.rest -= 15; return true; } },
    () => { const x = items.find(i => i.role === 'force' && i.rest > 120); if (x) { x.rest -= 30; return true; } },
    () => { const x = items.find(i => (i.role === 'hyper' || i.role === 'iso' || i.role === 'core') && i.sets > 2); if (x) { x.sets--; return true; } },
    () => { const c = items.find(i => i.role === 'cardio'); if (c) { items.splice(items.indexOf(c), 1); return true; } },
    () => { if (items.filter(i => i.role === 'core').length > 0 && items.length > 3) { items.splice(items.findLastIndex(i => i.role === 'core'), 1); return true; } },
    () => { const x = items.find(i => i.role === 'force' && i.sets > 3); if (x) { x.sets--; return true; } },
    () => { const h = items.find(i => i.role === 'hiit' && i.rounds > 4); if (h) { h.rounds -= 2; return true; } },
    () => { if (budget <= 40) { const x = items.find(i => i.sets > 2); if (x) { x.sets--; return true; } } },
    () => { if (items.length > 2) { const i = items.findLastIndex(x => x.role !== 'force'); items.splice(i >= 0 ? i : items.length - 1, 1); return true; } },
  ];
  let guard = 0;
  while (est() > budget && guard++ < 200) { if (!steps.some(s => s())) break; }
  // du temps en plus : on enrichit (séries, finisher cardio)
  guard = 0;
  while (grow && budget - est() >= 6 && guard++ < 20) {
    const x = items.find(i => (i.role === 'hyper' && i.sets < 4) || (i.role === 'force' && i.sets < 5));
    if (x && budget - est() >= 4) { x.sets++; continue; }
    const c = items.find(i => i.role === 'cardio');
    if (c && c.minutes < 30) { c.minutes += 5; continue; }
    if (!c && budget - est() >= 10) { const ex = exById(goal === 'prise' ? 'brisk_walk' : 'incline_walk') || exById('brisk_walk'); items.push({ ...makeItem(ex, 'cardio'), minutes: Math.min(20, Math.floor((budget - est()) / 5) * 5) }); continue; }
    break;
  }
  return items;
}

// opts : preset, minutes (durée max), trainingDays (jours de la semaine 0=lundi)
export function generateProgram(profile, opts = {}) {
  const tdays = (opts.trainingDays || profile.trainingDays || []).slice().sort((a, b) => a - b);
  const n = Math.min(7, Math.max(1, tdays.length || Number(profile.days) || 4));
  const equipment = profile.equipment || 'salle';
  const level = profile.level || 'inter';
  const presetId = opts.preset || profile.preset || 'hybride';
  const preset = PRESETS[presetId] || PRESETS.hybride;
  const budget = +(opts.minutes || profile.sessionMinutes || 60);
  const split = preset.split(n) || PRESETS.hybride.split(n);
  const program = {
    id: 'p' + Date.now(),
    name: `${preset.label} · ${n} j · ${budget} min — ${equipment === 'salle' ? 'Salle' : equipment === 'maison' ? 'Maison' : 'Poids du corps'}`,
    created: new Date().toISOString(),
    startDate: new Date().toISOString().slice(0, 10),
    weeks: 12, preset: presetId, minutes: budget, schedule: tdays.length ? tdays : null,
    days: [],
  };
  split.forEach((tpl, i) => {
    const t = DAY_TEMPLATES[tpl];
    const used = new Set();
    let items = [];
    for (const [slot, role] of t.slots) {
      const ex = pick(slot, equipment, used);
      if (!ex) continue;
      used.add(ex.id);
      const item = makeItem(ex, role);
      if (level === 'debutant' && item.sets) item.sets = Math.max(2, item.sets - 1);
      if (level === 'debutant' && role === 'force') { item.repMin = 6; item.repMax = 8; item.rest = 120; }
      if (level === 'avance' && role === 'hyper') item.sets = 4;
      if (role === 'cardio' && tpl !== 'cardio_z2') item.minutes = 15;
      if (tpl === 'conditioning' && role === 'cardio') item.minutes = 8;
      if ((profile.goal === 'seche' || profile.goal === 'perte') && role === 'cardio') item.minutes += 5;
      items.push(item);
    }
    items = fitDay(items, budget, tpl === 'cardio_z2', profile.goal);
    const wd = tdays[i];
    program.days.push({ id: 'd' + i + '_' + Date.now().toString(36), name: `${wd != null ? WEEKDAY_LONG[wd] : 'J' + (i + 1)} · ${t.name}`, focus: t.focus, items, weekday: wd ?? null });
  });
  return program;
}

// Ajuste un programme existant (modifié ou non) à un temps max par séance, sans rien ajouter.
export function fitProgramToTime(program, minutes, goal) {
  const periodize = program.periodize !== false;
  for (const d of program.days) {
    const cardioDay = d.items.some(i => i.role === 'cardio') && d.items.every(i => i.role === 'cardio' || i.role === 'core');
    d.items = fitDay(d.items, minutes, cardioDay, goal, { grow: false, periodize });
  }
  program.minutes = minutes;
  return program;
}
export function fitDayToTime(day, minutes, goal, periodize = true) {
  const cardioDay = day.items.some(i => i.role === 'cardio') && day.items.every(i => i.role === 'cardio' || i.role === 'core');
  day.items = fitDay(day.items, minutes, cardioDay, goal, { grow: false, periodize });
  return day;
}

// Séance prévue un jour donné (selon les jours de la semaine du programme).
export function dayForDate(program, date = new Date()) {
  if (!program) return null;
  const wd = (date.getDay() + 6) % 7;
  return program.days.find(d => d.weekday === wd) || null;
}

// Périodisation 12 semaines : 3 blocs de 4 semaines, la 4e = décharge.
export function weekInfo(program, date = new Date()) {
  if (!program) return { week: 1, block: 1, phase: 'Accumulation', deload: false };
  const start = new Date(program.startDate + 'T00:00:00');
  const diff = Math.floor((date - start) / 86400000);
  const total = program.weeks || 12;
  const week = Math.min(total, Math.max(1, Math.floor(diff / 7) + 1));
  const block = Math.min(3, Math.ceil(week / 4));
  if (program.periodize === false) return { week, block: 1, phase: 'Programme libre', deload: false, total, off: true };
  const deload = week % 4 === 0;
  const phase = deload ? 'Décharge' : ['Accumulation', 'Intensification', 'Réalisation'][block - 1];
  return { week, block, phase, deload, total };
}

// Applique le bloc en cours à une prescription.
export function applyBlock(item, info) {
  const it = { ...item };
  if (info.off) return it;
  if (it.role === 'cardio' || it.role === 'hiit') {
    if (it.role === 'hiit' && info.block >= 2 && !info.deload) it.rounds = (it.rounds || 8) + 2;
    if (it.role === 'cardio' && info.block >= 2 && !info.deload) it.minutes = Math.round((it.minutes || 30) * 1.15);
    if (info.deload) { if (it.rounds) it.rounds = Math.max(4, it.rounds - 3); if (it.minutes) it.minutes = Math.round(it.minutes * 0.7); }
    return it;
  }
  if (info.deload) { it.sets = Math.max(2, (it.sets || 3) - 1); it.note = 'Décharge : charges −10 %, garde 3 reps en réserve'; return it; }
  if (it.role === 'force' && it.repMin) {
    if (info.block === 2) { it.repMin = Math.max(3, it.repMin - 1); it.repMax = Math.max(4, it.repMax - 1); it.sets = (it.sets || 4) + 1; }
    if (info.block === 3) { it.repMin = 2; it.repMax = 4; it.sets = it.sets || 4; it.rest = Math.max(it.rest || 150, 180); }
  }
  if (it.role === 'hyper' && it.repMin) {
    if (info.block === 2) { it.repMin = Math.max(6, it.repMin - 2); it.repMax = Math.max(8, it.repMax - 2); }
    if (info.block === 3) { it.sets = (it.sets || 3) + 1; }
  }
  if (it.role === 'core' && it.secs && info.block >= 2) it.secs = it.secs + 10 * (info.block - 1);
  return it;
}

// Aliments de base (pour 100 g) disponibles hors-ligne.
export const BASE_FOODS = [
  ['Blanc de poulet cuit', 165, 31, 0, 3.6], ['Steak haché 5 %', 125, 21, 0, 5], ['Saumon', 208, 20, 0, 13], ['Thon au naturel', 116, 26, 0, 1],
  ['Œuf entier (1 = 60 g)', 143, 12.6, 0.7, 9.5], ['Blanc d’œuf', 52, 11, 0.7, 0.2], ['Skyr nature', 63, 11, 4, 0.2], ['Fromage blanc 0 %', 46, 7.5, 4, 0.1],
  ['Riz basmati cuit', 130, 2.7, 28, 0.3], ['Pâtes cuites', 157, 5.8, 30.9, 0.9], ['Patate douce cuite', 90, 2, 20.7, 0.2], ['Pomme de terre cuite', 87, 1.9, 20, 0.1],
  ['Flocons d’avoine', 372, 13.5, 58.7, 7], ['Pain complet', 247, 13, 41, 3.4], ['Quinoa cuit', 120, 4.4, 21.3, 1.9], ['Lentilles cuites', 116, 9, 20, 0.4],
  ['Brocoli', 34, 2.8, 7, 0.4], ['Haricots verts', 31, 1.8, 7, 0.2], ['Courgette', 17, 1.2, 3.1, 0.3], ['Épinards', 23, 2.9, 3.6, 0.4],
  ['Banane', 89, 1.1, 22.8, 0.3], ['Pomme', 52, 0.3, 13.8, 0.2], ['Fruits rouges', 50, 1, 12, 0.3], ['Avocat', 160, 2, 8.5, 14.7],
  ['Amandes', 579, 21, 21.6, 49.9], ['Beurre de cacahuète', 588, 25, 20, 50], ['Huile d’olive', 884, 0, 0, 100], ['Whey (dose 30 g)', 400, 80, 7, 6],
  ['Lait demi-écrémé', 46, 3.2, 4.8, 1.6], ['Emmental', 380, 28, 0, 29.5], ['Tofu', 144, 15.6, 2.8, 8.7], ['Chocolat noir 70 %', 598, 7.8, 45.9, 42.6],
].map(([name, kcal, p, c, f]) => ({ name, kcal, p, c, f, src: 'base' }));

export const MEALS = [['matin', 'Petit-déjeuner'], ['midi', 'Déjeuner'], ['collation', 'Collation'], ['soir', 'Dîner']];
