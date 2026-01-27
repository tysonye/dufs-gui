import sys
import os
import subprocess
import threading
import time
import socket
import json
import shlex
import platform
import shutil
import tempfile
import zipfile
import tarfile
import re
import winreg
import webbrowser
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

import requests
import psutil

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QGridLayout, QMenu, QAction,
    QMessageBox, QFileDialog, QDialog, QCheckBox, QSystemTrayIcon, QStyle, QToolTip, QStatusBar, QHeaderView, QPlainTextEdit,
    QTabWidget, QComboBox, QSizePolicy, QProgressBar, QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont, QColor, QIcon, QFontMetrics, QCursor

# 配置文件路径
# 仅支持Windows系统
config_dir = os.path.join(os.environ['APPDATA'], 'DufsGUI')

# 创建配置目录（如果不存在）
os.makedirs(config_dir, exist_ok=True)

# 配置文件路径
CONFIG_FILE = os.path.join(config_dir, 'dufs_config.json')

# 密钥文件路径
KEY_FILE = os.path.join(config_dir, '.dufs_key')




def generate_key():
    """生成新的加密密钥"""
    return Fernet.generate_key()


def save_key(key):
    """保存密钥到文件，并设置权限为0600（只有所有者可读写）"""
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    
    # 设置密钥文件权限为0600（仅所有者可读写）
    try:
        if os.name == 'nt':  # Windows系统
            # 使用Windows特定的API设置文件权限
            import win32security
            import win32api
            import ntsecuritycon as con
            
            # 正确获取当前用户SID
            current_user = win32api.GetUserName()
            # 获取计算机名作为默认域
            computer_name = win32api.GetComputerName()
            try:
                user_sid, _, _ = win32security.LookupAccountName(computer_name, current_user)
            except win32security.error:
                # 尝试使用None作为域
                user_sid, _, _ = win32security.LookupAccountName(None, current_user)
            
            # 获取文件的安全描述符
            sd = win32security.GetFileSecurity(KEY_FILE, win32security.DACL_SECURITY_INFORMATION)
            
            # 创建一个新的DACL
            dacl = win32security.ACL()
            
            # 添加当前用户的读写权限
            dacl.AddAccessAllowedAce(win32security.ACL_REVISION, con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE, user_sid)
            
            # 设置文件的DACL
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(KEY_FILE, win32security.DACL_SECURITY_INFORMATION, sd)
        else:
            # 非Windows系统，使用chmod
            import stat
            os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600权限
    except (ImportError, OSError):
        # 权限设置失败，记录警告
        pass


def load_key():
    """从文件加载密钥"""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    # 如果密钥文件不存在，生成新密钥并保存
    key = generate_key()
    save_key(key)
    return key


def get_fernet():
    """获取Fernet加密对象"""
    key = load_key()
    return Fernet(key)


def generate_derived_key(password, salt=None):
    """使用PBKDF2从密码派生密钥
    
    Args:
        password (str): 用户密码
        salt (bytes, optional): 盐值，如果为None则生成新的盐值
        
    Returns:
        tuple: (派生的密钥, 使用的盐值)
    """
    if salt is None:
        salt = os.urandom(16)  # 生成16字节的盐值
    
    # 使用cryptography库的PBKDF2HMAC进行密钥派生，迭代次数为100000
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # Fernet需要32字节的密钥
        salt=salt,
        iterations=100000,
    )
    
    key = kdf.derive(password.encode())
    
    return key, salt


def encrypt_data(data):
    """加密数据"""
    fernet = get_fernet()
    json_str = json.dumps(data)
    encrypted = fernet.encrypt(json_str.encode())
    return encrypted


def decrypt_data(encrypted_data):
    """解密数据"""
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_data)
    return json.loads(decrypted.decode())

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
    SERVICE_START_WAIT_SECONDS = 0.5  
    PROCESS_TERMINATE_TIMEOUT = 2
    
    # 日志配置常量
    MAX_LOG_LINES = 2000
    MAX_LOG_BUFFER_SIZE = 100  # 最大日志缓冲区大小
    DEFAULT_LOG_REFRESH_INTERVAL = 50  # 默认日志刷新间隔（ms）
    MAX_LOG_REFRESH_INTERVAL = 200  # 最大日志刷新间隔（ms）
    
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


def make_log_readable(message):
    """将专业日志格式转换为易懂文字"""
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
    if hasattr(sys, '_MEIPASS'):
        # 单文件打包模式，从临时目录加载
        return os.path.join(sys._MEIPASS, filename)
    else:
        # 开发模式，从程序所在目录加载
        return os.path.abspath(os.path.join(os.path.dirname(__file__), filename))

# 独立日志窗口类
class ProgressDialog(QProgressDialog):
    """增强型进度对话框"""
    def __init__(self, title, cancel_text, min_val, max_val, parent=None):
        super().__init__(title, cancel_text, min_val, max_val, parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumDuration(300)  # 300ms后显示
        self.setAutoClose(True)
        self.setAutoReset(True)
        self.setStyleSheet("""
            QProgressDialog {
                background-color: #f5f5f5;
                border-radius: 8px;
            }
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                text-align: center;
                background-color: #FFFFFF;
            }
            QProgressBar::chunk {
                background-color: #4a6fa5;
                border-radius: 3px;
            }
        """)


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
        
        # 添加日志过滤和搜索控件
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索日志...")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        filter_layout.addWidget(self.search_edit)
        
        # 搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._on_search_clicked)
        filter_layout.addWidget(search_btn)
        
        # 过滤选项
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "错误", "信息"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_combo)
        
        # 清除按钮
        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self._on_clear_clicked)
        filter_layout.addWidget(clear_btn)
        
        main_layout.addLayout(filter_layout)
        
        # 创建日志Tab容器
        self.log_tabs = QTabWidget()
        self.log_tabs.setTabsClosable(True)
        self.log_tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.log_tabs)
        
        # 保存原始日志内容的字典，用于搜索和过滤
        self.original_logs = {}  # 键为tab索引，值为原始日志内容
    
    def add_log_tab(self, service_name, log_widget):
        """添加日志标签页"""
        index = self.log_tabs.count()
        self.log_tabs.addTab(log_widget, service_name)
        
        # 初始化原始日志内容
        self.original_logs[index] = []
        
        # 将当前日志控件的内容添加到原始日志
        current_logs = log_widget.toPlainText().split('\n')
        if current_logs and current_logs[0]:  # 避免添加空行
            self.original_logs[index].extend(current_logs)
    
    def update_log_tab_title(self, index, title):
        """更新日志标签页标题"""
        if 0 <= index < self.log_tabs.count():
            self.log_tabs.setTabText(index, title)
    
    def remove_log_tab(self, index):
        """移除日志标签页"""
        if 0 <= index < self.log_tabs.count():
            self.log_tabs.removeTab(index)
            
            # 更新原始日志字典的键
            new_logs = {}
            for i in range(self.log_tabs.count()):
                if i < index:
                    if i in self.original_logs:
                        new_logs[i] = self.original_logs[i]
                elif i > index:
                    if i in self.original_logs:
                        new_logs[i-1] = self.original_logs[i]
            self.original_logs = new_logs
    
    def _on_search_text_changed(self, text):
        """搜索文本变化时的处理"""
        self._apply_filter()
    
    def _on_search_clicked(self):
        """搜索按钮点击时的处理"""
        self._apply_filter()
    
    def _on_filter_changed(self, text):
        """过滤选项变化时的处理"""
        self._apply_filter()
    
    def _on_clear_clicked(self):
        """清除搜索和过滤"""
        self.search_edit.clear()
        self.filter_combo.setCurrentIndex(0)
        self._apply_filter()
    
    def _on_tab_changed(self, index):
        """切换标签页时的处理"""
        self._apply_filter()
    
    def _apply_filter(self):
        """应用搜索和过滤条件"""
        current_index = self.log_tabs.currentIndex()
        if current_index == -1:
            return
        
        log_widget = self.log_tabs.currentWidget()
        if not log_widget:
            return
        
        # 获取当前标签页的原始日志
        if current_index not in self.original_logs:
            return
        
        search_text = self.search_edit.text().lower()
        filter_level = self.filter_combo.currentText()
        
        # 保存当前滚动位置
        scroll_bar = log_widget.verticalScrollBar()
        scroll_position = scroll_bar.value()
        is_scrolled_to_bottom = scroll_bar.value() == scroll_bar.maximum()
        
        # 清空当前日志
        log_widget.clear()
        
        # 应用过滤
        for line in self.original_logs[current_index]:
            show_line = True
            
            # 搜索过滤
            if search_text and search_text not in line.lower():
                show_line = False
            
            # 级别过滤
            if filter_level == "错误" and "[ERROR]" not in line:
                show_line = False
            elif filter_level == "信息" and "[INFO]" not in line:
                show_line = False
            
            if show_line:
                log_widget.appendPlainText(line)
        
        # 恢复滚动位置
        if is_scrolled_to_bottom:
            # 避免使用ensureCursorVisible()，直接设置滚动条到最大值
            scroll_bar = log_widget.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
        else:
            scroll_bar.setValue(scroll_position)
    
    def append_log(self, index, message):
        """添加日志条目，同时保存到原始日志"""
        if index < 0 or index >= self.log_tabs.count():
            return
        
        log_widget = self.log_tabs.widget(index)
        if not log_widget:
            return
        
        # 保存到原始日志
        if index not in self.original_logs:
            self.original_logs[index] = []
        self.original_logs[index].append(message)
        
        # 应用过滤后显示
        search_text = self.search_edit.text().lower()
        filter_level = self.filter_combo.currentText()
        
        show_line = True
        if search_text and search_text not in message.lower():
            show_line = False
        
        if filter_level == "错误" and "[ERROR]" not in message:
            show_line = False
        elif filter_level == "信息" and "[INFO]" not in message:
            show_line = False
        
        if show_line:
            log_widget.appendPlainText(message)

# 服务状态枚举类
class ServiceStatus:
    """服务状态枚举"""
    STOPPED = "已停止"
    RUNNING = "运行中"
    STARTING = "启动中"
    ERROR = "错误"


class ServiceStateMachine:
    """服务状态机，确保状态转换的合法性"""
    
    # 状态转换表：当前状态 -> 允许的目标状态
    STATE_TRANSITIONS = {
        ServiceStatus.STOPPED: [ServiceStatus.STARTING, ServiceStatus.ERROR],
        ServiceStatus.STARTING: [ServiceStatus.RUNNING, ServiceStatus.STOPPED, ServiceStatus.ERROR],
        ServiceStatus.RUNNING: [ServiceStatus.STOPPED, ServiceStatus.ERROR],
        ServiceStatus.ERROR: [ServiceStatus.STOPPED]
    }
    
    PUBLIC_ACCESS_TRANSITIONS = {
        "stopped": ["starting"],
        "starting": ["running", "stopped"],
        "running": ["stopping"],
        "stopping": ["stopped"],
        "error": ["stopped"]
    }
    
    def can_transition(self, current_status, new_status, public_access=False):
        """检查状态转换是否合法
        
        Args:
            current_status (str): 当前状态
            new_status (str): 目标状态
            public_access (bool): 是否为公网访问状态转换
            
        Returns:
            bool: 状态转换是否合法
        """
        if public_access:
            transitions = self.PUBLIC_ACCESS_TRANSITIONS
        else:
            transitions = self.STATE_TRANSITIONS
        
        return new_status in transitions.get(current_status, [])
    
    def validate_combined_state(self, service_status, public_status):
        """验证服务状态和公网访问状态的组合是否合法
        
        Args:
            service_status (str): 服务状态
            public_status (str): 公网访问状态
            
        Returns:
            bool: 状态组合是否合法
        """
        # 服务未运行时，公网访问不能运行
        if service_status == ServiceStatus.STOPPED and public_status in ["running", "starting"]:
            return False
        return True

