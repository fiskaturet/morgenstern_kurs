#!/usr/bin/env python3
"""
Reklameforståelse — renderer fra dag-N.md til dag-N.html.

Gjør følgende:
1) Leser hver MD-fil
2) Anvender globale tekst-endringer (dager→økter, 30→15 min, kjøper→kunde der det er substantiv)
3) Skriver oppdatert MD tilbake (ren kilde av sannhet)
4) Rendrer HTML i Morgenstern-malen som matcher eksisterende design
5) Stiletypografi-fix: «smarte» quotes, em-dash etc.

Ikke en generell markdown-parser — håndterer formatet vi faktisk bruker.
"""
import re
import os
import yaml
import html as html_module
from pathlib import Path

# Paths relative to this script's location — fungerer både lokalt og i CI
ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'kurs-innhold'
DST = ROOT

# I CI: ikke skriv tilbake til MD-er. Hindrer auto-commit-loop.
WRITE_MD_BACK = os.environ.get('CI', '').lower() != 'true'

# ----------------------------------------------------------------------
# Globale endringer (anvendes på MD-prosa, ikke YAML/struktur)
# ----------------------------------------------------------------------

# Mapping fra ordinaler → tall (for «Dag én» → «Økt 1»)
ORDINAL_TO_NUM = {
    'én': '1', 'en': '1', 'to': '2', 'tre': '3', 'fire': '4', 'fem': '5',
    'seks': '6', 'sju': '7', 'syv': '7', 'åtte': '8', 'ni': '9', 'ti': '10',
    'elleve': '11', 'tolv': '12', 'tretten': '13'
}

# Steder der "kjøper" er verb, ikke substantiv — disse skal IKKE byttes til «kunde»
# Vi identifiserer dem ved at neste meningsbærende ord ikke er en avslutter (komma, punktum, slutt-tag)
# I praksis: jobb manuelt med en liste over kjente verb-fraser
VERB_KJOPER_PATTERNS = [
    r'\bsom kjøper\b',           # "folk som kjøper"
    r'\bkjøper og måler\b',      # "lager, kjøper og måler"
    r'\bkjøper fra\b',           # "du kjøper fra"
    r'\bkjøper osten\b',         # "kjøper osten"
    r'\bkjøper sjelden(t)?\b',   # "kjøper sjelden"
    r'\bkjøper merket\b',        # "kjøper merket"
    r'\bkjøper én gang\b',
    r'\bkjøper veldig ofte\b',
    r'\bkjøper litt sjeldnere\b',
    r'\bkjøper oss\b',
    r'\bkjøper vi\b',
    r'\bkjøper du\b',
    r'\bkjøper en bil\b',
    r'\bkjøper i\b',
    r'\bkjøper noen\b',
    r'\bkjøper det\b',
    r'\bkjøper oftere\b',
    r'\bkjøper bedre\b',
]


