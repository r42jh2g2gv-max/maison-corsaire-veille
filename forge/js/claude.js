// FORGE — connexion à Claude.
// Deux voies :
//  1) Abonnement Claude (claude.ai) : l'app prépare un message avec tout ton contexte, tu le colles
//     dans l'app Claude, puis tu recolles la réponse ici. Aucun coût en plus de ton abonnement.
//  2) Clé API Anthropic (facturée à l'usage, séparée de l'abonnement) : le coach répond directement dans l'app.
import { kv } from './db.js';

const SDK_URL = 'https://cdn.jsdelivr.net/npm/@anthropic-ai/sdk@1.7.0/+esm';
let clientCache = null;

export async function getSettings() { return (await kv.get('settings')) || {}; }

async function client() {
  const s = await getSettings();
  if (!s.apiKey) throw new Error('Ajoute ta clé API Anthropic dans Profil → Claude pour utiliser le coach intégré.');
  if (clientCache && clientCache.key === s.apiKey) return clientCache.c;
  const mod = await import(SDK_URL);
  const Anthropic = mod.default || mod.Anthropic;
  const c = new Anthropic({ apiKey: s.apiKey, dangerouslyAllowBrowser: true });
  clientCache = { key: s.apiKey, c };
  return c;
}

async function model() { return (await getSettings()).model || 'claude-opus-5-5'; }

const SYSTEM = `Tu es le coach de FORGE, une application de suivi sportif et nutritionnel en français.
Tu es préparateur physique (entraînement hybride : force, hypertrophie, endurance, cardio) et diététicien du sport.
Tu tutoies l'utilisateur, tu es direct, concret et bienveillant. Réponses courtes et actionnables, avec chiffres (séries, reps, charges, kcal, grammes).
Pour les repas, privilégie des recettes réalisables au Thermomix (style Cookidoo) quand c'est pertinent, en donnant les macros par portion.
Ne pose pas de diagnostic médical ; en cas de douleur ou de pathologie, recommande un professionnel de santé.`;

function checkStop(msg) {
  if (msg.stop_reason === 'refusal') throw new Error('Claude a refusé cette demande.');
  if (msg.stop_reason === 'max_tokens') throw new Error('Réponse trop longue, coupée. Réessaie avec une demande plus courte.');
}

// Chat en streaming : onText reçoit chaque morceau de texte.
export async function chat(history, context, onText) {
  const c = await client();
  const stream = c.beta.messages.stream({
    model: await model(),
    max_tokens: 64000,
    betas: ['server-side-fallback-2026-07-01'],
    fallbacks: 'default',
    output_config: { effort: 'low' },
    system: [
      { type: 'text', text: SYSTEM, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: 'Données actuelles de l’utilisateur :\n' + context },
    ],
    messages: history,
  });
  stream.on('text', onText);
  const msg = await stream.finalMessage();
  checkStop(msg);
  return msg.content.filter(b => b.type === 'text').map(b => b.text).join('');
}

// Appel qui renvoie un JSON validé par un schéma (sorties structurées).
export async function structured(prompt, schema, context, { images = [], effort = 'medium' } = {}) {
  const c = await client();
  const content = [
    ...images.map(d => ({ type: 'image', source: { type: 'base64', media_type: d.type, data: d.data } })),
    { type: 'text', text: prompt },
  ];
  const stream = c.beta.messages.stream({
    model: await model(),
    max_tokens: 64000,
    betas: ['server-side-fallback-2026-07-01'],
    fallbacks: 'default',
    output_config: { effort, format: { type: 'json_schema', schema } },
    system: [
      { type: 'text', text: SYSTEM, cache_control: { type: 'ephemeral' } },
      { type: 'text', text: 'Données actuelles de l’utilisateur :\n' + context },
    ],
    messages: [{ role: 'user', content }],
  });
  const msg = await stream.finalMessage();
  checkStop(msg);
  const text = msg.content.filter(b => b.type === 'text').map(b => b.text).join('');
  return JSON.parse(text);
}

// — Schémas JSON partagés entre la voie API et la voie « copier-coller » —
const str = { type: 'string' }, num = { type: 'number' }, int = { type: 'integer' };
const obj = (properties, required = Object.keys(properties)) => ({ type: 'object', properties, required, additionalProperties: false });

export const PROGRAM_SCHEMA = obj({
  name: str,
  explanation: str,
  days: { type: 'array', items: obj({
    name: str, focus: str,
    items: { type: 'array', items: obj({
      exercise: str,
      role: { type: 'string', enum: ['force', 'hyper', 'iso', 'core', 'cardio', 'hiit'] },
      sets: int, repMin: int, repMax: int, rest: int, secs: int, minutes: int, rounds: int, work: int, restWork: int,
    }, ['exercise', 'role']) },
  }) },
});

export const RECIPES_SCHEMA = obj({
  recipes: { type: 'array', items: obj({
    name: str, portions: int, kcal: num, protein: num, carbs: num, fat: num,
    ingredients: { type: 'array', items: str },
    steps: { type: 'array', items: str },
    meal: { type: 'string', enum: ['matin', 'midi', 'collation', 'soir'] },
  }) },
});

export const FOOD_SCHEMA = obj({
  items: { type: 'array', items: obj({ name: str, grams: num, kcal: num, protein: num, carbs: num, fat: num }) },
  comment: str,
});

// Extrait un bloc JSON d'une réponse collée depuis claude.ai.
export function extractJSON(text) {
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const raw = fence ? fence[1] : text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1);
  return JSON.parse(raw);
}

export const FORMAT_HINT = {
  program: `Réponds avec un bloc \`\`\`json contenant : {"name": "...", "explanation": "...", "days": [{"name": "J1 · ...", "focus": "...", "items": [{"exercise": "Squat barre", "role": "force|hyper|iso|core|cardio|hiit", "sets": 4, "repMin": 4, "repMax": 6, "rest": 150}]}]}. Pour le cardio : {"exercise": "Course à pied", "role": "cardio", "minutes": 40}. Pour le fractionné : {"exercise": "Fractionné rameur", "role": "hiit", "rounds": 8, "work": 30, "restWork": 90}. Pour le gainage chronométré : "secs".`,
  recipes: `Réponds avec un bloc \`\`\`json contenant : {"recipes": [{"name": "...", "portions": 4, "kcal": 520, "protein": 42, "carbs": 50, "fat": 15, "ingredients": ["..."], "steps": ["Thermomix : 5 s / vitesse 5", "..."], "meal": "midi"}]} — kcal et macros PAR PORTION.`,
  food: `Réponds avec un bloc \`\`\`json contenant : {"items": [{"name": "...", "grams": 150, "kcal": 240, "protein": 30, "carbs": 5, "fat": 10}], "comment": "..."}.`,
};

export function fileToBase64(file, maxSide = 1280) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, maxSide / Math.max(img.width, img.height));
      const cv = document.createElement('canvas');
      cv.width = Math.round(img.width * k); cv.height = Math.round(img.height * k);
      cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
      const url = cv.toDataURL('image/jpeg', 0.85);
      URL.revokeObjectURL(img.src);
      resolve({ type: 'image/jpeg', data: url.split(',')[1] });
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}
