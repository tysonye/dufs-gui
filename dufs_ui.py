import os
import sys
import socket
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import pystray
from PIL import Image

# ===================== 基础配置 =====================
DEFAULT_PORT = "5000"
SERVE_DIR = None
dufs_process = None
tray_icon = None

# ===================== 路径处理（兼容 PyInstaller） =====================
def resource_path(rel):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.abspath("."), rel)

DUFS_EXE = resource_path("dufs.exe")
ICON_PATH = resource_path("icon.ico")

# ===================== IP 获取（加速版） =====================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "未知"

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=2).text
    except:
        return "获取失败"

# ===================== Dufs 控制 =====================
def start_dufs(args, success_msg):
    global dufs_process

    if not SERVE_DIR or not os.path.isdir(SERVE_DIR):
        messagebox.showerror("错误", "请先选择共享目录")
        return

    stop_dufs_fast()

    try:
        dufs_process = subprocess.Popen(
            [DUFS_EXE] + args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        status_var.set("● 运行中")
        show_start_info_async(success_msg)
    except Exception as e:
        messagebox.showerror("启动失败", str(e))
        status_var.set("● 已停止")

def stop_dufs_fast():
    global dufs_process
    if dufs_process and dufs_process.poll() is None:
        try:
            dufs_process.kill()
        except:
            pass
    dufs_process = None
    status_var.set("● 已停止")

# ===================== 异步启动提示 =====================
def show_start_info_async(msg):
    def worker():
        local_ip = get_local_ip()
        public_ip = get_public_ip()
        root.after(0, lambda: messagebox.showinfo(
            "服务已启动",
            f"{msg}\n\n"
            f"本机：http://127.0.0.1:{DEFAULT_PORT}\n"
            f"内网：http://{local_ip}:{DEFAULT_PORT}\n"
            f"外网 IP：{public_ip}"
        ))
    threading.Thread(target=worker, daemon=True).start()

# ===================== 目录选择 =====================
def choose_dir():
    global SERVE_DIR
    path = filedialog.askdirectory()
    if path:
        SERVE_DIR = path
        dir_label.config(text=SERVE_DIR)

# ===================== UI 操作 =====================
def run_readonly():
    start_dufs(["serve", SERVE_DIR, "--port", DEFAULT_PORT], "已启动只读文件服务")

def run_all():
    start_dufs(["serve", SERVE_DIR, "--port", DEFAULT_PORT, "--allow-all"], "已启动可写文件服务")

def run_auth():
    start_dufs(
        ["serve", SERVE_DIR, "--port", DEFAULT_PORT, "--auth", "admin:123456"],
        "账号：admin / 123456"
    )

# ===================== 托盘 =====================
def tray_action(func):
    threading.Thread(target=func, daemon=True).start()

def show_window(icon=None, item=None):
    root.after(0, root.deiconify)

def exit_app(icon=None, item=None):
    stop_dufs_fast()
    if tray_icon:
        tray_icon.stop()
    root.destroy()
    os._exit(0)

def setup_tray():
    global tray_icon
    image = Image.open(ICON_PATH)
    menu = pystray.Menu(
        pystray.MenuItem("显示界面", show_window),
        pystray.MenuItem("只读服务", lambda: tray_action(run_readonly)),
        pystray.MenuItem("允许写入", lambda: tray_action(run_all)),
        pystray.MenuItem("账号密码", lambda: tray_action(run_auth)),
        pystray.MenuItem("停止服务", lambda: tray_action(stop_dufs_fast)),
        pystray.MenuItem("退出", exit_app)
    )
    tray_icon = pystray.Icon("dufs", image, "Dufs 文件服务器", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

def minimize_to_tray():
    root.withdraw()

# ===================== 关闭处理 =====================
def on_close():
    minimize_to_tray()

# ===================== UI =====================
root = tk.Tk()
root.title("Dufs 文件服务器（中文可视化界面）")
root.geometry("520x520")
root.protocol("WM_DELETE_WINDOW", on_close)

status_var = tk.StringVar(value="● 已停止")

tk.Label(root, text="Dufs 文件服务器控制面板", font=("微软雅黑", 16, "bold")).pack(pady=10)
tk.Label(root, textvariable=status_var, fg="green").pack()

tk.Button(root, text="选择共享目录", width=30, command=choose_dir).pack(pady=10)
dir_label = tk.Label(root, text="未选择共享目录", fg="blue")
dir_label.pack()

tk.Button(root, text="📁 只读文件服务", width=30, command=lambda: tray_action(run_readonly)).pack(pady=5)
tk.Button(root, text="✏️ 允许全部操作", width=30, command=lambda: tray_action(run_all)).pack(pady=5)
tk.Button(root, text="🔐 启用账号密码", width=30, command=lambda: tray_action(run_auth)).pack(pady=5)
tk.Button(root, text="⛔ 停止文件服务", width=30, command=lambda: tray_action(stop_dufs_fast)).pack(pady=5)
tk.Button(root, text="🧲 最小化到托盘", width=30, command=minimize_to_tray).pack(pady=15)
tk.Button(root, text="❌ 停止并退出", width=30, command=exit_app).pack()

setup_tray()
root.mainloop()
