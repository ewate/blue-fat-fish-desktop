"""与额度卡片配套的消息浮层。"""
import tkinter as tk
from tkinter import font
from PIL import Image, ImageDraw, ImageTk
from quota_card import KEY, INK, MUTED


class MessageCard(tk.Toplevel):
    def __init__(self, root, close, choose_chat, toggle_quota, copy_reply, menu):
        super().__init__(root)
        self.title('蓝色大肥鱼 · 消息')
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-transparentcolor', KEY)
        self.configure(bg=KEY)
        self.withdraw()
        self.card_width, self.card_height = 344, 328
        self.canvas = tk.Canvas(self, width=344, height=328, bg=KEY, highlightthickness=0)
        self.canvas.pack()
        c = self.canvas
        bg = Image.new('RGBA', (344*3, 328*3))
        d = ImageDraw.Draw(bg)
        def rounded(box, radius, fill, outline=None):
            d.rounded_rectangle(tuple(v*3 for v in box), radius=radius*3,
                                fill=fill, outline=outline, width=3)
        rounded((1, 1, 343, 327), 19, '#f2f8ff', '#b7cee6')
        rounded((8, 8, 336, 43), 13, '#e1edfc')
        rounded((14, 101, 330, 279), 13, '#ffffff')
        for box in [(14, 290, 95, 316), (103, 290, 184, 316), (239, 290, 330, 316)]:
            rounded(box, 10, '#e1edfc')
        bg = bg.resize((344, 328), Image.Resampling.LANCZOS)
        rgb = Image.new('RGB', bg.size, KEY)
        rgb.paste(bg.convert('RGB'), mask=bg.getchannel('A').point(lambda a:255 if a>=96 else 0))
        self.background = ImageTk.PhotoImage(rgb, master=self)
        c.create_image(0, 0, anchor='nw', image=self.background)
        c.create_oval(17, 22, 36, 32, fill='#5f83b6', outline='')
        c.create_polygon(34, 27, 42, 20, 41, 31, fill='#5f83b6', outline='')
        c.create_oval(21, 24, 23, 26, fill='#f2f8ff', outline='')
        c.create_text(49, 26, text='蓝色大肥鱼', anchor='w', fill=INK,
                      font=('Microsoft YaHei UI', 10, 'bold'))
        c.create_text(287, 26, text='消息', anchor='e', fill=MUTED,
                      font=('Microsoft YaHei UI', 9))
        c.create_rectangle(304, 12, 332, 39, fill='#e1edfc', outline='', tags='close')
        c.create_text(318, 26, text='×', fill=MUTED, font=('Segoe UI', 15), tags='close')
        self.small_font = font.Font(self, family='Microsoft YaHei UI', size=8)
        self.status_item = c.create_text(19, 62, anchor='w', fill='#486da3',
                                         font=('Microsoft YaHei UI', 9, 'bold'))
        self.phase_item = c.create_text(325, 62, anchor='e', fill=MUTED, font=self.small_font)
        self.chat_item = c.create_text(19, 84, anchor='w', fill=MUTED, font=self.small_font)
        self.status_var = tk.StringVar(value='正在连接…')
        self.phase_var = tk.StringVar(value='等待消息')
        self.chat_var = tk.StringVar(value='跟随当前会话')
        for variable, item, width in [(self.status_var, self.status_item, 146),
                                      (self.phase_var, self.phase_item, 152),
                                      (self.chat_var, self.chat_item, 306)]:
            variable.trace_add('write', lambda *args, v=variable, i=item, w=width:self.label(v, i, w))
            self.label(variable, item, width)
        self.message = tk.Text(c, wrap='word', bd=0, highlightthickness=0,
                              bg='white', fg=INK, font=('Microsoft YaHei UI', 10),
                              padx=0, pady=0, spacing1=2, spacing3=4,
                              selectbackground='#d8e9fb', state='disabled', cursor='arrow')
        self.message.place(x=25, y=111, width=286, height=155)
        self.scroll = tk.Canvas(c, width=6, height=152, bg='white', highlightthickness=0)
        self.scroll.place(x=317, y=113)
        self.scroll_start = None
        self.scroll.bind('<Button-1>', self.start_scroll)
        self.scroll.bind('<B1-Motion>', self.drag_scroll)
        self.scroll.bind('<MouseWheel>', lambda e:self.message.yview_scroll(-int(e.delta/120)*3, 'units'))
        self.message.configure(yscrollcommand=self.draw_scroll)
        c.tag_bind('close', '<Button-1>', lambda e:close())
        for tag, label, x, command in [('choose', '切换会话', 54, choose_chat),
                                       ('quota', '额度卡片', 143, toggle_quota),
                                       ('copy', '复制回复', 284, copy_reply)]:
            c.create_rectangle(x-35, 292, x+35, 314, fill='#e1edfc', outline='', tags=tag)
            c.create_text(x, 303, text=label, fill='#486da3',
                          font=('Microsoft YaHei UI', 9), tags=tag)
            c.tag_bind(tag, '<Button-1>', lambda e, fn=command:fn())
        for tag in ['close', 'choose', 'quota', 'copy']:
            c.tag_bind(tag, '<Enter>', lambda e:c.configure(cursor='hand2'))
            c.tag_bind(tag, '<Leave>', lambda e:c.configure(cursor=''))
        c.bind('<Button-3>', menu)
        self.message.bind('<Button-3>', menu)
        self.bind('<Escape>', lambda e:close())
        self.protocol('WM_DELETE_WINDOW', close)

    def label(self, variable, item, width):
        text = variable.get().replace('\n', ' ')
        original = text
        while self.small_font.measure(text) > width and text:
            text = text[:-1]
        if text != original:
            text = text[:-1]+'…'
        self.canvas.itemconfigure(item, text=text)

    def draw_scroll(self, first, last):
        first, last = float(first), float(last)
        self.scroll.delete('all')
        if last-first < .999:
            self.scroll.create_line(3, 3+146*first, 3, 3+146*last, width=4,
                                    fill='#b3cde9', capstyle='round')

    def start_scroll(self, event):
        first, last = self.message.yview()
        if last-first >= .999:
            return
        if first <= event.y/152 <= last:
            self.scroll_start = (event.y, first)
        else:
            self.message.yview_moveto(max(0, min(1, event.y/152-(last-first)/2)))
            self.scroll_start = (event.y, self.message.yview()[0])

    def drag_scroll(self, event):
        if self.scroll_start:
            y, first = self.scroll_start
            self.message.yview_moveto(max(0, min(1, first+(event.y-y)/152)))
