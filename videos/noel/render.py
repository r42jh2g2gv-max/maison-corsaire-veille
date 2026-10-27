"""Vidéo d'annonce Maison Corsaire — arrivée pour Noël.

Mer au clair de lune (ouverture), nuit étoilée en dégradé, étoiles filantes, coffre au trésor et grelots (planche
d'illustrations de Noël), puis les trois cuvées et le logo. Couleurs et polices de
la charte (cuivre, ivoire, bordeaux / vert forêt / brun, Playfair Display + Montserrat).
Musique composée dans le script, avec grelots.

Format story 1080x1920, 20 s, 30 i/s.
Usage : python3 videos/noel/render.py  ->  videos/noel/maison-corsaire-noel.mp4
"""
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
ASSETS = HERE.parent / "assets"
OUT = HERE / "maison-corsaire-noel.mp4"
AUDIO = HERE / "musique.wav"

W, H, FPS, DUR = 1080, 1920, 30, 20.0
NFRAMES = int(FPS * DUR)
S1, S2, S3, S4 = 0.0, 5.0, 10.0, 12.5  # débuts de scène, calés sur les mesures de la musique
BAND_H = 540  # trois bandeaux, en laissant le bas libre pour la mention légale

# palette de la charte
IVOIRE = (247, 241, 231)
CUIVRE = (208, 132, 84)  # cuivre dorure, sur fonds foncés
BORDEAUX = (58, 11, 27)
VERT = (15, 58, 39)
BRUN = (79, 39, 17)
# dégradé de nuit : du noir bleuté au bleu marin de la charte, éclairci vers l'horizon
NUIT = [(0.0, (2, 5, 14)), (0.45, (8, 20, 42)), (0.8, (20, 40, 60)), (1.0, (38, 64, 92))]

FONTS = ASSETS / "fonts"
PLAYFAIR = str(FONTS / "playfair-display-latin-400-normal.woff")
PLAYFAIR_IT = str(FONTS / "playfair-display-latin-400-italic.woff")
MONTSERRAT = str(FONTS / "montserrat-latin-500-normal.woff")
MONTSERRAT_SEMI = str(FONTS / "montserrat-latin-600-normal.woff")

rng = np.random.default_rng(11)


# --- utilitaires d'animation -------------------------------------------------

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 3 * x * x - 2 * x * x * x


def window(t, start, end, fade_in=0.9, fade_out=0.6):
    """Opacité 0..1 d'un élément visible entre start et end."""
    if t < start or t > end:
        return 0.0
    out = ease((end - t) / fade_out) if fade_out else 1.0
    return min(ease((t - start) / fade_in), out)


def tone(color, k):
    """Couleur légèrement éclaircie, pour le ton sur ton."""
    return tuple(int(c + (255 - c) * k) for c in color)


# --- calques ------------------------------------------------------------------

