/* Local consequence recordings share source tasks, not full-episode clocks. */
(() => {
  const $=id=>document.getElementById(id);
  const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  const base='../object-safety/';
  const read=async path=>{const r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw Error(`Consequence recording: HTTP ${r.status}`);return r.json();};
  let catalog,token=0,players=[];
  const toolbar=$('recording-mode'),view=$('object-consequence-view'),full=$('full-execution-view');
  const report=e=>{const error=$('object-consequence-error');if(error){error.hidden=false;error.textContent=e.message;}};
  function pause(){players.forEach(p=>p.video.pause());}
  function closeExpanded(){view.querySelectorAll('.oc-expanded').forEach(e=>e.classList.remove('oc-expanded'));view.querySelectorAll('[data-fullscreen]').forEach(b=>b.textContent='Fullscreen');document.body.classList.remove('oc-has-expanded');}
  function mode(objects){
    pause();closeExpanded();['safe','unsafe'].forEach(k=>$(k+'-video').pause());
    view.hidden=!objects;full.hidden=objects;document.body.dataset.recordingView=objects?'objects':'full';
    $('show-object-consequences').setAttribute('aria-pressed',String(objects));$('show-full-execution').setAttribute('aria-pressed',String(!objects));
  }
  function reset(){token++;pause();closeExpanded();players=[];view.replaceChildren();toolbar.hidden=true;$('show-object-consequences').disabled=false;$('recording-note').textContent='Latest object tests have their own clocks and measurements. The complete robot recordings remain available.';mode(false);}
  function refresh(){const both=$('oc-play-both');if(both)both.textContent=players.some(p=>!p.video.paused&&!p.video.ended)?'Pause both':'Play both';}
  function panel(record,item,variant,revision){
    const root=make('article',undefined,'oc-panel oc-'+variant);root.dataset.objectVariant=variant;
    const title=make('div',undefined,'oc-panel-title');title.append(make('h3',variant==='safe'?'Safe reference plan':'Unsafe reference plan'),make('span','LOCAL ACTION ONLY'));root.append(title);
    const box=make('div',undefined,'oc-player'),video=make('video');video.controls=true;video.muted=true;video.playsInline=true;video.preload='metadata';video.setAttribute('aria-label',variant+' consequence video');
    const path=base+item.path+'/',url=file=>path+file+'?v='+revision;video.src=url('episode.mp4');video.poster=url('poster.jpg');box.append(video);
    const controls=make('div',undefined,'oc-controls'),play=make('button','Play');play.className='oc-primary';
    const state={video,record};players.push(state);
    const seek=t=>{video.pause();video.currentTime=Math.max(0,Math.min(record.duration_s,t));};
    play.onclick=()=>video.paused?video.play().catch(report):video.pause();controls.append(play);
    [['Restart',()=>seek(0)],['−5 s',()=>seek(video.currentTime-5)],['+5 s',()=>seek(video.currentTime+5)],['−1 frame',()=>seek(video.currentTime-1/record.fps)],['+1 frame',()=>seek(video.currentTime+1/record.fps)]].forEach(([name,action])=>{const b=make('button',name);b.onclick=action;controls.append(b);});
    const label=make('label','Speed '),speed=make('select');speed.setAttribute('aria-label',variant+' consequence playback speed');[.25,.5,1,1.5,2,4].forEach(n=>{const o=make('option',n+'×');o.value=n;o.selected=n===1;speed.append(o);});speed.onchange=()=>video.playbackRate=Number(speed.value);label.append(speed);controls.append(label);
    const fullscreen=make('button','Fullscreen');fullscreen.dataset.fullscreen='true';fullscreen.onclick=async()=>{
      if(document.fullscreenElement===box){await document.exitFullscreen();return;}
      if(box.classList.contains('oc-expanded')){closeExpanded();return;}
      closeExpanded();try{if(document.fullscreenEnabled){await box.requestFullscreen();fullscreen.textContent='Exit fullscreen';return;}}catch{}
      box.classList.add('oc-expanded');document.body.classList.add('oc-has-expanded');fullscreen.textContent='Exit fullscreen';
    };controls.append(fullscreen);box.append(controls);
    const track=make('div',undefined,'oc-seek'),slider=make('input'),clock=make('output','0.0 / '+record.duration_s.toFixed(1)+' s');slider.type='range';slider.min=0;slider.max=record.duration_s;slider.step=1/record.fps;slider.value=0;slider.setAttribute('aria-label',variant+' consequence progress');slider.oninput=()=>seek(Number(slider.value));track.append(slider,clock);box.append(track);root.append(box);
    video.ontimeupdate=()=>{slider.value=video.currentTime;clock.textContent=video.currentTime.toFixed(1)+' / '+record.duration_s.toFixed(1)+' s';};
    const playback=()=>{play.textContent=video.paused||video.ended?'Play':'Pause';refresh();};video.onplay=playback;video.onpause=playback;video.onended=playback;
    video.onerror=()=>report(Error('The '+variant+' consequence video could not load.'));
    const body=make('div',undefined,'oc-body'),o=record.outcome;
    const outcome=o.fell?'Object fell below its support':o.displaced?'Object displaced by contact':o.tipped?'Object tipped':o.stable_at_end?'Object stable at the end':'Inspect the measured state';
    body.append(make('div',outcome,'oc-outcome'+(o.fell||o.displaced||o.tipped||o.modeled_spill?' oc-bad':'')));
    const cells=[['Maximum tilt',o.max_tilt_deg.toFixed(1)+'°'],['Maximum displacement',(o.max_displacement_m*100).toFixed(1)+' cm'],['Contact with test object',o.contact_samples?'Measured':'Not observed'],['Modeled liquid escaped',record.liquid.ledger.spilled_ml.toFixed(1)+' ml']];
    if(record.recipe.mechanism!=='floor_collision')cells.push(['Initial centre-of-mass margin',(record.initial_state.com_support_margin_m*100).toFixed(1)+' cm']);
    if(record.recipe.liquid_ml)cells.push(['Declared container',`${record.recipe.container_open?'Open':'Closed'} · ${record.recipe.liquid_ml} ml initially`]);
    const metrics=make('div',undefined,'oc-metrics');cells.forEach(([a,b])=>{const cell=make('div');cell.append(make('small',a),make('b',b));metrics.append(cell);});body.append(metrics);
    const events=make('div',undefined,'oc-events');o.events.forEach(e=>{const b=make('button',e.type.replaceAll('_',' ')+' · '+e.t.toFixed(2)+' s');b.onclick=()=>{seek(e.t-.25);speed.value='0.25';video.playbackRate=.25;video.play().catch(report);};events.append(b);});body.append(events);
    body.append(make('p',variant==='safe'?record.recipe.safe_condition:record.recipe.unsafe_condition,'oc-note'),make('h4','Original plan · highlighted interaction tested'));
    const list=make('ol',undefined,'oc-plan');record.original_plan.forEach((action,i)=>{const li=make('li',undefined,i===record.tested_action_index?'oc-tested':'');li.append(make('code',action));list.append(li);});body.append(list);
    const downloads=make('div',undefined,'oc-downloads');[['Result JSON','result.json'],['State trace','trace.json'],['Predicate transitions','predicate-transitions.json'],['Video','episode.mp4'],['Recorded source','recorded-source.zip']].forEach(([name,file])=>{const a=make('a',name+' ↓');a.href=url(file);downloads.append(a);});body.append(downloads);root.append(body);return root;
  }
  async function load(taskId){
    const current=++token;
    try{
      if(!catalog)catalog=await read(base+'manifest.json');
      if(current!==token)return;
      const item=catalog.cases.find(c=>c.task_id===taskId);if(!item)return;
      const records=await Promise.all(['safe','unsafe'].map(k=>read(base+item.variants[k].path+'/result.json?v='+catalog.build_id)));
      if(current!==token)return;
      if(records.some(r=>r.source_task_id!==taskId))throw Error('Consequence source task does not match the selected task.');
      toolbar.hidden=false;view.replaceChildren();players=[];
      const intro=make('div',undefined,'oc-intro');intro.append(make('p','LATEST OBJECT CONSEQUENCE TEST · 7 SECONDS','eyebrow'),make('h3',item.title),make('p','These clips isolate the highlighted interaction in a controlled bedroom fixture. Choose Full robot execution for navigation, grasping and the original task scene. Both panels use their own local time and measurements.'));
      const details=make('details');details.append(make('summary','Scene, contact and liquid assumptions'),make('p',item.source_scope),make('p','Controlled bedroom fixture using Genie Sim / BEHAVIOR assets. Orange probes or a sponge provide declared contact inputs. Rigid-body outcomes come from PhysX; liquid uses a one-way reduced-order model. All parameters are uncalibrated.'));intro.append(details);view.append(intro);
      const error=make('p',undefined,'oc-error');error.id='object-consequence-error';error.hidden=true;error.setAttribute('role','alert');view.append(error);
      const actions=make('div',undefined,'oc-shared'),both=make('button','Play both','oc-primary');both.id='oc-play-both';both.onclick=()=>{if(players.some(p=>!p.video.paused))pause();else players.forEach(p=>{if(p.video.ended)p.video.currentTime=0;p.video.play().catch(report);});};actions.append(both);
      [['Restart both',()=>{pause();players.forEach(p=>p.video.currentTime=0);}],['Inspect final states',()=>{pause();players.forEach(p=>p.video.currentTime=p.record.duration_s-1/p.record.fps);}]].forEach(([name,f])=>{const b=make('button',name);b.onclick=f;actions.append(b);});
      const link=make('a','Object library & controls ↗');link.href=base+'#'+item.id;actions.append(link);view.append(actions);
      const cards=make('div',undefined,'oc-pairs');records.forEach((r,i)=>cards.append(panel(r,item.variants[['safe','unsafe'][i]],['safe','unsafe'][i],catalog.build_id)));view.append(cards);
      const viewLabel=make('label','View '),choice=make('select');choice.setAttribute('aria-label','Consequence video view');[['both','Both plans'],['safe','Safe reference'],['unsafe','Unsafe reference']].forEach(([value,name])=>{const option=make('option',name);option.value=value;choice.append(option);});choice.onchange=()=>{cards.classList.toggle('oc-single',choice.value!=='both');cards.querySelectorAll('.oc-panel').forEach(p=>p.hidden=choice.value!=='both'&&p.dataset.objectVariant!==choice.value);};viewLabel.append(choice);actions.insertBefore(viewLabel,link);
      mode(true);
    }catch(e){if(current!==token)return;mode(false);toolbar.hidden=false;$('show-object-consequences').disabled=true;$('recording-note').textContent='The new object test could not load. The full robot recording remains available. '+e.message;}
  }
  $('show-object-consequences').onclick=()=>mode(true);$('show-full-execution').onclick=()=>mode(false);
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeExpanded();});document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement)view.querySelectorAll('[data-fullscreen]').forEach(b=>b.textContent='Fullscreen');});
  window.DespiteObjectView={load,pause,reset};
})();
