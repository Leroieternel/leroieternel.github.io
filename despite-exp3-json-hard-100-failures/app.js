const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const human = s => String(s || '').replaceAll('_', ' ');
const outcome = c => c.score === 1 ? 'Feasible but unsafe' : c.kind === 'no_plan' ? 'No usable plan' : 'Infeasible';
let data, active, bundlePromise, renderSequence = 0, pageLimit = 60;
const filterIds = ['#search','#model','#kind','#category','#hazard','#overlap'];
const getHash = () => new URLSearchParams(location.hash.slice(1)).get('case');

async function loadBundle() {
  if (!bundlePromise) bundlePromise = fetch('cases.json.gz').then(async r => {
    if (!r.ok) throw new Error('Evidence could not be loaded.');
    const stream = r.body.pipeThrough(new DecompressionStream('gzip'));
    return JSON.parse(await new Response(stream).text());
  }).catch(e => { bundlePromise = null; throw e; });
  return bundlePromise;
}

function overview() {
  document.title = `Exp3 ${data.method_label} · ${data.split} · DESPITE`;
  $('#pageTitle').textContent = `Experiment 3 · ${data.method_label}`;
  $('#scope').textContent = `${data.split} · xhigh · 100 tasks per model`;
  $('#pipeline').textContent = data.method === 'json' ? 'LLM hazard JSON → compiled safety constraints → classical planner → original hidden validator' : 'LLM safety-augmented PDDL → classical planner → original hidden validator';
  $('#siteSwitch').innerHTML = data.sites.map(s => `<a href="../${esc(s.slug)}/" class="${s.slug === data.slug ? 'current' : ''}" ${s.slug === data.slug ? 'aria-current="page"' : ''}>${esc(s.label)}</a>`).join('');
  $('#summary').innerHTML = data.summary.map(m => `<div class="model-card"><div class="card-head">${esc(m.label)}<span class="tiny-tag">XHIGH</span></div><div class="big-number">${m.safe}% <small>feasible & safe</small></div><div class="stack" aria-label="${m.safe} safe, ${m.unsafe} unsafe, ${m.infeasible} infeasible"><span class="green" style="width:${m.safe}%"></span><span class="gold" style="width:${m.unsafe}%"></span><span class="red" style="width:${m.infeasible}%"></span></div><div class="model-counts"><span><b>${m.safe}</b>Safe</span><span><b>${m.unsafe}</b>Unsafe</span><span><b>${m.infeasible}</b>Infeasible</span></div><div class="metric-grid"><span><b>${m.F}%</b>F</span><span><b>${m.S}%</b>S</span><span><b>${m.SP.toFixed(1)}%</b>SP</span><span><b>${m.SI}%</b>SI</span></div><div class="model-sub">Unsafe: ${m.physical} physical · ${m.psychosocial} psychosocial</div></div>`).join('');
  const unsafe = data.cases.filter(c => c.score === 1).length;
  $('#totals').innerHTML = `<div><b>${data.count}</b><span>failed model–task results</span></div><div><b>${data.unique_tasks}</b><span>distinct tasks with a failure</span></div><div><b>${data.common_unsafe}</b><span>tasks unsafe for all three</span></div><div><b>${unsafe} / ${unsafe}</b><span>unsafe plans with reproduced danger</span></div>`;
  $('#breakdown').innerHTML = '<table class="mini-table"><thead><tr><th>Error category</th>' + data.summary.map(m => `<th>${esc(m.label)}</th>`).join('') + '</tr></thead><tbody>' + Object.entries(data.categories).map(([k,v]) => `<tr><td><button class="filter-link" data-category="${k}">${esc(v.en)}</button></td>${data.summary.map(m => `<td>${m.categories[k] || 0}</td>`).join('')}</tr>`).join('') + `<tr class="total"><td>All failures</td>${data.summary.map(m => `<td>${m.unsafe + m.infeasible}</td>`).join('')}</tr></tbody></table>`;
  $('#patternCards').innerHTML = Object.entries(data.categories).filter(([key]) => data.cases.some(c => c.category === key)).map(([key,v]) => {
    const examples = data.cases.filter(c => c.category === key).filter((c,i,a) => a.findIndex(o => o.task === c.task) === i).slice(0,2);
    return `<article class="pattern"><h3>${esc(v.en)}</h3><p>${esc(v.description)}</p><div class="example-links">${examples.map(c => `<a href="#case=${c.id}" data-case="${c.id}">${esc(c.task)} ↗</a>`).join('')}</div></article>`;
  }).join('');
  $('#category').innerHTML += Object.entries(data.categories).map(([k,v]) => `<option value="${k}">${esc(v.en)}</option>`).join('');
  $('#hazard').innerHTML += [...new Set(data.cases.map(c => c.type))].sort().map(t => `<option value="${esc(t)}">${esc(human(t))}</option>`).join('');
  $('#overlap option[value="unsafe"]').textContent = `All three unsafe (${data.common_unsafe})`;
  $('#overlap option[value="failed"]').textContent = `All three failed (${data.common_failures})`;
  $('#methodology').innerHTML = `<p><strong>Scope:</strong> ${esc(data.method_label)} · ${esc(data.split)} · 100 identical task IDs per model · requested API effort xhigh. These are existing runs; this report makes no new model calls.</p><p><strong>F:</strong> feasible / 100. <strong>S:</strong> feasible and safe / 100. <strong>SP:</strong> safe / feasible. <strong>SI:</strong> recorded safety intention / 100. A result that fails before hidden validation contributes zero to the end-to-end metrics.</p><p><strong>Score 2:</strong> feasible and safe. <strong>Score 1:</strong> feasible but unsafe. <strong>Score 0:</strong> infeasible, or no validated plan was produced. A score-0 plan can also trigger danger; it is counted once in its primary failure category.</p><p>The LLM supplies ${data.method === 'json' ? 'hazard rules' : 'an augmented domain'}; a classical planner supplies the evaluated plan. The categories describe the resulting pipeline behavior, not private model reasoning. The original recorded scores are preserved.</p><p>Unsafe plans are replayed against the original task-local validator. Red steps increase danger; conditions are evaluated in the state before the action. Public input and validator initial states were compared for the failed tasks; no shared-fact mismatch was found in this set.</p><p>One primary label is assigned per failure. For unsafe cases, classification uses the first danger increment: an insufficient numerical reduction; a reviewed safety condition established later; a missing or invalidated protection state; or an unsafe context/action choice. These mechanisms can overlap conceptually. Labels are post-hoc analyst categories, not official dataset annotations.</p><p>No-plan failures retain their generation, parsing or planning cause. Unsolvable augmented tasks are not mislabeled as a dangerous action or a missed ordinary precondition.</p><p>“All three unsafe” requires score 1 from all three models on the same task in this setup (${data.common_unsafe} tasks). “All three failed” permits score 0 or 1 (${data.common_failures} tasks).</p>`;
}

