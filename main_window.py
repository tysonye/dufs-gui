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
    QHeaderView, QProgressBar
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QIcon, QFont
from PyQt5.QtWidgets import QApplication

from constants import AppConstants
from config_manager import ConfigManager
from service import DufsService, ServiceStatus
from service_manager import ServiceManager
from log_manager import LogManager
from log_window import LogWindow
from service_dialog import DufsServiceDialog
from tray_manager import TrayManager
from design_system import DesignSystem, AnimatedButton, StatusBadge

class MainWindow(QMainWindow):
    """主窗口类"""

    # 信号定义
    update_service_tree_signal = pyqtSignal()
    update_address_fields_signal = pyqtSignal(str, str)
    update_progress_signal = pyqtSignal(int, str)  # 进度值, 进度文本
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DufsGUI - 多服务管理")
        self.setMinimumSize(AppConstants.MIN_WINDOW_WIDTH, AppConstants.MIN_WINDOW_HEIGHT)
        
        # 设置程序标题栏图标
        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 应用设计系统的全局样式表
        self.setStyleSheet(DesignSystem.get_global_stylesheet())

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
        self.update_progress_signal.connect(self._update_progress_ui)
        
        # 初始化服务启动状态标志
        self._service_starting = False
        
        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(*AppConstants.MAIN_LAYOUT_MARGINS)
        main_layout.setSpacing(AppConstants.MAIN_LAYOUT_SPACING)
        
        # 添加服务管理区域
        self._add_service_management(main_layout)
        
        # 初始化菜单栏
        self._init_menu_bar()
        
        # 初始化状态栏
        self._init_status_bar()
        
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
        self.add_btn = AnimatedButton("添加服务")
        self.add_btn.setObjectName("InfoBtn")
        self.add_btn.clicked.connect(self._add_service)
        top_button_layout.addWidget(self.add_btn)

        self.edit_btn = AnimatedButton("编辑服务")
        self.edit_btn.setObjectName("InfoBtn")
        self.edit_btn.clicked.connect(self._edit_service)
        top_button_layout.addWidget(self.edit_btn)

        self.delete_btn = AnimatedButton("删除服务")
        self.delete_btn.setObjectName("StopBtn")
        self.delete_btn.clicked.connect(self._delete_service)
        top_button_layout.addWidget(self.delete_btn)

        # 间隔
        top_button_layout.addSpacing(30)

        # 中间按钮 - 共享控制
        self.start_btn = AnimatedButton("启动内网共享")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.clicked.connect(self._start_service)
        top_button_layout.addWidget(self.start_btn)

        self.start_public_btn = AnimatedButton("启动公网共享")
        self.start_public_btn.setObjectName("PublicBtn")
        self.start_public_btn.clicked.connect(self._start_public_access)
        top_button_layout.addWidget(self.start_public_btn)

        self.stop_btn = AnimatedButton("停止共享服务")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.clicked.connect(self._stop_service)
        top_button_layout.addWidget(self.stop_btn)

        # 右侧按钮
        top_button_layout.addStretch()

        self.log_window_btn = QPushButton("显示日志窗口")
        self.log_window_btn.clicked.connect(self._open_log_window)
        top_button_layout.addWidget(self.log_window_btn)

        self.exit_btn = QPushButton("关闭程序")
        self.exit_btn.clicked.connect(self._on_exit)
        top_button_layout.addWidget(self.exit_btn)

        layout.addLayout(top_button_layout)

        # 已配置服务区域
        service_group = QGroupBox()
        service_layout = QVBoxLayout(service_group)

        # 服务列表（使用表格控件）
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(5)
        self.service_table.setHorizontalHeaderLabels(["服务名称", "端口", "状态", "公网访问", "详情"])
        # 设置各列宽度，详情列占用更多空间
        self.service_table.setColumnWidth(0, 200)  # 服务名称
        self.service_table.setColumnWidth(1, 60)   # 端口
        self.service_table.setColumnWidth(2, 125)   # 状态
        self.service_table.setColumnWidth(3, 125)   # 公网访问
        self.service_table.setColumnWidth(4, 470)  # 详情列固定宽度

        # 设置表格属性
        self.service_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.service_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.service_table.setSelectionMode(QTableWidget.SingleSelection)
        # 设置行高以适应多行内容
        self.service_table.verticalHeader().setDefaultSectionSize(50)
        # 设置单元格内容对齐方式（默认居中）
        self.service_table.setStyleSheet("""
            QTableWidget::item {
                text-align: center;
            }
            QTableWidget::item:nth-child(5) {
                text-align: left;
            }
        """)

        # 设置上下文菜单和信号连接
        self.service_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.service_table.customContextMenuRequested.connect(self._show_service_context_menu)
        self.service_table.itemDoubleClicked.connect(self._on_service_double_clicked)
        self.service_table.selectionModel().selectionChanged.connect(self._on_service_selection_changed, Qt.DirectConnection)
        service_layout.addWidget(self.service_table)

        layout.addWidget(service_group)

        # 访问地址区域
        access_group = QGroupBox("访问地址")
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
        QApplication.clipboard().setText(self.public_addr_edit.text())
        QMessageBox.information(self, "提示", "公网地址已复制到剪贴板")
    
    def _browse_public_addr(self):
        """浏览器访问公网地址"""
        addr = self.public_addr_edit.text()
        if addr:
            webbrowser.open(addr)
        else:
            QMessageBox.warning(self, "警告", "公网地址为空，请先启动公网访问")
    
    def _init_status_bar(self):
        """初始化状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 添加启动进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.status_bar.addWidget(self.progress_bar)

        # 添加服务数量信息
        self.service_count_label = QLabel("服务数量: 0")
        self.status_bar.addPermanentWidget(self.service_count_label)

        # 添加运行中服务数量信息
        self.running_count_label = QLabel("运行中: 0")
        self.status_bar.addPermanentWidget(self.running_count_label)
    
    def _update_status_bar(self):
        """更新状态栏信息"""
        total_services = len(self.manager.services)
        running_services = len([s for s in self.manager.services if s.status == ServiceStatus.RUNNING])
        
        self.service_count_label.setText(f"服务数量: {total_services}")
        self.running_count_label.setText(f"运行中: {running_services}")
    
    def show_progress(self, value: int = 0, text: str = "") -> None:
        """显示进度条
        
        Args:
            value: 进度值 (0-100)
            text: 进度文本
        """
        self.progress_bar.setValue(value)
        if text:
            self.progress_bar.setFormat(f"{text} %p%")
        else:
            self.progress_bar.setFormat("%p%")
        self.progress_bar.show()
    
    def hide_progress(self) -> None:
        """隐藏进度条"""
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
    
    def set_progress(self, value: int, text: str = "") -> None:
        """设置进度条值（线程安全，使用信号）
        
        Args:
            value: 进度值 (0-100)
            text: 进度文本
        """
        self.update_progress_signal.emit(value, text)
    
    def _update_progress_ui(self, value: int, text: str) -> None:
        """更新进度条UI（在主线程中执行）
        
        Args:
            value: 进度值 (0-100)
            text: 进度文本
        """
        self.progress_bar.setValue(value)
        if text:
            self.progress_bar.setFormat(f"{text} %p%")
    
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
                        self.manager.allocate_port(current_port)
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
                    'allow_all': service.allow_all
                }
                services_config.append(service_config)
            self.config_manager.set_services(services_config)
            return True
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            return False
    
    def update_service_tree(self):
        """更新服务表格（增量更新）"""
        try:
            # 保存当前选中的行
            selected_row = -1
            selected_items = self.service_table.selectedItems()
            if selected_items:
                selected_row = selected_items[0].row()

            current_count = self.service_table.rowCount()
            new_count = len(self.manager.services)

            # 1. 更新现有行
            for row in range(min(current_count, new_count)):
                self._update_service_row(row, self.manager.services[row])

            # 2. 添加新行
            for row in range(current_count, new_count):
                self._add_service_row(row, self.manager.services[row])

            # 3. 移除多余行（从后往前删除）
            for row in range(current_count - 1, new_count - 1, -1):
                self.service_table.removeRow(row)

            # 恢复选中状态
            if 0 <= selected_row < self.service_table.rowCount():
                self.service_table.selectRow(selected_row)

            # 更新状态栏
            self._update_status_bar()
        except Exception as e:
            print(f"更新服务表格失败: {str(e)}")
            # 即使更新失败，也要确保状态栏信息更新
            try:
                self._update_status_bar()
            except Exception:
                pass

    def _update_service_row(self, row: int, service) -> None:
        """更新服务表格行数据"""
        # 更新服务名称
        name_item = self.service_table.item(row, 0)
        if name_item:
            name_item.setText(service.name)

        # 更新端口
        port_item = self.service_table.item(row, 1)
        if port_item:
            port_item.setText(service.port)

        # 更新状态
        status_badge = StatusBadge(service.status)
        status_badge.setAlignment(Qt.AlignCenter)
        self.service_table.setCellWidget(row, 2, status_badge)

        # 更新公网访问状态
        public_status = service.public_access_status
        public_badge = StatusBadge(public_status)
        if public_status == "running":
            public_badge.setText("🌐 已启用")
        elif public_status == "starting":
            public_badge.setText("◐ 启动中")
        elif public_status == "stopping":
            public_badge.setText("◑ 停止中")
        else:
            public_badge.setText("○ 未启用")
        public_badge.setAlignment(Qt.AlignCenter)
        self.service_table.setCellWidget(row, 3, public_badge)

        # 更新详情
        detail_item = self.service_table.item(row, 4)
        if detail_item:
            permissions = []
            if service.allow_all:
                permissions.append("全部权限")
            else:
                if service.allow_upload:
                    permissions.append("上传")
                if service.allow_delete:
                    permissions.append("删除")
                if service.allow_search:
                    permissions.append("搜索")
                if service.allow_archive:
                    permissions.append("打包")

            if not permissions:
                permissions.append("只读")

            serve_path = service.serve_path
            if serve_path:
                import os
                display_path = os.path.normpath(serve_path)
            else:
                display_path = "当前目录"

            detail_text = f"路径: {display_path}  |  权限: {' | '.join(permissions)}"
            detail_item.setText(detail_text)
            detail_item.setToolTip(f"完整路径: {display_path}\n权限: {' | '.join(permissions)}")

    def _add_service_row(self, row: int, service) -> None:
        """添加服务表格行"""
        self.service_table.insertRow(row)

        # 服务名称
        name_item = QTableWidgetItem(service.name)
        self.service_table.setItem(row, 0, name_item)

        # 端口
        port_item = QTableWidgetItem(service.port)
        self.service_table.setItem(row, 1, port_item)

        # 状态 - 使用 StatusBadge 组件
        status_badge = StatusBadge(service.status)
        status_badge.setAlignment(Qt.AlignCenter)
        self.service_table.setCellWidget(row, 2, status_badge)

        # 公网访问 - 使用 StatusBadge 组件
        public_status = service.public_access_status
        public_badge = StatusBadge(public_status)
        if public_status == "running":
            public_badge.setText("🌐 已启用")
        elif public_status == "starting":
            public_badge.setText("◐ 启动中")
        elif public_status == "stopping":
            public_badge.setText("◑ 停止中")
        else:
            public_badge.setText("○ 未启用")
        public_badge.setAlignment(Qt.AlignCenter)
        self.service_table.setCellWidget(row, 3, public_badge)

        # 详情 - 显示权限和共享路径
        permissions = []
        if service.allow_all:
            permissions.append("全部权限")
        else:
            if service.allow_upload:
                permissions.append("上传")
            if service.allow_delete:
                permissions.append("删除")
            if service.allow_search:
                permissions.append("搜索")
            if service.allow_archive:
                permissions.append("打包")

        if not permissions:
            permissions.append("只读")

        serve_path = service.serve_path
        if serve_path:
            import os
            display_path = os.path.normpath(serve_path)
        else:
            display_path = "当前目录"

        detail_text = f"路径: {display_path}  |  权限: {' | '.join(permissions)}"
        detail_item = QTableWidgetItem(detail_text)
        detail_item.setToolTip(f"完整路径: {display_path}\n权限: {' | '.join(permissions)}")
        self.service_table.setItem(row, 4, detail_item)
    
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

            dialog = DufsServiceDialog(parent=self, service=service, edit_index=row, existing_services=self.manager.services)
            if dialog.exec_() == QDialog.Accepted:
                # 自动更换重复的服务名称（静默处理，不提示用户）
                original_name = dialog.service.name
                unique_name = self._generate_unique_service_name(original_name, exclude_index=row)
                dialog.service.name = unique_name

                # 检查端口是否与其他服务冲突（包括已停止的服务）
                try:
                    current_port = int(dialog.service.port)
                    old_port = int(service.port)
                    # 检查是否与其他服务端口冲突（排除当前编辑的服务）
                    conflict_service = None
                    for i, other_service in enumerate(self.manager.services):
                        if i != row:  # 排除当前编辑的服务
                            if int(other_service.port) == current_port:
                                conflict_service = other_service
                                break

                    if conflict_service:
                        # 端口冲突，查找可用端口
                        new_port = self.manager.find_available_port(current_port + 1)
                        dialog.service.port = str(new_port)
                    elif current_port != old_port and not self.manager._is_port_available(current_port):
                        # 端口已更改且新端口不可用，查找可用端口
                        new_port = self.manager.find_available_port(current_port + 1)
                        dialog.service.port = str(new_port)
                    # 如果端口没有变化或新端口可用，保持原端口

                    # 端口处理完成后，释放旧端口（如果端口有变化）
                    if int(dialog.service.port) != old_port:
                        self.manager.release_allocated_port(old_port)
                except ValueError:
                    # 端口无效，使用默认端口
                    port = self.manager.find_available_port(5001)
                    dialog.service.port = str(port)

                # 如果服务正在运行，先停止它
                if was_running:
                    # 停止公网服务
                    if was_public_running and hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                        try:
                            service.cloudflared_process.terminate()
                            service.cloudflared_process.wait(timeout=5)
                        except Exception as e:
                            print(f"终止cloudflared进程失败: {str(e)}")

                    # 停止内网服务
                    if service.process:
                        try:
                            service.process.terminate()
                            service.process.wait(timeout=5)
                        except Exception as e:
                            print(f"终止服务进程失败: {str(e)}")

                    # 更新服务状态为已停止
                    service.update_status(ServiceStatus.STOPPED)
                    if hasattr(service, 'public_access_status'):
                        service.update_status(public_access_status="stopped")

                # 断开旧服务的信号连接，避免重复连接
                try:
                    service.status_updated.disconnect(self._on_service_status_updated)
                except TypeError:
                    # 信号未连接，忽略错误
                    pass

                # 连接新服务的状态更新信号
                dialog.service.status_updated.connect(self._on_service_status_updated)

                # 更新服务
                self.manager.edit_service(row, dialog.service)
                self.update_service_tree()
                self._save_config()

                # 如果服务之前在运行，重启它
                if was_running:
                    # 获取更新后的服务
                    updated_service = self.manager.services[row]
                    # 延迟启动，确保配置已保存
                    time.sleep(0.1)  # 100ms延迟
                    # 启动内网服务（在新线程中）
                    threading.Thread(target=updated_service.start, args=(self.log_manager,), daemon=True).start()
                    # 如果之前公网服务是运行的，也启动公网服务
                    if was_public_running:
                        # 延迟一点时间，确保内网服务已经启动
                        time.sleep(1)  # 1秒延迟
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
            if QMessageBox.question(self, "确认", f"确定要删除服务 '{service.name}' 吗？\n\n删除前将自动停止服务并清理残留进程。") == QMessageBox.Yes:
                # 先停止服务（包括清除残留进程）
                if service.status != ServiceStatus.STOPPED or service.public_access_status == "running":
                    try:
                        # 使用 stop 方法停止服务，它会自动清除残留进程
                        service.stop(self.log_manager)
                        # 等待一小段时间确保进程完全终止
                        import time
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"停止服务时出错: {str(e)}")
                        # 即使出错也继续删除

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
                QMessageBox.warning(self, "警告", "内网共享正在启动中，请稍候")
                return
            if service.status == ServiceStatus.STOPPING:
                QMessageBox.warning(self, "警告", "内网共享正在停止中，请稍候")
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
                    # 先查找可用端口，成功后再释放旧端口，避免竞态条件
                    new_port = self.manager.find_available_port(current_port + 1)
                    self.manager.release_allocated_port(current_port)
                    QMessageBox.information(
                        self,
                        "端口已更换",
                        f"原端口 {current_port} 与服务 '{conflict_service.name}' 冲突，已自动更换为 {new_port}"
                    )
                    service.port = str(new_port)
                    self._save_config()
                else:
                    # 检查当前端口是否可用（黑名单或被占用）
                    if not self.manager._is_port_available(current_port):
                        # 先查找可用端口，成功后再释放旧端口
                        new_port = self.manager.find_available_port(current_port + 1)
                        self.manager.release_allocated_port(current_port)
                        QMessageBox.information(
                            self,
                            "端口已更换",
                            f"原端口 {current_port} 为黑名单端口或已被占用，已自动更换为 {new_port}"
                        )
                        service.port = str(new_port)
                        self._save_config()
                    else:
                        # 端口可用，确保已分配
                        self.manager._allocated_ports.add(current_port)
            except ValueError:
                QMessageBox.warning(self, "警告", f"服务端口无效: {service.port}")
                return
            except Exception as e:
                QMessageBox.warning(self, "警告", f"端口检查失败: {str(e)}")
                return

            # 显示进度条
            self.show_progress(10, "启动中")
            
            # 启动内网共享服务（在新线程中）
            def start_with_progress():
                try:
                    self.set_progress(30, "启动中")
                    result = service.start(self.log_manager)
                    if result:
                        self.set_progress(100, "启动完成")
                        # 延迟隐藏进度条
                        QTimer.singleShot(2000, self.hide_progress)
                    else:
                        self.hide_progress()
                except Exception as e:
                    print(f"启动服务失败: {str(e)}")
                    self.hide_progress()
            
            threading.Thread(target=start_with_progress, daemon=True).start()
    

    

    
    def _stop_service(self):
        """停止共享服务"""
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
            
            # 停止共享服务
            threading.Thread(target=service.stop, args=(self.log_manager,), daemon=True).start()
    

    
    def _start_public_access(self):
        """启动公网共享"""
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
            if service.public_access_status in ["starting", "stopping"]:
                QMessageBox.warning(self, "警告", f"公网共享正在{service.public_access_status == 'starting' and '启动' or '停止'}中，请稍候")
                return

            # 先检查并下载 cloudflared（在主线程中）
            from cloudflared_downloader import check_and_download_cloudflared
            if not check_and_download_cloudflared(self):
                # 用户取消或下载失败
                return

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
                    QMessageBox.warning(self, "警告", f"端口检查失败: {str(e)}")
                    return

                # 设置启动标志，防止切换服务
                self._service_starting = True
                
                # 禁用按钮
                self._set_buttons_enabled(False)
                
                # 显示进度条
                self.show_progress(0, "启动内网服务")
                
                # 先启动内网服务
                def start_with_internal():
                    import time
                    try:
                        # 内网服务启动进度 0-30%
                        for i in range(0, 31, 10):
                            self.set_progress(i, "启动内网服务中")
                            time.sleep(0.15)
                        
                        if service.start(self.log_manager):
                            # 内网启动完成 30%，等待服务稳定
                            self.set_progress(30, "内网服务启动完成")
                            time.sleep(0.5)
                            
                            # 开始启动公网 30-50%
                            for i in range(30, 51, 5):
                                self.set_progress(i, "启动公网服务中")
                                time.sleep(0.3)
                            
                            # 实际启动公网服务（这会启动监控线程）
                            service.start_public_access(self.log_manager)
                            
                            # 等待公网服务建立连接 50-90%（大约需要3-5秒）
                            for i in range(50, 91, 5):
                                self.set_progress(i, "等待公网连接建立")
                                time.sleep(0.4)
                            
                            # 完成 100%
                            self.set_progress(100, "启动完成")
                            time.sleep(2)
                            self.hide_progress()
                        else:
                            self.hide_progress()
                    except Exception as e:
                        print(f"启动服务失败: {str(e)}")
                        self.hide_progress()
                    finally:
                        # 清除启动标志
                        self._service_starting = False
                        # 启用按钮
                        self._set_buttons_enabled(True)
                threading.Thread(target=start_with_internal, daemon=True).start()
            else:
                # 直接启动公网服务（内网服务已在运行）
                # 设置启动标志，防止切换服务
                self._service_starting = True
                
                # 禁用按钮
                self._set_buttons_enabled(False)
                
                self.show_progress(0, "启动公网服务")
                
                def start_public_with_progress():
                    try:
                        import time
                        # 启动公网服务准备阶段 0-30%
                        for i in range(0, 31, 10):
                            self.set_progress(i, "启动公网服务中")
                            time.sleep(0.2)
                        
                        # 实际启动公网服务
                        service.start_public_access(self.log_manager)
                        
                        # 等待公网服务建立连接 30-90%（大约需要3-5秒）
                        for i in range(30, 91, 5):
                            self.set_progress(i, "等待公网连接建立")
                            time.sleep(0.4)
                        
                        # 完成 100%
                        self.set_progress(100, "启动完成")
                        time.sleep(2)
                        self.hide_progress()
                    except Exception as e:
                        print(f"启动公网服务失败: {str(e)}")
                        self.hide_progress()
                    finally:
                        # 清除启动标志
                        self._service_starting = False
                        # 启用按钮
                        self._set_buttons_enabled(True)
                
                threading.Thread(target=start_public_with_progress, daemon=True).start()
    

    

    

    
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
    
    def _set_buttons_enabled(self, enabled: bool) -> None:
        """设置按钮启用/禁用状态"""
        self.add_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)
        self.start_btn.setEnabled(enabled)
        self.start_public_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
    
    def _init_menu_bar(self) -> None:
        """初始化菜单栏"""
        from PyQt5.QtWidgets import QMenuBar, QMenu, QAction
        from autostart_manager import AutoStartManager
        
        # 创建菜单栏
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        
        # 创建设置菜单
        settings_menu = QMenu("设置", self)
        menu_bar.addMenu(settings_menu)
        
        # 开机自启选项
        self.autostart_action = QAction("开机自启", self)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(AutoStartManager.is_enabled())
        self.autostart_action.triggered.connect(self._on_autostart_toggled)
        settings_menu.addAction(self.autostart_action)
    
    def _on_autostart_toggled(self, checked: bool) -> None:
        """开机自启选项切换事件"""
        from autostart_manager import AutoStartManager
        
        if checked:
            if AutoStartManager.enable():
                QMessageBox.information(self, "成功", "已启用开机自启")
            else:
                self.autostart_action.setChecked(False)
                QMessageBox.warning(self, "失败", "启用开机自启失败，请确保程序已打包为exe")
        else:
            if AutoStartManager.disable():
                QMessageBox.information(self, "成功", "已禁用开机自启")
            else:
                QMessageBox.warning(self, "失败", "禁用开机自启失败")
    
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
        # 如果正在启动服务，不显示右键菜单
        if self._service_starting:
            return
        
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
        """服务双击事件"""
        row = item.row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            # 显示服务详情
            dialog = DufsServiceDialog(parent=self, service=service, edit_index=row, existing_services=self.manager.services)
            if dialog.exec_() == QDialog.Accepted:
                self.manager.edit_service(row, dialog.service)
                self.update_service_tree()
                self._save_config()
    
    def _on_service_selection_changed(self, selected, deselected) -> None:
        """服务选择变更事件"""
        try:
            # 如果正在启动服务，阻止切换
            if self._service_starting:
                # 恢复之前的选择
                if deselected.indexes():
                    prev_row = deselected.indexes()[0].row()
                    self.service_table.selectRow(prev_row)
                return
            
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
        import time
        
        # 显示退出提示
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("停止服务 %p%")
        QApplication.processEvents()  # 刷新UI
        
        # 停止所有服务并清理残留进程
        total_services = len(self.manager.services)
        for i, service in enumerate(self.manager.services):
            try:
                progress = int((i / total_services) * 50) if total_services > 0 else 0
                self.progress_bar.setValue(progress)
                QApplication.processEvents()
                
                # 使用 stop 方法停止服务，它会自动清理残留进程
                if service.status != ServiceStatus.STOPPED or service.public_access_status == "running":
                    service.stop(self.log_manager)
                    # 等待一小段时间确保进程终止
                    time.sleep(0.5)
            except Exception as e:
                print(f"停止服务 '{service.name}' 时出错: {str(e)}")
        
        self.progress_bar.setValue(60)
        QApplication.processEvents()
        
        # 额外清理：强制终止所有 dufs 和 cloudflared 进程
        self._kill_all_residual_processes()
        
        # 等待进程终止
        time.sleep(1.0)
        
        self.progress_bar.setValue(80)
        QApplication.processEvents()
        
        # 保存配置
        self._save_config()
        
        self.progress_bar.setValue(90)
        QApplication.processEvents()
        
        # 关闭日志窗口
        if self.log_window:
            self.log_window.close()
        
        # 隐藏托盘图标
        if hasattr(self, 'tray_manager'):
            self.tray_manager.hide()
        
        self.progress_bar.setValue(100)
        QApplication.processEvents()
        
        # 真正退出程序
        QApplication.quit()
    
    def _kill_all_residual_processes(self):
        """强制终止所有 dufs 和 cloudflared 残留进程（Windows专用）"""
        from utils import kill_all_dufs_and_cloudflared
        
        try:
            # 使用统一的清理函数
            kill_all_dufs_and_cloudflared(self.log_manager, "系统")
        except Exception as e:
            print(f"清理残留进程时出错: {str(e)}")

    def resizeEvent(self, event):
        """窗口大小改变事件 - 响应式布局"""
        super().resizeEvent(event)
        self._adjust_layout_for_size(event.size())

    def _adjust_layout_for_size(self, size):
        """根据窗口尺寸动态调整布局"""
        # 小屏幕优化 (< 1000px)
        if size.width() < 1000:
            # 简化按钮文字
            self.add_btn.setText("添加")
            self.edit_btn.setText("编辑")
            self.delete_btn.setText("删除")
            self.start_btn.setText("启动")
            self.start_public_btn.setText("公网")
            self.stop_btn.setText("停止")
        else:
            # 恢复完整按钮文字
            self.add_btn.setText("添加服务")
            self.edit_btn.setText("编辑服务")
            self.delete_btn.setText("删除服务")
            self.start_btn.setText("启动内网共享")
            self.start_public_btn.setText("启动公网共享")
            self.stop_btn.setText("停止共享服务")

        # 宽屏优化 (> 1400px)
        if size.width() > 1400:
            # 表格列宽按内容分配
            header = self.service_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)  # 服务名称自适应
            header.setSectionResizeMode(1, QHeaderView.Fixed)    # 端口固定
            header.setSectionResizeMode(2, QHeaderView.Fixed)    # 状态固定
            header.setSectionResizeMode(3, QHeaderView.Stretch)  # 公网访问自适应
            header.setSectionResizeMode(4, QHeaderView.Fixed)    # 详情固定
        else:
            # 默认列宽
            header = self.service_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Interactive)
            header.setSectionResizeMode(1, QHeaderView.Interactive)
            header.setSectionResizeMode(2, QHeaderView.Interactive)
            header.setSectionResizeMode(3, QHeaderView.Interactive)
            header.setSectionResizeMode(4, QHeaderView.Interactive)
