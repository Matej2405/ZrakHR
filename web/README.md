# ZrakHR — web dashboard

Sučelje projekta ZrakHR: React 19, TypeScript i Vite. Prikazuje mjerne postaje, kretanje PM10,
PM2.5 i vremenskih uvjeta, analizu i stanje prikupljanja podataka. Profesor je dopustio TypeScript
za sučelje uz uvjet da skriptni dio projekta (Python, Bash) ostane središnji.

## Preduvjeti

- Node.js 24 (zapisano u `.nvmrc`; najmanje 22.22, što traži React Router 8)
- npm, koji dolazi s Node.js-om

Provjera: `node --version`.

## Pokretanje

Iz korijena repozitorija (iste naredbe rade u Bashu i PowerShellu):

```bash
cd web
npm ci
npm run dev
```

Razvojni poslužitelj ispisuje adresu (zadano http://localhost:5173) i osvježava stranicu pri
svakoj izmjeni koda.

## Naredbe

| Naredba                  | Što radi                                                          |
| ------------------------ | ----------------------------------------------------------------- |
| `npm run dev`            | razvojni poslužitelj s automatskim osvježavanjem                  |
| `npm run build`          | provjera tipova, lint i produkcijski build u `dist/`              |
| `npm run preview`        | lokalno poslužuje produkcijski build                              |
| `npm test`               | jednom pokreće testove (Vitest); `npm run test:watch` ih ponavlja |
| `npm test -- --coverage` | testovi uz izvještaj pokrivenosti u `coverage/`                   |
| `npm run typecheck`      | provjera tipova (`tsc -b`)                                        |
| `npm run lint`           | ESLint; ne prolazi ni uz jedno upozorenje                         |
| `npm run format`         | formatira kod Prettierom; `npm run format:check` samo provjerava  |

## CI i objava

Workflow `.github/workflows/web.yml` na svakom pull requestu koji mijenja `web/` pokreće četiri
paralelne provjere: Lint, Type check, Tests i Build. Pokrivenost testova i veličina bundlea
upisuju se u sažetak joba, a greške se prikazuju kao anotacije u diffu PR-a.

Nakon mergea u `main` isti build se objavljuje na GitHub Pages, na
https://matej2405.github.io/ZrakHR/, ali samo ako su sve četiri provjere prošle. Stranica se
poslužuje s putanje `/ZrakHR/`, pa CI gradi s `--base /ZrakHR/`. Isti build lokalno:

```bash
npx vite build --base /ZrakHR/
npx vite preview --base /ZrakHR/
```

## Struktura

```
web/
├── public/            statične datoteke (favicon)
└── src/
    ├── api/           klijent za REST API backenda
    ├── components/    dijelovi koje dijele stranice (okvir aplikacije, prekidač teme)
    ├── hooks/         React hookovi
    ├── pages/         po jedna komponenta za svaku rutu
    ├── styles/        dizajnerski tokeni i osnovni stilovi
    ├── test/          postavke testova
    ├── main.tsx       ulazna točka
    └── router.tsx     rute
```

Rute su `/` (pregled), `/karta`, `/analiza` i `/status`. Nepoznata adresa prikazuje stranicu
„Stranica ne postoji” unutar okvira aplikacije, pa navigacija ostaje dostupna.

Komponente se stiliziraju CSS modulima (`*.module.css`), a zajedničke vrijednosti su u
`src/styles/tokens.css`. Svaka boja definirana je jednom, funkcijom `light-dark()`, za svijetlu i
tamnu temu. Tema prati postavku sustava dok je korisnik ne promijeni prekidačem u zaglavlju.

## Odluke o alatima

- **TypeScript 6.0, a ne 7.** typescript-eslint, koji provjerava kod uz pomoć tipova, zasad
  podržava TypeScript manji od 6.1.
- **ESLint 10 s `eslint-plugin-jsx-a11y-x`.** ESLint 9 više nije podržan, a izvorni
  `eslint-plugin-jsx-a11y` još ne radi s ESLintom 10, pa se koristi fork zajednice es-tooling.
- **Strogi TypeScript:** `strict` i `noUncheckedIndexedAccess` u `tsconfig.app.json` te
  `strictTypeChecked` pravila typescript-eslinta.
- **Font Archivo** poslužuje se lokalno (Fontsource), bez zahtjeva prema Google Fontsu, i pokriva
  hrvatske znakove. Naslovi koriste njegovu os širine.
