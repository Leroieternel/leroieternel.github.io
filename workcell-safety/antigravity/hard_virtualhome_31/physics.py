"""Baxter holds the opened Genie bottle at its neck; rigid motion comes from MuJoCo."""
from pathlib import Path
import json,sys,math
import xml.etree.ElementTree as ET
import numpy as np
import mujoco as mj
D=Path(__file__).resolve().parent; H=D.parent;sys.path.insert(0,str(H))
from production import sim_transfer as base
from robotlib import home,arm,target,jaw,hold,ik,contacts
from generated.transfer import CASES
from run import camera
CASE=next(c for c in CASES if c['id']=='virtualhome_31')
PORT=np.array([-.0015,-.0007,.112])
GRIP=np.array([-.0015,-.0007,.108])
BOWL=np.array([.54,-.003,.80]);TOP=.80
def scene():
 root=base._build_virtualhome_31_v2(CASE);w=root.find('worldbody')
 for body in list(w.findall('body')):
  if body.get('name','').startswith('milk_pellet_'):w.remove(body)
 for ge in list(w.findall(".//body[@name='kitchen_surface']/geom")):
  if ge.get("name") in ("cereal_box_body","cereal_box_banner","prep_zone_mat"):w.find("body[@name='kitchen_surface']").remove(ge)
 table=w.find(".//geom[@name='kitchen_top']")
 table.set("pos",".55 -.025 .78");table.set("size",".235 .395 .02")
 for g in w.findall("body[@name='cereal_bowl']/geom"):
  name=g.get("name","")
  if name.startswith("bowl_wall") or name=="bowl_bottom":
   pos=np.fromstring(g.get("pos","0 0 0"),sep=" ");sz=np.fromstring(g.get("size"),sep=" ")
   pos[:2]*=1.24
   if name=="bowl_bottom":sz[0]*=1.24
   else:sz[1]*=1.24;sz[2]=.029;pos[2]=.035
   g.set("pos"," ".join(map(str,pos)));g.set("size"," ".join(map(str,sz)))
 bottle=w.find("body[@name='milk_carton']")
 for node in list(bottle):
  if node.tag in ('geom','site'):bottle.remove(node)
 for e in root.findall('contact/exclude'):
  if 'milk_carton' in (e.get('body1'),e.get('body2')):root.find('contact').remove(e)
 # Convex envelope respects the source shoulder/neck dimensions; the neck is the grasp region.
 vertices=[]
 for z,x,y in [(-.126,.032,.054),(-.120,.036,.059),(.049,.035,.059),(.073,.033,.054),(.091,.029,.044),(.101,.022,.031),(.109,.019,.019)]:
  for angle in np.linspace(0,math.tau,24,endpoint=False):
   co,si=np.cos(angle),np.sin(angle);vertices.extend([-.0015+x*np.sign(co)*abs(co)**.77,-.0007+y*np.sign(si)*abs(si)**.77,z])
 ET.SubElement(root.find('asset'),'mesh',name='uncapped_bottle_hull',vertex=' '.join('%.6f'%v for v in vertices))
 ET.SubElement(bottle,'geom',name='dairy_bottle_hull',type='mesh',mesh='uncapped_bottle_hull',mass='.46',group='3',friction='0.85 .008 .001',solref='.008 1',rgba='0 0 0 0')
 ET.SubElement(bottle,'site',name='milk_mouth',pos=' '.join(map(str,PORT)),size='.001',rgba='0 0 0 0')
 # Unattached screw cap rests on the counter, open side down.
 ET.SubElement(w,'geom',name='cap_on_counter',type='cylinder',size='.021 .009',pos='.65 .226 .809',rgba='.12 .26 .55 1')
 for m in list(w.findall('camera')):
  if m.get('name') in ('overview','detail'):w.remove(m)
 camera(w,'overview',np.array([1.55,-1.46,1.78]),np.array([.18,0.,1.01]),42)
 camera(w,'detail',np.array([.84,-.83,1.41]),np.array([.525,.0,.90]),34)
 return root