def apply_text_changes(text: str, *, is_md_prose: bool = True) -> str:
    """Anvend globale tekst-endringer på prosa. Ikke på YAML/HTML-tags."""
    s = text

    # 1) "30 minutter" → "15 minutter"
    s = re.sub(r'\b30 minutter\b', '15 minutter', s)
    s = re.sub(r'\b30 min\b', '15 min', s)

    # 2) Dag/dager → Økt/økter — kontekstbasert
    # Vern verb-fraser kjøper/dager først? Faktisk, dager-ordet er mindre tvetydig,
    # men "i dag" (today) skal stå.

    # "i dag" som idiomatisk uttrykk: la stå når brukt om "today" / "samtid"
    # "I dag handler det om" → "I denne økten handler det om" (lesson-specific)
    s = re.sub(r'\bI dag handler det om\b', 'I denne økten handler det om', s)

    # "den siste dagen" → "den siste økten"
    s = re.sub(r'\bden siste dagen\b', 'den siste økten', s)

    # "denne dagen" → "denne økten"
    s = re.sub(r'\bdenne dagen\b', 'denne økten', s)

    # "Vi har vært gjennom 12 dager med teori" → "Vi har vært gjennom 12 økter med teori"
    s = re.sub(r'\b(\d+) dager med teori\b', r'\1 økter med teori', s)

    # "13-dagers krasjkurs" → "krasjkurs over 13 økter"
    s = re.sub(r'\b13-dagers krasjkurs\b', 'krasjkurs over 13 økter', s)

    # "Marker dagen som fullført" → "Marker økten som fullført" (lesson-footer button)
    s = re.sub(r'\bMarker dagen som fullført\b', 'Marker økten som fullført', s)
    s = re.sub(r'\bgå til neste dag\b', 'gå til neste økt', s)

    # "X dager fullført" → "X økter fullført" (counter)
    s = re.sub(r'\b(\d+) dager fullført\b', r'\1 økter fullført', s)

    # "Kursets 13 dager" → "Kursets 13 økter"
    s = re.sub(r'\bKursets (\d+) dager\b', r'Kursets \1 økter', s)

    # "13 dager · 30 minutter om dagen" → "13 økter · 15 minutter per økt"
    # 30 minutter er allerede byttet over; nå dropper vi "om dagen" → "per økt"
    s = re.sub(r'(\d+ minutter) om dagen', r'\1 per økt', s)

    # "13 dager" som standalone teller
    s = re.sub(r'\b(\d+) dager\b(?!\s+(siden|gjennom|med teori))',
               r'\1 økter', s)

    # "Dag N" → "Økt N" (tall etter)
    s = re.sub(r'\bDag (\d+)\b', r'Økt \1', s)
    s = re.sub(r'\bdag (\d+)\b(?!-)', r'økt \1', s)  # ikke dag-1.html
    # «Les dag 5 →» → «Les økt 5 →» — dekkes av regelen over

    # "Dag én" / "Dag to" / ... → "Økt 1" / "Økt 2" / ...
    for word, num in ORDINAL_TO_NUM.items():
        s = re.sub(rf'\bDag {word}\b', f'Økt {num}', s, flags=re.IGNORECASE)

    # "i dag" (today, idiomatic) er ikke endret — la stå
    # "dager med teori"/"dager med X" — case-by-case dekket over

    # 3) "kjøper(en|ne|e)" som substantiv → "kunde(n|ne)/kunder"
    # Strategi: finn alle verb-instanser først og marker dem unrørbart, så bytt resten
    placeholder_map = {}
    for i, pat in enumerate(VERB_KJOPER_PATTERNS):
        for match in re.finditer(pat, s):
            placeholder = f'__VERB_KJOP_{i}_{match.start()}__'
            placeholder_map[placeholder] = match.group(0)

    # Erstatt verb-instanser med placeholders først (i omvendt rekkefølge)
    for placeholder, original in placeholder_map.items():
        s = s.replace(original, placeholder, 1)

    # Nå er det «trygt» å bytte resterende «kjøper»-substantiv
    # kjøperen → kunden
    s = re.sub(r'\bkjøperen\b', 'kunden', s)
    # kjøperne → kundene
    s = re.sub(r'\bkjøperne\b', 'kundene', s)
    # kjøpere → kunder
    s = re.sub(r'\bkjøpere\b', 'kunder', s)
    # kjøper (substantiv, sjelden, gjenværende) → kunde
    s = re.sub(r'\b(en sjelden) kjøper\b', r'\1 kunde', s)

    # Sett tilbake placeholders
    for placeholder, original in placeholder_map.items():
        s = s.replace(placeholder, original)

    return s


