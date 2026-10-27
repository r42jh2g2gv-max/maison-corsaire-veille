"""Vidéo d'annonce Maison Corsaire — arrivée pour les fêtes de Noël.

Format vertical 1080x1920 (Reels / TikTok / Shorts), 15 s, 30 i/s.
Usage : python3 videos/noel/render.py  ->  videos/noel/maison-corsaire-noel.mp4
"""
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "maison-corsaire-noel.mp4"
AUDIO = HERE / "musique.wav"

W, H, FPS, DUR = 1080, 1920, 30, 15.0
NFRAMES = int(FPS * DUR)

GOLD = (222, 181, 106)
CREAM = (246, 236, 214)
NAVY_TOP = np.array([6, 14, 28], float)
NAVY_BOT = np.array([22, 16, 22], float)

FONTS = "/usr/share/fonts"
SERIF_BOLD = f"{FONTS}/truetype/crosextra/Caladea-Bold.ttf"
SERIF_ITALIC = f"{FONTS}/truetype/crosextra/Caladea-Italic.ttf"
SANS_LIGHT = f"{FONTS}/opentype/inter/Inter-Light.otf"
SANS_MED = f"{FONTS}/opentype/inter/Inter-Medium.otf"

rng = np.random.default_rng(7)


# --- utilitaires d'animation -------------------------------------------------

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def window(t, start, end, fade_in=0.8, fade_out=0.6):
    """Opacité 0..1 d'un élément visible entre start et end."""
    if t < start or t > end:
        return 0.0
    return min(ease((t - start) / fade_in), ease((end - t) / fade_out) if fade_out else 1.0)


# --- calques ------------------------------------------------------------------

