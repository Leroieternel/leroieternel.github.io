from pathlib import Path
import xml.etree.ElementTree as E
import json,numpy as np
from pxr import Usd,UsdGeom,UsdSkel
root=Path.cwd(); out=root/'outputs/antigravity_revision/people/rig';out.mkdir(exist_ok=True)
stage=Usd.Stage.Open(str(root/'.runtime/staff-assets/F_Business_02/F_Business_02.usd'))
sk=next(UsdSkel.Skeleton(p) for p in stage.Traverse() if p.IsA(UsdSkel.Skeleton))
paths=list(map(str,sk.GetJointsAttr().Get())); ns=[p.split('/')[-1] for p in paths];raw=np.array(sk.GetBindTransformsAttr().Get())[:,3,:3];sh,el,kn=(raw[ns.index(x)] for x in ['L_Upperarm','L_Forearm','L_Mid1'])
def cal(points):
 v=points.copy();v[:,0]=-np.sign(v[:,0])*np.interp(abs(v[:,0]),[0,sh[0],el[0],kn[0],.90],[0,.175,.525,.872,1.07]);v[:,1]=-(v[:,1]-sh[1])*1.06;v[:,2]*=1.4/sh[2];return v
base=E.parse(root/'outputs/paired_workcells/assets/operator_skin.xml')
def driver(j):
 p=paths[ns.index(j)]
 for side in 'LR':
  if '/'+side+'_Calf/' in p or j==side+'_Calf':return 'fabric_'+side+'_leg'
  if '/'+side+'_Upperarm/' in p or j==side+'_Upperarm':
   if '/'+side+'_Hand/' in p or j==side+'_Hand':
    if j.split('_')[-1].endswith('End'):return p.split('/')[-2]
    return j
   if '/'+side+'_Forearm/' in p or j==side+'_Forearm':return 'fabric_'+side+'_lower'
   return 'fabric_'+side+'_upper'
 if '/Head' in p or j=='NeckTwist02':return 'fabric_head'
 return 'operator_standing'
bind={n:p.tolist() for n,p in zip(ns,cal(raw))}
npz={}
for prim in stage.Traverse():
 if not prim.IsA(UsdGeom.Mesh):continue
 m=UsdGeom.Mesh(prim); points=np.array(m.GetPointsAttr().Get());faces=np.array(m.GetFaceVertexIndicesAttr().Get()).reshape(-1,3)
 uv=UsdGeom.PrimvarsAPI(prim).GetPrimvar('st0');uids=np.array(uv.GetIndices()).reshape(-1,3)
 b=UsdSkel.BindingAPI(prim);ii=np.array(b.GetJointIndicesPrimvar().Get()).reshape(len(points),-1);ww=np.array(b.GetJointWeightsPrimvar().Get()).reshape(ii.shape);jp=b.GetJointsAttr().Get()
 names=np.array([driver(v.split('/')[-1]) for v in (list(map(str,jp)) if jp else paths)])
 part=prim.GetName().split('__')[-1]; mask0=np.abs(points[faces,0].mean(axis=1))>.54
 for name,mask in ({'skin':~mask0,'gloves':mask0} if part=='skin' else {part:np.ones(len(faces),bool)}).items():
  skel=base.find(".//skin[@name='uniform_"+name+"']")
  refs=np.unique(np.column_stack((faces[mask].ravel(),uids[mask].ravel())),axis=0)
  vid=refs[:,0]
  verts=cal(points[vid]); assert np.allclose(verts,np.fromstring(skel.get('vertex'),sep=' ').reshape(-1,3),atol=1e-5)
  for bn in skel.findall('bone'):skel.remove(bn)
  for bone in sorted(set(names[ii[vid]].ravel())):
   weights=((names[ii[vid]]==bone)*ww[vid]).sum(axis=1); ids=np.flatnonzero(weights>1e-7)
   if not len(ids):continue
   bp=bind[bone] if bone in bind else json.loads((root/'outputs/paired_workcells/assets/landmarks.json').read_text())[bone]
   E.SubElement(skel,'bone',body=bone,bindpos=' '.join(map(str,bp)),bindquat='1 0 0 0',vertid=' '.join(map(str,ids)),vertweight=' '.join(map(str,weights[ids])))
  if name=='gloves':
   ids=names[ii[vid]]; npz=dict(vertices=verts,faces=np.fromstring(skel.get('face'),sep=' ',dtype=int).reshape(-1,3),bones=ids,weights=ww[vid])
base.write(out/'articulated-skin.xml');np.savez_compressed(out/'hands.npz',**npz)
joints={b.get('body'):list(map(float,b.get('bindpos').split())) for b in base.findall('.//bone')}
(out/'bind.json').write_text(json.dumps(joints,indent=2));print(list(joints))
