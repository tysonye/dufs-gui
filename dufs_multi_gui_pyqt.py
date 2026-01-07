import sys
import os
import subprocess
import threading
import time
import socket
import psutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QFrame, QGroupBox, QGridLayout, QMenu, QAction,
    QMessageBox, QFileDialog, QDialog, QComboBox, QCheckBox, QSystemTrayIcon, QStyle, QToolTip, QStatusBar, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QFontMetrics, QCursor

# 全局样式表配置
GLOBAL_STYLESHEET = """
/* 基础控件样式 */
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 12px;
    color: #333333;
    background-color: #FFFFFF;
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
    background-color: #3498DB;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #2980B9;
}

QPushButton:pressed {
    background-color: #1F618D;
}

QPushButton:disabled {
    background-color: #BDC3C7;
}

/* 浏览按钮特殊样式 */
QPushButton#PathBrowseBtn {
    background-color: #2ECC71;
}

QPushButton#PathBrowseBtn:hover {
    background-color: #27AE60;
}

/* 确定/取消按钮样式区分 */
QPushButton#OkBtn {
    background-color: #27AE60;
}

QPushButton#OkBtn:hover {
    background-color: #219653;
}

QPushButton#CancelBtn {
    background-color: #E74C3C;
}

QPushButton#CancelBtn:hover {
    background-color: #C0392B;
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
    padding: 8px 16px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
    background-color: #ECF0F1;
}

QTabBar::tab:selected {
    background-color: #3498DB;
    color: white;
}

QTabBar::tab:!selected:hover {
    background-color: #D5DBDB;
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



/* 状态栏样式 */
QStatusBar {
    background-color: #ECF0F1;
    color: #2C3E50;
    font-size: 11px;
}
"""

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
        self.setGeometry(400, 200, 750, 550)
        self.setModal(True)
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        # 字体设置
        font = QFont("Microsoft YaHei", 12)
        self.setFont(font)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QGridLayout()
        basic_layout.setContentsMargins(15, 15, 15, 15)
        basic_layout.setSpacing(12)
        
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
            default_port = 5001  # 从5001开始，避开常用的5000端口
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
        self.password_edit.setEchoMode(QLineEdit.Normal)
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
        
        if not port.isdigit():
            QMessageBox.critical(self, "错误", "端口必须是数字")
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
            # 用户名限制：长度在3-20个字符之间，包含至少一个字母
            if len(username) < 3 or len(username) > 20:
                QMessageBox.critical(self, "错误", "用户名长度必须在3-20个字符之间")
                return
            if not any(c.isalpha() for c in username):
                QMessageBox.critical(self, "错误", "用户名必须包含至少一个字母")
                return
            
            # 密码限制：长度在6-30个字符之间，包含至少一个字母和一个数字
            if len(password) < 6 or len(password) > 30:
                QMessageBox.critical(self, "错误", "密码长度必须在6-30个字符之间")
                return
            if not any(c.isalpha() for c in password):
                QMessageBox.critical(self, "错误", "密码必须包含至少一个字母")
                return
            if not any(c.isdigit() for c in password):
                QMessageBox.critical(self, "错误", "密码必须包含至少一个数字")
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
    
    def __init__(self):
        super().__init__()
        self.services = []
        self.init_ui()
        self.status_updated.connect(self.update_service_list)
    
    def init_ui(self):
        """初始化主窗口UI"""
        # 设置窗口属性
        self.setWindowTitle("Dufs多服务管理")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(GLOBAL_STYLESHEET)
        
        # 居中显示
        screen_geo = QApplication.desktop().screenGeometry()
        self.setGeometry(
            (screen_geo.width() - 900) // 2,
            (screen_geo.height() - 600) // 2,
            900, 600
        )
        
        # 中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 10)
        main_layout.setSpacing(15)
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("Dufs 多服务管理面板")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #2C3E50;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)
        
        # 按钮组
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
        
        # 服务列表
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
        
        # 访问地址
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
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪 - 未运行任何服务 | 点击「添加服务」创建新服务")
        self.setStatusBar(self.status_bar)
        
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
        
        # 初始化服务列表
        self.update_service_list()
        
        # 初始化系统托盘
        self.init_system_tray()
        
        # 绑定窗口关闭事件
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.show()
    
    def init_system_tray(self):
        """初始化系统托盘"""
        # 获取图标路径
        def get_icon_path():
            # 单文件打包时，PyInstaller会设置sys._MEIPASS指向临时目录
            if hasattr(sys, '_MEIPASS'):
                # 单文件打包模式，从临时目录加载
                return os.path.join(sys._MEIPASS, "icon.ico")
            else:
                # 开发模式，从当前目录或程序目录加载
                # 尝试从当前目录加载
                icon_path = "icon.ico"
                if os.path.exists(icon_path):
                    return icon_path
                # 尝试从程序所在目录加载
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
                if os.path.exists(icon_path):
                    return icon_path
                return None
        
        # 创建托盘图标
        icon_path = get_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        else:
            # 如果没有图标文件，使用默认图标
            self.tray_icon = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        
        # 设置托盘图标提示
        self.tray_icon.setToolTip("Dufs多服务管理")
        
        # 创建托盘菜单
        tray_menu = QMenu(self)
        
        # 显示窗口菜单项
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        # 退出程序菜单项
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.on_exit)
        tray_menu.addAction(exit_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)
        
        # 绑定托盘图标激活事件
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
    
    def show_window(self):
        """显示主窗口"""
        self.showNormal()
        self.raise_()
        self.activateWindow()
    
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
            item = QTreeWidgetItem([
                service.name,
                service.port,
                service.status,
                auth_info,
                perms_text,
                service.serve_path
            ])
            
            # 设置所有列的内容居中对齐
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
            self.status_bar.showMessage(f"已添加服务: {dialog.service.name}")
    
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
                # 保存旧服务实例，用于停止旧进程
                old_service = service
                # 停止旧服务
                self.stop_service(index)
            
            # 更新服务
            self.services[index] = dialog.service
            self.status_updated.emit()
            
            # 如果服务之前是运行中的，启动新服务
            if was_running:
                QMessageBox.information(self, "提示", "服务配置已更改，服务将自动重启以应用新配置。")
                self.start_service(index)
    
    def start_service_from_button(self):
        """从主面板按钮启动服务（修复：获取选中的服务）"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要启动的服务")
            return
        
        # 单选模式下，只处理第一个选中项
        selected_item = selected_items[0]
        # 从树项中获取服务在self.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)
        
        # 确保索引是有效的数字
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return
        
        # 调用带索引的启动服务方法
        self.start_service(index)
    
    def stop_service_from_button(self):
        """从主面板按钮停止服务（修复：获取选中的服务）"""
        # 获取当前选中的服务
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要停止的服务")
            return
        
        # 单选模式下，只处理第一个选中项
        selected_item = selected_items[0]
        # 从树项中获取服务在self.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)
        
        # 确保索引是有效的数字
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return
        
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
    
    def start_service(self, index=None):
        """启动选中的服务"""
        # 如果没有提供索引，获取当前选中的服务索引
        if index is None:
            selected_items = self.service_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择要启动的服务")
                return
            # 单选模式下，只处理第一个选中项
            selected_item = selected_items[0]
            # 从树项中获取服务在self.services列表中的实际索引
            index = selected_item.data(0, Qt.UserRole)
        
        # 确保索引是有效的数字
        if not isinstance(index, int) or index < 0 or index >= len(self.services):
            QMessageBox.critical(self, "错误", "无效的服务索引")
            return
        
        # 获取对应的服务对象
        service = self.services[index]
        
        # 系统常用、浏览器黑名单、特殊软件常用端口黑名单（只包含真正需要屏蔽的端口）
        blocked_ports = {
            # 系统常用端口（真正需要屏蔽的）
            20, 21, 22, 23, 25, 53, 67, 68, 80, 443, 110, 143, 161, 162, 389, 445, 514, 636, 993, 995,
            # 数据库端口
            1433, 1521, 3306, 3389, 5432, 6446, 6447, 6379, 27017, 28017, 9200, 9300,
            # 常见危险端口
            4444, 5555, 6666, 7777, 8888, 9999, 12345, 12346, 12347, 16992, 16993
        }
        
        # 尝试获取可用端口，最多尝试100次
        original_port = int(service.port.strip())
        available_port = None
        
        # 从原始端口开始尝试，如果被占用则尝试更高的端口
        for i in range(100):
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
            start_port = 8000
            for i in range(50):
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
        else:
            # 尝试了多个端口都不可用，提示用户
            QMessageBox.critical(
                self,
                "错误",
                f"端口 {original_port} 不可用，尝试了多个端口都不可用。\n" +
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
        
        # 添加服务根目录（dufs.exe [options] [path]）
        command.append(service.serve_path)
        
        # 启动服务
        try:
            # 检查 dufs.exe 是否存在
            if not os.path.exists(dufs_path):
                QMessageBox.critical(self, "错误", f"启动服务失败: dufs.exe 不存在\n路径: {dufs_path}")
                return
            
            # 检查服务路径是否存在
            if not os.path.exists(service.serve_path):
                QMessageBox.critical(self, "错误", f"启动服务失败: 服务路径不存在\n路径: {service.serve_path}")
                return
            
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
                error_msg += f"\n执行命令: {' '.join(command)}"
                error_msg += f"\n服务工作目录: {service.serve_path}"
                QMessageBox.critical(self, "错误", error_msg)
                service.process = None
                return
            
            # 更新服务状态
            service.status = "运行中"
            
            # 启动监控线程
            threading.Thread(target=self.monitor_service, args=(service, index), daemon=True).start()
            
            # 更新服务列表
            self.status_updated.emit()
            
            # 更新地址
            self.refresh_address(index)
            
            # 更新状态栏
            self.status_bar.showMessage(f"已启动服务: {service.name} | 访问地址: {service.local_addr}")
        except Exception as e:
            # 显示错误信息
            error_msg = f"启动服务失败: {str(e)}"
            error_msg += f"\n执行命令: {' '.join(command)}"
            error_msg += f"\n当前目录: {os.getcwd()}"
            error_msg += f"\n服务工作目录: {service.serve_path}"
            QMessageBox.critical(self, "错误", error_msg)
    
    def stop_service(self, index=None):
        """停止选中的服务"""
        # 检查服务列表是否为空
        if not self.services:
            QMessageBox.information(self, "提示", "没有服务正在运行")
            return
        
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
            psutil.wait_procs(children, timeout=2)
            # 终止主进程
            proc.terminate()
            # 等待主进程终止
            proc.wait(timeout=2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 如果进程不存在或无法访问，直接继续
            pass
        except subprocess.TimeoutExpired:
            # 如果超时，强制终止
            try:
                proc.kill()
            except:
                pass
        finally:
            # 无论如何，都执行原始的终止和清理操作
            service.process.terminate()
            try:
                service.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                service.process.kill()
        
        # 更新服务状态
        service.process = None
        service.status = "未运行"
        service.local_addr = ""
        
        # 更新服务列表
        self.status_updated.emit()
        
        # 清空地址显示
        self.addr_edit.setText("")
        
        # 更新状态栏
        self.status_bar.showMessage(f"已停止服务: {service.name}")
    
    def monitor_service(self, service, index):
        """监控服务运行状态"""
        while service.process:
            if service.process.poll() is not None:
                service.status = "未运行"
                service.process = None
                # 使用信号在主线程更新UI
                self.status_updated.emit()
                break
            time.sleep(1)
    
    def refresh_address(self, index):
        """刷新服务访问地址"""
        service = self.services[index]
        
        if service.status != "运行中":
            # 清空地址显示
            self.addr_edit.setText("")
            return
        
        # 获取本地IP
        local_ip = self.get_local_ip()
        service.local_addr = f"http://{local_ip}:{service.port}"
        
        # 更新地址显示
        self.addr_edit.setText(service.local_addr)
    
    def on_service_selected(self):
        """服务选中事件处理"""
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            # 单选模式下，只显示第一个选中服务的地址
            selected_item = selected_items[0]
            # 从树项中获取服务在self.services列表中的实际索引
            index = selected_item.data(0, Qt.UserRole)
            self.refresh_address(index)
    
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
    
    def browser_access(self):
        """用浏览器访问服务"""
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要访问的服务")
            return
        
        # 单选模式下，只访问第一个选中的服务
        selected_item = selected_items[0]
        # 从树项中获取服务在self.services列表中的实际索引
        index = selected_item.data(0, Qt.UserRole)
        service = self.services[index]
        
        if service.status != "运行中":
            QMessageBox.information(self, "提示", "服务未运行")
            return
        
        if service.local_addr:
            subprocess.Popen(["start", service.local_addr], shell=True)
    
    def copy_address(self):
        """复制地址到剪贴板"""
        address = self.addr_edit.text()
        if address:
            clipboard = QApplication.clipboard()
            clipboard.setText(address)


    
    def is_port_available(self, port, exclude_service=None):
        """检查端口是否可用，排除指定服务"""
        try:
            # 检查端口是否被当前运行的服务占用，排除指定服务
            for service in self.services:
                # 只有当服务不是排除服务且状态为运行中且端口匹配时，才返回 False
                if service != exclude_service and service.status == "运行中" and str(service.port) == str(port):
                    return False
            
            # 尝试绑定端口，检查是否被系统占用
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", port))
                return True
        except:
            return False
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()
        
        # 获取右键点击的项
        item = self.service_tree.itemAt(position)
        if not item:
            return
        
        # 确保右键点击的项被选中
        self.service_tree.setCurrentItem(item)
        
        # 获取服务索引
        # 从树项中获取服务在self.services列表中的实际索引
        index = item.data(0, Qt.UserRole)
        
        # 浏览器访问
        browse_action = QAction("浏览器访问", self)
        browse_action.triggered.connect(self.browser_access)
        menu.addAction(browse_action)
        
        menu.addSeparator()
        
        # 复制账户
        copy_account_action = QAction("复制账户", self)
        copy_account_action.triggered.connect(self.copy_account)
        menu.addAction(copy_account_action)
        
        # 复制密码
        copy_password_action = QAction("复制密码", self)
        copy_password_action.triggered.connect(self.copy_password)
        menu.addAction(copy_password_action)
        
        menu.addSeparator()
        
        # 启动服务
        start_action = QAction("启动服务", self)
        start_action.triggered.connect(lambda: self.start_service(index))
        menu.addAction(start_action)
        
        # 停止服务
        stop_action = QAction("停止服务", self)
        stop_action.triggered.connect(lambda: self.stop_service(index))
        menu.addAction(stop_action)
        
        menu.addSeparator()
        
        # 编辑服务
        edit_action = QAction("编辑服务", self)
        edit_action.triggered.connect(lambda: self.edit_service(index))
        menu.addAction(edit_action)
        
        # 删除服务
        delete_action = QAction("删除服务", self)
        delete_action.triggered.connect(lambda: self.delete_service(index))
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.service_tree.viewport().mapToGlobal(position))
    
    def copy_account(self):
        """复制服务账户到剪贴板"""
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            index = self.service_tree.indexOfTopLevelItem(selected_item)
            service = self.services[index]
            if service.auth_rules:
                username = service.auth_rules[0].get("username", "")
                if username:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(username)
    
    def copy_password(self):
        """复制服务密码到剪贴板"""
        selected_items = self.service_tree.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            index = self.service_tree.indexOfTopLevelItem(selected_item)
            service = self.services[index]
            if service.auth_rules:
                password = service.auth_rules[0].get("password", "")
                if password:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(password)
    
    def on_exit(self):
        """退出程序，停止所有服务"""
        # 停止所有运行中的服务
        for i in range(len(self.services)):
            if self.services[i].status == "运行中":
                self.stop_service(i)
        
        # 额外的进程清理：确保所有dufs进程都被终止
        try:
            # 查找所有名称为dufs.exe的进程并终止
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == 'dufs.exe':
                    try:
                        proc.terminate()
                    except:
                        try:
                            proc.kill()
                        except:
                            pass
            # 等待所有进程终止
            time.sleep(1)
        except:
            pass
        
        # 隐藏托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        # 关闭主窗口并退出应用程序
        self.close()
        QApplication.quit()
        # 强制退出Python解释器，确保所有线程都被终止
        sys.exit(0)

if __name__ == "__main__":
    # 解决PyInstaller临时目录删除失败的警告
    # 方法：使用ctypes捕获Windows错误消息，防止警告弹窗
    if hasattr(sys, '_MEIPASS') and sys.platform == 'win32':
        try:
            import ctypes
            # 设置Windows错误模式，忽略删除目录失败的错误
            SEM_NOGPFAULTERRORBOX = 0x0002
            SEM_NOOPENFILEERRORBOX = 0x8000
            ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX)
        except Exception:
            pass
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 跨平台统一样式
    
    # 设置应用程序图标
    # 获取图标路径
    def get_icon_path():
        # 单文件打包时，PyInstaller会设置sys._MEIPASS指向临时目录
        if hasattr(sys, '_MEIPASS'):
            # 单文件打包模式，从临时目录加载
            return os.path.join(sys._MEIPASS, "icon.ico")
        else:
            # 开发模式，从当前目录或程序目录加载
            # 尝试从当前目录加载
            icon_path = "icon.ico"
            if os.path.exists(icon_path):
                return icon_path
            # 尝试从程序所在目录加载
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                return icon_path
            return None
    
    icon_path = get_icon_path()
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = DufsMultiGUI()
    window.show()
    sys.exit(app.exec_())