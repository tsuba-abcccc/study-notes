#!/bin/bash
# regenerate new/physics.tex from base/physics.tex and compile it
set -e
cd "$(dirname "$0")/.."
python3 tools/reformat.py base/physics.tex new/body.tex > new/report.txt
python3 tools/manual.py new/body.tex new/body2.tex
{ cat new/preamble.tex; printf '%s\n' '\begin{document}'; cat new/body2.tex; printf '%s\n' '\end{document}'; } > new/physics.tex
if [ "$1" != "nocompile" ]; then
  cd new
  latexmk -xelatex -interaction=nonstopmode -halt-on-error physics.tex > build.stdout 2>&1 || true
  grep -E '^Output written|^!' physics.log | head
  grep -A4 '^!' physics.log | head -40
fi