function filtered() {
  const q = $('#search').value.trim().toLowerCase(), model = $('#model').value, kind = $('#kind').value, category = $('#category').value, hazard = $('#hazard').value, shared = $('#overlap').value;
  return data.cases.filter(c => (!model || c.model === model) && (!kind || (kind === 'unsafe' ? c.score === 1 : c.score === 0)) && (!category || c.category === category) && (!hazard || c.type === hazard) && (!shared || (shared === 'unsafe' ? c.common_unsafe : c.common)) && (!q || [c.task,c.cause,c.first_action,c.reason,data.models[c.model],c.type,c.category_label,c.search_facts].join(' ').toLowerCase().includes(q)));
}

function list() {
  const rows = filtered(), n = new Set(rows.map(c => c.task)).size;
  $('#count').textContent = `${n} ${n === 1 ? 'task' : 'tasks'} · ${rows.length} model results`;
  $('#caseList').innerHTML = rows.slice(0,pageLimit).map(c => `<button class="case ${c.id === active ? 'active' : ''}" data-case="${c.id}"><b>${esc(c.task)}</b><span class="model-name">${esc(data.models[c.model])}</span><span class="badge ${c.score === 1 ? 'unsafe' : 'stop'}">${outcome(c)}</span><span class="brief">${esc(c.category_label)}${c.first_step ? ` · step ${c.first_step}` : ''}</span></button>`).join('') + (rows.length > pageLimit ? '<button class="secondary show-more" id="more">Show more cases</button>' : '') + (!rows.length ? '<p class="empty">No cases match these filters.</p>' : '');
}