# ----------------------------------------------------------------------
# YAML frontmatter parser (simple)
# ----------------------------------------------------------------------
def parse_frontmatter(text: str):
    """Returner (frontmatter_dict, body_text)."""
    if not text.startswith('---'):
        return {}, text
    end = text.find('\n---', 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    body = text[end + 4:].lstrip('\n')

    # YAML-fix: enkelte filer har «smart-quotes» som bryter parsing
    fm_raw_fixed = fm_raw.replace('»', '"').replace('«', '"')
    # Også enkeltquotes som ikke matcher
    try:
        fm = yaml.safe_load(fm_raw_fixed)
    except yaml.YAMLError as e:
        print(f"YAML feil: {e}")
        # Best effort line-by-line
        fm = {}
        for line in fm_raw_fixed.splitlines():
            if ':' in line and not line.startswith(' '):
                k, _, v = line.partition(':')
                fm[k.strip()] = v.strip().strip('"').strip("'")

    return fm or {}, body


# ----------------------------------------------------------------------
# Inline markdown → HTML
# ----------------------------------------------------------------------
def inline_md(s: str) -> str:
    """*kursiv*, **fet**, [link](url) → HTML, &-escape resten."""
    # Escape HTML først
    s = html_module.escape(s, quote=False)

    # **fet**
    s = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', s)
    # *kursiv*
    s = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<em>\1</em>', s)

    # [tekst](url)
    s = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', s)

    # Em-dash «—»: la stå (allerede tegn)
    return s


# ----------------------------------------------------------------------
# Block-renderer (vår spesielle subset)
# ----------------------------------------------------------------------
def render_section_blocks(body: str, day_part: int) -> dict:
    """
    Del kropp i seksjoner basert på `## Lesning`, `## Kritikk av teori(en)`,
    `## Sjekkliste...`, `## Prøve`, `## Det du tar...`, `## Avslutning`.
    Returner dict med pre-rendrede HTML-blokker.
    """
    sections = {
        'reading_html': '',
        'critique_html': '',
        'checklist_items': [],
        'checklist_intro': '',
        'quiz_intro': '',
        'quiz_items': [],
        'extra_html': '',  # for «Det du tar med deg videre» og «Avslutning» (kun dag 13)
    }

    # Splitt på h2 (## )
    parts = re.split(r'\n(?=## )', body)
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith('## Lesning'):
            sections['reading_html'] = render_reading(part[len('## Lesning'):])
        elif part.startswith('## Kritikk av teori'):
            # tittel kan være «Kritikk av teori» eller «Kritikk av teorien»
            head_end = part.find('\n')
            sections['critique_html'] = render_critique(part[head_end:])
        elif part.startswith('## Sjekkliste'):
            sections['checklist_intro'], sections['checklist_items'] = render_checklist(part)
        elif part.startswith('## Prøve'):
            sections['quiz_intro'], sections['quiz_items'] = render_quiz(part)
        elif part.startswith('## Det du tar med deg videre') or part.startswith('## Avslutning'):
            sections['extra_html'] += render_extra(part)
        else:
            # Noe vi ikke kjenner — slipp gjennom som plain
            pass

    return sections


YT_PATTERNS = [
    re.compile(r'^https?://(?:www\.)?youtube\.com/watch\?[^\s]*?v=([A-Za-z0-9_-]{6,})[^\s]*$'),
    re.compile(r'^https?://youtu\.be/([A-Za-z0-9_-]{6,})(?:\?[^\s]*)?$'),
    re.compile(r'^https?://(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{6,})(?:\?[^\s]*)?$'),
]


def parse_youtube_url(line: str):
    """Returner video-ID hvis linja er en bar YouTube-URL, ellers None."""
    line = line.strip()
    for pat in YT_PATTERNS:
        m = pat.match(line)
        if m:
            return m.group(1)
    return None


def render_video_embed(video_id: str, caption: str = '') -> str:
    """Bygg responsiv iframe + valgfri figcaption."""
    src = f'https://www.youtube-nocookie.com/embed/{video_id}'
    parts = ['      <figure class="video-embed">']
    parts.append(
        f'        <div class="video-frame">'
        f'<iframe src="{src}" title="Video" '
        f'allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
        f'allowfullscreen loading="lazy"></iframe></div>'
    )
    if caption:
        parts.append(f'        <figcaption>{inline_md(caption)}</figcaption>')
    parts.append('      </figure>')
    return '\n'.join(parts)


def render_paragraphs_with_specials(body: str) -> str:
    """
    Render markdown body med:
    - paragrafer
    - h3 (### )
    - ::: anders-kommentar :::-blokker
    - inline-kursiv/fet/lenker

    Kommentarer (CALUDE: ..., (Embed ..., (SETT INN ...) på egen linje) sløyfes som author-notes.
    """
    out = []
    lines = body.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Tom linje
        if not stripped:
            i += 1
            continue

        # Forfatter-notat (parentes-kommentarer og CALUDE/SETT INN-instruksjoner) — droppes
        if (stripped.startswith('(CLAUDE:') or
            stripped.startswith('(CALUDE:') or
            stripped.startswith('(SETT INN') or
            stripped.startswith('(Embed') or
            stripped.startswith('(SETT_INN')):
            # Skip til en lukkeparentes eller tom linje
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].strip().endswith(')'):
                i += 1
            if i < len(lines):
                i += 1  # spis avslutningen
            continue

        # YouTube-URL alene på en linje → video-embed
        # Hvis linja rett under er en kursiv-paragraf (*..*), brukes den som figcaption.
        yt_id = parse_youtube_url(stripped)
        if yt_id:
            caption = ''
            # Sjekk neste ikke-tomme linje
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                nxt = lines[j].strip()
                m_cap = re.match(r'^\*([^\*].*?)\*$', nxt)
                if m_cap:
                    caption = m_cap.group(1).strip()
                    i = j  # hopp forbi caption-linja
            out.append(render_video_embed(yt_id, caption))
            i += 1
            continue

        # h3
        if stripped.startswith('### '):
            out.append(f'      <h3>{inline_md(stripped[4:])}</h3>')
            i += 1
            continue

        # ::: kalkulator-kjopsoyeblikk :::
        if stripped.startswith('::: kalkulator-kjopsoyeblikk'):
            # Spis evt. avsluttende ::: hvis den finnes på neste/samme linje
            if not stripped.endswith(':::'):
                i += 1
                while i < len(lines) and lines[i].strip() != ':::':
                    i += 1
            i += 1
            out.append(KALKULATOR_HTML)
            continue

        # ::: anders-kommentar :::
        if stripped.startswith('::: anders-kommentar') or stripped == ':::' and False:
            # Samle innhold til avsluttende ":::"
            inner_lines = []
            i += 1
            while i < len(lines):
                ln = lines[i]
                # Avsluttende :::
                if ln.strip() == ':::' or ln.rstrip().endswith(':::'):
                    # Strip trailing :::
                    last = ln.rstrip()
                    if last.endswith(':::') and last != ':::':
                        inner_lines.append(last[:-3].rstrip())
                    i += 1
                    break
                inner_lines.append(ln)
                i += 1

            # Render innholdet som paragrafer
            inner_html = render_inner_paragraphs(inner_lines)
            out.append('      <div class="anders-note">')
            out.append('        <span class="label">Anders\' kommentar</span>')
            out.append(inner_html)
            out.append('      </div>')
            continue

        # Vanlig paragraf — samle linjer til neste tomme/spesial
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt or
                nxt.startswith('### ') or nxt.startswith('## ') or
                nxt.startswith(':::') or
                nxt.startswith('(CLAUDE:') or nxt.startswith('(CALUDE:') or nxt.startswith('(SETT INN') or
                nxt.startswith('(Embed') or nxt.startswith('(SETT_INN') or
                parse_youtube_url(nxt) is not None or
                nxt.startswith('- ') or nxt.startswith('> ')):
                break
            para_lines.append(nxt)
            i += 1
        para = ' '.join(para_lines)
        out.append(f'      <p>{inline_md(para)}</p>')

    return '\n'.join(out)


