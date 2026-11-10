"""Tiny numpy SDF modelling kit -> marching cubes mesh."""
import numpy as np
from skimage import measure
def smin(a,b,k):
    h=np.clip(0.5+0.5*(b-a)/k,0,1); return b+(a-b)*h-k*h*(1-h)
def smax(a,b,k): return -smin(-a,-b,k)
def ellipsoid(P,c,r):
    c=np.asarray(c); r=np.asarray(r,dtype=float)
    q=(P-c)/r; k0=np.linalg.norm(q,axis=-1); k1=np.linalg.norm(q/r,axis=-1)+1e-9
    return k0*(k0-1.0)/k1
def sphere(P,c,r): return np.linalg.norm(P-np.asarray(c),axis=-1)-r
def roundcone(P,a,b,r1,r2):
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    ba=b-a; l2=np.dot(ba,ba); rr=r1-r2; a2=l2-rr*rr; il2=1.0/l2
    pa=P-a; y=np.einsum('...i,i->...',pa,ba); z=y-l2
    xx=pa*l2-ba*y[...,None]; x2=np.einsum('...i,...i->...',xx,xx)
    y2=y*y*l2; z2=z*z*l2
    k=np.sign(rr)*rr*rr*x2
    d1=np.sqrt(x2+z2)*il2-r2
    d2=np.sqrt(x2+y2)*il2-r1
    d3=(np.sqrt(np.maximum(x2*a2*il2,0))+y*rr)*il2-r1
    return np.where(np.sign(z)*a2*z2>k,d1,np.where(np.sign(y)*a2*y2<k,d2,d3))
def chain(P,pts,radii,k=None):
    d=None
    for i in range(len(pts)-1):
        e=roundcone(P,pts[i],pts[i+1],radii[i],radii[i+1])
        d=e if d is None else (np.minimum(d,e) if k is None else smin(d,e,k))
    return d
def grid(lo,hi,vox):
    lo=np.asarray(lo,dtype=float); hi=np.asarray(hi,dtype=float)
    ax=[np.arange(lo[i],hi[i]+vox,vox) for i in range(3)]
    X,Y,Z=np.meshgrid(*ax,indexing='ij'); return np.stack([X,Y,Z],-1),lo
def mesh(field,lo,vox,smooth_iters=2):
    v,f,n,_=measure.marching_cubes(field,level=0.0,spacing=(vox,vox,vox))
    v=v+lo
    if smooth_iters:
        # simple umbrella smoothing to kill voxel stair-steps
        import scipy.sparse as sp
        nV=len(v); e=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]); e=np.concatenate([e,e[:,::-1]])
        A=sp.coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(nV,nV)).tocsr(); A.data[:]=1
        deg=np.asarray(A.sum(1)).ravel()[:,None]
        for _ in range(smooth_iters):
            v=0.5*v+0.5*(A@v)/deg
    return v,f[:,::-1]
def n3(P,freq,seed=0):
    Q=P*freq; I=np.floor(Q); Fr=Q-I; U=Fr*Fr*(3-2*Fr)
    def h(ix,iy,iz):
        v=np.sin(ix*127.1+iy*311.7+iz*74.7+seed*19.19)*43758.5453; return v-np.floor(v)
    x,y,z=I[...,0],I[...,1],I[...,2]; ux,uy,uz=U[...,0],U[...,1],U[...,2]
    c00=h(x,y,z)*(1-ux)+h(x+1,y,z)*ux; c10=h(x,y+1,z)*(1-ux)+h(x+1,y+1,z)*ux
    c01=h(x,y,z+1)*(1-ux)+h(x+1,y,z+1)*ux; c11=h(x,y+1,z+1)*(1-ux)+h(x+1,y+1,z+1)*ux
    return (c00*(1-uy)+c10*uy)*(1-uz)+(c01*(1-uy)+c11*uy)*uz
def fbm3(P,freq,oct=3,seed=0):
    s=0;a=.5;n=0
    for i in range(oct): s=s+a*n3(P,freq,seed+i); n+=a; freq*=2.1; a*=.5
    return s/n
