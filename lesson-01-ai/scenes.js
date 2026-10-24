// Анимированный видеоурок 1: сцены, фразы озвучки (beats) и разметка.
// Атрибуты элементов (их читает движок в anim.html):
//   data-b   — номер фразы, на которой элемент появляется; data-d — задержка, с; data-dur — длительность ("beat" = до следующей фразы)
//   data-fx  — up|down|left|right|pop|fade|zoom|draw|grow|type|count; data-o — фраза, на которой элемент исчезает
//   data-sfx — звук при появлении; data-float="амплитуда период фаза"; data-spin — град/с; data-pulse="b1 b2"; data-move="b:x,y|…"

const H = (eyebrow, a, b, o = "", bB = 0) => `
  <div class="eyebrow" style="left:120px;top:84px" data-b="0" data-fx="up" ${o}>${eyebrow}</div>
  <h1 style="left:120px;top:124px" ${o ? o : ""}><span data-b="0" data-fx="up" data-d=".1">${a}</span><span data-b="${bB}" data-fx="up" data-d="${bB ? 0 : .2}" ${bB ? 'data-sfx="sparkle"' : ""}>${b}</span></h1>`;

const STAR = `<svg class="star" viewBox="0 0 100 100" data-spin="15"><path fill="#fff" d="M50 2 C53 36 64 47 98 50 C64 53 53 64 50 98 C47 64 36 53 2 50 C36 47 47 36 50 2Z"/></svg>`;
const ORB = (x, y, s, attrs) => `<div class="orb" style="left:${x}px;top:${y}px;width:${s}px;height:${s}px" ${attrs}>
  <div class="glow" data-float="0 6 0" data-pulse=""></div><div class="squircle" data-float="14 6 .25">${STAR}</div></div>`;

// Искорки вокруг точки
const SPARK = (cx, cy, r, b, d = 0, n = 10) => Array.from({ length: n }, (_, i) => {
  const a = (i / n) * Math.PI * 2 + 0.3, rr = r * (0.8 + 0.35 * ((i * 7) % 3) / 2);
  const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr, s = 22 + ((i * 5) % 4) * 10;
  const c = ["#6f86ff", "#ff6fae", "#ffbe4a"][i % 3];
  return `<div class="spark" style="left:${x}px;top:${y}px;font-size:${s}px;color:${c}" data-b="${b}" data-fx="pop" data-d="${(d + i * 0.05).toFixed(2)}" data-float="8 ${2 + (i % 3)} ${i / n}">✦</div>`;
}).join("") + `<i data-b="${b}" data-d="${d}" data-sfx="sparkle"></i>`;

const PILL = (x, y, emo, text, b, d = 0, extra = "") =>
  `<div class="pill" style="left:${x}px;top:${y}px" data-b="${b}" data-d="${d}" data-fx="pop" data-sfx="pop" ${extra}><span class="emo">${emo}</span>${text}</div>`;