def render_inner_paragraphs(lines):
    """Render paragrafer inne i en anders-kommentar-blokk (med ekstra innrykk)."""
    out = []
    para = []
    for line in lines:
        s = line.strip()
        if not s:
            if para:
                out.append(f'        <p>{inline_md(" ".join(para))}</p>')
                para = []
        else:
            para.append(s)
    if para:
        out.append(f'        <p>{inline_md(" ".join(para))}</p>')
    return '\n'.join(out)


def render_reading(content: str) -> str:
    return render_paragraphs_with_specials(content)


def render_critique(content: str) -> str:
    return render_paragraphs_with_specials(content)


def render_extra(content: str) -> str:
    """Render «Det du tar med deg videre» / «Avslutning» som ekstra section."""
    head_match = re.match(r'## (.+?)\n', content)
    if head_match:
        title = head_match.group(1)
        body = content[head_match.end():]
    else:
        title = 'Sammendrag'
        body = content
    inner = render_paragraphs_with_specials(body)
    return f'''
    <section class="section reading">
      <h2>{inline_md(title)}</h2>
{inner}
    </section>'''


def render_checklist(content: str):
    """
    Returner (intro_html, [checklist_items]).
    Format:
      ## Sjekkliste for idévurdering
      <intro paragraph>
      - [ ] punkt 1
      - [ ] punkt 2
    """
    lines = content.split('\n')
    intro_lines = []
    items = []
    i = 1  # hopp over h2
    # Samle intro
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith('- ['):
            break
        if s:
            intro_lines.append(s)
        i += 1
    intro = inline_md(' '.join(intro_lines)) if intro_lines else ''

    # Samle items
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith('- ['):
            text = re.sub(r'^- \[[ x]\]\s*', '', s)
            items.append(inline_md(text))
        i += 1

    return intro, items


