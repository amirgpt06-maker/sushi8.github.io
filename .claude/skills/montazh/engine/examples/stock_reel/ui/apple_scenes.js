// Свои белые сцены в духе презентаций Apple (без шаблона движка и без стеклянной капли):
// крупная чистая типографика, слова выезжают из-под маски, спокойные появления (ease-out), телефоны с живыми экранами,
// поле запроса с переливающимся свечением. Время в update — ГЛОБАЛЬНОЕ время ролика (сцене передаётся t + T0).
const AMB = 'linear-gradient(100deg,#F2A900 0%,#FF8A00 60%,#FF6A00 100%)';
const INK = '#1d1d1f', GRAY = '#86868b', BG = '#f5f5f7';
function base(R0) {
  R.style.background = BG;
  el('div', `position:absolute;inset:0;background:radial-gradient(ellipse 90% 60% at 50% 35%,#ffffff 0%,#f5f5f7 60%,#ececf0 100%)`, R);
  return el('div', `position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:540px 860px`, R);
}
// строка из слов; каждое слово выезжает из-под маски (как в роликах Apple)
function wline(parent, words, y, css, grad) {
  const L = el('div', `position:absolute;left:0;right:0;top:${y}px;text-align:center;white-space:nowrap;${css}`, parent);
  const ws = words.map(([w, wt], i) => {
    const m = el('span', `display:inline-block;overflow:hidden;vertical-align:top;padding:0.06em 0.04em 0.16em;margin:-0.06em ${i < words.length - 1 ? '0.13em' : '-0.04em'} -0.16em -0.04em`, L);
    const s = el('span', `display:inline-block;${grad ? `background:${grad};-webkit-background-clip:text;background-clip:text;color:transparent;` : ''}`, m, w);
    return { s, t: wt };
  });
  return { L, ws };
}
function wshow(line, t, d = 0.62) {
  for (const { s, t: wt } of line.ws) {
    const k = eo5(lin(t, wt - 0.04, wt - 0.04 + d));
    s.style.transform = `translateY(${(1 - k) * 105}%)`; s.style.opacity = k > 0 ? 0.25 + 0.75 * k : 0;
    s.style.filter = k < 1 ? `blur(${(1 - k) * 6}px)` : '';
  }
}
function fadeIO(e, t, tin, tout, o = {}) {   // мягкое появление и уход: снизу вверх, из расфокуса
  const k = eo5(lin(t, tin, tin + (o.d ?? 0.75))), q = tout == null ? 0 : eio(lin(t, tout, tout + (o.od ?? 0.4)));
  e.style.opacity = k * (1 - q);
  e.style.transform = `translateY(${(1 - k) * (o.dy ?? 60) - q * (o.qy ?? 40)}px) scale(${(o.s0 ?? 0.97) + (1 - (o.s0 ?? 0.97)) * k}) ${o.extra || ''}`;
  e.style.filter = (1 - k) + q > 0.01 ? `blur(${(1 - k) * (o.bl ?? 16) + q * 12}px)` : '';
}
function outGroup(e, t, tout, od = 0.4) { const q = eio(lin(t, tout, tout + od)); e.style.opacity = 1 - q; e.style.filter = q > 0.01 ? `blur(${q * 14}px)` : ''; e.style.transform = `translateY(${-q * 50}px)`; }
// телефон для светлого фона (мягкая тень), масштаб и место — снаружи
function phoneL(parent, x, y, s, rot = 0) {
  const w = 860, h = 1780;
  const wrap = el('div', `position:absolute;left:${x - w / 2}px;top:${y - h / 2}px;width:${w}px;height:${h}px;transform-origin:50% 50%`, parent);
  const body = el('div', `position:absolute;inset:0;border-radius:118px;background:linear-gradient(145deg,#4a4b50,#16161a 40%,#2c2d31);box-shadow:0 80px 160px rgba(20,20,40,.22),0 24px 50px rgba(20,20,40,.14)`, wrap);
  el('div', `position:absolute;inset:6px;border-radius:112px;background:#050506`, body);
  const scr = el('div', `position:absolute;left:24px;top:24px;right:24px;bottom:24px;border-radius:96px;overflow:hidden;background:#000`, wrap);
  el('div', `position:absolute;left:50%;top:30px;width:210px;height:62px;margin-left:-105px;border-radius:32px;background:#000;z-index:60`, scr);
  el('div', `position:absolute;inset:0;z-index:70;background:linear-gradient(120deg,rgba(255,255,255,0) 35%,rgba(255,255,255,.08) 48%,rgba(255,255,255,0) 60%)`, scr);
  return { wrap, scr, s, rot, x, y };
}
function placePhone(P, t, tin, o = {}) {
  const k = eo5(lin(t, tin, tin + (o.d ?? 0.9)));
  const fl = Math.sin((t - tin) * 1.3 + (o.ph ?? 0)) * 8;
  P.wrap.style.opacity = k;
  P.wrap.style.transform = `translateY(${(1 - k) * 260 + fl}px) rotate(${P.rot + (1 - k) * (o.rr ?? 6)}deg) scale(${P.s * (0.94 + 0.06 * k)})`;
}
function chatContent(scr, text) {
  scr.style.background = '#0f1012';
  el('div', `position:absolute;left:0;right:0;top:0;height:200px;display:flex;align-items:flex-end;justify-content:center;padding-bottom:26px;box-sizing:border-box;font:600 40px SF;color:#e8e8ea;border-bottom:1px solid #1f2024`, scr, `<span style="color:#FFD60A;margin-right:14px">✦</span>Ассистент`);
  el('div', `position:absolute;right:44px;top:290px;padding:32px 44px;border-radius:46px 46px 12px 46px;background:#2b2c31;font:500 58px SF;color:#fff`, scr, text);
  const rep = el('div', `position:absolute;left:44px;right:140px;top:470px;display:flex;flex-direction:column;gap:24px`, scr);
  [1, .92, .97, .7, 0, .95, .85, .6].forEach(w => el('div', `height:${w ? 32 : 10}px;width:${w * 100}%;border-radius:16px;background:${w ? '#26272c' : 'transparent'}`, rep));
  el('div', `position:absolute;left:34px;right:34px;bottom:70px;height:150px;border-radius:75px;background:#1f2024;border:2px solid #2c2d33`, scr);
}
function orderContent(scr) {
  scr.style.background = '#f6f4f1';
  el('div', `position:absolute;left:0;right:0;top:0;height:250px;padding:120px 56px 0;box-sizing:border-box;display:flex;align-items:center;justify-content:space-between`, scr,
    `<div style="font:500 40px PF;color:#1d1d1f;letter-spacing:6px">SEZON</div><div style="width:80px;height:80px;border-radius:50%;background:#ece8e2;display:flex;align-items:center;justify-content:center;font:600 34px SF">2</div>`);
  const card = el('div', `position:absolute;left:40px;right:40px;top:290px;height:1060px;border-radius:56px;overflow:hidden;background:#fff;box-shadow:0 20px 50px rgba(0,0,0,.08)`, scr);
  el('div', `position:absolute;left:0;right:0;top:0;height:700px;background:url(img/burger.jpg) center 48%/cover`, card);
  el('div', `position:absolute;left:44px;top:732px;font:800 60px SF;color:#1d1d1f;letter-spacing:-1px`, card, 'Бургер с говядиной');
  el('div', `position:absolute;left:44px;top:812px;font:400 34px SF;color:#86868b`, card, 'Бриошь, мраморная говядина, чеддер');
  el('div', `position:absolute;left:44px;top:902px;font:800 64px SF;color:#1d1d1f`, card, '590 ₽');
  const btn = el('div', `position:absolute;left:40px;right:40px;top:1420px;height:170px;border-radius:85px;background:#FFD60A;color:#1a1200;font:700 60px SF;display:flex;align-items:center;justify-content:center;box-shadow:0 18px 40px rgba(255,190,0,.35)`, scr, 'Заказать · 590 ₽');
  const rip = el('div', `position:absolute;left:400px;top:1505px;width:60px;height:60px;margin:-30px;border-radius:50%;background:rgba(255,255,255,.75);z-index:5`, scr);
  const note = el('div', `position:absolute;left:28px;right:28px;top:110px;height:210px;border-radius:50px;background:rgba(250,250,252,.92);box-shadow:0 20px 60px rgba(0,0,0,.22);z-index:40;display:flex;align-items:center;gap:30px;padding:0 36px;box-sizing:border-box`, scr,
    `<div style="width:116px;height:116px;border-radius:28px;background:#1d1d1f;display:flex;align-items:center;justify-content:center;font:500 30px PF;color:#FFD60A;letter-spacing:2px;flex:none">SZN</div>
     <div style="flex:1"><div style="display:flex;justify-content:space-between;font:600 32px SF;color:#86868b"><span>SEZON</span><span>сейчас</span></div><div style="font:800 50px SF;color:#1d1d1f;margin-top:4px">Заказ принят ✓</div><div style="font:400 34px SF;color:#3a3a3c">Курьер будет через 25 минут</div></div>`);
  return { btn, rip, note };
}
function siteContent(scr) {
  scr.style.background = '#0e0c0a';
  el('div', `position:absolute;left:0;right:0;top:0;height:170px;background:rgba(20,18,16,.92);z-index:30;display:flex;align-items:flex-end;justify-content:center;padding-bottom:22px;box-sizing:border-box`, scr,
    `<div style="width:560px;height:72px;border-radius:24px;background:#2a2723;display:flex;align-items:center;justify-content:center;font:500 32px SF;color:#d8d2c8">🔒 sezon.ru</div>`);
  const pg = el('div', `position:absolute;left:0;right:0;top:170px`, scr);
  el('div', `position:relative;height:1180px;background:url(img/dish.jpg) 46% 50%/cover`, pg,
    `<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,12,10,.45),rgba(14,12,10,.15) 40%,rgba(14,12,10,.92))"></div>
     <div style="position:absolute;left:56px;right:56px;top:46px;display:flex;justify-content:space-between;font:500 30px SF;color:#efe7da;letter-spacing:1px"><span style="font:500 34px PF;letter-spacing:6px">SEZON</span><span>Меню · Бронь · Доставка</span></div>
     <div style="position:absolute;left:56px;right:56px;bottom:90px"><div style="font:400 30px SF;color:#d9b77a;letter-spacing:6px">КУХНЯ И КОФЕ</div>
     <div style="font:400 112px PF;color:#fff;line-height:1.02;margin-top:18px">Вкус, который<br>хочется<br>повторить</div>
     <div style="display:flex;gap:20px;margin-top:44px"><div style="padding:30px 48px;border-radius:60px;background:#FFD60A;color:#1a1200;font:700 38px SF">Заказать онлайн</div><div style="padding:30px 44px;border-radius:60px;border:2px solid rgba(255,255,255,.6);color:#fff;font:600 38px SF">Меню</div></div></div>`);
  el('div', `padding:70px 56px 30px;font:400 76px PF;color:#fff`, pg, 'Популярное');
  const grid = el('div', `display:grid;grid-template-columns:1fr 1fr;gap:28px;padding:0 56px`, pg);
  [['burger', 'Бургер', '590 ₽'], ['pizza', 'Пепперони', '720 ₽'], ['latte', 'Айс-латте', '290 ₽'], ['salad', 'Цезарь', '480 ₽'], ['grill', 'Гриль', '890 ₽'], ['espresso', 'Эспрессо', '190 ₽']].forEach(([im, n, p]) =>
    el('div', `border-radius:40px;overflow:hidden;background:#1b1815`, grid, `<div style="height:330px;background:url(img/${im}.jpg) center/cover"></div><div style="padding:24px 28px 30px"><div style="font:600 38px SF;color:#fff">${n}</div><div style="font:700 36px SF;color:#d9b77a;margin-top:6px">${p}</div></div>`));
  el('div', `margin:50px 56px;padding:56px;border-radius:44px;background:#FFD60A;color:#1a1200`, pg, `<div style="font:800 64px SF;letter-spacing:-1px">Доставка за 30 минут</div><div style="font:500 36px SF;margin-top:10px">Закажите на сайте — привезём горячим</div>`);
  return pg;
}
// поле запроса со свечением (переливается по кругу)
function glowField(parent, y, w = 900, h = 210) {
  const box = el('div', `position:absolute;left:${540 - w / 2}px;top:${y - h / 2}px;width:${w}px;height:${h}px`, parent);
  const glow = el('div', `position:absolute;inset:-26px;border-radius:${h / 2 + 26}px;filter:blur(34px);opacity:.75`, box);
  const ring = el('div', `position:absolute;inset:-5px;border-radius:${h / 2 + 5}px`, box);
  const card = el('div', `position:absolute;inset:0;border-radius:${h / 2}px;background:#fff;box-shadow:0 20px 50px rgba(20,20,40,.10)`, box);
  const tx = el('div', `position:absolute;left:70px;top:0;bottom:0;right:170px;display:flex;align-items:center;font:500 64px SF;color:${INK};letter-spacing:-1px;white-space:nowrap;overflow:hidden`, card);
  const caret = el('span', `display:inline-block;width:5px;height:70px;background:${INK};margin-left:4px;border-radius:3px`, null);
  const send = el('div', `position:absolute;right:30px;top:${(h - 130) / 2}px;width:130px;height:130px;border-radius:50%;background:${INK};display:flex;align-items:center;justify-content:center`, card,
    `<svg width="62" height="62" viewBox="0 0 24 24"><path d="M12 19V5M5.5 11.5L12 5l6.5 6.5" stroke="#fff" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`);
  return { box, glow, ring, tx, caret, send };
}
function glowSet(G, t) {
  const a = (t * 70) % 360, cg = `conic-gradient(from ${a}deg,#FFC21A,#FF7A3D,#FF3D8B,#9B5CFF,#3DA2FF,#3DE0C4,#FFC21A)`;
  G.glow.style.background = cg; G.ring.style.background = cg;
}
function typeInto(G, text, t, t0, t1, until) {
  const n = t < t0 ? 0 : Math.min(text.length, Math.floor((t - t0) / Math.max(.01, t1 - t0) * text.length) + 1);
  G.tx.textContent = n ? text.slice(0, n) : '';
  if (!n) G.tx.innerHTML = `<span style="color:#b0b0b6">Спросите что-нибудь</span>`;
  G.tx.appendChild(G.caret); G.caret.style.opacity = (t < until && (Math.floor(t * 3) % 2 === 0 || (n && n < text.length))) ? 1 : 0;
}
function personIcon() { return `<svg width="70" height="70" viewBox="0 0 24 24"><circle cx="12" cy="8.2" r="4.2" fill="#fff"/><path d="M3.8 21c.6-4.4 4-7 8.2-7s7.6 2.6 8.2 7z" fill="#fff"/></svg>`; }

