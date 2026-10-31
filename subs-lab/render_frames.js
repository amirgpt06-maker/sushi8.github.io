// Рендер оверлея arabic.html в PNG с прозрачностью.
// node render_frames.js data.json out_dir from_s to_s fps [кадры через запятую — только они]
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const [dataF, outDir, from, to, fps, only] = process.argv.slice(2);
const data = JSON.parse(fs.readFileSync(dataF, "utf8"));
fs.mkdirSync(outDir, { recursive: true });
const F = parseFloat(fps);
const frames = only ? only.split(",").map(Number) : (() => { const a = []; for (let i = Math.round(from * F); i < Math.round(to * F); i++) a.push(i); return a; })();

(async () => {
  const b = await chromium.launch();
  const N = 3;   // параллельные вкладки
  const pages = await Promise.all(Array.from({ length: N }, () => b.newPage({ viewport: { width: 1080, height: 1920 } })));
  await Promise.all(pages.map(async (p) => {
    await p.goto("file://" + path.join(__dirname, "arabic.html"));
    await p.evaluate(() => document.fonts.ready);
    await p.evaluate((d) => build(d), data);
    await p.evaluate(() => document.fonts.ready);
  }));
  await Promise.all(pages.map(async (p, w) => {
    for (let k = w; k < frames.length; k += N) {
      const i = frames[k];
      await p.evaluate((t) => render(t), i / F);
      await p.screenshot({ path: path.join(outDir, `${String(i).padStart(5, "0")}.png`), omitBackground: true });
    }
  }));
  console.log("кадров:", frames.length);
  await b.close();
})();