const SCENES = [
  // 0 — Интро
  {
    beats: [
      "Привет!",
      "Добро пожаловать на первый урок курса «Сайты и боты силой слов».",
      "Сегодня мы разберёмся, что такое искусственный интеллект, где ты встречаешь его каждый день,",
      "и почему он может стать твоим самым сильным помощником.",
    ],
    html: `
      <div class="eyebrow center" style="top:70px" data-b="0" data-fx="up">Школа «Аль-Кифая» · 3 месяца · от 12 лет</div>
      <h1 class="center big" style="top:110px"><span data-b="1" data-fx="up" data-sfx="whoosh">Сайты и боты.</span><span data-b="1" data-fx="up" data-d=".35">Силой слов.</span></h1>
      ${ORB(760, 420, 400, 'data-b="0" data-fx="pop" data-dur="1.1" data-sfx="chime" data-pulse="3"')}
      ${PILL(330, 500, "🤔", "Что это?", 2, 0.2, 'data-float="10 5 0"')}
      ${PILL(1260, 610, "🌍", "Где он вокруг нас?", 2, 1.6, 'data-float="10 5 .3"')}
      ${PILL(420, 800, "🚀", "Зачем он мне?", 2, 3.2, 'data-float="10 5 .6"')}
      ${SPARK(960, 620, 300, 3, 0.3, 12)}
      <div class="eyebrow center" style="top:960px" data-b="3" data-fx="up">Урок 1 · Что такое искусственный интеллект</div>`,
  },
  // 1 — Ты уже пользуешься
  {
    beats: [
      "Начнём с сюрприза: ты уже пользуешься искусственным интеллектом.",
      "Каждый день.",
      "Лента в Ютубе и ТикТоке подбирает видео именно под тебя.",
      "Телефон узнаёт твоё лицо и разблокируется.",
      "Навигатор строит маршрут в объезд пробок.",
      "Переводчик переводит текст с фотографии.",
      "Клавиатура подсказывает следующее слово.",
      "Всё это работает благодаря искусственному интеллекту.",
    ],
    html: `${H("Сюрприз", "Ты уже пользуешься", "искусственным интеллектом.")}
      <div class="phone" style="left:790px;top:360px" data-b="0" data-fx="up" data-d=".4" data-sfx="whoosh" data-pulse="1 7">
        <div class="screen">
          <div class="layer" data-b="0" data-o="2" data-fx="fade"><div class="clock">08:15</div><div class="sub2">Понедельник</div><div class="emo" style="font-size:90px;margin-top:150px">🔒</div></div>
          <div class="layer" data-b="2" data-o="3" data-fx="fade">
            ${["#7f98ff", "#ff86c8", "#ffc95e"].map((c, i) => `<div class="vid" style="background:linear-gradient(135deg,${c},#fff)" data-b="2" data-d="${0.3 + i * 0.35}" data-fx="up"><span class="emo">▶️</span></div>`).join("")}</div>
          <div class="layer" data-b="3" data-o="4" data-fx="fade"><div class="emo" style="font-size:150px;margin-top:150px" data-b="3" data-fx="pop">🙂</div>
            <div class="scan" data-b="3" data-d=".3" data-fx="zoom"></div><div class="ok" data-b="3" data-d="1.4" data-fx="pop" data-sfx="ding">🔓 Открыто</div></div>
          <div class="layer map" data-b="4" data-o="5" data-fx="fade"><svg viewBox="0 0 300 540" width="300" height="540">
            <path d="M0 120H300M0 300H300M0 450H300M80 0V540M210 0V540" stroke="#e4e4ea" stroke-width="18"/>
            <path d="M80 480V300H210V120" fill="none" stroke="#5468f0" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" data-b="4" data-d=".3" data-dur="1.6" data-fx="draw"/>
            <circle cx="210" cy="300" r="22" fill="#e3477e" opacity=".85"/></svg>
            <div class="emo" style="position:absolute;left:186px;top:60px;font-size:50px" data-b="4" data-d="1.8" data-fx="pop" data-sfx="pop">📍</div></div>
          <div class="layer" data-b="5" data-o="6" data-fx="fade"><div class="tcard" data-b="5" data-fx="up">Hello, friend!</div><div class="emo" style="font-size:60px" data-b="5" data-d=".8" data-fx="pop">⬇️</div><div class="tcard blue" data-b="5" data-d="1.4" data-fx="pop" data-sfx="pop">Привет, друг!</div></div>
          <div class="layer" data-b="6" data-o="7" data-fx="fade"><div class="typed" data-b="6" data-fx="type" data-dur="1.4" data-sfx="type">Я иду в ш</div>
            <div class="sugg"><span data-b="6" data-d="1.5" data-fx="pop">школу</span><span data-b="6" data-d="1.6" data-fx="pop">шахматы</span><span data-b="6" data-d="1.7" data-fx="pop">шоу</span></div>
            <div class="keys"></div></div>
          <div class="layer" data-b="7" data-fx="fade">${ORB(60, 150, 180, 'data-b="7" data-fx="pop" data-sfx="chime"')}</div>
        </div>
      </div>
      <div class="bubble" style="left:230px;top:420px" data-b="2" data-fx="right" data-sfx="pop"><span class="emo">📺</span><div><b>Рекомендации</b><small>видео именно под тебя</small></div></div>
      <div class="bubble" style="left:1240px;top:420px" data-b="3" data-fx="left" data-sfx="pop"><span class="emo">🙂</span><div><b>Вход по лицу</b><small>узнаёт тебя за миг</small></div></div>
      <div class="bubble" style="left:230px;top:620px" data-b="4" data-fx="right" data-sfx="pop"><span class="emo">🗺️</span><div><b>Навигатор</b><small>маршрут в объезд пробок</small></div></div>
      <div class="bubble" style="left:1240px;top:620px" data-b="5" data-fx="left" data-sfx="pop"><span class="emo">🌍</span><div><b>Переводчик</b><small>текст прямо с фото</small></div></div>
      <div class="bubble" style="left:230px;top:820px" data-b="6" data-fx="right" data-sfx="pop"><span class="emo">⌨️</span><div><b>Клавиатура</b><small>подсказывает слово</small></div></div>
      <div class="bubble glowing" style="left:1240px;top:820px" data-b="7" data-fx="left" data-d=".4" data-sfx="pop"><span class="emo">✨</span><div><b>Везде — ИИ</b><small>каждый день</small></div></div>
      ${SPARK(960, 660, 330, 7, 0.6, 12)}`,
  },
  // 2 — Определение
  {
    beats: [
      "Так что же это такое?",
      "Искусственный интеллект — это программа, которая умеет учиться на примерах и находить в них закономерности.",
      "Обычной программе человек прописывает каждое правило.",
      "А искусственному интеллекту показывают тысячи и миллионы примеров, и правила он находит сам.",
    ],
    html: `${H("Определение", "Так что же", "это такое?")}
      <div class="emo" style="left:1560px;top:90px;font-size:190px" data-b="0" data-fx="pop" data-d=".4" data-sfx="boop" data-float="12 4 0">🤔</div>
      <div class="defn" style="left:120px;top:360px;width:1680px" data-b="1" data-fx="type" data-dur="beat" data-sfx="type">Искусственный интеллект — это программа, которая учится на примерах и сама находит закономерности.</div>
      <div class="card" style="left:120px;top:560px;width:800px;height:420px" data-b="2" data-fx="up" data-sfx="whoosh">
        <div class="ch"><span class="emo">👨‍💻</span>Обычная программа</div>
        <div class="code" data-b="2" data-d=".6" data-fx="type" data-dur=".9" data-sfx="type">если уши острые → кошка</div>
        <div class="code" data-b="2" data-d="1.6" data-fx="type" data-dur=".9" data-sfx="type">если лает → собака</div>
        <div class="code red" data-b="2" data-d="2.6" data-fx="type" data-dur=".8">если … → ???</div>
        <div class="note">Каждое правило пишет человек</div></div>
      <div class="card grad" style="left:1000px;top:560px;width:800px;height:420px" data-b="3" data-fx="up" data-sfx="whoosh">
        <div class="ch"><span class="emo">✨</span>Искусственный интеллект</div>
        <div class="tiles">${Array.from({ length: 30 }, (_, i) => `<span class="emo" data-b="3" data-d="${(0.4 + i * 0.06).toFixed(2)}" data-fx="pop">${["🐱", "🐶", "🐈", "🐕", "😺", "🐩"][(i * 5) % 6]}</span>`).join("")}</div>
        <i data-b="3" data-d=".5" data-sfx="sparkle"></i>
        <div class="found" data-b="3" data-d="3.2" data-fx="pop" data-sfx="ding">✓ Правило найдено само</div></div>`,
  },
  // 3 — Как он учится
  {
    beats: [
      "Представь, как маленький ребёнок учится узнавать кошку.",
      "Ему никто не объясняет формулу кошки.",
      "Он просто много раз видит кошек и слышит: «это кошка».",
      "Искусственный интеллект учится так же.",
      "Сначала данные — огромное количество примеров.",
      "Потом обучение — программа ищет, что общего у этих примеров.",
      "И в итоге получается модель, которая может узнать кошку на фотографии, которую никогда раньше не видела.",
    ],
    html: `${H("Как он учится", "Как ребёнок,", "только быстрее.")}
      <div class="emo" style="left:150px;top:380px;font-size:220px" data-b="0" data-fx="pop" data-o="3" data-sfx="pop" data-float="10 4 0">👶</div>
      <div class="think" style="left:480px;top:400px" data-b="0" data-d=".8" data-fx="pop" data-o="3">Это кто? <span class="emo">🤔</span></div>
      <div class="think plain" style="left:1080px;top:400px" data-b="1" data-fx="up" data-o="3">Формула кошки = <b>???</b><div class="strike" data-b="1" data-d=".9" data-fx="grow" data-sfx="buzz"></div></div>
      ${["🐱", "🐈", "😺", "🐈‍⬛", "😸", "😻"].map((e, i) => `<div class="photo" style="left:${150 + i * 280}px;top:680px" data-b="2" data-d="${(0.2 + i * 0.35).toFixed(2)}" data-fx="pop" data-sfx="pop" data-o="3"><span class="emo">${e}</span><small>это кошка</small></div>`).join("")}
      <div class="pill big" style="left:610px;top:380px" data-b="3" data-fx="pop" data-o="4" data-sfx="chime"><span class="emo">🤖</span>Искусственный интеллект — так же!</div>
      <div class="col" style="left:120px" data-b="4" data-fx="up" data-sfx="whoosh"><div class="tag"><i class="dot blue"></i>01 · Данные</div>
        <div class="tiles small">${Array.from({ length: 24 }, (_, i) => `<span class="emo" data-b="4" data-d="${(0.3 + i * 0.05).toFixed(2)}" data-fx="pop">${["🐱", "🐈", "😺", "😸", "🐈‍⬛", "😻"][(i * 7) % 6]}</span>`).join("")}</div>
        <i data-b="4" data-d=".4" data-sfx="sparkle"></i><small class="cap">тысячи примеров</small></div>
      <div class="arrow" style="left:648px" data-b="5" data-fx="left">→</div>
      <div class="col" style="left:700px" data-b="5" data-fx="up" data-sfx="whoosh"><div class="tag"><i class="dot pink"></i>02 · Обучение</div>
        <svg class="net" viewBox="0 0 440 380" width="440" height="380">
          ${(() => {
            const L = [[60, [70, 160, 250, 340]], [220, [50, 140, 230, 320]], [380, [130, 260]]];
            let s = "", k = 0;
            for (let l = 0; l < 2; l++) for (const y1 of L[l][1]) for (const y2 of L[l + 1][1])
              s += `<path d="M${L[l][0]} ${y1}L${L[l + 1][0]} ${y2}" stroke="url(#gr)" stroke-width="3" fill="none" data-b="5" data-d="${(0.3 + (k++) * 0.04).toFixed(2)}" data-dur=".6" data-fx="draw"/>`;
            L.forEach(([x, ys], l) => ys.forEach((y, j) => s += `<circle cx="${x}" cy="${y}" r="20" fill="${["#5468f0", "#e3477e", "#ee9a2a"][l]}" data-b="5" data-d="${(0.2 + l * 0.6 + j * 0.08).toFixed(2)}" data-fx="pop" data-pulse=""/>`));
            return `<defs><linearGradient id="gr"><stop offset="0" stop-color="#7f98ff"/><stop offset="1" stop-color="#ff86c8"/></linearGradient></defs>` + s;
          })()}</svg><small class="cap">ищет общее</small></div>
      <div class="arrow" style="left:1228px" data-b="6" data-fx="left">→</div>
      <div class="col" style="left:1280px" data-b="6" data-fx="up" data-sfx="whoosh"><div class="tag"><i class="dot orange"></i>03 · Модель</div>
        <div class="frame"><span class="emo" style="font-size:170px">🐈</span><div class="scan" data-b="6" data-d=".6" data-fx="zoom"></div></div>
        <div class="found" style="position:relative;margin-top:22px" data-b="6" data-d="2.2" data-fx="pop" data-sfx="ding">✓ Кошка · 98%</div></div>`,
  },
  // 4 — Три суперсилы
  {
    beats: [
      "Сегодняшний искусственный интеллект умеет три главные вещи.",
      "Первое — распознавать: лица, голос, текст, предметы на фото.",
      "Второе — рекомендовать: подбирать музыку, видео, товары.",
      "И третье, самое новое — создавать: писать тексты, рисовать картинки, сочинять музыку и даже писать программный код.",
    ],
    html: `${H("Что он умеет", "Три", "суперсилы.")}
      ${[["👁️", "Распознавать", "blue", [["🙂", "Лица"], ["🎤", "Голос"], ["📄", "Текст"], ["📷", "Предметы"]]],
         ["🎯", "Рекомендовать", "pink", [["🎵", "Музыка"], ["🎬", "Видео"], ["🛍️", "Товары"]]],
         ["🪄", "Создавать", "orange", [["📝", "Тексты"], ["🎨", "Картинки"], ["🎵", "Музыка"], ["💻", "Код"]]]]
        .map(([e, t, c, chips], i) => `<div class="power ${c}" style="left:${120 + i * 580}px" data-b="${i + 1}" data-fx="up" data-sfx="whoosh" data-pulse="${i + 1}">
          <div class="emo pe" data-float="12 4 ${i / 3}">${e}</div><div class="num">0${i + 1}</div><h3>${t}</h3>
          <div class="chips">${chips.map(([ce, ct], j) => `<span data-b="${i + 1}" data-d="${(1.2 + j * 0.7).toFixed(1)}" data-fx="pop" data-sfx="pop"><b class="emo">${ce}</b>${ct}</span>`).join("")}</div></div>`).join("")}
      ${SPARK(1690, 470, 130, 3, 0.3, 8)}`,
  },
  // 5 — Чат-боты
  {
    beats: [
      "Отдельно поговорим о чат-ботах, таких как Чат Джи-Пи-Ти, Клод или Алиса.",
      "Внутри них — большая языковая модель.",
      "Она прочитала огромную часть интернета: книги, статьи, учебники.",
      "И научилась продолжать текст так, как его продолжил бы человек.",
      "Главное для нас: с ней можно говорить обычными словами.",
      "Не нужно знать сложные команды.",
      "Твой главный инструмент — это слова.",
    ],
    html: `${H("Чат-боты и нейросети", "Говори словами.", "Силой слов.", "", 6)}
      ${PILL(120, 360, "💬", "ChatGPT", 0, 1.6, 'data-o="4"')}${PILL(440, 360, "🧡", "Claude", 0, 2.4, 'data-o="4"')}${PILL(740, 360, "🟣", "Алиса", 0, 3.0, 'data-o="4"')}
      ${ORB(250, 520, 300, 'data-b="1" data-fx="pop" data-sfx="chime" data-o="4" data-pulse="2"')}
      <div class="pill" style="left:170px;top:860px" data-b="1" data-d=".6" data-fx="up" data-o="4">🧠 Большая языковая модель</div>
      ${[["📚", 640, 500], ["🌐", 800, 560], ["📰", 650, 660], ["📖", 800, 740]].map(([e, x, y], i) => `<div class="emo fly" style="left:${x}px;top:${y}px" data-b="2" data-d="${(0.3 + i * 0.6).toFixed(1)}" data-fx="right" data-sfx="whoosh" data-o="4" data-float="10 3 ${i / 4}">${e}</div>`).join("")}
      <div class="card" style="left:1000px;top:380px;width:800px;height:560px" data-b="3" data-fx="up" data-o="4" data-sfx="whoosh">
        <div class="ch"><span class="emo">🔮</span>Какое слово дальше?</div>
        <div class="pred">Луна вращается вокруг <span class="blank" data-b="3" data-d="3.0" data-fx="pop" data-sfx="ding">Земли</span></div>
        ${[["Земли", 92, "blue"], ["Солнца", 6, "pink"], ["Марса", 2, "orange"]].map(([w, p, c], i) => `<div class="bar"><span>${w}</span><div class="track"><div class="fill ${c}" style="width:${p}%" data-b="3" data-d="${(0.6 + i * 0.4).toFixed(1)}" data-dur="1" data-fx="grow"></div></div><b data-b="3" data-d="${(0.6 + i * 0.4).toFixed(1)}" data-dur="1" data-fx="count" data-count="0,${p}" data-suf="%">0%</b></div>`).join("")}</div>
      <div class="chat" style="left:360px;top:360px" data-b="4" data-fx="up" data-sfx="whoosh">
        <div class="msg me" data-b="4" data-d=".3" data-fx="type" data-dur="1.8" data-sfx="type">Помоги сделать сайт про моих котов 🐱</div>
        <div class="msg ai" data-b="4" data-d="2.4" data-fx="type" data-dur="2" data-sfx="type">Конечно! Начнём с главной страницы — какие фото добавим? ✨</div></div>
      <div class="pill code-x" style="left:360px;top:880px" data-b="5" data-fx="pop" data-sfx="buzz"><span class="mono">&lt;div class="…"&gt; sudo npm</span><div class="strike" data-b="5" data-d=".5" data-fx="grow"></div></div>
      <div class="pill" style="left:1000px;top:880px" data-b="5" data-d=".9" data-fx="pop" data-sfx="pop">✅ Просто пиши словами</div>
      ${SPARK(820, 250, 110, 6, 0.2, 8)}`,
  },
  // 6 — ИИ в мире
  {
    beats: [
      "А где ещё работает искусственный интеллект?",
      "В медицине он помогает врачам находить болезни на снимках.",
      "В транспорте — управляет беспилотными машинами и такси.",
      "В науке — открывает новые лекарства и материалы.",
      "В играх — управляет персонажами.",
      "А в учёбе — объясняет сложные темы так, чтобы стало понятно.",
    ],
    html: `${H("Искусственный интеллект в мире", "Где ещё он", "работает?")}
      <svg class="ring" style="left:700px;top:360px" width="520" height="520" viewBox="0 0 520 520" data-b="0" data-fx="fade" data-spin="8">
        <circle cx="260" cy="260" r="240" fill="none" stroke="#c9c9d6" stroke-width="4" stroke-dasharray="4 18" stroke-linecap="round"/>
        ${[0, 72, 144, 216, 288].map((a, i) => `<circle cx="${260 + 240 * Math.cos(a * Math.PI / 180)}" cy="${260 + 240 * Math.sin(a * Math.PI / 180)}" r="12" fill="${["#5468f0", "#e3477e", "#ee9a2a"][i % 3]}"/>`).join("")}</svg>
      <div class="emo" style="left:835px;top:485px;font-size:250px" data-b="0" data-fx="pop" data-sfx="chime" data-float="14 5 0" data-pulse="1 2 3 4 5">🌍</div>
      ${[["🩺", "Медицина", "находит болезни на снимках", 150, 380], ["🚕", "Транспорт", "беспилотные машины и такси", 1330, 380],
         ["🧪", "Наука", "новые лекарства и материалы", 150, 640], ["🎮", "Игры", "живые персонажи", 1330, 640], ["🎓", "Учёба", "объясняет сложное просто", 740, 900]]
        .map(([e, t, s, x, y], i) => `<div class="bubble" style="left:${x}px;top:${y}px" data-b="${i + 1}" data-fx="${x < 700 ? "right" : x > 1000 ? "left" : "up"}" data-sfx="pop"><span class="emo">${e}</span><div><b>${t}</b><small>${s}</small></div></div>`).join("")}`,
  },
  // 7 — Что это даёт тебе
  {
    beats: [
      "Что это даёт именно тебе?",
      "Искусственный интеллект — это личный репетитор, который готов объяснять тему хоть десять раз, и никогда не устаёт.",
      "Это помощник, с которым ты можешь создать свой сайт или телеграм-бота, даже если раньше никогда не программировал.",
      "И это генератор идей: для проекта, для рассказа, для своего дела.",
      "То, на что раньше уходили годы учёбы, сегодня можно сделать за несколько вечеров.",
    ],
    html: `${H("Что это даёт тебе", "Твой личный", "помощник.")}
      <div class="power blue short" style="left:120px" data-b="1" data-fx="up" data-sfx="whoosh"><div class="emo pe" data-float="12 4 0">🧑‍🏫</div><div class="num">Репетитор</div><h3>Объясняет</h3>
        <div class="stack">${[0, 1].map((i) => `<span data-b="1" data-d="${(2 + i * 0.8).toFixed(1)}" data-fx="pop" data-sfx="pop">Объясни ещё раз 🙏</span>`).join("")}</div>
        <div class="counter" data-b="1" data-d="3.8" data-fx="count" data-dur="1.4" data-count="1,10" data-suf=" раз">1 раз</div></div>
      <div class="power pink short" style="left:700px" data-b="2" data-fx="up" data-sfx="whoosh"><div class="emo pe" data-float="12 4 .3">🚀</div><div class="num">Напарник</div><h3>Создаёт с тобой</h3>
        <div class="site"><div class="bar1" data-b="2" data-d="1.4" data-fx="grow"></div><div class="blk" data-b="2" data-d="2.2" data-fx="pop" data-sfx="pop"></div><div class="blk" data-b="2" data-d="2.7" data-fx="pop" data-sfx="pop"></div><div class="blk" data-b="2" data-d="3.2" data-fx="pop" data-sfx="pop"></div></div></div>
      <div class="power orange short" style="left:1280px" data-b="3" data-fx="up" data-sfx="whoosh"><div class="emo pe" data-float="12 4 .6">💡</div><div class="num">Генератор</div><h3>Придумывает</h3>
        <div class="chips">${[["🧩", "Проект"], ["📖", "Рассказ"], ["🛍️", "Своё дело"]].map(([e, t], j) => `<span data-b="3" data-d="${(1.4 + j * 0.8).toFixed(1)}" data-fx="pop" data-sfx="pop"><b class="emo">${e}</b>${t}</span>`).join("")}</div></div>
      <div class="banner" data-b="4" data-fx="up" data-sfx="whoosh"><span class="old">Годы учёбы<div class="strike" data-b="4" data-d="1.6" data-fx="grow" data-sfx="buzz"></div></span>
        <span class="new" data-b="4" data-d="2.6" data-fx="pop" data-sfx="ding">→ несколько вечеров <b class="emo">🌙</b></span></div>`,
  },
  // 8 — Правила безопасности
  {
    beats: [
      "Но у искусственного интеллекта есть слабые места, и их важно знать.",
      "Он может ошибаться и уверенно выдумывать факты.",
      "Поэтому важную информацию всегда проверяй.",
      "Никогда не отправляй ему личные данные: пароли, адрес, номер телефона.",
      "И помни: если просто списать ответ, ты ничему не научишься.",
      "Используй его, чтобы понять, а не чтобы не думать.",
    ],
    html: `${H("Важно знать", "Три правила", "безопасности.")}
      <div class="emo" style="left:1560px;top:110px;font-size:180px" data-b="0" data-fx="pop" data-d=".5" data-sfx="chime" data-float="10 4 0">🛡️</div>
      <div class="power blue tall" style="left:120px" data-b="1" data-fx="up" data-sfx="whoosh"><div class="num">01</div><h3>Проверяй факты</h3>
        <div class="msg ai small" data-b="1" data-d=".8" data-fx="type" data-dur="1.2">Наполеон изобрёл интернет 🙃</div>
        <div class="stamp" data-base="rotate(-10deg)" data-b="1" data-d="2.3" data-fx="zoom" data-sfx="buzz">ВЫДУМКА</div>
        <div class="good-chip" data-b="2" data-fx="pop" data-sfx="ding">✓ Проверь в источниках</div></div>
      <div class="power pink tall" style="left:700px" data-b="3" data-fx="up" data-sfx="whoosh"><div class="num">02</div><h3>Береги данные</h3>
        <div class="emo" style="font-size:100px;margin:10px 0" data-b="3" data-d=".5" data-fx="pop" data-sfx="pop">🔒</div>
        <div class="xlist">${["Пароль ••••••", "Домашний адрес", "Номер телефона"].map((t, i) => `<span data-b="3" data-d="${(1.4 + i * 0.7).toFixed(1)}" data-fx="pop" data-sfx="pop">${t}<div class="strike" data-b="3" data-d="${(1.8 + i * 0.7).toFixed(1)}" data-fx="grow"></div></span>`).join("")}</div></div>
      <div class="power orange tall" style="left:1280px" data-b="4" data-fx="up" data-sfx="whoosh"><div class="num">03</div><h3>Думай сам</h3>
        <div class="pill code-x inline" data-b="4" data-d=".8" data-fx="pop"><span class="mono">Ctrl+C → Ctrl+V</span><div class="strike" data-b="4" data-d="1.6" data-fx="grow" data-sfx="buzz"></div></div>
        <div class="emo" style="font-size:100px;margin-top:24px" data-b="5" data-fx="pop" data-sfx="pop" data-float="8 3 0">🧠</div>
        <div class="good-chip" data-b="5" data-d=".8" data-fx="pop" data-sfx="ding">Понять, а не списать</div></div>`,
  },
  // 9 — Промпт
  {
    beats: [
      "Запрос к нейросети называют промптом.",
      "И от того, как ты его напишешь, зависит результат.",
      "Сравни.",
      "Плохой запрос: «расскажи про космос».",
      "Хороший: «Объясни, почему Луна не падает на Землю. Мне двенадцать лет. Ответь коротко, в пять предложений, и приведи один пример из жизни».",
      "Хороший промпт отвечает на вопросы: кто ты, что нужно сделать, какие детали важны и в каком виде нужен ответ.",
    ],
    html: `${H("Промпт — запрос к нейросети", "Как спросишь,", "так и ответит.")}
      <div class="emo" style="left:1580px;top:110px;font-size:170px" data-b="0" data-fx="pop" data-d=".4" data-sfx="pop" data-float="10 4 0">✍️</div>
      <div class="card" style="left:120px;top:400px;width:620px;height:440px" data-b="1" data-fx="up" data-sfx="whoosh">
        <div class="ch gray">Слабый промпт</div><div class="input" data-b="3" data-fx="type" data-dur="1.2" data-sfx="type">Расскажи про космос</div>
        ${[90, 70, 80].map((w, i) => `<div class="line" style="width:${w}%" data-b="3" data-d="${(1.6 + i * 0.2).toFixed(1)}" data-fx="grow"></div>`).join("")}
        <div class="badge bad" data-b="3" data-d="2.3" data-fx="pop" data-sfx="buzz">😐 Скучно и общо</div></div>
      <div class="vs" data-b="2" data-fx="pop" data-sfx="boop">VS</div>
      <div class="card grad" style="left:820px;top:400px;width:980px;height:440px" data-b="1" data-d=".3" data-fx="up">
        <div class="ch gray">Сильный промпт</div><div class="input" data-b="4" data-fx="type" data-dur="beat" data-sfx="type">Объясни, почему Луна не падает на Землю. Мне 12 лет. Ответь в 5 предложениях и приведи пример из жизни.</div>
        <div class="badge good" data-b="5" data-fx="pop" data-sfx="ding">🤩 Точно, понятно, интересно</div></div>
      ${[["👤", "Кто ты"], ["🎯", "Что сделать"], ["🔍", "Детали"], ["📋", "Формат ответа"]].map(([e, t], i) => PILL(120 + i * 400, 900, e, t, 5, 2.2 + i * 0.9)).join("")}`,
  },
  // 10 — Путь на курсе
  {
    beats: [
      "Вот что ждёт тебя на курсе.",
      "Сначала — разговор с искусственным интеллектом: научимся задавать правильные вопросы и получать точные ответы.",
      "Потом — вайб-кодинг: будем создавать настоящие сайты, описывая их словами.",
      "И в финале — ботмейкер: сделаем своего телеграм-бота.",
      "Три месяца — и у тебя будут собственные проекты.",
    ],
    html: `${H("Курс · 3 месяца", "Твой путь", "на курсе.")}
      <svg class="road" width="1920" height="1080" viewBox="0 0 1920 1080">
        <defs><linearGradient id="rg" x1="0" x2="1"><stop offset="0" stop-color="#5468f0"/><stop offset=".5" stop-color="#e3477e"/><stop offset="1" stop-color="#ee9a2a"/></linearGradient></defs>
        <path d="M180 940 Q370 860 560 820 T1040 680 T1480 540 T1760 420" fill="none" stroke="#dcdce4" stroke-width="16" stroke-dasharray="2 28" stroke-linecap="round" data-b="0" data-fx="fade"/>
        <path d="M180 940 Q370 860 560 820" fill="none" stroke="url(#rg)" stroke-width="16" stroke-linecap="round" data-b="1" data-fx="draw" data-dur="1.2"/>
        <path d="M560 820 Q800 770 1040 680" fill="none" stroke="#e3477e" stroke-width="16" stroke-linecap="round" data-b="2" data-fx="draw" data-dur="1.2"/>
        <path d="M1040 680 Q1260 590 1480 540" fill="none" stroke="#ee9a2a" stroke-width="16" stroke-linecap="round" data-b="3" data-fx="draw" data-dur="1.2"/>
        <path d="M1480 540 Q1620 480 1760 420" fill="none" stroke="#ee9a2a" stroke-width="16" stroke-linecap="round" data-b="4" data-fx="draw" data-dur="1.2"/>
        ${[[560, 820, "#5468f0", 1], [1040, 680, "#e3477e", 2], [1480, 540, "#ee9a2a", 3]].map(([x, y, c, b]) => `<circle cx="${x}" cy="${y}" r="24" fill="${c}" stroke="#fff" stroke-width="8" data-b="${b}" data-d="1" data-fx="fade"/>`).join("")}
      </svg>
      ${[["💬", "Месяц 1", "Разговор с ИИ", "правильные вопросы — точные ответы", 380, 600, 1], ["🌐", "Месяц 2", "Вайб-кодинг", "сайты, описанные словами", 860, 460, 2], ["🤖", "Месяц 3", "Ботмейкер", "свой телеграм-бот", 1300, 320, 3]]
        .map(([e, m, t, s, x, y, b]) => `<div class="mile" style="left:${x}px;top:${y}px" data-b="${b}" data-d=".9" data-fx="pop" data-sfx="pop"><span class="emo">${e}</span><div><small>${m}</small><b>${t}</b><i>${s}</i></div></div>`).join("")}
      <div class="emo" style="font-size:96px" data-b="0" data-fx="pop" data-d=".3" data-sfx="whoosh" data-move="0:180,940|1:560,820|2:1040,680|3:1480,540|4:1760,420" data-base="translate(-50%,-60%)">🚀</div>
      <div class="emo" style="left:1700px;top:250px;font-size:120px" data-b="4" data-d="1.1" data-fx="pop" data-sfx="ding" data-float="10 3 0">🏆</div>
      ${SPARK(1760, 330, 160, 4, 1.2, 10)}`,
  },
  // 11 — Задание и финал
  {
    beats: [
      "Задание до следующего урока.",
      "Открой любой чат с искусственным интеллектом и задай ему три вопроса.",
      "Первый — про то, что ты давно хотел понять.",
      "Второй — попроси придумать идею для своего сайта.",
      "А третий — спроси его самого, в чём он может ошибаться.",
      "Запиши, что получилось, и принеси на урок.",
      "До встречи!",
      "Сайты и боты — силой слов.",
    ],
    html: `${H("Домашнее задание", "Задай", "три вопроса.", 'data-o="6"')}
      ${PILL(120, 360, "💬", "Открой любой чат с ИИ", 1, 0, 'data-o="6"')}
      ${["О том, что ты давно хотел понять", "Попроси идею для своего сайта", "Спроси, в чём он может ошибаться"].map((t, i) => `
        <div class="task" style="top:${480 + i * 140}px" data-b="${i + 2}" data-fx="right" data-sfx="pop" data-o="6"><span class="box"><b data-b="${i + 2}" data-d="1.6" data-fx="pop" data-sfx="ding">✓</b></span><i class="dot ${["blue", "pink", "orange"][i]}"></i>${t}</div>`).join("")}
      <div class="card note" style="left:1340px;top:480px;width:460px;height:400px" data-b="5" data-fx="up" data-sfx="whoosh" data-o="6"><div class="emo" style="font-size:120px" data-float="10 3 0">✍️</div><b>Запиши ответы</b><small>и принеси на урок</small></div>
      ${ORB(760, 200, 400, 'data-b="6" data-fx="pop" data-sfx="chime" data-pulse="7"')}
      <div class="bye" data-b="6" data-d=".4" data-fx="up" data-o="7">До встречи! <span class="emo">👋</span></div>
      <h1 class="center big" style="top:640px"><span data-b="7" data-fx="up" data-sfx="whoosh">Сайты и боты.</span><span data-b="7" data-fx="up" data-d=".4">Силой слов.</span></h1>
      ${SPARK(960, 400, 300, 7, 0.6, 12)}
      <div class="cta" data-b="7" data-d="1.2" data-fx="up"><div><div class="eyebrow" style="position:static">НАБОР ОТКРЫТ</div><div class="nick">@ModeratorAlKifaya</div></div><div class="btn">Записаться</div></div>`,
  },
];
if (typeof module !== "undefined") module.exports = SCENES;
