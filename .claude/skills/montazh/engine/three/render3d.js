// Рендер 3D-сцен по таймлайну: node render3d.js timeline.json out_dir [from_s] [to_s] [только_эти_секунды через запятую]
// timeline.json: {fps, scenes:[{t0, t1, spec:{type, p, cam, exposure}}]}
const { chromium } = require("playwright"); const fs = require("fs"); const path = require("path");
(async () => {
  const [tlf, out, a, b, only] = process.argv.slice(2); const TL = JSON.parse(fs.readFileSync(tlf, "utf8")); fs.mkdirSync(out, { recursive: true });
  const fps = TL.fps || 30, end = TL.scenes[TL.scenes.length - 1].t1;
  let frames = [];
  if (only) frames = only.split(",").map((s) => Math.round(parseFloat(s) * fps));
  else for (let n = Math.round((parseFloat(a) || 0) * fps); n < Math.round((b ? parseFloat(b) : end) * fps); n++) frames.push(n);
  const br = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--allow-file-access-from-files"] });
  const pg = await br.newPage({ viewport: { width: 1080, height: 1920 } });
  pg.on("pageerror", (e) => console.log("err:", e.message));
  await pg.goto("file://" + path.resolve(__dirname, "scenes3d.html")); await pg.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  let cur = -1; const t0 = Date.now();
  for (const n of frames) {
    const t = n / fps; let k = TL.scenes.findIndex((s) => t >= s.t0 && t < s.t1); if (k < 0) k = TL.scenes.length - 1;
    const s = TL.scenes[k];
    if (k !== cur) { await pg.evaluate((sp) => window.setup(sp), s.spec); cur = k; }
    await pg.evaluate(([u, tl]) => window.renderAt(u, tl), [(t - s.t0) / (s.t1 - s.t0), t - s.t0]);
    await pg.screenshot({ path: path.join(out, String(n).padStart(5, "0") + ".jpg"), type: "jpeg", quality: 93 });
    if (n % 60 === 0) console.log(`${t.toFixed(1)} с  (${((Date.now() - t0) / 1000).toFixed(0)} с прошло)`);
  }
  console.log("кадров:", frames.length, "сек/кадр:", ((Date.now() - t0) / 1000 / frames.length).toFixed(2)); await br.close();
})();
