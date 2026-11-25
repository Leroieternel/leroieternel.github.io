"""Native breakfast bowl, contact hulls, ballistic first hits and a volume-conserving basin."""
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from registered_assets import D,REV,ROOT,artist,read

ORIGINAL=REV/'hard1044/milk-registered-1ae2545fff80'
WORK=D/'physics/native-milk'
RUN=WORK/'runs/27_virtualhome_31'
KEY='hard_virtualhome_31'
sys.path[:0]=[str(ORIGINAL),str(ORIGINAL.parent)]

def dimensions():
    return read(WORK/'bowl-registration.json')

def register():
    from furnished_subjects import vertical_rays
    from support_models import data
    studio,_=artist('household_subjects')
    v,tris=data(studio.BOWL_KEY)
    prof=studio.select_bowl_profile(v,tris,vertical_rays(v,tris))
    prof.update(key=studio.BOWL_KEY,dimensions_m=np.ptp(v,axis=0).tolist(),sector_count=32,
                surface='Original Genie Sim triangles for the first jet hit. The radial profile describes drainage and the interior hydrostatic film.')
    WORK.mkdir(parents=True,exist_ok=True);(WORK/'bowl-registration.json').write_text(json.dumps(prof,indent=1))
    for n in ('bottle.npz','cap.npz','bottle-source.json'):
        f=WORK/n
        if not f.exists():f.symlink_to(ORIGINAL/n)
    return prof

def rigid_trial(prof):
    from support_models import data,shell
    import rigid
    v,tris=data(prof['key']);r=np.linalg.norm(v[:,:2],axis=1)
    angle=np.arctan2(v[:,1],v[:,0]);old=rigid.scene
    def scene():
        tree=old();body=tree.find(".//body[@name='cereal_bowl']")
        previous=body.findall('geom')
        total=sum(float(g.get('mass','0')) for g in previous)
        for g in previous:body.remove(g)
        count=prof['sector_count'];centers=2*math.pi*np.arange(count)/count
        # Use separate wedge hulls so the working bowl has an open cavity.
        for i,a in enumerate(centers):
            mask=np.abs(np.arctan2(np.sin(angle-a),np.cos(angle-a)))<np.pi/count+.025
            near=v[mask];low=near[near[:,2]<prof['inner_floor']+.002];hi=near[near[:,2]>=prof['inner_floor']-.002]
            for part,vertices in [('foot',low),('wall',hi)]:
                name='bowl_bottom' if i==0 and part=='foot' else f'bowl_{part}_{i}'
                g=ET.Element('geom',name=name,group='3',mass=str(max(total,.38)/count*(.5 if part=='foot' else .5)),friction='1.15 .012 .0004')
                if shell(tree,body,g,vertices):body.append(g)
        if body.find("geom[@name='bowl_bottom']") is None:raise ValueError('Missing native foot ring')
        # Export a hidden anchor with the exact free bowl pose alongside the gripper.
        ET.SubElement(body,'geom',name='bowl_frame',type='sphere',size='.0001',mass='0',group='1',contype='0',conaffinity='0')
        return tree
    rigid.D=WORK;rigid.scene=scene;rigid.simulate()
    sys.path.insert(0,str(ROOT/'outputs/robot_plans'));import optics
    optics.ROOT=WORK/'runs';optics.CACHE=WORK/'optics';optics.CACHE.mkdir(exist_ok=True);optics.export(27)

