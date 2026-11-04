"""蓝白配色的独立额度卡片。"""
import datetime as dt
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

KEY = '#ff00fe'
INK = '#303e66'
MUTED = '#7486a6'


class QuotaCard(tk.Toplevel):
    def __init__(self, root, close, refresh, menu):
        super().__init__(root)
        self.title('蓝色大肥鱼 · 剩余额度')
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-transparentcolor', KEY)
        self.configure(bg=KEY)
        self.withdraw()
        self.card_width = 236
        self.card_height = 126
        self.rows = []
        self.updated = None
        self.failed = False
        self.canvas = tk.Canvas(self, width=self.card_width, height=self.card_height,
                                bg=KEY, highlightthickness=0)
        self.canvas.pack()
        self.canvas.tag_bind('close', '<Button-1>', lambda e: close())
        self.canvas.tag_bind('refresh', '<Button-1>', lambda e: refresh())
        self.canvas.bind('<Button-3>', menu)
        self.draw()

    def update_limits(self, rows=None, updated=None, failed=False):
        if rows is not None:
            self.rows = rows
        if updated is not None:
            self.updated = updated
        self.failed = failed
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete('all')
        self.card_height = 78 + max(1, len(self.rows))*60
        c.configure(height=self.card_height)
        # Supersampling keeps the round border smooth against the desktop.
        scale = 3
        bg = Image.new('RGBA', (self.card_width*scale, self.card_height*scale))
        d = ImageDraw.Draw(bg)
        d.rounded_rectangle((3, 3, (self.card_width-1)*scale, (self.card_height-1)*scale),
                            radius=19*scale, fill='#f2f8ff', outline='#b7cee6', width=scale)
        d.rounded_rectangle((8*scale, 8*scale, (self.card_width-8)*scale, 37*scale),
                            radius=12*scale, fill='#e1edfc')
        bg = bg.resize((self.card_width, self.card_height), Image.Resampling.LANCZOS)
        rgb = Image.new('RGB', bg.size, KEY)
        rgb.paste(bg.convert('RGB'), mask=bg.getchannel('A').point(lambda a:255 if a>=96 else 0))
        self.background = ImageTk.PhotoImage(rgb, master=self)
        c.create_image(0, 0, image=self.background, anchor='nw')
        # A small whale motif matches the pet's blue tail.
        c.create_oval(16, 19, 35, 29, fill='#5f83b6', outline='')
        c.create_polygon(33, 24, 41, 17, 40, 28, fill='#5f83b6', outline='')
        c.create_oval(20, 21, 22, 23, fill='#f2f8ff', outline='')
        c.create_text(48, 23, text='剩余额度', anchor='w', fill=INK,
                      font=('Microsoft YaHei UI', 10, 'bold'))
        c.create_rectangle(201, 10, 227, 36, fill='#e1edfc', outline='', tags='close')
        c.create_text(214, 23, text='×', fill=MUTED, font=('Segoe UI', 15), tags='close')
        if not self.rows:
            c.create_text(18, 66, text='暂时无法读取' if self.failed else '正在读取…',
                          anchor='w', fill=MUTED, font=('Microsoft YaHei UI', 9))
        for i, row in enumerate(self.rows):
            y = 53+i*60
            label = row['label']
            if len(label) > 17:
                label = label[:16]+'…'
            value = max(0, min(100, row['remaining']))
            c.create_text(18, y, text=label, anchor='w', fill=INK,
                          font=('Microsoft YaHei UI', 9))
            c.create_text(217, y, text=f'{value:g}%', anchor='e', fill='#486da3',
                          font=('Segoe UI', 12, 'bold'))
            c.create_line(22, y+19, 214, y+19, fill='#dce8f5', width=7, capstyle='round')
            if value > 0:
                c.create_line(22, y+19, 22+192*value/100, y+19,
                              fill='#719fd1', width=7, capstyle='round')
            reset = dt.datetime.fromtimestamp(row['reset']).strftime('%m-%d %H:%M') if row.get('reset') else None
            c.create_text(18, y+36, text=f'{reset} 重置' if reset else '重置时间暂不可用',
                          anchor='w', fill=MUTED, font=('Microsoft YaHei UI', 8))
        stamp = dt.datetime.fromtimestamp(self.updated).strftime('%H:%M:%S') if self.updated else ''
        caption = ('更新失败 · '+stamp) if self.failed else (stamp+' · 自动刷新' if stamp else '每 30 秒自动刷新')
        c.create_text(18, self.card_height-18, text=caption, anchor='w', fill=MUTED,
                      font=('Microsoft YaHei UI', 8))
        c.create_rectangle(190, self.card_height-30, 225, self.card_height-6,
                           fill='#f2f8ff', outline='', tags='refresh')
        c.create_text(216, self.card_height-18, text='刷新', anchor='e', fill='#486da3',
                      font=('Microsoft YaHei UI', 8), tags='refresh')
