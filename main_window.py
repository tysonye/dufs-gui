"""主窗口文件"""

import os
import subprocess
import threading
import time
import re
import webbrowser

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QMenu, QAction,
    QMessageBox, QDialog, QSystemTrayIcon, QStyle, QStatusBar, QTableWidget,
    QPlainTextEdit, QTableWidgetItem, QSizePolicy, QGraphicsDropShadowEffect,
    QProgressBar, QHeaderView
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QIcon, QFont

from constants import AppConstants, GLOBAL_STYLESHEET
from config_manager import ConfigManager
from service import DufsService, ServiceStatus
from service_manager import ServiceManager
from log_manager import LogManager
from log_window import LogWindow
from service_dialog import DufsServiceDialog
from tray_manager import TrayManager

class MainWindow(QMainWindow):
    """主窗口类"""

    # 信号定义
    update_service_tree_signal = pyqtSignal()
    update_address_fields_signal = pyqtSignal(str, str)
    update_progress_signal = pyqtSignal(int)  # 更新进度条信号
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DufsGUI - 多服务管理")
        self.setMinimumSize(AppConstants.MIN_WINDOW_WIDTH, AppConstants.MIN_WINDOW_HEIGHT)
        
        # 设置程序标题栏图标
        from constants import get_resource_path
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 应用全局样式表
        self.setStyleSheet(GLOBAL_STYLESHEET)

        # 设置全局字体
        self._setup_fonts()

        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化服务管理器
        self.manager = ServiceManager()
        
        # 初始化日志窗口
        self.log_window = None
        
        # 初始化日志管理器
        self.log_manager = LogManager(self)
        
        # 连接信号
        self.update_service_tree_signal.connect(self.update_service_tree)
        self.update_address_fields_signal.connect(self._update_address_fields_ui)
        
        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(*AppConstants.MAIN_LAYOUT_MARGINS)
        main_layout.setSpacing(AppConstants.MAIN_LAYOUT_SPACING)
        
        # 添加服务管理区域
        self._add_service_management(main_layout)
        
        # 初始化状态栏（包含进度条）
        self._init_status_bar(main_layout)
        
        # 加载配置
        self._load_config()
        
        # 初始化托盘管理器
        self.tray_manager = TrayManager(self)

        # 为关键区域添加阴影效果
        self._setup_shadows()

    def _setup_fonts(self):
        """优化全局字体排版"""
        # 使用微软雅黑作为默认字体
        app_font = QFont("Microsoft YaHei", 10)
        app_font.setHintingPreference(QFont.PreferFullHinting)
        self.setFont(app_font)

    def _add_shadow(self, widget, blur_radius=12, offset=(0, 2), color=(0, 0, 0, 40)):
        """为任意widget添加专业阴影效果"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setOffset(offset[0], offset[1])
        shadow.setColor(QColor(color[0], color[1], color[2], color[3]))
        widget.setGraphicsEffect(shadow)

    def _setup_shadows(self):
        """为关键区域设置阴影效果"""
        # 延迟设置阴影，确保widget已创建
        QTimer.singleShot(100, self._apply_shadows)

    def _apply_shadows(self):
        """应用阴影到具体组件"""
        # 为服务列表区域添加阴影
        if hasattr(self, 'service_table'):
            service_group = self.service_table.parentWidget()
            if service_group:
                self._add_shadow(service_group, blur_radius=10, offset=(0, 2), color=(0, 0, 0, 30))

        # 为地址区域添加阴影
        if hasattr(self, 'local_addr_edit'):
            access_group = self.local_addr_edit.parentWidget()
            if access_group and isinstance(access_group, QGroupBox):
                self._add_shadow(access_group, blur_radius=10, offset=(0, 2), color=(0, 0, 0, 30))

    def _add_service_management(self, layout: QVBoxLayout) -> None:
        """添加服务管理区域"""
        # 顶部操作按钮
        top_button_layout = QHBoxLayout()
        top_button_layout.setSpacing(10)

        # 左侧按钮 - 服务管理
        self.add_btn = QPushButton("添加服务")
        self.add_btn.setObjectName("InfoBtn")
        _ = self.add_btn.clicked.connect(self._add_service)
        top_button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑服务")
        self.edit_btn.setObjectName("InfoBtn")
        _ = self.edit_btn.clicked.connect(self._edit_service)
        top_button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除服务")
        self.delete_btn.setObjectName("StopBtn")
        _ = self.delete_btn.clicked.connect(self._delete_service)
        top_button_layout.addWidget(self.delete_btn)

        # 间隔
        top_button_layout.addSpacing(30)

        # 中间按钮 - 共享控制
        self.start_btn = QPushButton("启动内网共享")
        self.start_btn.setObjectName("StartBtn")
        _ = self.start_btn.clicked.connect(self._start_service)
        top_button_layout.addWidget(self.start_btn)

        self.start_public_btn = QPushButton("启动公网共享")
        self.start_public_btn.setObjectName("PublicBtn")
        _ = self.start_public_btn.clicked.connect(self._start_public_access)
        top_button_layout.addWidget(self.start_public_btn)

        self.stop_btn = QPushButton("停止共享服务")
        self.stop_btn.setObjectName("StopBtn")
        _ = self.stop_btn.clicked.connect(self._stop_service)
        top_button_layout.addWidget(self.stop_btn)

        # 右侧按钮
        top_button_layout.addStretch()

        self.log_window_btn = QPushButton("显示日志窗口")
        _ = self.log_window_btn.clicked.connect(self._open_log_window)
        top_button_layout.addWidget(self.log_window_btn)

        self.exit_btn = QPushButton("关闭程序")
        _ = self.exit_btn.clicked.connect(self._on_exit)
        top_button_layout.addWidget(self.exit_btn)

        layout.addLayout(top_button_layout)

        # 已配置服务区域
        service_group = QGroupBox()
        service_layout = QVBoxLayout(service_group)

        # 服务列表（使用表格控件）
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(5)
        self.service_table.setHorizontalHeaderLabels(["服务名称", "端口", "状态", "公网访问", "详情"])
        self.service_table.setColumnWidth(0, 120)
        self.service_table.setColumnWidth(1, 60)
        self.service_table.setColumnWidth(2, 80)
        self.service_table.setColumnWidth(3, 80)
        # 详情列使用拉伸模式，自动填充剩余空间
        self.service_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        # 设置表格属性
        self.service_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.service_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.service_table.setSelectionMode(QTableWidget.SingleSelection)

        # 设置上下文菜单和信号连接
        self.service_table.setContextMenuPolicy(Qt.CustomContextMenu)
        _ = self.service_table.customContextMenuRequested.connect(self._show_service_context_menu)
        _ = self.service_table.itemDoubleClicked.connect(self._on_service_double_clicked)
        _ = self.service_table.selectionModel().selectionChanged.connect(self._on_service_selection_changed, Qt.DirectConnection)
        service_layout.addWidget(self.service_table)

        layout.addWidget(service_group)

        # 访问地址区域
        access_group = QGroupBox()
        access_layout = QVBoxLayout(access_group)

        # 本地访问地址
        local_access_layout = QHBoxLayout()
        local_access_layout.addWidget(QLabel("访问地址:"))
        self.local_addr_edit = QLineEdit()
        self.local_addr_edit.setReadOnly(True)
        self.local_addr_edit.setMinimumWidth(400)
        local_access_layout.addWidget(self.local_addr_edit)

        self.copy_local_btn = QPushButton("复制")
        _ = self.copy_local_btn.clicked.connect(self._copy_local_addr)
        local_access_layout.addWidget(self.copy_local_btn)

        self.browse_local_btn = QPushButton("浏览器访问")
        _ = self.browse_local_btn.clicked.connect(self._browse_local_addr)
        local_access_layout.addWidget(self.browse_local_btn)

        access_layout.addLayout(local_access_layout)

        # 公网访问地址
        public_access_layout = QHBoxLayout()
        public_access_layout.addWidget(QLabel("公网地址:"))
        self.public_addr_edit = QLineEdit()
        self.public_addr_edit.setReadOnly(True)
        self.public_addr_edit.setMinimumWidth(400)
        public_access_layout.addWidget(self.public_addr_edit)

        self.copy_public_btn = QPushButton("复制")
        _ = self.copy_public_btn.clicked.connect(self._copy_public_addr)
        public_access_layout.addWidget(self.copy_public_btn)

        self.browse_public_btn = QPushButton("浏览器访问")
        _ = self.browse_public_btn.clicked.connect(self._browse_public_addr)
        public_access_layout.addWidget(self.browse_public_btn)

        access_layout.addLayout(public_access_layout)

        layout.addWidget(access_group)
    
    def _copy_local_addr(self):
        """复制本地地址"""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.local_addr_edit.text())
        QMessageBox.information(self, "提示", "本地地址已复制到剪贴板")
    
    def _browse_local_addr(self):
        """浏览器访问本地地址"""
        addr = self.local_addr_edit.text()
        if addr:
            webbrowser.open(addr)
        else:
            QMessageBox.warning(self, "警告", "本地地址为空，请先启动服务")
    
    def _copy_public_addr(self):
        """复制公网地址"""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.public_addr_edit.text())
        QMessageBox.information(self, "提示", "公网地址已复制到剪贴板")
    
    def _browse_public_addr(self):
        """浏览器访问公网地址"""
        addr = self.public_addr_edit.text()
        if addr:
            webbrowser.open(addr)
        else:
            QMessageBox.warning(self, "警告", "公网地址为空，请先启动公网访问")
    
    def _init_status_bar(self, layout):
        """初始化状态栏（包含进度条）"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.hide()  # 初始隐藏
        self.progress_bar.setMaximumWidth(200)  # 限制进度条宽度

        # 创建进度条标签
        self.progress_label = QLabel("")

        # 添加到状态栏
        self.status_bar.addWidget(self.progress_label)
        self.status_bar.addWidget(self.progress_bar)

        # 初始化进度条定时器
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.progress_value = 0
        self.is_operation_in_progress = False

        # 连接进度条更新信号
        self.update_progress_signal.connect(self._set_progress_value)

    def _start_progress(self, operation_name="操作"):
        """开始进度条动画"""
        self.is_operation_in_progress = True
        self.progress_label.setText(f"{operation_name}中...")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_value = 0
        self.progress_timer.start(50)  # 每50ms更新一次
        self._set_buttons_enabled(False)

    def _stop_progress(self, success=True):
        """停止进度条动画"""
        self.progress_timer.stop()
        self.progress_bar.setValue(100 if success else 0)
        if success:
            self.progress_label.setText("完成")
            # 延迟隐藏进度条
            QTimer.singleShot(1000, self._hide_progress)
        else:
            self.progress_label.setText("失败")
            self.progress_bar.hide()
        self.is_operation_in_progress = False
        self._set_buttons_enabled(True)

    def _hide_progress(self):
        """隐藏进度条"""
        self.progress_bar.hide()
        self.progress_label.setText("")

    def _update_progress(self):
        """更新进度条"""
        if self.progress_value < 80:
            self.progress_value += 5
            self.progress_bar.setValue(self.progress_value)

    def _set_progress_value(self, value):
        """设置进度条值（线程安全）"""
        self.progress_value = value
        self.progress_bar.setValue(value)

    def _set_buttons_enabled(self, enabled):
        """设置按钮启用/禁用状态"""
        self.start_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.start_public_btn.setEnabled(enabled)
        self.add_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)

    def _update_status_bar(self):
        """更新状态栏信息"""
        # 状态栏现在包含进度条，不需要额外更新
        pass
    
    def _load_config(self):
        """加载配置"""
        try:
            services_config = self.config_manager.get_services()
            for service_config in services_config:
                service = DufsService(
                    name=str(service_config.get('name', '默认服务')),
                    serve_path=str(service_config.get('serve_path', '.')),
                    port=str(service_config.get('port', '5000')),
                    bind=str(service_config.get('bind', ''))
                )
                service.allow_upload = service_config.get('allow_upload', False)
                service.allow_delete = service_config.get('allow_delete', False)
                service.allow_search = service_config.get('allow_search', False)
                service.allow_archive = service_config.get('allow_archive', False)
                service.allow_all = service_config.get('allow_all', False)
                # 加载认证配置
                service.auth_user = service_config.get('auth_user', '')
                service.auth_pass = service_config.get('auth_pass', '')
                # 连接服务状态更新信号
                service.status_updated.connect(self._on_service_status_updated)
                # 检查并自动更换重复的服务名称
                unique_name = self._generate_unique_service_name(service.name)
                service.name = unique_name
                # 检查并自动更换重复的端口
                try:
                    current_port = int(service.port)
                    # 检查是否与其他已加载的服务端口冲突
                    conflict = False
                    for existing_service in self.manager.services:
                        if int(existing_service.port) == current_port:
                            conflict = True
                            break
                    if conflict:
                        # 端口冲突，查找可用端口
                        new_port = self.manager.find_available_port(current_port)
                        service.port = str(new_port)
                    else:
                        # 添加到已分配端口
                        self.manager._allocated_ports.add(current_port)
                except ValueError:
                    # 端口无效，使用默认端口
                    port = self.manager.find_available_port(5001)
                    service.port = str(port)
                self.manager.add_service(service)
            self.update_service_tree()
            # 如果有名称或端口被更改，保存配置
            self._save_config()
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def _save_config(self):
        """保存配置"""
        try:
            services_config = []
            for service in self.manager.services:
                service_config = {
                    'name': service.name,
                    'serve_path': service.serve_path,
                    'port': service.port,
                    'bind': service.bind,
                    'allow_upload': service.allow_upload,
                    'allow_delete': service.allow_delete,
                    'allow_search': service.allow_search,
                    'allow_archive': service.allow_archive,
                    'allow_all': service.allow_all,
                    'auth_user': getattr(service, 'auth_user', ''),
                    'auth_pass': getattr(service, 'auth_pass', '')
                }
                services_config.append(service_config)
            self.config_manager.set_services(services_config)
            return True
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            return False
    
    def update_service_tree(self):
        """更新服务表格"""
        try:
            # 保存当前选中的行
            selected_row = -1
            selected_items = self.service_table.selectedItems()
            if selected_items:
                selected_row = selected_items[0].row()

            # 清空表格
            self.service_table.setRowCount(0)

            # 添加服务到表格
            for service in self.manager.services:
                row_position = self.service_table.rowCount()
                self.service_table.insertRow(row_position)

                # 服务名称
                name_item = QTableWidgetItem(service.name)
                self.service_table.setItem(row_position, 0, name_item)

                # 端口
                port_item = QTableWidgetItem(service.port)
                self.service_table.setItem(row_position, 1, port_item)

                # 状态
                status_item = QTableWidgetItem(service.status)
                from PyQt5.QtGui import QColor
                from constants import AppConstants
                status_item.setForeground(QColor(AppConstants.STATUS_COLORS.get(service.status, "#95a5a6")))
                self.service_table.setItem(row_position, 2, status_item)

                # 公网访问
                public_access = "已启用" if service.public_access_status == "running" else "未启用"
                public_item = QTableWidgetItem(public_access)
                self.service_table.setItem(row_position, 3, public_item)

                # 详情 - 显示路径和权限摘要
                perms = []
                if service.allow_all:
                    perms.append("全部")
                else:
                    if service.allow_upload:
                        perms.append("上传")
                    if service.allow_delete:
                        perms.append("删除")
                    if service.allow_search:
                        perms.append("搜索")
                    if service.allow_archive:
                        perms.append("存档")
                perms_str = ",".join(perms) if perms else "只读"
                detail_text = f"{service.serve_path} | {perms_str}"
                detail_item = QTableWidgetItem(detail_text)
                detail_item.setToolTip(f"路径: {service.serve_path}\n权限: {perms_str}")
                self.service_table.setItem(row_position, 4, detail_item)

            # 恢复选中状态
            if 0 <= selected_row < self.service_table.rowCount():
                self.service_table.selectRow(selected_row)

            # 更新状态统计
            running_count = len([s for s in self.manager.services if s.status == ServiceStatus.RUNNING])

            # 更新状态栏
            self._update_status_bar()
        except Exception as e:
            print(f"更新服务表格失败: {str(e)}")
    
    def _generate_unique_service_name(self, base_name: str, exclude_index: int = None) -> str:
        """生成唯一的服务名称

        Args:
            base_name: 基础名称
            exclude_index: 排除的服务索引（编辑时使用）

        Returns:
            str: 唯一的名称
        """
        # 获取所有现有服务名称
        existing_names = []
        for i, service in enumerate(self.manager.services):
            if exclude_index is None or i != exclude_index:
                existing_names.append(service.name)

        # 如果名称不重复，直接返回
        if base_name not in existing_names:
            return base_name

        # 尝试添加数字后缀
        counter = 1
        while True:
            new_name = f"{base_name}_{counter}"
            if new_name not in existing_names:
                return new_name
            counter += 1
            # 防止无限循环
            if counter > 1000:
                return f"{base_name}_{int(time.time())}"

    def _add_service(self):
        """添加服务"""
        dialog = DufsServiceDialog(parent=self, existing_services=self.manager.services)
        if dialog.exec_() == QDialog.Accepted:
            # 自动更换重复的服务名称（静默处理，不提示用户）
            original_name = dialog.service.name
            unique_name = self._generate_unique_service_name(original_name)
            dialog.service.name = unique_name

            # 检查端口是否与其他服务冲突
            try:
                current_port = int(dialog.service.port)
                # 检查是否与其他服务端口冲突
                conflict_service = None
                for other_service in self.manager.services:
                    if int(other_service.port) == current_port:
                        conflict_service = other_service
                        break

                if conflict_service:
                    # 端口冲突，查找可用端口
                    new_port = self.manager.find_available_port(current_port)
                    dialog.service.port = str(new_port)
                else:
                    # 查找可用端口（会自动跳过黑名单端口和被占用端口）
                    new_port = self.manager.find_available_port(current_port)
                    dialog.service.port = str(new_port)
            except ValueError:
                # 端口无效，使用默认端口
                port = self.manager.find_available_port(5001)
                dialog.service.port = str(port)

            # 连接服务状态更新信号
            dialog.service.status_updated.connect(self._on_service_status_updated)

            # 添加服务
            self.manager.add_service(dialog.service)
            self.update_service_tree()
            self._save_config()
    
    def _edit_service(self):
        """编辑服务"""
        selected_items = self.service_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要编辑的服务")
            return
        
        # 获取选中行的索引
        row = selected_items[0].row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            # 记录服务的当前运行状态
            was_running = service.status == ServiceStatus.RUNNING
            # 记录公网服务的当前状态
            was_public_running = hasattr(service, 'public_access_status') and service.public_access_status == "running"
            # 记录旧端口号（在对话框打开前记录，因为对话框可能修改端口号）
            old_port = int(service.port)
            # 记录原始配置数据，用于对比是否有变化（使用拷贝避免引用问题）
            import copy
            original_data = {
                'name': str(service.name),
                'serve_path': str(service.serve_path),
                'port': str(service.port),
                'bind': str(service.bind),
                'allow_upload': bool(service.allow_upload),
                'allow_delete': bool(service.allow_delete),
                'allow_search': bool(service.allow_search),
                'allow_archive': bool(service.allow_archive),
                'allow_all': bool(service.allow_all),
                'auth_user': str(getattr(service, 'auth_user', '')),
                'auth_pass': str(getattr(service, 'auth_pass', ''))
            }
            
            dialog = DufsServiceDialog(parent=self, service=service, edit_index=row, existing_services=self.manager.services)
            if dialog.exec_() == QDialog.Accepted:
                # 自动更换重复的服务名称（静默处理，不提示用户）
                original_name = dialog.service.name
                unique_name = self._generate_unique_service_name(original_name, exclude_index=row)
                dialog.service.name = unique_name

                # 检查配置是否有变化
                has_changes = (
                    original_data['name'] != dialog.service.name or
                    original_data['serve_path'] != dialog.service.serve_path or
                    original_data['port'] != dialog.service.port or
                    original_data['bind'] != dialog.service.bind or
                    original_data['allow_upload'] != dialog.service.allow_upload or
                    original_data['allow_delete'] != dialog.service.allow_delete or
                    original_data['allow_search'] != dialog.service.allow_search or
                    original_data['allow_archive'] != dialog.service.allow_archive or
                    original_data['allow_all'] != dialog.service.allow_all or
                    original_data['auth_user'] != getattr(dialog.service, 'auth_user', '') or
                    original_data['auth_pass'] != getattr(dialog.service, 'auth_pass', '')
                )
                
                # 如果服务正在运行且有配置变化，先停止它
                if was_running and has_changes:
                    print(f"[调试] 检测到配置变化，准备重启服务: {service.name}")
                    # 停止公网服务
                    if was_public_running and hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                        try:
                            service.cloudflared_process.terminate()
                            service.cloudflared_process.wait(timeout=5)
                            service.cloudflared_process = None
                        except Exception as e:
                            print(f"终止cloudflared进程失败: {str(e)}")
                            service.cloudflared_process = None
                    
                    # 停止内网服务
                    if service.process:
                        try:
                            service.process.terminate()
                            service.process.wait(timeout=5)
                            service.process = None
                        except Exception as e:
                            print(f"终止服务进程失败: {str(e)}")
                            service.process = None
                    
                    # 强制更新服务状态为已停止
                    with service.lock:
                        service.status = ServiceStatus.STOPPED
                    service.status_updated.emit()
                    if hasattr(service, 'public_access_status'):
                        service.public_access_status = "stopped"
                        service.status_updated.emit()
                
                # 释放旧端口
                try:
                    self.manager.release_allocated_port(old_port)
                except ValueError:
                    pass

                # 检查端口是否与其他服务冲突
                try:
                    current_port = int(dialog.service.port)
                    conflict_service = None
                    for i, other_service in enumerate(self.manager.services):
                        if i != row:
                            if int(other_service.port) == current_port:
                                conflict_service = other_service
                                break

                    if conflict_service:
                        new_port = self.manager.find_available_port(current_port)
                        dialog.service.port = str(new_port)
                    else:
                        new_port = self.manager.find_available_port(current_port)
                        dialog.service.port = str(new_port)
                except ValueError:
                    port = self.manager.find_available_port(5001)
                    dialog.service.port = str(port)
                
                # 连接服务状态更新信号
                dialog.service.status_updated.connect(self._on_service_status_updated)
                
                # 更新服务
                self.manager.edit_service(row, dialog.service)
                self.update_service_tree()
                self._save_config()
                
                # 如果服务之前在运行且有配置变化，重启它
                print(f"[调试] 检查重启条件: was_running={was_running}, has_changes={has_changes}")
                if was_running and has_changes:
                    print(f"[调试] 开始重启服务: {dialog.service.name}")
                    updated_service = self.manager.services[row]
                    print(f"[调试] 服务状态: {updated_service.status}, 进程: {updated_service.process}")
                    import time
                    time.sleep(0.1)
                    import threading
                    print(f"[调试] 启动服务线程...")
                    threading.Thread(target=updated_service.start, args=(self.log_manager,), daemon=True).start()
                    if was_public_running:
                        time.sleep(1)
                        threading.Thread(target=updated_service.start_public_access, args=(self.log_manager,), daemon=True).start()
    
    def _delete_service(self):
        """删除服务"""
        selected_items = self.service_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要删除的服务")
            return
        
        # 获取选中行的索引
        row = selected_items[0].row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            
            # 弹出确认对话框
            if QMessageBox.question(self, "确认", f"确定要删除服务 '{service.name}' 吗？\n\n删除前将自动停止服务。") == QMessageBox.Yes:
                # 自动停止服务
                if service.status == ServiceStatus.RUNNING:
                    # 停止公网服务
                    if hasattr(service, 'public_access_status') and service.public_access_status == "running":
                        try:
                            if hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                                service.cloudflared_process.terminate()
                                service.cloudflared_process.wait(timeout=5)
                        except Exception as e:
                            print(f"终止cloudflared进程失败: {str(e)}")
                    
                    # 停止内网服务
                    if hasattr(service, 'process') and service.process:
                        try:
                            service.process.terminate()
                            service.process.wait(timeout=5)
                        except Exception as e:
                            print(f"终止服务进程失败: {str(e)}")
                
                # 删除服务
                self.manager.remove_service(row)
                self.update_service_tree()
                self._save_config()
                # 清空地址编辑框
                self.update_address_fields_signal.emit("", "")
                
                # 显示删除成功消息
                QMessageBox.information(self, "成功", f"服务 '{service.name}' 已成功删除")
    
    def _start_service(self):
        """启动内网共享"""
        if self.is_operation_in_progress:
            QMessageBox.warning(self, "警告", "有操作正在进行中，请稍后再试")
            return

        selected_items = self.service_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要启动内网共享的服务")
            return

        # 获取选中行的索引
        row = selected_items[0].row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            if service.status == ServiceStatus.RUNNING:
                QMessageBox.warning(self, "警告", "内网共享已经在运行中")
                return
            if service.status == ServiceStatus.STARTING:
                QMessageBox.warning(self, "警告", "内网共享正在启动中")
                return

            # 检查端口是否在黑名单中、与其他服务冲突或被占用
            try:
                current_port = int(service.port)

                # 检查是否与其他服务端口冲突（包括已停止的服务）
                conflict_service = None
                for i, other_service in enumerate(self.manager.services):
                    if i != row:  # 排除当前服务
                        if int(other_service.port) == current_port:
                            conflict_service = other_service
                            break

                if conflict_service:
                    # 端口冲突，需要更换
                    self.manager.release_allocated_port(current_port)
                    # 从当前端口+1开始查找可用端口
                    new_port = self.manager.find_available_port(current_port + 1)
                    QMessageBox.information(
                        self,
                        "端口已更换",
                        f"原端口 {current_port} 与服务 '{conflict_service.name}' 冲突，已自动更换为 {new_port}"
                    )
                    service.port = str(new_port)
                    self._save_config()
                else:
                    # 释放当前端口（如果已分配）
                    self.manager.release_allocated_port(current_port)
                    # 查找可用端口（会自动跳过黑名单端口和被占用端口）
                    new_port = self.manager.find_available_port(current_port)
                    if new_port != current_port:
                        # 端口已更换，提示用户
                        QMessageBox.information(
                            self,
                            "端口已更换",
                            f"原端口 {current_port} 为黑名单端口或已被占用，已自动更换为 {new_port}"
                        )
                        service.port = str(new_port)
                        self._save_config()
            except ValueError:
                QMessageBox.warning(self, "警告", f"服务端口无效: {service.port}")
                return
            except Exception as e:
                QMessageBox.warning(self, "警告", f"端口检查失败: {str(e)}")
                return

            # 启动进度条
            self._start_progress("启动内网共享")

            # 启动内网共享服务
            # 在新线程中启动服务
            import threading
            threading.Thread(target=service.start, args=(self.log_manager,), daemon=True).start()

            # 轮询服务状态，更新进度条
            def monitor_progress():
                import time
                max_wait = 100  # 最大等待10秒
                wait_count = 0
                while wait_count < max_wait:
                    time.sleep(0.1)
                    wait_count += 1

                    # 根据服务状态更新进度
                    if service.status == ServiceStatus.RUNNING:
                        # 服务已启动，完成进度条
                        self._stop_progress(success=True)
                        return
                    elif service.status == ServiceStatus.ERROR:
                        # 启动失败
                        self._stop_progress(success=False)
                        return
                    else:
                        # 更新进度条到80-95%
                        progress = min(80 + wait_count, 95)
                        self.update_progress_signal.emit(progress)

                # 超时
                self._stop_progress(success=False)

            # 延迟一点再开始监控，让服务有时间进入STARTING状态
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, monitor_progress)
    

    

    
    def _stop_service(self):
        """停止共享服务"""
        if self.is_operation_in_progress:
            QMessageBox.warning(self, "警告", "有操作正在进行中，请稍后再试")
            return

        selected_items = self.service_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要停止共享服务的服务")
            return

        # 获取选中行的索引
        row = selected_items[0].row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            if service.status == ServiceStatus.STOPPED and service.public_access_status != "running":
                QMessageBox.warning(self, "警告", "服务已经停止")
                return

            # 启动进度条
            self._start_progress("停止共享服务")

            # 停止共享服务
            # 在新线程中停止服务
            import threading
            threading.Thread(target=service.stop, args=(self.log_manager,), daemon=True).start()

            # 轮询服务状态，更新进度条
            def monitor_stop_progress():
                import time
                max_wait = 100  # 最大等待10秒
                wait_count = 0
                while wait_count < max_wait:
                    time.sleep(0.1)
                    wait_count += 1

                    # 根据服务状态更新进度
                    if service.status == ServiceStatus.STOPPED:
                        # 服务已停止，完成进度条
                        self._stop_progress(success=True)
                        return
                    elif service.status == ServiceStatus.ERROR:
                        # 停止失败
                        self._stop_progress(success=False)
                        return
                    else:
                        # 更新进度条到80-95%
                        progress = min(80 + wait_count, 95)
                        self.update_progress_signal.emit(progress)

                # 超时
                self._stop_progress(success=False)

            # 延迟一点再开始监控
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, monitor_stop_progress)
    

    
    def _start_public_access(self):
        """启动公网共享"""
        if self.is_operation_in_progress:
            QMessageBox.warning(self, "警告", "有操作正在进行中，请稍后再试")
            return

        selected_items = self.service_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要启动公网共享的服务")
            return

        # 获取选中行的索引
        row = selected_items[0].row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            if service.public_access_status == "running":
                QMessageBox.warning(self, "警告", "公网共享已经在运行中")
                return

            # 先检查并下载 cloudflared（在主线程中）
            from cloudflared_downloader import check_and_download_cloudflared
            if not check_and_download_cloudflared(self):
                # 用户取消或下载失败
                return

            # 启动进度条
            self._start_progress("启动公网共享")

            # 检查内网服务状态
            if service.status != ServiceStatus.RUNNING:
                # 先检查端口（包括与其他服务的冲突）
                try:
                    current_port = int(service.port)

                    # 检查是否与其他运行中的服务端口冲突
                    conflict_service = None
                    for other_service in self.manager.services:
                        if other_service != service and other_service.status == ServiceStatus.RUNNING:
                            if int(other_service.port) == current_port:
                                conflict_service = other_service
                                break

                    if conflict_service:
                        self.manager.release_allocated_port(current_port)
                        new_port = self.manager.find_available_port(current_port)
                        QMessageBox.information(
                            self,
                            "端口已更换",
                            f"原端口 {current_port} 与服务 '{conflict_service.name}' 冲突，已自动更换为 {new_port}"
                        )
                        service.port = str(new_port)
                        self._save_config()
                    else:
                        self.manager.release_allocated_port(current_port)
                        new_port = self.manager.find_available_port(current_port)
                        if new_port != current_port:
                            QMessageBox.information(
                                self,
                                "端口已更换",
                                f"原端口 {current_port} 为黑名单端口或已被占用，已自动更换为 {new_port}"
                            )
                            service.port = str(new_port)
                            self._save_config()
                except Exception as e:
                    self._stop_progress(success=False)
                    QMessageBox.warning(self, "警告", f"端口检查失败: {str(e)}")
                    return

                # 先启动内网服务，再启动公网服务
                # 在新线程中启动内网服务
                import threading
                threading.Thread(target=service.start, args=(self.log_manager,), daemon=True).start()

                # 监控内网服务启动，然后启动公网服务
                def monitor_internal_then_public():
                    import time
                    max_wait = 100
                    wait_count = 0

                    # 等待内网服务启动
                    while wait_count < max_wait:
                        time.sleep(0.1)
                        wait_count += 1
                        if service.status == ServiceStatus.RUNNING:
                            break
                        elif service.status == ServiceStatus.ERROR:
                            self._stop_progress(success=False)
                            return
                        else:
                            # 更新进度条到40-60%
                            progress = min(40 + wait_count // 2, 60)
                            self.update_progress_signal.emit(progress)

                    if service.status != ServiceStatus.RUNNING:
                        self._stop_progress(success=False)
                        return

                    # 启动公网服务
                    threading.Thread(target=service.start_public_access, args=(self.log_manager,), daemon=True).start()

                    # 轮询公网服务状态
                    wait_count = 0
                    while wait_count < max_wait:
                        time.sleep(0.1)
                        wait_count += 1

                        if service.public_access_status == "running":
                            self._stop_progress(success=True)
                            return
                        elif service.public_access_status == "error":
                            self._stop_progress(success=False)
                            return
                        else:
                            # 更新进度条到60-95%
                            progress = min(60 + wait_count, 95)
                            self.update_progress_signal.emit(progress)

                    # 超时
                    self._stop_progress(success=False)

                # 延迟一点再开始监控
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, monitor_internal_then_public)
            else:
                # 直接启动公网服务
                import threading
                threading.Thread(target=service.start_public_access, args=(self.log_manager,), daemon=True).start()

                # 监控公网服务启动
                def monitor_public_only():
                    import time
                    max_wait = 100
                    wait_count = 0
                    while wait_count < max_wait:
                        time.sleep(0.1)
                        wait_count += 1

                        if service.public_access_status == "running":
                            self._stop_progress(success=True)
                            return
                        elif service.public_access_status == "error":
                            self._stop_progress(success=False)
                            return
                        else:
                            # 更新进度条
                            progress = min(80 + wait_count, 95)
                            self.update_progress_signal.emit(progress)

                    # 超时
                    self._stop_progress(success=False)

                # 延迟一点再开始监控
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, monitor_public_only)
    

    

    

    
    def _stop_public_access(self):
        """停止公网共享"""
        selected_items = self.service_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要停止公网共享的服务")
            return
        
        # 获取选中行的索引
        row = selected_items[0].row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            if service.public_access_status != "running":
                QMessageBox.warning(self, "警告", "公网共享已经停止")
                return
            
            # 停止公网共享
            threading.Thread(target=service.stop_public_access, args=(self.log_manager,), daemon=True).start()
    

    
    def _update_address_fields(self, service: DufsService) -> None:
        """更新地址编辑框"""
        # 确保在UI线程中执行
        try:
            local_addr = str(service.local_addr)
            public_url = str(getattr(service, 'public_url', ''))
            # 触发地址编辑框更新信号
            self.update_address_fields_signal.emit(local_addr, public_url)
        except Exception as e:
            print(f"更新地址编辑框失败: {str(e)}")
    
    def _update_address_fields_ui(self, local_addr: str, public_addr: str) -> None:
        """更新地址编辑框UI"""
        try:
            self.local_addr_edit.setText(local_addr)
            self.public_addr_edit.setText(public_addr)
        except Exception as e:
            print(f"更新地址编辑框UI失败: {str(e)}")
    
    def _on_service_status_updated(self):
        """处理服务状态更新信号"""
        try:
            # 更新服务树
            self.update_service_tree_signal.emit()
            
            # 更新地址编辑框
            # 1. 优先更新当前选中的服务
            selected_items = self.service_table.selectedItems()
            if selected_items:
                row = selected_items[0].row()
                if 0 <= row < len(self.manager.services):
                    service = self.manager.services[row]
                    self._update_address_fields(service)
            else:
                # 2. 如果没有选中的服务，尝试找到刚刚启动的服务
                for service in self.manager.services:
                    if service.status == ServiceStatus.RUNNING and service.local_addr:
                        self._update_address_fields(service)
                        break
        except Exception as e:
            print(f"处理服务状态更新失败: {str(e)}")
    
    def _show_service_context_menu(self, position: QPoint) -> None:
        """显示服务上下文菜单"""
        # 获取选中项
        selected_items = self.service_table.selectedItems()
        if not selected_items:
            return
        
        # 创建菜单
        menu = QMenu()
        
        # 添加操作
        start_action = QAction("启动服务", self)
        start_action.triggered.connect(self._start_service)
        menu.addAction(start_action)
        
        start_public_action = QAction("启动公网访问", self)
        start_public_action.triggered.connect(self._start_public_access)
        menu.addAction(start_public_action)
        
        stop_action = QAction("停止服务", self)
        stop_action.triggered.connect(self._stop_service)
        menu.addAction(stop_action)
        
        menu.addSeparator()
        
        edit_action = QAction("编辑服务", self)
        edit_action.triggered.connect(self._edit_service)
        menu.addAction(edit_action)
        
        delete_action = QAction("删除服务", self)
        delete_action.triggered.connect(self._delete_service)
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.service_table.viewport().mapToGlobal(position))
    
    def _on_service_double_clicked(self, item: QTableWidgetItem) -> None:
        """服务双击事件 - 显示服务详情信息面板"""
        row = item.row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            # 显示服务详情信息面板（只读，不编辑）
            from service_info_dialog import ServiceInfoDialog
            dialog = ServiceInfoDialog(parent=self, service=service)
            dialog.exec_()
    
    def _on_service_selection_changed(self, selected, deselected) -> None:
        """服务选择变更事件"""
        try:
            # 获取当前选中的行
            selected_rows = set()
            for index in selected.indexes():
                selected_rows.add(index.row())
            
            if selected_rows:
                # 获取第一个选中的行
                row = next(iter(selected_rows))
                if 0 <= row < len(self.manager.services):
                    service = self.manager.services[row]
                    # 更新地址编辑框
                    self._update_address_fields(service)
        except Exception as e:
            print(f"服务选择变更处理失败: {str(e)}")
    
    def _open_log_window(self):
        """打开日志窗口"""
        if not self.log_window:
            self.log_window = LogWindow(self)
        
        # 为每个服务创建独立的日志标签页（如果不存在）
        from PyQt5.QtWidgets import QPlainTextEdit
        service_tab_indices = {}
        
        # 为每个服务创建标签页
        for service in self.manager.services:
            service_name = service.name
            # 查找服务对应的标签页
            service_tab_index = -1
            for i in range(self.log_window.log_tabs.count()):
                if self.log_window.log_tabs.tabText(i) == service_name:
                    service_tab_index = i
                    break
            
            # 如果标签页不存在，创建新的
            if service_tab_index == -1:
                log_widget = QPlainTextEdit()
                log_widget.setReadOnly(True)
                log_widget.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11px;")
                self.log_window.add_log_tab(service_name, log_widget)
                service_tab_index = self.log_window.log_tabs.count() - 1
            
            service_tab_indices[service_name] = service_tab_index
        
        # 将历史日志添加到对应的标签页
        for log_message in self.log_manager.log_buffer:
            # 尝试提取服务名称
            import re
            # 匹配实际的日志格式：[timestamp] [level] [service_name] message
            service_match = re.search(r'\[\d{2}:\d{2}:\d{2}\] \[(INFO|ERROR)\] \[(.*?)\]', log_message)
            if service_match:
                service_name = service_match.group(2)
                # 检查服务名称是否有效
                if service_name and service_name != "全局日志" and service_name in service_tab_indices:
                    # 添加到服务对应的标签页
                    self.log_window.append_log(service_tab_indices[service_name], log_message)
        
        self.log_window.show()
    
    def closeEvent(self, event):
        """关闭事件"""
        # 最小化到托盘，而不是真正关闭
        event.ignore()
        self.hide()
        # 显示托盘消息
        if hasattr(self, 'tray_manager'):
            self.tray_manager.show_message("DufsGUI", "程序已最小化到托盘")
    
    def _on_exit(self):
        """真正退出程序"""
        # 停止所有服务
        for service in self.manager.services:
            if service.process:
                try:
                    service.process.terminate()
                    service.process.wait(timeout=2)
                except Exception:
                    pass
            if hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                try:
                    service.cloudflared_process.terminate()
                    service.cloudflared_process.wait(timeout=2)
                except Exception:
                    pass
        
        # 保存配置
        self._save_config()
        
        # 关闭日志窗口
        if self.log_window:
            self.log_window.close()
        
        # 隐藏托盘图标
        if hasattr(self, 'tray_manager'):
            self.tray_manager.hide()
        
        # 真正退出程序
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
