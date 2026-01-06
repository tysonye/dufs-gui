import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import subprocess
import os
import threading
import time
import socket
import requests
import webbrowser
from PIL import Image, ImageTk
import sys
import queue

class DufsService:
    """单个Dufs服务实例"""
    def __init__(self, name="默认服务", serve_path=".", port="5000", bind=""):
        self.name = name
        self.serve_path = serve_path
        self.port = port
        self.bind = bind
        
        # 权限设置
        self.allow_all = False
        self.allow_upload = False
        self.allow_delete = False
        self.allow_search = False
        self.allow_symlink = False
        self.allow_archive = False
        
        # 多用户权限规则
        self.auth_rules = []
        
        # 进程信息
        self.process = None
        self.status = "未运行"
        
        # 访问地址
        self.local_addr = ""

class DufsServiceDialog:
    """服务配置对话框"""
    def __init__(self, parent, service=None, edit_index=None, on_save=None):
        self.parent = parent
        self.service = service
        self.edit_index = edit_index
        self.on_save = on_save
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑服务" if service else "添加服务")
        self.dialog.geometry("700x600")
        self.dialog.resizable(True, True)
        
        # 窗口保持在最前面
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建笔记本组件
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        
        # 只创建一个综合设置标签页
        self.create_main_tab()
        
        # 按钮框架
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 确定按钮
        ttk.Button(button_frame, text="确定", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        
        # 取消按钮
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def create_main_tab(self):
        """创建综合设置标签页"""
        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="服务设置")
        
        # ========== 基本设置 ==========
        basic_frame = ttk.LabelFrame(main_tab, text="基本设置", padding="10")
        basic_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=20, pady=10, columnspan=2)
        
        # 配置列权重
        basic_frame.columnconfigure(1, weight=1)
        
        # 服务名称
        ttk.Label(basic_frame, text="服务名称: ").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self.name_var = tk.StringVar(value=self.service.name if self.service else "新服务")
        ttk.Entry(basic_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=10)
        
        # 服务路径
        ttk.Label(basic_frame, text="服务路径: ").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        path_frame = ttk.Frame(basic_frame)
        path_frame.grid(row=1, column=1, sticky=tk.W, pady=10)
        self.serve_path_var = tk.StringVar(value=self.service.serve_path if self.service else ".")
        ttk.Entry(path_frame, textvariable=self.serve_path_var, width=30).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Button(path_frame, text="浏览", command=self.browse_path).grid(row=0, column=1)
        
        # 端口
        ttk.Label(basic_frame, text="端口: ").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        self.port_var = tk.StringVar(value=self.service.port if self.service else "5000")
        ttk.Entry(basic_frame, textvariable=self.port_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=10)
        
        # ========== 权限设置 ==========
        perm_frame = ttk.LabelFrame(main_tab, text="权限设置", padding="10")
        perm_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=20, pady=10, columnspan=2)
        
        # 配置列权重
        perm_frame.columnconfigure(1, weight=1)
        
        # 全选（替代原来的允许所有操作）
        self.allow_all_var = tk.BooleanVar(value=self.service.allow_all if self.service else False)
        
        def on_select_all():
            """全选/取消全选逻辑"""
            value = self.allow_all_var.get()
            self.allow_upload_var.set(value)
            self.allow_delete_var.set(value)
            self.allow_search_var.set(value)
        
        def on_perm_change():
            """权限变化时的逻辑"""
            # 当所有权限都勾选时，自动勾选全选
            if self.allow_upload_var.get() and self.allow_delete_var.get() and self.allow_search_var.get():
                self.allow_all_var.set(True)
            else:
                self.allow_all_var.set(False)
        
        ttk.Checkbutton(perm_frame, text="全选", variable=self.allow_all_var, command=on_select_all).grid(row=0, column=0, sticky=tk.W, padx=10, pady=10, columnspan=2)
        
        # 允许上传
        self.allow_upload_var = tk.BooleanVar(value=self.service.allow_upload if self.service else False)
        ttk.Checkbutton(perm_frame, text="允许上传", variable=self.allow_upload_var, command=on_perm_change).grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        
        # 允许删除
        self.allow_delete_var = tk.BooleanVar(value=self.service.allow_delete if self.service else False)
        ttk.Checkbutton(perm_frame, text="允许删除", variable=self.allow_delete_var, command=on_perm_change).grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # 允许搜索
        self.allow_search_var = tk.BooleanVar(value=self.service.allow_search if self.service else False)
        ttk.Checkbutton(perm_frame, text="允许搜索", variable=self.allow_search_var, command=on_perm_change).grid(row=2, column=0, sticky=tk.W, padx=10, pady=5, columnspan=2)
        
        # ========== 认证设置 ==========
        auth_frame = ttk.LabelFrame(main_tab, text="认证设置", padding="10")
        auth_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=20, pady=10, columnspan=2)
        
        # 配置列权重
        auth_frame.columnconfigure(1, weight=1)
        auth_frame.columnconfigure(3, weight=1)
        
        # 用户名
        ttk.Label(auth_frame, text="用户名: ").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        if self.service and self.service.auth_rules:
            default_username = self.service.auth_rules[0].get("username", "")
            default_password = self.service.auth_rules[0].get("password", "")
        else:
            default_username = ""
            default_password = ""
        self.username_var = tk.StringVar(value=default_username)
        ttk.Entry(auth_frame, textvariable=self.username_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 密码
        ttk.Label(auth_frame, text="密码: ").grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)
        self.password_var = tk.StringVar(value=default_password)
        ttk.Entry(auth_frame, textvariable=self.password_var, width=20, show="*").grid(row=0, column=3, sticky=tk.W, pady=5, padx=5)
        
        # 提示信息
        ttk.Label(auth_frame, text="提示: 留空表示不启用认证", foreground="gray").grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=10, pady=5)
    
    def browse_path(self):
        """浏览服务路径"""
        path = filedialog.askdirectory()
        if path:
            self.serve_path_var.set(path)
    
    def on_ok(self):
        """保存服务配置"""
        # 先释放对话框的焦点，确保所有 messagebox 都能获得焦点
        self.dialog.grab_release()
        
        name = self.name_var.get().strip()
        serve_path = self.serve_path_var.get().strip()
        port = self.port_var.get().strip()
        
        if not name:
            messagebox.showerror("错误", "服务名称不能为空")
            return
        
        if not serve_path:
            messagebox.showerror("错误", "服务路径不能为空")
            return
        
        if not port.isdigit():
            messagebox.showerror("错误", "端口必须是数字")
            return
        
        # 权限设置
        allow_all = self.allow_all_var.get()
        allow_upload = self.allow_upload_var.get()
        allow_delete = self.allow_delete_var.get()
        allow_search = self.allow_search_var.get()
        allow_symlink = False  # 移除了该选项，默认禁用
        allow_archive = True  # 移除了该选项，默认启用
        
        # 认证设置（简化为单个用户名密码）
        auth_rules = []
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if username and password:
            # 验证用户名密码格式和长度
            if len(username) < 3 or len(username) > 20:
                messagebox.showerror("错误", "用户名长度必须在3-20个字符之间")
                return
            if len(password) < 6 or len(password) > 20:
                messagebox.showerror("错误", "密码长度必须在6-20个字符之间")
                return
            if not any(c.isalpha() for c in username):
                messagebox.showerror("错误", "用户名必须包含至少一个字母")
                return
            if not any(c.isalpha() for c in password):
                messagebox.showerror("错误", "密码必须包含至少一个字母")
                return
            
            # 创建单个认证规则，应用到根路径
            auth_rules.append({
                "username": username,
                "password": password,
                "paths": [("/", "rw")]  # 根路径，读写权限
            })
        
        # 创建服务实例
        service = DufsService(name=name, serve_path=serve_path, port=port, bind="")
        service.allow_all = allow_all
        service.allow_upload = allow_upload
        service.allow_delete = allow_delete
        service.allow_search = allow_search
        service.allow_symlink = allow_symlink
        service.allow_archive = allow_archive
        service.auth_rules = auth_rules
        
        # 调用保存回调
        if self.on_save:
            # 调用保存回调
            self.on_save(service, self.edit_index)
        
        # 关闭对话框
        self.dialog.destroy()

