import numpy as np, pickle
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
files={'NexaTrend':('NexaTrend_TrendResearcher',3),'ByteGuard':('ByteGuard_QCInspector',8),'CrossByte':('CrossByte_Multi-PlatformPublisher',3),'EchoBee':('EchoBee_CommunityManager',3),'Metrix':('Metrix_DataAnalyst',3)}
out={}; font=ImageFont.load_default()
for k,(f,it) in files.items():
    a=np.asarray(Image.open(f'/tmp/na/New 5 Agent/{f}.png').convert('RGBA')); al=a[...,3]>40
    d=ndi.binary_dilation(al,iterations=it); lab,n=ndi.label(d); objs=ndi.find_objects(lab); areas=ndi.sum(al,lab,range(1,n+1)); med=np.median(areas)
    comps=[dict(id=i+1,box=o,cy=(o[0].start+o[0].stop)/2,cx=(o[1].start+o[1].stop)/2,h=o[0].stop-o[0].start) for i,(o,ar) in enumerate(zip(objs,areas)) if ar>=0.3*med]
    mh=np.median([c['h'] for c in comps]); comps.sort(key=lambda c:c['cy']); rows=[]
    for c in comps:
        if rows and c['cy']-rows[-1][-1]['cy']<0.6*mh: rows[-1].append(c)
        else: rows.append([c])
    for r in rows: r.sort(key=lambda c:c['cx'])
    frames=[]
    for ri,r in enumerate(rows):
        for ci,c in enumerate(r):
            o=c['box']; y0,y1,x0,x1=o[0].start,o[0].stop,o[1].start,o[1].stop
            m=(lab[y0:y1,x0:x1]==c['id']); sub=a[y0:y1,x0:x1].copy(); sub[...,3]=np.where(m&(sub[...,3]>40),sub[...,3],0)
            frames.append(dict(row=ri,col=ci,box=(x0,y0,x1,y1),img=sub))
    out[k]=frames; print(k,'rows',[len(r) for r in rows],'mh',int(mh))
    cols=max(len(r) for r in rows); cw,chh=130,150; W=Image.new('RGB',(cols*cw,len(rows)*chh),(70,72,84)); dr=ImageDraw.Draw(W)
    for i,fr in enumerate(frames):
        im=Image.fromarray(fr['img']); s=min((cw-6)/im.width,(chh-20)/im.height); im=im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.LANCZOS)
        W.paste(im,(fr['col']*cw+(cw-im.width)//2,fr['row']*chh+chh-14-im.height),im); dr.text((fr['col']*cw+3,fr['row']*chh+chh-12),str(i),fill=(255,255,0),font=font)
    W.save(f'{k}_contact.png')
pickle.dump(out,open('nframes.pkl','wb'))
