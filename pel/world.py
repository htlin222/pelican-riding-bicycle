"""Sky, sea, terrain, road, guardrail."""
import bpy, math, numpy as np
from .common import *
from .bl import *

def build_sky():
    sc=bpy.context.scene
    w=bpy.data.worlds.new('World'); sc.world=w; w.use_nodes=True; nt=w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    g=G(nt); out=g.N('ShaderNodeOutputWorld')
    sky=g.N('ShaderNodeTexSky',sky_type='MULTIPLE_SCATTERING')
    sky.sun_elevation=SUN_EL; sky.sun_rotation=math.pi/2-SUN_AZ
    import os
    sky.sun_disc=False; sky.sun_size=math.radians(2.6); sky.sun_intensity=float(os.environ.get('SUNI',0.22))
    sky.altitude=30; sky.air_density=float(os.environ.get('AIR',1.8)); sky.aerosol_density=float(os.environ.get('AERO',4.0)); sky.ozone_density=float(os.environ.get('OZ',2.5))
    tc=g.N('ShaderNodeTexCoord'); d=tc.outputs['Generated']
    xyz=g.N('ShaderNodeSeparateXYZ',{0:d}); dz=xyz.outputs[2]
    inv=g.math('DIVIDE',1.0,g.math('MAXIMUM',dz,0.03))
    p=g.vmath('MULTIPLY',g.N('ShaderNodeCombineXYZ',{0:xyz.outputs[0],1:xyz.outputs[1],2:0.0}).outputs[0],g.N('ShaderNodeCombineXYZ',{0:inv,1:inv,2:0.0}).outputs[0]).outputs[0]
    tval=g.N('ShaderNodeValue'); tval.name='TIME'; tv=tval.outputs[0]
    drift=g.N('ShaderNodeCombineXYZ',{0:g.math('MULTIPLY',tv,0.004),1:g.math('MULTIPLY',tv,0.0015),2:0.0}).outputs[0]
    p2=g.vmath('ADD',p,drift).outputs[0]
    # layer 1: altocumulus puffs
    n1=g.noise(p2,0.55,detail=8,rough=.6,dist=.12)
    patch_=g.maprange(g.noise(p2,0.085,detail=3,rough=.5),0.38,0.62,smooth=True)
    c1=g.math('MULTIPLY',g.maprange(n1,0.44,0.68,smooth=True),patch_)
    # layer 2: stretched cirrus
    st=g.N('ShaderNodeMapping',{'Vector':p2,'Scale':(0.20,0.50,1),'Rotation':(0,0,0.5)}).outputs[0]
    n2=g.noise(st,1.0,detail=7,rough=.66,dist=.25)
    c2=g.math('MULTIPLY',g.maprange(n2,0.50,0.80,smooth=True),0.5)
    dens=g.math('MAXIMUM',c1,c2)
    hor=g.maprange(dz,0.012,0.09,smooth=True)
    dens=g.math('MULTIPLY',dens,hor)
    # low cloud bank hugging the horizon (spherical mapping so it never smears)
    az=g.math('ARCTAN2',xyz.outputs[1],xyz.outputs[0])
    hl=g.math('SQRT',g.math('ADD',g.math('MULTIPLY',xyz.outputs[0],xyz.outputs[0]),g.math('MULTIPLY',xyz.outputs[1],xyz.outputs[1])))
    bv=g.N('ShaderNodeCombineXYZ',{0:g.math('MULTIPLY',g.math('DIVIDE',xyz.outputs[0],hl),6.0),1:g.math('MULTIPLY',g.math('DIVIDE',xyz.outputs[1],hl),6.0),2:g.math('MULTIPLY',dz,44.0)}).outputs[0]
    nb=g.noise(bv,1.0,detail=6,rough=.6,dist=.1)
    bank=g.math('MULTIPLY',g.maprange(nb,0.50,0.66,smooth=True),g.math('MULTIPLY',g.maprange(dz,0.004,0.02,smooth=True),g.math('SUBTRACT',1.0,g.maprange(dz,0.05,0.13,smooth=True))))
    dens=g.math('MAXIMUM',dens,g.math('MULTIPLY',bank,0.95))
    sdot=g.vmath('DOT_PRODUCT',g.vmath('NORMALIZE',d).outputs[0],tuple(SUN)).outputs['Value']
    near=g.math('POWER',g.math('MAXIMUM',sdot,0.0),3.0)
    near2=g.math('POWER',g.math('MAXIMUM',sdot,0.0),24.0)
    lit=g.mix(near,(0.9,0.42,0.31,1),(1.0,0.42,0.18,1))
    lit=g.vmath('SCALE',g.mix(near2,g.vmath('SCALE',lit,scale=0.45).outputs[0],(1.0,0.62,0.30,1)),scale=2.4).outputs[0]
    shade=g.mix(near,(0.13,0.11,0.2,1),(0.42,0.2,0.2,1))
    # fake self shadowing: thicker parts darker, edges lit
    thick=g.maprange(n1,0.60,0.80,smooth=True)
    ccol=g.mix(g.math('MULTIPLY',thick,0.75),lit,shade)
    CL=g.N('ShaderNodeValue'); CL.name='CLOUD_GAIN'; CL.outputs[0].default_value=1.0
    ccol=g.vmath('SCALE',ccol,scale=CL.outputs[0]).outputs[0]
    au=g.math('ADD',g.math('MULTIPLY',g.math('POWER',g.math('MAXIMUM',sdot,0.0),900.0),2.2),g.math('MULTIPLY',g.math('POWER',g.math('MAXIMUM',sdot,0.0),90.0),0.9))
    skyw=g.vmath('MULTIPLY',sky.outputs[0],(1.22,0.95,0.76)).outputs[0]
    skyc=g.vmath('ADD',skyw,g.vmath('SCALE',(1.0,0.42,0.12),scale=au).outputs[0]).outputs[0]
    # limb darkening on the sun disc
    r2=g.math('DIVIDE',g.math('MULTIPLY',g.math('SUBTRACT',1.0,sdot),2.0),(math.radians(2.6)/2)**2)
    limb=g.math('POWER',g.math('MAXIMUM',g.math('SUBTRACT',1.0,r2),0.0),0.35)
    indisc=g.math('LESS_THAN',r2,1.0)
    lc=g.vmath('MULTIPLY',skyc,g.vmath('SCALE',g.mix(limb,(0.34,0.17,0.06,1),(1.0,0.84,0.62,1)),scale=7.0).outputs[0]).outputs[0]
    edge=g.math('SUBTRACT',1.0,g.maprange(r2,0.88,1.0,smooth=True))
    skyc=g.mix(g.math('MULTIPLY',indisc,edge),skyc,lc)
    col=g.mix(g.math('MULTIPLY',dens,0.9),skyc,ccol)
    # horizon haze, same colour as the distance fog on sea and land
    hw=g.math('POWER',g.math('MAXIMUM',sdot,0.0),6.0); hw2=g.math('POWER',g.math('MAXIMUM',sdot,0.0),60.0)
    hz=g.mix(hw,(0.62,0.43,0.36,1),(1.0,0.50,0.24,1)); hz=g.mix(hw2,hz,(1.15,0.72,0.36,1))
    hz=g.vmath('SCALE',hz,scale=0.62).outputs[0]
    col=g.mix(g.math('MULTIPLY',g.math('SUBTRACT',1.0,g.maprange(dz,-0.002,0.016,smooth=True)),g.math('SUBTRACT',1.0,g.math('MULTIPLY',indisc,0.85))),col,hz)
    bg=g.N('ShaderNodeBackground',{'Color':col,'Strength':float(os.environ.get('BG',0.82))}); bg.name='BG'
    g.link(bg.outputs[0],out.inputs['Surface'])
    ld=bpy.data.lights.new('SunL','SUN'); ld.energy=float(os.environ.get('LAMP',8.0)); ld.color=(1.0,0.56,0.30); ld.angle=math.radians(2.8)
    lo=bpy.data.objects.new('SunL',ld); sc.collection.objects.link(lo)
    from mathutils import Vector
    ke=math.radians(8.5); kd=Vector((math.cos(ke)*math.cos(SUN_AZ),math.cos(ke)*math.sin(SUN_AZ),math.sin(ke)))
    lo.rotation_mode='QUATERNION'; lo.rotation_quaternion=kd.to_track_quat('Z','Y')
    return w

