"""逐日 / Chasing the Sun - scene assembly, animation and rendering.
usage:  python3 film.py stills OUTDIR t1 t2 ...      |  python3 film.py range OUTDIR f0 f1
env: W,H,SPP,GPU=1,DENSE,FLOCK=0/1,MBLUR=0/1"""
import sys, os, math, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import bpy, numpy as np
from mathutils import Vector, Matrix, Quaternion
from pel import common as C, bl, world, render, pelican, bike, scenery
from pel.common import smooth, clamp, roadZ, roadC, roadCs, roadZs, terrainH, worldTime, flightZ, V, WJ, XJ, ZJ, FPS, DUR, SUN, LANE, arclen

E=lambda k,d: type(d)(os.environ.get(k,d))
R_=math.radians

class Film:
    def __init__(s):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        s.sc=render.setup(E('W',1280),E('H',536),E('SPP',48),gpu=bool(E('GPU',0)),mblur=bool(E('MBLUR',1)))
        t0=time.time()
        s.world=world.build_sky(); world.build_terrain(); world.build_sea(); world.build_road(); world.build_guardrail()
        dense=E('DENSE',1.0)
        if dense>0: scenery.build_grass(dense); scenery.build_props(dense)
        s.rider=bl.empty('Rider'); s.bike=bike.Bike(s.rider); s.pel=pelican.Pelican(s.bike.root,bike.SADDLE)
        s.flock=[]
        if E('FLOCK',1):
            for i in range(8):
                e=bl.empty('FlockBird'); p=pelican.Pelican(e,(0,0,0),flight=True)
                s.flock.append(dict(e=e,p=p,side=1 if i%2 else -1,rank=(i>>1)+1,ph=i*1.3))
        s.cam=render.make_camera(); s.cam.data.dof.use_dof=True
        s.focus=bl.empty('Focus'); s.cam.data.dof.focus_object=s.focus
        s.time_nodes=[n for nt in [s.world.node_tree]+[m.node_tree for m in bpy.data.materials if m.node_tree] for n in nt.nodes if n.name=='TIME']
        s.end0=s.rider_state(worldTime(59.5))
        print('scene built in %.1fs, objects=%d'%(time.time()-t0,len(bpy.data.objects)),flush=True)

    # ------------------------------------------------------------ rider
    def rider_state(s,w):
        x=V*w
        if w<=WJ:
            wb=bike.WB; cs=float(roadCs(x)); cz=float(roadZs(x)); k=1/math.sqrt(1+cs*cs)
            pr=C.pathPoint(x-wb/2*k); pf=C.pathPoint(x+wb/2*k)
            fwd=Vector(pf-pr).normalized(); org=Vector((pr+pf)/2)
            # lateral curvature -> lean + steer
            ypp=float(roadC(x+1)-2*roadC(x)+roadC(x-1)); kap=ypp/(1+cs*cs)**1.5
            lean=math.atan(V*V*kap/9.81)+0.022*math.sin(w*8.4*0.5*2)
            steer=math.atan(wb*kap)*1.0+0.018*math.sin(w*2.3)
            spin=arclen(x)/bike.RW
        else:
            u=w-WJ; z=flightZ(u); dz=(flightZ(u+0.02)-z)/0.02
            org=Vector((x,LANE,z+0.02)); fwd=Vector((V,0,dz*0.85)).normalized()
            lean=0.10*math.sin(u*0.9)*smooth(0.2,1.5,u)+0.55*math.sin((w-47.2)*0.75)*smooth(47.2,47.7,w)*(1-smooth(52.0,52.6,w)); steer=0.0
            spin=arclen(XJ)/bike.RW+(x-XJ)/bike.RW*max(0.35,1-0.2*u)
        left=Vector((0,0,1)).cross(fwd).normalized(); up=fwd.cross(left).normalized()
        M=Matrix((fwd,left,up)).transposed().to_4x4()@Matrix.Rotation(-lean,4,'X'); M.translation=org
        Fh=Vector((fwd.x,fwd.y,0)).normalized(); Lh=Vector((-Fh.y,Fh.x,0))
        return dict(M=M,org=org,F=Fh,L=Lh,spin=spin,steer=steer,x=x,air=w>WJ,u=max(0,w-WJ),spread=float(smooth(WJ-0.05,WJ+0.9,w)))

    # ------------------------------------------------------------ shots
    def shot(s,t,rs):
        P=rs['org']; F=rs['F']; L=rs['L']; Z=Vector((0,0,1)); roll=0.0; fstop=4.0; expo=0.0
        def road_z(p): return float(roadZ(p.x))
        if t<6:
            u=t/6; i=0; pos=P+F*(-30+11*u)+L*(22-7*u)+Z*(13-5*u); look=P+F*13+Z*0.6-L*3; fov=34; fstop=11
        elif t<12:
            u=(t-6)/6; u2=u*u*(3-2*u); i=1; pos=P+F*(-1.30+1.15*u2)-L*(1.05+1.15*u2); pos.z=road_z(pos)+0.15+0.55*u2
            look=P+F*(0.05+0.15*u2)+Z*(0.26+0.92*u2); fov=44; fstop=2.8
        elif t<21:
            u=(t-12)/9; i=2; pos=P+F*(1.2+2.0*u)+L*9.5; pos.z=max(float(terrainH(pos.x,pos.y))+0.6,P.z+1.05)
            look=P+F*0.25+Z*0.95; fov=12.5; fstop=2.0; expo=0.25
        elif t<30:
            u=(t-21)/9; i=3; pos=P+F*(5.8-4.1*u)-L*(0.75-0.55*u); pos.z=road_z(pos)+0.28+0.32*u
            look=P+Z*1.05; fov=37; fstop=2.8
        elif t<39:
            u=(t-30)/9; i=4; a=R_(262-170*u); r=4.9-0.8*u; pos=P+F*(math.cos(a)*r)+L*(math.sin(a)*r)+Z*(1.0+1.1*math.sin(math.pi*u))
            look=P+Z*1.15+F*0.3; fov=36; fstop=2.8; expo=0.1
        elif t<44:
            u=(t-39)/5; i=5; pos=P-F*(4.3-1.4*u)+L*0.55+Z*(1.35-0.5*u); look=P+F*4+Z*1.45; fov=54; fstop=4
            pos.z+=0.012*math.sin(t*37)+0.008*math.sin(t*23); look.z+=0.02*math.sin(t*29); roll=0.004*math.sin(t*17)
        elif t<52:
            u=(t-44)/8; i=6; pos=Vector((XJ+30,LANE-3.2,ZJ+7.2)); look=P+Z*0.8
            d=(look-pos).length; fov=float(clamp(math.degrees(2*math.atan(2.0/d)),6.5,42)); fstop=4; expo=0.0
        elif t<59.5:
            u=(t-52)/7.5; i=7; D=38.0; SH=Vector((SUN[0],SUN[1],0)).normalized(); PP=Vector((-SH.y,SH.x,0)); tanE=SUN[2]/math.hypot(SUN[0],SUN[1])
            look=P+Z*0.95; pos=look-SH*D-Z*(D*tanE)+PP*(-0.8+1.6*u)+Z*(0.2-0.4*u); fov=4.9; fstop=11; expo=-2.75
        else:
            u=(t-59.5)/6.5; i=8; e=s.end0; pos=e['org']-e['F']*5.5+e['L']*0.9+Z*2.6; look=P+Z*1.6+e['F']*2; fov=30-8*u; fstop=5.6; expo=-0.45
        g=max(float(terrainH(pos.x,pos.y)),0.0)+0.25
        if pos.z<g: pos.z=g
        return i,pos,look,fov,roll,fstop,expo

    # ------------------------------------------------------------ per-frame
    def set_time(s,t):
        t=max(0.0,min(DUR,t)); w=worldTime(t); rs=s.rider_state(w)
        s.rider.matrix_world=rs['M']
        ped,ph=s.bike.pose(rs['spin'],rs['steer']); s.pel.pose_legs(ped,ph)
        f=rs['spread']; om=4.2
        A=0.62+0.34*(1-float(smooth(WJ+1.6,WJ+3.2,w))); flap=0.14+A*math.sin(om*w); flex=(0.5+0.5*math.cos(om*w))*0.9
        s.pel.pose_wings(f,flap*f,flex*f); s.pel.pose_neck(float(smooth(WJ+0.35,WJ+1.7,w)))
        s.pel.bird.location=Vector(bike.SADDLE)+Vector((0,0,0.004*math.sin(2*ph)-0.03*f*math.sin(om*w-0.6)))
        s.pel.pose_scarf(w,1.0,lift=-0.12*f)
        for n in s.time_nodes: n.outputs[0].default_value=t
        # flock
        if s.flock:
            P=rs['org']; gj=float(smooth(46.6,49.4,w)); xr=min(rs['x'],XJ); cz=float(roadZ(xr))+5.0
            for b in s.flock:
                r=b['rank']; sd=b['side']
                a=Vector((P.x+10-r*1.7,-27+sd*r*1.4,cz+r*0.2)); c=Vector((P.x+2.0+r*2.6,LANE+sd*(1.6+r*2.3),P.z+0.35+r*0.5-0.3*sd))
                jx=math.sin(b['ph']*7.1)*1.4; jy=math.sin(b['ph']*3.3)*0.9; jz=math.sin(b['ph']*5.7)*0.7
                p=a.lerp(c,gj)+Vector((jx,jy,jz)); p.z+=0.35*math.sin(w*(1.1+0.2*math.sin(b['ph']))+b['ph'])
                roll=0.16*math.sin(w*0.7+b['ph']*2.3)+0.1*math.sin(b['ph']*4)
                b['e'].matrix_world=Matrix.Translation(p)@Matrix.Rotation(roll,4,'X')
                ob_=om*(0.82+0.07*((b['rank']*3+b['side'])%5)); fl=0.10+0.46*math.sin(ob_*w+b['ph']*1.9); fx=(0.5+0.5*math.cos(ob_*w+b['ph']*1.9))*0.9
                b['p'].pose_wings(1.0,fl,fx)
        i,pos,look,fov,roll,fstop,expo=s.shot(t,rs)
        render.aim(s.cam,pos,look,fov,roll)
        s.focus.location=rs['org']+Vector((0,0,0.9)); s.cam.data.dof.aperture_fstop=fstop
        s.sc.view_settings.exposure=-1.6+expo
        return i

def main():
    a=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    mode,out=a[0],os.path.abspath(a[1]); os.makedirs(out,exist_ok=True)
    film=Film(); sc=film.sc
    def handler(scene,*_):
        film.set_time((scene.frame_current+scene.frame_subframe)/FPS)
    bpy.app.handlers.frame_change_pre.append(handler)
    if mode=='stills':
        for ts in a[2:]:
            t=float(ts); fr=t*FPS; sc.frame_set(int(fr),subframe=fr-int(fr)); sc.render.filepath=os.path.join(out,'s_%05.1f.jpg'%t)
            t0=time.time(); bpy.ops.render.render(write_still=True); print('still',t,'%.1fs'%(time.time()-t0),flush=True)
    else:
        f0,f1=int(a[2]),int(a[3])
        for fr in range(f0,f1):
            fp=os.path.join(out,'f_%05d.jpg'%fr)
            if os.path.exists(fp): continue
            sc.frame_set(fr); sc.render.filepath=fp; t0=time.time(); bpy.ops.render.render(write_still=True); print('frame',fr,'%.1fs'%(time.time()-t0),flush=True)
if __name__=='__main__': main()
