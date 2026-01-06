import sys
import os
import subprocess
import threading
import time
import socket
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QFrame, QGroupBox, QGridLayout, QMenu, QAction,
    QMessageBox, QFileDialog, QDialog, QComboBox, QCheckBox, QSystemTrayIcon, QStyle, QToolTip
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QBrush, QIcon, QFontMetrics, QCursor

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
    def __init__(self, parent=None, service=None, edit_index=None):
        super().__init__(parent)
        self.service = service
        self.edit_index = edit_index
        self.init_ui()
    
    def init_ui(self):
        """初始化对话框UI"""
        self.setWindowTitle("编辑服务" if self.service else "添加服务")
        self.setGeometry(400, 200, 700, 500)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 综合设置标签页
        tab_widget = QTabWidget()
        main_tab = QWidget()
        main_layout.addWidget(tab_widget)
        
        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QGridLayout()
        
        # 服务名称
        basic_layout.addWidget(QLabel("服务名称:"), 0, 0)
        self.name_edit = QLineEdit()
        basic_layout.addWidget(self.name_edit, 0, 1)
        
        # 服务路径
        basic_layout.addWidget(QLabel("服务路径:"), 1, 0)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        path_btn = QPushButton("浏览")
        path_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_btn)
        basic_layout.addLayout(path_layout, 1, 1)
        
        # 端口
        basic_layout.addWidget(QLabel("端口:"), 2, 0)
        self.port_edit = QLineEdit()
        basic_layout.addWidget(self.port_edit, 2, 1)
        
        basic_group.setLayout(basic_layout)
        
        # 权限设置
        perm_group = QGroupBox("权限设置")
        perm_layout = QVBoxLayout()
        
        # 全选（单独一行）
        self.allow_all_check = QCheckBox("全选")
        self.allow_all_check.stateChanged.connect(self.on_select_all)
        perm_layout.addWidget(self.allow_all_check)
        
        # 其他权限选项水平排列
        perm_row_layout = QHBoxLayout()
        
        # 允许上传
        self.allow_upload_check = QCheckBox("允许上传")
        self.allow_upload_check.stateChanged.connect(self.on_perm_change)
        perm_row_layout.addWidget(self.allow_upload_check)
        
        # 允许删除
        self.allow_delete_check = QCheckBox("允许删除")
        self.allow_delete_check.stateChanged.connect(self.on_perm_change)
        perm_row_layout.addWidget(self.allow_delete_check)
        
        # 允许搜索
        self.allow_search_check = QCheckBox("允许搜索")
        self.allow_search_check.stateChanged.connect(self.on_perm_change)
        perm_row_layout.addWidget(self.allow_search_check)
        
        # 添加水平布局到垂直布局
        perm_layout.addLayout(perm_row_layout)
        
        perm_group.setLayout(perm_layout)
        
        # 认证设置
        auth_group = QGroupBox("认证设置")
        auth_layout = QGridLayout()
        
        # 用户名
        auth_layout.addWidget(QLabel("用户名:"), 0, 0)
        self.username_edit = QLineEdit()
        auth_layout.addWidget(self.username_edit, 0, 1)
        
        # 密码
        auth_layout.addWidget(QLabel("密码:"), 0, 2)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(self.password_edit, 0, 3)
        
        # 提示信息
        tip_label = QLabel("提示: 留空表示不启用认证")
        tip_label.setStyleSheet("color: gray;")
        auth_layout.addWidget(tip_label, 1, 0, 1, 4)
        
        auth_group.setLayout(auth_layout)
        
        # 主标签页布局
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(basic_group)
        tab_layout.addWidget(perm_group)
        tab_layout.addWidget(auth_group)
        main_tab.setLayout(tab_layout)
        tab_widget.addTab(main_tab, "服务设置")
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
        # 填充现有数据
        if self.service:
            self.name_edit.setText(self.service.name)
            self.path_edit.setText(self.service.serve_path)
            self.port_edit.setText(self.service.port)
            
            # 权限设置
            self.allow_all_check.setChecked(self.service.allow_all)
            self.allow_upload_check.setChecked(self.service.allow_upload)
            self.allow_delete_check.setChecked(self.service.allow_delete)
            self.allow_search_check.setChecked(self.service.allow_search)
            
            # 认证设置
            if self.service.auth_rules:
                username = self.service.auth_rules[0].get("username", "")
                password = self.service.auth_rules[0].get("password", "")
                self.username_edit.setText(username)
                self.password_edit.setText(password)
    
    def browse_path(self):
        """浏览服务路径"""
        path = QFileDialog.getExistingDirectory(self, "选择服务路径")
        if path:
            self.path_edit.setText(path)
    
    def on_select_all(self):
        """全选/取消全选逻辑"""
        value = self.allow_all_check.isChecked()
        self.allow_upload_check.setChecked(value)
        self.allow_delete_check.setChecked(value)
        self.allow_search_check.setChecked(value)
    
    def on_perm_change(self):
        """权限变化时的逻辑"""
        # 当所有权限都勾选时，自动勾选全选
        if (self.allow_upload_check.isChecked() and 
            self.allow_delete_check.isChecked() and 
            self.allow_search_check.isChecked()):
            self.allow_all_check.setChecked(True)
        else:
            self.allow_all_check.setChecked(False)
    
    def on_ok(self):
        """保存服务配置"""
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
        
        # 权限设置
        allow_all = self.allow_all_check.isChecked()
        allow_upload = self.allow_upload_check.isChecked()
        allow_delete = self.allow_delete_check.isChecked()
        allow_search = self.allow_search_check.isChecked()
        allow_symlink = False  # 移除了该选项，默认禁用
        allow_archive = True  # 移除了该选项，默认启用
        
        # 认证设置（简化为单个用户名密码）
        auth_rules = []
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if username and password:
            # 验证用户名密码格式
            if not any(c.isalpha() for c in username):
                QMessageBox.critical(self, "错误", "用户名必须包含至少一个字母")
                return
            if not any(c.isalpha() for c in password):
                QMessageBox.critical(self, "错误", "密码必须包含至少一个字母")
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
        
        self.service = service
        self.accept()

