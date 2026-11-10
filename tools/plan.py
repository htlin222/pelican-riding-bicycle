import json
c=json.load(open('render.json')); jobs=[]
base=dict(tag=c['tag'],w=c.get('w',1280),h=c.get('h',536),spp=c.get('spp',32))
if c['mode']=='stills':
    for i,t in enumerate(c['times']): jobs.append(dict(base,id='s%02d'%i,mode='stills',args=str(t)))
else:
    n=c.get('frames',1584); k=c.get('chunks',40); a0=c.get('start',0)
    for i in range(k):
        a=a0+(n-a0)*i//k; b=a0+(n-a0)*(i+1)//k
        if b>a: jobs.append(dict(base,id='c%03d'%(i+c.get('id0',0)),mode='range',args='%d %d'%(a,b)))
print(json.dumps(jobs,separators=(',',':')))
