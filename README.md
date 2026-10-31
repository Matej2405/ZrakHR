# ZrakHR

Sustav koji periodički preuzima podatke o vremenu i kvaliteti zraka za hrvatske
gradove s [Open-Meteo](https://open-meteo.com/) API-ja, sprema ih u lokalnu bazu
i vizualizira na web dashboardu.

Semestralni projekt iz kolegija **Programiranje skriptnih jezika** (RITEH).

## Istraživačko pitanje

Kako vremenski uvjeti (temperatura, relativna vlažnost, tlak zraka, brzina vjetra
i oborine) utječu na koncentracije lebdećih čestica PM10 i PM2.5 u hrvatskim
gradovima?

Gradovi obuhvaćeni projektom: Zagreb, Rijeka, Split, Osijek i Slavonski Brod.

## Tim

- Matej Brodarac
- [Ime Prezime kolege]

## Tehnologije

Projekt koristi isključivo Python, JavaScript, Bash i PowerShell.

- **Python 3.10+** — kolektori, normalizacija, pohrana u SQLite, REST API i SSE
- **requests** — HTTP klijent za Open-Meteo API-je
- **SQLite** — lokalna baza normaliziranih mjerenja
- **JavaScript** — web dashboard
- **Bash / PowerShell** — skripte za pokretanje i periodičko izvršavanje
  (cron na Linuxu/macOS-u, Task Scheduler na Windowsima)
- **Izvori podataka** — Open-Meteo Weather Forecast API i Air Quality API
  (besplatni, bez API ključa)

## Planirana arhitektura

```
scheduler (cron / Task Scheduler)
    │
    ▼
kolektori (Open-Meteo vrijeme, Open-Meteo kvaliteta zraka) ──► data/raw/*.json
    │
    ▼
normalizacija → zapisi {source, location, metric, timestamp, value, unit}
    │
    ▼
SQLite
    │
    ▼
REST API + SSE
    │
    ▼
dashboard (web)
```

| Komponenta    | Opis                                                                     | Mapa                     |
| ------------- | ------------------------------------------------------------------------ | ------------------------ |
| Scheduler     | Periodički pokreće prikupljanje podataka za sve gradove                  | `scripts/`               |
| Kolektori     | Dohvaćaju sirove odgovore API-ja i čuvaju ih kao JSON                    | `src/zrakhr/collectors/` |
| Normalizacija | Pretvara odgovore različitih izvora u jedinstveni oblik zapisa           | `src/zrakhr/`            |
| SQLite        | Trajna pohrana normaliziranih zapisa                                     | `data/`                  |
| REST API, SSE | Upiti nad podacima i obavještavanje dashboarda o novim mjerenjima        | `api/`                   |
| Dashboard     | Grafovi vremenskih uvjeta i koncentracija PM10/PM2.5 po gradovima        | `web/`                   |

Testovi su u `tests/`, a dokumentacija u `docs/`.

## Plan po kontrolnim točkama

| KT  | Datum       | Cilj                                                                                      |
| --- | ----------- | ----------------------------------------------------------------------------------------- |
| KT1 | 1.11.2026.  | Struktura repozitorija, README, prototip kolektora za vrijeme i kvalitetu zraka s CLI-jem |
| KT2 | 27.11.2026. | SQLite shema i spremanje normaliziranih zapisa, periodičko prikupljanje za sve gradove    |
| KT3 | 18.12.2026. | REST API i SSE, prva verzija dashboarda                                                   |
| KT4 | 22.1.2027.  | Analiza utjecaja vremena na PM10/PM2.5, dovršen dashboard, testovi i dokumentacija        |

## Pokretanje

Potreban je Python 3.10 ili noviji (provjera: `python3 --version`).

macOS / Linux (Bash):

```bash
git clone https://github.com/Matej2405/ZrakHR.git
cd ZrakHR
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
git clone https://github.com/Matej2405/ZrakHR.git
cd ZrakHR
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Virtualno okruženje se isključuje naredbom `deactivate`.