def render_quiz(content: str):
    """
    Returner (intro_html, [quiz_items]).
    Format:
      ## Prøve
      <intro paragraph>
      ### Q1. Spørsmål?
      - [ ] Alt 1
      - [x] Alt 2 (riktig)
      - [ ] Alt 3
      - [ ] Alt 4
      > Forklaring som vises etter retting.
    """
    lines = content.split('\n')
    i = 1  # hopp over h2

    # Samle intro
    intro_lines = []
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith('### Q'):
            break
        if s:
            intro_lines.append(s)
        i += 1
    intro = inline_md(' '.join(intro_lines)) if intro_lines else ''

    # Samle quiz-items
    items = []
    current = None
    while i < len(lines):
        s = lines[i].strip()
        m = re.match(r'### Q(\d+)\.\s*(.+)', s)
        if m:
            if current:
                items.append(current)
            current = {
                'q_num': int(m.group(1)),
                'question': m.group(2).strip(),
                'options': [],
                'correct': None,
                'explanation': '',
            }
            i += 1
            continue

        if current and s.startswith('- ['):
            opt_match = re.match(r'- \[([ x])\]\s*(.+)', s)
            if opt_match:
                is_correct = opt_match.group(1) == 'x'
                opt_letter = chr(ord('a') + len(current['options']))
                current['options'].append({'letter': opt_letter, 'text': opt_match.group(2).strip()})
                if is_correct:
                    current['correct'] = opt_letter
            i += 1
            continue

        if current and s.startswith('>'):
            # Forklaring (kan strekke over flere linjer som blockquote)
            expl_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                expl_lines.append(re.sub(r'^>\s*', '', lines[i].strip()))
                i += 1
            current['explanation'] = ' '.join(expl_lines)
            continue

        i += 1

    if current:
        items.append(current)

    return intro, items


# ----------------------------------------------------------------------
# Page templates
# ----------------------------------------------------------------------
TOPBAR = '''<header class="topbar">
  <a class="brand-mark" href="index.html" aria-label="Morgenstern — Reklameforståelse">
    <img src="assets/logo/logo-primary-black.png" alt="Morgenstern" />
    <span class="sitename">Reklameforståelse <em>— et krasjkurs fra Morgenstern</em></span>
  </a>
  <nav class="mainnav" aria-label="Hovednavigasjon">
    <a href="index.html">Forside</a>
    <a href="dag-1.html"{KURS_ACTIVE}>Kurs</a>
    <a href="oppslag.html"{OPPSLAG_ACTIVE}>Oppslag</a>
    <a href="index.html#om">Om</a>
  </nav>
</header>'''

SITE_FOOTER = '''<footer class="site-footer">
  <div>Morgenstern · <a href="https://morgenstern.no">morgenstern.no</a></div>
  <div class="user-strip"><span class="user-email" data-user-email>—</span> · <a href="#" class="logout-link" data-logout>Logg ut</a></div>
</footer>'''

# ----------------------------------------------------------------------
# Drop-in kalkulator (Kjøpsøyeblikk) — leses fra egen fil
# ----------------------------------------------------------------------
def _load_kalkulator():
    p = DST / 'kalkulator-kjopsoyeblikk.html'
    if not p.exists():
        return ''
    return p.read_text(encoding='utf-8')

KALKULATOR_HTML = _load_kalkulator()

