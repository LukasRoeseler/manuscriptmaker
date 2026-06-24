"""Shared metadata loader for the R2 publishing pipeline.

Merges the three metadata sources that drive every output, in increasing
priority:

    1. themes/<theme>/theme.yml   (journal-wide defaults + OJS config)
    2. manuscripts/<id>/_metadata.yml   (editor-owned registry fields)
    3. manuscripts/<id>/article.qmd front matter   (authored fields)

and exposes a normalized view (authors with resolved affiliations) used by
validate_meta.py, enrich_jats.py and build_ojs.py.

Pure standard library + PyYAML — no Quarto round-trip needed.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_THEME = REPO_ROOT / "themes" / "r2" / "theme.yml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into ``base`` (override wins)."""
    out = dict(base)
    for key, val in (override or {}).items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def read_front_matter(qmd_path: Path) -> dict:
    """Extract the leading YAML front-matter block from a .qmd/.md file."""
    text = qmd_path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _resolve_authors(meta: dict) -> list[dict]:
    """Turn Quarto's author/affiliations schema into flat author dicts.

    Each returned author has: name, given, family, email, orcid,
    affiliations (list of names), corresponding (bool).
    """
    affil_by_id = {}
    for idx, aff in enumerate(meta.get("affiliations", []) or [], start=1):
        if isinstance(aff, dict):
            affil_by_id[aff.get("id")] = {"name": aff.get("name", ""), "number": idx}

    authors = []
    for a in meta.get("author", []) or []:
        if not isinstance(a, dict):
            continue
        name = a.get("name", {})
        if isinstance(name, dict):
            given, family = name.get("given", ""), name.get("family", "")
            literal = name.get("literal") or f"{given} {family}".strip()
        else:  # plain string name
            given, family, literal = "", str(name), str(name)
            parts = str(name).split()
            if len(parts) >= 2:
                given, family = " ".join(parts[:-1]), parts[-1]

        affs = []
        for ref in a.get("affiliations", []) or []:
            rid = ref.get("ref") if isinstance(ref, dict) else ref
            if rid in affil_by_id:
                affs.append(affil_by_id[rid])
            elif isinstance(ref, dict) and ref.get("name"):
                affs.append({"name": ref["name"], "number": len(affs) + 1})

        authors.append({
            "given": given,
            "family": family,
            "name": literal,
            "email": a.get("email", ""),
            "orcid": a.get("orcid", ""),
            "affiliations": affs,
            "corresponding": bool(a.get("corresponding", False)),
        })
    return authors


def load(manuscript_dir: str | os.PathLike, theme: Path | None = None) -> dict:
    """Load fully merged + normalized metadata for one manuscript folder."""
    mdir = Path(manuscript_dir).resolve()
    theme_path = Path(theme) if theme else DEFAULT_THEME

    theme_meta = yaml.safe_load(theme_path.read_text(encoding="utf-8")) or {}

    meta_file = mdir / "_metadata.yml"
    meta_meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}

    qmd = mdir / "article.qmd"
    fm = read_front_matter(qmd) if qmd.exists() else {}

    merged = _deep_merge(_deep_merge(theme_meta, meta_meta or {}), fm)
    merged["_authors"] = _resolve_authors(merged)
    merged["_dir"] = str(mdir)
    merged["_qmd"] = str(qmd)
    return merged


if __name__ == "__main__":  # quick manual inspection
    import json
    import sys
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    slim = {k: v for k, v in m.items() if not k.startswith("_")}
    print(json.dumps({"r2": slim.get("r2"), "authors": m["_authors"][:2]},
                     ensure_ascii=False, indent=2, default=str))
