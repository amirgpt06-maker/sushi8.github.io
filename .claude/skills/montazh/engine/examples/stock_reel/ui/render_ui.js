// node render_ui.js scene dur outdir [transparent=1] [from=0]
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const [scene, dur, out, tr = '1', from = '0', only] = process.argv.slice(2);
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on('console', m => console.log('console:', m.text())); p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + path.resolve(__dirname, 'ui.html'));
  const N = Math.round(parseFloat(dur) * 30);
  const list = only ? only.split(',').map(Number) : [...Array(N + 1).keys()];
  for (const n of list) {
    const t = parseFloat(from) + n / 30;
    await p.evaluate(([s, t]) => window.renderScene(s, t), [scene, t]);
    await p.screenshot({ path: `${out}/${String(n).padStart(5, '0')}.png`, omitBackground: tr === '1' });
  }
  await b.close();
})();
