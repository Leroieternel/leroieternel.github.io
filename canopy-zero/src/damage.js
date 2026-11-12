import * as THREE from 'three';
import {DecalGeometry} from 'three/addons/geometries/DecalGeometry.js';
import {damageProfile,seededRandom} from './impact-response.mjs?v=20261112-r3';
import {groundHeight} from './physics.mjs?v=20261112-r3';
const cache=new WeakMap(),Z=new THREE.Vector3(0,0,1),UP=new THREE.Vector3(0,1,0);
function sampleSurface(hit){
 const mat=Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex||0]:hit.object.material;
 const color=mat.color?.clone()||new THREE.Color('#68685a');
 if(mat.map?.image&&hit.uv){try{let c=cache.get(mat.map.image);if(!c){const canvas=document.createElement('canvas');canvas.width=canvas.height=256;c=canvas.getContext('2d',{willReadFrequently:true});c.drawImage(mat.map.image,0,0,256,256);cache.set(mat.map.image,c);}mat.map.updateMatrix();const uv=mat.map.transformUv(hit.uv.clone());const px=Math.min(251,Math.max(0,Math.floor(uv.x*256)-2)),py=Math.min(251,Math.max(0,Math.floor(uv.y*256)-2));const data=c.getImageData(px,py,5,5).data,rgb=[0,0,0];for(let i=0;i<data.length;i+=4)for(let k=0;k<3;k++)rgb[k]+=data[i+k]/(25*255);color.multiply(new THREE.Color().setRGB(...rgb,THREE.SRGBColorSpace));}catch{/* Base material remains available if a source texture cannot be sampled. */}}
 return color;
}
function textures(surface,base,p){
 const n=256,canvas=document.createElement('canvas'),height=document.createElement('canvas');canvas.width=canvas.height=height.width=height.height=n;
 const ctx=canvas.getContext('2d'),hc=height.getContext('2d'),im=ctx.createImageData(n,n),hm=hc.createImageData(n,n),rand=seededRandom(p.seed),cracks=Array.from({length:p.cracks},(_,i)=>[surface==='wood'?(i%2?1:-1)*Math.PI/2+(rand()-.5)*.3:rand()*6.283,.6+rand()*.4,.008+rand()*.009]);
 const rgb=base.clone().convertLinearToSRGB(),wood=surface==='wood',stone=surface==='stone';
 const fresh=wood?[Math.min(.76,rgb.r*.65+.26),Math.min(.65,rgb.g*.58+.20),Math.min(.48,rgb.b*.50+.12)]:[rgb.r*1.18+.025,rgb.g*1.18+.025,rgb.b*1.18+.022];
 for(let y=0;y<n;y++)for(let x=0;x<n;x++){
  const u=(x+.5)/n*2-1,v=(y+.5)/n*2-1,a=Math.atan2(v,u),noise=Math.sin(a*7+p.phase)*.08+Math.sin(a*13-p.phase*2)*p.jaggedness*.55+Math.cos(a*23+p.phase)*.025;
  const radius=Math.hypot(u,v)/( .68+noise),grain=(Math.sin(u*93+v*11+p.phase)+Math.sin(u*179-v*23))*.5,grit=rand();
  let crack=0;for(const [ca,reach,w] of cracks){const d=Math.abs(Math.atan2(Math.sin(a-ca),Math.cos(a-ca)));if(radius>.48&&radius<reach&&d<w*(1.2-radius))crack=1;}
  const edge=Math.max(0,Math.min(1,(1-radius)/.23)),core=Math.max(0,1-radius/.39),rim=Math.exp(-(((radius-.53)/.16)**2));
  let alpha=edge*(radius<.43?.98:.25+rim*.69);if(radius>.78)alpha*=Math.max(0,1-(grit*.7));alpha=Math.max(alpha,crack*.67);
  if(wood){alpha*=.82+.18*Math.sin(u*170+v*19)**2;}
  let shade=.76+grit*.3+(wood?grain*.07:Math.sin(u*139+v*97)*.05);shade*=1-core*.82;shade*=1-crack*.73;
  const k=(y*n+x)*4;for(let c=0;c<3;c++)im.data[k+c]=Math.max(0,Math.min(255,fresh[c]*shade*p.freshness*255));im.data[k+3]=Math.round(Math.min(1,alpha)*255);
  const h=Math.max(0,Math.min(1,.49-core*.43+rim*.21+(grit-.5)*.10*(1-core)-crack*.15));for(let c=0;c<3;c++)hm.data[k+c]=h*255;hm.data[k+3]=255;
 }
 ctx.putImageData(im,0,0);hc.putImageData(hm,0,0);const map=new THREE.CanvasTexture(canvas),bump=new THREE.CanvasTexture(height);map.colorSpace=THREE.SRGBColorSpace;map.anisotropy=8;return {map,bump};
}
function grainDirection(hit,normal){
 const g=hit.object.geometry,p=g.attributes.position,uv=g.attributes.uv,f=hit.face;
 if(uv&&f){const a=new THREE.Vector3().fromBufferAttribute(p,f.a),e1=new THREE.Vector3().fromBufferAttribute(p,f.b).sub(a),e2=new THREE.Vector3().fromBufferAttribute(p,f.c).sub(a),du1=uv.getX(f.b)-uv.getX(f.a),du2=uv.getX(f.c)-uv.getX(f.a),dv1=uv.getY(f.b)-uv.getY(f.a),dv2=uv.getY(f.c)-uv.getY(f.a),det=du1*dv2-du2*dv1;if(Math.abs(det)>1e-8){const t=e2.multiplyScalar(du1).addScaledVector(e1,-du2).multiplyScalar(1/det).transformDirection(hit.object.matrixWorld);t.addScaledVector(normal,-t.dot(normal));if(t.lengthSq()>.01)return t.normalize();}}
 const t=UP.clone().addScaledVector(normal,-normal.y);return t.lengthSq()>.01?t.normalize():new THREE.Vector3(0,0,1);
}
function raisedLip(source,profile,surface){
 const p=source.attributes.position,n=source.attributes.normal,uv=source.attributes.uv;if(!uv||!n)return source;const out=[],normals=[],tex=[];
 const read=i=>({p:new THREE.Vector3().fromBufferAttribute(p,i),n:new THREE.Vector3().fromBufferAttribute(n,i),uv:new THREE.Vector2().fromBufferAttribute(uv,i)});
 const mid=(a,b)=>({p:a.p.clone().lerp(b.p,.5),n:a.n.clone().lerp(b.n,.5).normalize(),uv:a.uv.clone().lerp(b.uv,.5)});
 function triangle(a,b,c,depth){if(depth<3&&Math.max(a.uv.distanceTo(b.uv),b.uv.distanceTo(c.uv),c.uv.distanceTo(a.uv))>.18){const ab=mid(a,b),bc=mid(b,c),ca=mid(c,a);triangle(a,ab,ca,depth+1);triangle(ab,b,bc,depth+1);triangle(ca,bc,c,depth+1);triangle(ab,bc,ca,depth+1);return;}
  for(const v of [a,b,c]){const q=v.uv.clone().multiplyScalar(2).subScalar(1),angle=Math.atan2(q.y,q.x),radius=q.length(),rise=(surface==='wood'?.0025:.0018)*Math.exp(-Math.pow((radius-.40)/.15,2))*(.65+.35*Math.sin(angle*9+profile.phase));out.push(...v.p.clone().addScaledVector(v.n,rise).toArray());normals.push(...v.n.toArray());tex.push(...v.uv.toArray());}}
 for(let i=0;i<p.count;i+=3)triangle(read(i),read(i+1),read(i+2),0);const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(out,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(normals,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(tex,2));source.dispose();return g;
}
export function createDamage(hit,direction,normal,seed){
 const surface=hit.object.userData.surface||'stone',incidence=Math.abs(direction.dot(normal)),profile=damageProfile(surface,seed,incidence),base=sampleSurface(hit),{map,bump}=textures(surface,base,profile);
 const material=new THREE.MeshStandardMaterial({map,bumpMap:bump,bumpScale:surface==='soil'?.015:.007,transparent:true,depthWrite:false,roughness:surface==='metal'?.66:.98,metalness:surface==='metal'?.3:0,polygonOffset:true,polygonOffsetFactor:-3,side:THREE.DoubleSide});
 const size=(surface==='soil'?.17:surface==='metal'?.075:.105)*profile.scale;
 let up=surface==='wood'?grainDirection(hit,normal):direction.clone().addScaledVector(normal,-direction.dot(normal));if(up.lengthSq()<.01)up=grainDirection(hit,normal);up.normalize();const right=new THREE.Vector3().crossVectors(up,normal).normalize();up.crossVectors(normal,right).normalize();
 const quat=new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(right,up,normal));quat.multiply(new THREE.Quaternion().setFromAxisAngle(Z,surface==='wood'?Math.sin(profile.phase)*.12:profile.phase));
 const point=hit.point.clone().addScaledVector(normal,.002),width=size/Math.sqrt(profile.aspect),height=size*Math.sqrt(profile.aspect)*profile.stretch;
 let geometry;
 if(surface==='soil'){geometry=new THREE.PlaneGeometry(width,height,18,18);geometry.applyQuaternion(quat);geometry.translate(point.x,point.y,point.z);const a=geometry.attributes.position;for(let i=0;i<a.count;i++){const x=a.getX(i),z=a.getZ(i),u=geometry.attributes.uv.getX(i)*2-1,v=geometry.attributes.uv.getY(i)*2-1,r=Math.hypot(u,v);a.setY(i,groundHeight(x,z)+.003+.007*Math.exp(-(((r-.45)/.19)**2)));}geometry.computeVertexNormals();}
 else geometry=new DecalGeometry(hit.object,point,new THREE.Euler().setFromQuaternion(quat),new THREE.Vector3(width,height,.12));
 if(surface!=='soil')geometry=raisedLip(geometry,profile,surface);
 const decal=new THREE.Mesh(geometry,material);decal.renderOrder=3;decal.userData.damage={...profile,surface,color:base.getHexString(),incidence,width,height};
 if(hit.object.userData.target){geometry.applyMatrix4(hit.object.matrixWorld.clone().invert());hit.object.add(decal);}else{hit.object.parent?.updateMatrixWorld(true);}
 if(hit.object.userData.breakable)decal.userData.breakable=hit.object.userData.breakable;
 return decal;
}
export function disposeDamage(d){d.removeFromParent();d.geometry.dispose();d.material.map?.dispose();d.material.bumpMap?.dispose();d.material.dispose();}