def ground_material():
    m,g,p=new_mat('Ground')
    geo=g.N('ShaderNodeNewGeometry'); pos=geo.outputs['Position']
    nz=g.N('ShaderNodeSeparateXYZ',{0:geo.outputs['True Normal']}).outputs[2]
    hz=g.N('ShaderNodeSeparateXYZ',{0:pos}).outputs[2]
    big=g.noise(pos,0.035,detail=5,rough=.55)
    mid=g.noise(pos,0.6,detail=5,rough=.6)
    fine=g.noise(pos,9.0,detail=4,rough=.7)
    grassc=g.ramp(big,[(0.25,srgb(0x3e4a1e)),(0.5,srgb(0x6a6a2a)),(0.75,srgb(0x8f7a38))])
    grassc=g.mix(g.math('MULTIPLY',mid,0.5),grassc,srgb(0x9a8a48))
    dirt=g.mix(mid,srgb(0x5a4632),srgb(0x7a6248))
    wob=g.vmath('ADD',pos,g.vmath('SCALE',g.N('ShaderNodeTexNoise',{'Vector':pos,'Scale':0.08,'Detail':3.0}).outputs['Color'],scale=14.0).outputs[0]).outputs[0]
    strata=g.noise(g.N('ShaderNodeMapping',{'Vector':wob,'Scale':(0.09,0.09,0.55),'Rotation':(0.22,0.1,0)}).outputs[0],1.0,detail=7,rough=.68,dist=1.6)
    rock=g.ramp(strata,[(0.25,srgb(0x4a413a)),(0.45,srgb(0x6b5c4e)),(0.65,srgb(0x7f6d5a)),(0.85,srgb(0x5a5048))])
    slope=g.maprange(g.math('ADD',nz,g.math('MULTIPLY',g.math('SUBTRACT',mid,0.5),0.30)),0.50,0.74,smooth=True)   # 1 = flat
    col=g.mix(slope,rock,g.mix(g.maprange(mid,0.62,0.74,smooth=True),grassc,dirt))
    wet=g.maprange(hz,0.2,3.5,smooth=True)
    col=g.mix(wet,g.vmath('SCALE',col,scale=0.35).outputs[0],col)
    foam=g.math('MULTIPLY',g.math('SUBTRACT',1.0,g.maprange(g.math('ADD',hz,g.math('MULTIPLY',g.noise(pos,0.5,detail=4),-1.0)),-0.25,0.35,smooth=True)),g.maprange(g.noise(pos,2.4,detail=5,rough=.75),0.42,0.6))
    col=g.mix(g.math('MULTIPLY',foam,0.7),col,(0.72,0.74,0.73,1))
    rb=g.N('ShaderNodeTexVoronoi',{'Vector':pos,'Scale':0.9,'Detail':3.0},feature='F1',distance='EUCLIDEAN').outputs['Distance']
    h=g.math('ADD',g.math('MULTIPLY',g.mixf(slope,g.math('ADD',g.math('MULTIPLY',rb,0.5),g.math('MULTIPLY',strata,0.25)),mid),g.mixf(slope,0.4,0.08)),g.math('MULTIPLY',fine,0.02))
    nrm=g.bump(h,strength=0.9,dist=1.0)
    setp(g,p,color=col,rough=g.mixf(wet,0.35,0.92),normal=nrm,spec=0.25)
    return m

