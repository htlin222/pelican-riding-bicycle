"""A small vintage steel bicycle. Bike frame: origin on the ground between the wheels, +X forward, +Y left, +Z up."""
import bpy, math, numpy as np
from mathutils import Vector, Matrix, Quaternion
from .bl import *
from . import sdf

RW=0.27; WB=0.90; AXR=np.array([-0.45,0,RW]); AXF=np.array([0.45,0,RW]); BB=np.array([-0.03,0,0.265]); CRANK=0.11; PEDY=0.105
ST=np.array([-0.20,0,0.56]); HT=np.array([0.27,0,0.625]); HB=np.array([0.305,0,0.505]); SADDLE=(-0.225,0,0.645)

def torus(R,r,nu=64,nv=12,sy=1.0):
    a=np.linspace(0,2*np.pi,nu,endpoint=False); b=np.linspace(0,2*np.pi,nv,endpoint=False)
    rr=R+r*np.cos(b)[None,:]
    V=np.stack([rr*np.cos(a)[:,None],np.repeat((r*sy*np.sin(b))[None,:],nu,0),rr*np.sin(a)[:,None]],-1).reshape(-1,3)
    return V,grid_faces(nu,nv,wrap_u=True,wrap_v=True)
def box(c,s):
    c=np.asarray(c); s=np.asarray(s)/2
    V=np.array([[x,y,z] for x in(-1,1) for y in(-1,1) for z in(-1,1)])*s+c
    F=np.array([[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]); return V,F

def mats():
    M={}
    m,g,p=new_mat('Paint'); n=g.noise(g.N('ShaderNodeTexCoord').outputs['Object'],900.0,detail=1)
    setp(g,p,color=g.mix(g.math('MULTIPLY',n,0.25),srgb(0x8e0f16),srgb(0xb81a1f)),rough=0.32,metal=0.25,coat=1.0,coatr=0.06); M['paint']=m
    m,g,p=new_mat('Cream'); setp(g,p,color=srgb(0xe9dfc6),rough=0.3,coat=0.8,coatr=0.1); M['cream']=m
    m,g,p=new_mat('Chrome'); setp(g,p,color=(0.82,0.82,0.83,1),rough=0.09,metal=1.0); M['chrome']=m
    m,g,p=new_mat('Alu'); n=g.noise(g.N('ShaderNodeTexCoord').outputs['Object'],300.0,detail=2)
    setp(g,p,color=(0.72,0.73,0.74,1),rough=g.mixf(n,0.22,0.38),metal=1.0); M['alu']=m
    m,g,p=new_mat('Steel'); setp(g,p,color=(0.33,0.33,0.34,1),rough=0.3,metal=1.0); M['steel']=m
    m,g,p=new_mat('Tire'); oc=g.N('ShaderNodeTexCoord').outputs['Object']; s=g.N('ShaderNodeSeparateXYZ',{0:oc})
    r=g.math('SQRT',g.math('ADD',g.math('MULTIPLY',s.outputs[0],s.outputs[0]),g.math('MULTIPLY',s.outputs[2],s.outputs[2])))
    tread=g.maprange(r,0.2535,0.2555)
    ang=g.math('ARCTAN2',s.outputs[2],s.outputs[0])
    knob=g.math('MULTIPLY',g.math('SINE',g.math('ADD',g.math('MULTIPLY',ang,180.0),g.math('MULTIPLY',g.math('ABSOLUTE',s.outputs[1]),900.0))),tread)
    dust=g.noise(oc,60.0,detail=4)
    c=g.mix(tread,srgb(0x6e5a40),srgb(0x101010)); c=g.mix(g.math('MULTIPLY',dust,0.25),c,srgb(0x6b5a48))
    setp(g,p,color=c,rough=0.75,normal=g.bump(knob,strength=0.6,dist=0.0015),spec=0.3); M['tire']=m
    m,g,p=new_mat('Leather'); oc=g.N('ShaderNodeTexCoord').outputs['Object']; n=g.noise(oc,220.0,detail=4,rough=.7); n2=g.noise(oc,18.0,detail=3)
    setp(g,p,color=g.mix(n2,srgb(0x8a4a1c),srgb(0xb0652a)),rough=g.mixf(n2,0.38,0.55),normal=g.bump(n,strength=0.25,dist=0.001),coat=0.2,coatr=0.3); M['leather']=m
    m,g,p=new_mat('Wicker'); oc=g.N('ShaderNodeTexCoord').outputs['Object']
    w1=g.N('ShaderNodeTexWave',{'Vector':oc,'Scale':42.0,'Distortion':0.6,'Detail':1.0},wave_type='BANDS',bands_direction='Z').outputs['Fac']
    w2=g.N('ShaderNodeTexWave',{'Vector':oc,'Scale':18.0,'Distortion':0.3},wave_type='BANDS',bands_direction='DIAGONAL').outputs['Fac']
    h=g.math('MULTIPLY',w1,g.math('ADD',0.5,g.math('MULTIPLY',w2,0.5)))
    setp(g,p,color=g.mix(h,srgb(0x4a3420),srgb(0x9a8058)),rough=0.7,normal=g.bump(h,strength=0.9,dist=0.004),spec=0.3); M['wicker']=m
    m,g,p=new_mat('Fish'); oc=g.N('ShaderNodeTexCoord').outputs['Object']; s=g.N('ShaderNodeSeparateXYZ',{0:oc})
    sc_=g.N('ShaderNodeTexVoronoi',{'Vector':oc,'Scale':260.0},feature='F1').outputs['Distance']
    back=g.maprange(s.outputs[2],-0.005,0.02,smooth=True)
    setp(g,p,color=g.mix(back,(0.75,0.78,0.8,1),(0.08,0.16,0.22,1)),rough=0.22,metal=0.75,normal=g.bump(sc_,strength=0.35,dist=0.001),coat=0.6,coatr=0.1); M['fish']=m
    m,g,p=new_mat('Brass'); setp(g,p,color=(0.83,0.62,0.25,1),rough=0.18,metal=1.0); M['brass']=m
    m,g,p=new_mat('Amber'); setp(g,p,color=(0.9,0.35,0.02,1),rough=0.15,emit=(0.9,0.3,0.02,1),emits=0.4); M['amber']=m
    return M

class Bike:
    def __init__(s,parent=None):
        M=mats(); s.M=M
        s.root=empty('Bike',parent)
        def obj(name,VF,mat,par=None,smooth=True):
            o=mesh_obj(name,VF[0],VF[1],smooth=smooth); o.data.materials.append(M[mat]); o.parent=par or s.root; return o
        def T(a,b,r,seg=12): return tube_mesh([a,(np.asarray(a)+np.asarray(b))/2,b],r,seg=seg)
        # ---- frame
        parts=[T(ST,BB,0.0135),T(ST-[0,0,0.03],HT-[0,0,0.025],0.0125),T(BB,HB+[0,0,0.02],0.0145),T(HT+[0,0,0.012],HB-[0,0,0.012],0.017),
               T(BB-[0,0.05,0],BB+[0,0.05,0],0.021)]
        for sy in (1,-1):
            parts.append(tube_mesh([BB+[-0.02,sy*0.03,0],(BB+AXR)/2+[0,sy*0.05,-0.004],AXR+[0,sy*0.058,0]],[0.010,0.0085,0.0075],seg=8))
            parts.append(tube_mesh([ST+[0,sy*0.012,-0.04],(ST+AXR)/2+[0,sy*0.042,0],AXR+[0,sy*0.058,0]],[0.008,0.007,0.0065],seg=8))
            parts.append(sdf_blob(AXR+[0,sy*0.058,0],0.014))
        obj('Frame',join(parts),'paint')
        obj('SeatPost',T(ST,ST+[-0.012,0,0.07],0.011),'chrome')
        # saddle
        VOX=0.004; P,lo=sdf.grid((-0.36,-0.09,0.60),(-0.07,0.09,0.67),VOX)
        d=sdf.ellipsoid(P,(-0.275,0,0.632),(0.062,0.072,0.017)); d=sdf.smin(d,sdf.roundcone(P,(-0.26,0,0.632),(-0.10,0,0.630),0.03,0.016),0.035)
        d=np.maximum(d,-(P[...,2]-0.619)); d=np.maximum(d,P[...,2]-0.6455)
        obj('Saddle',sdf.mesh(d,lo,VOX,3),'leather')
        for sy in (1,-1): obj('SaddleRail',tube_mesh([(-0.30,sy*0.02,0.622),(-0.24,sy*0.02,0.612),(-0.19,sy*0.012,0.612),(-0.12,0,0.624)],0.0035,seg=6),'chrome')
        # rear fender
        obj('FenderR',fender(AXR,math.radians(8),math.radians(200)),'alu');
        # chain + cog
        cy=-0.05; ch=[]
        r1,r2=0.076,0.03; c1=BB+[0,cy,0]; c2=AXR+[0,cy,0]
        for t in np.linspace(-np.pi/2,np.pi/2,14): ch.append(c1+[r1*math.cos(t),0,r1*math.sin(t)])
        for t in np.linspace(np.pi/2,3*np.pi/2,10): ch.append(c2+[r2*math.cos(t),0,r2*math.sin(t)])
        ch.append(ch[0]); ch.append(ch[1])
        obj('Chain',tube_mesh(ch,0.0042,seg=6,cap=False),'steel')
        V,F=torus(r2-0.003,0.004,24,6); V=V+c2; obj('Cog',(V,F),'steel')
        # ---- wheels
        s.wheelR=s._wheel(empty('WheelR',s.root,tuple(AXR)))
        # ---- crank
        s.crank=empty('Crank',s.root,tuple(BB))
        V,F=torus(r1-0.004,0.005,40,6); V[:,1]+=cy; parts=[(V,F)]
        for k in range(5):
            a=k*2*np.pi/5; parts.append(T((0,cy,0),(0.072*math.sin(a),cy,0.072*math.cos(a)),0.006,6))
        parts.append(T((0,-0.062,0),(0,0.062,0),0.009,8))
        for k in range(36):
            a=k*2*np.pi/36; parts.append(box((0.079*math.sin(a),cy,0.079*math.cos(a)),(0.006,0.003,0.006)))
        obj('Chainring',join(parts),'alu',s.crank)
        arms=[]
        for sy,sg in ((1,1),(-1,-1)):
            arms.append(tube_mesh([(0,sy*0.062,0),(0,sy*0.066,sg*CRANK*0.5),(0,sy*0.066,sg*CRANK)],[0.011,0.009,0.009],seg=8))
            arms.append(T((0,sy*0.066,sg*CRANK),(0,sy*(PEDY+0.04),sg*CRANK),0.005,6))
        obj('CrankArms',join(arms),'alu',s.crank)
        s.pedals=[]
        for sy,sg in ((1,1),(-1,-1)):
            e=empty('Pedal',s.crank,(0,sy*PEDY,sg*CRANK))
            parts=[box((0,0,0),(0.085,0.07,0.012))]+[box((sx*0.036,0,0.004),(0.008,0.075,0.016)) for sx in (1,-1)]
            obj('PedalBody',join(parts),'steel',e,smooth=False)
            s.pedals.append(e)
        # ---- steering assembly (built in bike coords, stored in steer-local coords)
        ax=Vector(tuple(HT-HB)).normalized(); s.steer=empty('Steer',s.root,tuple(HB)); s.q_steer=ax.to_track_quat('Z','Y'); s.steer.rotation_quaternion=s.q_steer
        Ri=np.array(s.q_steer.to_matrix().inverted())
        def L(VF): return (np.asarray(VF[0])-HB)@Ri.T, VF[1]
        s._L=L
        fork=[T(HB+[0,0,0.01],HB-[0.004,0,0.035],0.016),T(HB+[-0.006,-0.05,-0.035],HB+[-0.006,0.05,-0.035],0.012,8)]
        for sy in (1,-1):
            fork.append(tube_mesh([HB+[-0.006,sy*0.048,-0.035],(0.345,sy*0.048,0.40),(0.40,sy*0.048,0.315),(0.445,sy*0.048,0.275),AXF+[0,sy*0.048,0]],[0.011,0.010,0.008,0.007,0.0065],seg=8))
            fork.append(sdf_blob(AXF+[0,sy*0.048,0],0.012))
        obj('Fork',L(join(fork)),'paint',s.steer)
        stem=[T(HT,HT+[-0.018,0,0.075],0.011),tube_mesh([HT+[-0.018,0,0.075],HT+[0.0,0,0.092],HT+[0.045,0,0.09]],0.011,seg=10)]
        bc=HT+[0.045,0,0.09]; bar=[]
        for sy in (1,-1):
            bar.append(tube_mesh([bc,bc+[0.012,sy*0.07,0.004],bc+[-0.01,sy*0.15,0.018],bc+[-0.07,sy*0.205,0.022],bc+[-0.15,sy*0.225,0.016],bc+[-0.20,sy*0.228,0.012]],0.0105,seg=10))
        obj('Stem',L(join(stem+bar)),'chrome',s.steer)
        cab=[tube_mesh([bc+[-0.10,0.215,0.02],bc+[0.02,0.12,0.06],HT+[0.03,0.02,0.02],HB+[0.03,0.0,-0.05]],0.0028,seg=5),tube_mesh([bc+[-0.10,-0.215,0.02],bc+[0.02,-0.12,0.06],HT+[0.02,-0.02,0.0],HT+[-0.05,-0.016,-0.03]],0.0028,seg=5)]
        o_=obj('Cables',L(join(cab)),'tire',s.steer)
        gr=[]
        for sy in (1,-1): gr.append(tube_mesh([bc+[-0.115,sy*0.222,0.019],bc+[-0.16,sy*0.226,0.015],bc+[-0.205,sy*0.228,0.012]],[0.0155,0.0165,0.0155],seg=12))
        obj('Grips',L(join(gr)),'leather',s.steer)
        V,F=uv_hemi(0.024); V=V+(bc+[-0.02,0.11,0.03]); obj('Bell',L((V,F)),'brass',s.steer)
        obj('FenderF',L(fender(AXF,math.radians(45),math.radians(175))),'alu',s.steer)
        # basket + fish
        bcx=np.array([0.455,0,0.70]); sx,sy_,sz=0.19,0.27,0.15
        bv=[];bf=[]
        nx,ny=8,10; ring=[]
        for i in range(nx): ring.append((-sx/2+sx*i/nx,-sy_/2))
        for i in range(ny): ring.append((sx/2,-sy_/2+sy_*i/ny))
        for i in range(nx): ring.append((sx/2-sx*i/nx,sy_/2))
        for i in range(ny): ring.append((-sx/2,sy_/2-sy_*i/ny))
        ring=np.array(ring); nz=7
        for k in range(nz):
            q=k/(nz-1); scl=0.84+0.16*q
            for (x,y) in ring: bv.append(bcx+[x*scl,y*scl,-sz/2+sz*q])
        bV=np.array(bv); bF=grid_faces(nz,len(ring),wrap_v=True)
        nb=len(bV); bV=np.vstack([bV,bcx+[0,0,-sz/2]]); bot=np.array([[nb,(j+1)%len(ring),j,nb] for j in range(len(ring))])
        bo=obj('Basket',L((bV,np.vstack([bF,bot]))),'wicker',s.steer); md=bo.modifiers.new('S','SOLIDIFY'); md.thickness=0.007
        top=[bcx+[x,y,sz/2] for (x,y) in ring]; top+=top[:2]
        obj('BasketRim',L(tube_mesh(top,0.0065,seg=8,cap=False)),'wicker',s.steer)
        for sy in (1,-1): obj('BasketArm',L(T(bc+[0.0,sy*0.06,0],bcx+[-sx/2,sy*0.06,sz/2-0.01],0.004,6)),'chrome',s.steer)
        fV,fF=fish_geo()
        for (pos,rot) in (((0.445,0.035,0.745),(0.0,-1.05,0.5)),((0.47,-0.05,0.725),(0.3,-0.75,-0.7))):
            M4=Matrix.Translation(pos)@Matrix.Rotation(rot[2],4,'Z')@Matrix.Rotation(rot[1],4,'Y')@Matrix.Rotation(rot[0],4,'X')
            Vw=(np.array(M4.to_3x3())@fV.T).T+np.array(pos)
            obj('Fish',L((Vw,fF)),'fish',s.steer)
        s.wheelF=s._wheel(empty('WheelF',s.steer,tuple((AXF-HB)@Ri.T)))
        s.pose(0.0,0.0)
    def _wheel(s,e):
        M=s.M
        def obj(name,VF,mat):
            o=mesh_obj(name,VF[0],VF[1]); o.data.materials.append(M[mat]); o.parent=e; return o
        obj('Tire',torus(0.252,0.018,96,14),'tire')
        V,F=torus(0.229,0.0085,72,8,sy=1.35); obj('Rim',(V,F),'alu')
        sp=[]; N=36
        for i in range(N):
            a=i*2*np.pi/N; side=1 if i%2 else -1; off=0.85*(1 if (i//2)%2 else -1)
            h=np.array([0.02*math.cos(a+off),side*0.027,0.02*math.sin(a+off)]); r=np.array([0.224*math.cos(a),0,0.224*math.sin(a)])
            sp.append(tube_mesh([h,r],0.0028,seg=5,cap=False))
        obj('Spokes',join(sp),'chrome')
        hub=[tube_mesh([(0,-0.05,0),(0,0,0),(0,0.05,0)],0.012,seg=10)]
        for sy in (1,-1): hub.append(tube_mesh([(0,sy*0.024,0),(0,sy*0.03,0)],0.024,seg=16))
        obj('Hub',join(hub),'alu')
        obj('Valve',tube_mesh([(0.224,0,0),(0.19,0,0)],0.003,seg=6),'brass')
        return e
    def pose(s,spin,steer,crank_phase=None):
        """spin: wheel angle (rad). returns pedal positions [left,right] in bike frame."""
        qy=Quaternion((0,1,0),spin)
        s.wheelR.rotation_quaternion=qy
        s.steer.rotation_quaternion=s.q_steer@Quaternion((0,0,1),steer)
        s.wheelF.rotation_quaternion=s.q_steer.inverted()@qy
        ph=spin*0.30 if crank_phase is None else crank_phase
        s.crank.rotation_quaternion=Quaternion((0,1,0),ph)
        for e in s.pedals: e.rotation_quaternion=Quaternion((0,1,0),-ph)
        out=[]
        for sy,sg in ((1,1),(-1,-1)):
            out.append(Vector((BB[0]+sg*CRANK*math.sin(ph),sy*PEDY,BB[2]+sg*CRANK*math.cos(ph))))
        return out,ph

def sdf_blob(c,r):
    V,F=uv_hemi(r,full=True); return V+np.asarray(c),F
def uv_hemi(r,full=False,nu=16,nv=9):
    th=np.linspace(0,np.pi if full else np.pi/2,nv); ph=np.linspace(0,2*np.pi,nu,endpoint=False)
    V=np.stack([r*np.sin(th)[:,None]*np.cos(ph)[None,:],r*np.sin(th)[:,None]*np.sin(ph)[None,:],r*np.cos(th)[:,None]*np.ones(nu)[None,:]],-1).reshape(-1,3)
    return V,grid_faces(nv,nu,wrap_v=True)
def fender(c,a0,a1):
    Rf=0.287; na=40; ps=np.linspace(-1.25,1.25,9); V=[]
    for a in np.linspace(a0,a1,na):
        for p_ in ps:
            rr=Rf-0.016*(1-math.cos(p_)); V.append(c+[rr*math.cos(a),0.026*math.sin(p_),rr*math.sin(a)])
    V=np.array(V); F=grid_faces(na,len(ps))
    # give it thickness
    c_=np.asarray(c); dirv=V-c_; dirv[:,1]=0; dirv/=np.linalg.norm(dirv,axis=1)[:,None]
    V2=V+dirv*0.0018; n=len(V)
    return np.vstack([V,V2]),np.vstack([F[:,::-1],F+n])
def fish_geo():
    VOX=0.003; P,lo=sdf.grid((-0.10,-0.03,-0.045),(0.10,0.03,0.045),VOX)
    d=sdf.ellipsoid(P,(0.01,0,0),(0.075,0.014,0.026))
    d=sdf.smin(d,sdf.roundcone(P,(-0.05,0,0),(-0.075,0,0),0.008,0.005),0.01)
    tail=np.maximum(np.maximum(np.abs(P[...,1])-0.002,np.abs(P[...,2])-(0.004+( -0.072-P[...,0])*1.4)),np.maximum(P[...,0]+0.07,-0.095-P[...,0]))
    d=sdf.smin(d,tail,0.004)
    fin=np.maximum(np.maximum(np.abs(P[...,1])-0.0015,sdf.sphere(P,(0.0,0,0.028),0.022)),-(P[...,2]-0.02))
    d=sdf.smin(d,fin,0.003)
    return sdf.mesh(d,lo,VOX,2)
