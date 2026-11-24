'use strict';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!=null)x.textContent=text;if(cls)x.className=cls;return x};
const releaseAsset=releaseMediaUrl;
const link=(text,url)=>{const a=el('a',text);a.href=releaseAsset(url);return a};
let catalog=[],current,vids=[],playing=false,handle=0;
const lastSceneTask=new Map();
const branch=['unsafe','safe'], labels={unsafe:'Unsafe',safe:'Safe'};
function halt(){playing=false;cancelAnimationFrame(handle);vids.forEach(v=>v.pause());$('play').textContent='Play together'}
function sync(){if(!playing)return;if(vids.every(atReplayEnd))return halt();syncLiveReplays(vids);handle=requestAnimationFrame(sync)}
function jump(t){for(const v of vids){if(v.readyState>0)v.currentTime=Math.min(t,v.duration);else v.addEventListener('loadedmetadata',()=>v.currentTime=Math.min(t,v.duration),{once:true})}}
$('play').onclick=async()=>{if(playing)return halt();const at=pairPosition(vids);try{await startReplays(vids,at);playing=true;$('play').textContent='Pause both';sync()}catch{halt()}};
$('event').onclick=()=>{halt();jump(current.eventFrameTime??current.event)};
function card(key,title){const article=el('article',null,'card '+key);article.append(el('h3',title));return article}
function imgFig(src,label,cls){const f=el('figure',null,cls),a=link('',src),i=el('img');i.src=releaseAsset(src);i.alt=label;i.loading='lazy';a.append(i);f.append(a,el('figcaption',label));return f}
function use(c){
  renderEventReplay(c.eventReplay,c.film,c.id);
 halt();current=c;const scene=taskEnvironment(c.id);$('group').value=scene;lastSceneTask.set(scene,c);
 $('tasks').replaceChildren(...catalog.filter(x=>taskEnvironment(x.id)===scene).map(x=>{const b=el('button');b.type='button';b.setAttribute('aria-current',String(c.id===x.id));const i=el('img');i.src=releaseAsset(x.id+'/thumb.jpg');i.alt='';b.append(i,el('span',x.title));b.onclick=()=>{location.hash=x.id};return b}));
 $('title').textContent=c.title;$('robot').textContent=c.robot;$('task').textContent=c.description;document.title=c.title+' · Antigravity edition';
 const orig=$('baseline');
 const mainId=c.baseline||(c.dataset?c.id:null);orig.hidden=!mainId;
 if(mainId){orig.textContent=c.dataset?'View on the main site':'View original study ↗';orig.href=mainId.startsWith('archive/')?'../archive/#'+mainId.split('/')[1]:'../#'+mainId;}
 const photos=c.roomPhotographs || (c.photos?[['Room overview','world'],['Second view','aisle']]:[]);
 $('room').hidden=photos.length===0;
 function showPhoto(idx){
   const [label,name]=photos[idx];
   const a=link('',c.id+'/'+name+'.jpg'),im=el('img');
   im.src=releaseAsset(c.id+'/'+name+'-preview.jpg');im.alt=c.title+' · '+label;a.append(im);$('photo').replaceChildren(a);
   ['overview','aisle'].forEach((id,n)=>$(id).setAttribute('aria-pressed',String(idx===n)));
 }
 if(photos.length){
   ['overview','aisle'].forEach((id,n)=>{$(id).textContent=photos[n][0];$(id).onclick=()=>showPhoto(n)});
   showPhoto(0);
 }
 $('productionNote').hidden=!(c.dataset||c.revisionNote);$('editionMethods').hidden=!!(c.dataset||c.revisionNote);
 if(c.revisionNote)$('productionNote').textContent=c.revisionNote;
 else if(c.fluidSurface)$('productionNote').textContent=c.scope+' Antigravity authored the surface-film solver. Codex integrated the scanned bottle and coupled the rigid and liquid models.';
 else if(c.longRank)$('productionNote').textContent=c.scope+' Google Antigravity authored the task programs, geometry generators, room specifications and physical-process helpers. Codex integrated and tested the MuJoCo rollout and rendered its recorded poses in Blender.';
 else if(c.group==='hard1044')$('productionNote').textContent=c.scope+' Google Antigravity authored the task, controller and Blender set. Codex integrated and tuned the generated controllers. MuJoCo produced the trajectories and measurements, and Blender rendered those trajectories.';
 else if(c.group==='shared_spaces')$('productionNote').textContent=c.scope+' Google Antigravity authored the task boards, sets, decision policies and human motion refinements. Codex fitted the library rigs, ran the physics and checked the final films.';
 else if(c.group==='people')$('productionNote').textContent=c.scope+' Google Antigravity (Gemini 4 Neon High) authored the simulation and visual scene. Codex corrected runtime issues, rendered and checked both runs, and published this edition.';
 else if(c.dataset)$('productionNote').textContent='Google Antigravity ran Gemini 4 Neon High on an existing MuJoCo mobile-Panda project. Gemini authored the rooms, Genie Sim surface materials, action sequences and Blender renderer, and revised the robot and tool mechanics during testing. Codex supplied the initial physics setup, ran the generated programs, checked the outputs and published the results. The two DESPITE examples supplied the reference actions. No PDDL planner was used.';
 $('time').textContent='Event at '+c.event.toFixed(2)+' s · '+c.duration.toFixed(2)+' s replay';
 $('notes').textContent=c.notes;$('detail').textContent=c.detail;$('criterion').textContent=c.criterion;
 $('hardware').hidden=!c.hardware;
 if(c.hardware){
  $('mechanismShots').replaceChildren(imgFig(c.id+'/withdrawn.jpg','3.00 s · Bridge withdrawn while the pusher advances'),imgFig(c.id+'/deployed.jpg','5.40 s · Bridge deployed before the carton crosses'));
  const sources=c.mechanismSources||[['Before and after at 3.00 s','fabrication-comparison.jpg'],['Measured plate travel and height','mechanism.png'],['Carton-to-steel force history','steel.png'],['Unsafe steel loads (CSV.GZ)','unsafe-steel.csv.gz'],['Safe steel loads (CSV.GZ)','safe-steel.csv.gz'],['Solver verification','fabrication-audit.json']];
  $('mechanismData').replaceChildren(...sources.map(([title,file])=>link(title,c.id+'/'+file)));
 }
 vids=[];for(const id of ['players','plans','evidence','charts','facts','downloads','sources'])$(id).replaceChildren();
 if(c.filmReview)$('sources').append(link('Review of these two films',c.id+'/'+c.filmReview));
 for(const b of branch){
  const p=card(b,labels[b]+' replay'),v=el('video');v.defaultPlaybackRate=c.nativePlaybackRate||1;v.playbackRate=v.defaultPlaybackRate;v.controls=true;v.playsInline=true;v.preload='metadata';v.poster=releaseAsset(c.id+'/'+b+'_poster.jpg');
  const s=el('source');s.type='video/mp4';s.src=c.film+'/'+b+'.mp4';v.append(s);vids.push(v);p.append(v,el('div',c[b].outcome,'caption'));$('players').append(p);
  const plan=card(b,labels[b]+' plan'),ol=el('ol',null,'steps');for(const step of c[b].steps){const li=el('li');const clock=el(c.longRank||c.group==='shared_spaces'?'button':'span',Number(step.t).toFixed(2)+' s',c.longRank||c.group==='shared_spaces'?'step-seek':'clock');
    if(c.longRank||c.group==='shared_spaces'){clock.type='button';clock.setAttribute('aria-label','Seek '+b+' replay to '+step.text);clock.onclick=()=>{halt();if(v.readyState>=1)v.currentTime=step.t;else v.addEventListener('loadedmetadata',()=>v.currentTime=step.t,{once:true})}}
    li.append(clock,el('span',step.text));ol.append(li)}plan.append(ol);$('plans').append(plan);
  $('evidence').append(imgFig(c.id+'/detail_'+b+'.jpg',labels[b]+' event view'));
 }
 if(c.spatialMission){$('charts').append(imgFig(c.id+'/route.png',c.layoutLegend,'chart'));$('downloads').append(link('Spatial mission measurements',c.id+'/results.json'),link('Replay trajectories and models','sources/spatial-mobile-replays.zip'))}
 if(c.spatialLayout){
   $('charts').append(imgFig(c.id+'/layout.png',c.layoutLegend,'chart'));
   $('downloads').append(link('Station coordinates and path measurements',c.id+'/layout.json'),link('MuJoCo model (XML.GZ)',c.id+'/scene.xml.gz'),link('Planning and replay source','sources/spatial-layout-source.zip'));
 }
 if(c.fluidSurface){
  if(c.firstTrickle){$('charts').append(imgFig(c.id+'/first-trickle.png','Where the first trickle lands','chart'));$('downloads').append(link('Offset pour · first-hit log',c.id+'/unsafe-first-contacts.csv'),link('Bowl wall geometry checks',c.id+'/wall-audit.json'))}
  for(const b of branch)$('evidence').append(imgFig(c.id+'/end_'+b+'.jpg',b==='safe'?'After withdrawal · milk stays in the bowl':'After withdrawal · milk pools on the worktop'));
  $('charts').append(imgFig(c.id+'/volume.png','Milk collected in the bowl and on the counter','chart'));
  $('downloads').append(...branch.map(b=>link(labels[b]+' volume balance and forces (CSV)',c.id+'/'+b+'-flow.csv')));
  $('sources').append(link('Genie Sim bottle and texture record',c.id+'/bottle-source.json'),link('Bottle discharge model',c.id+'/outlet.py'),link('Jet and surface coupling',c.id+'/coupling.py'));
 }
 if(c.id==='everyday_pool'){for(const b of branch)$('evidence').append(imgFig(c.id+'/end_'+b+'.jpg',b==='safe'?'After tool return · grit in the collection pan':'After tool return · grit on the pool floor'));$('downloads').append(link('Top-down tracks of all 24 clusters',c.id+'/particle-tracks.png'))}
 if(c.objectActionSequence){
  $('evidence').append(imgFig(c.id+'/sequence.jpg',c.objectActionSequence));
  if(c.id==='long_bddl_839')$('downloads').append(link('Flap contact, opening angle and final object supports',c.id+'/carton-contact.json'));
  if(c.id==='hard_alfred_2345')$('sources').append(link('Scanned alarm clock and digital wristwatch sources',c.id+'/timepiece-sources.json'));
 }
 const table=el('table',null,'metrics'),head=el('tr');for(const h of ['Measurement','Unsafe','Safe'])head.append(el('th',h));table.append(head);
 for (const [name,get] of [[c.metric+' · peak ('+c.unit+')',b=>Number(c[b].peak).toLocaleString('en-US',{maximumFractionDigits:3})],(c.group==='shared_spaces'&&!c.hasContact?['Closest person clearance (m)',b=>c[b].gap]:[c.force+' · peak (N)',b=>Number(c[b].force).toLocaleString('en-US',{maximumFractionDigits:3})]),...(c.terminalMetric?[[c.terminalMetric.label,b=>c.terminalMetric[b]]]:[]),[c.completionLabel || (c.longRank?'All source steps visited':(c.group==='shared_spaces'?'Safety criterion met':'Task goal reached')),b=>c[b].completed?'Yes':'No']]){const r=el('tr');[name,...branch.map(get)].forEach(v=>r.append(el('td',v)));table.append(r)}$('facts').append(table);
 if(c.motionAudit)$('downloads').append(link('Measured motion and support',c.id+'/motion-audit.json'),link('Updated simulation and rendering source',c.id+'/revision-source.zip'));
 if(c.seatTravel){
  $('charts').append(imgFig(c.id+'/seat-travel.png','Chair and loose cushion displacement (mm)','chart'));
  for(const b of branch)$('downloads').append(link(labels[b]+' chair and cushion positions',c.id+'/'+b+'-seat.csv'));
 }
 if(c.objectContactRecord)$('downloads').append(link(c.objectContactRecord[0],c.id+'/'+c.objectContactRecord[1]));
 $('charts').append(imgFig(c.id+'/metric.png',c.metric,'chart'),imgFig(c.id+'/force.png',c.force,'chart'));
 $('downloads').append(...branch.map(b=>link(labels[b]+' solver trace (CSV.GZ)',c.id+'/'+b+'.csv.gz')));
 if(c.consequence){
  $('evidence').append(imgFig(c.id+'/sequence.jpg',c.sequenceCaption));
  if(c.stanceCaption)$('evidence').append(imgFig(c.id+'/stance-comparison.jpg',c.stanceCaption));
  $('charts').append(imgFig(c.id+'/reaction.png',c.reactionChart,'chart'));
  $('sources').append(link('Antigravity revision prompt',c.id+'/revision-prompt.txt'),link('Revision source and authoring records','sources/shared-outcomes-authoring.zip'),link('Human performance and timing',c.id+'/performance.json'));
  if(c.id==='shared_bank')$('downloads').append(link('Independent view from the queue',c.id+'/observer-check.json'));
 }
 if(c.motionReview)$('downloads').append(link('Human motion before and after',c.id+'/motion-comparison.jpg'),link('Human movement and contact audit',c.id+'/human-motion.json'),link('Review all ten human performances','sources/shared-motion-review.html'));
 if(c.group==='shared_spaces'){
  $('sources').append(link('DESPITE source and adaptation',c.id+'/source-example.json'),link('Genie Sim materials and lighting',c.id+'/appearance.json'),link(c.consequence?'Initial scene prompts':'Original Antigravity prompts','sources/shared-spaces-prompts.txt'),link('Scripts and authoring records','sources/shared-spaces-authoring.zip'),link('Production record',c.id+'/production.json'));
  $('downloads').append(link('Physics and terminal states',c.id+'/physics-audit.json'),link('Render-space mesh checks',c.id+'/mesh-check.json'),link('Video verification',c.id+'/video-verification.json'));
 } else if(c.group==='people'){
  if(c.performance){$('evidence').append(imgFig(c.id+'/cup-sequence.jpg','Reach, lift, sip and return'));$('downloads').append(link('Hand and cup mesh checks',c.id+'/grip-accepted.json'),link('Frame-by-frame handle clearance',c.id+'/grip-clearance.csv'));$('sources').append(link('Antigravity character performance',c.id+'/neon_cafe_performance.py'))}
  $('charts').append(imgFig(c.id+'/interaction.png',c.interactionChart,'chart'));
  $('sources').append(link('DESPITE reference plans',c.id+'/source-example.json'),link('Physics brief','sources/people_physics-prompt.txt'),link('Lighting brief','sources/people_look-prompt.txt'),link('Production physics and controller',c.id+'/physics.py'),link('Production materials and lighting',c.id+'/look.py'),link('Material inventory',c.id+'/appearance.json'),link('Authorship record',c.id+'/production.json'));
  $('downloads').append(link('Physics checks and terminal states',c.id+'/physics-audit.json'),...branch.map(b=>link(labels[b]+' complete solver trace',c.id+'/'+b+'-full.csv.gz')));
 } else if(c.productionSource){
  $('sources').append(link('Original DESPITE plans',c.id+'/source-example.json'),link('Production controller, pacing and renderer',c.id+'/'+c.productionSource),link('Geometry, materials and lighting',c.id+'/appearance.json'));
  $('downloads').append(link('MuJoCo robot and task model',c.id+'/scene.xml.gz'),link('Solver measurements and terminal states',c.id+'/physics-audit.json'),link('Replay timing and checks',c.id+'/replay-audit.json'));
 } else if(c.group==='hard1044'){
  $('sources').append(link('Original DESPITE plans',c.id+'/source-example.json'),link('Original benchmark controller',c.id+'/physics.py'),link('Geometry and materials in this film',c.id+'/appearance.json'),link('Robot model assembly','sources/neon_hard1044_models.py'),link('Original room and lighting setup','sources/neon_hard1044_dressing.py'));
  $('downloads').append(link('Run measurements and terminal states',c.id+'/physics-audit.json'),link(c.longRank?'Trajectory and support-contact checks':'Replay and clearance checks',c.id+'/replay-audit.json'),link('Frame verification',c.id+'/video-verification.json'));
 } else if(c.dataset){$('sources').append(link('DESPITE example · '+c.dataset,c.id+'/source-example.json'),link('Production brief','sources/everyday-production-prompt.txt'),link('Materials used',c.id+'/appearance.json'),link('Antigravity production record',c.id+'/production.json'),link('MuJoCo scene',c.id+'/scenes.py'),link('Robot controller',c.id+'/trials.py'),link('Antigravity renderer',c.id+'/antigravity_film.py'));$('downloads').append(link('Physics checks and terminal states',c.id+'/physics-audit.json'),...branch.map(b=>link(labels[b]+' full contact log',c.id+'/'+b+'-full.csv.gz')))}
 if(c.armClearance)$('downloads').append(link('Robot-to-support clearance audit',c.id+'/arm-clearance.json'));
 const sourceFile=c.program || {legacy:'legacy',studies:'workcells',cnc:'cnc',mobile:c.id.includes('washroom')?'washroom':'mobile'}[c.group];
 if(!c.productionSource)$('sources').append(link('Gemini-generated Python',c.consequence?c.id+'/antigravity.py':'sources/neon_'+sourceFile+'.py'));$('sources').append(link('Production record',c.group==='hard1044'||c.group==='shared_spaces'?c.id+'/production.json':'sources/manifest.json'));if(c.source)$('sources').append(link('Robot model library',c.source));if(c.productionFiles){$('sources').append(link('Complete workcell brief','sources/factory-brief.md'),link('Materials used in this render',c.id+'/appearance.json'));for(const name of c.productionFiles)$('sources').append(link(name[0].toUpperCase()+name.slice(1)+' prompt','sources/'+name+'-prompt.txt'));}
}
function route(){if(location.hash==='#mobile_washroom_bump'&&catalog.some(x=>x.id==='everyday_drawer')){location.replace('#everyday_drawer');return}const match=catalog.find(x=>x.id===location.hash.slice(1));use(match||catalog.find(x=>x.id==='everyday_drawer')||catalog.find(x=>x.id==='legacy_05_parcel')||catalog[0])}
$('group').onchange=e=>{const scene=e.target.value;const c=lastSceneTask.get(scene)||catalog.find(x=>taskEnvironment(x.id)===scene);if(c)location.hash=c.id};
window.addEventListener('hashchange',route);
fetch('catalog.json'+(document.documentElement.dataset.build?'?v='+document.documentElement.dataset.build:''),{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(data=>{catalog=[...data.filter(x=>x.dataset),...data.filter(x=>!x.dataset)];registerStudyScenes(catalog);fillSceneOptions($('group'),catalog);route()}).catch(()=>{$('title').textContent='Studies could not be loaded. Refresh to try again.'});
