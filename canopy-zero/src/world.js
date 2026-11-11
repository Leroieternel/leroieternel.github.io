import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { groundHeight, pathCenter } from './physics.mjs';

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
  const clock = { value: 0 }, loader = new THREE.TextureLoader(manager);
  const load = async (name, srgb, rx = 1, ry = rx) => {
    const t = await loader.loadAsync(`./assets/${name}`);
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry);
    t.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8); return t;
  };
  const loaded = await Promise.all([
    load('forest_diff.jpg', true, 34), load('forest_nor_gl.jpg', false, 34), load('forest_rough.jpg', false, 34),
    load('soil_diff.jpg', true, 34), load('bark_diff.jpg', true, 1.6, 5.5), load('bark_nor_gl.jpg', false, 1.6, 5.5),
    load('rock_diff.jpg', true, 1.2), load('rock_nor_gl.jpg', false, 1.2), load('rock_rough.jpg', false, 1.2),
  ]);
  const [forest, forestNormal, forestRough, soil, bark, barkNormal, rockMap, rockNormal, rockRough] = loaded;
  scene.background = new THREE.Color('#80998b'); scene.fog = new THREE.FogExp2('#718e7d', 0.022);
  const hemisphere = new THREE.HemisphereLight('#d9e7ce', '#303b27', 1.25); scene.add(hemisphere);
  const sun = new THREE.DirectionalLight('#f3e3ba', 3.1); sun.position.set(-12, 25, -19); sun.target.position.set(0, 0, -2);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = -28; sun.shadow.camera.right = 28; sun.shadow.camera.top = 28; sun.shadow.camera.bottom = -28;
  sun.shadow.camera.near = 1; sun.shadow.camera.far = 70; sun.shadow.bias = -0.0002; sun.shadow.normalBias = 0.045; sun.shadow.radius = 2;
  scene.add(sun, sun.target);
  const fill = new THREE.DirectionalLight('#a9cdd1', 0.32); fill.position.set(8, 8, 14); scene.add(fill);
  let env;
  try { env = await new RGBELoader(manager).loadAsync('./assets/forest.hdr'); env.mapping = THREE.EquirectangularReflectionMapping; scene.environment = env; scene.environmentIntensity = 0.38; } catch { /* Directional and hemispheric light remain usable. */ }

  const terrainG = new THREE.PlaneGeometry(160, 160, 160, 160); terrainG.rotateX(-Math.PI / 2);
  for (let i = 0; i < terrainG.attributes.position.count; i++) { const p = terrainG.attributes.position; p.setY(i, groundHeight(p.getX(i), p.getZ(i))); }
  terrainG.computeVertexNormals();
  const terrainM = new THREE.MeshStandardMaterial({ map: forest, normalMap: forestNormal, roughnessMap: forestRough, normalScale: new THREE.Vector2(0.7, 0.7), roughness: 0.83, color: '#c5cbb7' });
  terrainM.onBeforeCompile = shader => {
    shader.uniforms.uSoil = { value: soil };
    shader.vertexShader = 'varying vec3 vTerrainPosition;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvTerrainPosition = position;');
    shader.fragmentShader = 'uniform sampler2D uSoil; varying vec3 vTerrainPosition;\n' + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <map_fragment>', `#include <map_fragment>
      float trail = abs(vTerrainPosition.x - sin(vTerrainPosition.z * 0.105) * 2.6);
      float trailMix = 1.0 - smoothstep(2.0, 4.5, trail + sin(vTerrainPosition.z * 1.4) * 0.3);
      vec4 trailColor = texture2D(uSoil, vMapUv * 1.1);
      diffuseColor.rgb = mix(diffuseColor.rgb, trailColor.rgb * vec3(0.6, 0.59, 0.52), trailMix * 0.94);`);
  };
  const terrain = new THREE.Mesh(terrainG, terrainM); terrain.receiveShadow = true; terrain.userData.surface = 'soil'; terrain.name = 'forest-floor'; scene.add(terrain); solids.push(terrain);
  const barkM = new THREE.MeshStandardMaterial({ map: bark, normalMap: barkNormal, normalScale: new THREE.Vector2(1.3, 1.3), roughness: 0.95, color: '#92976d' });
  const rootM = barkM.clone(); rootM.color.set('#6c7c4e');
  const leafM = new THREE.MeshStandardMaterial({ color: '#91aa58', vertexColors: true, roughness: 0.68, side: THREE.DoubleSide, emissive: '#142008', emissiveIntensity: 0.2 });
  const fernM = leafM.clone(); fernM.color.set('#a4b97a');
  const leafTexture=canvasTexture(256,512,(c,w,h)=>{const g=c.createLinearGradient(0,0,w,0);g.addColorStop(0,'#314520');g.addColorStop(.5,'#82964d');g.addColorStop(1,'#344b25');c.fillStyle=g;c.fillRect(0,0,w,h);c.strokeStyle='#b4bd7055';c.lineWidth=2;c.beginPath();c.moveTo(128,0);c.lineTo(128,512);c.stroke();for(let y=18;y<512;y+=22){for(const sign of [-1,1]){c.beginPath();c.moveTo(128,y);c.quadraticCurveTo(128+sign*48,y-10,128+sign*128,y-66);c.lineWidth=.8;c.stroke();}}for(let i=0;i<9500;i++){c.fillStyle=i%2?'#20340d12':'#e3ddb011';c.fillRect(random()*w,random()*h,1+random()*2,1+random()*4);}});
  leafM.map=leafTexture;leafM.color.set('#adbf8b');
  addWind(leafM, clock, 0.065); addWind(fernM, clock, 0.05);
  const barkParts = [], rootParts = [], branches = [];
  const canopyPoints = [], vinePoints = [];

  function tree(x, z, radius, height, hero = false) {
    const y = groundHeight(x, z) - 0.07, phase = random() * 6.28;
    const g = organicTrunk(radius, height, phase); g.translate(x, y, z); barkParts.push(g);
    const c = { type: 'circle', x, z, radius: radius * 1.07, bottom: y, top: y + height, name: 'tree' }; colliders.push(c); trees.push(c);
    for (let j = 0; j < (hero ? 7 : 5); j++) {
      const a = j / (hero ? 7 : 5) * Math.PI * 2 + phase, length = radius * (1.2 + random() * 1.2);
      const g = rootGeometry(radius, length, a, radius * (hero ? 1.9 : 1.15)); g.translate(x, y + 0.06, z); rootParts.push(g);
      colliders.push({ type: 'capsule', a: {x: x + Math.cos(a) * radius * 0.45, z: z + Math.sin(a) * radius * 0.45}, b: {x: x + Math.cos(a) * (length + radius * 0.3), z: z + Math.sin(a) * (length + radius * 0.3)}, radius: radius * 0.17, bottom: y, top: y + radius * 0.9, name: 'root' });
    }
    for (let j = 0; j < 4; j++) {
      const a = phase + j * 1.7, h = height * (0.61 + random() * 0.2);
      const length = 2.5 + radius * 2 + random() * 1.8;
      const pts = [new THREE.Vector3(x, y + h, z), new THREE.Vector3(x + Math.cos(a) * length * 0.45, y + h + 1.1, z + Math.sin(a) * length * 0.45), new THREE.Vector3(x + Math.cos(a) * length, y + h + 1.5, z + Math.sin(a) * length)];
      const bg = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 10, radius * 0.19, 7, false); branches.push(bg);
      canopyPoints.push({x: pts[2].x, y: pts[2].y, z: pts[2].z, size: 1.6 + radius});
      if (j < 2 && hero) vinePoints.push(pts[1]);
    }
    canopyPoints.push({x, y: y + height, z, size: 3});
  }
  // Hero trunks frame the trail and carry broad, visible buttress roots.
  [[-5, 5, 1.15, 15], [6.8, 0, 1.48, 17], [-7, -9, 1.35, 17], [6.4, -17, 1.05, 16], [8.3, 15, 1.3, 16], [-8, 21, 1.1, 15]].forEach(t => tree(...t, true));
  for (let i = 0; i < 86; i++) {
    const x = (random() - 0.5) * 100, z = (random() - 0.5) * 110;
    if (Math.abs(x - pathCenter(z)) < 6.5 || trees.some(t => Math.hypot(t.x - x, t.z - z) < t.radius + 2.3)) continue;
    tree(x, z, 0.34 + random() * 0.6, 11 + random() * 10);
  }
  for (const [parts, material, name] of [[barkParts, barkM, 'tree-trunks'], [rootParts, rootM, 'buttress-roots'], [branches, barkM, 'canopy-branches']]) {
    const m = new THREE.Mesh(mergeGeometries(parts), material); m.castShadow = m.receiveShadow = true; m.userData.surface = 'wood'; m.name = name; scene.add(m); solids.push(m); parts.forEach(g => g.dispose());
  }

  // Dense 3D fronds, broad leaves and overhead foliage share instanced geometry.
  const fernG = fernGeometry(random), fernPositions = [];
  for (let i = 0; i < 260; i++) {
    const x = (random() - 0.5) * 65, z = (random() - 0.5) * 75;
    const trail = Math.abs(x - pathCenter(z)); if (trail < 3.25 || trees.some(t => Math.hypot(t.x - x, t.z - z) < t.radius)) continue;
    fernPositions.push({x,z,size:0.65 + random() * 1.15});
  }
  // A few close fronds give the foreground a readable silhouette.
  fernPositions.push({x:-2.7,z:9,size:1.5},{x:3.5,z:7,size:1.3},{x:-3.5,z:1,size:1.7},{x:4.6,z:-7,size:1.3});
  const fernAsset=await new GLTFLoader(manager).loadAsync('./assets/fern/fern.gltf');
  const fernAlpha=await loader.loadAsync('./assets/fern/textures/fern_02_alpha_1k.jpg');fernAlpha.flipY=false;
  const fernMeshes=[];fernAsset.scene.traverse(o=>{if(o.isMesh)fernMeshes.push(o);});
  for(let variant=0;variant<fernMeshes.length;variant++){
    const source=fernMeshes[variant],material=source.material.clone();material.alphaMap=fernAlpha;material.alphaTest=.55;material.side=THREE.DoubleSide;material.roughness=.85;material.color.set('#e0e5be');material.envMapIntensity=.25;addWind(material,clock,.035);
    const list=fernPositions.filter((_,i)=>i%fernMeshes.length===variant);
    const ferns=new THREE.InstancedMesh(source.geometry,material,list.length);
    list.forEach((p,i)=>{dummy.position.set(p.x,groundHeight(p.x,p.z),p.z);dummy.rotation.set(0,random()*6.28,0);dummy.scale.setScalar(p.size*2.25);dummy.updateMatrix();ferns.setMatrixAt(i,dummy.matrix);});
    ferns.castShadow=ferns.receiveShadow=true;scene.add(ferns);
  }
  const broadG = bladeGeometry(1.1, 0.28, 0.21, 5, 2);
  const broad = new THREE.InstancedMesh(broadG, leafM, 1700);
  for (let i = 0; i < 1700; i++) {
    let x,z; do { x = (random() - 0.5) * 70; z = (random() - 0.5) * 80; } while (Math.abs(x - pathCenter(z)) < 4.1);
    dummy.position.set(x, groundHeight(x,z) + 0.025, z); dummy.rotation.set(-0.2-random()*.7, random() * 6.28, (random()-0.5)*0.3); dummy.scale.setScalar(0.45 + random() * 0.9); dummy.updateMatrix(); broad.setMatrixAt(i,dummy.matrix);
    broad.setColorAt(i,new THREE.Color().setHSL(0.23 + random() * 0.055,0.35,0.6 + random() * 0.25));
  }
  broad.receiveShadow = true; scene.add(broad);
  const branchLeaves=[],twigs=[];
  for(let i=0;i<8;i++){
    const t=i/8;
    for(const side of [-1,1]){
      const leaf=bladeGeometry(.52,.14,.07,5,2);leaf.rotateY(side*1.05);leaf.rotateX(-.12);leaf.translate(0,Math.sin(t*2)*.25,t*2.9);branchLeaves.push(leaf);
    }
  }
  const branchG=mergeGeometries(branchLeaves);branchLeaves.forEach(g=>g.dispose());
  const twigG=new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(0,0,0),new THREE.Vector3(0,.23,1.4),new THREE.Vector3(0,.23,3)]),8,.018,5,false);
  const canopy=new THREE.InstancedMesh(branchG,leafM,canopyPoints.length*3);
  const canopyTwigs=new THREE.InstancedMesh(twigG,barkM,canopyPoints.length*3);
  let ci=0;
  canopyPoints.forEach(p=>{for(let j=0;j<3;j++){dummy.position.set(p.x,p.y,p.z);dummy.rotation.set((random()-.5)*.6,random()*6.28,(random()-.5)*.4);dummy.scale.setScalar(.9+random()*.65);dummy.updateMatrix();canopy.setMatrixAt(ci,dummy.matrix);canopyTwigs.setMatrixAt(ci,dummy.matrix);ci++;}});
  canopy.castShadow=true;canopy.receiveShadow=true;scene.add(canopy,canopyTwigs);

  // Hanging lianas remain thin and round at close range.
  const vineM = new THREE.MeshStandardMaterial({color:'#38402a',roughness:1});
  const vineParts=[];
  vinePoints.forEach((p,i)=>{
    const length=3+random()*6, points=[];
    for(let j=0;j<7;j++) points.push(new THREE.Vector3(p.x+Math.sin(j*.7+i)*.25,p.y-j/6*length,p.z+Math.cos(j*.6)*.18));
    vineParts.push(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),24,.025,5,false));
  });
  if(vineParts.length){const m=new THREE.Mesh(mergeGeometries(vineParts),vineM);scene.add(m);vineParts.forEach(g=>g.dispose());}

  const rockM = new THREE.MeshStandardMaterial({ map:rockMap, normalMap:rockNormal, roughnessMap:rockRough, color:'#8a947b',roughness:.92,normalScale:new THREE.Vector2(1,1) });
  const rockPositions=[[-3.9,3,1.1],[4.2,-3,1.0],[-4.4,-15,1.7],[4.8,19,1.5],[-10,11,1.7],[10,-9,2.0],[-1,-24,1.8],[16,5,2.5]];
  rockPositions.forEach(([x,z,s],i)=>{
    const g=new THREE.SphereGeometry(1,24,18),p=g.attributes.position;
    for(let k=0;k<p.count;k++){const a=p.getX(k),b=p.getY(k),c=p.getZ(k);const n=1+Math.sin(a*9+c*7+i)*Math.sin(b*7+a*3)*.12;p.setXYZ(k,a*n,b*n,c*n);}g.computeVertexNormals();
    const mesh=new THREE.Mesh(g,rockM);mesh.position.set(x,groundHeight(x,z)+s*.25,z);mesh.scale.set(s,s*.78,s*.86);mesh.rotation.y=random()*6.28;mesh.castShadow=mesh.receiveShadow=true;mesh.userData.surface='stone';mesh.name=`boulder-${i}`;scene.add(mesh);solids.push(mesh);
    colliders.push({type:'circle',x,z,radius:s*.91,bottom:mesh.position.y-s*.8,top:mesh.position.y+s*.72,name:'rock'});
  });
  // Pebbles are visual detail, low enough to walk over.
  const pebble=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1,1),rockM,240);
  for(let i=0;i<240;i++){const x=(random()-.5)*34,z=(random()-.5)*50,s=.035+random()*.12;dummy.position.set(x,groundHeight(x,z),z);dummy.rotation.set(random(),random()*6.28,random());dummy.scale.set(s,s*.55,s*.8);dummy.updateMatrix();pebble.setMatrixAt(i,dummy.matrix);}pebble.receiveShadow=true;scene.add(pebble);

  const waterM=new THREE.MeshPhysicalMaterial({color:'#334b3d',metalness:.25,roughness:.1,transparent:true,opacity:.42,clearcoat:1,clearcoatRoughness:.08,depthWrite:false});
  const puddles=[];
  [[-.6,8,1.1,1.9],[1.8,2,.85,1.5],[-1,-7,1.25,2],[.6,-17,.9,1.6],[-1.2,19,1,1.3]].forEach(([x,z,rx,rz])=>{
    const vertices=[x,groundHeight(x,z)+.013,z],uv=[.5,.5],indices=[];
    for(let i=0;i<=50;i++){const a=i/50*6.28318,r=1+Math.sin(a*7)*.09+Math.cos(a*11)*.05,px=x+Math.cos(a)*rx*r,pz=z+Math.sin(a)*rz*r;vertices.push(px,groundHeight(px,pz)+.016,pz);uv.push(Math.cos(a)*.5+.5,Math.sin(a)*.5+.5);if(i<50)indices.push(0,i+2,i+1);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();const m=new THREE.Mesh(g,waterM);m.receiveShadow=true;m.renderOrder=1;scene.add(m);puddles.push({x,z,rx,rz});
  });

  const woodM=new THREE.MeshStandardMaterial({map:bark,color:'#89744b',roughness:.9});
  const steelM=new THREE.MeshStandardMaterial({color:'#5b6455',metalness:.72,roughness:.46});
  const orangeM=new THREE.MeshStandardMaterial({color:'#cc7849',roughness:.7,metalness:.15});
  const supplyM=new THREE.MeshStandardMaterial({color:'#515e40',roughness:.67,metalness:.22});
  const meshBox=(w,h,d,material,x,y,z)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);m.position.set(x,y,z);m.castShadow=m.receiveShadow=true;scene.add(m);return m;};
  function target(x,z,label,metal=true) {
    const y=groundHeight(x,z),group=new THREE.Group();group.position.set(x,y+1.65,z);scene.add(group);
    const stem=meshBox(.07,1.8,.08,steelM,x,y+.9,z-.12);stem.userData.surface='metal';solids.push(stem);
    const foot=meshBox(.8,.07,.5,steelM,x,y+.035,z);
    const plate=new THREE.Mesh(new THREE.CylinderGeometry(.33,.33,.045,48),metal?steelM:woodM);plate.rotation.x=Math.PI/2;group.add(plate);plate.userData.surface=metal?'metal':'wood';plate.userData.target=true;plate.name=`target-${label}`;solids.push(plate);
    const targetMap=canvasTexture(512,512,c=>{c.clearRect(0,0,512,512);c.strokeStyle=metal?'#e1d7ba':'#252b24';c.lineWidth=11;for(const r of [205,140,75]){c.beginPath();c.arc(256,256,r,0,Math.PI*2);c.stroke();}c.fillStyle='#c9774a';c.beginPath();c.arc(256,256,28,0,6.28);c.fill();});
    const decal=new THREE.Mesh(new THREE.PlaneGeometry(.62,.62),new THREE.MeshStandardMaterial({map:targetMap,transparent:true,depthWrite:false,roughness:.8,polygonOffset:true,polygonOffsetFactor:-2}));decal.position.z=.025;group.add(decal);
    const sign=new THREE.Mesh(new THREE.PlaneGeometry(.38,.19),new THREE.MeshStandardMaterial({map:labelTexture(label,'FIELD TARGET'),roughness:1}));sign.position.set(x,y+.48,z+.05);scene.add(sign);
    const obj={mesh:plate,pivot:group,angle:0,velocity:0,baseY:y+1.65,label};plate.userData.targetRef=obj;targets.push(obj);
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
  let raining=true;
  return {
    solids,colliders,targets,breakables,trees,terrain,supply,puddles,sun,clock,
    setRain(enabled){raining=enabled;rain.visible=enabled;},
    update(dt,time,camera){clock.value=time;for(const t of targets){t.velocity+=(-t.angle*34-t.velocity*6)*dt;t.angle+=t.velocity*dt;t.pivot.rotation.x=t.angle;}if(raining){rain.position.set(camera.position.x,0,camera.position.z);for(let i=0;i<rainCount;i++){const k=i*6;rainArray[k+1]-=dt*11;rainArray[k+4]-=dt*11;if(rainArray[k+1]<-.2){rainArray[k+1]+=18;rainArray[k+4]+=18;}}rainG.attributes.position.needsUpdate=true;}},
    reset(){targets.forEach(t=>{t.velocity=0;t.angle=0;t.pivot.rotation.x=0;});breakables.forEach(b=>{b.hp=5;b.alive=true;b.group.visible=true;b.collider.disabled=false;});}
  };
}
