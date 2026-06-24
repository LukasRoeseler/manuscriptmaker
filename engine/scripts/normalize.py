"""Normalize a submitted manuscript into the canonical R2 source.

Input  : manuscripts/<id>/source/  containing ONE of
           *.qmd | *.md | *.rmd            (passthrough)
           *.docx | *.doc                  (Word, incl. Zotero/Mendeley cites)
           *.tex                           (LaTeX / Overleaf)
           *.zip                           (Overleaf project export)
Output : manuscripts/<id>/article.qmd  +  references.bib  +  figures/

The canonical → {HTML, PDF, JATS} path is identical for every input; only
this input → canonical step differs per format. Run it before `quarto render`.

Usage:
    python engine/scripts/normalize.py manuscripts/<id>
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PANDOC = ["quarto", "pandoc"]  # Pandoc shipped with Quarto; no separate install
SUPPORTED = {".qmd", ".md", ".rmd", ".docx", ".doc", ".tex", ".zip"}

FRONT_MATTER_SKELETON = """---
title: "TODO: article title"
author:
  - name: {{ given: TODO, family: TODO }}
    orcid: ""
    email: ""
    corresponding: true
    affiliations: [{{ ref: aff1 }}]
affiliations:
  - {{ id: aff1, name: "TODO: affiliation" }}
abstract: >
  TODO: abstract (paste here if it was not detected automatically).
keywords: [TODO]
bibliography: references.bib
---

