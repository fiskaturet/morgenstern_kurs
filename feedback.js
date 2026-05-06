/* Reklameforståelse — feedback widget
 * Marker tekst på siden -> liten knapp dukker opp -> popup -> sender forslag til Anders via Formspree.
 * Krever ingen avhengigheter. Selvdrevet (injiserer egen CSS).
 *
 * Slik konfigurerer du:
 *   1) Opprett gratis konto på formspree.io
 *   2) New form -> kall den "Reklameforståelse — forslag" -> get endpoint URL
 *   3) Bytt ut FORMSPREE_ENDPOINT under
 */
(function () {
  'use strict';

  // ============================================================
  // Konfigurasjon
  // ============================================================
  const FORMSPREE_ENDPOINT = 'https://formspree.io/f/xdabgyja';
  const MIN_SELECTION_LENGTH = 5;       // ignorer veldig korte markeringer
  const STORAGE_KEY_NAME = 'reklameforstaelse.feedback.name';
  const STORAGE_KEY_EMAIL = 'reklameforstaelse.feedback.email';

  // ============================================================
  // CSS — injisert ved oppstart
  // ============================================================
  const css = `
  .rf-fb-trigger {
    position: absolute;
    z-index: 9998;
    transform: translate(-50%, 8px);
    background: var(--part-color, #DD6B6E);
    color: #fff;
    border: none;
    padding: 0.5rem 0.85rem;
    font-family: 'Sohne', -apple-system, system-ui, sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.01em;
    border-radius: 999px;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(0,0,0,0.18), 0 1px 3px rgba(0,0,0,0.10);
    opacity: 0;
    pointer-events: none;
    transition: opacity 140ms ease, transform 140ms ease;
    white-space: nowrap;
  }
  .rf-fb-trigger.is-visible {
    opacity: 1;
    pointer-events: auto;
    transform: translate(-50%, 14px);
  }
  .rf-fb-trigger:hover { filter: brightness(0.95); }
  .rf-fb-trigger:focus-visible { outline: 2px solid #1A1A1A; outline-offset: 2px; }

  .rf-fb-overlay {
    position: fixed;
    inset: 0;
    background: rgba(26, 26, 26, 0.45);
    z-index: 9999;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    animation: rf-fb-fade 140ms ease;
  }
  .rf-fb-overlay.is-open { display: flex; }
  @keyframes rf-fb-fade { from { opacity: 0; } to { opacity: 1; } }

  .rf-fb-modal {
    background: #fff;
    color: #1A1A1A;
    width: 100%;
    max-width: 32rem;
    border-radius: 4px;
    border: 1px solid #E8E4DC;
    box-shadow: 0 24px 64px rgba(0,0,0,0.25);
    font-family: 'Sohne', -apple-system, system-ui, sans-serif;
    overflow: hidden;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
  }
  .rf-fb-header {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid #E8E4DC;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }
  .rf-fb-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.01em;
  }
  .rf-fb-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    line-height: 1;
    color: #5A5A5A;
    cursor: pointer;
    padding: 0;
    width: 1.75rem;
    height: 1.75rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
  }
  .rf-fb-close:hover { background: #F5F1E8; color: #1A1A1A; }

  .rf-fb-body {
    padding: 1.25rem;
    overflow-y: auto;
  }
  .rf-fb-quote {
    background: var(--part-soft, rgba(221, 107, 110, 0.12));
    border-left: 3px solid var(--part-color, #DD6B6E);
    padding: 0.75rem 1rem;
    margin: 0 0 1.25rem;
    font-style: italic;
    font-size: 0.92rem;
    line-height: 1.5;
    color: #1A1A1A;
    max-height: 8rem;
    overflow-y: auto;
  }
  .rf-fb-quote::before { content: "\\201C"; margin-right: 0.1em; }
  .rf-fb-quote::after  { content: "\\201D"; margin-left: 0.1em; }

  .rf-fb-field { margin-bottom: 1rem; }
  .rf-fb-label {
    display: block;
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #5A5A5A;
    margin-bottom: 0.4rem;
  }
  .rf-fb-input,
  .rf-fb-textarea {
    width: 100%;
    font-family: inherit;
    font-size: 0.95rem;
    padding: 0.6rem 0.75rem;
    border: 1px solid #E8E4DC;
    border-radius: 3px;
    background: #fff;
    color: #1A1A1A;
    line-height: 1.5;
  }
  .rf-fb-input:focus,
  .rf-fb-textarea:focus {
    outline: none;
    border-color: var(--part-color, #DD6B6E);
    box-shadow: 0 0 0 3px var(--part-soft, rgba(221, 107, 110, 0.18));
  }
  .rf-fb-textarea {
    min-height: 6rem;
    resize: vertical;
  }
  .rf-fb-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  @media (max-width: 480px) { .rf-fb-row { grid-template-columns: 1fr; } }

  .rf-fb-footer {
    padding: 1rem 1.25rem;
    border-top: 1px solid #E8E4DC;
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    background: #FBFAF7;
  }
  .rf-fb-btn {
    font-family: inherit;
    font-size: 0.92rem;
    font-weight: 500;
    padding: 0.55rem 1.1rem;
    border-radius: 3px;
    border: 1px solid transparent;
    cursor: pointer;
    transition: filter 120ms ease;
  }
  .rf-fb-btn-secondary {
    background: transparent;
    color: #1A1A1A;
    border-color: #E8E4DC;
  }
  .rf-fb-btn-secondary:hover { background: #F5F1E8; }
  .rf-fb-btn-primary {
    background: #1A1A1A;
    color: #fff;
  }
  .rf-fb-btn-primary:hover { filter: brightness(1.15); }
  .rf-fb-btn-primary:disabled {
    background: #B5B5B5;
    cursor: not-allowed;
  }

  .rf-fb-status {
    padding: 1.25rem;
    text-align: center;
    font-size: 0.95rem;
  }
  .rf-fb-status .rf-fb-icon {
    display: block;
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }
  .rf-fb-status-success { color: #2E7D43; }
  .rf-fb-status-error { color: #C03030; }

  .rf-fb-hint {
    font-size: 0.78rem;
    color: #5A5A5A;
    margin: 0 0 1rem;
    line-height: 1.45;
  }
  `;

  function injectCSS() {
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ============================================================
  // DOM-bygging
  // ============================================================
  let triggerBtn, overlay, modal, quoteEl, commentEl, nameEl, emailEl, submitBtn, bodyEl, footerEl;
  let currentSelection = '';

  function buildDOM() {
    // Den flytende «Foreslå endring»-knappen
    triggerBtn = document.createElement('button');
    triggerBtn.className = 'rf-fb-trigger';
    triggerBtn.type = 'button';
    triggerBtn.innerHTML = '💬 Foreslå endring';
    triggerBtn.setAttribute('aria-label', 'Foreslå endring til markert tekst');
    document.body.appendChild(triggerBtn);

    // Modal
    overlay = document.createElement('div');
    overlay.className = 'rf-fb-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'rf-fb-title');
    overlay.innerHTML = `
      <div class="rf-fb-modal">
        <div class="rf-fb-header">
          <h2 class="rf-fb-title" id="rf-fb-title">Foreslå endring</h2>
          <button class="rf-fb-close" type="button" aria-label="Lukk">×</button>
        </div>
        <div class="rf-fb-body">
          <p class="rf-fb-hint">Du har markert dette stykket. Skriv en kort kommentar — f.eks. «dette skulle jeg gjerne fått bedre forklart», «typo her» eller «mistenker at kilden er feil». Forslaget sendes til Anders.</p>
          <blockquote class="rf-fb-quote" id="rf-fb-quote"></blockquote>
          <div class="rf-fb-field">
            <label class="rf-fb-label" for="rf-fb-comment">Din kommentar</label>
            <textarea class="rf-fb-textarea" id="rf-fb-comment" required maxlength="2000" placeholder="Hva tenker du om dette stykket?"></textarea>
          </div>
          <div class="rf-fb-row">
            <div class="rf-fb-field">
              <label class="rf-fb-label" for="rf-fb-name">Navn (valgfritt)</label>
              <input class="rf-fb-input" id="rf-fb-name" type="text" maxlength="120" autocomplete="name">
            </div>
            <div class="rf-fb-field">
              <label class="rf-fb-label" for="rf-fb-email">E-post (valgfritt)</label>
              <input class="rf-fb-input" id="rf-fb-email" type="email" maxlength="200" autocomplete="email">
            </div>
          </div>
        </div>
        <div class="rf-fb-footer">
          <button class="rf-fb-btn rf-fb-btn-secondary" type="button" data-action="cancel">Avbryt</button>
          <button class="rf-fb-btn rf-fb-btn-primary" type="button" data-action="submit">Send forslag</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    quoteEl = overlay.querySelector('#rf-fb-quote');
    commentEl = overlay.querySelector('#rf-fb-comment');
    nameEl = overlay.querySelector('#rf-fb-name');
    emailEl = overlay.querySelector('#rf-fb-email');
    submitBtn = overlay.querySelector('[data-action="submit"]');
    bodyEl = overlay.querySelector('.rf-fb-body');
    footerEl = overlay.querySelector('.rf-fb-footer');
  }

  // ============================================================
  // Selection-handling
  // ============================================================
  function isInsideWidget(node) {
    if (!node) return false;
    const el = node.nodeType === 1 ? node : node.parentElement;
    if (!el) return false;
    return !!el.closest('.rf-fb-overlay, .rf-fb-trigger, header.topbar, footer.site-footer, nav, button, input, textarea, a.btn');
  }

  function getSelectionInfo() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
    const text = sel.toString().trim();
    if (text.length < MIN_SELECTION_LENGTH) return null;
    const range = sel.getRangeAt(0);
    if (isInsideWidget(range.startContainer) || isInsideWidget(range.endContainer)) return null;
    const rect = range.getBoundingClientRect();
    if (!rect || (rect.width === 0 && rect.height === 0)) return null;
    return { text, rect };
  }

  function showTrigger(info) {
    const x = info.rect.left + info.rect.width / 2 + window.scrollX;
    const y = info.rect.bottom + window.scrollY;
    triggerBtn.style.left = x + 'px';
    triggerBtn.style.top = y + 'px';
    triggerBtn.classList.add('is-visible');
    currentSelection = info.text;
  }

  function hideTrigger() {
    triggerBtn.classList.remove('is-visible');
  }

  // ============================================================
  // Modal-handling
  // ============================================================
  function openModal() {
    quoteEl.textContent = currentSelection;
    commentEl.value = '';
    // Pre-fill navn/epost: foretrekk innlogget e-post, fall tilbake til husket
    try {
      nameEl.value = localStorage.getItem(STORAGE_KEY_NAME) || '';
      var loggedIn = localStorage.getItem('reklameforstaelse.user.email');
      emailEl.value = loggedIn || localStorage.getItem(STORAGE_KEY_EMAIL) || '';
    } catch (e) { /* ignore */ }
    overlay.classList.add('is-open');
    setTimeout(() => commentEl.focus(), 50);
    hideTrigger();
  }

  function closeModal() {
    overlay.classList.remove('is-open');
    // Tilbakestill kropp/footer hvis vi har vist en status
    bodyEl.style.display = '';
    footerEl.style.display = '';
    const status = overlay.querySelector('.rf-fb-status');
    if (status) status.remove();
  }

  function showStatus(type, message) {
    bodyEl.style.display = 'none';
    footerEl.style.display = 'none';
    const old = overlay.querySelector('.rf-fb-status');
    if (old) old.remove();
    const status = document.createElement('div');
    status.className = 'rf-fb-status rf-fb-status-' + type;
    status.innerHTML = `
      <span class="rf-fb-icon">${type === 'success' ? '✓' : '⚠'}</span>
      <div>${message}</div>
      <div style="margin-top: 1rem;">
        <button class="rf-fb-btn rf-fb-btn-secondary" type="button" data-action="cancel">Lukk</button>
      </div>
    `;
    overlay.querySelector('.rf-fb-modal').appendChild(status);
    status.querySelector('[data-action="cancel"]').addEventListener('click', closeModal);
  }

  async function submitFeedback() {
    const comment = commentEl.value.trim();
    if (!comment) {
      commentEl.focus();
      commentEl.style.borderColor = '#C03030';
      setTimeout(() => { commentEl.style.borderColor = ''; }, 1500);
      return;
    }

    const name = nameEl.value.trim();
    const email = emailEl.value.trim();

    // Husk navn og e-post lokalt
    try {
      if (name) localStorage.setItem(STORAGE_KEY_NAME, name); else localStorage.removeItem(STORAGE_KEY_NAME);
      if (email) localStorage.setItem(STORAGE_KEY_EMAIL, email); else localStorage.removeItem(STORAGE_KEY_EMAIL);
    } catch (e) { /* ignore */ }

    submitBtn.disabled = true;
    const originalLabel = submitBtn.textContent;
    submitBtn.textContent = 'Sender …';

    const payload = {
      side: document.title,
      url: window.location.href,
      markert_tekst: currentSelection,
      kommentar: comment,
      navn: name || '(ikke oppgitt)',
      _replyto: email || '',
      tidspunkt: new Date().toISOString()
    };

    try {
      if (FORMSPREE_ENDPOINT.includes('DITT_ENDEPUNKT_HER')) {
        // Demo-modus: ingen ekte sending
        await new Promise(r => setTimeout(r, 600));
        console.log('[feedback] Ville sendt:', payload);
        showStatus('success', 'Demo-modus: forslaget ble logget i konsollen, ikke sendt. Sett opp Formspree-endepunkt for å sende på ekte.');
        return;
      }

      const res = await fetch(FORMSPREE_ENDPOINT, {
        method: 'POST',
        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        showStatus('success', 'Takk! Forslaget er sendt til Anders.');
      } else {
        const data = await res.json().catch(() => ({}));
        const msg = (data && data.errors && data.errors[0] && data.errors[0].message) || ('HTTP ' + res.status);
        showStatus('error', 'Klarte ikke å sende: ' + msg + '. Send heller en e-post til anders@mrgn.no.');
      }
    } catch (err) {
      showStatus('error', 'Klarte ikke å sende. Sjekk nettforbindelsen, eller send heller en e-post til anders@mrgn.no.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
    }
  }

  // ============================================================
  // Event-binding
  // ============================================================
  function bindEvents() {
    // Vis triggeren etter at brukeren har sluppet musen / fingeren
    document.addEventListener('mouseup', () => {
      setTimeout(() => {
        const info = getSelectionInfo();
        if (info) showTrigger(info); else hideTrigger();
      }, 10);
    });

    document.addEventListener('selectionchange', () => {
      // Hvis seleksjonen blir tom, skjul triggeren
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || sel.toString().trim().length < MIN_SELECTION_LENGTH) {
        hideTrigger();
      }
    });

    // Skjul triggeren ved scroll/resize for å unngå at den blir hengende feil sted
    window.addEventListener('scroll', hideTrigger, { passive: true });
    window.addEventListener('resize', hideTrigger);

    // Trigger åpner modal
    triggerBtn.addEventListener('mousedown', (e) => {
      // Ikke la mousedown rive vekk seleksjonen vår før vi har lest den
      e.preventDefault();
    });
    triggerBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openModal();
    });

    // Modal-knapper
    overlay.querySelector('.rf-fb-close').addEventListener('click', closeModal);
    overlay.querySelector('[data-action="cancel"]').addEventListener('click', closeModal);
    overlay.querySelector('[data-action="submit"]').addEventListener('click', submitFeedback);

    // Klikk utenfor modal lukker
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });

    // Esc lukker
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.classList.contains('is-open')) closeModal();
    });

    // Cmd/Ctrl+Enter sender
    commentEl.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        submitFeedback();
      }
    });
  }

  // ============================================================
  // Init
  // ============================================================
  function init() {
    if (document.body.dataset.feedbackInit === '1') return;
    document.body.dataset.feedbackInit = '1';
    injectCSS();
    buildDOM();
    bindEvents();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
