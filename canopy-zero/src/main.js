import * as THREE from 'three';
import { createWorld } from './world.js?v=20261111-r2';
import { Player } from './player.js?v=20261111-r2';
import { Weapon } from './weapon.js?v=20261111-r2';
import { Effects } from './effects.js?v=20261111-r2';
import { FieldAudio } from './audio.js?v=20261111-r2';
import { groundHeight } from './physics.mjs?v=20261111-r2';

const $=id=>document.getElementById(id);
const surfaceNames={water:'水面',soil:'湿润土壤',wood:'木材',stone:'岩石',metal:'金属'};
let active=false,started=false,ready=false,elapsed=0,hits=0,shots=0,lastHit=null;
let world,player,weapon,effects,renderer,scene,camera,audio;
let toastTimer,markerTimer,qaFrozen=new URLSearchParams(location.search).has('qa');
function toast(text){$('toast').textContent=text;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),2600);}
function fatal(error){console.error(error);$('fatal-message').textContent=error instanceof Error?error.message:String(error);$('fatal').hidden=false;$('load-text').textContent='加载遇到问题';}

async function init(){
  renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
  renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.shadowMap.enabled=true;renderer.shadowMap.autoUpdate=false;renderer.shadowMap.needsUpdate=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.08;
  $('viewport').appendChild(renderer.domElement);renderer.domElement.tabIndex=0;
  renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();pause();fatal(new Error('图形上下文已断开。请关闭其它占用显存的页面后重新加载。'));});
  scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(74,innerWidth/innerHeight,.035,160);scene.add(camera);
  audio=new FieldAudio();effects=new Effects(scene,audio);weapon=new Weapon(camera,scene,audio,effects);weapon.group.visible=false;
  const manager=new THREE.LoadingManager();let maxProgress=0;
  manager.onProgress=(url,done,total)=>{maxProgress=Math.max(maxProgress,Math.min(92,done/total*90));$('load-progress').style.width=`${maxProgress}%`;$('load-text').textContent=url.includes('M4A1')?'检查枪械与材质':'载入雨林材质';};
  [world]=await Promise.all([createWorld(scene,renderer,manager),weapon.load(manager),effects.load(manager)]);
  effects.colliders=world.colliders;effects.puddles=world.puddles;weapon.solids=world.solids;weapon.colliders=world.colliders;
  player=new Player(camera,world.colliders);player.onStep=sprint=>audio.step(sprint);
  weapon.onFire=fire;weapon.onReload=()=>toast('正在更换弹匣');
  bindInput();ready=true;$('enter').disabled=false;$('enter-label').textContent='进入雨林';$('load-progress').style.width='100%';$('load-text').textContent='场景就绪 · 点击进入后锁定鼠标';
  let previous=performance.now(),simTime=0,uiTime=0,shadowTime=0;
  function frame(now){
    const dt=Math.min((now-previous)/1000,.04);previous=now;if(qaFrozen){requestAnimationFrame(frame);return;}simTime+=dt;
    if(active){elapsed+=dt;player.update(dt,weapon.aiming);}
    else if(!started){camera.position.set(1.1,1.8,13);camera.rotation.set(.035+Math.sin(simTime*.1)*.006,-.13+Math.sin(simTime*.09)*.018,0,'YXZ');}
    weapon.update(dt,simTime,player,active);
    world.update(dt,simTime,camera);if(active)effects.update(dt);shadowTime+=dt;if(shadowTime>.1&&world.targets.some(t=>t.body.angularVelocity.some(v=>Math.abs(v)>.006)||t.body.velocity.some(v=>Math.abs(v)>.006))){renderer.shadowMap.needsUpdate=true;shadowTime=0;}
    if(active){
      const near=player.position.distanceTo(new THREE.Vector3(world.supply.x,groundHeight(world.supply.x,world.supply.z),world.supply.z))<2.3;
      $('interaction').hidden=!near;
      $('crosshair').classList.toggle('aiming',weapon.aim>.8);$('crosshair').style.setProperty('--gap',`${6+weapon.recoil*100+(player.moving?3:0)}px`);
    }
    uiTime+=dt;if(uiTime>.08){updateHUD();uiTime=0;}
    renderer.render(scene,camera);requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  if(new URLSearchParams(location.search).has('qa'))installQA();
  window.dispatchEvent(new Event('canopy-ready'));
}

