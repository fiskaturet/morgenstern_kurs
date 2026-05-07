# Reklameforståelse — et krasjkurs fra Morgenstern

Et krasjkurs i reklameforståelse over 13 økter, bygget på Les Binet & Peter Field, Byron Sharp, Rory Sutherland og Robert Cialdini.

Utviklet av Anders Muurman Holm, kreativ leder i Morgenstern.

## Stack

Statisk HTML/CSS/JS. Ingen runtime-avhengigheter. MD-til-HTML rendres av en GitHub Action ved hver push.

```
kurs-innhold/      ← kilde (Markdown). Rediger her.
  dag-1.md … dag-13.md
  kurs-tekster.md  ← chrome-tekster (footer, login, navigasjon m.m.)

render_lessons.py  ← MD → HTML (kjøres av GitHub Action)
requirements.txt   ← pyyaml
.github/workflows/render.yml  ← CI-action

Resten ved repo-rot:
  dag-1.html … dag-13.html  ← generert (ikke rediger manuelt)
  index.html  oppslag.html  login.html  ← chrome-sider, redigeres direkte
  kalkulator-kjopsoyeblikk.html  ← drop-in modul
  styles.css  app.js  feedback.js
  og-image.jpg  assets/  ← bilder/fonter
  vercel.json
```

## Slik redigerer du innhold

### Kapittel-innhold (Økt 1–13)

Rediger `kurs-innhold/dag-N.md` direkte på github.com (blyant-ikon → commit).
GitHub Action rendrer ny HTML automatisk og committer tilbake innen ~30 sek.
Vercel deployer ny versjon innen ~30 sek etter det. **Total: ~1 minutt fra commit til live.**

`kurs-innhold/dag-N.html` skal aldri redigeres manuelt — endringene blir overskrevet ved neste render.

### Chrome-tekster (forsiden, oppslag, login, footer)

Rediger HTML-filene direkte (`index.html`, `oppslag.html`, `login.html`).
Vercel deployer ved push. Hold `kurs-innhold/kurs-tekster.md` synkronisert som referanse.

### Stil og kode

Rediger `styles.css`, `app.js`, `feedback.js` direkte. Pushes deployer.

## Lokal kjøring

For å rendre lokalt:

```bash
pip install -r requirements.txt
python render_lessons.py
```

Forhåndsvis i nettleseren:

```bash
python3 -m http.server 8000
# → http://localhost:8000
```

Lokal kjøring oppdaterer både MD-er (typo-rens) og HTML. I CI hopper rendreren over MD-skrivebackn (env `CI=true`) for å unngå commit-loop.

## Deploy

Vercel auto-deployer fra `main`-branchen. Ingen manuelle steg.

## Markdown-formatet

Hver `dag-N.md` har:

- **YAML-frontmatter** (day, part, duration, title, principle, primary_source, related, prev, next)
- **`## Lesning`** — brødtekst med `### h3`-underseksjoner
- **`::: anders-kommentar :::`** — egen blokk for Anders-kommentaren
- **`::: kalkulator-kjopsoyeblikk :::`** — drop-in kalkulator (Økt 2 og 7)
- **`## Kritikk av teori(en)`** — kritikk-paragrafer
- **`## Sjekkliste`** — punkter med `- [ ]`
- **`## Prøve`** — quiz-format (`### Q1.` + `- [ ]`/`- [x]` + `> forklaring`)

Rendreren håndterer norsk-typografi (em-dash, kursive ord, smarte sitattegn).
