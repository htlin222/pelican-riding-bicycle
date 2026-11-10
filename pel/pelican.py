"""Great white pelican (Pelecanus onocrotalus), built for riding a bicycle.
Bird frame: +X forward, +Y left, +Z up, origin = where the body rests on the saddle."""
import bpy, math, numpy as np
from mathutils import Vector, Matrix, Quaternion
from .bl import *
from . import sdf

R_=math.radians
# ---------------------------------------------------------------- materials
def plumage_mat():
    m,g,p=new_mat('Plumage')
    col=g.N('ShaderNodeVertexColor',layer_name='Col').outputs['Color']
    tc=g.N('ShaderNodeTexCoord').outputs['Object']
    st=g.N('ShaderNodeMapping',{'Vector':tc,'Scale':(22,48,48)}).outputs[0]
    vor=g.N('ShaderNodeTexVoronoi',{'Vector':st,'Scale':1.6,'Randomness':1.0,'Smoothness':1.0},feature='SMOOTH_F1').outputs['Distance']
    big=g.noise(tc,9.0,detail=4,rough=.6)
    fine=g.noise(st,6.0,detail=3,rough=.7)
    h=g.math('ADD',g.math('MULTIPLY',vor,0.0035),g.math('MULTIPLY',fine,0.0022))
    c2=g.mix(g.math('MULTIPLY',big,0.25),col,(0.80,0.72,0.66,1))
    c2=g.mix(g.math('MULTIPLY',g.maprange(vor,0.0,0.7),0.06),c2,(0.66,0.6,0.56,1))
    setp(g,p,color=c2,rough=0.62,normal=g.bump(h,strength=0.4,dist=1.0),sheen=0.6,sheenr=0.45,sss=0.12,sssr=(0.02,0.012,0.008),ssss=1.0,spec=0.3)
    return m
