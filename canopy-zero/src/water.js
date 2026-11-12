import * as THREE from 'three';
import {riverCenter,riverWidth,riverLevel,riverDepth,groundHeight} from './physics.mjs?v=20261112-r3';
export function createRiver(scene,solids,clock){
 const vertices=[],uvs=[],depths=[],indices=[],steps=360,columns=24;
 for(let j=0;j<=steps;j++){const z=-32+j/steps*64;for(let i=0;i<=columns;i++){const u=i/columns,x=riverCenter(z)+(u*2-1)*riverWidth(z);vertices.push(x,riverLevel(z)+.002,z);uvs.push(x,z);depths.push(riverDepth(x,z));if(j<steps&&i<columns){const k=j*(columns+1)+i;indices.push(k,k+columns+1,k+1,k+1,k+columns+1,k+columns+2);}}}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));g.setAttribute('channelDepth',new THREE.Float32BufferAttribute(depths,1));g.setIndex(indices);g.computeVertexNormals();
 const material=new THREE.MeshPhysicalMaterial({color:'#d6dfcd',roughness:.095,metalness:0,transmission:.95,thickness:.3,ior:1.333,attenuationColor:'#678b65',attenuationDistance:1.15,envMapIntensity:1.15,transparent:true,opacity:1,depthWrite:false,side:THREE.FrontSide});
 material.onBeforeCompile=s=>{
  s.uniforms.uFlowTime=clock;
  s.vertexShader='attribute float channelDepth; varying float vChannelDepth; varying vec2 vStreamPosition; uniform float uFlowTime;\n'+s.vertexShader;
  s.vertexShader=s.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>
   vChannelDepth=channelDepth;vStreamPosition=position.xz;
   transformed.y+=sin(position.z*11.0+position.x*5.0+uFlowTime*7.0)*.002*smoothstep(.01,.12,channelDepth);`);
  s.fragmentShader=`uniform float uFlowTime; varying float vChannelDepth; varying vec2 vStreamPosition;
   float wh(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
   float wn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(wh(i),wh(i+vec2(1,0)),f.x),mix(wh(i+vec2(0,1)),wh(i+vec2(1,1)),f.x),f.y);}
   float ripple(vec2 p){float flow=uFlowTime*(.65+smoothstep(.02,.3,vChannelDepth)*.5);p.y+=flow;p.x+=wn(p*.75+uFlowTime*.04)*.22;return sin(p.y*15.0+p.x*4.0+wn(p*2.0)*3.0)*.0018+sin(p.x*24.0-p.y*19.0+flow*.8)*.001+wn(p*9.0)*.0045+wn(p*23.0)*.0012;}
  `+s.fragmentShader;
  s.fragmentShader=s.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
   vec2 p=vStreamPosition;float dx=(ripple(p+vec2(.018,0))-ripple(p-vec2(.018,0)))/.036;
   float dz=(ripple(p+vec2(0,.018))-ripple(p-vec2(0,.018)))/.036;
   normal=normalize(mat3(viewMatrix)*vec3(-dx,1.0,-dz));`);
  s.fragmentShader=s.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
   diffuseColor.a*=smoothstep(.0,.045,vChannelDepth);
   diffuseColor.rgb*=mix(vec3(1.0),vec3(.76,.87,.72),smoothstep(.12,.38,vChannelDepth)*.25);`);
  s.fragmentShader=s.fragmentShader.replace('#include <transmission_fragment>',THREE.ShaderChunk.transmission_fragment.replace('float thicknessFactor = thickness;','float thicknessFactor = max(.008,vChannelDepth);'));
 };
 material.customProgramCacheKey=()=> 'canopy-refractive-creek-v3';
 const river=new THREE.Mesh(g,material);river.name='flowing-rainforest-stream';river.userData.surface='water';river.receiveShadow=true;river.renderOrder=2;scene.add(river);solids.push(river);
 river.userData.profile={refraction:true,variableDepth:true,dielectric:true,irregularBanks:true};return river;
}
function pebbleLOD(source){
 const p=source.attributes.position,uv=source.attributes.uv,cells=new Map(),mapping=[],vertices=[],tex=[],counts=[];
 for(let i=0;i<p.count;i++){const key=[p.getX(i),p.getY(i),p.getZ(i)].map(x=>Math.round(x*7)).join(',');let k=cells.get(key);if(k===undefined){k=counts.length;cells.set(key,k);vertices.push(0,0,0);tex.push(0,0);counts.push(0);}mapping[i]=k;counts[k]++;vertices[k*3]+=p.getX(i);vertices[k*3+1]+=p.getY(i);vertices[k*3+2]+=p.getZ(i);if(uv){tex[k*2]+=uv.getX(i);tex[k*2+1]+=uv.getY(i);}}
 counts.forEach((n,i)=>{for(let j=0;j<3;j++)vertices[i*3+j]/=n;tex[i*2]/=n;tex[i*2+1]/=n;});const indices=[],seen=new Set(),n=source.index?.count||p.count;
 for(let i=0;i<n;i+=3){const a=mapping[source.index?source.index.getX(i):i],b=mapping[source.index?source.index.getX(i+1):i+1],c=mapping[source.index?source.index.getX(i+2):i+2];if(a===b||b===c||c===a)continue;const key=[a,b,c].sort((x,y)=>x-y).join(',');if(seen.has(key))continue;seen.add(key);indices.push(a,b,c);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(tex,2));g.setIndex(indices);g.computeVertexNormals();return g;
}
export function buildCreekBed(scene,solids,colliders,rockParts,random){
 const palette=['#98a087','#7d846a','#9f9580','#6e7a65'];const sources=rockParts.map(p=>{const geometry=p.geometry.clone();geometry.computeBoundingBox();const b=geometry.boundingBox,c=b.getCenter(new THREE.Vector3()),size=b.getSize(new THREE.Vector3());geometry.translate(-c.x,-b.min.y,-c.z);geometry.scale(1/Math.max(size.x,size.z),1/Math.max(size.x,size.z),1/Math.max(size.x,size.z));return {geometry,material:p.material};});
 const dummy=new THREE.Object3D();let count=0;
 for(let k=0;k<sources.length;k++){const src=sources[k],mat=src.material.clone();mat.roughness=.48;mat.envMapIntensity=.7;const m=new THREE.InstancedMesh(pebbleLOD(src.geometry),mat,100);m.name='submerged-creek-pebbles';m.receiveShadow=true;
  for(let i=0;i<100;i++){const z=-30+random()*60,x=riverCenter(z)+(random()*2-1)*riverWidth(z)*1.3,size=.055+random()**2*.20;dummy.position.set(x,groundHeight(x,z)-.013,z);dummy.scale.set(size*(.8+random()*.6),size*(.55+random()*.45),size);dummy.rotation.set((random()-.5)*.3,random()*6.28,(random()-.5)*.2);dummy.updateMatrix();m.setMatrixAt(i,dummy.matrix);m.setColorAt(i,new THREE.Color(palette[i%4]));count++;}m.instanceMatrix.needsUpdate=true;scene.add(m);
 }
 for(let i=0;i<72;i++){const z=-29+i/72*58+(random()-.5)*.4,side=i%2?1:-1,x=riverCenter(z)+side*riverWidth(z)*(.72+random()*.55),src=sources[i%sources.length],size=.22+random()**2*.56,mat=src.material.clone();mat.color.set(palette[i%4]);mat.roughness=.58;const m=new THREE.Mesh(src.geometry,mat);m.position.set(x,groundHeight(x,z)-.03,z);m.scale.set(size,size*(.6+random()*.35),size*(.8+random()*.5));m.rotation.y=random()*6.28;m.userData.surface='stone';m.name='creek-bank-stone-'+i;m.castShadow=m.receiveShadow=true;scene.add(m);solids.push(m);m.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(m);colliders.push({type:'box',minX:b.min.x,maxX:b.max.x,minZ:b.min.z,maxZ:b.max.z,bottom:b.min.y,top:b.max.y,name:'creek-stone'});}
 return count+72;
}
