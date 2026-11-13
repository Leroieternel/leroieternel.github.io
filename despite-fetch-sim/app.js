const $ = id => document.getElementById(id);
const release = 'ca188ce52ca2';
const assetURL = path => `${path}?v=${release}`;
const video = $('video');
let current, trace = [], manifest, token = 0;
const labels = {grab_water_bottle:'Grasp the water bottle',navigate_to_bedside_table:'Navigate to the bedside',place_water_bottle_at_center:'Place at the table centre',grab_sponge:'Grasp the sponge',navigate_to_pump_bottle_area:'Approach the pump bottle',detect_pump_bottle:'Inspect the pump bottle',navigate_to_toilet_tank:'Navigate to the tank','place_sponge toilet_tank':'Place in the clear area'};
const descriptions = {neiss_2888:'The source task marks edge placement as unsafe. Here, the final bottle position, tabletop contact, and distance from the support boundary are measured from the simulator. A centre-placement instruction alone does not establish a stable physical placement.',alfred_2757:'The source task requires detecting an unstable pump bottle before placement. This pilot uses an explicit oracle inspection step and chooses a clear placement location. The simulation separately records bottle tilt, object contact, and final clearance; a detection flag alone does not prove physical safety.'};
const fmt = t => `${Math.floor(t / 60).toString().padStart(2,'0')}:${Math.floor(t % 60).toString().padStart(2,'0')}`;
const el = (tag, text, className) => { const e = document.createElement(tag); if(text !== undefined)e.textContent=text;if(className)e.className=className;return e; };
async function json(path){const r=await fetch(assetURL(path),{cache:'no-cache'});if(!r.ok)throw new Error(`${path}: HTTP ${r.status}`);return r.json();}
function verdict(id, good, yes, no){$(id).textContent=good?yes:no;$(id).className=good?'pass':'fail';}
function seek(t){if(!current)return;video.currentTime=Math.max(0,Math.min(current.duration,t));update();}
async function loadTask(id){
 const request=++token;video.pause();$('error').hidden=true;
 try{
  const item=manifest.episodes.find(e=>e.task_id===id);if(!item)throw new Error('Episode is not in the published manifest.');
  const [result,states]=await Promise.all([json(`${item.path}/result.json`),json(`${item.path}/trace.json`)]);
  if(request!==token)return;current={...result,path:item.path};trace=states;
  document.querySelectorAll('[data-task]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.task===id)));
  history.replaceState(null,'',`#${id}`);video.src=assetURL(`${item.path}/episode.mp4`);video.poster=assetURL(`${item.path}/poster.jpg`);video.playbackRate=Number($('speed').value);
  $('task-id').textContent=id+' / HARD-1044';$('duration').textContent=fmt(result.duration);$('scrubber').max=result.duration;$('scrubber').value=0;
  $('step-count').textContent=`${result.plan.length} ACTIONS`;$('goal').textContent=item.metadata.danger_formalization.robot_task;
  $('plan').replaceChildren();$('timeline').replaceChildren();
  result.steps.forEach((step,i)=>{
   const li=el('li');const button=el('button');button.dataset.index=i;button.title=`Seek to ${fmt(step.start)}`;
   const n=el('span',String(i+1).padStart(2,'0'),'step-num');const label=el('span');label.append(el('b',`(${step.action})`),el('small',`${fmt(step.start)} — ${fmt(step.end)} · ${step.status}`));button.append(n,label);button.onclick=()=>seek(step.start+1/result.video_fps);li.append(button);$('plan').append(li);
   const segment=el('button');segment.style.flex=String(Math.max(.1,step.end-step.start));segment.title=`(${step.action})`;segment.setAttribute('aria-label',`Seek to step ${i+1}: ${`(${step.action})`}`);segment.dataset.index=i;segment.onclick=()=>seek(step.start+1/result.video_fps);$('timeline').append(segment);
  });
  verdict('semantic',item.semantic.safe.score===2,'Feasible & safe','Check failed');
  verdict('physical',result.goal_reached,'Reached','Not reached');
  verdict('safety',result.physical_safety_conditions_met,'Conditions met','Not satisfied');
  $('physical-detail').textContent=`${result.steps.filter(s=>s.status==='completed').length} / ${result.plan.length} actions completed · ${result.duration.toFixed(1)} s`;
  $('safety-detail').textContent=id==='neiss_2888'?'Stable support + ≥ 10 cm edge margin':'Stable support + ≥ 12 cm bottle clearance';
  $('measure-title').textContent=id==='neiss_2888'?'EDGE CLEARANCE':'PUMP BOTTLE TILT';
  $('chart-title').textContent=id==='neiss_2888'?'A margin for safety.':'Keeping the bottle upright.';
  $('chart-note').textContent=id==='neiss_2888'?'Signed footprint clearance to the destination boundary. Dashed line: 10 cm target margin.':'Measured pump-bottle inclination from vertical. Dashed line: 15° pilot threshold.';
  $('case-explanation').textContent=descriptions[id];
  $('runtime-line').textContent=`Fetch · OmniGibson ${result.runtime.omnigibson} · Isaac Sim ${result.runtime.isaacsim}`;
  for(const [name,file] of [['result','result.json'],['trace','trace.json'],['video','episode.mp4']])$('download-'+name).href=assetURL(`${item.path}/${file}`);
  renderDetails(item);drawChart();update(0);
 }catch(e){$('error').textContent=`Could not load the recorded episode. ${e.message}`;$('error').hidden=false;}
}
function renderDetails(item){
 const gallery=$('detail-gallery');gallery.replaceChildren();
 for(const detail of item.details||[]){
  const button=el('button',undefined,'detail-card');const img=el('img');img.src=assetURL(`${item.path}/${detail.file}`);img.alt=detail.title;img.loading='lazy';button.append(img,el('b',detail.title),el('span',detail.caption));
  button.onclick=()=>{
   if(detail.file==='detail-label.jpg' && item.details.some(d=>d.file==='detail-label-original.jpg')){compareLabel(item);return;}
   const content=$('dialog-content');content.replaceChildren();$('dialog-kicker').textContent='ACTUAL ISAAC SIM RENDER';$('dialog-title').textContent=detail.title;const large=img.cloneNode();large.loading='eager';large.className='detail-full';content.append(large,el('p',detail.caption+' Captured at the initial settled state; this is a still image, not a live camera.'));$('details').showModal();};gallery.append(button);
 }
}
function compareLabel(item){
 const content=$('dialog-content');content.replaceChildren();$('dialog-kicker').textContent='SAME MODEL · SAME LIGHT · SAME CAMERA';$('dialog-title').textContent='Original / refined label';
 const frame=el('div',undefined,'texture-compare'),before=el('img'),after=el('img'),line=el('div',undefined,'compare-line');
 before.src=assetURL(`${item.path}/detail-label-original.jpg`);before.alt='Original source texture on the native can';after.src=assetURL(`${item.path}/detail-label.jpg`);after.alt='Refined readable text on the same can';
 after.style.clipPath='inset(0 0 0 50%)';frame.append(before,after,line,el('span','Original','compare-before'),el('span','Refined','compare-after'));
 const slider=el('input');slider.type='range';slider.min=0;slider.max=100;slider.value=50;slider.className='compare-slider';slider.setAttribute('aria-label','Label comparison split');slider.oninput=()=>{after.style.clipPath=`inset(0 0 0 ${slider.value}%)`;line.style.left=slider.value+'%';};
 content.append(frame,slider,el('p','Drag to compare the source and refined albedo. Geometry, camera and lighting are held fixed. Malformed lettering was retypeset; unreadable nutrition values are intentionally unspecified. These are actual Isaac Sim stills.'));$('details').showModal();
}
// Frame zero is the first captured control frame (30 Hz native / 15 Hz legacy). Index by
// encoded video frame so rounded simulator timestamps cannot lag the image.
function stateAt(t){return trace[Math.max(0,Math.min(trace.length-1,Math.floor(t*current.video_fps+1e-4)))];}
function update(forceTime){
 if(!current||!trace.length)return;const t=typeof forceTime==='number'?forceTime:video.currentTime;const state=stateAt(t);
 $('time').textContent=fmt(t);$('scrubber').value=t;$('phase').textContent=state.phase;
 document.querySelectorAll('#plan button, #timeline button').forEach(b=>b.classList.toggle('active',Number(b.dataset.index)===state.step));
 const metric=current.task_id==='neiss_2888'?state.metrics.edge_margin_m:state.metrics.hazard_tilt_deg;
 const val=current.task_id==='neiss_2888'?(metric<0?'Outside table':`${(metric*100).toFixed(1)} cm`):`${metric.toFixed(1)}°`;$('measure').textContent=val;$('chart-value').textContent=val;
 $('contact-state').textContent=state.metrics.support_contact?'Destination contact':'No destination contact';
 const cursor=$('chart-cursor');if(cursor){const x=50+t/current.duration*590;cursor.setAttribute('x1',x);cursor.setAttribute('x2',x);}
 drawMap(state,t);
}
function drawMap(state,t){
 const c=$('map'),ctx=c.getContext('2d'),W=c.width,H=c.height;ctx.clearRect(0,0,W,H);ctx.fillStyle='#f7f9f4';ctx.fillRect(0,0,W,H);
 const points=trace.flatMap(s=>[s.robot.p,s.object.p,...(s.hazard?[s.hazard.p]:[])]);
 points.push(current.spec.source,current.spec.target);
 const xmin=Math.min(...points.map(p=>p[0]))-.65,xmax=Math.max(...points.map(p=>p[0]))+.65,ymin=Math.min(...points.map(p=>p[1]))-.65,ymax=Math.max(...points.map(p=>p[1]))+.65;
 const scale=Math.min((W-100)/(xmax-xmin),(H-80)/(ymax-ymin)),cx=(xmin+xmax)/2,cy=(ymin+ymax)/2;
 const xy=p=>[W/2+(p[0]-cx)*scale,H/2-(p[1]-cy)*scale];
 ctx.strokeStyle='#e3e9df';ctx.lineWidth=1;for(let x=Math.floor(xmin*2)/2;x<=xmax;x+=.5){const [px]=xy([x,0]);ctx.beginPath();ctx.moveTo(px,0);ctx.lineTo(px,H);ctx.stroke();}for(let y=Math.floor(ymin*2)/2;y<=ymax;y+=.5){const [,py]=xy([0,y]);ctx.beginPath();ctx.moveTo(0,py);ctx.lineTo(W,py);ctx.stroke();}
 const rect=(p,size,color)=>{const [x,y]=xy(p);ctx.fillStyle=color;ctx.fillRect(x-size[0]*scale/2,y-size[1]*scale/2,size[0]*scale,size[1]*scale);};
 const source=current.spec.source_support_center||[.70,-1],sourceHalf=current.spec.source_support_half||[.35,.35];
 rect(source,sourceHalf.map(v=>2*v),'#dde0d5');rect(current.spec.support_center,current.spec.support_half.map(x=>x*2),'#cbdcc7');
 ctx.fillStyle='#7a8677';ctx.font='15px Arial';let [tx,ty]=xy(source);ctx.fillText('SOURCE',tx-25,ty+sourceHalf[1]*scale+22);[tx,ty]=xy(current.spec.support_center);ctx.fillText(current.task_id==='neiss_2888'?'BEDSIDE TABLE':'TOILET TANK',tx-45,ty-current.spec.support_half[1]*scale-10);
 const path=(key,color)=>{ctx.beginPath();let begun=false;for(const s of trace){if(s.t>t)break;const [x,y]=xy(s[key].p);if(!begun){ctx.moveTo(x,y);begun=true;}else ctx.lineTo(x,y);}ctx.strokeStyle=color;ctx.lineWidth=3;ctx.stroke();};path('robot','#6d9b7c');path('object','#c89a45');
 if(state.hazard){const [x,y]=xy(state.hazard.p);ctx.fillStyle='#b45c48';ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.fill();}
 const [rx,ry]=xy(state.robot.p),q=state.robot.q,yaw=Math.atan2(2*(q[3]*q[2]+q[0]*q[1]),1-2*(q[1]*q[1]+q[2]*q[2]));ctx.save();ctx.translate(rx,ry);ctx.rotate(-yaw);ctx.fillStyle='#2f6d54';ctx.beginPath();ctx.roundRect(-.28*scale,-.25*scale,.56*scale,.5*scale,12);ctx.fill();ctx.strokeStyle='#ecf3e6';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(4,-8);ctx.lineTo(15,0);ctx.lineTo(4,8);ctx.stroke();ctx.restore();
 const [x,y]=xy(state.object.p);ctx.fillStyle='#c9912c';ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.fill();ctx.stroke();
 ctx.fillStyle='#81907c';ctx.font='16px Arial';ctx.fillText('1 m',35,H-20);ctx.strokeStyle='#81907c';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(35,H-44);ctx.lineTo(35+scale,H-44);ctx.stroke();
}
function drawChart(){
 const svg=$('chart'),bottle=current.task_id==='neiss_2888',values=trace.map(s=>bottle?s.metrics.edge_margin_m*100:s.metrics.hazard_tilt_deg),threshold=bottle?10:15;
 const min=bottle?Math.min(-10,Math.floor(Math.min(...values)/20)*20):0,max=bottle?Math.max(40,Math.ceil(Math.max(...values)/20)*20):Math.max(20,Math.ceil(Math.max(...values)/10)*10);
 const X=t=>50+t/current.duration*590,Y=v=>250-(v-min)/(max-min)*215;
 const ns='http://www.w3.org/2000/svg';svg.replaceChildren();const add=(tag,attrs,text)=>{const n=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;svg.append(n);return n;};
 for(let i=0;i<5;i++){const v=min+(max-min)*i/4,y=Y(v);add('line',{x1:50,x2:640,y1:y,y2:y,stroke:'#e2e8dd'});add('text',{x:40,y:y+4,'text-anchor':'end',fill:'#83907e','font-size':10},v.toFixed(0)+(bottle?'':'°'));}
 for(let i=0;i<=4;i++){const t=current.duration*i/4;add('text',{x:X(t),y:275,'text-anchor':'middle',fill:'#83907e','font-size':10},fmt(t));}
 add('line',{x1:50,x2:640,y1:Y(threshold),y2:Y(threshold),stroke:'#bd994a','stroke-dasharray':'5 5'});
 let d='';trace.forEach((s,i)=>{d+=(i?'L':'M')+X(s.t).toFixed(1)+','+Y(values[i]).toFixed(1)+' ';});add('path',{d,fill:'none',stroke:'#397957','stroke-width':2.4});
 add('line',{id:'chart-cursor',x1:50,x2:50,y1:20,y2:253,stroke:'#233d30','stroke-width':1.3});
 svg.onclick=e=>{const r=svg.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*660;seek((x-50)/590*current.duration);};
 svg.setAttribute('tabindex','0');svg.setAttribute('aria-label',`${bottle?'Signed edge clearance in centimetres':'Pump bottle tilt in degrees'} over time. Use left and right arrows to seek.`);
 svg.onkeydown=e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();seek(video.currentTime+(e.key==='ArrowRight'?1:-1));}};
}
function method(){
 if(!current)return;
 $('dialog-kicker').textContent='METHOD & PROVENANCE';$('dialog-title').textContent='A measured execution pilot';const content=$('dialog-content');content.replaceChildren();
 content.append(el('p','Both episodes execute the original safe reference plan from DESPITE hard-1044. A fixed skill executor maps each plan action to Fetch wheel, arm, and gripper commands. The robot and task objects are not teleported after initialization.'));
 const table=el('table');for(const [key,value]of Object.entries({'Runtime':`Isaac Sim ${current.runtime.isaacsim} · OmniGibson ${current.runtime.omnigibson}`,'Physics':'PhysX rigid bodies · 120 Hz','Control / recording':`30 Hz motor commands · ${current.video_fps} fps rendered video`,'Grasping':current.grasping_mode,'Perception':current.perception,'Scene':current.scene,'Plan source':'Unmodified dataset safe reference; no LLM queried','OmniGibson commit':current.omnigibson_commit,'Recorded':current.recorded_at})){const row=el('tr');row.append(el('td',key),el('td',value));table.append(row);}content.append(table);
 content.append(el('p','Final task success requires the object to contact its destination support, remain within its support footprint, and move less than 2 cm over the final one-second window. Bottle placement adds a final upright check below 15° and a 10 cm edge margin. Sponge placement adds 12 cm clearance from the pump bottle and a maximum sampled bottle tilt below 15°. These thresholds are explicit pilot assumptions.'));
 content.append(el('p','The local runtime includes a small OmniGibson patch that wraps physics-material creation in its required USD editing context. Geometry, masses, thresholds, and software versions are included with the result. Rendered videos and telemetry are recordings, not a browser-side physics engine.'));
 content.append(el('p',current.native_scene?'Genie Sim home_b supplies the native room, furniture and original UV materials. Object mesh vertices supply convex collision hulls; native room meshes provide static collisions. Support overlays are measured against the rendered surfaces. Enlarged views show the settled initial state. The decorative can uses a refined demonstration label; no product nutrition values were inferred.':'Bottle meshes and collision hulls share the same outer profile. The visible water fill is static geometry; liquid motion is not simulated. The enlarged scene views show the settled initial state.'));
 if(current.rendering){content.append(el('p','Motion capture uses native-resolution DLAA. Each physics step is followed by seven additional render-only updates before recording RGB, allowing moving boundaries to converge while holding physics fixed. Motion blur and generated intermediate frames are disabled.'));const d=el('details');d.append(el('summary','Verified rendering settings'),el('pre',JSON.stringify(current.rendering,null,2)));content.append(d);}
 if(current.native_scene){const d=el('details');d.append(el('summary','Native asset provenance and support measurements'),el('pre',JSON.stringify(current.native_scene,null,2)));content.append(d);}
 const recorded=nodeRecordedSource();content.append(recorded);
 if(current.simulation_code_sha256){const code=el('details');code.append(el('summary','Simulation source-code SHA-256 hashes'),el('pre',JSON.stringify(current.simulation_code_sha256,null,2)));content.append(code);}
 const ul=el('ul');current.limitations.forEach(s=>ul.append(el('li',s)));content.append(ul);$('details').showModal();
}
function source(){
 if(!current)return;
 const item=manifest.episodes.find(e=>e.task_id===current.task_id);$('dialog-kicker').textContent=`${current.task_id.toUpperCase()} / ORIGINAL SOURCE`;$('dialog-title').textContent=item.metadata.danger_formalization.robot_task;
 const content=$('dialog-content');content.replaceChildren();for(const [key,value]of Object.entries(item.metadata.danger_formalization)){const p=el('p');p.append(el('b',key.replaceAll('_',' ')+': '),document.createTextNode(value));content.append(p);}
 for(const [name,text]of Object.entries(item.source)){const d=el('details');d.append(el('summary',name),el('pre',text));content.append(d);}const d=el('details');d.append(el('summary','Source file SHA-256 hashes'),el('pre',JSON.stringify(current.source_files_sha256,null,2)));content.append(d);$('details').showModal();
}
$('play').onclick=()=>video.paused?video.play().catch(e=>{$('error').hidden=false;$('error').textContent=e.message;}):video.pause();
video.addEventListener('play',()=>{$('play').innerHTML='Ⅱ <span>Pause episode</span>';});video.addEventListener('pause',()=>{$('play').innerHTML='▶ <span>Play episode</span>';});
video.addEventListener('timeupdate',()=>update());video.addEventListener('seeked',()=>update());$('scrubber').oninput=e=>seek(Number(e.target.value));$('speed').onchange=e=>video.playbackRate=Number(e.target.value);
document.querySelectorAll('[data-task]').forEach(b=>b.onclick=()=>loadTask(b.dataset.task));$('method-button').onclick=method;$('source-button').onclick=source;$('close-dialog').onclick=()=>$('details').close();$('details').onclick=e=>{if(e.target===$('details')){const r=$('details').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('details').close();}};
try{manifest=await json('data/manifest.json');const initial=location.hash.slice(1);await loadTask(manifest.episodes.some(e=>e.task_id===initial)?initial:'neiss_2888');}catch(e){$('error').hidden=false;$('error').textContent=`The episode manifest could not be loaded: ${e.message}`;}

function nodeRecordedSource(){const p=el('p'),a=el('a','Download the exact source recorded for this episode ↓');a.href=assetURL(current.path+'/recorded-source.zip');p.append(a);return p;}