def feather_mat(vc=False):
    m,g,p=new_mat('FeatherVC' if vc else 'Feather')
    oi=g.N('ShaderNodeObjectInfo'); col=oi.outputs['Color']; rnd=oi.outputs['Random']
    if vc: col=g.N('ShaderNodeVertexColor',layer_name='Col').outputs['Color']
    uv=g.N('ShaderNodeUVMap').outputs[0]; s=g.N('ShaderNodeSeparateXYZ',{0:uv}); u=s.outputs[0]; v=s.outputs[1]
    av=g.math('ABSOLUTE',g.math('SUBTRACT',v,0.5))
    barb=g.math('SINE',g.math('ADD',g.math('MULTIPLY',u,260.0),g.math('MULTIPLY',av,170.0)))
    rach=g.math('SUBTRACT',1.0,g.maprange(av,0.0,0.035,smooth=True))
    tint=g.mix(g.math('MULTIPLY',rnd,0.10),col,g.vmath('SCALE',col,scale=0.86).outputs[0])
    tint=g.mix(g.math('MULTIPLY',rach,0.35),tint,(0.75,0.72,0.66,1))
    h=g.math('ADD',g.math('MULTIPLY',barb,0.0006),g.math('MULTIPLY',rach,0.002))
    setp(g,p,color=tint,rough=0.5,normal=g.bump(h,strength=0.8,dist=1.0),sheen=0.35,sheenr=0.4,spec=0.35)
    # backlit translucency
    nt=m.node_tree; out=[n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'][0]
    surf=out.inputs['Surface'].links[0].from_socket
    fogn=[n for n in nt.nodes if n.type=='GROUP'][0]
    tr=g.N('ShaderNodeBsdfTranslucent',{'Color':tint})
    mx=g.N('ShaderNodeMixShader',{0:0.30,1:p.outputs[0],2:tr.outputs[0]})
    for l in list(fogn.inputs[0].links): nt.links.remove(l)
    g.link(mx.outputs[0],fogn.inputs[0])
    return m
def simple_mat(name,color,rough=.5,**kw):
    m,g,p=new_mat(name); setp(g,p,color=color,rough=rough,**kw); return m,g,p
def bill_mat():
    m,g,p=new_mat('Bill')
    col=g.N('ShaderNodeVertexColor',layer_name='Col').outputs['Color']
    tc=g.N('ShaderNodeTexCoord').outputs['Object']
    st=g.noise(g.N('ShaderNodeMapping',{'Vector':tc,'Scale':(6,60,60)}).outputs[0],4.0,detail=4,rough=.6)
    c=g.mix(g.math('MULTIPLY',st,0.25),col,g.vmath('SCALE',col,scale=0.7).outputs[0])
    setp(g,p,color=c,rough=0.34,normal=g.bump(st,strength=0.12,dist=0.004),coat=0.25,coatr=0.3,sss=0.1,sssr=(0.01,0.005,0.003))
    return m
def pouch_mat():
    m,g,p=new_mat('Pouch')
    tc=g.N('ShaderNodeTexCoord').outputs['Object']
    wr=g.noise(g.N('ShaderNodeMapping',{'Vector':tc,'Scale':(5,70,40)}).outputs[0],3.0,detail=4,rough=.65)
    vein=g.maprange(g.noise(tc,38.0,detail=5,rough=.7,dist=1.5),0.55,0.62,smooth=True)
    c=g.mix(wr,srgb(0xf7bc2a),srgb(0xee9418)); c=g.mix(g.math('MULTIPLY',vein,0.3),c,srgb(0xd0581c))
    setp(g,p,color=c,rough=0.42,normal=g.bump(wr,strength=0.35,dist=0.004),sss=0.75,sssr=(0.12,0.05,0.015),ssss=0.25,coat=0.15)
    return m
def skin_mat():
    m,g,p=new_mat('LegSkin')
    tc=g.N('ShaderNodeTexCoord').outputs['Object']
    sc_=g.N('ShaderNodeTexVoronoi',{'Vector':tc,'Scale':420.0},feature='F1').outputs['Distance']
    n=g.noise(tc,30.0,detail=3)
    c=g.mix(n,srgb(0xf29a84),srgb(0xeaa272))
    setp(g,p,color=c,rough=0.45,normal=g.bump(sc_,strength=0.3,dist=0.002),sss=0.3,sssr=(0.02,0.008,0.004),ssss=0.5)
    return m
def scarf_mat():
    m,g,p=new_mat('Scarf')
    uv=g.N('ShaderNodeUVMap').outputs[0]
    w1=g.N('ShaderNodeTexWave',{'Vector':uv,'Scale':260.0,'Distortion':0.4},wave_type='BANDS',bands_direction='X').outputs['Fac']
    w2=g.N('ShaderNodeTexWave',{'Vector':uv,'Scale':260.0,'Distortion':0.4},wave_type='BANDS',bands_direction='Y').outputs['Fac']
    n=g.noise(uv,14.0,detail=4)
    h=g.math('MULTIPLY',g.math('ADD',w1,w2),0.5)
    c=g.mix(n,srgb(0xb3121c),srgb(0xd42a22)); c=g.mix(g.math('MULTIPLY',h,0.2),c,srgb(0x7a0a12))
    setp(g,p,color=c,rough=0.85,normal=g.bump(h,strength=0.5,dist=0.0015),sheen=1.0,sheenr=0.5,sheent=(1,.55,.45,1),spec=0.2)
    nt=m.node_tree; fogn=[n_ for n_ in nt.nodes if n_.type=='GROUP'][0]
    tr=g.N('ShaderNodeBsdfTranslucent',{'Color':c}); mx=g.N('ShaderNodeMixShader',{0:0.3,1:p.outputs[0],2:tr.outputs[0]})
    for l in list(fogn.inputs[0].links): nt.links.remove(l)
    g.link(mx.outputs[0],fogn.inputs[0])
    return m

# ---------------------------------------------------------------- geometry bits
def uv_sphere(r,nu=16,nv=12):
    th=np.linspace(0,np.pi,nv); ph=np.linspace(0,2*np.pi,nu,endpoint=False)
    V=np.stack([r*np.sin(th)[:,None]*np.cos(ph)[None,:],r*np.sin(th)[:,None]*np.sin(ph)[None,:],r*np.cos(th)[:,None]*np.ones(nu)[None,:]],-1).reshape(-1,3)
    return V,grid_faces(nv,nu,wrap_v=True)
def feather_geo(pointed=0.5,asym=0.0,nu=12,nv=7):
    u=np.linspace(0,1,nu); v=np.linspace(-1,1,nv)
    hw=0.5*np.clip(u/0.10,0,1)**0.55*(1-u**(2.0+2.5*pointed))**0.55
    hw[0]=0.02
    X=u[:,None]*np.ones(nv)[None,:]
    Y=hw[:,None]*(v[None,:]+asym*(1-v[None,:]**2))
    Z=-0.42*Y**2-0.035*X**2+0.012*np.sin(3.1*X)
    V=np.stack([X,Y,Z],-1).reshape(-1,3)
    UV=np.stack([X,(v[None,:]*.5+.5)*np.ones(nu)[:,None]],-1).reshape(-1,2)
    return V,grid_faces(nu,nv),UV
_feather_meshes={}
def feather_obj(name,kind,mat,parent,loc,quat,L,W,color):
    key=kind
    if key not in _feather_meshes:
        V,F,UV=feather_geo(*{'prim':(0.9,0.25),'sec':(0.25,0.08),'cov':(0.1,0.0),'crest':(1.3,0.0)}[kind])
        tmp=mesh_obj('F_'+kind,V,F,uvs=UV); me=tmp.data; me.materials.append(mat)
        bpy.data.objects.remove(tmp); _feather_meshes[key]=me
    ob=bpy.data.objects.new(name,_feather_meshes[key]); bpy.context.scene.collection.objects.link(ob)
    ob.parent=parent; ob.location=loc; ob.rotation_mode='QUATERNION'; ob.rotation_quaternion=quat; ob.scale=(L,W,W); ob.color=color
    return ob

WHITE=(0.93,0.90,0.87,1); BLACK=(0.035,0.033,0.036,1); GREY=(0.16,0.15,0.15,1)
Lh,Lf,Lm=0.26,0.36,0.30

HR=np.array([0.338,0,0.897])        # head centre in the coordinates the head parts are modelled in
NB=(0.255,0,0.355)
def head_mats():
    ride=Matrix.Translation(Vector((0.292,0,0.893)))@Matrix.Rotation(R_(7),4,'Y')@Matrix.Translation(-Vector(HR))
    fly=Matrix.Translation(Vector((0.262,0,0.585)))@Matrix.Rotation(R_(-17),4,'Y')@Matrix.Translation(-Vector(HR))
    return ride,fly
NECK_RIDE=[NB,(0.352,0,0.452),(0.372,0,0.575),(0.318,0,0.695),(0.262,0,0.795)]
NECK_FLY=[NB,(0.300,0,0.450),(0.235,0,0.530),(0.150,0,0.545),(0.150,0,0.610)]
NECK_R=[.118,.098,.076,.064,.060,.060]
NECK_ATT=np.array([0.326,0,0.889])   # where the neck enters the head, head-model coords
def catmull(P,n):
    P=np.asarray(P,dtype=float); Q=np.vstack([2*P[0]-P[1],P,2*P[-1]-P[-2]]); out=[]
    m=len(P)-1
    for k in range(n):
        u=k/(n-1)*m; i=min(int(u),m-1); t=u-i; p0,p1,p2,p3=Q[i],Q[i+1],Q[i+2],Q[i+3]
        out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3))
    return np.array(out)
