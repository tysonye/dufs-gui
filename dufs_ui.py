import os
import sys
import socket
import time
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests

# ===============================
# 基础路径
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
DUFS_EXE = os.path.join(BASE_DIR, "dufs.exe")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")

# ===============================
# ===== 来自 dufs_ui启动.py 的服务内核（原样逻辑）
# ===============================
dufs_proc = None
current_dir = ""
port_entry = None

UNSAFE_PORTS = set(range(6660, 6670)) | {21, 22, 25, 10080, 31337}


def try_bind(port: int) -> bool:
    if port in UNSAFE_PORTS:
        return False
    s = socket.socket()
    try:
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def find_port(start: int, max_try=30) -> int:
    port = start
    for _ in range(max_try):
        if try_bind(port):
            return port
        port += 1
    raise RuntimeError("未找到可用端口")


def wait_http(port: int, timeout=3) -> bool:
    end = time.time() + timeout
    url = f"http://127.0.0.1:{port}"
    while time.time() < end:
        try:
            r = requests.get(url, timeout=0.5)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def stop_dufs():
    global dufs_proc
    if dufs_proc and dufs_proc.poll() is None:
        dufs_proc.terminate()
        try:
            dufs_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            dufs_proc.kill()
    dufs_proc = None


def start_dufs_async(extra_args):
    threading.Thread(target=start_dufs, args=(extra_args,), daemon=True).start()


def start_dufs(extra_args):
    global dufs_proc
    stop_dufs()

    port = int(port_entry.get())
    port = find_port(port)

    cmd = [
        DUFS_EXE,
        current_dir,
        "--port",
        str(port)
    ] + extra_args

    dufs_proc = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )

    if not wait_http(port):
        stop_dufs()
        raise RuntimeError("DUFS 启动失败")

    port_entry.set(port)


# ===============================
# ===== UI 层（来自原 dufs_ui.py）
# ===============================
class DummyPort:
    """用于桥接 UI port_var 给启动内核"""
    def __init__(self, tk_var):
        self.var = tk_var

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(str(v))


class DufsUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DUFS 文件共享")
        self.root.geometry("640x420")
        self.root.resizable(False, False)

        if os.path.exists(ICON_PATH):
            self.root.iconbitmap(ICON_PATH)

        self.running = False

        self.dir_var = tk.StringVar()
        self.port_var = tk.StringVar(value="5000")
        self.mode_var = tk.StringVar(value="只读共享")

        self.build_ui()

    # ---------- UI ----------
    def build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        # 目录 + 端口
        row1 = ttk.Frame(main)
        row1.pack(fill="x", pady=5)

        ttk.Label(row1, text="共享目录").pack(side="left")
        ttk.Entry(row1, textvariable=self.dir_var, width=42).pack(side="left", padx=5)
        ttk.Button(row1, text="浏览", command=self.choose_dir).pack(side="left")

        ttk.Label(row1, text="端口").pack(side="left", padx=(10, 2))
        ttk.Entry(row1, textvariable=self.port_var, width=8).pack(side="left")

        # 模式 + 启动
        row2 = ttk.Frame(main)
        row2.pack(fill="x", pady=10)

        ttk.Label(row2, text="共享模式").pack(side="left")
        ttk.Combobox(
            row2,
            textvariable=self.mode_var,
            values=["只读共享", "可编辑共享", "账号密码共享"],
            state="readonly",
            width=16
        ).pack(side="left", padx=5)

        self.main_btn = ttk.Button(row2, text="启动服务", command=self.toggle_service)
        self.main_btn.pack(side="left", padx=15)

        # 地址显示
        self.addr_frame = ttk.LabelFrame(main, text="访问地址", padding=10)
        self.addr_frame.pack(fill="x", pady=10)
        self.addr_frame.pack_forget()

        self.lan_var = tk.StringVar()
        self.wan_var = tk.StringVar()

        self.addr_row("内网地址", self.lan_var).pack(fill="x", pady=2)
        self.addr_row("外网地址", self.wan_var).pack(fill="x", pady=2)

        # 底部
        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=10)

        ttk.Button(bottom, text="退出", command=self.exit_app).pack(side="right")

    def addr_row(self, label, var):
        f = ttk.Frame(self.addr_frame)
        ttk.Label(f, text=label, width=8).pack(side="left")
        e = ttk.Entry(f, textvariable=var, state="readonly")
        e.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(f, text="复制", command=lambda: self.copy(var.get())).pack(side="left")
        return f

    # ---------- 行为 ----------
    def choose_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.dir_var.set(d)

    def toggle_service(self):
        if not self.running:
            self.start_service()
        else:
            self.stop_service()

    def start_service(self):
        global current_dir, port_entry
        if not self.dir_var.get():
            messagebox.showwarning("提示", "请选择共享目录")
            return

        current_dir = self.dir_var.get()
        port_entry = DummyPort(self.port_var)

        mode = self.mode_var.get()
        args = []

        if mode == "可编辑共享":
            args = ["--allow-all"]
        elif mode == "账号密码共享":
            args = ["-a", "admin:123456@/:rw"]

        try:
            start_dufs_async(args)
        except Exception as e:
            messagebox.showerror("错误", str(e))
            return

        self.running = True
        self.main_btn.config(text="停止服务")
        self.update_addr()
        self.addr_frame.pack(fill="x", pady=10)

    def stop_service(self):
        stop_dufs()
        self.running = False
        self.main_btn.config(text="启动服务")
        self.addr_frame.pack_forget()

    def update_addr(self):
        port = self.port_var.get()
        self.lan_var.set(f"http://{self.get_lan_ip()}:{port}")
        threading.Thread(target=self.update_wan, daemon=True).start()

    def update_wan(self):
        try:
            ip = requests.get("https://api.ipify.org", timeout=3).text
            self.wan_var.set(f"http://{ip}:{self.port_var.get()}")
        except Exception:
            self.wan_var.set("获取失败")

    def get_lan_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    def copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def exit_app(self):
        stop_dufs()
        self.root.destroy()


# ===============================
# 入口
# ===============================
if __name__ == "__main__":
    root = tk.Tk()
    app = DufsUI(root)
    root.mainloop()