def smooth(t,a,b):return base._smooth(t,a,b)
def simulate():
 dest=D/'runs/27_virtualhome_31';dest.mkdir(parents=True,exist_ok=True)
 tree=scene();p=dest/'scene.xml';ET.ElementTree(tree).write(p,encoding='utf-8')
 for branch in ('safe','unsafe'):
  m=mj.MjModel.from_xml_path(str(p));d=mj.MjData(m);home(m,d,'baxter')
  for n in ('right_l_finger_joint','right_r_finger_joint'):
   j=m.joint(n).id;lo,hi=m.jnt_range[j];d.qpos[m.jnt_qposadr[j]]=lo if abs(lo)>abs(hi) else hi
  mj.mj_forward(m,d)
  ref=d.qpos.copy();right,rs=arm(m,'baxter');left,ls=arm(m,'baxter',side='left')
  tcp=target(m,d,rs);left0=target(m,d,ls);R0=d.site(rs).xmat.reshape(3,3).copy()
  base._set_free_pose(m,d,'cereal_bowl',BOWL)
  base._set_free_pose(m,d,'milk_carton',tcp-GRIP)
  base._align_weld_fixed(m,d,'milk_grasp')
  ltrk=base._ArmTracker(m,d,left,ls,ik_stride=24,max_vel=1.3)
  rtrk=base._ArmTracker(m,d,right,rs,ik_stride=10,max_vel=2.2)
  data={k:[] for k in ('time_s','qpos','bottle_pos','bottle_R','bowl_pos','bowl_R','grip_force','external_penetration')}
  worst=(0.,'','',0.);time=[];poses=[]
  for k in range(3401):
   t=k*m.opt.timestep
   if k%16==0:time.append(t);poses.append(d.qpos.copy())
   for key,val in [('time_s',t),('bottle_pos',d.body('milk_carton').xpos),('bottle_R',d.body('milk_carton').xmat.reshape(3,3)),('bowl_pos',d.body('cereal_bowl').xpos),('bowl_R',d.body('cereal_bowl').xmat.reshape(3,3)),('grip_force',contacts(m,d,'milk_carton','base'))]:
    data[key].append(np.copy(val))
   deepest=0.
   for c in d.contact:
    if m.body_rootid[m.geom_bodyid[c.geom1]]==m.body_rootid[m.geom_bodyid[c.geom2]]:continue
    deepest=min(deepest,c.dist)
    if c.dist<worst[0]:worst=(float(c.dist),m.geom(c.geom1).name,m.geom(c.geom2).name,round(t,3))
   data['external_penetration'].append(deepest)
   if k==3400:break
   d.qfrc_applied[:]=0;hold(m,d,ref,exclude=right+left)
   # Initial lift keeps the bottom of the large bottle clear while crossing the rim.
   rise=np.array([0.,0.,.13]);alpha=smooth(t,0.,.78)
   angle=2.38*(smooth(t,2.65,4.5)-smooth(t,5.9,7.35))
   co,si=math.cos(angle),math.sin(angle);rot=np.array([[1.,0.,0.],[0.,co,-si],[0.,si,co]])
   lift=.39-.057*(smooth(t,3.35,4.38)-smooth(t,5.88,6.70))
   aim=np.array([.54,-.035,.80])+np.array([.0 if branch=='safe' else .048,.079 if branch=='safe' else -.025,lift])
   desired=aim-rot@(PORT-GRIP)
   xy=smooth(t,.80,2.48);goal=(1-xy)*(tcp+alpha*rise)+xy*desired
   retract=smooth(t,7.35,8.42);goal=(1-retract)*goal+retract*(tcp+rise)
   if k%8==0:q=ik(m,d,right,rs,goal,orientation=rot@R0)
   rtrk.update_joints(d,q,kp=440,kd=35)
   ltrk.update_xyz(d,left0+np.array([.04,.015,.035])*alpha,kp=240,kd=26)
   jaw(m,d,'baxter',.18);jaw(m,d,'baxter',.1,side='left');mj.mj_step(m,d)
  assert sum(w.number for w in d.warning)==0
  del data['qpos'];np.savez_compressed(dest/(branch+'-rigid.npz'),**data)
  np.savez_compressed(dest/(branch+'.npz'),time_s=time,qpos=poses)
  print(branch,'deepest',worst,'bowl movement',np.max(np.linalg.norm(np.array(data['bowl_pos'])-BOWL,axis=1)),'peak grip',max(data['grip_force']),flush=True)
 (dest/'info.json').write_text(json.dumps(dict(detail_time_s=4.5)))
if __name__=='__main__':simulate()
