"""蓝白圆角动画速度滑块。"""
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from quota_card import KEY, INK, MUTED


class SpeedSlider(tk.Toplevel):
    def __init__(self, root, value, change, save):
        super().__init__(root)
        self.title('蓝色大肥鱼 · 动画速度')
        self.overrideredirect(True)
        self.attributes('-topmost',True)
        self.attributes('-transparentcolor',KEY)
        self.configure(bg=KEY)
        self.value=value
        self.change=change
        self.save=save
        self.dragging=False
        self.canvas=tk.Canvas(self,width=254,height=110,bg=KEY,highlightthickness=0)
        self.canvas.pack()
        bg=Image.new('RGBA',(762,330))
        ImageDraw.Draw(bg).rounded_rectangle((3,3,759,327),radius=54,fill='#f2f8ff',outline='#b7cee6',width=3)
        bg=bg.resize((254,110),Image.Resampling.LANCZOS)
        rgb=Image.new('RGB',bg.size,KEY)
        rgb.paste(bg.convert('RGB'),mask=bg.getchannel('A').point(lambda a:255 if a>=96 else 0))
        self.background=ImageTk.PhotoImage(rgb,master=self)
        self.canvas.bind('<ButtonPress-1>',self.press)
        self.canvas.bind('<B1-Motion>',self.move)
        self.canvas.bind('<ButtonRelease-1>',self.release)
        self.bind('<Escape>',lambda e:self.dismiss())
        self.bind('<Left>',lambda e:self.set_value(self.value-.05,True))
        self.bind('<Right>',lambda e:self.set_value(self.value+.05,True))
        self.bind('<Home>',lambda e:self.set_value(1,True))
        self.bind('<FocusOut>',lambda e:self.after(80,self.check_focus))
        self.draw()
        x=max(0,min(root.winfo_screenwidth()-254,root.winfo_x()+(root.winfo_width()-254)//2))
        y=root.winfo_y()+root.winfo_height()+8
        if y+110>root.winfo_screenheight()-45:
            y=max(0,root.winfo_y()-118)
        self.geometry(f'254x110+{x}+{y}')
        self.focus_force()

    def draw(self):
        c=self.canvas;c.delete('all')
        c.create_image(0,0,anchor='nw',image=self.background)
        c.create_text(17,23,anchor='w',text='动画速度',fill=INK,font=('Microsoft YaHei UI',10,'bold'))
        c.create_text(209,23,anchor='e',text=f'{self.value:.2f}×',fill='#486da3',font=('Segoe UI',11,'bold'))
        c.create_text(233,23,text='×',fill=MUTED,font=('Segoe UI',15))
        x=24+(self.value-.5)/1.5*206
        c.create_line(24,61,230,61,fill='#d8e5f3',width=5,capstyle='round')
        c.create_line(24,61,x,61,fill='#719fd1',width=5,capstyle='round')
        c.create_oval(x-7,54,x+7,68,fill='#638cbe',outline='white',width=2)
        c.create_text(24,88,anchor='w',text='0.5×',fill=MUTED,font=('Segoe UI',9))
        c.create_text(230,88,anchor='e',text='2.0×',fill=MUTED,font=('Segoe UI',9))
        c.create_text(127,88,text='恢复默认',fill='#486da3',font=('Microsoft YaHei UI',9))

    def set_value(self,value,persist=False):
        self.value=max(.5,min(2,round(value*20)/20))
        self.change(self.value)
        self.draw()
        if persist:self.save()

    def press(self,event):
        if event.y<40 and event.x>217:self.dismiss();return
        if event.y>76 and 85<event.x<170:self.set_value(1,True);return
        if 40<=event.y<=76:
            self.dragging=True
            self.move(event)

    def move(self,event):
        if self.dragging:self.set_value(.5+(event.x-24)/206*1.5)

    def release(self,event=None):
        if self.dragging:self.dragging=False;self.save()

    def check_focus(self):
        if self.winfo_exists():
            focused=self.focus_get()
            if focused is None or focused.winfo_toplevel()!=self:self.dismiss()

    def dismiss(self):
        self.save()
        self.destroy()