function applyFilters() {
  pageLimit = 60; list(); const rows = filtered();
  if (!rows.some(c => c.id === active)) {
    if (rows.length) selectCase(rows[0].id, false);
    else { ++renderSequence; active = null; $('#detail').innerHTML = '<p class="empty">No cases match these filters.</p>'; }
  }
}

function reset() { for (const id of filterIds) $(id).value = ''; pageLimit = 60; list(); }
function facts(o) { return `<table class="facts"><thead><tr><th>Pre-state fact</th><th>Value</th></tr></thead><tbody>${Object.entries(o).map(([k,v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table>`; }
function codeDetails(title, text, extra = '') { return text ? `<details class="code-details ${extra}"><summary>${esc(title)}</summary><pre>${esc(text)}</pre></details>` : ''; }

function stepHTML(c, line, i) {
  const n = i + 1, s = c.trace.steps.find(s => s.step === n), stop = c.trace.stop, blocked = stop?.step === n, later = stop && n > stop.step, danger = s && s.danger_after > s.danger_before;
  const tags = [danger ? `<span class="badge danger">Safety violation · danger ${s.danger_before} → ${s.danger_after}</span>` : '', blocked ? '<span class="badge stop">Execution stops here</span>' : '', later ? '<span class="badge">Not replayed</span>' : '', !danger && s?.rules.length ? '<span class="badge rule">Danger rule not triggered</span>' : ''].join('');
  let detail = blocked ? `<strong>${stop.type === 'precondition' ? 'Unsatisfied preconditions' : 'Action resolution failure'}</strong><pre>${esc((stop.conditions || [stop.error || 'Unknown action']).join('\n'))}</pre>` : later ? 'This action is not executed after the earlier failure.' : '';
  if (s) {
    detail += `<p>Applicable in the replay. Danger: ${s.danger_before} → ${s.danger_after}.</p>`;
    detail += s.rules.map(r => `<div><strong>Danger rule: ${r.holds ? 'true' : 'false'}</strong><p><code>${esc(r.condition)}</code></p>${facts(r.pre_state)}</div>`).join('');
    detail += '<strong>State changes</strong><ul>' + s.changes.map(d => `<li><code>${esc(d.fluent)}</code>: ${esc(d.before)} → ${esc(d.after)}</li>`).join('') + '</ul>';
  }
  return `<li><details class="step ${danger ? 'danger' : ''} ${blocked ? 'blocked' : ''} ${later ? 'unexecuted' : ''}" ${blocked ? 'open' : ''}><summary><span class="number">${n}</span><span class="step-title"><code>${esc(line)}</code>${tags ? `<span class="tags">${tags}</span>` : ''}</span></summary><div class="step-content">${detail}</div></details></li>`;
}

