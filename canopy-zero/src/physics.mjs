export const PLAYER_RADIUS = 0.32;
export const BOUNDS = { minX: -24, maxX: 24, minZ: -28, maxZ: 28 };
export const pathCenter = z => Math.sin(z * 0.105) * 2.6;
// Shared channel profile: terrain, water surface and collision use the same banks.
export const riverCenter = z => 9.3 + Math.sin(z*.115)*1.75 + Math.sin(z*.31)*.23 + Math.sin(z*.81)*.11;
export const riverWidth = z => 1.05 + .18*Math.sin(z*.22) + .10*Math.sin(z*.93+1.2) + .045*Math.sin(z*2.13);
export const riverLevel = z => -.13+(z+28)*.003;
const smoothstep=(a,b,x)=>{const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t);};
export function riverDepth(x,z){const u=Math.abs(x-riverCenter(z))/riverWidth(z);return Math.max(0,(.28+.09*Math.sin(z*.37)+.035*Math.sin(z*.91))*(1-u*u));}
export function groundHeight(x, z) {
  const edge = Math.min(1, Math.max(0, (Math.abs(x - pathCenter(z)) - 2.6) / 7));
  const base=Math.sin(z*.11)*.13+Math.sin(x*.19+z*.075)*.065+edge*(.1+Math.sin(x*.22)*Math.cos(z*.21)*.3);
  const distance=Math.abs(x-riverCenter(z)),width=riverWidth(z),level=riverLevel(z);
  if(distance<=width)return level-riverDepth(x,z);
  const bank=distance-width,crest=Math.max(base,level+.12),shore=level+(crest-level)*smoothstep(0,.65,bank);
  return shore*(1-smoothstep(.7,1.5,bank))+base*smoothstep(.7,1.5,bank);
}
export function waterHeight(x,z){return riverDepth(x,z)>.0001&&z>-32&&z<32?riverLevel(z):null;}
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
