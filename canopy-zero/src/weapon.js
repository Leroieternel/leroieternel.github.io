import * as THREE from 'three';
import {correctGrip} from './hand-pose.js?v=20261112-r5';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { groundHeight } from './physics.mjs?v=20261112-r5';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export class Weapon {
  constructor(camera,scene,audio,effects){
    this.camera=camera;this.scene=scene;this.audio=audio;this.effects=effects;
    this.group=new THREE.Group();camera.add(this.group);
    this.magazine=30;this.reserve=120;this.aim=0;this.aiming=false;this.trigger=false;this.cooldown=0;this.recoil=0;this.reloadTime=0;this.reloadDuration=2.35;this.reloading=false;this.onFire=()=>{};this.onReload=()=>{};
    this.base=new THREE.Vector3(.18,-.20,-.50);this.ads=new THREE.Vector3(0,-.30,-.41);
    this.solids=[];this.obstruction=0;this.obstructionRay=new THREE.Raycaster();this.muzzle=new THREE.Object3D();this.group.add(this.muzzle);
    this.flash=new THREE.Group();this.group.add(this.flash);this.flash.visible=false;
    const flashM=new THREE.MeshBasicMaterial({color:'#ffe6a0',transparent:true,opacity:.9,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending});
    const shape=new THREE.Shape();for(let i=0;i<16;i++){const a=i/16*Math.PI*2,r=i%2===0?.07:.014;if(i===0)shape.moveTo(Math.cos(a)*r,Math.sin(a)*r);else shape.lineTo(Math.cos(a)*r,Math.sin(a)*r);}shape.closePath();
    const fm=new THREE.Mesh(new THREE.ShapeGeometry(shape),flashM);this.flash.add(fm);const fm2=fm.clone();fm2.rotation.y=Math.PI/2;this.flash.add(fm2);
    this.muzzleLight=new THREE.PointLight('#ffc373',0,3,2);this.group.add(this.muzzleLight);
  }
  async load(manager){
    const loader=new GLTFLoader(manager).setMeshoptDecoder(MeshoptDecoder);
    const gltf=await loader.loadAsync('./assets/fp/m4a1.glb');
    const holder=gltf.scene;holder.scale.setScalar(.5);this.group.add(holder);this.model=holder;
    const bones={};let skinnedMeshes=0;
    holder.traverse(m=>{if(m.isBone)bones[m.name]=m;if(!m.isMesh)return;if(m.isSkinnedMesh)skinnedMeshes++;m.frustumCulled=false;m.castShadow=false;m.receiveShadow=false;
      if(m.material){m.material=m.material.clone();for(const t of [m.material.map,m.material.normalMap,m.material.roughnessMap])if(t)t.anisotropy=8;
        if(m.material.name==='arms'){m.material.roughness=.88;m.material.metalness=0;m.material.envMapIntensity=.75;}
        else{m.material.color.set('#8a9691');m.material.metalness=.82;m.material.roughness=.64;m.material.envMapIntensity=1.1;}
      }
    });
    const poseReport=correctGrip(holder,bones);
    holder.updateMatrixWorld(true);const gun=holder.getObjectByName('Gun_m4a1');const box=new THREE.Box3().setFromObject(gun);
    this.top=.109;this.muzzle.position.copy(holder.getObjectByName('MuzzleSocket').position).multiplyScalar(.5);
    this.flash.position.copy(this.muzzle.position);this.muzzleLight.position.copy(this.muzzle.position);
    this.addOptic(this.top);this.ads.set(0,-(this.top+.068),-.48);
    this.handInfo={pose:poseReport,source:'DJMaesen / bumstrum; ccransh; IRONLINE asset adaptation',license:'CC BY 4.0',hands:2,skinnedMeshes,skeletonBones:Object.keys(bones).length,fingerJoints:Object.keys(bones).filter(n=>n.startsWith('Bone_')).length,anatomical:true,continuousForearms:true,textured:true};
    this.hands={entries:[{wrapper:holder,bones}],info:this.handInfo};
    this.modelInfo={dimensions:box.getSize(new THREE.Vector3()).toArray(),source:'Firewarden M4A1 / CC BY 4.0',rigged:true};this.group.position.copy(this.base);
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
    const forward=new THREE.Vector3();this.camera.getWorldDirection(forward);const ray=new THREE.Ray(this.camera.position,forward),box=new THREE.Box3(),point=new THREE.Vector3();let near=1.05;
    for(const c of this.colliders||[]){if(c.disabled)continue;const r=c.radius||.05;if(c.type==='box')box.min.set(c.minX,c.bottom,c.minZ),box.max.set(c.maxX,c.top,c.maxZ);else if(c.type==='capsule')box.min.set(Math.min(c.a.x,c.b.x)-r,c.bottom,Math.min(c.a.z,c.b.z)-r),box.max.set(Math.max(c.a.x,c.b.x)+r,c.top,Math.max(c.a.z,c.b.z)+r);else box.min.set(c.x-r,c.bottom,c.z-r),box.max.set(c.x+r,c.top,c.z+r);if(ray.intersectBox(box,point))near=Math.min(near,point.distanceTo(this.camera.position));}
    // Check the barrel width and lower handguard, not only the reticle ray.
    if(this.meshCollision){for(const offset of [[0,0,0],[-.15,-.12,0],[.15,-.12,0],[0,-.25,0]]){const origin=new THREE.Vector3(...offset).applyQuaternion(this.camera.quaternion).add(this.camera.position);near=Math.min(near,this.meshCollision.rayDistance(origin,forward,1.05));}}
    for(let d=.12;d<1.01;d+=.12){point.copy(this.camera.position).addScaledVector(forward,d);if(point.y-.20<groundHeight(point.x,point.z)+.03){near=Math.min(near,d);break;}}
    this.obstruction=THREE.MathUtils.damp(this.obstruction,THREE.MathUtils.clamp((.95-near)/.65,0,1),16,dt);
    this.group.position.z+=this.obstruction*.32;this.group.position.y-=this.obstruction*.12;
    this.group.rotation.set(this.recoil*(1-this.aim*.4),0,-.035*(1-this.aim));
    this.group.rotation.x-=this.obstruction*.9;
    if(player.sprint&&active){this.group.rotation.z-=.35;this.group.rotation.x-=.23;this.group.position.y-=.07;}
    if(this.reloading){const t=this.reloadTime/this.reloadDuration,w=Math.sin(t*Math.PI);this.group.rotation.z+=w*.65;this.group.rotation.x-=w*.4;this.group.position.y-=w*.16;}
    this.camera.fov=THREE.MathUtils.lerp(74,49,this.aim);this.camera.updateProjectionMatrix();
  }
}
