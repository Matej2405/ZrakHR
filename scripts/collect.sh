#!/usr/bin/env bash
# Prikupljanje podataka za ZrakHR: pokreće kolektore, sirove odgovore sprema u <podaci>/raw/,
# DHMZ-ova mjerenja i u bazu <podaci>/zrakhr.db, a u <podaci>/logs/ dopisuje po jedan redak
# sažetka za svako pokretanje.
#
# Svaki sat ga pokreće GitHub Actions (.github/workflows/collect.yml), a radi i iz crona na
# bilo kojem računalu, npr. svaki sat u 20 minuta:
#   20 * * * *  cd /putanja/do/ZrakHR && scripts/collect.sh dhmz data
#
# Upotreba: scripts/collect.sh <dhmz|forecasts> [mapa-podataka]
#   dhmz       tekući sat DHMZ-ovih mjerenja; feed sadrži samo tekući sat, pa ide svaki sat
#   forecasts  Open-Meteo prognoze vremena i kvalitete zraka za gradove projekta
# Izlazni kod je 0 ako je sve prikupljeno, 1 ako izvor nije uspio i 2 za pogrešnu upotrebu.
set -euo pipefail

usage='Upotreba: scripts/collect.sh <dhmz|forecasts> [mapa-podataka]'
what="${1:-}"
data_dir="${2:-data}"
month="$(date -u +%Y-%m)"
log="$data_dir/logs/collect-$month.log"

if [[ "$what" != dhmz && "$what" != forecasts ]]; then
  echo "$usage" >&2
  exit 2
fi
mkdir -p "$data_dir/logs"

# Lokalno i na serveru paket je u venvu; u GitHub Actionsu je instaliran bez venva
if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

# Jedan redak po pokretanju: u log, na izlaz i, u GitHub Actionsu, u sažetak joba
note() {
  local line
  line="$(date -u +%Y-%m-%dT%H:%M:%SZ) $*"
  echo "$line" | tee -a "$log"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    echo "- $line" >> "$GITHUB_STEP_SUMMARY"
  fi
}

collect_dhmz() {
  local output
  if ! output="$(python -m zrakhr collect --source dhmz --raw-dir "$data_dir/raw/dhmz/$month" \
      --db "$data_dir/zrakhr.db")"; then
    note "dhmz: prikupljanje nije uspjelo"
    return 1
  fi
  echo "$output"
  # Prvi redak ispisa naredbe collect je sažetak: postaje, zapisi i odbačene vrijednosti
  note "${output%%$'\n'*}"
}

collect_forecasts() {
  local city count=0 failed=0
  # Gradovi dolaze iz paketa (zrakhr.cities), da popis postoji samo na jednom mjestu
  while IFS= read -r city; do
    count=$((count + 1))
    if ! python -m zrakhr fetch --city "$city" --raw-dir "$data_dir/raw/open-meteo/$month"; then
      failed=$((failed + 1))
    fi
  done < <(python -c 'from zrakhr.cities import CITIES; print("\n".join(CITIES))')
  note "open-meteo: prognoze za gradove $count, neuspjelih $failed"
  [[ $count -gt 0 && $failed -eq 0 ]]
}

case "$what" in
  dhmz) collect_dhmz ;;
  forecasts) collect_forecasts ;;
esac
