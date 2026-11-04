"""桌宠下方的蓝白圆角状态条。"""
import tkinter as tk
from tkinter import font
from PIL import Image, ImageDraw, ImageTk
from quota_card import KEY, INK


class StatusBadge(tk.Canvas):
    def __init__(self, root, size, open_message, menu):
        super().__init__(root, height=30, bg=KEY, highlightthickness=0, cursor='hand2')
        self.status_text = '正在连接'
        self.text_font = font.Font(self, family='Microsoft YaHei UI', size=9)
        self.hover = False
        self.bind('<Button-1>', lambda e:open_message())
        self.bind('<Button-3>', menu)
        self.bind('<Enter>', lambda e:self.set_hover(True))
        self.bind('<Leave>', lambda e:self.set_hover(False))
        self.set_width(size)

    def set_width(self, size):
        self.pill_width = max(80, min(212, size-12))
        self.configure(width=self.pill_width)
        self.draw()

    def set_hover(self, value):
        self.hover = value
        self.draw()

    def set_status(self, text):
        if self.status_text != text:
            self.status_text = text
            self.draw()

    def draw(self):
        w = self.pill_width
        self.delete('all')
        bg = Image.new('RGBA', (w*3, 90))
        d = ImageDraw.Draw(bg)
        d.rounded_rectangle((3, 3, (w-1)*3, 87), radius=42,
                            fill='#e1edfc' if self.hover else '#f2f8ff',
                            outline='#b7cee6', width=3)
        bg = bg.resize((w, 30), Image.Resampling.LANCZOS)
        rgb = Image.new('RGB', bg.size, KEY)
        rgb.paste(bg.convert('RGB'), mask=bg.getchannel('A').point(lambda a:255 if a>=96 else 0))
        self.background = ImageTk.PhotoImage(rgb, master=self)
        self.create_image(0, 0, anchor='nw', image=self.background)
        self.create_oval(12, 12, 18, 18, fill='#719fd1', outline='')
        text = self.status_text
        if self.text_font.measure(text+' · 消息') <= w-38:
            text += ' · 消息'
        if self.text_font.measure(text) > w-38:
            while text and self.text_font.measure(text+'…') > w-38:
                text = text[:-1]
            text += '…'
        self.create_text((w+16)/2, 15, text=text, fill=INK, font=self.text_font)