def router(prof):
    from support_models import data
    from bowl import Landing
    v,t=data(prof['key']);a,b,c=v[t].transpose(1,0,2);u=b-a;w=c-a;n=np.cross(u,w)
    uu=(u*u).sum(1);ww=(w*w).sum(1);uw=(u*w).sum(1);den=uu*ww-uw*uw
    proper=den>1e-22;det=np.where(proper,den,1.)
    rz=np.asarray(prof['profile']);crest=prof['crest'];inner=rz[crest:][::-1];outer=rz[:crest+1]
    def route(origin,vel,center,table_z):
        o=origin-center
        # Exact parabolic-flight/triangle-plane intersections, tested against that triangle's barycentric coordinates.
        A=-.5*9.81*n[:,2];B=n@vel;C=((o-a)*n).sum(1)
        disc=B*B-4*A*C;curved=np.abs(A)>1e-13
        root=np.sqrt(np.maximum(0,disc));two=np.where(curved,2*A,1.)
        ts=[(-B-root)/two,(-B+root)/two,np.where((~curved)&(np.abs(B)>1e-13),-C/np.where(np.abs(B)>1e-13,B,1.),-1.)]
        ground=(vel[2]+np.sqrt(vel[2]**2+2*9.81*(origin[2]-(table_z+.00012))))/9.81
        def at(dt):return origin+dt*vel-np.array([0,0,.5*9.81*dt*dt])
        best=ground;intersection=None
        for k,dt in enumerate(ts):
            ok=proper&(dt>0)&(dt<best)&(disc>=0)
            if k<2:ok&=curved
            ii=np.flatnonzero(ok)
            if not len(ii):continue
            p=o+dt[ii,None]*vel-a[ii];p[:,2]-=.5*9.81*dt[ii]**2
            su=(p*u[ii]).sum(1);sw=(p*w[ii]).sum(1)
            s=(ww[ii]*su-uw[ii]*sw)/det[ii];q=(uu[ii]*sw-uw[ii]*su)/det[ii]
            ii=ii[(s>=-1e-7)&(q>=-1e-7)&(s+q<=1.0000001)]
            if len(ii):
                ix=ii[dt[ii].argmin()];best=dt[ix];intersection=ix
        p=at(best)
        if intersection is None:return Landing('counter',best,p,np.array([best]),p[None,:])
        xy=p[:2]-center[:2];r=np.linalg.norm(xy);radial=xy/max(r,1e-12)
        z=p[2]-center[2]
        inside=abs(z-np.interp(r,inner[:,0],inner[:,1]))<=abs(z-np.interp(r,outer[:,0],outer[:,1]))
        if inside and z<=prof['inner_floor']+.002:return Landing('bowl floor',best,p,np.array([best]),p[None,:])
        # Follow the side hit by the stream. Preserve both the first impact and the later deposit in the ledger.
        ar=inner if inside else outer
        onward=ar[(ar[:,0]<r-.0001)&(ar[:,1]<=z+.0002)][::-1]
        if inside:
            onward=onward[onward[:,0]>=.34*prof['opening_radius']]
        else:
            onward=onward[onward[:,0]>=.20*prof['opening_radius']]
            onward=np.vstack((onward,[onward[-1,0] if len(onward) else r,table_z-center[2]+.00012]))
        pts=[p];times=[best];speed=.25
        for rr,h in onward:
            q=np.r_[center[:2]+rr*radial,center[2]+h]
            dist=np.linalg.norm(q-pts[-1])
            if dist<1e-7:continue
            nxt=min(.85,np.sqrt(speed*speed+.65*2*9.81*max(0,pts[-1][2]-q[2])))
            times.append(times[-1]+2*dist/(speed+nxt));pts.append(q);speed=nxt
        return Landing('inner wall' if inside else 'outer wall',best,p,np.asarray(times),np.asarray(pts))
    return route

def hydraulic_trial(prof):
    import pour
    pour.D=WORK;pour.route=router(prof)
    source=ORIGINAL/'continuum.py';code=source.read_text()
    radius=prof['opening_radius'];inner=np.asarray(prof['profile'][prof['crest']:])[::-1]
    from support_models import data
    v,_=data(prof['key'])
    foot=float(np.linalg.norm(v[v[:,2]<v[:,2].min()+.0015,:2],axis=1).max())
    code=code.replace('BOWL_R=.095','BOWL_R='+repr(radius)).replace('.094**2',repr(foot**2))
    code=code.replace('if r<.103:',f'if r<{foot+.002}:').replace('cx+.104*dx',f'cx+{foot+.0035}*dx').replace('cy+.104*dy',f'cy+{foot+.0035}*dy')
    code=code.replace('rr>.088',f'rr>{radius*.88}').replace('(.088/rr)',f'({radius*.88}/rr)')
    ns={'__name__':'native_film_solver','__file__':str(source)}
    exec(compile(code,str(source),'exec'),ns)
    for b in ('safe','unsafe'):
        ns['simulate'](b);file=RUN/(b+'-surfaces.npz')
        with np.load(file) as src:fields={k:src[k] for k in src.files}
        x,y=np.meshgrid(fields['bx'],fields['by']);cx,cy=fields['bowl_center']
        r=np.hypot(x-cx,y-cy);ground=np.interp(r,inner[:,0],inner[:,1]);active=r<=radius
        area=float(np.diff(fields['bx']).mean()*np.diff(fields['by']).mean())
        depths=[];levels=[];errors=[]
        for h in fields['bowl']:
            volume=float(np.sum(h,dtype=np.float64))*area
            lo,hi=ground[active].min(),float(inner[:,1].max())
            for _ in range(43):
                level=(lo+hi)*.5
                if np.maximum(0,level-ground[active]).sum()*area<volume:lo=level
                else:hi=level
            depths.append(np.where(active,np.maximum(0,hi-ground),0).astype('f'));levels.append(hi)
            errors.append(abs(depths[-1].sum(dtype=np.float64)*area-volume))
        if max(errors)>1e-10:raise ValueError(('Bowl capacity exceeded',b,max(errors)))
        fields.update(bowl=depths,bowl_levels=levels,bowl_ground=ground)
        np.savez_compressed(file,**fields)
    budgets={b:np.genfromtxt(RUN/(b+'-flow.csv'),names=True,delimiter=',')[-1] for b in ('safe','unsafe')}
    if not budgets['safe']['bowl_ml']>=170 or not budgets['unsafe']['table_ml']>100:raise ValueError('Original outcomes changed')
    (RUN/'repeat.json').write_text(json.dumps({'key':KEY,'solver':'MuJoCo + volume-conserving film with quasi-static interior pool','native_bowl':prof['key'],
       'final_mL':{b:{name:float(row[name]) for name in ('bowl_ml','table_ml','bottle_ml')} for b,row in budgets.items()}},indent=1))

