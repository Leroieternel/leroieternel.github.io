"""Render exported MuJoCo poses through Antigravity's scene and trace-driven lighting."""
from pathlib import Path
import sys, json, os, argparse
import numpy as np
import bpy
from mathutils import Vector
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'paired_workcells'))
import cycles_render as cr
import neon_people_look as look
ap=argparse.ArgumentParser()
ap.add_argument('case',choices=['cafe','darkroom'])
ap.add_argument('--movie',action='store_true')
ap.add_argument('--mesh-check',action='store_true')
ap.add_argument('--performance-stills',action='store_true')
ap.add_argument('--branch', choices=('safe','unsafe'))
ap.add_argument('--start', type=int,default=1)
args=ap.parse_args()
case=args.case
k=1 if case=='cafe' else 2
src=next(H.glob(f'{k:02d}_*'))
out=H.parent/'gallery'/('people_'+case)
frames=H/'frames'/case
out.mkdir(parents=True,exist_ok=True)
frames.mkdir(parents=True,exist_ok=True)
cr.CACHE=H/'optics'
v=cr.View(k)
v.pose('safe',0)
bpy.context.view_layer.update()
s=v.scene
audit, relight=look.dress(s,v,case,H.parents[2]/'.runtime/genie-assets')
if case=='cafe':
    sys.path.insert(0,str(H.parent))
    import neon_cafe_props
    audit['cafe_detail_pass']=neon_cafe_props.refine(v)
    sys.path.insert(0,str(H.parents[1]/'mobile_worlds/library'))
    import world_assets
    walnut=world_assets.pbr('walnut_veneer',0.90,'XY')
    for obj in s.objects:
        if obj.type=='MESH' and (obj.name in ('table1_top','table2_top') or 'CabDoor_' in obj.name or 'BarCounterTop' in obj.name):
            obj.data.materials.clear()
            obj.data.materials.append(walnut)
    world_assets.align_planar_uvs()
    audit['walnut_finish']={'source':'https://polyhaven.com/a/walnut_veneer','tile_m':0.90,'channels':list(world_assets.finish_maps('walnut_veneer'))}
if args.mesh_check:
    from check_cup import export_surfaces
    export_surfaces(v,src)
    sys.exit(0)
(out/'appearance.json').write_text(json.dumps(audit,indent=2))
info=json.loads((src/'info.json').read_text())
s.render.resolution_x=1920
s.render.resolution_y=1080
s.render.resolution_percentage=100
s.render.image_settings.file_format='JPEG'
s.render.image_settings.quality=94
s.render.fps=25
s.cycles.samples=40
s.render.use_persistent_data=True
records={b:np.genfromtxt(src/(b+'.csv'),delimiter=',',names=True,usecols=(0,1,2,3,4)) for b in ('safe','unsafe')}
times=np.load(src/'safe.npz')['time_s']
def performance_camera(target,portrait):
    target=Vector(target)
    offset=Vector((-.62,-.72,.14)) if portrait else Vector((-.19,-.25,.13))
    v.cam.location=target+offset
    v.cam.rotation_euler=(target-v.cam.location).to_track_quat('-Z','Y').to_euler()
    v.cam.data.lens=33 if portrait else 38
if case=='cafe':
    cup_index=next(j for j,x in enumerate(v.spec) if x['name']=='cup_body')
    cup_xyz=v.frames['safe']['poses'][:,cup_index,9:]
    in_air=np.flatnonzero(cup_xyz[:,2]>cup_xyz[0,2]+.016)
    start,end=int(in_air[0]),int(in_air[-1])
    top=int(np.argmax(cup_xyz[:,2]))
    down=cup_xyz[0].copy()
    high=cup_xyz[top].copy()
    half_up=np.flatnonzero(cup_xyz[:top+1,2]>(down[2]+high[2])*.5)[0]
    checks=[('Reach',round(3.65*25)),('Grip',round(6.35*25)),('Lift',int(half_up)),('Sip',top),('Set down',round(14.82*25)),('Release',round(16.1*25))]

def frame(b,i,detail):
    v.pose(b,i)
    t=times[i]
    trace=records[b]
    j=int(np.searchsorted(trace['time_s'],t+1e-8,side='right'))-1
    relight(float(trace['door_open'][j]),float(trace['cover_closed'][j]),float(t))
    cr.camera_pose(v.cam,v.meta[b+'_detail'] if detail else v.meta['overview'])
    if case=='cafe':
        if detail:
            v.cam.location=(0.02,0.69,1.60)
            v.cam.rotation_euler=(Vector((-0.57,0.674,0.902))-v.cam.location).to_track_quat('-Z','Y').to_euler()
            v.cam.data.lens=59
        else:
            v.cam.location.y-=0.42
            v.cam.location.z+=0.04
            v.cam.rotation_euler=(Vector((0.0,0.68,1.02))-v.cam.location).to_track_quat('-Z','Y').to_euler()
def proof(b, detail, tag):
    i=v.meta[b+'_detail_index'] if detail or case=='cafe' else round(5.2*25)
    if detail and case=="cafe": i=round(8.4*25)
    frame(b,i,detail)
    s.render.filepath=str(out/(tag+'.jpg'))
    bpy.ops.render.render(write_still=True)
if args.performance_stills:
    for j,(label,i) in enumerate(checks):
        frame('safe',i,False)
        portrait=label in ('Lift','Sip')
        target=cup_xyz[i]+np.array([0.,0.,.015])
        if portrait:target=(target+np.array([-.60,1.15,1.48]))*.5
        else:target[0]-=.035
        performance_camera(target,portrait)
        s.render.filepath=str(out/(f'gesture_{j}.jpg'))
        bpy.ops.render.render(write_still=True)
    (out/'gesture-frames.json').write_text(json.dumps([(name,float(times[i])) for name,i in checks]))
elif not args.movie:
    for b in ('unsafe','safe'):
        proof(b,False,b+'_poster')
        proof(b,True,'detail_'+b)
else:
    s.render.engine='BLENDER_EEVEE_NEXT'
    s.eevee.taa_render_samples=8
    s.eevee.use_shadows=True
    s.eevee.use_raytracing=True
    for b in ([args.branch] if args.branch else ('unsafe','safe')):
        s.frame_start=args.start
        s.frame_end=len(times)
        s.render.filepath=str(frames/(b+'_'))
        def update(scene,*unused):
            i=scene.frame_current-1
            t=times[i]
            detail=(4.3<=t<=8.45) if case=='cafe' else (3.2<=t<=8.5)
            frame(b,i,detail)
            if case=='cafe' and 8.65 <= t < 12.1:
                target=(high+np.array([-.60,1.14,1.43]))*.5
                performance_camera(target,True)
            elif case=='cafe' and 14.3 <= t < 16.2:
                performance_camera(down+np.array([-.033,.008,.02]),False)
        bpy.app.handlers.frame_change_pre.append(update)
        try:
            s.frame_set(1)
            bpy.ops.render.render(animation=True)
        finally:
            bpy.app.handlers.frame_change_pre.remove(update)
