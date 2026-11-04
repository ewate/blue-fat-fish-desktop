"""Short transitions from the exact displayed pose, built off the Tk thread."""
import numpy as np
from PIL import Image
from motion_math import pair_flow, interpolate


def make_bridge(source, target, count=10):
    size=target.size
    source=source.convert('RGBA').resize(size,Image.Resampling.LANCZOS)
    target=target.convert('RGBA')
    if np.array_equal(np.asarray(source),np.asarray(target)):
        return [target.copy()]
    a=np.asarray(source.resize((256,256),Image.Resampling.LANCZOS),dtype=np.float32)/255
    b=np.asarray(target.resize((256,256),Image.Resampling.LANCZOS),dtype=np.float32)/255
    flow=pair_flow(a,b)
    frames=[source.copy()]
    for i in range(1,count-1):
        t=i/(count-1)
        t=t*t*(3-2*t)
        frames.append(Image.fromarray(interpolate(a,b,flow,t),'RGBA').resize(size,Image.Resampling.LANCZOS))
    frames.append(target.copy())
    return frames
