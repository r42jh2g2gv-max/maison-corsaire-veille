"""Logo personnalisé : envoi, icônes, en-tête, PDF, retour à l'ancre. Lancer depuis gestion/ : python tests/test_logo.py"""
import io
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="corsaire-test-")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image, ImageDraw  # noqa: E402

import app as _  # noqa: E402,F401
from noyau import app  # noqa: E402

c = app.test_client()
with c.session_transaction() as s:
    s["user_id"] = 1
    s["csrf"] = "t"

# Logo de test : rond doré sur fond transparent, format portrait (comme une photo)
img = Image.new("RGBA", (600, 800), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.ellipse([50, 150, 550, 650], fill=(224, 180, 90, 255))
d.rectangle([250, 300, 350, 500], fill=(15, 29, 51, 255))
buf = io.BytesIO()
img.save(buf, "PNG")
buf.seek(0)

origine = c.get("/icone/apple-touch-icon.png").data
assert c.get("/icone/logo.png").status_code == 404
r = c.post("/parametres/logo", data={"csrf": "t", "fond": "#ffffff", "logo": (buf, "logo.png")},
           content_type="multipart/form-data")
assert r.status_code == 302, r.status_code
for nom, taille in [("icone-192", 192), ("icone-512", 512), ("icone-maskable-512", 512),
                    ("apple-touch-icon", 180)]:
    r = c.get(f"/icone/{nom}.png")
    im = Image.open(io.BytesIO(r.data))
    assert im.size == (taille, taille), (nom, im.size)
    assert im.getpixel((2, 2))[:3] == (255, 255, 255), "fond blanc demandé"
assert c.get("/icone/apple-touch-icon.png").data != origine
assert c.get("/icone/logo.png").status_code == 200
html = c.get("/").get_data(as_text=True)
assert "/icone/logo.png" in html and "/icone/apple-touch-icon.png" in html
assert "/icone/icone-192.png" in c.get("/manifest.webmanifest").get_data(as_text=True)
# Les icônes sont accessibles sans connexion (iOS les télécharge sans cookie)
assert app.test_client().get("/icone/icone-192.png").status_code == 200
for url in ["/tickets/2/ticket.pdf", "/tickets/2/facture.pdf", "/bons/1.pdf"]:
    assert c.get(url).data[:4] == b"%PDF", url
sortie = os.environ.get("APERCU_LOGO")
if sortie:
    for url, nom in [("/tickets/2/ticket.pdf", "ticket"), ("/tickets/2/facture.pdf", "facture"),
                     ("/bons/1.pdf", "bon")]:
        open(os.path.join(sortie, f"logo-{nom}.pdf"), "wb").write(c.get(url).data)
    open(os.path.join(sortie, "logo-icone.png"), "wb").write(c.get("/icone/icone-512.png").data)
# Image illisible
r = c.post("/parametres/logo", data={"csrf": "t", "logo": (io.BytesIO(b"pas une image"), "x.png")},
           content_type="multipart/form-data", follow_redirects=True)
assert "Image illisible" in r.get_data(as_text=True)
# Retour à l'ancre
c.post("/parametres/logo/supprimer", data={"csrf": "t"})
assert c.get("/icone/apple-touch-icon.png").data == origine
assert "/icone/logo.png" not in c.get("/").get_data(as_text=True)
print("OK")
