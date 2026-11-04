"""Create original procedural whale samples for the MIT source release."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw


def draw_frame(name,n,closed=False):
    im=Image.new('RGBA',(512,512))
    d=ImageDraw.Draw(im)
    p=2*math.pi*n/120
    x=6*math.sin(p);y=4*math.sin(p*2)
    if name=='happy':x*=2;y*=2
    d.polygon([(338+x,252+y),(417+12*math.sin(p),210+y),(408,275+y),(425,304+y)],fill='#5077b1')
    d.ellipse((75+x,155+y,363+x,362+y),fill='#719fd2',outline='#3e6095',width=5)
    d.ellipse((120+x,267+y,318+x,350+y),fill='#dceeff')
    d.ellipse((219+x,286+y,277+x,326+y),fill='#527bb2')
    if name=='wave':
        hand=83+24*math.sin(p*3)
        d.line((112+x,258+y,hand,95),fill='#5077b1',width=28)
        d.ellipse((hand-19,65,hand+19,102),fill='#719fd2')
    eye_y=230+y
    if closed or name in ('smile','happy'):
        d.arc((133+x,eye_y-8,162+x,eye_y+6),0,180,fill='#2c456e',width=5)
    else:d.ellipse((145+x,eye_y-8,158+x,eye_y+9),fill='#2c456e')
    d.arc((175+x,238+y,213+x,263+y),0,180,fill='#2c456e',width=4)
    d.ellipse((121+x,249+y,147+x,260+y),fill='#f1bed0')
    if name=='wink':d.line((145+x,eye_y,159+x,eye_y+4),fill='#2c456e',width=5)
    if name=='rice':
        d.ellipse((161,304,266,363),fill='#f4f8ff',outline='#527bb2',width=4)
        d.ellipse((162,294,265,323),fill='white',outline='#527bb2',width=3)
        d.line((119,279,213,306-38*(1+math.sin(p))/2),fill='#b58b61',width=4)
        d.line((119,287,215,311-38*(1+math.sin(p))/2),fill='#b58b61',width=4)
    return im.resize((256,256),Image.Resampling.LANCZOS)


def main(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    manifest={}
    for name in ['idle','rice','wink','smile','wave','happy']:
        folder=root/'assets'/name;folder.mkdir(parents=True,exist_ok=True)
        paths=[]
        for n in range(120):
            path=folder/f'{n:03}.png';draw_frame(name,n).save(path)
            paths.append(path.relative_to(root/'assets').as_posix())
        manifest[name]={'frames':paths,'fps':60,'duration_ms':1000/60,'repeats':1}
    (root/'assets/animations-smooth.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    paths=[]
    for n in range(120):
        folder=root/'assets/idle_closed';folder.mkdir(exist_ok=True)
        path=folder/f'{n:03}.png';draw_frame('idle',n,True).save(path)
        paths.append(path.relative_to(root/'assets').as_posix())
    (root/'assets/blink.json').write_text(json.dumps({'frames':paths},indent=2),encoding='utf-8')


if __name__=='__main__':main()
