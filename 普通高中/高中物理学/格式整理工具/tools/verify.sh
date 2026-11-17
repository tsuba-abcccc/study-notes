#!/bin/bash
# build old & new bodies under the same layout and compare extracted text
cd "$(dirname "$0")/../verify"
rm -f old.out new.out old.aux new.aux
for f in ${1:-old new}; do
  ( latexmk -xelatex -interaction=nonstopmode -halt-on-error $f.tex > $f.stdout 2>&1
    grep -E '^Output written|^!' $f.log | head -3; grep -A4 '^!' $f.log | head -20
    python3 ../tools/extract.py $f.pdf $f.txt ) &
done
wait
