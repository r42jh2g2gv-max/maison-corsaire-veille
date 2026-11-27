// FORGE — écarts : alcool, fast-food, repas lourd, grignotage + plan de compensation.
import { S, esc, $, $$, toast, sheet, today, num, targets, bmr, defTime, mealTimeFields, bindMealTime } from './ui.js';
import { food, kv, uid } from './db.js';
import { MEALS } from './data.js';

// profils de macros (% des kcal hors alcool) : p, c, f
const PROFILE = { ff: [15, 45, 40], heavy: [18, 30, 52], sweet: [5, 58, 37], salty: [9, 40, 51], nuts: [18, 15, 67], drink: [0, 100, 0] };
// [nom, kcal, profil, grammes d'alcool]
const CATS = {
  alcool: { label: '🍺 Alcool', items: [
    ['Demi de bière (25 cl)', 105, 'drink', 10], ['Pinte de bière (50 cl)', 210, 'drink', 20], ['Bière forte / IPA (33 cl)', 200, 'drink', 18],
    ['Verre de vin (12 cl)', 85, 'drink', 11], ['Coupe de champagne', 80, 'drink', 9], ['Cidre (25 cl)', 100, 'drink', 9],
    ['Spritz', 160, 'drink', 12], ['Mojito', 220, 'drink', 14], ['Gin tonic', 160, 'drink', 13], ['Rhum / whisky-coca', 180, 'drink', 13],
    ['Whisky, rhum, vodka (4 cl)', 95, 'drink', 13], ['Shot (3 cl)', 70, 'drink', 10], ['Pastis (2 cl)', 55, 'drink', 6], ['Soda (33 cl)', 140, 'drink', 0],
  ] },
  fastfood: { label: '🍔 Fast-food', items: [
    ['Menu burger + frites + soda', 1100, 'ff', 0], ['Burger classique', 500, 'ff', 0], ['Frites moyennes', 340, 'salty', 0], ['6 nuggets', 270, 'ff', 0],
    ['Kebab sandwich', 750, 'ff', 0], ['Assiette kebab-frites', 1200, 'ff', 0], ['Tacos français (M)', 1100, 'ff', 0], ['Pizza entière', 1100, 'ff', 0],
    ['Part de pizza', 280, 'ff', 0], ['Box sushis (12 pièces)', 550, 'sweet', 0], ['Poulet frit (3 pièces)', 750, 'ff', 0], ['Sandwich jambon-beurre', 400, 'ff', 0],
  ] },
  lourd: { label: '🧀 Repas lourd', items: [
    ['Raclette (assiette complète)', 1100, 'heavy', 0], ['Fondue savoyarde', 1000, 'heavy', 0], ['Tartiflette (portion)', 800, 'heavy', 0],
    ['Burger + frites au resto', 1300, 'ff', 0], ['Entrée + plat + dessert resto', 1500, 'heavy', 0], ['Barbecue (saucisses, chips…)', 1000, 'heavy', 0],
    ['Grande assiette de pâtes carbo', 900, 'heavy', 0], ['Brunch complet', 1200, 'heavy', 0], ['Plateau de fromages (100 g)', 380, 'heavy', 0], ['Dessert (tiramisu, fondant…)', 450, 'sweet', 0],
  ] },
  grignotage: { label: '🍫 Grignotage', items: [
    ['Poignée de chips (30 g)', 160, 'salty', 0], ['Paquet de chips (150 g)', 800, 'salty', 0], ['Poignée de cacahuètes (30 g)', 180, 'nuts', 0],
    ['Gâteaux apéro (30 g)', 150, 'salty', 0], ['Saucisson (5 tranches)', 125, 'heavy', 0], ['Bonbons (50 g)', 170, 'sweet', 0],
    ['2 carrés de chocolat', 110, 'sweet', 0], ['Barre chocolatée', 250, 'sweet', 0], ['4 biscuits', 200, 'sweet', 0], ['Viennoiserie', 300, 'sweet', 0],
    ['Glace (2 boules)', 250, 'sweet', 0], ['Part de gâteau', 350, 'sweet', 0], ['Fromage (30 g)', 110, 'heavy', 0],
  ] },
};

function macros(kcal, prof, alc) {
  const rest = Math.max(0, kcal - alc * 7);
  const [p, c, f] = PROFILE[prof];
  return { p: +(rest * p / 100 / 4).toFixed(1), c: +(rest * c / 100 / 4).toFixed(1), f: +(rest * f / 100 / 9).toFixed(1) };
}

const shiftD = (d, n) => { const x = new Date(d + 'T12:00:00'); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); };