class Layer:
    """Calque RGBA pré-rendu, composé sur l'image à une position donnée."""

    def __init__(self, img):
        a = np.asarray(img, dtype=np.float32) / 255.0
        self.rgb = a[..., :3]
        self.alpha = a[..., 3:4]
        self.h, self.w = a.shape[:2]

    def draw(self, frame, cx, cy, opacity=1.0):
        if opacity <= 0.001:
            return
        x0, y0 = int(round(cx - self.w / 2)), int(round(cy - self.h / 2))
        fx0, fy0 = max(x0, 0), max(y0, 0)
        fx1, fy1 = min(x0 + self.w, W), min(y0 + self.h, H)
        if fx0 >= fx1 or fy0 >= fy1:
            return
        sub = frame[fy0:fy1, fx0:fx1]
        a = self.alpha[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * opacity
        sub *= 1 - a
        sub += self.rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * a


def text_image(text, font_path, size, color, tracking=0):
    font = ImageFont.truetype(font_path, size)
    widths = [font.getlength(c) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    asc, desc = font.getmetrics()
    img = Image.new("RGBA", (int(total) + 8, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 4
    for c, w in zip(text, widths):
        d.text((x, 4), c, font=font, fill=color + (255,))
        x += w + tracking
    return img


def text_layer(*args, **kw):
    return Layer(text_image(*args, **kw))


def asset(name, width=None, height=None):
    img = Image.open(ASSETS / f"{name}.png").convert("RGBA")
    if width:
        height = round(img.height * width / img.width)
    elif height:
        width = round(img.width * height / img.height)
    else:
        return img
    return img.resize((width, height), Image.LANCZOS)


class Swinging:
    """Ornement suspendu qui se balance autour de son point d'attache (en haut, au centre)."""

    def __init__(self, img):
        # point d'attache au centre du canevas, avec assez de marge pour ne rien couper en tournant
        side = 2 * math.ceil(math.hypot(img.width / 2, img.height)) + 4
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(img, ((side - img.width) // 2, side // 2))
        self.canvas = canvas
        self.cache = {}

    def draw(self, frame, px, py, angle, opacity=1.0):
        key = round(angle * 4) / 4
        if key not in self.cache:
            self.cache[key] = Layer(self.canvas.rotate(key, resample=Image.BICUBIC))
        self.cache[key].draw(frame, px, py, opacity)


# --- nuit étoilée ----------------------------------------------------------------

def night_sky():
    y = np.linspace(0, 1, H)
    stops = [s for s, _ in NUIT]
    sky = np.stack([np.interp(y, stops, [c[k] for _, c in NUIT]) for k in range(3)], axis=1)[:, None, :]
    img = Image.fromarray(np.broadcast_to(sky, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    srng = np.random.default_rng(5)
    for _ in range(900):  # poussière d'étoiles fixe
        x, yy = srng.uniform(0, W), srng.uniform(0, H * 0.9)
        r = srng.choice([0.6, 0.9, 1.2, 1.6], p=[0.5, 0.3, 0.15, 0.05])
        v = int(srng.uniform(70, 200) * (1 - yy / H * 0.5))
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=(v, v, min(255, v + 25), 255))
    return np.asarray(img.convert("RGB"), np.float32) / 255.0


N_TWINKLE = 70
twinkle = {
    "x": rng.uniform(20, W - 20, N_TWINKLE),
    "y": rng.uniform(20, H * 0.85, N_TWINKLE),
    "r": rng.uniform(1.6, 3.4, N_TWINKLE),
    "f": rng.uniform(0.6, 1.8, N_TWINKLE),
    "ph": rng.uniform(0, 2 * math.pi, N_TWINKLE),
}
N_SNOW = 110
snow = {
    "x": rng.uniform(0, W, N_SNOW),
    "y": rng.uniform(0, H, N_SNOW),
    "r": rng.uniform(1.5, 4.0, N_SNOW),
    "v": rng.uniform(40, 100, N_SNOW),
    "ph": rng.uniform(0, 2 * math.pi, N_SNOW),
}
# étoiles filantes : (départ, x, y, déplacement x, déplacement y)
# (en dehors des zones de texte ; elles passent derrière les illustrations et le logo)
METEORS = [(0.5, 1020, 120, -720, 400), (1.8, 700, 50, -500, 280), (2.9, 1070, 330, -380, 210),
           (3.9, 1060, 230, -480, 270), (4.5, 520, 60, -400, 220),
           (10.2, 1000, 240, -620, 340), (11.3, 620, 90, -450, 250), (12.1, 1060, 380, -420, 240),
           (14.6, 1000, 60, -520, 290), (16.2, 560, 80, -380, 210), (17.6, 1040, 190, -480, 270),
           (18.8, 760, 60, -420, 230)]
METEOR_DUR = 1.0


def draw_meteor(d, t, t0, x0, y0, dx, dy):
    p = (t - t0) / METEOR_DUR
    if not 0 <= p <= 1:
        return
    p = ease(p)
    glow = math.sin(math.pi * min(1.0, (t - t0) / METEOR_DUR))
    hx, hy = x0 + dx * p, y0 + dy * p
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    tail = min(340, length * p)
    steps = 16
    for k in range(steps):  # halo doux autour de la traînée
        a0, a1 = tail * k / steps, tail * (k + 1) / steps
        d.line([(hx - ux * a0, hy - uy * a0), (hx - ux * a1, hy - uy * a1)],
               fill=(255, 230, 190, int(70 * (1 - k / steps) * glow)), width=10)
    for k in range(steps):  # traînée qui s'estompe vers l'arrière
        a0, a1 = tail * k / steps, tail * (k + 1) / steps
        alpha = (1 - k / steps) ** 1.6
        d.line([(hx - ux * a0, hy - uy * a0), (hx - ux * a1, hy - uy * a1)],
               fill=(255, 244, 220, int(255 * alpha * glow)), width=max(1, round(4 * (1 - k / steps))))
    d.ellipse([hx - 4, hy - 4, hx + 4, hy + 4], fill=(255, 250, 235, int(255 * glow)))


# étoiles dorées de la planche, qui scintillent : (x, y, taille, phase)
GOLD_STARS = [(150, 560, 70, 0.0), (985, 470, 56, 1.7), (640, 300, 44, 3.1), (110, 1180, 50, 4.4),
              (980, 1120, 64, 2.2), (520, 120, 38, 5.3), (300, 900, 34, 0.9), (960, 1620, 40, 3.8)]


# --- mer au clair de lune (scène d'ouverture) -------------------------------------

SEA = Image.open(ASSETS / "nuit-mer.jpg").convert("RGB")
HORIZON = 822  # ligne d'horizon de la photo, à l'écran
N_GLINT = 110
glints = {  # éclats de lumière dans le reflet de la lune, plus larges vers le premier plan
    "y": rng.uniform(HORIZON + 8, H, N_GLINT),
    "f": rng.uniform(3.0, 7.0, N_GLINT),
    "ph": rng.uniform(0, 2 * math.pi, N_GLINT),
    "r": rng.uniform(1.2, 3.2, N_GLINT),
}
glints["x"] = 790 + rng.normal(0, 1, N_GLINT) * (25 + (glints["y"] - HORIZON) * 0.11)


def sea_frame(t):
    """Photo de la mer avec un zoom très lent (léger assombrissement pour les textes)."""
    z = 1 + 0.07 * ease_io(t / (S2 + 2.0))
    bw = min(SEA.width, SEA.height * W / H) / z
    bh = bw * H / W
    cx, cy = SEA.width / 2, SEA.height / 2
    img = SEA.resize((W, H), Image.BICUBIC, box=(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2))
    return np.asarray(img, np.float32) / 255.0 * SEA_SHADE


# assombrissement doux du bas de l'image, pour la lisibilité de la mention sanitaire
SEA_SHADE = (0.9 - 0.5 * np.clip((np.arange(H) - 1520) / 220, 0, 1))[:, None, None].astype(np.float32)


def glint_layer(t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x, y, f, ph, r in zip(glints["x"], glints["y"], glints["f"], glints["ph"], glints["r"]):
        k = max(0.0, math.sin(t * f + ph)) ** 6
        if k > 0.05:
            d.ellipse([x - r * 1.8, y - r * 0.7, x + r * 1.8, y + r * 0.7], fill=(255, 232, 190, int(255 * k)))
    return Layer(img.filter(ImageFilter.GaussianBlur(0.8)))


def sky_layer(t, snow_level, star_max_y=H):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x, y, r, f, ph in zip(twinkle["x"], twinkle["y"], twinkle["r"], twinkle["f"], twinkle["ph"]):
        if y > star_max_y:  # pas d'étoiles sur la mer
            continue
        k = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * f * 2 * math.pi / 2 + ph)) ** 2
        rr = r * (0.7 + 0.3 * k)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 250, 235, int(255 * k)))
    for x, y0, r, v, ph in zip(snow["x"], snow["y"], snow["r"], snow["v"], snow["ph"]):
        y = (y0 + v * t) % (H + 20) - 10
        xx = x + 18 * math.sin(t * 0.7 + ph)
        d.ellipse([xx - r, y - r, xx + r, y + r], fill=IVOIRE + (int(160 * snow_level),))
    for meteor in METEORS:
        draw_meteor(d, t, *meteor)
    return Layer(img.filter(ImageFilter.GaussianBlur(0.6)))


# --- carte marine (fond des bandeaux de cuvée) -------------------------------------

def chart_image(w, h, color, seed=0):
    """Carte marine très fine, ton sur ton : quadrillage et lignes de rhumb."""
    s = 2
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    line = tone(color, 0.10) + (255,)
    faint = tone(color, 0.06) + (255,)
    for x in range(0, w * s, 135 * s):
        d.line([(x, 0), (x, h * s)], fill=faint, width=s)
    for y in range(0, h * s, 135 * s):
        d.line([(0, y), (w * s, y)], fill=faint, width=s)
    crng = np.random.default_rng(seed)
    for _ in range(2):
        ox, oy = crng.uniform(0.15, 0.85) * w * s, crng.uniform(0.15, 0.85) * h * s
        for k in range(16):
            ang = k * math.pi / 8
            d.line([(ox, oy), (ox + 3000 * s * math.cos(ang), oy + 3000 * s * math.sin(ang))], fill=line, width=s)
    return img.resize((w, h), Image.LANCZOS)


# --- éléments de marque ----------------------------------------------------------

def frame_path(x0, y0, x1, y1):
    """Périmètre d'un rectangle, partant du milieu haut, dans les deux sens."""
    cx = (x0 + x1) / 2
    left = [(cx, y0), (x0, y0), (x0, y1), (cx, y1)]
    right = [(cx, y0), (x1, y0), (x1, y1), (cx, y1)]
    return left, right


def partial(path, frac):
    segs = list(zip(path, path[1:]))
    lengths = [math.dist(a, b) for a, b in segs]
    remaining = sum(lengths) * frac
    pts = [path[0]]
    for (a, b), ln in zip(segs, lengths):
        if remaining >= ln:
            pts.append(b)
            remaining -= ln
        else:
            k = remaining / ln if ln else 0
            pts.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
            break
    return pts


def double_filet(frac):
    """Double filet cuivre de l'étiquette, tracé progressivement."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for inset, width in ((70, 4), (86, 2)):
        for path in frame_path(inset, inset + 60, W - inset, H - inset - 60):
            pts = partial(path, frac)
            if len(pts) > 1:
                d.line(pts, fill=CUIVRE + (255,), width=width, joint="curve")
    return Layer(img)


def cuvee_band(name, wind, color, seed, bottle, bottle_left):
    bw, bh = W, BAND_H
    img = Image.new("RGBA", (bw, bh), color + (255,))
    img.alpha_composite(chart_image(bw, bh, color, seed=seed))
    d = ImageDraw.Draw(img)
    d.line([(60, 26), (bw - 60, 26)], fill=CUIVRE + (255,), width=3)
    d.line([(60, 36), (bw - 60, 36)], fill=CUIVRE + (255,), width=1)
    d.line([(60, bh - 26), (bw - 60, bh - 26)], fill=CUIVRE + (255,), width=3)
    d.line([(60, bh - 36), (bw - 60, bh - 36)], fill=CUIVRE + (255,), width=1)
    b = asset(f"bouteille-{bottle}", height=bh - 96)
    bx = 150 if bottle_left else bw - 150 - b.width
    img.alpha_composite(b, (bx, 48))
    tx = (bx + b.width + bw - 60) // 2 if bottle_left else (60 + bx) // 2  # centre de la zone de texte
    t = text_image(name, PLAYFAIR, 140, IVOIRE)
    img.alpha_composite(t, (tx - t.width // 2, bh // 2 - t.height // 2 - 40))
    c = text_image(wind, MONTSERRAT_SEMI, 30, CUIVRE, tracking=7)
    img.alpha_composite(c, (tx - c.width // 2, bh // 2 + 80))
    return Layer(img)


# --- musique (celle de la première version, prolongée, avec grelots) -------------

def render_audio(path):
    sr = 44100
    n = int(sr * DUR)
    t = np.arange(n) / sr
    out = np.zeros(n)
    arng = np.random.default_rng(2)

    def note(freq, start, length, amp, kind="bell"):
        i0 = int(start * sr)
        i1 = min(n, i0 + int(length * sr))
        if i0 >= n:
            return
        tt = t[: i1 - i0]
        if kind == "bell":
            env = np.exp(-tt * 3.2) * np.minimum(1, tt * 400)
            w = (np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * tt) * np.exp(-tt * 6)
                 + 0.2 * np.sin(2 * np.pi * freq * 5.4 * tt) * np.exp(-tt * 9))
        else:  # nappe
            env = np.minimum(1, tt / 1.2) * np.minimum(1, (length - tt) / 1.0)
            w = sum(np.sin(2 * np.pi * freq * dt * tt) for dt in (1, 1.003, 0.997, 2.0)) / 4
        out[i0:i1] += amp * env * w

    # grelots : petites billes métalliques, partiels aigus inharmoniques + souffle aigu
    jingles = []
    for _ in range(6):
        ln = int(0.18 * sr)
        tt = t[:ln]
        w = sum(np.sin(2 * np.pi * arng.uniform(2600, 8500) * tt + arng.uniform(0, 6)) * np.exp(-tt * arng.uniform(22, 45))
                for _ in range(9))
        noise = arng.normal(0, 1, ln)
        hiss = noise - np.convolve(noise, np.ones(6) / 6, mode="same")
        jingles.append((w / 9 + 0.5 * hiss * np.exp(-tt * 40)) * np.minimum(1, tt * 2000))

    def shake(start, amp):
        for _ in range(3):  # plusieurs grelots qui sonnent presque ensemble
            j = jingles[arng.integers(len(jingles))]
            i0 = int((start + arng.uniform(0, 0.03)) * sr)
            i1 = min(n, i0 + len(j))
            if i0 < n:
                out[i0:i1] += amp * arng.uniform(0.6, 1.0) * j[: i1 - i0]

    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    beat = 60 / 96
    # progression ré majeur : D - Bm - G - A - G, puis retour sur ré au logo
    chords = [[50, 57, 62, 66], [47, 54, 59, 62], [43, 50, 55, 59], [45, 52, 57, 61], [43, 50, 55, 59]]
    for bar, chord in enumerate(chords):
        start = bar * 4 * beat
        for m in chord:
            note(hz(m), start, 4 * beat + 0.6, 0.08, "pad")
        arp = [chord[k] + 12 for k in (1, 2, 3, 2, 1, 2, 3, 2)]
        for k, m in enumerate(arp):
            if start + k * beat / 2 > 1.0:  # les clochettes entrent après l'intro
                note(hz(m), start + k * beat / 2, 1.6, 0.10)
    for m in (50, 57, 62, 66, 69):
        note(hz(m), S4, DUR - S4, 0.08, "pad")
    for k, m in enumerate((74, 78, 81, 86)):
        note(hz(m), S4 + k * 0.12, 3.0, 0.13)
    # mélodie de clochettes sur le final
    for k, m in enumerate((81, 78, 74, 76, 78, 81, 86)):
        note(hz(m), S4 + 1.5 * beat * (k + 2), 2.0, 0.09)

    # grelots en rythme : discrets au début, plus présents au final
    k = 0
    while k * beat / 2 < DUR - 1.0:
        s = k * beat / 2
        if s > 0.8:
            level = 0.10 if s < S2 else 0.14 if s < S4 else 0.20
            shake(s, level * (1.0 if k % 2 == 0 else 0.55))
        k += 1
    for s in (0.8, S3, S4):  # secousses à l'apparition des grelots
        for d in np.arange(0, 0.5, 0.06):
            shake(s + d, 0.22 * (1 - d * 1.5))

    # souffle de vent sur les changements de scène
    noise = np.random.default_rng(1).normal(0, 1, n)
    wind = np.convolve(noise, np.ones(60) / 60, mode="same")
    for s, amp in ((S2, 0.45), (S4, 0.5)):
        out += amp * wind * np.exp(-((t - s) / 0.7) ** 2)

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

    sky = night_sky()
    gold_star = asset("noel-etoile")
    gold_stars = [(x, y, Layer(gold_star.resize((s, round(s * gold_star.height / gold_star.width)), Image.LANCZOS)), ph)
                  for x, y, s, ph in GOLD_STARS]
    chest = Layer(asset("noel-coffre", width=920))
    bells_left = Swinging(asset("noel-grelots-suspendus", width=260))
    bell_right = Swinging(asset("noel-grelot-suspendu", width=210))
    # au final, plus petits, suspendus au filet de l'étiquette
    small_left = Swinging(asset("noel-grelots-suspendus", width=180))
    small_right = Swinging(asset("noel-grelot-suspendu", width=150))
    bow_bells = Layer(asset("noel-grelots-noeud", width=460))

    s1a = text_layer("Au bout du voyage,", PLAYFAIR_IT, 92, IVOIRE)
    s1b = text_layer("un trésor vous attend.", PLAYFAIR_IT, 92, IVOIRE)

    bands = [
        cuvee_band("Noroît", "VENT DU NORD-OUEST", BORDEAUX, 1, "noroit", True),
        cuvee_band("Zéphyr", "VENT D'OUEST", VERT, 2, "zephyr", False),
        cuvee_band("Suroît", "VENT DU SUD-OUEST", BRUN, 3, "suroit", True),
    ]

    s3a = text_layer("Trois vents.", PLAYFAIR_IT, 104, IVOIRE)
    s3b = text_layer("Une même Maison.", PLAYFAIR_IT, 104, IVOIRE)

    logo = Layer(asset("logo-cuivre", width=460))
    bottles = [Layer(asset(f"bouteille-{n}", height=620)) for n in ("noroit", "zephyr", "suroit")]
    sep = Layer(Image.new("RGBA", (120, 3), CUIVRE + (255,)))
    cta = text_layer("ARRIVE POUR NOËL", MONTSERRAT_SEMI, 46, IVOIRE, tracking=10)
    cta2 = text_layer("FAIT MAIN  ·  FABRICATION FRANÇAISE", MONTSERRAT, 28, CUIVRE, tracking=5)
    handle = text_layer("@maisoncorsaire", PLAYFAIR_IT, 46, IVOIRE)
    legal1 = text_layer("L'abus d'alcool est dangereux pour la santé.", MONTSERRAT, 26, IVOIRE)
    legal2 = text_layer("À consommer avec modération.", MONTSERRAT, 26, IVOIRE)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", str(AUDIO),
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT)],
        stdin=subprocess.PIPE,
    )

    filet_cache = {}
    previews = {int(s * FPS) for s in (1.0, 4.4, 5.9, 10.7, 18.2)}
    for i in range(NFRAMES):
        t = i / FPS
        # ouverture sur la mer au clair de lune, puis la nuit en dégradé (pendant les bandeaux)
        sea = 1 - ease_io((t - S2 - 1.0) / 1.0)
        if sea >= 1:
            frame = sea_frame(t)
        elif sea > 0:
            frame = sea_frame(t) * sea + sky * (1 - sea)
        else:
            frame = sky.copy()
        if sea > 0:
            glint_layer(t).draw(frame, W / 2, H / 2, sea)

        # étoiles qui scintillent et neige
        for x, y, star, ph in gold_stars:
            if sea > 0 and y > HORIZON - 60:
                continue
            star.draw(frame, x, y, max(0.0, math.sin(t * 1.3 + ph)) ** 2 * ease(t / 1.5))
        sky_layer(t, 0.6 + 0.4 * ease((t - S4) / 1.0), HORIZON - 40 if sea > 0 else H).draw(frame, W / 2, H / 2)

        # scène 1 : le coffre au trésor sort du reflet de la lune
        s1a.draw(frame, W / 2, 640 - 20 * ease((t - 1.4) / 1.2), window(t, 1.4, S2 - 0.1))
        s1b.draw(frame, W / 2, 760 - 20 * ease((t - 2.2) / 1.2), window(t, 2.2, S2 - 0.1))
        chest.draw(frame, W / 2, 1250 + 120 * (1 - ease((t - 2.8) / 1.4)), window(t, 2.8, S2 - 0.1, 1.2, 0.5))

        # grelots suspendus au bord haut de l'écran, qui se balancent
        bells_op = window(t, 0.8, S2 + 0.4, 0.8, 0.4)
        drop = 120 * (1 - ease((t - 0.8) / 1.2))
        bells_left.draw(frame, 180, -drop, 6 * math.sin(t * 2.6), bells_op)
        bell_right.draw(frame, 965, -drop, -5 * math.sin(t * 2.3 + 1.0), bells_op)

        # scène 2 : les trois cuvées, une par vent
        if S2 <= t < S3 + 0.1:
            for k, band in enumerate(bands):
                start = S2 + 0.35 * k
                side = -1 if k % 2 == 0 else 1
                x_in = side * W * (1 - ease((t - start) / 0.9))
                x_out = -side * W * ease_io((t - (S3 - 0.6) - 0.1 * k) / 0.6)
                band.draw(frame, W / 2 + x_in + x_out, BAND_H / 2 + k * BAND_H)

        # scène 3 : la devise, sous les grelots enrubannés
        op = window(t, S3, S4 - 0.1, 0.8, 0.5)
        bow_bells.draw(frame, W / 2 + 6 * math.sin(t * 9) * math.exp(-(t - S3) * 2), 640, op)
        s3a.draw(frame, W / 2, 1000 - 20 * ease((t - S3) / 1.0), op)
        s3b.draw(frame, W / 2, 1130 - 20 * ease((t - S3 - 0.5) / 1.0), window(t, S3 + 0.5, S4 - 0.1, 0.8, 0.5))

        # scène 4 : révélation du logo et des trois cuvées dans le cadre de l'étiquette
        if t >= S4:
            frac = round(ease_io((t - S4) / 1.6), 3)
            if frac not in filet_cache:
                filet_cache[frac] = double_filet(frac)
            filet_cache[frac].draw(frame, W / 2, H / 2)
            op = window(t, S4 + 1.2, DUR, 0.8, 0)
            small_left.draw(frame, 205, 146, 6 * math.sin(t * 2.6), op)
            small_right.draw(frame, 875, 146, -5 * math.sin(t * 2.3 + 1.0), op)
        logo.draw(frame, W / 2, 420 - 25 * ease((t - S4 - 0.4) / 1.4), window(t, S4 + 0.4, DUR, 1.4, 0))
        for k, b in enumerate(bottles):  # les trois cuvées montent l'une après l'autre
            start = S4 + 1.4 + 0.3 * k
            b.draw(frame, W / 2 + (k - 1) * 300, 1010 + 60 * (1 - ease((t - start) / 1.2)), window(t, start, DUR, 1.0, 0))
        sep.draw(frame, W / 2, 1365, window(t, S4 + 2.8, DUR, 0.6, 0))
        cta.draw(frame, W / 2, 1430 - 15 * ease((t - S4 - 3.0) / 1.0), window(t, S4 + 3.0, DUR, 0.8, 0))
        cta2.draw(frame, W / 2, 1500, window(t, S4 + 3.5, DUR, 0.8, 0))
        handle.draw(frame, W / 2, 1580, window(t, S4 + 4.0, DUR, 0.8, 0))

        legal1.draw(frame, W / 2, 1700)
        legal2.draw(frame, W / 2, 1738)

        fade = ease(t / 0.5) * (1 - ease((t - (DUR - 0.8)) / 0.8) if t > DUR - 0.8 else 1.0)
        out = (np.clip(frame * fade, 0, 1) * 255).astype(np.uint8)
        ff.stdin.write(out.tobytes())

        if i in previews:
            Image.fromarray(out).save(HERE / f"apercu-{t:04.1f}s.jpg", quality=88)

    ff.stdin.close()
    ff.wait()
    AUDIO.unlink()
    print("OK ->", OUT)


if __name__ == "__main__":
    main()