class Layer:
    """Calque RGBA pré-rendu, composé sur l'image à une position donnée."""

    def __init__(self, img):
        a = np.asarray(img, dtype=np.float32) / 255.0
        self.rgb = a[..., :3]
        self.alpha = a[..., 3:4]
        self.h, self.w = a.shape[:2]

    def draw(self, frame, cx, cy, opacity):
        if opacity <= 0.001:
            return
        x0, y0 = int(cx - self.w / 2), int(cy - self.h / 2)
        fx0, fy0 = max(x0, 0), max(y0, 0)
        fx1, fy1 = min(x0 + self.w, W), min(y0 + self.h, H)
        if fx0 >= fx1 or fy0 >= fy1:
            return
        sub = frame[fy0:fy1, fx0:fx1]
        a = self.alpha[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * opacity
        rgb = self.rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
        sub *= 1 - a
        sub += rgb * a


def text_image(text, font_path, size, color, tracking=0, glow=0):
    font = ImageFont.truetype(font_path, size)
    widths = [font.getlength(c) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    asc, desc = font.getmetrics()
    pad = glow * 3 + 10
    img = Image.new("RGBA", (int(total) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for c, w in zip(text, widths):
        d.text((x, pad), c, font=font, fill=color + (255,))
        x += w + tracking
    if glow:
        halo = Image.new("RGBA", img.size, GOLD + (0,))
        halo.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(glow)).point(lambda v: int(v * 0.55)))
        img = Image.alpha_composite(halo, img)
    return img


def text_layer(*args, **kw):
    return Layer(text_image(*args, **kw))


def bottle_image():
    """Bouteille de rhum arrangé stylisée : verre ambré, fruits, étiquette, ruban."""
    s = 2  # sur-échantillonnage pour des bords propres
    bw, bh = 520 * s, 1000 * s
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = bw // 2

    body_w, body_top, body_bot = 420 * s, 400 * s, 980 * s
    neck_w, neck_top = 120 * s, 110 * s

    # silhouette (masque)
    mask = Image.new("L", (bw, bh), 0)
    m = ImageDraw.Draw(mask)
    m.rounded_rectangle([cx - body_w // 2, body_top, cx + body_w // 2, body_bot], radius=60 * s, fill=255)
    shoulder = [(cx - neck_w // 2, neck_top + 160 * s)]
    for i in range(41):
        a = i / 40
        x = cx - neck_w // 2 - (body_w - neck_w) / 2 * math.sin(a * math.pi / 2)
        y = neck_top + 160 * s + (body_top + 60 * s - neck_top - 160 * s) * (1 - math.cos(a * math.pi / 2))
        shoulder.append((x, y))
    right = [(2 * cx - x, y) for x, y in reversed(shoulder)]
    m.polygon(shoulder + right, fill=255)
    m.rectangle([cx - neck_w // 2, neck_top, cx + neck_w // 2, neck_top + 170 * s], fill=255)

    # liquide ambré en dégradé
    yy = np.linspace(0, 1, bh)[:, None]
    xx = np.abs(np.linspace(-1, 1, bw))[None, :]
    r = 120 + 110 * (1 - yy) - 40 * xx
    g = 55 + 60 * (1 - yy) - 30 * xx
    b = 18 + 15 * (1 - yy) + 0 * xx
    liquid = np.dstack([r, g, b, np.full_like(r, 255)]).clip(0, 255).astype(np.uint8)
    glass = Image.fromarray(liquid, "RGBA")
    level = neck_top + 250 * s
    glass_mask = mask.copy()
    ImageDraw.Draw(glass_mask).rectangle([0, 0, bw, level], fill=0)
    img.paste(glass, (0, 0), glass_mask)
    # verre vide au-dessus du niveau
    empty = Image.new("RGBA", (bw, bh), (40, 30, 30, 120))
    top_mask = mask.copy()
    ImageDraw.Draw(top_mask).rectangle([0, level, bw, bh], fill=0)
    img.paste(empty, (0, 0), top_mask)

    # fruits et épices dans le rhum
    fruits = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    f = ImageDraw.Draw(fruits)
    frng = np.random.default_rng(3)
    for _ in range(26):
        fx = cx + frng.uniform(-170, 170) * s
        fy = frng.uniform(560, 950) * s
        kind = frng.integers(0, 3)
        if kind == 0:  # tranche d'orange
            rr = frng.uniform(28, 42) * s
            f.ellipse([fx - rr, fy - rr, fx + rr, fy + rr], fill=(240, 140, 40, 210))
            f.ellipse([fx - rr * .8, fy - rr * .8, fx + rr * .8, fy + rr * .8], fill=(250, 175, 70, 200))
            for k in range(8):
                ang = k * math.pi / 4
                f.line([fx, fy, fx + rr * .8 * math.cos(ang), fy + rr * .8 * math.sin(ang)], fill=(255, 225, 160, 200), width=2 * s)
        elif kind == 1:  # morceau d'ananas
            rr = frng.uniform(22, 32) * s
            f.polygon([(fx, fy - rr), (fx + rr, fy + rr * .7), (fx - rr, fy + rr * .7)], fill=(250, 205, 70, 210))
        else:  # bâton de vanille / cannelle
            ang = frng.uniform(0, math.pi)
            ln = frng.uniform(60, 110) * s
            f.line([fx - ln * math.cos(ang), fy - ln * math.sin(ang), fx + ln * math.cos(ang), fy + ln * math.sin(ang)],
                   fill=(70, 35, 20, 230), width=10 * s)
    fruit_mask = Image.fromarray(np.minimum(np.asarray(glass_mask), np.asarray(fruits.getchannel("A"))))
    img.paste(fruits, (0, 0), fruit_mask)

    # reflet du verre
    hl = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(hl).rounded_rectangle([cx - body_w // 2 + 40 * s, body_top + 40 * s, cx - body_w // 2 + 75 * s, body_bot - 80 * s],
                                         radius=20 * s, fill=110)
    hl = hl.filter(ImageFilter.GaussianBlur(10 * s))
    img.paste(Image.new("RGBA", (bw, bh), (255, 240, 220, 255)), (0, 0), hl)

    # bouchon
    d.rounded_rectangle([cx - 70 * s, 20 * s, cx + 70 * s, neck_top + 20 * s], radius=14 * s, fill=(96, 62, 38, 255))
    d.rounded_rectangle([cx - 76 * s, neck_top - 10 * s, cx + 76 * s, neck_top + 30 * s], radius=10 * s, fill=GOLD + (255,))

    # ruban rouge de Noël sur le col
    d.rectangle([cx - neck_w // 2, neck_top + 110 * s, cx + neck_w // 2, neck_top + 145 * s], fill=(150, 18, 30, 255))
    d.polygon([(cx, neck_top + 128 * s), (cx - 90 * s, neck_top + 80 * s), (cx - 90 * s, neck_top + 175 * s)], fill=(170, 24, 36, 255))
    d.polygon([(cx, neck_top + 128 * s), (cx + 90 * s, neck_top + 80 * s), (cx + 90 * s, neck_top + 175 * s)], fill=(170, 24, 36, 255))
    d.ellipse([cx - 22 * s, neck_top + 106 * s, cx + 22 * s, neck_top + 150 * s], fill=(120, 12, 22, 255))

    # étiquette
    lx0, ly0, lx1, ly1 = cx - 165 * s, 600 * s, cx + 165 * s, 860 * s
    d.rounded_rectangle([lx0, ly0, lx1, ly1], radius=16 * s, fill=CREAM + (255,), outline=GOLD + (255,), width=5 * s)
    d.rounded_rectangle([lx0 + 14 * s, ly0 + 14 * s, lx1 - 14 * s, ly1 - 14 * s], radius=10 * s, outline=(150, 110, 50, 255), width=2 * s)
    f_mono = ImageFont.truetype(SERIF_BOLD, 74 * s)
    f_small = ImageFont.truetype(SERIF_BOLD, 26 * s)
    f_it = ImageFont.truetype(SERIF_ITALIC, 30 * s)
    d.text((cx, ly0 + 80 * s), "MC", font=f_mono, fill=(70, 40, 20, 255), anchor="mm")
    d.text((cx, ly0 + 158 * s), "MAISON CORSAIRE", font=f_small, fill=(70, 40, 20, 255), anchor="mm")
    d.text((cx, ly0 + 205 * s), "Rhum arrangé", font=f_it, fill=(140, 30, 30, 255), anchor="mm")

    # contour doré
    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(5))
    img.paste(Image.new("RGBA", (bw, bh), GOLD + (255,)), (0, 0), edge)

    img = img.resize((bw // s, bh // s), Image.LANCZOS)
    # halo chaud autour de la bouteille
    halo = Image.new("RGBA", (img.width + 200, img.height + 200), (255, 170, 80, 0))
    big = Image.new("L", halo.size, 0)
    big.paste(img.getchannel("A"), (100, 100))
    halo.putalpha(big.filter(ImageFilter.GaussianBlur(45)).point(lambda v: int(v * 0.5)))
    halo.alpha_composite(img, (100, 100))
    return halo


# --- décor ---------------------------------------------------------------------

def background():
    y = np.linspace(0, 1, H)[:, None, None]
    bg = NAVY_TOP * (1 - y) + NAVY_BOT * y
    return np.broadcast_to(bg, (H, W, 3)).astype(np.float32) / 255.0


def radial_glow(cx, cy, radius, color):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    g = np.exp(-d ** 2)[..., None]
    return g * (np.array(color, np.float32) / 255.0)


N_SNOW = 260
snow = {
    "x": rng.uniform(0, W, N_SNOW),
    "y": rng.uniform(-H, H, N_SNOW),
    "r": rng.uniform(1.5, 6.0, N_SNOW),
    "v": rng.uniform(60, 170, N_SNOW),
    "ph": rng.uniform(0, 2 * math.pi, N_SNOW),
}
N_STARS = 40
stars = {
    "x": rng.uniform(40, W - 40, N_STARS),
    "y": rng.uniform(80, H * 0.75, N_STARS),
    "s": rng.uniform(6, 16, N_STARS),
    "ph": rng.uniform(0, 2 * math.pi, N_STARS),
    "f": rng.uniform(1.0, 2.5, N_STARS),
}


def particles(t, star_level):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x, y0, r, v, ph in zip(snow["x"], snow["y"], snow["r"], snow["v"], snow["ph"]):
        y = (y0 + v * t * (r / 4 + 0.4)) % (H + 40) - 20
        xx = x + 25 * math.sin(t * 0.8 + ph)
        a = int(90 + 25 * r)
        d.ellipse([xx - r, y - r, xx + r, y + r], fill=(255, 255, 255, a))
    if star_level > 0:
        for x, y, s, ph, fr in zip(stars["x"], stars["y"], stars["s"], stars["ph"], stars["f"]):
            k = max(0.0, math.sin(t * fr * 2 + ph)) ** 3 * star_level
            if k < 0.05:
                continue
            ss = s * k
            col = GOLD + (int(255 * k),)
            d.polygon([(x, y - ss * 2), (x + ss * .25, y), (x, y + ss * 2), (x - ss * .25, y)], fill=col)
            d.polygon([(x - ss * 2, y), (x, y + ss * .25), (x + ss * 2, y), (x, y - ss * .25)], fill=col)
    return Layer(img.filter(ImageFilter.GaussianBlur(0.8)))


# --- musique (composée ici, libre de droits) ------------------------------------

def render_audio(path):
    sr = 44100
    n = int(sr * DUR)
    t = np.arange(n) / sr
    out = np.zeros(n)

    def note(freq, start, length, amp, kind="bell"):
        i0 = int(start * sr)
        i1 = min(n, i0 + int(length * sr))
        tt = t[: i1 - i0]
        if kind == "bell":
            env = np.exp(-tt * 3.2) * np.minimum(1, tt * 400)
            w = (np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * tt) * np.exp(-tt * 6)
                 + 0.2 * np.sin(2 * np.pi * freq * 5.4 * tt) * np.exp(-tt * 9))
        else:  # nappe
            env = np.minimum(1, tt / 1.2) * np.minimum(1, (length - tt) / 1.0)
            w = sum(np.sin(2 * np.pi * freq * dt * tt) for dt in (1, 1.003, 0.997, 2.0)) / 4
        out[i0:i1] += amp * env * w

    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    beat = 60 / 96
    # progression ré majeur : D - Bm - G - A
    chords = [[50, 57, 62, 66], [47, 54, 59, 62], [43, 50, 55, 59], [45, 52, 57, 61]]
    for bar in range(4):
        start = bar * 4 * beat
        for m in chords[bar % 4]:
            note(hz(m), start, 4 * beat + 0.6, 0.08, "pad")
        arp = [chords[bar % 4][k] + 12 for k in (1, 2, 3, 2, 1, 2, 3, 2)]
        for k, m in enumerate(arp):
            if start + k * beat / 2 > 1.0:  # les clochettes entrent après l'intro
                note(hz(m), start + k * beat / 2, 1.6, 0.10)
    # retour sur l'accord de ré pour la fin
    for m in (50, 57, 62, 66, 69):
        note(hz(m), 16 * beat, DUR - 16 * beat, 0.08, "pad")
    for k, m in enumerate((74, 78, 81, 86)):
        note(hz(m), 16 * beat + k * 0.12, 3.0, 0.13)

    # souffle de vent au moment de la révélation de la bouteille
    noise = np.random.default_rng(1).normal(0, 1, n)
    kernel = np.ones(60) / 60
    wind = np.convolve(noise, kernel, mode="same")
    env = np.exp(-((t - 7.6) / 0.7) ** 2)
    out += 0.5 * wind * env

    out *= np.minimum(1, t / 0.8) * np.minimum(1, (DUR - t) / 1.5)
    out = out / np.max(np.abs(out)) * 0.8
    stereo = np.stack([out, np.roll(out, 220)], axis=1)
    data = (stereo * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


# --- montage ---------------------------------------------------------------------

def main():
    render_audio(AUDIO)

    bg = background()
    warm = radial_glow(W / 2, 1000, 650, (120, 60, 20))

    l1a = text_layer("Cette année,", SERIF_ITALIC, 96, CREAM, glow=10)
    l1b = text_layer("Noël prend le large…", SERIF_ITALIC, 96, CREAM, glow=10)
    l2a = text_layer("FRUITS • ÉPICES", SERIF_BOLD, 64, GOLD, tracking=8, glow=8)
    l2b = text_layer("& rhum des îles", SERIF_ITALIC, 100, CREAM, glow=10)
    title = text_layer("MAISON CORSAIRE", SERIF_BOLD, 92, GOLD, tracking=6, glow=14)
    sub = text_layer("Rhum arrangé", SERIF_ITALIC, 66, CREAM, glow=8)
    cta = text_layer("ARRIVE POUR LES FÊTES", SERIF_BOLD, 62, GOLD, tracking=5, glow=10)
    cta2 = text_layer("Bientôt disponible  ·  Noël 2026", SANS_LIGHT, 40, CREAM)
    legal1 = text_layer("L'abus d'alcool est dangereux pour la santé.", SANS_MED, 27, (200, 195, 185))
    legal2 = text_layer("À consommer avec modération.", SANS_MED, 27, (200, 195, 185))
    bottle_src = bottle_image()

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", str(AUDIO),
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT)],
        stdin=subprocess.PIPE,
    )

    bottle_cache = {}
    for i in range(NFRAMES):
        t = i / FPS
        frame = bg.copy()

        reveal = ease((t - 7.4) / 1.6)
        frame += warm * reveal

        particles(t, 0.3 + 0.7 * reveal).draw(frame, W / 2, H / 2, 1.0)

        # scène 1 : accroche
        o = window(t, 0.4, 3.9)
        l1a.draw(frame, W / 2, 860 - 30 * ease((t - 0.4) / 1.2), o)
        o = window(t, 1.3, 3.9)
        l1b.draw(frame, W / 2, 990 - 30 * ease((t - 1.3) / 1.2), o)

        # scène 2 : promesse produit
        o = window(t, 4.2, 7.3)
        l2a.draw(frame, W / 2, 860 - 30 * ease((t - 4.2) / 1.2), o)
        o = window(t, 4.9, 7.3)
        l2b.draw(frame, W / 2, 990 - 30 * ease((t - 4.9) / 1.2), o)

        # scène 3 : révélation de la marque
        end = DUR - 0.05
        if t >= 7.4:
            p = ease((t - 7.4) / 1.8)
            scale = round(0.86 + 0.14 * p, 3)
            if scale not in bottle_cache:
                bottle_cache[scale] = Layer(bottle_src.resize(
                    (int(bottle_src.width * scale * 0.9), int(bottle_src.height * scale * 0.9)), Image.LANCZOS))
            float_y = 8 * math.sin((t - 7.4) * 1.6)
            bottle_cache[scale].draw(frame, W / 2, 1000 + 160 * (1 - p) + float_y, window(t, 7.4, end, 1.2, 0))

        title.draw(frame, W / 2, 300 - 25 * ease((t - 8.4) / 1.2), window(t, 8.4, end, 1.0, 0))
        sub.draw(frame, W / 2, 410, window(t, 9.0, end, 1.0, 0))
        cta.draw(frame, W / 2, 1500 - 20 * ease((t - 10.6) / 1.0), window(t, 10.6, end, 0.9, 0))
        cta2.draw(frame, W / 2, 1585, window(t, 11.3, end, 0.9, 0))

        legal1.draw(frame, W / 2, 1720, 1.0)
        legal2.draw(frame, W / 2, 1760, 1.0)

        # fondu au noir final
        fade = 1 - ease((t - 14.3) / 0.7) if t > 14.3 else 1.0
        fade *= ease(t / 0.4)
        out = (np.clip(frame * fade, 0, 1) * 255).astype(np.uint8)
        ff.stdin.write(out.tobytes())

        if i in (90, 180, 300, 400):
            Image.fromarray(out).save(HERE / f"apercu-{i // FPS:02d}s.jpg", quality=88)

    ff.stdin.close()
    ff.wait()
    AUDIO.unlink()
    print("OK ->", OUT)


if __name__ == "__main__":
    main()
