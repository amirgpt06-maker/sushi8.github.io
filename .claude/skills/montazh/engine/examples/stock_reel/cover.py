import sys; sys.argv = ["x", "none"]
import numpy as np, cv2
import compose as C
from PIL import Image, ImageDraw, ImageFont, ImageFilter
F = C.FONTS
x = C.shot_frame(2, 1.85)                         # такси сзади, тёплый грейд
x = C.finish(x, 3, 'stock')
x = x * np.linspace(.55, .35, C.H)[:, None, None] ** 1.0 + 0
im = Image.fromarray((np.clip(x[..., ::-1], 0, 1) * 255).astype(np.uint8)).convert("RGBA")
# затемнение по центру под текст
ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
for i in range(60):
    a = int(150 * (1 - i / 60) ** 1.6); d.rectangle([0, 520 + i * 6, 1080, 1420 - i * 6], fill=(0, 0, 0, a // 6))
im.alpha_composite(ov)
d = ImageDraw.Draw(im)
def T(txt, y, font, fill, mark=None, sh=True):
    w = d.textlength(txt, font=font); x0 = (1080 - w) / 2
    if mark:
        asc, desc = font.getmetrics(); d.rounded_rectangle([x0 - 30, y + asc * .30, x0 + w + 30, y + asc * 1.16], 24, fill=mark)
    if sh:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(s).text((x0, y + 6), txt, font=font, fill=(0, 0, 0, 200)); im.alpha_composite(s.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(im).text((x0, y), txt, font=font, fill=fill)
H1 = ImageFont.truetype(F + "SF-Pro-Display-Heavy.otf", 150); H2 = ImageFont.truetype(F + "SF-Pro-Display-Heavy.otf", 112)
S1 = ImageFont.truetype(F + "SF-Pro-Display-Semibold.otf", 50)
T("ПОЧЕМУ ИИ", 560, H1, (255, 255, 255))
T("«ТУПИТ»?", 725, H1, (255, 214, 10))
d = ImageDraw.Draw(im)
T("ты не сказал ему", 960, S1, (240, 240, 240))
T("свой адрес", 1040, H2, (20, 18, 10), mark=(255, 214, 10), sh=False)
T("3 шага, чтобы он понял тебя", 1250, S1, (235, 235, 235))
im.convert("RGB").save("work/oblozhka-taksi.png")
print("ok")