// ---------------- Сцена A: «А нейросетями так пользуются почти все» + «Сделай сайт. Сделай монтаж» ----------------
SC.apA = {
  build() {
    const c = this.c = base();
    this.g1 = el('div', `position:absolute;inset:0`, c);
    this.l1 = wline(this.g1, [['А', 9.39], ['нейросетями', 9.52]], 300, `font:700 118px SF;color:${INK};letter-spacing:-4px`);
    this.l2 = wline(this.g1, [['так', 10.36], ['пользуются', 10.56]], 450, `font:500 66px SF;color:${GRAY};letter-spacing:-1px`);
    this.l3 = wline(this.g1, [['почти', 11.20], ['все', 11.60]], 540, `font:800 130px SF;letter-spacing:-4px`, AMB);
    this.ph = [['Сделай сайт', 250, -9, 10.40], ['Сделай логотип', 540, 0, 10.60], ['Напиши пост', 830, 9, 10.80]].map(([tx, x, r, t0], i) => {
      const P = phoneL(this.g1, x, 1230, 0.33, r); chatContent(P.scr, tx); P.t0 = t0; P.i = i; return P; });
    this.g2 = el('div', `position:absolute;inset:0`, c);
    this.orb = el('div', `position:absolute;left:465px;top:330px;width:150px;height:150px;border-radius:50%`, this.g2);
    this.b1 = el('div', `position:absolute;right:120px;top:640px;padding:34px 50px;border-radius:52px 52px 14px 52px;background:${INK};font:500 60px SF;color:#fff`, this.g2, 'Сделай сайт');
    this.b2 = el('div', `position:absolute;right:120px;top:640px;padding:34px 50px;border-radius:52px 52px 14px 52px;background:${INK};font:500 60px SF;color:#fff`, this.g2, 'Сделай монтаж');
    this.G = glowField(this.g2, 1060);
  },
  update(t) {
    wshow(this.l1, t); wshow(this.l2, t); wshow(this.l3, t);
    this.ph.forEach((P, i) => placePhone(P, t, P.t0, { ph: i }));
    outGroup(this.g1, t, 12.22, 0.38); this.g1.style.display = t < 12.62 ? '' : 'none';
    // промпты
    const on = t >= 12.30; this.g2.style.display = on ? '' : 'none';
    if (on) {
      fadeIO(this.G.box, t, 12.30, null, { d: 0.7, dy: 80 }); glowSet(this.G, t);
      const a = (t * 60) % 360; this.orb.style.background = `conic-gradient(from ${a}deg,#FFC21A,#FF7A3D,#FF3D8B,#9B5CFF,#3DA2FF,#3DE0C4,#FFC21A)`;
      this.orb.style.filter = `blur(${2 + 1.5 * Math.sin(t * 3)}px)`; fadeIO(this.orb, t, 12.32, null, { d: .8, dy: 40, extra: `scale(${1 + .05 * Math.sin(t * 2.4)})` });
      if (t < 13.47) typeInto(this.G, 'Сделай сайт', t, 12.49, 13.30, 13.45);
      else typeInto(this.G, 'Сделай монтаж', t, 13.68, 14.40, 14.50);
      const ks = Math.max(lin(t, 13.43, 13.63) * (1 - lin(t, 13.63, 13.8)), lin(t, 14.48, 14.68) * (1 - lin(t, 14.68, 14.85)));
      this.G.send.style.transform = `scale(${1 - 0.12 * ks})`;
      // отправленные сообщения улетают вверх пузырём
      const k1 = eo5(lin(t, 13.46, 13.95)), up = eo5(lin(t, 14.50, 14.95));
      this.b1.style.opacity = k1; this.b1.style.transform = `translateY(${(1 - k1) * 360 - up * 150}px) scale(${0.85 + 0.15 * k1})`; this.b1.style.transformOrigin = '100% 100%';
      const k2 = eo5(lin(t, 14.51, 15.0)); this.b2.style.opacity = k2; this.b2.style.transform = `translateY(${(1 - k2) * 360}px) scale(${0.85 + 0.15 * k2})`; this.b2.style.transformOrigin = '100% 100%';
    }
    this.c.style.transform = `scale(${1 + 0.025 * lin(t, 9.36, 14.8)})`;
  }
};

