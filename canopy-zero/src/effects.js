import * as THREE from 'three';
import {createDamage,disposeDamage} from './damage.js?v=20261112-r3';
import {splashFrame,splashVelocity} from './impact-response.mjs?v=20261112-r3';
import { groundHeight,waterHeight,resolveOverlap } from './physics.mjs?v=20261112-r3';
const UP=new THREE.Vector3(0,1,0),Z=new THREE.Vector3(0,0,1);
function containsParticle(c,p,r=0){if(c.disabled||p.y>c.top||p.y+.02<c.bottom)return false;if(c.type==='box')return p.x>=c.minX-r&&p.x<=c.maxX+r&&p.z>=c.minZ-r&&p.z<=c.maxZ+r;if(c.type==='circle')return (p.x-c.x)**2+(p.z-c.z)**2<=(c.radius+r)**2;return false;}

function dustTexture(){const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d');const g=x.createRadialGradient(64,64,5,64,64,61);g.addColorStop(0,'#ffffff70');g.addColorStop(.4,'#ffffff40');g.addColorStop(1,'#ffffff00');x.fillStyle=g;x.fillRect(0,0,128,128);return new THREE.CanvasTexture(c);}
function splinterGeometry(){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute([-.4,-.5,-.25,.5,-.45,-.2,.3,.5,0,-.2,.4,.25,0,-.45,.35],3));g.setIndex([0,1,2,0,2,3,0,3,4,0,4,1,1,4,2,2,4,3]);g.computeVertexNormals();return g;}
export class Effects {
 constructor(scene,audio){
  this.scene=scene;this.audio=audio;this.decals=[];this.particles=[];this.casings=[];this.waves=[];this.maxDecals=100;this.colliders=[];this.puddles=[];this.lastEmission=null;this.emissionCounter=0;this.holes={};
  this.chipGeometry=new THREE.IcosahedronGeometry(1,0);const chip=this.chipGeometry.attributes.position;for(let i=0;i<chip.count;i++){const x=chip.getX(i),y=chip.getY(i),z=chip.getZ(i),k=.78+.25*Math.sin(x*13+y*7+z*19);chip.setXYZ(i,x*k,y*k*.8,z*k);}this.chipGeometry.computeVertexNormals();this.woodGeometry=splinterGeometry();this.dropletGeometry=new THREE.SphereGeometry(1,6,4);
  this.chipMaterials={soil:new THREE.MeshStandardMaterial({color:'#403626',roughness:.98}),wood:new THREE.MeshStandardMaterial({color:'#b7996a',roughness:.93}),bark:new THREE.MeshStandardMaterial({color:'#453727',roughness:1}),stone:new THREE.MeshStandardMaterial({color:'#9caa98',roughness:.94}),metal:new THREE.MeshBasicMaterial({color:'#ffd99c',toneMapped:false}),water:new THREE.MeshPhysicalMaterial({color:'#9bbfb3',roughness:.08,metalness:0,transparent:true,opacity:.48,clearcoat:1,envMapIntensity:1.0})};
  this.dust=dustTexture();this.casingGeometry=new THREE.CylinderGeometry(.005,.0055,.027,8);this.casingMaterial=new THREE.MeshStandardMaterial({color:'#b49149',metalness:.85,roughness:.32});
 }
 async load(){ /* Impact textures are generated from the actual hit material. */ }
 impact(hit,direction){
  const surface=hit.object.userData.surface||'stone';
  const normal=hit.face.normal.clone().transformDirection(hit.object.matrixWorld);if(normal.dot(direction)>0)normal.negate();
  const point=hit.point.clone().addScaledVector(normal,.007);
  if(surface==='water'){this.splash(point,direction);this.audio.impact('water');return surface;}
  const seed=(Math.imul(++this.emissionCounter,2654435761)^Math.round(point.x*7919+point.y*3571+point.z*104729))>>>0;
  const decal=createDamage(hit,direction,normal,seed);if(!decal.parent)this.scene.add(decal);this.decals.push(decal);this.lastDamage=decal.userData.damage;
  while(this.decals.length>this.maxDecals)disposeDamage(this.decals.shift());
  this.emit(point,normal,surface,surface==='wood'?22:surface==='soil'?25:17,direction);this.audio.impact(surface);return surface;
 }
 emit(point,normal,surface,count,direction=new THREE.Vector3(0,-1,0)){
  this.emissionCounter++;const originColliders=this.colliders.filter(c=>containsParticle(c,point,.02));
  this.lastEmission={surface,count,material:surface==='wood'?'bark-and-wood-fibres':surface};
  for(let i=0;i<count;i++){
   const wood=surface==='wood',spark=surface==='metal',mesh=new THREE.Mesh(wood?this.woodGeometry:this.chipGeometry,this.chipMaterials[wood&&i%3===0?'bark':surface]);mesh.position.copy(point);
   const s=spark?.004:.005+Math.random()*.012;mesh.scale.set(s,wood?s*(2.5+Math.random()*4):s,s*.65);if(wood)mesh.scale.x*=.6;
   if(surface==='stone'&&this.lastDamage?.surface==='stone'){mesh.material=mesh.material.clone();mesh.material.color.set('#'+this.lastDamage.color).lerp(new THREE.Color('#b6ad97'),.18).multiplyScalar(1.12);}
   this.scene.add(mesh);const reflected=direction.clone().reflect(normal);const v=normal.clone().multiplyScalar(1.4+Math.random()*2.6).addScaledVector(reflected,.5).add(new THREE.Vector3((Math.random()-.5)*2.4,Math.random()*2.4,(Math.random()-.5)*2.4));
   const life=spark?.14+Math.random()*.22:2.1+Math.random()*1.6;
   this.particles.push({mesh,velocity:v,life,total:life,batch:this.emissionCounter,origin:point.clone(),ignore:new Set(originColliders),ownMaterial:surface==='stone',spin:new THREE.Vector3(Math.random()*15,Math.random()*18,Math.random()*12),surface,radius:s,restitution:wood?.15:.23,drag:wood?.55:.16});
  }
  if(surface!=='metal')for(let i=0;i<3;i++){const material=new THREE.SpriteMaterial({map:this.dust,color:surface==='soil'?'#8a7653':surface==='wood'?'#baac82':'#a8aea0',transparent:true,opacity:.24,depthWrite:false});const mesh=new THREE.Sprite(material);mesh.position.copy(point);mesh.scale.setScalar(.10);this.scene.add(mesh);this.particles.push({mesh,velocity:normal.clone().multiplyScalar(.3+Math.random()*.35),life:.65+Math.random()*.35,total:1,surface:'dust',ownMaterial:true,drag:2.5});}
  this.trim();
 }
 splash(point,direction){
  this.emissionCounter++;const frame=splashFrame(direction.toArray()),tangent=new THREE.Vector3(...frame.tangent),side=new THREE.Vector3(...frame.side);
  this.lastEmission={surface:'water',count:34,material:'water-droplets',incidence:frame.incidence,tangent:frame.tangent};
  for(let i=0;i<34;i++){const a=i/34*Math.PI*2+Math.random()*.18,s=.0025+Math.random()*.005,m=new THREE.Mesh(this.dropletGeometry,this.chipMaterials.water);m.position.copy(point);m.scale.set(s,s*(1.3+Math.random()),s);this.scene.add(m);const velocity=new THREE.Vector3(...splashVelocity(frame,a,.22+Math.random()*.95,Math.random()*1.1));m.quaternion.setFromUnitVectors(UP,velocity.clone().normalize());this.particles.push({mesh:m,velocity,life:1.1,total:1.1,surface:'water',radius:s,drag:.35});}
  for(let i=0;i<2;i++){
   const phase={value:0},mat=new THREE.MeshBasicMaterial({color:'#a9c2b0',transparent:true,opacity:.15,depthWrite:false,side:THREE.DoubleSide});
   mat.onBeforeCompile=shader=>{shader.uniforms.uWavePhase=phase;shader.vertexShader='varying vec2 vRippleUv;\n'+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvRippleUv=uv;');shader.fragmentShader='uniform float uWavePhase;varying vec2 vRippleUv;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
    vec2 q=vRippleUv*2.0-1.0;float r=length(q),theta=atan(q.y,q.x),radius=.10+uWavePhase*.76;
    float wave=exp(-pow((r-radius)/.025,2.0))*.65+exp(-pow((r-radius+.06)/.019,2.0))*.18;
    diffuseColor.a*=wave*(.55+.45*sin(theta*9.0+r*31.0)*sin(theta*9.0+r*31.0));`);};
   mat.customProgramCacheKey=()=> 'soft-water-wave-v3';const m=new THREE.Mesh(new THREE.PlaneGeometry(1.8,1.8),mat);m.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(tangent,side.clone().negate(),UP));m.position.copy(point);m.position.y+=.003+i*.001;m.scale.set(frame.stretch,1,1);this.scene.add(m);this.waves.push({mesh:m,phase,life:1.5+i*.22,total:1.5+i*.22,delay:i*.12,type:'ring',direction:tangent.clone().multiplyScalar(frame.bias*.045)});
  }
  const pos=[],uv=[],indices=[],segments=32,arc=Math.PI*(.65+frame.incidence*1.35);
  for(let j=0;j<=2;j++)for(let i=0;i<=segments;i++){const a=(i/segments-.5)*arc,r=.025+j*.022,h=j===0?0:(.025+Math.sin(a*7+1)*.01)*(j/2);const v=tangent.clone().multiplyScalar(Math.cos(a)*r).addScaledVector(side,Math.sin(a)*r);pos.push(v.x,h,v.z);uv.push(i/segments,j/2);if(j<2&&i<segments){const k=j*(segments+1)+i;indices.push(k,k+1,k+segments+1,k+1,k+segments+2,k+segments+1);}}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();const mat=this.chipMaterials.water.clone();mat.side=THREE.DoubleSide;mat.opacity=.20;const crown=new THREE.Mesh(g,mat);crown.position.copy(point);this.scene.add(crown);this.waves.push({mesh:crown,life:.29,total:.29,type:'sheet',direction:tangent.multiplyScalar(frame.bias*.14),up:frame.up});this.trim();
 }
 trim(){while(this.particles.length>230){const p=this.particles.shift();p.mesh.removeFromParent();if(p.ownMaterial)p.mesh.material.dispose();}}
 eject(camera){const mesh=new THREE.Mesh(this.casingGeometry,this.casingMaterial);mesh.position.set(.2,-.12,-.35).applyMatrix4(camera.matrixWorld);mesh.quaternion.copy(camera.quaternion);this.scene.add(mesh);this.casings.push({mesh,velocity:new THREE.Vector3(1.5+Math.random(),1.3+Math.random(),.4).applyQuaternion(camera.quaternion),life:13,bounced:false,spin:new THREE.Vector3(Math.random()*15,12,18)});while(this.casings.length>45)this.casings.shift().mesh.removeFromParent();}
 breakCrate(object){object.alive=false;object.group.visible=false;object.collider.disabled=true;this.decals=this.decals.filter(d=>{if(d.userData.breakable===object){disposeDamage(d);return false;}return true;});this.emit(object.group.position,UP,'wood',40);}
 update(dt){
  for(let i=this.waves.length-1;i>=0;i--){const w=this.waves[i];w.life-=dt;if(w.life<=0){w.mesh.removeFromParent();w.mesh.geometry.dispose();w.mesh.material.dispose();this.waves.splice(i,1);continue;}const t=1-w.life/w.total;if(w.type==='ring'){w.phase.value=Math.max(0,t-(w.delay||0));w.mesh.material.opacity=.15*(1-t)**1.7;}else{w.mesh.scale.set(1+t*3,Math.max(.05,Math.sin(Math.PI*t))*(1+w.up*.3),1+t*3);w.mesh.material.opacity=.20*(1-t)**1.5;}w.mesh.position.addScaledVector(w.direction,dt);}
  for(let i=this.particles.length-1;i>=0;i--){const p=this.particles[i];p.life-=dt;if(p.life<=0){p.mesh.removeFromParent();if(p.ownMaterial)p.mesh.material.dispose();this.particles.splice(i,1);continue;}
   if(p.surface==='dust'){p.mesh.position.addScaledVector(p.velocity,dt);p.mesh.scale.setScalar(.10+(1-p.life/p.total)*.65);p.mesh.material.opacity=.24*(p.life/p.total);continue;}
   p.velocity.multiplyScalar(Math.exp(-p.drag*dt));p.velocity.y-=9.81*dt;p.mesh.position.addScaledVector(p.velocity,dt);
   if(p.spin){p.mesh.rotation.x+=p.spin.x*dt;p.mesh.rotation.z+=p.spin.z*dt;}
   const floor=groundHeight(p.mesh.position.x,p.mesh.position.z)+.005;
   if(p.surface==='water'){p.mesh.quaternion.setFromUnitVectors(UP,p.velocity.clone().normalize());const water=waterHeight(p.mesh.position.x,p.mesh.position.z);if(p.velocity.y<0&&p.mesh.position.y<(water??floor)+.01)p.life=0;continue;}
   if(p.mesh.position.y<floor){p.mesh.position.y=floor;p.velocity.y=Math.abs(p.velocity.y)*(p.restitution||.15);p.velocity.x*=.6;p.velocity.z*=.6;if(p.velocity.lengthSq()<.08){p.velocity.set(0,0,0);if(p.spin)p.spin.set(0,0,0);}}
   if(p.surface==='wood'||p.surface==='stone'){const pos=p.mesh.position;for(const c of this.colliders){if(p.ignore?.has(c)){if(!containsParticle(c,pos,p.radius))p.ignore.delete(c);continue;}if(c.disabled||pos.y>c.top||pos.y+.02<c.bottom)continue;const radius=p.radius+(c.radius||0);if(c.type==='box'&&(pos.x<c.minX-p.radius||pos.x>c.maxX+p.radius||pos.z<c.minZ-p.radius||pos.z>c.maxZ+p.radius))continue;if(c.type==='circle'&&((pos.x-c.x)**2+(pos.z-c.z)**2)>radius*radius)continue;const old=pos.clone();if(resolveOverlap(pos,c,p.radius,.02)){const normal=pos.clone().sub(old).normalize();if(p.velocity.dot(normal)<0)p.velocity.reflect(normal).multiplyScalar(.3);}}}
  }
  for(let i=this.casings.length-1;i>=0;i--){const c=this.casings[i];c.life-=dt;if(c.life<0){c.mesh.removeFromParent();this.casings.splice(i,1);continue;}c.velocity.y-=9.81*dt;c.mesh.position.addScaledVector(c.velocity,dt);const floor=groundHeight(c.mesh.position.x,c.mesh.position.z)+.008;if(c.mesh.position.y<floor){c.mesh.position.y=floor;if(!c.bounced){c.bounced=true;c.velocity.y=Math.abs(c.velocity.y)*.25;c.velocity.x*=.45;c.velocity.z*=.45;this.audio.casing();}else{c.velocity.set(0,0,0);c.spin.set(0,0,0);c.mesh.rotation.z=Math.PI/2;}}c.mesh.rotation.x+=c.spin.x*dt;c.mesh.rotation.y+=c.spin.y*dt;c.mesh.rotation.z+=c.spin.z*dt;}
 }
 stats(){return {lastDamage:this.lastDamage,particles:this.particles.length,splashes:this.waves.length,lastEmission:this.lastEmission?{...this.lastEmission,maxDisplacement:Math.max(0,...this.particles.filter(p=>p.batch===this.emissionCounter&&p.origin).map(p=>p.mesh.position.distanceTo(p.origin)))}:null,materials:[...new Set(this.particles.map(p=>p.surface))]};}
 reset(){for(const d of this.decals)disposeDamage(d);for(const p of [...this.particles,...this.casings,...this.waves]){p.mesh.removeFromParent();if(p.ownMaterial)p.mesh.material.dispose();}for(const w of this.waves){w.mesh.geometry.dispose();w.mesh.material.dispose();}this.decals=[];this.particles=[];this.casings=[];this.waves=[];this.lastEmission=null;this.lastDamage=null;}
}
