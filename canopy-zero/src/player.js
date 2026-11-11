import * as THREE from 'three';
import { groundHeight, moveWithCollisions, supportHeight } from './physics.mjs?v=20261111-r2';

export class Player {
  constructor(camera, colliders) {
    this.camera = camera; this.colliders = colliders; this.position = new THREE.Vector3();
    this.keys = new Set(); this.velocity = new THREE.Vector3(); this.yaw = 0; this.pitch = 0;
    this.eye = 1.67; this.bob = 0; this.sensitivity = 1; this.sprint = false; this.contacts = 0;
    this.onStep = () => {}; this.stepDistance = 0; this.reset();
  }
  reset() {
    this.position.set(0.6, groundHeight(0.6, 13), 13);
    this.velocity.set(0, 0, 0); this.yaw = -0.08; this.pitch = -0.045; this.grounded = true; this.jumpRequested = false;
    this.keys.clear(); this.eye = 1.67; this.bob = 0; this.stepDistance = 0;
    this.updateCamera(0, false);
  }
  look(dx, dy, aim = false) {
    const sensitivity = 0.0018 * this.sensitivity * (aim ? 0.55 : 1);
    this.yaw -= dx * sensitivity;
    this.pitch = THREE.MathUtils.clamp(this.pitch - dy * sensitivity, -1.43, 1.43);
  }
  update(dt, aiming) {
    const crouch = this.keys.has('KeyC');
    this.sprint = this.keys.has('ShiftLeft') && !aiming && !crouch && this.keys.has('KeyW');
    const speed = crouch ? 1.55 : this.sprint ? 5.6 : aiming ? 2.1 : 3.2;
    let x = Number(this.keys.has('KeyD')) - Number(this.keys.has('KeyA'));
    let z = Number(this.keys.has('KeyS')) - Number(this.keys.has('KeyW'));
    const length = Math.hypot(x, z) || 1; x /= length; z /= length;
    const vx = (x * Math.cos(this.yaw) + z * Math.sin(this.yaw)) * speed;
    const vz = (z * Math.cos(this.yaw) - x * Math.sin(this.yaw)) * speed;
    this.velocity.x = THREE.MathUtils.damp(this.velocity.x, vx, 13, dt);
    this.velocity.z = THREE.MathUtils.damp(this.velocity.z, vz, 13, dt);
    if (this.grounded && (this.jumpRequested || this.keys.has('Space')) && !crouch) { this.velocity.y = 5.5; this.grounded = false; this.keys.delete('Space'); }
    this.jumpRequested = false;
    this.velocity.y -= 15 * dt;
    const prevX = this.position.x, prevZ = this.position.z;
    this.contacts = moveWithCollisions(this.position, this.velocity.x * dt, this.velocity.z * dt, this.colliders, crouch ? 1.2 : 1.8);
    const previousFeet = this.position.y;
    this.position.y += this.velocity.y * dt;
    const floor = Math.max(groundHeight(this.position.x, this.position.z), supportHeight(this.position.x, this.position.z, previousFeet, this.colliders));
    if (this.position.y <= floor) { this.position.y = floor; this.velocity.y = 0; this.grounded = true; }
    else if (this.position.y - floor > 0.1) this.grounded = false;
    const distance = Math.hypot(this.position.x - prevX, this.position.z - prevZ);
    if (this.grounded) {
      this.bob += distance * 8;
      this.stepDistance += distance;
      if (this.stepDistance > (this.sprint ? 1.7 : 1.35)) { this.stepDistance = 0; this.onStep(this.sprint); }
    }
    this.moving = distance > 0.0008;
    this.eye = THREE.MathUtils.damp(this.eye, crouch ? 1.08 : 1.67, 12, dt);
    this.updateCamera(dt, aiming);
  }
  updateCamera(dt, aiming) {
    this.camera.position.copy(this.position);
    this.camera.position.y += this.eye + (this.moving && this.grounded ? Math.sin(this.bob) * (aiming ? 0.004 : 0.015) : 0);
    this.camera.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
  }
}
