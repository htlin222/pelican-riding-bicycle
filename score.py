"""逐日 - orchestral score rendered from sampled instruments (GeneralUser GS) + synthesized low end and sound design.
Bars are 3 s (80 BPM, 4/4). Take-off downbeat lands at 45.0 s."""
import numpy as np, tinysoundfont, math, sys, os
from scipy import signal
SR=44100; BEAT=0.75; BAR=3.0; DUR=66.0; TAIL=4.0; N=int((DUR+TAIL)*SR)
SF=os.path.join(os.path.dirname(os.path.abspath(__file__)),'gugs','GeneralUser-GS.sf2')
rng=np.random.RandomState(3)

def render(notes,bank,preset,cc=()):
    """notes: (t,dur,key,vel). cc: (t,controller,value)"""
    syn=tinysoundfont.Synth(samplerate=SR); sf=syn.sfload(SF); syn.program_select(0,sf,bank,preset)
    ev=[]
    for (t,d,k,v) in notes:
        t=max(0,t+rng.uniform(-0.006,0.006)); v=int(np.clip(v+rng.randint(-5,6),1,127))
        ev.append((t,1,int(k),v)); ev.append((t+d,0,int(k),0))
    for (t,c,v) in cc: ev.append((t,2,int(c),int(np.clip(v,0,127))))
    ev.sort(key=lambda e:(e[0],e[1]))
    out=np.zeros((N,2),np.float32); pos=0
    for (t,typ,a,b) in ev:
        n=min(N,int(t*SR))-pos
        if n>0:
            out[pos:pos+n]=np.frombuffer(syn.generate(n),dtype=np.float32).reshape(-1,2); pos+=n
        if typ==1: syn.noteon(0,a,b)
        elif typ==0: syn.noteoff(0,a)
        else: syn.control_change(0,a,b)
    if pos<N: out[pos:]=np.frombuffer(syn.generate(N-pos),dtype=np.float32).reshape(-1,2)
    return out.astype(np.float64)

def bt(bar,beat=0.0): return bar*BAR+beat*BEAT
CH={'Dm':(38,[50,57,62,65,69]),'Bb':(34,[46,53,58,62,65]),'F':(41,[53,60,65,69,72]),'C':(36,[48,55,60,64,67]),'A':(33,[45,52,57,61,64])}
TRI={'Dm':(50,53,57),'Bb':(46,50,53),'F':(53,57,60),'C':(48,52,55),'A':(45,49,52)}
PROG=['Dm','Dm','Dm','Bb','F','C','Dm','Bb','F','C','Dm','Bb','F','C','A','F','C','Dm','Bb','F','C','F']
T1=[[(62,1.5),(65,.5),(69,2)],[(70,1.5),(69,.5),(65,1),(62,1)],[(65,1.5),(67,.5),(69,1),(72,1)],[(67,2.5),(64,.5),(67,1)]]
T2=[[(69,1),(74,1),(77,1.5),(76,.5)],[(74,1.5),(77,.5),(82,2)],[(81,1.5),(79,.5),(77,1),(72,1)],[(76,1.5),(74,.5),(76,1),(79,1)]]
T3=[[(72,1),(77,1),(81,2)],[(79,1.5),(76,.5),(79,1),(84,1)],[(81,1.5),(79,.5),(77,1),(74,1)],[(74,1),(77,1),(82,1.5),(81,.5)]]
def mel(bar,line,tr=0,vel=90,leg=0.98):
    out=[];b=0
    for k,d in line: out.append((bt(bar,b),d*BEAT*leg,k+tr,vel)); b+=d
    return out
def swell(t0,t1,v0,v1,steps=16,cc=11): return [(t0+(t1-t0)*i/steps,cc,v0+(v1-v0)*i/steps) for i in range(steps+1)]

S={}   # stems
def add(name,x,gain_db,pan=0.0):
    g=10**(gain_db/20); l=g*math.cos((pan+1)*math.pi/4)*1.414; r=g*math.sin((pan+1)*math.pi/4)*1.414
    y=x*np.array([l,r]); S[name]=S.get(name,0)+y

# ---------------- strings pad (slow strings) ----------------
pad=[];padcc=[]
for b,c in enumerate(PROG):
    root,v=CH[c]
    if b<2: ks=[root+12,v[1],v[2]+12]; vel=46
    elif b<6: ks=v; vel=58
    elif b<10: ks=v+[v[4]+12-12]; vel=70
    elif b<14: ks=v+[v[2]+12]; vel=84
    elif b==14: ks=v+[v[3]+12]; vel=88
    elif b<19: ks=v+[v[2]+12,v[4]+12]; vel=104
    else: ks=v; vel=66 if b<21 else 54
    dur=BAR*1.02 if b!=14 else 2.2
    for k in ks: pad.append((bt(b),dur,k,vel))
