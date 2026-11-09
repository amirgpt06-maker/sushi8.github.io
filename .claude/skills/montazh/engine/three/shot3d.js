const { chromium } = require("playwright");
(async () => { const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--allow-file-access-from-files"] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on("console", (m) => console.log("console:", m.text())); p.on("pageerror", (e) => console.log("err:", e.message));
  await p.goto("file://" + process.argv[2]); await p.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
  const t0 = Date.now();
  for (const [i, t] of [[0, 0.3], [1, 1.2]]) { await p.evaluate((t) => window.renderAt(t), t); await p.screenshot({ path: `t3d_${i}.png` }); }
  console.log("мс на кадр:", (Date.now() - t0) / 2); await b.close(); })();
