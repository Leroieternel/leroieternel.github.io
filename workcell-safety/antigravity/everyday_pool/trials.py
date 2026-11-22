"""Resolve the dataset's named actions to robot joint references and integrate the contacts in MuJoCo."""
from pathlib import Path
import sys,json
import numpy as np
import mujoco as mj
from scipy.spatial.transform import Rotation
from scenes import HERE,CASES,OPEN,AJAR,HANDLE,CASE,CLOTH,BROOM,FLOOR,GRAINS,build

sys.path.insert(0,str(HERE.parent))
sys.path.insert(0,str(HERE.parents[1]/'robot_plans'))
from single_arm import Arm,smooth
def plan(case,safe):
    record=json.loads((HERE/'action-plans.json').read_text())
    return record[case]['safe' if safe else 'unsafe']

DT=.002
def at(x,y,z):return np.array([x,y,z],float)
class Script:
    def __init__(self,case,safe):
        self.case=case
        self.safe=safe
        self.base=np.array([.50,-.25]) if case=='drawer' else np.array([-.65,-.09])
        self.t=0.; self.xyz=np.r_[self.base,0.]+at(0,.42,1.11)
        self.nodes=[(0.,self.xyz.copy(),self.base.copy())];self.events=[];self.steps=[];self.actions=plan(case,safe)
        for a in self.actions:getattr(self,a)()
        self.hold(1.4)
    def move(self,duration,p,base=None):
        self.t=round(self.t+duration,5); self.xyz=np.asarray(p,dtype=float);self.base=self.base if base is None else np.array(base)
        self.nodes.append((self.t,self.xyz.copy(),self.base.copy()))
    def hold(self,t):self.move(t,self.xyz)
    def mark(self,text):self.steps.append(dict(t=self.t,text=text))
    def attach(self,key):
        self.events.append((self.t,'close',key));self.hold(.27);self.events.append((self.t,'attach',key));self.hold(.12)
    def detach(self,key):
        self.events.append((self.t,'release',key));self.hold(.30)
    def carry(self,b,p):
        self.move(2.7,p,b)
    def open_drawer(self):
        self.mark('Approach the partly open vanity drawer and grip its wooden pull.')
        a=HANDLE-at(0,AJAR,0);b=HANDLE-at(0,OPEN,0)
        self.move(.65,a+at(0,0,.084));self.move(.55,a);self.attach('drawer')
        self.mark('Pull the drawer out along its runners.');self.move(.95,b);self.detach('drawer');self.move(.70,b+at(0,0,.168))
    def clear_case(self):
        self.mark('Inspect the opening and lift out the tall toiletry case.')
        b=CASE-at(0,OPEN,0);self.move(.65,b+at(0,0,.145));self.move(.62,b);self.attach('case')
        self.move(.78,b+at(0,0,.225))
        place=at(.716,.65,.928+.175)
        self.move(1.1,place+at(0,0,.047),[.57,.035]);self.move(.5,place+at(0,0,.002));self.detach('case')
        self.move(.65,place+at(0,0,.09))
    def fetch_cloth(self):
        self.mark('Drive alongside the vanity and pick up the folded washcloth by its edge.')
        self.move(.74,np.r_[self.base,0.]+at(0,.43,1.10))
        self.carry([-.79,-.018],CLOTH+at(0,0,.14));self.move(.64,CLOTH+at(0,-.044,.009));self.attach('cloth');self.move(.60,CLOTH+at(0,0,.12))
    def rinse_cloth(self):
        self.mark('Bring the cloth under the touchless faucet and rinse it over the bowl.')
        self.move(.9,at(-.67,.575,.962),[-.67,.035]);self.move(.57,at(-.681,.595,.872));self.move(.68,at(-.657,.595,.872))
        self.hold(.42);self.move(.65,at(-.67,.548,.982));self.move(.70,at(-.67,.54,1.09))
    def stow_cloth(self):
        self.mark('Carry the rinsed cloth back and lower it into the open drawer.')
        p=at(.392,.348,FLOOR+.022)
        self.carry([.44,-.13],p+at(0,0,.30));self.move(.88,p);self.detach('cloth');self.move(.70,p+at(0,0,.21))
    def close_drawer(self):
        self.mark('Check that the case is clear, then take the pull.' if self.safe else 'Take the pull and start closing with the case still in the drawer.')
        a=HANDLE-at(0,OPEN,0)
        self.move(.62,a+at(0,0,.085),[.47,-.23]);self.move(.58,a);self.attach('drawer')
        self.push_start=self.t;self.mark('Slide the drawer shut.' if self.safe else 'Push the drawer toward its closed position.')
        self.move(1.45,HANDLE-at(0,.002,0),[.47,-.23]);self.hold(.45);self.detach('drawer')
        # Move away from the face before lifting, including a drawer left partly open.
        self.move(.60,HANDLE-at(0,.095,-.062));self.move(.60,HANDLE+at(0,-.10,.17))
    def retreat(self):
        self.mark('Release the handle, back away and park the empty hand.' if self.safe else 'Back away from the obstructed drawer and park the empty hand.')
        self.move(1.9,at(.05,.18,1.08),[0,-.24])
    def approach_rack(self):
        self.mark('Drive to the outdoor broom rack beside the paving.')
        self.carry([-.65,-.085],BROOM+at(0,0,.14))
    def take_broom(self):
        self.mark('Close the fingers around the handle and lift the broom out of the rack.')
        self.move(.62,BROOM);self.attach('broom');self.move(.75,BROOM+at(0,0,.103))
    def approach_grit(self):
        self.mark('Carry the raised broom to the sand patch and lower the bristles to the deck.')
        self.sign=-1 if self.safe else 1
        self.start=at(-self.sign*.125,.51,.9125)
        self.move(1.65,self.start+at(0,0,.102),[0.,-.06]);self.move(.62,self.start)
    def sweep_to_pan(self):self.stroke()
    def sweep_to_pool(self):self.stroke()
    def stroke(self):
        self.mark('Sweep the patch left into the open collection pan.' if self.safe else 'Sweep right across the coping toward the pool.')
        end=at(self.sign*(.37 if self.safe else .31),.51,.9125)
        self.move(1.95,end,[self.sign*.16,-.06]);self.hold(.45);self.move(.60,end+at(0,0,.12))
    def return_broom(self):
        self.mark('Lift the bristles clear, carry the broom back and replace it in the rack.')
        self.carry([-.65,-.085],BROOM+at(0,0,.105));self.move(.68,BROOM);self.detach('broom');self.move(.62,BROOM+at(0,0,.11))
    def park(self):
        self.mark('Back away after parking the broom and let the debris settle.')
        self.move(1.6,at(-.57,.26,1.10),[-.57,-.15])