padcc+=swell(0,6,40,80)+swell(bt(14),bt(14)+2.2,70,127)+[(bt(14)+2.26,11,0),(bt(15)-0.05,11,127)]+swell(bt(19),bt(22),127,40,24)
add('pad',render(pad,0,49,padcc),-9,-0.1)
# high violins sustain (dawn shimmer + triumphant top)
hi=[(0.5,5.6,81,40),(bt(1),3.0,86,36)]
for b in range(15,19): hi.append((bt(b),BAR,CH[PROG[b]][1][2]+24,92))
for b in range(19,22): hi.append((bt(b),BAR,CH[PROG[b]][1][2]+24,60))
add('hi',render(hi,0,44,swell(0,6,30,90)+[(bt(15)-.05,11,127)]+swell(bt(19),bt(22),110,30)),-15,-0.35)
# ---------------- low strings: drone, pizz, chug ----------------
low=[(0.0,6.2,26,60),(0.0,6.2,38,50)]
for b in range(2,6):
    r=CH[PROG[b]][0]; low+=[(bt(b),BAR,r,62)]
for b in range(6,14):
    r=CH[PROG[b]][0]
    for st in (0,3,6,8,11,14): low.append((bt(b,st/4),0.20 if b<10 else 0.24,r,(88 if st in(0,8) else 72)+(10 if b>=10 else 0))); low.append((bt(b,st/4),0.2,r+12,70 if b<10 else 84))
r=CH['A'][0]
for st in range(12): low.append((bt(14,st/4),0.16,r,70+st*4));
for b in range(15,19):
    r=CH[PROG[b]][0]; low+=[(bt(b),BAR*0.98,r,112),(bt(b),BAR*0.98,r+12,100)]
for b in range(19,22): low.append((bt(b),BAR,CH[PROG[b]][0],64))
add('basses',render(low,0,43),-7,0.25); add('celli',render([(t,d,k+12,v-6) for t,d,k,v in low if k<46],0,42),-11,0.15)
# ---------------- spiccato ostinato ----------------
ost=[]
for b in range(4,14):
    r,f_,t3=TRI[PROG[b]][0],TRI[PROG[b]][2],TRI[PROG[b]][1]
    pat=[r+12,r+12,f_,r+12,t3+12,r+12,f_,r+12,r+12,r+12,f_,r+12,t3+12,f_+12,t3+12,f_]
    step=2 if b<6 else 1
    for i in range(0,16,step):
        vel=(56 if b<6 else 74 if b<10 else 92)+(16 if i%4==0 else 0)
        ost.append((bt(b,i/4),0.11,pat[i],vel))
        if b>=10: ost.append((bt(b,i/4),0.11,pat[i]+12,vel-14))