function validSolids(){return world.solids.filter(m=>!m.userData.breakable||m.userData.breakable.alive);}
const ray=new THREE.Raycaster();ray.far=130;
function fire(){
  shots++;scene.updateMatrixWorld(true);camera.updateMatrixWorld(true);
  const direction=new THREE.Vector3();camera.getWorldDirection(direction);
  const spread=weapon.aim>.8?.0007:player.moving?.008:.002;
  direction.add(new THREE.Vector3((Math.random()-.5)*spread,(Math.random()-.5)*spread,0).applyQuaternion(camera.quaternion)).normalize();
  ray.set(camera.position,direction);const solids=validSolids();let hit=ray.intersectObjects(solids,false)[0];
  // Check the muzzle-to-reticle segment too; cover can block the barrel.
  const muzzle=weapon.muzzle.getWorldPosition(new THREE.Vector3());
  const aimPoint=hit?hit.point.clone():camera.position.clone().addScaledVector(direction,130);
  const muzzleDirection=aimPoint.clone().sub(muzzle).normalize();
  ray.set(muzzle,muzzleDirection);ray.far=muzzle.distanceTo(aimPoint)+.015;
  const obstruction=ray.intersectObjects(solids,false)[0];if(obstruction&&(!hit||obstruction.distance<ray.far-.025))hit=obstruction;ray.far=130;
  if(hit){
    const surface=effects.impact(hit,direction);lastHit={surface,object:hit.object.name||hit.object.uuid,point:hit.point.toArray(),normal:hit.face.normal.clone().transformDirection(hit.object.matrixWorld).toArray(),distance:camera.position.distanceTo(hit.point)};
    $('impact-status').textContent=`命中 ${surfaceNames[surface]} · ${lastHit.distance.toFixed(1)} m`;
    if(hit.object.userData.target){renderer.shadowMap.needsUpdate=true;world.hitTarget(hit,muzzleDirection);hits++;$('hitmarker').classList.add('show');clearTimeout(markerTimer);markerTimer=setTimeout(()=>$('hitmarker').classList.remove('show'),130);}
    const object=hit.object.userData.breakable;if(object&&object.alive){object.hp--;if(object.hp<=0){effects.breakCrate(object);renderer.shadowMap.needsUpdate=true;toast('木箱已破碎');}}
  }else{$('impact-status').textContent='未命中可交互表面';lastHit=null;}
  player.pitch=THREE.MathUtils.clamp(player.pitch+.004*(weapon.aim>.8?.6:1),-1.43,1.43);
}