def build_terrain():
    xs=np.arange(-170,640.01,1.25)
    near=np.arange(-46,46.01,0.8)
    far_in=46+np.cumsum(0.8*1.045**np.arange(1,400)); far_in=far_in[far_in<1500]
    far_sea=-46-np.cumsum(0.8*1.06**np.arange(1,400)); far_sea=far_sea[far_sea>-260][::-1]
    ys=np.concatenate([far_sea,near,far_in])
    X,Y=np.meshgrid(xs,ys,indexing='ij'); Z=terrainH(X,Y)
    V=np.stack([X,Y,Z],-1).reshape(-1,3); F=grid_faces(len(xs),len(ys))
    ob=mesh_obj('Terrain',V,F); ob.data.materials.append(ground_material()); return ob

def sea_material():
    m,g,p=new_mat('Sea')
    geo=g.N('ShaderNodeNewGeometry'); pos=geo.outputs['Position']
    tval=g.N('ShaderNodeValue'); tval.name='TIME'; tv=tval.outputs[0]
    def layer(scale,speed,ang,detail,dist):
        off=g.N('ShaderNodeCombineXYZ',{0:g.math('MULTIPLY',tv,speed*math.cos(ang)),1:g.math('MULTIPLY',tv,speed*math.sin(ang)),2:g.math('MULTIPLY',tv,speed*.35)}).outputs[0]
        v=g.vmath('ADD',g.N('ShaderNodeMapping',{'Vector':pos,'Scale':(1,1.9,1),'Rotation':(0,0,ang)}).outputs[0],off).outputs[0]
        return g.noise(v,scale,detail=detail,rough=.55,dist=dist)
    swell=layer(0.035,1.2,0.5,3,0.6); chop=layer(0.22,0.6,0.2,4,0.4); rip=layer(1.7,0.35,1.1,3,0.2)
    d=g.N('ShaderNodeCameraData').outputs['View Distance']
    lod=g.math('SUBTRACT',1.0,g.maprange(d,60,900,smooth=True))
    h=g.math('ADD',g.math('ADD',g.math('MULTIPLY',swell,1.6),g.math('MULTIPLY',chop,0.30)),g.math('MULTIPLY',g.math('MULTIPLY',rip,0.035),lod))
    nrm=g.bump(h,strength=1.0,dist=1.0)
    crest=g.maprange(g.math('ADD',swell,g.math('MULTIPLY',chop,0.6)),0.95,1.12,smooth=True)
    col=g.mix(g.math('MULTIPLY',crest,0.35),(0.006,0.035,0.05,1),(0.55,0.62,0.62,1))
    setp(g,p,color=col,rough=g.mixf(crest,0.085,0.5),normal=nrm,ior=1.33)
    return m
