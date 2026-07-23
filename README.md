# R2 Publishing Workflow

A **GitHub-hosted, single-source publishing pipeline** for the Diamond Open
Access journal *Replication Research (R2)* — and, via its theme system, for
any journal that wants the same workflow.

Drop an accepted manuscript into the repository, open a Pull Request, and
GitHub Actions automatically produces, in the journal's exact design:

- **HTML** — a self-contained web article (also usable as an OJS HTML galley)
- **PDF** — typeset to the R2 LaTeX design
- **JATS XML** — the archival, single-source publishing master
- **OJS native-import package** — metadata + all galleys, ready to import into
  [Open Journal Systems](https://pkp.sfu.ca/software/ojs/)

It covers the workflow from *“manuscript accepted”* to *“published in the final
journal design.”* Inspired by PhiMiSci's
[Magic Manuscript Maker](https://github.com/phimisci/mmm-web-app-os), re-built
for GitHub Pages + Actions so there is **no server to host or maintain**.

## How it works

```
 submit (.docx/.doc/.md/.rmd/.qmd/.tex/Overleaf .zip)
        │
        ▼  normalize.py  (Pandoc / LibreOffice)
 canonical source:  manuscripts/<id>/article.qmd + references.bib + figures/
        │
        ▼  quarto render   (one source → three outputs)
   ┌────────────┬────────────┬───────────────┐
   │  r2-html   │   r2-pdf   │    r2-jats     │
   │  (Quarto + │ (pdflatex+ │ (Pandoc JATS + │
   │   SCSS)    │ R2 .tex)   │  enrich_jats)  │
   └────────────┴────────────┴───────────────┘
        │
        ▼  build_ojs.py
   OJS native-import XML  (article + galleys, base64-embedded)
```

Everything that defines the **journal design** lives in a reusable Quarto
extension (`_extensions/r2/`) parameterized by a per-journal config
(`themes/<name>/theme.yml`). A new journal = a new theme folder; the engine is
untouched.

## Repository map

| Path | What it is |
|---|---|
| `_extensions/r2/` | The engine: PDF `template.tex`, HTML `r2.scss` + masthead partial, bundled fonts/badges/CSL. |
| `themes/r2/` | The journal's customization surface: `theme.yml` (colours, strings, OJS settings) + `assets/`. |
| `manuscripts/<id>/` | One article: `article.qmd` (authored), `_metadata.yml` (editor registry), `references.bib`, `figures/`, `source/` (original upload). |
| `engine/scripts/` | `normalize.py`, `validate_meta.py`, `enrich_jats.py`, `build_ojs.py`, `build_all.sh`, `r2meta.py`. |
| `engine/templates/` | `ojs_native.xml.j2` (OJS package template). |
| `.github/workflows/` | `build-manuscript.yml` (PR preview), `publish.yml` (on merge), `cleanup-preview.yml`. |
| `docs/` | GitHub Pages landing page, author guide, and theme customizer. |

## Quick start (local)

Requires [Quarto ≥ 1.5](https://quarto.org), a LaTeX engine (TinyTeX is fine),
and Python 3.10+ with `pyyaml` and `jinja2`.

```bash
pip install pyyaml jinja2
# Build the bundled sample end-to-end (skip PDF if you have no LaTeX):
NO_PDF=1 engine/scripts/build_all.sh manuscripts/R2.2025.001
# Or render a single format:
quarto render manuscripts/R2.2025.001/article.qmd --to r2-html
```

Outputs land next to the source: `article.html`, `article.pdf`, `article.xml`,
and `ojs/<id>_ojs_import.xml`.

## Submitting a manuscript (research assistants)

See **[docs/author-guide.md](docs/author-guide.md)**. In short: copy
`manuscripts/_TEMPLATE/` to `manuscripts/<article-id>/`, drop the accepted file
in `source/`, fill in `_metadata.yml`, and open a Pull Request. The bot replies
with a live preview and downloadable galleys.

## Adapting this to another journal

1. Copy `themes/r2/` to `themes/<your-journal>/` and edit `theme.yml`
   (accent colour, journal name, license, OJS section, …) and `assets/`
   (logo, license badge, open-science badges).
2. Point `_quarto.yml`'s `metadata-files:` at your `theme.yml`.
3. For a structurally different design, override `template.tex` / `r2.scss`
   in `themes/<your-journal>/overrides/`.

The conversion engine in `_extensions/r2/` does not change.
