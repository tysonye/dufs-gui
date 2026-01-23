import sys
import os
import subprocess
import threading
import time
import socket
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QFrame, QGroupBox, QGridLayout, QMenu, QAction, QSplitter,
    QMessageBox, QFileDialog, QDialog, QCheckBox, QSystemTrayIcon, QStyle, QToolTip, QStatusBar, QHeaderView, QPlainTextEdit,
    QTabWidget, QComboBox, QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QFontMetrics, QCursor

# 配置文件路径
# 获取用户配置目录，支持跨平台
if os.name == 'nt':  # Windows
    config_dir = os.path.join(os.environ['APPDATA'], 'DufsGUI')
elif os.name == 'posix':  # Linux/macOS
    config_dir = os.path.join(os.environ['HOME'], '.dufs_gui')
else:
    # 其他平台使用当前目录
    config_dir = os.path.dirname(os.path.abspath(__file__))

# 创建配置目录（如果不存在）
os.makedirs(config_dir, exist_ok=True)

# 配置文件路径
CONFIG_FILE = os.path.join(config_dir, 'dufs_config.json')

# 应用常量集中管理类
class AppConstants:
    """应用常量集中管理类
    
    用于集中管理所有应用常量，提高代码的可维护性和一致性
    """
    # 窗口尺寸常量
    MIN_WINDOW_WIDTH = 1000
    MIN_WINDOW_HEIGHT = 700
    DIALOG_WIDTH = 750
    DIALOG_HEIGHT = 550
    
    # 端口配置常量
    DEFAULT_PORT = 5001
    PORT_TRY_LIMIT = 100
    PORT_TRY_LIMIT_BACKUP = 50
    BACKUP_START_PORT = 8000
    SERVICE_START_WAIT_SECONDS = 0.5  # 减少启动检查延迟时间，从2秒改为0.5秒
    PROCESS_TERMINATE_TIMEOUT = 2
    
    # 日志配置常量
    MAX_LOG_LINES = 2000
    
    # 布局常量
    MAIN_LAYOUT_MARGINS = (20, 20, 20, 10)
    MAIN_LAYOUT_SPACING = 15
    DIALOG_LAYOUT_MARGINS = (20, 20, 20, 20)
    DIALOG_LAYOUT_SPACING = 15
    BASIC_LAYOUT_MARGINS = (15, 15, 15, 15)
    BASIC_LAYOUT_SPACING = 12
    
    # 服务状态颜色映射
    STATUS_COLORS = {
        "运行中": "#2ecc71",  # 绿色
        "启动中": "#3498db",  # 蓝色
        "停止中": "#9b59b6",  # 紫色
        "未运行": "#95a5a6",  # 灰色
        "错误": "#e74c3c"       # 红色
    }
    
    # 最大路径深度限制
    MAX_PATH_DEPTH = 20



# 全局样式表配置
GLOBAL_STYLESHEET = """
/* 基础控件样式 */
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 12px;
    color: #333333;
    background-color: #f5f5f5;
}

QMainWindow {
    background-color: #f5f5f5;
    color: #333333;
}

/* 分组框样式 */
QGroupBox {
    font-weight: 600;
    font-size: 13px;
    color: #2C3E50;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px 0 8px;
    color: #2C3E50;
}

/* 按钮样式 */
QPushButton {
    background-color: #4a6fa5;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 5px 10px;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #3a5a8a;
}

QPushButton:pressed {
    background-color: #2a4a7a;
}

QPushButton:disabled {
    background-color: #cccccc;
}

/* 浏览按钮特殊样式 - 统一为普通按钮样式 */
QPushButton#PathBrowseBtn {
    background-color: #4a6fa5;
}

QPushButton#PathBrowseBtn:hover {
    background-color: #3a5a8a;
}

/* 按钮语义化配色 */
/* 主要操作 - 绿色系 */
QPushButton#PrimaryBtn {
    background-color: #27ae60;
}

QPushButton#PrimaryBtn:hover {
    background-color: #219a52;
}

QPushButton#PrimaryBtn:pressed {
    background-color: #1e8449;
}

/* 危险操作 - 红色系 */
QPushButton#DangerBtn {
    background-color: #e74c3c;
}

QPushButton#DangerBtn:hover {
    background-color: #c0392b;
}

QPushButton#DangerBtn:pressed {
    background-color: #a93226;
}

/* 信息操作 - 蓝色系 */
QPushButton#InfoBtn {
    background-color: #3498db;
}

QPushButton#InfoBtn:hover {
    background-color: #2980b9;
}

QPushButton#InfoBtn:pressed {
    background-color: #2471a3;
}

/* 确定/取消按钮样式 - 统一为普通按钮样式 */
QPushButton#OkBtn {
    background-color: #4a6fa5;
}

QPushButton#OkBtn:hover {
    background-color: #3a5a8a;
}

QPushButton#CancelBtn {
    background-color: #4a6fa5;
}

QPushButton#CancelBtn:hover {
    background-color: #3a5a8a;
}

/* 输入框样式 */
QLineEdit {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 12px;
}

QLineEdit:focus {
    border-color: #3498DB;
    outline: none;
}

/* 复选框样式 */
QCheckBox {
    spacing: 8px;
    font-size: 12px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #BDC3C7;
}

QCheckBox::indicator:checked {
    background-color: #3498DB;
    border-color: #3498DB;
    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-check.png);
}

/* 标签样式 */
QLabel {
    color: #2C3E50;
}

QLabel#TipLabel {
    color: #7F8C8D;
    font-size: 11px;
    font-style: italic;
}

/* 标签页样式 */
QTabWidget::pane {
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    background-color: #FFFFFF;
}

QTabBar::tab {
    background-color: #e0e0e0;
    padding: 5px 15px;
    border: 1px solid #ccc;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #4a6fa5;
    color: white;
}

QTabBar::tab:!selected:hover {
    background-color: #d0d0d0;
}

/* 树形控件样式 - 核心修改 */
QTreeWidget {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 0px;  /* 移除内边距，避免挤压复选框 */
    alternate-background-color: #F8F9FA;  /* 隔行变色优化 */
    outline: none; /* 移除控件焦点轮廓 */
}

/* 树项基础样式 - 修复复选框挤压 */
QTreeWidget::item {
    padding: 4px 0px 4px 0px;  /* 仅上下内边距，左右无内边距 */
    height: 28px;  /* 固定行高，确保复选框垂直居中 */
    border: none; /* 确保基础项无边框 */
    outline: none; /* 确保基础项无轮廓 */
}

/* 移除树项指示器，避免服务名称前面空白 */
QTreeWidget::branch {
    background: transparent;
}

/* 树项选中样式 - 优化配色（柔和蓝 + 渐变） */
QTreeWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4A90E2, stop:1 #357ABD);
    color: white;
    border-radius: 4px;  /* 圆角提升质感 */
    border: none;  /* 移除边框，避免选中时显示黑色边框 */
    outline: none; /* 移除焦点轮廓 */
    selection-background-color: transparent; /* 透明选中背景，使用自定义背景 */
    selection-color: white; /* 选中文字颜色 */
}

/* 树项hover样式 - 补充未选中行的hover效果 */
QTreeWidget::item:!selected:hover {
    background-color: #E8F4FD;
    border-radius: 4px;
    border: none; /* 确保hover项无边框 */
    outline: none; /* 确保hover项无轮廓 */
}

/* 移除树形控件的焦点矩形 */
QTreeWidget:focus {
    outline: none;
}

/* 移除树形控件项的焦点矩形 */
QTreeWidget::item:focus {
    outline: none;
    border: none;
}

/* 菜单样式 - 修复菜单项无高亮问题 */
QMenu {
    background-color: white;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    padding: 4px 0;
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}

/* 菜单项基础样式 */
QMenu::item {
    padding: 8px 24px;
    margin: 0;
    background-color: transparent;
    border-radius: 4px;
}

/* 菜单项悬停样式 - 高亮显示 */
QMenu::item:hover {
    background-color: #3498DB;
    color: white;
}

/* 菜单项选中样式 - 高亮显示 */
QMenu::item:selected {
    background-color: #2980B9;
    color: white;
}

/* 菜单项禁用样式 */
QMenu::item:disabled {
    background-color: transparent;
    color: #BDC3C7;
}

/* 菜单项分隔线样式 */
QMenu::separator {
    height: 1px;
    background-color: #E0E0E0;
    margin: 4px 8px;
}

/* 状态栏样式 */
QStatusBar {
    background-color: #ECF0F1;
    color: #2C3E50;
    font-size: 11px;
}
"""

def get_resource_path(filename):
    """获取资源文件的绝对路径，处理单文件打包情况
    
    Args:
        filename (str): 资源文件名
        
    Returns:
        str: 资源文件的绝对路径
    """
    path = ""
    if hasattr(sys, '_MEIPASS'):
        # 单文件打包模式，从临时目录加载
        path = os.path.join(sys._MEIPASS, filename)
        
        # 检查文件是否存在
        if not os.path.exists(path):
            # 尝试在当前目录查找
            current_dir = os.getcwd()
            alternative_path = os.path.join(current_dir, filename)
            if os.path.exists(alternative_path):
                path = alternative_path
            else:
                # 尝试在可执行文件所在目录查找
                exe_dir = os.path.dirname(sys.executable)
                alternative_path = os.path.join(exe_dir, filename)
                if os.path.exists(alternative_path):
                    path = alternative_path
                else:
                    # 检查当前目录下的dufs目录
                    dufs_dir = os.path.join(current_dir, "dufs")
                    alternative_path = os.path.join(dufs_dir, filename)
                    if os.path.exists(alternative_path):
                        path = alternative_path
                    else:
                        # 检查可执行文件所在目录下的dufs目录
                        dufs_dir = os.path.join(exe_dir, "dufs")
                        alternative_path = os.path.join(dufs_dir, filename)
                        if os.path.exists(alternative_path):
                            path = alternative_path
    else:
        # 开发模式，从程序所在目录加载
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), filename))
        
        # 检查文件是否存在
        if not os.path.exists(path):
            # 检查当前目录下的dufs目录
            dufs_dir = os.path.join(os.path.dirname(__file__), "dufs")
            alternative_path = os.path.join(dufs_dir, filename)
            if os.path.exists(alternative_path):
                path = alternative_path
    
    return path

