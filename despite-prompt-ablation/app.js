'use strict';

(() => {
  const data = window.PROMPT_STUDY;
  const $ = id => document.getElementById(id);
  const state = { task: 'church', config: 'own-declarations', experiment: 'own-actions', model: 'fable51', view: 'diff' };
  const inputViews = [{id:'diff',label:'Diff'},{id:'prompt',label:'Full prompt'},{id:'domain',label:'domain.pddl'},{id:'problem',label:'problem.pddl'}];
  const remembered = new Map();
  const escapeHTML = text => text.replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  let copySequence = 0;

  function selection() {
    const task = data.tasks.find(item => item.id === state.task) || data.tasks[0];
    const experiment = task.experiments?.find(item => item.id === state.experiment) || task.experiments?.[0];
    const configs = experiment ? task.configs.filter(item => experiment.configIds.includes(item.id)) : task.configs;
    const config = configs.find(item => item.id === state.config) || configs.find(item => item.id === (experiment?.defaultConfig || task.defaultConfig));
    const model = data.models.find(item => item.id === state.model) || data.models[0];
    const input = state.view === 'diff'
      ? {text:config.diffText || config.prompt,file:config.diffFile || config.promptFile}
      : state.view === 'prompt' ? {text:config.prompt,file:config.promptFile} : task.files[state.view];
    return { task, experiment, configs, config, model, plan: config.plans[model.id], input };
  }

  function readHash() {
    const query = new URLSearchParams(location.hash.slice(1));
    const task = data.tasks.find(item => item.id === query.get('task'));
    if (task) {
      state.task = task.id;
      state.config = task.configs.find(item => item.id === query.get('prompt'))?.id || task.defaultConfig;
      const requested = task.experiments?.find(item => item.id === query.get('experiment') && item.configIds.includes(state.config));
      state.experiment = (requested || task.experiments?.find(item => item.configIds.includes(state.config)))?.id || 'original';
    }
    if (data.models.some(item => item.id === query.get('model'))) state.model = query.get('model');
    state.view = inputViews.some(item => item.id === query.get('view')) ? query.get('view')
      : state.config === 'full-benchmark' ? 'prompt' : 'diff';
  }

  function tabs(container, entries, active, kind, panel) {
    container.replaceChildren();
    entries.forEach(entry => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = entry.label;
      button.id = `${kind}-${entry.id}`;
      button.dataset.id = entry.id;
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-selected', String(entry.id === active));
      button.setAttribute('aria-controls', panel);
      button.tabIndex = entry.id === active ? 0 : -1;
      if (kind === 'model') {
        const available = Boolean(selection().config.plans[entry.id]);
        button.dataset.available = available;
        if (!available) button.setAttribute('aria-label', `${entry.label}, not run`);
      }
      button.addEventListener('click', () => {
        if (kind === 'task') {
          remembered.set(state.task, {config: state.config, experiment: state.experiment});
          state.task = entry.id;
          state.config = remembered.get(entry.id)?.config || data.tasks.find(item => item.id === entry.id).defaultConfig;
          state.experiment = remembered.get(entry.id)?.experiment || data.tasks.find(item => item.id === entry.id).experiments?.[0]?.id || 'original';
        } else if (kind === 'experiment') {
          const condition = state.config.replace(/^(classic-|own-)/, '');
          state.experiment = entry.id;
          state.config = entry.configIds.find(id => id.replace(/^(classic-|own-)/, '') === condition) || entry.defaultConfig;
          state.view = 'diff';
        } else if (kind === 'config') { state.config = entry.id; state.view = entry.id === 'full-benchmark' ? 'prompt' : 'diff'; }
        else if (kind === 'input') state.view = entry.id;
        else state.model = entry.id;
        const focus = button.id;
        render(true);
        $(focus)?.focus({ preventScroll: true });
      });
      container.append(button);
    });
  }

  function highlight(text) {
    return text.split('\n').map(line => {
      const escaped = escapeHTML(line);
      if (/^(Task|Domain|Problem):$/.test(line)) return `<span class="prompt-label" data-section="${line.slice(0, -1).toLowerCase()}">${escaped}</span>`;
      return escaped.replace(/(:[a-z][a-z-]*)(?=[\s)])/g, '<span class="pddl-keyword">$1</span>')
        .replace(/\(([a-z][a-z_0-9-]*)(?=[\s)])/g, '(<span class="pddl-action">$1</span>');
    }).join('\n');
  }

  function render(updateHash = false) {
    const {task, experiment, configs, config, model, plan, input} = selection();
    state.task = task.id; state.config = config.id; state.model = model.id;
    if (experiment) state.experiment = experiment.id;
    tabs($('task-tabs'), data.tasks, task.id, 'task', 'prompt-panel');
    $('experiment-tabs').hidden = !experiment;
    tabs($('experiment-tabs'), task.experiments || [], experiment?.id, 'experiment', 'prompt-panel');
    tabs($('config-tabs'), configs, config.id, 'config', 'prompt-panel');
    tabs($('model-tabs'), data.models, model.id, 'model', 'plan-panel');
    tabs($('input-tabs'), inputViews, state.view, 'input', 'prompt-panel');
    $('task-record').textContent = task.record;
    $('cumulative-note').textContent = config.samePromptAs ? 'Independent repeat' : task.cumulative && config.id !== 'full-benchmark' ? 'Cumulative changes' : '';
    $('prompt-panel').setAttribute('aria-labelledby', `config-${config.id} input-${state.view}`);
    $('plan-panel').setAttribute('aria-labelledby', `model-${model.id}`);
    $('prompt-code').innerHTML = state.view === 'diff' ? config.promptDiff.map(segment => {
      if (segment.kind === 'equal') return `<span class="diff-equal">${highlight(segment.text)}</span>`;
      const tag = segment.kind === 'delete' ? 'del' : 'ins';
      return `<${tag} class="diff-${segment.kind}" aria-label="${segment.kind === 'delete' ? 'Removed' : 'Added'}">${escapeHTML(segment.text)}</${tag}>`;
    }).join('') : highlight(input.text);
    $('prompt-code').setAttribute('aria-label', state.view === 'diff' ? 'Changes from the full benchmark prompt' : state.view === 'prompt' ? 'Complete prompt' : `Original ${state.view}.pddl`);
    $('diff-key').hidden = state.view !== 'diff';
    $('prompt-code').scrollTop = 0;
    $('prompt-download').href = input.file;
    $('plan-code').hidden = !plan;
    $('not-run').hidden = Boolean(plan);
    $('copy-plan').disabled = !plan;
    $('copy-prompt').textContent = 'Copy';
    $('copy-plan').textContent = 'Copy';
    $('plan-download').hidden = !plan;
    const responseLabels = {no_plan:'No plan returned',empty_code_block:'Empty code block',conditional_example:'Conditional example'};
    $('plan-meta').textContent = plan ? (responseLabels[plan.responseKind] || (plan.text.trim() ? `${plan.actionCount} actions` : 'Empty final response')) : 'No recorded response';
    $('plan-code').innerHTML = plan ? highlight(plan.text) : '';
    $('plan-code').scrollTop = 0;
    if (plan) $('plan-download').href = plan.file;
    else $('plan-download').removeAttribute('href');
    copySequence++;
    $('status').textContent = `${task.label}. ${config.label}. ${model.label}. ${$('plan-meta').textContent}.`;
    const findings = experiment?.findings || [
      {title:'Actions removed',text:'All four models generate their own action sequences.'},
      {title:'Without moving_slow',text:'Fable 5.1 and 5.2 no longer explicitly name slow movement.'},
      {title:'Retained precaution',text:'GPT-6 Astra and Opus 5.5 still explicitly slow down.'}
    ];
    $('finding-grid').innerHTML = findings.map(item => `<article><h3>${escapeHTML(item.title)}</h3><p>${escapeHTML(item.text)}</p></article>`).join('');
    if (updateHash) {
      const params = new URLSearchParams({task: task.id, prompt: config.id, model: model.id});
      params.set('view', state.view);
      if (experiment) params.set('experiment', experiment.id);
      history.replaceState(null, '', '#' + params.toString());
    }
  }

  for (const id of ['task-tabs', 'experiment-tabs', 'config-tabs', 'model-tabs', 'input-tabs']) {
    $(id).addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
      const buttons = [...$(id).querySelectorAll('button')];
      const current = buttons.indexOf(document.activeElement);
      if (current < 0) return;
      event.preventDefault();
      const offset = ['ArrowRight','ArrowDown'].includes(event.key) ? 1 : -1;
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (current + offset + buttons.length) % buttons.length;
      buttons[next].click();
    });
  }

  async function copy(kind) {
    const current = selection();
    const text = kind === 'prompt' ? current.input.text : current.plan?.text;
    if (!text) return;
    const button = $(`copy-${kind}`);
    const sequence = ++copySequence;
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else {
        const field = document.createElement('textarea');
        field.value = text; field.style.position = 'fixed'; field.style.opacity = '0';
        document.body.append(field); field.select();
        const copied = document.execCommand('copy');
        field.remove(); button.focus();
        if (!copied) throw new Error('Clipboard unavailable');
      }
      if (sequence !== copySequence) return;
      button.textContent = 'Copied';
      $('status').textContent = `${kind === 'prompt' ? 'Prompt' : 'Plan'} copied.`;
      setTimeout(() => { if (sequence === copySequence) button.textContent = 'Copy'; }, 1600);
    } catch {
      if (sequence !== copySequence) return;
      button.textContent = 'Use download';
      $('status').textContent = 'Clipboard unavailable. Use the download link.';
    }
  }
  $('copy-prompt').addEventListener('click', () => copy('prompt'));
  $('copy-plan').addEventListener('click', () => copy('plan'));
  window.addEventListener('hashchange', () => { readHash(); render(); });
  readHash();
  render();
})();
