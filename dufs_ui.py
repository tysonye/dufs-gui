import os
import sys
import threading
import subprocess
import socket
import tkinter as tk
from tkinter import filedialog, messagebox
import urllib.request
import time

import pystray
from PIL import Image

# ================= 路径 =================
if getattr(sys, 'frozen', False):  # 判断是否是打包后的程序
    BASE_DIR = sys._MEIPASS  # 使用 PyInstaller 提供的临时目录
else:
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

DUFS_EXE = os.path.join(BASE_DIR, "dufs.exe")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")

# ================= 状态机 =================
STATE_STOPPED = "STOPPED"
STATE_STARTING = "STARTING"
STATE_RUNNING = "RUNNING"

current_state = STATE_STOPPED
dufs_proc = None
tray_icon = None
current_dir = BASE_DIR

# ================= 工具 =================
def port_used(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0

def wait_port_release(port, timeout=3):
    start = time.time()
    while time.time() - start < timeout:
        if not port_used(port):
            return True
        time.sleep(0.1)
    return False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_public_ip_async(var):
    def worker():
        try:
            ip = urllib.request.urlopen("https://api.ipify.org", timeout=3).read().decode()
        except:
            ip = "获取失败"
        root.after(0, lambda: var.set(ip))
    threading.Thread(target=worker, daemon=True).start()

# ================= DUFS 控制 =================
def stop_dufs():
    global dufs_proc, current_state
    current_state = STATE_STOPPED
    if dufs_proc and dufs_proc.poll() is None:
        try:
            dufs_proc.kill()
            dufs_proc.wait(timeout=2)
        except:
            pass
    dufs_proc = None
    status_var.set("已停止")

def start_dufs_async(extra_args):
    threading.Thread(target=start_dufs, args=(extra_args,), daemon=True).start()

def start_dufs(extra_args):
    global dufs_proc, current_state

    stop_dufs()

    try:
        port = int(port_entry.get())
    except:
        root.after(0, lambda: messagebox.showerror("错误", "端口无效"))
        return

    wait_port_release(port)

    current_state = STATE_STARTING
    root.after(0, lambda: status_var.set("启动中"))

    cmd = [DUFS_EXE, current_dir, "--port", str(port)] + extra_args

    try:
        dufs_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,  # 捕获标准输出
            stderr=subprocess.PIPE,  # 捕获标准错误输出
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        stdout, stderr = dufs_proc.communicate()  # 获取输出
        if stderr:
            print(f"Error: {stderr.decode()}")  # 打印错误信息到控制台
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("启动失败", str(e)))
        return

    def verify_started():
        global current_state
        for _ in range(20):
            if port_used(port):
                current_state = STATE_RUNNING
                local_url = f"http://{get_local_ip()}:{port}"
                root.after(0, lambda: (
                    status_var.set("运行中"),
                    local_addr_var.set(local_url),
                    public_addr_var.set("查询中…"),
                    get_public_ip_async(public_addr_var)
                ))
                return
            time.sleep(0.2)

        current_state = STATE_STOPPED
        root.after(0, lambda: (
            status_var.set("启动失败"),
            messagebox.showerror("错误", "DUFS 未能成功监听端口")
        ))

    threading.Thread(target=verify_started, daemon=True).start()

# ================= UI =================
root = tk.Tk()
root.title("Dufs 文件服务器")
root.geometry("580x340")
root.resizable(False, False)

if os.path.exists(ICON_PATH):
    root.iconbitmap(ICON_PATH)

status_var = tk.StringVar(value="未启动")
local_addr_var = tk.StringVar(value="-")
public_addr_var = tk.StringVar(value="-")

frame = tk.Frame(root)
frame.pack(padx=15, pady=10, fill="x")

tk.Label(frame, text="共享目录").grid(row=0, column=0, sticky="w")
dir_entry = tk.Entry(frame, width=45)
dir_entry.insert(0, current_dir)
dir_entry.grid(row=0, column=1, padx=5)

def choose_dir():
    global current_dir
    d = filedialog.askdirectory()
    if d:
        current_dir = d
        dir_entry.delete(0, tk.END)
        dir_entry.insert(0, d)

tk.Button(frame, text="浏览", command=choose_dir).grid(row=0, column=2)

tk.Label(frame, text="端口").grid(row=1, column=0, sticky="w")
port_entry = tk.Entry(frame, width=10)
port_entry.insert(0, "5000")
port_entry.grid(row=1, column=1, sticky="w", padx=5)

btns = tk.Frame(root)
btns.pack(pady=10)

tk.Button(btns, text="📁 只读文件服务", width=16,
          command=lambda: start_dufs_async([])).grid(row=0, column=0, padx=5)

tk.Button(btns, text="✏️ 允许全部操作", width=16,
          command=lambda: start_dufs_async(["--allow-all"])).grid(row=0, column=1, padx=5)

tk.Button(btns, text="🔐 启用账号密码", width=16,
          command=lambda: start_dufs_async(["-a", "admin:123456@/:rw"])).grid(row=0, column=2, padx=5)

info = tk.Frame(root)
info.pack()

def copy_text(var):
    root.clipboard_clear()
    root.clipboard_append(var.get())

tk.Label(info, text="状态").grid(row=0, column=0, sticky="e")
tk.Label(info, textvariable=status_var).grid(row=0, column=1, sticky="w")

tk.Label(info, text="内网地址").grid(row=1, column=0, sticky="e")
tk.Label(info, textvariable=local_addr_var).grid(row=1, column=1, sticky="w")
tk.Button(info, text="复制", command=lambda: copy_text(local_addr_var)).grid(row=1, column=2, padx=5)

tk.Label(info, text="外网地址").grid(row=2, column=0, sticky="e")
tk.Label(info, textvariable=public_addr_var).grid(row=2, column=1, sticky="w")
tk.Button(info, text="复制", command=lambda: copy_text(public_addr_var)).grid(row=2, column=2, padx=5)

actions = tk.Frame(root)
actions.pack(pady=10)

tk.Button(actions, text="停止服务", width=16,
          command=stop_dufs).grid(row=0, column=0, padx=6)

tk.Button(actions, text="最小化到托盘", width=16,
          command=lambda: root.withdraw()).grid(row=0, column=1, padx=6)

tk.Button(actions, text="停止服务并退出", width=16,
          command=lambda: exit_app()).grid(row=0, column=2, padx=6)

# ================= 托盘 =================
def exit_app(icon=None, item=None):
    stop_dufs()
    if tray_icon:
        tray_icon.stop()
    root.after(0, root.destroy)
    os._exit(0)

def create_tray():
    global tray_icon
    image = Image.open(ICON_PATH)

    menu = pystray.Menu(
        pystray.MenuItem("显示界面", lambda *_: root.after(0, root.deiconify)),
        pystray.MenuItem("只读服务", lambda *_: start_dufs_async([])),
        pystray.MenuItem("完全访问", lambda *_: start_dufs_async(["--allow-all"])),
        pystray.MenuItem("账号密码", lambda *_: start_dufs_async(["--auth", "admin:123456"])),
        pystray.MenuItem("停止服务", lambda *_: stop_dufs()),
        pystray.MenuItem("退出程序", exit_app)
    )

    tray_icon = pystray.Icon("dufs", image, "Dufs 文件服务器", menu)
    tray_icon.run()

def on_close():
    root.withdraw()

root.protocol("WM_DELETE_WINDOW", on_close)

threading.Thread(target=create_tray, daemon=True).start()
root.mainloop()
########################################################