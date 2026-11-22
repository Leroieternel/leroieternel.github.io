"""Sample posed hand and face meshes at the same 2 ms times as the MuJoCo controller."""
from pathlib import Path
from scipy.spatial.transform import Rotation
import numpy as np
import xml.etree.ElementTree as ET
import neon_people_physics as sim

H=Path(__file__).resolve().parent
out=H/'contact_samples';out.mkdir(exist_ok=True)
rig=sim.HumanRig('cafe',sim.CAFE_HUMAN_XY)
names=rig._performance_names
xml=ET.parse(H/'01_cafe/scene.xml')
baseline=np.load(H/'optics/01_cafe/unsafe.npz')
times=np.arange(round(20/sim.DT)+1)*sim.DT
indices=np.minimum((times*rig._source_fps).astype(int),len(rig._positions)-1)
j=np.minimum(indices+1,len(rig._positions)-1)
f=(times*rig._source_fps-indices)[:,None,None]
xyz=rig._positions[indices]*(1-f)+rig._positions[j]*f
q=rig._quaternions[indices]*(1-f)+rig._quaternions[j]*f
q/=np.linalg.norm(q,axis=2,keepdims=True)
rot=Rotation.from_quat(q[:,:,[1,2,3,0]].reshape(-1,4)).as_matrix().reshape(len(times),len(names),3,3)
k=names.index('espresso_cup')
np.savez_compressed(out/'cup.npz',t=times,pos=xyz[:,k],rot=rot[:,k])
for part,si in [('uniform_gloves',5),('uniform_skin',4)]:
    skin=xml.find(f".//skin[@name='{part}']")
    v=np.fromstring(skin.get('vertex'),sep=' ').reshape(-1,3)
    faces=np.fromstring(skin.get('face'),sep=' ',dtype=int).reshape(-1,3)
    # Keep actual face, neck and both forearms. Remove vertices outside all used faces.
    if si==4:
        mask=(v[:,2]>1.415)|(abs(v[:,0])>.46)
        faces=faces[mask[faces].any(axis=1)]
    ids,fid=np.unique(faces.ravel(),return_inverse=True)
    np.save(out/(part+'-faces.npy'),fid.reshape(-1,3))
    arr=np.lib.format.open_memmap(out/(part+'.npy'),dtype='float32',mode='w+',shape=(len(times),len(ids),3))
    for bone in skin.findall('bone'):
        idx=names.index(bone.get('body'))
        bp=np.fromstring(bone.get('bindpos'),sep=' ')
        m=np.fromstring(bone.get('vertid'),sep=' ',dtype=int)
        w=np.fromstring(bone.get('vertweight'),sep=' ')
        sel=np.isin(m,ids); u=m[sel]; slot=np.searchsorted(ids,u)
        vec=v[u]-bp
        for start in range(0,len(times),200):
            end=min(start+200,len(times))
            values=np.einsum('nij,kj->nki',rot[start:end,idx],vec)+xyz[start:end,idx,None]
            arr[start:end,slot]+=values*w[sel][None,:,None]
    err=float(abs(arr[::20]-baseline['skin'+str(si)][:,ids]).max());print(part,len(ids),err,flush=True)
    assert err<.000025,err
    arr.flush()
