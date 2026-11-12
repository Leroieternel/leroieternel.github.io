import * as THREE from 'three';
const lookup=(bones,name)=>bones[name]||bones[name.replace(/[.]/g,'')]||bones[name.replace(/[.]/g,'_')];
const Y=new THREE.Vector3(0,1,0),v=(x,y,z)=>new THREE.Vector3(x,y,z);
function aimBone(bone,direction){bone.updateWorldMatrix(true,false);const world=bone.getWorldQuaternion(new THREE.Quaternion()),current=Y.clone().applyQuaternion(world),change=new THREE.Quaternion().setFromUnitVectors(current,direction.clone().normalize());world.premultiply(change);bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(world));bone.updateWorldMatrix(false,true);}
function setPosition(bone,world){bone.position.copy(bone.parent.worldToLocal(world.clone()));bone.updateWorldMatrix(false,true);}
// Solve the elbow on the intersection circle of two fixed-length bone segments.
function elbowPosition(shoulder,wrist,l1,l2,pole){const axis=wrist.clone().sub(shoulder),d=Math.min(axis.length(),l1+l2-.00001);axis.normalize();const a=(l1*l1-l2*l2+d*d)/(2*d),h=Math.sqrt(Math.max(0,l1*l1-a*a)),across=pole.clone().sub(shoulder);across.addScaledVector(axis,-across.dot(axis)).normalize();return shoulder.clone().addScaledVector(axis,a).addScaledVector(across,h);}
export function correctGrip(holder,bones){
 holder.updateWorldMatrix(true,true);const control=bones.IK_Hand_Cntrl_R;const rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-24*Math.PI/180);const q=control.getWorldQuaternion(new THREE.Quaternion()).premultiply(rotation);control.quaternion.copy(control.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(q));setPosition(control,holder.localToWorld(new THREE.Vector3(.044,.014,.211).multiplyScalar(2)));holder.updateWorldMatrix(true,true);const toWorld=p=>holder.localToWorld(p.clone().multiplyScalar(2)),report={};
 for(const side of ['L','R']){
  const upper=bones['UpArm_'+side],fore=bones['Forearm_'+side],wrist=bones['Hand_'+side],end=lookup(bones,'BoneTwist_01.'+side+'_end');
  const hand=wrist.getWorldPosition(v(0,0,0)),oldShoulder=upper.getWorldPosition(v(0,0,0)),oldElbow=fore.getWorldPosition(v(0,0,0)),l1=oldShoulder.distanceTo(oldElbow),l2=oldElbow.distanceTo(end.getWorldPosition(v(0,0,0)));
  const shoulder=toWorld(side==='R'?v(.13,-.080,.42):v(-.24,-.23,.25)),pole=toWorld(side==='R'?v(.07,.045,.46):v(-.13,-.022,.103));
  // Restore the source sleeve's cropped 14 cm upper-arm segment to an adult
  // upper-arm length; keep the entire wrist/forearm at its original length.
  const elbow=side==='L'?oldElbow.clone():elbowPosition(shoulder,hand,l1,l2,pole);setPosition(upper,shoulder);aimBone(upper,elbow.clone().sub(shoulder));if(side==='L')setPosition(fore,elbow);aimBone(fore,hand.clone().sub(elbow));
  report[side]={upperLength:shoulder.distanceTo(elbow),forearmLength:l2,wristGap:end.getWorldPosition(v(0,0,0)).distanceTo(hand)};
 }
 const bone=(side,n)=>lookup(bones,'Bone_'+side+'.'+String(n).padStart(3,'0'));
 // PIP and DIP joints flex in one plane; no lateral zig-zag or reversed bends.
 for(const [a,b,c] of [[9,10,11],[13,14,15],[17,18,19]]){
  const down=a===17?-.03:-.08;
  for(const [n,d] of [[a,v(-.53,down,-.85)],[b,v(-.99,down,-.12)],[c,v(-.66,down,.75)]])aimBone(bone('R',n),d);
 }
 for(const [n,d] of [[5,v(-.22,-.08,-.97)],[6,v(-.65,-.08,-.76)],[7,v(-.98,-.08,.18)]])aimBone(bone('R',n),d);
 for(const [a,b,c] of [[5,6,7],[9,10,11],[13,14,15],[17,18,19]]){
  const base=Y.clone().applyQuaternion(bone('L',a).getWorldQuaternion(new THREE.Quaternion()));base.y=0;base.normalize();
  for(const [n,angle] of [[a,25],[b,77],[c,115]]){const t=angle*Math.PI/180;aimBone(bone('L',n),base.clone().multiplyScalar(Math.cos(t)).addScaledVector(Y,Math.sin(t)));}
 }
 for(const [n,d] of [[20,v(.12,.63,-.77)],[21,v(.35,.82,.45)],[22,v(.50,.14,.85)]])aimBone(bone('L',n),d);
 holder.updateWorldMatrix(true,true);
 for(const side of ['L','R']){const wrist=bones['Hand_'+side],fore=bones['Forearm_'+side],metacarpal=bone(side,8),dir=Y.clone().applyQuaternion(metacarpal.getWorldQuaternion(new THREE.Quaternion())),arm=wrist.getWorldPosition(v(0,0,0)).sub(fore.getWorldPosition(v(0,0,0))).normalize();report[side].wristAngle=THREE.MathUtils.radToDeg(arm.angleTo(dir));report[side].forearmLengthAfter=wrist.getWorldPosition(v(0,0,0)).distanceTo(fore.getWorldPosition(v(0,0,0)));}
 return report;
}
