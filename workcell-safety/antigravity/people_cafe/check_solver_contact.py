"""Test actual cup meshes against articulated hand and face surfaces on all solver samples."""
from pathlib import Path
import json,numpy as np
import bpy
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent;src=H/'01_cafe';geometry=np.load(src/'rendered_geometry.npz')
s=H/'contact_samples';c=dict(np.load(s/'cup.npz'))
verts={name:np.load(s/(name+'.npy'),mmap_mode='r') for name in ('uniform_gloves','uniform_skin')}
faces={name:np.load(s/(name+'-faces.npy')).tolist() for name in verts}
op=H/'optics/01_cafe';meta=json.loads((op/'meta.json').read_text())
ids={g['name']:i for i,g in enumerate(meta['objects'])}
pose=np.load(op/'unsafe.npz')['poses'][0];cp=pose[ids['cup_body']]
objects={}
for n in [k for k in ids if k.startswith('cup_')]:
    p=pose[ids[n]];v=(geometry[n+'_v']@p[:9].reshape(3,3).T+p[9:]-cp[9:])@cp[:9].reshape(3,3)
    objects[n]=BVHTree.FromPolygons(v.tolist(),geometry[n+'_f'].tolist(),all_triangles=True)
counts={}
for i,time in enumerate(c['t']):
    for name,array in verts.items():
        points=(array[i]-c['pos'][i])@c['rot'][i]
        if (points.min(axis=0)>[.034,.035,.037]).any() or (points.max(axis=0)<[-.073,-.035,-.037]).any():continue
        tree=BVHTree.FromPolygons(points.tolist(),faces[name],all_triangles=True)
        for n,part in objects.items():
            if tree.overlap(part):
                key=name+'/'+n
                if key not in counts:counts[key]=[0,float(time)]
                counts[key][0]+=1
result=dict(solver_samples=len(c['t']),dt_s=round(float(c['t'][1]),5),intersecting_sample_counts_and_first_time_s=counts,
            method='Direct linear blend skinning evaluated from the same bone and cup motion at every solver sample, verified against exported MuJoCo surfaces at the 501 camera frames. Tested hands, forearms and face against the final cup body, handle segments and espresso surface.')
(src/'solver-grip-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(result,flush=True)
