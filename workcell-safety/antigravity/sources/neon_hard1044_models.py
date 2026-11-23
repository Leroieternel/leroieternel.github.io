"""Native DESPITE robot assembly and common joint, Jacobian and contact access."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUTS = ROOT/'outputs'
LIB = Path.home()/'github/robosuite/robosuite/models/assets'
SOURCES = {
    'spot': (OUTPUTS/'robot_plans/03_inspection/scene.xml','body'),
    'husky': (OUTPUTS/'robot_plans/01_crossing/scene.xml','husky_base'),
    'panda': (OUTPUTS/'robot_plans/06_balance/scene.xml','base'),
    'baxter': (OUTPUTS/'robot_plans/09_bimanual/scene.xml','base'),
    'omron': (OUTPUTS/'mobile_worlds/physics/01_warehouse/scene.xml','base'),
    'gr1': (LIB/'robots/gr1/robot.xml','base'),
}
def string(v):
    if isinstance(v,(list,tuple,np.ndarray)):
        return ' '.join(str(x) for x in np.asarray(v).ravel())
    if isinstance(v,(bool,np.bool_)):
        return 'true' if v else 'false'
    return str(v)
def add(parent,tag,**attributes):
    return ET.SubElement(parent,tag,{k:string(v) for k,v in attributes.items() if v is not None})
def geom(parent,name,kind,pos,size,rgba=(.5,.5,.5,1),**kwargs):
    return add(parent,'geom',name=name,type=kind,pos=pos,size=size,rgba=rgba,**kwargs)
def free(world,name,pos):
    body=add(world,'body',name=name,pos=pos)
    add(body,'freejoint',name=name+'_free')
    return body
def gr1(robot,assets):
    robot.set('pos','0 0 .953')
    # The library's GR1FixedLowerBody configuration removes the free joint and leg joints.
    for body in robot.iter('body'):
        for joint in list(body):
            if joint.tag=='freejoint' or (joint.tag=='joint' and '_leg_' in joint.get('name','')):
                body.remove(joint)
    for i,side in enumerate(('right','left')):
        path=LIB/'grippers'/('fourier_'+side+'_hand.xml')
        tree=ET.parse(path)
        for item in tree.findall('asset/*'):
            if item.get('file'): item.set('file',str((path.parent/item.get('file')).resolve()))
            assets.append(item)
        hand=tree.find('worldbody/body')
        for item in hand.iter():
            if item.tag=='body' and item.get('name') in ('l_index','l_middle','l_ring','l_pinky'):
                item.set('name',side+'_hand_'+item.get('name'))
            if item.tag=='site' or item.get('name')=='eef':
                item.set('name',side+'_distal_eef' if item.tag=='body' else side+'_'+item.get('name','site'))
        robot.find(".//body[@name='"+side+"_eef']").append(hand)
    # Rotor inertia reflected at the joint stabilizes the sampled external torque controller.
    for joint in robot.iter('joint'):
        digit=joint.get('name','')[:1].isupper()
        joint.set('armature',str(max(float(joint.get('armature',0)),.002 if digit else .06)))
        joint.set('damping',str(max(float(joint.get('damping',0)),.08 if digit else .8)))
    for g in robot.iter('geom'):
        if g.get('group') != '1':
            g.set('group','3')
            g.set('rgba','0 0 0 0')
@lru_cache(maxsize=6)
def template(key):
    path,name=SOURCES[key]
    original=ET.parse(path).getroot()
    root=ET.Element('mujoco',model='hard1044_'+key)
    add(root,'compiler',angle='radian',autolimits='true',fusestatic='false')
    add(root,'option',timestep=.0025,integrator='implicitfast',iterations=65,gravity=[0,0,-9.81])
    vis=add(root,'visual');add(vis,'global',offwidth=1280,offheight=720)
    defaults=original.find('default')
    if defaults is not None: root.append(defaults)
    asset=add(root,'asset')
    world=add(root,'worldbody')
    robot=original.find("worldbody/body[@name='"+name+"']")
    if key=='gr1': gr1(robot,asset)
    if key=='baxter':
        hand=ET.parse(LIB/'grippers/rethink_gripper.xml')
        for side in ('left','right'):
            for j in hand.findall('.//joint[@type="slide"]'):
                joint=robot.find(".//joint[@name='"+side+"_"+j.get('name')+"']")
                if joint is not None: joint.set('range',j.get('range'))
    if key=='husky':
        robot.set('pos','0 0 .14523')
        for el in robot.iter():
            for attr in ('euler','axisangle'):
                if el.get(attr):
                    a=np.fromstring(el.get(attr),sep=' ');a[-(3 if attr=='euler' else 1):]*=np.pi/180;el.set(attr,string(a))
    world.append(robot)
    if key=='panda':
        geom(world,'robot_pedestal','cylinder',[0,0,.389],[.117,.389],(.24,.28,.31,1))
        geom(world,'pedestal_foot','box',[0,0,.025],[.165,.165,.025],(.18,.21,.24,1))
    # Retain only assets referenced by the robot or its MJCF defaults (including material textures).
    candidates=original.findall('asset/*')
    refs={v for el in robot.iter() for v in el.attrib.values()}
    if defaults is not None: refs.update(v for el in defaults.iter() for v in el.attrib.values())
    for elem in candidates:
        if elem.tag=='material' and elem.get('name') in refs and elem.get('texture'):refs.add(elem.get('texture'))
    for elem in candidates:
        if elem.get('name') not in refs:continue
        if elem.get('file'):elem.set('file',str((path.parent/elem.get('file')).resolve()))
        asset.append(elem)
    contact=add(root,'contact')
    bodies={e.get('name') for e in robot.iter('body')}
    for item in original.findall('contact/exclude'):
        if item.get('body1') in bodies and item.get('body2') in bodies:contact.append(item)
    add(root,'equality')
    add(root,'actuator')
    return ET.tostring(root)
def make(key):return ET.fromstring(template(key))

def arm(m,key,side='right'):
    if key in ('panda','omron'):
        names=['joint'+str(j) for j in range(1,8)];site='tcp'
    elif key=='baxter':
        names=[side+'_'+j for j in ('s0','s1','e0','e1','w0','w1','w2')];site=side+'_tcp'
    elif key=='gr1':
        names=[side[0]+'_'+j for j in ('shoulder_pitch','shoulder_roll','shoulder_yaw','elbow_pitch','wrist_yaw','wrist_roll','wrist_pitch')];site=side+'_grip_site'
    elif key=='spot':
        names=['arm_'+j for j in ('sh0','sh1','el0','el1','wr0','wr1')];site='grip_site'
    else:raise ValueError(key)
    return [m.joint(n).id for n in names],site
def home(m,d,key):
    if key in ('omron','panda','baxter','gr1','spot'):
        for side in (('right','left') if key in ('baxter','gr1') else ('right',)):
            ids,_=arm(m,key,side)
            q={'panda':[0,-.50,0,-2.05,0,1.69,.78],'omron':[0,-.45,0,-2.08,0,1.67,.78],
               'spot':[0,-1.2,1.85,0,-.65,0],'baxter':[-.16,-.85,1.65,2.34,-.85,1.05,1.2] if side=='right' else [.16,-.85,-1.65,2.34,.85,1.05,-1.2],
               'gr1':[0,-.1 if side=='right' else .1,0,-1.57,0,0,0]}[key]
            d.qpos[m.jnt_qposadr[ids]]=q
    if key=='spot':
        for leg in ('fr','fl','hr','hl'):
            for axis,q in zip(('hx','hy','kn'),(0,.79,-1.52)):d.joint(leg+'_'+axis+'_leg_joint').qpos[0]=q
        d.joint('arm_f1x').qpos[0]=-.14
    if key in ('panda','omron'):d.qpos[[m.joint('finger_joint1').qposadr[0],m.joint('finger_joint2').qposadr[0]]]=[.027,-.027]
    mj.mj_forward(m,d)
def target(m,d,name):
    site=mj.mj_name2id(m,mj.mjtObj.mjOBJ_SITE,name)
    return (d.site_xpos[site] if site>=0 else d.body(name).xpos).copy()
def ik(m,d,ids,site,xyz,orientation=None):
    from production.robotics import solve
    return np.asarray(solve(m,d,site,ids,np.asarray(xyz,float),orientation=orientation),float)
def servo(m,d,jids,goal,kp=250,kd=28):
    ids=np.atleast_1d(jids).astype(int);v=m.jnt_dofadr[ids];q=m.jnt_qposadr[ids]
    # Implicit derivative stabilization for small inertias.
    jdiag=m.dof_M0[v].clip(.0001)
    scale=1+(kd*m.opt.timestep+kp*m.opt.timestep**2)/jdiag
    d.qfrc_applied[v]=d.qfrc_bias[v]+(kp*(goal-d.qpos[q])-kd*d.qvel[v])/scale
@lru_cache(maxsize=64)
def robot_joints(m):
    names=[n for _,n in SOURCES.values()]
    rid=next((mj.mj_name2id(m,mj.mjtObj.mjOBJ_BODY,n) for n in names if mj.mj_name2id(m,mj.mjtObj.mjOBJ_BODY,n)>=0),None)
    def inside(i):
        while i:
            if i==rid:return True
            i=m.body_parentid[i]
        return False
    return tuple(j for j in range(m.njnt) if inside(m.jnt_bodyid[j]) and m.jnt_type[j] in (2,3) and not any(s in m.joint(j).name.lower() for s in ('finger','thumb','index','middle','ring','pinky','arm_f1x','wheel')))
def hold(m,d,reference_qpos,exclude=()):
    ids=[j for j in robot_joints(m) if j not in exclude]
    if ids:servo(m,d,ids,reference_qpos[m.jnt_qposadr[ids]],kp=400,kd=32)
def jaw(m,d,key,closure,side='right'):
    f=float(np.clip(closure,0,1))
    if key in ('panda','omron'):names=['finger_joint1','finger_joint2']
    elif key=='baxter':names=[side+'_l_finger_joint',side+'_r_finger_joint']
    elif key=='spot':names=['arm_f1x']
    elif key=='gr1':names=[m.joint(j).name for j in range(m.njnt) if m.joint(j).name.startswith(side[0].upper()+'_') and m.joint(j).name.endswith('joint')]
    else:return
    ids=[m.joint(n).id for n in names];lo,hi=m.jnt_range[ids].T
    if key=='spot':goal=lo*(1-f)+hi*f
    elif key=='gr1':goal=np.where(abs(lo)>abs(hi),lo,hi)*f*.78
    else:goal=np.where(abs(lo)>abs(hi),lo,hi)*(1-f)
    servo(m,d,ids,goal,kp=90 if key=='gr1' else 350,kd=3)
@lru_cache(maxsize=512)
def geom_ids(m,name):
    if name.startswith('@'):return {m.geom(name[1:]).id}
    bid=mj.mj_name2id(m,mj.mjtObj.mjOBJ_BODY,name)
    if bid<0:return {m.geom(name).id}
    family={bid}
    for i in range(bid+1,m.nbody):
        if m.body_parentid[i] in family:family.add(i)
    return set(np.flatnonzero(np.isin(m.geom_bodyid,list(family))))
def contacts(m,d,body_a,body_b):
    aa,bb=geom_ids(m,body_a),geom_ids(m,body_b)
    total=0.; wrench=np.zeros(6)
    for k in range(d.ncon):
        c=d.contact[k]
        if (c.geom1 in aa and c.geom2 in bb) or (c.geom1 in bb and c.geom2 in aa):
            mj.mj_contactForce(m,d,k,wrench);total+=max(0.,wrench[0])
    return total
