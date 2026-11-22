'use strict';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!=null)x.textContent=text;if(cls)x.className=cls;return x};
const build=document.documentElement.dataset.build;
function releaseAsset(url){return build && !/^(https?:|\.\.\/|#)/.test(url) ? url+'?v='+encodeURIComponent(build) : url}
const link=(text,url)=>{const a=el('a',text);a.href=releaseAsset(url);return a};
let catalog=[],current,vids=[],playing=false,handle=0;
const lastSceneTask=new Map();
const branch=['unsafe','safe'], labels={unsafe:'Unsafe',safe:'Safe'};
function halt(){playing=false;cancelAnimationFrame(handle);vids.forEach(v=>v.pause());$('play').textContent='Play together'}
function sync(){if(!playing)return;if(vids.some(v=>v.ended))return halt();if(vids.every(v=>v.readyState>2)&&Math.abs(vids[0].currentTime-vids[1].currentTime)>.12)vids[1].currentTime=vids[0].currentTime;handle=requestAnimationFrame(sync)}
function jump(t){for(const v of vids){if(v.readyState>0)v.currentTime=Math.min(t,v.duration);else v.addEventListener('loadedmetadata',()=>v.currentTime=Math.min(t,v.duration),{once:true})}}
$('play').onclick=async()=>{if(playing)return halt();if(vids.some(v=>v.ended))jump(0);else jump(vids[0].currentTime);try{await Promise.all(vids.map(v=>v.play()));playing=true;$('play').textContent='Pause both';sync()}catch{halt()}};
$('event').onclick=()=>{halt();jump(current.event)};
function card(key,title){const article=el('article',null,'card '+key);article.append(el('h3',title));return article}
function imgFig(src,label,cls){const f=el('figure',null,cls),a=link('',src),i=el('img');i.src=releaseAsset(src);i.alt=label;i.loading='lazy';a.append(i);f.append(a,el('figcaption',label));return f}
function use(c){
 halt();current=c;const scene=taskEnvironment(c.id);$('group').value=scene;lastSceneTask.set(scene,c);
 $('tasks').replaceChildren(...catalog.filter(x=>taskEnvironment(x.id)===scene).map(x=>{const b=el('button');b.type='button';b.setAttribute('aria-current',String(c.id===x.id));const i=el('img');i.src=releaseAsset(x.id+'/thumb.jpg');i.alt='';b.append(i,el('span',x.title));b.onclick=()=>{location.hash=x.id};return b}));
 $('title').textContent=c.title;$('robot').textContent=c.robot;$('task').textContent=c.description;document.title=c.title+' · Antigravity edition';
 const orig=$('baseline');
 const mainId=c.baseline||(c.dataset?c.id:null);orig.hidden=!mainId;
 if(mainId){orig.textContent=c.dataset?'View on the main site':'View original study ↗';orig.href=mainId.startsWith('archive/')?'../archive/#'+mainId.split('/')[1]:'../#'+mainId;}
 $('room').hidden=!c.photos;
 function showPhoto(name){const f=$('photo'),a=link('',c.id+'/'+name+'.jpg'),im=el('img');im.src=releaseAsset(c.id+'/'+name+'-preview.jpg');im.alt=name==='world'?'Room overview':'Alternate camera view';a.append(im);f.replaceChildren(a);for(const [id,val] of [['overview','world'],['aisle','aisle']])$(id).setAttribute('aria-pressed',String(val===name))}
 $('overview').onclick=()=>showPhoto('world');$('aisle').onclick=()=>showPhoto('aisle');if(c.photos)showPhoto('world');
 $('productionNote').hidden=!c.dataset;$('editionMethods').hidden=!!c.dataset;
 if(c.group==='people')$('productionNote').textContent=c.scope+' Google Antigravity (Gemini 4 Neon High) authored the simulation and visual scene. Codex corrected runtime issues, rendered and checked both runs, and published this edition.';
 else if(c.dataset)$('productionNote').textContent='Google Antigravity ran Gemini 4 Neon High on an existing MuJoCo mobile-Panda project. Gemini authored the rooms, Genie Sim surface materials, action sequences and Blender renderer, and revised the robot and tool mechanics during testing. Codex supplied the initial physics setup, ran the generated programs, checked the outputs and published the results. The two DESPITE examples supplied the reference actions. No PDDL planner was used.';
 $('time').textContent='Event at '+c.event.toFixed(2)+' s · '+c.duration.toFixed(2)+' s replay';
 $('notes').textContent=c.notes;$('detail').textContent=c.detail;$('criterion').textContent=c.criterion;
 $('hardware').hidden=!c.hardware;
 if(c.hardware){$('mechanismShots').replaceChildren(imgFig(c.id+'/withdrawn.jpg','3.00 s · Bridge withdrawn while the pusher advances'),imgFig(c.id+'/deployed.jpg','5.40 s · Bridge deployed before the carton crosses'));$('mechanismData').replaceChildren(link('Before and after at 3.00 s',c.id+'/fabrication-comparison.jpg'),link('Measured plate travel and height',c.id+'/mechanism.png'),link('Carton-to-steel force history',c.id+'/steel.png'),link('Unsafe steel loads (CSV.GZ)',c.id+'/unsafe-steel.csv.gz'),link('Safe steel loads (CSV.GZ)',c.id+'/safe-steel.csv.gz'),link('Solver verification',c.id+'/fabrication-audit.json'))}
 vids=[];for(const id of ['players','plans','evidence','charts','facts','downloads','sources'])$(id).replaceChildren();
 for(const b of branch){
  const p=card(b,labels[b]+' replay'),v=el('video');v.controls=true;v.playsInline=true;v.preload='metadata';v.poster=releaseAsset(c.id+'/'+b+'_poster.jpg');
  const s=el('source');s.type='video/mp4';s.src=c.film+'/'+b+'.mp4';v.append(s);vids.push(v);p.append(v,el('div',c[b].outcome,'caption'));$('players').append(p);
  const plan=card(b,labels[b]+' plan'),ol=el('ol',null,'steps');for(const step of c[b].steps){const li=el('li');li.append(el('span',Number(step.t).toFixed(2)+' s','clock'),el('span',step.text));ol.append(li)}plan.append(ol);$('plans').append(plan);
  $('evidence').append(imgFig(c.id+'/detail_'+b+'.jpg',labels[b]+' event view'));
 }
 if(c.id==='everyday_pool'){for(const b of branch)$('evidence').append(imgFig(c.id+'/end_'+b+'.jpg',b==='safe'?'After tool return · grit in the collection pan':'After tool return · grit on the pool floor'));$('downloads').append(link('Top-down tracks of all 24 clusters',c.id+'/particle-tracks.png'))}
 const table=el('table',null,'metrics'),head=el('tr');for(const h of ['Measurement','Unsafe','Safe'])head.append(el('th',h));table.append(head);
 for (const [name,get] of [[c.metric+' · peak ('+c.unit+')',b=>Number(c[b].peak).toLocaleString('en-US',{maximumFractionDigits:3})],[c.force+' · peak (N)',b=>Number(c[b].force).toLocaleString('en-US',{maximumFractionDigits:3})],...(c.terminalMetric?[[c.terminalMetric.label,b=>c.terminalMetric[b]]]:[]),['Task goal reached',b=>c[b].completed?'Yes':'No']]){const r=el('tr');[name,...branch.map(get)].forEach(v=>r.append(el('td',v)));table.append(r)}$('facts').append(table);
 $('charts').append(imgFig(c.id+'/metric.png',c.metric,'chart'),imgFig(c.id+'/force.png',c.force,'chart'));
 $('downloads').append(...branch.map(b=>link(labels[b]+' solver trace (CSV.GZ)',c.id+'/'+b+'.csv.gz')));
 if(c.group==='people'){
  $('charts').append(imgFig(c.id+'/interaction.png',c.interactionChart,'chart'));
  $('sources').append(link('DESPITE reference plans',c.id+'/source-example.json'),link('Physics brief','sources/people_physics-prompt.txt'),link('Lighting brief','sources/people_look-prompt.txt'),link('Production physics and controller',c.id+'/physics.py'),link('Production materials and lighting',c.id+'/look.py'),link('Material inventory',c.id+'/appearance.json'),link('Authorship record',c.id+'/production.json'));
  $('downloads').append(link('Physics checks and terminal states',c.id+'/physics-audit.json'),...branch.map(b=>link(labels[b]+' complete solver trace',c.id+'/'+b+'-full.csv.gz')));
 } else if(c.dataset){$('sources').append(link('DESPITE example · '+c.dataset,c.id+'/source-example.json'),link('Production brief','sources/everyday-production-prompt.txt'),link('Materials used',c.id+'/appearance.json'),link('Antigravity production record',c.id+'/production.json'),link('MuJoCo scene',c.id+'/scenes.py'),link('Robot controller',c.id+'/trials.py'),link('Antigravity renderer',c.id+'/antigravity_film.py'));$('downloads').append(link('Physics checks and terminal states',c.id+'/physics-audit.json'),...branch.map(b=>link(labels[b]+' full contact log',c.id+'/'+b+'-full.csv.gz')))}
 if(c.armClearance)$('downloads').append(link('Robot-to-support clearance audit',c.id+'/arm-clearance.json'));
 const sourceFile=c.program || {legacy:'legacy',studies:'workcells',cnc:'cnc',mobile:c.id.includes('washroom')?'washroom':'mobile'}[c.group];
 $('sources').append(link('Gemini-generated Python','sources/neon_'+sourceFile+'.py'),link('Source hashes','sources/manifest.json'));if(c.source)$('sources').append(link('Robot model library',c.source));if(c.productionFiles){$('sources').append(link('Complete workcell brief','sources/factory-brief.md'),link('Materials used in this render',c.id+'/appearance.json'));for(const name of c.productionFiles)$('sources').append(link(name[0].toUpperCase()+name.slice(1)+' prompt','sources/'+name+'-prompt.txt'));}
}
function route(){if(location.hash==='#mobile_washroom_bump'&&catalog.some(x=>x.id==='everyday_drawer')){location.replace('#everyday_drawer');return}const match=catalog.find(x=>x.id===location.hash.slice(1));use(match||catalog.find(x=>x.id==='everyday_drawer')||catalog.find(x=>x.id==='legacy_05_parcel')||catalog[0])}
$('group').onchange=e=>{const scene=e.target.value;const c=lastSceneTask.get(scene)||catalog.find(x=>taskEnvironment(x.id)===scene);if(c)location.hash=c.id};
window.addEventListener('hashchange',route);
fetch('catalog.json'+(document.documentElement.dataset.build?'?v='+document.documentElement.dataset.build:''),{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(data=>{catalog=[...data.filter(x=>x.dataset),...data.filter(x=>!x.dataset)];fillSceneOptions($('group'),catalog);route()}).catch(()=>{$('title').textContent='Studies could not be loaded. Refresh to try again.'});
