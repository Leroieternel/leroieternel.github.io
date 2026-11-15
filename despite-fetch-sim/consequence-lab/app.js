const revision='d6bbc3e4d7c1';
const $=id=>document.getElementById(id),videos=[],finalStates=[];
const get=async p=>{const r=await fetch(`${p}?v=${revision}`);if(!r.ok)throw Error(`${p}: ${r.status}`);return r.json();};
const time=t=>`${Number(t||0).toFixed(1)} s`;
const label={edge_threshold_disturbance_requested:'Threshold → disturbance',physical_tipping_observed:'Measured tipping',physical_fall_observed:'Measured fall',modeled_liquid_spill_started:'Modeled spill begins'};
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function metric(box,title){const cell=node('div');cell.append(node('label',title));const value=node('strong','—');cell.append(value);box.append(cell);return value;}
function locate(trace,t){let a=0,b=trace.length-1;while(a<b){const m=Math.ceil((a+b)/2);if(trace[m].t<=t)a=m;else b=m-1;}return trace[a];}
async function panel(variant,entry){
 const base=entry.path;const [r,trace]=await Promise.all([get(base+'/result.json'),get(base+'/trace.json')]);
 const section=node('article',undefined,'panel '+variant);section.id=variant;section.append(node('h2',variant==='safe'?'Safe reference plan':'Unsafe reference plan'));
 const player=node('div',undefined,'player'),video=node('video');video.id=variant+'-video';video.setAttribute('aria-label',variant+' reference consequence recording');video.controls=true;video.muted=true;video.playsInline=true;video.preload='metadata';video.poster=base+'/poster.jpg?v='+revision;
 const sources={detail:'consequence-detail.mp4',room:'episode.mp4'};video.src=base+'/'+sources.room+'?v='+revision;
 const controls=node('div',undefined,'controls');
 function button(text,fn){const b=node('button',text);b.onclick=fn;controls.append(b);return b;}
 const play=button('Play',()=>video.paused?video.play():video.pause());play.className='primary';
 const seek=t=>{video.pause();video.currentTime=Math.max(0,Math.min(r.duration-1/r.video_fps,t));update();};
 button('Restart',()=>seek(0));button('−5 s',()=>seek(video.currentTime-5));button('+5 s',()=>seek(video.currentTime+5));
 button('−1 frame',()=>seek(video.currentTime-1/r.video_fps));button('+1 frame',()=>seek(video.currentTime+1/r.video_fps));
 const speed=node('select');speed.setAttribute('aria-label',variant+' playback speed');
 for(const n of [.25,.5,1,1.5,2,4]){const o=node('option',n+'×');o.value=n;o.selected=n===1;speed.append(o);}speed.onchange=()=>video.playbackRate=+speed.value;
 controls.append(node('label','Speed'),speed);
 const camera=node('select');camera.setAttribute('aria-label',variant+' camera');
 for(const [id,title] of [['room','Whole bedroom'],['detail','Edge & floor']]){const o=node('option',title);o.value=id;camera.append(o);}
 function changeCamera(name,t,playing=false){const rate=video.playbackRate;video.pause();camera.value=name;video.src=base+'/'+sources[name]+'?v='+revision;video.addEventListener('loadedmetadata',()=>{video.currentTime=Math.min(t,r.duration-1/r.video_fps);video.playbackRate=rate;if(playing)video.play();},{once:true});}
 camera.onchange=()=>changeCamera(camera.value,video.currentTime,!video.paused);controls.append(camera);
 // Embedded browsers may deny native fullscreen. Keep the same controls in a
 // viewport-sized fallback, with an explicit exit and Escape-key support.
 const setExpanded=enabled=>{player.classList.toggle('is-expanded',enabled);document.body.classList.toggle('player-expanded',!!document.querySelector('.is-expanded'));fullscreen.textContent=enabled?'Exit fullscreen':'Fullscreen';};
 const fullscreen=button('Fullscreen',async()=>{
  if(player.classList.contains('is-expanded')){setExpanded(false);return;}
  if(document.fullscreenElement){await document.exitFullscreen();return;}
  try{if(player.requestFullscreen){await player.requestFullscreen();return;}if(video.webkitEnterFullscreen){video.webkitEnterFullscreen();return;}}catch{/* Use the viewport fallback when native fullscreen is unavailable. */}
  setExpanded(true);
 });
 document.addEventListener('fullscreenchange',()=>fullscreen.textContent=document.fullscreenElement===player||player.classList.contains('is-expanded')?'Exit fullscreen':'Fullscreen');
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&player.classList.contains('is-expanded'))setExpanded(false);});
 const row=node('div',undefined,'seek-row'),slider=node('input');slider.type='range';slider.min=0;slider.max=r.duration;slider.step=1/r.video_fps;slider.value=0;slider.setAttribute('aria-label',variant+' video progress');slider.oninput=()=>seek(+slider.value);const elapsed=node('span');row.append(slider,elapsed);player.append(video,controls,row);section.append(player);
 const final=r.consequence_simulation.metrics;section.append(node('p',`Final outcome: ${final.physical_fallen?'bottle fell':r.metrics.support_contact?'bottle supported':'bottle unsupported'} · ${final.rule_liquid_spilled_ml>0?'modeled liquid escaped':'no modeled spill'}`,'result'+(final.physical_fallen?' hazard':'')));
 const metrics=node('div',undefined,'metrics');const edge=metric(metrics,'EDGE MARGIN · WHILE SUPPORTED'),trigger=metric(metrics,'DISTURBANCE · RULE'),tilt=metric(metrics,'BOTTLE TILT · PHYSX'),fall=metric(metrics,'FALL · PHYSX'),spill=metric(metrics,'SPILLED · LIQUID MODEL'),floor=metric(metrics,'ON FLOOR · LIQUID MODEL');section.append(metrics);
 const plans=node('div',undefined,'section');plans.append(node('h3','THE ORIGINAL PLAN'));const list=node('ol',undefined,'plan');const steps=[];
 r.plan.forEach((action,i)=>{const li=node('li'),b=node('button');b.append(node('code',`(${action})`),node('small',`${time(r.steps[i].start)} – ${time(r.steps[i].end)}`));if(variant==='unsafe'&&i===2){b.classList.add('violation');b.title='Dangerous placement in the original dataset rules';}b.onclick=()=>seek(r.steps[i].start);steps.push(b);li.append(b);list.append(li);});plans.append(list);section.append(plans);
 const events=node('div',undefined,'section');events.append(node('h3','REPLAY THE CONSEQUENCE'));const buttons=node('div',undefined,'events');
 for(const event of r.consequence_simulation.events){if(!label[event.type])continue;const b=node('button',`${label[event.type]} · ${time(event.t)}`);b.onclick=()=>changeCamera('detail',Math.max(0,event.t-.4),true);buttons.append(b);}
 const end=node('button','Final state');end.onclick=()=>changeCamera('detail',r.duration-1/r.video_fps);buttons.append(end);events.append(buttons);section.append(events);
 const links=node('div',undefined,'section evidence-links');for(const [name,title] of [['result.json','Result'],['trace.json','State trace'],['state-transitions.json','State transitions'],['consequences.json','Rule & events'],['episode.mp4','Room video'],['consequence-detail.mp4','Detail video'],['recorded-source.zip','Recorded source']]){const a=node('a',title+' ↓');a.href=base+'/'+name;links.append(a);}section.append(links);
 function update(){const s=locate(trace,video.currentTime);slider.value=video.currentTime;elapsed.textContent=`${time(video.currentTime)} / ${time(r.duration)}`;play.textContent=video.paused?'Play':'Pause';edge.textContent=s.metrics.support_contact?(s.metrics.edge_margin_m*100).toFixed(2)+' cm':'—';trigger.textContent=s.metrics.rule_triggered?'Triggered':'Not triggered';tilt.textContent=s.metrics.object_tilt_deg.toFixed(1)+'°';fall.textContent=s.metrics.physical_fallen?'Observed':'Not observed';spill.textContent=s.metrics.rule_liquid_spilled_ml.toFixed(1)+' ml';floor.textContent=s.metrics.rule_liquid_floor_ml.toFixed(1)+' ml';steps.forEach((b,i)=>b.classList.toggle('current',s.step===i));}
 for(const e of ['timeupdate','seeked','play','pause','loadedmetadata','ended'])video.addEventListener(e,update);
 update();videos.push(video);finalStates.push(()=>changeCamera('detail',r.duration-1/r.video_fps));return section;
}
try{
 const m=await get('manifest.json'),c=m.config.rule;
 $('threshold').textContent=(c.threshold_m*100).toFixed(1)+' cm';$('container').textContent=(c.container_open?'Open':'Closed')+' · '+c.initial_liquid_ml+' ml';$('pulse').textContent=c.force_n+' N · '+c.pulse_s+' s';
 $('rule-description').textContent=`Once the released bottle remains within ${c.threshold_m*100} cm of the table edge for ${c.dwell_s} s, the rule can request the declared disturbance. The robot first withdraws ${c.withdrawal_m} m using the checked motion planner. The rule does not read the safe/unsafe label. An open bottle can emit modeled liquid only after its measured tilt exceeds ${c.spill_tilt_deg}°. All parameters are uncalibrated.`;
 const panels=await Promise.all(['safe','unsafe'].map(v=>panel(v,m.variants[v])));$('players').append(...panels);
 $('play-both').onclick=()=>Promise.all(videos.map(v=>v.play()));$('pause-both').onclick=()=>videos.forEach(v=>v.pause());$('restart-both').onclick=()=>videos.forEach(v=>{v.pause();v.currentTime=0;});$('final-both').onclick=()=>finalStates.forEach(show=>show());
}catch(e){$('players').textContent='Unable to load the verified recording: '+e.message;console.error(e);}
