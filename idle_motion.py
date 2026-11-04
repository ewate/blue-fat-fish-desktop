"""Continuous idle motion; the blink texture follows the exact same warp."""
import json
import math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parent
X,Y=np.meshgrid(np.arange(256,dtype=np.float32),np.arange(256,dtype=np.float32))


def closed_texture(base):
    source=Image.open(ROOT/'sources/idle-blink-v4.png').convert('RGBA')
    box=source.getchannel('A').point(lambda a:255 if a>=96 else 0).getbbox()
    bbox=base.getchannel('A').point(lambda a:255 if a>=96 else 0).getbbox()
    crop=source.crop(box)
    scale=(bbox[3]-bbox[1])/crop.height
    crop=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.LANCZOS)
    aligned=Image.new('RGBA',(256,256))
    aligned.alpha_composite(crop,(round((bbox[0]+bbox[2]-crop.width)/2),bbox[1]))
    def gray(im):
        a=np.asarray(im,dtype=np.float32)/255
        return cv2.cvtColor(((a[:,:,:3]*a[:,:,3:]+1-a[:,:,3:])*255).astype(np.uint8),cv2.COLOR_RGB2GRAY)
    detector=cv2.ORB_create(nfeatures=1200,edgeThreshold=8,patchSize=15)
    ka,da=detector.detectAndCompute(gray(aligned),None)
    kb,db=detector.detectAndCompute(gray(base),None)
    matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2)
    good=[m for m,n in matches if m.distance<.7*n.distance]
    if len(good)>8:
        a=np.float32([ka[m.queryIdx].pt for m in good])
        b=np.float32([kb[m.trainIdx].pt for m in good])
        matrix,_=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=2)
        if matrix is not None and .9<np.linalg.norm(matrix[:,0])<1.1:
            aligned=Image.fromarray(cv2.warpAffine(np.asarray(aligned),matrix,(256,256)),'RGBA')
    # Register the closed eyelids in neutral pose BEFORE applying head motion.
    # Nothing is pasted onto an already-moving face.
    mask=np.zeros((256,256),np.float32)
    for cx,cy,rx,ry in [(108,119,17,15),(144,118,18,16)]:
        radius=((X-cx)/rx)**2+((Y-cy)/ry)**2
        mask=np.maximum(mask,np.clip((1.12-radius)/.2,0,1))
    a=np.asarray(base,dtype=np.float32);b=np.asarray(aligned,dtype=np.float32)
    out=(a*(1-mask[:,:,None])+b*mask[:,:,None]).clip(0,255).astype(np.uint8)
    result=Image.fromarray(out,'RGBA')
    result.save(ROOT/'previews/idle-closed-registered.png')
    return result


def maps(phase,head=True,tail_amount=8):
    mx,my=X.copy(),Y.copy()
    if head:
        weight=np.clip((170-Y)/36,0,1)
        weight=weight*weight*(3-2*weight)
        angle=math.radians(2.5)*math.sin(phase)
        rx=math.cos(angle)*(X-128)+math.sin(angle)*(Y-155)+128
        ry=-math.sin(angle)*(X-128)+math.cos(angle)*(Y-155)+155
        mx+=(rx-X)*weight
        my+=(ry-Y)*weight
        body=np.clip((242-Y)/90,0,1)
        mx-=.65*math.sin(phase)*body
        my-=.4*math.sin(phase*2)*body
    tail=np.exp(-(((X-218)/37)**4+((Y-210)/30)**4))*np.clip((X-172)/26,0,1)
    mx-=tail_amount*math.sin(phase+.5)*tail
    my-=1.8*math.sin(phase*2+.8)*tail
    return mx.astype(np.float32),my.astype(np.float32)


def build_idle():
    base=Image.open(ROOT/'assets/idle/00.png').convert('RGBA')
    closed=closed_texture(base)
    paths={'open':[],'closed':[]}
    preview=[]
    for kind in paths:(ROOT/'assets'/f'idle_{kind}_60fps').mkdir(exist_ok=True)
    for n in range(144):
        mx,my=maps(2*math.pi*n/144)
        for kind,im in [('open',base),('closed',closed)]:
            # Premultiplication avoids dark borders on transparent pixels.
            a=np.asarray(im,dtype=np.float32)/255;a[:,:,:3]*=a[:,:,3:]
            out=cv2.remap(a,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            out[:,:,:3]/=np.maximum(out[:,:,3:],1e-6)
            frame=Image.fromarray(np.clip(out*255,0,255).astype(np.uint8),'RGBA')
            path=ROOT/'assets'/f'idle_{kind}_60fps'/f'{n:03}.png';frame.save(path)
            paths[kind].append(path.relative_to(ROOT/'assets').as_posix())
            if kind=='open' and n%2==0:
                bg=Image.new('RGBA',(256,256),'#f6fbff');bg.alpha_composite(frame);preview.append(bg.convert('RGB'))
    preview[0].save(ROOT/'previews/idle-smooth.gif',save_all=True,append_images=preview[1:],duration=33,loop=0,disposal=2)
    (ROOT/'assets/blink.json').write_text(json.dumps({'frames':paths['closed'],'interval_seconds':4,'period_frames':144},indent=2),encoding='utf-8')
    return {'frames':paths['open'],'duration_ms':1000/60,'fps':60,'keyframes':1,'repeats':1,'cycle_seconds':2.4,'interpolation':'continuous_sinusoidal_head_and_lateral_tail'}
