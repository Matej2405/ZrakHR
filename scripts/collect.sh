#!/usr/bin/env bash
# Prikupljanje podataka za ZrakHR: pokreće kolektore, sirove odgovore sprema u <podaci>/raw/,
# mjerenja i prognoze i u bazu <podaci>/zrakhr.db, a u <podaci>/logs/ dopisuje po jedan redak
# sažetka za svako pokretanje.
#
# Svaki sat ga pokreće GitHub Actions (.github/workflows/collect.yml), a radi i iz crona na
# bilo kojem računalu, npr. svaki sat u 20 minuta:
#   20 * * * *  cd /putanja/do/ZrakHR && scripts/collect.sh dhmz data
#
# Upotreba: scripts/collect.sh <dhmz|azo|forecasts|check> [mapa-podataka]
#   dhmz       tekući sat DHMZ-ovih mjerenja; feed sadrži samo tekući sat, pa ide svaki sat
#   azo        AZO-ova satna mjerenja kvalitete zraka od jučer do danas; portal čuva povijest
#   forecasts  Open-Meteo prognoze vremena i kvalitete zraka za gradove projekta
#   check      dnevna provjera: učitava arhivu raw/ u bazu i za jučer (UTC) upisuje u log po
#              jedan redak po izvoru s brojem sati i zapisa te satima koji nedostaju
# Izlazni kod je 0 ako je sve prikupljeno (za check: ako je jučer potpun), 1 ako izvor nije
# uspio i 2 za pogrešnu upotrebu.
set -euo pipefail

usage='Upotreba: scripts/collect.sh <dhmz|azo|forecasts|check> [mapa-podataka]'
what="${1:-}"
data_dir="${2:-data}"
month="$(date -u +%Y-%m)"
log="$data_dir/logs/collect-$month.log"

if [[ "$what" != dhmz && "$what" != azo && "$what" != forecasts && "$what" != check ]]; then
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

# Mjerenja s izvora (dhmz ili azo). AZO može djelomično uspjeti: tada ispisuje sažetak s brojem
# nedohvaćenih nizova, koji se upisuje u log, a izlazni kod ostaje 1.
collect_measurements() {
  local source="$1" output status=0
  output="$(python -m zrakhr collect --source "$source" --raw-dir "$data_dir/raw/$source/$month" \
    --db "$data_dir/zrakhr.db")" || status=$?
  if [[ -z "$output" ]]; then
    note "$source: prikupljanje nije uspjelo"
    return 1
  fi
  echo "$output"
  # Prvi redak ispisa naredbe collect je sažetak: zapisi, odbačene vrijednosti i novi zapisi u bazi
  note "${output%%$'\n'*}"
  return "$status"
}

collect_forecasts() {
  local city count=0 failed=0
  # Gradovi dolaze iz paketa (zrakhr.cities), da popis postoji samo na jednom mjestu
  while IFS= read -r city; do
    count=$((count + 1))
    if ! python -m zrakhr fetch --city "$city" --raw-dir "$data_dir/raw/open-meteo/$month" \
        --db "$data_dir/zrakhr.db"; then
      failed=$((failed + 1))
    fi
  done < <(python -c 'from zrakhr.cities import CITIES; print("\n".join(CITIES))')
  note "open-meteo: prognoze za gradove $count, neuspjelih $failed"
  [[ $count -gt 0 && $failed -eq 0 ]]
}

# Baza se dopunjuje iz cijele arhive, pa je potpuna i kad je prikupljanje radilo negdje drugdje
# (u GitHub Actionsu baza nakon pokretanja nestaje, a arhiva ostaje u grani data)
check() {
  local output status=0
  python -m zrakhr import --raw-dir "$data_dir/raw" --db "$data_dir/zrakhr.db" || status=$?
  output="$(python -m zrakhr check --db "$data_dir/zrakhr.db")" || status=$?
  if [[ -z "$output" ]]; then
    note "check: provjera nije uspjela"
    return 1
  fi
  while IFS= read -r line; do
    note "$line"
  done <<< "$output"
  return "$status"
}

case "$what" in
  dhmz | azo) collect_measurements "$what" ;;
  forecasts) collect_forecasts ;;
  check) check ;;
esac
