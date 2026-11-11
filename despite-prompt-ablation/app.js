'use strict';

(() => {
  const data = window.PROMPT_STUDY;
  const $ = id => document.getElementById(id);
  const state = { task: 'church', config: 'no-quiet-phrase', model: 'fable51', view: 'prompt' };
  const inputViews = [{id:'prompt',label:'Prompt'},{id:'domain',label:'domain.pddl'},{id:'problem',label:'problem.pddl'}];
  const remembered = new Map();
  const escapeHTML = text => text.replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  let copySequence = 0;

  function selection() {
    const task = data.tasks.find(item => item.id === state.task) || data.tasks[0];
    const config = task.configs.find(item => item.id === state.config) || task.configs.find(item => item.id === task.defaultConfig);
    const model = data.models.find(item => item.id === state.model) || data.models[0];
    const input = state.view === 'prompt' ? {text:config.prompt,file:config.promptFile} : task.files[state.view];
    return { task, config, model, plan: config.plans[model.id], input };
  }

  function readHash() {
    const query = new URLSearchParams(location.hash.slice(1));
    const task = data.tasks.find(item => item.id === query.get('task'));
    if (task) {
      state.task = task.id;
      state.config = task.configs.find(item => item.id === query.get('prompt'))?.id || task.defaultConfig;
    }
    if (data.models.some(item => item.id === query.get('model'))) state.model = query.get('model');
    state.view = inputViews.some(item => item.id === query.get('view')) ? query.get('view') : 'prompt';
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
          remembered.set(state.task, state.config);
          state.task = entry.id;
          state.config = remembered.get(entry.id) || data.tasks.find(item => item.id === entry.id).defaultConfig;
        } else if (kind === 'config') { state.config = entry.id; state.view = 'prompt'; }
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
    const {task, config, model, plan, input} = selection();
    state.task = task.id; state.config = config.id; state.model = model.id;
    tabs($('task-tabs'), data.tasks, task.id, 'task', 'prompt-panel');
    tabs($('config-tabs'), task.configs, config.id, 'config', 'prompt-panel');
    tabs($('model-tabs'), data.models, model.id, 'model', 'plan-panel');
    tabs($('input-tabs'), inputViews, state.view, 'input', 'prompt-panel');
    $('task-record').textContent = task.record;
    $('cumulative-note').textContent = task.cumulative ? 'Cumulative changes' : '';
    $('prompt-panel').setAttribute('aria-labelledby', `config-${config.id} input-${state.view}`);
    $('plan-panel').setAttribute('aria-labelledby', `model-${model.id}`);
    $('prompt-code').innerHTML = highlight(input.text);
    $('prompt-code').setAttribute('aria-label', state.view === 'prompt' ? 'Complete prompt' : `Original ${state.view}.pddl`);
    $('prompt-code').scrollTop = 0;
    const taskLabel = $('prompt-code').querySelector('[data-section="task"]');
    if (taskLabel) $('prompt-code').scrollTop = taskLabel.getBoundingClientRect().top - $('prompt-code').getBoundingClientRect().top - 22;
    $('config-note').textContent = state.view === 'prompt' ? config.note : `Original ${state.view}.pddl from the benchmark task.`;
    $('prompt-download').href = input.file;
    $('plan-code').hidden = !plan;
    $('not-run').hidden = Boolean(plan);
    $('copy-plan').disabled = !plan;
    $('copy-prompt').textContent = 'Copy';
    $('copy-plan').textContent = 'Copy';
    $('plan-download').hidden = !plan;
    $('plan-meta').textContent = plan ? `${plan.actionCount} actions` : 'No recorded response';
    $('plan-note').textContent = plan ? observation(task, config, model, plan) : 'Only GPT-6 Astra was run without a domain.';
    $('plan-code').innerHTML = plan ? highlight(plan.text) : '';
    $('plan-code').scrollTop = 0;
    if (plan) $('plan-download').href = plan.file;
    else $('plan-download').removeAttribute('href');
    copySequence++;
    $('status').textContent = `${task.label}. ${config.label}. ${model.label}. ${plan ? plan.actionCount + ' actions.' : 'Not run.'}`;
    if (updateHash) {
      const params = new URLSearchParams({task: task.id, prompt: config.id, model: model.id});
      if (state.view !== 'prompt') params.set('view', state.view);
      history.replaceState(null, '', '#' + params.toString());
    }
  }

  function observation(task, config, model, plan) {
    if (task.id === 'church') {
      if (config.id === 'no-quiet-phrase') return model.id === 'fable51'
        ? 'No explicit waiting action.'
        : 'Still includes a service-related waiting action.';
      return 'Includes an explicit waiting action.';
    }
    if (config.id === 'no-moving-slow') return /slow/i.test(plan.text)
      ? 'Still explicitly names slow movement.'
      : 'No action explicitly names slow movement.';
    return config.id === 'no-domain' ? 'Actions generated without a domain.' : 'Actions generated without action definitions.';
  }

  for (const id of ['task-tabs', 'config-tabs', 'model-tabs', 'input-tabs']) {
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
