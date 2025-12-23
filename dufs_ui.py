import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import socket
import time
import os
import sys
import urllib.request

# ========================
# 全局状态
# ========================
STATE_STOPPED = "STOPPED"
STATE_STARTING = "STARTING"
STATE_RUNNING = "RUNNING"

current_state = STATE_STOPPED
dufs_proc = None

SERVE_DIR = os.getcwd()
PORT = 5000
USE_AUTH = False

# ========================
# 工具函数
# ========================
def is_port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except:
        return False

def wait_port_release(port, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        if not is_port_open(port):
            return True
        time.sleep(0.1)
    return False

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_wan_ip_async(callback):
    def run():
        try:
            ip = urllib.request.urlopen("https://api.ipify.org", timeout=3).read().decode()
        except:
            ip = "获取失败"
        callback(ip)
    threading.Thread(target=run, daemon=True).start()

# ========================
# DUFS 控制
# ========================
def stop_dufs():
    global dufs_proc, current_state
    if dufs_proc and dufs_proc.poll() is None:
        dufs_proc.kill()
        dufs_proc.wait()
    dufs_proc = None
    current_state = STATE_STOPPED
    update_status()

def start_dufs():
    global dufs_proc, current_state

    current_state = STATE_STARTING
    update_status()

    stop_dufs()
    wait_port_release(PORT)

    cmd = ["dufs.exe", SERVE_DIR, "--port", str(PORT)]
    if USE_AUTH:
        cmd += ["--auth", "admin:123456"]

    try:
        dufs_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        messagebox.showerror("启动失败", str(e))
        current_state = STATE_STOPPED
        update_status()
        return

    # 验证是否真正启动
    def verify():
        global current_state
        for _ in range(20):
            if is_port_open(PORT):
                current_state = STATE_RUNNING
                update_status()
                show_addresses()
                return
            time.sleep(0.2)
        current_state = STATE_STOPPED
        update_status()
        messagebox.showerror("启动失败", "DUFS 未监听端口")

    threading.Thread(target=verify, daemon=True).start()

# ========================
# UI 更新
# ========================
def update_status():
    if current_state == STATE_RUNNING:
        status_var.set("🟢 运行中")
    elif current_state == STATE_STARTING:
        status_var.set("🟡 启动中")
    else:
        status_var.set("🔴 已停止")

def show_addresses():
    lan = f"http://{get_lan_ip()}:{PORT}"
    lan_var.set(lan)

    def set_wan(ip):
        wan_var.set(f"http://{ip}:{PORT}")

    get_wan_ip_async(set_wan)

# ========================
# UI 操作
# ========================
def choose_dir():
    global SERVE_DIR
    d = filedialog.askdirectory()
    if d:
        SERVE_DIR = d
        dir_var.set(d)

def toggle_auth():
    global USE_AUTH
    USE_AUTH = not USE_AUTH
    auth_btn.config(text="启用账号密码" if not USE_AUTH else "关闭账号密码")

# ========================
# Tk UI（冷启动）
# ========================
root = tk.Tk()
root.title("Dufs 文件服务器")

dir_var = tk.StringVar(value=SERVE_DIR)
status_var = tk.StringVar(value="🔴 已停止")
lan_var = tk.StringVar(value="-")
wan_var = tk.StringVar(value="-")

tk.Label(root, text="共享目录").grid(row=0, column=0, sticky="e")
tk.Entry(root, textvariable=dir_var, width=40).grid(row=0, column=1)
tk.Button(root, text="选择", command=choose_dir).grid(row=0, column=2)

tk.Label(root, text="服务状态").grid(row=1, column=0, sticky="e")
tk.Label(root, textvariable=status_var).grid(row=1, column=1, sticky="w")

tk.Label(root, text="内网地址").grid(row=2, column=0, sticky="e")
tk.Entry(root, textvariable=lan_var, width=40).grid(row=2, column=1)

tk.Label(root, text="外网地址").grid(row=3, column=0, sticky="e")
tk.Entry(root, textvariable=wan_var, width=40).grid(row=3, column=1)

tk.Button(root, text="启动服务", command=start_dufs).grid(row=4, column=0)
tk.Button(root, text="停止服务", command=stop_dufs).grid(row=4, column=1)
auth_btn = tk.Button(root, text="启用账号密码", command=toggle_auth)
auth_btn.grid(row=4, column=2)

# ========================
# 退出清理
# ========================
def on_exit():
    stop_dufs()
    root.destroy()
    os._exit(0)

root.protocol("WM_DELETE_WINDOW", on_exit)

# ========================
# 延迟托盘（热启动）
# ========================
def start_tray_later():
    time.sleep(0.5)
    try:
        import pystray
        from PIL import Image

        icon = Image.open("icon.ico")
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", lambda: root.after(0, root.deiconify)),
            pystray.MenuItem("启动服务", lambda: start_dufs()),
            pystray.MenuItem("停止服务", lambda: stop_dufs()),
            pystray.MenuItem("退出", lambda: on_exit())
        )
        tray = pystray.Icon("dufs", icon, "Dufs 文件服务器", menu)
        tray.run()
    except:
        pass

threading.Thread(target=start_tray_later, daemon=True).start()

root.mainloop()
