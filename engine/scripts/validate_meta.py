"""Validate a manuscript's metadata before rendering.

Fails fast (non-zero exit) with GitHub Actions error annotations so a PR
that is missing required publication fields is rejected with a clear
message instead of producing a broken galley.

Usage:
    python engine/scripts/validate_meta.py manuscripts/R2.2025.001
"""
from __future__ import annotations

import sys
from pathlib import Path

import r2meta

# (dotted-path, human label) — dotted path is resolved against merged meta.
REQUIRED = [
    ("title", "article title"),
    ("abstract", "abstract"),
    ("keywords", "keywords"),
    ("r2.volume", "r2.volume"),
    ("r2.year", "r2.year"),
    ("r2.article-id", "r2.article-id"),
    ("r2.article-type", "r2.article-type"),
    ("r2.discipline", "r2.discipline"),
    ("r2.journal", "r2.journal"),
]
RECOMMENDED = [
    ("r2.doi", "r2.doi (DOI)"),
    ("r2.lay-summary", "r2.lay-summary (plain-language summary)"),
    ("r2.recommended-citation", "r2.recommended-citation"),
]


def _get(meta: dict, dotted: str):
    cur = meta
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _annotate(level: str, msg: str, file: str | None = None) -> None:
    loc = f" file={file}" if file else ""
    print(f"::{level}{loc}::{msg}")


def main(manuscript_dir: str) -> int:
    mdir = Path(manuscript_dir)
    meta = r2meta.load(mdir)
    meta_file = str((mdir / "_metadata.yml"))
    errors = 0

    for dotted, label in REQUIRED:
        if not _get(meta, dotted):
            _annotate("error", f"Missing required field: {label}", meta_file)
            errors += 1

    authors = meta.get("_authors", [])
    if not authors:
        _annotate("error", "No authors found (front matter 'author:' is empty).", meta["_qmd"])
        errors += 1
    for i, a in enumerate(authors, 1):
        if not a["name"].strip():
            _annotate("error", f"Author #{i} has no name.", meta["_qmd"])
            errors += 1
    if authors and not any(a["email"] for a in authors):
        _annotate("warning", "No author has an email; OJS requires at least the "
                  "corresponding author's email for import.", meta["_qmd"])

    bib = meta.get("bibliography")
    if bib:
        bibs = [bib] if isinstance(bib, str) else bib
        for b in bibs:
            if not (mdir / b).exists():
                _annotate("error", f"bibliography file not found: {b}", meta["_qmd"])
                errors += 1

    for dotted, label in RECOMMENDED:
        if not _get(meta, dotted):
            _annotate("warning", f"Recommended field missing: {label}", meta_file)

    if errors:
        print(f"\nValidation FAILED with {errors} error(s).")
        return 1
    print("Validation passed.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_meta.py <manuscript-dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
