# Nettside-tekster — alt utenfor dag-MD-ene

Dette dokumentet samler all tekst som ligger hardkodet i HTML/CSS/JS-filene og ikke i kapitler-MD-ene. Når du redigerer her, gi meg beskjed så synker jeg endringene til HTML-laget.

> **Begrepsbruk:** Vi bruker «økt» (ikke «dag») i all synlig kopi. Filnavn (dag-1.html etc.), CSS-klasser og JS-data-attributter beholdes for stabile lenker. Vi bruker «kunde» (ikke «kjøper») som substantiv. Verbet «kjøper» (i betydning «buys») la stå.

---

## Globalt (alle sider)

### Topbar (alle sider)
**Sitenavn:** Reklameforståelse — et krasjkurs fra Morgenstern
**Aria-label på logo-lenke:** Morgenstern — Reklameforståelse
**Logo alt-tekst:** Morgenstern

### Hovednavigasjon
- Forside
- Kurs
- Oppslag
- Om

### Site-footer
**Venstre:** Morgenstern · morgenstern.no
**Høyre:** Versjon 0.7 — utkast

### Side-tittel-mal i nettleseren
- Forsiden: «Reklameforståelse — et krasjkurs»
- Dagsider: «Økt N — [Tittel] · Reklameforståelse»
- Oppslag: «Oppslag · Reklameforståelse»

### Meta-beskrivelse (forsiden)
Et krasjkurs i reklameforståelse over 13 økter, bygget på Binet & Field, Byron Sharp, Rory Sutherland og Robert Cialdini.

---

## Forside (index.html)

### Hero
**Eyebrow:** 13 økter · 15 minutter per økt
**Tittel:** Et felles språk
for god reklame.
**Tagline:** Bygget på fire bøker mange referer til men færre har lest ferdig.

### CTA-knapper på hero
- Primær: Start med økt 1 →
- Sekundær: Se oppslagsverket
- Progresjonstekst (under knappene): 0 av 13 økter fullført

### Intro-seksjon (3 paragrafer + signatur)

**Para 1.** Dette er et krasjkurs for deg som lager, kjøper eller vurderer reklame. Her samler vi prinsippene fra Les Binet og Peter Field, Byron Sharp, Rory Sutherland og Robert Cialdini til ett felles rammeverk — slik at Morgenstjerner, kunder og byråer kan diskutere reklame med samme språk.

**Para 2.** Hver økt tar mindre enn 15 minutter: kort lesning, litt diskusjon og noen raske quiz-spørsmål. Du får også noen enkle sjekklister du kan bruke for å vurdere ideene dine opp mot prinsippene.

**Para 3.** Du trenger ikke å ha lest bøkene på forhånd (men jeg anbefaler å lese både Sutherland og Cialdini). Målet er at du om to uker har et tydelig rammeverk du kan bruke til å argumentere for gode ideer!

**Signatur.** — Anders Muurman Holm, kreativ leder i Morgenstern

### Kursoversikt-tittel
Kursets 13 økter

### Del-merkelapper og titler

**Del 1 · Fundamentet**
- Tittel: Hvorfor trenger vi teori?
- Bøker: Oppsett og premisser

**Del 2 · Les Binet & Peter Field**
- Tittel: Reklamens to hovedoppgaver
- Bøker: The Long and the Short of It

**Del 3 · Byron Sharp**
- Tittel: Hvordan merker faktisk vokser
- Bøker: How Brands Grow

**Del 4 · Rory Sutherland**
- Tittel: Psyko-logikk
- Bøker: Alchemy

**Del 5 · Robert Cialdini**
- Tittel: Overtalelse og innflytelse
- Bøker: Influence · Pre-Suasion

**Del 6 · Syntese**
- Tittel: Fra teori til dømmekraft
- Bøker: Alle fire bøker sett samlet

### Om-seksjon (på forsiden)

**Tittel:** Om kurset

**Para 1.** Kurset er utviklet av Anders Muurman Holm, kreativ leder i Morgenstern. Materialet bygger på Les Binet og Peter Fields *The Long and the Short of It*, Byron Sharps *How Brands Grow*, Rory Sutherlands *Alchemy*, og Robert Cialdinis *Influence*.

**Para 2.** Kurset er gratis og åpent. Progresjon lagres lokalt i nettleseren din, slik at du kan ta det i ditt eget tempo uten å opprette en konto.

---

## Dagsside-chrome (gjentas på alle dag-X.html)

### Topp av dagsside
**Tidsangivelse:** 15 minutter

### Day-marker (det store økt-nummer-elementet)
- Liten label: «Økt 1» / «Økt 2» / … / «Økt 13»
- Stor: «01» / «02» / … / «13»

### Principle-blokk
**Label:** Øktens prinsipp

### Anders-kommentar
**Label:** Anders' kommentar

### Sjekkliste
**Tittel:** Sjekkliste
**Badge:** for idévurdering

### Prøve
**Tittel:** Prøve
**Badge:** 4 spørsmål
**Intro:** Velg ett svar per spørsmål. Du får fasit og forklaring når du har svart på alle.

### Quiz-knapper
- Send inn: Rett prøven
- Reset: Ta om igjen

### Lesson-footer (navigasjon nederst)
- Venstre: ← Forrige
- Midten (knapp): Marker økten som fullført →
- Midten (når økten er fullført): Ferdig ✓ — gå til neste
- Høyre: Neste →
- Siste økt (økt 13), høyre: Tilbake → / Forsiden
- Marker kurset som fullført →