class DufsMultiGUI(QMainWindow):
    """Dufs多服务GUI主程序"""
    def __init__(self):
        super().__init__()
        self.services = []
        self.init_ui()
    
    def init_ui(self):
        """初始化主窗口UI"""
        # 设置窗口属性
        self.setWindowTitle("Dufs多服务管理")
        self.setGeometry(300, 150, 900, 600)
        
        # 设置玻璃态主题
        self.set_glass_theme()
        
        # 中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 服务列表
        self.service_tree = QTreeWidget()
        self.service_tree.setColumnCount(6)
        self.service_tree.setHeaderLabels(["服务名称", "端口", "状态", "认证", "权限", "服务路径"])
        self.service_tree.setAlternatingRowColors(True)
        self.service_tree.setStyleSheet("""QTreeWidget {
            background-color: white;
            border: 1px solid #e0e8f0;
            border-radius: 8px;
            font-size: 10pt;
        }
        QTreeWidget::header {
            background-color: #f0f4f8;
            border-bottom: 1px solid #e0e8f0;
            font-weight: bold;
            font-size: 10pt;
        }
        QTreeWidget::item {
            height: 30px;
        }
        QTreeWidget::item:selected {
            background-color: #c9d8e8;
            color: #333333;
        }
        QTreeWidget::item:hover {
            background-color: #f8f8f8;
        }""")
        
        # 设置列宽
        self.service_tree.setColumnWidth(0, 150)
        self.service_tree.setColumnWidth(1, 80)
        self.service_tree.setColumnWidth(2, 100)
        self.service_tree.setColumnWidth(3, 150)
        self.service_tree.setColumnWidth(4, 120)
        self.service_tree.setColumnWidth(5, 300)
        
        # 绑定双击事件
        self.service_tree.itemDoubleClicked.connect(self.edit_service)
        
        # 绑定右键菜单
        self.service_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.service_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # 启用鼠标跟踪，以便实现悬浮提示
        self.service_tree.setMouseTracking(True)
        # 绑定鼠标进入项事件
        self.service_tree.itemEntered.connect(self.on_item_entered)
        
        main_layout.addWidget(self.service_tree)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # 添加服务按钮
        self.add_btn = QPushButton("添加服务")
        self.add_btn.clicked.connect(self.add_service)
        
        # 编辑服务按钮
        self.edit_btn = QPushButton("编辑服务")
        self.edit_btn.clicked.connect(self.edit_service)
        
        # 删除服务按钮
        self.delete_btn = QPushButton("删除服务")
        self.delete_btn.clicked.connect(self.delete_service)
        
        # 启动服务按钮
        self.start_btn = QPushButton("启动服务")
        self.start_btn.clicked.connect(self.start_service)
        
        # 停止服务按钮
        self.stop_btn = QPushButton("停止服务")
        self.stop_btn.clicked.connect(self.stop_service)
        
        # 关闭程序按钮
        self.exit_btn = QPushButton("关闭程序")
        self.exit_btn.clicked.connect(self.on_exit)
        
        # 添加按钮到布局
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.exit_btn)
        
        main_layout.addLayout(btn_layout)
        
        # 访问地址
        addr_group = QGroupBox("访问地址")
        addr_layout = QHBoxLayout()
        
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
        
        # 绑定服务列表选择事件
        self.service_tree.itemSelectionChanged.connect(self.on_service_selected)
        
        # 初始化服务列表
        self.update_service_list()
        
        # 初始化系统托盘
        self.init_system_tray()
        
        # 绑定窗口关闭事件
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.show()
        
    def init_system_tray(self):
        """初始化系统托盘"""
        # 创建托盘图标
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ICON.ICO"))
        if os.path.exists(icon_path):
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
        """处理鼠标进入项事件，显示悬浮提示"""
        # 只对认证列（索引3）和服务路径列（索引5）显示悬浮提示
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
    
    def set_glass_theme(self):
        """设置玻璃态主题"""
        # 设置全局样式
        self.setStyleSheet("""QMainWindow {
            background-color: #f0f4f8;
        }
        QWidget {
            background-color: #f0f4f8;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        QGroupBox {
            background-color: white;
            border: 1px solid #e0e8f0;
            border-radius: 8px;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            font-weight: bold;
            color: #333333;
        }
        QPushButton {
            background-color: #f0f4f8;
            color: #333333;
            border: 1px solid #e0e8f0;
            border-radius: 6px;
            padding: 8px 15px;
            font-size: 10pt;
        }
        QPushButton:hover {
            background-color: #e0e8f0;
        }
        QPushButton:pressed {
            background-color: #c9d8e8;
        }
        QLineEdit {
            background-color: white;
            border: 1px solid #e0e8f0;
            border-radius: 6px;
            padding: 6px;
            font-size: 10pt;
        }
        QLineEdit:focus {
            border-color: #c9d8e8;
        }
        QTabWidget::pane {
            border: 1px solid #e0e8f0;
            border-radius: 8px;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #f0f4f8;
            border: 1px solid #e0e8f0;
            border-radius: 8px 8px 0 0;
            padding: 8px 15px;
            font-size: 10pt;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
        }
        QTabBar::tab:hover {
            background-color: #e0e8f0;
        }
        QCheckBox {
            font-size: 10pt;
        }
        QLabel {
            font-size: 10pt;
        }
        QMessageBox {
            background-color: white;
            border: 1px solid #e0e8f0;
            border-radius: 8px;
        }""")
    
    def update_service_list(self):
        """更新服务列表"""
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
            if service.allow_all:
                perms_info.append("全选")
            else:
                if service.allow_upload:
                    perms_info.append("上传")
                if service.allow_delete:
                    perms_info.append("删除")
                if service.allow_search:
                    perms_info.append("搜索")
            perms_text = ", ".join(perms_info) if perms_info else ""
            
            # 创建树项
            item = QTreeWidgetItem([service.name, service.port, service.status, auth_info, perms_text, service.serve_path])
            self.service_tree.addTopLevelItem(item)
    
    def add_service(self):
        """添加新服务"""
        dialog = DufsServiceDialog(self)
        if dialog.exec_():
            self.services.append(dialog.service)
            self.update_service_list()
    
    def edit_service(self, item=None, column=None):
        """编辑选中的服务"""
        if not item:
            selected_items = self.service_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择要编辑的服务")
                return
            selected_item = selected_items[0]
            index = self.service_tree.indexOfTopLevelItem(selected_item)
        else:
            index = self.service_tree.indexOfTopLevelItem(item)
        
        service = self.services[index]
        dialog = DufsServiceDialog(self, service=service, edit_index=index)
        if dialog.exec_():
            # 保存服务当前状态（是否运行中）
            was_running = service.status == "运行中"
            
            # 更新服务
            self.services[index] = dialog.service
            self.update_service_list()
            
            # 如果服务之前是运行中的，询问是否重新启动
            if was_running:
                if QMessageBox.question(self, "提示", "服务已更新，是否重新启动服务？") == QMessageBox.Yes:
                    self.start_service(index)
    
    def delete_service(self):
        """删除选中的服务"""
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的服务")
            return
        
        selected_item = selected_items[0]
        index = self.service_tree.indexOfTopLevelItem(selected_item)
        service = self.services[index]
        
        # 如果服务正在运行，先停止
        if service.status == "运行中":
            self.stop_service(index)
        
        # 确认删除
        if QMessageBox.question(self, "提示", f"确定要删除服务 '{service.name}' 吗？") == QMessageBox.Yes:
            del self.services[index]
            self.update_service_list()
    
    def start_service(self, index=None):
        """启动选中的服务"""
        if index is None:
            selected_items = self.service_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择要启动的服务")
                return
            selected_item = selected_items[0]
            index = self.service_tree.indexOfTopLevelItem(selected_item)
        
        service = self.services[index]
        
        # 常用端口列表（需要屏蔽的端口）
        blocked_ports = [
            80, 443, 22, 21, 23, 53, 135, 137, 138, 139, 445, 1433, 1434, 3389, 1521,
            8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8888, 9090,
            3306, 5432, 6379, 27017, 11211, 9200, 9300,
            6666, 6667, 6668, 6669, 6697, 10808, 10809, 10810,
            3000, 3001, 4000, 4001, 5000, 5001, 6000, 6001, 7000, 7001, 9000, 9001,
            1080, 8080, 8081, 3128, 10808,
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
            QMessageBox.critical(
                self,
                "错误",
                f"端口 {original_port} 不可用，尝试了20个端口（{original_port}-{original_port+19}）都不可用。\n" +
                f"以下端口被占用或屏蔽: {', '.join(map(str, used_ports))}\n" +
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
                QMessageBox.critical(self, "错误", error_msg)
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
            QMessageBox.critical(self, "错误", error_msg)
    
    def stop_service(self, index=None):
        """停止选中的服务"""
        if index is None:
            selected_items = self.service_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择要停止的服务")
                return
            selected_item = selected_items[0]
            index = self.service_tree.indexOfTopLevelItem(selected_item)
        
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
            self.addr_edit.setText("")
    
    def monitor_service(self, service, index):
        """监控服务运行状态"""
        while service.process:
            if service.process.poll() is not None:
                service.status = "未运行"
                service.process = None
                # 使用信号或定时器在主线程更新UI
                QTimer.singleShot(0, lambda: self.update_service_list())
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
            selected_item = selected_items[0]
            index = self.service_tree.indexOfTopLevelItem(selected_item)
            self.refresh_address(index)
    
    def browser_access(self):
        """用浏览器访问服务"""
        selected_items = self.service_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要访问的服务")
            return
        
        selected_item = selected_items[0]
        index = self.service_tree.indexOfTopLevelItem(selected_item)
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
        """检查端口是否可用"""
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
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()
        
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
        start_action.triggered.connect(self.start_service)
        menu.addAction(start_action)
        
        # 停止服务
        stop_action = QAction("停止服务", self)
        stop_action.triggered.connect(self.stop_service)
        menu.addAction(stop_action)
        
        menu.addSeparator()
        
        # 编辑服务
        edit_action = QAction("编辑服务", self)
        edit_action.triggered.connect(self.edit_service)
        menu.addAction(edit_action)
        
        # 删除服务
        delete_action = QAction("删除服务", self)
        delete_action.triggered.connect(self.delete_service)
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
        
        # 关闭主窗口
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ICON.ICO"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = DufsMultiGUI()
    window.show()
    sys.exit(app.exec_())