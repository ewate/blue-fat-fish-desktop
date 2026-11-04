"""Render a text-free 1080p demo; text is limited to the actual UI controls."""
from pathlib import Path
from functools import lru_cache
import argparse,json,math,subprocess,sys,wave,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from motion_bridge import make_bridge
W,H,FPS=1920,1080,60
S=1.5
INK='#303e66';MUTED='#7486a6';BLUE='#719fd1'
MAN=json.loads((ROOT/'assets/animations-smooth.json').read_text())
BLINK=json.loads((ROOT/'assets/blink.json').read_text())['frames']

@lru_cache(32)
def font(size,bold=False):
    path=Path('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc')
    return ImageFont.truetype(str(path),round(size*S))
def text(im,xy,label,n=24,fill=INK,bold=False,anchor=None):
    ImageDraw.Draw(im).text(tuple(round(v*S) for v in xy),label,font=font(n,bold),fill=fill,anchor=anchor,spacing=round(10*S))
def rect(im,box,fill='white',r=24,outline=None):
    ImageDraw.Draw(im).rounded_rectangle(tuple(round(v*S) for v in box),round(r*S),fill,outline,width=2)

rows=np.zeros((H,W,3),np.uint8)
for y in range(H):
    f=y/(H-1);rows[y,:,0]=int(247-14*f);rows[y,:,1]=int(251-8*f);rows[y,:,2]=255
BACKGROUND=Image.fromarray(rows)
d=ImageDraw.Draw(BACKGROUND)
d.ellipse((1400,-250,2150,480),fill='#e3effd');d.ellipse((-380,760,450,1550),fill='#e7f1ff')

@lru_cache(100)
def frame(name,index,size):
    path=BLINK[index%len(BLINK)] if name=='blink' else MAN[name]['frames'][index%len(MAN[name]['frames'])]
    return Image.open(ROOT/'assets'/path).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)

def sprite(im,name,t,x,y,size):
    index=int(t*60)%len(MAN['idle' if name=='blink' else name]['frames'])
    if name=='idle' and t>3.9 and .035<t%4<.13:name='blink'
    image=frame(name,index,round(size*S));im.paste(image,(round(x*S),round(y*S)),image)

def music(path):
    sr=44100;audio=np.zeros(sr*60,np.float32)
    notes=[60,64,67,71,69,67,64,62,60,67,72,71,67,64,62,64]
    def note(start,midi,duration,volume):
        n=min(int(sr*duration),len(audio)-int(start*sr));t=np.arange(n)/sr;f=440*2**((midi-69)/12)
        signal=(np.sin(2*np.pi*f*t)+.22*np.sin(4*np.pi*f*t))*(1-np.exp(-45*t))*np.exp(-3.1*t)*volume
        a=int(start*sr);audio[a:a+n]+=signal
    for k in range(96):
        note(k*.625,notes[k%16]+(12 if k%8 in (2,6) else 0),1.4,.08)
        if k%4==0:
            for x in (0,7,12):note(k*.625,[48,43,45,41][k//4%4]+x,2.2,.027)
    delayed=np.zeros_like(audio);delay=int(.21*sr);delayed[delay:]=audio[:-delay]*.13;audio+=delayed
    fade=np.minimum(1,np.arange(len(audio))/(sr*1.5))*np.minimum(1,(len(audio)-np.arange(len(audio)))/(sr*2))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(audio*fade,-.7,.7)*32767).astype('<i2').tobytes())

RICE_TRACK=[]
def rice_track():
    global RICE_TRACK
    if RICE_TRACK:return
    idle=Image.open(ROOT/'assets'/MAN['idle']['frames'][0]).convert('RGBA')
    poses=[Image.open(ROOT/'assets'/p).convert('RGBA') for p in MAN['rice']['frames']]
    RICE_TRACK=make_bridge(idle,poses[0],10)+poses+make_bridge(poses[-1],idle,10)
    RICE_TRACK += [Image.open(ROOT/'assets'/p).convert('RGBA') for p in MAN['idle']['frames'][:45]]

@lru_cache(64)
def rice_frame(index,size):return RICE_TRACK[index%len(RICE_TRACK)].resize((size,size),Image.Resampling.LANCZOS)

def speed_ui(im,x,y,value):
    rect(im,(x,y,x+330,y+124),'#f2f8ff',24,'#b7cee6')
    text(im,(x+20,y+18),'动画速度',23,bold=True);text(im,(x+290,y+18),f'{value:.2f}×',23,fill='#486da3',bold=True,anchor='ra')
    d=ImageDraw.Draw(im);a,b=(x+25)*S,(x+305)*S;yy=(y+72)*S
    d.line((a,yy,b,yy),fill='#d8e5f3',width=round(6*S))
    k=a+(value-.5)/1.5*(b-a);d.line((a,yy,k,yy),fill=BLUE,width=round(6*S));d.ellipse((k-9*S,yy-9*S,k+9*S,yy+9*S),fill='#638cbe')
    text(im,(x+25,y+96),'0.5×',15,fill=MUTED);text(im,(x+165,y+96),'恢复默认',15,fill='#486da3',anchor='ma');text(im,(x+305,y+96),'2.0×',15,fill=MUTED,anchor='ra')