# ----------------------------------------------------------------------
# Lesson renderer
# ----------------------------------------------------------------------
def render_lesson(day_num: int, fm: dict, body: str) -> str:
    title = fm.get('title', '').strip().strip('"').strip("«»")
    duration = fm.get('duration', '15 minutter').strip().strip('"')
    # Force "15 minutter"
    if '30 minutter' in duration:
        duration = '15 minutter'
    if '15' not in duration and 'minutter' in duration:
        duration = '15 minutter'

    part_label = fm.get('part', '').strip().strip('"').strip("«»")

    principle = fm.get('principle', '').strip()
    # Anvend tekst-endringer på principle (som er prosa)
    principle = apply_text_changes(principle)

    primary = fm.get('primary_source', {}) or {}
    primary_title = (primary.get('title') or '').strip().strip('"')
    primary_meta = (primary.get('meta') or '').strip().strip('"')

    related = fm.get('related', []) or []

    prev_data = fm.get('prev', {}) or {}
    next_data = fm.get('next', {}) or {}

    # Bestem data-part fra "Del N · ..."
    part_match = re.match(r'Del (\d+)', part_label)
    data_part = int(part_match.group(1)) if part_match else 1

    # Ordinal til norsk
    ordinal_map = {1: 'én', 2: 'to', 3: 'tre', 4: 'fire', 5: 'fem',
                   6: 'seks', 7: 'sju', 8: 'åtte', 9: 'ni', 10: 'ti',
                   11: 'elleve', 12: 'tolv', 13: 'tretten'}
    # økt-marker label — vi bruker «Økt N» med tall
    okt_label = f"Økt {day_num}"
    big_num = f"{day_num:02d}"

    # Render seksjoner
    sections = render_section_blocks(body, data_part)

    # Forrige-lenke
    if prev_data and prev_data.get('day'):
        prev_day = prev_data['day']
        prev_title = (prev_data.get('title') or '').strip().strip('"')
        prev_html = f'''      <a href="dag-{prev_day}.html" class="prev">
        <span class="dir">← Forrige</span>
        <span>{html_module.escape(prev_title)}</span>
      </a>'''
    else:
        # Forsiden / kursoversikt
        prev_html = '''      <a href="index.html" class="prev">
        <span class="dir">← Forside</span>
        <span>Kursoversikt</span>
      </a>'''

    # Neste-lenke
    if next_data and next_data.get('day'):
        next_day = next_data['day']
        next_title = (next_data.get('title') or '').strip().strip('"')
        next_html = f'''      <a href="dag-{next_day}.html" class="next">
        <span class="dir">Neste →</span>
        <span>{html_module.escape(next_title)}</span>
      </a>'''
    else:
        next_html = '''      <a href="index.html" class="next">
        <span class="dir">Tilbake →</span>
        <span>Forsiden</span>
      </a>'''

    # Sjekkliste-HTML
    if sections['checklist_items']:
        cl_intro = sections['checklist_intro']
        cl_items_html = '\n'.join([
            f'        <li>\n          <input type="checkbox" id="c{idx+1}" data-key="c{idx+1}" />\n          <label for="c{idx+1}">{txt}</label>\n        </li>'
            for idx, txt in enumerate(sections['checklist_items'])
        ])
        checklist_html = f'''
    <section class="section">
      <h2>Sjekkliste <span class="badge">for idévurdering</span></h2>
      <p>{cl_intro}</p>

      <ul class="checklist">
{cl_items_html}
      </ul>
    </section>'''
    else:
        checklist_html = ''

    # Quiz-HTML
    if sections['quiz_items']:
        quiz_intro = sections['quiz_intro']
        quiz_items_html = []
        for q in sections['quiz_items']:
            opts_html = '\n'.join([
                f'            <label><input type="radio" name="q{q["q_num"]}" value="{o["letter"]}" /><span>{inline_md(o["text"])}</span></label>'
                for o in q['options']
            ])
            quiz_items_html.append(f'''        <li class="quiz-item" data-question="q{q["q_num"]}" data-correct="{q["correct"] or "a"}">
          <div class="quiz-question">{inline_md(q["question"])}</div>
          <div class="quiz-options">
{opts_html}
          </div>
          <div class="quiz-explanation">{inline_md(q["explanation"])}</div>
        </li>''')
        quiz_items_str = '\n\n'.join(quiz_items_html)
        quiz_html = f'''
    <section class="section quiz" data-quiz>
      <h2>Prøve <span class="badge">4 spørsmål</span></h2>
      <p>{quiz_intro}</p>

      <ol class="quiz-list">

{quiz_items_str}

      </ol>

      <div class="quiz-actions">
        <button type="button" class="btn" data-quiz-submit>Rett prøven</button>
        <button type="button" class="btn secondary" data-quiz-reset hidden>Ta om igjen</button>
      </div>

      <div class="quiz-result" data-quiz-result hidden></div>
    </section>'''
    else:
        quiz_html = ''

    # Aside (sidefelt)
    aside_blocks = []
    if primary_title:
        aside_blocks.append(f'''    <div class="source-box">
      <span class="label">Primærkilde</span>
      <div class="title">{html_module.escape(primary_title)}</div>
      <div class="meta">{html_module.escape(primary_meta).replace(chr(10), '<br/>')}</div>
    </div>''')

    for r in related:
        rt = (r.get('title') or '').strip().strip('"')
        rm = (r.get('meta') or '').strip().strip('"')
        if rt:
            aside_blocks.append(f'''    <div class="source-box">
      <span class="label">Beslektet</span>
      <div class="title">{html_module.escape(rt)}</div>
      <div class="meta">{html_module.escape(rm)}</div>
    </div>''')
    aside_html = '\n\n'.join(aside_blocks)

    # Topbar
    topbar = TOPBAR.format(KURS_ACTIVE=' class="active"', OPPSLAG_ACTIVE='')

    # Bygg full side
    extra_section = sections.get('extra_html', '')

    html = f'''<!DOCTYPE html>
<html lang="nb">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <script>
    (function () {{
      if (location.pathname.split('/').pop() === 'login.html') return;
      try {{
        if (!localStorage.getItem('reklameforstaelse.user.email')) {{
          var here = (location.pathname.split('/').pop() || '') + location.search;
          location.replace('login.html?return=' + encodeURIComponent(here));
        }}
      }} catch (e) {{ /* localStorage utilgjengelig */ }}
    }})();
  </script>
  <title>Økt {day_num} — {html_module.escape(title)} · Reklameforståelse</title>
  <link rel="stylesheet" href="styles.css" />

  <link rel="icon" type="image/x-icon" href="assets/favicon/favicon.ico" />
  <link rel="icon" type="image/png" sizes="32x32" href="assets/favicon/favicon-32.png" />
  <link rel="icon" type="image/png" sizes="16x16" href="assets/favicon/favicon-16.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="assets/favicon/apple-touch-icon.png" />

  <meta property="og:type" content="website" />
  <meta property="og:locale" content="nb_NO" />
  <meta property="og:site_name" content="Reklameforståelse — Morgenstern" />
  <meta property="og:title" content="Økt {day_num} — {html_module.escape(title)} · Reklameforståelse" />
  <meta property="og:description" content="Et krasjkurs i reklameforståelse over 13 økter — bygget på Binet &amp; Field, Sharp, Sutherland og Cialdini. Fra Morgenstern." />
  <meta property="og:url" content="https://reklameforstaelse.morgenstern.no/dag-{day_num}" />
  <meta property="og:image" content="https://reklameforstaelse.morgenstern.no/og-image.jpg" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Økt {day_num} — {html_module.escape(title)} · Reklameforståelse" />
  <meta name="twitter:description" content="Et krasjkurs i reklameforståelse over 13 økter — bygget på Binet &amp; Field, Sharp, Sutherland og Cialdini. Fra Morgenstern." />
  <meta name="twitter:image" content="https://reklameforstaelse.morgenstern.no/og-image.jpg" />
</head>
<body data-part="{data_part}">

{topbar}

<main class="lesson" data-lesson-day="{day_num}">

  <article class="lesson-main">

    <div class="running-head">
      <span>{html_module.escape(part_label)}</span>
      <span>{html_module.escape(duration)}</span>
    </div>

    <header>
      <div class="day-marker">
        <small>{okt_label}</small>
        {big_num}
      </div>
      <h1>{html_module.escape(title)}</h1>
    </header>

    <div class="principle">
      <span class="principle-label">Øktens prinsipp</span>
      {inline_md(principle)}
    </div>

    <section class="section reading">
      <h2>Lesning</h2>

{sections["reading_html"]}
    </section>

    <section class="section critique">
      <h2>Kritikk av teorien</h2>

{sections["critique_html"]}
    </section>
{checklist_html}{quiz_html}{extra_section}

    <footer class="lesson-footer">
{prev_html}
      <a href="#" class="btn" data-finish-day>Marker økten som fullført →</a>
{next_html}
    </footer>

  </article>

  <aside class="lesson-aside">

    <div class="progress-strip">
      <span class="progress-strip-label">Din progresjon</span>
      <div class="progress-bar" aria-label="13 økter, nåværende økt {day_num}"></div>
    </div>

{aside_html}

  </aside>

</main>

{SITE_FOOTER}

<script src="app.js"></script>
<script src="feedback.js"></script>
</body>
</html>
'''
    return html