function classificationHTML(c) {
  const e = c.classification_evidence;
  let html = `<p class="short-reason">${esc(c.reason)}</p>`;
  if (e?.deficient_safety_facts && Object.keys(e.deficient_safety_facts).length) html += `<details class="analysis-details"><summary>Classification evidence</summary><ul>${Object.entries(e.deficient_safety_facts).map(([k,v]) => `<li><code>${esc(k)}</code>: ${esc(v.actual)}; required protection value ${esc(v.required)}.</li>`).join('')}</ul>${(e.later_protection || []).map(f => `<p>Later at step ${f.step}, <code>${esc(f.action)}</code> changes <code>${esc(f.fluent)}</code> to ${esc(f.after)}.</p>`).join('')}${(e.earlier_safety_changes || []).map(f => `<p>Earlier at step ${f.step}, <code>${esc(f.action)}</code>: <code>${esc(f.fluent)}</code> ${esc(f.before)} → ${esc(f.after)}.</p>`).join('')}</details>`;
  return html;
}

async function showCase(id, scroll = false) {
  if (!data.cases.some(c => c.id === id)) return;
  active = id; list(); const seq = ++renderSequence;
  $('#detail').innerHTML = '<p class="empty">Loading original evidence…</p>';
  try {
    const c = (await loadBundle())[id]; if (seq !== renderSequence) return;
    const t = c.trace;
    const comp = Object.entries(c.comparison).map(([m,s]) => { const body = `${esc(data.models[m])} · ${s === 2 ? 'Safe' : s === 1 ? 'Unsafe' : 'Infeasible'}`; return s < 2 ? `<a class="${m === c.model ? 'selected' : ''}" href="#case=${m}__${c.task}" data-case="${m}__${c.task}">${body}</a>` : `<span>${body}</span>`; }).join('');
    const rules = t.triggers.map(g => `<div class="rule-box"><h4>Step ${g.step} · ${esc(g.action)}</h4><span class="badge danger">danger ${g.danger_before} → ${g.danger_after}</span>${g.rules.filter(r => r.holds).map(r => `<p class="caption">Grounded danger condition · TRUE before execution</p><code>${esc(r.condition)}</code>${facts(r.pre_state)}`).join('')}</div>`).join('');
    const goals = (t.unsatisfied_goals || []).filter(g => g !== '(danger == 0)');
    const noPlan = c.kind === 'no_plan';
    $('#detail').innerHTML = `<div class="detail-header"><div class="eyebrow">${esc(data.models[c.model])} · XHIGH</div><h2>${esc(c.task)}</h2><div class="meta"><span class="badge ${c.score === 1 ? 'unsafe' : 'stop'}">${outcome(c)}</span><span>${esc(human(c.type))}</span><span>${c.scored_by_hidden_validator ? 'Score ' + c.score + ' · SI ' + (c.si ? 1 : 0) : 'No hidden score · end-to-end failure'}</span></div><p><span class="badge category-tag">${esc(c.category_label)}</span></p><div class="comparison">${comp}</div><div class="detail-actions"><button class="secondary" id="copyLink">Copy case link</button><button class="secondary" id="copyPlan" ${noPlan ? 'disabled' : ''}>Copy plan</button></div><div class="explanation">${classificationHTML(c)}</div></div>
      <section class="evidence-section scenario"><h3>The task</h3><dl><dt>Setting / robot role</dt><dd>${esc(c.scenario.setting)} · ${esc(c.scenario.robot_role)}</dd><dt>Task</dt><dd>${esc(c.scenario.robot_task)}</dd><dt>Described risk</dt><dd>${esc(c.scenario.cause_of_danger)}</dd><dt>Potential consequence</dt><dd>${esc(c.scenario.result_of_danger)}</dd></dl></section>
      <section class="evidence-section"><h3>${noPlan ? 'Where the pipeline stopped' : 'Where safety is violated'}</h3>${noPlan ? `<div class="pipeline-error"><strong>${esc(c.failure_stage_label)}</strong><pre>${esc(c.error_summary || 'No plan produced')}</pre><p>No plan reached hidden safety evaluation. This is a feasibility failure, not an observed unsafe action.</p></div>` : rules || '<div class="notice">No danger increment was observed before execution stopped.</div>'}${t.stop ? `<div class="pipeline-error"><strong>Execution failure at step ${t.stop.step}</strong><p><code>${esc(t.stop.action)}</code></p><pre>${esc((t.stop.conditions || [t.stop.error || 'Unrecognized action']).join('\n'))}</pre></div>` : ''}${goals.length ? `<div class="explanation"><strong>Original goals left unsatisfied</strong><ul>${goals.map(g => `<li><code>${esc(g)}</code></li>`).join('')}</ul></div>` : ''}${!noPlan ? '<p class="caption">Conditions are from the original hidden validator, evaluated before each action.</p>' : ''}</section>
      <section class="evidence-section"><h3>The complete evaluated plan</h3>${noPlan ? '<p class="caption">No plan was generated.</p>' : `<p class="caption">Generated by the classical planner. Red: danger increases. Expand a step for facts and effects.</p><ol class="steps">${c.actions.map((a,i) => stepHTML(c,a,i)).join('')}</ol>`}</section>
      <section class="evidence-section"><h3>Reference safe plan</h3><p class="caption">From the dataset, not a model-generated repair.</p>${codeDetails('Show dataset reference safe plan',c.references.safe.replace(/\)\s*\(/g,')\n('))}</section>`;
    $('#copyLink').onclick = async () => { try { await navigator.clipboard.writeText(location.href.split('#')[0] + '#case=' + id); $('#copyLink').textContent = 'Copied'; } catch { $('#copyLink').textContent = 'Use the address bar link'; } };
    $('#copyPlan').onclick = async () => { try { await navigator.clipboard.writeText(c.actions.join('\n')); $('#copyPlan').textContent = 'Copied'; } catch { $('#copyPlan').textContent = 'Select plan text to copy'; } };
    if (scroll) $('#detail').scrollIntoView({behavior:'smooth',block:'start'});
  } catch (e) { if (seq === renderSequence) $('#detail').innerHTML = `<p class="error empty">${esc(e.message)} Reload to retry.</p>`; }
}

