"""蓝白圆角会话选择浮层。"""
import tkinter as tk
from tkinter import font
from PIL import Image, ImageDraw, ImageTk
from quota_card import KEY, INK, MUTED


class ChatPicker(tk.Toplevel):
    def __init__(self, root, chats, current_id, choose):
        super().__init__(root)
        self.title('蓝色大肥鱼 · 切换会话')
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-transparentcolor', KEY)
        self.configure(bg=KEY)
        self.chats, self.current_id, self.choose = chats, current_id, choose
        self.selected = current_id
        self.visible = []
        self.drag_origin = None
        self.canvas = tk.Canvas(self, width=430, height=440, bg=KEY, highlightthickness=0)
        self.canvas.pack()
        c = self.canvas
        self.normal_font = font.Font(self, family='Microsoft YaHei UI', size=10)
        self.small_font = font.Font(self, family='Microsoft YaHei UI', size=8)
        self.background = self.rounded_image(430, 440, '#f2f8ff', '#b7cee6', 20, True)
        c.create_image(0, 0, anchor='nw', image=self.background)
        self.header = self.rounded_image(414, 38, '#e1edfc', None, 13)
        c.create_image(8, 8, anchor='nw', image=self.header)
        c.create_oval(18, 22, 37, 32, fill='#5f83b6', outline='')
        c.create_polygon(35, 27, 43, 20, 42, 31, fill='#5f83b6', outline='')
        c.create_oval(22, 24, 24, 26, fill='#f2f8ff', outline='')
        c.create_text(50, 27, text='切换会话', anchor='w', fill=INK,
                      font=('Microsoft YaHei UI', 11, 'bold'))
        c.create_rectangle(384, 12, 418, 42, fill='#e1edfc', outline='', tags='close')
        c.create_text(401, 27, text='×', fill=MUTED, font=('Segoe UI', 16), tags='close')
        c.tag_bind('close', '<Button-1>', lambda e:self.destroy())
        self.search_background = self.rounded_image(398, 34, 'white', '#d8e5f3', 11)
        c.create_image(16, 59, anchor='nw', image=self.search_background)
        c.create_oval(29, 69, 39, 79, outline='#819bbb', width=2)
        c.create_line(38, 78, 43, 83, fill='#819bbb', width=2)
        self.query = tk.StringVar()
        self.entry = tk.Entry(c, textvariable=self.query, bd=0, highlightthickness=0,
                              bg='white', fg=INK, insertbackground=INK, font=self.normal_font)
        self.entry.place(x=51, y=65, width=344, height=23)
        self.placeholder = tk.Label(c, text='搜索会话名称', bg='white', fg=MUTED,
                                    font=('Microsoft YaHei UI', 9), anchor='w')
        self.placeholder.place(x=51, y=65, width=300, height=23)
        self.placeholder.bind('<Button-1>', lambda e:self.entry.focus_set())
        self.entry.bind('<FocusIn>', lambda e:self.placeholder.place_forget())
        self.entry.bind('<FocusOut>', lambda e:self.update_placeholder())
        self.count_item = c.create_text(20, 106, anchor='w', fill=MUTED, font=self.small_font)
        self.list = tk.Canvas(c, width=390, height=268, bg='#f2f8ff', highlightthickness=0)
        self.list.place(x=16, y=120)
        self.scroll = tk.Canvas(c, width=6, height=266, bg='#f2f8ff', highlightthickness=0)
        self.scroll.place(x=408, y=121)
        self.list.configure(yscrollcommand=self.draw_scroll, yscrollincrement=18)
        self.list.bind('<Button-1>', self.select_click)
        self.list.bind('<Double-Button-1>', self.confirm_click)
        self.list.bind('<MouseWheel>', lambda e:self.list.yview_scroll(-int(e.delta/120)*3,'units'))
        self.scroll.bind('<Button-1>', self.scroll_to)
        self.scroll.bind('<B1-Motion>', self.scroll_to)
        self.row_images = {key:self.rounded_image(386, 51, fill, border, 10)
                           for key, fill, border in [('normal','white',None),
                                                     ('selected','#e1edfc','#9bb9dc')]}
        c.create_text(20, 414, text='单击选择 · 双击切换', anchor='w', fill=MUTED, font=self.small_font)
        self.button_images = [self.rounded_image(132, 32, color, None, 12)
                              for color in ['#dce7f3','#638cbe']]
        self.button_bg = c.create_image(282, 398, anchor='nw', tags='confirm')
        self.button_text = c.create_text(348, 414, text='跟随此会话', font=('Microsoft YaHei UI',9,'bold'), tags='confirm')
        c.tag_bind('confirm', '<Button-1>', lambda e:self.confirm())
        for tag in ['close','confirm']:
            c.tag_bind(tag,'<Enter>',lambda e:c.configure(cursor='hand2'))
            c.tag_bind(tag,'<Leave>',lambda e:c.configure(cursor=''))
        c.bind('<ButtonPress-1>', self.start_drag)
        c.bind('<B1-Motion>', self.drag)
        self.bind('<Escape>', lambda e:self.destroy())
        self.bind('<Return>', lambda e:self.confirm())
        self.bind('<Up>', lambda e:self.move_selection(-1))
        self.bind('<Down>', lambda e:self.move_selection(1))
        self.query.trace_add('write', lambda *args:self.filter())
        self.filter()
        x = root.winfo_x()-440
        if x < 0: x = root.winfo_x()+root.winfo_width()+10
        x = max(0,min(root.winfo_screenwidth()-430,x))
        y = max(0,min(root.winfo_screenheight()-490,root.winfo_y()))
        self.geometry(f'430x440+{x}+{y}')
        self.after(50,self.focus_set)

    def rounded_image(self, width, height, fill, outline, radius, transparent=False):
        im=Image.new('RGBA',(width*3,height*3))
        ImageDraw.Draw(im).rounded_rectangle((3,3,(width-1)*3,(height-1)*3),
            radius=radius*3,fill=fill,outline=outline,width=3)
        im=im.resize((width,height),Image.Resampling.LANCZOS)
        rgb=Image.new('RGB',im.size,KEY if transparent else '#f2f8ff')
        mask=im.getchannel('A')
        if transparent: mask=mask.point(lambda a:255 if a>=96 else 0)
        rgb.paste(im.convert('RGB'),mask=mask)
        return ImageTk.PhotoImage(rgb,master=self)

    def clip(self, text, width, face):
        text=' '.join((text or '').split()) or '未命名会话'
        if face.measure(text)<=width: return text
        while text and face.measure(text+'…')>width: text=text[:-1]
        return text+'…'

    def update_placeholder(self):
        if not self.query.get() and self.focus_get()!=self.entry:
            self.placeholder.place(x=51,y=65,width=300,height=23)
        else:
            self.placeholder.place_forget()

    def filter(self):
        query=self.query.get().strip().casefold()
        self.visible=[item for item in self.chats if query in (item.get('name') or '').casefold()]
        if self.selected not in [item['id'] for item in self.visible]:
            self.selected=None
        self.list.yview_moveto(0)
        self.update_placeholder()
        self.draw_rows()

    def draw_rows(self):
        c=self.list
        c.delete('all')
        c.configure(scrollregion=(0,0,390,max(268,len(self.visible)*57)))
        self.canvas.itemconfigure(self.count_item,text=f'{len(self.visible)} 个会话 · 最近使用优先')
        if not self.visible:
            c.create_text(195,105,text='没有找到匹配的会话' if self.chats else '暂无可切换的会话',
                          fill=MUTED,font=self.normal_font)
        for i,item in enumerate(self.visible):
            y=i*57
            selected=item['id']==self.selected
            current=item['id']==self.current_id
            c.create_image(1,y,anchor='nw',image=self.row_images['selected' if selected else 'normal'])
            c.create_text(15,y+16,anchor='w',text=self.clip(item.get('name'),290 if current else 350,self.normal_font),
                          fill=INK,font=self.normal_font)
            folder=(item.get('cwd') or '').replace('\\','/').rstrip('/').rsplit('/',1)[-1]
            c.create_text(15,y+36,anchor='w',text=self.clip(folder or '本机会话',350,self.small_font),
                          fill=MUTED,font=self.small_font)
            if current:
                c.create_text(371,y+16,anchor='e',text='跟随中',fill='#5f83b6',font=self.small_font)
        enabled=self.selected in [item['id'] for item in self.visible]
        self.canvas.itemconfigure(self.button_bg,image=self.button_images[int(enabled)])
        self.canvas.itemconfigure(self.button_text,fill='white' if enabled else MUTED)

    def select_click(self,event):
        index=int(self.list.canvasy(event.y)//57)
        if 0<=index<len(self.visible):
            self.selected=self.visible[index]['id']
            self.draw_rows()

    def confirm_click(self,event):
        index=int(self.list.canvasy(event.y)//57)
        if 0<=index<len(self.visible):
            self.selected=self.visible[index]['id']
            self.confirm()

    def confirm(self):
        item=next((item for item in self.visible if item['id']==self.selected),None)
        if item:
            self.choose(item)
            self.destroy()

    def move_selection(self,direction):
        if not self.visible: return 'break'
        ids=[item['id'] for item in self.visible]
        index=ids.index(self.selected) if self.selected in ids else (-1 if direction>0 else len(ids))
        index=max(0,min(len(ids)-1,index+direction))
        self.selected=ids[index]
        self.draw_rows()
        top=self.list.canvasy(0)
        if index*57<top: self.list.yview_moveto(index*57/max(268,len(ids)*57))
        elif index*57+51>top+268: self.list.yview_moveto((index*57+51-268)/max(268,len(ids)*57))
        return 'break'

    def draw_scroll(self,first,last):
        first,last=float(first),float(last)
        self.scroll.delete('all')
        if last-first<.999:
            self.scroll.create_line(3,3+260*first,3,3+260*last,fill='#b3cde9',width=4,capstyle='round')

    def scroll_to(self,event):
        first,last=self.list.yview()
        self.list.yview_moveto(max(0,event.y/266-(last-first)/2))

    def start_drag(self,event):
        self.drag_origin=(event.x_root,event.y_root,self.winfo_x(),self.winfo_y()) if event.y<48 and event.x<380 else None

    def drag(self,event):
        if self.drag_origin:
            sx,sy,x,y=self.drag_origin
            x=max(0,min(self.winfo_screenwidth()-430,x+event.x_root-sx))
            y=max(0,min(self.winfo_screenheight()-440,y+event.y_root-sy))
            self.geometry(f'+{x}+{y}')
