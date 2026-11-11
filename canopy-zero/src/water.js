import * as THREE from 'three';
import {riverCenter,riverWidth,riverLevel} from './physics.mjs?v=20261111-r2';
export function createRiver(scene,solids,clock){
 const vertices=[],uvs=[],indices=[];const steps=280,columns=12;
 for(let j=0;j<=steps;j++){const z=-32+j/steps*64;for(let i=0;i<=columns;i++){const u=i/columns,x=riverCenter(z)+(u*2-1)*riverWidth(z);vertices.push(x,riverLevel(z)+.006,z);uvs.push(u,z);if(j<steps&&i<columns){const k=j*(columns+1)+i;indices.push(k,k+1,k+columns+1,k+1,k+columns+2,k+columns+1);}}}
 const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));geometry.setIndex(indices);geometry.computeVertexNormals();
 const material=new THREE.MeshPhysicalMaterial({color:'#364c3b',roughness:.25,metalness:.02,envMapIntensity:.55,clearcoat:.55,clearcoatRoughness:.2,transparent:true,opacity:.88,side:THREE.DoubleSide});
 material.onBeforeCompile=shader=>{
  shader.uniforms.uFlowTime=clock;
  shader.vertexShader='varying vec2 vFlowUv;\n'+shader.vertexShader;
  shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvFlowUv=uv;');
  shader.fragmentShader=`uniform float uFlowTime; varying vec2 vFlowUv;
  float waterHash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
  float waterNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(waterHash(i),waterHash(i+vec2(1,0)),f.x),mix(waterHash(i+vec2(0,1)),waterHash(i+vec2(1,1)),f.x),f.y);}
  float riverNoise(vec2 p){return waterNoise(p)*.55+waterNoise(p*2.13+7.1)*.3+waterNoise(p*4.37)*.15;}
  `+shader.fragmentShader;
  shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
   vec2 q=vec2(vFlowUv.x*18.0,vFlowUv.y*5.0+uFlowTime*3.15);
   float a=riverNoise(q+vec2(.18,0))-riverNoise(q-vec2(.18,0));
   float b=riverNoise(q+vec2(0,.18))-riverNoise(q-vec2(0,.18));
   normal=normalize(normal+vec3(a*.12,b*.12,0.0));`);
  shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
   float bank=smoothstep(.35,.49,abs(vFlowUv.x-.5));
   float flow=smoothstep(.73,.9,riverNoise(vec2(vFlowUv.x*32.0,vFlowUv.y*3.0+uFlowTime*1.89)));
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.38,.48,.39),flow*(.06+bank*.22));`);
 };
 material.customProgramCacheKey=()=> 'canopy-flow-v2';
 const river=new THREE.Mesh(geometry,material);river.name='flowing-rainforest-stream';river.userData.surface='water';river.receiveShadow=true;scene.add(river);solids.push(river);return river;
}