export function ecartSheet(date = today(), rerender) {
  let cat = 'alcool';
  const qty = {};
  const w = sheet(`<h3>🍻 Écart, soirée, fast-food</h3>
    <p class="muted small">Note-le sans culpabiliser : un écart compté est un écart maîtrisé.</p>
    <div class="chips" id="ecats">${Object.entries(CATS).map(([k, c]) => `<button class="chip ${k === cat ? 'on' : ''}" data-c="${k}">${c.label}</button>`).join('')}</div>
    <div id="eitems" class="eitems"></div>
    <div class="etotal" id="etot"></div>
    ${mealTimeFields('soir', defTime(date, 'soir'), ['emeal', 'etime'])}
    <button class="btn block" id="eadd">Ajouter au journal</button>`, { onClose: rerender });
  bindMealTime(w, ['emeal', 'etime']);
  const all = Object.values(CATS).flatMap(c => c.items);
  const total = () => Object.entries(qty).reduce((a, [n, q]) => { const it = all.find(x => x[0] === n); return { kcal: a.kcal + it[1] * q, alc: a.alc + it[3] * q }; }, { kcal: 0, alc: 0 });
  const draw = () => {
    $('#eitems', w).innerHTML = CATS[cat].items.map(([n, k]) => `<div class="eitem"><div class="grow"><b>${esc(n)}</b><small>${k} kcal</small></div>
      <button class="icon-btn sm" data-n="${esc(n)}" data-d="-1" aria-label="Moins">−</button><span class="eq">${qty[n] || 0}</span><button class="icon-btn sm" data-n="${esc(n)}" data-d="1" aria-label="Plus">+</button></div>`).join('');
    const t = total();
    $('#etot', w).innerHTML = t.kcal ? `<b>${Math.round(t.kcal)} kcal</b>${t.alc ? `<span>${num(t.alc / 10, 1)} unité${t.alc >= 20 ? 's' : ''} d’alcool (${Math.round(t.alc)} g)</span>` : ''}` : '<span class="muted">Ajoute ce que tu as mangé ou bu</span>';
  };
  draw();
  $('#ecats', w).onclick = (e) => { const b = e.target.closest('[data-c]'); if (!b) return; cat = b.dataset.c; $$('#ecats .chip', w).forEach(c => c.classList.toggle('on', c === b)); draw(); };
  $('#eitems', w).onclick = (e) => { const b = e.target.closest('[data-n]'); if (!b) return; const n = b.dataset.n; qty[n] = Math.max(0, (qty[n] || 0) + +b.dataset.d); if (!qty[n]) delete qty[n]; draw(); };
  $('#eadd', w).onclick = async () => {
    const t = total(); if (!t.kcal) return toast('Ajoute au moins un élément');
    const meal = $('#emeal', w).value, time = $('#etime', w).value || null;
    for (const [n, q] of Object.entries(qty)) {
      const it = all.find(x => x[0] === n), k = it[1] * q, m = macros(k, it[2], it[3] * q);
      await food.put({ id: uid('f'), date, meal, time, name: (q > 1 ? q + ' × ' : '') + n, kcal: k, ...m, alc: it[3] * q, ecart: true, src: 'ecart' });
    }
    w.close();
    setTimeout(() => compensation(date, t.alc, rerender), 280);
  };
}

// Combien je dépasse, et comment rattraper intelligemment
export async function compensation(date = today(), alc = 0, rerender) {
  const eaten = (await food.all()).filter(f => f.date === date).reduce((a, f) => a + (+f.kcal || 0), 0);
  const t = targets(S.profile, date);
  const over = Math.round(eaten - t.kcal);
  const kg = +S.profile?.weight || 75;
  const perMin = (met) => met * 3.5 * kg / 200;
  const alcDay = (await food.all()).filter(f => f.date === date).reduce((a, f) => a + (+f.alc || 0), 0) || alc;
  const floor = Math.round(bmr(S.profile) * 1.05);
  const tips = alcDay ? `<div class="note small">🍺 <b>${num(alcDay / 10, 1)} unités d’alcool</b> : l’alcool (7 kcal/g) freine la récupération et la construction musculaire pendant ~24 h. Bois 1 verre d’eau par verre d’alcool, mange protéiné demain, pas de séance lourde à jeun le lendemain : privilégie du cardio léger.</div>` : '';
  if (over <= 100) {
    const w = sheet(`<h3>Tout va bien 👍</h3><p>Avec cet écart tu restes dans ton objectif du jour (${Math.round(eaten)} / ${t.kcal} kcal). Rien à compenser.</p>${tips}<button class="btn block" data-close>OK</button>`, { onClose: rerender });
    return w;
  }
  const opts = [2, 3, 4].map(n => {
    const per = Math.min(500, Math.ceil(over / n / 10) * 10);
    const ok = targets(S.profile, shiftD(date, 1)).kcal - per >= floor;
    return { n, per, ok };
  });
  const w = sheet(`<h3>+${over} kcal au-dessus de ton objectif</h3>
    <p class="small muted">Un écart ponctuel ne ruine rien : ce qui compte, c’est la moyenne de la semaine. Choisis comment rattraper (ou pas) :</p>
    ${tips}
    <h3 class="sec">Étaler sur les jours suivants</h3>
    ${opts.map(o => `<button class="btn ghost block comp" data-n="${o.n}" data-per="${o.per}" ${o.ok ? '' : 'disabled'}><b>−${o.per} kcal/jour pendant ${o.n} jours</b><small>${o.ok ? 'surtout sur les glucides et les lipides, protéines inchangées' : 'trop bas pour ton métabolisme'}</small></button>`).join('')}
    <h3 class="sec">Ou le brûler en bougeant</h3>
    <div class="table">${[['Marche rapide', 4.5], ['Vélo modéré', 7], ['Course à pied', 9], ['Corde à sauter', 11]].map(([n, met]) => `<div class="tr"><span>${n}</span><b>${Math.round(over / perMin(met))} min</b><small>~${Math.round(perMin(met) * 10)} kcal/10 min</small></div>`).join('')}</div>
    <p class="small muted">Tu peux aussi mixer : par exemple 30 min de marche + 2 jours à −${Math.ceil(Math.max(0, over - perMin(4.5) * 30) / 2 / 10) * 10} kcal.</p>
    <button class="btn ghost block" data-close>Ne rien compenser</button>`, { onClose: rerender });
  w.addEventListener('click', async (e) => {
    const b = e.target.closest('.comp'); if (!b || b.disabled) return;
    const n = +b.dataset.n, per = +b.dataset.per;
    S.comp = S.comp || {};
    for (let i = 1; i <= n; i++) { const d = shiftD(date, i); S.comp[d] = (S.comp[d] || 0) + per; }
    await kv.set('comp', S.comp);
    toast(`Compensation : −${per} kcal les ${n} prochains jours`); w.close();
  });
}
