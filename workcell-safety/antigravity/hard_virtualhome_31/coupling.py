"""Couple the measured outlet to a continuous jet and an impact-driven liquid film."""
from pathlib import Path
import json,math,sys
import numpy as np
from pour import D,H,hydraulic,DT,G,RHO,INITIAL,TOP
from generated.milk_flow import Layer
BOWL_R=.095
def simulate(branch):
 ar,times,centers,emission=hydraulic(branch);center=centers[-1,:2];cx,cy=center
 bowl=Layer(cx-.103,cx+.103,cy-.103,cy+.103,.0025,kind='bowl',radius=BOWL_R)
 table=Layer(.315,.785,-.42,.37,.0035)
 # Mask the footprint of the bowl so liquid cannot move beneath the dish.
 table_free=(table.x[None,:]-cx)**2+(table.y[:,None]-cy)**2 > .094**2
 table.active &= table_free
 A=table.active
 table._active_e=A[:,:-1]&A[:,1:];table._active_s=A[:-1]&A[1:]
 table._active_se=A[:-1,:-1]&A[1:,1:];table._active_sw=A[:-1,1:]&A[1:,:-1]
 def add_film(layer,x,y,volume,radius):
  accepted=layer.deposit(x,y,volume,radius)
  residual=volume-accepted
  if residual>1e-15:
   # A subcell footprint cut by a wall drains onto the nearest cell on that same wetted side.
   col=int(np.argmin(abs(layer.x-x)));row=int(np.argmin(abs(layer.y-y)))
   if not layer.active[row,col]:
    ir,ic=np.where(layer.active);j=np.argmin((layer.x[ic]-x)**2+(layer.y[ir]-y)**2);row,col=ir[j],ic[j]
   layer.h[row,col]+=residual/layer.cell_area
 def outside_bowl(x,y):
  dx=x-cx;dy=y-cy;r=np.hypot(dx,dy)
  if r<.103:
   return cx+.104*dx/max(r,1e-7),cy+.104*dy/max(r,1e-7)
  return x,y
 arrivals=sorted(emission,key=lambda p:p[0]+p[5]);ei=ai=0
 sent=deposited=0.; rows=[];frames=[];hs=[];ht=[];ripple=[];qs=[];impact_history=[]
 effs=[0.,0.];bench_delta=np.zeros_like(table.h);last=[None,None]
 diskX,diskY=np.meshgrid(table.x,table.y)
 # Precompute a conservative projection to the nearest exterior boundary cell.
 from scipy.ndimage import distance_transform_edt
 nearest=distance_transform_edt(~table_free,return_distances=False,return_indices=True)
 for i,t in enumerate(times):
  while ei<len(emission) and emission[ei][0]<=t+1e-8:
   sent+=emission[ei][2];ei+=1
  while ai<len(arrivals) and arrivals[ai][0]+arrivals[ai][5]<=t+1e-8:
   p=arrivals[ai];ai+=1;ti,q,dv,origin,vel,tau,land,inside,speed=p
   isurf=int(not inside);layer=(bowl,table)[isurf];x,y=land[:2] if inside else outside_bowl(*land[:2])
   # The impinging jet feeds a local spreading sheet. A fraction first fans out to a corrugated rim.
   volume=dv;rad=.008 if inside else .012;split=.09 if inside else .20
   add_film(layer,x,y,volume*(1-split),rad)
   for theta in np.linspace(0,2*np.pi,12,endpoint=False):
    reach=(.015 if inside else .027)*(1+.32*np.cos(3*theta+8*ti)+.17*np.sin(5*theta-4*ti))
    xx=x+reach*np.cos(theta);yy=y+reach*np.sin(theta)
    if inside:
     dxy=np.array([xx-cx,yy-cy]);rr=np.linalg.norm(dxy)
     if rr>.088:xx,yy=center+dxy*(.088/rr)
    else:xx,yy=outside_bowl(xx,yy)
    add_film(layer,xx,yy,volume*split/12,.0045)
   effs[isurf]+=dv;deposited+=dv;last[isurf]=(t,x,y,q,speed)
   impact_history.append((t,isurf,x,y,q,speed))
  if i%2==0:
   for layer in (bowl,table):
    if layer.volume()>1e-13:layer.step(2*DT)
   leaked=table.h[~table_free].copy()
   if leaked.any():
    table.h[~table_free]=0.;np.add.at(table.h,(nearest[0][~table_free],nearest[1][~table_free]),leaked)
  vb=bowl.volume();vt=table.volume()
  balance=(INITIAL-sent)+(sent-deposited)+vb+vt
  if abs(balance-INITIAL)>2e-10:raise ValueError((branch,t,balance-INITIAL,vb,vt))
  jforce=0.
  for item in last:
   if item and t-item[0]<.012:jforce+=RHO*item[3]*item[4]
  rows.append([t,(INITIAL-sent)*1e6,(sent-deposited)*1e6,vb*1e6,vt*1e6,jforce,float(ar['grip_force'][2*i]),(balance-INITIAL)*1e6])
  if i%8:continue
  hs.append(bowl.h.astype('f').copy());ht.append(table.h.astype('f').copy())
  # Spacetime characteristics sample the single connected jet from mouth to current head.
  line=[]
  for ti,q,dv,o,v,tau,land,inside,speed in reversed(emission[max(0,ei-115):ei]):
   age=t-ti
   if age>tau:break
   pos=o+age*v;pos[2]-=.5*G*age**2
   tangent=v-np.array([0.,0.,G*age])
   radius=min(.013,np.sqrt(q/(np.pi*max(.05,np.linalg.norm(tangent)))))
   line.append([*pos,radius])
  if len(line)>1 and ai and t-arrivals[ai-1][0]-arrivals[ai-1][5]<.014:
   item=arrivals[ai-1];pos=item[6].copy()
   layer=bowl if item[7] else table
   ix=np.argmin(abs(layer.x-pos[0]));iy=np.argmin(abs(layer.y-pos[1]))
   pos[2]=(centers[2*i if len(centers)>len(times) else i,2]+.012 if item[7] else TOP)+layer.h[iy,ix]
   if np.linalg.norm(pos-np.array(line[-1][:3]))<.045:line.append([*pos,line[-1][3]])
  frames.append(np.asarray(line,dtype='f').reshape(-1,4))
  raw=[]
  for item in last:
   if item:
    ti,x,y,q,speed=item;raw.append([x,y,q*np.exp(-max(t-ti,0)/.045),speed])
   else:raw.append([0,0,0,0])
  ripple.append(raw)
 dest=D/'runs/27_virtualhome_31';rows=np.asarray(rows)
 assert rows[-1,2]<1e-7 and abs(rows[-1,1]+rows[-1,3:5].sum()-INITIAL*1e6)<.0002
 assert rows[-1,4]<.01 if branch=='safe' else rows[-1,4]>100
 np.savetxt(dest/(branch+'-flow.csv'),rows,fmt='%.9g',delimiter=',',header='time_s,bottle_ml,in_flight_ml,bowl_ml,table_ml,jet_normal_momentum_flux_N,gripper_bottle_normal_force_N,balance_error_ml',comments='')
 nmax=max(map(len,frames));jet=np.full((len(frames),nmax,4),np.nan,'f')
 for i,f in enumerate(frames):jet[i,:len(f)]=f
 np.savez_compressed(dest/(branch+'-surfaces.npz'),jet=jet,bowl=hs,table=ht,bx=bowl.x,by=bowl.y,tx=table.x,ty=table.y,impact=np.array(ripple),bowl_center=center)
 print(branch,'final budget mL',rows[-1,1:5], 'peak depth mm',np.max(hs[-1])*1000,np.max(ht[-1])*1000,flush=True)
if __name__=='__main__':
 for b in ('safe','unsafe'):simulate(b)
