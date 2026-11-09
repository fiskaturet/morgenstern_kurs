/* Reklameforståelse — lesesporing
 * Sender små hendelser til /spor, som lagrer dem per deltaker:
 *  - at siden ble åpnet
 *  - hvor langt ned på siden deltakeren kom (høyeste prosent)
 *  - hvor mange sekunder siden var aktiv i forgrunnen
 *  - svarene på prøven når den rettes, og når en økt markeres som fullført
 * Innloggingen avgjør hvem deltakeren er. For dem som logget inn før sporingen kom,
 * sender skriptet e-posten innloggingssiden lagret i nettleseren.
 */
(function () {
  'use strict';
  if (!window.fetch) return;

  var sti = location.pathname.replace(/\.html$/, '').replace(/^\/+|\/+$/g, '');
  var side = sti === '' ? 'forside' : sti;
  if (!/^(forside|dag-\d{1,2}|hele-kurset|oppslag)$/.test(side)) return;

  var epost = '';
  try { epost = localStorage.getItem('reklameforstaelse.user.email') || ''; } catch (e) {}

  var maxDybde = 0, sekunder = 0, sendtSek = 0, sendtDybde = -1, sistAktiv = Date.now();

  function send(data, beacon) {
    data.side = side;
    if (epost) data.epost = epost;
    var body = JSON.stringify(data);
    try {
      if (beacon && navigator.sendBeacon) {
        navigator.sendBeacon('/spor', new Blob([body], { type: 'text/plain' }));
        return;
      }
      fetch('/spor', { method: 'POST', body: body, headers: { 'content-type': 'text/plain' }, keepalive: true, credentials: 'same-origin' }).catch(function () {});
    } catch (e) { /* sporing skal aldri stoppe siden */ }
  }

  function dybde() {
    var doc = document.documentElement;
    var hoyde = Math.max(doc.scrollHeight, document.body ? document.body.scrollHeight : 0);
    var synlig = window.innerHeight || doc.clientHeight;
    if (hoyde <= synlig) return 100;
    var bunn = (window.scrollY || doc.scrollTop) + synlig;
    return Math.max(0, Math.min(100, Math.round(bunn / hoyde * 100)));
  }

  // Teller bare tid når fanen er synlig og deltakeren har gjort noe de siste to minuttene.
  ['scroll', 'mousemove', 'keydown', 'touchstart', 'click'].forEach(function (ev) {
    window.addEventListener(ev, function () { sistAktiv = Date.now(); }, { passive: true });
  });
  window.addEventListener('scroll', function () { var d = dybde(); if (d > maxDybde) maxDybde = d; }, { passive: true });
  setInterval(function () {
    if (document.visibilityState === 'visible' && Date.now() - sistAktiv < 120000) sekunder += 5;
  }, 5000);

  function flush(beacon) {
    var d = Math.max(maxDybde, dybde());
    var nySek = sekunder - sendtSek;
    if (nySek <= 0 && d <= sendtDybde) return;
    send({ type: 'les', dybde: d, sek: Math.min(nySek, 1800) }, beacon);
    sendtSek = sekunder; sendtDybde = d;
  }

  send({ type: 'vis' });
  setTimeout(function () { maxDybde = Math.max(maxDybde, dybde()); }, 1500);
  setInterval(function () { flush(false); }, 30000);
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') flush(true); });
  window.addEventListener('pagehide', function () { flush(true); });

  // Prøven: les svarene i det deltakeren trykker «Se resultat».
  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest ? e.target : null;
    if (!t) return;
    var knapp = t.closest('[data-quiz-submit]');
    if (knapp) {
      var svar = [];
      document.querySelectorAll('[data-quiz] .quiz-item').forEach(function (item, i) {
        var valgt = item.querySelector('input[type="radio"]:checked');
        svar.push({
          q: item.getAttribute('data-question') || String(i + 1),
          valgt: valgt ? valgt.value : '',
          riktig: item.getAttribute('data-correct') || ''
        });
      });
      if (svar.length) send({ type: 'quiz', svar: svar.slice(0, 20) });
      return;
    }
    if (t.closest('[data-finish-day]')) send({ type: 'fullfort' }, true);
  });
})();