def build_sea():
    s=30000.0
    V=[(-s,-s,SEA),(s,-s,SEA),(s,s,SEA),(-s,s,SEA)]
    ob=mesh_obj('Sea',V,[[0,1,2,3]],smooth=False); ob.data.materials.append(sea_material()); ob.location=(XJ,0,0); return ob

def road_material():
    m,g,p=new_mat('Road')
    uv=g.N('ShaderNodeUVMap').outputs[0]; s=g.N('ShaderNodeSeparateXYZ',{0:uv}); u=s.outputs[0]; v=s.outputs[1]
    pos=g.N('ShaderNodeNewGeometry').outputs['Position']
    agg=g.N('ShaderNodeTexVoronoi',{'Vector':pos,'Scale':130.0},feature='F1').outputs['Distance']
    blot=g.noise(pos,0.5,detail=5,rough=.6); streak=g.noise(g.N('ShaderNodeMapping',{'Vector':g.N('ShaderNodeCombineXYZ',{0:u,1:v,2:0.0}).outputs[0],'Scale':(0.03,2.2,1)}).outputs[0],1.0,detail=5,rough=.6)
    base=g.mix(blot,srgb(0x3b3835),srgb(0x57524b)); base=g.mix(g.math('MULTIPLY',streak,0.5),base,srgb(0x49453f))
    crk=g.N('ShaderNodeTexVoronoi',{'Vector':g.vmath('ADD',pos,g.vmath('SCALE',g.N('ShaderNodeTexNoise',{'Vector':pos,'Scale':1.5,'Detail':3.0}).outputs['Color'],scale=0.5).outputs[0]).outputs[0],'Scale':0.55},feature='DISTANCE_TO_EDGE').outputs['Distance']
    crack=g.math('MULTIPLY',g.math('SUBTRACT',1.0,g.maprange(crk,0.0,0.012)),g.maprange(g.noise(pos,0.25,detail=3),0.45,0.6))
    tyre=g.math('MULTIPLY',g.math('SUBTRACT',1.0,g.maprange(g.math('ABSOLUTE',g.math('SUBTRACT',g.math('ABSOLUTE',v),1.75)),0.25,0.75,smooth=True)),0.35)
    base=g.mix(tyre,base,srgb(0x2f2d2b)); base=g.mix(crack,base,srgb(0x151413))
    base=g.mix(g.math('MULTIPLY',agg,0.25),base,srgb(0x77736a))
    av=g.math('ABSOLUTE',v)
    def band(lo,hi,soft=.012): return g.math('MULTIPLY',g.maprange(av,lo-soft,lo+soft),g.math('SUBTRACT',1.0,g.maprange(av,hi-soft,hi+soft)))
    wear=g.maprange(g.noise(pos,2.5,detail=6,rough=.7),0.35,0.62)
    yellow=g.math('MULTIPLY',band(0.07,0.17),g.math('ADD',0.12,g.math('MULTIPLY',wear,0.75)))
    white=g.math('MULTIPLY',band(3.22,3.32),g.math('ADD',0.1,g.math('MULTIPLY',wear,0.75)))
    col=g.mix(yellow,base,srgb(0xc9992a)); col=g.mix(white,col,srgb(0xcfccc0))
    paint=g.math('MAXIMUM',yellow,white)
    h=g.math('ADD',g.math('MULTIPLY',agg,0.004),g.math('MULTIPLY',paint,0.002))
    setp(g,p,color=col,rough=g.mixf(paint,g.mixf(blot,0.82,0.95),0.6),normal=g.bump(g.math('SUBTRACT',h,g.math('MULTIPLY',crack,0.004)),strength=1.0,dist=1.0),spec=0.3)
    return m
