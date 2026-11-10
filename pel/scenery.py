"""Grass, wildflowers, scrub, boulders, wind-shaped cypress - all instanced."""
import bpy, math, numpy as np
from .common import *
from .bl import *
from . import sdf

def scatter(name,pts,sizes,yaws,child):
    n=len(pts); s=np.asarray(sizes)*1.5197   # equilateral tri with area = size^2
    a=np.asarray(yaws)[:,None]+np.array([0,2*np.pi/3,4*np.pi/3])[None,:]
    r=s[:,None]/math.sqrt(3)
    V=np.stack([pts[:,None,0]+r*np.cos(a),pts[:,None,1]+r*np.sin(a),np.repeat(pts[:,None,2],3,1)],-1).reshape(-1,3)
    F=np.arange(n*3).reshape(-1,3)
    ob=mesh_obj(name,V,F,smooth=False); ob.instance_type='FACES'; ob.use_instance_faces_scale=True; ob.instance_faces_scale=1.0
    ob.show_instancer_for_render=False; ob.show_instancer_for_viewport=False
    child.parent=ob; return ob

def grass_mat():
    m,g,p=new_mat('Grass')
    uv=g.N('ShaderNodeUVMap').outputs[0]; v=g.N('ShaderNodeSeparateXYZ',{0:uv}).outputs[1]
    oi=g.N('ShaderNodeObjectInfo'); rnd=oi.outputs['Random']
    pos=g.N('ShaderNodeNewGeometry').outputs['Position']
    patch=g.noise(pos,0.09,detail=3)
    patch2=g.maprange(g.noise(pos,0.03,detail=4),0.35,0.65,smooth=True)
    base=g.mix(patch,srgb(0x34481a),srgb(0x6b6a26)); tip=g.mix(patch2,srgb(0x6f8a3a),srgb(0xcfae5c))
    c=g.mix(g.math('POWER',v,1.4),base,tip)
    c=g.mix(g.math('MULTIPLY',rnd,0.3),c,srgb(0x77722c))
    setp(g,p,color=c,rough=0.55,spec=0.3)
    nt=m.node_tree; fogn=[n for n in nt.nodes if n.type=='GROUP'][0]
    tr=g.N('ShaderNodeBsdfTranslucent',{'Color':g.vmath('SCALE',c,scale=1.25).outputs[0]}); mx=g.N('ShaderNodeMixShader',{0:0.45,1:p.outputs[0],2:tr.outputs[0]})
    for l in list(fogn.inputs[0].links): nt.links.remove(l)
    g.link(mx.outputs[0],fogn.inputs[0]); return m
def tuft_geo(seed,nblades=13,h=0.42,spread=0.13):
    rng=np.random.RandomState(seed); V=[];F=[];UV=[]
    for b in range(nblades):
        a=rng.uniform(0,2*np.pi); r0=rng.uniform(0,spread*0.6); hh=h*rng.uniform(0.45,1.0); lean=rng.uniform(0.05,0.5); w=rng.uniform(0.006,0.011)
        dirv=np.array([math.cos(a),math.sin(a),0]); side=np.array([-math.sin(a+rng.uniform(-.6,.6)),math.cos(a),0])
        base=dirv*r0; o=len(V); nseg=4
        for k in range(nseg+1):
            q=k/nseg; c=base+dirv*(lean*hh*q*q)+np.array([0,0,hh*q*(1-0.25*lean*q)]); ww=w*(1-q**1.5)+0.0008
            V.append(c-side*ww); V.append(c+side*ww); UV.append((0,q)); UV.append((1,q))
            if k<nseg: F.append([o+2*k,o+2*k+1,o+2*k+3,o+2*k+2])
    return np.array(V),np.array(F),np.array(UV)