{body}
"""


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def _candidates_in(search: Path) -> list[Path]:
    # Unzip an Overleaf export first, if present.
    for z in sorted(search.glob("*.zip")):
        print(f"  unzipping {z.name}")
        with zipfile.ZipFile(z) as zf:
            zf.extractall(search)
    return [p for p in search.rglob("*")
            if p.suffix.lower() in SUPPORTED - {".zip"} and p.is_file()]


def find_source(mdir: Path) -> Path:
    src_dir = mdir / "source"
    # Prefer a real upload in source/; fall back to a canonical article.qmd
    # already sitting in the manuscript folder (idempotent re-runs).
    candidates = _candidates_in(src_dir) if src_dir.is_dir() else []
    if not candidates:
        candidates = [p for p in mdir.glob("*")
                      if p.suffix.lower() in SUPPORTED - {".zip"} and p.is_file()]
    if not candidates:
        raise SystemExit(f"No supported source file found in {src_dir} or {mdir}")
    # Prefer an explicit main file; else the largest .tex/.docx/.md.
    for pref in ("main.tex", "manuscript.tex", "article.tex"):
        for c in candidates:
            if c.name.lower() == pref:
                return c
    # For LaTeX, pick the file that has \begin{document}; else largest.
    texs = [c for c in candidates if c.suffix.lower() == ".tex"]
    for t in texs:
        if "\\begin{document}" in t.read_text(encoding="utf-8", errors="ignore"):
            return t
    return max(candidates, key=lambda p: p.stat().st_size)


def passthrough(src: Path, mdir: Path) -> None:
    dst = mdir / "article.qmd"
    if src.resolve() != dst.resolve():
        shutil.copyfile(src, dst)
    print(f"  passthrough -> {dst.name}")


def from_docx(src: Path, mdir: Path) -> None:
    if src.suffix.lower() == ".doc":  # legacy .doc -> .docx via LibreOffice
        run(["soffice", "--headless", "--convert-to", "docx",
             "--outdir", str(src.parent), str(src)])
        src = src.with_suffix(".docx")

    body = mdir / "_body.md"
    # Run with cwd=mdir so --extract-media writes *relative* figure paths.
    run(PANDOC + [str(src), "-f", "docx+citations", "-t",
                  "markdown+yaml_metadata_block-raw_attribute",
                  "--extract-media=figures", "--wrap=none", "-o", "_body.md"],
        cwd=mdir)

    # Recover the reference-manager bibliography to BibTeX, if any.
    refs_json = mdir / "_refs.json"
    try:
        run(PANDOC + [str(src), "-f", "docx+citations", "-t", "csljson",
                      "-o", "_refs.json"], cwd=mdir)
        if refs_json.exists() and refs_json.read_text(encoding="utf-8").strip() not in ("", "[]"):
            run(PANDOC + ["_refs.json", "-f", "csljson", "-t", "bibtex",
                          "-o", "references.bib"], cwd=mdir)
        else:
            _warn_no_bib(mdir)
        refs_json.unlink(missing_ok=True)
    except subprocess.CalledProcessError:
        _warn_no_bib(mdir)

    _assemble_qmd(mdir, body.read_text(encoding="utf-8"))
    body.unlink(missing_ok=True)


def from_latex(src: Path, mdir: Path) -> None:
    text = src.read_text(encoding="utf-8", errors="ignore")
    extracted = _extract_r2_macros(text)

    # Copy any .bib alongside the source.
    bibs = list(src.parent.rglob("*.bib"))
    if bibs:
        shutil.copyfile(bibs[0], mdir / "references.bib")
        print(f"  bibliography: {bibs[0].name} -> references.bib")
    else:
        _warn_no_bib(mdir)

    body = mdir / "_body.md"
    run(PANDOC + [str(src), "-f", "latex", "-t", "markdown",
                  "--extract-media=figures", "--wrap=none", "-o", "_body.md"],
        cwd=mdir)
    _assemble_qmd(mdir, body.read_text(encoding="utf-8"), extracted)
    body.unlink(missing_ok=True)


def _extract_r2_macros(tex: str) -> dict:
    """Pull \\RtwoAbstract / \\keywords / \\recommendedcitation arguments."""
    out = {}
    for macro, key in (("RtwoAbstract", "abstract"),
                       ("keywords", "keywords"),
                       ("recommendedcitation", "recommended-citation")):
        m = re.search(r"\\" + macro + r"\{", tex)
        if not m:
            continue
        i, depth, start = m.end(), 1, m.end()
        while i < len(tex) and depth:
            if tex[i] == "{":
                depth += 1
            elif tex[i] == "}":
                depth -= 1
            i += 1
        out[key] = re.sub(r"\s+", " ", tex[start:i - 1]).strip()
    return out


def _assemble_qmd(mdir: Path, body: str, extracted: dict | None = None) -> None:
    """Write article.qmd, splitting any YAML pandoc produced from the body."""
    fm = ""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", body, re.DOTALL)
    if m:
        fm, body = m.group(1), m.group(2)

    extracted = extracted or {}
    if "abstract" in extracted and "abstract" not in fm:
        fm += f'\nabstract: >\n  {extracted["abstract"]}\n'
    if "keywords" in extracted and "keywords" not in fm:
        kws = ", ".join(k.strip() for k in re.split(r"[,;]", extracted["keywords"]))
        fm += f"\nkeywords: [{kws}]\n"

    if fm.strip():
        if "bibliography" not in fm:
            fm += "\nbibliography: references.bib\n"
        content = f"---\n{fm.strip()}\n---\n\n{body}"
    else:
        content = FRONT_MATTER_SKELETON.format(body=body)
        print("  NOTE: no metadata detected — article.qmd uses a TODO skeleton; "
              "fill it in (validation will fail until then).")
    (mdir / "article.qmd").write_text(content, encoding="utf-8")
    print("  wrote article.qmd")


def _warn_no_bib(mdir: Path) -> None:
    print("::warning::No bibliography detected. If the manuscript cites "
          "sources, add a references.bib (Word citations must use live "
          "Zotero/Mendeley field codes to be extracted automatically).")
    (mdir / "references.bib").touch(exist_ok=True)


def main(manuscript_dir: str) -> int:
    mdir = Path(manuscript_dir).resolve()
    src = find_source(mdir)
    print(f"Source: {src}  (.{src.suffix.lower().lstrip('.')})")
    ext = src.suffix.lower()
    (mdir / "figures").mkdir(exist_ok=True)

    if ext in {".qmd", ".md", ".rmd"}:
        passthrough(src, mdir)
    elif ext in {".docx", ".doc"}:
        from_docx(src, mdir)
    elif ext == ".tex":
        from_latex(src, mdir)
    else:
        raise SystemExit(f"Unsupported source type: {ext}")
    print("Normalization complete.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: normalize.py <manuscript-dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