def build_road():
    xs=np.arange(-170,XJ+.01,0.5)
    c=roadC(xs); z=roadZ(xs)+0.02; cs=roadCs(xs)
    rr=np.random.RandomState(8)
    nx=-cs/np.sqrt(1+cs*cs); ny=1/np.sqrt(1+cs*cs)
    lat=np.array([-3.55,-2.4,-1.2,0,1.2,2.4,3.55])
    VX=xs[:,None]+nx[:,None]*lat[None,:]
    VZ=roadZ(VX)+0.02
    VX[-1]+=rr.uniform(0.15,1.0,len(lat)); VZ[-1]=VZ[-2]+ (VZ[-2]-VZ[-3])*1.0-rr.uniform(0.02,0.10,len(lat)); VX[-2]+=rr.uniform(-0.1,0.25,len(lat))
    V=np.stack([VX, c[:,None]+ny[:,None]*lat[None,:], VZ],-1).reshape(-1,3)
    s=np.array([arclen(x) for x in xs])
    UV=np.stack([np.repeat(s[:,None],7,1),np.repeat(lat[None,:],len(xs),0)],-1).reshape(-1,2)
    ob=mesh_obj('Road',V,grid_faces(len(xs),7),uvs=UV); ob.data.materials.append(road_material()); return ob

def build_guardrail():
    """weathered timber posts carrying three steel cables: keeps the sea visible behind the rider"""
    mm,g,p=new_mat('Cable'); setp(g,p,color=(0.22,0.22,0.23,1),metal=1.0,rough=0.6)
    mw,g2,p2=new_mat('Timber'); pos=g2.N('ShaderNodeNewGeometry').outputs['Position']
    gr=g2.noise(g2.N('ShaderNodeMapping',{'Vector':pos,'Scale':(30,30,2.5)}).outputs[0],1.0,detail=5,rough=.7,dist=.6); n=g2.noise(pos,2.0,detail=3)
    setp(g2,p2,color=g2.mix(gr,srgb(0x4a3d32),srgb(0x8c7a66)),rough=0.85,normal=g2.bump(gr,strength=0.8,dist=0.01))
    xs=np.arange(-170,XJ-1.0,0.5); c=roadC(xs); cs=roadCs(xs)
    nx=-cs/np.sqrt(1+cs*cs); ny=1/np.sqrt(1+cs*cs); off=-4.3
    cx=xs+nx*off; cy=c+ny*off; cz=roadZ(cx)
    parts=[]
    for h in (0.30,0.48,0.66):
        sag=0.02*np.cos(np.arange(len(xs))*2*np.pi/6.0)
        parts.append(tube_mesh(np.stack([cx,cy,cz+h+sag],1),0.0042,seg=5,cap=False))
    V,F=join(parts); cab=mesh_obj('Cables',V,F); cab.data.materials.append(mm)
    rng=np.random.RandomState(4); parts=[]
    for i in range(0,len(xs),6):
        b=np.array([cx[i],cy[i],cz[i]-0.3]); lean=rng.uniform(-0.03,0.03,2); hh=rng.uniform(0.74,0.82)
        t=b+np.array([lean[0],lean[1],0.3+hh]); V_,F_=tube_mesh([b,(b+t)/2,t],[0.075,0.07,0.062],seg=7); parts.append((V_,F_))
    V,F=join(parts); posts=mesh_obj('Posts',V,F,smooth=False); posts.data.materials.append(mw)
    return cab,posts
