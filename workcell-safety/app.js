'use strict';
const cases=[...(window.EVERYDAY_STUDIES||[]),...(window.MOBILE_WORLDS||[]),...window.WORKCELLS];
registerStudyScenes(window.EVERYDAY_STUDIES||[]);
const node=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e};
const versioned=url=>url+'?v='+(url.includes('everyday_drawer/')?'drawer-contact-v1':((url.includes('/long_')||url.includes('antigravity/mobile_'))?'spatial-ff15c4b863da':url.includes('hard_virtualhome_31/')?'milk-rim-2':url.includes('people_cafe/')?'cafe-grip-2':'mobile-worlds-1'));
const mediaUrl=(c,file)=>(c.filmBase&&file.endsWith('.mp4')?c.filmBase:c.base)+'/'+file;
const by=id=>document.getElementById(id);
const link=(text,url)=>{const a=node('a',null,text);a.href=url;return a};
let item,vids=[],paired=false,tick=0,slowEnd=null;
const tLabel=t=>t.toFixed(2)+' s';
function stopPair(){
  paired=false;cancelAnimationFrame(tick);slowEnd=null;vids.forEach(v=>v.playbackRate=1);
  by('play').textContent='Play together';
}
function pauseBoth(){stopPair();vids.forEach(v=>v.pause())}
function loop(){
  if(!paired)return;
  if(slowEnd!==null&&vids[0].currentTime>=slowEnd){vids.forEach(v=>v.playbackRate=1);slowEnd=null}
  if(vids.some(v=>v.ended)){pauseBoth();return}
  if(vids.every(v=>v.readyState>=3)&&Math.abs(vids[0].currentTime-vids[1].currentTime)>.15)vids[1].currentTime=vids[0].currentTime;
  tick=requestAnimationFrame(loop);
}
async function playPair(at,rate=1,until=null){
  cancelAnimationFrame(tick);
  if(at===undefined)at=vids.some(v=>v.ended)?0:vids[0].currentTime;
  slowEnd=until;
  vids.forEach(v=>{v.currentTime=at;v.playbackRate=rate});paired=true;by('play').textContent='Pause both';
  try{await Promise.all(vids.map(v=>v.play()));if(paired)loop()}catch{pauseBoth()}
}
by('play').onclick=()=>paired?pauseBoth():playPair();
function seekTo(t){
  pauseBoth();
  vids.forEach(v=>{if(v.readyState>=1)v.currentTime=t;else v.addEventListener('loadedmetadata',()=>v.currentTime=t,{once:true})})
}
by('event').onclick=()=>seekTo(item.event);
function picture(url,alt){
  const a=link('',url);a.target='_blank';a.rel='noopener';const im=node('img');im.src=url;im.alt=alt;im.loading='lazy';a.append(im);return a;
}
const sceneFilter=by('scene-filter');
const lastChoice=new Map();
fillSceneOptions(sceneFilter,cases.filter(c=>!c.parentId));
sceneFilter.onchange=()=>{
  const scene=sceneFilter.value;
  const target=lastChoice.get(scene)||cases.find(c=>!c.parentId && taskEnvironment(c.id)===scene);
  if(target)location.hash=target.id;
};
for(const c of cases.filter(c=>!c.parentId)){
  const b=node('button','taskbtn');b.type='button';b.dataset.id=c.id;b.dataset.scene=taskEnvironment(c.id);b.setAttribute('aria-pressed','false');
  const im=node('img');im.src=versioned(c.base+'/thumb.jpg');im.alt='';const label=node('span',null,c.short);label.append(node('small','nav-model',c.robotShort||'Earlier study'));b.append(im,label);
  b.onclick=()=>{const id=c.defaultTrial||c.id;if(location.hash!=='#'+id)location.hash=id;else render(cases.find(x=>x.id===id))};by('nav').append(b);
}
function render(c){
  renderEventReplay(c.eventReplay,c.filmBase,c.base);
  pauseBoth();item=c;vids=[];
  const scene=taskEnvironment(c.parentId||c.id);
  sceneFilter.value=scene;lastChoice.set(scene,c);
  const directoryLink=by('browse-scene');
  directoryLink.hidden=!c.dataset;
  if(c.dataset){
    const slug=scene.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replaceAll(' ','-');
    directoryLink.href='despite/#'+slug;
    directoryLink.textContent='Browse DESPITE examples in '+scene;
  }
  for(const b of by('nav').children)b.hidden=b.dataset.scene!==scene;
  const trials=by('trials');trials.replaceChildren();trials.hidden=!c.trials;
  for(const [id,name] of c.trials||[]){
    const btn=node('button',null,name);btn.type='button';btn.setAttribute('aria-pressed',String(c.id===id));btn.onclick=()=>{location.hash=id};trials.append(btn);
  }
  const room=by('room-view');room.hidden=!c.mobile;
  by('main').classList.toggle('mobile-study',!!(c.mobile||c.editionId));
  if(c.mobile){
    const cap=by('room-caption'),image=by('room-photo'),photoLink=by('room-link');
    const actions=node('div','photo-actions'),full=link('Open 4K photograph','');
    cap.replaceChildren(node('span',null,c.roomCaption),actions);
    const options=[['Room overview','world'],['Aisle at eye level','aisle']];
    const choose=(idx)=>{
      const [label,file]=options[idx],src=c.base+'/'+file;
      image.src=versioned(src+'-preview.jpg');
      image.srcset=versioned(src+'-preview.jpg')+' 1600w, '+versioned(src+'.jpg')+' 3840w';
      image.sizes='(max-width: 820px) 96vw, 75vw';
      image.alt=c.robot+' in '+c.robotShort+' — '+label.toLowerCase();
      photoLink.href=full.href=versioned(src+'.jpg');
      for(const btn of actions.querySelectorAll('button'))btn.setAttribute('aria-pressed',String(Number(btn.dataset.view)===idx));
    };
    options.forEach(([label],idx)=>{const btn=node('button',null,label);btn.type='button';btn.dataset.view=idx;btn.onclick=()=>choose(idx);actions.append(btn)});
    for(const a of [photoLink,full]){a.target='_blank';a.rel='noopener'}
    actions.append(full);choose(0);
  }
  const editionId=c.editionId||(c.mobile||c.id==='cnc_full'?c.id:'studies_'+c.id);
  by('updated-task').href=by('updated-edition').href='antigravity/#'+editionId;
  document.title=c.title+' · Workcell Safety';
  by('title').textContent=c.title;by('description').textContent=c.description;by('category').textContent=c.category;
  by('timing').textContent='Event at '+tLabel(c.event)+'  ·  '+Number(c.duration.toFixed(2))+' s replay';
  const specs=by('specs');specs.replaceChildren();
  if(c.robot){specs.append(link(c.robot+' ↗',c.source),node('span',null,c.form),node('span',null,c.human));}
  const credit=link(c.credit||(c.mobile?'Created with Codex · MuJoCo + Blender':c.id==='cnc_full'?'Neon CNC environment · Codex safety trial':'Workcell authored in Codex'),c.creditUrl||'credits.html#production');
  specs.append(credit);
  if(c.materialSource)specs.append(link('Scene materials and sources',c.materialSource));
  if(c.handSource)specs.append(link('Panda Hand model',c.handSource));
  const chapters=by('chapters');chapters.replaceChildren();
  if(c.slowRange){const slow=node('button','slow-button','Replay incident at ¼ speed');slow.type='button';slow.onclick=()=>playPair(c.slowRange[0],.25,c.slowRange[1]);chapters.append(slow)}
  for(const [label,t] of c.chapters||[]){const button=node('button',null,label+' · '+tLabel(t));button.type='button';button.onclick=()=>seekTo(t);chapters.append(button)}
  const sequence=by('sequence');sequence.replaceChildren();sequence.hidden=!c.sequenceCaption;
  const study=by('high-speed');study.replaceChildren();study.hidden=!c.highSpeed;
  if(c.highSpeed){
    const video=node('video');video.controls=true;video.playsInline=true;video.preload='metadata';
    video.poster=versioned(c.base+'/slow_poster.jpg');video.src=versioned(c.base+'/incident-slow.mp4');
    video.setAttribute('aria-label','Ten-times slow-motion incident comparison');
    study.append(node('h3',null,'Incident in slow motion'),video,node('figcaption',null,'Each frame is a MuJoCo state sampled 4 ms apart and played at 25 fps. The clock shows simulation time. The force plot uses all 1,000 solver samples per second.'));
  }
  if(c.sequenceCaption)sequence.append(picture(versioned(c.base+'/sequence.jpg'),c.sequenceCaption),node('figcaption',null,c.sequenceCaption));
  by('criterion').textContent=c.criterion||'';
  by('goal-test').textContent=c.goalTest?'Task acceptance. '+c.goalTest:'';
  by('plan-intro').textContent=c.planIntro;
  by('detailintro').textContent=c.detailIntro;
  by('measurement').textContent=c.method||'';
  by('auditnote').textContent=c.auditnote;
  for(const b of by('nav').children)b.setAttribute('aria-pressed',String(b.dataset.id===(c.parentId||c.id)));
  for(const id of ['players','plans','details','facts','charts','downloads'])by(id).replaceChildren();
  for(const key of ['unsafe','safe']){
    const data=c[key],name=key==='unsafe'?'Unsafe':'Safe',base=c.base+'/';
    const player=node('div','player '+key);player.append(node('h3',null,name+' replay'));
    const video=node('video');video.setAttribute('aria-label',name+' replay of '+c.title);video.controls=true;video.playsInline=true;video.preload='metadata';video.poster=versioned(base+key+'_poster.jpg');
    const source=node('source');source.type='video/mp4';source.src=versioned(mediaUrl(c,key+'.mp4'));video.append(source);
    video.addEventListener('pause',()=>{if(paired&&vids.includes(video))pauseBoth()});vids.push(video);
    player.append(video,node('small',null,data.summary));by('players').append(player);
    const card=node('div','stepcard '+key);card.append(node('h3',null,name+' plan'));const ol=node('ol','steps');
    for(const step of data.steps){
      const li=node('li',step.hazard?'haz':'');
      const time=node(c.longRank||c.group==='shared_spaces'?'button':'time',c.longRank||c.group==='shared_spaces'?'step-seek':null,tLabel(step.t));
      if(c.longRank||c.group==='shared_spaces'){
        time.type='button';time.setAttribute('aria-label','Seek '+name.toLowerCase()+' replay to '+step.text);
        time.onclick=()=>{pauseBoth();if(video.readyState>=1)video.currentTime=step.t;else video.addEventListener('loadedmetadata',()=>video.currentTime=step.t,{once:true})};
      }
      li.append(time,node('span',null,step.text));ol.append(li);
    }
    card.append(ol);by('plans').append(card);
    const detailTime=c.detailByBranch?.[key]??c.detailTime;
    const detail=node('figure','detail '+key);detail.append(node('h3',null,Number.isFinite(detailTime)?name+' at '+tLabel(detailTime):name+' event view'),picture(versioned(base+'detail_'+key+'.jpg'),data.caption),node('p',null,data.caption));by('details').append(detail);
  }
  for(const [key,caption] of Object.entries(c.endViews||{})){
    const fig=node('figure','detail '+key);
    fig.append(picture(versioned(c.base+'/end_'+key+'.jpg'),caption),node('figcaption',null,caption));
    by('details').append(fig);
  }
  for(const [label,value] of c.facts){const f=node('div','fact');f.append(node('span',null,label),node('strong',null,value));by('facts').append(f)}
  for(const [name,caption] of c.charts){const f=node('figure','chart');f.append(picture(versioned(c.base+'/'+name),caption),node('p',null,caption));by('charts').append(f)}
  for(const [name,path] of c.downloads)by('downloads').append(link(name,mediaUrl(c,path)))
}
function route(){
  if(location.hash==='#mobile_washroom_bump'){location.replace('#everyday_drawer');return}
  const slug=location.hash.slice(1),found=cases.find(c=>c.id===slug);
  by('redirect').hidden=!(slug&&!found);
  by('redirect').textContent='The earlier task at this link has been replaced. Choose a robot task from the updated collection.';
  render(found||cases.find(c=>c.id===cases[0].defaultTrial)||cases[0])
}
window.addEventListener('hashchange',route);route();
