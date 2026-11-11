export const PLAYER_RADIUS = 0.32;
export const BOUNDS = { minX: -24, maxX: 24, minZ: -28, maxZ: 28 };
export const pathCenter = z => Math.sin(z * 0.105) * 2.6;
export function groundHeight(x, z) {
  const edge = Math.min(1, Math.max(0, (Math.abs(x - pathCenter(z)) - 2.6) / 7));
  return Math.sin(z * 0.11) * 0.13 + Math.sin(x * 0.19 + z * 0.075) * 0.065
    + edge * (0.1 + Math.sin(x * 0.22) * Math.cos(z * 0.21) * 0.3);
}
export function closestOnSegment(x, z, a, b) {
  const dx = b.x - a.x, dz = b.z - a.z, d = dx * dx + dz * dz;
  const t = d > 0 ? Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / d)) : 0;
  return { x: a.x + dx * t, z: a.z + dz * t };
}
export function resolveOverlap(pos, collider, radius = PLAYER_RADIUS, height = 1.8) {
  if (collider.disabled || pos.y >= collider.top - 0.025 || pos.y + height < collider.bottom) return false;
  let cx, cz;
  if (collider.type === 'box') {
    cx = Math.max(collider.minX, Math.min(collider.maxX, pos.x));
    cz = Math.max(collider.minZ, Math.min(collider.maxZ, pos.z));
    if (cx === pos.x && cz === pos.z) {
      const sides = [
        { d: pos.x - collider.minX, x: collider.minX - radius, z: pos.z },
        { d: collider.maxX - pos.x, x: collider.maxX + radius, z: pos.z },
        { d: pos.z - collider.minZ, x: pos.x, z: collider.minZ - radius },
        { d: collider.maxZ - pos.z, x: pos.x, z: collider.maxZ + radius },
      ].sort((a, b) => a.d - b.d);
      pos.x = sides[0].x; pos.z = sides[0].z; return true;
    }
  } else if (collider.type === 'capsule') {
    const p = closestOnSegment(pos.x, pos.z, collider.a, collider.b); cx = p.x; cz = p.z;
  } else { cx = collider.x; cz = collider.z; }
  const dx = pos.x - cx, dz = pos.z - cz;
  const distance = Math.hypot(dx, dz), required = radius + (collider.type === 'box' ? 0 : collider.radius);
  if (distance >= required) return false;
  if (distance < 1e-7) { pos.x += required; return true; }
  pos.x += dx / distance * (required - distance + 0.0001);
  pos.z += dz / distance * (required - distance + 0.0001);
  return true;
}
export function moveWithCollisions(position, dx, dz, colliders, height = 1.8) {
  // Substeps limit tunnelling even after a slow frame or against thin target posts.
  const steps = Math.max(1, Math.ceil(Math.hypot(dx, dz) / 0.075));
  let contacts = 0;
  for (let i = 0; i < steps; i++) {
    position.x += dx / steps; position.z += dz / steps;
    for (let iteration = 0; iteration < 4; iteration++) {
      let changed = false;
      for (const c of colliders) if (resolveOverlap(position, c, PLAYER_RADIUS, height)) { changed = true; contacts++; }
      if (!changed) break;
    }
    position.x = Math.max(BOUNDS.minX + PLAYER_RADIUS, Math.min(BOUNDS.maxX - PLAYER_RADIUS, position.x));
    position.z = Math.max(BOUNDS.minZ + PLAYER_RADIUS, Math.min(BOUNDS.maxZ - PLAYER_RADIUS, position.z));
  }
  return contacts;
}

export function supportHeight(x, z, previousFeet, colliders) {
  let floor = -Infinity;
  for (const c of colliders) {
    if (c.disabled || c.type !== 'box' || previousFeet < c.top - 0.04) continue;
    if (x >= c.minX && x <= c.maxX && z >= c.minZ && z <= c.maxZ) floor = Math.max(floor, c.top);
  }
  return floor;
}