### Sidefelt
- Progresjons-label: Din progresjon
- Sidefelt-label: Primærkilde
- Sidefelt-label (relaterte): Beslektet

---

## Oppslag (oppslag.html)

### Tittel og intro
**Tittel:** Oppslagsverk

**Intro para 1.** En samlet ordliste over begrepene kurset bruker, med kort definisjon, primærkilde og lenke tilbake til økten der begrepet behandles i dybden.

### Termer (gjeldende skjelett)

**Mental tilgjengelighet** *(Økt 5 · Sharp)*
Sannsynligheten for at en merkevare dukker opp i hodet til en kunde i en kjøpssituasjon. Oftest den viktigste jobben reklame gjør — og en av de mest misforståtte. Bygges ved at merkevaren kobles til mange kategori-inngangsporter i hukommelsen.

**Kategori-inngangsport** *(Økt 5 · Sharp · Romaniuk)*
En situasjon, et behov eller et øyeblikk som får en kunde til å tenke på kategorien (f.eks. "tørst etter trening", "pizza på fredag"). Jo flere inngangsporter merkevaren er knyttet til, jo oftere blir den hentet fram. Ikke det samme som "vanligste brukssituasjon".

**Distinkte merkemarkører** *(Økt 6 · Sharp · Romaniuk)*
Visuelle og auditive elementer som er unikt knyttet til merkevaren (logo, farge, musikalsk signatur, typografi, karakterer) og som gjør den gjenkjennelig uten at navnet nevnes. Ikke det samme som differensiering — poenget er gjenkjenning, ikke overtalelse.

**Double Jeopardy** *(Økt 7 · Ehrenberg-Bass)*
Empirisk lovmessighet: små merker har både færre kunder og litt mindre lojale kunder enn store merker. Lojalitet følger størrelse, ikke omvendt. Implikasjon: vekst kommer fra flere kunder, ikke fra dypere lojalitet.

**60/40-regelen** *(Økt 3 · Binet & Field)*
Basert på IPA-databanken: optimal mediemix ligger i snitt rundt 60 % merkebygging og 40 % salgsaktivering, målt over tid. Rask aktivering alene bygger ikke merket; ren merkebygging uten aktivering konverterer ikke.

**Sosial validering** *(Økt 11 · Cialdini)*
Tendensen til å se etter hva andre gjør i usikre situasjoner — og kopiere — særlig når de andre ligner oss selv. Motoren bak kundetestimonialer, anmeldelsestall og bestselgermerking. Et av Cialdinis seks klassiske overtalelses-prinsipper.

**Signalverdi** *(Økt 9 · Sutherland · Spence)*
Ideen om at signaler må være kostbare for å bære mening. Noe som er gratis å produsere, er gratis å ignorere. Gjelder både merkevarer (dyr reklame = seriøst merke) og enkeltannonser (innsats = seriøs intensjon).

---

## App.js — dynamiske strenger (skrives av JS, ikke i HTML)

### Forsidens CTA (skiftes basert på progresjon)
- Ingen økter fullført: «Start med økt 1 →» (lenker til dag-1.html)
- Mellom: «Fortsett med økt N →» (lenker til dag-N.html)
- Alle økter fullført: «Åpne oppslagsverket →» (lenker til oppslag.html)

### Progresjonstekst på forsiden
«X av 13 økter fullført»

### Status på dagsoversikten
- Default: «15 min»
- Fullført: «ferdig»

### Marker-økten-knapp (når økten alt er fullført)
«Ferdig ✓ — gå til neste»

### Quiz-resultatboks (etter retting)
- Hovedlinje: «X av Y riktige (Z%)»
- Notat: «Les forklaringene nedenfor. Du kan ta prøven på nytt om du vil.»

### Quiz-feilmelding hvis ikke alle besvart
«Svar på alle X spørsmålene før du retter.»

### Quiz-svaretiketter (etter retting)
- Riktig svar: «✓ riktig»
- Feil svar: «ditt svar»

### Lokal-lagring
Lagringsnøkkel: `reklameforstaelse.v1`
(Lagrer fullførte økter, sjekkliste-kryss, og quiz-svar i nettleseren)

---

## Feedback-widget (feedback.js)

### Trigger-knapp (vises når tekst er markert)
«💬 Foreslå endring»

### Modal — header
- Tittel: «Foreslå endring»

### Modal — kropp
**Hint-tekst:** Du har markert dette stykket. Skriv en kort kommentar — f.eks. «dette skulle jeg gjerne fått bedre forklart», «typo her» eller «mistenker at kilden er feil». Forslaget sendes til Anders.

**Felter:**
- Din kommentar (påkrevd, tekstområde)
- Navn (valgfritt)
- E-post (valgfritt)

### Modal — knapper
- Avbryt
- Send forslag

### Bekreftelse etter send
- Suksess: «Takk! Forslaget er sendt til Anders.»
- Feil: «Klarte ikke å sende: [feilmelding]. Send heller en e-post til anders@mrgn.no.»

### Konfigurasjon
- Endepunkt: `https://formspree.io/f/xdabgyja` (sjekk feedback.js)

---

## Notater til Anders

- Tekst i HTML-filer er hardkodet og må synkes manuelt etter endringer her. Si fra når noe er klart for sync.
- Filnavn (`dag-1.html` osv.) beholdes med vilje — endring ville brutt alle interne lenker og bookmarks.
- «Dag» i CSS-klasser (`.day-marker`, `.lesson-day`) og JS-data-attributter (`data-day`) er internt — beholdes.
- Versjonsstreng i footer ("Versjon 0.7 — utkast") er typisk noe du vil bumpe når kurset blir publisert.
