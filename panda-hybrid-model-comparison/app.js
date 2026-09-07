'use strict';
const D=JSON.parse(document.getElementById('data').textContent);
const P=JSON.parse(document.getElementById('curve-data').textContent);
const $=s=>document.querySelector(s);
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>v==null?'—':(100*v).toFixed(2)+'%';
const dec=v=>v==null?'—':Number(v).toFixed(4);
const descriptions={oa_only:'Recognize the current atomic action from the observed prefix.',oa_om:'Predict the ongoing action and then its mission. The two semantic components are scored separately.',om_only:'Predict the ongoing mission directly, without generating the ongoing-action field.',oa_future:'Predict the current action and the remaining ordered actions within its mission.'};
const options=(values,labels,selected)=>values.map(v=>`<option value="${esc(v)}" ${v===selected?'selected':''}>${esc(labels[v])}</option>`).join('');
function leaders(format,component,cutoff,metric){
  const rows=D.model_order.map(model=>({model,value:D.cube[format][model][cutoff][component][metric]}));
  const best=Math.max(...rows.map(r=>r.value));
  return {names:rows.filter(r=>Math.abs(r.value-best)<1e-12).map(r=>D.model_names[r.model]).join(' / '),value:best};
}
function metricTable(format,component,cutoff){
  const rows=D.model_order.map(model=>({model,...D.cube[format][model][cutoff][component]}));
  const metrics=['exact_match','token_f1','sentencebert'];
  const maxima=Object.fromEntries(metrics.map(k=>[k,Math.max(...rows.map(r=>r[k]??-1))]));
  return '<caption class="sample-note">'+esc(D.format_names[format]+' · '+P.component_names[component]+' · '+(cutoff==='all'?'all six cutoffs':cutoff+'% observed'))+'</caption><thead><tr><th scope="col">Model</th><th scope="col">N</th><th scope="col">Exact Match</th><th scope="col">Token F1</th><th scope="col">SentenceBERT</th></tr></thead><tbody>'+rows.map(r=>`<tr><th scope="row">${esc(D.model_names[r.model])}</th><td>${r.n.toLocaleString()}</td>${metrics.map(k=>`<td class="${Math.abs(r[k]-maxima[k])<1e-12?'winner':''}">${k==='exact_match'?pct(r[k]):dec(r[k])}</td>`).join('')}</tr>`).join('')+'</tbody>';
}
function renderChart(format){
  const card=document.getElementById(format),component=card.querySelector('select').value;
  const chart=P.charts[format][component],img=card.querySelector('img');
  img.src=chart.svg;img.alt=chart.title+': four models compared at six observation cutoffs.';
  card.querySelector('.svg-link').href=chart.svg;card.querySelector('.pdf-link').href=chart.pdf;
  const first=leaders(format,component,'25','sentencebert'),last=leaders(format,component,'95','sentencebert');
  card.querySelector('.chart-caption').textContent=`At 25%, ${first.names} has the highest mean (${dec(first.value)}); at 95%, ${last.names} has the highest mean (${dec(last.value)}). These are point-estimate rankings, not significance tests.`;
  card.querySelector('.sample-note').textContent=`Evaluated target: ${P.component_names[component]}. N = ${chart.n_per_cutoff} matched samples per model at each cutoff.`+(component==='future'?' Restricted to actions with nonempty ground-truth future actions.':component==='output'?' Includes required field labels and formatting.':'');
  card.querySelector('table').innerHTML='<thead><tr><th scope="col">Model</th>'+P.cutoffs.map(p=>`<th scope="col">${p}%</th>`).join('')+'</tr></thead><tbody>'+D.model_order.map(m=>`<tr><th scope="row">${esc(D.model_names[m])}</th>${chart.series[m].values.map(v=>`<td>${dec(v)}</td>`).join('')}</tr>`).join('')+'</tbody>';
}
$('#progress-charts').innerHTML=D.formats.map(f=>`<section class="chart-card" id="${esc(f)}"><div class="section-heading"><div><div class="eyebrow">Observation progress · SentenceBERT</div><h2>${esc(D.format_names[f])}</h2></div><label>Evaluated component<select aria-label="${esc(D.format_names[f])} chart component">${options(D.components[f],P.component_names,P.defaults[f])}</select></label></div><p class="chart-description">${descriptions[f]}</p><div class="plot-viewport"><img loading="${f==='oa_only'?'eager':'lazy'}" width="1140" height="480" alt=""></div><p class="chart-caption"></p><p class="sample-note"></p><div class="downloads"><a class="svg-link" download>Download SVG</a><a class="pdf-link" download>Download PDF</a></div><details class="extra"><summary>Show exact values at all six cutoffs</summary><div class="table-wrap"><table></table></div></details></section>`).join('');
for(const f of D.formats){document.getElementById(f).querySelector('select').addEventListener('change',()=>renderChart(f));renderChart(f);}
$('#metric-format').innerHTML=options(D.formats,D.format_names,'oa_only');
function resetMetricComponent(){const f=$('#metric-format').value;$('#metric-component').innerHTML=options(D.components[f],P.component_names,P.defaults[f]);renderMetrics();}
function renderMetrics(){
  const f=$('#metric-format').value,c=$('#metric-component').value,p=$('#cutoff').value;
  $('#metric-table').innerHTML=metricTable(f,c,p);
  const winners=[['exact_match','Exact Match'],['token_f1','Token F1'],['sentencebert','SentenceBERT']].map(([key,name])=>{const w=leaders(f,c,p,key);return `${name}: ${w.names} (${key==='exact_match'?pct(w.value):dec(w.value)})`;});
  $('#metric-finding').textContent='Highest values for this selection — '+winners.join('; ')+'.';
  $('#bars').innerHTML=D.model_order.map(m=>`<div><h3>${esc(D.model_names[m])}</h3>${D.formats.map(fmt=>{const v=D.cube[fmt][m][p].output.token_f1;return `<div class="rank"><span>${esc(D.format_names[fmt])}</span><div class="track"><div class="bar" style="width:${100*v}%"></div></div><b>${dec(v)}</b></div>`;}).join('')}</div>`).join('');
}
$('#metric-format').addEventListener('change',resetMetricComponent);
$('#metric-component').addEventListener('change',renderMetrics);$('#cutoff').addEventListener('change',renderMetrics);
$('#system-prompt').textContent=D.cohort.system_prompt;
resetMetricComponent();
