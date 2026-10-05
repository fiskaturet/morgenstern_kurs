#!/usr/bin/env python3
"""
Notion <-> kurs-innhold/*.md

  python notion_sync.py pull      # Notion -> kurs-innhold/dag-N.md (brukes av GitHub Action)
  python notion_sync.py setup ID  # lag «Økter»-databasen + redigeringsguide under Notion-siden ID
  python notion_sync.py import    # kurs-innhold/dag-N.md -> Notion (engangs-migrering)
  python notion_sync.py bootstrap ID  # setup (om nødvendig) + import

Miljøvariabler:
  NOTION_TOKEN        Notion internal integration secret (databasen må være delt med integrasjonen)
  NOTION_DATABASE_ID  (valgfri) ID til «Økter»-databasen. Ellers finnes den på navn.

Format-mapping (Notion-blokk <-> MD):
  heading_2 / heading_3        <->  ## / ###
  paragraph                    <->  avsnitt (blank linje mellom)
  to_do (huket / ikke huket)   <->  - [x] / - [ ]
  bulleted_list_item           <->  - tekst
  quote                        <->  > tekst
  callout 💬                   <->  ::: anders-kommentar ... :::
  callout 🧩 «navn»            <->  ::: navn :::   (f.eks. kalkulator-kjopsoyeblikk)
  divider                      <->  ---
  video/embed/bookmark (URL)   <->  URL alene på linja
Bilder og YouTube-lenker skrives som vanlig tekst på egen linje i Notion.
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'kurs-innhold'
API = 'https://api.notion.com/v1'
NOTION_VERSION = '2022-06-28'
COMMENT_ICON = '💬'
DIRECTIVE_ICON = '🧩'
DB_TITLE = 'Økter'
PARTS = ['Del 1 · Fundamentet', 'Del 2 · Les Binet & Peter Field · The Long and the Short of It',
         'Del 3 · Byron Sharp · How Brands Grow', 'Del 4 · Rory Sutherland · Alchemy',
         'Del 5 · Robert Cialdini · Influence', 'Del 6 · Syntese']


# ----------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------
def _token():
    t = os.environ.get('NOTION_TOKEN')
    if not t:
        sys.exit('NOTION_TOKEN mangler')
    return t


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(6):
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            'Authorization': f'Bearer {_token()}',
            'Notion-Version': NOTION_VERSION,
            'Content-Type': 'application/json',
        })
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(float(e.headers.get('Retry-After', 2 ** attempt)))
                continue
            sys.exit(f'Notion API {e.code}: {e.read().decode()[:500]}')


_DB = None


def db_id():
    """NOTION_DATABASE_ID, ellers databasen «Økter» som integrasjonen har tilgang til."""
    global _DB
    if _DB:
        return _DB
    _DB = os.environ.get('NOTION_DATABASE_ID') or find_db()
    if not _DB:
        sys.exit(f'Fant ingen database «{DB_TITLE}». Kjør «python notion_sync.py setup <side-id>» først.')
    return _DB


def find_db():
    r = api('POST', '/search', {'query': DB_TITLE, 'filter': {'property': 'object', 'value': 'database'}})
    hits = [d for d in r['results'] if ''.join(t['plain_text'] for t in d.get('title', [])) == DB_TITLE]
    return hits[0]['id'] if hits else None


# ----------------------------------------------------------------------
# Rich text
# ----------------------------------------------------------------------
INLINE_RE = re.compile(r'\*\*(.+?)\*\*|(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|\[([^\]]+)\]\(([^)\s]+)\)')


def md_to_rich(s):
    """**fet**, *kursiv*, [lenke](url) -> Notion rich_text (maks 2000 tegn per bit)."""
    out, pos = [], 0

    def add(text, bold=False, italic=False, link=None):
        for k in range(0, len(text), 2000):
            chunk = text[k:k + 2000]
            rt = {'type': 'text', 'text': {'content': chunk}}
            if link:
                rt['text']['link'] = {'url': link}
            if bold or italic:
                rt['annotations'] = {'bold': bold, 'italic': italic}
            out.append(rt)

    for m in INLINE_RE.finditer(s):
        if m.start() > pos:
            add(s[pos:m.start()])
        if m.group(1) is not None:
            inner = m.group(1)
            # støtt kursiv inni fet
            parts = re.split(r'(?<!\*)\*([^*]+)\*(?!\*)', inner)
            for idx, p in enumerate(parts):
                if p:
                    add(p, bold=True, italic=bool(idx % 2))
        elif m.group(2) is not None:
            add(m.group(2), italic=True)
        else:
            add(m.group(3), link=m.group(4))
        pos = m.end()
    if pos < len(s):
        add(s[pos:])
    return out


def rich_to_md(rich):
    out = []
    for rt in rich:
        text = rt.get('plain_text', '')
        if not text:
            continue
        a = rt.get('annotations', {})
        href = rt.get('href') or ((rt.get('text') or {}).get('link') or {}).get('url')
        if not text.strip():
            out.append(text)
            continue
        lead = text[:len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        core = text.strip()
        if core:
            if a.get('code'):
                core = f'`{core}`'
            if a.get('italic'):
                core = f'*{core}*'
            if a.get('bold'):
                core = f'**{core}**'
            if href and not core.startswith('http'):
                core = f'[{core}]({href})'
        out.append(lead + core + trail)
    md = ''.join(out)
    # slå sammen tilstøtende markører: **a****b** -> **ab**, *a**b* -> *ab*
    md = md.replace('****', '')
    return md


# ----------------------------------------------------------------------
# MD -> Notion blocks (import)
# ----------------------------------------------------------------------
YT_RE = re.compile(r'^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)\S+$')
IMG_RE = re.compile(r'^!\[[^\]]*\]\([^)\s]+\)$')
NOTE_PREFIXES = ('(CLAUDE:', '(CALUDE:', '(SETT INN', '(Embed', '(SETT_INN')


def blk(kind, rich, **extra):
    b = {'object': 'block', 'type': kind, kind: {'rich_text': rich, **extra}}
    return b


def md_body_to_blocks(body):
    lines = body.split('\n')
    blocks, i = [], 0

    def is_special(s):
        return (not s or s.startswith(('#', ':::', '- ', '> ', '---')) or s.startswith(NOTE_PREFIXES)
                or YT_RE.match(s) or IMG_RE.match(s))

    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith('### '):
            blocks.append(blk('heading_3', md_to_rich(s[4:])))
        elif s.startswith('## '):
            blocks.append(blk('heading_2', md_to_rich(s[3:])))
        elif s == '---':
            blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
        elif re.match(r'^- \[[ xX]\]', s):
            checked = s[3] in 'xX'
            blocks.append(blk('to_do', md_to_rich(s[6:].strip()), checked=checked))
        elif s.startswith('- '):
            blocks.append(blk('bulleted_list_item', md_to_rich(s[2:])))
        elif s.startswith('> '):
            q = [s[2:]]
            while i + 1 < len(lines) and lines[i + 1].strip().startswith('> '):
                i += 1
                q.append(lines[i].strip()[2:])
            blocks.append(blk('quote', md_to_rich(' '.join(q))))
        elif s.startswith(':::'):
            name = s.strip(':').strip()
            if name == 'anders-kommentar':
                inner, para = [], []
                i += 1
                while i < len(lines):
                    ln = lines[i].rstrip()
                    end = ln.strip() == ':::' or ln.endswith(':::')
                    txt = ln[:-3].rstrip() if (end and ln.strip() != ':::') else ('' if end else ln)
                    if txt.strip():
                        para.append(txt.strip())
                    elif para:
                        inner.append(' '.join(para)); para = []
                    if end:
                        break
                    i += 1
                if para:
                    inner.append(' '.join(para))
                children = [blk('paragraph', md_to_rich(p)) for p in inner[1:]]
                b = blk('callout', md_to_rich(inner[0] if inner else ''),
                        icon={'type': 'emoji', 'emoji': COMMENT_ICON}, color='gray_background')
                if children:
                    b['callout']['children'] = children
                blocks.append(b)
            else:
                if not s.endswith(':::') or s == ':::':
                    while i + 1 < len(lines) and lines[i + 1].strip() != ':::':
                        i += 1
                    i += 1
                blocks.append(blk('callout', md_to_rich(name), icon={'type': 'emoji', 'emoji': DIRECTIVE_ICON},
                                  color='blue_background'))
        elif YT_RE.match(s) or IMG_RE.match(s):
            blocks.append(blk('paragraph', [{'type': 'text', 'text': {'content': s}}]))
        else:
            para = [s]
            while i + 1 < len(lines) and not is_special(lines[i + 1].strip()):
                i += 1
                para.append(lines[i].strip())
            blocks.append(blk('paragraph', md_to_rich(' '.join(para))))
        i += 1
    return blocks


def parse_md(path):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    fm = yaml.safe_load(m.group(1).replace('»', '"').replace('«', '"'))
    return fm, text[m.end():]


def props_from_fm(fm, status='Publisert'):
    def rt(s):
        return {'rich_text': md_to_rich(str(s or '').strip())}
    related = '\n'.join(f"{r.get('title', '')} | {r.get('meta', '')}" for r in (fm.get('related') or []))
    ps = fm.get('primary_source') or {}
    return {
        'Tittel': {'title': md_to_rich(fm['title'])},
        'Økt': {'number': int(fm['day'])},
        'Del': {'select': {'name': fm['part']}},
        'Status': {'select': {'name': status}},
        'Varighet': rt(fm.get('duration')),
        'Prinsipp': rt(fm.get('principle')),
        'Hovedkilde': rt(ps.get('title')),
        'Hovedkilde info': rt(ps.get('meta')),
        'Relatert': {'rich_text': [{'type': 'text', 'text': {'content': related}}] if related else []},
    }


def cmd_import():
    existing = {int(p['properties']['Økt']['number']): p['id']
                for p in query_all() if p['properties']['Økt']['number'] is not None}
    for path in sorted(SRC.glob('dag-*.md'), key=lambda p: int(re.search(r'\d+', p.name).group())):
        fm, body = parse_md(path)
        day = int(fm['day'])
        if day in existing:
            print(f'Økt {day} finnes allerede i Notion – hopper over')
            continue
        blocks = md_body_to_blocks(body)
        page = api('POST', '/pages', {'parent': {'database_id': db_id()},
                                      'properties': props_from_fm(fm), 'children': blocks[:100]})
        for k in range(100, len(blocks), 100):
            api('PATCH', f"/blocks/{page['id']}/children", {'children': blocks[k:k + 100]})
        print(f'Importerte økt {day}: {fm["title"]} ({len(blocks)} blokker)')


GUIDE_MD = """**Slik redigerer du kurset.** Hver økt er en side i databasen «Økter». Bare sider med status **Publisert** går ut på nettsiden. Nettsiden oppdateres automatisk innen et kvarter.
## Faste seksjoner på hver økt
- **Lesning**: hovedteksten. Bruk overskrift 3 for mellomtitler.
- **Sjekkliste for idévurdering**: avkrysningsliste (ikke huk av).
- **Prøve**: én intro-linje, så overskrift 3 «Q1. Spørsmål?», fire avkrysningsalternativer der det riktige er huket av, og et sitat med forklaringen.
- **Kritikk av teorien**: vanlig tekst.
## Spesialblokker
- **Anders-kommentar**: en callout med 💬-ikon.
- **Kalkulator**: en callout med 🧩-ikon og teksten kalkulator-kjopsoyeblikk.
- **YouTube-video**: lim inn lenken alene på en linje (kursiv linje rett under blir bildetekst).
- **Bilde fra nettsiden**: skriv ![alt-tekst](assets/filnavn.svg) alene på en linje.
- **Notater som ikke skal publiseres**: start linjen med (CLAUDE: …)."""


def cmd_setup(parent):
    api('PATCH', f'/blocks/{parent}/children', {'children': md_body_to_blocks(GUIDE_MD)})
    db = api('POST', '/databases', {
        'parent': {'type': 'page_id', 'page_id': parent},
        'title': [{'type': 'text', 'text': {'content': DB_TITLE}}],
        'is_inline': True,
        'properties': {
            'Tittel': {'title': {}},
            'Økt': {'number': {}},
            'Del': {'select': {'options': [{'name': p} for p in PARTS]}},
            'Status': {'select': {'options': [{'name': 'Publisert', 'color': 'green'},
                                              {'name': 'Utkast', 'color': 'gray'}]}},
            'Varighet': {'rich_text': {}},
            'Prinsipp': {'rich_text': {}},
            'Hovedkilde': {'rich_text': {}},
            'Hovedkilde info': {'rich_text': {}},
            'Relatert': {'rich_text': {}},
            'Sist endret': {'last_edited_time': {}},
        }})
    print(f"Opprettet databasen «{DB_TITLE}»: {db['id']}")
    global _DB
    _DB = db['id']


def cmd_bootstrap(parent):
    """Engangsoppsett: lag databasen hvis den mangler, og importer øktene som ikke finnes."""
    if not (os.environ.get('NOTION_DATABASE_ID') or find_db()):
        cmd_setup(parent)
    cmd_import()


# ----------------------------------------------------------------------
# Notion -> MD (pull)
# ----------------------------------------------------------------------
def query_all(filter_=None):
    results, cursor = [], None
    while True:
        body = {'page_size': 100}
        if filter_:
            body['filter'] = filter_
        if cursor:
            body['start_cursor'] = cursor
        r = api('POST', f'/databases/{db_id()}/query', body)
        results += r['results']
        if not r.get('has_more'):
            return results
        cursor = r['next_cursor']


def children(block_id):
    out, cursor = [], None
    while True:
        q = f'?page_size=100' + (f'&start_cursor={cursor}' if cursor else '')
        r = api('GET', f'/blocks/{block_id}/children{q}')
        out += r['results']
        if not r.get('has_more'):
            return out
        cursor = r['next_cursor']


def prop_text(p):
    t = p.get('type')
    if t in ('title', 'rich_text'):
        return rich_to_md(p[t]).strip()
    if t == 'select':
        return (p['select'] or {}).get('name', '')
    if t == 'number':
        return p['number']
    return ''


def blocks_to_md(blocks):
    out = []  # liste av (tekst, kind) så vi kan styre blanke linjer mellom listepunkter
    for b in blocks:
        t = b['type']
        d = b.get(t, {})
        rich = d.get('rich_text', [])
        if t == 'paragraph':
            txt = rich_to_md(rich).strip()
            if txt:
                out.append((txt, 'p'))
        elif t in ('heading_1', 'heading_2'):
            out.append(('## ' + rich_to_md(rich).strip(), 'h'))
        elif t == 'heading_3':
            out.append(('### ' + rich_to_md(rich).strip(), 'h'))
        elif t == 'to_do':
            out.append((f"- [{'x' if d.get('checked') else ' '}] " + rich_to_md(rich).strip(), 'li'))
        elif t in ('bulleted_list_item', 'numbered_list_item'):
            out.append(('- ' + rich_to_md(rich).strip(), 'li'))
        elif t == 'quote':
            out.append(('> ' + rich_to_md(rich).strip().replace('\n', ' '), 'p'))
        elif t == 'divider':
            out.append(('---', 'p'))
        elif t == 'callout':
            icon = (d.get('icon') or {}).get('emoji')
            first = rich_to_md(rich).strip()
            if icon == DIRECTIVE_ICON:
                out.append((f'::: {first} :::', 'p'))
            else:
                inner = [first] if first else []
                if b.get('has_children'):
                    inner += [x for x, _ in blocks_to_md(children(b['id']))]
                out.append(('::: anders-kommentar\n' + '\n\n'.join(inner) + '\n:::', 'p'))
        elif t in ('video', 'embed', 'bookmark'):
            url = d.get('url') or (d.get('external') or {}).get('url', '')
            if url:
                out.append((url, 'p'))
        elif t == 'image':
            cap = rich_to_md(d.get('caption', [])).strip()
            print(f'  ADVARSEL: opplastet bilde i Notion støttes ikke ennå ({cap or "uten bildetekst"}). '
                  f'Legg bildet i assets/ og skriv ![alt](assets/fil) på egen linje.')
        elif t == 'code':
            out.append(('```\n' + ''.join(r['plain_text'] for r in rich) + '\n```', 'p'))
    return out


def join_md(items):
    s, prev = '', None
    for txt, kind in items:
        if prev is not None:
            s += '\n' if (kind == 'li' and prev == 'li') else '\n\n'
        s += txt
        prev = kind
    return s + '\n'


def yaml_str(v):
    return json.dumps(str(v), ensure_ascii=False)


def build_frontmatter(meta, prev, nxt):
    lines = ['---', f"day: {meta['day']}", f"part: {yaml_str(meta['part'])}",
             f"duration: {yaml_str(meta['duration'] or '15 minutter')}", f"title: {yaml_str(meta['title'])}",
             'principle: >', '  ' + meta['principle'].replace('\n', ' '),
             'primary_source:', f"  title: {yaml_str(meta['ps_title'])}", f"  meta: {yaml_str(meta['ps_meta'])}"]
    if meta['related']:
        lines.append('related:')
        for r in meta['related']:
            lines += [f"  - title: {yaml_str(r[0])}", f"    meta: {yaml_str(r[1])}"]
    lines.append('prev:')
    lines += ['  day: null'] if not prev else [f"  day: {prev['day']}", f"  title: {yaml_str(prev['title'])}"]
    lines.append('next:')
    lines += ['  day: null'] if not nxt else [f"  day: {nxt['day']}", f"  title: {yaml_str(nxt['title'])}"]
    lines.append('---')
    return '\n'.join(lines) + '\n\n'


def cmd_pull():
    pages = query_all({'property': 'Status', 'select': {'equals': 'Publisert'}})
    metas = []
    for p in pages:
        pr = p['properties']
        if pr['Økt']['number'] is None:
            continue
        related = []
        for line in prop_text(pr['Relatert']).split('\n'):
            if line.strip():
                a, _, b = line.partition('|')
                related.append((a.strip(), b.strip()))
        metas.append({'id': p['id'], 'day': int(pr['Økt']['number']), 'title': prop_text(pr['Tittel']),
                      'part': prop_text(pr['Del']), 'duration': prop_text(pr['Varighet']),
                      'principle': prop_text(pr['Prinsipp']), 'ps_title': prop_text(pr['Hovedkilde']),
                      'ps_meta': prop_text(pr['Hovedkilde info']), 'related': related})
    metas.sort(key=lambda m: m['day'])
    if not metas:
        sys.exit('Fant ingen publiserte økter – avbryter for ikke å slette innhold')
    SRC.mkdir(exist_ok=True)
    for idx, m in enumerate(metas):
        prev = metas[idx - 1] if idx > 0 else None
        nxt = metas[idx + 1] if idx + 1 < len(metas) else None
        body = join_md(blocks_to_md(children(m['id'])))
        path = SRC / f"dag-{m['day']}.md"
        new = build_frontmatter(m, prev, nxt) + body
        if not path.exists() or path.read_text(encoding='utf-8') != new:
            path.write_text(new, encoding='utf-8')
            print(f"Oppdaterte {path.name}")
        else:
            print(f"Uendret {path.name}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'pull'
    if cmd == 'setup':
        cmd_setup(sys.argv[2])
    elif cmd == 'bootstrap':
        cmd_bootstrap(sys.argv[2])
    else:
        {'pull': cmd_pull, 'import': cmd_import}[cmd]()
