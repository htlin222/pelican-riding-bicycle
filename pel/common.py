"""Shared world maths + Blender helpers for 逐日 (Chasing the Sun)."""
import math, numpy as np
FPS=24; DUR=66.0
V=7.5; WJ=44.4; XJ=V*WJ          # speed m/s, take-off world-time, take-off x
SEA=0.0
SUN_EL=math.radians(3.2); SUN_AZ=math.radians(-3.0)
SUN=np.array([math.cos(SUN_EL)*math.cos(SUN_AZ), math.cos(SUN_EL)*math.sin(SUN_AZ), math.sin(SUN_EL)])
LANE=-1.75                        # rider rides the sea-side lane (sea is -Y)

def clamp(x,a,b): return np.minimum(b,np.maximum(a,x))
def smooth(a,b,x):
    t=clamp((x-a)/(b-a),0.0,1.0); return t*t*(3-2*t)

# ---- value noise (vectorised) ----
def _hash(ix,iy,seed=0):
    h=np.sin(ix*127.1+iy*311.7+seed*74.7)*43758.5453
    return h-np.floor(h)
def vnoise(x,y,seed=0):
    ix=np.floor(x); iy=np.floor(y); fx=x-ix; fy=y-iy
    u=fx*fx*(3-2*fx); v=fy*fy*(3-2*fy)
    a=_hash(ix,iy,seed); b=_hash(ix+1,iy,seed); c=_hash(ix,iy+1,seed); d=_hash(ix+1,iy+1,seed)
    return a+(b-a)*u+(c-a)*v+(a-b-c+d)*u*v
def fbm(x,y,oct=5,seed=0):
    s=0; a=.5; n=0
    for i in range(oct):
        s=s+a*vnoise(x,y,seed+i); n+=a; x=x*2.03+17.1; y=y*2.03+9.7; a*=.5
    return s/n
def ridge(x,y,oct=5,seed=0):
    s=0; a=.5; n=0; w=1.0
    for i in range(oct):
        r=1-np.abs(2*vnoise(x,y,seed+i)-1); r=r*r*w; w=clamp(r*1.6,0,1)
        s=s+a*r; n+=a; x=x*2.07+31.3; y=y*2.07+5.2; a*=.5
    return s/n

# ---- road ----
def roadZ(x):
    x=np.asarray(x,dtype=float); c=clamp((x-240)/93.0,0,1)
    return 24+2.2*np.sin(x*.018)+1.0*np.sin(x*.047+1)+13*c*c
def roadC(x):
    x=np.asarray(x,dtype=float)
    return (9*np.sin(x*.016+.5)+4*np.sin(x*.037+2))*(1-smooth(245,320,x))
def roadZs(x): return (roadZ(x+.05)-roadZ(x-.05))/.1
def roadCs(x): return (roadC(x+.05)-roadC(x-.05))/.1

STACKS=[(398,-70,27,14),(440,-104,19,10),(300,-88,22,11),(150,-96,31,13),(476,-52,12,8),(60,-78,14,9),(540,-80,16,9),(232,-120,11,7)]
def terrainH(x,y):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    rz=roadZ(x); d=y-roadC(x)
    # inland
    s=smooth(4.6,240,d)**1.25
    wx=x+38*(fbm(x*.006+7,y*.006,3,71)-.5); wy=y+38*(fbm(x*.006,y*.006+3,3,73)-.5)
    M=26+250*ridge(wx*.0032+3,wy*.0032,5,1)+40*fbm(x*.011,y*.011,4,7)+22*(fbm(wx*.024,wy*.024,5,75)-.5)+9*ridge(wx*.06,wy*.06,4,77)
    roll=(fbm(x*.045,y*.045,4,3)-.5)*3.2*smooth(4.6,22,d)
    ditch=-0.35*smooth(4.4,5.6,d)*(1-smooth(5.6,9,d))
    inland=rz+s*M+roll+ditch
    # sea side: shoulder then cliff
    e=-d
    cn=fbm(x*.06,y*.06,4,11)
    edge=6.3+2.8*(fbm(x*.03,0*y,3,5)-.5)
    c=smooth(edge,edge+15+10*cn,e)
    ledge=(fbm(x*.09+4,y*.09,4,13)-.5)*5*smooth(edge,edge+4,e)*(1-smooth(edge+14,edge+30,e))
    floor=-7+3*fbm(x*.02,y*.02,3,17)
    seaside=rz+(floor-rz)*c**0.8+ledge-0.25*smooth(4.4,edge,e)
    h=np.where(d>=0,inland,seaside)
    # headland end
    inl=smooth(20,120,d); f=smooth(XJ+inl*55,XJ+5+inl*150,x)
    endn=-np.abs(fbm(x*.08,y*.08,4,19)-.5)*6*f*(1-f)*4
    h=h+(floor-h)*f+endn
    # sea stacks
    for (sx,sy,sh,sr) in STACKS:
        r=np.sqrt((x-sx)**2+(y-sy)**2)
        ax=x+5*(fbm(x*.11+sx,y*.11,3,81)-.5); ay=y+5*(fbm(x*.11,y*.11+sy,3,83)-.5)
        r=np.sqrt((ax-sx)**2+(ay-sy)**2)
        re=r/(sr*(0.55+0.9*fbm(ax*.07+sx,ay*.07,4,29)))
        prof=(1-smooth(0.22,1.0,re))**0.55
        top=0.5+0.5*ridge(ax*.08+sy,ay*.08,4,23)+0.16*fbm(x*.45,y*.45,3,31)-0.10*np.floor(fbm(ax*.2,ay*.2,2,33)*4)/4
        h=np.maximum(h, -7+(sh+7)*prof*top)
    return h

# ---- timeline ----
def worldTime(t):
    if t<44: return t
    if t<52: return 44+(t-44)*.4
    return 47.2+(t-52)*.7
ZJ=float(roadZ(XJ)); SJ=float(roadZs(XJ)); VZ=SJ*V; KF=.35
def flightZ(u): return ZJ+VZ/KF*(1-math.exp(-KF*u))+0.9*(1-math.cos(u*.8))
def pathPoint(x):
    """centre of rider lane on the road surface"""
    return np.array([x, float(roadC(x))+LANE, float(roadZ(x))+0.02])
# arc length table for wheel rotation
_xs=np.arange(-200,XJ+400,0.25)
_pts=np.stack([_xs,roadC(_xs)+LANE,roadZ(_xs)],1)
_seg=np.linalg.norm(np.diff(_pts,axis=0),axis=1); _S=np.concatenate([[0],np.cumsum(_seg)])
def arclen(x): return float(np.interp(x,_xs,_S))
