/* Reklameforståelse — progresjonssporing
 * Lagrer i localStorage, keyed per innlogget e-post (per enhet).
 */
(function () {
  'use strict';

  const USER_KEY = 'reklameforstaelse.user.email';
  const userEmail = localStorage.getItem(USER_KEY);
  const STORAGE_KEY = userEmail
    ? 'reklameforstaelse.v1.' + userEmail
    : 'reklameforstaelse.v1';
  const TOTAL_DAYS = 13;

  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { completed: [], checklists: {}, quizAnswers: {} };
      const parsed = JSON.parse(raw);
      return {
        completed: Array.isArray(parsed.completed) ? parsed.completed : [],
        checklists: parsed.checklists || {},
        quizAnswers: parsed.quizAnswers || {},
      };
    } catch (e) {
      return { completed: [], checklists: {}, quizAnswers: {} };
    }
  }

  function writeState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('Kunne ikke lagre progresjon:', e);
    }
  }

  function markDayComplete(day) {
    const state = readState();
    if (!state.completed.includes(day)) {
      state.completed.push(day);
      writeState(state);
    }
  }

  function nextDay() {
    const state = readState();
    for (let i = 1; i <= TOTAL_DAYS; i++) {
      if (!state.completed.includes(i)) return i;
    }
    return null; // alle ferdige
  }

  /* ---------- Forside: CTA og dag-status ---------- */
  function hydrateHome() {
    const state = readState();
    const next = nextDay();

    const primaryBtn = document.querySelector('[data-cta="primary"]');
    if (primaryBtn) {
      if (state.completed.length === 0) {
        primaryBtn.textContent = 'Start med økt 1 →';
        primaryBtn.href = 'dag-1.html';
      } else if (next) {
        primaryBtn.textContent = `Fortsett med økt ${next} →`;
        primaryBtn.href = `dag-${next}.html`;
      } else {
        primaryBtn.textContent = 'Åpne oppslagsverket →';
        primaryBtn.href = 'oppslag.html';
      }
    }

    // Marker ferdige dager i oversikten
    document.querySelectorAll('[data-day]').forEach((el) => {
      const day = parseInt(el.getAttribute('data-day'), 10);
      const status = el.querySelector('.status');
      if (state.completed.includes(day) && status) {
        status.textContent = 'ferdig';
        status.classList.add('done');
      }
    });

    // Progresjonstelling
    const progressText = document.querySelector('[data-progress-text]');
    if (progressText) {
      progressText.textContent = `${state.completed.length} av ${TOTAL_DAYS} økter fullført`;
    }
  }

  /* ---------- Dagsleksjon: progresjonsstripe, checklist, prøve, fullfør ---------- */
  function hydrateLesson() {
    const lesson = document.querySelector('[data-lesson-day]');
    if (!lesson) return;

    const currentDay = parseInt(lesson.getAttribute('data-lesson-day'), 10);
    const state = readState();

    // Progresjonsstripe
    const strip = document.querySelector('.progress-bar');
    if (strip) {
      strip.innerHTML = '';
      for (let i = 1; i <= TOTAL_DAYS; i++) {
        const dot = document.createElement('a');
        dot.className = 'progress-dot';
        dot.href = `dag-${i}.html`;
        dot.title = `Økt ${i}`;
        if (state.completed.includes(i)) dot.classList.add('done');
        if (i === currentDay) dot.classList.add('current');
        strip.appendChild(dot);
      }
    }

    // Sjekkliste — gjenopprett og lagre krysseringer
    const checklistKey = `day-${currentDay}`;
    const savedChecks = state.checklists[checklistKey] || {};
    document.querySelectorAll('.checklist input[type="checkbox"]').forEach((cb, idx) => {
      const key = cb.getAttribute('data-key') || `c${idx}`;
      if (savedChecks[key]) cb.checked = true;
      cb.addEventListener('change', () => {
        const current = readState();
        current.checklists[checklistKey] = current.checklists[checklistKey] || {};
        current.checklists[checklistKey][key] = cb.checked;
        writeState(current);
      });
    });

    // Prøve (multiple choice)
    hydrateQuiz(currentDay, state);

    // "Marker som fullført"-knapp
    const finishBtn = document.querySelector('[data-finish-day]');
    if (finishBtn) {
      if (state.completed.includes(currentDay)) {
        finishBtn.textContent = 'Ferdig ✓ — gå til neste';
        finishBtn.classList.add('done');
      }
      finishBtn.addEventListener('click', (e) => {
        e.preventDefault();
        markDayComplete(currentDay);
        const next = currentDay < TOTAL_DAYS ? currentDay + 1 : null;
        window.location.href = next ? `dag-${next}.html` : 'index.html';
      });
    }
  }

  /* ---------- Prøve (MC) ---------- */
  function hydrateQuiz(currentDay, state) {
    const quiz = document.querySelector('[data-quiz]');
    if (!quiz) return;

    const quizKey = `day-${currentDay}`;
    const items = Array.from(quiz.querySelectorAll('.quiz-item'));
    const submitBtn = quiz.querySelector('[data-quiz-submit]');
    const resetBtn = quiz.querySelector('[data-quiz-reset]');
    const resultEl = quiz.querySelector('[data-quiz-result]');

    // Gjenopprett tidligere svar
    const saved = state.quizAnswers[quizKey] || {};

    items.forEach((item) => {
      const q = item.getAttribute('data-question');
      const savedValue = saved[q];
      if (savedValue) {
        const input = item.querySelector(`input[value="${savedValue}"]`);
        if (input) input.checked = true;
      }

      // Lagre valg fortløpende (før retting)
      item.querySelectorAll('input[type="radio"]').forEach((inp) => {
        inp.addEventListener('change', () => {
          if (item.classList.contains('graded')) return; // lås etter retting
          const current = readState();
          current.quizAnswers[quizKey] = current.quizAnswers[quizKey] || {};
          current.quizAnswers[quizKey][q] = inp.value;
          writeState(current);
        });
      });
    });

    // Vis tidligere retting hvis den finnes
    if (saved.__graded) {
      gradeQuiz({ fromSave: true });
    }

    function gradeQuiz(opts = {}) {
      let correct = 0;
      let answered = 0;
      items.forEach((item) => {
        const q = item.getAttribute('data-question');
        const correctAnswer = item.getAttribute('data-correct');
        const chosen = item.querySelector('input[type="radio"]:checked');

        item.classList.add('graded');
        // Lås inputs
        item.querySelectorAll('input[type="radio"]').forEach((inp) => {
          inp.disabled = true;
        });

        if (chosen) {
          answered++;
          const isCorrect = chosen.value === correctAnswer;
          if (isCorrect) correct++;
          // Marker valgt option
          const chosenLabel = chosen.closest('label');
          if (chosenLabel) chosenLabel.classList.add(isCorrect ? 'is-correct' : 'is-wrong');
        }

        // Marker alltid korrekt option
        const correctInput = item.querySelector(`input[value="${correctAnswer}"]`);
        if (correctInput) {
          const correctLabel = correctInput.closest('label');
          if (correctLabel) correctLabel.classList.add('is-answer');
        }

        // Vis forklaring
        const expl = item.querySelector('.quiz-explanation');
        if (expl) expl.classList.add('visible');
      });

      // Resultatboks
      if (resultEl) {
        resultEl.hidden = false;
        const pct = items.length > 0 ? Math.round((correct / items.length) * 100) : 0;
        resultEl.innerHTML =
          `<strong>${correct} av ${items.length} riktige</strong> ` +
          `<span class="quiz-result-pct">(${pct}%)</span>` +
          `<p class="quiz-result-note">Les forklaringene nedenfor. Du kan ta prøven på nytt om du vil.</p>`;
        resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      if (submitBtn) submitBtn.hidden = true;
      if (resetBtn) resetBtn.hidden = false;

      if (!opts.fromSave) {
        const current = readState();
        current.quizAnswers[quizKey] = current.quizAnswers[quizKey] || {};
        current.quizAnswers[quizKey].__graded = true;
        current.quizAnswers[quizKey].__score = correct;
        current.quizAnswers[quizKey].__total = items.length;
        writeState(current);
      }
    }

    function resetQuiz() {
      items.forEach((item) => {
        item.classList.remove('graded');
        item.querySelectorAll('input[type="radio"]').forEach((inp) => {
          inp.disabled = false;
          inp.checked = false;
        });
        item.querySelectorAll('label').forEach((l) => {
          l.classList.remove('is-correct', 'is-wrong', 'is-answer');
        });
        const expl = item.querySelector('.quiz-explanation');
        if (expl) expl.classList.remove('visible');
      });
      if (resultEl) {
        resultEl.hidden = true;
        resultEl.innerHTML = '';
      }
      if (submitBtn) submitBtn.hidden = false;
      if (resetBtn) resetBtn.hidden = true;

      const current = readState();
      delete current.quizAnswers[quizKey];
      writeState(current);
    }

    if (submitBtn) {
      submitBtn.addEventListener('click', () => {
        // Krev at alle er besvart
        const unanswered = items.filter((item) => !item.querySelector('input[type="radio"]:checked'));
        if (unanswered.length > 0) {
          if (resultEl) {
            resultEl.hidden = false;
            resultEl.innerHTML = `<em>Svar på alle ${items.length} spørsmålene før du retter.</em>`;
          }
          return;
        }
        gradeQuiz();
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', resetQuiz);
    }
  }

  /* ---------- Footer: vis innlogget e-post + logg ut ---------- */
  function hydrateUserStrip() {
    const emailEl = document.querySelector('[data-user-email]');
    if (emailEl && userEmail) emailEl.textContent = userEmail;

    const logoutEl = document.querySelector('[data-logout]');
    if (logoutEl) {
      logoutEl.addEventListener('click', (e) => {
        e.preventDefault();
        try {
          localStorage.removeItem(USER_KEY);
        } catch (err) { /* ignore */ }
        window.location.href = 'login.html';
      });
    }
  }

  /* ---------- Init ---------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      hydrateHome();
      hydrateLesson();
      hydrateUserStrip();
    });
  } else {
    hydrateHome();
    hydrateLesson();
    hydrateUserStrip();
  }

  // Eksporter for debug og eksport-funksjon senere
  window.Reklamekurs = { readState, writeState, markDayComplete, nextDay };
})();
