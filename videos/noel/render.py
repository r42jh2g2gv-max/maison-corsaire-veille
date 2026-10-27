"""Vidéo d'annonce Maison Corsaire — arrivée pour Noël.

Respecte la charte graphique (version du 27/10/2026) : fonds bordeaux / vert forêt /
brun, cuivre dorure, ivoire, Playfair Display + Montserrat, aplats sans dégradé,
ni brillance, ni ombre portée, carte marine fine ton sur ton.

Format story 1080x1920, 18 s, 30 i/s.
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

W, H, FPS, DUR = 1080, 1920, 30, 18.0
NFRAMES = int(FPS * DUR)

# palette de la charte
IVOIRE = (247, 241, 231)
CUIVRE = (208, 132, 84)  # cuivre dorure, sur fonds foncés
BORDEAUX = (58, 11, 27)
VERT = (15, 58, 39)
BRUN = (79, 39, 17)

FONTS = ASSETS / "fonts"
PLAYFAIR = str(FONTS / "playfair-display-latin-400-normal.woff")
PLAYFAIR_IT = str(FONTS / "playfair-display-latin-400-italic.woff")
PLAYFAIR_BOLD = str(FONTS / "playfair-display-latin-700-normal.woff")
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


def solid(color):
    return np.broadcast_to(np.array(color, np.float32) / 255.0, (H, W, 3)).copy()


# --- carte marine -------------------------------------------------------------

def chart_image(w, h, color, seed=0, coast=True):
    """Carte marine très fine, ton sur ton : quadrillage, lignes de rhumb, côte."""
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
    if coast:
        # côte stylisée et courbes de profondeur
        base = crng.uniform(0.6, 0.8) * w * s
        for off in (0, 26, 52, 78):
            pts = []
            for y in range(-20, h * s + 40, 12):
                x = (base + off * s + 70 * s * math.sin(y / (180 * s) + seed)
                     + 30 * s * math.sin(y / (63 * s) + 2 * seed) + 12 * s * math.sin(y / (23 * s)))
                pts.append((x, y))
            d.line(pts, fill=line if off == 0 else faint, width=2 * s if off == 0 else s)
    return img.resize((w, h), Image.LANCZOS)


def reveal_mask(w, h):
    """Distance normalisée 0..1 pour faire apparaître la carte en diagonale."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return ((xx / w) * 0.4 + (1 - yy / h) * 0.6)[..., None]


# --- éléments de marque ----------------------------------------------------------

def logo_image(width):
    mask = Image.open(ASSETS / "logo-masque.png").convert("L")
    h = int(mask.height * width / mask.width)
    mask = mask.resize((width, h), Image.LANCZOS)
    img = Image.new("RGBA", mask.size, CUIVRE + (255,))
    img.putalpha(mask)
    return img


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


