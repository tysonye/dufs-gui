import sys
import os
import subprocess
import threading
import time
import socket
import psutil
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QFrame, QGroupBox, QGridLayout, QMenu, QAction,
    QMessageBox, QFileDialog, QDialog, QCheckBox, QSystemTrayIcon, QStyle, QToolTip, QStatusBar, QHeaderView, QPlainTextEdit,
    QTabWidget
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

# 窗口尺寸常量
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 600
DIALOG_WIDTH = 750
DIALOG_HEIGHT = 550

# 端口配置常量
DEFAULT_PORT = 5001
PORT_TRY_LIMIT = 100
PORT_TRY_LIMIT_BACKUP = 50
BACKUP_START_PORT = 8000
SERVICE_START_WAIT_SECONDS = 2
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
        self.running = False
        
        # 访问地址
        self.local_addr = ""
        
        # 添加线程锁，保护共享资源
        self.lock = threading.Lock()
        
        # 日志相关属性
        self.log_widget = None
        self.log_tab_index = None
        
        # 日志线程终止标志
        self.log_thread_terminate = False

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
        self.setGeometry(400, 200, DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setModal(True)
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        # 字体设置
        font = QFont("Microsoft YaHei", 12)
        self.setFont(font)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(*DIALOG_LAYOUT_MARGINS)
        main_layout.setSpacing(DIALOG_LAYOUT_SPACING)
        
        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QGridLayout()
        basic_layout.setContentsMargins(*BASIC_LAYOUT_MARGINS)
        basic_layout.setSpacing(BASIC_LAYOUT_SPACING)
        
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
            default_port = DEFAULT_PORT  # 从DEFAULT_PORT开始，避开常用的5000端口
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
        
        self.allow_all_check = QCheckBox("全选所有权限")
        self.allow_all_check.setStyleSheet("font-weight: 500;")
        self.allow_all_check.stateChanged.connect(self.on_select_all)
        perm_layout.addWidget(self.allow_all_check)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E0E0E0;")
        perm_layout.addWidget(line)
        
        # 权限水平布局
        perm_h_layout = QHBoxLayout()
        perm_h_layout.setSpacing(20)
        
        self.allow_upload_check = QCheckBox("允许上传文件")
        self.allow_upload_check.stateChanged.connect(self.on_perm_change)
        perm_h_layout.addWidget(self.allow_upload_check)
        
        self.allow_delete_check = QCheckBox("允许删除文件/文件夹")
        self.allow_delete_check.stateChanged.connect(self.on_perm_change)
        perm_h_layout.addWidget(self.allow_delete_check)
        
        self.allow_search_check = QCheckBox("允许搜索文件")
        self.allow_search_check.stateChanged.connect(self.on_perm_change)
        perm_h_layout.addWidget(self.allow_search_check)
        
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
            self.allow_all_check.setChecked(self.service.allow_all)
            self.allow_upload_check.setChecked(self.service.allow_upload)
            self.allow_delete_check.setChecked(self.service.allow_delete)
            self.allow_search_check.setChecked(self.service.allow_search)
            
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
    
    def on_select_all(self):
        """全选权限"""
        value = self.allow_all_check.isChecked()
        self.allow_upload_check.setChecked(value)
        self.allow_delete_check.setChecked(value)
        self.allow_search_check.setChecked(value)
    
    def on_perm_change(self):
        """权限变更"""
        if (self.allow_upload_check.isChecked() and 
            self.allow_delete_check.isChecked() and 
            self.allow_search_check.isChecked()):
            self.allow_all_check.setChecked(True)
        else:
            self.allow_all_check.setChecked(False)
    
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
        allow_all = self.allow_all_check.isChecked()
        service = DufsService(name=name, serve_path=serve_path, port=port, bind="")
        service.allow_all = allow_all
        service.allow_upload = self.allow_upload_check.isChecked()
        service.allow_delete = self.allow_delete_check.isChecked()
        service.allow_search = self.allow_search_check.isChecked()
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
        self.services = []
        self.init_ui()
        self.status_updated.connect(self.update_service_list)
        self.log_signal.connect(self._append_log_ui)
    
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
            # 根据错误级别设置不同的颜色
            if error:
                color = "#f44336"  # 红色
                level = "错误"
            else:
                color = "#2196f3"  # 蓝色
                level = "信息"
            
            # 使用HTML格式添加带颜色的日志，包含时间戳和级别
            service.log_widget.appendHtml(f"<span style='color:{color}'>{message}</span>")
        else:
            # 如果没有指定服务或服务没有日志控件，暂时不处理
            pass
    
    def init_ui(self):
        """初始化主窗口UI"""
        # 设置窗口属性
        self._setup_window_properties()
        
        # 创建中央组件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(*MAIN_LAYOUT_MARGINS)
        main_layout.setSpacing(MAIN_LAYOUT_SPACING)
        
        # 添加各UI组件
        self._add_title_bar(main_layout)
        self._add_button_group(main_layout)
        self._add_service_list(main_layout)
        self._add_access_address(main_layout)
        self._add_log_window(main_layout)
        
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
            for service in self.services:
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
            self.services.clear()
            
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
                
                # 添加到服务列表
                self.services.append(service)
            
            self.append_log(f"从配置文件加载了 {len(self.services)} 个服务", service_name="系统")
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

    def add_auto_start(self):
        """添加系统自启动项"""
        try:
            if os.name == 'nt':  # Windows
                import winreg
                # 获取当前可执行文件路径
                exe_path = sys.executable
                # 如果是单文件打包的程序，直接使用sys.executable
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                
                key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "DufsGUI", 0, winreg.REG_SZ, f'"{exe_path}"')
                self.append_log("已添加开机自启动", service_name="系统")
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
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        # 设置窗口图标
        icon_path = get_resource_path("icon.ico")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 居中显示
        screen_geo = QApplication.desktop().screenGeometry()
        self.setGeometry(
            (screen_geo.width() - MIN_WINDOW_WIDTH) // 2,
            (screen_geo.height() - MIN_WINDOW_HEIGHT) // 2,
            MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
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
        
        main_layout.addLayout(btn_layout)
    
    def _add_service_list(self, main_layout):
        """添加服务列表"""
        service_group = QGroupBox("已配置服务")
        service_layout = QVBoxLayout(service_group)
        service_layout.setContentsMargins(15, 15, 15, 15)
        
        self.service_tree = QTreeWidget()
        # 移除复选框列，列数改为6
        self.service_tree.setColumnCount(6)
        self.service_tree.setHeaderLabels(["服务名称", "端口", "状态", "认证", "权限", "服务路径"])
        self.service_tree.setAlternatingRowColors(True)
        # 改为单选模式
        self.service_tree.setSelectionMode(QTreeWidget.SingleSelection)
        # 设置为整行选择模式
        self.service_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        # 移除缩进，避免服务名称前面空白
        self.service_tree.setIndentation(0)
        # 调整各列宽度，确保初始界面不需要水平滚动条
        self.service_tree.setColumnWidth(0, 140)  # 服务名称
        self.service_tree.setColumnWidth(1, 70)   # 端口
        self.service_tree.setColumnWidth(2, 90)   # 状态
        self.service_tree.setColumnWidth(3, 140)  # 认证
        self.service_tree.setColumnWidth(4, 110)  # 权限
        self.service_tree.setColumnWidth(5, 250)  # 服务路径
        
        # 设置表头标签居中显示
        header = self.service_tree.header()
        for i in range(self.service_tree.columnCount()):
            header.setDefaultAlignment(Qt.AlignCenter)
        
        # 设置表头拉伸策略，最后一列自动拉伸
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        # 其他列固定宽度，不允许用户调整
        for i in range(5):
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
        copy_btn.clicked.connect(self.copy_address)
        addr_layout.addWidget(copy_btn)
        
        browse_btn = QPushButton("浏览器访问")
        browse_btn.clicked.connect(self.browser_access)
        addr_layout.addWidget(browse_btn)
        
        addr_group.setLayout(addr_layout)
        main_layout.addWidget(addr_group)
    
    def _add_log_window(self, main_layout):
        """添加日志窗口"""
        log_group = QGroupBox("服务日志")
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建日志Tab容器
        self.log_tabs = QTabWidget()
        self.log_tabs.setTabsClosable(True)
        self.log_tabs.tabCloseRequested.connect(self.close_log_tab)
        log_layout.addWidget(self.log_tabs)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
    
    def create_service_log_tab(self, service):
        """为服务创建专属日志Tab"""
        log_view = QPlainTextEdit()
        log_view.setReadOnly(True)
        log_view.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; background-color: #0f111a; color: #c0c0c0;")
        log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        # 设置日志最大块数，防止内存无限增长
        log_view.setMaximumBlockCount(MAX_LOG_LINES)
        
        # 创建Tab标题
        title = f"服务 {service.name} ({service.port})"
        index = self.log_tabs.addTab(log_view, title)
        
        # 绑定服务与日志控件
        service.log_widget = log_view
        service.log_tab_index = index
    
    def close_log_tab(self, index):
        """关闭日志Tab"""
        # 获取要关闭的日志Tab对应的服务
        widget = self.log_tabs.widget(index)
        for service in self.services:
            if service.log_widget == widget:
                # 清空服务的日志相关属性
                service.log_widget = None
                service.log_tab_index = None
                break
        # 移除Tab并释放资源
        self.log_tabs.removeTab(index)
    
    def view_service_log(self, index):
        """查看服务日志，如日志Tab不存在则重新创建"""
        # 检查索引是否有效
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return
        
        service = self.services[index]
        
        # 检查服务是否正在运行
        if service.status != "运行中":
            QMessageBox.information(self, "提示", "该服务未运行，无法查看日志")
            return
        
        # 检查是否已存在日志Tab
        if service.log_widget:
            # 日志Tab已存在，切换到该Tab
            tab_index = self.log_tabs.indexOf(service.log_widget)
            if tab_index != -1:
                self.log_tabs.setCurrentIndex(tab_index)
        else:
            # 日志Tab不存在，重新创建
            self.create_service_log_tab(service)
            # 切换到新创建的Tab
            self.log_tabs.setCurrentIndex(self.log_tabs.count() - 1)
    
    def _setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪 - 未运行任何服务 | 点击「添加服务」创建新服务")
        self.setStatusBar(self.status_bar)
    
    def _bind_events(self):
        """绑定事件"""
        # 绑定服务列表选择事件
        self.service_tree.itemSelectionChanged.connect(self.on_service_selected)
        
        # 绑定双击事件
        self.service_tree.itemDoubleClicked.connect(self.edit_service)
        
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
        
        # 添加分隔线
        menu.addSeparator()
        
        # 根据服务状态启用/禁用菜单项
        service = self.services[index]
        start_action.setEnabled(service.status == "未运行")
        stop_action.setEnabled(service.status == "运行中")
        view_log_action.setEnabled(service.status == "运行中")
        
        # 添加菜单项到菜单
        menu.addAction(start_action)
        menu.addAction(stop_action)
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
        self.update_tray_icon()
        self.update_tray_tooltip()
        
        # 创建托盘菜单
        self.tray_menu = QMenu(self)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # 初始刷新托盘菜单
        self.refresh_tray_menu()
        
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
        self.refresh_tray_menu()
    
    def update_tray_icon(self):
        """根据服务状态更新托盘图标"""
        running_count = sum(1 for service in self.services if service.running)
        
        if running_count == 0:
            # 没有服务运行，使用默认图标
            self.tray_icon.setIcon(self.default_icon)
        elif running_count == 1:
            # 一个服务运行，使用默认图标
            self.tray_icon.setIcon(self.default_icon)
        else:
            # 多个服务运行，使用默认图标
            self.tray_icon.setIcon(self.default_icon)
    
    def update_tray_tooltip(self):
        """更新托盘提示，显示详细服务状态"""
        tooltip = "Dufs多服务管理\n\n正在运行的服务:\n"
        running_services = [s for s in self.services if s.running]
        
        if running_services:
            for service in running_services:
                tooltip += f"• {service.name}: {service.local_addr}\n"
        else:
            tooltip += "• 无正在运行的服务"
        
        tooltip += f"\n总共: {len(self.services)} 个服务"
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
        for i in range(len(self.services)):
            service = self.services[i]
            if service.status != "运行中":
                self.start_service_by_index(i)
    
    def stop_all_services(self):
        """停止所有服务"""
        for i in range(len(self.services)):
            service = self.services[i]
            if service.status == "运行中":
                self.stop_service_by_index(i)
    
    def refresh_tray_menu(self):
        """刷新托盘菜单，根据当前services列表重建"""
        # 清空现有菜单
        self.tray_menu.clear()
        
        # 1. 服务状态摘要
        running_count = sum(1 for service in self.services if service.status == "运行中")
        status_action = QAction(f"🖥️ 正在运行: {running_count}/{len(self.services)} 个服务", self)
        status_action.setEnabled(False)
        self.tray_menu.addAction(status_action)
        self.tray_menu.addSeparator()
        
        # 2. 快速访问正在运行的服务
        running_services = [service for service in self.services if service.status == "运行中"]
        if running_services:
            quick_access_menu = self.tray_menu.addMenu("🚀 快速访问")
            for service in running_services[:5]:  # 限制显示数量
                # 显示服务名称和访问地址
                access_action = quick_access_menu.addAction(f"🌐 {service.name}")
                access_action.triggered.connect(
                    lambda checked=False, url=service.local_addr: self.open_url(url)
                )
            self.tray_menu.addSeparator()
        
        # 3. 服务控制
        if self.services:
            # 遍历所有服务，而不仅仅是运行中的服务
            for i, service in enumerate(self.services):
                # 格式化服务标题
                title = f"{service.name} ({service.port})"
                
                # 根据服务状态显示不同的图标
                if service.status == "运行中":
                    status_icon = "🟢"
                elif service.status == "启动中":
                    status_icon = "🟡"
                else:
                    status_icon = "🔴"
                
                # 根据服务状态添加启动/停止菜单项
                # 直接将服务名称和状态合并到动作中
                if service.status == "运行中":
                    # 服务正在运行，显示停止选项
                    stop_action = QAction(f"⏹ {status_icon} {title} - 停止服务", self)
                    stop_action.triggered.connect(
                        lambda checked=False, idx=i: self.stop_service(idx)
                    )
                    self.tray_menu.addAction(stop_action)
                else:
                    # 服务未运行，显示启动选项
                    start_action = QAction(f"▶ {status_icon} {title} - 启动服务", self)
                    start_action.triggered.connect(
                        lambda checked=False, idx=i: self.start_service(idx)
                    )
                    self.tray_menu.addAction(start_action)
                
                # 每个服务之间添加分隔线
                self.tray_menu.addSeparator()
        else:
            # 没有服务
            no_service_action = QAction("暂无配置的服务", self)
            no_service_action.setEnabled(False)
            self.tray_menu.addAction(no_service_action)
            self.tray_menu.addSeparator()
        
        # 显示主界面
        show_action = QAction("🖥 显示主界面", self)
        show_action.triggered.connect(self.show_window)
        self.tray_menu.addAction(show_action)
        
        # 打开日志窗口
        log_action = QAction("📄 打开日志窗口", self)
        log_action.triggered.connect(self.show_window)
        self.tray_menu.addAction(log_action)
        
        # 添加分隔线
        self.tray_menu.addSeparator()
        
        # 退出程序
        exit_action = QAction("❌ 退出程序", self)
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
        # 停止所有正在运行的服务
        for i in range(len(self.services)):
            service = self.services[i]
            if service.status == "运行中":
                self.stop_service(i)
        
        # 退出应用
        QApplication.quit()
    
    def is_port_available(self, port, exclude_service=None):
        """检查端口是否可用
        
        Args:
            port (int): 要检查的端口号
            exclude_service (DufsService, optional): 要排除的服务对象. Defaults to None.
        
        Returns:
            bool: 端口是否可用
        """
        # 检查是否被当前服务列表中的其他服务占用
        for service in self.services:
            if service == exclude_service:
                continue
            try:
                if int(service.port) == port and service.status == "运行中":
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
                # 获取IP地址
                ip = addr_info[4][0]
                # 排除IPv6地址和回环地址
                if ip != '127.0.0.1' and ':' not in ip:
                    return ip
        except Exception:
            pass
        
        # 方法3：尝试获取所有网络接口信息（适用于复杂网络环境）
        try:
            import psutil
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    # 只处理IPv4地址，排除回环地址
                    if addr.family == socket.AF_INET and addr.address != '127.0.0.1':
                        return addr.address
        except Exception:
            pass
        
        # 如果所有方法都失败，返回localhost作为备选
        return 'localhost'
    
    def stream_log(self, process, service):
        """实时读取进程日志并添加到日志窗口
        
        Args:
            process (subprocess.Popen): 要监控的进程对象
            service (DufsService): 对应的服务对象
        """
        def read_logs():
            """读取日志的内部函数"""
            # 使用简单的阻塞读取方式，这在Windows上更可靠
            import time
            
            # 读取stdout的函数
            def read_stdout():
                while True:
                    # 检查是否需要终止日志线程
                    if service.log_thread_terminate:
                        break
                    if process.poll() is not None:
                        break
                    try:
                        # 读取一行stdout字节流
                        line_bytes = process.stdout.readline()
                        if line_bytes:
                            # 使用UTF-8解码为字符串并去除换行符
                            line = line_bytes.decode('utf-8').strip()
                            if line:
                                self.append_log(line, service_name=service.name, service=service)
                    except Exception as e:
                        # 读取出错，可能是进程已经退出
                        break
            
            # 读取stderr的函数
            def read_stderr():
                while True:
                    # 检查是否需要终止日志线程
                    if service.log_thread_terminate:
                        break
                    if process.poll() is not None:
                        break
                    try:
                        # 读取一行stderr字节流
                        line_bytes = process.stderr.readline()
                        if line_bytes:
                            # 使用UTF-8解码为字符串并去除换行符
                            line = line_bytes.decode('utf-8').strip()
                            if line:
                                self.append_log(line, error=True, service_name=service.name, service=service)
                    except Exception as e:
                        # 读取出错，可能是进程已经退出
                        break
            
            # 启动两个线程分别读取stdout和stderr
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            
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
    
    def on_service_selected(self):
        """处理服务列表选择事件"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            self.addr_edit.setText("")
            return
        
        # 获取选中的服务项
        selected_item = selected_items[0]
        
        # 获取服务索引
        index = selected_item.data(0, Qt.UserRole)
        if index is None:
            self.addr_edit.setText("")
            return
        
        # 获取服务对象
        service = self.services[index]
        
        # 更新访问地址
        self.refresh_address(index)
    
    def refresh_address(self, index):
        """刷新访问地址"""
        service = self.services[index]
        if service.status == "运行中":
            # 使用局域网IP地址而不是localhost
            bind = service.bind if service.bind else self.get_local_ip()
            service.local_addr = f"http://{bind}:{service.port}"
            self.addr_edit.setText(service.local_addr)
        else:
            self.addr_edit.setText("")
    
    def update_service_list(self):
        """更新服务列表"""
        # 记录当前选中的服务名称（用于刷新后恢复选择）
        selected_names = [item.text(0) for item in self.service_tree.selectedItems()]
        
        # 清空现有列表
        self.service_tree.clear()
        
        # 添加服务到列表
        for i, service in enumerate(self.services):
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
            if service.allow_search:
                perms_info.append("搜索")
            perms_text = ", ".join(perms_info) if perms_info else ""
            
            # 创建树项（移除复选框列）
            status = service.status
            
            item = QTreeWidgetItem([
                service.name,
                service.port,
                status,
                auth_info,
                perms_text,
                service.serve_path
            ])
            
            # 根据服务状态设置状态列的颜色
            if status == "运行中":
                item.setForeground(2, QColor("#4caf50"))  # 绿色
            elif status == "未运行":
                item.setForeground(2, QColor("#f44336"))  # 红色
            elif status == "启动中":
                item.setForeground(2, QColor("#ff9800"))  # 橙色
            
            # 设置所有列的内容居中显示
            for col in range(self.service_tree.columnCount()):
                item.setTextAlignment(col, Qt.AlignCenter)
            
            # 设置状态列的文本颜色（状态列现在是索引2）
            if service.status == '运行中':
                item.setForeground(2, QColor('green'))
            else:
                item.setForeground(2, QColor('red'))
                
            # 先将树项添加到树控件中
            self.service_tree.addTopLevelItem(item)
            
            # 然后将服务在self.services列表中的实际索引存储到树项中
            item.setData(0, Qt.UserRole, i)
            
            # 恢复选中状态（刷新列表后保留之前的选择）
            is_selected = service.name in selected_names
            item.setSelected(is_selected)
        
        # 更新状态栏服务计数
        running_count = len([s for s in self.services if s.status == "运行中"])
        self.status_bar.showMessage(f"就绪 - 已配置{len(self.services)}个服务 | 运行中{running_count}个")
    
    def add_service(self):
        """添加新服务"""
        dialog = DufsServiceDialog(self, existing_services=self.services)
        if dialog.exec_():
            self.services.append(dialog.service)
            self.status_updated.emit()
            # 刷新托盘菜单，显示新增的服务
            self.refresh_tray_menu()
            self.status_bar.showMessage(f"已添加服务: {dialog.service.name}")
            self.save_config()
    
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
            # 从树项中获取服务在self.services列表中的实际索引
            index = selected_item.data(0, Qt.UserRole)
        else:
            # 从树项中获取服务在self.services列表中的实际索引
            index = item.data(0, Qt.UserRole)
        
        service = self.services[index]
        dialog = DufsServiceDialog(self, service=service, edit_index=index, existing_services=self.services)
        if dialog.exec_():
            # 保存服务当前状态（是否运行中）
            was_running = service.status == "运行中"
            
            # 如果服务之前是运行中的，先停止旧服务
            if was_running:
                # 停止旧服务
                self.stop_service(index)
            
            # 更新服务
            self.services[index] = dialog.service
            self.status_updated.emit()
            
            # 刷新托盘菜单，更新服务信息
            self.refresh_tray_menu()
            
            # 如果服务之前是运行中的，启动新服务
            if was_running:
                QMessageBox.information(self, "提示", "服务配置已更改，服务将自动重启以应用新配置。")
                self.start_service(index)
            self.save_config()
    
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
        # 从树项中获取服务在self.services列表中的实际索引
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
        # 从树项中获取服务在self.services列表中的实际索引
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
        # 从树项中获取服务在self.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)
        
        # 确保索引有效
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return
        
        service = self.services[index]
        
        # 如果服务正在运行，先停止
        if service.status == "运行中":
            self.stop_service(index)
        
        # 显示确认框
        if QMessageBox.question(self, "提示", f"确定要删除服务 '{service.name}' 吗？") != QMessageBox.Yes:
            return
        
        # 删除服务
        del self.services[index]
        
        # 更新服务列表
        self.status_updated.emit()
        
        # 刷新托盘菜单，更新服务列表
        self.refresh_tray_menu()
        
        # 更新状态栏
        self.status_bar.showMessage(f"已删除服务: {service.name}")
        
        # 保存配置
        self.save_config()
    
    def start_service(self, index=None):
        """启动选中的服务"""
        try:
            # 获取并验证服务索引
            index = self._get_service_index(index)
            if index is None:
                return
            
            # 获取服务对象
            service = self.services[index]
            
            # 检查服务是否已经在运行，如果是则直接返回
            if service.status == "运行中":
                self.append_log(f"服务 {service.name} 已经在运行中，无需重复启动", service_name=service.name, service=service)
                return
            
            # 查找可用端口
            available_port = self._find_available_port(service)
            if available_port is None:
                return
            
            # 构建命令
            command = self._build_command(service, available_port)
            if command is None:
                return
            
            # 启动服务进程
            if not self._start_service_process(service, command):
                return
            
            # 启动服务启动检查定时器
            self._start_service_check_timer(service, index)
            
        except Exception as e:
            # 记录错误信息
            service = self.services[index] if index is not None and 0 <= index < len(self.services) else None
            service_name = service.name if service else "未知服务"
            self.append_log(f"启动服务失败: {str(e)}", error=True, service_name=service_name)
            # 显示错误信息
            error_msg = f"启动服务失败: {str(e)}"
            if 'command' in locals():
                error_msg += f"\n执行命令: {' '.join(command)}"
            error_msg += f"\n当前目录: {os.getcwd()}"
            if service:
                error_msg += f"\n服务工作目录: {service.serve_path}"
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
            # 从树项中获取服务在self.services列表中的实际索引
            index = selected_item.data(0, Qt.UserRole)
        
        # 确保索引是有效的数字
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
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
        
        # 尝试获取可用端口，最多尝试PORT_TRY_LIMIT次
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
        for i in range(PORT_TRY_LIMIT):
            try_port = original_port + i
            
            # 跳过常用屏蔽端口
            if try_port in blocked_ports:
                continue
            
            # 检查端口是否可用，排除当前服务
            if self.is_port_available(try_port, exclude_service=service):
                available_port = try_port
                break
        
        # 如果没有找到可用端口，尝试从一个较高的起始端口开始
        if not available_port:
            start_port = BACKUP_START_PORT
            for i in range(PORT_TRY_LIMIT_BACKUP):
                try_port = start_port + i
                
                # 跳过常用屏蔽端口
                if try_port in blocked_ports:
                    continue
                
                # 检查端口是否可用，排除当前服务
                if self.is_port_available(try_port, exclude_service=service):
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
    
    def _build_command(self, service, available_port):
        """构建启动命令"""
        # 使用dufs.exe的完整路径
        # 使用统一的资源文件访问函数
        dufs_path = get_resource_path("dufs.exe")
        
        # 检查dufs.exe是否存在
        self.append_log(f"获取到的dufs.exe路径: {dufs_path}", service_name=service.name)
        if not os.path.exists(dufs_path):
            self.append_log(f"dufs.exe不存在于路径: {dufs_path}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"dufs.exe不存在于路径: {dufs_path}")
            return None
        
        command = [dufs_path]
        
        # 基本参数，去除多余空白字符
        service_port = str(available_port)
        service_bind = service.bind.strip()
        
        # 确保服务端口已更新
        service.port = service_port
        
        # 服务路径空值检查
        service_serve_path = service.serve_path.strip()
        if not service_serve_path:
            self.append_log(f"启动服务失败: 服务路径不能为空", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径不能为空")
            return None
        
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
            if hasattr(service, 'allow_symlink') and service.allow_symlink:
                command.append("--allow-symlink")
            if hasattr(service, 'allow_archive') and service.allow_archive:
                command.append("--allow-archive")
        
        # 多用户权限
        if service.auth_rules and isinstance(service.auth_rules, list) and len(service.auth_rules) > 0:
            for rule in service.auth_rules:
                # 检查rule是否为字典类型
                if isinstance(rule, dict):
                    username = rule.get("username", "").strip()
                    password = rule.get("password", "").strip()
                    
                    # 确保用户名和密码都不为空
                    if username and password:
                        # 修复认证参数格式：使用正确的权限格式，格式为 user:pass@/:rw
                        auth_rule = f"{username}:{password}@/:rw"
                        command.extend(["--auth", auth_rule])
        # 当没有配置认证规则时，添加默认的匿名访问权限
        # 这确保tokengen功能能够正常工作
        else:
            # 允许匿名访问，确保tokengen功能正常
            command.extend(["--auth", "@/:rw"])
        
        # 移除--log-format参数，使用Dufs的默认日志格式
        # 默认日志格式已经包含了我们需要的所有信息：客户端IP地址、请求方法和路径、HTTP状态码
        # 通过源码分析，默认格式为：$remote_addr "$request" $status
        # 添加--log-format参数明确启用HTTP访问日志
        command.extend(["--log-format", "$remote_addr \"$request\" $status"]) 
    
        # 添加服务根目录（dufs.exe [options] [path]）
        # 在Windows系统上直接使用路径，不使用shlex.quote，因为它会产生单引号包裹的路径
        # 确保路径中的反斜杠被正确处理
        command.append(service_serve_path)
    
        return command
    
    def _start_service_process(self, service, command):
        """启动服务进程"""
        # 检查命令是否有效
        if not command or not isinstance(command, list):
            self.append_log(f"启动服务失败: 无效的命令", error=True, service_name=service.name)
            return False
        
        # 检查服务是否已经在运行，如果是则直接返回
        if service.status == "运行中":
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
                bufsize=1,  # 行缓冲，确保实时获取日志
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
        
        # 启动日志读取线程
        self.append_log(f"启动日志读取线程", service_name=service.name)
        self.stream_log(service.process, service)
        
        return True
    
    def _start_service_check_timer(self, service, index):
        """启动服务启动检查定时器"""
        # 创建一个单次定时器，延迟检查服务状态
        timer = QTimer(self)
        timer.setSingleShot(True)
        # 使用lambda来传递服务对象和索引，同时避免闭包陷阱
        timer.timeout.connect(lambda: self._delayed_check_service_started(service, index, timer))
        # 设置延迟时间
        timer.start(SERVICE_START_WAIT_SECONDS * 1000)
    
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
                stdout_output = ""
                stderr_output = ""
                try:
                    # 尝试读取所有剩余输出
                    if service.process.stdout:
                        stdout_output = service.process.stdout.read()
                    if service.process.stderr:
                        stderr_output = service.process.stderr.read()
                    
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
                service.running = False
                service.status = "未运行"
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
        
        # 服务启动成功，更新服务状态和UI
        self._update_service_after_start(service, index)
        return True
    
    def _update_service_after_start(self, service, index):
        """服务启动后更新状态和UI"""
        # 更新服务状态
        self.append_log(f"进程正常运行，更新服务状态", service_name=service.name, service=service)
        service.status = "运行中"
        service.running = True
        
        # 启动监控线程
        self.append_log(f"启动监控线程", service_name=service.name, service=service)
        threading.Thread(target=self.monitor_service, args=(service, index), daemon=True).start()
        
        # 更新服务列表
        self.append_log(f"更新服务列表", service_name=service.name, service=service)
        self.status_updated.emit()
        
        # 刷新托盘菜单
        self.refresh_tray_menu()
        
        # 更新地址
        self.append_log(f"更新服务地址", service_name=service.name, service=service)
        self.refresh_address(index)
        
        # 更新状态栏
        self.append_log(f"服务启动成功", service_name=service.name, service=service)
        self.status_bar.showMessage(f"已启动服务: {service.name} | 访问地址: {service.local_addr}")
        
        # 刷新托盘菜单
        self.refresh_tray_menu()
    
    def stop_service(self, index_or_service=None):
        """停止选中的服务
        
        Args:
            index_or_service (int or DufsService, optional): 服务索引或服务对象. Defaults to None.
        """
        # 检查服务列表是否为空
        if not self.services:
            QMessageBox.information(self, "提示", "没有服务正在运行")
            return
        
        # 处理服务对象情况
        if isinstance(index_or_service, DufsService):
            service = index_or_service
            # 获取服务索引
            index = self.services.index(service)
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
                # 从树项中获取服务在self.services列表中的实际索引
                index = selected_item.data(0, Qt.UserRole)
            
            # 检查索引是否有效
            if not isinstance(index, int):
                QMessageBox.warning(self, "提示", "请先选择要停止的服务")
                return
            
            # 索引越界保护
            if index < 0 or index >= len(self.services):
                QMessageBox.critical(self, "错误", f"服务索引异常: {index}")
                return
            
            service = self.services[index]
        
        # 进程存在性检查
        if service.process is None or service.process.poll() is not None:
            QMessageBox.information(self, "提示", "该服务已停止")
            return
        
        # 使用psutil更彻底地终止进程及其子进程
        try:
            # 获取进程PID
            pid = service.process.pid
            # 获取进程对象
            proc = psutil.Process(pid)
            # 获取所有子进程
            children = proc.children(recursive=True)
            # 终止所有子进程
            for child in children:
                child.terminate()
            # 等待子进程终止
            psutil.wait_procs(children, timeout=PROCESS_TERMINATE_TIMEOUT)
            # 终止主进程
            proc.terminate()
            # 等待主进程终止
            proc.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 如果进程不存在或无法访问，直接继续
            pass
        except subprocess.TimeoutExpired:
            # 如果超时，强制终止
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 更新服务状态（添加线程锁保护）
        with service.lock:
            service.running = False
            service.process = None
            service.status = "未运行"
            service.local_addr = ""
            # 设置日志线程终止标志
            service.log_thread_terminate = True
        
        # 关闭服务的日志Tab
        if service.log_widget:
            index = self.log_tabs.indexOf(service.log_widget)
            if index != -1:
                self.log_tabs.removeTab(index)
            # 清空服务的日志相关属性
            service.log_widget = None
            service.log_tab_index = None
        
        # 记录服务停止信息
        self.append_log(f"已停止服务", service_name=service.name, service=service)
        
        # 更新服务列表
        self.status_updated.emit()
        
        # 刷新托盘菜单
        self.refresh_tray_menu()
        
        # 清空地址显示
        self.addr_edit.setText("")
        
        # 更新状态栏
        self.status_bar.showMessage(f"已停止服务: {service.name}")
        
        # 刷新托盘菜单
        self.refresh_tray_menu()
    
    def monitor_service(self, service, index):
        """监控服务状态"""
        while True:
            # 检查服务是否仍在运行
            with service.lock:
                if not service.running or service.process is None:
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
                    service.running = False
                    service.process = None
                    service.status = "未运行"
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
            
            # 控制循环频率，避免占用过多CPU资源
            time.sleep(1)


# 主入口代码
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置窗口图标
    icon_path = get_resource_path("icon.ico")
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = DufsMultiGUI()
    sys.exit(app.exec_())
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
        # 从树项中获取服务在self.services列表中的实际索引
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
        # 从树项中获取服务在self.services列表中的实际索引
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
        # 从树项中获取服务在self.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)

        # 确保索引有效
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return

        service = self.services[index]

        # 如果服务正在运行，先停止
        if service.status == "运行中":
            self.stop_service(index)

        # 显示确认框
        if QMessageBox.question(self, "提示", f"确定要删除服务 '{service.name}' 吗？") != QMessageBox.Yes:
            return

        # 删除服务
        del self.services[index]

        # 更新服务列表
        self.status_updated.emit()

        # 更新状态栏
        self.status_bar.showMessage(f"已删除服务: {service.name}")

        # 保存配置
        self.save_config()

    def start_service(self, index=None):
        """启动选中的服务"""
        try:
            # 获取并验证服务索引
            index = self._get_service_index(index)
            if index is None:
                return

            # 获取服务对象
            service = self.services[index]

            # 检查服务是否已经在运行，如果是则直接返回
            if service.status == "运行中":
                self.append_log(f"服务 {service.name} 已经在运行中，无需重复启动", service_name=service.name, service=service)
                return

            # 查找可用端口
            available_port = self._find_available_port(service)
            if available_port is None:
                return

            # 构建命令
            command = self._build_command(service, available_port)

            # 启动服务进程
            if not self._start_service_process(service, command):
                return

            # 启动服务启动检查定时器
            self._start_service_check_timer(service, index)

        except Exception as e:
            # 记录错误信息
            service = self.services[index] if index is not None and 0 <= index < len(self.services) else None
            service_name = service.name if service else "未知服务"
            self.append_log(f"启动服务失败: {str(e)}", error=True, service_name=service_name)
            # 显示错误信息
            error_msg = f"启动服务失败: {str(e)}"
            if 'command' in locals():
                error_msg += f"\n执行命令: {' '.join(command)}"
            error_msg += f"\n当前目录: {os.getcwd()}"
            if service:
                error_msg += f"\n服务工作目录: {service.serve_path}"
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
            # 从树项中获取服务在self.services列表中的实际索引
            index = selected_item.data(0, Qt.UserRole)

        # 确保索引是有效的数字
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
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

        # 尝试获取可用端口，最多尝试PORT_TRY_LIMIT次
        original_port = int(service.port.strip())
        available_port = None

        # 从原始端口开始尝试，如果被占用则尝试更高的端口
        for i in range(PORT_TRY_LIMIT):
            try_port = original_port + i

            # 跳过常用屏蔽端口
            if try_port in blocked_ports:
                continue

            # 检查端口是否可用，排除当前服务
            if self.is_port_available(try_port, exclude_service=service):
                available_port = try_port
                break

        # 如果没有找到可用端口，尝试从一个较高的起始端口开始
        if not available_port:
            start_port = BACKUP_START_PORT
            for i in range(PORT_TRY_LIMIT_BACKUP):
                try_port = start_port + i

                # 跳过常用屏蔽端口
                if try_port in blocked_ports:
                    continue

                # 检查端口是否可用，排除当前服务
                if self.is_port_available(try_port, exclude_service=service):
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

    def _build_command(self, service, available_port):
        """构建启动命令"""
        # 使用dufs.exe的完整路径
        # 使用统一的资源文件访问函数
        dufs_path = get_resource_path("dufs.exe")
        command = [dufs_path]

        # 基本参数，去除多余空白字符
        service_port = str(available_port)
        service_bind = service.bind.strip()

        # 确保服务端口已更新
        service.port = service_port

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
            if hasattr(service, 'allow_symlink') and service.allow_symlink:
                command.append("--allow-symlink")
            if service.allow_archive:
                command.append("--allow-archive")
        
        # 多用户权限
        if service.auth_rules:
            for rule in service.auth_rules:
                username = rule["username"].strip()
                password = rule["password"].strip()
                
                # 确保用户名和密码都不为空
                if username and password:
                    # 修复认证参数格式：使用正确的权限格式，格式为 user:pass@/:rw
                    auth_rule = f"{username}:{password}@/:rw"
                    command.extend(["--auth", auth_rule])
        # 当没有配置认证规则时，添加默认的匿名访问权限
        # 这确保tokengen功能能够正常工作
        else:
            # 允许匿名访问，确保tokengen功能正常
            command.extend(["--auth", "@/:rw"])
        
        # 移除--log-format参数，使用Dufs的默认日志格式
        # 默认日志格式已经包含了我们需要的所有信息：客户端IP地址、请求方法和路径、HTTP状态码
        # 通过源码分析，默认格式为：$remote_addr "$request" $status
        
        # 添加服务根目录（dufs.exe [options] [path]）
        command.append(service.serve_path)
        
        return command
    
    def _start_service_process(self, service, command):
        """启动服务进程"""
        # 检查服务是否已经在运行，如果是则直接返回
        if service.status == "运行中":
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
        
        # 检查服务路径是否可访问（读取权限）
        if not os.access(service.serve_path, os.R_OK):
            self.append_log(f"启动服务失败: 服务路径不可访问（缺少读取权限） - 路径: {service.serve_path}", error=True, service_name=service.name)
            QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径不可访问（缺少读取权限）\n路径: {service.serve_path}")
            return False
        
        # 记录服务启动信息
        self.append_log(f"启动 DUFS...", service_name=service.name)
        
        # 启动进程 - 使用正确的参数
        # 设置工作目录为程序所在目录，确保dufs.exe能找到所需依赖
        cwd = os.path.dirname(dufs_path)
        
        # 启动进程，捕获输出以支持实时日志
        creation_flags = 0
        if os.name == 'nt':  # Windows系统
            creation_flags = subprocess.CREATE_NO_WINDOW  # 隐藏命令窗口
        
        # 启动服务进程
        self.append_log(f"执行命令: {' '.join(command)}", service_name=service.name)
        
        service.process = subprocess.Popen(
            command,
            cwd=cwd,  # 设置工作目录
            shell=False,  # 不使用shell执行
            env=os.environ.copy(),  # 复制当前环境变量
            stdout=subprocess.PIPE,  # 捕获标准输出
            stderr=subprocess.PIPE,  # 捕获标准错误
            text=True,  # 使用文本模式而不是字节模式
            bufsize=1,  # 行缓冲，确保实时获取日志
            universal_newlines=True,  # 确保正确处理换行符
            creationflags=creation_flags  # 隐藏命令窗口
        )
        
        self.append_log(f"进程已启动，PID: {service.process.pid}", service_name=service.name)
        
        # 启动日志读取线程
        self.append_log(f"启动日志读取线程", service_name=service.name)
        self.stream_log(service.process, service)
        
        return True
    
    def _start_service_check_timer(self, service, index):
        """启动服务启动检查定时器"""
        # 创建一个单次定时器，延迟检查服务状态
        timer = QTimer(self)
        timer.setSingleShot(True)
        # 使用lambda来传递服务对象和索引，同时避免闭包陷阱
        timer.timeout.connect(lambda: self._delayed_check_service_started(service, index, timer))
        # 设置延迟时间
        timer.start(SERVICE_START_WAIT_SECONDS * 1000)
    
    def _delayed_check_service_started(self, service, index, timer):
        """延迟检查服务是否成功启动"""
        # 确保定时器被释放
        timer.deleteLater()
        
        # 检查进程是否还在运行
        poll_result = service.process.poll()
        self.append_log(f"进程状态检查结果: {poll_result}", service_name=service.name)
        if poll_result is not None:
            # 进程已退出，说明启动失败
            # 尝试读取stdout和stderr获取详细错误信息
            stdout_output = ""
            stderr_output = ""
            try:
                # 尝试读取所有剩余输出
                if service.process.stdout:
                    stdout_output = service.process.stdout.read()
                if service.process.stderr:
                    stderr_output = service.process.stderr.read()
                
                if stdout_output:
                    self.append_log(f"进程退出，stdout: {stdout_output}", error=True, service_name=service.name)
                if stderr_output:
                    self.append_log(f"进程退出，stderr: {stderr_output}", error=True, service_name=service.name)
            except Exception as e:
                self.append_log(f"读取进程输出失败: {str(e)}", error=True, service_name=service.name)
            
            service.process = None
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
        
        # 服务启动成功，更新服务状态和UI
        self._update_service_after_start(service, index)
        return True
    
    def _update_service_after_start(self, service, index):
        """服务启动后更新状态和UI"""
        # 更新服务状态
        self.append_log(f"进程正常运行，更新服务状态", service_name=service.name, service=service)
        service.status = "运行中"
        service.running = True
        
        # 启动监控线程
        self.append_log(f"启动监控线程", service_name=service.name, service=service)
        threading.Thread(target=self.monitor_service, args=(service, index), daemon=True).start()
        
        # 更新服务列表
        self.append_log(f"更新服务列表", service_name=service.name, service=service)
        self.status_updated.emit()
        
        # 更新地址
        self.append_log(f"更新服务地址", service_name=service.name, service=service)
        self.refresh_address(index)
        
        # 更新状态栏
        self.append_log(f"服务启动成功", service_name=service.name, service=service)
        self.status_bar.showMessage(f"已启动服务: {service.name} | 访问地址: {service.local_addr}")
        
        # 刷新托盘菜单
        self.refresh_tray_menu()
    
    def stop_service(self, index_or_service=None):
        """停止选中的服务
        
        Args:
            index_or_service (int or DufsService, optional): 服务索引或服务对象. Defaults to None.
        """
        # 检查服务列表是否为空
        if not self.services:
            QMessageBox.information(self, "提示", "没有服务正在运行")
            return
        
        # 处理服务对象情况
        if isinstance(index_or_service, DufsService):
            service = index_or_service
            # 获取服务索引
