import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export class Weapon {
  constructor(camera,scene,audio,effects){
    this.camera=camera;this.scene=scene;this.audio=audio;this.effects=effects;
    this.group=new THREE.Group();camera.add(this.group);
    this.magazine=30;this.reserve=120;this.aim=0;this.aiming=false;this.trigger=false;this.cooldown=0;this.recoil=0;this.reloadTime=0;this.reloadDuration=2.35;this.reloading=false;this.onFire=()=>{};this.onReload=()=>{};
    this.base=new THREE.Vector3(.205,-.34,-.50);this.ads=new THREE.Vector3(0,-.30,-.41);
    this.muzzle=new THREE.Object3D();this.group.add(this.muzzle);
    this.flash=new THREE.Group();this.group.add(this.flash);this.flash.visible=false;
    const flashM=new THREE.MeshBasicMaterial({color:'#ffe6a0',transparent:true,opacity:.9,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending});
    const shape=new THREE.Shape();for(let i=0;i<16;i++){const a=i/16*Math.PI*2,r=i%2===0?.07:.014;if(i===0)shape.moveTo(Math.cos(a)*r,Math.sin(a)*r);else shape.lineTo(Math.cos(a)*r,Math.sin(a)*r);}shape.closePath();
    const fm=new THREE.Mesh(new THREE.ShapeGeometry(shape),flashM);this.flash.add(fm);const fm2=fm.clone();fm2.rotation.y=Math.PI/2;this.flash.add(fm2);
    this.muzzleLight=new THREE.PointLight('#ffc373',0,3,2);this.group.add(this.muzzleLight);
  }
  async load(manager){
    const textureLoader=new THREE.TextureLoader(manager);
    const [texture,normal,roughness,metallic]=await Promise.all(['Base_Color','Normal','Roughness','Metallic'].map(name=>textureLoader.loadAsync('./assets/M4A1_'+name+'.png')));texture.colorSpace=THREE.SRGBColorSpace;for(const map of [texture,normal,roughness,metallic])map.anisotropy=8;
    const fbx=await new FBXLoader(manager).loadAsync('./assets/M4A1.fbx');
    const holder=new THREE.Group();holder.add(fbx);holder.updateMatrixWorld(true);
    let box=new THREE.Box3().setFromObject(holder),size=box.getSize(new THREE.Vector3());
    const major=size.x>size.z?'x':'z';
    const limits={lo:box.min[major],hi:box.max[major]},span=limits.hi-limits.lo;
    const ends=[new THREE.Box3(),new THREE.Box3()],v=new THREE.Vector3();
    fbx.traverse(m=>{if(!m.isMesh)return;const a=m.geometry.attributes.position;for(let i=0;i<a.count;i++){v.fromBufferAttribute(a,i).applyMatrix4(m.matrixWorld);if(v[major]<limits.lo+span*.12)ends[0].expandByPoint(v);if(v[major]>limits.hi-span*.12)ends[1].expandByPoint(v);}});
    const section=b=>{const s=b.getSize(new THREE.Vector3());return s.y*(major==='x'?s.z:s.x);};
    const tipPositive=section(ends[1])<section(ends[0]);
    if(major==='x')holder.rotation.y=tipPositive?Math.PI/2:-Math.PI/2;else if(tipPositive)holder.rotation.y=Math.PI;
    holder.updateMatrixWorld(true);box=new THREE.Box3().setFromObject(holder);size=box.getSize(new THREE.Vector3());
    const scale=.94/size.z;holder.scale.setScalar(scale);holder.updateMatrixWorld(true);box=new THREE.Box3().setFromObject(holder);
    const center=box.getCenter(new THREE.Vector3());holder.position.sub(center);holder.position.y+=.015;holder.updateMatrixWorld(true);
    fbx.traverse(m=>{if(m.isMesh){m.material=new THREE.MeshStandardMaterial({map:texture,normalMap:normal,roughnessMap:roughness,metalnessMap:metallic,color:'#d0d4d1',metalness:1,roughness:.86,normalScale:new THREE.Vector2(.8,.8),envMapIntensity:1.25});m.castShadow=false;m.receiveShadow=false;m.frustumCulled=false;m.geometry.computeVertexNormals();}});
    this.group.add(holder);this.model=holder;
    box=new THREE.Box3().setFromObject(holder);
    this.top=box.max.y;this.muzzle.position.set(0,this.top-.075,box.min.z-.025);
    this.flash.position.copy(this.muzzle.position);this.muzzleLight.position.copy(this.muzzle.position);
    this.addOptic(this.top);this.addHands();this.ads.set(0,-(this.top+.068),-.42);
    this.modelInfo={originalAxis:major,tipPositive,dimensions:box.getSize(new THREE.Vector3()).toArray()};this.group.position.copy(this.base);
  }
  addOptic(top){
    const steel=new THREE.MeshStandardMaterial({color:'#3e4441',metalness:.8,roughness:.32});const rubber=new THREE.MeshStandardMaterial({color:'#171d1b',metalness:.05,roughness:.85});
    const mount=new THREE.Mesh(new RoundedBoxGeometry(.055,.023,.1,2,.005),steel);mount.position.set(0,top+.013,.04);this.group.add(mount);
    const optic=new THREE.Mesh(new THREE.TorusGeometry(.043,.009,10,48),steel);optic.position.set(0,top+.068,.045);this.group.add(optic);const second=optic.clone();second.position.z-=.05;this.group.add(second);
    const barrel=new THREE.Mesh(new THREE.CylinderGeometry(.05,.05,.048,48,1,true),steel);barrel.rotation.x=Math.PI/2;barrel.position.set(0,top+.068,.022);this.group.add(barrel);
    const glass=new THREE.Mesh(new THREE.CircleGeometry(.041,48),new THREE.MeshBasicMaterial({color:'#709e9b',transparent:true,opacity:.13,depthWrite:false,side:THREE.DoubleSide}));glass.position.set(0,top+.068,.048);this.group.add(glass);
    const dot=new THREE.Mesh(new THREE.CircleGeometry(.0013,16),new THREE.MeshBasicMaterial({color:'#ff5244',toneMapped:false,depthWrite:false}));dot.position.set(0,top+.068,.051);this.group.add(dot);this.redDot=dot;
    const knob=new THREE.Mesh(new THREE.CylinderGeometry(.014,.014,.019,16),rubber);knob.rotation.z=Math.PI/2;knob.position.set(.054,top+.068,.016);this.group.add(knob);
    for(const z of [.08,-.006]){const screw=new THREE.Mesh(new THREE.CylinderGeometry(.004,.004,.005,12),steel);screw.rotation.z=Math.PI/2;screw.position.set(.03,top+.014,z);this.group.add(screw);}
  }
  addHands(){
    const cloth=new THREE.MeshStandardMaterial({color:'#59614c',roughness:.95}),glove=new THREE.MeshStandardMaterial({color:'#343b30',roughness:.92}),palm=new THREE.MeshStandardMaterial({color:'#242b23',roughness:.94});
    const segment=(a,b,r1,r2,mat)=>{const d=new THREE.Vector3().subVectors(b,a),m=new THREE.Mesh(new THREE.CylinderGeometry(r2,r1,d.length(),16),mat);m.position.copy(a).add(b).multiplyScalar(.5);m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());this.group.add(m);return m;};
    segment(new THREE.Vector3(-.20,-.28,.34),new THREE.Vector3(-.085,-.095,-.19),.058,.044,cloth);
    const hand=new THREE.Mesh(new THREE.SphereGeometry(1,20,14),glove);hand.position.set(-.035,-.06,-.19);hand.scale.set(.056,.045,.077);hand.rotation.z=-.3;this.group.add(hand);
    for(let i=0;i<4;i++){
      const finger=new THREE.Mesh(new THREE.CapsuleGeometry(.0095,.055,5,10),glove);finger.position.set(.006,-.043,-.235+i*.025);finger.rotation.z=1.25;finger.rotation.x=.35;this.group.add(finger);
      const knuckle=new THREE.Mesh(new THREE.SphereGeometry(.011,10,8),palm);knuckle.position.set(-.02,-.017,-.235+i*.025);this.group.add(knuckle);
    }
    segment(new THREE.Vector3(.13,-.3,.43),new THREE.Vector3(.027,-.115,.19),.058,.042,cloth);
    const right=new THREE.Mesh(new THREE.SphereGeometry(1,20,14),glove);right.position.set(.02,-.1,.17);right.scale.set(.044,.075,.043);right.rotation.x=-.3;this.group.add(right);
  }
  reload(){if(this.reloading||this.magazine===30||this.reserve<=0)return false;this.reloading=true;this.aiming=false;this.reloadTime=0;this.audio.magazine();this.onReload();return true;}
  refill(){this.reserve=150;this.magazine=30;this.reloading=false;this.reloadTime=0;}
  reset(){this.magazine=30;this.reserve=120;this.reloading=false;this.reloadTime=0;this.aiming=false;this.aim=0;this.trigger=false;this.cooldown=0;this.recoil=0;}
  update(dt,time,player,active){
    this.cooldown=Math.max(0,this.cooldown-dt);this.flash.visible=false;this.muzzleLight.intensity=0;
    if(this.reloading&&active){const before=this.reloadTime;this.reloadTime+=dt;if(before<1.65&&this.reloadTime>=1.65)this.audio.bolt();if(this.reloadTime>=this.reloadDuration){const amount=Math.min(30-this.magazine,this.reserve);this.magazine+=amount;this.reserve-=amount;this.reloading=false;}}
    if(active&&this.trigger&&!this.reloading&&!player.sprint&&this.cooldown<=0){
      if(this.magazine>0){this.magazine--;this.cooldown=.105;this.recoil=Math.min(.13,this.recoil+.055);this.flash.visible=true;this.flash.rotation.z=Math.random()*6.28;this.muzzleLight.intensity=5;this.audio.fire();this.camera.updateMatrixWorld(true);this.effects.eject(this.camera);this.onFire();}
      else{this.cooldown=.25;this.audio.empty();}
    }
    this.recoil=THREE.MathUtils.damp(this.recoil,0,17,dt);this.aim=THREE.MathUtils.damp(this.aim,this.aiming&&!this.reloading&&!player.sprint?1:0,17,dt);
    this.group.position.lerpVectors(this.base,this.ads,this.aim);
    const walk=player.moving&&active?Math.sin(player.bob)*.006*(1-this.aim):Math.sin(time*1.5)*.001;
    this.group.position.y+=walk;this.group.position.x+=Math.cos(player.bob*.5)*.003*(1-this.aim)*(player.moving?1:0);this.group.position.z+=this.recoil*.4;
    this.group.rotation.set(this.recoil*(1-this.aim*.4),0,-.035*(1-this.aim));
    if(player.sprint&&active){this.group.rotation.z-=.35;this.group.rotation.x-=.23;this.group.position.y-=.07;}
    if(this.reloading){const t=this.reloadTime/this.reloadDuration,w=Math.sin(t*Math.PI);this.group.rotation.z+=w*.65;this.group.rotation.x-=w*.4;this.group.position.y-=w*.16;}
    this.camera.fov=THREE.MathUtils.lerp(74,49,this.aim);this.camera.updateProjectionMatrix();
  }
}