// ---------------- Сцена B: «Адрес для ИИ — это…», шаги 1-2-3 ----------------
SC.apB = {
  build() {
    const c = this.c = base();
    // 1) Адрес для ИИ — на фоне светлая схема улиц
    const g0 = this.g0 = el('div', `position:absolute;inset:0`, c);
    const r = rng(3); let sv = '';
    for (let i = 0; i < 16; i++) { const x = r() * 1300 - 110; sv += `<line x1="${x}" y1="-50" x2="${x + (r() - .5) * 300}" y2="1970" stroke="#d9d9de" stroke-width="${i % 4 ? 6 : 14}"/>`; }
    for (let i = 0; i < 20; i++) { const y = r() * 2000 - 40; sv += `<line x1="-50" y1="${y}" x2="1130" y2="${y + (r() - .5) * 260}" stroke="#d9d9de" stroke-width="${i % 4 ? 6 : 14}"/>`; }
    this.map = el('div', `position:absolute;inset:-60px`, g0, `<svg width="1200" height="2040" viewBox="-60 -60 1200 2040">${sv}</svg>`);
    this.route = el('div', `position:absolute;inset:0`, g0, `<svg width="1080" height="1920"><path id="rt" d="M180 1700 L180 1420 L640 1420 L640 1180 L900 1180" fill="none" stroke="url(#gr)" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/><defs><linearGradient id="gr"><stop offset="0" stop-color="#F2A900"/><stop offset="1" stop-color="#FF6A00"/></linearGradient></defs></svg>`);
    this.pin = el('div', `position:absolute;left:478px;top:380px;width:124px;height:160px`, g0,
      `<svg width="124" height="160" viewBox="0 0 24 31"><defs><linearGradient id="pg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFC21A"/><stop offset="1" stop-color="#FF6A00"/></linearGradient></defs><path d="M12 1a10 10 0 0 0-10 10c0 7.5 10 19 10 19s10-11.5 10-19A10 10 0 0 0 12 1z" fill="url(#pg)"/><circle cx="12" cy="11" r="4" fill="#fff"/></svg>`);
    this.a1 = wline(g0, [['Адрес', 22.02]], 590, `font:800 200px SF;letter-spacing:-7px`, AMB);
    this.a2 = wline(g0, [['для', 22.46], ['ИИ', 22.70]], 820, `font:800 200px SF;color:${INK};letter-spacing:-7px`);
    this.a3 = wline(g0, [['это', 23.26]], 1080, `font:500 72px SF;color:${GRAY}`);
    // шаги: крупная тонкая цифра, подпись, ключевое — градиентом
    const step = (n, lab, labT, key, y0, size) => {
      const g = el('div', `position:absolute;inset:0`, c);
      const num = el('div', `position:absolute;left:0;right:0;top:170px;text-align:center;font:200 300px SF;color:${INK};letter-spacing:-12px;line-height:1`, g, String(n));
      const L = wline(g, [[lab, labT]], 500, `font:500 60px SF;color:${GRAY}`);
      const K = key.map((ln, i) => wline(g, ln, y0 + i * size * 1.02, `font:800 ${size}px SF;letter-spacing:-${size / 28}px`, AMB));
      return { g, num, L, K };
    };
    this.s1 = step(1, 'Первое —', 23.96, [[['Для', 24.44], ['кого', 24.68]]], 600, 150);
    this.s1sub = wline(this.s1.g, [['Сайт', 25.64], ['для', 26.00], ['общепита', 26.20]], 800, `font:700 80px SF;color:${INK};letter-spacing:-2px`);
    this.cards = [['grill', 225, 25.70, -5], ['latte', 540, 25.98, 0], ['dish', 855, 26.26, 5]].map(([im, x, t0, rr]) => {
      const d = el('div', `position:absolute;left:${x - 145}px;top:1080px;width:290px;height:390px;border-radius:44px;background:url(img/${im}.jpg) center/cover;box-shadow:0 40px 80px rgba(20,20,40,.18)`, this.s1.g); return { d, t0, rr }; });
    this.s2 = step(2, 'Второе —', 27.18, [[['Что', 27.63], ['должно', 27.91]], [['получиться', 28.35]]], 600, 130);
    this.s2sub = wline(this.s2.g, [['Чтобы', 29.45], ['люди', 29.86], ['заказывали', 30.18], ['онлайн', 30.94]], 500, `font:600 58px SF;color:${INK};letter-spacing:-1px`);
    this.p2 = phoneL(this.s2.g, 540, 1165, 0.47, 0); this.o2 = orderContent(this.p2.scr);
    this.s3 = step(3, 'Третье —', 32.05, [[['Пример', 32.53]]], 600, 170);
    this.s3a = wline(this.s3.g, [['Вот', 33.36], ['сайт,', 33.68]], 470, `font:700 92px SF;color:${INK};letter-spacing:-3px`);
    this.s3b = wline(this.s3.g, [['который', 34.08], ['мне', 34.48], ['нравится', 34.72]], 590, `font:500 60px SF;color:${GRAY}`);
    this.p3 = phoneL(this.s3.g, 540, 1190, 0.47, 0); this.pg3 = siteContent(this.p3.scr);
  },
  update(t) {
    const show = (g, a, b) => { g.style.display = t >= a && t < b ? '' : 'none'; };
    // 1) адрес
    show(this.g0, 21.80, 24.2);
    this.map.style.opacity = 0.55 * eo5(lin(t, 21.9, 22.6)); this.map.style.transform = `translate(${-30 * lin(t, 21.9, 24)}px, ${-40 * lin(t, 21.9, 24)}px) rotate(-8deg) scale(1.1)`;
    const rk = eio(lin(t, 22.1, 23.0)); const rt = document.getElementById('rt'); if (rt) { const L = 1440; rt.style.strokeDasharray = L; rt.style.strokeDashoffset = L * (1 - rk); }
    this.route.style.opacity = 0.9;
    fadeIO(this.pin, t, 21.92, null, { d: 0.8, dy: -60 });
    wshow(this.a1, t); wshow(this.a2, t); wshow(this.a3, t);
    outGroup(this.g0, t, 23.72, 0.38);
    // 2) шаг 1
    const st = (S, a, b, out) => { show(S.g, a - .05, b);
      const k = eo5(lin(t, a, a + 0.9)); S.num.style.opacity = k; S.num.style.filter = k < 1 ? `blur(${(1 - k) * 22}px)` : ''; S.num.style.transform = `scale(${1.12 - .12 * k})`;
      wshow(S.L, t); S.K.forEach(L => wshow(L, t)); outGroup(S.g, t, out, 0.38); };
    st(this.s1, 23.86, 27.25, 26.95); wshow(this.s1sub, t);
    this.cards.forEach(({ d, t0, rr }, i) => { const k = eo5(lin(t, t0, t0 + 0.8)); d.style.opacity = k;
      d.style.transform = `translateY(${(1 - k) * 220 + Math.sin(t * 1.4 + i) * 6}px) rotate(${rr * (0.6 + 0.4 * k)}deg) scale(${0.92 + 0.08 * k})`; });
    // 3) шаг 2: заголовок уезжает вверх, появляется телефон с заказом
    st(this.s2, 27.10, 32.15, 31.80);
    const m2 = eio(lin(t, 29.25, 29.85));
    this.s2.num.style.opacity = (+this.s2.num.style.opacity) * (1 - m2);
    this.s2.L.L.style.transform = `translateY(${-m2 * 330}px)`; this.s2.L.L.style.opacity = 1 - m2;
    this.s2.K.forEach((L, i) => { L.L.style.transform = `translateY(${-m2 * (430 - i * 0)}px) scale(${1 - 0.42 * m2})`; L.L.style.transformOrigin = '50% 0'; L.L.style.top = (600 + i * 133 - m2 * i * 56) + 'px'; });
    wshow(this.s2sub, t); this.s2sub.L.style.top = '470px';
    placePhone(this.p2, t, 29.50, { d: 1.0 });
    const tap = 30.20, done = t > tap + 0.12;
    this.o2.btn.style.transform = `scale(${t > tap - .03 && t < tap + .12 ? .95 : 1})`;
    this.o2.btn.style.background = done ? '#30D158' : '#FFD60A'; this.o2.btn.style.color = done ? '#fff' : '#1a1200'; this.o2.btn.textContent = done ? '✓ Заказ принят' : 'Заказать · 590 ₽';
    const rp = lin(t, tap, tap + 0.45); this.o2.rip.style.opacity = rp > 0 && rp < 1 ? 0.85 * (1 - rp) : 0; this.o2.rip.style.transform = `scale(${1 + rp * 16})`;
    const nk = eo5(lin(t, 30.94, 31.40)); this.o2.note.style.transform = `translateY(${(1 - nk) * -340}px)`; this.o2.note.style.opacity = t > 30.94 ? 1 : 0;
    // 4) шаг 3: «Пример», затем сайт листается
    st(this.s3, 31.95, 37.00, 99);
    const m3 = eio(lin(t, 33.15, 33.75));
    this.s3.num.style.opacity = (+this.s3.num.style.opacity) * (1 - m3);
    this.s3.L.L.style.opacity = 1 - m3; this.s3.L.L.style.transform = `translateY(${-m3 * 300}px)`;
    this.s3.K[0].L.style.transformOrigin = '50% 0'; this.s3.K[0].L.style.transform = `translateY(${-m3 * 330}px) scale(${1 - 0.55 * m3})`;
    wshow(this.s3a, t); wshow(this.s3b, t);
    placePhone(this.p3, t, 33.55, { d: 1.0 });
    this.pg3.style.transform = `translateY(${-eio(lin(t, 33.9, 35.65)) * 1500}px)`;
    this.c.style.transform = `scale(${1 + 0.02 * Math.sin((t - 21.9) * 0.35)})`;
  }
};