def build_body(bird,flight=False,mat=None):
    """torso only; the neck is a posable tube and the head a rigid group (see Pelican)"""
    VOX=0.005
    P,lo=sdf.grid((-0.50,-0.27,-0.10),(0.42,0.27,0.50),VOX)
    Rp,Mp,Cp=(-0.29,0,0.105),(-0.05,0,0.17),(0.16,0,0.265)
    d=sdf.chain(P,[Rp,Mp,Cp,NB,(0.285,0,0.392)],[.095,.17,.155,.105,.092],k=.07)
    d=sdf.smin(d,sdf.ellipsoid(P,(0.02,0,0.115),(0.25,0.158,0.118)),.05)
    for sy in (1,-1):
        d=sdf.smin(d,sdf.ellipsoid(P,(-0.05,sy*0.095,0.07),(0.11,0.062,0.10)),.04)
    d=sdf.smin(d,sdf.ellipsoid(P,(-0.36,0,0.085),(0.10,0.075,0.04)),.05)
    V,F=sdf.mesh(d,lo,VOX,smooth_iters=4)
    base=np.array([0.93,0.90,0.87]); pinkw=np.array([0.95,0.85,0.83]); yellow=np.array([0.95,0.83,0.50])
    C=np.repeat(base[None,:],len(V),0)
    k=np.clip(0.5+0.5*np.sin(V[:,0]*9+V[:,2]*7),0,1)[:,None]*0.4; C=C*(1-k)+pinkw*k
    r=np.linalg.norm(V-np.array([0.275,0,0.27]),axis=1); k=(1-np.clip((r-0.03)/0.10,0,1))[:,None]**1.5*0.8; C=C*(1-k)+yellow*k
    ob=mesh_obj('PelicanBody',V,F,colors=C); ob.data.materials.append(mat or plumage_mat()); ob.parent=bird
    # layered contour feathers: soft silhouette break-up, kept bright and close to the skin
    fn=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]); VN=np.zeros_like(V)
    for c_ in range(3): np.add.at(VN,F[:,c_],fn)
    VN/=np.linalg.norm(VN,axis=1)[:,None]+1e-12
    rng=np.random.RandomState(11); fV,fF,fUV=feather_geo(0.1,0.0,7,5)
    idx=np.where(VN[:,2]>-0.55)[0]; Vs=[];Fs=[];UVs=[];Cs=[];o=0
    for i in rng.choice(idx,1700 if not flight else 500):
        n=VN[i]; t0=np.array([-1,0,-0.3])+rng.uniform(-.22,.22,3); x_=t0-n*np.dot(n,t0); nl=np.linalg.norm(x_)
        if nl<1e-3: continue
        x_/=nl; a=R_(rng.uniform(3,8)); xa=math.cos(a)*x_+math.sin(a)*n; za=math.cos(a)*n-math.sin(a)*x_; ya=np.cross(za,xa)
        L=rng.uniform(0.06,0.105); W=0.05*rng.uniform(0.85,1.2)
        Vf=(fV*np.array([L,W,W*0.6]))@np.stack([xa,ya,za],0)+V[i]-n*0.004
        Vs.append(Vf);Fs.append(fF+o);UVs.append(fUV);Cs.append(np.repeat((C[i]*rng.uniform(0.985,1.02))[None,:],len(Vf),0));o+=len(Vf)
    fo=mesh_obj('BodyFeathers',np.vstack(Vs),np.vstack(Fs),uvs=np.vstack(UVs),colors=np.vstack(Cs)); fo.data.materials.append(Pelican._M['feather_vc']); fo.parent=bird
    return ob