# ----------------------------------------------------------------------
# Update MD source (apply text changes, fix typos)
# ----------------------------------------------------------------------
def update_md_source(md_text: str) -> str:
    """Anvend tekst-endringer på MD body (ikke YAML)."""
    fm_match = re.match(r'^---\n(.*?)\n---\n', md_text, re.S)
    if not fm_match:
        return apply_text_changes(md_text)

    fm_block = fm_match.group(0)
    body = md_text[fm_match.end():]

    # Også anvend på YAML-felter som principle/title/duration/part/related-titles/prev-titles/next-titles
    fm_block_updated = fm_block
    # Force duration → "15 minutter"
    fm_block_updated = re.sub(r'duration:\s*"30 minutter"', 'duration: "15 minutter"', fm_block_updated)
    fm_block_updated = re.sub(r"duration:\s*'30 minutter'", "duration: '15 minutter'", fm_block_updated)
    # Anvend på principle-feltet (kan strekke seg over linjer med >)
    # For enkelhets skyld, anvend på hele fm-blokken — men bevar "day:"-felter
    # day-felter er heltall (day: 1), så ikke en problem
    # principle: > og deretter linjer er prosa
    # I praksis: kjør tekstendringer på hele fm-blokken minus "day:"-numrene
    # (gjør et ekstra steg som plukker ut numerikalske day:-felter)

    # Kompromiss: kjør apply_text_changes på fm_block_updated, men beskytt YAML-keys
    # Vi vet at:
    # - "Dag" finnes ikke i YAML keys, kun mulig som ord i prev/next titles
    # - Apply_text_changes vil bytte "Dag X" → "Økt X" innenfor strings — det er greit
    # - "30 minutter" kan endres til 15 — også greit

    # Bygg en sikker variant ved å kjøre apply_text_changes (bare på linjer som ikke begynner med "day:")
    fm_lines = fm_block_updated.split('\n')
    safe_fm_lines = []
    for line in fm_lines:
        stripped = line.strip()
        if (stripped.startswith('day:') or
            stripped == '---' or
            re.match(r'\s+day:\s*\d+', line)):
            safe_fm_lines.append(line)
        else:
            safe_fm_lines.append(apply_text_changes(line))
    fm_block_updated = '\n'.join(safe_fm_lines)

    body_updated = apply_text_changes(body)
    return fm_block_updated + body_updated


# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
if __name__ == '__main__':
    md_files = sorted(SRC.glob('dag-*.md'), key=lambda p: int(re.search(r'\d+', p.name).group()))

    for mdp in md_files:
        day_num = int(re.search(r'\d+', mdp.name).group())
        print(f"\n=== Behandler dag-{day_num} ===")
        text = mdp.read_text(encoding='utf-8')

        # 1) Oppdater MD-kilde (kun lokalt; i CI skipper vi for å unngå loop)
        updated_md = update_md_source(text)
        if updated_md != text and WRITE_MD_BACK:
            mdp.write_text(updated_md, encoding='utf-8')
            print(f"  Oppdaterte {mdp.name}")
        else:
            print(f"  Ingen MD-endring i {mdp.name}")

        # 2) Render HTML
        fm, body = parse_frontmatter(updated_md)
        html_out = render_lesson(day_num, fm, body)
        out_path = DST / f'dag-{day_num}.html'
        out_path.write_text(html_out, encoding='utf-8')
        print(f"  Skrev {out_path.name}")

    print("\nFerdig.")
