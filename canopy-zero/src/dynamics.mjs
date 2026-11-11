// SI units: metres, kilograms, seconds. A chain-suspended rigid plate.
export class SuspendedTarget {
  constructor({mass=5.2,radius=.33,length=.52,damping=1.4}={}) {
    Object.assign(this,{mass,radius,length,damping});
    this.inertia=mass*radius*radius/4;this.reset();
  }
  reset(){this.offset=[0,0,0];this.velocity=[0,0,0];this.rotation=[0,0,0];this.angularVelocity=[0,0,0];this.lastImpulse=null;}
  applyImpulse(point,direction,strength=1.65){
    const J=direction.map(v=>v*strength),r=point;
    // Angular momentum depends on the signed lever arm, not a canned animation.
    const torque=[r[1]*J[2]-r[2]*J[1],r[2]*J[0]-r[0]*J[2],r[0]*J[1]-r[1]*J[0]];
    for(const axis of [0,2])this.velocity[axis]+=J[axis]/this.mass;
    for(let i=0;i<3;i++)this.angularVelocity[i]+=torque[i]/(this.inertia*(i===2?2:1));
    this.lastImpulse={point:[...point],direction:[...direction],linear:J,torque};
  }
  update(dt){
    const steps=Math.max(1,Math.ceil(dt/(1/120))),h=dt/steps;
    for(let j=0;j<steps;j++){
      for(const i of [0,2]){
        this.velocity[i]+=(-9.81/this.length*this.offset[i]-this.damping*this.velocity[i])*h;
        this.offset[i]+=this.velocity[i]*h;
      }
      const distance=Math.hypot(this.offset[0],this.offset[2]),limit=this.length*.72;
      if(distance>limit){for(const i of [0,2]){this.offset[i]*=limit/distance;this.velocity[i]*=.65;}}
      this.offset[1]=this.length-Math.sqrt(Math.max(.001,this.length*this.length-this.offset[0]**2-this.offset[2]**2));
      for(let i=0;i<3;i++){
        const spring=i===1?4.5:15;
        this.angularVelocity[i]+=(-spring*Math.sin(this.rotation[i])-this.damping*1.15*this.angularVelocity[i])*h;
        this.rotation[i]+=this.angularVelocity[i]*h;
      }
    }
  }
  energy(){return .5*this.mass*(this.velocity[0]**2+this.velocity[2]**2)+this.mass*9.81*this.offset[1]+this.rotation.reduce((s,a,i)=>s+.5*this.inertia*(this.angularVelocity[i]**2+(i===1?4.5:15)*a*a),0);}
}
