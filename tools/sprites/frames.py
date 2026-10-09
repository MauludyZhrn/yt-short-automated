import numpy as np, json, pickle
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from cut import process, TONES
out={}
for name in TONES:
    a,fg=process(name)
    lab,n=ndi.label(fg)
    objs=ndi.find_objects(lab); hs=[o[0].stop-o[0].start for o in objs]; mh=np.median(hs)
    for i,o in enumerate(objs,1):                              # frame bertumpuk yang menempel -> potong di celah tersempit
        h=o[0].stop-o[0].start
        if h>1.6*mh:
            m=(lab[o]==i); rs=m.sum(1); lo,hi=int(h*.35),int(h*.65); cut=lo+int(np.argmin(rs[lo:hi]))
            n+=1; sub=lab[o]; sub[cut:][m[cut:]]=n; lab[o]=sub
    objs=ndi.find_objects(lab); areas=ndi.sum(fg,lab,range(1,n+1))
    comps=[]
    for i,(sl,ar) in enumerate(zip(objs,areas),1):
        y0,y1,x0,x1=sl[0].start,sl[0].stop,sl[1].start,sl[1].stop
        comps.append(dict(id=i,area=float(ar),box=(x0,y0,x1,y1),cx=(x0+x1)/2,cy=(y0+y1)/2))
    med=np.median([c['area'] for c in comps]); main=[c for c in comps if c['area']>=0.3*med]; small=[c for c in comps if c['area']<0.3*med]
    # rows
    main.sort(key=lambda c:c['cy']); rows=[]
    for c in main:
        if rows and c['cy']-rows[-1][-1]['cy']<85: rows[-1].append(c)      # single-linkage: baris terpisah > 85px
        else: rows.append([c])
    for r in rows: r.sort(key=lambda c:c['cx'])
    # attach small comps
    for s in small:
        best=None;bd=1e9
        for r in rows:
            for c in r:
                d=abs(s['cx']-c['cx'])+abs(s['cy']-c['cy'])*0.5
                if d<bd: bd=d;best=c
        if bd<260: best.setdefault('extra',[]).append(s)
    print(name,'rows',[len(r) for r in rows],'median area',int(med),'small',len(small))
    frames=[]
    for ri,r in enumerate(rows):
        for ci,c in enumerate(r):
            ids=[c['id']]+[e['id'] for e in c.get('extra',[])]
            m=np.isin(lab,ids)
            ys,xs=np.where(m); x0,x1,y0,y1=xs.min(),xs.max()+1,ys.min(),ys.max()+1
            rgba=np.dstack([a[y0:y1,x0:x1].astype(np.uint8),(m[y0:y1,x0:x1]*255).astype(np.uint8)])
            frames.append(dict(row=ri,col=ci,box=(int(x0),int(y0),int(x1),int(y1)),img=rgba))
    out[name]=frames
pickle.dump(out,open('frames.pkl','wb'))
# contact sheets with indices
font=ImageFont.load_default()
for name,frames in out.items():
    cols=max(f['col'] for f in frames)+1; rows=max(f['row'] for f in frames)+1
    cw,chh=150,170; W=Image.new('RGB',(cols*cw,rows*chh),(60,60,70)); d=ImageDraw.Draw(W)
    for i,f in enumerate(frames):
        im=Image.fromarray(f['img']); s=min((cw-6)/im.width,(chh-22)/im.height); im=im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.LANCZOS)
        x=f['col']*cw+(cw-im.width)//2; y=f['row']*chh+(chh-14-im.height); W.paste(im,(x,y),im)
        d.text((f['col']*cw+4,f['row']*chh+chh-13),f'{i} r{f["row"]}c{f["col"]}',fill=(255,255,0),font=font)
    W.save(f'{name}_contact.png')
