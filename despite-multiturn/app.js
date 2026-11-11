'use strict';

(() => {
  const $ = id => document.getElementById(id);
  const state = { scene: 'medication', subject: 0, view: 'explore', model: 'astra', file: 'prompt', cursor: 0 };
  const cache = new Map();
  const explorations = new Map();
  const expanded = { explore: new Set(), runs: new Set() };
  const mobile = window.matchMedia('(max-width: 760px)');
  const fileViews = [
    { id: 'prompt', label: 'Initial prompt' }, { id: 'domain', label: 'domain.pddl' },
    { id: 'problem', label: 'problem.pddl' }, { id: 'questions', label: 'Question bank' },
  ];
  let manifest, groundTruth, scene, timer = null, loadSequence = 0, downloadURL = null;

  function element(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function button(text, className, handler) {
    const el = element('button', className, text);
    el.type = 'button';
    if (handler) el.addEventListener('click', handler);
    return el;
  }

  function announce(text) { $('announcement').textContent = text; }
  function subject() { return scene.subjects[state.subject]; }
  function run() { return subject().runs[state.model]; }
  function exploration() {
    const key = `${scene.id}:${subject().id}`;
    if (!explorations.has(key)) explorations.set(key, { asked: [], choice: null });
    return explorations.get(key);
  }
  function mask(asked) { return scene.public.questions.reduce((v, q, i) => v | (asked.includes(q.id) ? 1 << i : 0), 0); }
  function evidence(encoding, branch) {
    if (branch === null) return { text: 'Not evaluated', tone: '' };
    if (encoding & (1 << branch)) return { text: 'Supported', tone: 'good' };
    if (encoding & (1 << (branch + 2))) return { text: 'Rules not met', tone: 'bad' };
    return { text: 'Missing facts', tone: 'unknown' };
  }

  function tabs(container, entries, active, kind, panel, onSelect) {
    container.replaceChildren();
    entries.forEach(entry => {
      const el = button(entry.label, '', () => onSelect(entry.id));
      el.id = `${kind}-${entry.id}`;
      el.dataset.id = entry.id;
      el.setAttribute('role', 'tab');
      el.setAttribute('aria-selected', String(entry.id === active));
      el.setAttribute('aria-controls', panel);
      el.tabIndex = entry.id === active ? 0 : -1;
      container.append(el);
    });
  }

  function restoreFocus(id) { if (id && $(id) && !$(id).disabled) $(id).focus({ preventScroll: true }); }

  function stopPlayback() {
    if (timer !== null) clearInterval(timer);
    timer = null;
  }

  function updateURL() {
    const query = new URLSearchParams({ scene: state.scene, subject: String(state.subject + 1), view: state.view });
    if (state.view === 'runs') query.set('model', state.model);
    if (state.view === 'files') query.set('file', state.file);
    history.replaceState(null, '', `#${query}`);
  }

  function readURL() {
    const query = new URLSearchParams(location.hash.slice(1));
    const selected = manifest.scenes.find(s => s.id === query.get('scene')) || manifest.scenes[0];
    state.scene = selected.id;
    const n = Number(query.get('subject'));
    state.subject = Number.isInteger(n) && n >= 1 && n <= selected.subjects ? n - 1 : 0;
    state.view = ['explore', 'runs', 'files'].includes(query.get('view')) ? query.get('view') : 'explore';
    state.model = selected.models.includes(query.get('model')) ? query.get('model') : selected.models[0];
    state.file = fileViews.some(v => v.id === query.get('file')) ? query.get('file') : 'prompt';
    state.cursor = 0;
  }

  async function loadScene(focusId) {
    stopPlayback();
    expanded.explore.clear(); expanded.runs.clear();
    const sequence = ++loadSequence;
    const selected = manifest.scenes.find(s => s.id === state.scene);
    $('workspace').setAttribute('aria-busy', 'true');
    $('workspace').inert = true;
    $('error').hidden = true;
    $('loading').hidden = false;
    tabs($('scene-tabs'), manifest.scenes, state.scene, 'scene', 'workspace', id => {
      if (id === state.scene && scene?.id === id) return;
      state.scene = id; state.subject = 0; state.cursor = 0;
      if (mobile.matches) $('scenario-picker').open = false;
      loadScene(`scene-${id}`);
    });
    try {
      if (!cache.has(selected.id)) {
        cache.set(selected.id, fetch(selected.file).then(r => {
          if (!r.ok) throw new Error('Scenario unavailable');
          return r.json();
        }).catch(e => { cache.delete(selected.id); throw e; }));
      }
      const loaded = await cache.get(selected.id);
      if (sequence !== loadSequence) return;
      scene = loaded;
      if (!scene.models.includes(state.model)) state.model = scene.models[0];
      state.subject = Math.min(state.subject, scene.subjects.length - 1);
      state.cursor = 0;
      $('workspace').hidden = false;
      $('workspace').inert = false;
      $('workspace').setAttribute('aria-busy', 'false');
      $('loading').hidden = true;
      renderScene();
      updateURL();
      if (mobile.matches && focusId?.startsWith('scene-')) $('scenario-picker').querySelector('summary').focus({ preventScroll: true });
      else restoreFocus(focusId);
    } catch (e) {
      if (sequence !== loadSequence) return;
      $('workspace').hidden = true;
      $('loading').hidden = true;
      $('error').hidden = false;
    }
  }

  function selectSubject(index, focusId) {
    if (index < 0 || index >= scene.subjects.length) return;
    stopPlayback(); state.subject = index; state.cursor = 0;
    expanded.explore.clear(); expanded.runs.clear();
    renderScene(); updateURL(); restoreFocus(focusId);
  }

  function renderScene() {
    $('scene-title').textContent = scene.label;
    $('subject-name').textContent = `${scene.subjectLabel} ${String(state.subject + 1).padStart(2, '0')}`;
    $('previous-subject').disabled = state.subject === 0;
    $('next-subject').disabled = state.subject === scene.subjects.length - 1;
    const subjects = scene.subjects.map((s, i) => ({ id: String(i), label: String(i + 1).padStart(2, '0') }));
    tabs($('subject-tabs'), subjects, String(state.subject), 'subject', 'explore-panel', id => selectSubject(Number(id), `subject-${id}`));
    [...$('subject-tabs').children].forEach((el, i) => el.setAttribute('aria-label', `${scene.subjectLabel} ${i + 1}`));
    $('setting').textContent = scene.public.setting;
    $('request').textContent = scene.public.request;
    renderViews();
    renderGroundTruth();
  }

  function renderViews() {
    ['explore', 'runs', 'files'].forEach(view => {
      const selected = state.view === view;
      $(`view-${view}`).setAttribute('aria-selected', String(selected));
      $(`view-${view}`).tabIndex = selected ? 0 : -1;
      $(`${view}-panel`).hidden = !selected;
    });
    if (state.view === 'explore') renderExplore();
    if (state.view === 'runs') renderRun();
    if (state.view === 'files') renderFiles();
  }

  function emptyAnswers(container) {
    const empty = element('div', 'empty-answer');
    // Decorative only. All experiment text is inserted with textContent.
    empty.innerHTML = '<svg viewBox="0 0 60 60" aria-hidden="true"><path d="M10 12h40v28H30L18 49v-9h-8z" stroke-linejoin="round"/><path d="M20 23h20M20 31h13" stroke-linecap="round"/></svg>';
    empty.append(element('span', 'sr-only', 'Select a question to reveal its answer.'));
    container.append(empty);
  }

  function questionItem(q, asked, count, mode, handler) {
    const open = expanded[mode].has(q.id);
    const id = `${mode === 'explore' ? 'question' : 'replay-question'}-${q.id}`;
    const row = element('div', 'question-row');
    const el = button(undefined, 'question', () => handler(!open));
    el.id = id;
    el.append(element('span', 'question-id', q.id), element('span', '', q.text));
    const mark = element('span', 'question-asked', asked ? (count > 1 ? `×${count}` : '✓') : '');
    mark.setAttribute('aria-hidden', 'true');
    const toggle = element('span', 'question-mark', open ? '−' : '+');
    toggle.setAttribute('aria-hidden', 'true');
    el.append(mark, toggle);
    el.dataset.asked = String(asked);
    el.setAttribute('aria-expanded', String(open));
    el.setAttribute('aria-controls', `${id}-answer`);
    el.setAttribute('aria-label', `${q.id}: ${q.text}${asked ? (mode === 'runs' ? ' Asked by model.' : ' Included in your evidence.') : ''}`);
    const answer = element('p', 'question-answer', subject().answers[q.id]);
    answer.id = `${id}-answer`;
    answer.hidden = !open;
    row.append(el, answer);
    return row;
  }

  function answerItem(qid, answer, id) {
    const q = scene.public.questions.find(q => q.id === qid);
    const article = element('article', 'answer');
    if (id) article.id = id;
    const heading = element('p', 'answer-q');
    heading.append(element('code', '', qid), element('span', '', q.text));
    article.append(heading, element('p', 'answer-text', answer));
    return article;
  }

  function results(container, outcome, proof) {
    container.replaceChildren();
    for (const [label, value] of [['Rule check', outcome], ['Evidence', proof]]) {
      const item = element('div', 'result-item');
      item.append(element('h4', '', label));
      const badge = element('span', 'badge', value.text);
      badge.dataset.tone = value.tone;
      item.append(badge); container.append(item);
    }
  }

  function renderExplore() {
    const local = exploration();
    const locked = local.choice !== null;
    $('question-count').textContent = `${local.asked.length} / ${scene.public.questions.length}`;
    $('question-list').replaceChildren();
    scene.public.questions.forEach(q => {
      const row = questionItem(q, local.asked.includes(q.id), 1, 'explore', open => {
        if (open) expanded.explore.add(q.id); else expanded.explore.delete(q.id);
        if (open && !locked && !local.asked.includes(q.id)) local.asked.push(q.id);
        renderExplore(); restoreFocus(`question-${q.id}`);
        announce(`${q.id} ${open ? 'expanded' : 'collapsed'}.`);
      });
      $('question-list').append(row);
    });
    $('answer-list').replaceChildren();
    if (!local.asked.length) emptyAnswers($('answer-list'));
    local.asked.forEach(qid => $('answer-list').append(answerItem(qid, subject().answers[qid], `answer-${qid}`)));
    $('choice-list').replaceChildren();
    scene.public.branches.forEach((branch, i) => {
      const choice = button(undefined, 'choice', () => {
        local.choice = i;
        renderExplore();
        const safe = subject().safeBranches.includes(i);
        announce(`${safe ? 'No rule violation' : 'Rule violation'}. ${evidence(subject().evidence[mask(local.asked)], i).text}.`);
        $('manual-plan').focus({ preventScroll: true });
      });
      choice.id = `choice-${i}`;
      choice.append(element('span', '', branch.finish.text), element('span', '', '→'));
      choice.setAttribute('aria-pressed', String(local.choice === i));
      choice.disabled = locked;
      $('choice-list').append(choice);
    });
    $('decision-panel').hidden = !locked;
    $('decision-panel').parentElement.classList.toggle('has-decision', locked);
    if (locked) {
      const branch = scene.public.branches[local.choice];
      $('manual-plan').textContent = [scene.public.approach, branch.prepare, branch.finish].map(a => `(${a.id})`).join('\n');
      const safe = subject().safeBranches.includes(local.choice);
      results($('manual-result'), { text: safe ? 'No violation' : 'Rule violation', tone: safe ? 'good' : 'bad' }, evidence(subject().evidence[mask(local.asked)], local.choice));
    }
  }

  function renderRun() {
    tabs($('model-tabs'), manifest.models.filter(m => scene.models.includes(m.id)), state.model, 'model', 'runs-panel', id => {
      stopPlayback(); state.model = id; state.cursor = 0; expanded.runs.clear(); renderRun(); updateURL(); restoreFocus(`model-${id}`);
    });
    const recorded = run();
    const events = recorded.events.slice(0, state.cursor);
    const asked = events.filter(e => e.type === 'question').map(e => e.questionId);
    $('replay-questions').replaceChildren();
    scene.public.questions.forEach(q => $('replay-questions').append(questionItem(q, asked.includes(q.id), asked.filter(id => id === q.id).length, 'runs', open => {
      if (open) expanded.runs.add(q.id); else expanded.runs.delete(q.id);
      renderRun(); restoreFocus(`replay-question-${q.id}`);
      announce(`${q.id} ${open ? 'expanded' : 'collapsed'}.`);
    })));
    $('replay-progress').textContent = `${state.cursor} / ${recorded.events.length}`;
    $('replay-events').replaceChildren();
    if (!events.length) emptyAnswers($('replay-events'));
    events.forEach((event, index) => {
      if (event.type === 'question') {
        $('replay-events').append(answerItem(event.questionId, event.answer, `event-${index}`));
      } else {
        const output = element('article', 'recorded-response');
        if (event.type === 'limit') output.append(element('p', 'stop-label', 'Turn limit reached'));
        else if (!event.raw) output.append(element('p', 'stop-label', 'No final text'));
        else {
          output.append(element('h4', '', recorded.decision.kind === 'plan' ? 'Plan' : 'Response'));
          const pre = element('pre', '', event.raw); pre.id = 'recorded-plan'; pre.tabIndex = 0; output.append(pre);
        }
        $('replay-events').append(output);
      }
    });
    const done = state.cursor >= recorded.events.length;
    $('run-result').hidden = !done;
    if (done) {
      const outcome = recorded.violation ? { text: 'Rule violation', tone: 'bad' } : recorded.safe ? { text: 'No violation', tone: 'good' } : { text: 'No plan', tone: 'unknown' };
      results($('run-result'), outcome, evidence(recorded.evidence, recorded.branch));
    }
    $('play-run').textContent = timer !== null ? 'Pause' : done ? 'Replay' : 'Play';
    $('step-run').disabled = done;
    $('finish-run').disabled = done;
    $('restart-run').disabled = state.cursor === 0;
  }

  function advance() {
    state.cursor = Math.min(state.cursor + 1, run().events.length);
    if (state.cursor === run().events.length) stopPlayback();
    renderRun();
    announce(`Recorded turn ${state.cursor} of ${run().events.length}.`);
  }

  function combination(qids) {
    const group = element('span', 'question-combination');
    qids.forEach((qid, i) => {
      if (i) group.append(element('span', 'combination-plus', '+'));
      const code = element('code', '', qid);
      code.title = scene.public.questions.find(q => q.id === qid).text;
      group.append(code);
    });
    return group;
  }

  function renderGroundTruth() {
    const truth = groundTruth[scene.id];
    const current = truth.subjects[state.subject];
    $('ground-truth-subject').textContent = $('subject-name').textContent;
    const questions = $('ground-truth-questions');
    questions.replaceChildren();
    const relevant = element('div', 'truth-question-group');
    relevant.append(element('span', '', 'Relevant questions'), combination(truth.relevantQuestions));
    const distractor = element('div', 'truth-question-group');
    distractor.append(element('span', '', 'Distractor'), combination([truth.distractor]));
    questions.append(relevant, distractor);
    const cards = $('ground-truth-branches');
    cards.replaceChildren();
    truth.branches.forEach((branch, i) => {
      const outcome = current.branches[i];
      const card = element('article', 'truth-card');
      card.dataset.branch = String(i);
      const heading = element('div', 'truth-heading');
      const status = element('span', 'badge', outcome.ruleMet ? 'Rule met' : 'Rule not met');
      status.dataset.tone = outcome.ruleMet ? 'good' : 'bad';
      heading.append(element('h3', '', branch.label), status);
      const sets = element('div', 'truth-combinations');
      if (!outcome.combinations.length) {
        sets.append(element('span', 'missing-combination', 'No available combination'));
        if (current.unavailableQuestions.length) sets.append(element('span', 'unavailable-question', `${current.unavailableQuestions.join(', ')} unavailable`));
      } else if (outcome.combinations.some(qids => qids.length === 0)) {
        sets.append(element('span', '', 'No questions required by this rule'));
      } else {
        outcome.combinations.forEach((qids, j) => {
          if (j) sets.append(element('span', 'combination-or', 'or'));
          sets.append(combination(qids));
        });
      }
      const fact = element('p', 'truth-fact');
      fact.append(element('strong', '', 'Fact '), document.createTextNode(branch.fact));
      card.append(heading, element('h4', 'truth-combinations-title', 'Sufficient question sets'), sets, fact);
      cards.append(card);
    });
  }

  function fileText() {
    if (state.file === 'prompt') return scene.initialPrompt;
    if (state.file === 'domain' || state.file === 'problem') return scene[state.file];
    return scene.public.questions.map(q => `${q.id}: ${q.text}\n${subject().answers[q.id]}`).join('\n\n');
  }

  function renderFiles() {
    tabs($('file-tabs'), fileViews, state.file, 'file', 'files-panel', id => {
      state.file = id; renderFiles(); updateURL(); restoreFocus(`file-${id}`);
    });
    const text = fileText();
    $('file-content').textContent = text;
    $('copy-file').textContent = 'Copy';
    if (downloadURL) URL.revokeObjectURL(downloadURL);
    downloadURL = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
    $('download-file').href = downloadURL;
    $('download-file').download = `${scene.id}-${state.file === 'questions' ? subject().id + '-questions.txt' : state.file === 'prompt' ? 'initial-prompt.txt' : state.file + '.pddl'}`;
  }

  document.addEventListener('keydown', event => {
    const tab = event.target.closest('[role="tab"]');
    if (!tab || !['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    const list = [...tab.parentElement.querySelectorAll('[role="tab"]')];
    let index = list.indexOf(tab);
    if (event.key === 'Home') index = 0;
    else if (event.key === 'End') index = list.length - 1;
    else index = (index + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + list.length) % list.length;
    event.preventDefault();
    const id = list[index].id; list[index].click(); restoreFocus(id);
  });
  $('view-tabs').addEventListener('click', event => {
    const tab = event.target.closest('[data-view]');
    if (!tab || !scene) return;
    stopPlayback(); state.view = tab.dataset.view; renderViews(); updateURL();
  });
  $('previous-subject').addEventListener('click', () => selectSubject(state.subject - 1, 'previous-subject'));
  $('next-subject').addEventListener('click', () => selectSubject(state.subject + 1, 'next-subject'));
  $('reset-explore').addEventListener('click', () => {
    const local = exploration(); local.asked = []; local.choice = null; expanded.explore.clear(); renderExplore(); announce('Questions and plan reset.');
  });
  $('play-run').addEventListener('click', () => {
    if (timer !== null) { stopPlayback(); renderRun(); return; }
    if (state.cursor >= run().events.length) state.cursor = 0;
    timer = setInterval(advance, 1300); advance();
  });
  $('step-run').addEventListener('click', () => { stopPlayback(); advance(); });
  $('finish-run').addEventListener('click', () => { stopPlayback(); state.cursor = run().events.length; renderRun(); announce('Complete recorded conversation shown.'); });
  $('restart-run').addEventListener('click', () => { stopPlayback(); state.cursor = 0; renderRun(); });
  $('copy-file').addEventListener('click', async () => {
    const current = fileText();
    try {
      await navigator.clipboard.writeText(current);
      if (current === fileText()) $('copy-file').textContent = 'Copied';
      announce('Copied to clipboard.');
    } catch { announce('Copy is unavailable. Use Download.'); }
  });
  $('retry').addEventListener('click', () => manifest ? loadScene() : initialize());
  window.addEventListener('hashchange', () => { if (manifest) { readURL(); loadScene(); } });
  document.addEventListener('visibilitychange', () => { if (document.hidden && timer !== null) { stopPlayback(); renderRun(); } });
  mobile.addEventListener('change', event => { $('scenario-picker').open = !event.matches; });
  async function initialize() {
    $('workspace').hidden = true;
    $('scenario-picker').open = !mobile.matches;
    try {
      [manifest, groundTruth] = await Promise.all(['manifest.json', 'ground-truth.json'].map(async file => {
        const response = await fetch(file);
        if (!response.ok) throw new Error('Dataset unavailable');
        return response.json();
      }));
      if (manifest.scenes.length !== 20 || manifest.counts.subjects !== 115) throw new Error('Unexpected dataset');
      readURL(); await loadScene();
    } catch { $('loading').hidden = true; $('error').hidden = false; }
  }
  initialize();
})();
