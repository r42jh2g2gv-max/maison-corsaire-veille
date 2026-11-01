import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import corentin  # noqa: E402

PAGE_V1 = """
<html><head><title>Boutique X</title>
<meta name="description" content="Collection été"></head>
<body><h1>Nouveautés</h1><h2>Veste Marin</h2><p>Prix : 89,00 €</p></body></html>
"""
PAGE_V2 = """
<html><head><title>Boutique X</title>
<meta name="description" content="Soldes d'automne -30%"></head>
<body><h1>Nouveautés</h1><h2>Veste Marin</h2><h2>Pull Corsaire</h2>
<p>Prix : 62,30 €</p></body></html>
"""


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(corentin, "DB", tmp_path / "veille.db")
    config = tmp_path / "competitors.json"
    config.write_text(json.dumps([
        {"name": "Boutique X", "website": "https://x.example/"}
    ]), encoding="utf-8")
    monkeypatch.setattr(corentin, "CONFIG", config)


def test_missing_config(tmp_path, monkeypatch):
    monkeypatch.setattr(corentin, "DB", tmp_path / "veille.db")
    monkeypatch.setattr(corentin, "CONFIG", tmp_path / "absent.json")
    assert "competitors.json" in corentin.collect()


def test_extract():
    snap = corentin.extract(PAGE_V1)
    assert snap["title"] == "Boutique X"
    assert snap["description"] == "Collection été"
    assert "Veste Marin" in snap["headings"]
    assert snap["prices"] == ["89,00 €"]


def test_collect_detects_changes(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    first = corentin.collect(fetcher=lambda url: PAGE_V1)
    assert "première photo" in first

    same = corentin.collect(fetcher=lambda url: PAGE_V1)
    assert "aucun changement" in same

    changed = corentin.collect(fetcher=lambda url: PAGE_V2)
    assert "changement(s) enregistré(s)" in changed

    report = corentin.weekly_report()
    assert "## Boutique X" in report
    assert "[prix]" in report and "62,30 €" in report
    assert "[marketing]" in report and "Soldes" in report
    assert "Pull Corsaire" in report


def test_unreachable_site(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)

    def boom(url):
        raise ConnectionError("down")

    assert "inaccessible" in corentin.collect(fetcher=boom)
