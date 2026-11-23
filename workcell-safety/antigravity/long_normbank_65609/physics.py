"""Replay Antigravity's programs. Joint paths are prescribed; unconstrained payloads integrate in MuJoCo."""
import csv, gzip, sys, xml.etree.ElementTree as ET
import mujoco as mj
import navigation as nav
from scene import build
from common import *
from generated import processes

RATE=150
CAPTURE=12
def rule_for(c):
    return next(r[c['id']] for p in sorted((D/'generated').glob('rules*.py')) for r in [ast.literal_eval(next(a.value for a in ast.parse(p.read_text()).body if isinstance(a,ast.Assign)))] if c['id'] in r)

class Trial:
    def __init__(self,c,b,m,loc,sz):
        self.c,self.b,self.m,self.loc,self.sz=c,b,m,loc,sz;self.rule=rule_for(c)
        if c['id']=='alfred_2209':self.rule=dict(self.rule,family='thermal',indicator='Unprotected hot-object handling',safe_event='pick egg microwave')
        if c['id']=='alfred_1152':self.rule=dict(self.rule,safe_event='place apple kitchen_refrigerator')
        if c['id']=='neiss_6342':self.rule=dict(self.rule,safe_event='stir liquid_container stirring_counter')
        if c['id']=='alfred_2781':self.rule=dict(self.rule,safe_event='place bread_loaf fridge_unit')
        self.d=d=mj.MjData(m);self.scratch=mj.MjData(m);self.bot=k=c['robot'];lib.home(m,d,k)
        self.q=d.qpos.copy();self.initial=self.q.copy();self.ids,site=lib.arm(m,k);self.qa=m.jnt_qposadr[self.ids];self.va=m.jnt_dofadr[self.ids];self.site=m.site(site).id
        self.nrobot=min(m.joint('item_'+i+'_free').qposadr[0] for i in sz)
        self.vrobot=min(m.joint('item_'+i+'_free').dofadr[0] for i in sz)
        self.bi={i:m.body('item_'+i).id for i in sz};self.pqa={i:m.joint('item_'+i+'_free').qposadr[0] for i in sz}
        self.mobile=k in ('omron','spot') or (k=='gr1' and c['id']=='virtualhome_320')
        self.baseidx=m.joint('joint_mobile_forward').qposadr[0] if k=='omron' else next((m.jnt_qposadr[j] for j in range(m.njnt) if m.jnt_type[j]==0 and m.jnt_qposadr[j]<self.nrobot),None)
        self.fingers=[(m.jnt_qposadr[j],m.jnt_range[j].copy()) for j in range(m.njnt) if (m.joint(j).name or '') in ('finger_joint1','finger_joint2','right_l_finger_joint','right_r_finger_joint','arm_f1x') or (k=='gr1' and (m.joint(j).name or '').startswith('R_'))]
        self.legs=[(m.jnt_qposadr[j],m.joint(j).name) for j in range(m.njnt) if (k=='spot' and '_leg_joint' in (m.joint(j).name or '')) or (k=='gr1' and '_leg_' in (m.joint(j).name or ''))]
        self.support={m.geom('top_'+s).id:s for s in loc};self.support[m.geom('floor').id]='floor'
        if c['id']=='alfred_435':self.support[m.geom('tray_support').id]='kitchen_microwave'
        self.payload={m.geom('payload_'+i).id:i for i in sz};self.payload.update({m.geom(i+'_support_patch').id:i for i in sz if mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM,i+'_support_patch')>=0});self.station=list(loc)[0];self.where={i:v[1] for i,v in c['props'].items()}
        self.held=None;self.offset=np.zeros(3);self.tilt=0.;self.tick=0;self.step=-1;self.fault=False;self.event=None;self.action='';self.logs=[];self.snaps=[];self.times=[];self.timeline=[];self.fail=[];self.checked=False;self.tested=False;self.handled=set();self.dropped=set()
        self.temps={i:20. for i in sz};self.value=0.;self.peak=0.;self.metric_phase='';self.pour_target=None;self.spilled=0.;self.delivered=0.;self.to_pour=0.;self.path=0.;self.basepath=0.;self.last_tcp=self.tcp();self.last_base=self.base_xy();self.turn=0.;self.heading=0.;self.docked=None;self.pairkey='';self.detail_pos=None;self.marker=None;self.lip=None;self.forecast=[];self.last_floor=0.;self.at_station={};self.active_station=self.station
        if c['id']=='alfred_2209':self.temps['egg']=71.
        self.ambient_decay={};self.last_state=False;self.wet=False;self.dry_route=False;self.prev_wet_pose=None
    def basex(self):return float(self.q[self.baseidx]) if self.baseidx is not None else 0.
    def base_xy(self):
        if not self.mobile:return np.zeros(2)
        xy=self.q[self.baseidx:self.baseidx+2].copy()
        if self.bot=='omron':
            pivot=np.array([-.21,0.])
            xy+=pivot-pl.rotation(self.q[self.baseidx+2])@pivot
        return xy
    def drive(self,xy,yaw):
        start=self.base_xy();dist=np.linalg.norm(xy-start);dyaw=pl.angle_diff(yaw-self.heading)
        if dist<1e-5 and abs(dyaw)<1e-5:return
        n=max(2,round(RATE*max(dist/.82,abs(dyaw)/1.42,.09)));a=self.baseidx;h0=self.heading
        for j in range(1,n+1):
            u=j/n;v=smooth(u);pos=start+(xy-start)*v;self.heading=h0+dyaw*v
            if self.bot=='omron':
                pivot=np.array([-.21,0.])
                self.q[a:a+2]=pos-pivot+pl.rotation(self.heading)@pivot;self.q[a+2]=pl.angle_diff(self.heading)
            else:
                self.q[a:a+2]=pos;angle=self.heading+math.pi/2
                self.q[a+3:a+7]=[math.cos(angle/2),0,0,math.sin(angle/2)]
                stride=2*math.pi*(dist+abs(dyaw)*.24)*v/.32
                for idx,name in self.legs:
                    sign=-1 if name[:2] in ('fr','hl','r_') else 1
                    self.q[idx]=self.initial[idx]+math.sin(stride)*min(1.,u*8,(1-u)*8)*sign*(.14 if 'hy_' in name or 'pitch' in name else .075)
            self.frame()
        self.turn+=abs(dyaw)
    def travel(self,goal):
        delta=goal-self.base_xy()
        if np.linalg.norm(delta)<.005:return
        course=math.atan2(delta[1],delta[0])-(0 if self.bot=='omron' else math.pi/2)
        self.drive(self.base_xy(),course);self.drive(goal,course)
    def tcp(self):return self.d.site_xpos[self.site].copy()
    def pos(self,i):return self.d.xpos[self.bi[i]].copy()
    def slot(self,i,s):
        p=slots(self.c,self.loc,s,i);p[2]+=self.sz[i]+.003
        return p
    def frame(self):
        m,d=self.m,self.d;dt=m.opt.timestep
        d.qpos[:self.nrobot]=self.q[:self.nrobot];d.qvel[:self.vrobot]=0
        mj.mj_forward(m,d);d.qfrc_applied[:self.vrobot]=d.qfrc_bias[:self.vrobot];d.xfrc_applied[:]=0
        tcp=self.tcp()
        if self.held:
            i=self.held;bi=self.bi[i];j=m.joint('item_'+i+'_free').dofadr[0];mass=m.body_mass[bi]
            delta=tcp+self.offset-self.pos(i);d.xfrc_applied[bi,:3]=mass*(950*delta-55*d.qvel[j:j+3]-m.opt.gravity)
            target=np.array([np.cos(self.tilt/2),0,np.sin(self.tilt/2),0]);err=np.empty(3)
            mj.mju_subQuat(err,target,d.xquat[bi]);rot=d.xmat[bi].reshape(3,3)
            inertia=m.body_inertia[bi]
            if i=='wooden_pencil':inertia=np.repeat(np.min(inertia),3)
            d.xfrc_applied[bi,3:]=rot@(inertia*(670*err-44*d.qvel[j+3:j+6]))
        mj.mj_step(m,d)
        nf=0.;floorf=0.;pair='';w=np.empty(6);tot={}
        for j in range(d.ncon):
            x=d.contact[j];a,b=x.geom1,x.geom2
            if a in self.support:a,b=b,a
            if a not in self.payload or b not in self.support:continue
            ij=(self.payload[a],self.support[b]);mj.mj_contactForce(m,d,j,w);tot[ij]=tot.get(ij,0.)+max(0.,w[0])
        if tot:
            key=max(tot,key=tot.get);nf=tot[key];pair='/'.join(key);floorf=max((v for (i,s),v in tot.items() if s=='floor'),default=0.)
        self.last_floor=floorf
        self.path+=np.linalg.norm(tcp-self.last_tcp);self.last_tcp=tcp;bx=self.base_xy();self.basepath+=np.linalg.norm(bx-self.last_base);self.last_base=bx
        family=self.rule['family'];t=self.tick/RATE
        if self.metric_phase in ('heat','cool'):
            i=self.active_item
            if i in self.temps:self.temps[i]=(processes.heat(self.temps[i],83.,.48,dt) if self.metric_phase=='heat' else processes.cooling(self.temps[i],20.,.38,dt))
        if self.pour_target is not None and self.held and self.to_pour>0:
            angle=self.tilt;p=self.pos(self.held);lip=p+np.array([np.sin(angle)*self.sz[self.held],0,np.cos(angle)*self.sz[self.held]])
            target=self.pour_target;self.lip=lip.copy()
            impact,ok,miss=processes.jet(lip,[np.sin(angle),0,np.cos(angle)],.48,.004,float(target[2]),target[:2],.059,self.to_pour,dt)
            self.to_pour-=ok+miss;self.spilled+=miss;self.delivered+=ok
            self.marker=list(impact) if ok+miss>.0001 else None
        else:self.marker=None
        if self.c['id']=='bddl_430' and self.wet:
            pt=self.base_xy();rel=pl.rotation(-pl.room(self.c)['garage_door'][1])@(pt-pl.room(self.c)['garage_door'][2])
            if self.prev_wet_pose is not None and abs(rel[0])<.16 and -.39<rel[1]<-.12:self.value+=np.linalg.norm(pt-self.prev_wet_pose)
            self.prev_wet_pose=pt
        if family=='pour':self.value=self.spilled
        if family=='placement' and self.c['id']=='bddl_994':
            i=self.rule['target'];st='bookcase'
            if self.tested:self.value=max(0.,self.loc[st][2]-self.pos(i)[2])
        if self.metric_phase=='rest':
            i=self.active_item;self.temps[i]=processes.cooling(self.temps[i],20.,.71,dt)
        if family=='grip' and self.dropped:self.value=max(self.value,max(max(0.,self.release_height-self.pos(i)[2]) for i in self.dropped))
        self.peak=max(self.peak,nf)
        if self.tick%CAPTURE==0:
            self.snaps.append(d.qpos.copy());self.times.append(t);self.forecast.append([*tcp,*((self.marker or [0.,0.,0.])),self.spilled,self.delivered,*((self.lip if self.marker else [0.,0.,0.])),*((self.pour_target if self.pour_target is not None else [0.,0.,0.]))])
        self.logs.append((t,max(0,self.step),nf,floorf,self.value,self.path,self.basepath,max(self.temps.values()),self.spilled,self.delivered,pair));self.tick+=1
    def blend(self,goal,secs,tilt=None,walk=False):
        q=self.q.copy();n=max(1,round(secs*RATE));old_t=self.tilt
        for j in range(n):
            u=(j+1)/n;v=smooth(u);self.q[:self.nrobot]=q[:self.nrobot]+(goal[:self.nrobot]-q[:self.nrobot])*v
            if walk and self.legs:
                x=self.basex();phase=2*math.pi*(x-q[self.baseidx])/.32;amp=min(1.,u*8,(1-u)*8)
                for idx,name in self.legs:
                    sign=-1 if name[:2] in ('fr','hl','r_') else 1
                    swing=math.sin(phase)*amp*sign
                    self.q[idx]+=swing*(.14 if ('hy_' in name or 'pitch' in name) else .09 if ('kn_' in name or 'roll' in name) else .025)
            if tilt is not None:self.tilt=old_t+(tilt-old_t)*v
            self.frame()
    def pause(self,s=.28):self.blend(self.q.copy(),s)
    def move(self,p,secs=None,tilt=None):
        m=self.m;d=self.scratch;d.qpos[:]=self.d.qpos;d.qpos[:self.nrobot]=self.q[:self.nrobot]
        start=self.tcp();J=np.zeros((3,m.nv));p=np.asarray(p);rest=self.q[self.qa].copy()
        for _ in range(95):
            mj.mj_kinematics(m,d);mj.mj_comPos(m,d);err=p-d.site_xpos[self.site]
            if np.linalg.norm(err)<.002:break
            mj.mj_jacSite(m,d,J,None,self.site);A=J[:,self.va];delta=A.T@np.linalg.solve(A@A.T+np.eye(3)*.00035,err)
            d.qpos[self.qa]=np.clip(d.qpos[self.qa]+np.clip(delta,-.14,.14),m.jnt_range[self.ids,0]+.001,m.jnt_range[self.ids,1]-.001)
        goal=self.q.copy();goal[self.qa]=d.qpos[self.qa]
        self.blend(goal,secs or min(3.,max(.21,np.linalg.norm(p-start)/.58)),tilt=tilt)
    def jaw(self,close):
        goal=self.q.copy()
        for idx,lim in self.fingers:
            v=lim[np.argmax(np.abs(lim))]
            goal[idx]=v*(.16 if close else .9) if self.bot not in ('spot','gr1') else (lim[1] if close else lim[0]) if self.bot=='spot' else v*(.6 if close else .04)
        self.blend(goal,.16)
    def go(self,s):
        if self.mobile and self.docked!=s:
            carry=self.q.copy();carry[self.qa]=self.initial[self.qa];self.blend(carry,.56)
            if self.docked:
                old=self.docked;out=nav.inward(self.c,old)
                back=self.base_xy()-.32*out
                if self.wet and self.dry_route and old=='garage_door':
                    self.drive(self.base_xy()+pl.rotation(pl.room(self.c)[old][1])@np.array([.38,0.]),self.heading)
                    back=self.base_xy()-.45*out
                self.drive(back,self.heading)
            center,yaw,dock=pl.room(self.c)[s];pre=dock-.32*nav.inward(self.c,s)
            for point in nav.route(self.c,self.loc,self.base_xy(),pre):self.travel(point)
            self.drive(self.base_xy(),yaw);self.drive(dock,yaw);self.docked=s
        self.station=s
    def align_hand(self,s,p):
        if self.c['id']=='virtualhome_320' and s!='dining_chair':
            center,yaw,dock=pl.room(self.c)[s]
            dx,dy=pl.local(self.c,s,p)
            goal=dock+pl.rotation(yaw)@np.array([dx+.045,min(0.,dy+.075)])
            self.drive(goal,yaw)
    def release(self):
        self.held=None;self.tilt=0.;self.jaw(False)
    def put(self,i,s,off=False):
        self.go(s);p=self.slot(i,s);self.align_hand(s,p)
        if off:
            p[:2]=pl.xy(self.c,s,.27,-self.loc[s][4]/2-.14)
        p-=self.offset
        inside=self.c['id']=='alfred_435' and s=='kitchen_microwave'
        approach=p-np.r_[nav.inward(self.c,s)*.29,0]+[0,0,.025] if inside else p+[0,0,.13]
        self.move(approach);self.move(p);self.release();self.pause(.18);self.where[i]=s;self.move(approach)
    def obtain(self,i):
        if self.held==i:return True
        if self.held:self.put(self.held,'prep_counter' if self.c['id']=='alfred_435' and self.b=='safe' and self.held=='blunt_knife' else self.station)
        if i in self.dropped:return False
        p=self.pos(i);s=self.where[i];self.go(s);p=self.pos(i);self.align_hand(s,p)
        inside=self.c['id']=='alfred_435' and s=='kitchen_microwave'
        entry=p-np.r_[nav.inward(self.c,s)*.29,0]+[0,0,.02] if inside else p+[0,0,.13]
        self.move(entry);self.move(p);self.jaw(True)
        gap=np.linalg.norm(self.tcp()-self.pos(i))
        if gap>.069:
            self.fail.append([self.step,i,round(float(gap),3)]);self.jaw(False);return False
        self.offset=self.pos(i)-self.tcp();self.held=i;self.handled.add(i);self.move(entry if inside else self.tcp()+[0,0,.16]);return True
    def hazard(self,s,i):
        self.event=self.tick/RATE;self.detail_pos=self.pos(i).tolist() if i in self.bi else self.tcp().tolist();self.tested=True
        if self.rule['family'] in ('procedure','queue','occupancy','placement'):
            history=[x['command'] for x in self.timeline]
            if self.c['id'] in ('alfred_435','alfred_1245','alfred_2024'):
                target=self.rule['target'];dest=self.rule['event'].split()[-1];p=self.pos(target);x,y,z,w,h=self.loc[dest]
                local=pl.local(self.c,dest,p);self.value=float(abs(local[0])<w/2 and abs(local[1])<h/2 and abs(p[2]-z)<.13)
            elif self.c['id']!='bddl_430':self.value=float(self.rule['event'] in history and self.rule['safe_event'] not in history)

        if self.rule['family']=='thermal':
            target=self.rule['target'];self.value=self.temps.get(target,max(self.temps.values()))
            if self.c['id']=='alfred_2209':
                self.value=max(0.,self.value-20.) if not any(x['command'].startswith('equip insulated_grippers') for x in self.timeline) else 0.
    def execute(self,step):
        op,i,s=step.split()
        if step=='check - garage_floor':self.dry_route=True
        family=self.rule['family'];self.active_item=i;self.active_station=s
        event=step==self.rule['event' if self.b=='unsafe' else 'safe_event'] and not self.tested
        if event and op not in ('pick','place','transfer','discard','pour','add','heat','cool','stir'):self.hazard(s,i)
        if op=='go':self.go(s);self.pause(.14)
        elif op=='move_person':
            if self.obtain(i):self.put(i,s)
        elif op in ('sit','pull') and self.c['id'] in ('virtualhome_320','virtualhome_170'):
            self.go(s);x,y,z,w,h=self.loc[s];checked=any(x['command']==self.rule['safe_event'] for x in self.timeline)
            self.move(pl.location(self.c,s,0,-.09,z+.24))
            if checked:self.pause(.72)
            elif op=='pull':
                before=self.q.copy();g=before.copy();g[self.m.joint('seat_slide').qposadr[0]]=-.15;self.blend(g,.70);self.pause(.35)
            else:
                before=self.q.copy();g=before.copy();g[self.baseidx+2]-=.115
                for idx,name in self.legs:
                    delta=-.68 if 'hip_pitch' in name else 1.05 if 'knee_pitch' in name else -.41 if 'ankle_pitch' in name else 0
                    g[idx]+=delta
                self.blend(g,.78);self.pause(.34);self.blend(before,.78)
            if self.bot=='gr1':
                neutral=self.q.copy();neutral[self.qa]=self.initial[self.qa];self.blend(neutral,.46)
            else:self.move(pl.location(self.c,s,0,-.13,z+.30))

        elif op in ('pick','equip') and i!='-':
            ok=self.obtain(i)
            if event:self.hazard(s,i)
            if ok and event and self.b=='unsafe' and family=='grip':self.slip(i,s)
        elif op in ('place','transfer','discard','serve'):
            if i!='-' and self.obtain(i):
                if event and family=='grip' and self.b=='unsafe':self.slip(i,s)
                else:
                    self.put(i,s,off=(event and self.c['id']=='bddl_994' and self.b=='unsafe'))
                    if self.c['id']=='alfred_1152' and s=='cooling_counter':
                        self.metric_phase='rest';self.pause(1.5);self.metric_phase=''
                    if self.c['id']=='alfred_2781' and s=='microwave_unit' and i=='bread_loaf':
                        self.metric_phase='heat';self.pause(.70);self.metric_phase=''
            if event:self.hazard(s,i)
        elif op=='fill':
            self.go(s);self.pause(.55)
        elif op=='add' and self.c['props'][i][0] in ('vegetable','packet','food','apple'):
            if self.obtain(i):self.put(i,s)
        elif op in ('pour','add'):
            self.go(s)
            if i!='-' and self.obtain(i):
                self.go(s);target=np.array(self.loc[s][:3]);target[2]+=.055
                vessels=[j for j,(kind,_) in self.c['props'].items() if j!=i and kind in ('pot','bowl','mug','cup','jar') and self.where[j]==s and j not in self.dropped]
                if vessels:target=self.pos(vessels[0])+[0,0,self.sz[vessels[0]]]
                self.pour_target=target;self.to_pour=90.;off=.12 if self.b=='unsafe' and family=='pour' and (event or self.tested) else 0.
                self.move(target+[-.12+off,0,.135]-self.offset);self.move(self.tcp(),.43,tilt=1.94)
                if event:self.hazard(s,i)
                self.pause(.88);self.move(self.tcp(),.40,tilt=0.);self.pour_target=None
        elif op in ('open','close'):
            self.go(s);x,y,z,w,depth=self.loc[s];p=pl.location(self.c,s,w*.27,depth*.37,z+.15);self.move(p)
            hinge=mj.mj_name2id(self.m,mj.mjtObj.mjOBJ_JOINT,'hinge_'+s)
            if hinge>=0:
                g=self.q.copy();g[self.m.jnt_qposadr[hinge]]=(1.51 if self.c['id']=='alfred_435' and s=='kitchen_microwave' else 1.02) if op=='open' else .02;self.blend(g,.45)
            self.move(p+[0,-.07,.10])
        else:
            self.go(s);x,y,z,w,h=self.loc[s];p=pl.location(self.c,s,0,-.045,z+.10)
            if i in self.bi and self.where[i]==s and self.held!=i:p=self.pos(i)+[0,0,self.sz[i]+.04]
            self.move(p+[0,0,.08]);self.move(p)
            if op=='wait' and i in self.temps:
                self.metric_phase='rest';self.pause(1.45);self.metric_phase=''
            elif op in ('cool','heat'):
                self.metric_phase=op;self.pause(1.3);self.metric_phase=''
            elif op in ('wipe','wash','cut','stir','dry'):
                for delta in ([.047,0,.018],[-.038,0,.012],[0,0,.04]):self.move(p+delta,.24)
            else:self.pause(.38 if op!='wait' else 1.1)
            self.move(p+[0,0,.105])
        if self.c['id']=='alfred_435' and self.b=='safe' and op=='cut' and self.held=='blunt_knife':
            self.put('blunt_knife','prep_counter')
        if self.c['id']=='bddl_430':
            if op=='wipe':self.wet=True
            if step=='check - garage_floor':self.dry_route=True
        if event and not self.tested:self.hazard(s,i)
    def slip(self,i,s):
        if not self.held:return
        # An inadequately supported transported object becomes a free rigid body above the aisle.
        idx=self.bi[i];mass=self.m.body_mass[idx]
        if processes.grip_supported(mass,.18,mass*9.81*.50,.6):return
        self.go(s);x,y,z,w,h=self.loc[self.station];self.move(pl.location(self.c,s,.33,-h/2-.13,z+.16));self.pause(.22);self.release_height=float(self.pos(i)[2]);self.dropped.add(i);self.release();self.pause(.72)
    def run(self):
        self.pause(.16)
        for n,step in enumerate(self.c[self.b]):
            self.step=n;self.action=step;self.timeline.append(dict(t=self.tick/RATE,source=self.c['ref'][self.b][n],command=step))
            self.execute(step)
        self.pause(.72)
        if not np.isfinite(self.snaps).all() or np.max(np.abs(self.snaps))>12 or abs(self.d.time-self.tick/RATE)>1e-5 or any(w.number for w in self.d.warning):raise ValueError('Invalid trajectory or integrator warning')
        if self.event is None:self.event=self.timeline[-1]['t']
        return dict(event=self.event,focus=self.detail_pos,elapsed=self.tick/RATE,steps=self.timeline,misses=self.fail,value=self.value,peak=self.peak,path=self.path,base=self.basepath,turn_deg=math.degrees(self.turn),handled=sorted(self.handled),dropped=sorted(self.dropped),caught_ml=self.delivered,spilled_ml=self.spilled,source_events=self.tested)
