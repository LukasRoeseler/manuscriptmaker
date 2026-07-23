# Author / Research-Assistant Guide

This guide takes one accepted manuscript from *“accepted”* to *“published in the
R2 design.”* No software needs to run on your machine — GitHub does the work.

> **Tip — instant preview.** Before submitting, drop your file into the
> [in-browser preview](preview/) to see it typeset in the R2 design immediately
> (`.docx`, Markdown/Quarto, and basic LaTeX). It runs entirely in your browser;
> the authoritative PDF/JATS/OJS galleys are still produced by the pipeline below.

## 1. Create the manuscript folder

1. On GitHub, click **Add file → Create new file** (or use the web editor).
2. Copy the folder `manuscripts/_TEMPLATE/` to `manuscripts/<article-id>/`,
   where `<article-id>` is the assigned id, e.g. `R2.2025.014`.

The folder should contain:

```
manuscripts/R2.2025.014/
  source/      ← put the accepted file here (.docx/.doc/.md/.rmd/.qmd/.tex/.zip)
  _metadata.yml ← publication fields (DOI, volume, type, discipline, badges…)
```

## 2. Add the manuscript file

Upload the accepted file into `source/`. Accepted inputs:

| Format | Notes |
|---|---|
| `.docx` / `.doc` | Citations are extracted **only** if they use live Zotero/Mendeley/Word field codes. Otherwise also add a `references.bib`. |
| `.qmd` / `.md` / `.rmd` | Used directly. R Markdown should be pre-rendered (`_freeze/`); CI does not run R/Python. |
| `.tex` | A single main LaTeX file. R2 macros (`\RtwoAbstract`, `\keywords`, `\recommendedcitation`) are detected. |
| `.zip` | An Overleaf project export containing the main `.tex`. |

## 3. Fill in `_metadata.yml`

Set `article-id` (must match the folder name), `doi`, `volume`, `year`,
`article-type`, `discipline`, the lay summary, the recommended citation, and
flip any earned open-science `badges` to `true`. These fields drive the title
page, the JATS, and the OJS package.

> Author names, affiliations, ORCIDs, abstract, and keywords come from the
> manuscript's front matter (or, for `.docx`, are filled into the generated
> `article.qmd` — check the TODO markers the bot points out).

## 4. Open a Pull Request

Commit on a new branch and open a PR. Within a few minutes the **R2 bot**
comments with a link to the workflow run's **Artifacts**, containing:

- 🌐 the built **HTML**, 📕 the **PDF**, 🗂️ the **JATS XML**, and 📦 the
  **OJS import package**.

(There's no live preview URL — download the HTML artifact and open it locally,
or use the [instant preview tool](preview/) for a quick look before submitting.)
Push more commits to rebuild. The PR is also where **typesetting / proofreading**
happens: reviewers download the HTML/PDF, comment inline on the PR, the RA
pushes fixes, the artifacts update.

## 5. Publish

When the PR is approved and merged into `main`:

- the article is deployed to `…/articles/<article-id>/`, and
- the **OJS native-import package** is produced as a build artifact.

An editor imports that package into OJS via **Tools → Import/Export → Native XML
Plugin**, creating the article with its PDF, HTML, and JATS galleys.

## Troubleshooting

| The bot says… | Do this |
|---|---|
| `Missing required field: …` | Fill that field in `_metadata.yml` (or the `.qmd` front matter). |
| `No bibliography detected` | Add `references.bib` to the manuscript folder, or fix the Word citations to use a reference manager. |
| `article.qmd uses a TODO skeleton` | Word metadata couldn't be auto-detected — open the generated `article.qmd` and replace the `TODO:` placeholders. |
| PDF looks wrong but HTML is fine | Check the build log artifact; LaTeX errors are reported there. |
