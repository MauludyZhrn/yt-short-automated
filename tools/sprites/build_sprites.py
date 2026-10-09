import pickle, json, numpy as np, os
from PIL import Image
from scipy import ndimage as ndi
frames=pickle.load(open('frames.pkl','rb'))
CW,CH,FOOT,IDLE_H,COLS=80,92,86,64,12
R=lambda a,b:list(range(a,b))
ANIMS={
 'MorbMyth':dict(idle=R(0,6),walkR=R(12,24),walkD=R(37,42),walkU=[65,66,67,68],wave=R(24,30),cheer=[30,31,32,33,32,31],think=R(54,60),speak=R(24,30)),
 'KaelQuill':dict(idle=R(0,6),walkR=R(12,18),walkU=R(52,58),wave=R(24,30),cheer=[30,31,32,33,32,31],alert=[34,35],think=R(36,42),read=[46,47],type=[46,47],run=R(42,46),speak=R(24,30)),
 'VoxArden':dict(idle=R(0,6),walkR=R(12,24),walkU=R(52,58),wave=R(24,30),cheer=[30,31,32,33,32,31],alert=[34,35],speak=R(46,52),run=R(42,46),think=R(36,42)),
 'MikaPixel':dict(idle=R(0,6),walkR=R(12,18),walkU=[57,58,59,53],wave=R(18,24),cheer=[27,28,29,28],type=R(30,36),read=R(6,12),think=R(36,42),run=R(42,48),speak=[24,25,26,25]),
 'RivenCut':dict(idle=R(0,10),walkR=[10,11,12,11],wave=[14,15,16,15],cheer=[17,18,19,18],type=[20,23,24,28,29,28],run=[25,26],speak=[14,15,16,15]),
}
IDS={'MorbMyth':'ceo','KaelQuill':'scriptwriter','VoxArden':'voiceactor','MikaPixel':'designer','RivenCut':'editor'}
os.makedirs('out',exist_ok=True); meta={}
for name,anims in ANIMS.items():
    fr=frames[name]; need=sorted({i for v in anims.values() for i in v})
    idle_h=np.median([fr[i]['img'].shape[0] for i in anims['idle']]); f=IDLE_H/idle_h
    # baseline per baris = median dasar frame pada baris itu
    rows={}
    for i,x in enumerate(fr): rows.setdefault(x['row'],[]).append(x['box'][3])
    base={r:np.median(v) for r,v in rows.items()}
    prepared={}
    for i in need:
        x=fr[i]; img=x['img'].copy(); a=img[...,3]>127
        a=ndi.binary_opening(a,structure=np.ones((3,3),bool))
        lab,n=ndi.label(a)
        if n>1:
            sizes=ndi.sum(a,lab,range(1,n+1)); a=lab==(1+int(np.argmax(sizes)))        # buang bayangan/serpihan terpisah
        a=ndi.binary_fill_holes(a)
        img[...,3]=(a*255).astype(np.uint8)
        h,w=a.shape; ys,xs=np.where(a); low=ys>h*0.65
        ax=xs[low].mean() if low.any() else xs.mean()                                  # jangkar x = pusat kaki
        float_off=(base[x['row']]-x['box'][3])                                         # frame melompat tetap melayang
        prepared[i]=(img,ax,float_off)
    # skala + letakkan di sel
    cells={}
    for i,(img,ax,fo) in prepared.items():
        h,w=img.shape[:2]; nw,nh=max(1,round(w*f)),max(1,round(h*f))
        im=Image.fromarray(img).resize((nw,nh),Image.BOX)
        cell=Image.new('RGBA',(CW,CH),(0,0,0,0)); px=int(round(CW/2-ax*f)); py=int(round(FOOT-nh-max(0,fo)*f))
        cell.paste(im,(px,py),im); cells[i]=cell
    # palet global per karakter
    sample=[]
    for c in cells.values():
        arr=np.asarray(c); m=arr[...,3]>127; sample.append(arr[m][:,:3])
    sample=np.concatenate(sample); rng=np.random.default_rng(1); sample=sample[rng.choice(len(sample),min(len(sample),120000),replace=False)]
    side=int(np.ceil(np.sqrt(len(sample)))); pad=np.zeros((side*side,3),np.uint8); pad[:len(sample)]=sample
    pal=Image.fromarray(pad.reshape(side,side,3)).quantize(colors=40,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    order={i:k for k,i in enumerate(need)}; rows_n=int(np.ceil(len(need)/COLS)); atlas=Image.new('RGBA',(COLS*CW,rows_n*CH),(0,0,0,0))
    for i,c in cells.items():
        arr=np.asarray(c); alpha=(arr[...,3]>127)
        q=Image.fromarray(arr[...,:3]).quantize(palette=pal,dither=Image.Dither.NONE).convert('RGB')
        out=np.dstack([np.asarray(q),(alpha*255).astype(np.uint8)]); k=order[i]
        atlas.paste(Image.fromarray(out),((k%COLS)*CW,(k//COLS)*CH))
    sid=IDS[name]; atlas.save(f'out/{sid}.png',optimize=True)
    meta[sid]=dict(w=CW,h=CH,foot=FOOT,cols=COLS,rows=rows_n,idleH=IDLE_H,anims={k:[order[i] for i in v] for k,v in anims.items()})
    print(name,sid,'frames',len(need),'scale %.3f'%f,'atlas',atlas.size,os.path.getsize(f'out/{sid}.png')//1024,'KB')
json.dump(meta,open('out/sprites.json','w'),separators=(',',':'))
# preview: idle + walk + wave on a floor-colored bg, 3x nearest
rowsimgs=[]
for sid,mt in meta.items():
    at=Image.open(f'out/{sid}.png'); strip=Image.new('RGBA',(CW*8,CH),(150,170,120,255))
    pick=[mt['anims']['idle'][0],mt['anims']['walkR'][0],mt['anims']['walkR'][3 if len(mt['anims']['walkR'])>3 else 1],mt['anims'].get('walkU',[mt['anims']['idle'][0]])[0],mt['anims']['wave'][2],mt['anims']['cheer'][1],(mt['anims'].get('type') or mt['anims']['idle'])[0],(mt['anims'].get('speak') or mt['anims']['idle'])[0]]
    for k,idx in enumerate(pick):
        c=at.crop(((idx%COLS)*CW,(idx//COLS)*CH,(idx%COLS+1)*CW,(idx//COLS+1)*CH)); strip.paste(c,(k*CW,0),c)
    rowsimgs.append(strip)
W=Image.new('RGBA',(CW*8,CH*5)); [W.paste(s,(0,i*CH)) for i,s in enumerate(rowsimgs)]
W.resize((CW*8*2,CH*5*2),Image.NEAREST).save('out/preview.png')