for i in range(12): ost.append((bt(14,i/4),0.11,57+[0,2,4,5,7,9,11,12,14,16,17,19][i],80+i*4))
for b in range(15,19):
    r,t3,f_=TRI[PROG[b]]
    for i in range(0,16,2): ost.append((bt(b,i/4),0.14,[r+12,f_+12,t3+24,f_+12][(i//2)%4],78))
add('ost',render(ost,0,48),-10,-0.3)
# ---------------- harp ----------------
harp=[]
for b in range(0,6):
    v=CH[PROG[b]][1]; seq=[v[0],v[1],v[2],v[3],v[4],v[3],v[2],v[1]]
    for i,k in enumerate(seq): harp.append((bt(b,i/2),1.2,k+12,44 if b<2 else 56))
for b in range(15,22):
    v=CH[PROG[b]][1]
    for i in range(12): harp.append((bt(b)+i*0.045,2.0,[v[0],v[1],v[2],v[3],v[4]][i%5]+12*(i//5),70 if b<19 else 48))
add('harp',render(harp,0,46),-11,0.4)
# ---------------- horns: theme ----------------
horn=[(bt(1),BEAT*1.95,62,62),(bt(1,2),BEAT*1.95,69,66)]
for b in range(2,6): horn+=mel(b,T1[b-2],0,72)
for b in range(6,10): horn+=mel(b,T1[b-6],0,96)+mel(b,T1[b-6],-12,84)
for b in range(10,14): horn+=mel(b,T2[b-10],-12,104)
horn+=[(bt(14),2.2,57,90),(bt(14),2.2,64,90),(bt(14),2.2,69,96)]
for b in range(15,19): horn+=mel(b,T3[b-15],-12,118)+mel(b,T3[b-15],-24,104)
horn+=[(bt(19),BAR*0.97,69,70),(bt(20),BAR*0.97,67,64),(bt(21),BAR,65,56),(bt(21),BAR,60,50)]
add('horns',render(horn,0,60,swell(bt(14),bt(14)+2.2,60,127)+[(bt(14)+2.26,11,0),(bt(15)-.05,11,127)]),-5.5,-0.2)
# ---------------- trumpets + violins carry theme 2/3 ----------------
tp=[]
for b in range(10,14): tp+=mel(b,T2[b-10],0,92)
for b in range(15,19): tp+=mel(b,T3[b-15],0,110)
add('trumpets',render(tp,0,56),-12.5,0.2)
vl=[]
for b in range(6,10): vl+=mel(b,T1[b-6],12,80)
for b in range(10,14): vl+=mel(b,T2[b-10],0,96)+mel(b,T2[b-10],12,84)
for b in range(15,19): vl+=mel(b,T3[b-15],0,110)+mel(b,T3[b-15],12,100)
add('violins',render(vl,0,48),-9.5,-0.4)
# ---------------- brass section / trombones / tuba ----------------
br=[]
for b in range(10,14):
    r=CH[PROG[b]][0]; tr_=TRI[PROG[b]]
    for st in (0,3,6,8,11,14): br+=[(bt(b,st/4),0.22,k,96 if st in(0,8) else 80) for k in (r+12,r+19)]
    br+=[(bt(b),BAR*0.97,k,84) for k in tr_]
br+=[(bt(14),2.2,k,92) for k in (45,52,57,61)]
for b in range(15,19): br+=[(bt(b),BAR*0.98,k,112) for k in TRI[PROG[b]]]+[(bt(b),BAR*0.98,TRI[PROG[b]][0]+12,104)]
add('brass',render(br,0,61,swell(bt(14),bt(14)+2.2,50,127)+[(bt(14)+2.26,11,0),(bt(15)-.05,11,127)]),-10,0.3)
tb=[]
for b in range(10,14):
    r=CH[PROG[b]][0]
    for st in (0,3,6,8,11,14): tb.append((bt(b,st/4),0.24,r+12,100 if st in(0,8) else 84))
for b in range(15,19): tb+=[(bt(b),BAR*0.98,CH[PROG[b]][0]+12,112),(bt(b),BAR*0.98,CH[PROG[b]][0]+19,104)]
add('trombones',render(tb,0,57),-10,0.35)
add('tuba',render([(t,d,k-12,v) for t,d,k,v in tb],0,58),-10,0.1)
# ---------------- choir ----------------
ch=[]
for b in range(10,14): ch+=[(bt(b),BAR*1.0,k+12,78) for k in TRI[PROG[b]]]
for b in range(15,19): ch+=[(bt(b),BAR*1.0,k+12,112) for k in TRI[PROG[b]]]+[(bt(b),BAR,TRI[PROG[b]][0]+24,104),(bt(b),BAR,TRI[PROG[b]][0],96)]
for b in range(19,22): ch+=[(bt(b),BAR*1.0,k+12,70 if b<21 else 56) for k in TRI[PROG[b]]]
add('choir',render(ch,0,52,[(bt(15)-.05,11,127)]+swell(bt(19),bt(22),120,40)),-8.5,0.0)
# ---------------- bells ----------------
bl=[(bt(b),2.8,CH[PROG[b]][1][0]+12,100) for b in range(15,19)]+[(bt(21),3.0,65,60)]
add('bells',render(bl,0,14),-14,0.15)
# ---------------- percussion ----------------
timp=[(bt(b),1.2,CH[PROG[b]][0]+12,70 if b<10 else 100) for b in range(6,14)]
timp+=[(bt(b,2),0.8,CH[PROG[b]][0]+12,84) for b in range(10,14)]
timp+=[(bt(14)+i*0.09,0.2,45,int(50+i*3)) for i in range(25)]
timp+=[(bt(b),2.0,CH[PROG[b]][0]+12,120) for b in range(15,19)]+[(bt(b,2.5),0.3,CH[PROG[b]][0]+12,96) for b in range(15,19)]+[(bt(b,3),0.6,CH[PROG[b]][0]+12,104) for b in range(15,19)]
timp+=[(bt(19),2,53,70),(bt(21),2.5,41,60)]
add('timp',render(timp,0,47),-6,-0.15)
tk=[]
for b in range(6,10): tk+=[(bt(b),0.5,45,96),(bt(b,2),0.5,45,80)]+([(bt(b,3.5),0.4,47,72)] if b%2 else [])
for b in range(10,14):
    for st in (0,3,6,8,11,14): tk.append((bt(b,st/4),0.4,43 if st in(0,8) else 47,118 if st in(0,8) else 96))
    tk+=[(bt(b,3.75),0.2,50,84)]
for st,(p,v) in enumerate([(0,90),(4,96),(8,104),(10,110),(11,116)]): tk.append((bt(14,p/4),0.4,43,v))
for b in range(15,19): tk+=[(bt(b),0.8,41,127),(bt(b,2),0.6,43,112),(bt(b,3),0.4,47,90),(bt(b,3.5),0.4,45,96)]
add('taiko',render(tk,0,116),-4,0.1)
orch=[(bt(b),2.5,57,110) for b in (10,12)]+[(bt(15),4,57,127),(bt(15),4,49,120),(bt(17),3,57,104)]
orch+=[(bt(b),0.8,36,127) for b in (10,11,12,13,15,16,17,18)]
orch+=[(bt(14)+i*0.07,0.1,38,int(30+i*2.7)) for i in range(32)]
add('kit',render(orch,128,48),-8,0.0)
add('revcym',render([(bt(14)+0.25,2.0,60,100),(bt(9)+1.2,1.8,60,70)],0,119),-14,0.0)

# ---------------- synthesized layers ----------------
t=np.arange(N)/SR
def env_ad(t0,a,d):
    x=t-t0; return np.where(x<0,0,np.where(x<a,x/a,np.exp(-(x-a)/d)))
def lp(x,fc,order=2): b,a=signal.butter(order,fc/(SR/2)); return signal.lfilter(b,a,x,axis=0)
def hp(x,fc,order=2): b,a=signal.butter(order,fc/(SR/2),'high'); return signal.lfilter(b,a,x,axis=0)
def bp(x,f1,f2): b,a=signal.butter(2,[f1/(SR/2),f2/(SR/2)],'band'); return signal.lfilter(b,a,x,axis=0)
sub=np.zeros(N)
def boom(t0,g,f0=62,f1=30,d=1.6):
    global sub
    x=t-t0; ph=2*np.pi*np.cumsum(np.where(x>0,f1+(f0-f1)*np.exp(-np.maximum(x,0)/0.18),0))/SR
    sub+=g*np.sin(ph)*env_ad(t0,0.004,d)
for b in (10,11,12,13): boom(bt(b),0.5,d=0.9)
boom(bt(15),1.0,70,28,2.6)
for b in (16,17,18): boom(bt(b),0.6,d=1.4)
boom(bt(21),0.35,d=2.0)
# braam: detuned saw stack on D1/F1
def braam(t0,f,g,d):
    x=np.zeros(N)
    for det in (-9,-4,0,5,11):
        ff=f*2**(det/1200); x+=signal.sawtooth(2*np.pi*ff*t+rng.uniform(0,6))+0.5*signal.sawtooth(2*np.pi*ff*2*t+rng.uniform(0,6))
    e=np.where((t>=t0)&(t<t0+d),np.minimum((t-t0)/0.08,1)*np.exp(-np.maximum(t-t0-d*0.5,0)/(d*0.3)),0)
    return lp(x*e,420,3)*g
braams=braam(bt(15),43.65,0.22,2.8)+braam(bt(17),36.7,0.16,2.6)+braam(bt(10),36.7,0.10,1.6)+braam(bt(12),43.65,0.10,1.6)
add('sub',np.stack([sub,sub],1),-9); add('braam',np.stack([braams,np.roll(braams,37)],1),-7)
noise=rng.randn(N,2)
# wind + sea bed (whole film), louder in the silence before the drop and in flight
wind=bp(noise,180,900)*(0.5+0.5*np.sin(2*np.pi*0.11*t+1)[:,None])*(0.6+0.4*np.sin(2*np.pi*0.037*t)[:,None])
sea=bp(noise,90,700)*(0.55+0.45*np.sin(2*np.pi*0.085*t)[:,None])**2
amb_env=np.interp(t,[0,1.5,6,40,44,45,52,60,64,66,70],[0,1,0.75,0.5,1.0,0.7,0.8,0.6,0.5,0.0,0.0])[:,None]
add('amb',(wind*0.8+sea*1.0)*amb_env,-30)
# riser into the drop + whoosh on take-off + reverse swell
ris=bp(noise,300,9000)*np.where((t>bt(14))&(t<bt(14)+2.25),np.clip((t-bt(14))/2.25,0,1)**2.2,0)[:,None]
sw=signal.sosfilt(signal.butter(2,[400/(SR/2),6000/(SR/2)],'band',output='sos'),noise,axis=0)
who=sw*(np.exp(-((t-45.05)/0.35)**2)+0.5*np.exp(-((t-44.75)/0.12)**2))[:,None]
add('fx',ris*0.5+who*0.6,-13)
# free-wheel tick + tyre hum while on the road (0-44 s)
tick=np.zeros(N); period=0.085
for k in np.arange(2.0,44.0,period):
    i=int(k*SR);
    if i+200<N: tick[i:i+200]+=rng.uniform(0.6,1.0)*np.exp(-np.arange(200)/22.0)*np.sin(2*np.pi*3800*np.arange(200)/SR)
hum=bp(noise[:,0],70,260)*np.interp(t,[0,2,43.9,44.6,70],[0,1,1,0,0])
add('bike',np.stack([tick*0.5+hum*1.2]*2,1)*np.interp(t,[0,6,12,21,30,44,45],[0.2,1.0,0.6,0.9,0.6,0.8,0.0])[:,None],-26,0.0)
# wing beats in flight (slow-mo then real-time)
wb=np.zeros(N)
for k in np.arange(45.2,64.5,1.55): wb+=np.exp(-((t-k)/0.16)**2)
add('wings',lp(noise,700)*wb[:,None],-21)

# ---------------- reverb + mix ----------------
def hall(rt=2.9,pre=0.028):
    n=int(rt*1.4*SR); x=rng.randn(n,2)*np.exp(-6.9*np.arange(n)/(rt*SR))[:,None]
    x=lp(x,5200); x[:int(pre*SR)]=0; x[int(pre*SR):int(pre*SR)+int(0.05*SR)]*=np.linspace(0.2,1,int(0.05*SR))[:,None]
    return x/np.sqrt((x**2).sum(0))
IR=hall()
WET={'pad':.45,'hi':.5,'basses':.18,'celli':.25,'ost':.3,'harp':.4,'horns':.55,'trumpets':.45,'violins':.45,'brass':.4,'trombones':.35,'tuba':.25,'choir':.6,'bells':.5,
     'timp':.35,'taiko':.3,'kit':.3,'revcym':.4,'sub':0,'braam':.2,'amb':0,'fx':.3,'bike':.05,'wings':.2}
dry=np.zeros((N,2)); send=np.zeros((N,2))
for k,x in S.items():
    x=hp(x,28) if k not in('sub',) else x
    dry+=x; send+=x*WET.get(k,.3)
wet=np.stack([signal.fftconvolve(send[:,c],IR[:,c])[:N] for c in range(2)],1)
mix=dry+wet*0.9
mix=mix-0.42*lp(mix,110)+0.85*hp(mix,3800)+0.35*hp(mix,9000)
mix*=np.interp(t,[0,16,19,44.22,44.36,44.93,45.0,70],[1.45,1.45,1.0,1.0,0.16,0.14,1.0,1.0])[:,None]
# glue compression (slow RMS) + soft limiter
rms=np.sqrt(lp((mix**2).sum(1),8,1).clip(1e-9)); thr=np.percentile(rms,85)*0.9
gain=np.where(rms>thr,(thr/rms)**0.35,1.0); mix*=gain[:,None]
mix*=np.interp(t,[0,0.4,DUR-0.9,DUR,DUR+TAIL],[0,1,1,0,0])[:,None]
mix/=np.abs(mix).max()/1.6; mix=np.tanh(mix)*0.97
out=sys.argv[1] if len(sys.argv)>1 else 'score.wav'
from scipy.io import wavfile
wavfile.write(out,SR,(mix[:int(DUR*SR)]*32767).astype(np.int16))
# section loudness report
for a,b,nm in ((0,6,'dawn'),(6,18,'theme'),(18,30,'drive'),(30,42,'full'),(42,44.25,'build'),(44.3,44.95,'breath'),(45,57,'flight'),(57,66,'outro')):
    seg=mix[int(a*SR):int(b*SR)]; print('%-7s rms %.1f dB  peak %.1f dB'%(nm,20*np.log10(np.sqrt((seg**2).mean())+1e-9),20*np.log10(np.abs(seg).max()+1e-9)))
