'use strict';
const $ = s => document.querySelector(s);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
let data, selected, changesOnly = false, toastTimer;
const byId = id => data.cases.find(c => c.id === id);
function filtered() {
  const model=$('#model').value, scope=$('#scope').value, q=$('#search').value.trim().toLowerCase();
  return data.cases.filter(c => (model==='all'||c.model===model) && (scope==='all'||c.original_safe===(scope==='safe')) && (!q||[c.task,data.models[c.model],c.summary,...c.original,...c.cleaned].join(' ').toLowerCase().includes(q)));
}
function renderList() {
  const list=filtered();
  $('#count').textContent=`${list.length} ${list.length===1?'case':'cases'}`;
  $('#cases').innerHTML=list.map(c=>`<button class="case-item" type="button" data-id="${c.id}" aria-current="${selected===c.id}"><strong>${escapeHTML(c.task)}</strong><span>${escapeHTML(data.models[c.model])}</span>${c.original_safe?'':'<small>Original already unsafe</small>'}</button>`).join('');
  $('#cases').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>choose(b.dataset.id,true)));
  return list;
}
function toast(text) {clearTimeout(toastTimer);$('#toast').textContent=text;$('#toast').classList.add('visible');toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),1800);}
async function copy(text) {
  try {await navigator.clipboard.writeText(text);toast('Copied');}
  catch (_) {const t=document.createElement('textarea');t.value=text;t.style.position='fixed';t.style.opacity='0';document.body.append(t);t.select();const ok=document.execCommand('copy');t.remove();toast(ok?'Copied':'Copy unavailable');}
}
function diffCell(cell, side, kind, c) {
  if(!cell)return `<div class="cell gap"><span class="line-number"></span><span class="action">${side==='cleaned'?'Removed':'—'}</span></div>`;
  const failure=side==='cleaned' && c.failure.step===cell.number;
  const after=side==='cleaned' && c.failure.step && cell.number>c.failure.step;
  const klass=[side==='original'&&kind==='delete'?'deleted':'',kind==='replace'?'replaced':'',failure?'failure':'',after?'after-stop':''].filter(Boolean).join(' ');
  return `<div class="cell ${klass}" data-side="${side}" data-line="${cell.number}"><span class="line-number">${cell.number}</span><div class="action"><span class="action-text">${escapeHTML(cell.action)}</span>${failure?'<span class="failure-mark">Fails here</span>':''}</div></div>`;
}
function showDetail(c) {
  $('#detail').setAttribute('aria-busy','false');
  const failureTitle=c.failure.step?`Fails at cleaned step ${c.failure.step}`:'Goal not reached';
  const conditions=c.failure.conditions.length?`<div><code>${c.failure.conditions.map(escapeHTML).join(' ; ')}</code></div>`:'';
  const changeCount=[c.removed?`${c.removed} ${c.removed===1?'step':'steps'} removed`:'',c.rewritten?`${c.rewritten} ${c.rewritten===1?'step':'steps'} rewritten`:''].filter(Boolean).join(', ');
  $('#detail').innerHTML=`
    <div class="case-header"><div><h2>${escapeHTML(c.task)}</h2><div class="model-name">${escapeHTML(data.models[c.model])}</div></div><button type="button" class="link-button" id="copyLink">Copy link</button></div>
    <p class="goal">${escapeHTML(c.goal)}</p>
    <p class="change-note"><strong>${escapeHTML(c.summary)}</strong></p>
    ${c.original_safe?'':`<p class="unsafe-note">This original plan was feasible but already unsafe at step ${c.original_danger_steps[0]}. It is excluded from the 8 safe originals.</p>`}
    <div class="failure-note"><span class="failure-heading">${failureTitle}</span>${escapeHTML(c.reason)}${conditions}</div>
    <div class="diff-tools"><div class="legend"><span><i class="swatch removed"></i>Removed</span><span><i class="swatch rewritten"></i>Rewritten</span><span><i class="swatch failed"></i>Failure</span></div><label class="changes-only"><input type="checkbox" id="changesOnly" ${changesOnly?'checked':''}>Changes only</label></div>
    <div class="diff-scroll" tabindex="0" role="region" aria-label="Full plans; scroll horizontally on small screens"><div class="diff">
      <div class="plan-heads"><div class="plan-head"><div><strong>Original plan</strong><span class="status ${c.original_safe?'safe':'unsafe'}">${c.original_safe?'Feasible and safe':'Feasible but unsafe'}</span></div><button class="copy-plan" type="button" id="copyOriginal">Copy</button></div><div class="plan-head"><div><strong>After cleaning</strong><span class="status infeasible">Infeasible</span></div><button class="copy-plan" type="button" id="copyCleaned">Copy</button></div></div>
      <div class="diff-body">${c.rows.map(row=>`<div class="diff-row" data-kind="${row.kind}">${diffCell(row.original,'original',row.kind,c)}${diffCell(row.cleaned,'cleaned',row.kind,c)}</div>`).join('')}</div>
    </div></div>
    <div class="detail-bottom"><span>${c.original.length} original steps → ${c.cleaned.length} cleaned steps</span><span>${changeCount}</span></div>`;
  $('#copyOriginal').addEventListener('click',()=>copy(c.original.join('\n')));
  $('#copyCleaned').addEventListener('click',()=>copy(c.cleaned.join('\n')));
  $('#copyLink').addEventListener('click',()=>copy(`${location.origin}${location.pathname}#case=${encodeURIComponent(c.id)}`));
  $('#changesOnly').addEventListener('change',e=>{changesOnly=e.target.checked;applyDiffFilter();});
  applyDiffFilter();
}
function applyDiffFilter() {
  document.querySelectorAll('.diff-row').forEach(row=>row.classList.toggle('hidden',changesOnly && row.dataset.kind==='equal' && !row.querySelector('.failure')));
}
function choose(id, setHash=false) {
  const c=byId(id);if(!c)return;
  selected=id;renderList();showDetail(c);
  if(setHash)history.replaceState(null,'',`#case=${encodeURIComponent(id)}`);
}
function update() {
  const list=filtered();
  if(!list.some(c=>c.id===selected))selected=list[0]?.id;
  renderList();
  if(selected){showDetail(byId(selected));history.replaceState(null,'',`#case=${encodeURIComponent(selected)}`);}
  else {$('#detail').innerHTML='<div class="empty">No matching cases.<br><button type="button" id="clearEmpty">Clear filters</button></div>';$('#clearEmpty').addEventListener('click',reset);}
}
function reset() {$('#model').value='all';$('#scope').value='safe';$('#search').value='';changesOnly=false;selected=data.default_case;update();}
function fromHash() {
  let id;try{id=decodeURIComponent(location.hash.replace(/^#case=/,''));}catch(_){return;}
  const c=byId(id);if(!c)return;
  $('#model').value='all';$('#scope').value=c.original_safe?'safe':'all';$('#search').value='';choose(id);
}
async function init() {
  try {
    const response=await fetch('data.json');if(!response.ok)throw new Error(`HTTP ${response.status}`);data=await response.json();
    $('#summary tbody').innerHTML=data.stats.map(s=>`<tr><th scope="row">${escapeHTML(s.label)}</th><td>${s.affected}</td><td>${s.infeasible}</td><td>${s.share.toFixed(2)}%</td></tr>`).join('');
    $('#model').innerHTML='<option value="all">All models</option>'+Object.entries(data.models).map(([k,v])=>`<option value="${k}">${escapeHTML(v)}</option>`).join('');
    $('#model').addEventListener('change',update);$('#scope').addEventListener('change',update);$('#search').addEventListener('input',update);$('#reset').addEventListener('click',reset);
    window.addEventListener('hashchange',fromHash);selected=data.default_case;choose(selected);fromHash();
  }catch(error){$('#detail').setAttribute('aria-busy','false');$('#detail').innerHTML='<p class="empty">Unable to load cases. Please reload this page.</p>';console.error(error);}
}
init();
