import * as THREE from 'three';
import { Octree } from 'three/addons/math/Octree.js';
import { Capsule } from 'three/addons/math/Capsule.js';
import { BOUNDS, PLAYER_RADIUS, groundHeight } from './physics.mjs?v=20261112-r5';

// Index reachable wood and rock surfaces, not leaves or moving targets. The
// original triangles retain side branches, protruding roots and sloped rocks.
export function createMeshCollision(meshes) {
  const tree = new Octree(), a = new THREE.Vector3(), b = a.clone(), c = a.clone();
  const matrix = new THREE.Matrix4(), instance = new THREE.Matrix4();
  let triangles = 0, objects = 0;
  for (const mesh of meshes) {
    mesh.updateWorldMatrix(true, false);
    const position = mesh.geometry.attributes.position, index = mesh.geometry.index;
    const count = index ? index.count : position.count;
    const copies = mesh.isInstancedMesh ? mesh.count : 1;
    let included = false;
    for (let copy = 0; copy < copies; copy++) {
      matrix.copy(mesh.matrixWorld);
      if (mesh.isInstancedMesh) { mesh.getMatrixAt(copy, instance); matrix.multiply(instance); }
      for (let i = 0; i < count; i += 3) {
        a.fromBufferAttribute(position, index ? index.getX(i) : i).applyMatrix4(matrix);
        b.fromBufferAttribute(position, index ? index.getX(i + 1) : i + 1).applyMatrix4(matrix);
        c.fromBufferAttribute(position, index ? index.getX(i + 2) : i + 2).applyMatrix4(matrix);
        if (Math.min(a.x, b.x, c.x) > BOUNDS.maxX + 1 || Math.max(a.x, b.x, c.x) < BOUNDS.minX - 1 ||
            Math.min(a.z, b.z, c.z) > BOUNDS.maxZ + 1 || Math.max(a.z, b.z, c.z) < BOUNDS.minZ - 1) continue;
        const floor = groundHeight((a.x + b.x + c.x) / 3, (a.z + b.z + c.z) / 3);
        if (Math.min(a.y, b.y, c.y) > floor + 3.5 || Math.max(a.y, b.y, c.y) < floor - .1) continue;
        const triangle = new THREE.Triangle(a.clone(), b.clone(), c.clone());
        if (triangle.getArea() < 1e-9) continue;
        tree.addTriangle(triangle); triangles++; included = true;
      }
    }
    if (included) objects++;
  }
  if (triangles) tree.build();
  // r170 deduplicates candidates with repeated Array.indexOf calls. Dense
  // scanned roots can share a triangle across many octants; use a Set while
  // keeping the original depth-first order and the same narrow-phase tests.
  const collect = (shape, result) => {
    const seen = new Set(result);
    const visit = node => {
      for (const child of node.subTrees) {
        if (!shape.intersectsBox(child.box)) continue;
        if (child.triangles.length) {
          for (const triangle of child.triangles) {
            if (!seen.has(triangle)) { seen.add(triangle); result.push(triangle); }
          }
        } else visit(child);
      }
    };
    visit(tree);
    return result;
  };
  tree.getCapsuleTriangles = collect;
  tree.getSphereTriangles = collect;
  const capsule = new Capsule();
  const setCapsule = (position, height) => {
    capsule.start.set(position.x, position.y + PLAYER_RADIUS, position.z);
    capsule.end.set(position.x, position.y + height - PLAYER_RADIUS, position.z);
    capsule.radius = PLAYER_RADIUS;
  };
  return {
    triangles, objects,
    intersect(position, height = 1.8) {
      if (!triangles) return false;
      setCapsule(position, height);
      return tree.capsuleIntersect(capsule);
    },
    resolve(position, height = 1.8) {
      const normal = new THREE.Vector3(); let contacts = 0, grounded = false, ceiling = false;
      for (let i = 0; i < 5; i++) {
        const hit = this.intersect(position, height);
        if (!hit || hit.depth < .00001) break;
        position.addScaledVector(hit.normal, hit.depth + .00005);
        normal.add(hit.normal); grounded ||= hit.normal.y > .55; ceiling ||= hit.normal.y < -.55; contacts++;
      }
      return { contacts, grounded, ceiling, normal: normal.normalize() };
    },
    rayDistance(origin, direction, limit = 1.2) {
      if (!triangles) return limit;
      const candidates = [], ray = new THREE.Ray(origin, direction), point = new THREE.Vector3();
      const sphere = new THREE.Sphere(origin.clone().addScaledVector(direction, limit / 2), limit / 2 + .02);
      tree.getSphereTriangles(sphere, candidates);
      let distance = limit;
      for (const triangle of candidates) {
        if (ray.intersectTriangle(triangle.a, triangle.b, triangle.c, false, point)) distance = Math.min(distance, point.distanceTo(origin));
      }
      return distance;
    }
  };
}
