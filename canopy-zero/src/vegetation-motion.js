import * as THREE from 'three';

// The visible material and shadow caster share the same deformation. Roots
// stay fixed; the reachable wood of large trees stays aligned with collision.
export function createVegetationMotion(clock, player) {
  const materials = new Map();
  let animatedMeshes = 0;
  function attach(mesh, { height, tree = false, leaf = true, track = true }) {
    const geometry = mesh.geometry;
    if (!geometry.getAttribute('foliageTip')) {
      const weights = new Float32Array(geometry.attributes.position.count);
      const uv = geometry.attributes.uv;
      if (leaf && tree && uv && weights.length % 4 === 0) {
        // Tree leaves are authored as individual four-vertex cards. The
        // max-V edge is the petiole, so flutter never detaches that edge.
        for (let i = 0; i < weights.length; i += 4) {
          const vs = [0, 1, 2, 3].map(j => uv.getY(i + j));
          const lo = Math.min(...vs), hi = Math.max(...vs);
          for (let j = 0; j < 4; j++) weights[i + j] = (hi - vs[j]) / Math.max(hi - lo, .0001);
        }
      } else if (leaf) {
        for (let i = 0; i < weights.length; i++) weights[i] = Math.min(1, Math.max(0, geometry.attributes.position.getY(i) / height));
      }
      geometry.setAttribute('foliageTip', new THREE.BufferAttribute(weights, 1));
      geometry.computeBoundingSphere();
      geometry.boundingSphere.radius += .5;
    }
    const key = `${mesh.material.uuid}/${height}/${tree}/${leaf}`;
    if (!materials.has(key)) {
      const visible = mesh.material.clone();
      visible.alphaToCoverage = leaf;
      visible.dithering = true;
      if (leaf) { visible.roughness = .94; visible.metalness = 0; visible.envMapIntensity = .8; }
      const depth = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking,
        map: visible.map, alphaMap: visible.alphaMap, alphaTest: visible.alphaTest, side: THREE.DoubleSide });
      const inject = (shader, shaded) => {
        shader.uniforms.uFoliageTime = clock;
        shader.uniforms.uFoliageHeight = { value: height };
        shader.uniforms.uFoliagePlayer = player;
        shader.vertexShader = `uniform float uFoliageTime; uniform float uFoliageHeight; uniform vec3 uFoliagePlayer;
          attribute float foliageTip;\n` + shader.vertexShader;
        shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
          mat4 plantMatrix = modelMatrix;
          #ifdef USE_INSTANCING
            plantMatrix = modelMatrix * instanceMatrix;
          #endif
          mat3 basis = mat3(plantMatrix);
          vec3 plantOrigin = plantMatrix[3].xyz;
          vec3 plantPoint = (plantMatrix * vec4(position, 1.0)).xyz;
          float heightWorld = max(plantPoint.y - plantOrigin.y, 0.0);
          float plantHeight = max(uFoliageHeight * length(basis[1]), .01);
          float phase = plantOrigin.x * .57 + plantOrigin.z * .31;
          float gust = .72 + .28 * sin(uFoliageTime * .37 + phase * .23);
          float wave = sin(uFoliageTime * .82 + phase) * .68 + sin(uFoliageTime * 1.63 + phase * .71) * .32;
          float bendWeight = ${tree ? 'pow(clamp((heightWorld - 3.5) / max(plantHeight - 3.5, 1.0), 0.0, 1.0), 1.6)' : 'pow(clamp(heightWorld / plantHeight, 0.0, 1.0), 1.6)'};
          float amplitude = ${tree ? '.012 * min(plantHeight, 22.0)' : '.085 * min(plantHeight, 2.5)'};
          vec3 drift = vec3(.84, 0.0, .54) * wave * gust * bendWeight * amplitude;
          ${leaf ? `drift += normalize(basis * normal) * foliageTip * .012 *
            sin(uFoliageTime * 3.1 + plantPoint.x * 2.7 + plantPoint.z * 1.9);` : ''}
          ${!tree ? `vec2 away = plantPoint.xz - uFoliagePlayer.xz;
            float touch = (1.0 - smoothstep(.18, .95, length(away))) *
              (1.0 - smoothstep(.10, .95, abs(plantPoint.y - uFoliagePlayer.y)));
            drift.xz += normalize(away + vec2(.0001)) * touch * bendWeight * .48;` : ''}
          transformed += vec3(dot(basis[0], drift) / dot(basis[0], basis[0]),
            dot(basis[1], drift) / dot(basis[1], basis[1]),
            dot(basis[2], drift) / dot(basis[2], basis[2]));`);
        if (shaded && leaf) {
          shader.fragmentShader = shader.fragmentShader
            .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = max(roughnessFactor, .64);')
            .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\nreflectedLight.indirectDiffuse += diffuseColor.rgb * .045;');
        }
      };
      visible.onBeforeCompile = shader => inject(shader, true);
      depth.onBeforeCompile = shader => inject(shader, false);
      visible.customProgramCacheKey = () => `foliage-v5/${tree}/${leaf}`;
      depth.customProgramCacheKey = visible.customProgramCacheKey;
      materials.set(key, { visible, depth });
    }
    const pair = materials.get(key);
    mesh.material = pair.visible;
    mesh.customDepthMaterial = pair.depth;
    mesh.userData.vegetationMotion = true;
    if (track) animatedMeshes++;
  }
  return { attach, get count() { return animatedMeshes; } };
}
