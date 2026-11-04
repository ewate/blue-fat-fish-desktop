"""Offline motion-aware interpolation; runtime only needs Pillow and Tk."""
import json
import math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from idle_motion import build_idle, maps

ROOT=Path(__file__).resolve().parent
grid_x,grid_y=np.meshgrid(np.arange(256,dtype=np.float32),np.arange(256,dtype=np.float32))
TIMING={
    'idle':[.50,.32,.14,.12,.50,.45,.45,.52],
    'rice':[.10,.10,.12,.16,.17,.16,.16,.14,.13,.20,.48,.65],
    'wink':[.16,.16,.18,.22,.20,.16,.16,.16],
    'smile':[.17,.20,.24,.30,.26,.20,.18,.17],
    'wave':[.12,.12,.12,.13,.11,.13,.11,.13,.11,.13,.11,.13,.13,.14,.13,.14],
    'happy':[.10,.11,.11,.13,.12,.10,.11,.13,.13,.11,.10,.11,.12,.11,.10,.12],
}


def pair_flow(a,b):
    def gray(im):
        white=(im[:,:,:3]*im[:,:,3:]+1-im[:,:,3:])*255
        return cv2.cvtColor(white.astype(np.uint8),cv2.COLOR_RGB2GRAY)
    ga,gb=gray(a),gray(b)
    engine=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    engine.setVariationalRefinementIterations(5)
    return engine.calc(ga,gb,None),engine.calc(gb,ga,None)


def warp(im,flow,amount):
    # Invert the intermediate motion field so every part moves at the same time.
    amount=np.float32(amount)
    mx,my=grid_x.copy(),grid_y.copy()
    for _ in range(4):
        sampled=cv2.remap(flow,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        mx=grid_x-amount*sampled[:,:,0]
        my=grid_y-amount*sampled[:,:,1]
    return cv2.remap(im,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)


def interpolate(a,b,flow,t):
    t=float(t)
    pa,pb=a.copy(),b.copy()
    pa[:,:,:3]*=pa[:,:,3:]
    pb[:,:,:3]*=pb[:,:,3:]
    wa=warp(pa,flow[0],t)
    wb=warp(pb,flow[1],1-t)
    # Blend aligned content only. Changed expressions and occlusions use one
    # warped pose; never paste an unwarped face over a moving body.
    ca=wa[:,:,:3]+1-wa[:,:,3:]
    cb=wb[:,:,:3]+1-wb[:,:,3:]
    difference=np.max(np.abs(ca-cb),axis=2)
    unmatched=cv2.dilate((difference>.13).astype(np.float32),np.ones((5,5),np.uint8))
    unmatched=cv2.GaussianBlur(unmatched,(5,5),.8)[:,:,None]
    weight=t*(1-unmatched)+(0 if t<.5 else 1)*unmatched
    out=wa*(1-weight)+wb*weight
    out[:,:,:3]/=np.maximum(out[:,:,3:],1e-6)
    out=np.clip(out*255,0,255).astype(np.uint8)
    out[out[:,:,3]<3]=0
    return out


def build():
    manifest=json.loads((ROOT/'assets/animations.json').read_text(encoding='utf-8'))
    result={}
    for name,info in manifest.items():
        if name=='idle':
            result[name]=build_idle()
            print('idle',len(result[name]['frames']),flush=True)
            continue
        originals=[np.asarray(Image.open(ROOT/'assets'/p).convert('RGBA'),dtype=np.float32)/255 for p in info['frames']]
        if name=='rice':originals=originals[:12]
        durations=TIMING[name]
        assert len(durations)==len(originals),name
        boundaries=np.cumsum([0]+durations)
        total=boundaries[-1]
        count=round(total*60)
        flows=[pair_flow(a,originals[min(i+1,len(originals)-1) if name=='rice' else (i+1)%len(originals)]) for i,a in enumerate(originals)]
        folder=ROOT/'assets'/f'{name}_60fps'
        folder.mkdir(exist_ok=True)
        paths,previews=[],[]
        for n in range(count):
            when=n/count*total
            i=min(len(originals)-1,np.searchsorted(boundaries,when,side='right')-1)
            t=(when-boundaries[i])/durations[i]
            next_i=min(i+1,len(originals)-1) if name=='rice' else (i+1)%len(originals)
            out=interpolate(originals[i],originals[next_i],flows[i],t)
            # Subtle continuous follow-through, anchored at the feet.
            phase=2*math.pi*n/count
            transform=cv2.getRotationMatrix2D((128,244),.30*math.sin(phase),1)
            transform[1,2]+=.45*math.sin(phase*2)
            out=cv2.warpAffine(out,transform,(256,256),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            mx,my=maps(phase,head=False,tail_amount=4)
            out=cv2.remap(out,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            frame=Image.fromarray(out,'RGBA')
            path=folder/f'{n:03}.png'
            frame.save(path)
            paths.append(path.relative_to(ROOT/'assets').as_posix())
            bg=Image.new('RGBA',(256,256),'#f6fbff')
            bg.alpha_composite(frame)
            if n%2==0:previews.append(bg.convert('RGB'))
        previews[0].save(ROOT/'previews'/f'{name}-smooth.gif',save_all=True,append_images=previews[1:],duration=33,loop=0,disposal=2)
        result[name]={'frames':paths,'duration_ms':1000/60,'fps':60,'keyframes':len(originals),
                      'repeats':1,'satisfaction_seconds':1.13 if name=='rice' else 0,
                      'interpolation':'aligned_bidirectional_with_occlusion_selection','cycle_seconds':count/60}
        print(name,count,flush=True)
    (ROOT/'assets/animations-smooth.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':
    build()
