"""Assemble an OJS native-XML import package for one article.

Reads the merged metadata + the three rendered galleys (PDF, HTML, JATS),
base64-embeds them, and renders engine/templates/ojs_native.xml.j2. The
result imports into OJS via Tools -> Import/Export -> Native XML Plugin and
creates the article in 'production' with all three galleys attached.

Usage:
    python engine/scripts/build_ojs.py manuscripts/R2.2025.001 [--out DIR]
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

import r2meta

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

# Galley definitions: (output filename suffix, OJS galley label, genre, mimetype)
GALLEY_SPECS = [
    ("article.pdf", "PDF", "Article Text", "application/pdf"),
    ("article.html", "HTML", "Article Text", "text/html"),
    ("article.xml", "JATS XML", "Article Text", "application/xml"),
]


def _b64(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii"), len(data)


def build(manuscript_dir: Path, out_dir: Path | None) -> Path:
    meta = r2meta.load(manuscript_dir)
    r2 = meta.get("r2", {})
    ojs = meta.get("ojs", {})
    authors = meta.get("_authors", [])

    fallback_email = next((a["email"] for a in authors if a["email"]),
                          f"noreply@{ojs.get('journal-path', 'journal')}.invalid")

    galleys = []
    for fid, (fname, label, genre, mime) in enumerate(GALLEY_SPECS, start=1):
        fpath = manuscript_dir / fname
        if not fpath.exists():
            print(f"  [skip] galley not found: {fname}")
            continue
        b64, size = _b64(fpath)
        ext = fname.rsplit(".", 1)[-1]
        galleys.append({
            "file_id": fid, "filename": f"{r2.get('article-id', 'article')}.{ext}",
            "label": label, "genre": genre, "mimetype": mime,
            "extension": ext, "filesize": size, "b64": b64,
        })

    if not galleys:
        raise SystemExit("No rendered galleys found — run quarto render first.")

    abstract = meta.get("abstract", "")
    if isinstance(abstract, str):
        abstract = " ".join(abstract.split())

    ctx = {
        "locale": (meta.get("lang") or "en").replace("-", "_"),
        "journal": r2.get("journal", ""),
        "title": meta.get("title", ""),
        "abstract": abstract,
        "keywords": meta.get("keywords", []) or [],
        "authors": authors,
        "doi": r2.get("doi", ""),
        "year": r2.get("year", ""),
        "date_published": str(meta.get("date", "")),
        "license_url": r2.get("license-url", ""),
        "section_ref": ojs.get("section-ref", "ART"),
        "user_group_ref": ojs.get("user-group-ref", "Author"),
        "uploader": ojs.get("uploader", "admin"),
        "fallback_email": fallback_email,
        "galleys": galleys,
    }

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["xml", "j2"]),
        trim_blocks=True, lstrip_blocks=True,
    )
    xml = env.get_template("ojs_native.xml.j2").render(**ctx)

    out_dir = out_dir or (manuscript_dir / "ojs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{r2.get('article-id', 'article')}_ojs_import.xml"
    out_path.write_text(xml, encoding="utf-8")
    print(f"OJS native import package: {out_path} "
          f"({len(galleys)} galley/-ies, {out_path.stat().st_size // 1024} KB)")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("manuscript_dir")
    ap.add_argument("--out", default=None, help="output directory")
    args = ap.parse_args()
    build(Path(args.manuscript_dir), Path(args.out) if args.out else None)
