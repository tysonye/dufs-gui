import os
import sys
import time
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import urllib.request

import pystray
from PIL import Image

# ================== 基础配置 ==================
APP_TITLE = "文件共享工具（本地 / 外网）"

FONT_MAIN = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_STATUS = ("Segoe UI", 10, "bold")

COLOR_BG = "#f5f6f8"  # 浅灰背景
COLOR_CARD = "#ffffff"  # 白色卡片
COLOR_PRIMARY = "#2563eb"  # 蓝色主色
COLOR_SUCCESS = "#16a34a"  # 绿色
COLOR_WARN = "#f59e0b"  # 黄色
COLOR_DANGER = "#dc2626"  # 红色
COLOR_TEXT = "#111827"  # 文字颜色
COLOR_SUB = "#6b7280"  # 副文字颜色

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

DUFS_EXE = os.path.join(BASE_DIR, "dufs.exe")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")

# ================== 全局状态 ==================
dufs_proc = None
current_dir = ""
tray_icon = None

UNSAFE_PORTS = set(range(6660, 6670)) | {21, 22, 25, 10080, 31337}

# ================== 工具函数 ==================
def try_bind(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except:
        return None

def find_port(start, max_try=30):
    for i in range(max_try):
        p = start + i
        if p in UNSAFE_PORTS:
            continue
        s = try_bind(p)
        if s:
            return p, s
    return None, None

def wait_http(port, timeout=3):
    end = time.time() + timeout
    while time.time() < end:
        try:
            socket.create_connection(("127.0.0.1", port), 0.5).close()
            return True
        except:
            time.sleep(0.1)
    return False

def copy_text(var):
    root.clipboard_clear()
    root.clipboard_append(var.get())

# ================== IP ==================
def get_public_ip_async(var, port):
    def worker():
        try:
            ip = urllib.request.urlopen("https://api.ipify.org", timeout=3).read().decode()
            url = f"http://{ip}:{port}"
        except:
            url = "获取失败"
        root.after(0, lambda: var.set(url))
    threading.Thread(target=worker, daemon=True).start()

# ================== DUFS 控制 ==================
def stop_dufs():
    global dufs_proc
    if dufs_proc and dufs_proc.poll() is None:
        try:
            dufs_proc.terminate()
            dufs_proc.wait(timeout=2)
        except:
            try:
                dufs_proc.kill()
            except:
                pass
    dufs_proc = None
    status_var.set("🔴 已停止共享")
    status_label.config(fg=COLOR_DANGER)

def start_dufs_async(args):
    threading.Thread(target=start_dufs, args=(args,), daemon=True).start()

def start_dufs(args):
    global dufs_proc

    if not os.path.isdir(current_dir):
        messagebox.showerror("提示", "请先选择要共享的文件夹")
        return

    try:
        base_port = int(port_entry.get())
    except:
        messagebox.showerror("提示", "端口号无效")
        return

    stop_dufs()
    status_var.set("🟠 正在启动共享…")
    status_label.config(fg=COLOR_WARN)

    port, sock = find_port(base_port)
    if not sock:
        messagebox.showerror("失败", "未找到可用端口")
        return

    sock.close()

    dufs_proc = subprocess.Popen(
        [DUFS_EXE, current_dir, "--port", str(port)] + args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    if not wait_http(port):
        stop_dufs()
        messagebox.showerror("失败", "共享启动失败")
        return

    def ok():
        port_entry.delete(0, tk.END)
        port_entry.insert(0, str(port))
        local_addr_var.set(f"http://127.0.0.1:{port}")
        public_addr_var.set("正在获取…")
        get_public_ip_async(public_addr_var, port)
        status_var.set("🟢 已开始共享")
        status_label.config(fg=COLOR_SUCCESS)

    root.after(0, ok)

# ================== 托盘 ==================
def show_window(icon=None, item=None):
    root.after(0, root.deiconify)

def quit_app(icon=None, item=None):
    stop_dufs()
    if tray_icon:
        tray_icon.stop()
    os._exit(0)

def create_tray():
    global tray_icon
    image = Image.open(ICON_PATH)
    menu = pystray.Menu(
        pystray.MenuItem("显示界面", show_window),
        pystray.MenuItem("只读共享（推荐）", lambda *_: start_dufs_async([])),
        pystray.MenuItem("可编辑共享", lambda *_: start_dufs_async(["--allow-all"])),
        pystray.MenuItem("账号密码访问", lambda *_: start_dufs_async(["-a", "admin:123456@/:rw"])),
        pystray.MenuItem("停止共享", lambda *_: stop_dufs()),
        pystray.MenuItem("退出程序", quit_app),
    )
    tray_icon = pystray.Icon("dufs", image, "文件共享工具", menu)
    tray_icon.run()

def ensure_tray():
    if tray_icon is None:
        threading.Thread(target=create_tray, daemon=True).start()

# ================== 窗口行为 ==================
def on_minimize(event):
    if root.state() == "iconic":
        root.withdraw()
        ensure_tray()

def on_close():
    quit_app()

# ================== UI ==================
root = tk.Tk()
root.title(APP_TITLE)
root.geometry("620x420")
root.configure(bg=COLOR_BG)
root.resizable(False, False)

if os.path.exists(ICON_PATH):
    root.iconbitmap(ICON_PATH)

# ====== 标题 ======
title = tk.Label(root, text="文件共享工具", font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT)
title.pack(anchor="w", padx=20, pady=(15, 5))

subtitle = tk.Label(
    root,
    text="快速共享本地文件夹，支持局域网和外网访问",
    font=FONT_MAIN,
    bg=COLOR_BG,
    fg=COLOR_SUB
)
subtitle.pack(anchor="w", padx=20, pady=(0, 10))

# ====== 卡片容器 ======
card = tk.Frame(root, bg=COLOR_CARD)
card.pack(fill="both", expand=True, padx=20, pady=10)

# ====== 目录选择 ======
tk.Label(card, text="要共享的文件夹", bg=COLOR_CARD, font=FONT_MAIN).pack(anchor="w", padx=15, pady=(15, 5))
dir_row = tk.Frame(card, bg=COLOR_CARD)
dir_row.pack(fill="x", padx=15)

dir_entry = tk.Entry(dir_row, font=FONT_MAIN)
dir_entry.pack(side="left", fill="x", expand=True)

def choose_dir():
    global current_dir
    d = filedialog.askdirectory()
    if d:
        current_dir = d
        dir_entry.delete(0, tk.END)
        dir_entry.insert(0, d)

tk.Button(dir_row, text="浏览", command=choose_dir).pack(side="left", padx=8)

# ====== 端口 ======
tk.Label(card, text="端口（一般无需修改）", bg=COLOR_CARD, font=FONT_MAIN).pack(anchor="w", padx=15, pady=(10, 5))
port_entry = tk.Entry(card, width=10, font=FONT_MAIN)
port_entry.insert(0, "5000")
port_entry.pack(anchor="w", padx=15)

# ====== 启动按钮 ======
btn_row = tk.Frame(card, bg=COLOR_CARD)
btn_row.pack(pady=15)

tk.Button(btn_row, text="🔒 只读共享（推荐）", width=18,
          command=lambda: start_dufs_async([])).grid(row=0, column=0, padx=5)
tk.Button(btn_row, text="✏️ 可编辑共享", width=18,
          command=lambda: start_dufs_async(["--allow-all"])).grid(row=0, column=1, padx=5)
tk.Button(btn_row, text="🔐 账号密码访问", width=18,
          command=lambda: start_dufs_async(["-a", "admin:123456@/:rw"])).grid(row=0, column=2, padx=5)

# ====== 状态 ======
status_var = tk.StringVar(value="⚪ 尚未开始共享")
status_label = tk.Label(card, textvariable=status_var, font=FONT_STATUS, bg=COLOR_CARD)
status_label.pack(pady=(5, 10))

# ====== 地址 ======
addr_box = tk.Frame(card, bg=COLOR_CARD)
addr_box.pack(fill="x", padx=15, pady=10)

local_addr_var = tk.StringVar(value="-")
public_addr_var = tk.StringVar(value="-")

def addr_row(title, var):
    r = tk.Frame(addr_box, bg=COLOR_CARD)
    r.pack(fill="x", pady=4)
    tk.Label(r, text=title, bg=COLOR_CARD, width=22, anchor="w").pack(side="left")
    tk.Label(r, textvariable=var, bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(side="left", fill="x", expand=True)
    tk.Button(r, text="复制", command=lambda: copy_text(var)).pack(side="right")

addr_row("局域网访问地址", local_addr_var)
addr_row("外网访问地址", public_addr_var)

# ====== 底部 ======
bottom = tk.Frame(root, bg=COLOR_BG)
bottom.pack(fill="x", pady=10)

tk.Button(bottom, text="停止共享", width=18, command=stop_dufs).pack(side="left", padx=10)
tk.Button(bottom, text="最小化到托盘", width=18,
          command=lambda: (root.withdraw(), ensure_tray())).pack(side="left", padx=10)
tk.Button(bottom, text="停止共享并退出", width=18,
          fg="white", bg=COLOR_DANGER,
          command=on_close).pack(side="right", padx=10)

root.bind("<Unmap>", on_minimize)
root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