def flower_geo(seed,color_petal):
    rng=np.random.RandomState(seed); parts=[]; 
    V,F=tube_mesh([(0,0,0),(0.01,0,0.12),(0.0,0.01,0.26)],0.002,seg=4,cap=False); parts.append((V,F)); ns=len(V)
    th=np.linspace(0,np.pi*0.45,5); ph=np.linspace(0,2*np.pi,10,endpoint=False); r=0.032
    Vp=np.stack([r*np.sin(th)[:,None]*np.cos(ph)[None,:],r*np.sin(th)[:,None]*np.sin(ph)[None,:],0.26+0.05-r*np.cos(th)[:,None]*np.ones(10)[None,:]],-1).reshape(-1,3)
    parts.append((Vp,grid_faces(5,10,wrap_v=True)))
    V,F=join(parts); return V,F,ns

def build_grass(dense=1.0):
    gm=grass_mat(); rng=np.random.RandomState(1)
    def sample(n,dlo,dhi,xlo=-70,xhi=XJ+2,power=1.0):
        x=rng.uniform(xlo,xhi,n); d=dlo+(dhi-dlo)*rng.uniform(0,1,n)**power
        cs=roadCs(x); y=roadC(x)+d*np.sqrt(1+cs*cs)
        z=terrainH(x,y); return np.stack([x,y,z],1),d
    obs=[]
    specs=[('GrassNear',int(110000*dense),3.72,12,1.0,0.5,0.14),('GrassMid',int(50000*dense),9,40,1.5,0.6,0.22),('GrassSea',int(26000*dense),-6.1,-3.72,1.0,0.42,0.13)]
    for i,(nm,n,dlo,dhi,pw,h,sp) in enumerate(specs):
        P,d=sample(n,dlo,dhi,power=pw)
        keep=(P[:,2]>roadZ(P[:,0])-1.2)|(d>0); P=P[keep]
        V,F,UV=tuft_geo(10+i,nblades=13 if i<2 else 10,h=h,spread=sp)
        t=mesh_obj(nm+'Tuft',V,F,uvs=UV); t.data.materials.append(gm)
        d=d[keep]; sz=rng.uniform(0.65,1.5,len(P))*(1.0 if i!=1 else 1.5)*np.clip((np.abs(d)-3.6)/1.3,0.3,1.0)
        obs.append(scatter(nm,P,sz,rng.uniform(0,6.28,len(P)),t))
    # poppies and lupine-ish blooms
    for nm,col,n in (('Poppy',srgb(0xf07a12),int(5200*dense)),('Bloom',srgb(0x7a56c8),int(2400*dense)),('Daisy',srgb(0xf2ead0),int(2600*dense))):
        P,d=sample(n,4.8,20,power=1.4)
        clump=fbm(P[:,0]*.08+len(nm),P[:,1]*.08,3,41); P=P[clump>0.5]
        V,F,ns=flower_geo(3,col); o=mesh_obj(nm,V,F)
        m,g,p=new_mat(nm+'M'); setp(g,p,color=col,rough=0.5,sss=0.4,sssr=(0.05,0.03,0.01),ssss=0.2)
        ms,gs,ps=new_mat(nm+'Stem'); setp(gs,ps,color=srgb(0x4a5a1e),rough=0.6)
        o.data.materials.append(ms); o.data.materials.append(m)
        mi=np.zeros(len(F),dtype=np.int32); mi[[i for i,f in enumerate(F) if f.min()>=ns]]=1; o.data.polygons.foreach_set('material_index',mi)
        obs.append(scatter(nm+'S',P,rng.uniform(0.7,1.5,len(P)),rng.uniform(0,6.28,len(P)),o))
    return obs

def rock_mat():
    m,g,p=new_mat('Rock'); pos=g.N('ShaderNodeNewGeometry').outputs['Position']
    n=g.noise(pos,1.2,detail=6,rough=.65,dist=.5); v=g.N('ShaderNodeTexVoronoi',{'Vector':pos,'Scale':3.0,'Detail':2.0},feature='F1').outputs['Distance']
    lich=g.maprange(g.noise(pos,2.6,detail=4),0.58,0.68,smooth=True)
    c=g.ramp(n,[(0.25,srgb(0x6e6050)),(0.5,srgb(0x978671)),(0.75,srgb(0xb8a78c))]); c=g.mix(g.math('MULTIPLY',lich,0.6),c,srgb(0xa9a25a))
    setp(g,p,color=c,rough=0.85,normal=g.bump(g.math('ADD',g.math('MULTIPLY',v,0.5),n),strength=0.9,dist=0.08)); return m
