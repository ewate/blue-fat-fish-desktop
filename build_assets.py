"""Extract generated 4x2 sheets, align feet, and write transparent playback frames."""
import json
from pathlib import Path
import statistics
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
NAMES = ['idle','rice','wink','smile','wave','happy']


def build(name):
    replacement = {'rice':'rice-v2.png','wave':'wave-v4.png','happy':'happy-v4.png'}.get(name)
    upgraded = replacement is not None and (ROOT/'sources'/replacement).exists()
    rows = 4 if upgraded else 2
    sheet = Image.open(ROOT/'sources'/(replacement if upgraded else f'{name}.png')).convert('RGBA')
    mask=sheet.getchannel('A').point(lambda a:255 if a>=96 else 0)
    boundaries=[]
    for row in range(rows):
        band=mask.crop((0,row*sheet.height//rows,sheet.width,(row+1)*sheet.height//rows))
        splits=[0]
        for col in range(1,4):
            expected=col*sheet.width//4
            runs=[]
            start=None
            for x in range(expected-60,expected+61):
                empty=band.crop((x,0,x+1,band.height)).getbbox() is None
                if empty and start is None:
                    start=x
                if not empty and start is not None:
                    runs.append((start,x));start=None
            if start is not None:
                runs.append((start,expected+61))
            if not runs:
                raise ValueError(f'{name}: no clear gap between poses {row},{col}')
            left,right=min(runs,key=lambda r:abs((r[0]+r[1])/2-expected))
            splits.append((left+right)//2)
        splits.append(sheet.width)
        boundaries.append(splits)
    cells=[]
    anchors=[]
    heights=[]
    for i in range(rows*4):
        col,row=i%4,i//4
        cell=sheet.crop((boundaries[row][col],round(row*sheet.height/rows),
                         boundaries[row][col+1],round((row+1)*sheet.height/rows)))
        # Remove low-alpha generation haze while retaining the original foreground colors.
        alpha=cell.getchannel('A').point(lambda a:255 if a>=96 else 0)
        box=alpha.getbbox()
        if not box:
            raise ValueError(f'{name} frame {i}: blank')
        x0,y0,x1,y1=box
        if x0<2 or y0<2 or x1>cell.width-2 or y1>cell.height-2:
            raise ValueError(f'{name} frame {i}: touches cell boundary {box}')
        cell.putalpha(alpha)
        clean=Image.new('RGBA',cell.size)
        clean.paste(cell,mask=alpha)
        feet=[]
        for y in range(y1-10,y1):
            feet.extend(x for x in range(x0,x1) if alpha.getpixel((x,y))>128)
        anchor=statistics.mean(feet)
        anchors.append((anchor,y1))
        cells.append((clean,box))
        heights.append(y1-y0)
    max_half=max(max(anchor[0]-box[0],box[2]-anchor[0]) for (_,box),anchor in zip(cells,anchors))
    scale=min(230/statistics.median(heights),122/max_half,238/max(heights))
    folder=ROOT/'assets'/name
    folder.mkdir(exist_ok=True)
    frames=[]
    paths=[]
    for i,((cell,box),(ax,ay)) in enumerate(zip(cells,anchors)):
        crop=cell.crop(box)
        crop=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.LANCZOS)
        frame=Image.new('RGBA',(256,256))
        x=round(128-(ax-box[0])*scale)
        y=round(244-(ay-box[1])*scale)
        frame.alpha_composite(crop,(x,y))
        frame.save(folder/f'{i:02}.png')
        frames.append(frame)
        paths.append(f'{name}/{i:02}.png')
    duration=220 if name=='idle' else 160
    # GIF is for preview only; the app uses original RGBA PNGs.
    previews=[]
    for im in frames:
        bg=Image.new('RGBA',im.size,'#f6fbff')
        bg.alpha_composite(im)
        previews.append(bg.convert('RGB'))
    (ROOT/'previews').mkdir(exist_ok=True)
    previews[0].save(ROOT/'previews'/f'{name}.gif',save_all=True,append_images=previews[1:],
                     duration=duration,loop=0,disposal=2)
    strip=Image.new('RGB',(256*4,288*rows),'#f6fbff')
    draw=ImageDraw.Draw(strip)
    for i,im in enumerate(previews):
        strip.paste(im,(i%4*256,i//4*288))
        draw.text((i%4*256+12,i//4*288+260),f'{name} {i+1}/{len(frames)}',fill='#223451')
    strip.save(ROOT/'previews'/f'{name}-frames.png')
    return {'frames':paths,'duration_ms':duration,'source_scale':scale,'source_heights':heights}


if __name__=='__main__':
    manifest={}
    for name in NAMES:
        if (ROOT/'sources'/f'{name}.png').exists():
            manifest[name]=build(name)
    (ROOT/'assets/animations.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({name:len(item['frames']) for name,item in manifest.items()}))
