"""Blender helpers: meshes, node graphs, fog wrapper."""
import bpy, math, numpy as np
from mathutils import Vector, Matrix, Quaternion
from .common import SUN

def mesh_obj(name, verts, faces, smooth=True, coll=None, uvs=None, colors=None):
    me=bpy.data.meshes.new(name)
    verts=np.asarray(verts,dtype=np.float32); faces=np.asarray(faces)
    me.vertices.add(len(verts)); me.vertices.foreach_set('co',verts.ravel())
    n=faces.shape[1]; me.loops.add(faces.size); me.loops.foreach_set('vertex_index',faces.ravel().astype(np.int32))
    me.polygons.add(len(faces)); me.polygons.foreach_set('loop_start',np.arange(0,faces.size,n,dtype=np.int32)); me.polygons.foreach_set('loop_total',np.full(len(faces),n,dtype=np.int32))
    me.update(calc_edges=True); me.validate()
    if smooth: me.polygons.foreach_set('use_smooth',np.ones(len(me.polygons),dtype=bool))
    if uvs is not None:
        uv=me.uv_layers.new(name='UV'); uv.data.foreach_set('uv',np.asarray(uvs,dtype=np.float32)[faces.ravel()].ravel())
    if colors is not None:
        ca=me.color_attributes.new('Col','FLOAT_COLOR','POINT'); c=np.asarray(colors,dtype=np.float32)
        if c.shape[1]==3: c=np.concatenate([c,np.ones((len(c),1),np.float32)],1)
        ca.data.foreach_set('color',c.ravel())
    ob=bpy.data.objects.new(name,me); (coll or bpy.context.scene.collection).objects.link(ob); return ob

def grid_faces(nu,nv,wrap_u=False,wrap_v=False):
    """quads for a (nu x nv) vertex grid indexed i*nv+j"""
    iu=np.arange(nu if wrap_u else nu-1); iv=np.arange(nv if wrap_v else nv-1)
    I,J=np.meshgrid(iu,iv,indexing='ij'); I=I.ravel(); J=J.ravel()
    I2=(I+1)%nu; J2=(J+1)%nv
    return np.stack([I*nv+J,I2*nv+J,I2*nv+J2,I*nv+J2],1)

def empty(name,parent=None,loc=(0,0,0)):
    e=bpy.data.objects.new(name,None); bpy.context.scene.collection.objects.link(e); e.empty_display_size=.05
    if parent: e.parent=parent
    e.location=loc; e.rotation_mode='QUATERNION'; return e

def tube_mesh(points, radii, seg=12, cap=True):
    """sweep a circle along a polyline; returns verts, faces"""
    P=np.asarray(points,dtype=float); n=len(P)
    R=np.full(n,radii,dtype=float) if np.isscalar(radii) else np.asarray(radii,dtype=float)
    T=np.gradient(P,axis=0); T/=np.linalg.norm(T,axis=1)[:,None]+1e-12
    up=np.array([0,0,1.0]) if abs(T[0,2])<.9 else np.array([1.0,0,0])
    N=np.zeros_like(P); B=np.zeros_like(P)
    nrm=np.cross(up,T[0]); nrm/=np.linalg.norm(nrm)
    for i in range(n):
        nrm=nrm-T[i]*np.dot(nrm,T[i]); nrm/=np.linalg.norm(nrm)+1e-12
        N[i]=nrm; B[i]=np.cross(T[i],nrm)
    a=np.linspace(0,2*np.pi,seg,endpoint=False)
    V=P[:,None,:]+R[:,None,None]*(np.cos(a)[None,:,None]*N[:,None,:]+np.sin(a)[None,:,None]*B[:,None,:])
    V=V.reshape(-1,3); F=grid_faces(n,seg,wrap_v=True)
    if cap:
        V=np.vstack([V,P[0],P[-1]]); c0=len(V)-2; c1=len(V)-1
        j=np.arange(seg); j2=(j+1)%seg
        F=np.vstack([F,np.stack([np.full(seg,c0),j2,j,np.full(seg,c0)],1),np.stack([np.full(seg,c1),(n-1)*seg+j,(n-1)*seg+j2,np.full(seg,c1)],1)])
    return V,F