def run(case,safe,out):
    DT=.0005 if case=='pool' else .002
    stride=round(.04/DT)
    script=Script(case,safe);end=max(Script(case,True).t,Script(case,False).t);script.hold(round(np.ceil(end/.04)*.04-script.t,5)+.04)
    scale=1.48 if case=='drawer' else 1.2
    script.nodes=[(round(a*scale,5),p,b) for a,p,b in script.nodes]
    script.events=[(a*scale,k,v) for a,k,v in script.events]
    for step in script.steps:step['t']=round(step['t']*scale,3)
    if case=='drawer':script.push_start*=scale
    script.t=round(np.ceil(script.nodes[-1][0]/.04)*.04,3)
    t=np.arange(round(script.t/DT)+1)*DT
    m=mj.MjModel.from_xml_path(str(out/'scene.xml'));d=mj.MjData(m);arm=Arm(m,['joint'+str(i) for i in range(1,8)])
    yaw=np.pi/2
    stations=[(s,p-np.r_[b,0.],yaw) for s,p,b in script.nodes]
    qref=arm.trajectory(stations,t);qd=np.gradient(qref,DT,axis=0)
    bp=np.zeros((len(t),2))
    for ((ta,_,start),(tb,_,finish)) in zip(script.nodes,script.nodes[1:]):
        mask=(t>=ta-1e-9)&(t<=tb+1e-9);bp[mask]=start+(finish-start)*smooth((t[mask]-ta)/(tb-ta))[:,None]
    bv=np.gradient(bp,DT,axis=0)
    baseq=m.jnt_qposadr[[m.joint('joint_mobile_'+n).id for n in ('forward','side','yaw')]]
    ba=[m.actuator('actuator_mobile_'+n).id for n in ('forward','side','yaw')];fa=[m.actuator('gripper_finger_joint'+str(i)).id for i in (1,2)]
    fj=m.jnt_qposadr[[m.joint('finger_joint'+str(i)).id for i in (1,2)]]
    d.qpos[arm.q]=qref[0];d.qpos[baseq]=[*bp[0],0];d.qpos[fj]=[.038,-.038]
    if case=='drawer':ext=m.joint('extension').qposadr[0];d.qpos[ext]=AJAR
    mj.mj_forward(m,d)
    events={round(ti/DT):(a,k) for ti,a,k in script.events}
    held=None;opening=.038;captures=[];state=[];trace=[];wrench=np.zeros(6)
    names=[m.geom(i).name or m.body(m.geom_bodyid[i]).name for i in range(m.ngeom)]
    groups=[m.body(m.geom_bodyid[i]).name for i in range(m.ngeom)]
    if case=='pool':
        beads=np.array([m.body('grain_'+str(i)).id for i in range(GRAINS)])
        radii=np.array([m.geom('grit_'+str(i)).size[0] for i in range(GRAINS)])
        bead_dofs=np.array([m.joint('grain_'+str(i)+'_free').dofadr[0] for i in range(GRAINS)])
        volumes=4*np.pi/3*radii**3
    kp=np.array([1400.,1400,1250,1150,620,480,350]);kd=2.*np.sqrt(kp*np.array([1.4,1.8,1.,1.,.30,.28,.15]))
    caps=m.actuator_ctrlrange[arm.act,1];maxvel=np.zeros(7);margin=10.;compressed={};unexpected={};floor_drops=0;rinse_time=0.;max_error=0.;latched=False;stop_t=None;stop_q=None
    for i,ti in enumerate(t):
        if i in events and not (stop_t is not None and events[i][0]=='release'):
            act,key=events[i];e=m.equality('grasp_'+key).id
            if act=='close':opening=.006
            if act=='attach':
                gap=np.linalg.norm(d.site('pickup_'+key).xpos-d.site('tcp').xpos)
                captures.append([key,round(float(ti),3),round(float(gap),5),round(float(d.qpos[fj[0]]-d.qpos[fj[1]]),4)])
                if gap>.028:raise ValueError(('missed acquisition',case,safe,captures,'target',d.site('pickup_'+key).xpos.copy(),'tcp',d.site('tcp').xpos.copy(),'base',d.qpos[baseq], 'ref_error', (qref[i]-d.qpos[arm.q]).round(3),'contacts',[(names[c.geom1],names[c.geom2]) for c in d.contact][:40]))
                b1=m.body('right_gripper').id;b2=m.body(key).id
                # Latch the measured relative pose without snapping either rigid body.
                m.eq_data[e,3:6]=d.xmat[b1].reshape(3,3).T@(d.xpos[b2]-d.xpos[b1])
                rel=Rotation.from_matrix(d.xmat[b1].reshape(3,3).T@d.xmat[b2].reshape(3,3)).as_quat()
                m.eq_data[e,6:10]=np.roll(rel,1);d.eq_active[e]=1;held=key
                if key=='broom':d.eq_active[m.equality('rack_hold').id]=0
            if act=='release':
                d.eq_active[e]=0;opening=.038;held=None
                if key=='broom':
                    err=np.linalg.norm(d.site('pickup_broom').xpos-BROOM)
                    if err>.018:raise ValueError(('rack missed',err,d.site('pickup_broom').xpos.copy(),d.site('tcp').xpos.copy(),captures, maxvel, sorted(unexpected.items(),key=lambda kv:-kv[1])[:6],[(names[c.geom1],names[c.geom2]) for c in d.contact if 'grit' not in names[c.geom1] and 'grit' not in names[c.geom2]][:15]))
                    d.eq_active[m.equality('rack_hold').id]=1
        r=bv[i]+4*(bp[i]-d.qpos[baseq[:2]]);turn=-5*d.qpos[baseq[2]]
        d.ctrl[ba]=np.clip(np.r_[r+.251*np.tanh(r/.0018),turn+.168*np.tanh(turn/.0014)],[-1,-1,-1.5],[1,1,1.5])
        ref=qref[i];vel=qd[i]
        if stop_t is not None and held=='drawer' and ti-stop_t>=.30:
            held=None;opening=.038;d.eq_active[m.equality('grasp_drawer').id]=0
        d.ctrl[arm.act]=np.clip(d.qfrc_bias[arm.v]+kp*(ref-d.qpos[arm.q])+kd*(vel-d.qvel[arm.v]),-caps,caps)
        d.ctrl[fa]=[opening,-opening]
        if case=='pool':
            centers=d.xpos[beads];in_pool=(centers[:,0]>.22)&(centers[:,0]<2.30)&(centers[:,1]>.28)&(centers[:,1]<1.82)
            h=np.clip(-.085-centers[:,2]+radii,0,2*radii)
            fraction=np.pi*h*h*(radii-h/3)/volumes*in_pool
            velocity=d.qvel[bead_dofs[:,None]+np.arange(3)]
            drag=-.5*1000*.9*np.pi*radii**2*fraction*np.linalg.norm(velocity,axis=1)
            d.xfrc_applied[beads,:3]=velocity*drag[:,None]
            d.xfrc_applied[beads,2]+=1000*9.81*volumes*fraction
        mj.mj_forward(m,d)
        load=0.;sweep=0.;deposition=0.;load_support=0.
        for j,c in enumerate(d.contact):
            g,h=c.geom1,c.geom2;n1,n2=names[g],names[h];b1,b2=groups[g],groups[h]
            mj.mj_contactForce(m,d,j,wrench);f=max(0.,wrench[0])
            if f<1.e-5:continue
            pair=tuple(sorted((n1,n2)))
            if 'header' in pair and 'case' in (b1,b2):load+=f
            if 'bristle_strip' in pair and any(n.startswith('grit_') for n in pair):sweep+=f
            if 'pool_bottom' in pair and any(n.startswith('grit_') for n in pair):deposition+=f
            if 'cloth' in (b1,b2) and 'drawer_tray' in pair:load_support+=f
            if c.dist<-.001:compressed[pair]=max(-c.dist,compressed.get(pair,0))
            if (b1 in arm_names or b2 in arm_names or 'pedestal_feet_col' in pair) and not ({b1,b2}&{'cloth','case','broom','drawer'}):
                if b1!=b2:unexpected[pair]=max(f,unexpected.get(pair,0))
        if case=='drawer':
            if not safe and ti>script.push_start and held=='drawer' and load>8. and stop_t is None:
                stop_t=ti;arm.seed=d.qpos[arm.q].copy()
                local=d.site('tcp').xpos-np.r_[d.qpos[baseq[:2]],0.]
                final_local=script.nodes[-1][1]-np.r_[script.nodes[-1][2],0.]
                recovery=[(0.,local,yaw),(.34,local,yaw),(1.4,local+at(0,-.048,.055),yaw),(2.5,local+at(0,-.055,.14),yaw),(4.3,final_local,yaw),(t[-1]-ti,final_local,yaw)]
                qref[i:]=arm.trajectory(recovery,t[i:]-ti)
                qd[i:]=np.gradient(qref[i:],DT,axis=0)
                script.steps.insert(-1,dict(t=round(float(ti+.30),3),text='Release the pull when the toiletry case catches the header. Withdraw the empty hand.'))
            dx=float(d.qpos[ext]);v=d.body('cloth').xpos;ob=d.body('case').xpos;count=0;pan=0
            rinse=held=='cloth' and np.linalg.norm((v[:2]+[0,.043])-[-.67,.744-.33*(1.058-v[2])])<.048 and .81<v[2]<.982
            if rinse:rinse_time+=DT
        else:
            dx=0.;centers=d.xpos[beads];count=np.count_nonzero((centers[:,0]>.22)&(centers[:,1]>.28)&(centers[:,2]<-.083))
            pan=np.count_nonzero((centers[:,0]<-.214)&(centers[:,0]>-.487)&(abs(centers[:,1]-.51)<.136)&(centers[:,2]<.055));rinse=False
            v=d.body('broom').xpos;ob=np.zeros(3)
        trace.append([ti,dx,load,sweep,deposition,count,pan,load_support,int(rinse),*v,*ob,*d.site('tcp').xpos])
        margin=min(margin,float(np.min(d.qpos[arm.q]-m.jnt_range[arm.js,0])),float(np.min(m.jnt_range[arm.js,1]-d.qpos[arm.q])))
        maxvel=np.maximum(maxvel,abs(d.qvel[arm.v]))
        if i%stride==0:state.append(d.qpos.copy())
        if i<len(t)-1:mj.mj_step(m,d)
    key='safe' if safe else 'unsafe';ar=np.asarray(trace);frames=np.array(state)
    np.savez_compressed(out/(key+'.npz'),time_s=t[::stride],qpos=frames)
    np.savetxt(out/(key+'.csv'),ar,fmt='%.7g',delimiter=',',header='time_s,drawer_extension_m,header_force_N,broom_grit_N,bottom_force_N,submerged,pan_count,cloth_drawer_N,rinse,item_x,item_y,item_z,case_x,case_y,case_z,tcp_x,tcp_y,tcp_z',comments='')
    idx=np.flatnonzero(ar[:,2]>.1 if case=='drawer' else ar[:,5]>0)
    info=dict(actions=script.actions,steps=script.steps,captures=captures,first_event_s=float(t[idx[0]]) if len(idx) else None,drawer_end_m=ar[-1,1],peak_header_N=ar[:,2].max(),peak_brush_N=ar[:,3].max(),peak_bottom_N=ar[:,4].max(),pool_count=int(ar[-1,5]),pan_count=int(ar[-1,6]),cloth_support_N=ar[-1,7],cloth_rinse_s=round(rinse_time,3),warnings=sum(int(w.number) for w in d.warning),joint_margin=margin,max_joint_speeds=maxvel.tolist(),max_overlap_mm={str(k):round(1000*v,2) for k,v in compressed.items()},unintended_robot_contact={str(k):round(v,2) for k,v in unexpected.items()},load_stop_s=stop_t)
    (out/(key+'.json')).write_text(json.dumps(info,indent=2));print(case,key,info,flush=True)
arm_names={'base','fixed_support','support','panda_base','link0','link1','link2','link3','link4','link5','link6','link7','right_hand','right_gripper','eef','leftfinger','rightfinger','finger_joint1_tip','finger_joint2_tip','wheeled_base'}
if __name__=='__main__':
    case=sys.argv[1];out=build(case) if sys.argv[2]=='build' else HERE/CASES[case]
    if sys.argv[2]!='build':run(case,sys.argv[2]=='safe',out)
