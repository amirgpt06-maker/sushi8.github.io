// Рендер оверлея (текст, карточки, плашки) в PNG с прозрачностью по кадрам.
// Запуск: node render_overlay.js cues.json style.json out_dir duration_s fps
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const [cuesF, styleF, outDir, dur, fps] = process.argv.slice(2);
const cues = JSON.parse(fs.readFileSync(cuesF, "utf8")).cues;
const style = JSON.parse(fs.readFileSync(styleF, "utf8"));
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto("file://" + path.join(__dirname, "overlay.html"));
  await p.evaluate(() => document.fonts.ready);
  await p.evaluate(([c, s]) => build(c, s), [cues, style]);
  const wm = !!style.watermark?.text;
  const N = Math.ceil(parseFloat(dur) * parseFloat(fps));
  let written = 0;
  for (let i = 0; i < N; i++) {
    const t = i / parseFloat(fps);
    const any = await p.evaluate((t) => render(t), t);
    if (!any && !wm) continue;
    await p.screenshot({ path: path.join(outDir, `${String(i).padStart(5, "0")}.png`), omitBackground: true });
    written++;
  }
  console.log("кадров оверлея:", written, "из", N);
  await b.close();
})();