async function enter(){
  if(!ready)return;
  try{
    await audio.start();
    const result=renderer.domElement.requestPointerLock();if(result?.then)await result;
  }catch(error){toast('鼠标锁定未成功，请点击「继续探索」重试。');if(!started)$('load-text').textContent='请允许浏览器锁定鼠标，或在独立浏览器窗口打开。';console.warn('Pointer lock:',error.message);}
}
function pause(){
  if(!started)return;active=false;weapon.trigger=false;weapon.aiming=false;player.keys.clear();audio.pause();$('pause-menu').hidden=false;
  if(document.pointerLockElement)document.exitPointerLock();
}
function reset(){world.reset();effects.reset();weapon.reset();player.reset();elapsed=0;hits=0;shots=0;lastHit=null;$('impact-status').textContent='射击后显示命中材质';updateHUD();toast('试射场已重置');enter();}
function setRain(enabled){world.setRain(enabled);audio.setRain(enabled);$('rain').checked=enabled;$('climate-label').textContent=enabled?'细雨 · 潮湿':'雨后 · 林间薄雾';$('surface-status').textContent=enabled?'雨林试射区 · 细雨':'雨林试射区 · 雨后';}
function updateHUD(){
  if(!weapon)return;$('mag').textContent=String(weapon.magazine).padStart(2,'0');$('reserve').textContent=weapon.reserve;
  $('clock').textContent=`${String(Math.floor(elapsed/60)).padStart(2,'0')}:${String(Math.floor(elapsed%60)).padStart(2,'0')}`;
  $('hit-count').textContent=String(hits).padStart(2,'0');const degree=Math.round((-player.yaw*180/Math.PI+360)%360);const dir=['N','NE','E','SE','S','SW','W','NW'][Math.round(degree/45)%8];$('bearing').textContent=`${dir} ${String(degree).padStart(3,'0')}`;
  $('ammo-state').textContent=weapon.reloading?'RELOADING / 正在换弹':weapon.magazine===0?'EMPTY / 按 R 换弹':'5.56 × 45 · AUTO';
  $('reload-progress').style.width=`${weapon.reloading?weapon.reloadTime/weapon.reloadDuration*100:weapon.magazine/30*100}%`;
}
function bindInput(){
  $('enter').addEventListener('click',enter);$('resume').addEventListener('click',enter);$('reset-button').addEventListener('click',reset);$('pause-button').addEventListener('click',pause);
  const open=id=>()=>$(id).showModal();$('show-controls').onclick=open('controls');$('pause-controls').onclick=open('controls');$('settings-button').onclick=open('settings');$('credits-button').onclick=open('credits');
  document.querySelectorAll('dialog').forEach(d=>{d.querySelector('.close').onclick=()=>d.close();d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});});
  $('sensitivity').oninput=e=>player.sensitivity=Number(e.target.value);$('sound').onchange=e=>audio.setEnabled(e.target.checked);$('rain').onchange=e=>setRain(e.target.checked);
  $('quality').onchange=e=>{const quality=e.target.value;renderer.setPixelRatio(Math.min(devicePixelRatio,quality==='high'?1.5:quality==='medium'?1.15:.85));renderer.shadowMap.enabled=quality!=='low';renderer.shadowMap.needsUpdate=true;scene.traverse(o=>{if(o.material){const ms=Array.isArray(o.material)?o.material:[o.material];ms.forEach(m=>m.needsUpdate=true);}});};
  document.addEventListener('pointerlockchange',()=>{
    if(document.pointerLockElement===renderer.domElement){active=true;started=true;$('menu').hidden=true;$('hud').hidden=false;$('pause-menu').hidden=true;weapon.group.visible=true;player.updateCamera(0,false);audio.start();renderer.domElement.focus();}
    else if(started){active=false;weapon.trigger=false;weapon.aiming=false;player.keys.clear();audio.pause();$('pause-menu').hidden=false;}
  });
  document.addEventListener('pointerlockerror',()=>toast('浏览器未锁定鼠标。请关闭其它弹窗后重试。'));
  document.addEventListener('mousemove',e=>{if(active&&!qaFrozen&&document.pointerLockElement===renderer.domElement)player.look(e.movementX,e.movementY,weapon.aiming);});
  document.addEventListener('mousedown',e=>{if(!active)return;if(e.button===0)weapon.trigger=true;if(e.button===2)weapon.aiming=true;});
  document.addEventListener('mouseup',e=>{if(e.button===0)weapon.trigger=false;if(e.button===2)weapon.aiming=false;});
  document.addEventListener('contextmenu',e=>{if(active)e.preventDefault();});
  document.addEventListener('keydown',e=>{
    if(!active)return;if(['Space','ShiftLeft','KeyW','KeyA','KeyS','KeyD','KeyC'].includes(e.code))e.preventDefault();player.keys.add(e.code);
    if(e.repeat)return;if(e.code==='Space')player.jumpRequested=true;if(e.code==='KeyR')weapon.reload();if(e.code==='KeyT'){setRain(!$('rain').checked);toast($('rain').checked?'细雨已开启':'细雨已关闭');}
    if(e.code==='KeyF'&&Math.hypot(player.position.x-world.supply.x,player.position.z-world.supply.z)<2.3){weapon.refill();audio.magazine();toast('弹药已补满');}
    if(e.code==='Escape')pause();
  });
  document.addEventListener('keyup',e=>player.keys.delete(e.code));
  window.addEventListener('blur',()=>{if(active)pause();});document.addEventListener('visibilitychange',()=>{if(document.hidden&&active)pause();});
  window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
}

