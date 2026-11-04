"""蓝色大肥鱼：透明桌宠、Codex 会话和额度。"""
import ctypes
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
import logging
import os
from pathlib import Path
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from bridge import LimitsClient, limit_windows, read_chat, list_chats
from quota_card import QuotaCard
from message_card import MessageCard
from status_badge import StatusBadge
from chat_picker import ChatPicker
from pet_menu import PetMenu
from motion_bridge import make_bridge
from speed_slider import SpeedSlider

ROOT = Path(__file__).resolve().parent
DEFAULT_THREAD = None
ACTION_NAMES = {'rice': '吃大白米饭', 'wink': '抛媚眼', 'smile': '闭眼侧头笑',
                'wave': '招招手', 'happy': '开心摇摆', 'idle': '轻摇头 · 摆尾'}
BG = '#f5f9ff'
INK = '#223451'
KEY = '#ff00fe'


def plain_text(text):
    # Keep all message content; remove only common Markdown decoration.
    import re
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    return text.replace('**', '').replace('### ', '').replace('## ', '')


class Pet:
    def __init__(self, root):
        self.root = root
        self.precise_timer = ctypes.windll.winmm.timeBeginPeriod(1)==0
        self.closed = threading.Event()
        self.refresh_limits = threading.Event()
        self.events = queue.Queue()
        self.limits_client = LimitsClient()
        self.config = {'thread_id': DEFAULT_THREAD, 'size': 176, 'panel': False, 'quota': False, 'status_bar': True, 'codex_sync': False}
        try:
            self.config.update(json.loads((ROOT/'settings.json').read_text(encoding='utf-8')))
        except (OSError, ValueError):
            pass
        self.thread_id = self.config['thread_id']
        self.sync_enabled=bool(self.config.get('codex_sync',False))
        self.size = int(self.config['size'])
        self.animation_speed=max(.5,min(2,float(self.config.get('animation_speed',1))))
        self.state = 'idle'
        self.last_action = None
        self.frame_number = 0
        self.frame_cursor = 0
        self.animation_start = time.perf_counter()
        self.next_frame_at = time.perf_counter()
        self.render_times = []
        self.playback_stats = {}
        self.loops = 0
        self.current_text = None
        self.last_limit_time = None
        self.last_snapshot = None
        self.animation_log = []
        self.drag_start = None
        self.dragged = False
        self.panel_visible = self.config.get('panel', True)
        self.quota_visible = self.config.get('quota', True)
        self.badge_visible = self.config.get('status_bar', True)
        self.photos = {}
        self.images = {}
        self.durations = {}
        self.repeats = {}
        self.blink_manifest = {}
        self.blink_cache = {}
        self.next_blink_at=time.perf_counter()+4
        self.blink_started=None
        self.blink_style='single'
        self.blink_log=[]
        self.motion_phase = 'loop'
        self.pending_action = None
        self.motion_log = []
        self.motion_worker = ThreadPoolExecutor(max_workers=1,thread_name_prefix='pet-motion')
        self.bridge_future = None
        self.bridge_images = []
        self.bridge_photos = []
        self.last_tick_at=time.perf_counter()
        self.load_assets()
        self.displayed_image = self.images['idle'][0]
        self.last_tick_at=self.next_frame_at=time.perf_counter()
        self.next_blink_at=self.last_tick_at+4
        root.title('蓝色大肥鱼')
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg=KEY)
        root.attributes('-transparentcolor', KEY)
        self.canvas = tk.Canvas(root, width=self.size, height=self.size, bg=KEY,
                                highlightthickness=0, cursor='hand2')
        self.canvas.pack()
        self.sprite = self.canvas.create_image(self.size//2, self.size//2, anchor='center')
        self.canvas.bind('<ButtonPress-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        self.canvas.bind('<Button-3>', self.menu)
        self.badge = StatusBadge(root, self.size, self.toggle_panel, self.menu)
        if self.badge_visible:
            self.badge.pack(pady=(2,2))
        x = self.config.get('x', root.winfo_screenwidth()-self.size-45)
        y = self.config.get('y', root.winfo_screenheight()-self.size-340)
        root.geometry(f'+{max(0,x)}+{max(0,y)}')
        self.build_panel()
        self.quota = QuotaCard(root, self.toggle_quota, self.refresh_limits.set, self.menu)
        self.root.update_idletasks()
        self.place_panel()
        if not self.panel_visible:
            self.panel.withdraw()
        root.after(200,root.deiconify)
        if self.panel_visible:
            root.after(220,lambda:self.panel.deiconify() if self.panel_visible else None)
        if self.quota_visible:
            root.after(230,lambda:self.quota.deiconify() if self.quota_visible else None)
        root.after(240,root.lift)
        root.bind('<Escape>', lambda e: self.toggle_panel())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.status_label = '正在连接' if self.sync_enabled else '未连接'
        self.limit_short = '额度读取中' if self.sync_enabled else '同步未开启'
        threading.Thread(target=self.chat_worker, daemon=True).start()
        threading.Thread(target=self.limits_worker, daemon=True).start()
        if not self.sync_enabled:
            self.status_var.set('● 同步未开启')
            self.limits_var.set('同步未开启')
            self.quota.update_limits(failed=True)
        self.tick()
        self.poll_events()

    def load_assets(self):
        self.photos.clear()
        self.images.clear()
        smooth=ROOT/'assets/animations-smooth.json'
        manifest = json.loads((smooth if smooth.exists() else ROOT/'assets/animations.json').read_text(encoding='utf-8'))
        for name, item in manifest.items():
            frames = []
            rgba_frames = []
            for path in item['frames']:
                im = Image.open(ROOT/'assets'/path).convert('RGBA').resize((self.size,self.size), Image.Resampling.LANCZOS)
                rgba_frames.append(im)
                # Windows color-key transparency; retain original edge RGB, no colored halo.
                rgb = Image.new('RGB', im.size, KEY)
                rgb.paste(im.convert('RGB'), mask=im.getchannel('A').point(lambda a: 255 if a >= 96 else 0))
                frames.append(ImageTk.PhotoImage(rgb, master=self.root))
            self.images[name] = rgba_frames
            self.photos[name] = frames
            self.durations[name] = item.get('duration_ms', 160)
            self.repeats[name] = item.get('repeats',2)
        self.blink_cache.clear()
        blink_path=ROOT/'assets/blink.json'
        self.blink_manifest=json.loads(blink_path.read_text(encoding='utf-8')) if blink_path.exists() else {}

    def make_photo(self, image):
        rgb=Image.new('RGB',image.size,KEY)
        rgb.paste(image.convert('RGB'),mask=image.getchannel('A').point(lambda a:255 if a>=96 else 0))
        return ImageTk.PhotoImage(rgb,master=self.root)

    def build_panel(self):
        self.panel = MessageCard(self.root, self.toggle_panel, self.choose_chat,
                                 self.toggle_quota, self.copy_reply, self.menu)
        self.status_var = self.panel.status_var
        self.chat_var = self.panel.chat_var
        if self.config.get('chat_name'):
            self.chat_var.set(self.config['chat_name'])
        self.phase_var = self.panel.phase_var
        self.message = self.panel.message
        self.limits_var = tk.StringVar(value='正在读取账号额度…')
        self.updated_var = tk.StringVar(value='额度自动刷新 · 30 秒')

    def place_panel(self):
        self.panel.update_idletasks()
        width, height = self.panel.winfo_reqwidth(), self.panel.winfo_reqheight()
        x = self.root.winfo_x() - width - 10
        if x < 0:
            x = self.root.winfo_x() + self.size + 10
        x = min(max(0,x), max(0,self.root.winfo_screenwidth()-width))
        y = min(max(0,self.root.winfo_y()+20), max(0,self.root.winfo_screenheight()-height-55))
        self.panel.geometry(f'{width}x{height}+{x}+{y}')
        if hasattr(self, 'quota'):
            self.place_quota()

    def place_quota(self):
        width, height = self.quota.card_width, self.quota.card_height
        x = self.root.winfo_x() + (self.size-width)//2
        x = max(0, min(self.root.winfo_screenwidth()-width, x))
        y = self.root.winfo_y() + self.root.winfo_height() + 8
        if y+height > self.root.winfo_screenheight()-48:
            y = self.root.winfo_y()-height-8
        y = max(0, min(self.root.winfo_screenheight()-height-48, y))
        self.quota.geometry(f'{width}x{height}+{x}+{y}')

    def save_settings(self):
        self.config.update(thread_id=self.thread_id, size=self.size, panel=self.panel_visible,
                           quota=self.quota_visible, status_bar=self.badge_visible,
                           animation_speed=self.animation_speed, codex_sync=self.sync_enabled,
                           x=self.root.winfo_x(), y=self.root.winfo_y())
        (ROOT/'settings.json').write_text(json.dumps(self.config,ensure_ascii=False,indent=2),encoding='utf-8')

    def toggle_badge(self):
        self.badge_visible = not self.badge_visible
        if self.badge_visible:
            self.badge.pack(pady=(2,2))
        else:
            self.badge.pack_forget()
        self.root.update_idletasks()
        self.place_panel()
        self.save_settings()

    def toggle_quota(self):
        self.quota_visible = not self.quota_visible
        if self.quota_visible:
            self.place_quota()
            self.quota.deiconify()
        else:
            self.quota.withdraw()
        self.save_settings()

    def toggle_panel(self):
        self.panel_visible = not self.panel_visible
        if self.panel_visible:
            self.place_panel()
            self.panel.deiconify()
        else:
            self.panel.withdraw()
        self.save_settings()

    def press(self, event):
        self.dragged = False
        self.drag_start = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def drag(self, event):
        if not self.drag_start:
            return
        sx, sy, wx, wy = self.drag_start
        dx, dy = event.x_root-sx, event.y_root-sy
        if abs(dx)+abs(dy)>6:
            self.dragged = True
            x = max(0,min(self.root.winfo_screenwidth()-self.size,wx+dx))
            y = max(0,min(self.root.winfo_screenheight()-self.size-60,wy+dy))
            self.root.geometry(f'+{x}+{y}')
            self.place_panel()

    def release(self, event):
        if not self.dragged:
            self.play_random()
        self.drag_start = None

    def play_random(self):
        choices = [x for x in ACTION_NAMES if x != 'idle' and x != self.last_action and x in self.photos]
        self.play(random.choice(choices))

    def play(self, name):
        if name not in self.photos:
            return
        if name != 'idle':
            self.last_action = name
        self.animation_log.append({'action': name, 'time': time.time()})
        self.animation_log = self.animation_log[-30:]
        if self.state=='idle' and self.motion_phase=='loop':
            if name!='idle':
                self.begin_action(name)
        else:
            # Finish the current gesture before changing props or expression.
            # Repeated clicks replace the queued request, never create a backlog.
            self.pending_action=name
            length=len(self.photos[self.state])
            self.pending_boundary=(int(self.frame_cursor)//length+1)*length if self.motion_phase=='loop' else length

    def begin_action(self, name):
        self.state=name
        self.playback_stats[name]={'frames':set(),'times':[]}
        self.frame_number=self.frame_cursor=0
        self.blink_started=None
        self.start_bridge(self.images[name][0],'loop')

    def start_bridge(self, target, next_phase):
        self.bridge_next=next_phase
        self.motion_phase='bridge_wait'
        self.bridge_future=self.motion_worker.submit(make_bridge,self.displayed_image.copy(),target.copy())
        self.motion_log.append({'event':'bridge','state':self.state,'next':next_phase,'time':time.perf_counter()})
        self.motion_log=self.motion_log[-100:]

    def settle_idle(self):
        self.state='idle'
        self.motion_phase='loop'
        self.frame_number=0
        self.frame_cursor=1
        self.motion_log.append({'event':'idle','time':time.perf_counter()})
        pending=self.pending_action
        self.pending_action=None
        if pending and pending!='idle':
            self.begin_action(pending)

    def finish_action(self):
        self.start_bridge(self.images['idle'][0],'rest')

    def blink_closed(self, now):
        if now>=self.next_blink_at:
            due=self.next_blink_at
            self.next_blink_at+=4*(int((now-self.next_blink_at)//4)+1)
            if self.state=='idle' and self.motion_phase=='loop':
                self.blink_started=now+random.uniform(0,.28)
                self.blink_style=random.choice(['single','single','single','double'])
                self.blink_log.append({'due':due,'start':self.blink_started,'style':self.blink_style,'frame':self.frame_number})
                self.blink_log=self.blink_log[-50:]
        if self.blink_started is None:return False
        t=now-self.blink_started
        if t>.38:self.blink_started=None;return False
        return .025<=t<.115 or (self.blink_style=='double' and .22<=t<.30)

    def blink_frame(self,index):
        key=(index,self.size)
        if key not in self.blink_cache:
            path=self.blink_manifest['frames'][index%len(self.blink_manifest['frames'])]
            im=Image.open(ROOT/'assets'/path).convert('RGBA').resize((self.size,self.size),Image.Resampling.LANCZOS)
            self.blink_cache[key]=(im,self.make_photo(im))
            if len(self.blink_cache)>64:self.blink_cache.pop(next(iter(self.blink_cache)))
        return self.blink_cache[key]

    def tick(self):
        if self.closed.is_set():return
        now=time.perf_counter()
        elapsed=min(.05,max(.001,now-self.last_tick_at))
        self.last_tick_at=now
        advance=elapsed*60*self.animation_speed
        image=photo=None
        eyes_closed=self.blink_closed(now)
        if self.motion_phase=='bridge_wait' and self.bridge_future.done():
            try:
                self.bridge_images=[im.resize((self.size,self.size),Image.Resampling.LANCZOS) for im in self.bridge_future.result()]
                self.bridge_photos=[self.make_photo(im) for im in self.bridge_images]
                self.bridge_index=0
                self.motion_phase='bridge'
            except Exception:
                logging.exception('动作过渡生成失败')
                self.pending_action=None
                self.motion_phase='loop'
                self.frame_cursor=0
        if self.motion_phase=='bridge':
            if self.bridge_index<len(self.bridge_photos):
                index=min(round(self.bridge_index),len(self.bridge_photos)-1)
                image=self.bridge_images[index]
                photo=self.bridge_photos[index]
                self.bridge_index=len(self.bridge_photos) if index==len(self.bridge_photos)-1 else min(self.bridge_index+advance,len(self.bridge_photos)-1)
            else:
                self.motion_phase=self.bridge_next
                self.frame_cursor=1
                if self.motion_phase=='rest':self.settle_idle()
        elif self.motion_phase=='loop':
            frames=self.photos[self.state]
            end=self.frame_cursor>=len(frames)*self.repeats[self.state]
            queued=self.pending_action is not None and self.frame_cursor>=getattr(self,'pending_boundary',len(frames))
            if self.state!='idle' and (end or queued):
                self.finish_action()
            else:
                self.frame_number=round(self.frame_cursor)%len(frames)
                # Non-looping rice ends on its satisfied expression, never wraps.
                if self.state!='idle' and self.repeats[self.state]==1:
                    self.frame_number=min(round(self.frame_cursor),len(frames)-1)
                image=self.images[self.state][self.frame_number]
                photo=frames[self.frame_number]
                if self.state=='idle' and eyes_closed and self.blink_manifest:
                    image,photo=self.blink_frame(self.frame_number)
                self.frame_cursor+=advance
        if image is not None and not getattr(self,'resize_preview',None):
            self.canvas.itemconfigure(self.sprite,image=photo)
            self.displayed_image=image
            if self.state!='idle' and self.motion_phase=='loop':
                stats=self.playback_stats[self.state]
                stats['frames'].add(self.frame_number)
                stats['times'].append(now)
        self.render_times.append(now)
        self.render_times=self.render_times[-180:]
        self.next_frame_at+=1/60
        if self.next_frame_at<now-.02:self.next_frame_at=now+1/60
        self.root.after(max(1,round((self.next_frame_at-time.perf_counter())*1000)),self.tick)

    def menu(self, event):
        if getattr(self,'popup_menu',None) is not None and self.popup_menu.winfo_exists():
            self.popup_menu.destroy()
        actions=[{'label':label,'command':lambda k=key:self.play(k)} for key,label in ACTION_NAMES.items()]
        sizes=[{'label':label,'command':lambda s=size:self.resize(s)}
               for size,label in [(128,'迷你 · 128'),(176,'小 · 176'),(224,'中 · 224'),(288,'大 · 288')]]
        entries=[
            {'label':'连接 Codex 同步','checked':lambda:self.sync_enabled,'command':self.toggle_sync},
            {'label':'随机可爱动作','command':self.play_random},
            {'label':'指定动作','children':actions},
            {'label':'显示状态条','checked':lambda:self.badge_visible,'command':self.toggle_badge},
            {'label':'显示消息卡片','checked':lambda:self.panel_visible,'command':self.toggle_panel},
            {'label':'显示额度卡片','checked':lambda:self.quota_visible,'command':self.toggle_quota},
            {'label':'切换跟随会话','command':self.choose_chat},
            {'label':'立即刷新额度','command':self.refresh_limits.set},
            {'label':'调整大小 · 滑块','command':self.size_dialog},
            {'label':f'动画速度 · {self.animation_speed:g}×','command':self.speed_dialog},
            {'label':'常用尺寸','children':sizes},
            {'label':'退出桌宠','command':self.close,'exit':True},
        ]
        self.popup_menu=PetMenu(self.root,entries,event.x_root,event.y_root)

    def speed_dialog(self):
        if getattr(self,'speed_popup',None) is not None and self.speed_popup.winfo_exists():
            self.speed_popup.lift();self.speed_popup.focus_force();return
        self.speed_popup=SpeedSlider(self.root,self.animation_speed,self.set_animation_speed,self.save_settings)

    def set_animation_speed(self,value):
        self.animation_speed=max(.5,min(2,float(value)))

    def resize(self, size):
        self.size = size
        self.badge.set_width(size)
        self.load_assets()
        self.displayed_image=self.displayed_image.resize((size,size),Image.Resampling.LANCZOS)
        self.bridge_images=[im.resize((size,size),Image.Resampling.LANCZOS) for im in self.bridge_images]
        self.bridge_photos=[self.make_photo(im) for im in self.bridge_images]
        self.canvas.configure(width=size,height=size)
        self.canvas.coords(self.sprite,size//2,size//2)
        self.root.update_idletasks()
        self.place_panel()
        self.save_settings()

    def size_dialog(self):
        popup=tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes('-topmost',True)
        popup.configure(bg='#b9d3ee',padx=1,pady=1)
        track=tk.Canvas(popup,width=220,height=58,bg=BG,highlightthickness=0,cursor='hand2')
        track.pack()
        pending=[self.size]
        source=self.displayed_image.copy()
        def draw():
            track.delete('all')
            track.create_text(13,15,text='大小',anchor='w',fill=INK,font=('Microsoft YaHei UI',9))
            track.create_text(207,15,text='重置',anchor='e',fill='#3374b4',font=('Microsoft YaHei UI',9),tags='reset')
            x=22+(pending[0]-96)/224*176
            track.create_line(22,40,198,40,fill='#d6e2ef',width=4,capstyle='round')
            track.create_line(22,40,x,40,fill='#568ac3',width=4,capstyle='round')
            track.create_oval(x-6,34,x+6,46,fill='#3374b4',outline='')
        def preview(event):
            if event.y<26:
                return
            size=max(96,min(320,round((96+(event.x-22)/176*224)/4)*4))
            pending[0]=size
            im=source.resize((size,size),Image.Resampling.LANCZOS)
            rgb=Image.new('RGB',im.size,KEY)
            rgb.paste(im.convert('RGB'),mask=im.getchannel('A').point(lambda a:255 if a>=96 else 0))
            self.resize_preview=ImageTk.PhotoImage(rgb,master=self.root)
            self.canvas.configure(width=size,height=size)
            self.badge.set_width(size)
            self.canvas.coords(self.sprite,size//2,size//2)
            self.canvas.itemconfigure(self.sprite,image=self.resize_preview)
            draw()
        def apply(event=None):
            if pending[0]!=self.size:
                self.resize(pending[0])
            self.resize_preview=None
            self.config['size']=self.size
            (ROOT/'settings.json').write_text(json.dumps(self.config,ensure_ascii=False,indent=2),encoding='utf-8')
        def dismiss(event=None):
            apply()
            if popup.winfo_exists():
                popup.destroy()
        def reset(event):
            pending[0]=176
            apply()
            draw()
            return 'break'
        track.bind('<ButtonPress-1>',preview)
        track.bind('<B1-Motion>',preview)
        track.bind('<ButtonRelease-1>',apply)
        track.tag_bind('reset','<Button-1>',reset)
        popup.bind('<FocusOut>',dismiss)
        popup.bind('<Escape>',dismiss)
        draw()
        x=max(0,min(self.root.winfo_screenwidth()-222,self.root.winfo_x()+(self.size-222)//2))
        y=min(self.root.winfo_screenheight()-65,self.root.winfo_y()+self.root.winfo_height()+5)
        popup.geometry(f'+{x}+{max(0,y)}')
        popup.focus_force()

    def copy_reply(self):
        if self.current_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_text)

    def choose_chat(self):
        if getattr(self,'chat_picker',None) is not None and self.chat_picker.winfo_exists():
            self.chat_picker.lift()
            self.chat_picker.focus_set()
            return
        try:
            chats = list_chats()
        except Exception as exc:
            messagebox.showerror('会话读取失败',str(exc), parent=self.root)
            return
        def choose(item):
            self.thread_id=item['id']
            self.config['chat_name']=' '.join((item.get('name') or '未命名会话').split())
            self.chat_var.set(self.config['chat_name'])
            self.current_text=None
            self.last_snapshot=None
            self.message.configure(state='normal')
            self.message.delete('1.0','end')
            self.message.insert('1.0','正在读取此会话的最新消息…')
            self.message.configure(state='disabled')
            self.status_label='正在连接'
            self.status_var.set('● 正在连接')
            self.phase_var.set('等待消息')
            self.save_settings()
        self.chat_picker=ChatPicker(self.root,chats,self.thread_id,choose)

    def toggle_sync(self):
        self.sync_enabled=not self.sync_enabled
        if self.sync_enabled:
            self.refresh_limits.set()
            if not self.thread_id:self.choose_chat()
        else:
            self.status_label='未连接'
            self.status_var.set('● 同步未开启')
        self.save_settings()

    def chat_worker(self):
        while not self.closed.is_set():
            if not self.sync_enabled or not self.thread_id:
                self.closed.wait(.5)
                continue
            thread_id = self.thread_id
            try:
                snapshot = read_chat(thread_id)
                self.events.put(('chat',(thread_id,snapshot)))
            except Exception as exc:
                self.events.put(('chat_error',str(exc)))
            self.closed.wait(2)

    def limits_worker(self):
        next_read = 0
        while not self.closed.is_set():
            if not self.sync_enabled:
                next_read=0
                self.closed.wait(.5)
                continue
            if time.perf_counter() >= next_read or self.refresh_limits.is_set():
                self.refresh_limits.clear()
                try:
                    windows = self.limits_client.read()
                    if not windows:
                        raise RuntimeError('账号未返回可用额度窗口')
                    self.events.put(('limits',windows))
                except Exception as exc:
                    self.events.put(('limits_error',str(exc)))
                    self.limits_client.disconnect()
                next_read = time.perf_counter()+30
            notification = self.limits_client.latest_notification
            if notification:
                self.limits_client.latest_notification = None
                # Re-read the complete multi-bucket response instead of replacing it with a partial event.
                next_read = 0
            self.closed.wait(.5)
        self.limits_client.close()

    def poll_events(self):
        if self.closed.is_set():
            return
        for _ in range(30):
            try:
                kind, data = self.events.get_nowait()
            except queue.Empty:
                break
            if not self.sync_enabled and kind in ('chat','chat_error','limits','limits_error'):
                continue
            if kind=='chat':
                thread_id,snapshot=data
                if thread_id!=self.thread_id:
                    continue
                self.status_label=snapshot['label']
                self.status_var.set('● '+self.status_label)
                if snapshot['text']!=self.current_text:
                    self.current_text=snapshot['text']
                    self.message.configure(state='normal')
                    self.message.delete('1.0','end')
                    self.message.insert('1.0',plain_text(self.current_text) or '还没有助手回复。')
                    self.message.configure(state='disabled')
                    phase='最新回复' if snapshot['phase']=='final_answer' else '最新进度'
                    stamp=dt.datetime.fromtimestamp(snapshot['time']/1000).strftime('%H:%M:%S') if snapshot['time'] else ''
                    self.phase_var.set(f'{phase} · {stamp}')
                if self.state=='idle' and self.last_snapshot and self.last_snapshot['state']=='inProgress' and snapshot['state']=='completed':
                    self.play('happy')
                self.last_snapshot=snapshot
            elif kind=='chat_error':
                self.status_label='同步失败'
                self.status_var.set('● 状态同步失败 · 保留上次消息')
                logging.warning('chat: %s',data)
            elif kind=='limits':
                self.last_limit_time=time.time()
                self.limit_short=' / '.join(f"{w['label']}剩 {w['remaining']:g}%" for w in data)
                lines=[]
                for w in data:
                    reset=dt.datetime.fromtimestamp(w['reset']).strftime('%m-%d %H:%M') if w['reset'] else '未知'
                    lines.append(f"{w['label']}剩余 {w['remaining']:g}%   ·   重置 {reset}")
                self.limits_var.set('\n'.join(lines))
                self.updated_var.set('更新于 '+dt.datetime.now().strftime('%H:%M:%S')+' · 每 30 秒刷新')
                self.quota.update_limits(data, self.last_limit_time)
                self.place_quota()
            elif kind=='limits_error':
                self.limit_short='额度更新失败'
                when=dt.datetime.fromtimestamp(self.last_limit_time).strftime('%H:%M:%S') if self.last_limit_time else '无'
                self.updated_var.set('更新失败 · 上次成功 '+when+' · 自动重试')
                self.quota.update_limits(failed=True)
                self.place_quota()
                logging.warning('limits: %s',data)
        self.badge.set_status(self.status_label)
        self.root.after(150,self.poll_events)

    def close(self):
        if self.closed.is_set():
            return
        self.save_settings()
        self.closed.set()
        if self.precise_timer:
            ctypes.windll.winmm.timeEndPeriod(1)
            self.precise_timer=False
        self.motion_worker.shutdown(wait=False,cancel_futures=True)
        self.limits_client.close()
        self.root.destroy()


if __name__=='__main__':
    logging.basicConfig(filename=ROOT/'pet.log', level=logging.WARNING, encoding='utf-8',
                        format='%(asctime)s %(levelname)s %(message)s')
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    ctypes.windll.kernel32.CreateMutexW.restype=ctypes.c_void_p
    ctypes.windll.kernel32.CloseHandle.argtypes=[ctypes.c_void_p]
    mutex=ctypes.windll.kernel32.CreateMutexW(None,False,'Local\\BlueFatFishDesktopPet')
    if ctypes.windll.kernel32.GetLastError()==183:
        raise SystemExit('桌宠已经运行')
    root=tk.Tk()
    try:
        pet=Pet(root)
        import sys
        if '--inspect' in sys.argv:
            root.overrideredirect(False)
            pet.panel.overrideredirect(False)
            pet.quota.overrideredirect(False)
        root.mainloop()
    except Exception:
        logging.exception('启动失败')
        messagebox.showerror('蓝色大肥鱼','启动失败，请查看同目录 pet.log。')
        raise
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)
