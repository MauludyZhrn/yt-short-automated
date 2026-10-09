import numpy as np, sys, json
from PIL import Image
from scipy import ndimage as ndi
import os
U=os.environ.get('SPRITE_SRC','sheets/')
if not U.endswith('/'): U+='/'
TONES={'MorbMyth':(109,133),'KaelQuill':(89,134),'VoxArden':(164,191),'MikaPixel':(205,242),'RivenCut':(196,255)}
def bgmask(a, tones, tol=9, chroma=7, solid=0, halo=0, halo_tol=24):
    mx=a.max(2); mn=a.min(2); lum=a.mean(2)
    lowc=(mx-mn)<=chroma
    lo,hi=min(tones)-tol,max(tones)+tol                      # rentang kontinu: termasuk piksel transisi antar-kotak
    cand=lowc&(lum>=lo)&(lum<=hi)
    core=ndi.binary_opening(cand,structure=np.ones((5,5),bool))      # putus jalur tipis (celana abu-abu dll)
    lab,n=ndi.label(core)
    border=np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])); border=border[border>0]
    bg=np.isin(lab,border)
    grow=ndi.binary_dilation(bg,iterations=3)&cand
    bg=grow|bg
    if solid:                                              # buang celah bg yang tipis (corak abu-abu di dalam celana)
        sol=ndi.binary_opening(bg,structure=np.ones((solid,solid),bool))
        bg=ndi.binary_dilation(sol,iterations=3)&bg
    if halo:                                                # halo JPEG di luar garis tepi: buang <= 'halo' px dari bg, hanya lewat piksel abu-abu
        c2=lowc&(lum>=lo-halo_tol)&(lum<=hi+halo_tol)
        for _ in range(halo): bg=ndi.binary_dilation(bg)&c2|bg
    return bg, cand
SOLID={'MorbMyth':13}
HALO={'MorbMyth':9}
TOL={'MorbMyth':4,'KaelQuill':26,'VoxArden':14,'MikaPixel':14,'RivenCut':14}
def process(name):
    a=np.asarray(Image.open(U+name+'.jpg').convert('RGB')).astype(int)
    bg,cand=bgmask(a,TONES[name],TOL[name],7,SOLID.get(name,0),HALO.get(name,0))
    fg=~bg
    # enclosed leftovers that look exactly like checker and small -> bg
    lab,n=ndi.label(cand&~bg)
    if n and name not in SOLID:
        sizes=ndi.sum(np.ones_like(lab),lab,range(1,n+1))
        for i,s in enumerate(sizes,1):
            if s<1200: fg[lab==i]=False
    fg=ndi.binary_opening(fg,iterations=1)
    fg=ndi.binary_closing(fg,iterations=1)
    # remove specks
    lab,n=ndi.label(fg); sizes=ndi.sum(fg,lab,range(1,n+1))
    keep=np.zeros(n+1,bool); keep[1:]=sizes>=250; fg=keep[lab]
    return a,fg
if __name__=='__main__':
    for n in TONES:
        a,fg=process(n)
        rgba=np.dstack([a.astype(np.uint8),(fg*255).astype(np.uint8)])
        Image.fromarray(rgba).save(f'{n}_cut.png')
        # preview on magenta to reveal leftovers
        pv=np.where(fg[...,None],a,np.array([255,0,255])).astype(np.uint8)
        Image.fromarray(pv).resize((1376,768),Image.LANCZOS).save(f'{n}_prev.png')
        lab,k=ndi.label(fg); print(n,'components',k)
