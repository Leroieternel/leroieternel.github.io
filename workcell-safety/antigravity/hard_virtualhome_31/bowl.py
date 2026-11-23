"""First contact of a falling jet with the same revolved ceramic profile used for rendering."""
from dataclasses import dataclass
import numpy as np
G=9.81
PROFILE=[(.002,.0005),(.094,.0005),(.102,.005),(.104,.026),(.104,.046),(.108,.061),(.1078,.065),(.105,.066),(.102,.063),(.101,.043),(.098,.022),(.095,.013),(.094,.012),(.0002,.012)]
CREST=7
@dataclass
class Landing:
    kind: str
    first_t: float
    first_xyz: np.ndarray
    times: np.ndarray
    points: np.ndarray
    @property
    def inside(self):return self.kind in ('bowl floor','inner wall')
    def on_wall(self,age):
        return np.array([np.interp(age,self.times,self.points[:,j]) for j in range(3)])
def route(o,v,center,table_z):
    from scipy.optimize import brentq
    def at(dt):
        xyz=o+dt*v
        xyz[2]-=.5*G*dt**2
        return xyz
    def crossing(z):
        return (v[2]+np.sqrt(v[2]**2+2*G*(o[2]-z)))/G
    def radius(dt):return np.linalg.norm(at(dt)[:2]-center[:2])
    best=None
    for j in range(1,len(PROFILE)):
        r0,z0=PROFILE[j-1];r1,z1=PROFILE[j]
        if z0==z1:
            tau=crossing(center[2]+z0)
            if not min(r0,r1)<=radius(tau)<=max(r0,r1):continue
        else:
            ta,tb=sorted([crossing(center[2]+z0),crossing(center[2]+z1)])
            def gap(dt):
                z=at(dt)[2]-center[2]
                return radius(dt)-(r0+(r1-r0)*(z-z0)/(z1-z0))
            ga,gb=gap(ta),gap(tb)
            if ga*gb>0:continue
            tau=brentq(gap,ta,tb,xtol=1e-12)
        if best is None or tau<best[0]:best=(tau,j)
    if best is None:
        tau=crossing(table_z+.00012);hit=at(tau)
        return Landing('counter',tau,hit,np.array([tau]),hit[None,:])
    tau,j=best;hit=at(tau)
    if j==len(PROFILE)-1:
        return Landing('bowl floor',tau,hit,np.array([tau]),hit[None,:])
    inside=j>CREST;direction=hit[:2]-center[:2];direction/=np.linalg.norm(direction)
    # Descend the contacted face toward its own basin. The thin film follows the
    # ceramic contour. No volume is transferred through the wall to the opposite side.
    nodes=[hit];times=[tau]
    path=(PROFILE[j:-1]+[(.092,.012)]) if inside else list(reversed(PROFILE[1:j]))+[(.0995,table_z-center[2]+.00012)]
    speed=.25
    for r,z in path:
        xyz=np.r_[center[:2]+r*direction,center[2]+z];prev=nodes[-1]
        distance=np.linalg.norm(xyz-prev)
        if distance<1e-7:continue
        v2=min(.85,np.sqrt(speed**2+.65*2*G*max(0.,prev[2]-xyz[2])))
        times.append(times[-1]+2*distance/(speed+v2));nodes.append(xyz);speed=v2
    return Landing('inner wall' if inside else 'outer wall',tau,hit,np.array(times),np.array(nodes))