function installQA(){
  let qaTime=0;let savedVisibility=[];
  // Only exposed when explicitly launching the local QA URL with ?qa=1.
  window.__canopy={
    freeze:value=>{qaFrozen=value;},
    focusImpact:()=>{const hit=lastHit;if(!hit)return;const object=world.solids.find(o=>(o.name||o.uuid)===hit.object);const keep=new Set([camera,object,...effects.decals,...effects.waves.map(w=>w.mesh),...effects.particles.map(p=>p.mesh)]);if(hit.surface==='water')keep.add(scene.getObjectByName('forest-floor'));const visible=o=>{let keepObject=false;o.traverse(n=>{if(keep.has(n)||n.isLight)keepObject=true;});return keepObject;};savedVisibility=scene.children.map(o=>[o,o.visible]);scene.children.forEach(o=>o.visible=visible(o));weapon.group.visible=false;const point=new THREE.Vector3(...hit.point),normal=new THREE.Vector3(...hit.normal);if(normal.dot(camera.position.clone().sub(point))<0)normal.negate();camera.position.copy(point).addScaledVector(normal,hit.surface==='water'?1.8:1.1);if(hit.surface==='water')camera.position.z+=.7;camera.lookAt(point);camera.fov=55;camera.updateProjectionMatrix();renderer.setPixelRatio(1);renderer.shadowMap.enabled=false;},
    restoreView:()=>{for(const [o,visible]of savedVisibility)o.visible=visible;weapon.group.visible=true;player.updateCamera(0,false);},
    showWeaponOnly:()=>{scene.children.forEach(o=>{if(o!==camera&&!o.isLight)o.visible=false;});renderer.setPixelRatio(1);renderer.shadowMap.enabled=false;},
    inspectHands:()=>weapon.hands.entries.map(e=>({position:e.wrapper.position.toArray(),bones:Object.values(e.bones).map(b=>({name:b.name,position:b.position.toArray()}))})),
    setQuality:()=>{renderer.setPixelRatio(1);world.sun.shadow.mapSize.set(1024,1024);renderer.shadowMap.needsUpdate=true;},
    capture:(quick=false)=>{if(quick){renderer.setPixelRatio(.5);renderer.shadowMap.enabled=false;scene.environment=null;}renderer.render(scene,camera);return renderer.domElement.toDataURL('image/png');},
    advance:seconds=>{for(let t=0;t<seconds;t+=1/120){if(active){player.update(1/120,weapon.aiming);elapsed+=1/120;}qaTime+=1/120;weapon.update(1/120,qaTime,player,active);world.update(1/120,qaTime,camera);effects.update(1/120);}updateHUD();},
    snapshot:()=>({ready,active,started,position:player.position.toArray(),yaw:player.yaw,pitch:player.pitch,grounded:player.grounded,contacts:player.contacts,ammo:weapon.magazine,reserve:weapon.reserve,reloading:weapon.reloading,aim:weapon.aim,shots,hits,lastHit,decals:effects.decals.length,casings:effects.casings.length,gun:weapon.modelInfo,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,flowTime:qaTime,trees:world.trees.length,crates:world.breakables.map(b=>({hp:b.hp,alive:b.alive})),effects:effects.stats(),forest:world.forestInfo,hands:weapon.handInfo,targets:world.targets.map(t=>({label:t.label,angle:t.angle,position:t.pivot.position.toArray(),rotation:t.body.rotation,angularVelocity:t.body.angularVelocity,lastImpulse:t.body.lastImpulse}))}),
    aimAt:(x,y,z)=>{const d=new THREE.Vector3(x,y,z).sub(camera.position).normalize();player.yaw=Math.atan2(-d.x,-d.z);player.pitch=Math.asin(d.y);player.updateCamera(0,false);},
    teleport:(x,z,y)=>{player.position.set(x,y??groundHeight(x,z),z);player.velocity.set(0,0,0);player.updateCamera(0,false);},
    step:(seconds,keys=[])=>{player.keys=new Set(keys);for(let t=0;t<seconds;t+=1/120)player.update(1/120,false);player.keys.clear();},
    reset,
    get colliderCount(){return world.colliders.length;}
  };
}
init().catch(fatal);
