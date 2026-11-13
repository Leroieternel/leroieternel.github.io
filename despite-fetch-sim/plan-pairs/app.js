const $=id=>document.getElementById(id), release='5969a6c191a0';
const variants=['safe','unsafe'], videos=Object.fromEntries(variants.map(k=>[k,$(k+'-video')]));
let manifest, selected, records={}, traces={}, request=0, playing=false, loading=true, animation=0, elapsed=0, duration=0, master='safe', linked=false, focused='safe', playRequest=0;
const url=p=>`${p}?v=${release}`;
const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const pretty=s=>s.replaceAll('_',' ').replace(/\b\w/,s=>s.toUpperCase());
const seconds=s=>`${Number(s).toFixed(1)} s`;
async function read(p){const r=await fetch(url(p),{cache:'no-cache'});if(!r.ok)throw Error(`${p}: HTTP ${r.status}`);return r.json();}
const timeOf=k=>Math.min(videos[k].currentTime||0,records[k]?.duration||0);
function setLinked(value){linked=value;$('link-clocks').checked=value;$('clock-note').textContent=value?'Linked timelines: both recordings share elapsed time. Shorter recordings hold their final frame.':'Independent playback: each video has its own clock. The controls above operate on both; the shared slider seeks both to the same time.';}
function refreshPlayback(){playing=variants.some(k=>!videos[k].paused&&!videos[k].ended);$('play').textContent=playing?'Pause both':'Play both';variants.forEach(k=>$(k+'-play').textContent=videos[k].paused||videos[k].ended?'Play':'Pause');cancelAnimationFrame(animation);if(playing)animation=requestAnimationFrame(tick);}
function pause(){playRequest++;variants.forEach(k=>videos[k].pause());refreshPlayback();}
function seek(t){if(loading)return;pause();elapsed=Math.max(0,Math.min(duration,t));variants.forEach(k=>{if(records[k])videos[k].currentTime=Math.min(elapsed,records[k].duration);});update();}
function seekOne(k,t){if(loading)return;playRequest++;setLinked(false);focused=k;videos[k].pause();videos[k].currentTime=Math.max(0,Math.min(records[k].duration,t));refreshPlayback();update();}
function jumpTo(t,k){seekOne(k,t);videos[k].scrollIntoView({behavior:'smooth',block:'center'});}
function cameraLoading(k,value){$(k+'-player').setAttribute('aria-busy',String(value));document.querySelectorAll(`#${k}-player .video-controls button,#${k}-player .video-controls select,#${k}-player .video-controls input`).forEach(c=>c.disabled=value);}
function switchCamera(k,detail,seekTime=null){
 if(loading)return;const v=videos[k],t=seekTime===null?timeOf(k):seekTime,rate=v.playbackRate,caseRequest=request;
 seekOne(k,t);cameraLoading(k,true);const path=selected.variants[k].path;
 v.onloadedmetadata=()=>{v.onloadedmetadata=null;if(caseRequest!==request)return;v.currentTime=Math.min(t,records[k].duration);v.playbackRate=rate;cameraLoading(k,false);update();};
 v.poster=url(path+(detail?'/liquid-detail-poster.jpg':'/poster.jpg'));
 v.src=url(path+(detail?'/liquid-detail.mp4':'/episode.mp4'));
 v.classList.toggle('cup-camera',detail);v.load();
}
async function playOne(k){
 if(loading)return;setLinked(false);focused=k;const token=++playRequest;
 if(!videos[k].paused){videos[k].pause();refreshPlayback();return;}
 if(timeOf(k)>=records[k].duration-.02)videos[k].currentTime=0;
 try{await videos[k].play();if(token!==playRequest)return;refreshPlayback();}
 catch(e){if(token===playRequest&&e.name!=='AbortError')showError(e.message);}
}
async function play(){
 if(!selected||loading)return;const pending=request,token=++playRequest;
 if(variants.every(k=>timeOf(k)>=records[k].duration-.02)){variants.forEach(k=>videos[k].currentTime=0);elapsed=0;}
 if(linked)variants.forEach(k=>videos[k].currentTime=Math.min(elapsed,records[k].duration));
 try{await Promise.all(variants.map(k=>timeOf(k)<records[k].duration-.02?videos[k].play():Promise.resolve()));if(pending!==request||token!==playRequest)return;refreshPlayback();}
 catch(e){if(pending===request&&token===playRequest&&e.name!=='AbortError'){pause();showError(e.message);}}
}
function tick(){if(!playing)return;if(linked){elapsed=timeOf(master);variants.forEach(k=>{if(k!==master&&elapsed<records[k].duration-.03&&Math.abs(timeOf(k)-elapsed)>.15)videos[k].currentTime=elapsed;});}update();refreshPlayback();}
function showError(s){$('error').hidden=false;$('error').textContent=s;}
function stateAt(k,t){const a=traces[k];if(!a?.length)return null;let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m].t<=t)lo=m+1;else hi=m;}return a[Math.max(0,lo-1)];}
function metricKey(){const m=selected.case.metric;return m==='bed_contact_frames'?'bed_contact':m==='max_stool_displacement_m'?'stool_displacement_m':m==='min_chair_clearance_m'?'chair_clearance_m':m==='max_navigation_tilt_deg'?'object_tilt_deg':m;}
function metricFormat(v,key=selected.case.metric){if(v===undefined||v===null)return '—';if(key.includes('contact'))return `${v}`;if(key.endsWith('_ml'))return `${Number(v).toFixed(1)} ml`;if(key.endsWith('_deg'))return `${Number(v).toFixed(1)}°`;return `${(v*100).toFixed(1)} cm`;}
function metricSeries(k){const key=metricKey();let contacts=0;return traces[k].map(s=>{if(key==='bed_contact'){contacts+=Number(s.metrics[key]);return contacts;}if(['edge_margin_m','reach_distance_m'].includes(key)&&!(s.metrics.support_contact&&!s.metrics.robot_contact&&s.step>0))return null;if(selected.case.metric==='max_navigation_tilt_deg'&&s.phase!=='navigating')return null;return s.metrics[key]*(['degrees','millilitres'].includes(selected.case.unit)?1:100);});}
function outcome(r){
 if(r.status==='blocked')return 'Navigation blocked · later actions not executed';
 if(r.physical_safety_conditions_met)return 'Measured physical conditions met';
 if(r.liquid_simulation&&r.metrics.spilled_volume_ml>=r.liquid_simulation.model.detection_threshold_ml)return 'Liquid spilled · measured physical safety condition violated';
 if(r.goal_reached)return 'Task reached · measured safety condition violated';
 return 'Task goal not reached · inspect the physical trace';
}
function metricCell(label,value,note){const e=node('div',undefined,'metric');e.append(node('small',label),node('b',value),node('span',note));return e;}
function executionNote(step){
 const e=step?.evidence;if(!e)return '';
 if(e.kind==='physical_navigation')return ` · ${e.base_displacement_m.toFixed(2)} m driven`;
 if(e.kind==='scripted_skeletal_actor_with_dynamic_parcel')return ' · visible staff handling';
 if(e.kind==='physical_grasp_after_staff_release')return ' · pickup after staff release';
 if(e.kind==='physical_approach_and_grasp_without_staff_processing')return ' · approach + direct pickup';
 if(e.kind==='inside_bin_then_stow_and_park')return ' · inside bin → reverse → fold arm → parked';
 return '';
}
function renderPanel(k){
 const r=records[k], item=selected.variants[k];const status=$(k+'-outcome');status.textContent=outcome(r);status.className='outcome'+(r.physical_safety_conditions_met?'':' bad');
 $(k+'-metrics').replaceChildren(metricCell(selected.case.metric_title,metricFormat(r.metrics[selected.case.metric]),`${selected.case.comparison} ${metricFormat(selected.case.threshold)} · pilot condition`),metricCell(r.storage_delivery?'Storage placement':'Physical task goal',r.storage_delivery?(r.storage_delivery.inside_bin_verified?'Inside the bin':'Not contained'):(r.goal_reached?'Reached':'Not reached'),`${r.steps.filter(s=>s.status==='completed').length} / ${r.plan.length} actions completed`));
 if(r.scene_id==='lobby')$(k+'-metrics').append(r.staff_interaction?metricCell('Visible staff handoff',r.staff_interaction.processing_completed?'Executed':'Bypassed','Scripted character · dynamic parcel'):metricCell('Staff-processing fixture',r.social_protocol_observed?'Recorded':'Skipped','Scripted protocol state · separate from physics'));
 if(r.storage_delivery)$(k+'-metrics').append(metricCell('Final robot pose',r.storage_delivery.robot_parked?'Parked · arm folded':'Not parked',`${(r.metrics.parking_error_m*100).toFixed(1)} cm from waiting position`));
 else if(r.motion_decisions?.some(d=>d.strategy.includes('arm_transfer')))$(k+'-metrics').append(metricCell('Delivery approach',r.motion_decisions.at(-1).strategy==='within_reach_arm_transfer'?'Arm transfer · base held':'Straight dock + arm transfer',`${r.metrics.delivery_base_rotation_deg.toFixed(1)}° measured base rotation · original plan unchanged`));
 if(r.liquid_simulation)$(k+'-metrics').append(metricCell('Liquid reached the floor',metricFormat(r.metrics.floor_liquid_ml,'floor_liquid_ml'),'Measured particle volume · no injury model'),metricCell('Minimum obstacle clearance',metricFormat(r.metrics.min_obstacle_clearance_m,'min_obstacle_clearance_m'),'Physical BEHAVIOR footstool · 0.29 m chassis disc'));
 $(k+'-progress').textContent=`${seconds(r.duration)} recorded`;
 const originalActions=item.original_plan||item.plan||selected.metadata.reference_feasible_plans[k];
 const rawActions=typeof originalActions==='string'?originalActions.match(/\([^()]+\)/g):null;
 const violations=new Set((item.semantic?.violation_steps||[]).map(v=>v.step_index));
 const list=$(k+'-plan');list.replaceChildren();r.plan.forEach((action,i)=>{const step=r.steps[i],li=node('li'),b=node('button');b.dataset.step=i;
  if(k==='unsafe'&&violations.has(i)){b.classList.add('violation');b.title='Safety violation in the original task rules. '+selected.metadata.danger_formalization.cause_of_danger;b.setAttribute('aria-label',`Step ${i+1}: ${rawActions?.[i]||`(${action})`}. Safety violation in the original task rules.`);}
  b.append(node('span',String(i+1).padStart(2,'0'),'num'));const text=node('span');text.append(node('code',rawActions?.[i]||`(${action})`,'plan-action'),node('small',step?`${seconds(step.start)} – ${seconds(step.end)} · ${step.status}${executionNote(step)}`:'Not executed'));b.append(text);if(step)b.onclick=()=>seekOne(k,step.start+1/r.video_fps);else b.disabled=true;li.append(b);list.append(li);});
 $(k+'-seek').max=r.duration;$(k+'-seek').step=1/r.video_fps;$(k+'-seek').value=0;
 document.getElementById(k+'-staff-events')?.remove();
 if(r.staff_interaction?.events?.length){
  const box=node('div',undefined,'staff-events');box.id=k+'-staff-events';box.append(node('p','Visible checkpoints'));
  const labels={fetch_arrived_at_counter:'Counter arrival',staff_grasp_constraint_engaged:'Staff takes parcel',parcel_lift_verified:'Parcel lifted',parcel_inspected:'Inspection',staff_released_parcel:'Staff release',handoff_ready:'Hands clear',fetch_physical_pickup_completed:'Fetch pickup',parcel_stored:'Inside storage bin',empty_arm_stowed:'Arm folded',robot_parked:'Parked'};
  [...r.staff_interaction.events,...(r.storage_delivery?.events||[])].sort((a,b)=>a.t-b.t).forEach(e=>{if(!labels[e.event])return;const b=node('button',`${labels[e.event]} · ${seconds(e.t)}`);b.onclick=()=>jumpTo(e.t+1/r.video_fps,k);box.append(b);});list.after(box);
 }
 document.getElementById(k+'-liquid-events')?.remove();
 document.getElementById(k+'-liquid-badge')?.remove();
 document.getElementById(k+'-camera-control')?.remove();
 videos[k].classList.remove('cup-camera');videos[k].onloadedmetadata=null;cameraLoading(k,false);
 if(r.liquid_simulation){
  const box=node('div',undefined,'staff-events');box.id=k+'-liquid-events';box.append(node('p','Physical evidence · uncalibrated fluid model'));
  const checkpoints=[{t:0,label:'Inspect the obstacle',view:'room'},...r.liquid_simulation.events.map(e=>({t:e.t,label:'First measured spill',view:'cup'})),{t:r.duration-.1,label:'Inspect the final liquid state',view:'room'}];
  checkpoints.forEach(e=>{const b=node('button',`${e.label} · ${seconds(e.t)}`);b.onclick=()=>{const t=Math.min(r.duration,e.t+(e.t>0?1/r.video_fps:0)),select=$(k+'-camera');if(select&&select.value!==e.view){select.value=e.view;switchCamera(k,e.view==='cup',t);videos[k].scrollIntoView({behavior:'smooth',block:'center'});}else jumpTo(t,k);};box.append(b);});list.after(box);
  const obstacle=node('a','View the physical stool →');obstacle.href=url(item.path+'/detail-obstacle.jpg');obstacle.target='_blank';obstacle.rel='noopener';box.append(obstacle);
  const badge=node('span','','liquid-badge');badge.id=k+'-liquid-badge';videos[k].parentElement.append(badge);
  if(r.liquid_simulation.evidence_camera){
   const label=node('label','Camera ','camera-control');label.id=k+'-camera-control';
   const select=node('select');select.id=k+'-camera';select.setAttribute('aria-label',`${k} recording camera`);
   [['room','Whole kitchen'],['cup','Cup close-up']].forEach(([value,text])=>{const option=node('option',text);option.value=value;select.append(option);});
   select.onchange=()=>switchCamera(k,select.value==='cup');label.append(select);$(k+'-speed').parentElement.after(label);
   box.append(node('p','Room and close-up cameras record the same physics. Switching cameras preserves this plan’s time and pauses playback.','evidence-note'));
   if(item.floor_inspection){const a=node('a','Inspect recorded floor droplets · robot hidden →');a.href=url(item.path+'/'+item.floor_inspection.image);a.title=item.floor_inspection.caption;a.target='_blank';a.rel='noopener';box.append(a);}
  }
  const firstSpill=r.liquid_simulation.events[0];
  box.append(node('p',firstSpill?`Observed at ${seconds(firstSpill.t)} during (${r.plan[firstSpill.step_index]}): liquid escaped over the rim. ${r.metrics.floor_liquid_ml.toFixed(1)} ml subsequently reached floor height. Maximum transit tilt: ${r.metrics.max_navigation_tilt_deg.toFixed(1)}°.`:`The recording did not cross the ${r.liquid_simulation.model.detection_threshold_ml.toFixed(1)} ml pilot spill threshold. Measured liquid reaching floor height: ${r.metrics.floor_liquid_ml.toFixed(1)} ml.`,'evidence-note'));
  box.append(node('p',`Initial liquid: ${r.liquid_simulation.initial_volume_ml.toFixed(1)} ml nominal particle volume; cup-body mass: ${(r.physical_parameters.object_mass_kg*1000).toFixed(0)} g (assumed). The source task concerns hot liquid: visible spill is a potential scalding exposure pathway. Temperature, skin contact and injury are not simulated.`,'evidence-note'));
 }
 const links=$(k+'-downloads');links.replaceChildren();[['Result JSON','result.json'],['State trace','trace.json'],['Video','episode.mp4'],['Recorded source','recorded-source.zip']].forEach(([label,file])=>{const a=node('a',label+' ↓');a.href=url(`${item.path}/${file}`);links.append(a);});
 if(r.liquid_simulation){const a=node('a','Fluid particle trace ↓');a.href=url(`${item.path}/${r.liquid_simulation.particle_trace}`);links.append(a);}
 if(selected.execution_audit){const a=node('a','Execution checks ↓');a.href=url(selected.execution_audit);links.append(a);}
}
async function loadCase(id){
 pause();const pending=++request;loading=true;$('play').disabled=true;$('comparison').setAttribute('aria-busy','true');$('error').hidden=true;
 try{
  const item=manifest.cases.find(c=>c.id===id);if(!item)throw Error('This case is not in the paired manifest.');
  const data=await Promise.all(variants.map(async k=>({k,result:await read(item.variants[k].path+'/result.json'),trace:await read(item.variants[k].path+'/trace.json')})));
  if(pending!==request)return;selected=item;records={};traces={};data.forEach(d=>{records[d.k]=d.result;traces[d.k]=d.trace;});
  duration=Math.max(...variants.map(k=>records[k].duration));master=records.safe.duration>=records.unsafe.duration?'safe':'unsafe';elapsed=0;
  $('case-id').textContent=item.id+' / HARD-1044';$('case-title').textContent=item.title;$('question').textContent=item.case.question;
  $('time-slider').max=duration;$('time-slider').value=0;$('grounding').textContent=item.case.grounding;$('limits').textContent=item.case.limits;
  if(records.safe.liquid_simulation)$('grounding').textContent+=' These are route-following limits. The shared final-heading alignment can command up to 0.50 rad/s; the smooth action retains its angular-acceleration limit during alignment.';
  if(records.safe.liquid_simulation)$('limits').textContent+=' The millimetre-scale particle surface shows resolved droplets; thin-film wetting and spreading on the floor have not been calibrated or validated.';
  $('original').textContent=JSON.stringify(item.metadata,null,2);$('source-link').href=url(`data/${item.id}/source/metadata.json`);$('metric-title').textContent=pretty(item.case.metric_title.replace('Final ','').replace('Maximum ',''));
  $('instrumented-case').href=`../safety-pilot/#${id}`;
  $('instrumented-case').textContent=records.safe.liquid_simulation?'Related 12-task pilot · separate settings and measurements →':'New instrumented trials: events, condition changes & repeated seeds →';
  $('comparison').dataset.scene=item.scene_id;
  const runtime=records.safe;
  $('runtime-note').textContent=`Physics: Isaac Sim ${runtime.runtime.isaacsim} / PhysX, ${runtime.physics_hz} Hz. Control: ${runtime.control_hz} Hz, oracle object poses. No LLM is queried. RGB: ${runtime.video_fps} fps, native-resolution DLAA, ${runtime.rendering?.extra_render_updates_per_recorded_frame??7} additional render-only updates per recorded frame.`;
  $('metric-note').textContent=runtime.liquid_simulation?'Cumulative escaped liquid is measured from particle positions throughout the episode. The dashed line is an uncalibrated pilot detection threshold, not an injury threshold.':'Placement clearance and reach conditions are evaluated after release. Chair clearance and obstacle disturbance are monitored throughout execution; cup tilt is evaluated during navigation.';
  $('motion-refinement').hidden=!data.some(d=>d.result.motion_decisions?.some(m=>m.strategy.includes('arm_transfer')));
  $('motion-refinement').querySelector('a').textContent=records.safe.staff_interaction?'Earlier motion-only comparison →':'See the motion refinement →';
  $('motion-refinement').querySelector('span').textContent=records.safe.staff_interaction?' · Archived comparison before the visible staff handoff was added.':' · Same original plan, a short straight approach, and a steadier arm transfer.';
  renderSelectors();history.replaceState(null,'','#'+id);
  variants.forEach(k=>{const v=videos[k];v.src=url(item.variants[k].path+'/episode.mp4');v.poster=url(item.variants[k].path+'/poster.jpg');v.playbackRate=Number($('speed').value);$(k+'-speed').value=$('speed').value;renderPanel(k);});
  drawChart();update();
 }catch(e){if(pending===request)showError(e.message);}
 finally{if(pending===request){loading=false;$('play').disabled=false;$('comparison').setAttribute('aria-busy','false');}}
}
function update(){
 if(!selected)return;if(!linked)elapsed=timeOf(focused);$('time-slider').value=elapsed;$('time').textContent=linked?`${elapsed.toFixed(1)} / ${duration.toFixed(1)} s`:`Safe ${timeOf('safe').toFixed(1)} s · Unsafe ${timeOf('unsafe').toFixed(1)} s`;
 variants.forEach(k=>{const t=timeOf(k),s=stateAt(k,t),r=records[k];if(!s)return;const badge=$(k+'-liquid-badge');if(badge){badge.textContent=`Spilled ${Number(s.metrics.spilled_volume_ml).toFixed(1)} ml · floor ${Number(s.metrics.floor_liquid_ml).toFixed(1)} ml`;badge.classList.toggle('spill',s.metrics.spilled_volume_ml>=r.liquid_simulation.model.detection_threshold_ml);}$(k+'-phase').textContent=t>=r.duration-.5/r.video_fps?'Episode ended · '+(r.status==='blocked'?'blocked':'completed'):s.phase;$(k+'-seek').value=t;$(k+'-seek').setAttribute('aria-valuetext',`${t.toFixed(1)} of ${r.duration.toFixed(1)} seconds`);$(k+'-time').textContent=`${t.toFixed(1)} / ${r.duration.toFixed(1)} s`;document.querySelectorAll(`#${k}-plan button`).forEach(b=>b.classList.toggle('active',Number(b.dataset.step)===s.step));const cursor=$('chart-cursor-'+k);if(cursor){cursor.setAttribute('x1',60+t/duration*635);cursor.setAttribute('x2',60+t/duration*635);}});drawMap();
}
function drawChart(){
 const svg=$('chart');svg.replaceChildren();const data=Object.fromEntries(variants.map(k=>[k,metricSeries(k)]));const contact=selected.case.metric.includes('contact');const degrees=selected.case.unit==='degrees',liquid=selected.case.unit==='millilitres';const threshold=selected.case.threshold*(contact||degrees||liquid?1:100);
 const values=[...data.safe,...data.unsafe,threshold].filter(v=>v!==null&&Number.isFinite(v));const lo=Math.min(0,...values),hi=Math.max(contact?5:liquid?1:20,...values)*1.08,span=hi-lo||1;
 const X=t=>60+t/duration*635,Y=v=>235-(v-lo)/span*205;
 const add=(tag,attrs,text)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;svg.append(n);return n;};
 for(let i=0;i<5;i++){const v=lo+span*i/4;add('line',{x1:60,x2:695,y1:Y(v),y2:Y(v),stroke:'#e4eadd'});add('text',{x:49,y:Y(v)+4,'text-anchor':'end','font-size':10,fill:'#829075'},(liquid?v.toFixed(1):Math.round(v))+(contact?'':degrees?'°':liquid?' ml':' cm'));}
 for(let i=0;i<=4;i++){const t=duration*i/4;add('text',{x:X(t),y:260,'text-anchor':'middle','font-size':10,fill:'#829075'},t.toFixed(0)+' s');}
 add('line',{x1:60,x2:695,y1:Y(threshold),y2:Y(threshold),stroke:'#b5a357','stroke-dasharray':'6 5'});
 variants.forEach(k=>{let d='',connected=false;traces[k].forEach((s,i)=>{if(data[k][i]===null){connected=false;return;}d+=(connected?'L':'M')+X(s.t).toFixed(2)+','+Y(data[k][i]).toFixed(2);connected=true;});add('path',{d,fill:'none',stroke:k==='safe'?'#467a54':'#b2764d','stroke-width':2});});
 variants.forEach(k=>add('line',{id:'chart-cursor-'+k,x1:60,x2:60,y1:20,y2:240,stroke:k==='safe'?'#467a54':'#b2764d','stroke-width':1.5,'stroke-dasharray':k==='safe'?'':'4 3'}));
 svg.onclick=e=>{const b=svg.getBoundingClientRect();seek(((e.clientX-b.left)/b.width*720-60)/635*duration);};
 svg.onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();seek(elapsed+(e.key==='ArrowRight'?1:-1));}};
}
function drawMap(){
 const canvas=$('map'),c=canvas.getContext('2d'),W=canvas.width,H=canvas.height;c.clearRect(0,0,W,H);
 const s=records.safe.spec;const bounds=s.map_bounds||[-.25,1.48,.05,3.5],scale=Math.min((W-80)/(bounds[1]-bounds[0]),(H-55)/(bounds[3]-bounds[2]));const left=(W-(bounds[1]-bounds[0])*scale)/2;
 const xy=p=>[left+(p[0]-bounds[0])*scale,H-25-(p[1]-bounds[2])*scale];
 const rect=(lo,hi,fill,label)=>{const a=xy([lo[0],hi[1]]),b=xy([hi[0],lo[1]]);c.fillStyle=fill;c.fillRect(a[0],a[1],b[0]-a[0],b[1]-a[1]);if(label){c.fillStyle='#809274';c.font='10px system-ui';c.fillText(label,a[0]+4,a[1]+15);}};
 if(s.map_objects)s.map_objects.forEach(o=>rect(o.lo,o.hi,o.label.includes('OBSTACLE')?'#e4c39e':'#e3e5d8',o.label));
 else{rect([-.25,.36],[-.035,2.40],'#d8dfcf','SOFA');rect([1.143,1.345],[1.48,3.42],'#e8e4d8','BED');}
 rect(s.source_support_center.map((v,i)=>v-s.source_support_half[i]),s.source_support_center.map((v,i)=>v+s.source_support_half[i]),'#e2d6c4','SOURCE');
 rect(s.support_center.map((v,i)=>v-s.support_half[i]),s.support_center.map((v,i)=>v+s.support_half[i]),'#d6e0ce',s.storage_bin?'STORAGE BIN':'TARGET');
 if(s.stool){const p=s.stool.position;rect([p[0]-.18,p[1]-.14],[p[0]+.18,p[1]+.14],'#e5d6c4','STOOL');}
 variants.forEach(k=>{c.beginPath();let started=false;traces[k].forEach(s=>{if(s.t>timeOf(k))return;const p=xy(s.robot.p);if(!started)c.moveTo(...p),started=true;else c.lineTo(...p);});c.strokeStyle=k==='safe'?'#467a54':'#b2764d';c.lineWidth=k==='safe'?3:2;c.setLineDash(k==='safe'?[]:[5,3]);c.stroke();c.setLineDash([]);const s=stateAt(k,timeOf(k)),p=xy(s.robot.p),q=s.robot.q,yaw=Math.atan2(2*(q[3]*q[2]+q[0]*q[1]),1-2*(q[1]**2+q[2]**2));c.save();c.translate(...p);c.rotate(-yaw);c.fillStyle=k==='safe'?'#467a54':'#b2764d';c.beginPath();c.moveTo(13,0);c.lineTo(-8,-7);c.lineTo(-5,0);c.lineTo(-8,7);c.closePath();c.fill();c.restore();});
 variants.forEach(k=>{const p=xy(stateAt(k,timeOf(k)).object.p);c.fillStyle=k==='safe'?'#467a54':'#b2764d';c.strokeStyle='white';c.lineWidth=1.5;c.beginPath();c.arc(...p,4.5,0,Math.PI*2);c.fill();c.stroke();});
 if(selected.id==='neiss_27998'){const anchor=xy(s.reach_anchor);c.fillStyle='#5e6684';c.beginPath();c.arc(...anchor,4,0,Math.PI*2);c.fill();c.font='9px system-ui';c.fillText('REACH ORIGIN',anchor[0]-60,anchor[1]-12);variants.forEach(k=>{const end=xy(stateAt(k,timeOf(k)).object.p);c.strokeStyle=k==='safe'?'#467a54':'#b2764d';c.setLineDash([3,4]);c.beginPath();c.moveTo(...anchor);c.lineTo(...end);c.stroke();c.setLineDash([]);});}
 if(s.stool){variants.forEach(k=>{const point=stateAt(k,timeOf(k)).stool;if(!point)return;const p=xy(point.p);c.strokeStyle=k==='safe'?'#467a54':'#b2764d';c.lineWidth=2;c.beginPath();c.arc(...p,8,0,Math.PI*2);c.stroke();});}
 c.strokeStyle='#87967b';c.lineWidth=1;c.beginPath();c.moveTo(25,H-18);c.lineTo(25+scale*.5,H-18);c.stroke();c.fillStyle='#87967b';c.font='10px system-ui';c.fillText('0.5 m',25,H-25);
}
$('play').onclick=()=>playing?pause():play();$('restart').onclick=()=>seek(0);$('back').onclick=()=>seek(elapsed-1/30);$('next').onclick=()=>seek(elapsed+1/30);$('time-slider').oninput=e=>seek(Number(e.target.value));
$('speed').onchange=e=>variants.forEach(k=>{videos[k].playbackRate=Number(e.target.value);$(k+'-speed').value=e.target.value;});
$('link-clocks').onchange=e=>{const t=timeOf(focused),rate=videos[focused].playbackRate;setLinked(e.target.checked);if(linked){variants.forEach(k=>{videos[k].playbackRate=rate;$(k+'-speed').value=String(rate);});$('speed').value=String(rate);seek(t);}};
$('view').onchange=e=>{const mode=e.target.value;$('comparison').classList.toggle('single',mode!=='both');variants.forEach(k=>document.querySelector(`[data-variant="${k}"]`).hidden=mode!=='both'&&k!==mode);};
$('zoom').onclick=()=>{const active=$('comparison').classList.toggle('detail');$('zoom').setAttribute('aria-pressed',String(active));$('zoom').textContent=active?'Show whole room':'Inspect destination';};
$('method').onclick=()=>$('dialog').showModal();$('close').onclick=()=>$('dialog').close();
variants.forEach(k=>{
 const v=videos[k];
 v.onerror=()=>{cameraLoading(k,false);showError('The '+k+' video could not be loaded.');};
 ['play','pause','ended'].forEach(event=>v.addEventListener(event,()=>{refreshPlayback();update();}));
 ['timeupdate','seeked','loadedmetadata'].forEach(event=>v.addEventListener(event,update));
 v.addEventListener('ratechange',()=>$(k+'-speed').value=String(v.playbackRate));
 $(k+'-play').onclick=()=>playOne(k);
 $(k+'-seek').oninput=e=>seekOne(k,Number(e.target.value));
 $(k+'-restart').onclick=()=>seekOne(k,0);
 $(k+'-back-frame').onclick=()=>{if(!loading)seekOne(k,timeOf(k)-1/records[k].video_fps);};
 $(k+'-next-frame').onclick=()=>{if(!loading)seekOne(k,timeOf(k)+1/records[k].video_fps);};
 $(k+'-rewind').onclick=()=>seekOne(k,timeOf(k)-5);
 $(k+'-forward').onclick=()=>seekOne(k,timeOf(k)+5);
 $(k+'-speed').onchange=e=>{setLinked(false);focused=k;v.playbackRate=Number(e.target.value);};
 $(k+'-fullscreen').onclick=()=>toggleFullscreen(k);
});
document.addEventListener('fullscreenchange',()=>variants.forEach(k=>{$(k+'-fullscreen').textContent=document.fullscreenElement===$(k+'-player')?'Exit fullscreen':'Fullscreen';}));
function closeExpanded(){document.querySelectorAll('.fullscreen-fallback').forEach(p=>p.classList.remove('fullscreen-fallback'));document.body.classList.remove('has-expanded-video');variants.forEach(k=>$(k+'-fullscreen').textContent='Fullscreen');}
async function toggleFullscreen(k){
 const player=$(k+'-player');if(player.classList.contains('fullscreen-fallback')){closeExpanded();return;}
 if(document.fullscreenElement===player){await document.exitFullscreen();return;}
 closeExpanded();
 try{if(player.requestFullscreen&&document.fullscreenEnabled){await player.requestFullscreen();return;}}
 catch(e){/* Embedded browsers can disallow native fullscreen. Keep all controls in an expanded viewport. */}
 player.classList.add('fullscreen-fallback');document.body.classList.add('has-expanded-video');$(k+'-fullscreen').textContent='Exit fullscreen';$(k+'-fullscreen').focus();
}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeExpanded();});
setLinked(false);
function renderSelectors(){
 const rooms=[...new Set(manifest.cases.map(c=>c.scene_id))];$('rooms').replaceChildren();
 rooms.forEach(id=>{const cases=manifest.cases.filter(c=>c.scene_id===id),item=cases[0],b=node('button');b.dataset.room=id;b.setAttribute('aria-pressed',String(selected.scene_id===id));
  const img=node('img');img.src=url(item.variants.safe.path+'/poster.jpg');img.alt=item.scene_title+' rendered in Isaac Sim';img.loading='lazy';
  b.append(img,node('strong',item.scene_title),node('small',`${cases.length} plan ${cases.length===1?'pair':'pairs'} · ${cases.length*2} physical recordings`));b.onclick=()=>loadCase(item.id);$('rooms').append(b);
 });
 $('cases').replaceChildren();manifest.cases.filter(c=>c.scene_id===selected.scene_id).forEach(item=>{const b=node('button');b.role='tab';b.dataset.case=item.id;b.setAttribute('aria-selected',String(item.id===selected.id));b.append(node('span',item.id.toUpperCase()),node('b',item.title));b.onclick=()=>loadCase(item.id);$('cases').append(b);});
}
read('manifest.json').then(m=>{manifest=m;loadCase(m.cases.some(c=>c.id===location.hash.slice(1))?location.hash.slice(1):m.cases[0].id);}).catch(e=>showError(e.message));
