// «Apple стекло»: рендер оверлея в PNG с прозрачностью + fx.json (что делать с видео) + events.json (звуки).
// node render.js cues.json out_dir [from_s] [to_s] [кадры через запятую]
// Пути картинок (img) в cues.json — относительно самого cues.json. anchor.json (лицо) подхватывается из cues.anchor.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const [cuesF, outDir, from, to, only] = process.argv.slice(2);
const data = JSON.parse(fs.readFileSync(cuesF, "utf8"));
const base = path.dirname(path.resolve(cuesF));
const fps = data.fps || 30;
for (const it of data.items) {
  if (it.img && !/^(file|https?|data):/.test(it.img)) it.img = "file://" + path.resolve(base, it.img);
  if (it.src) it.src = path.resolve(base, it.src);       // фон для замены (bg) — путь для compose.py
}
if (typeof data.anchor === "string") data.anchor = JSON.parse(fs.readFileSync(path.resolve(base, data.anchor), "utf8"));
fs.mkdirSync(outDir, { recursive: true });
const T0 = from ? parseFloat(from) : 0, T1 = to ? parseFloat(to) : data.duration;
const frames = only ? only.split(",").map(Number) : (() => { const a = []; for (let i = Math.round(T0 * fps); i < Math.round(T1 * fps); i++) a.push(i); return a; })();

(async () => {
  const b = await chromium.launch();
  const N = 3;
  const pages = await Promise.all(Array.from({ length: N }, () => b.newPage({ viewport: { width: 1080, height: 1920 } })));
  await Promise.all(pages.map(async (p) => {
    await p.goto("file://" + path.join(__dirname, "engine.html"));
    await p.evaluate(() => document.fonts.ready);
    await p.evaluate((d) => build(d), data);
    await p.evaluate(() => document.fonts.ready);
  }));
  const fx = {};
  await Promise.all(pages.map(async (p, w) => {
    for (let k = w; k < frames.length; k += N) {
      const i = frames[k];
      const name = `${String(i).padStart(5, "0")}.png`;
      const f = await p.evaluate((t) => render(t, "front"), i / fps);
      fx[i] = { blur: +f.blur.toFixed(4), dim: +f.dim.toFixed(4), zoom: +f.zoom.toFixed(4), lens: f.lens && f.lens.map((v) => +v.toFixed(2)), leak: +f.leak.toFixed(4),
                sil: +f.sil.toFixed(3), silColor: f.silColor, bg: f.bg, back: f.hasBack, face: [f.face.cx, f.face.cy, f.face.w, f.face.h].map((v) => +(+v).toFixed(1)) };
      await p.screenshot({ path: path.join(outDir, name), omitBackground: true });
      if (f.hasBack) {                                   // слой «за человеком» — отдельной картинкой
        await p.evaluate((t) => render(t, "back"), i / fps);
        fs.mkdirSync(path.join(outDir, "back"), { recursive: true });
        await p.screenshot({ path: path.join(outDir, "back", name), omitBackground: true });
      }
    }
  }));
  const ev = await pages[0].evaluate(() => events());
  // fx.json дополняется (можно рендерить кусками)
  const fxF = path.join(outDir, "fx.json");
  const old = fs.existsSync(fxF) ? JSON.parse(fs.readFileSync(fxF, "utf8")) : {};
  fs.writeFileSync(fxF, JSON.stringify({ ...old, ...fx }));
  fs.writeFileSync(path.join(outDir, "events.json"), JSON.stringify(ev, null, 1));
  console.log("кадров:", frames.length, "звуков:", ev.length);
  await b.close();
})();
