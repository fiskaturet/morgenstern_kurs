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
const BRUKER = 'rf_bruker';
const NITTI_DAGER = 60 * 60 * 24 * 90;
const INTERN = 'morgenstern-internt';
const SIDE = /^(forside|dag-\d{1,2}|hele-kurset|oppslag)$/;

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

// ---------- Lesesporing (Upstash Redis via Vercel) ----------
// Vercel-integrasjonen gir enten KV_REST_API_* eller UPSTASH_REDIS_REST_*.
function redisOppsett() {
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  return url && token ? { url: url.replace(/\/$/, ''), token } : null;
}

async function redis(kommandoer) {
  const r = redisOppsett();
  if (!r) throw new Error('Redis er ikke koblet til');
  const svar = await fetch(r.url + '/pipeline', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + r.token, 'content-type': 'application/json' },
    body: JSON.stringify(kommandoer),
    cache: 'no-store',
  });
  if (!svar.ok) throw new Error('Redis svarte ' + svar.status);
  return (await svar.json()).map((x) => x.result);
}

function json(data, status) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  });
}

function heltall(v, min, max) {
  const n = Math.round(Number(v));
  return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : min;
}

// Deltakeren identifiseres med e-posten fra innloggingen (cookie). Folk som logget inn før sporingen kom,
// mangler cookien. Da brukes e-posten nettleseren lagret ved innlogging, og til slutt bare koden.
const EPOST = /^[^@\s]{1,64}@[^@\s]{1,100}$/;
function deltaker(req, k, fraSiden) {
  const cookie = lesCookie(req, BRUKER).trim().toLowerCase();
  if (EPOST.test(cookie)) return cookie;
  const lagret = String(fraSiden || '').trim().toLowerCase();
  return EPOST.test(lagret) ? lagret : 'kode:' + k.id;
}

async function lagreSpor(req, k) {
  const tekst = (await req.text()).slice(0, 4000);
  let d;
  try { d = JSON.parse(tekst); } catch (e) { return new Response(null, { status: 400 }); }
  const side = String(d.side || '');
  if (!SIDE.test(side)) return new Response(null, { status: 400 });
  const uid = deltaker(req, k, d.epost);
  const naa = new Date().toISOString();
  const k1 = [
    ['SADD', 'brukere', uid],
    ['HSET', 'brukerinfo:' + uid, 'kode', k.id, 'sist', naa],
    ['HSETNX', 'brukerinfo:' + uid, 'forste', naa],
  ];
  if (d.type === 'vis') {
    k1.push(['HINCRBY', 'visninger:' + uid, side, 1]);
  } else if (d.type === 'les') {
    k1.push(['ZADD', 'dybde:' + uid, 'GT', heltall(d.dybde, 0, 100), side]);
    const sek = heltall(d.sek, 0, 1800);
    if (sek) k1.push(['HINCRBY', 'tid:' + uid, side, sek]);
  } else if (d.type === 'quiz' && Array.isArray(d.svar)) {
    const svar = d.svar.slice(0, 20).map((x) => ({
      q: String(x.q || '').slice(0, 20),
      valgt: String(x.valgt || '').slice(0, 4),
      riktig: String(x.riktig || '').slice(0, 4),
    }));
    k1.push(['HSET', 'quiz:' + uid, side, JSON.stringify({ tid: naa, svar })]);
    k1.push(['HINCRBY', 'quizforsok:' + uid, side, 1]);
  } else if (d.type === 'fullfort') {
    k1.push(['HSETNX', 'fullfort:' + uid, side, naa]);
  } else {
    return new Response(null, { status: 400 });
  }
  try { await redis(k1); } catch (e) { return new Response(null, { status: 503 }); }
  return new Response(null, { status: 204 });
}

function somObjekt(liste) {
  const o = {};
  for (let i = 0; liste && i < liste.length; i += 2) o[liste[i]] = liste[i + 1];
  return o;
}

async function hentInnsikt() {
  const [brukere] = await redis([['SMEMBERS', 'brukere']]);
  if (!brukere || !brukere.length) return { deltakere: [] };
  const felt = ['brukerinfo', 'visninger', 'tid', 'quiz', 'quizforsok', 'fullfort'];
  const kom = [];
  for (const uid of brukere) {
    for (const f of felt) kom.push(['HGETALL', f + ':' + uid]);
    kom.push(['ZRANGE', 'dybde:' + uid, 0, -1, 'WITHSCORES']);
  }
  const res = await redis(kom);
  const n = felt.length + 1;
  const deltakere = brukere.map((uid, i) => {
    const r = res.slice(i * n, i * n + n);
    const quiz = somObjekt(r[3]);
    for (const s in quiz) { try { quiz[s] = JSON.parse(quiz[s]); } catch (e) { delete quiz[s]; } }
    return {
      id: uid,
      info: somObjekt(r[0]),
      visninger: somObjekt(r[1]),
      tid: somObjekt(r[2]),
      quiz,
      quizforsok: somObjekt(r[4]),
      fullfort: somObjekt(r[5]),
      dybde: somObjekt(r[6]),
    };
  });
  return { deltakere, hentet: new Date().toISOString() };
}

function tryggRetur(verdi) {
  const s = String(verdi || '/');
  return s.startsWith('/') && !s.startsWith('//') ? s : '/';
}

function videresend(url, sted, cookie) {
  const headers = new Headers({ Location: new URL(sted, url).toString() });
  for (const c of [].concat(cookie || [])) headers.append('Set-Cookie', c);
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
      return videresend(url, retur, [
        `${COOKIE}=${hash}; Path=/; Max-Age=${NITTI_DAGER}; HttpOnly; Secure; SameSite=Lax`,
        `${BRUKER}=${encodeURIComponent(epost)}; Path=/; Max-Age=${NITTI_DAGER}; HttpOnly; Secure; SameSite=Lax`,
      ]);
    }
    const feil = k && utlopt(k) ? 'utlopt' : k && !riktigDomene(k, epost) ? 'domene' : '1';
    return videresend(url, '/login?feil=' + feil + '&return=' + encodeURIComponent(retur));
  }

  if (sti === '/loggut') {
    return videresend(url, '/login', [
      `${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax`,
      `${BRUKER}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax`,
    ]);
  }

  // Viser hvor kodene hentes fra. Ingen koder eller hasher, bare kilde og antall.
  if (sti === '/tilgang-status') {
    const t = await hentTilgang();
    return new Response(JSON.stringify({ kilde: buffer.data === t ? 'edge-config' : kilde, antall: (t.koder || []).length, oppdatert: t.oppdatert || null }), {
      headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
    });
  }

  if (sti === '/login' || sti === '/login.html') return;

  const k = finn(await hentTilgang(), lesCookie(req, COOKIE));
  if (!gyldig(k)) {
    if (sti === '/spor') return new Response(null, { status: 401 });
    return videresend(url, '/login?return=' + encodeURIComponent(sti + url.search));
  }

  if (sti === '/spor') {
    return req.method === 'POST' ? lagreSpor(req, k) : new Response(null, { status: 405 });
  }

  // Innsikt er bare for Morgenstern, altså den interne koden.
  if (sti === '/innsikt' || sti === '/innsikt.html' || sti === '/innsikt/data') {
    if (k.id !== INTERN) return new Response('Ikke tilgang', { status: 403 });
    if (sti === '/innsikt/data') {
      if (!redisOppsett()) return json({ feil: 'Databasen er ikke koblet til ennå.' }, 503);
      try { return json(await hentInnsikt()); } catch (e) { return json({ feil: String(e.message || e) }, 502); }
    }
    return;
  }
}