// ---------------- Сцена C: «Подпишись — тут про искусственный интеллект» ----------------
SC.apC = {
  build() {
    const c = this.c = base();
    this.l1 = wline(c, [['Подпишись', 39.00]], 330, `font:800 170px SF;letter-spacing:-6px`, AMB);
    this.l2 = wline(c, [['тут', 40.11], ['про', 40.16]], 560, `font:500 64px SF;color:${GRAY}`);
    this.l3 = wline(c, [['искусственный', 40.36], ['интеллект', 41.12]], 645, `font:700 74px SF;color:${INK};letter-spacing:-2px`);
    const card = this.card = el('div', `position:absolute;left:150px;right:150px;top:900px;height:560px;border-radius:64px;background:#fff;box-shadow:0 50px 110px rgba(20,20,40,.14),0 8px 24px rgba(20,20,40,.06)`, c);
    el('div', `position:absolute;left:50%;top:60px;margin-left:-90px;width:180px;height:180px;border-radius:50%;background:linear-gradient(160deg,#c7c7cc,#8e8e93);display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 8px #fff,0 0 0 12px rgba(242,169,0,.35)`, card, personIcon().replace(/70/g, '110'));
    el('div', `position:absolute;left:0;right:0;top:270px;text-align:center;font:700 60px SF;color:${INK};letter-spacing:-1px`, card, 'saidulaev.ai');
    el('div', `position:absolute;left:0;right:0;top:345px;text-align:center;font:400 38px SF;color:${GRAY}`, card, 'Амирхан | Вайбкодинг');
    this.btn = el('div', `position:absolute;left:70px;right:70px;top:420px;height:100px;border-radius:50px;background:${INK};color:#fff;font:600 44px SF;display:flex;align-items:center;justify-content:center`, card, 'Подписаться');
  },
  update(t) {
    wshow(this.l1, t); wshow(this.l2, t); wshow(this.l3, t);
    fadeIO(this.card, t, 39.30, null, { d: 0.9, dy: 120 });
    const p = 40.96, done = t >= p + 0.06;
    this.btn.style.transform = `scale(${t > p - .04 && t < p + .1 ? .95 : 1})`;
    this.btn.style.background = done ? '#ececf0' : INK; this.btn.style.color = done ? INK : '#fff';
    this.btn.innerHTML = done ? 'Вы подписаны <span style="color:#F2A900;margin-left:10px">✓</span>' : 'Подписаться';
    this.c.style.transform = `scale(${1 + 0.03 * lin(t, 38.9, 41.8)})`;
  }
};
