"""Motion interpolation shared by runtime transitions."""
import math
import cv2
import numpy as np
grid_x,grid_y=np.meshgrid(np.arange(256,dtype=np.float32),np.arange(256,dtype=np.float32))

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


