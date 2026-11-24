'use strict';
const cases=window.WORKCELLS;
const node=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e};
const by=id=>document.getElementById(id);
const link=(text,url)=>{const a=node('a',null,text);a.href=releaseMediaUrl(url);return a};
let item,vids=[],paired=false,tick=0;
const tLabel=t=>t.toFixed(2)+' s';
function stopPair(){
  paired=false;cancelAnimationFrame(tick);
  by('play').textContent='Play together';
}
function pauseBoth(){stopPair();vids.forEach(v=>v.pause())}
function loop(){
  if(!paired)return;
  if(vids.every(atReplayEnd)){pauseBoth();return}
  syncLiveReplays(vids);
  tick=requestAnimationFrame(loop);
}
by('play').onclick=async()=>{
  if(paired){pauseBoth();return}
  const at=pairPosition(vids);
  paired=true;by('play').textContent='Pause both';
  try{await startReplays(vids,at);if(paired)loop()}catch{pauseBoth()}
};
function seekTo(t){
  pauseBoth();
  vids.forEach(v=>{if(v.readyState>=1)v.currentTime=t;else v.addEventListener('loadedmetadata',()=>v.currentTime=t,{once:true})})
}
by('event').onclick=()=>seekTo(item.eventFrameTime??item.event);
function picture(url,alt){
  const a=link('',url);a.target='_blank';a.rel='noopener';const im=node('img');im.src=releaseMediaUrl(url);im.alt=alt;im.loading='lazy';a.append(im);return a;
}
for(const c of cases){
  const b=node('button','taskbtn');b.type='button';b.dataset.id=c.id;b.setAttribute('aria-pressed','false');
  const im=node('img');im.src=releaseMediaUrl(c.base+'/thumb.jpg');im.alt='';b.append(im,node('span',null,c.short));
  b.onclick=()=>{if(location.hash==='#'+c.id)render(c);else location.hash=c.id};by('nav').append(b);
}
function render(c){
  pauseBoth();item=c;vids=[];
  const editionId=c.id==='cnc_full'?c.id:'legacy_'+c.id;
  by('updated-task').href=by('updated-edition').href='../antigravity/#'+editionId;
  document.title=c.title+' · Workcell Safety';
  by('title').textContent=c.title;by('description').textContent=c.description;by('category').textContent=c.category;
  by('timing').textContent='Event at '+tLabel(c.event)+'  ·  '+Math.round(c.duration)+' s replay';
  by('plan-intro').textContent=c.planIntro;
  by('detailintro').textContent=c.detailIntro;
  by('measurement').textContent=c.method;
  by('auditnote').textContent=c.auditnote;
  for(const b of by('nav').children)b.setAttribute('aria-pressed',String(b.dataset.id===c.id));
  for(const id of ['players','plans','details','facts','charts','downloads'])by(id).replaceChildren();
  for(const key of ['unsafe','safe']){
    const data=c[key],name=key==='unsafe'?'Unsafe':'Safe',base=c.base+'/';
    const player=node('div','player '+key);player.append(node('h3',null,name+' replay'));
    const video=node('video');video.setAttribute('aria-label',name+' replay of '+c.title);video.controls=true;video.playsInline=true;video.preload='metadata';video.poster=releaseMediaUrl(base+key+'_poster.jpg');video.src=(c.filmBase||c.base)+'/'+key+'.mp4';video.addEventListener('pause',()=>{if(paired&&vids.includes(video)&&!atReplayEnd(video))pauseBoth()});vids.push(video);
    player.append(video,node('small',null,data.summary));by('players').append(player);
    const card=node('div','stepcard '+key);card.append(node('h3',null,name+' plan'));const ol=node('ol','steps');
    for(const step of data.steps){const li=node('li',step.hazard?'haz':'');li.append(node('time',null,tLabel(step.t)),node('span',null,step.text));ol.append(li)}
    card.append(ol);by('plans').append(card);
    const detailTime=c.detailByBranch?.[key]??c.detailTime??c.event;
    const detail=node('figure','detail '+key);detail.append(node('h3',null,name+' at '+tLabel(detailTime)),picture(base+'detail_'+key+'.jpg',data.caption),node('p',null,data.caption));by('details').append(detail);
  }
  for(const [label,value] of c.facts){const f=node('div','fact');f.append(node('span',null,label),node('strong',null,value));by('facts').append(f)}
  for(const [name,caption] of c.charts){const f=node('figure','chart');f.append(picture(c.base+'/'+name,caption),node('p',null,caption));by('charts').append(f)}
  for(const [name,path] of c.downloads)by('downloads').append(link(name,(path.endsWith('.mp4')&&c.filmBase?c.filmBase:c.base)+'/'+path))
}
function route(){render(cases.find(c=>c.id===location.hash.slice(1))||cases.find(c=>c.id==='03_cafe')||cases[0])}
window.addEventListener('hashchange',route);route();
