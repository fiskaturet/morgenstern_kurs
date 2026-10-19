// Tilgangskontroll for kurset.
// Alle sider krever en gyldig tilgangskode. Kodene ligger som hash i tilgang.json,
// som oppdateres fra tilgangsoversikten. Utløpte og sperrede koder slipper ikke inn.
import TILGANG from './tilgang.json';

export const config = {
  // Alt unntatt filene innloggingssiden trenger, og bildet som vises når lenken deles.
  matcher: ['/((?!assets/|styles\\.css|favicon\\.ico|og-image\\.jpg).*)'],
};

const COOKIE = 'rf_tilgang';
const NITTI_DAGER = 60 * 60 * 24 * 90;

async function sha256(tekst) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(tekst));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function finn(hash) {
  return (TILGANG.koder || []).find((k) => k.hash === hash) || null;
}

function utlopt(k) {
  if (!k.utloper) return false;
  // Koden gjelder ut utløpsdagen, norsk tid.
  return new Date(k.utloper + 'T23:59:59+02:00').getTime() < Date.now();
}

function gyldig(k) {
  return Boolean(k) && !k.sperret && !utlopt(k);
}

function lesCookie(req, navn) {
  const raw = req.headers.get('cookie') || '';
  for (const del of raw.split(';')) {
    const [k, ...v] = del.trim().split('=');
    if (k === navn) return decodeURIComponent(v.join('='));
  }
  return '';
}

function tryggRetur(verdi) {
  const s = String(verdi || '/');
  return s.startsWith('/') && !s.startsWith('//') ? s : '/';
}

function videresend(url, sted, cookie) {
  const headers = new Headers({ Location: new URL(sted, url).toString() });
  if (cookie) headers.append('Set-Cookie', cookie);
  return new Response(null, { status: 303, headers });
}

export default async function middleware(req) {
  const url = new URL(req.url);
  const sti = url.pathname;

  if (sti === '/logginn' && req.method === 'POST') {
    const form = await req.formData();
    const kode = String(form.get('kode') || '').trim().toLowerCase().replace(/\s+/g, '-');
    const retur = tryggRetur(form.get('return'));
    const hash = await sha256((TILGANG.salt || '') + kode);
    const k = finn(hash);
    if (gyldig(k)) {
      return videresend(url, retur, `${COOKIE}=${hash}; Path=/; Max-Age=${NITTI_DAGER}; HttpOnly; Secure; SameSite=Lax`);
    }
    const feil = k && utlopt(k) ? 'utlopt' : '1';
    return videresend(url, '/login?feil=' + feil + '&return=' + encodeURIComponent(retur));
  }

  if (sti === '/loggut') {
    return videresend(url, '/login', `${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax`);
  }

  if (sti === '/login' || sti === '/login.html') return;

  if (gyldig(finn(lesCookie(req, COOKIE)))) return;

  return videresend(url, '/login?return=' + encodeURIComponent(sti + url.search));
}
