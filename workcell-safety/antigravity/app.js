'use strict';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!=null)x.textContent=text;if(cls)x.className=cls;return x};
const link=(text,url)=>{const a=el('a',text);a.href=url;return a};
let catalog=[],current,vids=[],playing=false,handle=0;
const branch=['unsafe','safe'], labels={unsafe:'Unsafe',safe:'Safe'};
function halt(){playing=false;cancelAnimationFrame(handle);vids.forEach(v=>v.pause());$('play').textContent='Play together'}
function sync(){if(!playing)return;if(vids.some(v=>v.ended))return halt();if(vids.every(v=>v.readyState>2)&&Math.abs(vids[0].currentTime-vids[1].currentTime)>.12)vids[1].currentTime=vids[0].currentTime;handle=requestAnimationFrame(sync)}
function jump(t){for(const v of vids){if(v.readyState>0)v.currentTime=Math.min(t,v.duration);else v.addEventListener('loadedmetadata',()=>v.currentTime=Math.min(t,v.duration),{once:true})}}
$('play').onclick=async()=>{if(playing)return halt();if(vids.some(v=>v.ended))jump(0);else jump(vids[0].currentTime);try{await Promise.all(vids.map(v=>v.play()));playing=true;$('play').textContent='Pause both';sync()}catch{halt()}};
$('event').onclick=()=>{halt();jump(current.event)};
function card(key,title){const article=el('article',null,'card '+key);article.append(el('h3',title));return article}
function imgFig(src,label,cls){const f=el('figure',null,cls),a=link('',src),i=el('img');i.src=src;i.alt=label;i.loading='lazy';a.append(i);f.append(a,el('figcaption',label));return f}
function use(c){
 halt();current=c;$('group').value=c.group;
 $('tasks').replaceChildren(...catalog.filter(x=>x.group===c.group).map(x=>{const b=el('button');b.type='button';b.setAttribute('aria-current',String(c.id===x.id));const i=el('img');i.src=x.id+'/thumb.jpg';i.alt='';b.append(i,el('span',x.title));b.onclick=()=>{location.hash=x.id};return b}));
 $('title').textContent=c.title;$('robot').textContent=c.robot;$('task').textContent=c.description;document.title=c.title+' · Antigravity edition';
 const orig=$('baseline');orig.hidden=!c.baseline;if(c.baseline)orig.href='../#'+c.baseline;
 $('time').textContent='Event at '+c.event.toFixed(2)+' s · '+c.duration.toFixed(2)+' s replay';
 $('notes').textContent=c.notes;$('detail').textContent=c.detail;$('criterion').textContent=c.criterion;
 vids=[];for(const id of ['players','plans','evidence','charts','facts','downloads','sources'])$(id).replaceChildren();
 for(const b of branch){
  const p=card(b,labels[b]+' replay'),v=el('video');v.controls=true;v.playsInline=true;v.preload='metadata';v.poster=c.id+'/'+b+'_poster.jpg';
  const s=el('source');s.type='video/mp4';s.src=c.film+'/'+b+'.mp4';v.append(s);vids.push(v);p.append(v,el('div',c[b].outcome,'caption'));$('players').append(p);
  const plan=card(b,labels[b]+' plan'),ol=el('ol',null,'steps');for(const step of c[b].steps){const li=el('li');li.append(el('span',Number(step.t).toFixed(2)+' s','clock'),el('span',step.text));ol.append(li)}plan.append(ol);$('plans').append(plan);
  $('evidence').append(imgFig(c.id+'/detail_'+b+'.jpg',labels[b]+' event view'));
 }
 const table=el('table',null,'metrics'),head=el('tr');for(const h of ['Measurement','Unsafe','Safe'])head.append(el('th',h));table.append(head);
 for (const [name,get] of [[c.metric+' · peak ('+c.unit+')',b=>Number(c[b].peak).toLocaleString('en-US',{maximumFractionDigits:3})],[c.force+' · peak (N)',b=>Number(c[b].force).toLocaleString('en-US',{maximumFractionDigits:3})],['Task goal reached',b=>c[b].completed?'Yes':'No']]){const r=el('tr');[name,...branch.map(get)].forEach(v=>r.append(el('td',v)));table.append(r)}$('facts').append(table);
 $('charts').append(imgFig(c.id+'/metric.png',c.metric,'chart'),imgFig(c.id+'/force.png',c.force,'chart'));
 $('downloads').append(...branch.map(b=>link(labels[b]+' solver trace (CSV.GZ)',c.id+'/'+b+'.csv.gz')));
 const sourceFile={legacy:'legacy',studies:'workcells',cnc:'cnc',mobile:c.id.includes('washroom')?'washroom':'mobile'}[c.group];
 $('sources').append(link('Gemini-generated Python','sources/neon_'+sourceFile+'.py'),link('Source hashes','sources/manifest.json'));if(c.source)$('sources').append(link('Robot model library',c.source));
}
function route(){const match=catalog.find(x=>x.id===location.hash.slice(1));use(match||catalog.find(x=>x.id==='legacy_05_parcel')||catalog[0])}
$('group').onchange=e=>{const c=catalog.find(x=>x.group===e.target.value);if(c)location.hash=c.id};
window.addEventListener('hashchange',route);
fetch('catalog.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(data=>{catalog=data;for(const option of [...$('group').options])if(!data.some(c=>c.group===option.value))option.remove();route()}).catch(()=>{$('title').textContent='Studies could not be loaded. Refresh to try again.'});