def cuvee_band(name, wind, color, seed):
    bw, bh = W, BAND_H
    img = Image.new("RGBA", (bw, bh), color + (255,))
    img.alpha_composite(chart_image(bw, bh, color, seed=seed, coast=False))
    d = ImageDraw.Draw(img)
    d.line([(60, 26), (bw - 60, 26)], fill=CUIVRE + (255,), width=3)
    d.line([(60, 36), (bw - 60, 36)], fill=CUIVRE + (255,), width=1)
    d.line([(60, bh - 26), (bw - 60, bh - 26)], fill=CUIVRE + (255,), width=3)
    d.line([(60, bh - 36), (bw - 60, bh - 36)], fill=CUIVRE + (255,), width=1)
    t = text_image(name, PLAYFAIR, 150, IVOIRE)
    img.alpha_composite(t, ((bw - t.width) // 2, bh // 2 - t.height // 2 - 50))
    c = text_image(wind, MONTSERRAT_SEMI, 34, CUIVRE, tracking=9)
    img.alpha_composite(c, ((bw - c.width) // 2, bh // 2 + 85))
    return Layer(img)


# --- route du navire --------------------------------------------------------------

def bezier(p0, p1, p2, p3, n=400):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


ROUTE = bezier(np.array([120, 1600.]), np.array([520, 1500.]), np.array([180, 700.]), np.array([860, 420.]))


def route_layer(frac):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    n = int(len(ROUTE) * frac)
    for k in range(0, n, 9):  # pointillés
        x, y = ROUTE[k]
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=CUIVRE + (255,))
    if frac >= 1:
        x, y = ROUTE[-1]
        d.line([(x - 26, y - 26), (x + 26, y + 26)], fill=CUIVRE + (255,), width=7)
        d.line([(x - 26, y + 26), (x + 26, y - 26)], fill=CUIVRE + (255,), width=7)
    return Layer(img)


# --- neige ---------------------------------------------------------------------------

N_SNOW = 140
snow = {
    "x": rng.uniform(0, W, N_SNOW),
    "y": rng.uniform(0, H, N_SNOW),
    "r": rng.uniform(1.5, 4.5, N_SNOW),
    "v": rng.uniform(40, 110, N_SNOW),
    "ph": rng.uniform(0, 2 * math.pi, N_SNOW),
}


def snow_layer(t, level):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x, y0, r, v, ph in zip(snow["x"], snow["y"], snow["r"], snow["v"], snow["ph"]):
        y = (y0 + v * t) % (H + 20) - 10
        xx = x + 18 * math.sin(t * 0.7 + ph)
        d.ellipse([xx - r, y - r, xx + r, y + r], fill=IVOIRE + (int(150 * level),))
    return Layer(img)


# --- musique (composée ici, libre de droits) ------------------------------------

def render_audio(path):
    sr = 44100
    n = int(sr * DUR)
    t = np.arange(n) / sr
    out = np.zeros(n)

    def note(freq, start, length, amp, kind="cloche"):
        i0 = int(start * sr)
        i1 = min(n, i0 + int(length * sr))
        if i0 >= n:
            return
        tt = t[: i1 - i0]
        if kind == "cloche":
            env = np.exp(-tt * 2.2) * np.minimum(1, tt * 300)
            w = (np.sin(2 * np.pi * freq * tt) + 0.3 * np.sin(2 * np.pi * freq * 2.76 * tt) * np.exp(-tt * 5)
                 + 0.15 * np.sin(2 * np.pi * freq * 5.4 * tt) * np.exp(-tt * 8))
        elif kind == "cordes":
            env = np.minimum(1, tt / 0.9) * np.minimum(1, (length - tt) / 0.9)
            vib = 1 + 0.003 * np.sin(2 * np.pi * 5 * tt)
            w = sum(np.sin(2 * np.pi * freq * k * vib * tt) / k ** 1.3 for k in range(1, 7))
        else:  # timbale grave sur les changements de scène
            env = np.exp(-tt * 3.5)
            w = np.sin(2 * np.pi * freq * tt * (1 + 0.5 * np.exp(-tt * 20)))
        out[i0:i1] += amp * env * w

    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    # ré mineur, ample : Dm - B♭ - F - C - Dm - B♭ - Gm - A
    chords = [[38, 50, 57, 62, 65], [34, 46, 53, 58, 62], [41, 48, 57, 60, 65], [36, 48, 55, 60, 64],
              [38, 50, 57, 62, 65], [34, 46, 53, 58, 62], [43, 50, 55, 58, 62], [33, 45, 52, 57, 61]]
    bar = 2.2
    for i, ch in enumerate(chords):
        for m in ch:
            note(hz(m), i * bar, bar + 0.8, 0.045, "cordes")
    # final sur ré majeur (picardie) pour la révélation
    for m in (38, 50, 57, 62, 66, 69):
        note(hz(m), 8 * bar, DUR - 8 * bar, 0.05, "cordes")
    # mélodie de clochettes
    melody = [(4.4, 74), (4.95, 72), (5.5, 69), (6.6, 70), (7.15, 69), (7.7, 65), (8.8, 67), (9.9, 69),
              (11.0, 74), (11.55, 77), (12.1, 76), (13.2, 74), (13.75, 73), (14.3, 74), (15.4, 78), (15.9, 81)]
    for start, m in melody:
        note(hz(m), start, 2.5, 0.10)
    for s in (0.0, 4.4, 9.5, 12.0):
        note(48, s, 2.0, 0.35, "timbale")

    # houle : bruit filtré modulé lentement
    noise = np.random.default_rng(1).normal(0, 1, n)
    sea = np.convolve(noise, np.ones(140) / 140, mode="same")
    out += 0.9 * sea * (0.5 + 0.5 * np.sin(2 * np.pi * t / 4.5)) * (0.4 + 0.6 * (t < 9.5))

    out *= np.minimum(1, t / 1.0) * np.minimum(1, (DUR - t) / 2.0)
    out = out / np.max(np.abs(out)) * 0.8
    stereo = np.stack([out, np.roll(out, 260)], axis=1)
    data = (stereo * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


# --- montage ---------------------------------------------------------------------

S1, S2, S3, S4 = 0.0, 4.4, 9.5, 12.0  # débuts de scène
BAND_H = 540  # trois bandeaux, en laissant le bas libre pour la mention légale


def main():
    render_audio(AUDIO)

    bordeaux = solid(BORDEAUX)
    chart = Layer(chart_image(W, H, BORDEAUX, seed=4))
    chart_reveal = reveal_mask(W, H)

    s1a = text_layer("Au bout du voyage,", PLAYFAIR_IT, 92, IVOIRE)
    s1b = text_layer("un trésor vous attend.", PLAYFAIR_IT, 92, IVOIRE)

    bands = [
        cuvee_band("Noroît", "VENT DU NORD-OUEST", BORDEAUX, 1),
        cuvee_band("Zéphyr", "VENT D'OUEST", VERT, 2),
        cuvee_band("Suroît", "VENT DU SUD-OUEST", BRUN, 3),
    ]

    s3a = text_layer("Trois vents.", PLAYFAIR_IT, 104, IVOIRE)
    s3b = text_layer("Une même Maison.", PLAYFAIR_IT, 104, IVOIRE)

    logo = Layer(logo_image(640))
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
    previews = {int(s * FPS) for s in (3.6, 7.6, 11.2, 16.5)}
    for i in range(NFRAMES):
        t = i / FPS
        frame = bordeaux.copy()

        # carte marine qui se dessine, puis reste en fond
        p = ease_io((t - 0.2) / 3.0)
        if p > 0:
            a = np.clip((p * 1.25 - chart_reveal) / 0.25, 0, 1) * chart.alpha
            frame *= 1 - a
            frame += chart.rgb * a

        # scène 1 : la route du navire jusqu'au trésor
        if t < S2 + 0.6:
            route_layer(ease_io((t - 0.8) / 2.6)).draw(frame, W / 2, H / 2, window(t, 0.8, S2 + 0.4, 0.3, 0.5))
        s1a.draw(frame, W / 2, 900 - 20 * ease((t - 1.2) / 1.2), window(t, 1.2, S2 - 0.1))
        s1b.draw(frame, W / 2, 1020 - 20 * ease((t - 2.0) / 1.2), window(t, 2.0, S2 - 0.1))

        # scène 2 : les trois cuvées, une par vent
        if S2 <= t < S3 + 0.1:
            for k, band in enumerate(bands):
                start = S2 + 0.35 * k
                side = -1 if k % 2 == 0 else 1
                x_in = side * W * (1 - ease((t - start) / 0.9))
                x_out = -side * W * ease_io((t - (S3 - 0.6) - 0.1 * k) / 0.6)
                band.draw(frame, W / 2 + x_in + x_out, BAND_H / 2 + k * BAND_H)

        # scène 3 : la devise
        s3a.draw(frame, W / 2, 900 - 20 * ease((t - S3) / 1.0), window(t, S3, S4 - 0.1, 0.8, 0.5))
        s3b.draw(frame, W / 2, 1030 - 20 * ease((t - S3 - 0.5) / 1.0), window(t, S3 + 0.5, S4 - 0.1, 0.8, 0.5))

        # scène 4 : révélation du logo dans le cadre de l'étiquette
        if t >= S4:
            frac = round(ease_io((t - S4) / 1.6), 3)
            if frac not in filet_cache:
                filet_cache[frac] = double_filet(frac)
            filet_cache[frac].draw(frame, W / 2, H / 2)
        logo.draw(frame, W / 2, 760 - 30 * ease((t - S4 - 0.4) / 1.4), window(t, S4 + 0.4, DUR, 1.4, 0))
        sep.draw(frame, W / 2, 1190, window(t, S4 + 1.4, DUR, 0.6, 0))
        cta.draw(frame, W / 2, 1270 - 15 * ease((t - S4 - 1.6) / 1.0), window(t, S4 + 1.6, DUR, 0.8, 0))
        cta2.draw(frame, W / 2, 1350, window(t, S4 + 2.2, DUR, 0.8, 0))
        handle.draw(frame, W / 2, 1460, window(t, S4 + 2.8, DUR, 0.8, 0))

        snow_layer(t, 0.5 + 0.5 * (t > S4) * ease((t - S4) / 1.0)).draw(frame, W / 2, H / 2)

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
