# ZrakHR — arhiva prikupljenih podataka

Ova grana sadrži samo sirove podatke, bez koda. Puni je workflow **Collect** iz grane `main`
(`.github/workflows/collect.yml`), koji svaki sat pokreće `scripts/collect.sh`.

| Putanja | Sadržaj | Učestalost |
| --- | --- | --- |
| `raw/dhmz/<godina-mjesec>/dhmz_<vrijeme opažanja, UTC>.xml` | DHMZ-ov feed trenutnog vremena (https://vrijeme.hr/hrvatska_n.xml) | svaki sat |
| `raw/open-meteo/<godina-mjesec>/<izvor>_<grad>_<vrijeme dohvata, UTC>.json` | Open-Meteo prognoze vremena i kvalitete zraka (CAMS) za pet gradova projekta | svakih 6 sati |
| `logs/collect-<godina-mjesec>.log` | po jedan redak sažetka za svako pokretanje koje je spremilo podatke | uz svaki commit |

DHMZ objavljuje samo tekući sat, pa je ova arhiva jedini izvor povijesti vremenskih mjerenja.
Datoteke se ne mijenjaju naknadno; čišćenje, normalizacija i baza (SQLite) obrađuju ih iz arhive.

Lokalno se arhiva otvara u zasebnoj mapi, bez promjene trenutne grane:

```bash
git fetch origin data
git worktree add ../zrakhr-data data
```
