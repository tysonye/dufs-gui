current_args = None
import os
import sys
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import pystray
import requests
import time



# ========================
# PyInstaller 资源路径
# ========================
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ========================
# 基础配置
# ========================
DUFS_EXE = resource_path("dufs.exe")
ICON_PATH = resource_path("icon.ico")
DEFAULT_PORT = "5000"

dufs_process = None
serve_dir = ""
tray_icon = None

# ========================
# IP 获取
# ========================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=3).text
    except Exception:
        return "无法获取"

# ========================
# dufs 控制（★重点修复）
# ========================
def start_dufs(args, success_msg):
    global dufs_process, current_args

    if not serve_dir:
        messagebox.showwarning("提示", "请先选择共享目录")
        return

    # ★ 如果服务正在运行
    if dufs_process and dufs_process.poll() is None:
        # 如果参数一样，直接提示
        if args == current_args:
            messagebox.showinfo("提示", "服务已在当前模式运行")
            return
        # ★ 否则：自动切换模式（先停再启）
        stop_dufs()
        time.sleep(0.3)

    try:
        dufs_process = subprocess.Popen(
            [DUFS_EXE] + args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        current_args = args.copy()

        time.sleep(0.5)

        local_ip = get_local_ip()
        public_ip = get_public_ip()

        messagebox.showinfo(
            "启动成功",
            f"{success_msg}\n\n"
            f"内网访问：http://{local_ip}:{DEFAULT_PORT}\n"
            f"本机访问：http://127.0.0.1:{DEFAULT_PORT}\n"
            f"外网 IP：{public_ip}"
        )

        status_var.set("● 运行中")

    except Exception as e:
        messagebox.showerror("启动失败", str(e))


def stop_dufs():
    global dufs_process

    if dufs_process and dufs_process.poll() is None:
        try:
            dufs_process.terminate()
            dufs_process.wait(timeout=3)
        except Exception:
            pass
        finally:
            dufs_process = None
            current_args = None
            status_var.set("● 已停止")
    else:
        dufs_process = None
        current_args = None
        status_var.set("● 已停止")
# ========================
# 强制退出杀进程
# ========================
import subprocess
import os
import signal

def kill_dufs_process():
    global dufs_process

    try:
        subprocess.run(
            ["taskkill", "/T", "/F", "/IM", "dufs.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

    dufs_process = None


    # ★ 双保险：按进程名强杀（解决所有残留）
    try:
        subprocess.run(
            ["taskkill", "/T" "/F", "/IM", "dufs.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

    dufs_process = None

# ========================
# UI / 托盘协同
# ========================
def show_window():
    root.deiconify()
    root.after(0, root.lift)

def exit_all():
    stop_dufs()
    if tray_icon:
        tray_icon.stop()
    root.destroy()
    os._exit(0)   # ★ 强制退出，保证没有残留进程

# ========================
# 托盘
# ========================
def setup_tray():
    global tray_icon

    image = Image.open(ICON_PATH)

    tray_icon = pystray.Icon(
        "dufs",
        image,
        "Dufs 文件服务器",
        menu=pystray.Menu(
            pystray.MenuItem("恢复窗口", lambda: root.after(0, show_window)),
            pystray.MenuItem("启动只读服务", lambda: root.after(
                0, lambda: start_dufs(
                    [serve_dir, "--port", DEFAULT_PORT],
                    "已启动只读文件服务"
                ))),
            pystray.MenuItem("启动可写服务", lambda: root.after(
                0, lambda: start_dufs(
                    [serve_dir, "--port", DEFAULT_PORT, "--allow-all"],
                    "已启动可写文件服务"
                ))),
            pystray.MenuItem("账号密码模式", lambda: root.after(
                0, lambda: start_dufs(
                    [serve_dir, "--port", DEFAULT_PORT, "--auth", "admin:123456"],
                    "账号：admin / 123456"
                ))),
            pystray.MenuItem("停止服务", lambda: root.after(0, stop_dufs)),
            pystray.MenuItem("退出", lambda: root.after(0, exit_all))
        )
    )

    tray_icon.run()

# ========================
# 主窗口（完全保留你的样式）
# ========================
root = tk.Tk()
def on_close():
    if messagebox.askyesno("退出", "确定退出并停止服务吗？"):
        kill_dufs_process()
        try:
            tray_icon.stop()
        except Exception:
            pass
        root.destroy()
        os._exit(0)   # ★ 这一行必须要

root.protocol("WM_DELETE_WINDOW", on_close)

root.title("Dufs 文件服务器（中文可视化界面）")
root.geometry("460x540")
root.resizable(False, False)



tk.Label(root, text="Dufs 文件服务器控制面板", font=("微软雅黑", 16, "bold")).pack(pady=10)

status_var = tk.StringVar(value="● 已停止")
tk.Label(root, textvariable=status_var, fg="green").pack()

def choose_dir():
    global serve_dir
    serve_dir = filedialog.askdirectory()
    if serve_dir:
        dir_label.config(text=serve_dir)

tk.Button(root, text="选择共享目录", width=30, command=choose_dir).pack(pady=10)
dir_label = tk.Label(root, text="未选择共享目录", fg="blue")
dir_label.pack()

tk.Button(root, text="📁 只读文件服务", width=30,
          command=lambda: start_dufs(
    [serve_dir, "--port", DEFAULT_PORT],
    "已启动只读文件服务"
)).pack(pady=5)

tk.Button(root, text="✏️ 允许全部操作", width=30,
          command=lambda: start_dufs(
    [serve_dir, "--port", DEFAULT_PORT, "--allow-all"],
    "已启动可写文件服务"
)
).pack(pady=5)

tk.Button(root, text="🔐 启用账号密码", width=30,
          command=lambda: start_dufs(
    [serve_dir, "--port", DEFAULT_PORT, "--auth", "admin:123456"],
    "账号：admin / 123456"
)
).pack(pady=5)

tk.Button(root, text="⛔ 停止文件服务", width=30, command=stop_dufs).pack(pady=10)
tk.Button(root, text="🧲 最小化到托盘", width=30, command=root.withdraw).pack(pady=5)
tk.Button(root, text="❌ 停止并退出", width=30, command=exit_all).pack(pady=10)

# ========================
# 启动托盘线程
# ========================
threading.Thread(target=setup_tray, daemon=True).start()

root.mainloop()
