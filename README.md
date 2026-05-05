# Reklameforståelse — et krasjkurs fra Morgenstern

Et krasjkurs i reklameforståelse over 13 økter, bygget på Les Binet & Peter Field, Byron Sharp, Rory Sutherland og Robert Cialdini.

Utviklet av Anders Muurman Holm, kreativ leder i Morgenstern.

## Stack

Statisk HTML/CSS/JS. Ingen build-steg, ingen avhengigheter.

- `index.html` — kursoversikt
- `dag-1.html` til `dag-13.html` — kapitlene (filnavn beholdes for stabile lenker; UI sier «økt»)
- `oppslag.html` — ordliste
- `styles.css` — Morgenstern-stil med Söhne, fargesignatur per del
- `app.js` — progresjon i localStorage, quiz, sjekklister
- `feedback.js` — feedback-widget for forslag fra leserne (Formspree)
- `assets/` — Söhne-fonter, Morgenstern-logo, illustrasjoner

## Lokal preview

Åpne `index.html` direkte i nettleseren. Eller start en lokal server:

```bash
python3 -m http.server 8000
```

Deretter `http://localhost:8000`.

## Deploy

Koblet til Vercel for automatisk deploy fra `main`-branch.
