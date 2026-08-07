#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: build_twice.sh FILE.tex" >&2
  exit 2
fi

tex_path="$1"
tex_dir="$(CDPATH= cd -- "$(dirname -- "$tex_path")" && pwd)"
tex_name="$(basename -- "$tex_path")"
pdf_name="${tex_name%.tex}.pdf"

cd "$tex_dir"
xelatex -interaction=nonstopmode -halt-on-error "$tex_name" > build.log 2>&1
xelatex -interaction=nonstopmode -halt-on-error "$tex_name" >> build.log 2>&1
test -s "$pdf_name"
echo "build OK: $tex_dir/$pdf_name (xelatex 2회)"