def message_ui(im,x,y):
    rect(im,(x,y,x+430,y+340),'#f2f8ff',24,'#b7cee6');rect(im,(x+10,y+10,x+420,y+58),'#e1edfc',15)
    text(im,(x+24,y+21),'蓝色大肥鱼',23,bold=True);text(im,(x+395,y+21),'×',23,fill=MUTED)
    text(im,(x+23,y+78),'● 已完成',20,fill='#486da3')
    rect(im,(x+17,y+114,x+413,y+273),'white',18)
    text(im,(x+33,y+133),'任务已完成。\n检查通过，可以继续下一步。',22)
    for j,label in enumerate(['切换会话','额度卡片','复制回复']):
        rect(im,(x+20+j*136,y+292,x+139+j*136,y+324),'#e1edfc',11)
        text(im,(x+31+j*136,y+298),label,17,fill='#486da3')

def quota_ui(im,x,y):
    rect(im,(x,y,x+280,y+148),'#f2f8ff',24,'#b7cee6');rect(im,(x+10,y+10,x+270,y+54),'#e1edfc',15)
    text(im,(x+24,y+21),'剩余额度',22,bold=True);text(im,(x+247,y+21),'×',22,fill=MUTED)
    text(im,(x+24,y+86),'7 天',22);text(im,(x+254,y+79),'68%',32,fill='#486da3',bold=True,anchor='ra')

def menu_ui(im,x,y,on):
    rect(im,(x,y,x+274,y+346),'#f2f8ff',24,'#b7cee6');rect(im,(x+10,y+10,x+264,y+54),'#e1edfc',15)
    text(im,(x+24,y+21),'蓝色大肥鱼',23,bold=True)
    for j,label in enumerate(['显示状态条','显示消息卡片','显示额度卡片','动画速度 · 1×','切换跟随会话']):
        yy=y+84+j*48;text(im,(x+22,yy),label,18)
        if j<3:
            rect(im,(x+210,yy+2,x+250,yy+23),BLUE if on else '#d6e1ee',11)
            cx=x+(238 if on else 222);ImageDraw.Draw(im).ellipse(((cx-7)*S,(yy+5)*S,(cx+7)*S,(yy+20)*S),fill='white')

BOUNDS=[0,8,16,24,32,40,48,56,60]
def scene(i,t):
    im=BACKGROUND.copy()
    if i in (0,7):sprite(im,'idle' if i==0 else 'wave',t,375,70,530)
    elif i==1:
        rice_track();p=rice_frame(int(t*60)%len(RICE_TRACK),round(530*S));im.paste(p,(round(375*S),round(70*S)),p)
    elif i==2:sprite(im,'wave',t,375,70,530)
    elif i==3:sprite(im,'happy',t,365,66,550)
    elif i==4:
        rect(im,(92,150,610,610),'#ffffff',32);rect(im,(670,150,1188,610),'#ffffff',32)
        sprite(im,'wink',t,128,156,444);sprite(im,'smile',t,706,156,444)
    elif i==5:
        speed=1.25-.75*math.cos(2*math.pi*t/8)
        phase=1.25*t-.75*8/(2*math.pi)*math.sin(2*math.pi*t/8)
        sprite(im,'happy',phase,375,25,500);speed_ui(im,475,535,speed)
    elif i==6:
        on=t<4.2
        menu_ui(im,62,213,on);sprite(im,'idle',t,390,207,350)
        if on:message_ui(im,754,110);quota_ui(im,805,482)
    return im

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',default=shutil.which('ffmpeg'));parser.add_argument('--output',default=str(ROOT/'artifacts/video1080'));args=parser.parse_args()
    if not args.ffmpeg:parser.error('Pass --ffmpeg with an existing FFmpeg executable')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    audio=out/'music.wav';music(audio);rice_track()
    scene(0,1.5).save(out/'cover.jpg',quality=96)
    contact=Image.new('RGB',(960,720))
    for i in range(8):contact.paste(scene(i,2).resize((480,270)),((i%2)*480,(i//2)*180))
    # One separate full-size frame for each scene, for visual inspection.
    for i in range(8):scene(i,2).save(out/f'preview-{i}.jpg',quality=94)
    cmd=[args.ffmpeg,'-hide_banner','-loglevel','warning','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','60','-i','pipe:0','-i',str(audio),'-t','60','-c:v','libx264','-crf','18','-preset','fast','-threads','4','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out/'blue-fat-fish-demo-1080p.mp4')]
    with (out/'encode.log').open('w') as log:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
        try:
            for n in range(3600):
                t=n/60;i=next(i for i in range(8) if BOUNDS[i]<=t<BOUNDS[i+1]);im=scene(i,t-BOUNDS[i])
                if i<7 and t>BOUNDS[i+1]-.3:
                    a=(t-BOUNDS[i+1]+.3)/.3;a=a*a*(3-2*a);im=Image.blend(im,scene(i+1,0),a)
                p.stdin.write(im.tobytes())
                if n%300==0:print(f'Rendering {n//60}/60 seconds',flush=True)
        finally:p.stdin.close()
        if p.wait():raise RuntimeError('FFmpeg encoding failed')
    print(out/'blue-fat-fish-demo-1080p.mp4',flush=True)


if __name__=='__main__':main()