# 日志管理类
class LogManager:
    """日志管理类，负责处理日志相关功能"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.log_signal = pyqtSignal(str, bool, str)
        self.log_signal.connect(self._append_log_ui, Qt.QueuedConnection)
    
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
        readable_message = make_log_readable(message)
        
        # 构建日志消息，包含时间戳和级别
        log_message = f"[{timestamp}] [{level}] {service_tag}{readable_message}"
        
        # 使用信号槽机制更新UI，不再传递整个service对象
        self.log_signal.emit(log_message, error, service_name)
    

    
    def _append_log_ui(self, message, error=False, service_name=""):
        """在UI线程中添加日志条目"""
        # 通过service_name找到对应的service
        service = None
        if hasattr(self.main_window, 'manager') and hasattr(self.main_window.manager, 'services'):
            for s in self.main_window.manager.services:
                if s.name == service_name:
                    service = s
                    break
        
        if service and hasattr(service, 'lock') and hasattr(service, 'log_buffer'):
            # 添加日志到缓冲区（使用锁保护，确保线程安全）
            with service.lock:
                service.log_buffer.append((message, error))
                buffer_size = len(service.log_buffer)
            
            # 在锁外但捕获了安全的缓冲区大小
            MIN_LOGS_TO_REFRESH = 3
            if buffer_size >= MIN_LOGS_TO_REFRESH or buffer_size >= AppConstants.MAX_LOG_BUFFER_SIZE:
                # 通过QMetaObject.invokeMethod确保在主线程中处理
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, 
                    "_flush_log_buffer_signal", 
                    Qt.QueuedConnection,
                    Q_ARG(object, service)
                )
        else:
            # 如果没有指定服务或服务没有日志控件，暂时不处理
            pass
    
    @pyqtSlot(object)
    def _flush_log_buffer(self, service):
        """刷新日志缓冲区到UI"""
        if not service or not service.log_widget:
            return
        
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
                
                # 准备要添加的日志文本
                log_text = "\n".join(log_lines)
                
                # 清空缓冲区
                service.log_buffer.clear()
            
            # 使用QMetaObject.invokeMethod确保在主线程中执行UI更新
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, 
                "_perform_log_ui_update", 
                Qt.QueuedConnection,
                Q_ARG(object, service),
                Q_ARG(str, log_text)
            )
    
    @pyqtSlot(object)
    def _flush_log_buffer_signal(self, service):
        """接收日志刷新信号并处理"""
        self._flush_log_buffer(service)
    
    @pyqtSlot(object, str)
    def _perform_log_ui_update(self, service, log_text):
        """在主线程中执行日志UI更新"""
        if not service or not service.log_widget:
            return
        
        # 使用QMetaObject.invokeMethod确保在主线程中执行UI操作
        from PyQt5.QtCore import QMetaObject, Qt
        
        def update_ui():
            try:
                # 一次性添加所有日志
                service.log_widget.appendPlainText(log_text)
                
                # 限制日志行数，防止内存占用过多
                block_count = service.log_widget.blockCount()
                if block_count > AppConstants.MAX_LOG_LINES:
                    # 只删除超过的行数，而不是每次都重新计算
                    excess_lines = block_count - AppConstants.MAX_LOG_LINES
                    
                    # 避免直接操作QTextCursor，使用文档对象来操作文本
                    doc = service.log_widget.document()
                    if doc:
                        # 获取文档的第一个块
                        block = doc.firstBlock()
                        # 删除多余的块
                        for i in range(excess_lines):
                            if not block.isValid():
                                break
                            next_block = block.next()
                            doc.removeBlock(block)
                            block = next_block
                    
                    # 只在必要时滚动到末尾
                    if service.log_widget.verticalScrollBar().value() == service.log_widget.verticalScrollBar().maximum():
                        # 避免使用ensureCursorVisible()，直接滚动到底部
                        service.log_widget.verticalScrollBar().setValue(service.log_widget.verticalScrollBar().maximum())
            except Exception as e:
                # 捕获异常，避免UI更新失败导致程序崩溃
                print(f"执行日志UI更新时发生错误: {str(e)}")
        
        # 使用QTimer.singleShot确保在主线程中执行整个update_ui函数
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, update_ui)

class DufsService(QObject):
    """单个Dufs服务实例"""
    # 状态更新信号（类级别定义）
    status_updated = pyqtSignal()
    # 进度更新信号（类级别定义）
    progress_updated = pyqtSignal(int, str)
    # 日志更新信号（类级别定义）
    log_updated = pyqtSignal(str, bool, str)
    
    def __init__(self, name="默认服务", serve_path=".", port="5000", bind=""):
        super().__init__()
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
        # 统一使用枚举值管理公网访问状态
        self.public_access_status = "stopped"  # stopped, starting, running, stopping
        self.ngrok_authtoken = ""  # 用户配置的ngrok authtoken
        self.ngrok_mode = "authtoken"  # 使用方式：authtoken
        self.ngrok_start_progress = 0  # ngrok启动进度（0-100）
        
        # ngrok监控相关属性
        self.ngrok_monitor_thread = None
        self.ngrok_monitor_terminate = False
        self.ngrok_restart_count = 0
        self.max_ngrok_restarts = 3
        
    def update_status(self, status=None, public_access_status=None):
        """统一更新服务状态和公网访问状态，并确保UI更新在主线程中执行
        
        Args:
            status (str, optional): 服务状态
            public_access_status (str, optional): 公网访问状态
            
        Returns:
            bool: 状态更新是否成功
        """
        # 创建状态机实例
        state_machine = ServiceStateMachine()
        
        # 验证状态转换的合法性
        if status is not None:
            if not state_machine.can_transition(self.status, status):
                return False
        
        if public_access_status is not None:
            if not state_machine.can_transition(self.public_access_status, public_access_status, public_access=True):
                return False
        
        # 验证状态组合的合法性
        new_service_status = status if status is not None else self.status
        new_public_status = public_access_status if public_access_status is not None else self.public_access_status
        if not state_machine.validate_combined_state(new_service_status, new_public_status):
            return False
        
        # 更新服务状态（如果提供）
        if status is not None:
            self.status = status
        
        # 更新公网访问状态（如果提供）
        if public_access_status is not None:
            self.public_access_status = public_access_status
        
        # 发送状态更新信号
        self.status_updated.emit()
        
        return True
        
    def get_ngrok_path(self):
        """获取ngrok路径，直接使用根目录的ngrok.exe"""
        
        # 定义ngrok文件名（仅支持Windows系统）
        ngrok_filename = "ngrok.exe"
        
        # 检查多个位置，优先使用根目录的ngrok.exe
        check_paths = [
            os.path.join(os.getcwd(), ngrok_filename),  # 根目录
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ngrok_filename),  # 脚本所在目录
            os.path.join(config_dir, ngrok_filename)  # 配置目录
        ]
        
        for path in check_paths:
            if os.path.exists(path):
                return path
        
        # 尝试从系统PATH获取
        if shutil.which(ngrok_filename):
            return ngrok_filename
        
        # 如果都找不到，直接返回ngrok.exe（会在运行时失败）
        return ngrok_filename
        
    def start_ngrok(self):
        """启动ngrok内网穿透，将核心逻辑移至后台线程"""
        # 不再停止所有ngrok进程，允许多个ngrok进程同时运行
        # 每个服务使用独立的ngrok进程，通过不同的配置避免冲突
        
        self.append_log("开始启动ngrok内网穿透...")
        # 启动后台线程处理ngrok启动逻辑
        threading.Thread(target=self._start_ngrok_thread, daemon=True).start()
    
    def _start_ngrok_thread(self):
        """在后台线程中处理ngrok启动逻辑"""
        try:
            # 设置公网访问状态为启动中，初始化进度
            self.ngrok_start_progress = 0
            # 使用QTimer.singleShot确保在主线程中执行
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.update_status(public_access_status="starting"))
            
            # 1. 开始启动ngrok内网穿透（1%）
            self.ngrok_start_progress = 1
            # 直接发送进度更新信号
            self.progress_updated.emit(1, "开始启动ngrok内网穿透...")
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log("开始启动ngrok内网穿透..."))
            # 等待UI更新
            time.sleep(0.5)
            
            # 不再停止所有ngrok进程，允许多个ngrok进程同时运行
            # 使用不同的authtoken、区域和API端口来避免端点冲突
            
            # 获取ngrok路径
            ngrok_path = self.get_ngrok_path()
            
            # 优先使用用户配置的authtoken
            current_authtoken = self.ngrok_authtoken or os.environ.get("NGROK_AUTHTOKEN")
            
            # 构建ngrok命令 - 使用ngrok v3的正确格式
            local_port = str(self.port)
            
            # ngrok v3的命令格式：ngrok http <port> [flags]
            # ngrok v3不再支持--api-port参数，移除该参数
            
            # 创建临时配置文件，包含version属性，避免使用默认配置文件中的authtoken
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as f:
                # 创建包含version属性的配置文件，使用ngrok v3的配置版本
                f.write('version: "3"\n')
                temp_config = f.name
            
            def sanitize_command_arg(arg):
                """安全转义命令参数"""
                if os.name == 'nt':
                    # Windows需要特殊处理
                    return arg.replace('^', '^^').replace('&', '^&').replace('>', '^>')
                else:
                    import shlex
                    return shlex.quote(arg)
            
            # 构建ngrok命令，使用临时配置文件避免authtoken冲突
            safe_service_name = sanitize_command_arg(self.name)
            command = [
                ngrok_path,
                "http",  # 子命令在前
                local_port,  # 然后是本地端口
                "--authtoken", current_authtoken,  # authtoken参数放在前面
                "--config", temp_config,  # 使用临时空配置文件，避免authtoken冲突
                "--metadata", f"service={safe_service_name}"  # 服务元数据
                # 移除--api-port参数，ngrok v3不再支持
            ]
            
            # 保存临时配置文件路径，用于后续清理
            self.temp_config = temp_config

            # 过滤掉authtoken参数以保护敏感信息
            filtered_command = []
            skip_next = False
            for arg in command:
                if skip_next:
                    skip_next = False
                    continue
                if arg == '--authtoken':
                    filtered_command.append('--authtoken ***')
                    skip_next = True
                else:
                    filtered_command.append(arg)
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log(f"ngrok完整命令: {' '.join(filtered_command)}"))
            
            # 清除之前的进程引用
            if self.ngrok_process:
                self.ngrok_process = None
            
            # 简化端口检查日志
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', int(local_port)))
            except (socket.error, ValueError) as e:
                pass  # 不输出详细日志，只保留关键信息
            
            # 启动ngrok进程，将stderr合并到stdout方便统一处理
            # 添加creationflags参数来隐藏控制台窗口
            creation_flags = 0
            if os.name == 'nt':  # Windows系统
                creation_flags = subprocess.CREATE_NO_WINDOW  # 隐藏命令窗口
            
            self.ngrok_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                universal_newlines=True,
                bufsize=1,
                shell=False,
                close_fds=True,  # 设置为True，确保后台线程退出后ngrok进程仍能继续运行
                creationflags=creation_flags
            )
            
            # 2. 开始捕获ngrok输出（20%）
            self.ngrok_start_progress = 20
            # 直接发送进度更新信号
            self.progress_updated.emit(20, "开始捕获ngrok输出...")
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log("开始捕获ngrok输出..."))
            # 等待UI更新
            time.sleep(0.5)
            
            # 启动ngrok输出读取线程
            self.ngrok_output_terminate = False
            self.ngrok_output_thread = threading.Thread(target=self._read_ngrok_output, daemon=True)
            self.ngrok_output_thread.start()
            
            # 启动ngrok监控线程
            self.ngrok_monitor_terminate = False
            self.ngrok_monitor_thread = threading.Thread(target=self._monitor_ngrok_process, daemon=True)
            self.ngrok_monitor_thread.start()
            
            # 3. 正在获取ngrok公网URL（30%）
            self.ngrok_start_progress = 30
            # 直接发送进度更新信号
            self.progress_updated.emit(30, "正在获取ngrok公网URL...")
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log("正在获取ngrok公网URL..."))
            # 等待UI更新
            time.sleep(0.5)
            
            # 给ngrok一点启动时间
            time.sleep(1.5)
            
            # 检查self.ngrok_process是否为None，避免并发访问问题
            if self.ngrok_process is None:
                # 使用QTimer.singleShot确保在主线程中执行
                QTimer.singleShot(0, lambda: self.append_log("✗ ngrok启动失败", error=True))
                QTimer.singleShot(0, lambda: self.append_log("="*50))
                self._cleanup_ngrok_resources()
                return
            
            poll_result = self.ngrok_process.poll()
            if poll_result is not None:
                # 进程启动后立即退出，读取错误信息
                # 使用QTimer.singleShot确保在主线程中执行
                QTimer.singleShot(0, lambda: self.append_log(f"✗ ngrok进程启动失败，退出码: {poll_result}", error=True))
                
                # 直接读取所有输出，不依赖输出线程
                direct_stdout = ""
                direct_stderr = ""
                
                try:
                    direct_stdout = self.ngrok_process.stdout.read()
                except (IOError, OSError, ValueError, AttributeError) as e:
                    direct_stdout = f"读取stdout失败: {str(e)}"
                
                try:
                    direct_stderr = self.ngrok_process.stderr.read()
                except (IOError, OSError, ValueError, AttributeError) as e:
                    direct_stderr = f"读取stderr失败: {str(e)}"
                
                # 直接使用读取的输出
                stdout_output = direct_stdout
                stderr_output = direct_stderr
                
                # 检查是否是ERR_NGROK_334错误
                all_output_str = stdout_output + stderr_output
                if "ERR_NGROK_334" in all_output_str:
                    # 使用QTimer.singleShot确保在主线程中执行
                    QTimer.singleShot(0, lambda: self.append_log("✗ 遇到ERR_NGROK_334错误: 该endpoint已被其他ngrok进程使用"))
                    QTimer.singleShot(0, lambda: self.append_log("   请停止其他ngrok进程或使用不同的endpoint"))
                    # 清理资源
                    self._cleanup_ngrok_resources()
                    # 通知UI更新
                    QTimer.singleShot(0, lambda: self.status_updated.emit())
                    return
                
                # 只输出关键错误信息
                if stdout_output:
                    # 使用QTimer.singleShot确保在主线程中执行
                    QTimer.singleShot(0, lambda: self.append_log(f"标准输出: {stdout_output}"))
                if stderr_output:
                    # 使用QTimer.singleShot确保在主线程中执行
                    QTimer.singleShot(0, lambda: self.append_log(f"错误输出: {stderr_output}", error=True))
                
                # 清理资源
                self._cleanup_ngrok_resources()
                # 通知UI更新
                QTimer.singleShot(0, lambda: self.status_updated.emit())
                return
            else:
                pass
            
            # 等待ngrok完全启动并准备就绪
            for i in range(3):
                time.sleep(1)
                
                # 检查进程是否还在运行
                if self.ngrok_process is not None and self.ngrok_process.poll() is not None:
                    # 使用QTimer.singleShot确保在主线程中执行
                    QTimer.singleShot(0, lambda: self.append_log(f"✗ ngrok进程在启动过程中退出，退出码: {self.ngrok_process.poll()}", error=True))
                    # 输出线程已移除，简化输出处理
                    stdout_output = "进程已退出，无法读取详细输出"
                    stderr_output = "进程已退出，无法读取详细输出"
                    
                    # 检查是否是ERR_NGROK_334错误
                    all_output_str = stdout_output + stderr_output
                    if "ERR_NGROK_334" in all_output_str:
                        # 使用QTimer.singleShot确保在主线程中执行
                        QTimer.singleShot(0, lambda: self.append_log("✗ 遇到ERR_NGROK_334错误: 该endpoint已被其他ngrok进程使用"))
                        QTimer.singleShot(0, lambda: self.append_log("   请停止其他ngrok进程或使用不同的endpoint"))
                        # 清理资源
                        self._cleanup_ngrok_resources()
                        # 通知UI更新
                        QTimer.singleShot(0, lambda: self.status_updated.emit())
                        return
                    
                    # 只输出关键错误信息
                    if stdout_output:
                        # 使用QTimer.singleShot确保在主线程中执行
                        QTimer.singleShot(0, lambda: self.append_log(f"标准输出: {stdout_output}"))
                    if stderr_output:
                        # 使用QTimer.singleShot确保在主线程中执行
                        QTimer.singleShot(0, lambda: self.append_log(f"错误输出: {stderr_output}", error=True))
                    
                    # 清理资源
                    self._cleanup_ngrok_resources()
                    # 通知UI更新
                    QTimer.singleShot(0, lambda: self.status_updated.emit())
                    return
            
            # 4. 尝试使用ngrok本地API获取URL（50%）
            self.ngrok_start_progress = 50
            # 直接发送进度更新信号
            self.progress_updated.emit(50, "尝试使用ngrok本地API获取URL...")
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log("尝试使用ngrok本地API获取URL..."))
            # 等待UI更新
            time.sleep(0.5)
            
            public_url = None
            start_time = time.time()
            timeout = 15  # 15秒超时
            
            try:
                # 多次尝试获取URL，增加成功率
                while time.time() - start_time < timeout:
                    if self.ngrok_process is None or self.ngrok_process.poll() is not None:
                        break
                    
                    # 调用API获取URL的方法
                    public_url = self.get_ngrok_url(self.ngrok_process)
                    if public_url:
                        # 5. 通过API获取到当前服务的公网URL（80%）
                        self.ngrok_start_progress = 80
                        # 直接发送进度更新信号
                        self.progress_updated.emit(80, "通过API获取到当前服务的公网URL:")
                        # 使用QTimer.singleShot确保在主线程中执行
                        QTimer.singleShot(0, lambda: self.append_log(f"通过API获取到当前服务的公网URL: {public_url}"))
                        # 等待UI更新
                        time.sleep(0.5)
                        break
                    
                    # 等待1秒后重试
                    time.sleep(1)
                    
            except Exception as e:
                # 使用QTimer.singleShot确保在主线程中执行
                QTimer.singleShot(0, lambda: self.append_log(f"获取ngrok公网URL时发生错误: {str(e)}", error=True))
            
            if public_url:
                # 6. ngrok已成功启动（100%）
                self.ngrok_start_progress = 100
                # 直接发送进度更新信号
                self.progress_updated.emit(100, "ngrok已成功启动")
                # 等待UI更新
                time.sleep(0.5)
                # 重置重启计数
                self.ngrok_restart_count = 0
                self.public_url = public_url
                self.public_access_status = "running"
                # 使用QTimer.singleShot确保在主线程中执行
                QTimer.singleShot(0, lambda: self.append_log("✓ ngrok已成功启动！"))
                QTimer.singleShot(0, lambda: self.append_log(f"✓ 公网URL: {self.public_url}"))
                QTimer.singleShot(0, lambda: self.append_log("="*50))
                
                # 更新状态并通知UI
                # 使用QTimer.singleShot确保在主线程中执行
                QTimer.singleShot(0, lambda: self.update_status(public_access_status="running"))
                return
            
            # 进程还在运行但没有获取到URL，重置进度
            self.ngrok_start_progress = 0
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log("✗ 未能通过API获取ngrok公网URL", error=True))
            
            
            
            # 读取所有输出，直接从进程读取
            stdout_output = ""
            stderr_output = ""
            
            # 尝试直接读取剩余的输出
            if self.ngrok_process is not None:
                try:
                    remaining_stdout = self.ngrok_process.stdout.read()
                    if remaining_stdout:
                        stdout_output += "\n" + remaining_stdout
                except Exception as e:
                    # 使用QTimer.singleShot确保在主线程中执行
                    QTimer.singleShot(0, lambda: self.append_log(f"读取ngrok标准输出时发生错误: {str(e)}", error=True))
                
                try:
                    remaining_stderr = self.ngrok_process.stderr.read()
                    if remaining_stderr:
                        stderr_output += "\n" + remaining_stderr
                except Exception as e:
                    # 使用QTimer.singleShot确保在主线程中执行
                    QTimer.singleShot(0, lambda: self.append_log(f"读取ngrok标准错误时发生错误: {str(e)}", error=True))
            
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log("="*50))
            QTimer.singleShot(0, lambda: self.append_log(f"命令: {' '.join(command)}"))
            if self.ngrok_process:
                QTimer.singleShot(0, lambda: self.append_log(f"PID: {self.ngrok_process.pid}"))
                QTimer.singleShot(0, lambda: self.append_log(f"进程状态: {'运行中' if self.ngrok_process.poll() is None else '已退出'}"))
            QTimer.singleShot(0, lambda: self.append_log("\n=== 标准输出 ==="))
            QTimer.singleShot(0, lambda: self.append_log(stdout_output))
            QTimer.singleShot(0, lambda: self.append_log("\n=== 错误输出 ==="))
            QTimer.singleShot(0, lambda: self.append_log(stderr_output))
            QTimer.singleShot(0, lambda: self.append_log("="*50))
            
            # 检查是否是authtoken问题
            if "authtoken" in stderr_output.lower() or "unauthorized" in stderr_output.lower():
                QTimer.singleShot(0, lambda: self.append_log("\n❌ 问题诊断: ngrok需要有效的authtoken才能使用"))
                QTimer.singleShot(0, lambda: self.append_log("   请按照以下步骤配置:"))
                QTimer.singleShot(0, lambda: self.append_log("   1. 访问 https://dashboard.ngrok.com/signup 注册账号"))
                QTimer.singleShot(0, lambda: self.append_log("   2. 登录后，访问 https://dashboard.ngrok.com/get-started/your-authtoken 获取authtoken"))
                QTimer.singleShot(0, lambda: self.append_log("   3. 在命令行中运行: ngrok config add-authtoken <你的authtoken>"))
            elif "already online" in stderr_output.lower() or "ERR_NGROK_334" in stderr_output:
                QTimer.singleShot(0, lambda: self.append_log("\n❌ 问题诊断: 端口已被其他ngrok进程占用"))
                QTimer.singleShot(0, lambda: self.append_log("   请先停止之前的ngrok进程或使用不同的端口"))
            elif "failed to connect" in stderr_output.lower() or "connection refused" in stderr_output.lower():
                QTimer.singleShot(0, lambda: self.append_log("\n❌ 问题诊断: 无法连接到ngrok服务器"))
                QTimer.singleShot(0, lambda: self.append_log("   请检查网络连接或防火墙设置"))
            elif "listen tcp" in stderr_output.lower() and "bind: address already in use" in stderr_output.lower():
                QTimer.singleShot(0, lambda: self.append_log("\n❌ 问题诊断: 本地端口被占用"))
                QTimer.singleShot(0, lambda: self.append_log("   请使用不同的本地端口或停止占用该端口的进程"))
            else:
                QTimer.singleShot(0, lambda: self.append_log("\n❌ 问题诊断: 无法确定具体问题，请查看上面的详细输出"))
            
            # 清理资源
            self._cleanup_ngrok_resources()
            # 通知UI更新
            QTimer.singleShot(0, lambda: self.status_updated.emit())
            return
        except (subprocess.SubprocessError, requests.exceptions.RequestException, OSError, ValueError, AttributeError) as e:
            # 使用QTimer.singleShot确保在主线程中执行
            QTimer.singleShot(0, lambda: self.append_log(f"{'='*50}"))
            QTimer.singleShot(0, lambda: self.append_log(f"❌ 启动ngrok时发生异常: {str(e)}"))
            QTimer.singleShot(0, lambda: self.append_log(f"{'='*50}"))
            
            # 清理资源
            self._cleanup_ngrok_resources()
            # 通知UI更新
            QTimer.singleShot(0, lambda: self.status_updated.emit())
            return
    
    def _cleanup_ngrok_resources(self):
        """清理ngrok资源"""
        # 重置ngrok启动进度为0
        self.ngrok_start_progress = 0
        # 发送进度更新信号，重置UI上的进度条
        self.progress_updated.emit(0, "ngrok已停止")
        
        self.append_log("\n正在清理ngrok资源...")
        self.ngrok_monitor_terminate = True
        self.ngrok_output_terminate = True
        
        # 等待输出读取线程结束
        if hasattr(self, 'ngrok_output_thread') and self.ngrok_output_thread and self.ngrok_output_thread.is_alive():
            try:
                self.ngrok_output_thread.join(timeout=1)  # 等待1秒让线程结束
                self.append_log("   ✓ ngrok输出读取线程已终止")
            except (RuntimeError, ValueError):
                pass
        
        if self.ngrok_process:
            try:
                # 先关闭进程IO流，防止资源泄漏
                try:
                    if self.ngrok_process.stdout:
                        self.ngrok_process.stdout.close()
                    if self.ngrok_process.stderr:
                        self.ngrok_process.stderr.close()
                except (OSError, ValueError) as e:
                    self.append_log(f"   ✗ 关闭ngrok进程IO流失败: {str(e)}", error=True)
                
                # 使用ensure_process_termination方法确保进程完全终止
                terminated = self.ensure_process_termination(self.ngrok_process, "ngrok进程")
                if terminated:
                    self.append_log("   ✓ ngrok进程已成功终止")
                    # 只有当进程成功终止后才清除引用
                    self.ngrok_process = None
                else:
                    # 进程终止失败，保留引用以便后续处理
                    self.append_log(f"   ⚠ ngrok进程仍在运行，保留引用以便后续管理", error=True)
            except (OSError, ValueError, AttributeError) as e:
                self.append_log(f"   ✗ 终止ngrok进程失败: {str(e)}", error=True)
                # 进程终止失败，保留引用以便后续处理
                self.append_log(f"   ⚠ ngrok进程仍在运行，保留引用以便后续管理", error=True)
        
        # 清理临时配置文件
        if hasattr(self, 'temp_config') and self.temp_config:
            try:
                os.unlink(self.temp_config)
                self.append_log(f"   ✓ 已删除临时配置文件: {self.temp_config}")
                self.temp_config = None
            except OSError as e:
                self.append_log(f"   ✗ 删除临时配置文件失败: {str(e)}", error=True)
        
        self.public_url = ""
        self.append_log("   ✓ 已清理所有ngrok资源")
        self.append_log(f"{'='*50}")
        # 更新状态并通知UI
        self.update_status(public_access_status="stopped")
    
    def _read_ngrok_output(self):
        """读取并处理ngrok进程的输出"""
        if self.ngrok_process is None:
            return
        
        # 确保stdout是有效的
        if not hasattr(self.ngrok_process, 'stdout') or self.ngrok_process.stdout is None:
            return
        
        self.append_log("开始捕获ngrok输出...")
        
        try:
            # 循环读取输出，直到进程结束或被终止
            while not self.ngrok_output_terminate:
                if self.ngrok_process is None:
                    break
                
                # 检查进程是否还在运行
                if self.ngrok_process.poll() is not None:
                    # 进程已结束，尝试读取剩余的输出
                    self.append_log("ngrok进程已结束，尝试读取剩余输出...")
                    try:
                        # 读取所有剩余的输出
                        remaining_output = self.ngrok_process.stdout.read()
                        if remaining_output:
                            lines = remaining_output.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line:
                                    self.append_log(f"ngrok: {line}")
                    except (IOError, OSError, ValueError):
                        pass
                    break
                
                try:
                    # 对于Windows系统，使用简单的非阻塞读取方式
                    # 设置超时，避免阻塞
                    import time
                    
                    # 尝试读取一行
                    line = ""
                    try:
                        # 使用文件对象的readline方法
                        line = self.ngrok_process.stdout.readline()
                    except (IOError, OSError, ValueError):
                        # 读取失败，可能是进程已结束
                        break
                    
                    if not line:
                        # 输出流可能已关闭或暂时无数据
                        time.sleep(0.01)  # 短暂休眠，避免CPU占用过高
                        continue
                    
                    # 处理输出行
                    line = line.strip()
                    if line:
                        # 将ngrok输出转换为日志消息
                        self.append_log(f"ngrok: {line}")
                except Exception as e:
                    # 捕获所有异常，确保线程不会崩溃
                    self.append_log(f"读取ngrok输出时发生异常: {str(e)}", error=True)
                    break
        finally:
            self.append_log("ngrok输出捕获结束")
            # 确保输出线程正常结束
            pass
    
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
                
                # 检查是否是手动停止的，如果是，就不重新启动
                if not self.ngrok_monitor_terminate:
                    # 检查重新启动次数是否已达上限
                    if self.ngrok_restart_count < self.max_ngrok_restarts:
                        # 尝试重新启动
                        self._restart_ngrok()
                        self.ngrok_restart_count += 1
                    else:
                        self.append_log(f"ngrok重启次数已达上限 ({self.max_ngrok_restarts}次)，停止重试")
                        # 重置重启计数
                        self.ngrok_restart_count = 0
                        # 清理资源
                        self._cleanup_ngrok_resources()
                else:
                    # 手动停止的，直接清理资源
                    self.append_log("ngrok已被手动停止，不重新启动")
                    # 重置重启计数
                    self.ngrok_restart_count = 0
                    # 清理资源
                    self._cleanup_ngrok_resources()
                break
    
    def _restart_ngrok(self):
        """重新启动ngrok进程"""
        self.append_log("尝试重新启动ngrok...")
        
        # 首先使用taskkill命令强制停止所有ngrok进程，确保彻底清理
        try:
            import subprocess
            # 停止所有ngrok进程
            subprocess.run(['taskkill', '/F', '/IM', 'ngrok.exe'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
            # 等待1秒让进程完全停止
            time.sleep(1)
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # 清理之前的ngrok进程引用
        if self.ngrok_process:
            try:
                # 先关闭进程IO流，防止资源泄漏
                try:
                    if self.ngrok_process.stdout:
                        self.ngrok_process.stdout.close()
                    if self.ngrok_process.stderr:
                        self.ngrok_process.stderr.close()
                except (OSError, ValueError) as e:
                    self.append_log(f"关闭ngrok进程IO流失败: {str(e)}", error=True)
            except (OSError, ValueError, AttributeError) as e:
                self.append_log(f"清理ngrok进程失败: {str(e)}", error=True)
            finally:
                self.ngrok_process = None
        
        # 停止旧的监控线程
        self.ngrok_monitor_terminate = True
        if self.ngrok_monitor_thread and self.ngrok_monitor_thread.is_alive():
            # 等待旧的监控线程退出
            time.sleep(0.5)
        
        # 重置监控线程终止标志
        self.ngrok_monitor_terminate = False
        
        self.public_access_status = "stopped"
        self.public_url = ""
        
        # 随着重试次数增加，逐渐延长重试间隔，减少资源竞争
        retry_delay = 1 + self.ngrok_restart_count  # 基础延迟1秒，每次重试增加1秒
        self.append_log(f"等待 {retry_delay} 秒后重新尝试...")
        time.sleep(retry_delay)
        self.start_ngrok()
    
    def get_ngrok_url(self, process):
        """从ngrok进程输出中获取公网URL，优先使用ngrok本地API"""

        # 检查进程是否有效
        if process is None:
            return None

        # 添加调试输出，显示正在尝试获取URL
        self.append_log("正在获取ngrok公网URL...")
        local_port = str(self.port)

        # 使用ngrok本地API获取URL
        self.append_log("尝试使用ngrok本地API获取URL...")
        # ngrok v3不再支持--api-port参数，使用默认的API端口4040
        # 尝试多个可能的API端口，增加成功率
        api_ports_to_try = [4040, 4041, 4042, 4043, 4044, 4045]

        for port in api_ports_to_try:
            try:
                response = requests.get(f"http://127.0.0.1:{port}/api/tunnels", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and "tunnels" in data:
                        self.append_log(f"通过API获取到 {len(data['tunnels'])} 个隧道，端口 {port}")
                        for i, tunnel in enumerate(data["tunnels"]):
                            self.append_log(f"隧道 {i+1}: {tunnel.get('public_url', 'No URL')}, 配置: {tunnel.get('config', {})}, 元数据: {tunnel.get('metadata', '')}")
                            if tunnel["public_url"]:
                                # 严格检查隧道是否属于当前服务
                                # 检查隧道的配置，看是否匹配当前服务的端口
                                if "config" in tunnel and "addr" in tunnel["config"]:
                                    # 检查地址是否匹配当前服务的端口
                                    tunnel_addr = tunnel["config"]["addr"]
                                    if f":{local_port}" in tunnel_addr:
                                        self.append_log(f"通过API获取到当前服务的公网URL: {tunnel['public_url']}")
                                        return tunnel["public_url"]
                                # 检查隧道的元数据，看是否匹配当前服务的名称
                                if "metadata" in tunnel and tunnel["metadata"]:
                                    if f"service={self.name}" in tunnel["metadata"]:
                                        self.append_log(f"通过API获取到当前服务的公网URL: {tunnel['public_url']}")
                                        return tunnel["public_url"]
            except Exception as e:
                self.append_log(f"API请求失败，端口 {port}: {str(e)}", error=True)
                continue

        # 方法3: 从日志文件获取URL的逻辑已移除，不再生成日志文件
        self.append_log("不再从日志文件获取URL，因为不再生成日志文件")
        # 已移除从日志文件获取URL的逻辑
        pass

        self.append_log("未能获取ngrok公网URL", error=True)
        return None

    def append_log(self, message, error=False):
        """添加日志条目"""
        # 打印到控制台
        print(f"[{self.name}] {'ERROR: ' if error else ''}{message}")
        
        # 发出日志更新信号，将日志消息传递给GUI，不再传递整个self对象
        self.log_updated.emit(message, error, self.name)
        
        # 将日志添加到服务的日志缓冲区，这样日志窗口就能显示
        if hasattr(self, 'log_buffer') and hasattr(self, 'lock'):
            with self.lock:
                # 限制缓冲区大小，避免内存占用过高
                if hasattr(AppConstants, 'MAX_LOG_BUFFER_SIZE'):
                    if len(self.log_buffer) >= AppConstants.MAX_LOG_BUFFER_SIZE:
                        # 缓冲区已满，移除最早的日志
                        self.log_buffer.pop(0)
                # 添加新日志
                self.log_buffer.append((message, error))
    
    def ensure_process_termination(self, process, name="process"):
        """确保进程完全终止
        
        Args:
            process (subprocess.Popen): 要终止的进程对象
            name (str): 进程名称，用于日志输出
            
        Returns:
            bool: 进程是否成功终止
        """
        if not process:
            return True
            
        try:
            # 尝试正常终止
            process.terminate()
            try:
                process.wait(timeout=2)
                return True
            except subprocess.TimeoutExpired:
                pass
                
            # 尝试强制终止
            if os.name == 'nt':
                import subprocess
                # 设置creationflags参数来隐藏命令窗口
                creation_flags = 0
                if os.name == 'nt':  # Windows系统
                    creation_flags = subprocess.CREATE_NO_WINDOW  # 隐藏命令窗口
                subprocess.run(['taskkill', '/F', '/PID', str(process.pid)], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              timeout=2,
                              creationflags=creation_flags)  # 隐藏命令窗口
            else:
                import signal
                os.kill(process.pid, signal.SIGKILL)
                
            # 验证进程状态
            for _ in range(3):
                if process.poll() is not None:
                    return True
                import time
                time.sleep(0.5)
            
            # 最后手段：记录警告
            self.append_log(f"⚠ {name} (PID:{process.pid}) 未完全终止，可能成为僵尸进程", error=True)
            return False
        except Exception as e:
            self.append_log(f"✗ 终止 {name} 失败: {str(e)}", error=True)
            return False
    
    def stop_ngrok(self, wait=False):
        """停止ngrok进程
        
        Args:
            wait (bool): 是否等待进程完全停止后再返回
        """
        # 只停止当前服务启动的ngrok进程，而不是所有ngrok进程
        # 这样可以避免影响其他服务的公网访问
        
        # 创建一个事件对象，用于等待ngrok进程完全停止
        import threading
        stop_event = threading.Event()
        
        def _stop_ngrok_thread():
            # 终止监控线程
            self.ngrok_monitor_terminate = True
            if self.ngrok_monitor_thread and self.ngrok_monitor_thread.is_alive():
                self.ngrok_monitor_thread.join(timeout=0.5)  # 等待0.5秒让线程结束
            
            if self.ngrok_process:
                self.append_log("正在停止ngrok进程...")
                try:
                    # 保存进程引用，避免在多线程环境下被修改
                    ngrok_process = self.ngrok_process
                    
                    # 先关闭进程IO流，防止资源泄漏
                    try:
                        if ngrok_process and hasattr(ngrok_process, 'stdout') and ngrok_process.stdout:
                            ngrok_process.stdout.close()
                        if ngrok_process and hasattr(ngrok_process, 'stderr') and ngrok_process.stderr:
                            ngrok_process.stderr.close()
                    except (OSError, ValueError) as e:
                        self.append_log(f"关闭ngrok进程IO流失败: {str(e)}", error=True)
                    
                    # 使用ensure_process_termination方法确保进程完全终止
                    terminated = self.ensure_process_termination(ngrok_process, "ngrok进程")
                    
                    # 设置进程为None
                    self.ngrok_process = None
                    
                    if terminated:
                        self.append_log("ngrok进程已成功停止")
                    else:
                        self.append_log("ngrok进程可能未完全终止", error=True)
                except (OSError, ValueError, AttributeError) as e:
                    self.append_log(f"停止ngrok进程失败: {str(e)}", error=True)
                    # 进程终止失败，保留引用以便后续处理
            
            # 在主线程中更新UI
            from PyQt5.QtCore import QCoreApplication, QEvent
            class UiUpdateEvent(QEvent):
                def __init__(self, callback):
                    super().__init__(QEvent.User)
                    self.callback = callback
            
            def post_ui_update(callback):
                app = QCoreApplication.instance()
                if app:
                    event = UiUpdateEvent(callback)
                    app.postEvent(self, event)
            
            post_ui_update(lambda: self._update_ngrok_ui())
            
            # 通知等待线程，ngrok进程已停止
            stop_event.set()
        
        # 启动后台线程
        thread = threading.Thread(target=_stop_ngrok_thread)
        thread.daemon = True
        thread.start()
        
        # 如果需要等待，就阻塞直到ngrok进程完全停止
        if wait:
            stop_event.wait(timeout=3)  # 设置3秒超时，减少等待时间
    
    def _update_ngrok_ui(self):
        """在主线程中更新ngrok相关UI"""
        # 重置ngrok启动进度为0
        self.ngrok_start_progress = 0
        # 发送进度更新信号，重置UI上的进度条
        self.progress_updated.emit(0, "ngrok已停止")
        # 使用统一的状态更新方法，确保UI及时更新
        self.public_url = ""
        self.append_log("ngrok已停止")
        # 使用统一的状态更新方法
        self.update_status(public_access_status="stopped")
        # 发送状态更新信号，确保UI组件更新
        self.status_updated.emit()
            
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
        self.port_lock = threading.Lock()  # 端口检查和分配锁
        self.allocated_ports = set()  # 已分配但尚未使用的端口集合，用于防止端口冲突
    
    def add_service(self, service):
        """添加服务，会检查端口是否可用"""
        # 检查端口是否可用
        try:
            port = int(service.port)
            if not self.is_port_available(port):
                raise ValueError(f"端口 {port} 已被占用")
        except ValueError as e:
            raise ValueError(f"无效的端口配置: {e}")
        
        self.services.append(service)
    
    def remove_service(self, index):
        """删除服务"""
        if 0 <= index < len(self.services):
            del self.services[index]
    
    def edit_service(self, index, service):
        """编辑服务"""
        if 0 <= index < len(self.services):
            # 保存旧服务的状态
            old_service = self.services[index]
            
            # 停止旧服务的ngrok进程（如果正在运行）
            if hasattr(old_service, 'stop_ngrok'):
                old_service.stop_ngrok(wait=True)  # 设置wait=True，确保旧的ngrok进程完全停止
            
            # 确保旧服务的所有资源都被清理
            if hasattr(old_service, 'process') and old_service.process:
                try:
                    old_service.process.terminate()
                    old_service.process.wait(timeout=1)
                except (subprocess.TimeoutExpired, OSError, ValueError):
                    try:
                        old_service.process.kill()
                    except (OSError, ValueError):
                        pass
                finally:
                    old_service.process = None
            
            # 重置新服务的状态和属性，确保它处于正确的初始状态
            service.status = ServiceStatus.STOPPED
            service.process = None
            service.local_addr = ""
            service.public_url = ""
            service.public_access_status = "stopped"
            service.log_thread_terminate = False
            service.ngrok_process = None
            service.ngrok_monitor_terminate = False
            service.ngrok_start_progress = 0
            service.ngrok_restart_count = 0
            service.log_buffer = []
            service.log_widget = None
            service.log_tab_index = None
            
            # 替换服务
            self.services[index] = service
            
            # 释放旧服务占用的端口
            try:
                port = int(old_service.port)
                self.release_allocated_port(port)
            except (ValueError, AttributeError):
                pass
    
    def get_service(self, index):
        """获取服务"""
        if 0 <= index < len(self.services):
            return self.services[index]
        return None
    
    def get_running_services(self):
        """获取所有运行中的服务"""
        return [s for s in self.services if s.status == ServiceStatus.RUNNING]
    
    def is_port_available(self, port, exclude_service=None):
        """检查端口是否可用（未被任何服务或进程占用）
        
        Args:
            port (int): 要检查的端口号
            exclude_service: 要排除的服务（检查当前服务列表时忽略该服务）
            
        Returns:
            bool: 端口是否可用
        """
        # 1. 检查端口是否已被分配（防止并发分配）
        if port in self.allocated_ports:
            return False
        
        # 2. 检查是否被当前服务列表中的其他服务占用
        for service in self.services:
            if service == exclude_service:
                continue
            try:
                if int(service.port) == port and service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                    return False
            except ValueError:
                # 如果端口不是有效数字，跳过比较
                continue
        
        # 3. 检查端口是否被其他进程占用
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False
    
    def find_available_port(self, start_port=AppConstants.DEFAULT_PORT, max_tries=AppConstants.PORT_TRY_LIMIT):
        """自动寻找可用端口
        
        Args:
            start_port (int): 起始端口号
            max_tries (int): 最大尝试次数
            
        Returns:
            int: 可用的端口号
            
        Raises:
            ValueError: 如果在指定尝试次数内未找到可用端口
        """
        with self.port_lock:  # 使用锁保护端口分配过程，防止死锁
            port = start_port
            for _ in range(max_tries):
                if self.is_port_available(port):
                    # 原子化分配端口：将端口添加到已分配集合，防止其他服务同时使用
                    self.allocated_ports.add(port)
                    return port
                port += 1
            
            # 如果未找到可用端口，尝试使用备用起始端口范围
            port = AppConstants.BACKUP_START_PORT
            for _ in range(AppConstants.PORT_TRY_LIMIT_BACKUP):
                if self.is_port_available(port):
                    # 原子化分配端口：将端口添加到已分配集合，防止其他服务同时使用
                    self.allocated_ports.add(port)
                    return port
                port += 1
            
            raise ValueError(f"无法找到可用端口，已尝试从 {start_port} 开始的 {max_tries} 个端口和备用范围")
    
    def is_port_used_by_service(self, port, exclude_service=None):
        """检查端口是否被服务使用
        
        Args:
            port (int): 要检查的端口号
            exclude_service: 要排除的服务
            
        Returns:
            tuple: (是否被占用, 占用服务名称)
        """
        for service in self.services:
            if service == exclude_service:
                continue
            try:
                if int(service.port) == port and service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                    return True, service.name
            except ValueError:
                continue
        return False, None
    
    def release_allocated_port(self, port):
        """释放已分配的端口
        
        Args:
            port (int): 要释放的端口号
        """
        with self.port_lock:
            if port in self.allocated_ports:
                self.allocated_ports.remove(port)

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
        # 移除标题栏的问号
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
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
        
        # ngrok配置
        ngrok_group = QGroupBox("ngrok配置")
        ngrok_layout = QGridLayout()
        ngrok_layout.setContentsMargins(15, 15, 15, 15)
        ngrok_layout.setSpacing(12)
        
        authtoken_label = QLabel("Authtoken:")
        authtoken_label.setAlignment(Qt.AlignVCenter)
        ngrok_layout.addWidget(authtoken_label, 0, 0)
        
        # 创建水平布局容纳authtoken输入框和清空按钮
        authtoken_layout = QHBoxLayout()
        authtoken_layout.setSpacing(12)
        
        self.authtoken_edit = QLineEdit()
        self.authtoken_edit.setEchoMode(QLineEdit.Password)
        self.authtoken_edit.setPlaceholderText("请输入ngrok authtoken（留空不启用）")
        authtoken_layout.addWidget(self.authtoken_edit)
        
        # 添加清空按钮
        clear_authtoken_btn = QPushButton("清空")
        clear_authtoken_btn.setObjectName("InfoBtn")
        clear_authtoken_btn.setMinimumWidth(70)
        clear_authtoken_btn.setToolTip("清空已输入的authtoken")
        clear_authtoken_btn.clicked.connect(lambda: self.authtoken_edit.clear())
        authtoken_layout.addWidget(clear_authtoken_btn)
        
        ngrok_layout.addLayout(authtoken_layout, 0, 1)
        
        
        ngrok_group.setLayout(ngrok_layout)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 20, 0, 0)
        btn_layout.setSpacing(25)
        btn_layout.setAlignment(Qt.AlignCenter)
        
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("OkBtn")
        ok_btn.setMinimumWidth(120)
        ok_btn.setMinimumHeight(35)
        ok_btn.clicked.connect(self.on_ok)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addWidget(basic_group)
        main_layout.addSpacing(10)
        main_layout.addWidget(perm_group)
        main_layout.addSpacing(10)
        main_layout.addWidget(auth_group)
        main_layout.addSpacing(10)
        main_layout.addWidget(ngrok_group)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
        # 填充数据
        if self.service:
            self.name_edit.setText(self.service.name)
            self.path_edit.setText(self.service.serve_path)
            self.port_edit.setText(self.service.port)
            self.allow_upload_check.setChecked(self.service.allow_upload)
            self.allow_delete_check.setChecked(self.service.allow_delete)
            self.authtoken_edit.setText(self.service.ngrok_authtoken)
            
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
    
    def validate_serve_path(self, path):
        """验证服务路径是否安全
        
        Args:
            path (str): 要验证的服务路径
            
        Returns:
            bool: 路径是否安全且用户确认使用
        """
        # 规范化路径
        normalized_path = os.path.normpath(os.path.abspath(path))
        
        # 检查路径遍历模式
        import re
        if re.search(r'(\.\.[\/])|([\/]\.\.)|(%[0-9a-fA-F]{2,})', normalized_path, re.I):
            QMessageBox.critical(self, "安全错误", "路径包含不安全的遍历模式，请选择安全的路径")
            return False
        
        # 检查是否在用户目录或明确允许的目录内
        allowed_roots = [
            os.path.expanduser("~"),  # 用户目录
            os.path.abspath(os.getcwd())  # 当前工作目录
        ]
        
        # 检查是否在允许的根目录下
        is_allowed = False
        for root in allowed_roots:
            try:
                # 检查两个路径是否在同一个驱动器上
                if os.path.splitdrive(normalized_path)[0] != os.path.splitdrive(root)[0]:
                    continue  # 不在同一个驱动器上，跳过
                
                if os.path.commonpath([normalized_path, root]) == root:
                    # 检查是否包含系统敏感目录
                    sensitive_dirs = ["Windows", "System32", "Program Files", "ProgramData"]
                    parts = normalized_path.split(os.sep)
                    for part in parts:
                        if part in sensitive_dirs:
                            msg = f"警告：路径包含敏感目录 '{part}'\n确定要使用此路径吗？"
                            return QMessageBox.warning(self, "安全警告", msg, 
                                                     QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
                    is_allowed = True
                    break
            except ValueError:
                # 路径不在同一个驱动器上，跳过
                continue
        
        if not is_allowed:
            # 允许用户确认，但显示明确警告
            msg = (f"安全警告：路径 '{normalized_path}' 不在推荐的安全区域内。\n\n"
                   "这可能导致：\n- 意外暴露系统文件\n- 未授权访问敏感数据\n\n"
                   "确定要继续吗？")
            return QMessageBox.warning(self, "路径安全警告", msg, 
                                     QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
        
        return True
    
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
        
        # 检查路径深度，防止过深的目录结构
        path_parts = serve_path.split(os.sep)
        if len(path_parts) > AppConstants.MAX_PATH_DEPTH:
            QMessageBox.critical(self, "错误", f"服务路径深度超过限制 ({AppConstants.MAX_PATH_DEPTH}层)")
            return
        
        # 使用完善的路径验证函数
        if not self.validate_serve_path(serve_path):
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
            
            # 检查服务名称冲突（大小写不敏感）
            if existing_service.name.lower() == name.lower():
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
        
        # 设置ngrok配置
        service.ngrok_authtoken = self.authtoken_edit.text().strip()
        service.ngrok_mode = "authtoken"
        
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
    log_signal = pyqtSignal(str, bool, str)  # 日志内容, 是否错误, 服务名称
    
    def __init__(self):
        super().__init__()
        # 使用ServiceManager统一管理服务
        self.manager = ServiceManager()
        # 添加真实退出标志位
        self._real_exit = False
        # 独立日志窗口实例
        self.log_window = None
        
        # 初始化UI属性
        self.authtoken_widget = None
        self.authtoken_edit = None
        self.auto_start_checkbox = None
        self.log_window_btn = None
        self.service_tree = None
        self.addr_edit = None
        self.public_addr_edit = None
        self.public_copy_btn = None
        self.public_browse_btn = None
        self.public_access_btn = None
        self.log_tabs = None
        self.status_bar = None
        self.tray_icon = None
        self.default_icon = None
        self.tray_menu = None
        self._tray_refresh_timer = None        
        self.init_ui()
        # 使用QueuedConnection确保_append_log_ui方法总是在主线程中执行
        from PyQt5.QtCore import Qt
        self.status_updated.connect(self.update_service_list, Qt.QueuedConnection)
        self.log_signal.connect(self._append_log_ui, Qt.QueuedConnection)
    
    def event(self, event):
        """处理自定义事件"""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.User:
            # 检查事件是否有callback属性
            if hasattr(event, 'callback') and callable(event.callback):
                try:
                    # 执行回调函数
                    event.callback()
                except Exception as e:
                    # 捕获异常，避免事件处理失败导致程序崩溃
                    self.append_log(f"处理自定义事件时发生错误: {str(e)}", error=True)
                return True
        return super().event(event)
    
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
        
        # 使用信号槽机制更新UI，不再传递整个service对象，而是通过service_name找到对应的service
        self.log_signal.emit(log_message, error, service_name)
    
    def _make_log_readable(self, message):
        """将专业日志格式转换为易懂文字"""
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
    
    def _append_log_ui(self, message, error=False, service_name=""):
        """在UI线程中添加日志条目"""
        # 通过service_name找到对应的service
        service = None
        if hasattr(self, 'manager') and hasattr(self.manager, 'services'):
            for s in self.manager.services:
                if s.name == service_name:
                    service = s
                    break
        
        if service and service.log_widget:
            # 添加日志到缓冲区，使用锁保护
            with service.lock:
                # 检查缓冲区大小，超过上限则立即刷新
                if len(service.log_buffer) >= AppConstants.MAX_LOG_BUFFER_SIZE:
                    # 使用QMetaObject.invokeMethod确保在主线程中执行
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(
                        self, 
                        "_flush_log_buffer", 
                        Qt.QueuedConnection,
                        Q_ARG(object, service)
                    )
                service.log_buffer.append((message, error))
                
                # 使用QMetaObject.invokeMethod确保在主线程中执行日志刷新
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                # 50ms延迟，避免频繁更新UI
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(50, lambda: QMetaObject.invokeMethod(
                    self, 
                    "_flush_log_buffer", 
                    Qt.QueuedConnection,
                    Q_ARG(object, service)
                ))
        else:
            # 如果没有指定服务或服务没有日志控件，暂时不处理
            pass

    @pyqtSlot(object)
    def _flush_log_buffer(self, service):
        """刷新日志缓冲区到UI"""
        if not service or not service.log_widget:
            return
        
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
                    log_line = f"{prefix}{message}"
                    log_lines.append(log_line)
                
                # 构建日志文本
                log_text = "\n".join(log_lines)
                
                # 清空缓冲区
                service.log_buffer.clear()
            
            # 使用QMetaObject.invokeMethod确保在主线程中执行UI更新
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, 
                "_perform_log_ui_update", 
                Qt.QueuedConnection,
                Q_ARG(object, service),
                Q_ARG(str, log_text),
                Q_ARG(list, log_lines)
            )
    
    @pyqtSlot(object, str, list)
    def _perform_log_ui_update(self, service, log_text, log_lines):
        """在主线程中执行日志UI更新"""
        if not service or not service.log_widget:
            return
        
        try:
            # 1. 直接添加日志文本
            service.log_widget.appendPlainText(log_text)
            
            # 2. 处理独立日志窗口
            if hasattr(self, 'log_window') and self.log_window:
                # 遍历所有标签页，找到对应的日志控件
                for i in range(self.log_window.log_tabs.count()):
                    if self.log_window.log_tabs.widget(i) == service.log_widget:
                        # 添加到原始日志，以便过滤和搜索
                        if i not in self.log_window.original_logs:
                            self.log_window.original_logs[i] = []
                        self.log_window.original_logs[i].extend(log_lines)
                        break
            
            # 3. 限制日志行数，防止内存占用过多
            block_count = service.log_widget.blockCount()
            if block_count > AppConstants.MAX_LOG_LINES:
                # 只删除超过的行数，而不是每次都重新计算
                excess_lines = block_count - AppConstants.MAX_LOG_LINES
                
                # 避免直接操作QTextCursor，使用文档对象来操作文本
                doc = service.log_widget.document()
                if doc:
                    # 获取文档的第一个块
                    block = doc.firstBlock()
                    # 删除多余的块
                    for i in range(excess_lines):
                        if not block.isValid():
                            break
                        next_block = block.next()
                        doc.removeBlock(block)
                        block = next_block
                
                # 只在必要时滚动到末尾
                if service.log_widget.verticalScrollBar().value() == service.log_widget.verticalScrollBar().maximum():
                    # 避免使用ensureCursorVisible()，直接滚动到底部
                    service.log_widget.verticalScrollBar().setValue(service.log_widget.verticalScrollBar().maximum())
        except Exception as e:
            print(f"执行日志UI更新时发生错误: {str(e)}")
    

    
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
        
        # 直接添加服务列表、访问地址和公网访问到主布局
        self._add_service_list(main_layout)
        self._add_access_address(main_layout)
        self._add_public_access_address(main_layout)
        
        # 显示日志窗口按钮已移至主按钮区域
        
        # 初始化日志Tab容器
        self._add_log_window(None)
        
        # 设置状态栏
        self._setup_status_bar()
        
        # 绑定事件
        self._bind_events()
        
        # 绑定窗口大小变化事件
        self.resizeEvent = self.on_window_resize
        
        # 加载配置
        self.load_config()
        
        # 初始化服务列表
        self.update_service_list()
        
        # 初始化系统托盘
        self.init_system_tray()
        


    def save_config(self):
        """保存服务配置到JSON文件，实现事务性和备份机制"""
        try:
            # 构建配置数据结构，添加版本号和自启动设置
            config_data = {
                "version": "1.0",
                "auto_start": self.auto_start_checkbox.isChecked() if hasattr(self, 'auto_start_checkbox') else False,
                "services": []
            }
            
            # 遍历所有服务，将服务信息转换为可序列化的字典
            for service in self.manager.services:
                # 创建服务字典，包含所有配置
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
                    "ngrok_mode": service.ngrok_mode
                }
                
                # 加密敏感信息
                sensitive_data = {
                    "auth_rules": service.auth_rules,
                    "ngrok_authtoken": service.ngrok_authtoken
                }
                encrypted_sensitive = encrypt_data(sensitive_data)
                service_dict["encrypted_sensitive"] = base64.b64encode(encrypted_sensitive).decode()
                
                config_data["services"].append(service_dict)
            
            # 使用配置锁保护配置文件写入，防止并发写入冲突
            with self.manager.config_lock:
                # 1. 创建配置备份（如果配置文件存在）
                if os.path.exists(CONFIG_FILE):
                    # 生成带时间戳的备份文件名
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    backup_file = f"{CONFIG_FILE}.bak.{timestamp}"
                    
                    # 复制当前配置文件作为备份
                    shutil.copy2(CONFIG_FILE, backup_file)
                    
                    # 清理旧备份，只保留最近5个备份文件
                    self._cleanup_config_backups()
                
                # 2. 使用原子写入方式：先写入临时文件，再重命名为目标文件
                temp_config_file = CONFIG_FILE + '.tmp'
                
                # 写入临时文件
                with open(temp_config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                # 验证临时文件是否有效
                with open(temp_config_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # 验证JSON格式是否正确
                
                # 3. 原子重命名，确保配置文件完整性
                os.replace(temp_config_file, CONFIG_FILE)
            
            self.append_log("配置已保存到文件", service_name="系统")
        except (IOError, OSError, json.JSONDecodeError, ValueError, AttributeError) as e:
            self.append_log(f"保存配置失败: {str(e)}", error=True, service_name="系统")
            # 保存失败时，确保临时文件被清理
            temp_config_file = CONFIG_FILE + '.tmp'
            if os.path.exists(temp_config_file):
                try:
                    os.remove(temp_config_file)
                    self.append_log("临时配置文件已清理", service_name="系统")
                except Exception as cleanup_e:
                    self.append_log(f"清理临时文件失败: {str(cleanup_e)}", error=True, service_name="系统")
    
    def _cleanup_config_backups(self):
        """清理旧的配置备份文件，只保留最近5个"""
        try:
            # 获取所有备份文件
            backup_files = []
            for file in glob.glob(f"{CONFIG_FILE}.bak.*"):
                if os.path.isfile(file):
                    # 获取文件的修改时间
                    mtime = os.path.getmtime(file)
                    backup_files.append((mtime, file))
            
            # 按修改时间排序，保留最近5个
            backup_files.sort(reverse=True)  # 从新到旧排序
            
            # 删除多余的备份文件
            if len(backup_files) > 5:
                for _, file in backup_files[5:]:
                    os.remove(file)
                    self.append_log(f"已清理旧备份文件: {os.path.basename(file)}", service_name="系统")
        except Exception as e:
            self.append_log(f"清理配置备份失败: {str(e)}", error=True, service_name="系统")
    
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
                
                # 解密敏感信息
                sensitive_data = {
                    "auth_rules": [],
                    "ngrok_authtoken": ""
                }
                
                # 检查是否有加密的敏感数据
                encrypted_sensitive = service_dict.get("encrypted_sensitive")
                if encrypted_sensitive:
                    try:
                        # 解码并解密敏感数据
                        encrypted_bytes = base64.b64decode(encrypted_sensitive)
                        sensitive_data = decrypt_data(encrypted_bytes)
                    except Exception as e:
                        self.append_log(f"解密服务配置失败: {str(e)}", error=True, service_name="系统")
                        # 使用默认值继续
                else:
                    # 兼容旧版本配置文件
                    sensitive_data["auth_rules"] = service_dict.get("auth_rules", [])
                    sensitive_data["ngrok_authtoken"] = service_dict.get("ngrok_authtoken", "")
                
                # 设置认证规则
                service.auth_rules = sensitive_data["auth_rules"]
                
                # 设置ngrok相关配置
                service.ngrok_authtoken = sensitive_data["ngrok_authtoken"]
                service.ngrok_mode = service_dict.get("ngrok_mode", "authtoken")
                
                # 连接服务的状态更新信号
                # 使用QueuedConnection确保在主线程中执行
                from PyQt5.QtCore import Qt
                service.status_updated.connect(self.update_service_list, Qt.QueuedConnection)
                # 连接进度更新信号
                service.progress_updated.connect(lambda progress, message, s=service: self.update_ngrok_progress(progress, message, s), Qt.QueuedConnection)
                # 连接服务的日志更新信号
                service.log_updated.connect(self.append_log, Qt.QueuedConnection)
                # 添加到服务列表
                self.manager.add_service(service)
            
            self.append_log(f"从配置文件加载了 {len(self.manager.services)} 个服务", service_name="系统")
        except (IOError, OSError, json.JSONDecodeError, ValueError, AttributeError) as e:
            self.append_log(f"加载配置失败: {str(e)}", error=True, service_name="系统")
    
    def is_auto_start_enabled(self):
        """检查是否已启用系统自启动（仅支持Windows）"""
        try:
            key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                try:
                    # 尝试获取值
                    winreg.QueryValueEx(key, "DufsGUI")
                    return True
                except FileNotFoundError:
                    return False
        except (ImportError, OSError, KeyError) as e:
            self.append_log(f"检查自启动状态失败: {str(e)}", error=True, service_name="系统")
            return False

    def get_correct_exe_path(self):
        """获取正确的可执行文件路径，避免使用临时目录"""
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
            except (ImportError, OSError) as e:
                self.append_log(f"win32api方法失败: {str(e)}", service_name="系统")
            
            # 方法3: 检查当前进程的命令行
            try:
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
            except (ImportError, psutil.Error) as e:
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
        """添加系统自启动项（仅支持Windows）"""
        try:
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
        except (OSError, PermissionError, FileNotFoundError) as e:
            self.append_log(f"添加自启动失败: {str(e)}", error=True, service_name="系统")
            QMessageBox.warning(self, "警告", f"添加自启动失败: {str(e)}")

    def remove_auto_start(self):
        """移除系统自启动项（仅支持Windows）"""
        try:
            import winreg
            key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, "DufsGUI")
                    self.append_log("已移除开机自启动", service_name="系统")
                except FileNotFoundError:
                    pass  # 已经不存在，忽略
        except (OSError, PermissionError, subprocess.SubprocessError, FileNotFoundError) as e:
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
        
        # 设置表头拉伸策略，实现响应式列宽
        # 服务名称列自动拉伸
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        # 端口和状态列固定宽度
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        # 公网访问列自动拉伸，确保URL完整显示
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        # 详情列固定宽度
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        
        # 添加窗口大小变化事件处理，动态调整列宽
        self.service_tree.header().sectionResized.connect(self.on_header_section_resized)
        
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
        self.addr_edit.setMinimumWidth(200)  # 设置最小宽度
        self.addr_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 设置为可扩展
        addr_layout.addWidget(self.addr_edit)
        
        copy_btn = QPushButton("复制")
        copy_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        copy_btn.setMinimumWidth(60)  # 设置最小宽度
        copy_btn.clicked.connect(self.copy_address)
        addr_layout.addWidget(copy_btn)
        
        browse_btn = QPushButton("浏览器访问")
        browse_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        browse_btn.setMinimumWidth(100)  # 设置最小宽度
        browse_btn.clicked.connect(self.browser_access)
        addr_layout.addWidget(browse_btn)
        
        addr_group.setLayout(addr_layout)
        main_layout.addWidget(addr_group)
    
    def _add_public_access_address(self, main_layout):
        """添加公网访问地址UI，优化用户体验"""
        public_group = QGroupBox("公网访问")
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
        self.public_addr_edit.setMinimumWidth(200)  # 设置最小宽度
        self.public_addr_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 设置为可扩展
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

        # 添加ngrok启动进度条
        self.ngrok_progress_bar = QProgressBar()
        self.ngrok_progress_bar.setRange(0, 100)
        self.ngrok_progress_bar.setValue(0)
        self.ngrok_progress_bar.setVisible(False)  # 默认隐藏
        self.ngrok_progress_bar.setFormat("启动中... %p%")
        public_layout.addWidget(self.ngrok_progress_bar)
        
        # 添加服务启动进度条
        self.service_progress_bar = QProgressBar()
        self.service_progress_bar.setRange(0, 100)
        self.service_progress_bar.setValue(0)
        self.service_progress_bar.setVisible(False)  # 默认隐藏
        self.service_progress_bar.setFormat("准备阶段... %p%")
        public_layout.addWidget(self.service_progress_bar)

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
    
    def update_ngrok_progress(self, progress, message, service=None):
        """更新ngrok启动进度条
        
        Args:
            progress (int): 进度值（0-100）
            message (str): 进度消息
            service: 发送进度更新的服务对象
        """
        # 确保在主线程中执行UI更新
        from PyQt5.QtCore import QCoreApplication, QEvent
        class UiUpdateEvent(QEvent):
            def __init__(self, callback):
                super().__init__(QEvent.User)
                self.callback = callback
        
        def post_ui_update(callback):
            app = QCoreApplication.instance()
            if app:
                event = UiUpdateEvent(callback)
                app.postEvent(self, event)
        
        post_ui_update(lambda: self._update_ngrok_progress_ui(progress, message, service))
    
    def _update_ngrok_progress_ui(self, progress, message, service=None):
        """在主线程中更新ngrok启动进度条UI
        
        Args:
            progress (int): 进度值（0-100）
            message (str): 进度消息
            service: 发送进度更新的服务对象
        """
        # 检查服务是否是当前选中的服务
        if service:
            # 获取当前选中的服务
            selected_items = self.service_tree.selectedItems()
            if selected_items:
                selected_item = selected_items[0]
                index = selected_item.data(0, Qt.UserRole)
                if index is not None:
                    current_service = self.manager.services[index]
                    # 只有当发送进度更新的服务是当前选中的服务时，才更新进度条
                    if service != current_service:
                        return
        
        if hasattr(self, 'ngrok_progress_bar'):
            # 检查是否是ngrok已停止的情况
            if progress == 0 and message == "ngrok已停止":
                # 直接隐藏进度条
                self.ngrok_progress_bar.setVisible(False)
            else:
                # 显示进度条
                self.ngrok_progress_bar.setVisible(True)
                # 更新进度值
                self.ngrok_progress_bar.setValue(progress)
                # 更新进度消息
                self.ngrok_progress_bar.setFormat(f"{message} %p%")
                
                # 如果进度达到100%，延迟隐藏进度条
                if progress == 100:
                    # 使用post_ui_update确保在主线程中执行UI更新
                    from PyQt5.QtCore import QCoreApplication, QEvent
                    class UiUpdateEvent(QEvent):
                        def __init__(self, callback):
                            super().__init__(QEvent.User)
                            self.callback = callback
                    
                    def post_ui_update(callback):
                        app = QCoreApplication.instance()
                        if app:
                            event = UiUpdateEvent(callback)
                            app.postEvent(self, event)
                    
                    # 延迟1秒后隐藏进度条
                    def delayed_hide():
                        import time
                        time.sleep(1)
                        post_ui_update(lambda: self.ngrok_progress_bar.setVisible(False))
                    import threading
                    threading.Thread(target=delayed_hide, daemon=True).start()
    
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
        
        # 停止所有服务，无论状态如何，确保所有ngrok进程都被终止
        for i in range(len(self.manager.services)):
            service = self.manager.services[i]
            # 检查服务是否有ngrok进程在运行，无论服务本身的状态如何
            if hasattr(service, 'ngrok_process') and service.ngrok_process:
                # 直接停止ngrok进程
                if hasattr(service, 'stop_ngrok'):
                    service.stop_ngrok()
            # 停止服务本身
            if service.status == ServiceStatus.RUNNING or service.status == ServiceStatus.STARTING:
                self.stop_service(i)
        
        # 确保所有线程都正确退出
        # 给线程和进程足够的时间来清理资源
        import time
        time.sleep(1.0)  # 增加等待时间到1秒
        
        # 再次检查并清理剩余的ngrok进程
        for service in self.manager.services:
            if hasattr(service, 'ngrok_process') and service.ngrok_process:
                try:
                    # 强制终止剩余的ngrok进程
                    service.ngrok_process.terminate()
                    service.ngrok_process.wait(timeout=0.5)
                except (subprocess.TimeoutExpired, OSError):
                    try:
                        service.ngrok_process.kill()
                    except (OSError, ValueError):
                        pass
                finally:
                    service.ngrok_process = None
        
        # 再给一点时间确保所有资源都被释放
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
        return self.manager.is_port_available(port, exclude_service)
    
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
        except (socket.error, OSError):
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
                except (IndexError, TypeError):
                    pass
        except (socket.error, OSError):
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
                except (IndexError, TypeError):
                    pass
            # 如果找到有效的IP地址，返回第一个
            if ip_list:
                return ip_list[0]
        except (socket.error, OSError):
            pass
        
        # 方法4：使用socket.gethostbyname获取IP地址
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip != '127.0.0.1':
                return local_ip
        except (socket.error, OSError):
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
                                        self.append_log(line, error=is_stderr, service_name=service.name)
                        except BlockingIOError:
                            # 没有数据可读，继续循环
                            pass
                        except (OSError, IOError, BrokenPipeError) as e:
                            # 其他错误，可能是管道已关闭
                            break
                        
                        # 控制循环频率，避免占用过多CPU资源
                        time.sleep(0.1)
                    except (OSError, IOError, BrokenPipeError) as e:
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
                webbrowser.open(address)
            except (webbrowser.Error, OSError) as e:
                self.append_log(f"浏览器访问失败: {str(e)}", error=True)
                QMessageBox.warning(self, "警告", f"浏览器访问失败: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "请先选择一个服务")
    
    def browser_access_public(self):
        """在浏览器中访问公网服务"""
        address = self.public_addr_edit.text()
        if address:
            try:
                webbrowser.open(address)
            except (webbrowser.Error, OSError) as e:
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
        # 获取当前选中的服务索引
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            current_index = selected_item.data(0, Qt.UserRole)
            if current_index is not None:
                # 只有当目标服务是当前选中的服务时，才更新公网访问UI
                current_service = self.manager.services[current_index]
                if current_service == service:
                    if service and service.public_access_status == "running" and service.public_url:
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
                service = self.manager.services[index]
                if hasattr(self, 'refresh_address'):
                    self.refresh_address(index)
                self.update_public_access_ui(service)
                # 隐藏进度条
                if hasattr(self, 'ngrok_progress_bar'):
                    self.ngrok_progress_bar.setVisible(False)
                if hasattr(self, 'service_progress_bar'):
                    self.service_progress_bar.setVisible(False)
                # 更新ngrok配置面板，显示当前选中服务的配置
        else:
            # 没有选择服务，隐藏进度条
            if hasattr(self, 'ngrok_progress_bar'):
                self.ngrok_progress_bar.setVisible(False)
            if hasattr(self, 'service_progress_bar'):
                self.service_progress_bar.setVisible(False)

    
    def on_header_section_resized(self, logicalIndex, oldSize, newSize):
        """表头列宽调整事件处理"""
        # 可以添加一些自定义的列宽调整逻辑
        pass
    
    def on_window_resize(self, event):
        """窗口大小变化事件处理，实现响应式UI"""
        # 获取新的窗口宽度
        new_width = self.width()
        
        # 调整服务列表的列宽，根据窗口宽度动态分配
        if self.service_tree:
            # 计算可用宽度，减去固定列的宽度
            fixed_widths = self.service_tree.columnWidth(1) + self.service_tree.columnWidth(2) + self.service_tree.columnWidth(4)
            available_width = new_width - 300  # 减去边距和其他元素的宽度
            
            # 确保可用宽度为正数
            if available_width > 0:
                # 分配可用宽度给服务名称和公网访问列
                name_width = int(available_width * 0.4)  # 服务名称列占40%
                public_width = int(available_width * 0.6)  # 公网访问列占60%
                
                # 确保最小宽度
                name_width = max(name_width, 200)  # 服务名称列最小200像素
                public_width = max(public_width, 250)  # 公网访问列最小250像素
                
                # 更新列宽
                self.service_tree.setColumnWidth(0, name_width)  # 服务名称
                self.service_tree.setColumnWidth(3, public_width)  # 公网访问
        
        # 调用父类的resizeEvent方法
        super().resizeEvent(event)
    
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
        
        # ngrok配置信息
        details_text += f"ngrok模式: {service.ngrok_mode}\n"
        authtoken_display = f"{service.ngrok_authtoken[:10]}..." if service.ngrok_authtoken else "未配置"
        details_text += f"ngrok Authtoken: {authtoken_display}\n"
        
        QMessageBox.information(self, f"服务详情 - {service.name}", details_text)
    
    def on_service_selected(self):
        """处理服务列表选择事件"""
        # 断开之前服务的进度更新信号连接
        if hasattr(self, '_current_progress_service') and hasattr(self, '_on_progress_updated'):
            try:
                self._current_progress_service.progress_updated.disconnect(self._on_progress_updated)
            except Exception as e:
                pass
        
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            self.addr_edit.setText("")
            self.update_public_access_ui(None)
            # 隐藏进度条
            if hasattr(self, 'ngrok_progress_bar'):
                self.ngrok_progress_bar.setVisible(False)
            if hasattr(self, 'service_progress_bar'):
                self.service_progress_bar.setVisible(False)
            return
        
        # 获取选中的服务项
        selected_item = selected_items[0]
        
        # 获取服务索引
        index = selected_item.data(0, Qt.UserRole)
        if index is None:
            self.addr_edit.setText("")
            self.update_public_access_ui(None)
            # 隐藏进度条
            if hasattr(self, 'ngrok_progress_bar'):
                self.ngrok_progress_bar.setVisible(False)
            if hasattr(self, 'service_progress_bar'):
                self.service_progress_bar.setVisible(False)
            return
        
        # 获取服务对象
        service = self.manager.services[index]
        
        # 更新访问地址
        if hasattr(self, 'refresh_address'):
            self.refresh_address(index)
        
        # 更新公网访问UI
        self.update_public_access_ui(service)
        
        # 根据服务的公网访问状态显示或隐藏进度条
        if hasattr(self, 'ngrok_progress_bar'):
            if service.public_access_status == "starting" and hasattr(service, 'ngrok_start_progress'):
                # 显示进度条并设置为当前服务的进度
                self.ngrok_progress_bar.setVisible(True)
                self.ngrok_progress_bar.setValue(service.ngrok_start_progress)
                self.ngrok_progress_bar.setFormat(f"启动中... {service.ngrok_start_progress}%")
            else:
                # 隐藏进度条
                self.ngrok_progress_bar.setVisible(False)
        
        if hasattr(self, 'service_progress_bar'):
            # 服务启动进度条逻辑
            if service.status == ServiceStatus.STARTING:
                self.service_progress_bar.setVisible(True)
                # 可以根据服务的启动进度设置值
            else:
                self.service_progress_bar.setVisible(False)
        
        # 如果独立日志窗口已创建，切换到对应的日志标签
        if service.log_widget and self.log_window is not None:
            # 在独立日志窗口中切换到对应的日志标签
            for i in range(self.log_window.log_tabs.count()):
                if self.log_window.log_tabs.widget(i) == service.log_widget:
                    self.log_window.log_tabs.setCurrentIndex(i)
                    break
        

    
    def refresh_address(self, index):
        """刷新访问地址"""
        # 获取当前选中的服务索引
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            current_index = selected_item.data(0, Qt.UserRole)
            # 只有当目标服务是当前选中的服务时，才更新地址栏
            if current_index == index:
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
            
            # 检查服务是否正在启动公网访问
            if service.public_access_status == "starting":
                QMessageBox.information(self, "提示", "公网访问正在启动中，请稍候")
                return
            
            # 禁用公网访问按钮，防止重复点击
            self.public_access_btn.setEnabled(False)
            
            # 添加用户操作日志
            self.append_log(f"用户请求为服务 {service.name} 启动公网访问", service_name=service.name)
            
            # 检查authtoken或API key是否已配置
            authtoken_configured = False
            if service.ngrok_mode == "authtoken":
                # 检查authtoken是否已配置
                if service.ngrok_authtoken or os.environ.get("NGROK_AUTHTOKEN"):
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
                        # 重新启用公网访问按钮
                        self.public_access_btn.setEnabled(True)
                        return
            
            # 显示ngrok进度条
            self.ngrok_progress_bar.setVisible(True)
            self.ngrok_progress_bar.setValue(0)
            self.ngrok_progress_bar.setFormat("正在启动ngrok... %p%")
            QApplication.processEvents()
            
            # 设置公网访问状态为启动中，使用统一的状态更新方法
            service.update_status(public_access_status="starting")
            self.update_service_list()
            
            # 保存当前服务的引用
            current_service_ref = service
            
            # 定义进度更新回调函数
            def on_progress_updated(progress, message, service=None):
                """处理ngrok进度更新"""
                # 首先检查当前是否有选中的服务，并且选中的服务是当前服务
                selected_items = self.service_tree.selectedItems()
                if not selected_items:
                    return
                selected_item = selected_items[0]
                current_index = selected_item.data(0, Qt.UserRole)
                if current_index is None:
                    return
                selected_service = self.manager.services[current_index]
                # 使用传入的服务参数进行检查
                if service and selected_service != service:
                    return
                # 向后兼容，使用current_service_ref作为后备
                elif selected_service != current_service_ref:
                    return
                
                # 确保在主线程中执行UI更新
                from PyQt5.QtCore import QTimer
                
                # 使用QTimer.singleShot确保在主线程中执行UI更新
                def update_progress():
                    # 再次检查当前选中的服务是否是发送进度更新的服务
                    selected_items = self.service_tree.selectedItems()
                    if not selected_items:
                        return
                    selected_item = selected_items[0]
                    current_index = selected_item.data(0, Qt.UserRole)
                    if current_index is None:
                        return
                    selected_service = self.manager.services[current_index]
                    if selected_service != current_service_ref:
                        return
                    
                    # 显示进度条并更新其值
                    try:
                        self.ngrok_progress_bar.setVisible(True)
                        self.ngrok_progress_bar.setValue(progress)
                        self.ngrok_progress_bar.setFormat(f"{message} {progress}%")
                    except Exception as e:
                        pass
                QTimer.singleShot(0, update_progress)
            
            # 保存当前服务的引用和回调函数
            self._current_progress_service = current_service_ref
            self._on_progress_updated = on_progress_updated
            
            # 连接服务的进度更新信号
            service.progress_updated.connect(lambda progress, message, s=service: on_progress_updated(progress, message, s))
            
            # 在后台线程中启动ngrok，避免阻塞UI
            def start_ngrok_thread():
                # 导入必要的模块
                import time
                # 定义UI更新函数
                from PyQt5.QtCore import QCoreApplication, QEvent
                class UiUpdateEvent(QEvent):
                    def __init__(self, callback):
                        super().__init__(QEvent.User)
                        self.callback = callback
                
                def post_ui_update(callback):
                    app = QCoreApplication.instance()
                    if app:
                        event = UiUpdateEvent(callback)
                        app.postEvent(self, event)
                
                try:
                    # 使用post_ui_update确保在主线程中调用UI方法
                    post_ui_update(lambda: self.append_log(f"正在为服务 {service.name} 启动ngrok...", service_name=service.name))
                    # 启动ngrok - 现在start_ngrok返回None，核心逻辑在后台线程中执行
                    service.start_ngrok()
                    # 不需要处理返回值，因为ngrok的启动状态和URL会通过status_updated信号通知UI
                    
                    # 等待ngrok启动并获取URL，最多等待30秒
                    for i in range(30):
                        # 检查ngrok是否成功启动
                        if service.public_url and service.public_url.startswith("http"):
                            # 公网URL已获取成功
                            post_ui_update(lambda: self.append_log(f"ngrok已成功启动，公网URL: {service.public_url}", service_name=service.name))
                            post_ui_update(lambda: self.append_log(f"服务 {service.name} 公网访问已启用", service_name=service.name))
                            # 立即更新服务列表，确保公网访问状态显示正确
                            post_ui_update(self.update_service_list)
                            # 更新公网地址栏显示
                            post_ui_update(lambda: self.update_public_access_ui(service))
                            # 延迟隐藏进度条，使用post_ui_update确保在主线程中执行
                            def delayed_hide():
                                time.sleep(1)
                                post_ui_update(self.ngrok_progress_bar.hide)
                                # 重新启用公网访问按钮
                                post_ui_update(lambda: self.public_access_btn.setEnabled(True))
                            threading.Thread(target=delayed_hide, daemon=True).start()
                            break
                        elif service.public_access_status == "running":
                            # 状态为running但还没获取到URL，继续等待
                            post_ui_update(lambda: self.append_log(f"ngrok已启动，正在获取公网URL...", service_name=service.name))
                            # 立即更新服务列表，确保公网访问状态显示正确
                            post_ui_update(self.update_service_list)
                            # 延迟隐藏进度条，使用post_ui_update确保在主线程中执行
                            def delayed_hide():
                                time.sleep(1)
                                post_ui_update(self.ngrok_progress_bar.hide)
                                # 重新启用公网访问按钮
                                post_ui_update(lambda: self.public_access_btn.setEnabled(True))
                            threading.Thread(target=delayed_hide, daemon=True).start()
                            break
                        # 等待1秒后重试
                        time.sleep(1)
                    else:
                        # 超过30秒仍未获取到URL，更新服务列表
                        post_ui_update(self.update_service_list)
                        post_ui_update(self.ngrok_progress_bar.hide)
                        # 重新启用公网访问按钮
                        post_ui_update(lambda: self.public_access_btn.setEnabled(True))
                except (OSError, ValueError, subprocess.SubprocessError) as e:
                    error_msg = f"启动ngrok失败: {str(e)}"
                    post_ui_update(lambda: self.append_log(error_msg, error=True, service_name=service.name))
                    post_ui_update(lambda: self.append_log(f"服务 {service.name} 公网访问启动失败", error=True, service_name=service.name))
                    post_ui_update(lambda: QMessageBox.critical(self, "ngrok启动失败", error_msg))
                    post_ui_update(self.ngrok_progress_bar.hide)
                    # 更新服务列表，显示错误状态
                    post_ui_update(self.update_service_list)
                    # 重新启用公网访问按钮
                    post_ui_update(lambda: self.public_access_btn.setEnabled(True))
                finally:
                    # 使用post_ui_update确保在主线程中调用UI方法
                    post_ui_update(lambda: self.update_public_access_ui(service))
                    # 断开进度更新信号连接
                    try:
                        service.progress_updated.disconnect(on_progress_updated)
                    except:
                        pass
                    # 确保公网访问按钮被重新启用
                    post_ui_update(lambda: self.public_access_btn.setEnabled(True))
            
            thread = threading.Thread(target=start_ngrok_thread)
            thread.daemon = True
            thread.start()
    
    def stop_public_access(self, index):
        """停止公网访问"""
        if 0 <= index < len(self.manager.services):
            service = self.manager.services[index]
            # 检查服务是否正在停止公网访问
            if service.public_access_status == "stopping":
                QMessageBox.information(self, "提示", "公网访问正在停止中，请稍候")
                return
            
            # 禁用公网访问按钮，防止重复点击
            self.public_access_btn.setEnabled(False)
            
            # 使用QTimer确保在主线程中调用UI方法
            QTimer.singleShot(0, lambda: self.append_log(f"用户请求为服务 {service.name} 停止公网访问", service_name=service.name))
            QTimer.singleShot(0, lambda: self.append_log(f"正在为服务 {service.name} 停止ngrok...", service_name=service.name))
            
            # 停止ngrok进程
            service.stop_ngrok(wait=True)
            
            # 确保状态已正确更新
            service.public_url = ""
            service.public_access_status = "stopped"
            
            # 发送状态更新信号
            service.status_updated.emit()
            
            # 使用QTimer确保在主线程中调用UI方法
            QTimer.singleShot(0, lambda: self.append_log(f"ngrok已成功停止", service_name=service.name))
            QTimer.singleShot(0, lambda: self.append_log(f"服务 {service.name} 公网访问已停止", service_name=service.name))
            
            # 延迟更新UI，确保所有状态已正确更新
            QTimer.singleShot(100, self.update_service_list)
            QTimer.singleShot(100, lambda: self.update_public_access_ui(service))
            # 重新启用公网访问按钮
            QTimer.singleShot(100, lambda: self.public_access_btn.setEnabled(True))
    
    def _create_service_tree_item(self, service, index):
        """创建服务树项"""
        # 状态可视化增强，使用更直观的emoji图标
        status_emoji = "❓"
        if service.status == ServiceStatus.RUNNING:
            status_emoji = "🟢"
        elif service.status == ServiceStatus.STARTING:
            status_emoji = "🟡"
        elif service.status == ServiceStatus.STOPPED:
            status_emoji = "🔴"
        elif service.status == ServiceStatus.ERROR:
            status_emoji = "🟠"
        
        # 显示带图标的状态
        status_with_icon = f"{status_emoji} {service.status}"
        
        # 创建树项，公网访问列根据服务状态显示不同内容（仅显示状态，不显示完整URL）
        public_access_text = ""
        if service.status != ServiceStatus.RUNNING:
            public_access_text = "请先启动服务"
        elif service.public_access_status == "running":
            # 只显示状态，不显示完整URL
            public_access_text = "运行中"
        elif service.public_access_status == "starting":
            # 显示启动进度
            progress = getattr(service, 'ngrok_start_progress', 0)
            public_access_text = f"启动中... {progress}%"
        elif service.public_access_status == "stopping":
            public_access_text = "停止中..."
        else:
            public_access_text = "点击启动"
        
        # 合并认证和权限为详情列，使用图标表示权限
        auth_info = ""
        if service.auth_rules:
            username = service.auth_rules[0].get("username", "")
            password = service.auth_rules[0].get("password", "")
            auth_info = f"{username}:{password}"
        
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
        color = AppConstants.STATUS_COLORS.get(service.status, "#95a5a6")  # 默认灰色
        item.setForeground(2, QColor(color))
        
        # 将服务在self.manager.services列表中的实际索引存储到树项中
        item.setData(0, Qt.UserRole, index)
        
        return item
    
    def _update_service_tree_item(self, item, service, index):
        """更新服务树项"""
        # 状态可视化增强，使用更直观的emoji图标
        status_emoji = "❓"
        if service.status == ServiceStatus.RUNNING:
            status_emoji = "🟢"
        elif service.status == ServiceStatus.STARTING:
            status_emoji = "🟡"
        elif service.status == ServiceStatus.STOPPED:
            status_emoji = "🔴"
        elif service.status == ServiceStatus.ERROR:
            status_emoji = "🟠"
        
        # 显示带图标的状态
        status_with_icon = f"{status_emoji} {service.status}"
        
        # 创建树项，公网访问列根据服务状态显示不同内容（仅显示状态，不显示完整URL）
        public_access_text = ""
        if service.status != ServiceStatus.RUNNING:
            public_access_text = "请先启动服务"
        elif service.public_access_status == "running":
            # 只显示状态，不显示完整URL
            public_access_text = "运行中"
        elif service.public_access_status == "starting":
            public_access_text = "启动中..."
        elif service.public_access_status == "stopping":
            public_access_text = "停止中..."
        else:
            public_access_text = "点击启动"
        
        # 合并认证和权限为详情列，使用图标表示权限
        auth_info = ""
        if service.auth_rules:
            username = service.auth_rules[0].get("username", "")
            password = service.auth_rules[0].get("password", "")
            auth_info = f"{username}:{password}"
        
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
        
        # 更新树项内容
        item.setText(0, service.name)
        item.setText(1, service.port)
        item.setText(2, status_with_icon)
        item.setText(3, public_access_text)
        item.setText(4, details_text)
        
        # 设置状态列的文本颜色（状态列是索引2）
        color = AppConstants.STATUS_COLORS.get(service.status, "#95a5a6")  # 默认灰色
        item.setForeground(2, QColor(color))
        
        # 更新服务索引
        item.setData(0, Qt.UserRole, index)
    
    def _restore_service_selection(self, selected_names):
        """恢复服务选择状态"""
        # 恢复选中状态（刷新列表后保留之前的选择）
        for i in range(self.service_tree.topLevelItemCount()):
            item = self.service_tree.topLevelItem(i)
            service_name = item.text(0)
            is_selected = service_name in selected_names
            item.setSelected(is_selected)
    
    def update_service_list(self):
        """更新服务列表，采用增量更新提高性能"""
        # 记录当前选中的服务名称（用于刷新后恢复选择）
        selected_names = [item.text(0) for item in self.service_tree.selectedItems()]
        
        # 获取现有树项数量
        existing_count = self.service_tree.topLevelItemCount()
        current_count = len(self.manager.services)
        
        # 1. 更新现有树项
        for i in range(min(existing_count, current_count)):
            service = self.manager.services[i]
            item = self.service_tree.topLevelItem(i)
            
            # 更新树项内容
            self._update_service_tree_item(item, service, i)
        
        # 2. 如果服务数量增加，添加新的树项
        if current_count > existing_count:
            for i in range(existing_count, current_count):
                service = self.manager.services[i]
                item = self._create_service_tree_item(service, i)
                self.service_tree.addTopLevelItem(item)
        
        # 3. 如果服务数量减少，移除多余的树项
        elif current_count < existing_count:
            for i in range(existing_count - 1, current_count - 1, -1):
                self.service_tree.takeTopLevelItem(i)
        
        # 4. 恢复选中状态
        self._restore_service_selection(selected_names)
        
        # 跳过原有循环，使用新的增量更新逻辑
        # 更新状态栏服务计数
        self.update_status_bar()
        
        # 更新访问地址，确保当前选中服务的地址显示在地址栏中
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            index = selected_item.data(0, Qt.UserRole)
            if index is not None:
                if hasattr(self, 'refresh_address'):
                    self.refresh_address(index)
                # 同时更新公网访问UI，确保公网地址也能及时更新
                service = self.manager.services[index]
                self.update_public_access_ui(service)
    
    def add_service(self):
        """添加新服务"""
        dialog = DufsServiceDialog(self, existing_services=self.manager.services)
        if dialog.exec_():
            service = dialog.service
            # 连接服务的状态更新信号
            from PyQt5.QtCore import Qt
            service.status_updated.connect(self.update_service_list, Qt.QueuedConnection)
            # 连接进度更新信号
            service.progress_updated.connect(lambda progress, message, s=service: self.update_ngrok_progress(progress, message, s), Qt.QueuedConnection)
            # 连接服务的日志更新信号，使用QueuedConnection确保在主线程中执行
            service.log_updated.connect(self.append_log, Qt.QueuedConnection)
            self.manager.add_service(service)
            self.status_updated.emit()
            self.status_bar.showMessage(f"已添加服务: {service.name}")
            
            # 使用QTimer延迟执行耗时操作，避免卡顿
            QTimer.singleShot(200, self.refresh_tray_menu)  # 延迟刷新托盘菜单
            QTimer.singleShot(300, self.save_config)  # 延迟保存配置
    
    def edit_service(self, item=None, column=None):
        """编辑选中的服务"""
        # 导入Qt
        from PyQt5.QtCore import Qt
        
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
            
            # 比较基本配置
            if dialog.service.name != service.name or dialog.service.port != service.port:
                config_changed = True
            # 比较路径和权限配置
            elif dialog.service.serve_path != service.serve_path or dialog.service.allow_upload != service.allow_upload:
                config_changed = True
            # 比较更多权限配置
            elif dialog.service.allow_delete != service.allow_delete or dialog.service.allow_search != service.allow_search:
                config_changed = True
            # 比较最后一个权限配置
            elif dialog.service.allow_archive != service.allow_archive:
                config_changed = True
            
            # 比较ngrok配置 - 独立检查，不使用elif
            if dialog.service.ngrok_authtoken != service.ngrok_authtoken or dialog.service.ngrok_mode != service.ngrok_mode:
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
            # 重新连接服务的状态更新信号
            from PyQt5.QtCore import Qt
            dialog.service.status_updated.connect(self.update_service_list, Qt.QueuedConnection)
            # 连接服务的进度更新信号
            dialog.service.progress_updated.connect(lambda progress, message, s=dialog.service: self.update_ngrok_progress(progress, message, s), Qt.QueuedConnection)
            # 连接服务的日志更新信号，使用QueuedConnection确保在主线程中执行
            dialog.service.log_updated.connect(self.append_log, Qt.QueuedConnection)
            self.status_updated.emit()
            
            # 如果服务之前是运行中的，启动新服务
            if was_running:
                QMessageBox.information(self, "提示", "服务配置已更改，服务将自动重启以应用新配置。")
                self.start_service(index)
            
            # 使用QTimer延迟执行耗时操作，避免卡顿
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
        
        # 调用带进度反馈的启动服务方法
        self.start_service_with_progress(index)
    
    def start_service_with_progress(self, index=None):
        """带进度反馈的服务启动
        
        Args:
            index (int, optional): 服务索引
        """
        # 获取并验证服务索引
        index = self._get_service_index(index)
        if index is None:
            return
        
        # 获取服务对象
        service = self.manager.services[index]
        
        # 检查服务是否已经在运行或启动中
        if service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
            self.append_log(f"服务 {service.name} 已经在{service.status}，无需重复启动", service_name=service.name, service=service)
            # 隐藏进度条
            self.service_progress_bar.hide()
            return
        
        # 显示主面板中的服务启动进度条
        self.service_progress_bar.setVisible(True)
        self.service_progress_bar.setValue(0)
        self.service_progress_bar.setFormat("准备阶段... %p%")
        QApplication.processEvents()
        
        try:
            # 1. 准备阶段（20%）
            self.service_progress_bar.setValue(20)
            self.service_progress_bar.setFormat("准备阶段... 正在准备启动服务... %p%")
            QApplication.processEvents()
            
            # 查找可用端口
            available_port = self._find_available_port(service)
            if available_port is None:
                self.append_log(f"服务 {service.name} 启动被取消", service_name=service.name, service=service)
                self.service_progress_bar.setVisible(False)
                return
            
            # 2. 配置阶段（40%）
            self.service_progress_bar.setValue(40)
            self.service_progress_bar.setFormat("配置阶段... 正在配置服务参数... %p%")
            QApplication.processEvents()
            
            # 构建命令
            command = self._build_command(service, available_port)
            if command is None:
                self.append_log(f"服务 {service.name} 启动被取消", service_name=service.name, service=service)
                self.service_progress_bar.setVisible(False)
                return
            
            # 3. 启动阶段（60%）
            self.service_progress_bar.setValue(60)
            self.service_progress_bar.setFormat("启动阶段... 正在启动服务进程... %p%")
            QApplication.processEvents()
            
            # 设置服务状态为启动中
            service.update_status(status=ServiceStatus.STARTING)
            
            # 记录启动过程
            self.append_log("="*50, service_name=service.name, service=service)
            self.append_log(f"开始启动服务 {service.name}", service_name=service.name, service=service)
            self.append_log(f"服务状态: 正在准备启动", service_name=service.name, service=service)
            self.append_log(f"服务路径: {service.serve_path}", service_name=service.name, service=service)
            self.append_log(f"服务端口: {available_port}", service_name=service.name, service=service)
            self.append_log(f"执行命令: {' '.join(command)}", service_name=service.name, service=service)
            
            # 4. 执行阶段（80%）
            self.service_progress_bar.setValue(80)
            self.service_progress_bar.setFormat("执行阶段... 正在执行启动命令... %p%")
            QApplication.processEvents()
            
            # 启动服务进程
            start_success = self._start_service_process(service, command)
            
            if not start_success:
                # 启动失败，重置状态为未运行
                service.update_status(status=ServiceStatus.STOPPED)
                # 释放已分配的端口
                try:
                    port = int(available_port)
                    self.manager.release_allocated_port(port)
                except (ValueError, AttributeError):
                    pass
                self.append_log(f"服务 {service.name} 启动被取消", service_name=service.name, service=service)
                self.service_progress_bar.setVisible(False)
                return
            
            # 5. 检查阶段（90%）
            self.service_progress_bar.setValue(90)
            self.service_progress_bar.setFormat("检查阶段... 正在检查服务状态... %p%")
            QApplication.processEvents()
            
            # 启动服务启动检查定时器
            self._start_service_check_timer(service, index)
            
            # 6. 完成阶段（100%）
            self.service_progress_bar.setValue(100)
            self.service_progress_bar.setFormat("完成阶段... 服务启动完成！ %p%")
            QApplication.processEvents()
            
            # 记录完成信息
            self.append_log(f"✓ 服务 {service.name} 启动命令已执行，正在检查服务状态...", service_name=service.name, service=service)
            self.append_log("="*50, service_name=service.name, service=service)
        except Exception as e:
            # 记录错误信息
            self.append_log(f"启动服务时发生错误: {str(e)}", error=True, service_name=service.name, service=service)
            # 重置状态为未运行
            service.update_status(status=ServiceStatus.STOPPED)
            self.append_log(f"服务 {service.name} 启动被取消", service_name=service.name, service=service)
            # 隐藏进度条
            self.service_progress_bar.hide()
        finally:
            # 延迟隐藏进度条，让用户看到完成状态
            QTimer.singleShot(1000, self.service_progress_bar.hide)

    
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
        # 如果服务已经有日志控件，直接返回
        if service.log_widget is not None:
            return
        
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
        
        # 如果独立日志窗口已创建，添加到独立窗口
        if self.log_window is not None:
            # 获取当前标签页数量，即新添加的标签页索引
            service.log_tab_index = self.log_window.log_tabs.count()
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
            service.update_status(status=ServiceStatus.STARTING)
            
            # 记录启动过程
            self.append_log("="*50, service_name=service.name, service=service)
            self.append_log(f"开始启动服务 {service.name}", service_name=service.name, service=service)
            self.append_log(f"服务状态: 正在准备启动", service_name=service.name, service=service)
            self.append_log(f"服务路径: {service.serve_path}", service_name=service.name, service=service)
            self.append_log(f"服务端口: {available_port}", service_name=service.name, service=service)
            self.append_log(f"执行命令: {' '.join(command)}", service_name=service.name, service=service)
            
            # 直接在主线程中启动服务进程
            start_success = self._start_service_process(service, command)
            
            if not start_success:
                # 启动失败，重置状态为未运行
                service.update_status(status=ServiceStatus.STOPPED)
                # 释放已分配的端口
                try:
                    port = int(available_port)
                    self.manager.release_allocated_port(port)
                except (ValueError, AttributeError):
                    pass
                
                # 优化错误信息，添加更具体的提示和解决建议
                error_msg = f"✗ 服务 {service.name} 启动失败"
                self.append_log(error_msg, error=True, service_name=service.name, service=service)
                self.append_log("可能的原因：", error=True, service_name=service.name, service=service)
                self.append_log("1. dufs.exe 文件不存在或路径错误", error=True, service_name=service.name, service=service)
                self.append_log("2. 服务路径不存在或权限不足", error=True, service_name=service.name, service=service)
                self.append_log("3. 端口 {available_port} 被其他进程占用", error=True, service_name=service.name, service=service)
                self.append_log("解决建议：", error=True, service_name=service.name, service=service)
                self.append_log("1. 检查 dufs.exe 是否存在于程序目录", error=True, service_name=service.name, service=service)
                self.append_log("2. 确保服务路径存在且有读写权限", error=True, service_name=service.name, service=service)
                self.append_log("3. 尝试手动更换服务端口", error=True, service_name=service.name, service=service)
                self.append_log("="*50, service_name=service.name, service=service)
                
                # 优化弹出提示框，添加更友好的错误信息
                QMessageBox.critical(
                    self, 
                    "启动失败", 
                    f"服务 {service.name} 启动失败\n\n" +
                    f"详细信息请查看日志\n\n" +
                    "可能的原因：\n" +
                    "1. dufs.exe 文件不存在或路径错误\n" +
                    "2. 服务路径不存在或权限不足\n" +
                    "3. 端口被其他进程占用\n\n" +
                    "解决建议：\n" +
                    "1. 检查 dufs.exe 是否存在于程序目录\n" +
                    "2. 确保服务路径存在且有读写权限\n" +
                    "3. 尝试手动更换服务端口"
                )
                return
            
            # 启动服务启动检查定时器
            self._start_service_check_timer(service, index)
            self.append_log(f"✓ 服务 {service.name} 启动命令已执行，正在检查服务状态...", service_name=service.name, service=service)
            self.append_log("="*50, service_name=service.name, service=service)
            
        except (OSError, ValueError, subprocess.SubprocessError, IndexError, KeyError) as e:
            # 记录错误信息
            service = self.manager.services[index] if index is not None and 0 <= index < len(self.manager.services) else None
            service_name = service.name if service else "未知服务"
            self.append_log("="*50, service_name=service_name)
            self.append_log(f"✗ 启动服务 {service_name} 失败: {str(e)}", error=True, service_name=service_name)
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
            self.append_log("="*50, service_name=service_name)
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
        try:
            original_port = int(service.port.strip())
            
            # 端口范围验证
            if original_port < 1 or original_port > 65535:
                # 确保在主线程中显示错误信息
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: QMessageBox.critical(
                    self,
                    "错误",
                    f"端口 {original_port} 无效。\n端口必须在1-65535之间。"
                ))
                return None
        except ValueError:
            # 处理非数字端口的情况
            # 确保在主线程中显示错误信息
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self,
                "错误",
                f"端口 '{service.port}' 无效。\n请输入有效的数字端口。"
            ))
            return None
        
        available_port = None
        
        try:
            # 使用ServiceManager的原子化端口分配机制
            available_port = self.manager.find_available_port(original_port)
            
            # 如果找到了可用端口，更新服务端口
            if available_port:
                # 如果端口有变化，更新服务端口
                if available_port != original_port:
                    service.port = str(available_port)
                    # 更新服务列表显示
                    # 确保在主线程中执行
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self.status_updated.emit())
                    # 提示用户端口已自动更换
                    # 确保在主线程中显示提示信息
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "提示", f"端口 {original_port} 被占用，已自动更换为 {available_port}"))
                return available_port
        except ValueError as e:
            # 尝试了多个端口都不可用，提示用户
            # 确保在主线程中显示错误信息
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                self,
                "错误",
                f"端口 {original_port} 不可用，尝试了多个端口都不可用。\n" +
                f"原因：{str(e)}\n"
                "请手动更换端口。"
            ))
            return None
        
        # 尝试了多个端口都不可用，提示用户
        # 确保在主线程中显示错误信息
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: QMessageBox.critical(
            self,
            "错误",
            f"端口 {original_port} 不可用，尝试了多个端口都不可用。\n" +
            "请手动更换端口。"
        ))
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
        
        # 移除Windows特有的危险字符，防止命令注入
        dangerous_chars = ['&', '|', '<', '>', '^', '%']
        for char in dangerous_chars:
            arg = arg.replace(char, '')
        
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
        
        # 检测路径遍历攻击的变体
        # 检查基本的..路径遍历
        if ".." in path:
            raise ValueError("路径包含不安全的路径遍历字符")
        
        # 检查URL编码的路径遍历
        if "%2e%2e" in path.lower():
            raise ValueError("路径包含不安全的URL编码路径遍历字符")
        
        # 检查双重编码的路径遍历
        if "%252e%252e" in path.lower():
            raise ValueError("路径包含不安全的双重编码路径遍历字符")
        
        # 规范化路径，确保是绝对路径
        normalized_path = os.path.normpath(os.path.abspath(path))
        
        # 限制路径深度，防止路径遍历攻击
        path_depth = normalized_path.count(os.sep)
        if path_depth > AppConstants.MAX_PATH_DEPTH:
            raise ValueError(f"路径层级过深，最多允许{AppConstants.MAX_PATH_DEPTH}级目录")
        
        # 防止使用系统关键目录作为服务路径
        # Windows系统关键目录
        forbidden_paths = [
            os.environ.get("SystemRoot", "C:\\Windows"),
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            os.environ.get("APPDATA", "C:\\Users\\" + os.environ.get("USERNAME", "") + "\\AppData\\Roaming"),
            os.environ.get("LOCALAPPDATA", "C:\\Users\\" + os.environ.get("USERNAME", "") + "\\AppData\\Local")
        ]
        
        # 检查路径是否在系统关键目录内
        for forbidden in forbidden_paths:
            if forbidden:
                forbidden_norm = os.path.normpath(forbidden)
                if normalized_path == forbidden_norm or normalized_path.startswith(forbidden_norm + os.sep):
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
        # 1. ngrok服务已在stop_service中停止，此处不再重复处理
        
        with service.lock:
            # 2. 设置日志线程终止标志
            service.log_thread_terminate = True
            
            # 3. 关闭进程IO流，防止资源泄漏
            if service.process:
                try:
                    if service.process.stdout:
                        service.process.stdout.close()
                    if service.process.stderr:
                        service.process.stderr.close()
                except (OSError, ValueError) as e:
                    self.append_log(f"关闭进程IO流失败: {str(e)}", error=True, service_name=service.name)
            
            # 4. 清理日志界面资源
            if service.log_widget:
                # 移除日志控件（deleteLater()是异步安全的，不需要try-except）
                service.log_widget.deleteLater()
                service.log_widget = None
            
            # 5. 清空日志缓冲区
            service.log_buffer.clear()
            
            # 6. 重置服务状态为已停止
            # 直接修改状态，避免在锁内调用可能导致线程安全问题的方法
            service.status = ServiceStatus.STOPPED
            
            # 7. 重置服务状态和访问地址
            service.local_addr = ""
            
            # 发送状态更新信号
            service.status_updated.emit()
    
    def _add_basic_params(self, command, service, available_port):
        """添加基本参数：端口、绑定地址等"""
        # 验证端口值，确保是有效的数字
        if not isinstance(available_port, int) or available_port < 1 or available_port > 65535:
            raise ValueError(f"无效的端口值: {available_port}")
        
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
        success = True
        error_msg = ""
        
        try:
            # 检查命令是否有效
            if not command or not isinstance(command, list):
                error_msg = "启动服务失败: 无效的命令"
                success = False
            
            # 检查服务是否已经在运行
            elif service.status == ServiceStatus.RUNNING:
                # 直接在主线程中执行日志操作
                self.append_log(f"服务 {service.name} 已经在运行中，无需重复启动", service_name=service.name, service=service)
                success = False
            
            # 记录完整的命令信息（使用repr处理带空格的路径）
            command_str = " ".join([repr(arg) if ' ' in arg else arg for arg in command])
            # 直接在主线程中执行日志操作
            self.append_log(f"构建的命令: {command_str}", service_name=service.name)
            
            # 检查 dufs.exe 是否存在
            dufs_path = command[0]
            # 直接在主线程中执行日志操作
            self.append_log(f"检查 dufs.exe 路径: {dufs_path}", service_name=service.name)
            if not os.path.exists(dufs_path):
                error_msg = f"启动服务失败: dufs.exe 不存在 - 路径: {dufs_path}"
                success = False
            
            # 验证服务路径安全性
            try:
                validated_path = self._validate_service_path(service.serve_path)
                # 更新服务路径为验证通过后的规范化路径
                service.serve_path = validated_path
            except ValueError as e:
                error_msg = f"启动服务失败: {str(e)}"
                success = False
            
            # 基本路径检查（_validate_service_path已经包含了这些检查，但为了安全，保留这些检查）
            if success and not os.path.exists(service.serve_path):
                error_msg = f"启动服务失败: 服务路径不存在 - 路径: {service.serve_path}"
                success = False
            
            # 检查服务路径是否为目录
            if success and not os.path.isdir(service.serve_path):
                error_msg = f"启动服务失败: 服务路径必须是目录 - 路径: {service.serve_path}"
                success = False
            
            # 1. 首先检查读取权限（基本权限）
            if success and not os.access(service.serve_path, os.R_OK):
                error_msg = f"启动服务失败: 服务路径不可访问（缺少读取权限） - 路径: {service.serve_path}"
                success = False
            
            # 2. 如果允许上传，检查写入权限
            if success and (service.allow_all or service.allow_upload) and not os.access(service.serve_path, os.W_OK):
                error_msg = f"启动服务失败: 服务路径不可访问（缺少写入权限） - 路径: {service.serve_path}"
                success = False
            
            # 3. 如果允许删除，检查写入和执行权限
            if success and (service.allow_all or service.allow_delete) and not os.access(service.serve_path, os.W_OK | os.X_OK):
                error_msg = f"启动服务失败: 服务路径不可访问（缺少写入和执行权限） - 路径: {service.serve_path}"
                success = False
            
            # 记录服务启动信息
            # 直接在主线程中执行日志操作
            self.append_log("启动 DUFS...", service_name=service.name)
            
            # 直接使用当前工作目录或服务路径作为工作目录
            cwd = service.serve_path
            
            # 启动进程，捕获输出以支持实时日志
            creation_flags = 0
            if os.name == 'nt':  # Windows系统
                creation_flags = subprocess.CREATE_NO_WINDOW  # 隐藏命令窗口
            
            # 启动服务进程
            # 直接在主线程中执行日志操作
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
                
                # 直接在主线程中执行日志操作
                self.append_log(f"进程已启动，PID: {service.process.pid}", service_name=service.name)
            except (OSError, ValueError) as e:
                error_msg = f"启动进程失败: {str(e)}"
                success = False
            
            # 处理错误信息
            if not success:
                if error_msg:
                    # 直接在主线程中执行日志操作
                    self.append_log(error_msg, error=True, service_name=service.name)
                    if "启动服务失败" in error_msg or "启动进程失败" in error_msg:
                        # 直接在主线程中显示错误信息
                        self._show_error_message(error_msg)
            else:
                # 为服务创建专属日志Tab（提前创建，确保日志不丢失）
                # 直接在主线程中创建日志控件
                self.create_service_log_tab(service)
                
                # 启动日志读取线程（延迟150ms，避免Windows pipe初始阻塞）
                # 直接在主线程中执行日志操作
                self.append_log("启动日志读取线程", service_name=service.name)
                
                # 延迟150ms后执行，直接在后台线程中调用stream_log
                def delayed_stream_log():
                    import time
                    time.sleep(0.15)  # 150ms
                    self.stream_log(service.process, service)
                import threading
                threading.Thread(target=delayed_stream_log, daemon=True).start()
        except Exception as e:
            # 捕获所有异常，避免程序崩溃
            error_msg = f"启动服务时发生未知错误: {str(e)}"
            self.append_log(error_msg, error=True, service_name=service.name)
            self._show_error_message(error_msg)
            success = False
        
        return success
    
    def _show_error_message(self, error_msg):
        """在主线程中显示错误信息（非阻塞）"""
        from PyQt5.QtWidgets import QMessageBox
        # 创建非模态对话框，避免阻塞主线程
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("错误")
        msg_box.setText(error_msg)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setStandardButtons(QMessageBox.Ok)
        # 使用非模态方式显示
        msg_box.setModal(False)
        msg_box.show()
    
    def _start_service_check_timer(self, service, index):
        """启动服务启动检查定时器"""
        # 创建一个单次定时器，延迟检查服务状态
        # 不设置父对象，避免线程安全问题
        timer = QTimer()
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
                self.append_log("服务进程已被释放，跳过状态检查", service_name=service.name)
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
                except (IOError, UnicodeDecodeError) as e:
                    self.append_log(f"读取进程输出失败: {str(e)}", error=True, service_name=service.name)
                
                # 设置日志线程终止标志
                service.log_thread_terminate = True
                
                # 释放进程资源
                service.process = None
                # 使用统一的状态更新方法，确保信号发射和UI更新
                service.update_status(status=ServiceStatus.STOPPED)
                service.local_addr = ""
                
                # 释放已分配的端口
                try:
                    port = int(service.port)
                    self.manager.release_allocated_port(port)
                except (ValueError, AttributeError):
                    pass
            
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
        self.append_log("简化服务启动流程，直接更新服务状态", service_name=service.name)
        # 确保在主线程中执行UI更新
        from PyQt5.QtCore import QCoreApplication, QEvent
        class UiUpdateEvent(QEvent):
            def __init__(self, callback):
                super().__init__(QEvent.User)
                self.callback = callback
        
        def post_ui_update(callback):
            app = QCoreApplication.instance()
            if app:
                event = UiUpdateEvent(callback)
                app.postEvent(self, event)
        
        # 通过索引获取服务对象，避免闭包陷阱
        post_ui_update(lambda: self._update_service_after_start(self.manager.services[index], index))
        return True
    
    def _update_service_after_start(self, service, index):
        """服务启动后更新状态和UI"""
        # 使用统一的状态更新方法
        service.update_status(status=ServiceStatus.RUNNING)
        
        # 启动监控线程
        threading.Thread(target=self.monitor_service, args=(service, index), daemon=True).start()
        
        # 服务启动成功，释放已分配的端口（端口已经被实际占用）
        try:
            port = int(service.port)
            self.manager.release_allocated_port(port)
        except (ValueError, AttributeError):
            pass
        
        # 所有UI操作都通过信号槽机制在主线程中执行
        
        # 记录日志
        # 确保在主线程中执行UI更新
        from PyQt5.QtCore import QCoreApplication, QEvent
        class UiUpdateEvent(QEvent):
            def __init__(self, callback):
                super().__init__(QEvent.User)
                self.callback = callback
        
        def post_ui_update(callback):
            app = QCoreApplication.instance()
            if app:
                event = UiUpdateEvent(callback)
                app.postEvent(self, event)
        
        # 刷新访问地址，确保local_addr被正确设置
        post_ui_update(lambda: self.refresh_address(index))
        
        # 记录日志
        post_ui_update(lambda: self.append_log("进程正常运行，更新服务状态", service_name=self.manager.services[index].name, service=self.manager.services[index]))
        post_ui_update(lambda: self.append_log("启动监控线程", service_name=self.manager.services[index].name, service=self.manager.services[index]))
        post_ui_update(lambda: self.append_log("更新服务列表", service_name=self.manager.services[index].name, service=self.manager.services[index]))
        post_ui_update(lambda: self.append_log("服务启动成功", service_name=self.manager.services[index].name, service=self.manager.services[index]))
        
        # 强制更新服务列表UI
        post_ui_update(lambda: self.update_service_list())
        
        # 更新状态栏
        post_ui_update(lambda: self.status_bar.showMessage(f"已启动服务: {self.manager.services[index].name} | 访问地址: {self.manager.services[index].local_addr}"))
        
        # 刷新托盘菜单
        post_ui_update(self.refresh_tray_menu)
    
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
                    service.process = None
                    service.update_status(status=ServiceStatus.STOPPED)
            QMessageBox.information(self, "提示", "该服务已停止")
            return
        
        # 记录服务停止开始信息
        self.append_log("开始停止服务...", service_name=service.name, service=service)
        
        # 在后台线程中执行进程终止和资源清理，避免阻塞主线程
        def stop_service_in_background():
            # 停止ngrok服务（如果正在运行）
            if hasattr(service, 'stop_ngrok'):
                service.stop_ngrok(wait=False)  # 不等待，避免阻塞
            
            # 获取锁，确保线程安全
            with service.lock:
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
                except (OSError, subprocess.SubprocessError) as e:
                    self.append_log(f"终止进程失败: {str(e)}", error=True, service_name=service.name)
                finally:
                    # 释放进程对象
                    service.process = None
            
            # 调用统一的资源清理方法
            self.cleanup_service_resources(service)
            
            # 释放已分配的端口
            try:
                port = int(service.port)
                self.manager.release_allocated_port(port)
            except (ValueError, AttributeError):
                pass
            
            # 在主线程中更新UI和状态
            def update_ui():
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
                
                # 确保公网访问状态被正确重置
                service.public_url = ""
                service.public_access_status = "stopped"
                
                # 记录服务停止信息
                self.append_log("已停止服务", service_name=service.name, service=service)
                
                # 更新服务列表
                self.status_updated.emit()
                
                # 清空地址显示
                self.addr_edit.setText("")
                # 清空公网地址显示
                self.public_addr_edit.setText("")
                # 更新公网访问按钮状态
                self.public_access_btn.setText("启动公网访问")
                
                # 更新状态栏
                self.status_bar.showMessage(f"已停止服务: {service.name}")
                
                # 刷新托盘菜单
                self.refresh_tray_menu()
            
            # 使用post_ui_update确保在主线程中执行UI更新
            from PyQt5.QtCore import QCoreApplication, QEvent
            class UiUpdateEvent(QEvent):
                def __init__(self, callback):
                    super().__init__(QEvent.User)
                    self.callback = callback
            
            def post_ui_update(callback):
                app = QCoreApplication.instance()
                if app:
                    event = UiUpdateEvent(callback)
                    app.postEvent(self, event)
            
            post_ui_update(update_ui)
        
        # 启动后台线程执行停止服务操作
        threading.Thread(target=stop_service_in_background, daemon=True).start()
    
    def show_help(self):
        """显示帮助信息（优化版）"""
        help_text = '''
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #333; }
                h1 { color: #0066cc; margin-top: 0; font-size: 14pt; }
                h2 { color: #004488; font-size: 12pt; margin-top: 15px; }
                h3 { color: #004488; font-size: 11pt; margin-top: 12px; }
                ul { margin-left: 20px; }
                ol { margin-left: 20px; }
                li { margin-bottom: 8px; }
                p { margin-bottom: 10px; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
        <h1>欢迎使用 Dufs 服务管理工具！</h1>

        <h2>1. 局域网文件共享服务</h2>
        <ol>
            <li>步骤 1：点击界面中的“添加服务”按钮。</li>
            <li>步骤 2：在弹出的对话框中填写服务信息：</li>
            <ul>
                <li>服务名称：输入一个独一无二的服务名称。</li>
                <li>服务路径：挑选一个文件夹作为服务的根路径，所有通过此服务提供的文件都将存于该路径下。</li>
                <li>端口号：为服务分配一个端口。务必确保所选端口未被其他服务占用。（随意填写也无妨，程序会找到一个可用端口并进行修改）</li>
            </ul>
            <li>步骤 3：点击“确定”按钮，系统将检查端口是否可用并启动服务。</li>
        </ol>

        <h2>2. 外网文件共享</h2>
        <p>每个局域网共享服务均支持通过 ngrok 进行内网穿透，从而使服务能够从外网直接访问。</p>
        <ol>
            <li>步骤 1：在服务配置界面，填写你从 ngrok 获取的 authtoken。</li>
            <li>步骤 2：点击“启动外网访问”按钮。系统会自动启动一个独立的 ngrok 隧道，并为该服务分配一个公网地址。</li>
        </ol>

        <h3>注意：</h3>
        <ol>
            <li>ngrok 免费账号，每个账号仅能建立三条隧道，且只能有一条隧道在线。</li>
            <li>每个服务需要使用独立的 ngrok 配置，确保使用不同的 authtoken 以避免冲突。（双击详情可查看该服务保存的 authtoken 信息）</li>
            <li>理论上，只要 ngrok 账号足够多，就可以开启无数条隧道，支持无数服务共享。</li>
            <li>ngrok 免费账号，最高可提供 1GB 带宽，最多可承受 20k HTTP/S 请求。</li>
        </ol>

        <p style="margin-top: 20px; text-align: center;">
            <a href="https://ngrok.com">ngrok 官网</a> | 
            <a href="https://github.com/tysonye/dufs-gui">GitHub 仓库</a>
        </p>
    </body>
    </html>
        '''

        QMessageBox.information(
            self,
            "Dufs 帮助",
            help_text,
            QMessageBox.Ok
        )
    def monitor_service(self, service, _index):
        """监控服务状态"""
        port_unavailable_count = 0
        max_port_unavailable_count = 3  # 连续3次端口不可访问则认为服务异常
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
                
                # 使用QApplication.postEvent确保所有UI操作在主线程中执行
                from PyQt5.QtCore import QCoreApplication, QEvent
                class UiUpdateEvent(QEvent):
                    def __init__(self, callback):
                        super().__init__(QEvent.User)
                        self.callback = callback
                
                def post_ui_update(callback):
                    app = QCoreApplication.instance()
                    if app:
                        event = UiUpdateEvent(callback)
                        app.postEvent(self, event)
                
                post_ui_update(lambda: self.status_updated.emit())
                post_ui_update(lambda: self.status_bar.showMessage(f"服务已停止: {service.name}"))
                post_ui_update(lambda: self.append_log("服务异常退出", error=True, service_name=service.name))
                post_ui_update(self.refresh_tray_menu)
                break
            
            # 双校验：检查端口是否可访问
            try:
                port = int(service.port)
                if not self.is_port_open(port):
                    port_unavailable_count += 1
                    # 端口不可访问，记录日志
                    self.append_log(f"服务进程存在但端口 {port} 暂时不可访问", service_name=service.name)
                    
                    # 连续多次端口不可访问，认为服务异常
                    if port_unavailable_count >= max_port_unavailable_count:
                        self.append_log(f"服务端口 {port} 连续 {max_port_unavailable_count} 次不可访问，标记为异常状态", 
                                    error=True, service_name=service.name)
                        
                        with service.lock:
                            service.status = ServiceStatus.ERROR
                            service.local_addr = ""
                        
                        # 使用QApplication.postEvent确保所有UI操作在主线程中执行
                        from PyQt5.QtCore import QCoreApplication, QEvent
                        class UiUpdateEvent(QEvent):
                            def __init__(self, callback):
                                super().__init__(QEvent.User)
                                self.callback = callback
                        
                        def post_ui_update(callback):
                            app = QCoreApplication.instance()
                            if app:
                                event = UiUpdateEvent(callback)
                                app.postEvent(self, event)
                        
                        post_ui_update(lambda: self.status_updated.emit())
                        post_ui_update(lambda: self.status_bar.showMessage(f"服务 {service.name} 异常"))
                        post_ui_update(self.refresh_tray_menu)
                        break
                else:
                    # 端口可访问，重置计数器
                    port_unavailable_count = 0
            except (ValueError, OSError) as e:
                self.append_log(f"监控端口状态异常: {str(e)}", error=True, service_name=service.name)
            
            # 控制循环频率，避免占用过多CPU资源
            time.sleep(2)  # 每2秒检查一次


def clean_residual_processes():
    """清理残留的dufs和ngrok进程"""
    import subprocess
    import platform
    
    # 只在Windows系统上执行进程清理
    if platform.system() == "Windows":
        # 要清理的进程名称列表
        processes_to_clean = [
            "dufs.exe",
            "ngrok.exe"
        ]
        
        for process_name in processes_to_clean:
            try:
                # 设置creationflags参数来隐藏命令窗口
                creation_flags = 0
                if os.name == 'nt':  # Windows系统
                    creation_flags = subprocess.CREATE_NO_WINDOW  # 隐藏命令窗口
                
                # 使用taskkill命令终止进程，/F表示强制终止，/IM表示按进程名终止
                subprocess.run(
                    ["taskkill", "/F", "/IM", process_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    creationflags=creation_flags  # 隐藏命令窗口
                )
            except Exception as e:
                # 忽略清理过程中的错误，确保程序能够继续启动
                pass

# 主入口代码
if __name__ == "__main__":
    # 添加调试输出，显示应用程序启动
    print("应用程序开始启动...")
    
    # 清理残留的dufs和ngrok进程
    print("清理残留的dufs和ngrok进程...")
    clean_residual_processes()
    print("清理残留进程完成")
    
    # 尝试导入QLoggingCategory用于日志过滤，如果不可用则跳过
    try:
        from PyQt5.QtCore import QLoggingCategory
        # 禁用Qt的字体枚举警告
        QLoggingCategory.setFilterRules("qt.qpa.fonts=false")
        print("QLoggingCategory导入成功")
    except (ImportError, AttributeError) as e:
        # QLoggingCategory不可用，跳过
        print(f"QLoggingCategory导入失败: {str(e)}")
    
    print("创建QApplication实例...")
    app = QApplication(sys.argv)
    print("QApplication实例创建成功")
    
    # 设置应用程序字体，使用安全的字体族
    print("设置应用程序字体...")
    font = QFont()
    font.setFamily("Microsoft YaHei")
    font.setPointSize(12)
    app.setFont(font)
    print("应用程序字体设置成功")
    
    # 设置窗口图标
    print("设置窗口图标...")
    icon_path = get_resource_path("icon.ico")
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        print(f"窗口图标设置成功: {icon_path}")
    else:
        print(f"窗口图标设置失败: {icon_path}")
    
    print("创建DufsMultiGUI实例...")
    try:
        window = DufsMultiGUI()
        print("DufsMultiGUI实例创建成功")
        print("显示主窗口...")
        window.show()
        print("主窗口显示成功")
        print("进入应用程序主循环...")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"应用程序启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
