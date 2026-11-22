"""Check the final footage mesh geometry, including both sides of the cup and liquid level."""
from pathlib import Path
import sys, json
import numpy as np

H=Path(__file__).resolve().parent
def export_surfaces(v,src):
    import bpy
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    data={}
    for g,obj in zip(v.spec,v.obs):
        n=g['name']
        if n not in ['cup_body','cup_coffee','saucer_t1','table1_top','water_glass_t1','plate_base','plate_well','paper_leaf_l','paper_leaf_r'] and not n.startswith('cup_handle_'):continue
        ob=obj.evaluated_get(graph);me=ob.to_mesh();me.calc_loop_triangles()
        data[n+'_v']=np.array([list(x.co) for x in me.vertices])
        data[n+'_f']=np.array([list(x.vertices) for x in me.loop_triangles])
        ob.to_mesh_clear()
    np.savez_compressed(src/'rendered_geometry.npz',**data)
def run():
    import bpy
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    make=lambda v,f:BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True,epsilon=0.)
    src=H/'01_cafe';op=H/'optics'/src.name
    shape=np.load(src/'rendered_geometry.npz')
    meta=json.loads((op/'meta.json').read_text()); idx={s['name']:k for k,s in enumerate(meta['objects'])}
    si={s['name']:s['id'] for s in meta['skins']}
    faces=np.load(op/'shapes.npz');tr=dict(np.load(op/'unsafe.npz'))
    t=np.load(src/'unsafe.npz')['time_s']
    with np.load(op/'safe.npz') as other:
        for ix in si.values():assert np.array_equal(other['skin'+str(ix)],tr['skin'+str(ix)])
        for n in ['cup_body','cup_coffee','saucer_t1','table1_top']:assert np.array_equal(other['poses'][:,idx[n]],tr['poses'][:,idx[n]])
    geometry={n[:-2]:(shape[n],shape[n[:-2]+'_f']) for n in shape.files if n.endswith('_v')}
    fixed={}; cup_meshes={};segments=[]
    state=tr['poses'][0];cup=state[idx['cup_body']]
    def local(v,pose):return (v-pose[9:])@pose[:9].reshape(3,3)
    def world(v,pose):return v@pose[:9].reshape(3,3).T+pose[9:]
    for n,(vs,fs) in geometry.items():
        w=world(vs,state[idx[n]])
        if n.startswith('cup_'):
            cup_meshes[n]=make(local(w,cup),fs)
            if n.startswith('cup_handle_'):
                item=meta['objects'][idx[n]];r,half,_=item['sz']
                ends=local(world(np.array([[0.,0.,-half],[0.,0.,half]]),state[idx[n]]),cup)
                axis=ends[1]-ends[0];pts=ends[0]+np.linspace(0,1,max(5,int(np.ceil(2*half/.0008))+1))[:,None]*axis
                segments.append((pts,r))
        else:fixed[n]=make(w,fs)
    counts={}; hits=[]; held=[]; last=None; peak_hand_speed=0
    hand_info=dict(np.load(H/'rig/hands.npz'))
    digit_mask={n:np.any((np.char.startswith(hand_info['bones'],'R_'+n))&(hand_info['weights']>.2),axis=1) for n in ('Thumb','Index','Mid','Ring','Pinky')}
    finger_polys={}
    hand_faces=faces['s'+str(si['uniform_gloves'])+'_f']
    for side in ('L','R'):
        for finger in ('Thumb','Index','Mid','Ring','Pinky'):
            membership=(hand_info['weights']*np.char.startswith(hand_info['bones'],side+'_'+finger)).sum(axis=1)
            finger_polys[side+finger]=hand_faces[np.all(membership[hand_faces]>.5,axis=1)]
    raw=np.load(src/'unsafe.npz')
    bone_names=raw['human_bone_names'].tolist()
    kin={}
    from mathutils import Quaternion
    from math import degrees
    if 'R_Hand' in bone_names:
        def rotation(name):
            return [Quaternion(q) for q in raw['human_quat'][:,bone_names.index(name)]]
        def angle(p,q):
            return degrees(2*np.arccos(np.clip(abs(p.dot(q)),0,1)))
        for label,parent,child in [('wrist','fabric_R_lower','R_Hand'),('index','R_Hand','R_Index1'),('thumb','R_Hand','R_Thumb1'),('elbow','fabric_R_upper','fabric_R_lower')]:
            relative=[p.inverted() @ q for p,q in zip(rotation(parent),rotation(child))]
            kin[label]={'max_rotation_from_first_pose_degrees':round(max(angle(relative[0],q) for q in relative),2),'largest_frame_step_degrees':round(max(angle(p,q) for p,q in zip(relative,relative[1:])),2)}
    def record(key,i,flag):
        if flag:
            counts[key]=counts.get(key,0)+1
            if len(hits)<35:hits.append((round(float(t[i]),3),key))
    report={'frames_checked_per_branch':len(t),'mesh_test':'Final posed skin triangles versus the evaluated ceramic, espresso surface, saucer, tabletop and plate meshes. Identical held geometry and body animation verified across both films.'}
    import xml.etree.ElementTree as ET
    actor=ET.parse(src/'scene.xml').find(".//skin[@name='uniform_skin']")
    neutral=np.fromstring(actor.get('vertex'),sep=' ').reshape(-1,3)
    lip=(np.abs(neutral[:,0])<.022)&(neutral[:,1]>.13)&(neutral[:,2]>1.509)&(neutral[:,2]<1.531)
    lip_rim_gap=[]
    for i,pose in enumerate(tr['poses']):
        cup=pose[idx['cup_body']]
        for skin in ['uniform_gloves','uniform_skin']:
            j=si[skin];v=tr['skin'+str(j)][i];f=faces['s'+str(j)+'_f']
            tag='hands' if skin=='uniform_gloves' else 'face_and_forearms'
            cv=local(v,cup);tree=make(cv,f)
            for n in ('cup_body','cup_coffee'):
                record(tag+'_'+n,i,bool(tree.overlap(cup_meshes[n])))
            if tag=='face_and_forearms':
                lip_coords=cv[lip]
                lip_rim_gap.append(float(np.hypot(np.linalg.norm(lip_coords[:,:2],axis=1)-.0286,lip_coords[:,2]-.030).min()))
            if tag=='hands':
                clamped=(np.abs(cv[:,2])<.0295)&(np.linalg.norm(cv[:,:2],axis=1)<.0276)
                record('hand_vertices_inside_cup_envelope',i,bool(clamped.any()))
                trees={n:make(cv,ff) for n,ff in finger_polys.items() if len(ff)}
                keys=list(trees)
                for k,n in enumerate(keys):
                    for other in keys[k+1:]:
                        record('finger_'+n+'_'+other,i,bool(trees[n].overlap(trees[other])))
                tree_world=make(v,f)
                all_digits=make(v,np.vstack(list(finger_polys.values())))
                for garment in ('uniform_vest','uniform_bluejeans','uniform_shirt'):
                    gid=si[garment];bodytree=make(tr['skin'+str(gid)][i],faces['s'+str(gid)+'_f'])
                    record('fingers_'+garment,i,bool(all_digits.overlap(bodytree)))
                for n,ft in fixed.items():
                    record('hands_'+n,i,bool(tree_world.overlap(ft)))
                gap=min(tree.find_nearest(Vector(pt))[3]-r for points,r in segments for pt in points)
                handle_mesh_overlaps=sum(bool(tree.overlap(mesh)) for n,mesh in cup_meshes.items() if n.startswith('cup_handle_'))
                held.append({'t':round(float(t[i]),4),'cup_z':round(float(cup[-1]),5),'handle_gap_mm':round(gap*1000,3),'handle_mesh_intersections':handle_mesh_overlaps})
                for name,mask in digit_mask.items():
                    if not mask.any():continue
                    if abs(t[i]-10.0)<.001:
                        ff=f[mask[f].sum(axis=1)>=2]
                        if len(ff):
                            dig=make(cv,ff)
                            pad_gap=min(dig.find_nearest(Vector(pt))[3]-r for points,r in segments for pt in points)
                            report.setdefault('finger_surface_to_handle_mm_at_10s',{})[name]=round(pad_gap*1000,3)
                    high=1.
                    for pts,r in segments:
                        a,end=pts[0],pts[-1];vseg=end-a
                        vv=cv[mask]; frac=np.clip(((vv-a)@vseg)/(vseg@vseg),0.,1.)
                        high=min(high,float(np.linalg.norm(vv-(a+frac[:,None]*vseg),axis=1).min()-r))
                    held[-1][name.lower()+'_vertex_gap_mm']=round(high*1000,3)
                if last is not None:peak_hand_speed=max(peak_hand_speed,float(np.linalg.norm(last-v,axis=1).max()/.04))
                last=v.copy()
    samples=[r for r in held if r['cup_z']>.937]
    saucer_height=float(world(geometry['saucer_t1'][0],state[idx['saucer_t1']])[:,2].max())
    report['cup_base_clearance_above_saucer_mm_at_start']=round(float((world(geometry['cup_body'][0],state[idx['cup_body']])[:,2].min()-saucer_height)*1000),3)
    report['closest_lip_region_to_rim_mm']=round(min(lip_rim_gap)*1000,2)
    report['closest_lip_region_time_s']=round(float(t[int(np.argmin(lip_rim_gap))]),3)
    report.update(joint_motion=kin,intersection_frame_counts=counts,first_overlaps=hits,airborne_frames=len(samples),
                  airborne_handle_gap_mm=[min(r['handle_gap_mm'] for r in samples),max(r['handle_gap_mm'] for r in samples)] if samples else [],
                  minimum_handle_gap_all_frames_mm=min(r['handle_gap_mm'] for r in held),
                  maximum_skin_vertex_speed_m_s=round(peak_hand_speed,3))
    (src/'grip-check.json').write_text(json.dumps(report,indent=2)+'\n')
    import csv
    with (src/'grip-clearance.csv').open('w') as out:
        wr=csv.DictWriter(out,fieldnames=list(held[0]),lineterminator='\n');wr.writeheader();wr.writerows(held)
    print(json.dumps(report,indent=2))
if __name__=='__main__':run()