def build_head(head,mat):
    VOX=0.004
    P,lo=sdf.grid((0.24,-0.075,0.82),(0.43,0.075,0.975),VOX)
    d=sdf.ellipsoid(P,(0.338,0,0.897),(0.078,0.054,0.057)); d=sdf.smin(d,sdf.sphere(P,(0.374,0,0.918),0.042),.022)
    d=sdf.smin(d,sdf.sphere(P,tuple(NECK_ATT),0.049),.02)
    V,F=sdf.mesh(d,lo,VOX,smooth_iters=3)
    base=np.array([0.93,0.90,0.87]); skin=np.array([0.98,0.50,0.40]); skin2=np.array([1.0,0.72,0.36])
    C=np.repeat(base[None,:],len(V),0)
    e=np.array([0.378,0.0,0.908]); pv=V.copy(); pv[:,1]=np.abs(pv[:,1])-0.040
    dd=np.linalg.norm((pv-e)*np.array([0.62,1.5,0.9]),axis=1)
    k=(1-np.clip((dd-0.046)/0.012,0,1))[:,None]*(V[:,0]>0.312)[:,None]
    k2=(1-np.clip((dd-0.022)/0.012,0,1))[:,None]
    C=C*(1-k)+skin*k; C=C*(1-k2*0.7)+skin2*k2*0.7
    ob=mesh_obj('PelicanHead',V,F,colors=C); ob.data.materials.append(mat); ob.parent=head; return ob

def build_bill(bird,mats):
    B0=np.array([0.385,0,0.893]); ang=R_(27); a=np.array([math.cos(ang),0,-math.sin(ang)]); u=np.array([math.sin(ang),0,math.cos(ang)]); y=np.array([0,1,0.0]); L=0.54
    def w(s):
        s=np.asarray(s,dtype=float); return (0.034+0.007*np.clip(s,0,1))*np.sqrt(np.clip(1-np.clip((s-0.90)/0.10,0,1)**2,0,1))+0.0025
    def th(s): return 0.021*(1-0.70*np.clip(s,0,1))+0.004
    def spine(s): return B0+a*(L*s)-u*(0.016*np.clip(s,0,2)**2)
    ss=np.concatenate([[-0.05],np.linspace(0,0.9,17),[0.94,0.97,0.99,1.0]])
    tht=np.linspace(0,np.pi,11)
    V=[];C=[]
    grey=np.array([0.40,0.48,0.62]); red=np.array([0.84,0.34,0.32]); yel=np.array([0.90,0.70,0.34]); org=np.array([0.88,0.42,0.2])
    for s in ss:
        c=spine(s); ww=float(w(s)); tt=float(th(s))
        ring=[]
        for t in tht:
            ct=math.cos(t); zz=tt*math.sin(t)**0.8+0.0045*math.exp(-(ct/0.28)**2)*(1-0.6*max(s,0))
            ring.append((c+y*ww*ct+u*zz, abs(ct)))
        for fy in (-0.62,0.0,0.62):
            ring.append((c+y*ww*fy-u*(0.0035-0.002*abs(fy)),-1))
        for pt,e in ring:
            V.append(pt)
            if e<0: col=yel*0.9
            else:
                col=grey*(1-e**2.2)+red*e**2.2
                col=col*(1-0.35*max(0,1-s/0.15))+yel*0.35*max(0,1-s/0.15)
            k=float(np.clip((s-0.80)/0.2,0,1))*0.7; col=col*(1-k)+org*k
            C.append(col)
    nr=len(tht)+3
    upper=mesh_obj('BillUpper',np.array(V),grid_faces(len(ss),nr,wrap_v=True),colors=np.array(C)); upper.data.materials.append(mats['bill']); upper.parent=bird
    tip=spine(1.0)
    nV,nF=tube_mesh([tip+u*0.004-a*0.012,tip+u*0.003+a*0.006,tip+a*0.013-u*0.008,tip+a*0.012-u*0.022,tip+a*0.004-u*0.032],[.0095,.0095,.008,.0055,.002],seg=10)
    nail=mesh_obj('BillNail',nV,nF); nail.data.materials.append(mats['nail']); nail.parent=bird
    # lower mandible rami
    sr=np.linspace(-0.03,0.985,18); parts=[]
    for sy in (1,-1):
        pts=[spine(s)+y*sy*max(float(w(s))-0.004,0.0)*(1 if s<0.97 else 0.3)-u*0.008 for s in sr]
        parts.append(tube_mesh(pts,np.linspace(0.0058,0.0034,len(sr)),seg=8))
    rV,rF=join(parts); rami=mesh_obj('BillLower',rV,rF); rami.data.materials.append(mats['ramus']); rami.parent=bird
    # gular pouch
    sp=np.linspace(-0.10,0.975,30); ph=np.linspace(0,np.pi,15); V=[]
    for s in sp:
        c=spine(max(s,0.0))+a*(L*min(s,0.0))
        wr=max(float(w(max(s,0)))-0.004,0.001)
        dep=0.105*math.sin(math.pi*(np.clip(s+0.10,0,1.075)/1.075)**0.72)**0.9*(1-0.15*np.clip(s,0,1))+0.003
        for p_ in ph:
            V.append(c+y*wr*math.cos(p_)-u*(0.008+dep*math.sin(p_)**0.72))
    pouch=mesh_obj('Pouch',np.array(V),grid_faces(len(sp),len(ph))); pouch.data.materials.append(mats['pouch']); pouch.parent=bird
    md=pouch.modifiers.new('S','SOLIDIFY'); md.thickness=0.0022; md.offset=1.0
    return upper

