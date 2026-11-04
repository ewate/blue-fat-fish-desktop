"""与桌宠卡片配套的圆角右键菜单。"""
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from quota_card import KEY, INK, MUTED


class PetMenu(tk.Toplevel):
    def __init__(self, root, entries, x, y):
        super().__init__(root)
        self.title('蓝色大肥鱼 · 菜单')
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-transparentcolor', KEY)
        self.configure(bg=KEY)
        self.home = entries
        self.entries = entries
        self.origin = (x,y)
        self.page_title = '蓝色大肥鱼'
        self.selected = -1
        self.canvas = tk.Canvas(self,width=252,bg=KEY,highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind('<Motion>',self.motion)
        self.canvas.bind('<Leave>',lambda e:self.highlight(-1))
        self.canvas.bind('<Button-1>',self.click)
        self.bind('<Escape>',lambda e:self.destroy())
        self.bind('<Up>',lambda e:self.move(-1))
        self.bind('<Down>',lambda e:self.move(1))
        self.bind('<Return>',lambda e:self.activate(self.selected))
        self.bind('<space>',lambda e:self.activate(self.selected))
        self.bind('<Left>',lambda e:self.show_home())
        self.bind('<FocusOut>',lambda e:self.after(100,self.check_focus))
        self.draw()
        self.focus_force()

    def check_focus(self):
        if self.winfo_exists():
            focused=self.focus_get()
            if focused is None or focused.winfo_toplevel()!=self:
                self.destroy()

    def draw(self):
        c=self.canvas
        c.delete('all')
        height=54+len(self.entries)*34
        c.configure(height=height)
        bg=Image.new('RGBA',(252*3,height*3))
        d=ImageDraw.Draw(bg)
        d.rounded_rectangle((3,3,251*3,(height-1)*3),radius=18*3,
                            fill='#f2f8ff',outline='#b7cee6',width=3)
        d.rounded_rectangle((8*3,8*3,244*3,39*3),radius=11*3,fill='#e1edfc')
        for i,entry in enumerate(self.entries):
            if i==self.selected:
                y=46+i*34
                d.rounded_rectangle((8*3,y*3,244*3,(y+31)*3),radius=9*3,fill='#e1edfc')
        bg=bg.resize((252,height),Image.Resampling.LANCZOS)
        rgb=Image.new('RGB',bg.size,KEY)
        rgb.paste(bg.convert('RGB'),mask=bg.getchannel('A').point(lambda a:255 if a>=96 else 0))
        self.background=ImageTk.PhotoImage(rgb,master=self)
        c.create_image(0,0,anchor='nw',image=self.background)
        c.create_text(19,24,anchor='w',text=('‹  ' if self.entries is not self.home else '')+self.page_title,
                      fill=INK,font=('Microsoft YaHei UI',10,'bold'))
        c.create_text(230,24,text='×',fill=MUTED,font=('Segoe UI',15))
        for i,entry in enumerate(self.entries):
            y=61+i*34
            c.create_text(19,y,anchor='w',text=entry['label'],fill='#7b6688' if entry.get('exit') else INK,
                          font=('Microsoft YaHei UI',9))
            if 'children' in entry:
                c.create_text(228,y,text='›',fill=MUTED,font=('Segoe UI',15))
            elif 'checked' in entry:
                enabled=entry['checked']()
                c.create_line(211,y,229,y,fill='#86a9d1' if enabled else '#d6e1ee',width=14,capstyle='round')
                x=228 if enabled else 212
                c.create_oval(x-5,y-5,x+5,y+5,fill='white',outline='')
        x,y=self.origin
        x=max(0,min(self.winfo_screenwidth()-252,x))
        y=max(0,min(self.winfo_screenheight()-height-45,y))
        self.geometry(f'252x{height}+{x}+{y}')

    def highlight(self,index):
        if self.selected!=index:
            self.selected=index
            self.canvas.configure(cursor='hand2' if index>=0 else '')
            self.draw()

    def motion(self,event):
        index=(event.y-46)//34
        self.highlight(index if 0<=index<len(self.entries) else -1)

    def click(self,event):
        if event.y<42:
            if event.x>212: self.destroy()
            elif self.entries is not self.home: self.show_home()
            return
        self.activate((event.y-46)//34)

    def activate(self,index):
        if not 0<=index<len(self.entries): return
        entry=self.entries[index]
        if 'children' in entry:
            self.entries=entry['children']
            self.page_title=entry['label']
            self.selected=-1
            self.draw()
        elif 'checked' in entry:
            entry['command']()
            self.draw()
        else:
            self.destroy()
            entry['command']()

    def show_home(self):
        self.entries=self.home
        self.page_title='蓝色大肥鱼'
        self.selected=-1
        self.draw()

    def move(self,direction):
        self.highlight((self.selected+direction)%len(self.entries))