def join(parts):
    Vs=[];Fs=[];o=0
    for V,F in parts:
        Vs.append(np.asarray(V,dtype=float)); Fs.append(np.asarray(F)+o); o+=len(V)
    return np.vstack(Vs),np.vstack(Fs)

# ---------------- node graph helper ----------------
class G:
    def __init__(s,nt): s.nt=nt
    def N(s,typ,ins=None,**props):
        n=s.nt.nodes.new(typ)
        for k,v in props.items(): setattr(n,k,v)
        for k,v in (ins or {}).items():
            sock=n.inputs[k]
            if isinstance(v,bpy.types.NodeSocket): s.nt.links.new(v,sock)
            else: sock.default_value=v
        return n
    def link(s,a,b): s.nt.links.new(a,b)
    def math(s,op,a,b=None,c=None,clamp=False):
        ins={0:a}
        if b is not None: ins[1]=b
        if c is not None: ins[2]=c
        return s.N('ShaderNodeMath',ins,operation=op,use_clamp=clamp).outputs[0]
    def vmath(s,op,a,b=None,scale=None):
        ins={0:a}
        if b is not None: ins[1]=b
        n=s.N('ShaderNodeVectorMath',ins,operation=op)
        if scale is not None:
            sk=n.inputs['Scale']
            if isinstance(scale,bpy.types.NodeSocket): s.nt.links.new(scale,sk)
            else: sk.default_value=scale
        return n
    def mix(s,fac,a,b):
        n=s.N('ShaderNodeMix',data_type='RGBA'); 
        for idx,v in ((0,fac),(6,a),(7,b)):
            if isinstance(v,bpy.types.NodeSocket): s.nt.links.new(v,n.inputs[idx])
            else: n.inputs[idx].default_value=v
        return n.outputs[2]
    def mixf(s,fac,a,b):
        n=s.N('ShaderNodeMix',data_type='FLOAT')
        for idx,v in ((0,fac),(2,a),(3,b)):
            if isinstance(v,bpy.types.NodeSocket): s.nt.links.new(v,n.inputs[idx])
            else: n.inputs[idx].default_value=v
        return n.outputs[0]
    def ramp(s,fac,stops,interp='LINEAR'):
        n=s.N('ShaderNodeValToRGB',{0:fac}); cr=n.color_ramp; cr.interpolation=interp
        while len(cr.elements)<len(stops): cr.elements.new(.5)
        for e,(p,c) in zip(cr.elements,stops): e.position=p; e.color=c if len(c)==4 else (*c,1)
        return n.outputs[0]
    def maprange(s,v,a,b,c=0.0,d=1.0,smooth=False):
        n=s.N('ShaderNodeMapRange',{0:v,1:a,2:b,3:c,4:d}); 
        if smooth: n.interpolation_type='SMOOTHSTEP'
        return n.outputs[0]
    def noise(s,vec,scale,detail=4,rough=.5,dist=0.0,dims='3D',w=None):
        ins={'Scale':scale,'Detail':detail,'Roughness':rough,'Distortion':dist}
        if vec is not None: ins['Vector']=vec
        if w is not None: ins['W']=w
        return s.N('ShaderNodeTexNoise',ins,noise_dimensions=dims).outputs[0]
    def bump(s,height,strength=.5,dist=.02,normal=None):
        ins={'Height':height,'Strength':strength,'Distance':dist}
        if normal is not None: ins['Normal']=normal
        return s.N('ShaderNodeBump',ins).outputs[0]

def srgb(h):
    r=((h>>16)&255)/255; g=((h>>8)&255)/255; b=(h&255)/255
    f=lambda c: c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
    return (f(r),f(g),f(b),1.0)