def build_head_details(bird,body,mats):
    eV,eF=uv_sphere(0.017)
    for sy in (1,-1):
        e=mesh_obj('Eye',eV,eF); e.data.materials.append(mats['eye']); e.parent=bird; e.location=(0.381,sy*0.0420,0.911)
    # shaggy nape crest
    rng=np.random.RandomState(5)
    for i in range(34):
        az=rng.uniform(-0.7,0.7); el=rng.uniform(-1.25,-0.45)
        d=Vector((-math.cos(el)*math.cos(az),math.sin(az)*0.6,math.sin(el)))
        q=d.to_track_quat('X','Z')
        feather_obj('Crest',"crest",mats['feather'],bird,(0.285+rng.uniform(-.01,.01),rng.uniform(-.018,.018),0.905+rng.uniform(-.02,.012)),q,rng.uniform(0.07,0.15),0.030,(0.97,0.95,0.92,1))
    # tail fan
    for i in range(11):
        az=(i-5)/5*0.62
        d=Vector((-math.cos(az),math.sin(az),-0.20)); q=d.to_track_quat('X','Z')
        feather_obj('Tail','cov',mats['feather'],body,(-0.385,math.sin(az)*0.03,0.085-abs(i-5)*0.002),q,0.17,0.07,WHITE)

