"""Flux from a tilted bottle, gravity jet characteristics, and conservative surface reservoirs."""
from pathlib import Path
import math,sys,json
import numpy as np
from scipy.ndimage import gaussian_filter1d
D=Path(__file__).resolve().parent; H=D.parent;sys.path.insert(0,str(H))
from rigid import PORT, TOP
from bowl import route
DT=.005
RHO=1030.; G=9.81; INITIAL=180e-6; ORIFICE=.0105
def cavity():
    # Fixed volume quadrature of the internal bottle envelope, excluding walls and headspace above neck.
    dz=.003; area=dz**2;z=np.arange(-.119,.108,dz);u=np.arange(-.036,.036,dz);v=np.arange(-.061,.061,dz)
    X,Y,Z=np.meshgrid(u,v,z,indexing='ij')
    zz=[-.121,-.114,.049,.073,.091,.101,.111]
    rx=np.interp(Z,zz,[.031,.033,.033,.030,.026,.019,.016]);ry=np.interp(Z,zz,[.049,.055,.056,.049,.040,.026,.016])
    keep=(abs((X+.0015)/rx)**2.6+abs((Y+.0007)/ry)**2.6<1)
    return np.stack([X[keep],Y[keep],Z[keep]],axis=1),area*dz
def hydraulic(branch):
    ar=np.load(D/'runs/27_virtualhome_31'/(branch+'-rigid.npz'));t=ar['time_s'][::2];R=ar['bottle_R'][::2];c=ar['bottle_pos'][::2];bc=ar['bowl_pos'][::2]
    axis=R[:,:,2];down=-R[:,2,:2];down/=np.maximum(np.linalg.norm(down,axis=1)[:,None],1e-10)
    lip=np.tile(PORT,(len(t),1));lip[:,:2]+=.013*down;origin=c+np.einsum('ijk,ik->ij',R,lip)
    motion=gaussian_filter1d(np.gradient(origin,DT,axis=0),3,axis=0)
    xyz,cell=cavity();rem=INITIAL; paths=[]
    for i,ti in enumerate(t):
        if axis[i,2]>.43 or rem<1e-11:continue
        h=xyz@R[i,2,:];n=min(len(h)-1,int(rem/cell));surface=np.partition(h,n)[n]
        head=max(0.,surface-(origin[i,2]-c[i,2]));speed=.71*math.sqrt(2*G*head)
        if speed<=0:continue
        q=min(rem/DT,.54*math.pi*ORIFICE**2*speed)
        if q<1e-10:continue
        dv=q*DT;rem-=dv;vel=motion[i]+axis[i]*speed
        path=route(origin[i],vel,bc[i],TOP)
        tau=path.times[-1];land=path.points[-1].copy()
        if not (.315<land[0]<.785 and -.42<land[1]<.37):
            raise ValueError(f'Jet crosses worktop boundary at {land}')
        paths.append((ti,q,dv,origin[i].copy(),vel,tau,land,path.inside,abs(vel[2]-G*path.first_t),path))
    return ar,t,bc,paths
def ballistic(branch):
    ar,t,bc,paths=hydraulic(branch);vol=sum(p[2] for p in paths);capt=sum(p[2] for p in paths if p[7])
    print(branch,'discharged/caught/spill mL',np.round(np.array([vol,capt,vol-capt])*1e6,2),'range',np.round(np.min([p[6] for p in paths],axis=0),3),np.round(np.max([p[6] for p in paths],axis=0),3),flush=True)
if __name__=='__main__':
    for b in ('safe','unsafe'):ballistic(b)
