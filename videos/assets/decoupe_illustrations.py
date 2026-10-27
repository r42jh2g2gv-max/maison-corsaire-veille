"""Découpe les éléments de la planche d'illustrations de Noël (fond blanc) en PNG transparents.

Usage : python3 videos/assets/decoupe_illustrations.py planche.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).parent

# nom : (cadre x0, y0, x1, y1 dans la planche 1536x1024, point à l'intérieur de l'élément)
# taille du coeur opaque : assez grande pour garder les reflets des grelots, 0 pour les éléments fins
ELEMENTS = {
    "grelots-noeud": ((5, 10, 640, 440), (270, 300)),
    "etoile-filante": ((580, 15, 1275, 565), (700, 160), 0),
    "grelot-suspendu": ((1230, 0, 1536, 485), (1390, 380)),
    "coffre": ((0, 440, 785, 990), (380, 750)),
    "grelot": ((740, 555, 1125, 965), (930, 840)),
    "grelots-suspendus": ((1120, 490, 1536, 1000), (1400, 870)),
    "etoile": ((730, 300, 975, 570), (850, 435), 0),
}


def cut(planche, box, seed, core_size=41):
    crop = planche.crop(box)
    a = np.asarray(crop).astype(int)
    ink = (a.min(axis=2) < 232) | (a.max(axis=2) - a.min(axis=2) > 25)
    # on relie les petits morceaux proches (pièces, perles) avant de prendre l'élément
    joined = Image.fromarray((ink * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
    ImageDraw.floodfill(joined, (seed[0] - box[0], seed[1] - box[1]), 128)
    comp = np.asarray(joined) == 128
    # on bouche les trous (reflets blancs à l'intérieur)
    outside = Image.fromarray(np.where(comp, 255, 0).astype(np.uint8)).copy()  # copie : floodfill ne modifie pas une image partagée avec numpy
    w, h = outside.size
    for x in range(0, w, 4):
        for y in (0, h - 1):
            if outside.getpixel((x, y)) == 0:
                ImageDraw.floodfill(outside, (x, y), 64)
    for y in range(0, h, 4):
        for x in (0, w - 1):
            if outside.getpixel((x, y)) == 0:
                ImageDraw.floodfill(outside, (x, y), 64)
    filled = np.asarray(outside) != 64
    # on revient au contour réel (le MaxFilter l'a élargi), sans liseré blanc
    # coeur de l'élément : opaque (garde les reflets blancs des grelots)
    core = np.asarray(Image.fromarray(filled.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(core_size))) > 0 if core_size else np.zeros_like(filled)
    # près du bord : transparence selon la blancheur, pour ne pas garder le papier entre les aiguilles
    soft = np.clip((250 - a.min(axis=2)) / 70, 0, 1)
    soft = np.maximum(soft, np.clip((a.max(axis=2) - a.min(axis=2) - 15) / 40, 0, 1))
    alpha = np.where(core, 1.0, soft) * filled
    alpha = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))) / 255
    # on retire le blanc mélangé aux bords semi-transparents
    k = np.clip(alpha, 0.05, 1)[..., None]
    rgb = np.clip((a - (1 - k) * 255) / k, 0, 255)
    out = Image.fromarray(np.dstack([rgb, alpha[..., None] * 255]).astype(np.uint8), "RGBA")
    return out.crop(out.getbbox())


def main(path):
    planche = Image.open(path).convert("RGB")
    for name, (box, seed, *core) in ELEMENTS.items():
        img = cut(planche, box, seed, *core)
        img.save(HERE / f"noel-{name}.png", optimize=True)
        print(name, img.size)


if __name__ == "__main__":
    main(sys.argv[1])
