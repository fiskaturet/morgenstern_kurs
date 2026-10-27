// Tilgangskontroll for kurset.
// Alle sider krever en gyldig tilgangskode. Kodene ligger som saltet hash i Vercel Edge Config
// (nøkkelen «tilgang», koblet til prosjektet som GLOBAL_CONFIG), som tilgangsoversikten skriver til hver gang noe endres.
// tilgang.json i repoet er reserve hvis Edge Config ikke svarer eller ikke er koblet til.
// Utløpte og sperrede koder slipper ikke inn.
import RESERVE from './tilgang.json';

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

let buffer = { data: null, tid: 0 };
let kilde = 'ukjent';

// Henter kodene fra Edge Config. Svaret holdes i 15 sekunder per instans.
async function hentTilgang() {
  // Vercel kaller variabelen GLOBAL_CONFIG når Edge Config kobles til i dashbordet.
  const tilkobling = process.env.GLOBAL_CONFIG || process.env.EDGE_CONFIG;
  if (!tilkobling) { kilde = 'reserve: GLOBAL_CONFIG mangler'; return RESERVE; }
  if (buffer.data && Date.now() - buffer.tid < 15000) return buffer.data;
  try {
    const u = new URL(tilkobling);
    const id = u.pathname.replace(/^\//, '');
    const token = u.searchParams.get('token');
    const svar = await fetch(`${u.origin}/${id}/item/tilgang?token=${token}`, { cache: 'no-store' });
    if (svar.ok) {
      const data = await svar.json();
      if (data && data.salt && Array.isArray(data.koder) && data.koder.length) {
        buffer = { data, tid: Date.now() };
        kilde = 'edge-config';
        return data;
      }
      kilde = 'reserve: tomt svar fra Edge Config';
    } else {
      kilde = 'reserve: Edge Config svarte ' + svar.status;
    }
  } catch (e) {
    kilde = 'reserve: ' + String((e && e.message) || e).slice(0, 80);
  }
  return buffer.data || RESERVE;
}

function finn(tilgang, hash) {
  return (tilgang.koder || []).find((k) => k.hash === hash) || null;
}

function utlopt(k) {
  if (!k.utloper) return false;
  // Koden gjelder ut utløpsdagen, norsk tid.
  return new Date(k.utloper + 'T23:59:59+02:00').getTime() < Date.now();
}

function gyldig(k) {
  return Boolean(k) && !k.sperret && !utlopt(k);
}

// Noen koder gjelder bare for e-poster på bestemte domener, f.eks. den interne koden.
function riktigDomene(k, epost) {
  if (!k || !Array.isArray(k.domener) || !k.domener.length) return true;
  const domene = epost.split('@')[1] || '';
  return k.domener.includes(domene);
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
    const epost = String(form.get('epost') || '').trim().toLowerCase();
    const tilgang = await hentTilgang();
    const hash = await sha256((tilgang.salt || '') + kode);
    const k = finn(tilgang, hash);
    if (gyldig(k) && riktigDomene(k, epost)) {
      return videresend(url, retur, `${COOKIE}=${hash}; Path=/; Max-Age=${NITTI_DAGER}; HttpOnly; Secure; SameSite=Lax`);
    }
    const feil = k && utlopt(k) ? 'utlopt' : k && !riktigDomene(k, epost) ? 'domene' : '1';
    return videresend(url, '/login?feil=' + feil + '&return=' + encodeURIComponent(retur));
  }

  if (sti === '/loggut') {
    return videresend(url, '/login', `${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax`);
  }

  // Viser hvor kodene hentes fra. Ingen koder eller hasher, bare kilde og antall.
  if (sti === '/tilgang-status') {
    const t = await hentTilgang();
    return new Response(JSON.stringify({ kilde: buffer.data === t ? 'edge-config' : kilde, antall: (t.koder || []).length, oppdatert: t.oppdatert || null }), {
      headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
    });
  }

  if (sti === '/login' || sti === '/login.html') return;

  if (gyldig(finn(await hentTilgang(), lesCookie(req, COOKIE)))) return;

  return videresend(url, '/login?return=' + encodeURIComponent(sti + url.search));
}
