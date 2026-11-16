const $=id=>document.getElementById(id), el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let manifest,catalog,contracts,selection=0,players=[],limit=15;
const read=async p=>{const r=await fetch(p);if(!r.ok)throw Error(`${p}: ${r.status}`);return r.json();};
function fail(e){$('error').hidden=false;$('error').textContent=e.message;}
function pauseAll(){players.forEach(p=>p.v.pause());}
function panel(item,variant,r){
 const root=el('article',undefined,'panel '+variant),head=el('h3',variant==='safe'?'Safe reference action':'Unsafe reference action');
 const box=el('div',undefined,'player'),v=el('video');v.controls=true;v.playsInline=true;v.muted=true;v.preload='metadata';v.src=item.path+'/episode.mp4';v.poster=item.path+'/poster.jpg';v.setAttribute('aria-label',head.textContent+' video');box.append(v);
 const controls=el('div',undefined,'controls'),play=el('button','Play','play');play.type='button';
 const state={v,r,box};players.push(state);
 const seek=t=>{v.pause();v.currentTime=Math.max(0,Math.min(r.duration_s,t));};
 play.onclick=()=>v.paused?v.play().catch(fail):v.pause();controls.append(play);
 [['Restart',()=>seek(0)],['−1 s',()=>seek(v.currentTime-1)],['+1 s',()=>seek(v.currentTime+1)],['−1 frame',()=>seek(v.currentTime-1/r.fps)],['+1 frame',()=>seek(v.currentTime+1/r.fps)]].forEach(([s,f])=>{const b=el('button',s);b.onclick=f;controls.append(b);});
 const speed=el('select');speed.setAttribute('aria-label',variant+' playback speed');[.25,.5,1,2,4].forEach(n=>{const o=el('option',n+'×');o.value=n;o.selected=n===1;speed.append(o);});speed.onchange=()=>v.playbackRate=Number(speed.value);controls.append(speed);
 const full=el('button','Fullscreen');full.dataset.fullscreen='true';full.onclick=async()=>{if(document.fullscreenElement){await document.exitFullscreen();return;}if(box.classList.contains('expanded')){box.classList.remove('expanded');full.textContent='Fullscreen';return;}try{await box.requestFullscreen();full.textContent='Exit fullscreen';}catch{box.classList.add('expanded');full.textContent='Exit fullscreen';}};controls.append(full);
 const strip=el('div',undefined,'seek'),slider=el('input'),clock=el('span','0.0 / '+r.duration_s.toFixed(1)+' s');slider.type='range';slider.min=0;slider.max=r.duration_s;slider.step=1/r.fps;slider.value=0;slider.setAttribute('aria-label',variant+' video progress');slider.oninput=()=>seek(Number(slider.value));strip.append(slider,clock);box.append(controls,strip);
 const refresh=()=>{$('play-both').textContent=players.some(p=>!p.v.paused&&!p.v.ended)?'Pause both':'Play both';play.textContent=v.paused||v.ended?'Play':'Pause';};
 v.ontimeupdate=()=>{slider.value=v.currentTime;clock.textContent=v.currentTime.toFixed(1)+' / '+r.duration_s.toFixed(1)+' s';};v.onplay=refresh;v.onpause=refresh;v.onended=refresh;v.onerror=()=>fail(Error('Video could not load: '+v.src));
 const body=el('div',undefined,'body'),o=r.outcome,bad=o.fell||o.displaced||o.modeled_spill;
 const label=o.fell?'Object fell below support':o.displaced?'Object displaced by contact':o.tipped?'Object tipped':o.stable_at_end?'Stable at the end':'Inspect the measured state';
 body.append(el('div',label,'outcome'+(bad?' bad':'')));
 const metrics=el('div',undefined,'metrics');
 [['Maximum tilt',o.max_tilt_deg.toFixed(1)+'°'],['Maximum displacement',(o.max_displacement_m*100).toFixed(1)+' cm'],['Probe contact',o.contact_samples?'Measured':'Not observed'],['Modeled liquid escaped',r.liquid.ledger.spilled_ml.toFixed(1)+' ml']].forEach(([a,b])=>{const x=el('div',undefined,'metric');x.append(el('small',a),el('b',b));metrics.append(x);});body.append(metrics);
 if(r.recipe.mechanism!=='floor_collision'){const x=el('div',undefined,'metric');x.append(el('small','Initial centre-of-mass support margin'),el('b',(r.initial_state.com_support_margin_m*100).toFixed(1)+' cm'));metrics.append(x);}
 if(r.recipe.liquid_ml){const x=el('div',undefined,'metric');x.append(el('small','Declared container / initial liquid'),el('b',(r.recipe.container_open?'Open':'Closed')+' · '+r.recipe.liquid_ml+' ml'));metrics.append(x);}
 const events=el('div',undefined,'events');r.outcome.events.forEach(e=>{const b=el('button',e.type.replaceAll('_',' ')+' · '+e.t.toFixed(2)+' s');b.onclick=()=>{speed.value='.25';v.playbackRate=.25;seek(e.t-.25);v.play().catch(fail);};events.append(b);});body.append(events);
 body.append(el('p',variant==='safe'?r.recipe.safe_condition:r.recipe.unsafe_condition,'note'),el('p',r.source_task_id+' · original plan · highlighted interaction tested','eyebrow'));
 const plan=el('ol',undefined,'plan');r.original_plan.forEach((a,i)=>{const li=el('li',undefined,i===r.tested_action_index?'tested':'');li.append(el('code',a));if(i===r.tested_action_index)li.title='This local interaction is executed in the clip';plan.append(li);});body.append(plan);
 const links=el('div',undefined,'downloads');[['Result','result.json'],['State trace','trace.json'],['Predicate transitions','predicate-transitions.json'],['Video','episode.mp4'],['Recorded source','recorded-source.zip']].forEach(([name,path])=>{const a=el('a',name+' ↓');a.href=item.path+'/'+path;links.append(a);});body.append(links);root.append(head,box,body);return root;
}
async function choose(){
 const token=++selection;pauseAll();players=[];$('players').replaceChildren();const c=manifest.cases.find(c=>c.id===$('case').value);location.hash=c.id;
 $('scope').textContent='LOCAL INTERACTION TEST · 7 seconds · same object and physical parameters · independent video clocks';$('context').textContent=c.source_scope;$('full-link').href=c.full_url;
 const data=await Promise.all(['safe','unsafe'].map(k=>read(c.variants[k].path+'/result.json')));if(token!==selection)return;
 data.forEach((r,i)=>$('players').append(panel(c.variants[['safe','unsafe'][i]],['safe','unsafe'][i],r)));
}
function search(){
 const query=$('search').value.toLowerCase().trim(),group=$('group').value;
 const rows=catalog.filter(r=>(group==='all'||r.danger.danger_group===group)&&(!query||[r.task_id,r.danger.robot_task,r.danger.cause_of_danger,...r.objects.map(o=>o.entity),...Object.values(r.original_plans)].join(' ').toLowerCase().includes(query)));
 $('search-count').textContent=`${rows.length} source records · showing ${Math.min(limit,rows.length)}`;$('results').replaceChildren();$('more').hidden=limit>=rows.length;
 rows.slice(0,limit).forEach(r=>{const d=el('details',undefined,'record'),s=el('summary');s.append(el('span',r.task_id+' · '+r.danger.danger_type),el('strong',r.danger.robot_task));d.append(s,el('p',r.danger.cause_of_danger));
 ['safe','unsafe'].forEach(k=>{d.append(el('small',k.toUpperCase()+' ORIGINAL PLAN'),el('code',r.original_plans[k]));});
 d.append(el('p','Entities: '+r.objects.map(o=>o.entity+' → '+o.category_candidate+(o.installed_asset_count?' ('+o.installed_asset_count+' asset candidates)':' (asset review needed)')).join('; '),'note'));
 d.append(el('p',r.reviewed_fixtures.length?'Reviewed local binding: '+r.reviewed_fixtures.join(', '):'Not executed in this object library. Candidate mechanisms: '+r.mechanism_candidates.join(', '),'note'));$('results').append(d);});
}
function assetDetail(){
 const c=contracts.find(c=>c.category===$('asset-category').value),root=$('asset-detail');root.replaceChildren();
 root.append(el('h3',c.category.replaceAll('_',' ')),el('p',`${c.task_ids.length} physical source records · ${c.asset_candidates.length} installed asset candidates · not validated coverage`));
 [['Candidate observations',c.candidate_observations],['Native capability annotations',c.native_ability_annotations],['Required physical inputs',c.required_inputs],['Not established',c.not_established]].forEach(([name,values])=>{if(!values.length)return;root.append(el('strong',name));const ul=el('ul');values.forEach(v=>ul.append(el('li',v.replaceAll('_',' '))));root.append(ul);});
 const d=el('details');d.append(el('summary','Inspect candidate asset IDs'));const pre=el('pre',JSON.stringify(c.asset_candidates,null,2));d.append(pre);root.append(d);
}
async function loadControls(){
 if(!manifest.control_runs)return;const report=await read('data/controls.json');$('control-section').hidden=false;
 const names={closed:'Closed cap · same contact', 'zero-impact':'Zero impact speed · same placement','alternate-bottle':'Alternative BEHAVIOR bottle · closed cap'};
 report.controls.forEach(c=>{const card=el('div',undefined,'control-card');card.append(el('h3',names[c.name]));['safe','unsafe'].forEach(v=>{const r=c.variants[v],o=r.outcome;card.append(el('p',`${v==='safe'?'Safe':'Unsafe'} reference: ${o.fell?'fell':o.tipped?'tipped':'did not tip or fall'}; ${r.liquid.spilled_ml.toFixed(1)} ml modeled spill.`));});$('control-results').append(card);});
}
$('play-both').onclick=()=>{if(players.some(p=>!p.v.paused))pauseAll();else players.forEach(p=>{if(p.v.ended)p.v.currentTime=0;p.v.play().catch(fail);});};$('reset-both').onclick=()=>{pauseAll();players.forEach(p=>p.v.currentTime=0);};$('final-both').onclick=()=>{pauseAll();players.forEach(p=>p.v.currentTime=p.r.duration_s-1/p.r.fps);};
$('search').oninput=$('group').onchange=()=>{limit=15;search();};$('more').onclick=()=>{limit+=15;search();};$('case').onchange=()=>choose().catch(fail);document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.querySelectorAll('.expanded').forEach(x=>x.classList.remove('expanded'));document.querySelectorAll('[data-fullscreen]').forEach(x=>x.textContent='Fullscreen');}});document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement)document.querySelectorAll('[data-fullscreen]').forEach(x=>x.textContent='Fullscreen');});
(async()=>{[manifest,catalog,contracts]=await Promise.all([read('manifest.json'),read('data/catalog.json'),read('data/asset-contracts.json')]);const s=manifest.summary;
 [[s.task_count,'source records indexed'],[s.physical_source_tasks,'physical-safety source records'],[s.physical_categories_with_installed_candidates,'category / asset candidates'],[manifest.cases.length,'new physical comparison pairs']].forEach(([v,t])=>{const d=el('div',undefined,'count');d.append(el('b',v),el('span',t));$('counts').append(d);});
 manifest.cases.forEach(c=>{const o=el('option',c.title);o.value=c.id;$('case').append(o);});const initial=location.hash.slice(1);if(manifest.cases.some(c=>c.id===initial))$('case').value=initial;
 manifest.existing.forEach(c=>{const a=el('a');a.href=c.url;a.append(el('strong',c.category+' · '+c.mechanism),el('small',c.task_id+' · '+c.limitations));$('existing').append(a);});
 contracts.forEach(c=>{const o=el('option',c.category.replaceAll('_',' '));o.value=c.category;$('asset-category').append(o);});$('asset-category').onchange=assetDetail;assetDetail();search();await choose();await loadControls();})().catch(fail);
