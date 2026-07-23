# Put the accepted manuscript file in this folder

Drop ONE of the following here, then delete this placeholder file:

- `*.docx` or `*.doc` — Word (citations must use live Zotero/Mendeley field
  codes to be extracted automatically; otherwise add a `references.bib` to the
  manuscript folder)
- `*.qmd`, `*.md`, `*.rmd` — Markdown / Quarto / R Markdown
- `*.tex` — LaTeX (a single main file)
- `*.zip` — an Overleaf project export (must contain the main `.tex`)

The pipeline normalizes whatever you drop here into the canonical
`article.qmd` + `references.bib` + `figures/` and builds all galleys.