FOG_DENS=0.00075
def fog_group():
    if 'Fog' in bpy.data.node_groups: return bpy.data.node_groups['Fog']
    ng=bpy.data.node_groups.new('Fog','ShaderNodeTree')
    ng.interface.new_socket('Shader',in_out='INPUT',socket_type='NodeSocketShader')
    ng.interface.new_socket('Shader',in_out='OUTPUT',socket_type='NodeSocketShader')
    g=G(ng); gi=g.N('NodeGroupInput'); go=g.N('NodeGroupOutput')
    cam=g.N('ShaderNodeCameraData'); geo=g.N('ShaderNodeNewGeometry')
    lp=g.N('ShaderNodeLightPath')
    d=cam.outputs['View Distance']
    hz=g.N('ShaderNodeSeparateXYZ',{0:geo.outputs['Position']}).outputs[2]
    hfall=g.math('ADD',0.35,g.math('MULTIPLY',0.65,g.math('EXPONENT',g.math('MULTIPLY',hz,-0.012))))
    fac=g.math('SUBTRACT',1.0,g.math('EXPONENT',g.math('MULTIPLY',g.math('MULTIPLY',d,hfall),-FOG_DENS)))
    fac=g.math('MULTIPLY',fac,lp.outputs['Is Camera Ray'])
    dot=g.vmath('DOT_PRODUCT',geo.outputs['Incoming'],tuple(-SUN)).outputs['Value']
    warm=g.math('POWER',g.math('MAXIMUM',dot,0.0),6.0)
    warm2=g.math('POWER',g.math('MAXIMUM',dot,0.0),60.0)
    col=g.mix(warm,(0.62,0.43,0.36,1),(1.0,0.50,0.24,1))
    col=g.mix(warm2,col,(1.15,0.72,0.36,1))
    em=g.N('ShaderNodeEmission',{'Color':col,'Strength':ng_strength()})
    ng['em_node']=em.name
    mx=g.N('ShaderNodeMixShader',{0:fac,1:gi.outputs[0],2:em.outputs[0]})
    g.link(mx.outputs[0],go.inputs[0]); return ng
_FOG_STRENGTH=[0.62]
def ng_strength(): return _FOG_STRENGTH[0]
def set_fog_strength(v):
    _FOG_STRENGTH[0]=v
    if 'Fog' in bpy.data.node_groups:
        ng=bpy.data.node_groups['Fog']; ng.nodes[ng['em_node']].inputs['Strength'].default_value=v

def new_mat(name,fog=True):
    """returns (material, G, principled node). Surface gets wrapped by fog."""
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    g=G(nt); out=g.N('ShaderNodeOutputMaterial'); p=g.N('ShaderNodeBsdfPrincipled')
    if fog:
        f=g.N('ShaderNodeGroup'); f.node_tree=fog_group(); g.link(p.outputs[0],f.inputs[0]); g.link(f.outputs[0],out.inputs['Surface'])
    else: g.link(p.outputs[0],out.inputs['Surface'])
    return m,g,p
def setp(g,p,**kw):
    names={'color':'Base Color','rough':'Roughness','metal':'Metallic','normal':'Normal','sss':'Subsurface Weight','sssr':'Subsurface Radius','ssss':'Subsurface Scale',
           'sheen':'Sheen Weight','sheenr':'Sheen Roughness','sheent':'Sheen Tint','coat':'Coat Weight','coatr':'Coat Roughness','spec':'Specular IOR Level','ior':'IOR',
           'trans':'Transmission Weight','alpha':'Alpha','emit':'Emission Color','emits':'Emission Strength','aniso':'Anisotropic'}
    for k,v in kw.items():
        sock=p.inputs[names[k]]
        if isinstance(v,bpy.types.NodeSocket): g.link(v,sock)
        else: sock.default_value=v
