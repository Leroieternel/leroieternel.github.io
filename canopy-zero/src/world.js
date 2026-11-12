import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { groundHeight, pathCenter } from './physics.mjs?v=20261112-r5';
import { buildForest } from './vegetation.js?v=20261112-r5';
import { createMeshCollision } from './mesh-collision.js?v=20261112-r5';
import { createRiver } from './water.js?v=20261112-r5';
import { SuspendedTarget } from './dynamics.mjs?v=20261112-r5';

export function randomGenerator(seed = 731) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const UP = new THREE.Vector3(0, 1, 0);
const dummy = new THREE.Object3D();

function canvasTexture(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; }
function labelTexture(text, sub, background = '#c9c1a2') {
  return canvasTexture(512, 256, (c, w, h) => {
    c.fillStyle = background; c.fillRect(0, 0, w, h); c.strokeStyle = '#344335'; c.lineWidth = 5; c.strokeRect(15, 15, w - 30, h - 30);
    c.fillStyle = '#1d2d22'; c.textAlign = 'center'; c.font = 'bold 64px sans-serif'; c.fillText(text, 256, 126); c.font = '22px monospace'; c.fillText(sub, 256, 183);
  });
}

function organicTrunk(radius, height, phase) {
  const g = new THREE.CylinderGeometry(radius * 0.43, radius, height, 22, 16, false);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i), t = (y + height / 2) / height;
    const a = Math.atan2(z, x), warp = 1 + Math.sin(a * 7 + t * 2 + phase) * 0.075 + Math.sin(a * 13 + t * 9) * 0.025;
    x = x * warp + Math.sin(t * 3 + phase) * t * radius * 0.42;
    z = z * warp + Math.sin(t * 4 + phase * 2) * t * radius * 0.3;
    pos.setXYZ(i, x, y + height / 2, z);
  }
  g.computeVertexNormals(); return g;
}

function rootGeometry(r, length, a, rise) {
  // A curved tapering buttress: broad at the trunk, narrow and flush with the soil.
  const vertices = [], indices = [], uvs = [];
  const steps = 14, sides = 10;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps, distance = r * 0.5 + t * length, bend = a + Math.sin(t * 2.8) * 0.13;
    const width = r * (0.42 * (1 - t) ** 1.3 + 0.035), height = rise * (1 - t) ** 2.3 + 0.025;
    for (let j = 0; j <= sides; j++) {
      const theta = j / sides * Math.PI * 2;
      const side = Math.cos(theta) * width;
      vertices.push(Math.cos(bend) * distance - Math.sin(bend) * side, Math.max(-0.02, Math.sin(theta) * height), Math.sin(bend) * distance + Math.cos(bend) * side);
      uvs.push(j / sides * 1.4, t * length * 0.8);
      if (i < steps && j < sides) { const q = i * (sides + 1) + j; indices.push(q, q + sides + 1, q + 1, q + 1, q + sides + 1, q + sides + 2); }
    }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2)); g.setIndex(indices); g.computeVertexNormals(); return g;
}

function bladeGeometry(length = 1, width = 0.18, bend = 0.22, rows = 8, columns = 2) {
  const vertices = [], uv = [], indices = [], cols = [];
  const color = new THREE.Color();
  for (let i = 0; i <= rows; i++) {
    const t = i / rows, shape = Math.sin(Math.PI * t) ** 0.75;
    for (let j = 0; j <= columns; j++) {
      const s = (j / columns - 0.5) * 2;
      vertices.push(shape * width * s, Math.sin(t * Math.PI) * bend - Math.abs(s) * shape * width * 0.25, t * length);
      uv.push(j / columns, t);
      color.setHSL(0.235 + t * 0.025, 0.36, 0.36 + (1 - Math.abs(s)) * 0.12 + t * 0.08); cols.push(color.r, color.g, color.b);
      if (i < rows && j < columns) { const n = columns + 1, k = i * n + j; indices.push(k, k + n, k + 1, k + 1, k + n, k + n + 1); }
    }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3)); g.setIndex(indices); g.computeVertexNormals(); return g;
}

