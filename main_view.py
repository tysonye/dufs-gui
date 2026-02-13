"""主视图文件 - 负责UI展示和用户交互"""

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QCheckBox, 
    QMessageBox, QMenu, QAction, QStatusBar, QLineEdit, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor

from constants import (
    AppConstants, GLOBAL_STYLESHEET, get_resource_path,
    Theme, IconManager
)
from service_state import ServiceStatus


class MainView(QMainWindow):
    """主视图类 - 负责UI展示和用户交互"""

    # 定义信号
    update_service_tree_signal = pyqtSignal()
    update_address_fields_signal = pyqtSignal(str, str)
    update_progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_fonts()
        self._setup_ui()

        QTimer.singleShot(50, self._apply_stylesheet_delayed)

    def _apply_stylesheet_delayed(self):
        """延迟应用样式表"""
        self.setStyleSheet(GLOBAL_STYLESHEET)

    def _setup_fonts(self):
        """优化全局字体排版"""
        app_font = QFont("Microsoft YaHei", 10)
        self.setFont(app_font)

    def _setup_ui(self):
        """初始化UI - 极简布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建各区域
        self._create_header(main_layout)
        self._create_service_management(main_layout)
        self._create_service_list(main_layout)
        self._create_footer(main_layout)

        self._create_status_bar()

    def _create_header(self, layout: QVBoxLayout):
        """创建头部区域"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # 标题
        title_label = QLabel("DufsGUI")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        layout.addWidget(header)

    def _create_service_management(self, layout: QVBoxLayout):
        """创建服务管理区域"""
        management = QWidget()
        management_layout = QHBoxLayout(management)
        management_layout.setContentsMargins(0, 0, 0, 0)
        management_layout.setSpacing(8)

        # 服务操作按钮
        self.add_btn = QPushButton("新建服务")
        self.add_btn.setStyleSheet("""
        QPushButton {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #45a049;
        }
        QPushButton:pressed {
            background: #3d8b40;
        }
        """)
        management_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑服务")
        self.edit_btn.setStyleSheet("""
        QPushButton {
            background: #FF9800;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #f57c00;
        }
        QPushButton:pressed {
            background: #e65100;
        }
        """)
        management_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除服务")
        self.delete_btn.setStyleSheet("""
        QPushButton {
            background: #f44336;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #e53935;
        }
        QPushButton:pressed {
            background: #d32f2f;
        }
        """)
        management_layout.addWidget(self.delete_btn)

        management_layout.addSpacing(16)

        # 服务控制按钮
        self.start_btn = QPushButton("启动内网")
        self.start_btn.setStyleSheet("""
        QPushButton {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #45a049;
        }
        QPushButton:pressed {
            background: #3d8b40;
        }
        """)
        management_layout.addWidget(self.start_btn)

        self.start_public_btn = QPushButton("启动公网")
        self.start_public_btn.setStyleSheet("""
        QPushButton {
            background: #2196F3;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #1e88e5;
        }
        QPushButton:pressed {
            background: #1976d2;
        }
        """)
        management_layout.addWidget(self.start_public_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("""
        QPushButton {
            background: #f44336;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #e53935;
        }
        QPushButton:pressed {
            background: #d32f2f;
        }
        """)
        management_layout.addWidget(self.stop_btn)

        management_layout.addStretch()

        layout.addWidget(management)

    def _create_service_list(self, layout: QVBoxLayout):
        """创建服务列表区域"""
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)

        # 服务表格
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(5)
        self.service_table.setHorizontalHeaderLabels(["序号", "服务名称", "端口", "状态", "服务详情"])
        self.service_table.setColumnWidth(0, 50)
        self.service_table.setColumnWidth(1, 120)
        self.service_table.setColumnWidth(2, 80)
        self.service_table.setColumnWidth(3, 100)
        self.service_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.service_table.setStyleSheet("border: 1px solid #ddd;")
        # 设置整行选择
        self.service_table.setSelectionBehavior(QTableWidget.SelectRows)
        # 禁止编辑
        self.service_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 隐藏垂直表头（行号列）
        self.service_table.verticalHeader().setVisible(False)
        list_layout.addWidget(self.service_table)

        # 地址显示区域
        self._create_address_section(list_layout)

        layout.addWidget(list_container)

    def _create_address_section(self, layout: QVBoxLayout):
        """创建地址显示区域"""
        address_group = QGroupBox("访问地址")
        address_layout = QVBoxLayout(address_group)
        address_layout.setContentsMargins(10, 10, 10, 10)
        address_layout.setSpacing(8)

        # 内网地址
        local_layout = QHBoxLayout()
        local_layout.addWidget(QLabel("内网地址:"))
        self.local_addr_edit = QLineEdit()
        self.local_addr_edit.setReadOnly(True)
        self.local_addr_edit.setStyleSheet("""
        QLineEdit {
            background: #f5f5f5;
            border: 1px solid #ddd;
            padding: 4px 6px;
            border-radius: 4px;
            min-height: 20px;
            font-size: 12px;
        }
        """)
        local_layout.addWidget(self.local_addr_edit)

        self.copy_local_btn = QPushButton("复制")
        self.copy_local_btn.setStyleSheet("""
        QPushButton {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            min-height: 20px;
            font-size: 11px;
        }
        QPushButton:hover {
            background: #45a049;
        }
        QPushButton:pressed {
            background: #3d8b40;
        }
        """)
        local_layout.addWidget(self.copy_local_btn)

        self.browse_local_btn = QPushButton("访问")
        self.browse_local_btn.setStyleSheet("""
        QPushButton {
            background: #2196F3;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            min-height: 20px;
            font-size: 11px;
        }
        QPushButton:hover {
            background: #1e88e5;
        }
        QPushButton:pressed {
            background: #1976d2;
        }
        """)
        local_layout.addWidget(self.browse_local_btn)
        address_layout.addLayout(local_layout)

        # 公网地址
        public_layout = QHBoxLayout()
        public_layout.addWidget(QLabel("公网地址:"))
        self.public_addr_edit = QLineEdit()
        self.public_addr_edit.setReadOnly(True)
        self.public_addr_edit.setStyleSheet("""
        QLineEdit {
            background: #f5f5f5;
            border: 1px solid #ddd;
            padding: 4px 6px;
            border-radius: 4px;
            min-height: 20px;
            font-size: 12px;
        }
        """)
        public_layout.addWidget(self.public_addr_edit)

        self.copy_public_btn = QPushButton("复制")
        self.copy_public_btn.setStyleSheet("""
        QPushButton {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            min-height: 20px;
            font-size: 11px;
        }
        QPushButton:hover {
            background: #45a049;
        }
        QPushButton:pressed {
            background: #3d8b40;
        }
        """)
        public_layout.addWidget(self.copy_public_btn)

        self.browse_public_btn = QPushButton("访问")
        self.browse_public_btn.setStyleSheet("""
        QPushButton {
            background: #2196F3;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            min-height: 20px;
            font-size: 11px;
        }
        QPushButton:hover {
            background: #1e88e5;
        }
        QPushButton:pressed {
            background: #1976d2;
        }
        """)
        public_layout.addWidget(self.browse_public_btn)
        address_layout.addLayout(public_layout)

        layout.addWidget(address_group)

    def _create_footer(self, layout: QVBoxLayout):
        """创建底部区域"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(10)

        # 日志按钮
        self.log_window_btn = QPushButton("查看日志")
        self.log_window_btn.setStyleSheet("""
        QPushButton {
            background: #2196F3;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #1e88e5;
        }
        QPushButton:pressed {
            background: #1976d2;
        }
        """)
        footer_layout.addWidget(self.log_window_btn)

        # 开机自启
        self.startup_checkbox = QCheckBox("开机自动启动")
        footer_layout.addWidget(self.startup_checkbox)
        QTimer.singleShot(0, self._load_startup_state)

        footer_layout.addStretch()

        # 退出按钮
        self.exit_btn = QPushButton("退出")
        self.exit_btn.setStyleSheet("""
        QPushButton {
            background: #f44336;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background: #e53935;
        }
        QPushButton:pressed {
            background: #d32f2f;
        }
        """)
        footer_layout.addWidget(self.exit_btn)

        layout.addWidget(footer)

    def _create_status_bar(self):
        """创建状态栏"""
        self.statusBar().showMessage("就绪")

    def _setup_window(self):
        """设置窗口基本属性"""
        self.setWindowTitle("DufsGUI - 文件共享服务管理")
        self.setMinimumSize(700, 500)

        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    # ========== 公共接口方法 ==========

    def set_button_callbacks(self, callbacks: dict):
        """设置按钮回调函数"""
        if callbacks.get('add'):
            self.add_btn.clicked.connect(callbacks['add'])
        if callbacks.get('edit'):
            self.edit_btn.clicked.connect(callbacks['edit'])
        if callbacks.get('delete'):
            self.delete_btn.clicked.connect(callbacks['delete'])
        if callbacks.get('start'):
            self.start_btn.clicked.connect(callbacks['start'])
        if callbacks.get('start_public'):
            self.start_public_btn.clicked.connect(callbacks['start_public'])
        if callbacks.get('stop'):
            self.stop_btn.clicked.connect(callbacks['stop'])
        if callbacks.get('log_window'):
            self.log_window_btn.clicked.connect(callbacks['log_window'])
        if callbacks.get('exit'):
            self.exit_btn.clicked.connect(callbacks['exit'])
        # 地址操作按钮回调
        if callbacks.get('copy_local'):
            self.copy_local_btn.clicked.connect(callbacks['copy_local'])
        if callbacks.get('browse_local'):
            self.browse_local_btn.clicked.connect(callbacks['browse_local'])
        if callbacks.get('copy_public'):
            self.copy_public_btn.clicked.connect(callbacks['copy_public'])
        if callbacks.get('browse_public'):
            self.browse_public_btn.clicked.connect(callbacks['browse_public'])

    def set_table_callbacks(self, right_click_callback, double_click_callback, selection_changed_callback):
        """设置表格回调函数"""
        self.service_table.itemDoubleClicked.connect(double_click_callback)
        self.service_table.customContextMenuRequested.connect(right_click_callback)
        self.service_table.itemSelectionChanged.connect(selection_changed_callback)

    def get_selected_row(self) -> int:
        """获取当前选中的行索引"""
        selected_items = self.service_table.selectedItems()
        if selected_items:
            return selected_items[0].row()
        return -1

    def update_service_table(self, services: list, status_colors: dict):
        """更新服务表格（优化版，减少不必要的重绘）"""
        # 检查数据是否真正变化，避免不必要的刷新
        if self._is_table_data_unchanged(services):
            return

        selected_row = self.get_selected_row()

        # 禁用更新以优化性能
        self.service_table.setUpdatesEnabled(False)

        try:
            # 只更新变化的行，而不是清空重建
            current_row_count = self.service_table.rowCount()
            new_row_count = len(services)

            # 调整行数
            if new_row_count > current_row_count:
                for _ in range(new_row_count - current_row_count):
                    self.service_table.insertRow(current_row_count)
            elif new_row_count < current_row_count:
                for _ in range(current_row_count - new_row_count):
                    self.service_table.removeRow(current_row_count - 1)

            # 更新每行数据
            for row, service in enumerate(services):
                self._update_table_row(row, service)

        finally:
            # 恢复更新
            self.service_table.setUpdatesEnabled(True)

        # 恢复选中状态
        if selected_row >= 0 and selected_row < len(services):
            self.service_table.selectRow(selected_row)

    def _is_table_data_unchanged(self, services: list) -> bool:
        """检查表格数据是否未变化（包括权限信息）"""
        if not hasattr(self, '_last_services_data'):
            self._last_services_data = None
            return False

        if len(services) != self.service_table.rowCount():
            return False

        current_data = []
        for service in services:
            # 包含权限信息，确保权限变化时能刷新显示
            current_data.append((
                service.name,
                str(service.port),
                service.status,
                getattr(service, 'public_access_status', 'stopped'),
                getattr(service, 'allow_upload', False),
                getattr(service, 'allow_delete', False),
                getattr(service, 'allow_search', False),
                getattr(service, 'allow_archive', False),
                getattr(service, 'allow_all', False),
                getattr(service, 'serve_path', '')
            ))

        if self._last_services_data == current_data:
            return True

        self._last_services_data = current_data
        return False

    def _update_table_row(self, row: int, service):
        """更新表格单行数据"""
        # 序号
        serial_item = self.service_table.item(row, 0)
        if not serial_item:
            serial_item = QTableWidgetItem()
            serial_item.setTextAlignment(Qt.AlignCenter)
            self.service_table.setItem(row, 0, serial_item)
        serial_item.setText(str(row + 1))

        # 服务名称
        name_item = self.service_table.item(row, 1)
        if not name_item:
            name_item = QTableWidgetItem()
            self.service_table.setItem(row, 1, name_item)
        name_item.setText(service.name)

        # 端口
        port_item = self.service_table.item(row, 2)
        if not port_item:
            port_item = QTableWidgetItem()
            self.service_table.setItem(row, 2, port_item)
        port_item.setText(str(service.port))

        # 状态
        status_item = self.service_table.item(row, 3)
        if not status_item:
            status_item = QTableWidgetItem()
            self.service_table.setItem(row, 3, status_item)

        if hasattr(service, 'public_access_status') and service.public_access_status == "running":
            status_text = ServiceStatus.PUBLIC
            status_color = QColor(33, 150, 243)  # 蓝色
        elif service.status == ServiceStatus.RUNNING:
            status_text = ServiceStatus.RUNNING
            status_color = QColor(76, 175, 80)  # 绿色
        else:
            status_text = ServiceStatus.STOPPED
            status_color = QColor(158, 158, 158)  # 灰色

        if status_item.text() != status_text:
            status_item.setText(status_text)
            status_item.setForeground(status_color)

        # 服务详情
        detail_item = self.service_table.item(row, 4)
        if not detail_item:
            detail_item = QTableWidgetItem()
            self.service_table.setItem(row, 4, detail_item)

        path_value = getattr(service, 'path', getattr(service, 'serve_path', ''))

        # 构建权限显示字符串（不显示"全部"，直接显示勾选的权限）
        permissions = []
        if getattr(service, 'allow_upload', False):
            permissions.append("上传")
        if getattr(service, 'allow_delete', False):
            permissions.append("删除")
        if getattr(service, 'allow_search', False):
            permissions.append("搜索")
        if getattr(service, 'allow_archive', False):
            permissions.append("归档")

        permission_value = "、".join(permissions) if permissions else "只读"
        detail_text = f"{path_value} | {permission_value}"

        if detail_item.text() != detail_text:
            detail_item.setText(detail_text)

    def show_error_message(self, title: str, message: str):
        """显示错误消息"""
        QMessageBox.critical(self, title, message)

    def show_info_message(self, title: str, message: str):
        """显示信息消息"""
        QMessageBox.information(self, title, message)

    def show_confirm_dialog(self, title: str, message: str) -> bool:
        """显示确认对话框"""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def start_progress(self, message: str):
        """开始显示进度"""
        self.statusBar().showMessage(message)

    def stop_progress(self, success: bool = True):
        """停止显示进度"""
        self.statusBar().showMessage("就绪")

    def set_progress_value(self, value: int):
        """设置进度条值"""
        pass

    def set_checkbox_callback(self, callback):
        """设置复选框回调"""
        self.startup_checkbox.stateChanged.connect(callback)

    def update_address_fields(self, local_addr: str, public_addr: str):
        """更新地址编辑框"""
        self.local_addr_edit.setText(local_addr)
        self.public_addr_edit.setText(public_addr)

    def get_local_address(self) -> str:
        """获取本地地址"""
        return self.local_addr_edit.text()

    def get_public_address(self) -> str:
        """获取公网地址"""
        return self.public_addr_edit.text()

    def copy_to_clipboard(self, text: str):
        """复制文本到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def open_browser(self, url: str):
        """在浏览器中打开URL"""
        import webbrowser
        if url:
            webbrowser.open(url)

    def show_message(self, title: str, message: str, icon: int = 1):
        """显示消息"""
        if icon == 3:
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def show_question(self, title: str, message: str) -> bool:
        """显示确认对话框"""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def show_context_menu(self, position, callbacks: dict):
        """显示上下文菜单"""
        menu = QMenu()

        if callbacks.get('start'):
            start_action = QAction("启动内网共享", self)
            start_action.triggered.connect(callbacks['start'])
            menu.addAction(start_action)

        if callbacks.get('start_public'):
            start_public_action = QAction("启动公网共享", self)
            start_public_action.triggered.connect(callbacks['start_public'])
            menu.addAction(start_public_action)

        if callbacks.get('stop'):
            stop_action = QAction("停止共享", self)
            stop_action.triggered.connect(callbacks['stop'])
            menu.addAction(stop_action)

        menu.addSeparator()

        if callbacks.get('edit'):
            edit_action = QAction("编辑服务", self)
            edit_action.triggered.connect(callbacks['edit'])
            menu.addAction(edit_action)

        if callbacks.get('delete'):
            delete_action = QAction("删除服务", self)
            delete_action.triggered.connect(callbacks['delete'])
            menu.addAction(delete_action)

        menu.exec_(self.service_table.viewport().mapToGlobal(position))

    def _load_startup_state(self):
        """加载开机自启状态"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
                value, _ = winreg.QueryValueEx(key, "DufsGUI")
                winreg.CloseKey(key)
                self.startup_checkbox.setChecked(True)
            except (WindowsError, FileNotFoundError):
                self.startup_checkbox.setChecked(False)
        except Exception:
            self.startup_checkbox.setChecked(False)