def leaf_mat(name,c1,c2):
    m,g,p=new_mat(name); pos=g.N('ShaderNodeNewGeometry').outputs['Position']
    v=g.N('ShaderNodeTexVoronoi',{'Vector':pos,'Scale':14.0,'Detail':1.0},feature='F1').outputs['Distance']; n=g.noise(pos,1.5,detail=4)
    c=g.mix(n,c1,c2); c=g.mix(g.math('MULTIPLY',v,0.5),c,g.vmath('SCALE',c,scale=0.35).outputs[0])
    setp(g,p,color=c,rough=0.55,normal=g.bump(v,strength=1.0,dist=0.12),sheen=0.3,sss=0.15,sssr=(0.1,0.2,0.05),ssss=0.3); return m
def blob(seed,radii,disp,freq,vox,squash=1.0,lean=0.0,nblobs=1):
    rng=np.random.RandomState(seed); R=max(radii)*1.9
    P,lo=sdf.grid((-R,-R,-R*0.3),(R,R,R*1.3),vox)
    d=None
    for i in range(nblobs):
        c=np.array([rng.uniform(-.6,.6)*radii[0]+lean*i*radii[0]*0.35,rng.uniform(-.6,.6)*radii[1],radii[2]*(0.5+0.35*i*squash)]) if nblobs>1 else np.array([0,0,radii[2]*0.45])
        rr=np.array(radii)*(rng.uniform(0.6,1.0) if nblobs>1 else 1.0)
        e=sdf.ellipsoid(P,c,rr); d=e if d is None else sdf.smin(d,e,radii[0]*0.25)
    d=d+(sdf.fbm3(P,freq,4,seed)-0.5)*disp
    return sdf.mesh(d,lo,vox,1)

def build_props(dense=1.0):
    rng=np.random.RandomState(7); obs=[]
    def place(n,dlo,dhi,xlo=-120,xhi=XJ+80,pw=1.0,slope_max=None,zmin=1.0):
        x=rng.uniform(xlo,xhi,n); d=dlo+(dhi-dlo)*rng.uniform(0,1,n)**pw
        y=roadC(x)+d; z=terrainH(x,y); keep=z>zmin
        return np.stack([x,y,z],1)[keep],d[keep]
    rm=rock_mat()
    for k in range(3):
        V,F=blob(20+k,(0.5,0.42,0.36),0.38,2.2,0.035); o=mesh_obj('Rock%d'%k,V,F); o.data.materials.append(rm)
        P1,_=place(int(40*dense),6,70,pw=1.3); P2,_=place(int(220*dense),-34,-6.4)
        P=np.vstack([P1,P2]); sz_=rng.uniform(0.2,1.0,len(P))**2.5*1.9+0.18; P[:,2]-=0.22*sz_
        obs.append(scatter('Rocks%d'%k,P,sz_,rng.uniform(0,6.28,len(P)),o))
    sm=leaf_mat('Scrub',srgb(0x2f3d18),srgb(0x5a5f26))
    for k in range(3):
        V,F=blob(40+k,(0.9,0.8,0.42),0.55,3.4,0.05,nblobs=4); o=mesh_obj('Scrub%d'%k,V,F); o.data.materials.append(sm)
        P,d=place(int(3200*dense),11,300,pw=1.5,xhi=XJ+140)
        cl=fbm(P[:,0]*.02+k,P[:,1]*.02,3,51); P=P[cl>0.54]; P[:,2]-=0.22
        obs.append(scatter('Scrubs%d'%k,P,rng.uniform(0.6,1.9,len(P)),rng.uniform(0,6.28,len(P)),o))
    return obs
