import * as THREE from 'three';
import { DecalGeometry } from 'three/addons/geometries/DecalGeometry.js';
import { groundHeight } from './physics.mjs';

function holeTexture(surface) {
  const c=document.createElement('canvas');c.width=c.height=128;const ctx=c.getContext('2d');
  const dirt=surface==='soil',wood=surface==='wood',stone=surface==='stone';
  const radius=dirt?46:wood?28:26;
  const gradient=ctx.createRadialGradient(64,64,2,64,64,61);
  gradient.addColorStop(0,'rgba(10,9,5,1)');gradient.addColorStop(.22,'rgba(15,14,9,.98)');gradient.addColorStop(.4,wood?'rgba(80,57,30,.9)':stone?'rgba(103,105,92,.9)':'rgba(35,32,22,.9)');gradient.addColorStop(.62,dirt?'rgba(65,54,33,.72)':'rgba(25,26,21,.38)');gradient.addColorStop(1,'rgba(24,24,19,0)');ctx.fillStyle=gradient;ctx.fillRect(0,0,128,128);
  // Broken rim and short cracks read as a surface impact rather than a black dot.
  ctx.beginPath();for(let i=0;i<24;i++){const a=i/24*Math.PI*2,r=radius*(.66+Math.sin(i*9.7)*.14+Math.cos(i*4.1)*.14);const x=64+Math.cos(a)*r,y=64+Math.sin(a)*r;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.closePath();ctx.fillStyle=surface==='metal'?'#111310':wood?'#231a10':dirt?'#292417':'#30332b';ctx.fill();
  ctx.strokeStyle=surface==='metal'?'#b3b5a0':wood?'#a98b52':'#8b8a72';ctx.lineWidth=2.3;ctx.stroke();
  for(let i=0;i<8;i++){const a=i*.79+.2;ctx.beginPath();ctx.moveTo(64+Math.cos(a)*radius*.8,64+Math.sin(a)*radius*.8);ctx.lineTo(64+Math.cos(a+.09)*radius*1.3,64+Math.sin(a+.09)*radius*1.3);ctx.lineTo(64+Math.cos(a)*radius*1.65,64+Math.sin(a)*radius*1.65);ctx.strokeStyle=wood?'#b79b6555':'#191b1477';ctx.lineWidth=wood?2:1;ctx.stroke();}
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}

export class Effects {
  constructor(scene,audio){
    this.scene=scene;this.audio=audio;this.decals=[];this.particles=[];this.casings=[];this.maxDecals=100;
    this.holes=Object.fromEntries(['soil','wood','stone','metal'].map(s=>[s,new THREE.MeshStandardMaterial({map:holeTexture(s),transparent:true,depthWrite:false,roughness:s==='metal'?.5:1,polygonOffset:true,polygonOffsetFactor:-5,side:THREE.DoubleSide})]));
    this.chipGeometry=new THREE.IcosahedronGeometry(1,0);this.chipMaterials={soil:new THREE.MeshStandardMaterial({color:'#635637',roughness:1}),wood:new THREE.MeshStandardMaterial({color:'#a79059',roughness:1}),stone:new THREE.MeshStandardMaterial({color:'#959b8a',roughness:.9}),metal:new THREE.MeshBasicMaterial({color:'#ffd891'})};
    this.casingGeometry=new THREE.CylinderGeometry(.005,.0055,.027,8);this.casingMaterial=new THREE.MeshStandardMaterial({color:'#b49149',metalness:.85,roughness:.32});
    this.rippleMaterial=new THREE.MeshBasicMaterial({color:'#c5e0ce',transparent:true,opacity:.25,side:THREE.DoubleSide,depthWrite:false});
  }
  impact(hit,direction){
    const surface=hit.object.userData.surface||'stone';
    const normal=hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
    if(normal.dot(direction)>0)normal.negate();
    const point=hit.point.clone().addScaledVector(normal,.006);
    const size=surface==='soil'?.18:surface==='wood'?.105:surface==='stone'?.13:.075;
    const quat=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1),normal);
    quat.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),Math.random()*Math.PI*2));
    let decal;
    if(hit.object.userData.target){
      // Parent the decal to the moving steel plate. Its impact stays on the plate.
      const local=hit.object.worldToLocal(point.clone());
      const localNormal=normal.clone().transformDirection(hit.object.matrixWorld.clone().invert());
      decal=new THREE.Mesh(new THREE.PlaneGeometry(size,size),this.holes[surface]);decal.position.copy(local);decal.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),localNormal);hit.object.add(decal);
    }else if(surface==='soil'){
      // Conform each vertex to the same ground function used by the player.
      const g=new THREE.PlaneGeometry(size,size,4,4);g.rotateX(-Math.PI/2);
      const p=g.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i)+point.x,z=p.getZ(i)+point.z;p.setXYZ(i,x,groundHeight(x,z)+.012,z);}g.computeVertexNormals();decal=new THREE.Mesh(g,this.holes[surface]);this.scene.add(decal);
    }else{
      const orientation=new THREE.Euler().setFromQuaternion(quat);
      decal=new THREE.Mesh(new DecalGeometry(hit.object,point,orientation,new THREE.Vector3(size,size,.15)),this.holes[surface]);this.scene.add(decal);
      if(hit.object.userData.breakable)decal.userData.breakable=hit.object.userData.breakable;
    }
    decal.renderOrder=3;this.decals.push(decal);
    while(this.decals.length>this.maxDecals){const old=this.decals.shift();old.removeFromParent();old.geometry.dispose();}
    this.emit(point,normal,surface,surface==='soil'?13:9);
    this.audio.impact(surface);return surface;
  }
  emit(point,normal,surface,count){
    for(let i=0;i<count;i++){
      const mesh=new THREE.Mesh(this.chipGeometry,this.chipMaterials[surface]);mesh.position.copy(point);
      const s=surface==='metal'?.009:.012+Math.random()*.02;mesh.scale.set(s,s*(surface==='wood'?3:1),s);
      this.scene.add(mesh);const v=normal.clone().multiplyScalar(.7+Math.random()*1.6).add(new THREE.Vector3((Math.random()-.5)*1.8,Math.random()*1.7,(Math.random()-.5)*1.8));this.particles.push({mesh,velocity:v,life:.35+Math.random()*.65,total:1});
    }
    while(this.particles.length>180){this.particles.shift().mesh.removeFromParent();}
  }
  eject(camera){
    const mesh=new THREE.Mesh(this.casingGeometry,this.casingMaterial);
    mesh.position.set(.2,-.12,-.35).applyMatrix4(camera.matrixWorld);mesh.quaternion.copy(camera.quaternion);this.scene.add(mesh);
    const velocity=new THREE.Vector3(1.5+Math.random(),1.3+Math.random(),.4).applyQuaternion(camera.quaternion);
    this.casings.push({mesh,velocity,life:13,bounced:false,spin:new THREE.Vector3(Math.random()*15,12,18)});
    while(this.casings.length>45){this.casings.shift().mesh.removeFromParent();}
  }
  breakCrate(object){
    object.alive=false;object.group.visible=false;object.collider.disabled=true;
    this.decals=this.decals.filter(d=>{if(d.userData.breakable===object){d.removeFromParent();d.geometry.dispose();return false;}return true;});
    this.emit(object.group.position,new THREE.Vector3(0,1,0),'wood',28);
  }
  update(dt){
    for(let i=this.particles.length-1;i>=0;i--){const p=this.particles[i];p.life-=dt;if(p.life<=0){p.mesh.removeFromParent();this.particles.splice(i,1);continue;}p.velocity.y-=8*dt;p.mesh.position.addScaledVector(p.velocity,dt);p.mesh.rotation.x+=dt*9;p.mesh.rotation.z+=dt*5;const floor=groundHeight(p.mesh.position.x,p.mesh.position.z)+.01;if(p.mesh.position.y<floor){p.mesh.position.y=floor;p.velocity.set(0,0,0);}}
    for(let i=this.casings.length-1;i>=0;i--){const c=this.casings[i];c.life-=dt;if(c.life<0){c.mesh.removeFromParent();this.casings.splice(i,1);continue;}c.velocity.y-=9.81*dt;c.mesh.position.addScaledVector(c.velocity,dt);const floor=groundHeight(c.mesh.position.x,c.mesh.position.z)+.008;if(c.mesh.position.y<floor){c.mesh.position.y=floor;if(!c.bounced){c.bounced=true;c.velocity.y=Math.abs(c.velocity.y)*.25;c.velocity.x*=.45;c.velocity.z*=.45;this.audio.casing();}else{c.velocity.set(0,0,0);c.spin.set(0,0,0);c.mesh.rotation.z=Math.PI/2;}}c.mesh.rotation.x+=c.spin.x*dt;c.mesh.rotation.y+=c.spin.y*dt;c.mesh.rotation.z+=c.spin.z*dt;}
  }
  reset(){for(const d of this.decals){d.removeFromParent();d.geometry.dispose();}for(const p of [...this.particles,...this.casings])p.mesh.removeFromParent();this.decals=[];this.particles=[];this.casings=[];}
}
