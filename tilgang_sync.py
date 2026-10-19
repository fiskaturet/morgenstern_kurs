"""Bygger tilgang.json fra tilgangsoversikten.

Bruk: python tilgang_sync.py <mappe med eksporterte JSON-dokumenter fra samlingen «tilganger»>

Nettsiden får bare en saltet SHA-256-hash av hver kode, utløpsdatoen og en intern id.
Sperrede koder tas ikke med. Saltet beholdes fra forrige tilgang.json.
"""
import hashlib
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).parent
UT = ROOT / 'tilgang.json'


def main(mappe: str) -> None:
    gammel = json.loads(UT.read_text(encoding='utf-8')) if UT.exists() else {}
    salt = gammel.get('salt') or secrets.token_hex(16)
    koder = []
    for f in sorted(Path(mappe).glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        d = d.get('data', d)
        kode = str(d.get('kode', '')).strip().lower()
        if not kode or d.get('sperret'):
            continue
        oppf = {
            'id': f.stem,
            'hash': hashlib.sha256((salt + kode).encode('utf-8')).hexdigest(),
            'utloper': d.get('utloper') or '',
        }
        domener = [str(x).strip().lower().lstrip('@') for x in (d.get('domener') or []) if str(x).strip()]
        if domener:
            oppf['domener'] = domener
        koder.append(oppf)
    if not koder:
        sys.exit('Ingen aktive koder. Avbryter, ellers stenges alle ute.')
    UT.write_text(json.dumps({'salt': salt, 'koder': koder}, indent=1) + '\n', encoding='utf-8')
    print(f'{len(koder)} koder skrevet til {UT.name}')


if __name__ == '__main__':
    main(sys.argv[1])
