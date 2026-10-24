// Сборка анимированного видеоурока: озвучка по фразам -> тайминг -> кадры (Playwright, 4 потока) -> звук (mix.py) -> mp4
// Запуск: node build-anim.js [рабочая папка]
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const SCENES = require("./scenes.js");

const DIR = __dirname;
const WORK = path.resolve(process.argv[2] || path.join(DIR, "build"));
const VOICE = process.env.VOICE || "ruslan";
const PY = process.env.PY || path.join(process.env.HOME, "venv-video/bin/python");
const FPS = 30, WORKERS = 4, GAP = 0.45, LEAD = 0.9, TAIL = 1.8;

const run = (cmd, args, input) => execFileSync(cmd, args, { input, stdio: [input ? "pipe" : "ignore", "pipe", "pipe"], maxBuffer: 1 << 26 }).toString();
const dur = (f) => parseFloat(run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]));
const VOICE_FX = "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse," +
  "highpass=f=70,equalizer=f=160:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=2,equalizer=f=8500:t=q:w=1:g=-1.5," +
  "deesser=i=0.35,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=120:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=7";

(async () => {
  fs.rmSync(path.join(WORK, "frames"), { recursive: true, force: true });
  fs.mkdirSync(path.join(WORK, "frames"), { recursive: true });

  // 1. Озвучка по фразам: нейроголос Piper (tts.py), запасной вариант — RHVoice (VOICE=aleksandr-hq)
  const jobs = SCENES.flatMap((s, i) => s.beats.map((text, b) => ({ text, out: path.join(WORK, `r${i}_${b}.wav`) })));
  if (["ruslan", "dmitri", "denis"].includes(VOICE)) {
    fs.writeFileSync(path.join(WORK, "tts.json"), JSON.stringify(jobs));
    run(PY, ["-I", path.join(DIR, "tts.py"), VOICE, path.join(WORK, "tts.json")]);
  } else jobs.forEach((j) => run("RHVoice-test", ["-p", VOICE, "-q", "max", "-o", j.out], j.text));
  const voice = SCENES.map((s, i) => s.beats.map((_, b) => {
    const raw = path.join(WORK, `r${i}_${b}.wav`), out = path.join(WORK, `v${i}_${b}.wav`);
    run("ffmpeg", ["-y", "-i", raw, "-af", VOICE_FX, "-ar", "48000", "-ac", "2", out]);
    return { file: out, d: dur(out) };
  }));
  console.log("озвучка готова");

  // 2. Тайминг: фраза занимает max(речь, длину своих анимаций)
  const browser = await chromium.launch();
  const pages = await Promise.all(Array.from({ length: WORKERS }, () => browser.newPage({ viewport: { width: 1920, height: 1080 } })));
  await Promise.all(pages.map(async (p) => { await p.goto("file://" + path.join(DIR, "anim.html") + "?capture"); await p.evaluate(() => document.fonts.ready); }));
  const vis = await pages[0].evaluate(() => items.map((list, i) => SCENES[i].beats.map((_, b) =>
    Math.max(0, ...list.filter((it) => it.b === b && it.dur !== "beat" && it.fx !== "none").map((it) => it.d + (it.dur ? +it.dur : it.fx === "type" ? 1.2 : 0.8))))));
  let T = 0;
  const tl = { scenes: [], voice: [] };
  SCENES.forEach((s, i) => {
    let t = LEAD + (i === 0 ? 0.4 : 0);
    const beats = s.beats.map((_, b) => {
      const at = t;
      tl.voice.push({ t: T + at, file: voice[i][b].file });
      t += Math.max(voice[i][b].d + GAP, vis[i][b] + 0.25);
      return at;
    });
    const sd = t + TAIL + (i === SCENES.length - 1 ? 2.5 : 0);
    tl.scenes.push({ start: T, dur: sd, beats });
    T += sd;
  });
  tl.total = T;
  await Promise.all(pages.map((p) => p.evaluate((t) => setTimeline(t), tl)));
  tl.sfx = await pages[0].evaluate(() => sfxEvents());
  tl.sfx.unshift({ t: 0.2, name: "riser" });
  fs.writeFileSync(path.join(WORK, "timeline.json"), JSON.stringify(tl, null, 1));
  console.log(`длительность ${T.toFixed(1)}с`);

  // 3. Кадры в 4 потока
  const N = Math.ceil(T * FPS);
  let done = 0;
  await Promise.all(pages.map(async (p, w) => {
    for (let k = w; k < N; k += WORKERS) {
      await p.evaluate((t) => render(t), k / FPS);
      await p.screenshot({ path: path.join(WORK, "frames", `${String(k).padStart(6, "0")}.jpg`), type: "jpeg", quality: 94 });
      if (++done % 900 === 0) console.log(`кадры ${done}/${N}`);
    }
  }));
  await browser.close();

  // 4. Звук и видео
  const wav = path.join(WORK, "audio.wav"), out = path.join(WORK, "lesson-01-ai-anim.mp4");
  run(PY, ["-I", path.join(DIR, "mix.py"), path.join(WORK, "timeline.json"), wav]);
  run("ffmpeg", ["-y", "-framerate", String(FPS), "-i", path.join(WORK, "frames", "%06d.jpg"), "-i", wav,
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out]);
  console.log("готово:", out, dur(out).toFixed(1) + "с");
})();