class Wing:
    """Three-bone feathered wing. Built as the LEFT wing; the right one is the same rig under a mirrored root."""
    def __init__(s,bird,side,mats,static=False):
        s.side=side; s.static=static; specs=[]
        s.root=empty('WingRoot',bird,(0.135,side*0.118,0.335)); s.root.scale=(1,side,1)
        s.j0=empty('J0',s.root); s.j1=empty('J1',s.j0,(Lh,0,0)); s.j2=empty('J2',s.j1,(Lf,0,0))
        fm=mats['feather']; s.feathers=[]
        def bone(j,L,r1,r2):
            V,F=tube_mesh([(-0.01,0,0),(L*0.5,-0.004,0),(L+0.01,0,0)],[r1,(r1+r2)/2,r2],seg=10)
            V[:,2]*=0.55
            o=mesh_obj('WingArm',V,F); o.data.materials.append(mats['plumage_plain']); o.parent=j
        bone(s.j0,Lh,0.052,0.040); bone(s.j1,Lf,0.040,0.027); bone(s.j2,Lm*0.85,0.027,0.010)
        s.secs=[]; s.prims=[]
        def add(j,kind,x,z,a_sp,a_fd,L,W,color,roll=0.0,yoff=0.0,sec=False):
            if static: specs.append((j,kind,(x,yoff,z),a_sp,roll,L,W,color)); return
            ob=feather_obj('Fth',kind,fm,j,(x,yoff,z),Quaternion((1,0,0,0)),L,W,color)
            s.feathers.append((ob,a_sp,a_fd,roll))
            if sec: s.secs.append(ob)
            if kind=='prim': s.prims.append((ob,L))
        PL=[0.40,0.42,0.44,0.46,0.48,0.50,0.51,0.51,0.48,0.42]
        for i in range(10):
            k=i/9
            add(s.j2,'prim',Lm*(0.04+0.92*k),-0.0006*i,R_(84-78*k**1.25),R_(28-20*k),PL[i],0.074-0.016*k,BLACK,roll=R_(-4))
            add(s.j2,'cov',Lm*(0.04+0.92*k),0.006,R_(86-74*k**1.25),R_(30-20*k),PL[i]*0.50,0.075,WHITE)
            add(s.j2,'cov',Lm*(0.04+0.92*k),-0.008,R_(86-74*k**1.25),R_(30-20*k),PL[i]*0.55,0.11,WHITE)
        NS=15
        for j in range(NS):
            k=(j+0.5)/NS
            add(s.j1,'sec',Lf*(0.02+0.98*k),-0.0005*(NS-j)-0.006,R_(97-11*k),R_(158-10*k),0.44+0.03*k,0.078,BLACK,sec=True,roll=R_(-3))
            add(s.j1,'cov',Lf*(0.02+0.98*k),0.005,R_(98-11*k),R_(160-10*k),0.27,0.082,WHITE)
            add(s.j1,'cov',Lf*(0.02+0.98*k),0.011,R_(100-11*k),R_(162-10*k),0.15,0.08,WHITE,yoff=-0.005)
            add(s.j1,'cov',Lf*(0.02+0.98*k),-0.013,R_(98-11*k),R_(160-10*k),0.31,0.125,WHITE)
        for t in range(7):
            k=(t+0.5)/7
            add(s.j0,'sec',Lh*(0.10+0.90*k),0.002+0.0006*t,R_(112-12*k),R_(24+10*k),0.40+0.04*k,0.085,WHITE)
            add(s.j0,'cov',Lh*(0.10+0.90*k),0.009,R_(112-12*k),R_(22+10*k),0.24,0.085,WHITE)
            add(s.j0,'cov',Lh*(0.10+0.90*k),-0.010,R_(110-12*k),R_(24+10*k),0.30,0.125,WHITE)
        if static:
            for j in (s.j0,s.j1,s.j2):
                Vs=[];Fs=[];UVs=[];Cs=[];o=0
                for (jj,kind,loc,a,roll,L,W,color) in specs:
                    if jj is not j: continue
                    V,F,UV=feather_geo(*{'prim':(0.9,0.25),'sec':(0.25,0.08),'cov':(0.1,0.0)}[kind])
                    M3=np.array((Quaternion((0,0,1),a)@Quaternion((1,0,0),roll)).to_matrix())
                    V=(V*np.array([L,W,W]))@M3.T+np.array(loc)
                    Vs.append(V);Fs.append(F+o);UVs.append(UV);Cs.append(np.repeat(np.array(color)[None,:],len(V),0));o+=len(V)
                ob=mesh_obj('WingF',np.vstack(Vs),np.vstack(Fs),uvs=np.vstack(UVs),colors=np.vstack(Cs)); ob.data.materials.append(mats['feather_vc']); ob.parent=j
        # folded shoulder frame (left-wing coordinates)
        X0=Vector((-0.84,0.16,-0.50)).normalized(); Zt=Vector((0.10,0.98,0.14))
        Y0=Zt.cross(X0).normalized(); Z0=X0.cross(Y0).normalized()
        s.q_fold=Matrix((X0,Y0,Z0)).transposed().to_quaternion()
        s.q_base=Quaternion((0,0,1),R_(90))
    def pose(s,f,flap=0.0,flex=0.0,sweep=R_(10),aoa=R_(4)):
        """f: 0 folded .. 1 spread. flap: +up (rad). flex: 0..1 extra elbow/wrist bend on the upstroke."""
        qs=s.q_base@Quaternion((0,1,0),-flap)@Quaternion((0,0,1),sweep)@Quaternion((1,0,0),-aoa)
        k=1.0+0.2*f; s.root.scale=(k,s.side*k,k)
        s.j0.rotation_quaternion=s.q_fold.slerp(qs,f)
        e=R_(-128)+(R_(-22-34*flex)-R_(-128))*f
        w=R_(150)+(R_(16+38*flex)-R_(150))*f
        s.j1.rotation_quaternion=Quaternion((0,0,1),e); s.j2.rotation_quaternion=Quaternion((0,0,1),w)
        cs_=min(1.0,max(0.0,(f-0.15)/0.5)); cc=tuple(WHITE[i]+(BLACK[i]-WHITE[i])*cs_ for i in range(3))+(1,)
        for ob in s.secs: ob.color=cc
        for ob,L0 in s.prims: ob.scale=(L0*(0.60+0.40*f),ob.scale.y,ob.scale.z)
        for ob,a_sp,a_fd,roll in s.feathers:
            a=a_fd+(a_sp-a_fd)*f
            ob.rotation_quaternion=Quaternion((0,0,1),a)@Quaternion((1,0,0),roll)

def foot_geo():
    VOX=0.002
    P,lo=sdf.grid((-0.03,-0.075,-0.016),(0.125,0.075,0.022),VOX)
    toes=[(0.108,0.0),(0.094,0.052),(0.094,-0.052)]
    d=sdf.sphere(P,(0,0,0.004),0.011)
    for tx,ty in toes:
        d=sdf.smin(d,sdf.chain(P,[(0,0,0.004),(tx*0.55,ty*0.55,0.004),(tx,ty,0.0)],[.008,.0062,.004],k=.004),.004)
    d=sdf.smin(d,sdf.roundcone(P,(0,0,0.004),(-0.022,0.012,0.0),.006,.003),.004)
    r=np.sqrt(P[...,0]**2+P[...,1]**2); an=np.arctan2(P[...,1],P[...,0])
    edge=0.097-0.012*np.abs(np.sin(an*np.pi/0.52))**0.8
    web=np.maximum(np.maximum(r-edge,(np.abs(an)-0.51)*r),np.abs(P[...,2]-0.001)-0.0016)
    d=sdf.smin(d,web,0.004)
    return sdf.mesh(d,lo,VOX,smooth_iters=2)