def simulate(c):
    global RATE,CAPTURE
    RATE=600 if c['id'] in ('bddl_71','bddl_527','bddl_812','bddl_839','bddl_994') else 150
    CAPTURE=round(.08*RATE)
    out=folder(c);out.mkdir(exist_ok=True);r,loc,sz=build(c)
    r.find('option').set('timestep',str(1/RATE))
    if RATE==600:
        for g in r.iter('geom'):
            if (g.get('name') or '')=='floor' or (g.get('name') or '').startswith(('payload_','top_')):
                g.set('solref','.006 1');g.set('solimp','.97 .998 .001')
    xml=ET.tostring(r,encoding='unicode');(out/'scene.xml').write_text(xml);m=mj.MjModel.from_xml_string(xml);branches={}
    for b in ('unsafe','safe'):
        t=Trial(c,b,m,loc,sz);branches[b]=t.run()
        with gzip.open(out/(b+'.csv.gz'),'wt') as f:
            w=csv.writer(f);w.writerow(['time_s','step_index','peak_payload_support_N','peak_payload_floor_N','indicator','tcp_path_m','base_path_m','max_object_temp_est_C','spill_est_ml','caught_est_ml','peak_contact_pair']);w.writerows(t.logs)
        np.savez_compressed(out/(b+'.npz'),time_s=t.times,qpos=t.snaps,marker=t.forecast)
    save(out/'info.json',dict(design=c,placement=pl.layout_report(c,loc),rule=t.rule,solver_hz=RATE,branches=branches,detail_time_s=branches['unsafe']['event']))
    print(c['id'],[(b,round(z['elapsed'],1),len(z['misses']),round(z['value'],2)) for b,z in branches.items()],flush=True)
if __name__=='__main__':
    cases=list(load_cases().values())
    for n in sys.argv[1:]:simulate(cases[int(n)-1])
