#!/usr/bin/env bash
# Ispisuje markdown tablicu veličina datoteka u <dist>/assets, neobrađeno i nakon gzipa,
# za sažetak joba u GitHub Actionsu. Datoteke su poredane od najveće.
# Upotreba: bundle-size.sh <dist-mapa>
set -euo pipefail

dist="${1:?Upotreba: bundle-size.sh <dist-mapa>}"

kib() {
  awk -v bytes="$1" 'BEGIN { printf "%.1f kB", bytes / 1024 }'
}

echo '### Veličina bundlea'
echo
echo '| Datoteka | Veličina | gzip |'
echo '| --- | ---: | ---: |'

total=0
total_gzip=0
while IFS=$'\t' read -r size file; do
  gzip_size=$(gzip -c "$file" | wc -c)
  total=$((total + size))
  total_gzip=$((total_gzip + gzip_size))
  echo "| \`$(basename "$file")\` | $(kib "$size") | $(kib "$gzip_size") |"
done < <(
  for file in "$dist"/assets/*; do
    printf '%d\t%s\n' "$(wc -c < "$file")" "$file"
  done | sort -rn
)

echo "| **Ukupno** | **$(kib "$total")** | **$(kib "$total_gzip")** |"
