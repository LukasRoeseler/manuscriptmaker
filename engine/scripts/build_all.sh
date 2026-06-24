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
  quarto render "$MDIR/article.qmd" --to r2-pdf
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