def photograph(branch):
    import bpy
    from registered_assets import Library
    from optical_export import inspect
    from mathutils import Matrix
    sys.path.insert(0,str(REV/'visual_review'))
    from render_slot import acquire
    acquire()
    if not (RUN/'repeat.json').exists():raise ValueError('Missing fluid outcome')
    prof=dimensions()
    src=ORIGINAL/'render.py';code=src.read_text()
    code=code.replace("D.parents[3]/'.runtime/genie-assets'","ROOT/'.runtime/genie-assets'")
    start=code.index(" glaze=material('Blue-grey ceramic glaze'")
    end=code.index(' # Replace flat proxy flakes',start)
    code=code[:start]+" lib=Library(assets);outer=lib.place(SPEC['key'],(0,0,0))\n register(view=v,scene=s,lib=lib)\n"+code[end:]
    code=code.replace("rng.uniform(.016,.078)","rng.uniform(.009,SPEC['opening_radius']*.68)")
    code=code.replace("boz=bowlpos[2]+.012","boz=bowlpos[2]+SPEC['inner_floor']")
    code=code.replace("outer.location=bowlpos","B=np.eye(4);B[:3,:3]=rig['bowl_R'][j];B[:3,3]=bowlpos;outer.matrix_world=Matrix(B.tolist())")
    code=code.replace("obj.location=(bowlpos[0]+x,bowlpos[1]+y,boz+.001+max(0.,height-.0001))",
        "bed=np.interp(np.hypot(x,y),INNER[:,0],INNER[:,1]);obj.location=(bowlpos[0]+x,bowlpos[1]+y,bowlpos[2]+bed+.00165+height)")
    code=code.replace("set_geometry(ob,*wet_surface(Hm,X,Y,Z,im,k/25,bowlpos[:2] if ob==fluid[0] else None))",
        "if ob==fluid[0]:set_geometry(ob,*basin(wet_surface,Hm,X,Y,ar['bowl_levels'][k],bowlpos,im,k/25))\n   else:set_geometry(ob,*wet_surface(Hm,X,Y,Z,im,k/25))")
    code=code.replace("set_geometry(ob,*fan(im,Z+height+.00025,k/25,bowlpos,ob==fluid[3]))",
        "surface=(bowlpos[2]+ar['bowl_levels'][k]) if ob==fluid[3] else Z+height\n   set_geometry(ob,*fan(im,surface+.00025,k/25,bowlpos,ob==fluid[3]))")
    code=code.replace("PROFILE[7:-1]","PROFILE[SPEC['crest']:]").replace("PROFILE[1:8]","PROFILE[:SPEC['crest']+1]")
    inner=np.array(prof['profile'][prof['crest']:])[::-1]
    def basin(wet,h,x,y,level,center,impact,t):
        verts,faces=wet(h,x,y,0.,[0,0,0,0],t)
        if not len(faces):return [],[]
        pts=np.asarray(verts);rr=pts[:,:2]-center[:2];rad=np.linalg.norm(rr,axis=1)
        shore=np.interp(level,np.maximum.accumulate(inner[:,1]),inner[:,0])
        pts[:,:2]=center[:2]+rr*np.minimum(1.,max(.0001,shore-.0002)/np.maximum(rad,1e-9))[:,None]
        x0,y0,q,speed=impact;distance=np.linalg.norm(pts[:,:2]-[x0,y0],axis=1)
        ripple=.00032*min(1,q/.00006)*np.cos(350*distance-29*t)*np.exp(-distance/.035)
        pts[:,2]=center[2]+level+ripple*np.clip((shore-rad)/.006,0,1)+.00005
        return pts.tolist(),faces
    def register(view,scene,lib):
        manifest={'role':'Breakfast bowl','source_body':'cereal_bowl','native_key':prof['key'],'model_id':lib.entries[prof['key']]['id'],'replaced':True,
            'original_objects':['Glazed breakfast bowl','Ceramic foot band'],'notes':'Original USD, material images, triangle impacts and radius profile from the same ceramic bowl.'}
        inspect(KEY,view,scene,[manifest]);dest=D/'products/hard/virtualhome_31';dest.mkdir(parents=True,exist_ok=True)
        (dest/'native-furniture.json').write_text(json.dumps({'models':lib.evidence,'changes':[manifest],'physics_source':str(RUN)},indent=1))
    ns={'__name__':'native_breakfast_film','__file__':str(src),'ROOT':ROOT,'Library':Library,'SPEC':prof,'INNER':inner,'register':register,'basin':basin}
    exec(compile(code,str(src),'exec'),ns);ns['D']=WORK;ns['PROFILE']=prof['profile'];ns['render'](branch)

if __name__=='__main__':
    if sys.argv[1]=='solve':
        prof=register();rigid_trial(prof);hydraulic_trial(prof)
    elif sys.argv[1]=='fluid':hydraulic_trial(dimensions())
    elif sys.argv[1]=='record':photograph(sys.argv[2])
