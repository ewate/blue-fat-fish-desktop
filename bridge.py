"""Read local Codex messages and account limits without changing conversations."""
import datetime as dt
from contextlib import closing
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import threading
import time

CODEX_DIR = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))


def connect_db(name):
    connection = sqlite3.connect((CODEX_DIR / name).as_uri() + '?mode=ro', uri=True, timeout=1)
    connection.execute('PRAGMA query_only=ON')
    return connection


def list_chats():
    with closing(connect_db('state_5.sqlite')) as db:
        rows = db.execute("SELECT id, COALESCE(name,title), cwd FROM threads WHERE archived=0 "
                          "AND (agent_path IS NULL OR agent_path='' OR agent_path='/root') "
                          "ORDER BY recency_at_ms DESC, updated_at_ms DESC LIMIT 30").fetchall()
    return [{'id': r[0], 'name': r[1], 'cwd': r[2]} for r in rows]


def read_chat(thread_id):
    with closing(connect_db('thread_history_1.sqlite')) as db:
        turn = db.execute('SELECT turn_id,status,started_at,completed_at FROM thread_turns '
                          'WHERE thread_id=? ORDER BY rollout_ordinal DESC LIMIT 1', (thread_id,)).fetchone()
        row = db.execute("SELECT item_json,created_at_ms FROM thread_items WHERE thread_id=? "
                         "AND item_type='agentMessage' ORDER BY rollout_ordinal DESC LIMIT 1", (thread_id,)).fetchone()
    if not turn:
        return {'state': 'unknown', 'label': '暂无状态', 'text': '', 'phase': '', 'time': None}
    states = {'inProgress': '正在工作', 'completed': '已完成', 'interrupted': '已停止', 'failed': '出错'}
    message = json.loads(row[0]) if row else {}
    return {'state': turn[1], 'label': states.get(turn[1], '状态未知'),
            'text': message.get('text', ''), 'phase': message.get('phase', ''),
            'time': row[1] if row else None, 'turn': turn[0]}


def find_codex():
    base = Path(os.environ['LOCALAPPDATA']) / 'OpenAI/Codex/bin'
    choices = sorted(base.glob('*/codex.exe'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not choices:
        raise FileNotFoundError('未找到本机 Codex 命令行程序')
    return str(choices[0])


def limit_windows(response):
    buckets = response.get('rateLimitsByLimitId')
    if not buckets:
        item = response.get('rateLimits')
        buckets = {item.get('limitId', 'codex'): item} if item else {}
    windows = []
    for bucket_id, bucket in buckets.items():
        for key in ('primary', 'secondary'):
            window = bucket.get(key)
            if not window or window.get('usedPercent') is None:
                continue
            minutes = window.get('windowDurationMins')
            labels = {300: '5 小时', 10080: '7 天'}
            label = labels.get(minutes, f'{minutes} 分钟' if minutes else '额度')
            if len(buckets) > 1:
                label = (bucket.get('limitName') or bucket_id) + ' · ' + label
            windows.append({'label': label, 'remaining': max(0, min(100, 100-window['usedPercent'])),
                            'reset': window.get('resetsAt'), 'bucket': bucket_id})
    return windows


class LimitsClient:
    def __init__(self):
        self.process = None
        self.responses = queue.Queue()
        self.next_id = 1
        self.latest_notification = None
        self.closed = False

    def start(self):
        if self.closed:
            raise RuntimeError('额度连接已关闭')
        self.process = subprocess.Popen([find_codex(), 'app-server', '--stdio'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            encoding='utf-8', text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        threading.Thread(target=self._read, args=(self.process,), daemon=True).start()
        self.request('initialize', {'clientInfo': {'name': 'blue_fat_fish_pet', 'version': '1.0.0'}})
        self.process.stdin.write('{"method":"initialized"}\n')
        self.process.stdin.flush()

    def _read(self, process):
        for line in process.stdout:
            try:
                message = json.loads(line)
            except (ValueError, TypeError):
                continue
            if message.get('method') == 'account/rateLimits/updated':
                self.latest_notification = message.get('params')
            if 'id' in message and ('result' in message or 'error' in message):
                self.responses.put(message)

    def request(self, method, params=None):
        request_id = self.next_id
        self.next_id += 1
        self.process.stdin.write(json.dumps({'id': request_id, 'method': method, 'params': params or {}})+'\n')
        self.process.stdin.flush()
        deadline = time.monotonic() + 18
        while time.monotonic() < deadline and not self.closed:
            try:
                message = self.responses.get(timeout=.4)
            except queue.Empty:
                if self.process.poll() is not None:
                    raise RuntimeError('Codex 额度连接已退出')
                continue
            if message.get('id') != request_id:
                continue
            if 'error' in message:
                raise RuntimeError(message['error'].get('message', '额度读取失败'))
            return message['result']
        raise TimeoutError('额度查询超时')

    def read(self):
        if not self.process or self.process.poll() is not None:
            self.start()
        return limit_windows(self.request('account/rateLimits/read'))

    def disconnect(self):
        p, self.process = self.process, None
        if p and p.poll() is None:
            try:
                p.stdin.close()
                p.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                p.terminate()
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()

    def close(self):
        self.closed = True
        self.disconnect()


