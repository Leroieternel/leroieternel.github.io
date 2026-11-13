const $=id=>document.getElementById(id), release='31b0520eaa22';
const variants=['safe','unsafe'], videos=Object.fromEntries(variants.map(k=>[k,$(k+'-video')]));
let manifest, selected, records={}, traces={}, request=0, playing=false, loading=true, animation=0, elapsed=0, duration=0, master='safe';
const url=p=>`${p}?v=${release}`;
const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const pretty=s=>s.replaceAll('_',' ').replace(/\b\w/,s=>s.toUpperCase());
const seconds=s=>`${Number(s).toFixed(1)} s`;
async function read(p){const r=await fetch(url(p),{cache:'no-cache'});if(!r.ok)throw Error(`${p}: HTTP ${r.status}`);return r.json();}
function pause(){cancelAnimationFrame(animation);variants.forEach(k=>videos[k].pause());playing=false;$('play').textContent='Play both';}
function seek(t){if(loading)return;pause();elapsed=Math.max(0,Math.min(duration,t));variants.forEach(k=>{if(records[k])videos[k].currentTime=Math.min(elapsed,records[k].duration);});update();}
function jumpTo(t,k){seek(t);videos[k].scrollIntoView({behavior:'smooth',block:'center'});}
async function play(){
 if(!selected||loading)return;const pending=request;
 if(elapsed>=duration-1e-6)seek(0);
 try{await Promise.all(variants.map(k=>{const v=videos[k];v.currentTime=Math.min(elapsed,records[k].duration);return k===master||elapsed<records[k].duration-1e-6?v.play():Promise.resolve();}));if(pending!==request)return;playing=true;$('play').textContent='Pause both';tick();}
 catch(e){if(pending===request){pause();showError(e.message);}}
}
function tick(){if(!playing)return;elapsed=videos[master].currentTime;variants.forEach(k=>{if(k!==master&&elapsed<records[k].duration-.03&&Math.abs(videos[k].currentTime-elapsed)>.15)videos[k].currentTime=elapsed;});update();if(videos[master].ended){elapsed=duration;pause();update();}else animation=requestAnimationFrame(tick);}
function showError(s){$('error').hidden=false;$('error').textContent=s;}
function stateAt(k,t){const a=traces[k];if(!a?.length)return null;return a[Math.max(0,Math.min(a.length-1,Math.floor(t*records[k].video_fps)))];}
function metricKey(){const m=selected.case.metric;return m==='bed_contact_frames'?'bed_contact':m==='max_stool_displacement_m'?'stool_displacement_m':m==='min_chair_clearance_m'?'chair_clearance_m':m==='max_navigation_tilt_deg'?'object_tilt_deg':m;}
function metricFormat(v,key=selected.case.metric){if(v===undefined||v===null)return '—';if(key.includes('contact'))return `${v}`;if(key.endsWith('_deg'))return `${Number(v).toFixed(1)}°`;return `${(v*100).toFixed(1)} cm`;}
function metricSeries(k){const key=metricKey();let contacts=0;return traces[k].map(s=>{if(key==='bed_contact'){contacts+=Number(s.metrics[key]);return contacts;}if(['edge_margin_m','reach_distance_m'].includes(key)&&!(s.metrics.support_contact&&!s.metrics.robot_contact&&s.step>0))return null;if(selected.case.metric==='max_navigation_tilt_deg'&&s.phase!=='navigating')return null;return s.metrics[key]*(selected.case.unit==='degrees'?1:100);});}
function outcome(r){
 if(r.status==='blocked')return 'Navigation blocked · later actions not executed';
 if(r.physical_safety_conditions_met)return 'Measured physical conditions met';
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
 $(k+'-progress').textContent=`${seconds(r.duration)} recorded`;
 const list=$(k+'-plan');list.replaceChildren();r.plan.forEach((action,i)=>{const step=r.steps[i],li=node('li'),b=node('button');b.dataset.step=i;b.append(node('span',String(i+1).padStart(2,'0'),'num'));const text=node('span');text.append(node('b',pretty(action)),node('small',step?`${seconds(step.start)} – ${seconds(step.end)} · ${step.status}${executionNote(step)}`:'Not executed'));b.append(text);if(step)b.onclick=()=>seek(step.start+1/r.video_fps);else b.disabled=true;li.append(b);list.append(li);});
 document.getElementById(k+'-staff-events')?.remove();
 if(r.staff_interaction?.events?.length){
  const box=node('div',undefined,'staff-events');box.id=k+'-staff-events';box.append(node('p','Visible checkpoints'));
  const labels={fetch_arrived_at_counter:'Counter arrival',staff_grasp_constraint_engaged:'Staff takes parcel',parcel_lift_verified:'Parcel lifted',parcel_inspected:'Inspection',staff_released_parcel:'Staff release',handoff_ready:'Hands clear',fetch_physical_pickup_completed:'Fetch pickup',parcel_stored:'Inside storage bin',empty_arm_stowed:'Arm folded',robot_parked:'Parked'};
  [...r.staff_interaction.events,...(r.storage_delivery?.events||[])].sort((a,b)=>a.t-b.t).forEach(e=>{if(!labels[e.event])return;const b=node('button',`${labels[e.event]} · ${seconds(e.t)}`);b.onclick=()=>jumpTo(e.t+1/r.video_fps,k);box.append(b);});list.after(box);
 }
 const links=$(k+'-downloads');links.replaceChildren();[['Result JSON','result.json'],['State trace','trace.json'],['Video','episode.mp4'],['Recorded source','recorded-source.zip']].forEach(([label,file])=>{const a=node('a',label+' ↓');a.href=url(`${item.path}/${file}`);links.append(a);});
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
  $('original').textContent=JSON.stringify(item.metadata,null,2);$('source-link').href=url(`data/${item.id}/source/metadata.json`);$('metric-title').textContent=pretty(item.case.metric_title.replace('Final ','').replace('Maximum ',''));
  $('comparison').dataset.scene=item.scene_id;
  $('motion-refinement').hidden=!data.some(d=>d.result.motion_decisions?.some(m=>m.strategy.includes('arm_transfer')));
  $('motion-refinement').querySelector('a').textContent=records.safe.staff_interaction?'Earlier motion-only comparison →':'See the motion refinement →';
  $('motion-refinement').querySelector('span').textContent=records.safe.staff_interaction?' · Archived comparison before the visible staff handoff was added.':' · Same original plan, a short straight approach, and a steadier arm transfer.';
  renderSelectors();history.replaceState(null,'','#'+id);
  variants.forEach(k=>{const v=videos[k];v.src=url(item.variants[k].path+'/episode.mp4');v.poster=url(item.variants[k].path+'/poster.jpg');v.playbackRate=Number($('speed').value);renderPanel(k);});
  drawChart();update();
 }catch(e){if(pending===request)showError(e.message);}
 finally{if(pending===request){loading=false;$('play').disabled=false;$('comparison').setAttribute('aria-busy','false');}}
}
function update(){
 if(!selected)return;$('time-slider').value=elapsed;$('time').textContent=`${elapsed.toFixed(1)} / ${duration.toFixed(1)} s`;
 variants.forEach(k=>{const s=stateAt(k,elapsed),r=records[k];$(k+'-phase').textContent=elapsed>=r.duration-.5/r.video_fps?'Episode ended · '+(r.status==='blocked'?'blocked':'completed'):s.phase;document.querySelectorAll(`#${k}-plan button`).forEach(b=>b.classList.toggle('active',Number(b.dataset.step)===s.step));});
 const cursor=$('chart-cursor');if(cursor)cursor.setAttribute('x1',60+elapsed/duration*635),cursor.setAttribute('x2',60+elapsed/duration*635);drawMap();
}
function drawChart(){
 const svg=$('chart');svg.replaceChildren();const data=Object.fromEntries(variants.map(k=>[k,metricSeries(k)]));const contact=selected.case.metric.includes('contact');const degrees=selected.case.unit==='degrees';const threshold=selected.case.threshold*(contact||degrees?1:100);
 const values=[...data.safe,...data.unsafe,threshold].filter(v=>v!==null&&Number.isFinite(v));const lo=Math.min(0,...values),hi=Math.max(contact?5:20,...values)*1.08,span=hi-lo||1;
 const X=t=>60+t/duration*635,Y=v=>235-(v-lo)/span*205;
 const add=(tag,attrs,text)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;svg.append(n);return n;};
 for(let i=0;i<5;i++){const v=lo+span*i/4;add('line',{x1:60,x2:695,y1:Y(v),y2:Y(v),stroke:'#e4eadd'});add('text',{x:49,y:Y(v)+4,'text-anchor':'end','font-size':10,fill:'#829075'},Math.round(v)+(contact?'':degrees?'°':' cm'));}
 for(let i=0;i<=4;i++){const t=duration*i/4;add('text',{x:X(t),y:260,'text-anchor':'middle','font-size':10,fill:'#829075'},t.toFixed(0)+' s');}
 add('line',{x1:60,x2:695,y1:Y(threshold),y2:Y(threshold),stroke:'#b5a357','stroke-dasharray':'6 5'});
 variants.forEach(k=>{let d='',connected=false;traces[k].forEach((s,i)=>{if(data[k][i]===null){connected=false;return;}d+=(connected?'L':'M')+X(s.t).toFixed(2)+','+Y(data[k][i]).toFixed(2);connected=true;});add('path',{d,fill:'none',stroke:k==='safe'?'#467a54':'#b2764d','stroke-width':2});});
 add('line',{id:'chart-cursor',x1:60,x2:60,y1:20,y2:240,stroke:'#254033','stroke-width':1});
 svg.onclick=e=>{const b=svg.getBoundingClientRect();seek(((e.clientX-b.left)/b.width*720-60)/635*duration);};
 svg.onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();seek(elapsed+(e.key==='ArrowRight'?1:-1));}};
}
function drawMap(){
 const canvas=$('map'),c=canvas.getContext('2d'),W=canvas.width,H=canvas.height;c.clearRect(0,0,W,H);
 const s=records.safe.spec;const bounds=s.map_bounds||[-.25,1.48,.05,3.5],scale=Math.min((W-80)/(bounds[1]-bounds[0]),(H-55)/(bounds[3]-bounds[2]));const left=(W-(bounds[1]-bounds[0])*scale)/2;
 const xy=p=>[left+(p[0]-bounds[0])*scale,H-25-(p[1]-bounds[2])*scale];
 const rect=(lo,hi,fill,label)=>{const a=xy([lo[0],hi[1]]),b=xy([hi[0],lo[1]]);c.fillStyle=fill;c.fillRect(a[0],a[1],b[0]-a[0],b[1]-a[1]);if(label){c.fillStyle='#809274';c.font='10px system-ui';c.fillText(label,a[0]+4,a[1]+15);}};
 if(s.map_objects)s.map_objects.forEach(o=>rect(o.lo,o.hi,'#e3e5d8',o.label));
 else{rect([-.25,.36],[-.035,2.40],'#d8dfcf','SOFA');rect([1.143,1.345],[1.48,3.42],'#e8e4d8','BED');}
 rect(s.source_support_center.map((v,i)=>v-s.source_support_half[i]),s.source_support_center.map((v,i)=>v+s.source_support_half[i]),'#e2d6c4','SOURCE');
 rect(s.support_center.map((v,i)=>v-s.support_half[i]),s.support_center.map((v,i)=>v+s.support_half[i]),'#d6e0ce',s.storage_bin?'STORAGE BIN':'TARGET');
 if(s.stool){const p=s.stool.position;rect([p[0]-.18,p[1]-.14],[p[0]+.18,p[1]+.14],'#e5d6c4','STOOL');}
 variants.forEach(k=>{c.beginPath();let started=false;traces[k].forEach(s=>{if(s.t>elapsed)return;const p=xy(s.robot.p);if(!started)c.moveTo(...p),started=true;else c.lineTo(...p);});c.strokeStyle=k==='safe'?'#467a54':'#b2764d';c.lineWidth=k==='safe'?3:2;c.setLineDash(k==='safe'?[]:[5,3]);c.stroke();c.setLineDash([]);const s=stateAt(k,elapsed),p=xy(s.robot.p),q=s.robot.q,yaw=Math.atan2(2*(q[3]*q[2]+q[0]*q[1]),1-2*(q[1]**2+q[2]**2));c.save();c.translate(...p);c.rotate(-yaw);c.fillStyle=k==='safe'?'#467a54':'#b2764d';c.beginPath();c.moveTo(13,0);c.lineTo(-8,-7);c.lineTo(-5,0);c.lineTo(-8,7);c.closePath();c.fill();c.restore();});
 variants.forEach(k=>{const p=xy(stateAt(k,elapsed).object.p);c.fillStyle=k==='safe'?'#467a54':'#b2764d';c.strokeStyle='white';c.lineWidth=1.5;c.beginPath();c.arc(...p,4.5,0,Math.PI*2);c.fill();c.stroke();});
 if(selected.id==='neiss_27998'){const anchor=xy(s.reach_anchor);c.fillStyle='#5e6684';c.beginPath();c.arc(...anchor,4,0,Math.PI*2);c.fill();c.font='9px system-ui';c.fillText('REACH ORIGIN',anchor[0]-60,anchor[1]-12);variants.forEach(k=>{const end=xy(stateAt(k,elapsed).object.p);c.strokeStyle=k==='safe'?'#467a54':'#b2764d';c.setLineDash([3,4]);c.beginPath();c.moveTo(...anchor);c.lineTo(...end);c.stroke();c.setLineDash([]);});}
 if(s.stool){variants.forEach(k=>{const point=stateAt(k,elapsed).stool;if(!point)return;const p=xy(point.p);c.strokeStyle=k==='safe'?'#467a54':'#b2764d';c.lineWidth=2;c.beginPath();c.arc(...p,8,0,Math.PI*2);c.stroke();});}
 c.strokeStyle='#87967b';c.lineWidth=1;c.beginPath();c.moveTo(25,H-18);c.lineTo(25+scale*.5,H-18);c.stroke();c.fillStyle='#87967b';c.font='10px system-ui';c.fillText('0.5 m',25,H-25);
}
$('play').onclick=()=>playing?pause():play();$('restart').onclick=()=>seek(0);$('back').onclick=()=>seek(elapsed-1/30);$('next').onclick=()=>seek(elapsed+1/30);$('time-slider').oninput=e=>seek(Number(e.target.value));
$('speed').onchange=e=>variants.forEach(k=>videos[k].playbackRate=Number(e.target.value));
$('view').onchange=e=>{const mode=e.target.value;$('comparison').classList.toggle('single',mode!=='both');variants.forEach(k=>document.querySelector(`[data-variant="${k}"]`).hidden=mode!=='both'&&k!==mode);};
$('zoom').onclick=()=>{const active=$('comparison').classList.toggle('detail');$('zoom').setAttribute('aria-pressed',String(active));$('zoom').textContent=active?'Show whole room':'Inspect destination';};
$('method').onclick=()=>$('dialog').showModal();$('close').onclick=()=>$('dialog').close();
variants.forEach(k=>{videos[k].onerror=()=>showError('The '+k+' video could not be loaded.');videos[k].onended=()=>{if(k===master){elapsed=duration;pause();update();}};});
function renderSelectors(){
 const rooms=[...new Set(manifest.cases.map(c=>c.scene_id))];$('rooms').replaceChildren();
 rooms.forEach(id=>{const cases=manifest.cases.filter(c=>c.scene_id===id),item=cases[0],b=node('button');b.dataset.room=id;b.setAttribute('aria-pressed',String(selected.scene_id===id));
  const img=node('img');img.src=url(item.variants.safe.path+'/poster.jpg');img.alt=item.scene_title+' rendered in Isaac Sim';img.loading='lazy';
  b.append(img,node('strong',item.scene_title),node('small',`${cases.length} plan ${cases.length===1?'pair':'pairs'} · ${cases.length*2} physical recordings`));b.onclick=()=>loadCase(item.id);$('rooms').append(b);
 });
 $('cases').replaceChildren();manifest.cases.filter(c=>c.scene_id===selected.scene_id).forEach(item=>{const b=node('button');b.role='tab';b.dataset.case=item.id;b.setAttribute('aria-selected',String(item.id===selected.id));b.append(node('span',item.id.toUpperCase()),node('b',item.title));b.onclick=()=>loadCase(item.id);$('cases').append(b);});
}
read('manifest.json').then(m=>{manifest=m;loadCase(m.cases.some(c=>c.id===location.hash.slice(1))?location.hash.slice(1):m.cases[0].id);}).catch(e=>showError(e.message));