function fernGeometry(rand) {
  const parts = [];
  for (let frond = 0; frond < 7; frond++) {
    const a = frond / 7 * Math.PI * 2, length = 0.85 + rand() * 0.4;
    for (let j = 1; j < 15; j++) {
      const t = j / 15, z = t * length, h = Math.sin(t * Math.PI * 0.85) * 0.52 + 0.03;
      const leafLength = Math.sin(Math.PI * t) * 0.24 + 0.03;
      for (const side of [-1, 1]) {
        const leaf = bladeGeometry(leafLength, leafLength * 0.16, 0.025, 3, 1);
        leaf.rotateY(side * 1.15); leaf.rotateX(-0.12); leaf.translate(0, h, z); leaf.rotateY(a); parts.push(leaf);
      }
    }
  }
  const g = mergeGeometries(parts); parts.forEach(p => p.dispose()); return g;
}

function addWind(material, clock, strength) {
  material.onBeforeCompile = shader => {
    shader.uniforms.uWindTime = clock;
    shader.vertexShader = 'uniform float uWindTime;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      float offset = 0.0;
      #ifdef USE_INSTANCING
        offset = instanceMatrix[3].x * 0.73 + instanceMatrix[3].z * 0.36;
      #endif
      transformed.x += sin(uWindTime * 1.4 + offset + position.z * 1.7) * ${strength.toFixed(3)} * (0.12 + max(position.y, position.z * 0.5));
      transformed.z += cos(uWindTime * 0.9 + offset) * ${ (strength * 0.35).toFixed(3)} * position.y;`);
  };
  material.customProgramCacheKey = () => `canopy-wind-${strength}`;
}

export async function createWorld(scene, renderer, manager) {
  const random = randomGenerator();
  const solids = [], colliders = [], targets = [], breakables = [], trees = [];
  const clock = { value: 0 }, foliagePlayer = { value: new THREE.Vector3(0,1.67,13) }, loader = new THREE.TextureLoader(manager);
  const load = async (name, srgb, rx = 1, ry = rx) => {
    const t = await loader.loadAsync(`./assets/${name}`);
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry);
    t.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8); return t;
  };
  const loaded = await Promise.all([
    load('forest_diff.jpg', true, 34), load('forest_nor_gl.jpg', false, 34), load('forest_rough.jpg', false, 34),
    load('soil_diff.jpg', true, 34), load('bark_diff.jpg', true, 1.6, 5.5), load('bark_nor_gl.jpg', false, 1.6, 5.5),
  ]);
  const [forest, forestNormal, forestRough, soil, bark, barkNormal] = loaded;
  scene.background = new THREE.Color('#a0b0a8'); scene.fog = new THREE.FogExp2('#94a79a', 0.017);
  const hemisphere = new THREE.HemisphereLight('#e4edf0', '#4e5948', 1.05); scene.add(hemisphere);
  const sun = new THREE.DirectionalLight('#f4f0df', .9); sun.position.set(-8, 30, -14); sun.target.position.set(0, 0, -2);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = -28; sun.shadow.camera.right = 28; sun.shadow.camera.top = 28; sun.shadow.camera.bottom = -28;
  sun.shadow.camera.near = 1; sun.shadow.camera.far = 70; sun.shadow.bias = -0.0002; sun.shadow.normalBias = 0.025; sun.shadow.radius = 3.5;
  scene.add(sun, sun.target);
  const fill = new THREE.DirectionalLight('#d8e4e3', 0.28); fill.position.set(8, 8, 14); scene.add(fill);
  let env;
  try { env = await new RGBELoader(manager).loadAsync('./assets/forest.hdr'); env.mapping = THREE.EquirectangularReflectionMapping; scene.environment = env; scene.environmentIntensity = 0.78; } catch { /* Directional and hemispheric light remain usable. */ }

  const terrainG = new THREE.PlaneGeometry(120, 120, 480, 480); terrainG.rotateX(-Math.PI / 2);
  for (let i = 0; i < terrainG.attributes.position.count; i++) { const p = terrainG.attributes.position; p.setY(i, groundHeight(p.getX(i), p.getZ(i))); }
  terrainG.computeVertexNormals();
  const terrainM = new THREE.MeshStandardMaterial({ map: forest, normalMap: forestNormal, roughnessMap: forestRough, normalScale: new THREE.Vector2(0.42, 0.42), roughness: 0.94, color: '#c4ccba' });
  terrainM.onBeforeCompile = shader => {
    shader.uniforms.uSoil = { value: soil };
    shader.vertexShader = 'varying vec3 vTerrainPosition;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvTerrainPosition = position;');
    shader.fragmentShader = 'uniform sampler2D uSoil; varying vec3 vTerrainPosition;\n' + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <map_fragment>', `#include <map_fragment>
      float trail = abs(vTerrainPosition.x - sin(vTerrainPosition.z * 0.105) * 2.6);
      float trailMix = 1.0 - smoothstep(.65, 1.65, trail + sin(vTerrainPosition.z * 1.4) * 0.3);
      vec4 trailColor = texture2D(uSoil, vMapUv * 1.1);
      diffuseColor.rgb = mix(diffuseColor.rgb, trailColor.rgb * vec3(0.56, 0.53, 0.45), trailMix * 0.94);
      float creekX=9.3+sin(vTerrainPosition.z*.115)*1.75+sin(vTerrainPosition.z*.31)*.23+sin(vTerrainPosition.z*.81)*.11;
      float creekW=1.05+.18*sin(vTerrainPosition.z*.22)+.10*sin(vTerrainPosition.z*.93+1.2)+.045*sin(vTerrainPosition.z*2.13);
      float wetBank=1.0-smoothstep(creekW-.10,creekW+.55,abs(vTerrainPosition.x-creekX));
      diffuseColor.rgb=mix(diffuseColor.rgb,trailColor.rgb*vec3(.32,.37,.29),wetBank*.88);`);
    shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>','#include <roughnessmap_fragment>\nroughnessFactor=mix(roughnessFactor,.48,wetBank);');
  };
  const terrain = new THREE.Mesh(terrainG, terrainM); terrain.receiveShadow = true; terrain.userData.surface = 'soil'; terrain.name = 'forest-floor'; scene.add(terrain); solids.push(terrain);
  const barkM = new THREE.MeshStandardMaterial({ map: bark, normalMap: barkNormal, normalScale: new THREE.Vector2(1.3, 1.3), roughness: 0.95, color: '#92976d' });
  const vegetation=await buildForest(scene,manager,random,solids,colliders,trees,clock,foliagePlayer);
  const forestInfo=vegetation.info;
  const river=createRiver(scene,solids,clock);
  const waterM=new THREE.MeshPhysicalMaterial({color:'#334b3d',metalness:.25,roughness:.1,transparent:true,opacity:.42,clearcoat:1,clearcoatRoughness:.08,depthWrite:false});
  const puddles=[];
  [[-.6,8,1.1,1.9],[1.8,2,.85,1.5],[-1,-7,1.25,2],[.6,-17,.9,1.6],[-1.2,19,1,1.3]].forEach(([x,z,rx,rz])=>{
    const vertices=[x,groundHeight(x,z)+.013,z],uv=[.5,.5],indices=[];
    for(let i=0;i<=50;i++){const a=i/50*6.28318,r=1+Math.sin(a*7)*.09+Math.cos(a*11)*.05,px=x+Math.cos(a)*rx*r,pz=z+Math.sin(a)*rz*r;vertices.push(px,groundHeight(px,pz)+.016,pz);uv.push(Math.cos(a)*.5+.5,Math.sin(a)*.5+.5);if(i<50)indices.push(0,i+2,i+1);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();const m=new THREE.Mesh(g,waterM);m.receiveShadow=true;m.renderOrder=1;m.userData.surface='water';m.name='rain-puddle';scene.add(m);solids.push(m);puddles.push({x,z,rx,rz});
  });

  const woodM=new THREE.MeshStandardMaterial({map:bark,color:'#89744b',roughness:.9});
  const steelM=new THREE.MeshStandardMaterial({color:'#5b6455',metalness:.72,roughness:.46});
  const orangeM=new THREE.MeshStandardMaterial({color:'#cc7849',roughness:.7,metalness:.15});
  const supplyM=new THREE.MeshStandardMaterial({color:'#515e40',roughness:.67,metalness:.22});
  const meshBox=(w,h,d,material,x,y,z)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);m.position.set(x,y,z);m.castShadow=m.receiveShadow=true;scene.add(m);return m;};
  function target(x,z,label,metal=true) {
    const y=groundHeight(x,z),group=new THREE.Group();group.position.set(x,y+1.65,z);scene.add(group);
    for(const side of [-1,1]){const post=meshBox(.065,2.47,.065,steelM,x+side*.51,y+1.235,z-.06);post.userData.surface='metal';solids.push(post);}
    const rail=meshBox(1.14,.07,.09,steelM,x,y+2.46,z-.06);rail.userData.surface='metal';solids.push(rail);
    const foot=meshBox(1.2,.06,.62,steelM,x,y+.03,z);
    const plate=new THREE.Mesh(new THREE.CylinderGeometry(.33,.33,.045,48),metal?steelM:woodM);plate.rotation.x=Math.PI/2;group.add(plate);plate.userData.surface=metal?'metal':'wood';plate.userData.target=true;plate.name=`target-${label}`;solids.push(plate);
    const targetMap=canvasTexture(512,512,c=>{c.clearRect(0,0,512,512);c.strokeStyle=metal?'#e1d7ba':'#252b24';c.lineWidth=11;for(const r of [205,140,75]){c.beginPath();c.arc(256,256,r,0,Math.PI*2);c.stroke();}c.fillStyle='#c9774a';c.beginPath();c.arc(256,256,28,0,6.28);c.fill();});
    const decal=new THREE.Mesh(new THREE.PlaneGeometry(.62,.62),new THREE.MeshStandardMaterial({map:targetMap,transparent:true,depthWrite:false,roughness:.8,polygonOffset:true,polygonOffsetFactor:-2}));decal.position.z=.025;group.add(decal);
    const sign=new THREE.Mesh(new THREE.PlaneGeometry(.38,.19),new THREE.MeshStandardMaterial({map:labelTexture(label,'FIELD TARGET'),roughness:1}));sign.position.set(x,y+.48,z+.05);scene.add(sign);
    const chains=[],anchors=[];for(const side of [-1,1]){const chain=new THREE.Mesh(new THREE.CylinderGeometry(.006,.006,1,8),steelM);scene.add(chain);chains.push(chain);anchors.push(new THREE.Vector3(x+side*.18,y+2.43,z));}
    const obj={mesh:plate,pivot:group,base:group.position.clone(),angle:0,velocity:0,baseY:y+1.65,label,body:new SuspendedTarget({mass:metal?5.2:2.4,length:.54}),chains,anchors};plate.userData.targetRef=obj;targets.push(obj);
    colliders.push({type:'box',minX:x-.4,maxX:x+.4,minZ:z-.25,maxZ:z+.25,bottom:y,top:y+2,name:'target'});
  }
  target(-1.9,-10,'01');target(2.5,-18,'02');target(-3.3,-22,'03',false);
  // Nearby ammunition box is deliberately off the walking line.
  const supply={x:3.3,z:10.3};const sy=groundHeight(supply.x,supply.z);
  const supplyMesh=meshBox(1.2,.7,.75,supplyM,supply.x,sy+.35,supply.z);supplyMesh.userData.surface='metal';solids.push(supplyMesh);
  const lid=meshBox(1.24,.07,.79,supplyM,supply.x,sy+.73,supply.z);solids.push(lid);lid.userData.surface='metal';
  for(const x of [supply.x-.44,supply.x+.44])meshBox(.045,.48,.77,steelM,x,sy+.45,supply.z);
  const supplySign=new THREE.Mesh(new THREE.PlaneGeometry(.55,.25),new THREE.MeshStandardMaterial({map:labelTexture('RESUPPLY','5.56 / FIELD KIT'),roughness:.9}));supplySign.position.set(supply.x,sy+.42,supply.z+.381);scene.add(supplySign);
  colliders.push({type:'box',minX:supply.x-.62,maxX:supply.x+.62,minZ:supply.z-.4,maxZ:supply.z+.4,bottom:sy,top:sy+.8,name:'supply'});
  for(const [x,z] of [[3.3,-6.2],[-3.8,-3.6]]){
    const y=groundHeight(x,z),g=new THREE.Group();g.position.set(x,y+.48,z);scene.add(g);const collider={type:'box',minX:x-.47,maxX:x+.47,minZ:z-.47,maxZ:z+.47,bottom:y,top:y+.96,name:'crate'};colliders.push(collider);
    const m=new THREE.Mesh(new THREE.BoxGeometry(.9,.9,.9),woodM);g.add(m);m.castShadow=m.receiveShadow=true;m.userData.surface='wood';const object={group:g,mesh:m,collider,hp:5,alive:true};m.userData.breakable=object;solids.push(m);breakables.push(object);
    for(const zz of [-.465,.465])for(const xx of [-.3,.3]){const bar=new THREE.Mesh(new THREE.BoxGeometry(.09,.96,.05),woodM);bar.position.set(xx,0,zz);g.add(bar);}
  }
  const board=meshBox(1.4,.6,.07,woodM,-4.6,groundHeight(-4.6,11)+1.7,11);board.userData.surface='wood';solids.push(board);
  const boardFace=new THREE.Mesh(new THREE.PlaneGeometry(1.32,.53),new THREE.MeshStandardMaterial({map:labelTexture('CANOPY ZERO','FREE RANGE / 01','#b5ba98'),roughness:.9}));boardFace.position.copy(board.position).z+=.04;scene.add(boardFace);
  for(const x of [-5.12,-4.08]){const m=meshBox(.08,1.8,.08,woodM,x,groundHeight(x,11)+.9,11);solids.push(m);m.userData.surface='wood';colliders.push({type:'circle',x,z:11,radius:.08,bottom:groundHeight(x,11),top:2,name:'post'});}

  // Rain is camera-relative; line segments are shared in one draw call.
  const rainCount=1150,rainArray=new Float32Array(rainCount*6);
  for(let i=0;i<rainCount;i++){const k=i*6;rainArray[k]=(random()-.5)*42;rainArray[k+1]=random()*18;rainArray[k+2]=(random()-.5)*42;rainArray[k+3]=rainArray[k]+.04;rainArray[k+4]=rainArray[k+1]-.35;rainArray[k+5]=rainArray[k+2]+.02;}
  const rainG=new THREE.BufferGeometry();rainG.setAttribute('position',new THREE.BufferAttribute(rainArray,3));
  const rain=new THREE.LineSegments(rainG,new THREE.LineBasicMaterial({color:'#d4e6de',transparent:true,opacity:.17,depthWrite:false}));rain.frustumCulled=false;scene.add(rain);
  const meshCollision=createMeshCollision(solids.filter(m=>['wood','stone','metal'].includes(m.userData.surface)&&!m.userData.breakable&&!m.userData.target&&m.name!=='scanned-sapling'&&!m.name.startsWith('creek-')));
  const effectColliders=colliders.slice();
  const replaced=new Set(['scanned-tree','scanned-trunk-surface','scanned-root','root-base','rock','fallen-log']);
  for(let i=colliders.length-1;i>=0;i--)if(replaced.has(colliders[i].name))colliders.splice(i,1);
  let raining=true;
  return {
    solids,colliders,targets,breakables,trees,terrain,supply,puddles,sun,clock,forestInfo,river,meshCollision,effectColliders,
    hitTarget(hit,direction){const t=hit.object.userData.targetRef;t.body.applyImpulse(hit.point.clone().sub(t.pivot.position).toArray(),direction.toArray());},
    setRain(enabled){raining=enabled;rain.visible=enabled;},
    update(dt,time,camera){clock.value=time;foliagePlayer.value.copy(camera.position);vegetation.update(camera.position);for(const t of targets){t.body.update(dt);const o=t.body.offset,r=t.body.rotation;t.pivot.position.copy(t.base).add(new THREE.Vector3(...o));t.pivot.rotation.set(r[0]+o[2]/t.body.length*.4,r[1],r[2]-o[0]/t.body.length*.4);t.angle=t.pivot.rotation.x;t.velocity=t.body.velocity[2];t.pivot.updateMatrixWorld(true);for(let i=0;i<2;i++){const end=t.pivot.localToWorld(new THREE.Vector3((i===0?-1:1)*.18,.25,0)),a=t.anchors[i],delta=end.clone().sub(a),chain=t.chains[i];chain.position.copy(a).add(end).multiplyScalar(.5);chain.scale.y=delta.length();chain.quaternion.setFromUnitVectors(UP,delta.normalize());}}if(raining){rain.position.set(camera.position.x,0,camera.position.z);for(let i=0;i<rainCount;i++){const k=i*6;rainArray[k+1]-=dt*11;rainArray[k+4]-=dt*11;if(rainArray[k+1]<-.2){rainArray[k+1]+=18;rainArray[k+4]+=18;}}rainG.attributes.position.needsUpdate=true;}},
    reset(){targets.forEach(t=>{t.body.reset();t.velocity=0;t.angle=0;t.pivot.position.copy(t.base);t.pivot.rotation.set(0,0,0);});breakables.forEach(b=>{b.hp=5;b.alive=true;b.group.visible=true;b.collider.disabled=false;});}
  };
}
