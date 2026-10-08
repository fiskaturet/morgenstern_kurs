# Reklameforståelse — et krasjkurs fra Morgenstern

Et krasjkurs i reklameforståelse over 14 økter, bygget på Les Binet & Peter Field, Byron Sharp, Rory Sutherland og Robert Cialdini.

Utviklet av Anders Muurman Holm, kreativ leder i Morgenstern.

## Stack

Statisk HTML/CSS/JS. Ingen runtime-avhengigheter. Innholdet redigeres i Notion. En GitHub Action henter det, skriver Markdown og rendrer HTML.

```
kurs-innhold/      ← generert fra Notion (ikke rediger direkte)
  dag-1.md … dag-14.md
  kurs-tekster.md  ← chrome-tekster (footer, login, navigasjon m.m.)

notion_sync.py     ← Notion → MD (pull) / MD → Notion (import, engangs)
render_lessons.py  ← MD → HTML
requirements.txt   ← pyyaml
.github/workflows/notion-sync.yml  ← synk hvert kvarter + manuell knapp

Resten ved repo-rot:
  dag-1.html … dag-14.html  ← generert (ikke rediger manuelt)
  index.html  oppslag.html  login.html  ← chrome-sider, redigeres direkte
  kalkulator-kjopsoyeblikk.html  ← drop-in modul
  styles.css  app.js  feedback.js
  og-image.jpg  assets/  ← bilder/fonter
  vercel.json
```

## Slik redigerer du innhold

### Kapittel-innhold (Økt 1–14) — i Notion

Rediger i Notion: siden **«Reklameforståelse – kursinnhold»** → databasen **Økter**. Én side per økt.

- Bare sider med status **Publisert** går ut. Sett **Utkast** for å jobbe uten å publisere.
- Action-en *Synk fra Notion* kjører hvert kvarter, eller manuelt: *Actions → Synk fra Notion → Run workflow*. Den skriver `kurs-innhold/dag-N.md`, rendrer HTML og pusher. Vercel deployer.
- Forrige/neste-lenker regnes ut fra økt-nummer.
- `kurs-innhold/*.md` og `dag-N.html` overskrives ved synk — ikke rediger dem direkte.

Ny versjon av hele kurset: legg filene i `kurs-innhold/ny/` og push. Action-en erstatter da innholdet i Notion med filene, sletter mappa og rendrer siden på nytt.

Oppsett: repo-secret `NOTION_TOKEN` (Notion internal integration med tilgang til kursiden). Database-ID kan overstyres med repo-variabelen `NOTION_DATABASE_ID`.

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

Hver `dag-N.md` har (Notion-ekvivalent i parentes):

- **YAML-frontmatter** (database-feltene: Økt, Del, Varighet, Tittel, Prinsipp, Hovedkilde, Relatert)
- **`## Lesning`** — brødtekst med `### h3`-underseksjoner
- **`::: anders-kommentar :::`** — egen blokk for Anders-kommentaren (callout med 💬)
- **`::: kalkulator-kjopsoyeblikk :::`** og **`::: verktoy-… :::`** — interaktive verktøy (callout med 🧩 og filnavnet uten .html). Tilgjengelige: kalkulator-kjopsoyeblikk, verktoy-budsjett, verktoy-esov, verktoy-lemon, verktoy-markorer, verktoy-kjopere, verktoy-roi, verktoy-idevurdering
- **`## Kritikk av teori(en)`** — kritikk-paragrafer
- **`## Sjekkliste`** — punkter med `- [ ]` (to-do)
- **`## Prøve`** — quiz-format (`### Q1.` + `- [ ]`/`- [x]` + `> forklaring`; to-do huket = riktig svar, sitatblokk = forklaring)

Rendreren håndterer norsk-typografi (em-dash, kursive ord, smarte sitattegn).
