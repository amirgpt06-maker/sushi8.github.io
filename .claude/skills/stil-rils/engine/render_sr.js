// «Стиль рилс»: рендер слоя типографики в PNG с прозрачностью + fx.json (размытие/затемнение основы, стеклянная плашка).
// node render_sr.js cues.json out_dir [кадры через запятую]
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const [cuesF, outDir, only] = process.argv.slice(2);
const data = JSON.parse(fs.readFileSync(cuesF, "utf8"));
const fps = data.fps || 30;
fs.mkdirSync(outDir, { recursive: true });
const frames = only ? only.split(",").map(Number) : Array.from({ length: Math.round(data.duration * fps) }, (_, i) => i);
(async () => {
  const b = await chromium.launch();
  const N = 4;
  const pages = await Promise.all(Array.from({ length: N }, () => b.newPage({ viewport: { width: 1080, height: 1920 } })));
  await Promise.all(pages.map(async (p) => {
    await p.goto("file://" + path.join(__dirname, "sr.html"));
    await p.evaluate((d) => build(d), data);
    await p.evaluate(() => document.fonts.ready);
    await p.evaluate(() => render(0)); await p.evaluate(() => document.fonts.ready);
  }));
  const fx = {};
  await Promise.all(pages.map(async (p, w) => {
    for (let k = w; k < frames.length; k += N) {
      const i = frames[k];
      await p.evaluate((t) => render(t), i / fps);                 // первый проход раскладывает блоки, второй — с верными размерами
      fx[i] = await p.evaluate((t) => render(t), i / fps);
      await p.screenshot({ path: path.join(outDir, `${String(i).padStart(5, "0")}.png`), omitBackground: true });
    }
  }));
  fs.writeFileSync(path.join(outDir, "fx.json"), JSON.stringify(fx));
  await b.close();
  console.log("кадров:", frames.length);
})();