# 独立日志窗口类
class LogWindow(QMainWindow):
    """独立日志窗口，用于显示服务日志"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dufs 日志窗口")
        self.setMinimumSize(800, 600)
        
        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建日志Tab容器
        self.log_tabs = QTabWidget()
        self.log_tabs.setTabsClosable(True)
        main_layout.addWidget(self.log_tabs)
    
    def add_log_tab(self, service_name, log_widget):
        """添加日志标签页"""
        self.log_tabs.addTab(log_widget, service_name)
    
    def update_log_tab_title(self, index, title):
        """更新日志标签页标题"""
        if 0 <= index < self.log_tabs.count():
            self.log_tabs.setTabText(index, title)
    
    def remove_log_tab(self, index):
        """移除日志标签页"""
        if 0 <= index < self.log_tabs.count():
            self.log_tabs.removeTab(index)

# 服务状态枚举类
class ServiceStatus:
    """服务状态枚举"""
    STOPPED = "未运行"
    STARTING = "启动中"
    RUNNING = "运行中"
    ERROR = "错误"

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
        self.status = ServiceStatus.STOPPED
        
        # 访问地址
        self.local_addr = ""
        
        # 添加线程锁，保护共享资源
        self.lock = threading.Lock()
        
        # 日志相关属性
        self.log_widget = None
        self.log_tab_index = None
        
        # 日志线程终止标志
        self.log_thread_terminate = False
        
        # 日志缓冲，用于降低UI更新频率
        self.log_buffer = []
        # 日志刷新定时器
        self.log_timer = None
        
        # 公网访问相关属性
        self.ngrok_process = None
        self.public_url = ""
        self.public_access_status = "stopped"  # stopped, starting, running, stopping
        self.ngrok_authtoken = ""  # 用户配置的ngrok authtoken
        self.ngrok_api_key = ""  # 用户配置的ngrok API key
        self.ngrok_mode = "authtoken"  # 使用方式：authtoken或api_key
        
        # 日志相关属性
        self.gui_instance = None  # 用于访问GUI的append_log方法
        
        # ngrok监控相关属性
        self.ngrok_monitor_thread = None
        self.ngrok_monitor_terminate = False
        
        # ngrok重新启动计数器，避免无限循环
        self.ngrok_restart_count = 0
        self.max_ngrok_restarts = 3
        
    def get_ngrok_path(self):
        """获取ngrok路径，自动下载如果不存在"""
        import platform
        import shutil
        import requests
        
        # 定义ngrok文件名
        system = platform.system()
        if system == "Windows":
            ngrok_filename = "ngrok.exe"
        else:
            ngrok_filename = "ngrok"
        
        # 检查多个位置
        check_paths = [
            os.path.join(os.getcwd(), ngrok_filename),
            os.path.join(config_dir, ngrok_filename),
            get_resource_path(ngrok_filename)
        ]
        
        for path in check_paths:
            if os.path.exists(path):
                return path
        
        # 尝试从系统PATH获取
        if shutil.which(ngrok_filename):
            return ngrok_filename
        
        # 如果都找不到，下载ngrok
        # 注意：这里不使用append_log，因为get_ngrok_path可能在服务创建前调用，gui_instance可能还没有设置
        
        # 构建下载URL
        arch = platform.machine()
        if system == "Windows":
            if arch in ["AMD64", "x86_64"]:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
            else:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-386.zip"
        elif system == "Darwin":
            if arch in ["AMD64", "x86_64"]:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip"
            else:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip"
        else:  # Linux
            if arch in ["AMD64", "x86_64"]:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
            else:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-386.tgz"
        
        try:
            # 下载ngrok
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # 保存到临时文件
            import tempfile
            import zipfile
            import tarfile
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip" if ".zip" in download_url else ".tgz") as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # 解压文件
            extract_dir = tempfile.mkdtemp()
            if ".zip" in download_url:
                with zipfile.ZipFile(tmp_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:  # tar.gz
                with tarfile.open(tmp_path, "r:gz") as tar_ref:
                    tar_ref.extractall(extract_dir)
            
            # 找到ngrok可执行文件
            extracted_path = os.path.join(extract_dir, ngrok_filename)
            if not os.path.exists(extracted_path):
                # 可能在子目录中
                for root, dirs, files in os.walk(extract_dir):
                    if ngrok_filename in files:
                        extracted_path = os.path.join(root, ngrok_filename)
                        break
            
            # 复制到配置目录
            target_path = os.path.join(config_dir, ngrok_filename)
            shutil.copy2(extracted_path, target_path)
            
            # 设置执行权限（非Windows）
            if system != "Windows":
                os.chmod(target_path, 0o755)
            
            # 清理临时文件
            os.unlink(tmp_path)
            shutil.rmtree(extract_dir)
            
            # 不输出到控制台，只返回结果
            return target_path
        except Exception as e:
            # 不输出到控制台，只返回结果
            return "ngrok"  # 回退到系统PATH
        
    def _stop_existing_ngrok_processes(self):
        """停止系统中已存在的ngrok进程"""
        try:
            import psutil
            
            self.append_log("检查并停止已存在的ngrok进程...")
            # 查找所有ngrok进程
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # 检查进程名称或命令行中是否包含ngrok
                    proc_name = proc.info['name'] if proc.info['name'] else ''
                    proc_cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    if 'ngrok' in proc_name or 'ngrok' in proc_cmdline:
                        self.append_log(f"发现已存在的ngrok进程，PID: {proc.info['pid']}，正在停止...")
                        # 尝试优雅终止
                        proc.terminate()
                        # 等待进程退出
                        try:
                            proc.wait(timeout=2)
                            self.append_log(f"ngrok进程 {proc.info['pid']} 已成功停止")
                        except psutil.TimeoutExpired:
                            # 超时后强制终止
                            proc.kill()
                            self.append_log(f"ngrok进程 {proc.info['pid']} 已强制终止")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # 进程不存在或无权限访问，跳过
                    pass
        except Exception as e:
            self.append_log(f"停止已存在的ngrok进程失败: {str(e)}", error=True)
    
    def start_ngrok(self):
        """启动ngrok内网穿透"""
        try:
            self.append_log(f"开始启动ngrok内网穿透...")
            
            # 检查并停止已存在的ngrok进程
            self._stop_existing_ngrok_processes()
            
            # 获取ngrok路径
            ngrok_path = self.get_ngrok_path()
            
            # 优先使用用户配置的authtoken
            current_authtoken = self.ngrok_authtoken or os.environ.get("NGROK_AUTHTOKEN")
            
            # 构建ngrok命令
            command = [ngrok_path]
            
            # 设置authtoken或API key
            if self.ngrok_mode == "authtoken":
                if not current_authtoken:
                    self.append_log(f"⚠️  未配置authtoken，ngrok可能无法正常工作")
                    self.append_log(f"📌 请在设置中配置authtoken或设置环境变量 NGROK_AUTHTOKEN")
            elif self.ngrok_mode == "api_key":
                if not self.ngrok_api_key:
                    self.append_log(f"⚠️  未配置API key，ngrok可能无法正常工作")
            
            # 添加http子命令和端口参数
            local_port = str(self.port)
            
            # 不指定固定URL，让ngrok自动分配随机URL，避免端点冲突
            # 这是解决ERR_NGROK_334错误的最佳方法
            command.extend(["http", local_port])
            
            
            
            # 清除之前的进程引用
            if self.ngrok_process:
                self.ngrok_process = None
            
            # 简化端口检查日志
            try:
                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', int(local_port)))
            except Exception as e:
                pass  # 不输出详细日志，只保留关键信息
            
            # 启动ngrok进程，使用更合适的参数
            self.ngrok_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                shell=False,
                close_fds=False
            )
            
            # 启动ngrok监控线程
            self.ngrok_monitor_terminate = False
            self.ngrok_monitor_thread = threading.Thread(target=self._monitor_ngrok_process, daemon=True)
            self.ngrok_monitor_thread.start()
            
            # 简化输出处理，避免在Windows上出现管道读取问题
            # 先不启动线程，直接检查进程状态
            time.sleep(0.5)  # 给ngrok一点启动时间
            
            # 检查进程是否真的启动了
            time.sleep(1)
            
            # 检查self.ngrok_process是否为None，避免并发访问问题
            if self.ngrok_process is None:
                self.append_log(f"✗ ngrok启动失败", error=True)
                self.append_log(f"{'='*50}")
                return None
            
            poll_result = self.ngrok_process.poll()
            if poll_result is not None:
                # 进程启动后立即退出，读取错误信息
                self.append_log(f"✗ ngrok进程启动失败，退出码: {poll_result}", error=True)
                
                # 直接读取所有输出，不依赖输出线程
                direct_stdout = ""
                direct_stderr = ""
                
                try:
                    direct_stdout = self.ngrok_process.stdout.read()
                except Exception as e:
                    direct_stdout = f"读取stdout失败: {str(e)}"
                
                try:
                    direct_stderr = self.ngrok_process.stderr.read()
                except Exception as e:
                    direct_stderr = f"读取stderr失败: {str(e)}"
                
                # 输出线程已移除，直接使用直接读取的输出
                stdout_output = direct_stdout
                stderr_output = direct_stderr
                
                # 将直接读取的输出添加到结果中
                if direct_stdout:
                    stdout_output += "\n" + direct_stdout
                if direct_stderr:
                    stderr_output += "\n" + direct_stderr
                
                # 检查是否是ERR_NGROK_334错误
                all_output_str = stdout_output + stderr_output
                if "ERR_NGROK_334" in all_output_str:
                    self.append_log(f"✗ 遇到ERR_NGROK_334错误: 该endpoint已被其他ngrok进程使用")
                    self.append_log(f"   请停止其他ngrok进程或使用不同的endpoint")
                    # 清理资源
                    self.ngrok_process = None
                    self.public_access_status = "stopped"
                    self.ngrok_monitor_terminate = True
                    self.append_log(f"{'='*50}")
                    return None
                
                # 只输出关键错误信息
                if stdout_output:
                    self.append_log(f"标准输出: {stdout_output}")
                if stderr_output:
                    self.append_log(f"错误输出: {stderr_output}", error=True)
                
                # 清理资源
                self.ngrok_process = None
                self.public_access_status = "stopped"
                self.ngrok_monitor_terminate = True
                self.append_log(f"{'='*50}")
                return None
            else:
                pass
            
            # 等待ngrok完全启动并准备就绪
            for i in range(3):
                time.sleep(1)
                
                # 检查进程是否还在运行
                if self.ngrok_process is not None and self.ngrok_process.poll() is not None:
                    self.append_log(f"✗ ngrok进程在启动过程中退出，退出码: {self.ngrok_process.poll()}", error=True)
                    # 输出线程已移除，简化输出处理
                    stdout_output = "进程已退出，无法读取详细输出"
                    stderr_output = "进程已退出，无法读取详细输出"
                    
                    # 检查是否是ERR_NGROK_334错误
                    all_output_str = stdout_output + stderr_output
                    if "ERR_NGROK_334" in all_output_str:
                        self.append_log(f"✗ 遇到ERR_NGROK_334错误: 该endpoint已被其他ngrok进程使用")
                        self.append_log(f"   请停止其他ngrok进程或使用不同的endpoint")
                        # 清理资源
                        self.ngrok_process = None
                        self.public_access_status = "stopped"
                        self.ngrok_monitor_terminate = True
                        self.append_log(f"{'='*50}")
                        return None
                    
                    # 只输出关键错误信息
                    if stdout_output:
                        self.append_log(f"标准输出: {stdout_output}")
                    if stderr_output:
                        self.append_log(f"错误输出: {stderr_output}", error=True)
                    
                    # 清理资源
                    self.ngrok_process = None
                    self.public_access_status = "stopped"
                    self.ngrok_monitor_terminate = True
                    self.append_log(f"{'='*50}")
                    return None
            

            # 获取ngrok提供的公网URL
            self.public_url = self.get_ngrok_url(self.ngrok_process)
            if self.public_url:
                self.public_access_status = "running"
                # 重置重启计数
                self.ngrok_restart_count = 0
                self.append_log(f"✓ ngrok已成功启动！")
                self.append_log(f"✓ 公网URL: {self.public_url}")
                self.append_log(f"{'='*50}")
                return self.public_url
            else:
                # 进程还在运行但没有获取到URL，读取所有输出进行诊断
                self.append_log(f"✗ 未能获取ngrok公网URL", error=True)
                
                # 等待输出线程读取更多数据
                time.sleep(1)
                
                # 读取所有输出
                stdout_output = "\n".join(all_output['stdout'])
                stderr_output = "\n".join(all_output['stderr'])
                
                # 尝试直接读取剩余的输出
                if self.ngrok_process is not None:
                    try:
                        remaining_stdout = self.ngrok_process.stdout.read()
                        if remaining_stdout:
                            stdout_output += "\n" + remaining_stdout
                    except:
                        pass
                
                    try:
                        remaining_stderr = self.ngrok_process.stderr.read()
                        if remaining_stderr:
                            stderr_output += "\n" + remaining_stderr
                    except:
                        pass
                


                self.append_log(f"{'='*50}")
                self.append_log(f"命令: {' '.join(command)}")
                self.append_log(f"PID: {self.ngrok_process.pid}")
                self.append_log(f"进程状态: {'运行中' if self.ngrok_process.poll() is None else '已退出'}")
                self.append_log(f"\n=== 标准输出 ===")
                self.append_log(stdout_output)
                self.append_log(f"\n=== 错误输出 ===")
                self.append_log(stderr_output)
                self.append_log(f"{'='*50}")
                
                # 检查是否是authtoken问题
                if "authtoken" in stderr_output.lower() or "unauthorized" in stderr_output.lower():
                    self.append_log(f"\n❌ 问题诊断: ngrok需要有效的authtoken才能使用")
                    self.append_log(f"   请按照以下步骤配置:")
                    self.append_log(f"   1. 访问 https://dashboard.ngrok.com/signup 注册账号")
                    self.append_log(f"   2. 登录后，访问 https://dashboard.ngrok.com/get-started/your-authtoken 获取authtoken")
                    self.append_log(f"   3. 在命令行中运行: ngrok config add-authtoken <你的authtoken>")
                elif "already online" in stderr_output.lower() or "ERR_NGROK_334" in stderr_output:
                    self.append_log(f"\n❌ 问题诊断: 端口已被其他ngrok进程占用")
                    self.append_log(f"   请先停止之前的ngrok进程或使用不同的端口")
                elif "failed to connect" in stderr_output.lower() or "connection refused" in stderr_output.lower():
                    self.append_log(f"\n❌ 问题诊断: 无法连接到ngrok服务器")
                    self.append_log(f"   请检查网络连接或防火墙设置")
                elif "listen tcp" in stderr_output.lower() and "bind: address already in use" in stderr_output.lower():
                    self.append_log(f"\n❌ 问题诊断: 本地端口被占用")
                    self.append_log(f"   请使用不同的本地端口或停止占用该端口的进程")
                else:
                    self.append_log(f"\n❌ 问题诊断: 无法确定具体问题，请查看上面的详细输出")
                
                # 清理资源
                self.append_log("\n15. 清理ngrok资源...")
                self.public_access_status = "stopped"
                self.ngrok_monitor_terminate = True
                if self.ngrok_process:
                    try:
                        self.ngrok_process.terminate()
                        self.append_log(f"   ✓ 已发送终止信号到ngrok进程 {self.ngrok_process.pid}")
                        self.ngrok_process.wait(timeout=2)
                        self.append_log("   ✓ ngrok进程已终止")
                    except:
                        try:
                            self.ngrok_process.kill()
                            self.append_log("   ✓ 已强制终止ngrok进程")
                        except Exception as e:
                            self.append_log(f"   ✗ 强制终止ngrok进程失败: {str(e)}", error=True)
                    self.ngrok_process = None
                self.append_log("   ✓ 已清理所有ngrok资源")
                return None
        except Exception as e:
            self.append_log(f"{'='*50}")
            self.append_log(f"❌ 启动ngrok时发生异常: {str(e)}")
            self.append_log(f"{'='*50}")
            
            # 清理资源
            self.public_access_status = "stopped"
            self.ngrok_monitor_terminate = True
            if self.ngrok_process:
                try:
                    self.ngrok_process.terminate()
                    self.ngrok_process.wait(timeout=2)
                except Exception:
                    try:
                        self.ngrok_process.kill()
                    except Exception:
                        pass
                finally:
                    self.ngrok_process = None
            return None
    
    def _monitor_ngrok_process(self):
        """监控ngrok进程状态"""
        while not self.ngrok_monitor_terminate:
            time.sleep(1)  # 每秒检查一次
            
            if self.ngrok_process is None:
                break
            
            # 检查进程是否还在运行
            poll_result = self.ngrok_process.poll()
            if poll_result is not None:
                self.append_log(f"ngrok进程已退出，退出码: {poll_result}")
                
                # 检查重新启动次数是否已达上限
                if self.ngrok_restart_count < self.max_ngrok_restarts:
                    # 尝试重新启动
                    self._restart_ngrok()
                    self.ngrok_restart_count += 1
                else:
                    self.append_log(f"ngrok重启次数已达上限 ({self.max_ngrok_restarts}次)，停止重试")
                    # 重置重启计数
                    self.ngrok_restart_count = 0
                    # 停止监控线程
                    self.ngrok_monitor_terminate = True
                    # 更新状态
                    self.public_access_status = "stopped"
                    self.ngrok_process = None
                break
    
    def _restart_ngrok(self):
        """重新启动ngrok进程"""
        self.append_log("尝试重新启动ngrok...")
        
        # 首先确保彻底清理之前的ngrok进程
        if self.ngrok_process:
            try:
                self.ngrok_process.terminate()
                self.ngrok_process.wait(timeout=2)
            except:
                try:
                    self.ngrok_process.kill()
                except:
                    pass
            self.ngrok_process = None
        
        # 停止旧的监控线程
        self.ngrok_monitor_terminate = True
        if self.ngrok_monitor_thread and self.ngrok_monitor_thread.is_alive():
            # 等待旧的监控线程退出
            time.sleep(1)
        
        # 重置监控线程终止标志
        self.ngrok_monitor_terminate = False
        
        self.public_access_status = "stopped"
        self.public_url = ""
        
        # 短暂延迟后重新启动
        time.sleep(2)
        self.start_ngrok()
    
    def get_ngrok_url(self, process):
        """从ngrok进程输出中获取公网URL，优先使用ngrok本地API"""
        import re
        import requests
        
        # 检查进程是否有效
        if process is None:
            return None
        
        # 添加调试输出，显示正在尝试获取URL
        self.append_log("正在获取ngrok公网URL...")
        
        # 方法1: 使用ngrok本地API获取URL（推荐方法）
        self.append_log("尝试使用ngrok本地API获取URL...")
        try:
            # ngrok默认在127.0.0.1:4040提供API
            response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and "tunnels" in data:
                    for tunnel in data["tunnels"]:
                        if tunnel["public_url"]:
                            self.append_log(f"通过API获取到公网URL: {tunnel['public_url']}")
                            return tunnel["public_url"]
            else:
                self.append_log(f"ngrok API请求失败，状态码: {response.status_code}", error=True)
        except requests.exceptions.RequestException as e:
            self.append_log(f"ngrok API请求异常: {str(e)}", error=True)
        
        # 方法2: 从进程输出中获取URL（备选方法）
        self.append_log("尝试从ngrok进程输出中获取URL...")
        
        # 读取ngrok输出，尝试更多次并增加等待时间
        for i in range(15):  # 最多尝试15次
            try:
                # 直接读取一行，不使用select，避免在Windows上出现错误
                line = process.stdout.readline(1024)  # 限制读取大小，避免阻塞
                if line:
                    self.append_log(f"ngrok输出: {line.strip()}")
                    # 支持多种ngrok输出格式
                    patterns = [
                        # 格式1: t=2023-01-01T00:00:00+0000 lvl=info msg="started tunnel" obj=tunnels name=command_line addr=http://localhost:5000 url=https://abc123.ngrok.io
                        r'url=(https?://[\w\.-]+\.(ngrok\.io|ngrok-free\.app|ngrok\.dev))',
                        # 格式2: Forwarding                    https://abc123.ngrok.io -> http://localhost:5000
                        r'Forwarding\s+(https?://[\w\.-]+\.(ngrok\.io|ngrok-free\.app|ngrok\.dev))\s+->',
                        # 格式3: https://abc123.ngrok.io -> http://localhost:5000
                        r'(https?://[\w\.-]+\.(ngrok\.io|ngrok-free\.app|ngrok\.dev))\s+->',
                        # 格式4: 直接匹配URL
                        r'(https?://[\w\.-]+\.(ngrok\.io|ngrok-free\.app|ngrok\.dev))'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, line)
                        if match:
                            self.append_log(f"匹配到公网URL: {match.group(1)}")
                            return match.group(1)
            except Exception as e:
                self.append_log(f"读取ngrok输出失败: {str(e)}", error=True)
                break
            time.sleep(0.5)  # 等待500ms后重试，给ngrok更多时间输出
        
        self.append_log("未能获取ngrok公网URL", error=True)
        return None
    
    def append_log(self, message, error=False):
        """添加日志条目"""
        # 如果有gui_instance，使用它的append_log方法
        if self.gui_instance:
            self.gui_instance.append_log(message, error=error, service_name=self.name, service=self)
    
    def stop_ngrok(self):
        """停止ngrok进程"""
        # 终止监控线程
        self.ngrok_monitor_terminate = True
        if self.ngrok_monitor_thread and self.ngrok_monitor_thread.is_alive():
            self.ngrok_monitor_thread.join(timeout=1)  # 等待1秒让线程结束
        
        if self.ngrok_process:
            self.append_log("正在停止ngrok进程...")
            self.ngrok_process.terminate()
            try:
                self.ngrok_process.wait(timeout=5)
                self.append_log("ngrok进程已成功停止")
            except subprocess.TimeoutExpired:
                self.append_log("ngrok进程终止超时，强制终止")
                self.ngrok_process.kill()
                self.append_log("ngrok进程已强制终止")
            self.ngrok_process = None
            
        self.public_access_status = "stopped"
        self.public_url = ""
        self.append_log("ngrok已停止")
            
    def get_resource_path(self, resource_name):
        """获取资源文件路径"""
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            base_path = sys._MEIPASS
        else:
            # 开发模式
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, resource_name)

class ServiceManager:
    """服务管理器，统一管理所有服务实例"""
    def __init__(self):
        self.services = []
        self.config_lock = threading.Lock()  # 配置文件写入锁
    
    def add_service(self, service):
        """添加服务"""
        self.services.append(service)
    
    def remove_service(self, index):
        """删除服务"""
        if 0 <= index < len(self.services):
            del self.services[index]
    
    def edit_service(self, index, service):
        """编辑服务"""
        if 0 <= index < len(self.services):
            self.services[index] = service
    
    def get_service(self, index):
        """获取服务"""
        if 0 <= index < len(self.services):
            return self.services[index]
        return None
    
    def get_running_services(self):
        """获取所有运行中的服务"""
        return [s for s in self.services if s.status == ServiceStatus.RUNNING]
    
    def check_port_available(self, port, exclude_service=None):
        """检查端口是否可用"""
        # 检查是否被当前服务列表中的其他服务占用
        for service in self.services:
            if service == exclude_service:
                continue
            try:
                if int(service.port) == port and service.status == ServiceStatus.RUNNING:
                    return False
            except ValueError:
                # 如果端口不是有效数字，跳过比较
                continue
        
        # 检查端口是否被其他进程占用
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False
    
    def is_port_used_by_other_service(self, port, exclude_service=None):
        """检查端口是否被其他服务使用"""
        for service in self.services:
            if service == exclude_service:
                continue
            try:
                if int(service.port) == port and service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                    return True, service.name
            except ValueError:
                continue
        return False, None

class DufsServiceDialog(QDialog):
    """服务配置对话框"""
    def __init__(self, parent=None, service=None, edit_index=None, existing_services=None):
        super().__init__(parent)
        self.service = service
        self.edit_index = edit_index
        self.existing_services = existing_services or []
        self.init_ui()
    
    def init_ui(self):
        """初始化对话框UI"""
        self.setWindowTitle("编辑服务" if self.service else "添加服务")
        self.setGeometry(400, 200, AppConstants.DIALOG_WIDTH, AppConstants.DIALOG_HEIGHT)
        self.setModal(True)
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        # 字体设置
        font = QFont("Microsoft YaHei", 12)
        self.setFont(font)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(*AppConstants.DIALOG_LAYOUT_MARGINS)
        main_layout.setSpacing(AppConstants.DIALOG_LAYOUT_SPACING)
        
        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QGridLayout()
        basic_layout.setContentsMargins(*AppConstants.BASIC_LAYOUT_MARGINS)
        basic_layout.setSpacing(AppConstants.BASIC_LAYOUT_SPACING)
        
        # 服务名称
        name_label = QLabel("服务名称:")
        name_label.setAlignment(Qt.AlignVCenter)
        basic_layout.addWidget(name_label, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入服务名称（如：文件共享服务）")
        # 添加服务时设置默认推荐服务名，避免与现有服务名称冲突
        if not self.service:
            default_name = "文件共享服务"
            # 检查是否与现有服务名称冲突
            existing_names = [s.name for s in self.existing_services]
            if default_name in existing_names:
                # 如果冲突，添加数字后缀
                count = 1
                while f"{default_name}{count}" in existing_names:
                    count += 1
                default_name = f"{default_name}{count}"
            self.name_edit.setText(default_name)
        basic_layout.addWidget(self.name_edit, 0, 1)
        
        # 服务路径
        path_label = QLabel("服务路径:")
        path_label.setAlignment(Qt.AlignVCenter)
        basic_layout.addWidget(path_label, 1, 0)
        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("请选择或输入文件服务路径")
        # 添加服务时设置默认推荐服务路径，使用当前用户的文档目录
        if not self.service:
            default_path = os.path.expanduser("~")
            # 检查默认路径是否存在
            if not os.path.exists(default_path):
                # 如果不存在，使用程序当前目录
                default_path = os.getcwd()
            self.path_edit.setText(default_path)
        path_btn = QPushButton("浏览")
        path_btn.setObjectName("PathBrowseBtn")
        path_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_btn)
        basic_layout.addLayout(path_layout, 1, 1)
        
        # 端口
        port_label = QLabel("端口:")
        port_label.setAlignment(Qt.AlignVCenter)
        basic_layout.addWidget(port_label, 2, 0)
        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("请输入端口号（如：5000）")
        # 添加服务时设置默认推荐端口号，避免与现有服务端口冲突和系统常用端口
        if not self.service:
            # 系统常用、浏览器黑名单、特殊软件常用端口黑名单
            blocked_ports = {
                # 系统常用端口
                20, 21, 22, 23, 25, 53, 67, 68, 80, 443, 110, 143, 161, 162, 389, 445, 514, 636, 993, 995,
                # 数据库端口
                1433, 1521, 3306, 3389, 5432, 6446, 6447, 6379, 27017, 28017, 9200, 9300,
                # 浏览器黑名单端口
                1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 77, 79, 87, 95, 101, 102, 103,
                104, 109, 110, 111, 113, 115, 117, 119, 123, 135, 137, 138, 139, 143, 179, 389, 465, 512, 513,
                514, 515, 526, 530, 531, 532, 540, 556, 563, 587, 601, 636, 993, 995, 2049, 4045, 6000, 6665, 6666,
                6667, 6668, 6669, 6697,
                # 其他特殊软件常用端口
                3000, 4000, 5000, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8888, 9000, 9001,
                9090, 9091, 10000, 11211, 12345, 12346, 16992, 16993, 18080, 18081, 27017, 27018, 27019,
                # 常见危险端口
                4444, 5555, 6666, 7777, 8888, 9999, 12345, 12346, 12347, 16992, 16993
            }
            default_port = AppConstants.DEFAULT_PORT  # 从DEFAULT_PORT开始，避开常用的5000端口
            # 检查是否与现有服务端口冲突或在黑名单中
            existing_ports = [s.port for s in self.existing_services]
            while str(default_port) in existing_ports or default_port in blocked_ports:
                default_port += 1
            self.port_edit.setText(str(default_port))
        basic_layout.addWidget(self.port_edit, 2, 1)
        
        basic_group.setLayout(basic_layout)
        
        # 权限设置
        perm_group = QGroupBox("权限设置")
        perm_layout = QVBoxLayout()
        perm_layout.setContentsMargins(15, 15, 15, 15)
        perm_layout.setSpacing(10)
        
        # 权限水平布局
        perm_h_layout = QHBoxLayout()
        perm_h_layout.setSpacing(20)
        
        self.allow_upload_check = QCheckBox("允许上传文件")
        perm_h_layout.addWidget(self.allow_upload_check)
        
        self.allow_delete_check = QCheckBox("允许删除文件/文件夹")
        perm_h_layout.addWidget(self.allow_delete_check)
        
        perm_h_layout.addStretch()
        perm_layout.addLayout(perm_h_layout)
        perm_group.setLayout(perm_layout)
        
        # 认证设置
        auth_group = QGroupBox("认证设置")
        auth_layout = QGridLayout()
        auth_layout.setContentsMargins(15, 15, 15, 15)
        auth_layout.setSpacing(12)
        
        user_label = QLabel("用户名:")
        user_label.setAlignment(Qt.AlignVCenter)
        auth_layout.addWidget(user_label, 0, 0)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入认证用户名（留空不启用认证）")
        auth_layout.addWidget(self.username_edit, 0, 1)
        
        pwd_label = QLabel("密码:")
        pwd_label.setAlignment(Qt.AlignVCenter)
        auth_layout.addWidget(pwd_label, 1, 0)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("请输入认证密码（留空不启用认证）")
        auth_layout.addWidget(self.password_edit, 1, 1)
        
        tip_label = QLabel("📌 提示: 用户名/密码均需包含至少一个字母，留空表示不启用认证")
        tip_label.setObjectName("TipLabel")
        tip_label.setWordWrap(True)
        auth_layout.addWidget(tip_label, 2, 0, 1, 2)
        
        auth_group.setLayout(auth_layout)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.setSpacing(15)
        btn_layout.setAlignment(Qt.AlignCenter)
        
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("OkBtn")
        ok_btn.setMinimumWidth(100)
        ok_btn.clicked.connect(self.on_ok)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addWidget(basic_group)
        main_layout.addWidget(perm_group)
        main_layout.addWidget(auth_group)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
        # 填充数据
        if self.service:
            self.name_edit.setText(self.service.name)
            self.path_edit.setText(self.service.serve_path)
            self.port_edit.setText(self.service.port)
            self.allow_upload_check.setChecked(self.service.allow_upload)
            self.allow_delete_check.setChecked(self.service.allow_delete)
            
            if self.service.auth_rules:
                username = self.service.auth_rules[0].get("username", "")
                password = self.service.auth_rules[0].get("password", "")
                self.username_edit.setText(username)
                self.password_edit.setText(password)
    
    def browse_path(self):
        """浏览路径"""
        path = QFileDialog.getExistingDirectory(self, "选择服务路径", os.path.expanduser("~"))
        if path:
            self.path_edit.setText(path)
    
    def on_ok(self):
        """确认保存"""
        name = self.name_edit.text().strip()
        serve_path = self.path_edit.text().strip()
        port = self.port_edit.text().strip()
        
        if not name:
            QMessageBox.critical(self, "错误", "服务名称不能为空")
            return
        
        if not serve_path:
            QMessageBox.critical(self, "错误", "服务路径不能为空")
            return
        
        # 规范化服务路径，将相对路径转换为绝对路径
        serve_path = os.path.abspath(serve_path)
        
        # 检查路径是否存在
        if not os.path.exists(serve_path):
            QMessageBox.critical(self, "错误", f"服务路径 '{serve_path}' 不存在，请选择有效的路径")
            return
        
        # 检查路径是否为目录
        if not os.path.isdir(serve_path):
            QMessageBox.critical(self, "错误", f"服务路径 '{serve_path}' 不是有效的目录，请选择目录路径")
            return
        
        if not port.isdigit():
            QMessageBox.critical(self, "错误", "端口必须是数字")
            return
        
        # 验证端口范围
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            QMessageBox.critical(self, "错误", "端口必须在1-65535之间")
            return
        
        # 检查服务名称和端口是否与现有服务冲突
        for i, existing_service in enumerate(self.existing_services):
            # 跳过当前编辑的服务
            if self.edit_index is not None and i == self.edit_index:
                continue
            
            # 检查服务名称冲突
            if existing_service.name == name:
                QMessageBox.critical(self, "错误", "服务名称已存在，请使用其他名称")
                return
            
            # 检查端口冲突
            if existing_service.port == port:
                QMessageBox.critical(self, "错误", "端口已被其他服务使用，请使用其他端口")
                return
        
        # 构建服务实例
        service = DufsService(name=name, serve_path=serve_path, port=port, bind="")
        service.allow_upload = self.allow_upload_check.isChecked()
        service.allow_delete = self.allow_delete_check.isChecked()
        # 根据上传和删除权限状态自动计算allow_all
        service.allow_all = service.allow_upload and service.allow_delete
        # 搜索和打包下载功能默认启用，不再通过GUI配置
        service.allow_search = True
        service.allow_archive = True
        
        # 认证规则
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if username and password:
            # 用户名限制：长度在3-20个字符之间，包含至少一个字母，不得包含中文
            if len(username) < 3 or len(username) > 20:
                QMessageBox.critical(self, "错误", "用户名长度必须在3-20个字符之间")
                return
            if not any(c.isalpha() for c in username):
                QMessageBox.critical(self, "错误", "用户名必须包含至少一个字母")
                return
            if any('\u4e00' <= c <= '\u9fff' for c in username):
                QMessageBox.critical(self, "错误", "用户名不得包含中文")
                return
            
            # 密码限制：长度在6-30个字符之间，包含至少一个字母和一个数字，不得包含中文
            if len(password) < 6 or len(password) > 30:
                QMessageBox.critical(self, "错误", "密码长度必须在6-30个字符之间")
                return
            if not any(c.isalpha() for c in password):
                QMessageBox.critical(self, "错误", "密码必须包含至少一个字母")
                return
            if not any(c.isdigit() for c in password):
                QMessageBox.critical(self, "错误", "密码必须包含至少一个数字")
                return
            if any('\u4e00' <= c <= '\u9fff' for c in password):
                QMessageBox.critical(self, "错误", "密码不得包含中文")
                return
            
            service.auth_rules.append({
                "username": username,
                "password": password,
                "paths": ["/"]
            })
        
        self.service = service
        self.accept()

class DufsMultiGUI(QMainWindow):
    """Dufs多服务GUI主程序"""
    status_updated = pyqtSignal()
    log_signal = pyqtSignal(str, bool, str, object)  # 日志内容, 是否错误, 服务名称, 服务对象
    
    def __init__(self):
        super().__init__()
        # 使用ServiceManager统一管理服务
        self.manager = ServiceManager()
        # 添加真实退出标志位
        self._real_exit = False
        # 独立日志窗口实例
        self.log_window = None
        self.init_ui()
        self.status_updated.connect(self.update_service_list)
        self.log_signal.connect(self._append_log_ui)
    
    # 移除重复的is_port_open方法，使用ServiceManager.check_port_available
    def is_port_open(self, port):
        """检查端口是否可访问
        
        Args:
            port (int): 要检查的端口号
            
        Returns:
            bool: 端口是否可访问
        """
        try:
            # 尝试连接端口，如果成功，说明端口被占用（服务正在运行）
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
            return True
        except (OSError, ConnectionRefusedError):
            # 连接失败，说明端口不可访问
            return False
    
    def append_log(self, message, error=False, service_name="", service=None):
        """添加日志条目，将专业日志格式转换为易懂文字"""
        # 格式化日志消息
        timestamp = time.strftime("%H:%M:%S")
        service_tag = f"[{service_name}] " if service_name else ""
        
        # 根据错误级别设置日志级别和颜色
        if error:
            level = "错误"
        else:
            level = "信息"
        
        # 将专业日志格式转换为易懂文字
        readable_message = self._make_log_readable(message)
        
        # 构建日志消息，包含时间戳和级别
        log_message = f"[{timestamp}] [{level}] {service_tag}{readable_message}"
        
        # 使用信号槽机制更新UI
        self.log_signal.emit(log_message, error, service_name, service)
    
    def _make_log_readable(self, message):
        """将专业日志格式转换为易懂文字"""
        import re
        
        # 首先，检查日志是否已经包含时间戳和INFO标记
        # 例如：2026-01-08T10:00:00+08:00 INFO - 192.168.1.100 "GET /file.txt" 200
        info_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2} INFO - (.*)$')
        info_match = info_pattern.match(message)
        if info_match:
            # 提取实际的日志内容
            message = info_match.group(1)
        
        # 匹配Dufs默认日志格式：$remote_addr "$request" $status
        # 例如：192.168.1.100 "GET /file.txt" 200
        log_pattern = re.compile(r'^(\d+\.\d+\.\d+\.\d+) "(\w+) (.*?)" (\d+)$')
        match = log_pattern.match(message)
        
        if match:
            ip = match.group(1)
            method = match.group(2)
            path = match.group(3)
            status = match.group(4)
            
            # 转换HTTP方法
            method_map = {
                "GET": "访问",
                "POST": "上传",
                "PUT": "修改",
                "DELETE": "删除",
                "HEAD": "检查",
                "CHECKAUTH": "认证检查"
            }
            readable_method = method_map.get(method, method)
            
            # 转换HTTP状态码
            status_map = {
                "200": "成功",
                "201": "创建成功",
                "206": "部分内容成功",
                "400": "请求错误",
                "401": "未授权",
                "403": "禁止访问",
                "404": "找不到内容",
                "500": "服务器错误"
            }
            readable_status = status_map.get(status, f"状态码 {status}")
            
            # 转换路径
            readable_path = path if path != "/" else "根目录"
            
            # 组合成易懂的日志消息
            return f"IP {ip} {readable_method} '{readable_path}' {readable_status}"
        
        # 如果不匹配默认格式，直接返回原消息
        return message
    
    def _append_log_ui(self, message, error=False, service_name="", service=None):
        """在UI线程中添加日志条目"""
        if service and service.log_widget:
            # 添加日志到缓冲区
            service.log_buffer.append((message, error))
            
            # 如果定时器未激活，启动定时器
            if service.log_timer is None:
                service.log_timer = QTimer(self)  # 添加self作为父对象，确保在主线程中创建
                service.log_timer.timeout.connect(lambda s=service: self._flush_log_buffer(s))
            
            if not service.log_timer.isActive():
                service.log_timer.start(50)  # 50ms后刷新日志，降低UI更新频率
        else:
            # 如果没有指定服务或服务没有日志控件，暂时不处理
            pass
    
    def _flush_log_buffer(self, service):
        """刷新日志缓冲区到UI"""
        if not service or not service.log_widget:
            return
        
        # 停止定时器
        if service.log_timer and service.log_timer.isActive():
            service.log_timer.stop()
        
        # 批量处理日志
        if service.log_buffer:
            with service.lock:
                log_lines = []
                for message, error in service.log_buffer:
                    # 根据错误级别添加前缀标识，不使用HTML格式
                    if error:
                        prefix = "[ERROR] "
                    else:
                        prefix = "[INFO]  "
                    
                    # 构建纯文本日志条目
                    log_lines.append(f"{prefix}{message}")
                
                # 一次性添加所有日志
                service.log_widget.appendPlainText("\n".join(log_lines))
                
                # 清空缓冲区
                service.log_buffer.clear()
            
            # 限制日志行数，防止内存占用过多
            if service.log_widget.blockCount() > AppConstants.MAX_LOG_LINES:
                # 保留最新的MAX_LOG_LINES行日志
                cursor = service.log_widget.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.movePosition(cursor.Down, cursor.KeepAnchor, service.log_widget.blockCount() - AppConstants.MAX_LOG_LINES)
                cursor.removeSelectedText()
                service.log_widget.ensureCursorVisible()
    
    def init_ui(self):
        """初始化主窗口UI"""
        # 设置窗口属性
        self._setup_window_properties()
        
        # 创建中央组件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(*AppConstants.MAIN_LAYOUT_MARGINS)
        main_layout.setSpacing(AppConstants.MAIN_LAYOUT_SPACING)
        
        # 添加标题栏和按钮组
        self._add_title_bar(main_layout)
        self._add_button_group(main_layout)
        
        # 直接添加服务列表、ngrok配置和访问地址到主布局
        self._add_service_list(main_layout)
        self._add_ngrok_config(main_layout)
        self._add_access_address(main_layout)
        self._add_public_access_address(main_layout)
        
        # 显示日志窗口按钮已移至主按钮区域
        
        # 初始化日志Tab容器
        self._add_log_window(None)
        
        # 设置状态栏
        self._setup_status_bar()
        
        # 绑定事件
        self._bind_events()
        
        # 加载配置
        self.load_config()
        
        # 初始化服务列表
        self.update_service_list()
        
        # 初始化系统托盘
        self.init_system_tray()
        
        # 显示窗口
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.show()
    
    def _add_ngrok_config(self, main_layout):
        """添加ngrok配置UI"""
        ngrok_group = QGroupBox("ngrok配置")
        ngrok_layout = QVBoxLayout(ngrok_group)
        ngrok_layout.setContentsMargins(15, 15, 15, 15)
        ngrok_layout.setSpacing(10)
        
        # 选择ngrok使用方式
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("使用方式:"))
        
        self.ngrok_mode_combo = QComboBox()
        self.ngrok_mode_combo.addItems(["authtoken", "api_key"])
        self.ngrok_mode_combo.currentTextChanged.connect(self.on_ngrok_mode_changed)
        mode_layout.addWidget(self.ngrok_mode_combo)
        mode_layout.addStretch()
        ngrok_layout.addLayout(mode_layout)
        
        # authtoken配置 - 使用QWidget容器包装
        self.authtoken_widget = QWidget()
        authtoken_layout = QHBoxLayout(self.authtoken_widget)
        authtoken_layout.setContentsMargins(0, 0, 0, 0)
        authtoken_layout.addWidget(QLabel("Authtoken:"))
        
        self.authtoken_edit = QLineEdit()
        self.authtoken_edit.setPlaceholderText("请输入ngrok authtoken")
        self.authtoken_edit.setEchoMode(QLineEdit.Password)
        authtoken_layout.addWidget(self.authtoken_edit)
        
        authtoken_save_btn = QPushButton("保存Authtoken")
        authtoken_save_btn.clicked.connect(self.save_ngrok_authtoken)
        authtoken_layout.addWidget(authtoken_save_btn)
        ngrok_layout.addWidget(self.authtoken_widget)
        
        # API key配置 - 使用QWidget容器包装（默认隐藏）
        self.api_key_widget = QWidget()
        api_key_layout = QHBoxLayout(self.api_key_widget)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.addWidget(QLabel("API Key:"))
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("请输入ngrok API key")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_edit)
        
        api_key_save_btn = QPushButton("保存API Key")
        api_key_save_btn.clicked.connect(self.save_ngrok_api_key)
        api_key_layout.addWidget(api_key_save_btn)
        ngrok_layout.addWidget(self.api_key_widget)
        
        # 默认显示authtoken配置，隐藏API key配置
        self.api_key_widget.setVisible(False)
        
        # 添加使用提示
        tip_label = QLabel("提示：免费版ngrok每次重启URL会变化，建议使用Dufs内置认证保护共享文件夹")
        tip_label.setStyleSheet("color: #7F8C8D; font-size: 11px; font-style: italic;")
        ngrok_layout.addWidget(tip_label)
        
        main_layout.addWidget(ngrok_group)
    
    def on_ngrok_mode_changed(self, mode):
        """切换ngrok使用方式"""
        # 显示对应的配置项
        if mode == "authtoken":
            self.authtoken_widget.setVisible(True)
            self.api_key_widget.setVisible(False)
        else:
            self.authtoken_widget.setVisible(False)
            self.api_key_widget.setVisible(True)
    
    def save_ngrok_authtoken(self):
        """保存ngrok authtoken"""
        authtoken = self.authtoken_edit.text().strip()
        if not authtoken:
            QMessageBox.warning(self, "提示", "请输入authtoken")
            return
        
        try:
            # 保存authtoken到所有服务
            for service in self.manager.services:
                service.ngrok_authtoken = authtoken
                service.ngrok_mode = "authtoken"
            
            # 使用ngrok命令保存authtoken到配置文件
            result = subprocess.run(
                ["ngrok", "config", "add-authtoken", authtoken],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                QMessageBox.information(self, "成功", "authtoken已保存")
                self.authtoken_edit.clear()
            else:
                QMessageBox.warning(self, "失败", f"保存authtoken到配置文件失败: {result.stderr}")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存authtoken失败: {str(e)}")
    
    def save_ngrok_api_key(self):
        """保存ngrok API key"""
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请输入API key")
            return
        
        try:
            # 保存API key到所有服务
            for service in self.manager.services:
                service.ngrok_api_key = api_key
                service.ngrok_mode = "api_key"
            
            QMessageBox.information(self, "成功", "API key已保存")
            self.api_key_edit.clear()
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存API key失败: {str(e)}")
    
    def save_config(self):
        """保存服务配置到JSON文件"""
        try:
            # 构建配置数据结构，添加版本号和自启动设置
            config_data = {
                "version": "1.0",
                "auto_start": self.auto_start_checkbox.isChecked() if hasattr(self, 'auto_start_checkbox') else False,
                "services": []
            }
            
            # 遍历所有服务，将服务信息转换为可序列化的字典
            for service in self.manager.services:
                service_dict = {
                    "name": service.name,
                    "serve_path": service.serve_path,
                    "port": service.port,
                    "bind": service.bind,
                    "allow_all": service.allow_all,
                    "allow_upload": service.allow_upload,
                    "allow_delete": service.allow_delete,
                    "allow_search": service.allow_search,
                    "allow_symlink": getattr(service, 'allow_symlink', False),
                    "allow_archive": service.allow_archive,
                    "auth_rules": service.auth_rules
                }
                config_data["services"].append(service_dict)
            
            # 使用配置锁保护配置文件写入，防止并发写入冲突
            with self.manager.config_lock:
                # 写入配置文件
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.append_log("配置已保存到文件", service_name="系统")
        except Exception as e:
            self.append_log(f"保存配置失败: {str(e)}", error=True, service_name="系统")
    
    def load_config(self):
        """从JSON文件加载服务配置"""
        try:
            # 检查配置文件是否存在
            if not os.path.exists(CONFIG_FILE):
                self.append_log("配置文件不存在，使用默认配置", service_name="系统")
                return
            
            # 读取配置文件
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 处理不同版本的配置文件
            config_version = config_data.get("version", "1.0")  # 默认为1.0版本
            self.append_log(f"加载配置文件，版本: {config_version}", service_name="系统")
            
            # 加载自启动设置
            auto_start = config_data.get("auto_start", False)
            if hasattr(self, 'auto_start_checkbox'):
                self.auto_start_checkbox.setChecked(auto_start)
                # 检查当前系统自启动状态是否与配置一致
                current_state = self.is_auto_start_enabled()
                if current_state != auto_start:
                    self.toggle_auto_start(auto_start)
            
            # 清空现有服务列表
            self.manager.services.clear()
            
            # 遍历配置中的服务，创建服务对象
            for service_dict in config_data.get("services", []):
                service = DufsService(
                    name=service_dict.get("name", "默认服务"),
                    serve_path=service_dict.get("serve_path", "."),
                    port=service_dict.get("port", "5000"),
                    bind=service_dict.get("bind", "")
                )
                
                # 设置权限
                service.allow_all = service_dict.get("allow_all", False)
                service.allow_upload = service_dict.get("allow_upload", False)
                service.allow_delete = service_dict.get("allow_delete", False)
                service.allow_search = service_dict.get("allow_search", False)
                service.allow_symlink = service_dict.get("allow_symlink", False)
                service.allow_archive = service_dict.get("allow_archive", False)
                
                # 设置认证规则
                service.auth_rules = service_dict.get("auth_rules", [])
                
                # 设置gui_instance属性，以便服务可以访问GUI的日志功能
                service.gui_instance = self
                # 添加到服务列表
                self.manager.add_service(service)
            
            self.append_log(f"从配置文件加载了 {len(self.manager.services)} 个服务", service_name="系统")
        except Exception as e:
            self.append_log(f"加载配置失败: {str(e)}", error=True, service_name="系统")
    
    def is_auto_start_enabled(self):
        """检查是否已启用系统自启动"""
        try:
            if os.name == 'nt':  # Windows
                import winreg
                key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                    try:
                        # 尝试获取值
                        winreg.QueryValueEx(key, "DufsGUI")
                        return True
                    except FileNotFoundError:
                        return False
            elif os.name == 'posix':  # Linux/macOS
                # Linux: 检查桌面条目
                if os.path.exists(os.path.join(os.environ['HOME'], '.config', 'autostart', 'dufs-gui.desktop')):
                    return True
                # macOS: 检查LaunchAgents
                if os.path.exists(os.path.join(os.environ['HOME'], 'Library', 'LaunchAgents', 'com.dufs.gui.plist')):
                    return True
                return False
            else:
                return False
        except Exception as e:
            self.append_log(f"检查自启动状态失败: {str(e)}", error=True, service_name="系统")
            return False

    def get_correct_exe_path(self):
        """获取正确的可执行文件路径，避免使用临时目录"""
        import os
        if getattr(sys, 'frozen', False):
            # 对于单文件打包程序，使用更可靠的方法获取原始可执行文件路径
            
            # 方法1: 检查Nuitka提供的特殊环境变量，这是Nuitka单文件打包的最佳方式
            if 'NUITKA_ONEFILE_BINARY' in os.environ:
                exe_path = os.environ['NUITKA_ONEFILE_BINARY']
                self.append_log(f"使用NUITKA_ONEFILE_BINARY环境变量: {exe_path}", service_name="系统")
                return exe_path
            
            # 方法2: 使用win32api获取真实可执行文件路径（Windows专用）
            try:
                import win32api
                exe_path = win32api.GetModuleFileName(None)
                exe_path = os.path.abspath(exe_path)
                self.append_log(f"使用win32api方法: {exe_path}", service_name="系统")
                return exe_path
            except Exception as e:
                self.append_log(f"win32api方法失败: {str(e)}", service_name="系统")
            
            # 方法3: 检查当前进程的命令行
            try:
                import psutil
                # 获取当前进程ID
                pid = os.getpid()
                # 获取当前进程的命令行
                process = psutil.Process(pid)
                cmdline = process.cmdline()
                if cmdline:
                    # 命令行的第一个参数通常是可执行文件路径
                    exe_path = os.path.abspath(cmdline[0])
                    self.append_log(f"使用psutil方法: {exe_path}", service_name="系统")
                    return exe_path
            except Exception as e:
                self.append_log(f"psutil方法失败: {str(e)}", service_name="系统")
            
            # 方法4: 尝试获取当前工作目录下的可执行文件
            cwd = os.getcwd()
            possible_path = os.path.join(cwd, "dufs_multi_gui_pyqt.exe")
            if os.path.exists(possible_path):
                self.append_log(f"使用当前目录下的可执行文件: {possible_path}", service_name="系统")
                return possible_path
        
        # 方法5: 使用sys.argv[0]作为最后尝试
        exe_path = os.path.abspath(sys.argv[0])
        self.append_log(f"使用sys.argv[0]: {exe_path}", service_name="系统")
        return exe_path
    
    def add_auto_start(self):
        """添加系统自启动项"""
        try:
            if os.name == 'nt':  # Windows
                import winreg
                # 获取当前可执行文件路径
                exe_path = self.get_correct_exe_path()
                
                # 清理旧的自启动项
                key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    try:
                        winreg.DeleteValue(key, "DufsGUI")
                        self.append_log("已清理旧的自启动项", service_name="系统")
                    except FileNotFoundError:
                        pass  # 已经不存在，忽略
                
                # 设置新的自启动项
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "DufsGUI", 0, winreg.REG_SZ, f'"{exe_path}"')
                self.append_log(f"已添加开机自启动，路径: {exe_path}", service_name="系统")
            elif os.name == 'posix':  # Linux/macOS
                if sys.platform == 'darwin':  # macOS
                    # 使用LaunchAgents
                    plist_content = f'''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dufs.gui</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
                    '''
                    plist_path = os.path.join(os.environ['HOME'], 'Library', 'LaunchAgents', 'com.dufs.gui.plist')
                    with open(plist_path, 'w') as f:
                        f.write(plist_content)
                    # 加载启动项
                    subprocess.run(['launchctl', 'load', plist_path], check=True)
                else:  # Linux
                    # 创建桌面条目
                    desktop_content = f'''
[Desktop Entry]
Type=Application
Name=DufsGUI
Exec={sys.executable}
Terminal=false
Icon=utilities-terminal
Categories=Utility;
                    '''
                    autostart_dir = os.path.join(os.environ['HOME'], '.config', 'autostart')
                    os.makedirs(autostart_dir, exist_ok=True)
                    desktop_path = os.path.join(autostart_dir, 'dufs-gui.desktop')
                    with open(desktop_path, 'w') as f:
                        f.write(desktop_content)
                    # 确保文件可执行
                    os.chmod(desktop_path, 0o755)
                self.append_log("已添加开机自启动", service_name="系统")
        except Exception as e:
            self.append_log(f"添加自启动失败: {str(e)}", error=True, service_name="系统")
            QMessageBox.warning(self, "警告", f"添加自启动失败: {str(e)}")

    def remove_auto_start(self):
        """移除系统自启动项"""
        try:
            if os.name == 'nt':  # Windows
                import winreg
                key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    try:
                        winreg.DeleteValue(key, "DufsGUI")
                        self.append_log("已移除开机自启动", service_name="系统")
                    except FileNotFoundError:
                        pass  # 已经不存在，忽略
            elif os.name == 'posix':  # Linux/macOS
                if sys.platform == 'darwin':  # macOS
                    plist_path = os.path.join(os.environ['HOME'], 'Library', 'LaunchAgents', 'com.dufs.gui.plist')
                    if os.path.exists(plist_path):
                        # 卸载启动项
                        subprocess.run(['launchctl', 'unload', plist_path], check=True)
                        # 删除plist文件
                        os.remove(plist_path)
                        self.append_log("已移除开机自启动", service_name="系统")
                else:  # Linux
                    desktop_path = os.path.join(os.environ['HOME'], '.config', 'autostart', 'dufs-gui.desktop')
                    if os.path.exists(desktop_path):
                        os.remove(desktop_path)
                        self.append_log("已移除开机自启动", service_name="系统")
        except Exception as e:
            self.append_log(f"移除自启动失败: {str(e)}", error=True, service_name="系统")
            QMessageBox.warning(self, "警告", f"移除自启动失败: {str(e)}")

    def toggle_auto_start(self, enable=None):
        """切换系统自启动状态
        
        Args:
            enable (bool, optional): True为启用，False为禁用，None为切换当前状态
        """
        # 如果没有指定状态，从复选框获取
        if enable is None:
            enable = self.auto_start_checkbox.isChecked()
        else:
            # 确保复选框状态与实际状态一致
            self.auto_start_checkbox.setChecked(enable)
        
        if enable:
            self.add_auto_start()
        else:
            self.remove_auto_start()
        
        # 保存配置
        self.save_config()
    
    def _setup_window_properties(self):
        """设置窗口属性"""
        self.setWindowTitle("Dufs多服务管理")
        self.setMinimumSize(AppConstants.MIN_WINDOW_WIDTH, AppConstants.MIN_WINDOW_HEIGHT)
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        # 设置窗口图标
        icon_path = get_resource_path("icon.ico")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 居中显示
        screen_geo = QApplication.desktop().screenGeometry()
        self.setGeometry(
            (screen_geo.width() - AppConstants.MIN_WINDOW_WIDTH) // 2,
            (screen_geo.height() - AppConstants.MIN_WINDOW_HEIGHT) // 2,
            AppConstants.MIN_WINDOW_WIDTH, AppConstants.MIN_WINDOW_HEIGHT
        )
    
    def _add_title_bar(self, main_layout):
        """添加标题栏"""
        title_layout = QHBoxLayout()
        title_label = QLabel("Dufs 多服务管理")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #2C3E50;")
        title_layout.addWidget(title_label)
        
        # 添加自启动复选框
        self.auto_start_checkbox = QCheckBox("开机自启")
        self.auto_start_checkbox.stateChanged.connect(self.toggle_auto_start)
        title_layout.addWidget(self.auto_start_checkbox)
        
        title_layout.addStretch()
        main_layout.addLayout(title_layout)
    
    def _add_button_group(self, main_layout):
        """添加按钮组"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        add_btn = QPushButton("添加服务")
        add_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        add_btn.clicked.connect(self.add_service)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("编辑服务")
        edit_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        edit_btn.clicked.connect(self.edit_service)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除服务")
        delete_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        delete_btn.clicked.connect(self.delete_service)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        start_btn = QPushButton("启动服务")
        start_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        start_btn.clicked.connect(self.start_service_from_button)
        btn_layout.addWidget(start_btn)
        
        stop_btn = QPushButton("停止服务")
        stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        stop_btn.clicked.connect(self.stop_service_from_button)
        btn_layout.addWidget(stop_btn)
        
        close_btn = QPushButton("关闭程序")
        close_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        close_btn.clicked.connect(self.on_exit)
        btn_layout.addWidget(close_btn)
        
        # 添加显示日志窗口按钮
        self.log_window_btn = QPushButton("显示日志窗口")
        self.log_window_btn.setObjectName("InfoBtn")
        self.log_window_btn.clicked.connect(self.toggle_log_window)
        btn_layout.addWidget(self.log_window_btn)
        
        # 添加帮助按钮
        help_btn = QPushButton("帮助")
        help_btn.setObjectName("InfoBtn")
        help_btn.clicked.connect(self.show_help)
        btn_layout.addWidget(help_btn)
        
        main_layout.addLayout(btn_layout)
    
    def _add_service_list(self, main_layout):
        """添加服务列表"""
        service_group = QGroupBox("已配置服务")
        service_layout = QVBoxLayout(service_group)
        service_layout.setContentsMargins(15, 15, 15, 15)
        
        self.service_tree = QTreeWidget()
        # 精简为5列：服务名称 | 端口 | 状态 | 公网访问 | 详情
        self.service_tree.setColumnCount(5)
        self.service_tree.setHeaderLabels(["服务名称", "端口", "状态", "公网访问", "详情"])
        self.service_tree.setAlternatingRowColors(True)
        # 支持多选服务
        self.service_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        # 设置为整行选择模式
        self.service_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        # 移除缩进，避免服务名称前面空白
        self.service_tree.setIndentation(0)
        # 调整各列宽度，确保初始界面不需要水平滚动条
        self.service_tree.setColumnWidth(0, 200)  # 服务名称（增加宽度）
        self.service_tree.setColumnWidth(1, 80)   # 端口
        self.service_tree.setColumnWidth(2, 120)  # 状态（增加宽度，确保状态文字完整显示）
        self.service_tree.setColumnWidth(3, 250)  # 公网访问（大幅增加宽度，避免URL截断）
        self.service_tree.setColumnWidth(4, 150)  # 详情（减少宽度，因为详情信息较少）
        
        # 绑定双击事件，用于显示详情抽屉
        self.service_tree.itemDoubleClicked.connect(self.show_service_details)
        
        # 绑定选择变化事件
        self.service_tree.itemSelectionChanged.connect(self.on_service_selection_changed)
        
        # 设置表头标签居中显示
        header = self.service_tree.header()
        for i in range(self.service_tree.columnCount()):
            header.setDefaultAlignment(Qt.AlignCenter)
        
        # 设置表头拉伸策略，最后一列自动拉伸
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        # 其他列固定宽度，不允许用户调整
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.Fixed)
        
        service_layout.addWidget(self.service_tree)
        main_layout.addWidget(service_group)
    
    def _add_access_address(self, main_layout):
        """添加访问地址UI"""
        addr_group = QGroupBox("访问地址")
        addr_layout = QHBoxLayout()
        addr_layout.setContentsMargins(15, 15, 15, 15)
        addr_layout.setSpacing(10)
        
        addr_layout.addWidget(QLabel("访问地址: "))
        self.addr_edit = QLineEdit()
        self.addr_edit.setReadOnly(True)
        addr_layout.addWidget(self.addr_edit)
        
        copy_btn = QPushButton("复制")
        copy_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        copy_btn.clicked.connect(self.copy_address)
        addr_layout.addWidget(copy_btn)
        
        browse_btn = QPushButton("浏览器访问")
        browse_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        browse_btn.clicked.connect(self.browser_access)
        addr_layout.addWidget(browse_btn)
        
        addr_group.setLayout(addr_layout)
        main_layout.addWidget(addr_group)
    
    def _add_public_access_address(self, main_layout):
        """添加公网访问地址UI，优化用户体验"""
        public_group = QGroupBox("公网访问（免费版ngrok）")
        public_layout = QVBoxLayout()
        public_layout.setContentsMargins(15, 15, 15, 15)
        public_layout.setSpacing(10)
        
        # 地址显示行
        addr_layout = QHBoxLayout()
        addr_layout.setSpacing(10)
        
        # 公网地址显示
        addr_layout.addWidget(QLabel("公网地址: "))
        self.public_addr_edit = QLineEdit()
        self.public_addr_edit.setReadOnly(True)
        addr_layout.addWidget(self.public_addr_edit)
        
        # 复制按钮
        self.public_copy_btn = QPushButton("复制")
        self.public_copy_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.public_copy_btn.clicked.connect(self.copy_public_address)
        addr_layout.addWidget(self.public_copy_btn)
        
        # 浏览器访问按钮
        self.public_browse_btn = QPushButton("浏览器访问")
        self.public_browse_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.public_browse_btn.clicked.connect(self.browser_access_public)
        addr_layout.addWidget(self.public_browse_btn)
        
        # 公网访问控制按钮
        self.public_access_btn = QPushButton("启动公网访问")
        self.public_access_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.public_access_btn.clicked.connect(self.toggle_public_access_from_ui)
        addr_layout.addWidget(self.public_access_btn)
        
        # 将地址行添加到主布局
        public_layout.addLayout(addr_layout)
        
        # 添加重要提示
        tip_label = QLabel("📌 提示：免费版ngrok每次重启URL会变化，建议使用Dufs内置认证保护共享文件夹")
        tip_label.setStyleSheet("color: #7F8C8D; font-size: 11px; font-style: italic;")
        tip_label.setWordWrap(True)
        public_layout.addWidget(tip_label)
        
        public_group.setLayout(public_layout)
        main_layout.addWidget(public_group)
    
    def _add_log_window(self, main_layout):
        """初始化日志Tab容器，不添加到主窗口布局"""
        # 创建日志Tab容器，用于管理日志标签页
        self.log_tabs = QTabWidget()
        self.log_tabs.setTabsClosable(True)
        self.log_tabs.tabCloseRequested.connect(self.close_log_tab)
    
    def _get_status_icon(self, status):
        """获取状态对应的图标"""
        status_icons = {
            ServiceStatus.RUNNING: "🟢",
            ServiceStatus.STARTING: "🟡",
            ServiceStatus.STOPPED: "🔴",
            ServiceStatus.ERROR: "🟠"
        }
        return status_icons.get(status, "❓")
    
    def create_service_log_tab(self, service):
        """为服务创建专属日志Tab，优化显示"""
        log_view = QPlainTextEdit()
        log_view.setReadOnly(True)
        log_view.setStyleSheet("""
            font-family: 'Consolas', 'Monaco', monospace; 
            font-size: 12px; 
            background-color: #0f111a; 
            color: #c0c0c0;
            border: 1px solid #333;
        """)
        log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        log_view.setMaximumBlockCount(AppConstants.MAX_LOG_LINES)
        
        # 优化Tab标题，显示关键信息
        status_icon = self._get_status_icon(service.status)
        title = f"{status_icon} 服务 {service.name} | {service.port} | {service.status}"
        
        index = self.log_tabs.addTab(log_view, title)
        
        # 绑定服务与日志控件
        service.log_widget = log_view
        service.log_tab_index = index
    
    def close_log_tab(self, index):
        """关闭日志Tab"""
        # 获取要关闭的日志Tab对应的服务
        if self.log_tabs:
            widget = self.log_tabs.widget(index)
            for service in self.manager.services:
                if service.log_widget == widget:
                    # 清空服务的日志相关属性
                    service.log_widget = None
                    service.log_tab_index = None
                    break
            # 移除日志Tab
            self.log_tabs.removeTab(index)
        
        # 如果独立日志窗口已创建，也从独立窗口移除对应的Tab
        if self.log_window is not None:
            self.log_window.remove_log_tab(index)
    
    def view_service_log(self, index):
        """查看服务日志，如日志Tab不存在则重新创建"""
        # 检查索引是否有效
        if not isinstance(index, int) or index < 0 or index >= len(self.manager.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return
        
        service = self.manager.services[index]
        
        # 检查服务是否正在运行
        if service.status != ServiceStatus.RUNNING:
            QMessageBox.information(self, "提示", "该服务未运行，无法查看日志")
            return
        
        # 确保独立日志窗口已创建
        if self.log_window is None:
            self.toggle_log_window()
        
        # 检查是否已存在日志Tab
        if service.log_widget:
            # 日志Tab已存在，在独立窗口中切换到该Tab
            for i in range(self.log_window.log_tabs.count()):
                if self.log_window.log_tabs.widget(i) == service.log_widget:
                    self.log_window.log_tabs.setCurrentIndex(i)
                    break
        else:
            # 日志Tab不存在，重新创建
            self.create_service_log_tab(service)
        
        # 确保独立日志窗口可见
        if not self.log_window.isVisible():
            self.toggle_log_window()
    
    def update_status_bar(self):
        """更新状态栏，显示更详细信息"""
        running_count = sum(1 for s in self.manager.services if s.status == ServiceStatus.RUNNING)
        stopped_count = len(self.manager.services) - running_count
        
        status_text = f"就绪 - {running_count} 个服务运行中 | {stopped_count} 个服务已停止"
        
        # 添加快捷操作提示
        if running_count > 0:
            status_text += f" | 按Ctrl+Shift+R重启所有服务"
        
        self.status_bar.showMessage(status_text)
    
    def _setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.update_status_bar()
        self.setStatusBar(self.status_bar)
    
    def _bind_events(self):
        """绑定事件"""
        # 绑定服务列表选择事件
        self.service_tree.itemSelectionChanged.connect(self.on_service_selected)
        
        # 双击事件已在_add_service_list方法中绑定到show_service_details，无需重复绑定
        
        # 绑定右键菜单
        self.service_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.service_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # 启用鼠标跟踪，以便实现悬浮提示
        self.service_tree.setMouseTracking(True)
        # 绑定鼠标进入项事件
        self.service_tree.itemEntered.connect(self.on_item_entered)
        # 绑定项目点击事件
        self.service_tree.itemClicked.connect(self.on_item_clicked)
    
    def show_context_menu(self, pos):
        """显示右键菜单"""
        # 获取当前位置的项
        item = self.service_tree.itemAt(pos)
        if not item:
            return
        
        # 清除当前所有选择
        self.service_tree.clearSelection()
        # 设置当前项为选中状态，确保用户清楚看到选中的是哪个服务
        self.service_tree.setCurrentItem(item)
        # 确保项被选中，添加明确的选择操作
        item.setSelected(True)
        # 确保选择事件被触发
        self.service_tree.setFocus()
        
        # 获取服务索引
        index = item.data(0, Qt.UserRole)
        if index is None:
            return
        
        # 创建右键菜单
        menu = QMenu(self)
        
        # 添加菜单项
        start_action = QAction("启动服务", self)
        start_action.triggered.connect(lambda: self.start_service(index))
        
        stop_action = QAction("停止服务", self)
        stop_action.triggered.connect(lambda: self.stop_service(index))
        
        view_log_action = QAction("查看日志", self)
        view_log_action.triggered.connect(lambda: self.view_service_log(index))
        
        edit_action = QAction("编辑服务", self)
        edit_action.triggered.connect(lambda: self.edit_service(item))
        
        delete_action = QAction("删除服务", self)
        delete_action.triggered.connect(lambda: self.delete_service())
        
        # 添加公网访问相关菜单项
        start_public_action = QAction("启动公网访问", self)
        start_public_action.triggered.connect(lambda: self.start_public_access(index))
        
        stop_public_action = QAction("停止公网访问", self)
        stop_public_action.triggered.connect(lambda: self.stop_public_access(index))
        
        # 根据服务状态启用/禁用菜单项
        service = self.manager.services[index]
        start_action.setEnabled(service.status == ServiceStatus.STOPPED)
        stop_action.setEnabled(service.status == ServiceStatus.RUNNING)
        view_log_action.setEnabled(service.status == ServiceStatus.RUNNING)
        
        # 根据服务状态和公网访问状态启用/禁用公网访问菜单项
        start_public_action.setEnabled(service.status == ServiceStatus.RUNNING and service.public_access_status != "running")
        stop_public_action.setEnabled(service.public_access_status == "running")
        
        # 添加菜单项到菜单
        menu.addAction(start_action)
        menu.addAction(stop_action)
        menu.addSeparator()
        menu.addAction(start_public_action)
        menu.addAction(stop_public_action)
        menu.addSeparator()
        menu.addAction(view_log_action)
        menu.addAction(edit_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.service_tree.mapToGlobal(pos))
    
    def init_system_tray(self):
        """初始化系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.warning(self, "托盘功能不可用", "无法在系统托盘中显示图标。")
            return
            
        # 获取图标路径
        icon_path = get_resource_path("icon.ico")
        
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置默认图标
        if icon_path and os.path.exists(icon_path):
            self.default_icon = QIcon(icon_path)
        else:
            self.default_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        
        # 初始设置图标和工具提示
        self.tray_icon.setIcon(self.default_icon)  # 只设置一次图标，避免频繁更新
        self.update_tray_tooltip()
        
        # 创建托盘菜单
        self.tray_menu = QMenu(self)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # 初始化托盘菜单刷新防抖定时器
        self._tray_refresh_timer = QTimer(self)
        self._tray_refresh_timer.setSingleShot(True)
        self._tray_refresh_timer.setInterval(150)  # 150ms防抖
        self._tray_refresh_timer.timeout.connect(self._do_refresh_tray_menu)
        
        # 初始刷新托盘菜单
        self._do_refresh_tray_menu()
        
        # 绑定托盘图标激活事件
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
        
        # 更新服务状态时刷新托盘
        self.status_updated.connect(self.update_tray_ui)
    
    def update_tray_ui(self):
        """更新托盘UI，包括图标和工具提示"""
        self.update_tray_icon()
        self.update_tray_tooltip()
        
        # 只在服务状态为RUNNING或STOPPED时刷新托盘菜单，避免启动阶段频繁刷新
        # 启动阶段服务状态为STARTING，不刷新托盘菜单
        running_services = [s for s in self.manager.services if s.status == ServiceStatus.RUNNING]
        starting_services = [s for s in self.manager.services if s.status == ServiceStatus.STARTING]
        
        # 只有当没有服务处于启动中状态时，才刷新托盘菜单
        if not starting_services:
            self.refresh_tray_menu()
    
    def update_tray_icon(self):
        """根据服务状态更新托盘图标"""
        # 当前实现中，无论服务数量如何，都使用同一个默认图标
        # 因此不需要频繁设置图标，避免Shell刷新
        pass
    
    def update_tray_tooltip(self):
        """更新托盘提示，显示详细服务状态"""
        tooltip = "Dufs多服务管理\n\n正在运行的服务:\n"
        running_services = [s for s in self.manager.services if s.status == ServiceStatus.RUNNING]
        
        if running_services:
            for service in running_services:
                tooltip += f"• {service.name}: {service.local_addr}\n"
        else:
            tooltip += "• 无正在运行的服务"
        
        tooltip += f"\n总共: {len(self.manager.services)} 个服务"
        self.tray_icon.setToolTip(tooltip)
    
    def show_window(self):
        """显示主窗口"""
        self.showNormal()
        self.raise_()
        self.activateWindow()
    
    def open_url(self, url):
        """打开指定的URL
        
        Args:
            url (str): 要打开的URL地址
        """
        if url:
            import webbrowser
            webbrowser.open(url)
    
    def start_all_services(self):
        """启动所有服务"""
        for i in range(len(self.manager.services)):
            service = self.manager.services[i]
            if service.status != ServiceStatus.RUNNING:
                self.start_service(i)
    
    def stop_all_services(self):
        """停止所有服务"""
        for i in range(len(self.manager.services)):
            service = self.manager.services[i]
            if service.status == ServiceStatus.RUNNING:
                self.stop_service(i)
    
    def _make_start_handler(self, service):
        """创建启动服务的处理函数，避免lambda闭包索引问题"""
        def handler():
            # 直接绑定服务对象，而不是使用索引
            # 通过service对象找到当前的索引
            if service in self.manager.services:
                index = self.manager.services.index(service)
                QTimer.singleShot(0, lambda: self.start_service(index))
        return handler
    
    def _make_stop_handler(self, service):
        """创建停止服务的处理函数，避免lambda闭包索引问题"""
        def handler():
            # 直接绑定服务对象，而不是使用索引
            # 通过service对象找到当前的索引
            if service in self.manager.services:
                index = self.manager.services.index(service)
                QTimer.singleShot(0, lambda: self.stop_service(index))
        return handler
    
    def refresh_tray_menu(self):
        """刷新托盘菜单，根据当前services列表重建（带防抖）"""
        # 启动防抖定时器，延迟执行实际刷新
        self._tray_refresh_timer.start(150)
    
    def _do_refresh_tray_menu(self):
        """实际执行托盘菜单刷新"""
        # 清空现有菜单
        self.tray_menu.clear()
        
        # 1. 服务状态摘要
        running_count = sum(1 for service in self.manager.services if service.status == ServiceStatus.RUNNING)
        status_action = QAction(f"🖥️ {running_count} 个服务正在运行", self)
        status_action.setEnabled(False)
        self.tray_menu.addAction(status_action)
        
        # 2. 快速访问正在运行的服务
        running_services = [service for service in self.manager.services if service.status == ServiceStatus.RUNNING]
        if running_services:
            self.tray_menu.addSeparator()
            quick_access_menu = self.tray_menu.addMenu("🚀 快速访问")
            for service in running_services:
                # 显示服务名称和访问地址
                access_action = quick_access_menu.addAction(f"🌐 {service.name}")
                access_action.triggered.connect(
                    lambda checked=False, url=service.local_addr: self.open_url(url)
                )
        
        # 3. 主界面和退出选项
        self.tray_menu.addSeparator()
        
        # 显示主界面
        show_action = QAction("显示主界面", self)
        show_action.triggered.connect(self.show_window)
        self.tray_menu.addAction(show_action)
        
        # 退出程序
        exit_action = QAction("退出程序", self)
        exit_action.triggered.connect(self.on_exit)
        self.tray_menu.addAction(exit_action)
    
    def on_tray_icon_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            # 双击托盘图标显示窗口
            self.show_window()
        elif reason == QSystemTrayIcon.Trigger:
            # 单击托盘图标切换窗口显示状态
            if self.isVisible():
                self.hide()
            else:
                self.show_window()
    
    def closeEvent(self, event):
        """处理窗口关闭事件，最小化到托盘"""
        # 检查是否为真实退出
        if self._real_exit:
            event.accept()
            return
        # 取消事件，改为最小化到托盘
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Dufs多服务管理",
            "程序已最小化到托盘，双击托盘图标恢复窗口",
            QSystemTrayIcon.Information,
            2000
        )
    
    def on_exit(self):
        """退出程序"""
        # 设置真实退出标志位
        self._real_exit = True
        # 停止所有正在运行的服务
        for i in range(len(self.manager.services)):
            service = self.manager.services[i]
            if service.status == ServiceStatus.RUNNING or service.status == ServiceStatus.STARTING:
                self.stop_service(i)
        
        # 确保所有线程都正确退出
        # 给线程一些时间来清理资源
        import time
        time.sleep(0.5)
        
        # 退出应用
        QApplication.quit()
    
    # 移除重复的is_port_available方法，使用ServiceManager.check_port_available
    def is_port_available(self, port, exclude_service=None):
        """检查端口是否可用
        
        Args:
            port (int): 要检查的端口号
            exclude_service (DufsService, optional): 要排除的服务对象. Defaults to None.
        
        Returns:
            bool: 端口是否可用
        """
        return self.manager.check_port_available(port, exclude_service)
    
    def get_local_ip(self):
        """获取本地局域网IP地址
        
        Returns:
            str: 本地局域网IP地址，如192.168.x.x
        """
        # 方法1：尝试连接外部服务器获取IP（适用于有互联网连接的情况）
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            pass
        
        # 方法2：获取所有网络接口的IP地址（适用于局域网环境）
        try:
            # 获取主机名
            hostname = socket.gethostname()
            # 获取所有IP地址
            ip_addresses = socket.getaddrinfo(hostname, None)
            
            # 筛选出有效的IPv4地址，排除127.0.0.1
            for addr_info in ip_addresses:
                try:
                    # 获取IP地址
                    if len(addr_info) > 4 and addr_info[4]:
                        ip = addr_info[4][0]
                        # 排除IPv6地址和回环地址
                        if ip != '127.0.0.1' and ':' not in ip:
                            return ip
                except Exception:
                    pass
        except Exception:
            pass
        
        # 方法3：尝试获取所有网络接口信息（适用于复杂网络环境）
        # 使用纯Python标准库实现
        try:
            # 使用socket的gethostbyname_ex获取所有IP地址
            hostname = socket.gethostname()
            # 获取所有IP地址，包括IPv4和IPv6
            ip_list = []
            for ip_info in socket.getaddrinfo(hostname, None):
                try:
                    if ip_info[0] == socket.AF_INET and len(ip_info) > 4 and ip_info[4]:
                        ip = ip_info[4][0]
                        if ip != '127.0.0.1':
                            ip_list.append(ip)
                except Exception:
                    pass
            # 如果找到有效的IP地址，返回第一个
            if ip_list:
                return ip_list[0]
        except Exception:
            pass
        
        # 方法4：使用socket.gethostbyname获取IP地址
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip != '127.0.0.1':
                return local_ip
        except Exception:
            pass
        
        # 如果所有方法都失败，返回127.0.0.1作为备选，而不是localhost
        return '127.0.0.1'
    
    def stream_log(self, process, service):
        """实时读取进程日志并添加到日志窗口
        
        Args:
            process (subprocess.Popen): 要监控的进程对象
            service (DufsService): 对应的服务对象
        """
        def read_logs():
            """读取日志的内部函数"""
            # 读取stdout和stderr的函数
            def read_output(pipe, is_stderr):
                buffer = b""
                while True:
                    # 检查是否需要终止日志线程
                    if service.log_thread_terminate:
                        break
                    if process.poll() is not None:
                        break
                    try:
                        # 非阻塞读取：尝试读取一些数据，超时后返回
                        # 使用较小的缓冲区和超时，避免长时间阻塞
                        import time
                        import os
                        
                        # 尝试读取数据，使用select来实现非阻塞（在Windows上使用不同的方法）
                        if os.name == 'nt':  # Windows系统
                            # Windows上使用ctypes设置文件描述符为非阻塞
                            import ctypes
                            
                            # 获取文件描述符
                            fd = pipe.fileno()
                            
                            # 设置为非阻塞模式
                            flags = ctypes.windll.kernel32.SetNamedPipeHandleState(
                                fd, ctypes.byref(ctypes.c_uint(1)), None, None)
                            
                            try:
                                # 尝试读取数据，最多读取4096字节
                                data = pipe.read(4096)
                                if data:
                                    buffer += data
                                    # 处理缓冲区中的完整行
                                    while b'\n' in buffer:
                                        line_bytes, buffer = buffer.split(b'\n', 1)
                                        line = line_bytes.decode('utf-8', errors='replace').strip()
                                        if line:
                                            self.append_log(line, error=is_stderr, service_name=service.name, service=service)
                            except BlockingIOError:
                                # 没有数据可读，继续循环
                                pass
                            except Exception as e:
                                # 其他错误，可能是管道已关闭
                                break
                        else:  # Unix-like系统
                            import select
                            
                            # 使用select实现非阻塞读取
                            rlist, _, _ = select.select([pipe], [], [], 0.1)  # 100ms超时
                            if pipe in rlist:
                                data = pipe.read(4096)
                                if data:
                                    buffer += data
                                    # 处理缓冲区中的完整行
                                    while b'\n' in buffer:
                                        line_bytes, buffer = buffer.split(b'\n', 1)
                                        line = line_bytes.decode('utf-8', errors='replace').strip()
                                        if line:
                                            self.append_log(line, error=is_stderr, service_name=service.name, service=service)
                                else:
                                    # 管道已关闭
                                    break
                        
                        # 控制循环频率，避免占用过多CPU资源
                        time.sleep(0.1)
                    except Exception as e:
                        # 读取出错，可能是进程已经退出
                        break
                
                # 处理缓冲区中剩余的数据
                if buffer:
                    line = buffer.decode('utf-8', errors='replace').strip()
                    if line:
                        self.append_log(line, error=is_stderr, service_name=service.name, service=service)
            
            # 启动两个线程分别读取stdout和stderr
            stdout_thread = threading.Thread(target=read_output, args=(process.stdout, False), daemon=True)
            stderr_thread = threading.Thread(target=read_output, args=(process.stderr, True), daemon=True)
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待两个线程结束
            stdout_thread.join()
            stderr_thread.join()
        
        # 启动日志读取线程
        threading.Thread(target=read_logs, daemon=True).start()
    
    def on_item_entered(self, item, column):
        """处理鼠标进入项事件，显示悬浮提示（修复列索引错误）"""
        # 认证列（索引3）、服务路径列（索引5）显示悬浮提示
        if column == 3 or column == 5:
            # 获取当前项的完整文本
            full_text = item.text(column)
            
            # 获取项在当前列的实际显示宽度
            font = self.service_tree.font()
            metrics = QFontMetrics(font)
            text_width = metrics.width(full_text)
            column_width = self.service_tree.columnWidth(column)
            
            # 如果文本宽度大于列宽，显示悬浮提示
            if text_width > column_width:
                # 设置悬浮提示
                QToolTip.showText(QCursor.pos(), full_text)
            else:
                # 否则隐藏悬浮提示
                QToolTip.hideText()
    
    def on_item_clicked(self, item, column):
        """项目点击事件处理"""
        # 单选模式下，Qt默认会处理选择逻辑，这里不需要额外处理
        pass
    
    def copy_address(self):
        """复制访问地址到剪贴板"""
        address = self.addr_edit.text()
        if address:
            clipboard = QApplication.clipboard()
            clipboard.setText(address)
            self.status_bar.showMessage("地址已复制到剪贴板")
    
    def copy_public_address(self):
        """复制公网访问地址到剪贴板"""
        address = self.public_addr_edit.text()
        if address:
            clipboard = QApplication.clipboard()
            clipboard.setText(address)
            self.status_bar.showMessage("公网地址已复制到剪贴板")
    
    def browser_access(self):
        """在浏览器中访问服务"""
        address = self.addr_edit.text()
        if address:
            try:
                import webbrowser
                webbrowser.open(address)
            except Exception as e:
                self.append_log(f"浏览器访问失败: {str(e)}", error=True)
                QMessageBox.warning(self, "警告", f"浏览器访问失败: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个服务")
    
    def browser_access_public(self):
        """在浏览器中访问公网服务"""
        address = self.public_addr_edit.text()
        if address:
            try:
                import webbrowser
                webbrowser.open(address)
            except Exception as e:
                self.append_log(f"公网访问失败: {str(e)}", error=True)
                QMessageBox.warning(self, "警告", f"公网访问失败: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "公网地址为空")
    
    def toggle_public_access_from_ui(self):
        """从UI切换公网访问状态"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个服务")
            return
        
        # 获取选中的服务索引
        selected_item = selected_items[0]
        index = selected_item.data(0, Qt.UserRole)
        if index is None:
            QMessageBox.warning(self, "警告", "无效的服务索引")
            return
        
        # 切换公网访问状态
        self.toggle_public_access(index)
    
    def update_public_access_ui(self, service):
        """更新公网访问UI组件"""
        if service and service.public_url:
            self.public_addr_edit.setText(service.public_url)
            self.public_access_btn.setText("停止公网访问")
        else:
            self.public_addr_edit.setText("")
            self.public_access_btn.setText("启动公网访问")
    
    def on_service_selection_changed(self):
        """处理服务选择变化事件"""
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            # 至少选择了一个服务，更新访问地址和公网访问UI
            # 使用第一个选中的服务
            selected_item = selected_items[0]
            index = selected_item.data(0, Qt.UserRole)
            if index is not None:
                self.refresh_address(index)
                self.update_public_access_ui(self.manager.services[index])
        else:
            # 没有选择服务，清空访问地址和公网访问UI
            self.addr_edit.setText("")
            self.update_public_access_ui(None)
    
    def show_service_details(self, item, column):
        """显示服务详情抽屉"""
        # 获取服务索引
        index = item.data(0, Qt.UserRole)
        if index is None:
            return
        
        # 获取服务对象
        service = self.manager.services[index]
        
        # 显示服务详情对话框
        details_text = f"服务名称: {service.name}\n"
        details_text += f"端口: {service.port}\n"
        details_text += f"状态: {service.status}\n"
        details_text += f"服务路径: {service.serve_path}\n"
        
        # 权限信息
        perms_info = []
        if service.allow_upload:
            perms_info.append("上传")
        if service.allow_delete:
            perms_info.append("删除")
        perms_text = ", ".join(perms_info) if perms_info else "无特殊权限"
        details_text += f"权限: {perms_text}\n"
        
        # 认证信息
        auth_info = "无认证"
        if service.auth_rules:
            username = service.auth_rules[0].get("username", "")
            password = service.auth_rules[0].get("password", "")
            auth_info = f"{username}:{password}"
        details_text += f"认证: {auth_info}\n"
        
        # 公网访问信息
        public_access_info = "请先启动服务"
        if service.status == ServiceStatus.RUNNING:
            if service.public_access_status == "running":
                public_access_info = f"运行中: {service.public_url}"
            elif service.public_access_status == "starting":
                public_access_info = "启动中"
            elif service.public_access_status == "stopping":
                public_access_info = "停止中"
            else:
                public_access_info = "未启动"
        details_text += f"公网访问: {public_access_info}\n"
        
        QMessageBox.information(self, f"服务详情 - {service.name}", details_text)
    
    def on_service_selected(self):
        """处理服务列表选择事件"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            self.addr_edit.setText("")
            self.update_public_access_ui(None)
            return
        
        # 获取选中的服务项
        selected_item = selected_items[0]
        
        # 获取服务索引
        index = selected_item.data(0, Qt.UserRole)
        if index is None:
            self.addr_edit.setText("")
            self.update_public_access_ui(None)
            return
        
        # 获取服务对象
        service = self.manager.services[index]
        
        # 更新访问地址
        self.refresh_address(index)
        
        # 更新公网访问UI
        self.update_public_access_ui(service)
        
        # 如果独立日志窗口已创建，切换到对应的日志标签
        if service.log_widget and self.log_window is not None:
            # 在独立日志窗口中切换到对应的日志标签
            for i in range(self.log_window.log_tabs.count()):
                if self.log_window.log_tabs.widget(i) == service.log_widget:
                    self.log_window.log_tabs.setCurrentIndex(i)
                    break
    
    def refresh_address(self, index):
        """刷新访问地址"""
        service = self.manager.services[index]
        if service.status == ServiceStatus.RUNNING:
            # 使用局域网IP地址而不是localhost
            bind = service.bind if service.bind else self.get_local_ip()
            service.local_addr = f"http://{bind}:{service.port}"
            self.addr_edit.setText(service.local_addr)
        else:
            self.addr_edit.setText("")
    
    def toggle_public_access(self, index):
        """切换公网访问状态"""
        if 0 <= index < len(self.manager.services):
            service = self.manager.services[index]
            if service.public_access_status == "running":
                self.stop_public_access(index)
            else:
                self.start_public_access(index)
    
    def start_public_access(self, index):
        """启动公网访问"""
        if 0 <= index < len(self.manager.services):
            service = self.manager.services[index]
            if service.status != ServiceStatus.RUNNING:
                QMessageBox.warning(self, "提示", "请先启动服务")
                return
            
            # 添加用户操作日志
            self.append_log(f"用户请求为服务 {service.name} 启动公网访问", service_name=service.name)
            
            # 检查authtoken或API key是否已配置
            authtoken_configured = False
            if service.ngrok_mode == "authtoken":
                # 检查authtoken是否已配置
                if service.ngrok_authtoken or os.environ.get("NGROK_AUTHTOKEN"):
                    authtoken_configured = True
                    current_authtoken = service.ngrok_authtoken or os.environ.get("NGROK_AUTHTOKEN")
                    self.append_log(f"使用authtoken: {current_authtoken[:10]}...{current_authtoken[-5:]}", service_name=service.name)
                else:
                    # 未配置authtoken，显示弹窗提醒
                    self.append_log(f"未配置ngrok authtoken，需要用户配置", error=True, service_name=service.name)
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("提示")
                    msg_box.setText("未配置ngrok authtoken")
                    msg_box.setInformativeText(
                        "ngrok需要authtoken才能正常工作，请按照以下步骤配置：\n\n" \
                        "1. 访问 https://dashboard.ngrok.com/signup 注册账号\n" \
                        "2. 登录后，访问 https://dashboard.ngrok.com/get-started/your-authtoken 获取authtoken\n" \
                        "3. 在程序中保存authtoken或设置环境变量 NGROK_AUTHTOKEN"
                    )
                    msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    msg_box.setDefaultButton(QMessageBox.Ok)
                    
                    # 显示弹窗
                    result = msg_box.exec_()
                    if result == QMessageBox.Ok:
                        # 打开ngrok官网地址
                        self.append_log(f"用户选择前往ngrok官网配置authtoken", service_name=service.name)
                        import webbrowser
                        webbrowser.open("https://dashboard.ngrok.com/signup")
                    elif result == QMessageBox.Cancel:
                        # 终止启动公网服务
                        self.append_log(f"用户取消了公网访问启动", service_name=service.name)
                        return
            elif service.ngrok_mode == "api_key":
                # 检查API key是否已配置
                if service.ngrok_api_key:
                    authtoken_configured = True
                    self.append_log(f"使用API key模式", service_name=service.name)
                else:
                    # 未配置API key，显示弹窗提醒
                    self.append_log(f"未配置ngrok API key，需要用户配置", error=True, service_name=service.name)
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("提示")
                    msg_box.setText("未配置ngrok API key")
                    msg_box.setInformativeText(
                        "ngrok API key用于调用ngrok REST API，请按照以下步骤配置：\n\n" \
                        "1. 访问 https://dashboard.ngrok.com/api-keys 创建API key\n" \
                        "2. 在程序中保存API key"
                    )
                    msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    msg_box.setDefaultButton(QMessageBox.Ok)
                    
                    # 显示弹窗
                    result = msg_box.exec_()
                    if result == QMessageBox.Ok:
                        # 打开ngrok官网地址
                        self.append_log(f"用户选择前往ngrok官网配置API key", service_name=service.name)
                        import webbrowser
                        webbrowser.open("https://dashboard.ngrok.com/api-keys")
                    elif result == QMessageBox.Cancel:
                        # 终止启动公网服务
                        self.append_log(f"用户取消了公网访问启动", service_name=service.name)
                        return
            
            # 设置公网访问状态为启动中
            service.public_access_status = "starting"
            self.update_service_list()
            
            # 在后台线程中启动ngrok，避免阻塞UI
            def start_ngrok_thread():
                try:
                    # 使用QTimer确保在主线程中调用UI方法
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self.append_log(f"正在为服务 {service.name} 启动ngrok...", service_name=service.name))
                    # 启动ngrok
                    result = service.start_ngrok()
                    if isinstance(result, str):
                        if result.startswith("http"):
                            # 返回的是公网URL
                            QTimer.singleShot(0, lambda: self.append_log(f"ngrok已成功启动，公网URL: {result}", service_name=service.name))
                            QTimer.singleShot(0, lambda: self.append_log(f"服务 {service.name} 公网访问已启用", service_name=service.name))
                        else:
                            # 返回的是错误信息
                            error_msg = f"ngrok启动失败: {result}"
                            QTimer.singleShot(0, lambda: self.append_log(error_msg, error=True, service_name=service.name))
                            QTimer.singleShot(0, lambda: self.append_log(f"服务 {service.name} 公网访问启动失败", error=True, service_name=service.name))
                            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "ngrok启动失败", error_msg))
                    else:
                        QTimer.singleShot(0, lambda: self.append_log(f"ngrok启动失败，无法获取公网URL", error=True, service_name=service.name))
                        QTimer.singleShot(0, lambda: self.append_log(f"服务 {service.name} 公网访问启动失败", error=True, service_name=service.name))
                except Exception as e:
                    error_msg = f"启动ngrok失败: {str(e)}"
                    QTimer.singleShot(0, lambda: self.append_log(error_msg, error=True, service_name=service.name))
                    QTimer.singleShot(0, lambda: self.append_log(f"服务 {service.name} 公网访问启动失败", error=True, service_name=service.name))
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "ngrok启动失败", error_msg))
                finally:
                    # 使用QTimer确保在主线程中调用UI方法
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self.update_service_list)
                    QTimer.singleShot(0, lambda: self.update_public_access_ui(service))
            
            thread = threading.Thread(target=start_ngrok_thread)
            thread.daemon = True
            thread.start()
    
    def stop_public_access(self, index):
        """停止公网访问"""
        if 0 <= index < len(self.manager.services):
            service = self.manager.services[index]
            # 使用QTimer确保在主线程中调用UI方法
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.append_log(f"用户请求为服务 {service.name} 停止公网访问", service_name=service.name))
            QTimer.singleShot(0, lambda: self.append_log(f"正在为服务 {service.name} 停止ngrok...", service_name=service.name))
            service.stop_ngrok()
            QTimer.singleShot(0, lambda: self.append_log(f"ngrok已成功停止", service_name=service.name))
            QTimer.singleShot(0, lambda: self.append_log(f"服务 {service.name} 公网访问已停止", service_name=service.name))
            QTimer.singleShot(0, self.update_service_list)
    
    def update_service_list(self):
        """更新服务列表"""
        # 记录当前选中的服务名称（用于刷新后恢复选择）
        selected_names = [item.text(0) for item in self.service_tree.selectedItems()]
        
        # 清空现有列表
        self.service_tree.clear()
        
        # 添加服务到列表
        for i, service in enumerate(self.manager.services):
            # 格式化认证信息
            auth_info = ""
            if service.auth_rules:
                username = service.auth_rules[0].get("username", "")
                password = service.auth_rules[0].get("password", "")
                auth_info = f"{username}:{password}"
            
            # 格式化权限信息
            perms_info = []
            if service.allow_upload:
                perms_info.append("上传")
            if service.allow_delete:
                perms_info.append("删除")
            perms_text = ", ".join(perms_info) if perms_info else ""
            
            # 创建树项（添加公网访问列）
            status = service.status
            
            # 状态可视化增强，使用更直观的emoji图标
            status_emoji = "❓"
            if status == ServiceStatus.RUNNING:
                status_emoji = "🟢"
            elif status == ServiceStatus.STARTING:
                status_emoji = "🟡"
            elif status == ServiceStatus.STOPPED:
                status_emoji = "🔴"
            elif status == ServiceStatus.ERROR:
                status_emoji = "🟠"
            
            # 显示带图标的状态
            status_with_icon = f"{status_emoji} {status}"
            
            # 创建树项，公网访问列根据服务状态显示不同内容
            public_access_text = ""
            if service.status != ServiceStatus.RUNNING:
                public_access_text = "请先启动服务"
            elif service.public_access_status == "running":
                # 显示完整的公网URL
                public_access_text = service.public_url
            elif service.public_access_status == "starting":
                public_access_text = "启动中..."
            elif service.public_access_status == "stopping":
                public_access_text = "停止中..."
            else:
                public_access_text = "点击启动"
            
            # 合并认证和权限为详情列，使用图标表示权限
            perms_icons = ""
            if service.allow_upload:
                perms_icons += "📤"
            if service.allow_delete:
                perms_icons += "🗑️"
            
            # 详情列格式："user:pass (📤🗑️) - 路径"
            details_text = ""
            if auth_info:
                details_text += f"{auth_info} "
            if perms_icons:
                details_text += f"({perms_icons}) "
            details_text += f"- {service.serve_path}"
            
            item = QTreeWidgetItem([
                service.name,
                service.port,
                status_with_icon,
                public_access_text,
                details_text
            ])
            
            # 设置所有列的内容居中显示
            for col in range(self.service_tree.columnCount()):
                item.setTextAlignment(col, Qt.AlignCenter)
            
            # 设置状态列的文本颜色（状态列是索引2）
            color = AppConstants.STATUS_COLORS.get(status, "#95a5a6")  # 默认灰色
            item.setForeground(2, QColor(color))
            
            # 先将树项添加到树控件中
            self.service_tree.addTopLevelItem(item)
            
            # 不再在服务列表中显示公网访问按钮，改为通过右键菜单操作
            # 公网访问状态已通过文本显示在第4列
            
            # 然后将服务在self.manager.services列表中的实际索引存储到树项中
            item.setData(0, Qt.UserRole, i)
            
            # 恢复选中状态（刷新列表后保留之前的选择）
            is_selected = service.name in selected_names
            item.setSelected(is_selected)
        
        # 更新状态栏服务计数
        self.update_status_bar()
        
        # 更新访问地址，确保当前选中服务的地址显示在地址栏中
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            index = selected_item.data(0, Qt.UserRole)
            if index is not None:
                self.refresh_address(index)
    
    def add_service(self):
        """添加新服务"""
        dialog = DufsServiceDialog(self, existing_services=self.manager.services)
        if dialog.exec_():
            service = dialog.service
            # 设置gui_instance属性，以便服务可以访问GUI的日志功能
            service.gui_instance = self
            self.manager.add_service(service)
            self.status_updated.emit()
            self.status_bar.showMessage(f"已添加服务: {service.name}")
            
            # 使用QTimer延迟执行耗时操作，避免卡顿
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, self.refresh_tray_menu)  # 延迟刷新托盘菜单
            QTimer.singleShot(300, self.save_config)  # 延迟保存配置
    
    def edit_service(self, item=None, column=None):
        """编辑选中的服务"""
        if not item:
            selected_items = self.service_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择要编辑的服务")
                return
            # 检查是否只选择了一个服务
            if len(selected_items) > 1:
                QMessageBox.warning(self, "提示", "仅可对一个服务进行编辑")
                return
            selected_item = selected_items[0]
            # 从树项中获取服务在self.manager.services列表中的实际索引
            index = selected_item.data(0, Qt.UserRole)
        else:
            # 从树项中获取服务在self.manager.services列表中的实际索引
            index = item.data(0, Qt.UserRole)
        
        service = self.manager.services[index]
        dialog = DufsServiceDialog(self, service=service, edit_index=index, existing_services=self.manager.services)
        if dialog.exec_():
            # 检查服务配置是否真正发生了变化
            # 比较关键配置项
            config_changed = False
            if (dialog.service.name != service.name or
                dialog.service.port != service.port or
                dialog.service.serve_path != service.serve_path or
                dialog.service.allow_upload != service.allow_upload or
                dialog.service.allow_delete != service.allow_delete or
                dialog.service.allow_search != service.allow_search or
                dialog.service.allow_archive != service.allow_archive):
                config_changed = True
            
            # 比较auth_rules内容，而不是对象本身
            # 检查auth_rules列表长度
            if len(dialog.service.auth_rules) != len(service.auth_rules):
                config_changed = True
            else:
                # 检查每个auth_rule的内容
                for new_rule, old_rule in zip(dialog.service.auth_rules, service.auth_rules):
                    if (new_rule.get("username", "") != old_rule.get("username", "") or
                        new_rule.get("password", "") != old_rule.get("password", "") or
                        new_rule.get("paths", []) != old_rule.get("paths", [])):
                        config_changed = True
                        break
            
            if not config_changed:
                # 配置未变化，直接返回，不执行重启
                return
            
            # 保存服务当前状态（是否运行中）
            was_running = service.status == ServiceStatus.RUNNING
            
            # 如果服务之前是运行中的，先停止旧服务
            if was_running:
                # 停止旧服务
                self.stop_service(index)
            
            # 更新服务
            self.manager.edit_service(index, dialog.service)
            self.status_updated.emit()
            
            # 如果服务之前是运行中的，启动新服务
            if was_running:
                QMessageBox.information(self, "提示", "服务配置已更改，服务将自动重启以应用新配置。")
                self.start_service(index)
            
            # 使用QTimer延迟执行耗时操作，避免卡顿
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, self.refresh_tray_menu)  # 延迟刷新托盘菜单
            QTimer.singleShot(300, self.save_config)  # 延迟保存配置
    
    def start_service_from_button(self):
        """从主面板按钮启动服务"""
        self._start_service_from_ui()
    
    def _start_service_from_ui(self):
        """从UI启动服务的通用逻辑"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要启动的服务")
            return
        
        # 单选模式下，只处理第一个选中项
        selected_item = selected_items[0]
        # 从树项中获取服务在self.manager.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)
        
        # 调用带索引的启动服务方法
        self.start_service(index)
    
    def stop_service_from_button(self):
        """从主面板按钮停止服务"""
        self._stop_service_from_ui()
    
    def _stop_service_from_ui(self):
        """从UI停止服务的通用逻辑"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要停止的服务")
            return
        
        # 单选模式下，只处理第一个选中项
        selected_item = selected_items[0]
        # 从树项中获取服务在self.manager.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)
        
        # 调用带索引的停止服务方法
        self.stop_service(index)
    
    def delete_service(self):
        """删除选中的服务"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的服务")
            return
        
        # 单选模式下，只处理第一个选中项
        selected_item = selected_items[0]
        # 从树项中获取服务在self.manager.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)
        
        # 确保索引有效
        if not isinstance(index, int) or index < 0 or index >= len(self.manager.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return
        
        service = self.manager.services[index]
        
        # 显示确认框
        if QMessageBox.question(self, "提示", f"确定要删除服务 '{service.name}' 吗？") != QMessageBox.Yes:
            return
        
        # 关闭服务的日志标签页（如果存在）
        if service.log_widget and service.log_tab_index is not None:
            self.close_log_tab(service.log_tab_index)
        
        # 确认删除后，如果服务正在运行，先停止
        if service.status == ServiceStatus.RUNNING:
            self.stop_service(index)
        
        # 删除服务
        self.manager.remove_service(index)
        
        # 更新服务列表
        self.status_updated.emit()
        
        # 刷新托盘菜单，更新服务列表
        self.refresh_tray_menu()
        
        # 更新状态栏
        self.status_bar.showMessage(f"已删除服务: {service.name}")
        
        # 保存配置
        self.save_config()
    
    def start_all_services(self):
        """启动所有服务"""
        # 显示进度对话框
        progress_dialog = QProgressDialog("正在启动所有服务...", "取消", 0, len(self.manager.services))
        progress_dialog.setWindowTitle("启动全部")
        progress_dialog.setModal(True)
        progress_dialog.setValue(0)
        progress_dialog.show()
        
        # 启动所有服务
        for i, service in enumerate(self.manager.services):
            # 更新进度
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"正在启动服务: {service.name}")
            QApplication.processEvents()
            
            # 检查是否取消
            if progress_dialog.wasCanceled():
                break
            
            # 启动服务
            if service.status != ServiceStatus.RUNNING:
                self.start_service(i)
        
        # 完成进度
        progress_dialog.setValue(len(self.manager.services))
        progress_dialog.close()
        
        # 更新状态栏
        running_count = len([s for s in self.manager.services if s.status == ServiceStatus.RUNNING])
        self.status_bar.showMessage(f"已启动 {running_count}/{len(self.manager.services)} 个服务")
    
    def stop_all_services(self):
        """停止所有服务"""
        # 显示进度对话框
        progress_dialog = QProgressDialog("正在停止所有服务...", "取消", 0, len(self.manager.services))
        progress_dialog.setWindowTitle("停止全部")
        progress_dialog.setModal(True)
        progress_dialog.setValue(0)
        progress_dialog.show()
        
        # 停止所有服务
        for i, service in enumerate(self.manager.services):
            # 更新进度
            progress_dialog.setValue(i)
            progress_dialog.setLabelText(f"正在停止服务: {service.name}")
            QApplication.processEvents()
            
            # 检查是否取消
            if progress_dialog.wasCanceled():
                break
            
            # 停止服务
            if service.status == ServiceStatus.RUNNING:
                self.stop_service(i)
        
        # 完成进度
        progress_dialog.setValue(len(self.manager.services))
        progress_dialog.close()
        
        # 更新状态栏
        self.status_bar.showMessage(f"已停止所有服务")
    
    def export_config(self):
        """导出服务配置"""
        # 选择导出文件路径
        file_path, _ = QFileDialog.getSaveFileName(self, "导出配置", os.path.expanduser("~"), "JSON Files (*.json)")
        if not file_path:
            return
        
        # 准备配置数据
        config_data = {
            "services": [],
            "ngrok": {
                "authtoken": getattr(self, "ngrok_authtoken", ""),
                "api_key": getattr(self, "ngrok_api_key", ""),
                "mode": getattr(self, "ngrok_mode", "authtoken")
            }
        }
        
        # 收集服务配置
        for service in self.manager.services:
            service_config = {
                "name": service.name,
                "port": service.port,
                "serve_path": service.serve_path,
                "allow_upload": service.allow_upload,
                "allow_delete": service.allow_delete,
                "allow_search": service.allow_search,
                "allow_archive": service.allow_archive,
                "bind": service.bind,
                "auth_rules": service.auth_rules
            }
            config_data["services"].append(service_config)
        
        # 保存配置到文件
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", f"配置已成功导出到 {file_path}")
            self.status_bar.showMessage(f"配置已成功导出到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出配置失败: {str(e)}")
            self.status_bar.showMessage(f"导出配置失败: {str(e)}")
    
    def toggle_log_panel(self):
        """切换日志面板的显示/隐藏"""
        # 获取当前分割窗大小
        current_sizes = self.splitter.sizes()
        total_height = sum(current_sizes)
        
        # 获取日志面板部件（第二个部件）
        log_widget = self.splitter.widget(1)
        
        # 检查日志面板是否处于折叠状态
        is_collapsed = current_sizes[1] < 150  # 使用最小高度作为判断标准
        
        if is_collapsed:
            # 展开日志面板
            # 恢复正常最小高度
            log_widget.setMinimumHeight(150)
            # 默认占40%高度
            log_height = int(total_height * 0.4)
            self.splitter.setSizes([total_height - log_height, log_height])
            self.log_toggle_btn.setText("收起日志")
        else:
            # 折叠日志面板，完全隐藏
            # 设置最小高度为0
            log_widget.setMinimumHeight(0)
            # 将高度设置为0
            self.splitter.setSizes([total_height, 0])
            self.log_toggle_btn.setText("展开日志")
    
    def toggle_log_window(self):
        """显示/隐藏独立日志窗口"""
        if self.log_window is None:
            # 创建独立日志窗口
            self.log_window = LogWindow(self)
            
            # 为所有已创建日志控件的服务添加日志标签页
            for service in self.manager.services:
                if service.log_widget is not None:
                    # 优化Tab标题，显示关键信息
                    status_icon = self._get_status_icon(service.status)
                    title = f"{status_icon} 服务 {service.name} | {service.port} | {service.status}"
                    self.log_window.add_log_tab(title, service.log_widget)
        
        if self.log_window.isVisible():
            self.log_window.hide()
            self.log_window_btn.setText("显示日志窗口")
        else:
            self.log_window.show()
            self.log_window_btn.setText("隐藏日志窗口")
    
    def create_service_log_tab(self, service):
        """为服务创建专属日志Tab，只添加到独立日志窗口"""
        log_view = QPlainTextEdit()
        log_view.setReadOnly(True)
        log_view.setStyleSheet("""
            font-family: 'Consolas', 'Monaco', monospace; 
            font-size: 12px; 
            background-color: #0f111a; 
            color: #c0c0c0;
            border: 1px solid #333;
        """)
        log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        log_view.setMaximumBlockCount(AppConstants.MAX_LOG_LINES)
        
        # 优化Tab标题，显示关键信息
        status_icon = self._get_status_icon(service.status)
        title = f"{status_icon} 服务 {service.name} | {service.port} | {service.status}"
        
        # 绑定服务与日志控件
        service.log_widget = log_view
        service.log_tab_index = 0
        
        # 如果独立日志窗口已创建，添加到独立窗口
        if self.log_window is not None:
            self.log_window.add_log_tab(title, log_view)
    
    def start_service(self, index=None):
        """启动选中的服务"""
        try:
            # 获取并验证服务索引
            index = self._get_service_index(index)
            if index is None:
                return
            
            # 获取服务对象
            service = self.manager.services[index]
            
            # 检查服务是否已经在运行或启动中，如果是则直接返回
            if service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                self.append_log(f"服务 {service.name} 已经在{service.status}，无需重复启动", service_name=service.name, service=service)
                return
            
            # 查找可用端口
            available_port = self._find_available_port(service)
            if available_port is None:
                return
            
            # 构建命令
            command = self._build_command(service, available_port)
            if command is None:
                return
            
            # 设置服务状态为启动中，防止重复启动
            service.status = ServiceStatus.STARTING
            self.status_updated.emit()
            
            # 启动服务进程
            if not self._start_service_process(service, command):
                # 启动失败，重置状态为未运行
                service.status = ServiceStatus.STOPPED
                self.status_updated.emit()
                return
            
            # 启动服务启动检查定时器
            self._start_service_check_timer(service, index)
            
        except Exception as e:
            # 记录错误信息
            service = self.manager.services[index] if index is not None and 0 <= index < len(self.manager.services) else None
            service_name = service.name if service else "未知服务"
            self.append_log(f"启动服务失败: {str(e)}", error=True, service_name=service_name)
            # 显示错误信息
            error_msg = f"启动服务失败: {str(e)}"
            if 'command' in locals():
                error_msg += f"\n执行命令: {' '.join(command)}"
            error_msg += f"\n当前目录: {os.getcwd()}"
            if service:
                error_msg += f"\n服务工作目录: {service.serve_path}"
                # 确保服务状态被重置为未运行
                with service.lock:
                    service.status = ServiceStatus.STOPPED
                    service.process = None
                self.status_updated.emit()
            QMessageBox.critical(self, "错误", error_msg)
    
    def _get_service_index(self, index):
        """获取并验证服务索引"""
        # 如果没有提供索引，获取当前选中的服务索引
        if index is None:
            selected_items = self.service_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择要启动的服务")
                return None
            # 单选模式下，只处理第一个选中项
            selected_item = selected_items[0]
            # 从树项中获取服务在self.manager.services列表中的实际索引
            index = selected_item.data(0, Qt.UserRole)
        
        # 确保索引是有效的数字
        if not isinstance(index, int) or index < 0 or index >= len(self.manager.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return None
        
        return index
    
    def _find_available_port(self, service):
        """查找可用端口"""
        # 系统常用、浏览器黑名单、特殊软件常用端口黑名单（只包含真正需要屏蔽的端口）
        blocked_ports = {
            # 系统常用端口（真正需要屏蔽的）
            20, 21, 22, 23, 25, 53, 67, 68, 80, 443, 110, 143, 161, 162, 389, 445, 514, 636, 993, 995,
            # 数据库端口
            1433, 1521, 3306, 3389, 5432, 6446, 6447, 6379, 27017, 28017, 9200, 9300,
            # 常见危险端口
            4444, 5555, 6666, 7777, 8888, 9999, 12345, 12346, 12347, 16992, 16993
        }
        
        # 尝试获取可用端口，最多尝试AppConstants.PORT_TRY_LIMIT次
        try:
            original_port = int(service.port.strip())
            
            # 端口范围验证
            if original_port < 1 or original_port > 65535:
                QMessageBox.critical(
                    self,
                    "错误",
                    f"端口 {original_port} 无效。\n端口必须在1-65535之间。"
                )
                return None
        except ValueError:
            # 处理非数字端口的情况
            QMessageBox.critical(
                self,
                "错误",
                f"端口 '{service.port}' 无效。\n请输入有效的数字端口。"
            )
            return None
        
        available_port = None
        
        # 从原始端口开始尝试，如果被占用则尝试更高的端口
        for i in range(AppConstants.PORT_TRY_LIMIT):
            try_port = original_port + i
            
            # 跳过常用屏蔽端口
            if try_port in blocked_ports:
                continue
            
            # 检查端口是否可用，排除当前服务
            if self.manager.check_port_available(try_port, exclude_service=service):
                available_port = try_port
                break
        
        # 如果没有找到可用端口，尝试从一个较高的起始端口开始
        if not available_port:
            start_port = AppConstants.BACKUP_START_PORT
            for i in range(AppConstants.PORT_TRY_LIMIT_BACKUP):
                try_port = start_port + i
                
                # 跳过常用屏蔽端口
                if try_port in blocked_ports:
                    continue
                
                # 检查端口是否可用，排除当前服务
                if self.manager.check_port_available(try_port, exclude_service=service):
                    available_port = try_port
                    break
        
        # 如果找到了可用端口，更新服务端口
        if available_port:
            # 如果端口有变化，更新服务端口
            if available_port != original_port:
                service.port = str(available_port)
                # 更新服务列表显示
                self.status_updated.emit()
                # 提示用户端口已自动更换
                QMessageBox.information(self, "提示", f"端口 {original_port} 被占用，已自动更换为 {available_port}")
            return available_port
        else:
            # 尝试了多个端口都不可用，提示用户
            QMessageBox.critical(
                self,
                "错误",
                f"端口 {original_port} 不可用，尝试了多个端口都不可用。\n" +
                "请手动更换端口。"
            )
            return None
    
    def _sanitize_command_argument(self, arg):
        """清理命令行参数，防止注入攻击
        
        Args:
            arg (str): 要清理的命令行参数
            
        Returns:
            str: 清理后的安全参数
        """
        if not arg:
            return arg
        
        # 移除首尾空白字符
        arg = arg.strip()
        
        if os.name == 'nt':  # Windows系统
            # 移除Windows特有的危险字符，防止命令注入
            dangerous_chars = ['&', '|', '<', '>', '^', '%']
            for char in dangerous_chars:
                arg = arg.replace(char, '')
        else:  # Unix-like系统
            # 使用shlex.quote进行安全引用
            import shlex
            arg = shlex.quote(arg)
        
        return arg
    
    def _validate_service_path(self, path):
        """验证服务路径安全性
        
        Args:
            path (str): 要验证的服务路径
            
        Returns:
            str: 验证通过后的规范化路径
            
        Raises:
            ValueError: 路径不安全时抛出异常
        """
        if not path or not isinstance(path, str):
            raise ValueError("无效的服务路径")
        
        # 规范化路径，确保是绝对路径
        normalized_path = os.path.normpath(os.path.abspath(path))
        
        # 限制路径深度，防止路径遍历攻击
        path_depth = normalized_path.count(os.sep)
        if path_depth > AppConstants.MAX_PATH_DEPTH:
            raise ValueError(f"路径层级过深，最多允许{AppConstants.MAX_PATH_DEPTH}级目录")
        
        # 防止使用系统关键目录作为服务路径
        forbidden_paths = []
        if os.name == 'nt':  # Windows系统
            # Windows系统关键目录
            forbidden_paths = [
                os.environ.get("SystemRoot", "C:\\Windows"),
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                os.environ.get("APPDATA", "C:\\Users\\" + os.environ.get("USERNAME", "") + "\\AppData\\Roaming"),
                os.environ.get("LOCALAPPDATA", "C:\\Users\\" + os.environ.get("USERNAME", "") + "\\AppData\\Local")
            ]
        else:  # Unix-like系统
            # Unix系统关键目录
            forbidden_paths = [
                "/etc",
                "/bin",
                "/sbin",
                "/usr",
                "/lib",
                "/lib64",
                "/proc",
                "/sys",
                "/dev",
                "/boot"
            ]
        
        # 检查路径是否在系统关键目录内
        for forbidden in forbidden_paths:
            if forbidden and normalized_path.startswith(os.path.normpath(forbidden)):
                raise ValueError(f"禁止使用系统关键目录作为服务路径: {forbidden}")
        
        # 检查路径是否存在且可访问
        if not os.path.exists(normalized_path):
            raise ValueError(f"路径不存在: {normalized_path}")
        
        if not os.path.isdir(normalized_path):
            raise ValueError(f"路径不是目录: {normalized_path}")
        
        # 检查是否有读取权限
        if not os.access(normalized_path, os.R_OK):
            raise ValueError(f"对路径没有读取权限: {normalized_path}")
        
        return normalized_path
    
    def cleanup_service_resources(self, service):
        """确保彻底清理服务相关资源
        
        Args:
            service (DufsService): 要清理资源的服务对象
        """
        with service.lock:
            # 1. 设置日志线程终止标志
            service.log_thread_terminate = True
            
            # 2. 关闭进程IO流，防止资源泄漏
            if service.process:
                try:
                    if service.process.stdout:
                        service.process.stdout.close()
                    if service.process.stderr:
                        service.process.stderr.close()
                except Exception as e:
                    self.append_log(f"关闭进程IO流失败: {str(e)}", error=True, service_name=service.name)
            
            # 3. 终止并释放进程对象
            if service.process:
                try:
                    # 先尝试优雅终止
                    service.process.terminate()
                    # 等待进程终止
                    service.process.wait(timeout=AppConstants.PROCESS_TERMINATE_TIMEOUT)
                except subprocess.TimeoutExpired:
                    # 超时后强制终止
                    service.process.kill()
                except Exception as e:
                    self.append_log(f"终止进程失败: {str(e)}", error=True, service_name=service.name)
                finally:
                    # 释放进程对象
                    service.process = None
            
            # 4. 清理日志界面资源
            if service.log_widget:
                try:
                    # 移除日志控件
                    service.log_widget.deleteLater()
                except Exception as e:
                    self.append_log(f"清理日志控件失败: {str(e)}", error=True, service_name=service.name)
                finally:
                    service.log_widget = None
    
    def _add_basic_params(self, command, service, available_port):
        """添加基本参数：端口、绑定地址等"""
        service_port = str(available_port)
        service_bind = self._sanitize_command_argument(service.bind)
        
        # 确保服务端口已更新
        service.port = service_port
        
        # 添加基本参数
        command.extend(["--port", service_port])
        if service_bind:
            command.extend(["--bind", service_bind])
    
    def _add_permission_params(self, command, service):
        """添加权限相关参数"""
        if service.allow_all:
            command.append("--allow-all")
        else:
            if service.allow_upload:
                command.append("--allow-upload")
            if service.allow_delete:
                command.append("--allow-delete")
            if hasattr(service, 'allow_symlink') and service.allow_symlink:
                command.append("--allow-symlink")
        # 总是开启搜索功能
        command.append("--allow-search")
        # 总是开启打包下载功能
        command.append("--allow-archive")
    
    def _add_auth_params(self, command, service):
        """添加认证相关参数"""
        if service.auth_rules and isinstance(service.auth_rules, list) and len(service.auth_rules) > 0:
            for rule in service.auth_rules:
                if isinstance(rule, dict):
                    username = self._sanitize_command_argument(rule.get("username", "").strip())
                    password = self._sanitize_command_argument(rule.get("password", "").strip())
                    
                    if username and password:
                        auth_rule = f"{username}:{password}@/:rw"
                        command.extend(["--auth", auth_rule])
        else:
            # 允许匿名访问，确保tokengen功能正常
            command.extend(["--auth", "@/:rw"])
    
    def _add_service_path(self, command, service):
        """添加服务路径参数"""
        # 服务路径空值检查
        service_serve_path = service.serve_path.strip()
        if not service_serve_path:
            raise ValueError("服务路径不能为空")
        
        # 添加服务根目录，并进行安全清理
        command.append(self._sanitize_command_argument(service_serve_path))
    
    def _build_command(self, service, available_port):
        """构建启动命令，协调各部分配置"""
        # 使用dufs.exe的完整路径
        dufs_path = get_resource_path("dufs.exe")
        
        # 检查dufs.exe是否存在
        self.append_log(f"获取到的dufs.exe路径: {dufs_path}", service_name=service.name)
        if not os.path.exists(dufs_path):
            self.append_log(f"dufs.exe不存在于路径: {dufs_path}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"dufs.exe不存在于路径: {dufs_path}")
            return None
        
        command = [dufs_path]
        
        try:
            # 依次添加各部分参数
            self._add_basic_params(command, service, available_port)
            self._add_permission_params(command, service)
            self._add_auth_params(command, service)
            
            # 添加日志格式参数（在服务路径之前）
            command.extend(["--log-format", "$remote_addr \"$request\" $status"])
            
            self._add_service_path(command, service)
            
            return command
        except ValueError as e:
            self.append_log(f"构建命令失败: {str(e)}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"构建命令失败: {str(e)}")
            return None
    
    def _start_service_process(self, service, command):
        """启动服务进程"""
        # 检查命令是否有效
        if not command or not isinstance(command, list):
            self.append_log(f"启动服务失败: 无效的命令", error=True, service_name=service.name)
            return False
        
        # 检查服务是否已经在运行，如果是则直接返回
        if service.status == ServiceStatus.RUNNING:
            self.append_log(f"服务 {service.name} 已经在运行中，无需重复启动", service_name=service.name, service=service)
            return False
        
        # 记录完整的命令信息（使用repr处理带空格的路径）
        command_str = " ".join([repr(arg) if ' ' in arg else arg for arg in command])
        self.append_log(f"构建的命令: {command_str}", service_name=service.name)
        
        # 检查 dufs.exe 是否存在
        dufs_path = command[0]
        self.append_log(f"检查 dufs.exe 路径: {dufs_path}", service_name=service.name)
        if not os.path.exists(dufs_path):
            self.append_log(f"启动服务失败: dufs.exe 不存在 - 路径: {dufs_path}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"启动服务失败: dufs.exe 不存在\n路径: {dufs_path}")
            return False
        
        # 检查服务路径是否存在
        self.append_log(f"检查服务路径: {service.serve_path}", service_name=service.name)
        if not os.path.exists(service.serve_path):
            self.append_log(f"启动服务失败: 服务路径不存在 - 路径: {service.serve_path}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径不存在\n路径: {service.serve_path}")
            return False
        
        # 检查服务路径是否为目录
        if not os.path.isdir(service.serve_path):
            self.append_log(f"启动服务失败: 服务路径必须是目录 - 路径: {service.serve_path}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径必须是目录\n路径: {service.serve_path}")
            return False
        
        # 更充分的服务路径权限检查
        # 1. 首先检查读取权限（基本权限）
        if not os.access(service.serve_path, os.R_OK):
            self.append_log(f"启动服务失败: 服务路径不可访问（缺少读取权限） - 路径: {service.serve_path}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径不可访问（缺少读取权限）\n路径: {service.serve_path}")
            return False
        
        # 2. 如果允许上传，检查写入权限
        if service.allow_all or service.allow_upload:
            if not os.access(service.serve_path, os.W_OK):
                self.append_log(f"启动服务失败: 服务路径不可访问（缺少写入权限） - 路径: {service.serve_path}", error=True, service_name=service.name)
                QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径不可访问（缺少写入权限）\n路径: {service.serve_path}")
                return False
        
        # 3. 如果允许删除，检查写入和执行权限
        if service.allow_all or service.allow_delete:
            if not os.access(service.serve_path, os.W_OK | os.X_OK):
                self.append_log(f"启动服务失败: 服务路径不可访问（缺少写入和执行权限） - 路径: {service.serve_path}", error=True, service_name=service.name)
                QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径不可访问（缺少写入和执行权限）\n路径: {service.serve_path}")
                return False
        
        # 记录服务启动信息
        self.append_log(f"启动 DUFS...", service_name=service.name)
        
        # 启动进程 - 使用正确的参数
        # 不要设置工作目录为dufs.exe所在目录，特别是在单文件打包模式下，这可能导致权限问题
        # 直接使用当前工作目录或服务路径作为工作目录
        cwd = service.serve_path
        
        # 启动进程，捕获输出以支持实时日志
        creation_flags = 0
        if os.name == 'nt':  # Windows系统
            creation_flags = subprocess.CREATE_NO_WINDOW  # 隐藏命令窗口
        
        # 启动服务进程
        self.append_log(f"执行命令: {' '.join(command)}", service_name=service.name)
        
        try:
            service.process = subprocess.Popen(
                command,
                cwd=cwd,  # 使用服务路径作为工作目录
                shell=False,  # 不使用shell执行
                env=os.environ.copy(),  # 复制当前环境变量
                stdout=subprocess.PIPE,  # 捕获标准输出
                stderr=subprocess.PIPE,  # 捕获标准错误
                text=False,  # 使用字节模式，手动处理UTF-8编码
                bufsize=0,  # 无缓冲，在二进制模式下可靠工作
                universal_newlines=False,  # 不自动处理换行符
                creationflags=creation_flags  # 隐藏命令窗口
            )
            
            self.append_log(f"进程已启动，PID: {service.process.pid}", service_name=service.name)
        except Exception as e:
            self.append_log(f"启动进程失败: {str(e)}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"启动进程失败: {str(e)}")
            return False
        
        # 为服务创建专属日志Tab（提前创建，确保日志不丢失）
        self.create_service_log_tab(service)
        
        # 启动日志读取线程（延迟150ms，避免Windows pipe初始阻塞）
        self.append_log(f"启动日志读取线程", service_name=service.name)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(150, lambda: self.stream_log(service.process, service))
        
        return True
    
    def _start_service_check_timer(self, service, index):
        """启动服务启动检查定时器"""
        # 创建一个单次定时器，延迟检查服务状态
        timer = QTimer(self)
        timer.setSingleShot(True)
        # 使用lambda来传递服务对象和索引，同时避免闭包陷阱
        timer.timeout.connect(lambda: self._delayed_check_service_started(service, index, timer))
        # 设置延迟时间，将秒转换为整数毫秒
        timer.start(int(AppConstants.SERVICE_START_WAIT_SECONDS * 1000))
    
    def _delayed_check_service_started(self, service, index, timer):
        """延迟检查服务是否成功启动"""
        # 确保定时器被释放
        timer.deleteLater()
        
        # 检查进程是否还在运行
        # 使用线程锁保护共享资源
        with service.lock:
            if service.process is None:
                self.append_log(f"服务进程已被释放，跳过状态检查", service_name=service.name)
                return False
            
            poll_result = service.process.poll()
            self.append_log(f"进程状态检查结果: {poll_result}", service_name=service.name)
            if poll_result is not None:
                # 进程已退出，说明启动失败
                # 尝试读取stdout和stderr获取详细错误信息
                stdout_output = b""
                stderr_output = b""
                try:
                    # 尝试读取所有剩余输出
                    if service.process.stdout:
                        stdout_output = service.process.stdout.read()
                        stdout_output = stdout_output.decode('utf-8', errors='replace')
                    if service.process.stderr:
                        stderr_output = service.process.stderr.read()
                        stderr_output = stderr_output.decode('utf-8', errors='replace')
                    
                    if stdout_output:
                        self.append_log(f"进程退出，stdout: {stdout_output}", error=True, service_name=service.name)
                    if stderr_output:
                        self.append_log(f"进程退出，stderr: {stderr_output}", error=True, service_name=service.name)
                except Exception as e:
                    self.append_log(f"读取进程输出失败: {str(e)}", error=True, service_name=service.name)
                
                # 设置日志线程终止标志
                service.log_thread_terminate = True
                
                # 释放进程资源
                service.process = None
                service.status = ServiceStatus.STOPPED
                service.local_addr = ""
            
                error_msg = f"服务启动失败: 进程立即退出，退出码: {poll_result}"
                if stdout_output or stderr_output:
                    error_msg += "\n\n详细输出:"
                    if stdout_output:
                        error_msg += f"\n\n标准输出:\n{stdout_output}"
                    if stderr_output:
                        error_msg += f"\n\n标准错误:\n{stderr_output}"
                
                self.append_log(error_msg, error=True, service_name=service.name)
                QMessageBox.critical(self, "错误", error_msg)
                return False
        
        # 简化服务启动流程，去掉不可靠的异步端口检查
        # 直接调用_update_service_after_start函数更新服务状态
        self.append_log(f"简化服务启动流程，直接更新服务状态", service_name=service.name)
        # 确保在主线程中执行UI更新
        QTimer.singleShot(0, lambda: self._update_service_after_start(service, index))
        return True
    
    def _update_service_after_start(self, service, index):
        """服务启动后更新状态和UI"""
        # 更新服务状态
        with service.lock:
            service.status = ServiceStatus.RUNNING
        
        # 启动监控线程
        threading.Thread(target=self.monitor_service, args=(service, index), daemon=True).start()
        
        # 所有UI操作都通过信号槽机制在主线程中执行
        from PyQt5.QtCore import QTimer
        
        # 记录日志
        QTimer.singleShot(0, lambda: self.append_log(f"进程正常运行，更新服务状态", service_name=service.name, service=service))
        QTimer.singleShot(0, lambda: self.append_log(f"启动监控线程", service_name=service.name, service=service))
        QTimer.singleShot(0, lambda: self.append_log(f"更新服务列表", service_name=service.name, service=service))
        QTimer.singleShot(0, lambda: self.append_log(f"服务启动成功", service_name=service.name, service=service))
        
        # 更新服务列表
        QTimer.singleShot(0, self.status_updated.emit)
        
        # 更新状态栏
        status_msg = f"已启动服务: {service.name} | 访问地址: {service.local_addr}"
        QTimer.singleShot(0, lambda: self.status_bar.showMessage(status_msg))
        
        # 刷新托盘菜单
        QTimer.singleShot(0, self.refresh_tray_menu)
    
    def stop_service(self, index_or_service=None):
        """停止选中的服务
        
        Args:
            index_or_service (int or DufsService, optional): 服务索引或服务对象. Defaults to None.
        """
        # 检查服务列表是否为空
        if not self.manager.services:
            QMessageBox.information(self, "提示", "没有服务正在运行")
            return
        
        # 处理服务对象情况
        if isinstance(index_or_service, DufsService):
            service = index_or_service
            # 获取服务索引
            index = self.manager.services.index(service)
        else:
            # 处理索引情况
            index = index_or_service
            # 如果没有提供索引，获取当前选中的服务索引
            if index is None:
                selected_items = self.service_tree.selectedItems()
                if not selected_items:
                    QMessageBox.warning(self, "提示", "请先选择要停止的服务")
                    return
                # 单选模式下，只处理第一个选中项
                selected_item = selected_items[0]
                # 从树项中获取服务在self.manager.services列表中的实际索引
                index = selected_item.data(0, Qt.UserRole)
            
            # 检查索引是否有效
            if not isinstance(index, int):
                QMessageBox.warning(self, "提示", "请先选择要停止的服务")
                return
            
            # 索引越界保护
            if index < 0 or index >= len(self.manager.services):
                QMessageBox.critical(self, "错误", f"服务索引异常: {index}")
                return
            
            service = self.manager.services[index]
        
        # 进程存在性检查
        if service.process is None or service.process.poll() is not None:
            # 确保服务状态被正确重置
            if service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                with service.lock:
                    service.status = ServiceStatus.STOPPED
                    service.process = None
                self.status_updated.emit()
            QMessageBox.information(self, "提示", "该服务已停止")
            return
        
        # 终止进程
        try:
            # 尝试优雅终止进程
            service.process.terminate()
            # 等待进程终止
            service.process.wait(timeout=AppConstants.PROCESS_TERMINATE_TIMEOUT)
        except subprocess.TimeoutExpired:
            # 超时后强制终止
            service.process.kill()
            try:
                service.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
        except Exception as e:
            self.append_log(f"终止进程失败: {str(e)}", error=True, service_name=service.name)
        
        # 更新服务状态（添加线程锁保护）
        with service.lock:
            service.process = None
            service.status = ServiceStatus.STOPPED
            service.local_addr = ""
            # 设置日志线程终止标志
            service.log_thread_terminate = True
            # 清空日志缓冲区，防止下次启动时续接上一次的日志
            service.log_buffer.clear()
            # 停止日志定时器（如果存在）
            if service.log_timer:
                service.log_timer.stop()
                service.log_timer = None
        
        # 关闭服务的日志Tab
        if service.log_widget:
            # 从主窗口日志标签页中移除（如果存在）
            if self.log_tabs:
                tab_index = self.log_tabs.indexOf(service.log_widget)
                if tab_index != -1:
                    self.log_tabs.removeTab(tab_index)
            
            # 从独立日志窗口中移除（如果存在）
            if self.log_window is not None:
                # 查找日志标签页在独立窗口中的索引
                for i in range(self.log_window.log_tabs.count()):
                    if self.log_window.log_tabs.widget(i) == service.log_widget:
                        self.log_window.remove_log_tab(i)
                        break
            
            # 清空服务的日志相关属性
            service.log_widget = None
            service.log_tab_index = None
        
        # 记录服务停止信息
        self.append_log(f"已停止服务", service_name=service.name, service=service)
        
        # 更新服务列表
        self.status_updated.emit()
        
        # 清空地址显示
        self.addr_edit.setText("")
        
        # 更新状态栏
        self.status_bar.showMessage(f"已停止服务: {service.name}")
        
        # 刷新托盘菜单
        self.refresh_tray_menu()
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
        Dufs多服务管理 - 快速入门
        添加服务: 点击"添加服务"按钮，设置服务名称、路径和端口
        启动服务: 选择服务，点击"启动服务"按钮
        公网访问: 启动服务后，点击"公网访问"按钮获取公网URL
        安全提示: 强烈建议启用认证功能保护您的共享文件夹
        免费版限制: ngrok免费版URL每次重启会变化，建议使用Dufs内置认证
        """
        
        QMessageBox.information(self, "Dufs帮助", help_text, QMessageBox.Ok)
    
    def monitor_service(self, service, index):
        """监控服务状态"""
        while True:
            # 检查服务是否仍在运行
            with service.lock:
                if service.status != ServiceStatus.RUNNING or service.process is None:
                    break
                # 在锁内获取进程对象引用并检查状态
                current_process = service.process
                if current_process is not None:
                    poll_result = current_process.poll()
                else:
                    poll_result = None
            
            # 检查进程是否还在运行
            if poll_result is not None:
                # 进程已退出
                with service.lock:
                    service.process = None
                    service.status = ServiceStatus.STOPPED
                    service.local_addr = ""
                
                # 更新服务列表
                self.status_updated.emit()
                
                # 更新状态栏
                self.status_bar.showMessage(f"服务已停止: {service.name}")
                
                # 记录日志
                self.append_log(f"服务异常退出", error=True, service_name=service.name)
                
                # 刷新托盘菜单
                self.refresh_tray_menu()
                break
            
            # 双校验：检查端口是否可访问
            # 注意：删除服务确认过程中可能会导致短暂的端口不可访问，因此此处不自动停止服务
            # 只记录日志，不执行自动停止逻辑
            try:
                port = int(service.port)
                if not self.is_port_open(port):
                    # 端口不可访问，记录日志但不自动停止服务
                    self.append_log(f"服务进程存在但端口 {port} 暂时不可访问", service_name=service.name)
            except Exception as e:
                self.append_log(f"监控端口状态异常: {str(e)}", error=True, service_name=service.name)
            
            # 控制循环频率，避免占用过多CPU资源
            time.sleep(1)


# 主入口代码
if __name__ == "__main__":
    # 导入QtCore模块用于日志过滤
    from PyQt5.QtCore import Qt, QLoggingCategory
    
    # 禁用Qt的字体枚举警告
    QLoggingCategory.setFilterRules("qt.qpa.fonts=false")
    
    app = QApplication(sys.argv)
    
    # 设置应用程序字体，使用安全的字体族
    font = QFont()
    font.setFamily("Microsoft YaHei")
    font.setPointSize(12)
    app.setFont(font)
    
    # 设置窗口图标
    icon_path = get_resource_path("icon.ico")
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = DufsMultiGUI()
    sys.exit(app.exec_())
