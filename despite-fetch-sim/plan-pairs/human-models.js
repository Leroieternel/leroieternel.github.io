/* Human dynamics measurements and offline environment-author provenance. */
(() => {
  const $=id=>document.getElementById(id);
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const finite=(n,suffix,digits=2)=>Number.isFinite(n)?`${n.toFixed(digits)} ${suffix}`:'Not measured';
  function render(k,r,{url,path,jump,metricCell}){
    $(k+'-human-model')?.remove();
    if(!r.human_model)return;
    const m=r.metrics,a=r.model_author;
    $(k+'-metrics').append(
      metricCell('Human fall',m.ever_human_fallen?'Observed':'Not detected','Latched from measured body state'),
      metricCell('Head contact',m.ever_head_contact?'Observed':'Not detected','Contact report · separate from injury'),
      metricCell('Peak head speed',finite(m.peak_head_speed_m_s,'m/s'),'Recorded body velocity · not a mortality estimate'));
    const box=el('details',undefined,'planning-details');box.id=k+'-human-model';
    box.append(el('summary','Inspect the human model & its author'));
    if(a)box.append(el('p',`${a.display_name} · ${a.effort} · ${a.provider_label}. Environment code generated before execution; model APIs do not control rollout steps.`));
    box.append(el('p',typeof r.human_model==='string'?r.human_model:(r.human_model.description||r.human_model.type||r.human_model.control||'Dynamic articulated mannequin with declared physical parameters.')));
    if(r.visual_assets)box.append(el('p',`Native Genie Sim room, furniture and object texture maps. The character skin follows measured body motion. ${r.task_id==='neiss_1014'?'The native dual-arm TIAGo':'The original single-arm Fetch'} uses its original articulation, joint limits and motor controllers.`));
    for(const note of r.limitations||[])box.append(el('p',note));
    const links=el('div',undefined,'downloads');
    for(const [title,file] of [['Model & parameters','human-model.json'],['Model authorship','model-authoring.json'],['Native assets & rendering','visual-assets.json'],['Original model output and integration changes','model-source.zip']]){
      const a=el('a',title+' ↓');a.href=url(path+'/'+file);links.append(a);
    }
    if(r.model_review){const a=el('a','Post-recording model review ↓');a.href=url(path+'/'+r.model_review.report);links.append(a);}
    if(r.sensor_scan_exports){
      const scans=r.sensor_scan_exports;
      const a=el('a',scans.manifest?'Sensor scan reassembly & checksums ↓':'Complete sensor scans ↓');
      a.href=url(path+'/'+(scans.manifest||scans.file));links.append(a);
      for(const [i,part] of (scans.parts||[]).entries()){
        const a=el('a',`Sensor scans · part ${i+1}/${scans.parts.length} ↓`);
        a.href=url(path+'/'+part.file);a.download=part.file;links.append(a);
      }
    }
    box.append(links);$(k+'-metrics').after(box);
    const checkpoints=el('div',undefined,'staff-events');
    for(const [key,label] of [['robot_human_contact','First robot contact'],['human_fallen','First measured fall'],['head_contact','First head contact']]){
      const event=r.first_observed_events?.[key];if(!Number.isFinite(event))continue;
      const b=el('button',`${label} · ${event.toFixed(2)} s`);b.onclick=()=>jump(event,k);checkpoints.append(b);
    }
    box.append(checkpoints);
  }
  function configure(r,item){
    $('instrumented-case').parentElement.hidden=!!r.human_model;
    if(!r.human_model)return;
    $('case-id').textContent=item.id+' / DESPITE FULL · EASY';
    const a=r.model_author;
    const resolution=r.rendering?.width&&r.rendering?.height?`${r.rendering.width}×${r.rendering.height} · `:'';
    $('runtime-note').textContent=`Physics: Isaac Sim ${r.runtime.isaacsim} / PhysX · ${r.physics_hz} Hz. Recorded RGB: ${resolution}${r.video_fps} fps. ${a?a.display_name+' authored this environment via '+a.provider_label+' at '+a.effort+'. ':''}Human parameters and controllers are uncalibrated. The model is not called by the rollout controller.`;
    $('metric-note').textContent='Torso inclination is measured from simulated body orientation throughout execution. The dashed line is a declared pose-monitor threshold. It is not an injury or survival threshold. Falls and head contacts are reported separately.';
    $('map-note').textContent='Top view in metres. Arrows follow the robot; rings follow the measured human pelvis. Each video has its own clock.';
  }
  function map(c,xy,states){
    for(const [k,s] of Object.entries(states)){
      const p=s?.human?.pelvis_position_m||s?.human?.body_positions?.pelvis||s?.human?.body_positions?.h_pelvis;
      if(!p)continue;
      const q=xy(p);c.strokeStyle=k==='safe'?'#467a54':'#b2764d';c.lineWidth=2;
      c.beginPath();c.arc(q[0],q[1],9,0,2*Math.PI);c.stroke();
    }
  }
  window.DespiteHumanModels={render,configure,map};
})();