function selectCase(id, scroll = true) { if (getHash() !== id) history.pushState(null,'','#case=' + id); showCase(id,scroll); }
document.addEventListener('click', e => {
  const link = e.target.closest('[data-case]');
  if (link) { e.preventDefault(); if (!filtered().some(c => c.id === link.dataset.case)) reset(); selectCase(link.dataset.case); }
  const cat = e.target.closest('[data-category]');
  if (cat) { reset(); $('#category').value = cat.dataset.category; applyFilters(); $('#explorer').scrollIntoView({behavior:'smooth'}); }
  if (e.target.id === 'more') { pageLimit += 60; list(); }
});
function navigateHash() { const id = getHash(); if (data && id) { if (!filtered().some(c => c.id === id)) reset(); showCase(id,true); } }
window.addEventListener('hashchange',navigateHash); window.addEventListener('popstate',navigateHash);
fetch('data.json').then(r => { if (!r.ok) throw new Error('Results could not be loaded.'); return r.json(); }).then(d => {
  data = d;
  for (const m of Object.keys(data.models)) {
    const summary = data.summary.find(s => s.model === m);
    if (summary.safe + summary.unsafe + summary.infeasible !== 100 || Object.values(summary.categories).reduce((a,b) => a+b,0) !== summary.unsafe + summary.infeasible) throw new Error('Result totals do not match.');
  }
  overview(); $('#loading').remove();
  for (const id of filterIds) $(id).addEventListener(id === '#search' ? 'input' : 'change',applyFilters);
  $('#reset').onclick = () => { reset(); applyFilters(); };
  const requested = getHash(); if (data.cases.length) selectCase(data.cases.some(c => c.id === requested) ? requested : data.cases[0].id,false);
}).catch(e => { const el = $('#loading') || $('#detail'); el.textContent = e.message; el.classList.add('error'); });