class Pelican:
    _M=None
    def __init__(s,parent,loc,flight=False):
        s.flight=flight
        s.bird=empty('Bird',parent,loc); s.bird.scale=(1.14,1.14,1.14)
        if flight: s.bird.rotation_quaternion=Quaternion((0,1,0),R_(17))
        if Pelican._M is None: Pelican._M=dict(feather=feather_mat(),feather_vc=feather_mat(True),bill=bill_mat(),pouch=pouch_mat(),leg=skin_mat(),plum=plumage_mat(),
                    nail=simple_mat('Nail',srgb(0xd9451c),0.28,coat=0.5)[0],ramus=simple_mat('Ramus',srgb(0xe9b46a),0.4,sss=0.2)[0],
                    eye=simple_mat('Eye',(0.012,0.008,0.006,1),0.04,coat=1.0,spec=1.0)[0],
                    plumage_plain=simple_mat('PlumagePlain',WHITE,0.6,sheen=0.5,sheenr=0.45)[0],scarf=scarf_mat())
        s.mats=Pelican._M
        s.body=build_body(s.bird,flight,s.mats['plum'])
        s.head=empty('Head',s.bird); s.MR,s.MF=head_mats()
        build_head(s.head,s.mats['plum']); build_bill(s.head,s.mats); build_head_details(s.head,s.bird,s.mats)
        nV,nF=tube_mesh(catmull(NECK_RIDE+[tuple(NECK_ATT)],26),np.interp(np.linspace(0,5,26),range(6),NECK_R),seg=16)
        s.neck=mesh_obj('PelicanNeck',nV,nF,colors=np.repeat(np.array([[0.93,0.90,0.87]]),len(nV),0)); s.neck.data.materials.append(s.mats['plum']); s.neck.parent=s.bird
        s.scarf_anchor=None; s.pose_neck(1.0 if flight else 0.0)
        s.wings=[Wing(s.bird,1,s.mats,static=flight),Wing(s.bird,-1,s.mats,static=flight)]
        # legs are posed in the PARENT (bike) frame
        s.hip=[Vector((loc[0]+0.006,sy*0.097,loc[2]+0.086)) for sy in (1,-1)]
        s.L1=0.37; s.L2=0.26
        tV,tF=tube_mesh([(0,0,0),(0.2,0,0),(0.5,0,0),(0.8,0,0),(1,0,0)],[0.072,0.078,0.064,0.045,0.034],seg=12)
        sV,sF=tube_mesh([(0,0,0),(0.12,0,0),(0.88,0,0),(1,0,0)],[0.033,0.026,0.025,0.031],seg=10)
        fV,fF=foot_geo(); fV=fV*1.55; s.legs=[]
        for i in range(2):
            lp=s.bird if flight else parent
            th=mesh_obj('Thigh',tV,tF,colors=np.repeat(np.array([[0.93,0.90,0.87]]),len(tV),0)); th.data.materials.append(s.mats['plum']); th.parent=lp; th.rotation_mode='QUATERNION'
            sh=mesh_obj('Tarsus',sV,sF); sh.data.materials.append(s.mats['leg']); sh.parent=lp; sh.rotation_mode='QUATERNION'
            ft=mesh_obj('Foot',fV,fF); ft.data.materials.append(s.mats['leg']); ft.parent=lp; ft.rotation_mode='QUATERNION'
            s.legs.append((th,sh,ft))
            if flight:
                sy=1 if i==0 else -1; a=Vector((-0.12,sy*0.07,0.05)); b=Vector((-0.30,sy*0.065,0.03)); c=Vector((-0.50,sy*0.06,0.045))
                for ob,p0,p1 in ((th,a,b),(sh,b,c)):
                    v=p1-p0; ob.location=p0; ob.rotation_quaternion=v.to_track_quat('X','Z'); ob.scale=(v.length,0.8,0.8)
                ft.location=c; ft.rotation_quaternion=Quaternion((0,0,1),math.pi)@Quaternion((0,1,0),R_(-8))
        if flight:
            s.tails=[]; s.pose_wings(1.0); return
        # scarf: knot ring + two tails
        npt=np.array([0.0,0.0,0.0]); s.scarf_anchor=empty('ScarfAnchor',s.bird)
        a=np.linspace(0,2*np.pi,24,endpoint=False)
        ring=[(npt[0]+0.053*math.cos(t),0.053*math.sin(t),npt[2]+0.012*math.cos(t)) for t in a]; ring.append(ring[0]); ring.append(ring[1])
        rV,rF=tube_mesh(ring,0.010,seg=10,cap=False); rV[:,2]=(rV[:,2]-npt[2])*2.6+npt[2]
        o=mesh_obj('ScarfKnot',rV,rF,uvs=np.stack([np.repeat(np.linspace(0,3,len(ring)),10),np.tile(np.linspace(0,1,10),len(ring))],1)); o.data.materials.append(s.mats['scarf']); o.parent=s.scarf_anchor
        s.anchor=np.array([0.0,0,0.0])
        s.NS=34; s.NW=5; s.tails=[]
        for k in range(2):
            V=np.zeros(((s.NS+1)*s.NW,3)); UV=np.stack([np.repeat(np.linspace(0,6,s.NS+1),s.NW),np.tile(np.linspace(0,0.5,s.NW),s.NS+1)],1)
            o=mesh_obj('ScarfTail',V,grid_faces(s.NS+1,s.NW),uvs=UV); o.data.materials.append(s.mats['scarf']); o.parent=s.bird
            md=o.modifiers.new('S','SOLIDIFY'); md.thickness=0.0025
            s.tails.append(o)
        s.pose_neck(0.0); s.pose_wings(0.0); s.pose_scarf(0.0,1.0)
    def pose_neck(s,g):
        """g: 0 riding (tall S-curve) .. 1 flight (neck folded back, head on the shoulders)"""
        g=min(1.0,max(0.0,g)); g=g*g*(3-2*g)
        qr=s.MR.to_quaternion(); qf=s.MF.to_quaternion(); q=qr.slerp(qf,g)
        hc=Vector((0.292,0,0.893)).lerp(Vector((0.262,0,0.585)),g)+Vector((0.03*math.sin(math.pi*g),0,0))
        M=Matrix.Translation(hc)@q.to_matrix().to_4x4()@Matrix.Scale(1.16,4)@Matrix.Translation(-Vector(HR)); s.head.matrix_local=M
        att=np.array(M@Vector(NECK_ATT))
        ctrl=[tuple(np.array(a)*(1-g)+np.array(b)*g) for a,b in zip(NECK_RIDE,NECK_FLY)]+[tuple(att)]
        pts=catmull(ctrl,26); V,F=tube_mesh(pts,np.interp(np.linspace(0,5,26),range(6),NECK_R),seg=16)
        s.neck.data.vertices.foreach_set('co',V.astype(np.float32).ravel()); s.neck.data.update()
        if s.scarf_anchor is not None:
            i=14; p=pts[i]; t=Vector(pts[i+1]-pts[i-1]).normalized()
            s.scarf_anchor.matrix_local=Matrix.Translation(Vector(p))@t.to_track_quat('Z','X').to_matrix().to_4x4()
            back=Vector((-1,0,0)); back=(back-t*back.dot(t)).normalized()
            s.anchor=np.array(Vector(p)+back*0.052)
    def pose_wings(s,f,flap=0.0,flex=0.0):
        for w in s.wings: w.pose(f,flap,flex)
    def pose_legs(s,pedals,phase):
        """pedals: list of 2 Vector (bike frame) pedal-axle positions for left,right; phase: crank angle"""
        for i,(th,sh,ft) in enumerate(s.legs):
            hip=s.hip[i]; pd=pedals[i]
            ank=Vector((pd.x-0.035,pd.y,pd.z+0.040))
            dv=ank-hip; d=min(dv.length,s.L1+s.L2-1e-4)
            a1=math.acos(max(-1,min(1,(s.L1**2+d*d-s.L2**2)/(2*s.L1*d))))
            base=math.atan2(dv.z,dv.x)
            kn=Vector((hip.x+s.L1*math.cos(base+a1),hip.y+(pd.y-hip.y)*0.55,hip.z+s.L1*math.sin(base+a1)))
            for ob,a,b in ((th,hip,kn),(sh,kn,ank)):
                v=b-a; ob.location=a; ob.rotation_quaternion=v.to_track_quat('X','Z'); ob.scale=(v.length,1,1)
            ft.location=ank+Vector((0.0,0,-0.012)); ft.rotation_quaternion=Quaternion((0,1,0),R_(16)+0.18*math.sin(phase+(0 if i==0 else math.pi)))
    def pose_scarf(s,t,speed=1.0,lift=0.0):
        for k,o in enumerate(s.tails):
            me=o.data; V=np.zeros(((s.NS+1),s.NW,3)); L=0.028*(1.0 if k==0 else 0.82)
            p=s.anchor+np.array([0,(0.012 if k==0 else -0.012),0]);
            ph=k*1.7
            for i in range(s.NS+1):
                q=i/s.NS; amp=0.02+0.11*q**1.3
                yaw=math.sin(t*9.0-i*0.42+ph)*0.55*q+math.sin(t*5.1-i*0.23+ph*2)*0.25*q+math.sin(t*14.3-i*0.8+ph*3)*0.2*q*q
                pit=(0.10+lift)-0.55*q*(1-speed*0.75)+math.sin(t*7.3-i*0.36+ph)*0.35*q
                dvec=np.array([-math.cos(pit)*math.cos(yaw),math.sin(yaw),math.sin(pit)])
                if i>0: p=p+dvec*L
                tw=math.sin(t*6.1-i*0.3+ph)*0.9*q
                wd=(0.044+0.008*math.sin(i*0.5+ph))*(1-0.62*q**1.6)
                side=np.array([0,math.sin(tw)*0.6,math.cos(tw)]); side=side-dvec*np.dot(side,dvec); side/=np.linalg.norm(side)
                for j in range(s.NW):
                    V[i,j]=p+side*wd*(j/(s.NW-1)*2-1)
            me.vertices.foreach_set('co',V.reshape(-1).astype(np.float32)); me.update()