class DufsMultiGUI:
    """Dufs多服务GUI主程序"""
    def __init__(self, root):
        self.root = root
        self.root.title("Dufs多服务管理")
        
        # 设置窗口大小，更大的窗口尺寸，更大气
        window_width = 900
        window_height = 600
        self.root.geometry(f"{window_width}x{window_height}")
        
        # 计算居中位置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
        
        # 设置窗口位置
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 设置现代化主题
        self.set_modern_theme()
        
        # 设置字体
        self.root.option_add("*Font", ("Segoe UI", 10))
        
        # 服务列表
        self.services = []
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置列权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # 服务列表框架
        list_frame = ttk.LabelFrame(main_frame, text="服务列表", padding="10")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # 配置列表框架列权重
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 服务列表，增加账户、权限列
        self.service_list = ttk.Treeview(list_frame, columns=("name", "port", "status", "auth", "perms", "path"), show="headings")
        self.service_list.heading("name", text="服务名称")
        self.service_list.heading("port", text="端口")
        self.service_list.heading("status", text="状态")
        self.service_list.heading("auth", text="认证")
        self.service_list.heading("perms", text="权限")
        self.service_list.heading("path", text="服务路径")
        
        # 设置列宽，优化显示效果，适应700px窗口
        self.service_list.column("name", width=90, minwidth=70, stretch=tk.NO)  # 服务名称列
        self.service_list.column("port", width=50, anchor=tk.CENTER, stretch=tk.NO)  # 端口列
        self.service_list.column("status", width=60, anchor=tk.CENTER, stretch=tk.NO)  # 状态列
        self.service_list.column("auth", width=90, anchor=tk.CENTER, stretch=tk.YES)  # 认证列，自适应宽度
        self.service_list.column("perms", width=110, anchor=tk.CENTER, stretch=tk.NO)  # 权限列
        self.service_list.column("path", width=170, minwidth=100, stretch=tk.YES)  # 路径列，利用截断和悬停提示，设置较小宽度
        
        # 滚动条
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.service_list.yview)
        list_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S), pady=5)
        self.service_list.config(yscrollcommand=list_scrollbar.set)
        
        # 添加服务列表到框架
        self.service_list.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 创建字典来存储完整的认证信息和路径，用于悬停提示
        self.full_auth_info = {}
        self.full_path_info = {}
        
        # 创建提示框
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip_label = ttk.Label(self.tooltip, text="", background="yellow", relief="solid", borderwidth=1, padding=2)
        self.tooltip_label.pack()
        
        # 绑定鼠标事件
        self.service_list.bind("<Motion>", self.on_motion)
        self.service_list.bind("<Leave>", self.on_leave)
        
        # 添加选中事件监听器
        self.service_list.bind("<<TreeviewSelect>>", lambda event: self.on_service_selected())
        
        # 添加双击事件监听器，用于直接编辑服务
        self.service_list.bind("<Double-1>", lambda event: self.edit_service())
        
        # 创建右键菜单
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="浏览器访问", command=self.browser_access)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制账户", command=lambda: self.copy_account())
        self.context_menu.add_command(label="复制密码", command=lambda: self.copy_password())
        self.context_menu.add_separator()
        self.context_menu.add_command(label="启动服务", command=self.start_service)
        self.context_menu.add_command(label="停止服务", command=self.stop_service)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="编辑服务", command=self.edit_service)
        self.context_menu.add_command(label="删除服务", command=self.delete_service)
        
        # 绑定右键菜单
        self.service_list.bind("<Button-3>", self.show_context_menu)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 配置按钮框架列权重，使按钮分布更均匀
        for i in range(7):
            button_frame.columnconfigure(i, weight=1)
        
        # 添加服务按钮
        ttk.Button(button_frame, text="添加服务", command=self.add_service).grid(row=0, column=0, padx=5, sticky=tk.W)
        
        # 编辑服务按钮
        ttk.Button(button_frame, text="编辑服务", command=self.edit_service).grid(row=0, column=1, padx=5, sticky=tk.W)
        
        # 删除服务按钮
        ttk.Button(button_frame, text="删除服务", command=self.delete_service).grid(row=0, column=2, padx=5, sticky=tk.W)
        
        # 启动服务按钮
        ttk.Button(button_frame, text="启动服务", command=self.start_service).grid(row=0, column=3, padx=5, sticky=tk.E)
        
        # 停止服务按钮
        ttk.Button(button_frame, text="停止服务", command=self.stop_service).grid(row=0, column=4, padx=5, sticky=tk.E)
        
        # 关闭程序按钮
        ttk.Button(button_frame, text="关闭程序", command=self.on_exit).grid(row=0, column=5, padx=5, sticky=tk.E)
        
        # 地址显示框架
        address_frame = ttk.LabelFrame(main_frame, text="访问地址", padding="10")
        address_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 配置地址框架列权重
        address_frame.columnconfigure(1, weight=1)
        
        # 局域网地址
        ttk.Label(address_frame, text="访问地址: ").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.local_addr_var = tk.StringVar(value="")
        ttk.Entry(address_frame, textvariable=self.local_addr_var, state="readonly").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(address_frame, text="复制", command=lambda: self.copy_address(self.local_addr_var.get())).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(address_frame, text="浏览器访问", command=self.browser_access).grid(row=0, column=3, padx=5, pady=5)
        
        # 初始化服务列表
        self.update_service_list()
        
        # 创建事件队列，用于在不同线程之间传递事件
        self.event_queue = queue.Queue()
        
        # 添加窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # 初始化系统托盘
        self.create_tray_icon()
        
        # 启动事件处理循环
        self.process_events()
    
    def add_service(self):
        """添加新服务"""
        def on_save(service, _):
            self.services.append(service)
            self.update_service_list()
        
        dialog = DufsServiceDialog(self.root, on_save=on_save)
    
    def edit_service(self):
        """编辑选中的服务"""
        selected = self.service_list.selection()
        if selected:
            index = int(selected[0])
            service = self.services[index]
            
            # 保存服务当前状态（是否运行中）
            was_running = service.status == "运行中"
            
            def on_save(new_service, edit_index):
                # 如果服务正在运行，先停止
                if was_running:
                    self.stop_service(edit_index)
                
                # 更新服务
                self.services[edit_index] = new_service
                self.update_service_list()
                
                # 如果服务之前是运行中的，询问是否重新启动
                if was_running:
                    if messagebox.askyesno("提示", "服务已更新，是否重新启动服务？"):
                        self.start_service(edit_index)
            
            dialog = DufsServiceDialog(self.root, service=service, edit_index=index, on_save=on_save)
        else:
            messagebox.showinfo("提示", "请先选择要编辑的服务")
    
    def delete_service(self):
        """删除选中的服务"""
        selected = self.service_list.selection()
        if selected:
            index = int(selected[0])
            service = self.services[index]
            
            # 如果服务正在运行，先停止
            if service.status == "运行中":
                self.stop_service(index)
            
            del self.services[index]
            self.update_service_list()
        else:
            messagebox.showinfo("提示", "请先选择要删除的服务")
    
    def start_service(self, index=None):
        """启动选中的服务"""
        if index is None:
            selected = self.service_list.selection()
            if not selected:
                messagebox.showinfo("提示", "请先选择要启动的服务")
                return
            index = int(selected[0])
        
        service = self.services[index]
        
        # 常用端口列表（需要屏蔽的端口）
        blocked_ports = [
            # 系统保留端口（1-1023）
            80, 443, 22, 21, 23, 53, 135, 137, 138, 139, 445, 1433, 1434, 3389, 1521,
            
            # 常见Web服务器端口
            8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8888, 9090,
            
            # 常见数据库端口
            3306, 5432, 6379, 27017, 11211, 9200, 9300,
            
            # 浏览器屏蔽的高危端口
            6666, 6667, 6668, 6669, 6697, 10808, 10809, 10810,
            
            # 常见开发服务器端口
            3000, 3001, 4000, 4001, 5000, 5001, 6000, 6001, 7000, 7001, 9000, 9001,
            
            # 常见代理和P2P端口
            1080, 8080, 8081, 3128, 10808,
            
            # 常见木马和恶意软件端口
            4444, 5555, 6666, 7777, 8888, 9999, 12345, 12346, 12347, 16992, 16993
        ]
        
        # 尝试获取可用端口，最多尝试20次
        original_port = int(service.port.strip())
        available_port = None
        used_ports = []
        
        for i in range(20):
            try_port = original_port + i
            
            # 跳过常用屏蔽端口
            if try_port in blocked_ports:
                used_ports.append(try_port)
                continue
            
            # 检查端口是否可用
            if self.is_port_available(try_port):
                available_port = try_port
                break
            else:
                used_ports.append(try_port)
        
        # 如果找到了可用端口，更新服务端口
        if available_port:
            # 如果端口有变化，更新服务端口
            if available_port != original_port:
                service.port = str(available_port)
                # 更新服务列表显示
                self.update_service_list()
        else:
            # 尝试了20个端口都不可用，提示用户
            messagebox.showerror(
                "错误",
                f"端口 {original_port} 不可用，尝试了20个端口（{original_port}-{original_port+19}）都不可用。\n"
                f"以下端口被占用或屏蔽: {', '.join(map(str, used_ports))}\n"
                "请手动更换端口。"
            )
            return
        
        # 构建命令
        # 使用dufs.exe的完整路径
        dufs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dufs.exe"))
        command = [dufs_path]
        
        # 基本参数，去除多余空白字符
        service_port = str(available_port)
        service_bind = service.bind.strip()
        
        # 添加基本参数（dufs不支持--name参数）
        command.extend(["--port", service_port])
        # 只有当bind不为空时才添加
        if service_bind:
            command.extend(["--bind", service_bind])
        
        # 权限设置
        if service.allow_all:
            command.append("--allow-all")
        else:
            if service.allow_upload:
                command.append("--allow-upload")
            if service.allow_delete:
                command.append("--allow-delete")
            if service.allow_search:
                command.append("--allow-search")
            if service.allow_symlink:
                command.append("--allow-symlink")
            if service.allow_archive:
                command.append("--allow-archive")
        
        # 多用户权限
        if service.auth_rules:
            for rule in service.auth_rules:
                username = rule["username"].strip()
                password = rule["password"].strip()
                
                # 收集该用户的所有路径规则
                path_rules = []
                for path, perm in rule["paths"]:
                    # 修复Windows路径分隔符并去除空白字符
                    fixed_path = path.replace("\\", "/").strip()
                    # 构建单个路径规则（只包含路径，权限通过全局参数控制）
                    path_rules.append(fixed_path)
                
                # 构建完整的auth参数（格式：user:pass@path1,path2）
                auth_rule = f"{username}:{password}@{','.join(path_rules)}"
                command.extend(["--auth", auth_rule])
        
        # 添加服务根目录（dufs.exe [options] [path]）
        command.append(service.serve_path)
        
        # 启动服务
        try:
            # 获取当前工作目录
            current_dir = os.getcwd()
            
            # 调试：打印完整命令和工作目录
            print(f"执行命令: {' '.join(command)}")
            print(f"当前目录: {current_dir}")
            print(f"服务工作目录: {service.serve_path}")
            
            # 检查dufs.exe是否存在
            if not os.path.exists(dufs_path):
                print(f"警告: dufs.exe 不存在于路径 {dufs_path}")
            
            # 启动进程
            service.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏命令窗口
            )
            
            # 等待一小段时间，检查进程是否还在运行（端口冲突会导致进程立即退出）
            time.sleep(1)
            
            # 检查进程是否还在运行
            if service.process.poll() is not None:
                # 进程已退出，说明启动失败
                stdout, stderr = service.process.communicate()
                error_msg = f"启动服务失败: 进程立即退出\n标准输出: {stdout}\n标准错误: {stderr}"
                print(error_msg)
                messagebox.showerror("错误", error_msg)
                service.process = None
                return
            
            # 更新服务状态
            service.status = "运行中"
            
            # 启动监控线程
            threading.Thread(target=self.monitor_service, args=(service, index), daemon=True).start()
            
            # 更新服务列表
            self.update_service_list()
            
            # 更新地址
            self.refresh_address(index)
        except Exception as e:
            # 打印详细错误信息
            error_msg = f"启动服务失败: {str(e)}"
            error_msg += f"\n执行命令: {' '.join(command)}"
            error_msg += f"\n当前目录: {os.getcwd()}"
            error_msg += f"\n服务工作目录: {service.serve_path}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def stop_service(self, index=None):
        """停止选中的服务"""
        if index is None:
            selected = self.service_list.selection()
            if not selected:
                messagebox.showinfo("提示", "请先选择要停止的服务")
                return
            index = int(selected[0])
        
        service = self.services[index]
        
        if service.process:
            service.process.terminate()
            try:
                service.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service.process.kill()
            
            service.process = None
            service.status = "未运行"
            service.local_addr = ""
            
            # 更新服务列表
            self.update_service_list()
            
            # 清空地址显示
            self.local_addr_var.set("")
    
    def monitor_service(self, service, index):
        """监控服务运行状态"""
        while service.process:
            if service.process.poll() is not None:
                service.status = "未运行"
                service.process = None
                self.update_service_list()
                break
            time.sleep(1)
    
    def update_service_list(self):
        """更新服务列表"""
        # 清空现有列表
        for item in self.service_list.get_children():
            self.service_list.delete(item)
        
        # 添加服务到列表
        for i, service in enumerate(self.services):
            # 格式化认证信息
            auth_info = ""
            full_auth_info = ""
            if service.auth_rules:
                username = service.auth_rules[0].get("username", "")
                password = service.auth_rules[0].get("password", "")
                full_auth_info = f"{username}:{password}"
                # 对过长的认证信息进行截断处理，限制在15个字符以内
                if len(full_auth_info) > 15:
                    auth_info = f"{full_auth_info[:12]}..."
                else:
                    auth_info = full_auth_info
            
            # 格式化权限信息
            perms_info = []
            # 不管是否全选，都显示所有具体权限
            if service.allow_all or service.allow_upload:
                perms_info.append("上传")
            if service.allow_all or service.allow_delete:
                perms_info.append("删除")
            if service.allow_all or service.allow_search:
                perms_info.append("搜索")
            perms_text = ", ".join(perms_info) if perms_info else ""
            
            # 对过长的路径进行截断处理，限制在25个字符以内
            full_path = service.serve_path
            if len(full_path) > 25:
                display_path = f"{full_path[:22]}..."
            else:
                display_path = full_path
            
            # 插入服务项
            self.service_list.insert("", tk.END, iid=i, values=(service.name, service.port, service.status, auth_info, perms_text, display_path))
            
            # 存储完整的认证信息和路径，用于悬停提示
            self.full_auth_info[i] = full_auth_info
            self.full_path_info[i] = full_path
    
    def refresh_address(self, index=None, show_error=True):
        """刷新服务访问地址
        
        Args:
            index: 服务索引
            show_error: 是否显示错误提示
        """
        if index is None:
            selected = self.service_list.selection()
            if not selected:
                messagebox.showinfo("提示", "请先选择要刷新地址的服务")
                return
            index = int(selected[0])
        
        service = self.services[index]
        
        if service.status != "运行中":
            if show_error:
                messagebox.showinfo("提示", "服务未运行")
            # 清空地址显示
            self.local_addr_var.set("")
            return
        
        # 获取本地IP
        local_ip = self.get_local_ip()
        service.local_addr = f"http://{local_ip}:{service.port}"
        
        # 更新地址显示
        self.local_addr_var.set(service.local_addr)
    
    def on_service_selected(self):
        """服务选中事件处理"""
        selected = self.service_list.selection()
        if selected:
            index = int(selected[0])
            self.refresh_address(index, show_error=False)
    
    def browser_access(self):
        """用浏览器访问服务"""
        selected = self.service_list.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要访问的服务")
            return
        
        index = int(selected[0])
        service = self.services[index]
        
        if service.status != "运行中":
            messagebox.showinfo("提示", "服务未运行")
            return
        
        if service.local_addr:
            webbrowser.open(service.local_addr)
    
    def copy_address(self, address):
        """复制地址到剪贴板"""
        if address:
            self.root.clipboard_clear()
            self.root.clipboard_append(address)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取点击位置的项目
        item = self.service_list.identify_row(event.y)
        if item:
            # 选中点击的项目
            self.service_list.selection_set(item)
            # 显示菜单
            self.context_menu.post(event.x_root, event.y_root)
    
    def copy_account(self):
        """复制服务账户到剪贴板"""
        selected = self.service_list.selection()
        if selected:
            index = int(selected[0])
            service = self.services[index]
            if service.auth_rules:
                username = service.auth_rules[0].get("username", "")
                if username:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(username)
                    messagebox.showinfo("提示", f"已复制账户: {username}")
    
    def copy_password(self):
        """复制服务密码到剪贴板"""
        selected = self.service_list.selection()
        if selected:
            index = int(selected[0])
            service = self.services[index]
            if service.auth_rules:
                password = service.auth_rules[0].get("password", "")
                if password:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(password)
                    messagebox.showinfo("提示", f"已复制密码: {password}")
    
    def on_motion(self, event):
        """处理鼠标移动事件，显示悬停提示"""
        # 确定鼠标位置所在的行和列
        region = self.service_list.identify_region(event.x, event.y)
        if region == "cell":
            row = self.service_list.identify_row(event.y)
            column = self.service_list.identify_column(event.x)
            
            try:
                index = int(row)
                
                # 如果鼠标在认证列（第4列）
                if column == "#4":
                    if index in self.full_auth_info:
                        full_auth = self.full_auth_info[index]
                        # 只有当截断显示时才显示提示
                        current_auth = self.service_list.item(row, "values")[3]
                        if len(full_auth) > 15:
                            # 显示提示
                            self.tooltip_label.config(text=full_auth)
                            self.tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
                            self.tooltip.deiconify()
                            return
                
                # 如果鼠标在路径列（第6列）
                elif column == "#6":
                    if index in self.full_path_info:
                        full_path = self.full_path_info[index]
                        # 只有当截断显示时才显示提示
                        current_path = self.service_list.item(row, "values")[5]
                        if len(full_path) > 25:
                            # 显示提示
                            self.tooltip_label.config(text=full_path)
                            self.tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
                            self.tooltip.deiconify()
                            return
            except (ValueError, IndexError):
                pass
        
        # 隐藏提示
        self.tooltip.withdraw()
    
    def on_leave(self, event):
        """处理鼠标离开事件，隐藏悬停提示"""
        self.tooltip.withdraw()
    
    def get_local_ip(self):
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def is_port_available(self, port):
        """检查端口是否可用
        
        Args:
            port: 要检查的端口号
            
        Returns:
            bool: 端口是否可用
        """
        try:
            # 检查端口是否被当前运行的服务占用
            for service in self.services:
                if service.status == "运行中" and service.port.strip() == str(port):
                    return False
            
            # 尝试绑定端口，检查是否被系统占用
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", port))
                return True
        except:
            return False
    
    def on_window_close(self):
        """窗口关闭事件处理，最小化到托盘"""
        self.hide_window()
    
    def create_tray_icon(self):
        """创建系统托盘图标和菜单"""
        # 检查系统是否支持托盘
        if not hasattr(self.root, 'iconify'):
            return
        
        # 使用pywin32库直接调用Windows API实现托盘功能
        try:
            import win32api
            import win32con
            import win32gui
            
            # 创建一个简单的16x16图标
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.ico"))
            
            # 如果图标文件不存在，创建一个
            if not os.path.exists(icon_path):
                from PIL import Image
                img = Image.new('RGB', (16, 16), color='blue')
                img.save(icon_path)
            
            # 定义窗口类
            wc = win32gui.WNDCLASS()
            wc.hInstance = win32api.GetModuleHandle(None)
            wc.lpszClassName = "DufsTrayIcon"
            
            # 定义窗口过程
            def wnd_proc(hwnd, msg, wparam, lparam):
                if msg == win32con.WM_DESTROY:
                    win32gui.PostQuitMessage(0)
                    return 0
                elif msg == win32con.WM_USER + 100:  # 托盘消息
                    if lparam == win32con.WM_LBUTTONDBLCLK:
                        # 双击显示窗口
                        print("Windows API: 双击托盘图标")
                        # 将事件放入队列，由主线程处理
                        self.event_queue.put("show_window")
                    elif lparam == win32con.WM_LBUTTONDOWN:
                        # 左键单击显示窗口
                        print("Windows API: 左键单击托盘图标")
                        # 将事件放入队列，由主线程处理
                        self.event_queue.put("show_window")
                    elif lparam == win32con.WM_RBUTTONDOWN:
                        # 右键显示菜单
                        print("Windows API: 右键点击托盘图标")
                        # 尝试显示菜单（可能会失败，因为不在主线程）
                        try:
                            self.show_tray_menu_win32(hwnd)
                        except Exception as e:
                            print(f"显示Windows API托盘菜单时出错: {e}")
                return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
            
            wc.lpfnWndProc = wnd_proc
            wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
            wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
            wc.hbrBackground = win32con.COLOR_WINDOW
            
            # 注册窗口类
            win32gui.RegisterClass(wc)
            
            # 创建窗口
            self.tray_hwnd = win32gui.CreateWindow(
                wc.lpszClassName,
                "DufsTrayIcon",
                0,
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                0, 0, wc.hInstance, None
            )
            
            # 显示窗口（SW_HIDE表示隐藏）
            win32gui.ShowWindow(self.tray_hwnd, win32con.SW_HIDE)
            
            # 加载图标
            hicon = win32gui.LoadImage(
                wc.hInstance,
                icon_path,
                win32con.IMAGE_ICON,
                16, 16,
                win32con.LR_LOADFROMFILE
            )
            
            # 创建托盘图标
            nid = (
                self.tray_hwnd,
                0,
                win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                win32con.WM_USER + 100,
                hicon,
                "Dufs多服务管理"
            )
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
            
            # 保存图标和nid，以便后续删除
            self.hicon = hicon
            self.nid = nid
            
            print("Windows API托盘功能已初始化")
            
        except Exception as e:
            print(f"创建Windows API托盘时出错: {e}")
            # 如果所有托盘实现都失败，直接退出程序
            self.on_exit()
    
    def show_tray_menu_win32(self, hwnd):
        """显示Windows API托盘右键菜单"""
        try:
            import win32api
            import win32con
            import win32gui
            
            # 获取鼠标位置
            x, y = win32api.GetCursorPos()
            
            # 创建菜单
            hmenu = win32gui.CreatePopupMenu()
            
            # 添加菜单项
            win32gui.AppendMenu(hmenu, win32con.MF_STRING, 1001, "显示窗口")
            win32gui.AppendMenu(hmenu, win32con.MF_SEPARATOR, 0, "")  # 使用空字符串而不是None
            win32gui.AppendMenu(hmenu, win32con.MF_STRING, 1002, "退出")
            
            # 显示菜单
            win32gui.SetForegroundWindow(hwnd)
            result = win32gui.TrackPopupMenu(
                hmenu,
                win32con.TPM_LEFTALIGN | win32con.TPM_LEFTBUTTON | win32con.TPM_RETURNCMD,
                x, y, 0, hwnd, None
            )
            
            # 处理菜单项，将事件放入队列，由主线程处理
            if result == 1001:
                print("Windows API: 菜单-显示窗口")
                self.event_queue.put("show_window")
            elif result == 1002:
                print("Windows API: 菜单-退出")
                self.event_queue.put("exit_app")
            
            # 释放菜单资源
            win32gui.DestroyMenu(hmenu)
        except Exception as e:
            print(f"显示Windows API托盘菜单时出错: {e}")
    
    def show_window(self):
        """显示主窗口"""
        print("显示窗口：开始")
        try:
            # 确保窗口存在
            if self.root.winfo_exists():
                # 显示窗口
                self.root.deiconify()
                print("显示窗口：deiconify调用完成")
                
                # 确保窗口可见
                self.root.update_idletasks()
                print(f"显示窗口：update_idletasks调用完成，窗口状态：{self.root.state()}")
                
                # 提升窗口层级
                self.root.attributes("-topmost", True)
                print("显示窗口：设置为最顶层")
                
                # 聚焦窗口
                self.root.focus_set()
                print("显示窗口：设置焦点")
                
                # 恢复正常层级（可选）
                self.root.after(100, lambda: self.root.attributes("-topmost", False))
                print("显示窗口：计划恢复正常层级")
            else:
                print("显示窗口：窗口不存在")
        except Exception as e:
            print(f"显示窗口：发生错误：{e}")
        print("显示窗口：结束")
    
    def hide_window(self):
        """隐藏主窗口到托盘"""
        self.root.withdraw()
    
    def set_modern_theme(self):
        """设置苹果iOS液化玻璃风格主题"""
        style = ttk.Style()
        
        # 设置主题为clam（提供更多自定义选项）
        style.theme_use("clam")
        
        # 玻璃态主色调
        glass_bg = "#f0f4f8"
        glass_fg = "#333333"
        glass_highlight = "#e0e8f0"
        glass_selected = "#c9d8e8"
        
        # 配置主窗口背景
        self.root.configure(bg=glass_bg)
        
        # 配置框架样式
        style.configure("TFrame", background=glass_bg)
        style.configure("TLabelframe", 
                       background=glass_bg, 
                       borderwidth=1, 
                       relief="flat")
        style.configure("TLabelframe.Label", 
                       background=glass_bg, 
                       foreground=glass_fg,
                       font=("Segoe UI", 11, "bold"))
        
        # 配置Treeview样式（玻璃态效果）
        style.configure("Treeview",
                       background="white",
                       foreground=glass_fg,
                       fieldbackground="white",
                       borderwidth=1,
                       relief="flat")
        
        # 配置Treeview表头
        style.configure("Treeview.Heading",
                       background=glass_highlight,
                       foreground=glass_fg,
                       font=("Segoe UI", 10, "bold"),
                       padding=(8, 5),
                       relief="flat")
        
        # 配置Treeview行悬停效果
        style.map("Treeview",
                 background=[("selected", glass_selected),
                             ("active", "#f8f8f8")],
                 foreground=[("selected", glass_fg)])
        
        # 配置按钮样式（玻璃态按钮）
        style.configure("TButton",
                       background=glass_highlight,
                       foreground=glass_fg,
                       borderwidth=1,
                       relief="flat",
                       padding=(12, 6),
                       font=("Segoe UI", 10))
        
        # 配置按钮悬停效果
        style.map("TButton",
                 background=[("active", glass_selected),
                             ("hover", glass_selected)],
                 relief=[("hover", "flat")])
        
        # 配置标签样式
        style.configure("TLabel",
                       background=glass_bg,
                       foreground=glass_fg,
                       font=("Segoe UI", 10))
        
        # 配置输入框样式
        style.configure("TEntry",
                       background="white",
                       foreground=glass_fg,
                       borderwidth=1,
                       relief="flat")
        
        # 配置滚动条样式
        style.configure("Vertical.TScrollbar",
                       background=glass_highlight,
                       troughcolor=glass_bg,
                       borderwidth=1,
                       relief="flat")
        
        # 配置滚动条悬停效果
        style.map("Vertical.TScrollbar",
                 background=[("active", glass_selected),
                             ("hover", glass_selected)])
    
    def process_events(self):
        """处理事件队列中的事件"""
        try:
            # 非阻塞地获取事件
            event = self.event_queue.get(block=False)
            print(f"处理事件: {event}")
            
            # 根据事件类型处理
            if event == "show_window":
                self.show_window()
            elif event == "exit_app":
                self.on_exit()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"处理事件时出错: {e}")
        
        # 每100毫秒检查一次事件队列
        self.root.after(100, self.process_events)
    
    def on_exit(self):
        """退出程序，停止所有服务"""
        # 停止所有运行中的服务
        for i in range(len(self.services)):
            if self.services[i].status == "运行中":
                self.stop_service(i)
        
        # 清理Windows API托盘图标
        try:
            import win32gui
            if hasattr(self, 'nid'):
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self.nid)
                print("已删除Windows API托盘图标")
        except Exception as e:
            print(f"删除Windows API托盘图标时出错: {e}")
        
        # 关闭主窗口
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tk.Tk()
    app = DufsMultiGUI(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        # 当用户按下Ctrl+C时，优雅退出
        print("程序被中断，正在退出...")
        app.on_exit()