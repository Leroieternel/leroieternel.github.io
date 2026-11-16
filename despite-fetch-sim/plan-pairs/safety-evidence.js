/* Source descriptions, physical events and task goals use separate records. */
(() => {
  const $=id=>document.getElementById(id);
  const make=(tag,text,cls)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;};
  const labels={observed:'Observed',not_observed:'Not detected',not_modeled:'Not modeled',not_executed:'Not reached',unavailable:'Missing measurement'};
  const outcomes={physical_event_observed:'Physical event observed',modeled_event_observed:'Modeled consequence observed',risk_or_protocol_observed:'Risk condition / protocol violation observed',no_event_detected:'No event detected by connected monitors',not_evaluated:'Safety evidence unavailable'};
  let current={};
  function source(item){
    const box=$('source-danger');box.replaceChildren();
    const d=item.metadata.danger_formalization;
    box.append(make('p','ORIGINAL DANGER → RECORDED EVIDENCE','eyebrow'),make('p',d.cause_of_danger,'source-danger-text'));
    const details=make('details');details.append(make('summary','Source harm and measurement scope'),make('p','Original dangerous action: '+d.danger_action),make('p','Described harm: '+d.result_of_danger));
    if(d.instantaneous_solution)details.append(make('p','Original corrective description: '+d.instantaneous_solution));
    details.append(make('p','The chain below distinguishes measured physical events, risk conditions and consequences that are not modeled. Completing a plan does not erase an earlier event. All physical parameters remain uncalibrated.'));
    box.append(details);
  }
  function render(k,e,{result,item,url,jump,play}){
    current[k]=e;$(k+'-source-evidence')?.remove();$(k+'-evidence-badge')?.remove();
    if(!e)return;
    const status=$(k+'-outcome');status.textContent=!e.task.execution_completed&&!e.events.length?'Execution stopped · no incident detected in the recorded attempt':outcomes[e.safety.status];
    status.className='outcome evidence-outcome '+(e.events.length?'bad':'neutral');
    $(k+'-label-observation')?.remove();
    const root=make('section',undefined,'source-evidence');root.id=k+'-source-evidence';root.setAttribute('aria-label',k+' source-linked safety evidence');
    const summary=make('div',undefined,'evidence-summary');
    [['Final task goal',e.task.final_goal_reached?'Reached':'Not reached'],['Plan execution',`${e.task.completed_actions} / ${e.task.total_actions} actions`]].forEach(([title,value])=>{const cell=make('div');cell.append(make('small',title),make('strong',value));summary.append(cell);});root.append(summary);
    root.append(make('h4','Danger evidence in this recording'));
    const chain=make('ol',undefined,'danger-chain');
    e.source_chain.forEach(stage=>{
      const li=make('li',undefined,'chain-'+stage.status),label=make('span',labels[stage.status],'evidence-status');
      const main=make('div');main.append(make('span',stage.source_stage,'chain-label'),label);
      if(stage.status==='observed'){
        const seek=make('button',`View · ${stage.first_time_s.toFixed(2)} s`);seek.onclick=()=>jump(stage.first_time_s,k);main.append(seek);
      }
      li.append(main);chain.append(li);
    });root.append(chain);
    const extra=e.events.filter(event=>!e.source_chain.some(s=>s.id===event.id));
    if(extra.length){const box=make('div',undefined,'evidence-additional');box.append(make('small','Additional measured / declared conditions'));extra.forEach(ev=>{const b=make('button',`${ev.title} · ${ev.first_time_s.toFixed(2)} s`);b.onclick=()=>jump(ev.first_time_s,k);box.append(b);});root.append(box);}
    const incident=e.events.find(x=>x.category==='physical_event')||e.events.find(x=>x.category==='modeled_event')||e.events[0];
    if(incident){const watch=make('button','Watch the event in the full recording','evidence-watch');watch.onclick=()=>play(k,Math.max(0,incident.first_time_s-1));root.append(watch);}
    const detail=make('details',undefined,'evidence-definition');detail.append(make('summary','Definitions, thresholds & limitations'));
    detail.append(make('p',e.task.goal_definition),make('p',e.safety.coverage_note));
    e.observations.forEach(o=>{
      const parts=[o.title,`status: ${labels[o.status]}`];
      if(o.threshold)parts.push(`threshold ${o.threshold.comparison} ${o.threshold.value} ${o.unit||''} (${o.threshold.origin.replaceAll('_',' ')})`);
      if(o.minimum!==null&&o.unit)parts.push(`range ${o.minimum.toFixed(3)}–${o.maximum.toFixed(3)} ${o.unit}`);
      if(o.latched)parts.push(`first observed ${o.first_time_s.toFixed(2)} s · ${o.basis.replaceAll('_',' ')}`);
      if(o.explanation)parts.push(o.explanation);
      detail.append(make('p',parts.join(' · ')));
    });
    e.source_chain.filter(x=>x.status==='not_modeled').forEach(s=>detail.append(make('p',s.source_stage+': '+s.explanation)));
    if(result.consequence_simulation){const cfg=result.consequence_simulation.config.rule;detail.append(make('p',`Declared scene: ${cfg.mode==='gravity_overhang'?'gravity-driven overhang, no external force':'external disturbance experiment'}; ${cfg.container_open?'open':'closed'} container; ${cfg.initial_liquid_ml} ml modeled inventory. The liquid ledger is separate from rigid-body physics.`));}
    detail.append(make('p',`Event timing resolution: ${(e.timebase.resolution_s*1000).toFixed(1)} ms. Observation ends at ${e.timebase.end_s.toFixed(2)} s. Events remain recorded after recovery.`));root.append(detail);
    const download=make('a','Source-linked safety evidence ↓');download.href=url(item.path+'/safety-evidence.json');root.append(download);
    status.after(root);
    // Existing liquid/chair overlays already show their live channels.
    if(!result.liquid_simulation&&!result.spec.spatial_contract){const badge=make('span','','evidence-badge');badge.id=k+'-evidence-badge';badge.hidden=true;$(k+'-video').parentElement.append(badge);}
  }
  function update(k,time){
    const e=current[k],badge=$(k+'-evidence-badge');if(!e||!badge)return;
    const past=e.events.filter(x=>x.first_time_s<=time+.0001);
    const significant=past.filter(x=>x.category==='physical_event'||x.category==='modeled_event');
    const last=(significant.length?significant:past).at(-1);badge.hidden=!last;
    if(last)badge.textContent=`${last.title} · observed by ${last.first_time_s.toFixed(2)} s`;
  }
  window.DespiteSafetyEvidence={source,render,update};
})();
