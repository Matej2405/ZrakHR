#!/usr/bin/env bash
# Pretvara Vitestov coverage-summary.json u markdown tablicu za sažetak joba u GitHub Actionsu.
# Upotreba: coverage-summary.sh <coverage-summary.json>
set -euo pipefail

summary="${1:?Upotreba: coverage-summary.sh <coverage-summary.json>}"

echo '### Pokrivenost testovima'
echo
echo '| Metrika | Pokriveno | Ukupno | Postotak |'
echo '| --- | ---: | ---: | ---: |'
# Zagrade nisu nužne jer | veže najslabije, ali jasno pokazuju da se .total primjenjuje na sve četiri metrike
jq -r '.total
  | (["Linije", .lines], ["Naredbe", .statements], ["Grane", .branches], ["Funkcije", .functions])
  | "| \(.[0]) | \(.[1].covered) | \(.[1].total) | \(.[1].pct) % |"' "$summary"
