const $=id=>document.getElementById(id),release='2afd03148648',explorer='../';
let summary,selected,request=0;
const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const read=async path=>{const r=await fetch(`${path}?v=${release}`);if(!r.ok)throw Error(`${path}: ${r.status}`);return r.json();};
const label=s=>({pump_bottle_toppled:'pump tilt exceeded 15°'}[s]||s.replaceAll('_',' '));
async function readTrace(path){const r=await fetch(path);if(!r.ok)throw Error('Trace unavailable');if(!window.DecompressionStream)throw Error('This browser cannot decode compressed traces. Download the evidence archive to inspect the data.');return JSON.parse(await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text());}
function stat(value,name){const d=el('div',undefined,'fact');d.append(el('strong',value),el('span',name));return d;}
function signal(value,title){return el('span',value===null?`${title}: not evaluated`:`${title}: ${value?'yes':'no'}`,'signal'+(value===null?' unknown':value?' flag':''));}
function knownStep(r,t){return r.steps.findIndex(s=>s.start<=t&&s.end>=t);}
function stateAt(trace,t){let lo=0,hi=trace.length;while(lo<hi){const m=(lo+hi)>>1;if(trace[m].t<=t)lo=m+1;else hi=m;}return trace[Math.max(0,lo-1)];}
function graphMetric(c,r){
 if(c.mechanism==='spill')return ['Modeled spilled volume','ml',s=>s.safety.spilled_ml];
 if(c.mechanism==='drop')return ['Payload bottom height','m',s=>s.object_bottom_m];
 if(c.intervention==='placement_bias')return ['Distance from table edge','cm',s=>s.metrics.edge_margin_m*100];
 if(c.intervention==='processing_required')return ['Parcel inside storage','boolean',s=>Number(s.metrics.inside_storage_bin)];
 if(c.mechanism==='reach')return ['Recipient distance','cm',s=>s.metrics.reach_distance_m*100];
 if(c.intervention==='pump_bottle_present')return ['Pump tilt','degrees',s=>s.metrics.hazard_tilt_deg];
 if(c.intervention==='stool_present')return ['Stool displacement','cm',s=>s.metrics.stool_displacement_m*100];
 if(c.intervention==='chair_present')return ['Chair clearance','cm',s=>s.metrics.chair_clearance_m*100];
 return ['Robot–bed contact','boolean',s=>Number(s.metrics.bed_contact)];
}
function buildPanel(c,row,r,trace,original,scale){
 const k=row.variant,root=el('article',undefined,'panel '+k),h=el('h3',k==='safe'?'Safe reference plan':'Unsafe reference plan');h.append(el('small','DATASET LABEL'));root.append(h);
 const signals=el('div',undefined,'signals');signals.append(el('span',`Goal: ${r.goal_reached?'reached':'not reached'}`,'signal'+(r.goal_reached?'':' flag')),el('span',`Execution: ${r.status}`,'signal'+(r.status==='completed'?'':' flag')));
 [['physical_incident','Physical event'],['modeled_incident','Modeled spill'],['constraint_violation','Order violation'],['risk_condition','Risk threshold']].forEach(([f,title])=>signals.append(signal(r.safety[f],title)));root.append(signals);
 if(r.error)root.append(el('p',r.error.split('\n')[0]+' Later, unexecuted actions were not tested for hazards.','note'));
 const [metric,unit,value]=graphMetric(c,r);root.append(el('p',`${metric} · ${unit}`,'eyebrow'));
 const NS='http://www.w3.org/2000/svg',svg=document.createElementNS(NS,'svg');svg.setAttribute('viewBox','0 0 640 220');svg.setAttribute('role','img');svg.setAttribute('aria-label',`${k} measured ${metric}`);root.append(svg);
 const add=(tag,attrs,text)=>{const e=document.createElementNS(NS,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;svg.append(e);return e;};
 const vals=trace.map(value),finite=vals.filter(Number.isFinite),lo=scale?.[0]??Math.min(0,...finite),hi=scale?.[1]??Math.max(.1,...finite),span=hi-lo||1;
 const X=t=>45+t/r.duration*580,Y=v=>180-(v-lo)/span*155;
 for(let i=0;i<4;i++){const v=lo+span*i/3;add('line',{x1:45,x2:625,y1:Y(v),y2:Y(v),stroke:'#e3e9dc'});add('text',{x:37,y:Y(v)+4,'text-anchor':'end','font-size':10,fill:'#6c7c60'},v.toFixed(span<1?2:1));}
 let d='';trace.forEach((s,i)=>{if(Number.isFinite(vals[i]))d+=(d?'L':'M')+X(s.t).toFixed(1)+','+Y(vals[i]).toFixed(1);});
 add('path',{d,fill:'none',stroke:k==='safe'?'#467a54':'#b2764d','stroke-width':2});
 for(let i=0;i<=4;i++)add('text',{x:X(r.duration*i/4),y:205,'font-size':10,'text-anchor':'middle',fill:'#6c7c60'},(r.duration*i/4).toFixed(0)+' s');
 r.safety.events.filter(e=>!['observation','intervention'].includes(e.severity)).forEach(e=>add('line',{x1:X(e.t),x2:X(e.t),y1:15,y2:180,stroke:'#b5a357','stroke-dasharray':'4 3'}));
 const cursor=add('line',{x1:45,x2:45,y1:15,y2:180,stroke:'#263b30','stroke-width':1.4});
 const seek=el('div',undefined,'seek'),slider=el('input'),time=el('output');slider.type='range';slider.min=0;slider.max=r.duration;slider.step=1/30;slider.value=0;slider.setAttribute('aria-label',`${k} state trace time`);seek.append(slider,time);root.append(seek);
 const state=el('p',undefined,'state');root.append(state);root.append(el('h4','The original plan'));
 const plans=el('ol',undefined,'plans');(original.match(/\([^()]+\)/g)||[]).forEach((a,i)=>{const li=el('li'),s=r.steps[i];li.append(el('code',a),el('small',s?`${s.start.toFixed(1)}–${s.end.toFixed(1)} s · ${s.status}`:'Not executed'));plans.append(li);});root.append(plans);
 const detail=el('pre','Select an event to inspect its evidence.','event-detail');
 const show=t=>{const s=stateAt(trace,t);slider.value=t;time.textContent=`${t.toFixed(1)} / ${r.duration.toFixed(1)} s`;cursor.setAttribute('x1',X(t));cursor.setAttribute('x2',X(t));state.textContent=`${s.phase} · payload [${s.object.p.map(v=>v.toFixed(3)).join(', ')}] m`;Array.from(plans.children).forEach((li,i)=>li.classList.toggle('active',i===s.step));};
 slider.oninput=()=>show(Number(slider.value));show(0);
 root.append(el('h4','Observed events'));const events=el('div',undefined,'events');
 if(!r.safety.events.length)events.append(el('p','No events recorded in the monitored scope.','note'));
 r.safety.events.forEach(e=>{const b=el('button',undefined,e.severity);b.append(el('span',label(e.event)),el('span',`${e.t.toFixed(2)} s`));b.onclick=()=>{show(e.t);detail.textContent=JSON.stringify(e,null,2);};events.append(b);});root.append(events,detail);
 const downloads=el('div',undefined,'downloads');[['Result JSON','result.json'],['Full trace (gzip)','trace.json.gz'],['Events','events.json']].forEach(([name,file])=>{const a=el('a',name+' ↓');a.href=`data/${row.id}/${file}`;downloads.append(a);});root.append(downloads);return root;
}
async function selectCase(id){
 const token=++request;selected=summary.cases.find(c=>c.id===id);const c=selected,condition=$('condition').value,seed=Number($('seed').value);
 renderModels();
 $('experiment').setAttribute('aria-busy','true');$('error').hidden=true;$('task-id').textContent=`${id} / HARD-1044`;$('title').textContent=c.title;$('intervention').textContent=c.description;$('case-scope').textContent=c.scope||'Measured surrogate mechanisms; no human injury is simulated.';
 document.querySelectorAll('#cases button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.id===id)));
 const check=summary.pairing_checks.find(p=>p.task===id&&p.condition===condition&&p.seed===seed);
 const contrasts=(summary.intervention_checks||[]).filter(p=>p.task===id&&p.seed===seed);
 $('pairing').textContent=(check?(check.valid_pair?'Pair verified: same measured initial state, mass, condition and execution code.':'Pairing check failed. Do not interpret this pair as a controlled comparison.'):'Pairing awaits both recorded attempts.')+(contrasts.length===2?(contrasts.every(p=>p.valid_contrast)?' Condition contrast verified: the original plan and starting robot/payload match; only the declared condition changes.':' Condition-contrast audit failed; inspect the evidence ledger.'):'');
 const review=$('grounding-review');review.replaceChildren();review.hidden=summary.grounding_review?.task!==id;if(!review.hidden){const a=el('a','Inspect the navigation correction →');a.href=summary.grounding_review.path;review.append(a,el('span',' '+summary.grounding_review.description));}
 const video=$('video-link');video.href=['neiss_2888','neiss_9506','alfred_2757'].includes(id)?`${explorer}#${id==='neiss_9506'?'neiss_2888':id}`:`${explorer}plan-pairs/#${id==='neiss_13019'?'neiss_24170':id}`;
 $('contrasts').replaceChildren();c.effects.forEach(e=>Object.entries(e.conditions).forEach(([name,s])=>{const tr=el('tr');[e.variant,name,`${s.recorded} / ${e.planned_per_condition}`,s.goal_reached,s.physical_incident,s.modeled_incident,s.constraint_violation,s.risk_condition,s.execution_failures].forEach(v=>tr.append(el('td',String(v))));$('contrasts').append(tr);}));
 $('panels').replaceChildren(el('p','Loading measured states…','note'));
 try{
  const meta=await read(`sources/${id}/metadata.json`);
  const loaded=await Promise.all(['safe','unsafe'].map(async variant=>{const row=c.trials.find(r=>r.condition===condition&&r.seed===seed&&r.variant===variant);if(row.state!=='recorded')return {variant,row};
   const path=`data/${row.id}`,r=await read(path+'/result.json'),trace=await readTrace(`${path}/trace.json.gz?v=${release}`);return {variant,row,r,trace};}));
  const values=loaded.flatMap(d=>d.trace?d.trace.map(graphMetric(c,d.r)[2]):[]).filter(Number.isFinite),scale=[Math.min(0,...values),Math.max(.1,...values)];
  const panels=loaded.map(d=>{if(d.r)return buildPanel(c,d.row,d.r,d.trace,meta.reference_feasible_plans[d.variant],scale);const p=el('article',undefined,'panel '+d.variant);p.append(el('h3',`${label(d.variant)} reference plan`),el('p',label(d.row.state)),el('p',d.row.error||'This attempt has no recorded result.','note'));return p;});
  if(token!==request)return;$('panels').replaceChildren(...panels);history.replaceState(null,'','#'+id);
 }catch(e){if(token===request){$('error').hidden=false;$('error').textContent=e.message;}}
 finally{if(token===request)$('experiment').setAttribute('aria-busy','false');}
}
function renderModels(){
 const shown=summary.model_evaluations.filter(m=>$('model-scope').value==='all'||m.task===selected?.id);
 $('model-counts').textContent=`${shown.length} records shown. Configurations and failed responses are retained separately in the full evidence ledger.`;
 const body=$('models');body.replaceChildren();shown.forEach(m=>{const tr=el('tr');[m.model+' / '+m.configuration,m.task,m.parse_status+(m.evaluation_role==='interface_diagnostic'?' · interface diagnostic':''),m.semantic?.score??'—',m.rollout_status+(m.goal_reached!==undefined?` · goal ${m.goal_reached?'reached':'not reached'}`:'')].forEach(v=>tr.append(el('td',String(v))));const td=el('td'),details=el('details');details.append(el('summary','Inspect output'),el('code',m.plan||m.reason||'No parsed action sequence.'));const a=el('a','Raw response ↓');a.href=m.evidence_path;const req=el('a','Exact request ↓');req.href=m.evidence_path.replace(/response\.json$/,'request.json');details.append(el('br'),a,el('br'),req);if(m.semantic?.message)details.append(el('p',m.semantic.message));if(m.reason)details.append(el('p',m.reason));if(m.safety){details.append(el('pre',JSON.stringify({events:m.safety.events,task_goal_reached:m.goal_reached},null,2),'event-detail'));[['Physical result ↓','result.json'],['Physical state trace ↓','trace.json.gz']].forEach(([title,file])=>{const link=el('a',title);link.href=m.evidence_path.replace(/response\.json$/,'rollout/'+file);details.append(el('br'),link);});}td.append(details);tr.append(td);body.append(tr);});
 if(!summary.model_evaluations.length){const tr=el('tr'),td=el('td','No model output has been recorded yet.');td.colSpan=6;tr.append(td);body.append(tr);}
}
$('condition').onchange=() =>selectCase(selected.id);$('seed').onchange=()=>selectCase(selected.id);
$('model-scope').onchange=renderModels;
read('summary.json').then(s=>{summary=s;$('scope').textContent=s.scope;$('coverage').append(stat(s.source_records,s.source_records===1?'source record':'source records'),stat(`${s.recorded_trials} / ${s.expected_trials}`,'recorded attempts'),stat(`${s.valid_pairs} / ${s.expected_trials/2}`,'verified safe / unsafe pairs'),stat(s.pending_trials,'pending attempts'));
 s.cases.forEach(c=>{const b=el('button');b.dataset.id=c.id;b.setAttribute('aria-pressed','false');b.append(el('span',c.id+' / '+c.mechanism),el('b',c.title));b.onclick=()=>selectCase(c.id);$('cases').append(b);});renderModels();$('calibration-title').textContent=s.calibration.calibrated?'Calibration recorded.':'Real-world calibration remains open.';$('calibration').textContent=s.calibration.note;selectCase(s.cases.some(c=>c.id===location.hash.slice(1))?location.hash.slice(1):s.cases[0].id);
}).catch(e=>{$('error').hidden=false;$('error').textContent=e.message;});
