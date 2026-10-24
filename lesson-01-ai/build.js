// Сборка видеоурока: озвучка (RHVoice) + кадры слайдов (Playwright) -> lesson-01-ai.mp4
// Запуск: node lesson-01-ai/build.js [папка для временных файлов]
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const SLIDES = require("./slides.js");

const DIR = __dirname;
const WORK = path.resolve(process.argv[2] || path.join(DIR, "build"));
const VOICE = process.env.VOICE || "aleksandr-hq";
const FPS = 30, INTRO = 1.5, LOOP = 6;   // появление 1.5с, затем бесшовная петля 6с
const LEAD = 0.6, TAIL = 0.9, FADE = 0.35;

const run = (cmd, args, input) => execFileSync(cmd, args, { input, stdio: [input ? "pipe" : "ignore", "pipe", "pipe"] }).toString();
const dur = (f) => parseFloat(run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]));

// Обработка голоса: срез низа, тепло + разборчивость, де-эссер, компрессия, -16 LUFS
const VOICE_FX = "highpass=f=70,equalizer=f=160:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=2,equalizer=f=8500:t=q:w=1:g=-1.5," +
  "deesser=i=0.35,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=120:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=7";

(async () => {
  fs.mkdirSync(WORK, { recursive: true });

  // 1. Озвучка
  const durs = SLIDES.map((s, i) => {
    const raw = path.join(WORK, `raw${i}.wav`), out = path.join(WORK, `voice${i}.wav`);
    run("RHVoice-test", ["-p", VOICE, "-q", "max", "-o", raw], s.voice);
    run("ffmpeg", ["-y", "-i", raw, "-af", VOICE_FX, "-ar", "48000", "-ac", "2", out]);
    const d = dur(out);
    console.log(`голос ${i + 1}: ${d.toFixed(1)}с`);
    return d;
  });

  // 2. Кадры: появление + одна петля «дыхания» на каждый слайд
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto("file://" + path.join(DIR, "slides.html") + "?capture");
  await page.evaluate(() => document.fonts.ready);
  const total = Math.round((INTRO + LOOP) * FPS);
  for (let i = 0; i < SLIDES.length; i++) {
    const fdir = path.join(WORK, `f${i}`);
    fs.mkdirSync(fdir, { recursive: true });
    for (let k = 0; k < total; k++) {
      await page.evaluate(([i, t]) => window.seek(i, t), [i, k / FPS]);
      await page.screenshot({ path: path.join(fdir, `${String(k).padStart(4, "0")}.jpg`), type: "jpeg", quality: 95 });
    }
    console.log(`кадры ${i + 1}/${SLIDES.length}`);
  }
  await browser.close();

  // 3. Сегменты: кадры + голос, затухание в фон в конце каждого слайда
  const intro = Math.round(INTRO * FPS), loop = Math.round(LOOP * FPS);
  const list = [];
  SLIDES.forEach((_, i) => {
    const D = (LEAD + durs[i] + TAIL).toFixed(3), seg = path.join(WORK, `seg${i}.mp4`);
    run("ffmpeg", ["-y", "-framerate", String(FPS), "-i", path.join(WORK, `f${i}`, "%04d.jpg"), "-i", path.join(WORK, `voice${i}.wav`),
      "-filter_complex",
      `[0:v]split[x][y];[x]trim=end_frame=${intro}[a];[y]trim=start_frame=${intro},setpts=PTS-STARTPTS,loop=loop=-1:size=${loop}:start=0[b];` +
      `[a][b]concat=n=2:v=1,trim=duration=${D},fade=t=out:st=${(D - FADE).toFixed(3)}:d=${FADE}:color=0xF2F2F5,format=yuv420p[v];` +
      `[1:a]adelay=${LEAD * 1000}|${LEAD * 1000},apad,atrim=duration=${D}[au]`,
      "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "animation",
      "-c:a", "aac", "-b:a", "192k", "-ar", "48000", seg]);
    list.push(`file '${seg}'`);
  });
  fs.writeFileSync(path.join(WORK, "list.txt"), list.join("\n"));
  const out = path.join(WORK, "lesson-01-ai.mp4");
  run("ffmpeg", ["-y", "-f", "concat", "-safe", "0", "-i", path.join(WORK, "list.txt"), "-c", "copy", "-movflags", "+faststart", out]);
  console.log("готово:", out, dur(out).toFixed(1) + "с");
})();
