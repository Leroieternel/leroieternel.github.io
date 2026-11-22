"""Rigid geometry for the two everyday DESPITE adaptations; dimensions are in metres."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

HERE=Path(__file__).resolve().parent
OMRON=HERE.parents[1]/'mobile_worlds/physics/01_warehouse'
CASES={'drawer':'01_drawer','pool':'02_pool'}
DRAWER_X=.50
AJAR=.15
OPEN=.27
FLOOR=.683
HANDLE=np.array([.50,.425,.794])
CASE=np.array([.605,.58,.858])
CLOTH=np.array([-.98,.528,.921])
BROOM=np.array([-.65,.40,.915])
GRAINS=24
COLORS={'ceramic':'.87 .91 .88','doors':'.36 .55 .48','oak':'.55 .33 .18','chrome':'.68 .72 .74','terry':'.15 .42 .48','toiletry':'.70 .27 .14','paper':'.86 .78 .64','pan':'.18 .37 .37','grit':'.53 .30 .12','water':'.13 .55 .65','bristle':'.20 .17 .12','brush':'.66 .39 .15','gardenstone':'.58 .56 .48','wall':'.78 .80 .72','pool_tile':'.25 .57 .63'}
def vec(a):return ' '.join(f'{n:.8g}' for n in a)
def add(parent,kind,**attr):return ET.SubElement(parent,kind,{k:str(v) for k,v in attr.items()})
def shape(parent,name,typ,pos,size,role,solid=True,**kwargs):
    attrs=dict(name=name,type=typ,pos=vec(pos),size=vec(size),material=role)
    if not solid:attrs.update(contype=0,conaffinity=0,mass=0)
    return add(parent,'geom',**(attrs|kwargs))
def box(p,n,pos,size,mat,*args,**kw):return shape(p,n,'box',pos,size,mat,*args,**kw)
def cyl(p,n,pos,size,mat,*args,**kw):return shape(p,n,'cylinder',pos,size,mat,*args,**kw)
def rod(p,n,a,b,r,mat,solid=False):
    return add(p,'geom',name=n,type='capsule',fromto=vec([*a,*b]),size=r,material=mat,**({} if solid else dict(contype=0,conaffinity=0,mass=0)))
def body(p,n,pt):return add(p,'body',name=n,pos=vec(pt))
def free(p,n,pt):
    b=body(p,n,pt);add(b,'freejoint',name=n+'_free');return b
def site(b,n,xyz):add(b,'site',name=n,pos=vec(xyz),size='.001',rgba='0 0 0 0')
def grip(eq,n,torquescale='.055',solref='.012 1',solimp='.97 .995 .0007'):add(eq,'weld',name='grasp_'+n,body1='right_gripper',body2=n,active='false',solref=solref,solimp=solimp,torquescale=torquescale)
def camera(w,name,eye,target,fov):
    z=np.subtract(eye,target);z/=np.linalg.norm(z);x=np.cross([0.,0.,1.],z);x/=np.linalg.norm(x)
    add(w,'camera',name=name,pos=vec(eye),xyaxes=vec([*x,*np.cross(z,x)]),fovy=fov)
def vanity(w,eq):
    box(w,'room_floor',(0,0,-.055),(3.4,3,.055),'floor')
    # Open bowl with a continuous solid counter at the sides. Nothing sits in front of the tap.
    x=-.67
    box(w,'vanity_plinth',(x,.77,.055),(.49,.229,.055),'oak')
    box(w,'vanity_cabinet',(x,.77,.392),(.52,.255,.286),'doors')
    for v in (-1,1):
        box(w,'basin_flank'+str(v),(x+v*.41,.72,.891),(.13,.245,.019),'ceramic')
        box(w,'basin_wall'+str(v),(x+v*.285,.72,.798),(.007,.175,.085),'ceramic')
        box(w,'cabinet_cheek'+str(v),(x+v*.506,.76,.775),(.011,.23,.10),'doors')
    for name,y,hy in [('front',.492,.047),('back',.932,.033)]:
        box(w,'basin_rim_'+name,(x,y,.891),(.280,hy,.019),'ceramic')
    for name,y in [('front',.542),('back',.895)]:box(w,'bowl_'+name,(x,y,.798),(.285,.007,.085),'ceramic')
    box(w,'bowl_bottom',(x,.72,.716),(.285,.18,.009),'ceramic')
    cyl(w,'drain',(x,.71,.7256),(.024,.0006),'chrome',False)
    for k in range(4):box(w,'drain_slot'+str(k),(x,.702+k*.004,.7264),(.013,.0008,.0002),'bristle',False)
    for y,z,yt,zt in [(.93,.91,.93,1.05),(.93,1.05,.89,1.091),(.89,1.091,.77,1.091),(.77,1.091,.744,1.058)]:
        rod(w,'faucet_'+str(y)+'_'+str(z),(x,y,z),(x,yt,zt),.012,'chrome',True)
    cyl(w,'tap_base',(x,.93,.912),(.031,.005),'chrome')
    box(w,'infrared_window',(x,.916,.981),(.009,.001,.005),'bristle',False)
    # The storage unit stands next to the basin. A fully supported cross rail defines usable height.
    xc=DRAWER_X
    box(w,'drawer_kick',(xc,.762,.095),(.354,.196,.095),'oak')
    box(w,'drawer_base',(xc,.762,.422),(.387,.236,.232),'doors')
    for s in (-1,1):box(w,'cabinet_jamb'+str(s),(xc+s*.374,.756,.778),(.012,.244,.124),'doors')
    box(w,'vanity_counter',(xc,.755,.915),(.395,.253,.013),'ceramic')
    box(w,'header',(xc,.560,.886),(.353,.015,.015),'oak',priority=4,solref='.005 1')
    box(w,'cabinet_back',(xc,.992,.78),(.35,.008,.124),'oak')
    d=body(w,'drawer',(xc,0,0));add(d,'joint',name='extension',type='slide',axis='0 -1 0',range='0 .287',damping='16',frictionloss='3',armature='.18')
    box(d,'drawer_tray',(0,.713,FLOOR-.008),(.337,.183,.008),'oak',mass=.55,friction='1.3 .006 .001')
    box(d,'drawer_front',(0,.522,.752),(.355,.009,.084),'doors',mass=.30)
    box(d,'drawer_back',(0,.888,.724),(.331,.006,.041),'oak',mass=.06)
    for i in (-1,1):
        box(d,'drawer_side'+str(i),(i*.330,.70,.717),(.007,.178,.034),'oak',mass=.08)
        box(w,'fixed_runner'+str(i),(xc+i*.345,.728,.682),(.004,.198,.006),'chrome',False)
        rod(d,'pull_mount'+str(i),(i*.04,.512,.768),(i*.04,.429,.768),.005,'chrome')
    rod(d,'pull_horizontal',(-.045,.429,.768),(.045,.429,.768),.007,'chrome')
    box(d,'pull_grip',(0,.425,.785),(.012,.013,.022),'oak',mass=.03)
    site(d,'pickup_drawer',(0,HANDLE[1],HANDLE[2]));grip(eq,'drawer')
    c=free(w,'case',(CASE[0],CASE[1]-AJAR,FLOOR+.0004))
    box(c,'case_shell',(0,0,.092),(.030,.042,.092),'toiletry',mass=.115,friction='1.8 .02 .003')
    box(c,'case_lid',(0,0,.192),(.03,.042,.008),'toiletry',mass=.011)
    box(c,'case_seam',(0,0,.182),(.0303,.0423,.001),'paper',False)
    box(c,'case_label',(0,-.0422,.075),(.021,.0003,.018),'paper',False)
    site(c,'pickup_case',(0,0,.175));grip(eq,'case')
    # Short retaining rails keep toiletries upright when the drawer slides.
    for ix in (-1,1):
        box(d,'organizer'+str(ix),(.105+ix*.039,.594,.704),(.006,.063,.021),'oak',mass=.015)
    box(d,'organizer_rear',(.105,.633,.705),(.037,.007,.022),'oak',mass=.02)
    box(d,'organizer_front',(.105,.528,.707),(.037,.009,.024),'oak',mass=.02)
    c=free(w,'cloth',CLOTH);box(c,'folded_cloth',(0,0,0),(.028,.068,.011),'terry',mass=.052,friction='1.1 .012 .001')
    for n in range(3):rod(c,'hem_'+str(n),(-.027,-.054,-.006+n*.005),(.027,-.054,-.006+n*.005),.00125,'terry')
    site(c,'pickup_cloth',(0,-.044,.009));grip(eq,'cloth')
    camera(w,'overview',(1.84,-2.48,1.84),(-.02,.53,.69),40)
    camera(w,'detail',(.76,-.22,1.00),(.52,.43,.783),37)
def pool(w,eq):
    # Deck and sunken water have separate collision surfaces; there is no invisible floor under the waterline.
    for n,x,y,hx,hy in [('main',-1.89,0,2.11,3.2),('front',1.26,-1.51,1.04,1.79),('back',1.26,2.72,1.04,.9),('far',3.15,0,.85,3.2)]:
        box(w,'deck_'+n,(x,y,-.07),(hx,hy,.07),'gardenstone')
    box(w,'pool_bottom',(1.26,1.05,-.258),(1.04,.77,.012),'pool_tile')
    box(w,'pool_water',(1.26,1.05,-.085),(1.037,.768,.001),'water',False)
    for n,x,y,hx,hy in [('edge',.215,1.05,.005,.77),('front',1.26,.275,1.04,.005),('rear',1.26,1.825,1.04,.005)]:
        box(w,'coping_'+n,(x,y,-.128),(hx,hy,.123),'pool_tile')
    # A low, three-sided open pan sits flush on the paving. Beads roll up the thin 1 mm lip.
    box(w,'pan_plate',(-.351,.51,.0005),(.135,.137,.0005),'pan')
    for sign in (-1,1):box(w,'pan_side'+str(sign),(-.351,.51+sign*.137,.020),(.135,.003,.020),'pan')
    box(w,'pan_back',(-.489,.51,.025),(.003,.14,.025),'pan')
    rod(w,'pan_handle',(-.485,.51,.034),(-.597,.51,.062),.008,'chrome')
    tool=free(w,'broom',BROOM)
    cyl(tool,'wood_shaft',(0,0,-.418),(.012,.422),'brush',mass=.14)
    cyl(tool,'handle_grip',(0,0,-.012),(.014,.032),'bristle',mass=.025)
    box(tool,'broom_ferrule',(0,0,-.847),(.021,.095,.014),'brush',mass=.09)
    box(tool,'bristle_strip',(0,0,-.882),(.011,.118,.027),'bristle',mass=.045,friction='.50 .003 .0005',solref='.008 1',solimp='.95 .995 .001')
    for row,sx in enumerate((-1,1)):
        for j in range(-14,15):
            rod(tool,f'bristle_tuft_{row}_{j}',(sx*.004,j*.0074,-.859),(sx*.011,j*.0080,-.910),.0018,'bristle')
    site(tool,'pickup_broom',(0,0,0));grip(eq,'broom',torquescale='.55',solref='.008 1',solimp='.98 .998 .0005')
    add(eq,'weld',name='rack_hold',body1='world',body2='broom',active='true',solref='.005 1',solimp='.98 .998 .0005')
    box(w,'rack_base',(-.68,.567,.012),(.079,.042,.012),'pan')
    box(w,'rack_post',(-.692,.567,.37),(.012,.013,.345),'chrome')
    rod(w,'rack_arm',(-.692,.567,.704),(-.65,.416,.704),.006,'chrome')
    for s in (-1,1):
        rod(w,'rack_jaw'+str(s),(-.65,.416,.704),(-.65+s*.015,.394,.704),.0045,'chrome')
    rng=np.random.default_rng(17)
    for i in range(GRAINS):
        x=(i%4-1.5)*.022+rng.uniform(-.004,.004);y=.51+(i//4-2.5)*.020+rng.uniform(-.002,.002)
        rad=.0084+(i%3)*.0006
        b=free(w,'grain_'+str(i),(x,y,rad+.0003))
        shape(b,'grit_'+str(i),'sphere',(0,0,0),(rad,),'grit',mass=.0067,condim=6,friction='.80 .0008 .00022',solref='.006 1')
    camera(w,'overview',(1.43,-2.42,1.50),(-.02,.45,.48),38)
    camera(w,'detail',(.25,-.22,.61),(-.015,.53,.005),46)
def build(case):
    out=HERE/CASES[case];out.mkdir(exist_ok=True)
    r=ET.parse(OMRON/'scene.xml').getroot();r.set('model',case)
    w=r.find('worldbody');assets=r.find('asset')
    for obj in assets:
        if obj.get('file'):obj.set('file',str((OMRON/obj.get('file')).resolve()))
    for obj in list(w):
        if obj.tag!='light' and obj.get('name')!='base':w.remove(obj)
    eq=r.find('equality')
    if eq is None:eq=add(r,'equality')
    for role,color in COLORS.items():add(assets,'material',name=role,rgba=color+' 1')
    r.find('option').set('timestep','.0005' if case=='pool' else '.002')
    (vanity if case=='drawer' else pool)(w,eq)
    ET.indent(r);ET.ElementTree(r).write(out/'scene.xml')
    return out
