#!/usr/bin/env bash
# ---------------------------------------------------------------------
#  Build one manuscript end-to-end: normalize -> validate -> render
#  (HTML, PDF, JATS) -> enrich JATS -> assemble OJS import package.
#
#  Runs identically in GitHub Actions and on a research assistant's
#  machine (requires quarto, a LaTeX engine, python + pyyaml/jinja2).
#
#  Usage:  engine/scripts/build_all.sh manuscripts/R2.2025.001
#          NO_PDF=1 engine/scripts/build_all.sh <dir>   # skip PDF (no LaTeX)
# ---------------------------------------------------------------------
set -euo pipefail

MDIR="${1:?usage: build_all.sh <manuscript-dir>}"
MDIR="${MDIR%/}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "::group::Normalize"
python "$HERE/normalize.py" "$MDIR"
echo "::endgroup::"

echo "::group::Validate metadata"
python "$HERE/validate_meta.py" "$MDIR"
echo "::endgroup::"

echo "::group::Render HTML"
quarto render "$MDIR/article.qmd" --to r2-html
echo "::endgroup::"

if [[ "${NO_PDF:-0}" != "1" ]]; then
  echo "::group::Render PDF"
  # Let Quarto lower article.qmd -> article.tex (keep-tex is set in the
  # extension, so the .tex survives even if Quarto's own PDF-compile attempt
  # fails). We then compile it ourselves with the standard biblatex+biber
  # sequence: Quarto's automatic multi-pass PDF loop does not reliably
  # invoke biber for this template — it can misread the missing article.bbl
  # on the first pass as a missing *package* to tlmgr-install, fail, and
  # abort before biber ever runs. Running the passes explicitly sidesteps
  # that and matches exactly how a human would compile this document.
  quarto render "$MDIR/article.qmd" --to r2-pdf || true
  if [[ ! -f "$MDIR/article.tex" ]]; then
    echo "::error::Quarto did not produce $MDIR/article.tex — cannot compile the PDF."
    exit 1
  fi
  # Quarto resolves TinyTeX's pdflatex/biber internally without exporting
  # their directory to PATH, so a direct `pdflatex`/`biber` call here fails
  # with "command not found" even though Quarto's own render just used them
  # successfully. Locate TinyTeX's bin dir (platform-triplet subfolder of
  # ~/.TinyTeX/bin, e.g. x86_64-linux) and prepend it ourselves.
  TINYTEX_BIN="$(find "$HOME/.TinyTeX/bin" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)"
  if [[ -n "$TINYTEX_BIN" ]]; then
    export PATH="$TINYTEX_BIN:$PATH"
  elif ! command -v pdflatex >/dev/null 2>&1; then
    echo "::error::Could not find pdflatex (looked in \$HOME/.TinyTeX/bin/*; not on PATH either)."
    exit 1
  fi
  (
    cd "$MDIR"
    pdflatex -interaction=nonstopmode -halt-on-error article.tex
    biber article
    pdflatex -interaction=nonstopmode -halt-on-error article.tex
    pdflatex -interaction=nonstopmode -halt-on-error article.tex
  )
  echo "::endgroup::"
else
  echo "NO_PDF=1 set — skipping PDF render."
fi

echo "::group::Render JATS"
quarto render "$MDIR/article.qmd" --to r2-jats
python "$HERE/enrich_jats.py" "$MDIR/article.xml" "$MDIR"
echo "::endgroup::"

echo "::group::OJS native import package"
python "$HERE/build_ojs.py" "$MDIR"
echo "::endgroup::"

echo "Done: $MDIR"
ls -la "$MDIR"/article.* "$MDIR"/ojs/*.xml 2>/dev/null || true
