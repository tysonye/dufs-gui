"""主窗口视图层 - 负责UI构建和显示"""

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QMenu, QAction,
    QMessageBox, QSystemTrayIcon, QStatusBar, QTableWidget,
    QPlainTextEdit, QTableWidgetItem, QSizePolicy, QGraphicsDropShadowEffect,
    QProgressBar, QHeaderView, QCheckBox
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QIcon, QFont

from constants import AppConstants, GLOBAL_STYLESHEET, get_resource_path
from startup_manager import StartupManager


class MainView(QMainWindow):
    """主窗口视图类 - 纯UI构建和显示"""

    # 信号定义
    update_service_tree_signal = pyqtSignal()
    update_address_fields_signal = pyqtSignal(str, str)
    update_progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_fonts()
        self._setup_ui()
        self._setup_shadows()

    def _setup_window(self):
        """设置窗口基本属性"""
        self.setWindowTitle("DufsGUI - 多服务管理")
        self.setMinimumSize(AppConstants.MIN_WINDOW_WIDTH, AppConstants.MIN_WINDOW_HEIGHT)

        # 设置程序标题栏图标
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 应用全局样式表
        self.setStyleSheet(GLOBAL_STYLESHEET)

    def _setup_fonts(self):
        """优化全局字体排版"""
        app_font = QFont("Microsoft YaHei", 10)
        app_font.setHintingPreference(QFont.PreferFullHinting)
        self.setFont(app_font)

    def _setup_ui(self):
        """初始化UI"""
        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(*AppConstants.MAIN_LAYOUT_MARGINS)
        main_layout.setSpacing(AppConstants.MAIN_LAYOUT_SPACING)

        # 添加服务管理区域
        self._create_top_buttons(main_layout)
        self._create_service_table(main_layout)
        self._create_access_section(main_layout)

        # 初始化状态栏
        self._create_status_bar()

    def _create_top_buttons(self, layout: QVBoxLayout):
        """创建顶部操作按钮"""
        top_button_layout = QHBoxLayout()
        top_button_layout.setSpacing(10)

        # 左侧按钮 - 服务管理
        self.add_btn = QPushButton("添加服务")
        self.add_btn.setObjectName("InfoBtn")
        top_button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑服务")
        self.edit_btn.setObjectName("InfoBtn")
        top_button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除服务")
        self.delete_btn.setObjectName("StopBtn")
        top_button_layout.addWidget(self.delete_btn)

        # 间隔
        top_button_layout.addSpacing(30)

        # 中间按钮 - 共享控制
        self.start_btn = QPushButton("启动内网共享")
        self.start_btn.setObjectName("StartBtn")
        top_button_layout.addWidget(self.start_btn)

        self.start_public_btn = QPushButton("启动公网共享")
        self.start_public_btn.setObjectName("PublicBtn")
        top_button_layout.addWidget(self.start_public_btn)

        self.stop_btn = QPushButton("停止共享服务")
        self.stop_btn.setObjectName("StopBtn")
        top_button_layout.addWidget(self.stop_btn)

        # 右侧按钮
        top_button_layout.addStretch()

        self.log_window_btn = QPushButton("显示日志窗口")
        top_button_layout.addWidget(self.log_window_btn)

        # 开机自启复选框
        self.startup_checkbox = QCheckBox("开机自启")
        self.startup_checkbox.setChecked(StartupManager.is_startup_enabled())
        top_button_layout.addWidget(self.startup_checkbox)

        self.exit_btn = QPushButton("关闭程序")
        top_button_layout.addWidget(self.exit_btn)

        layout.addLayout(top_button_layout)

    def _create_service_table(self, layout: QVBoxLayout):
        """创建服务列表表格"""
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

        # 设置垂直表头（行号）按照内容自适应
        self.service_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # 设置表格属性
        self.service_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.service_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.service_table.setSelectionMode(QTableWidget.SingleSelection)

        # 设置上下文菜单
        self.service_table.setContextMenuPolicy(Qt.CustomContextMenu)

        service_layout.addWidget(self.service_table)
        layout.addWidget(service_group)

    def _create_access_section(self, layout: QVBoxLayout):
        """创建访问地址区域"""
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
        local_access_layout.addWidget(self.copy_local_btn)

        self.browse_local_btn = QPushButton("浏览器访问")
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
        public_access_layout.addWidget(self.copy_public_btn)

        self.browse_public_btn = QPushButton("浏览器访问")
        public_access_layout.addWidget(self.browse_public_btn)

        access_layout.addLayout(public_access_layout)

        layout.addWidget(access_group)

    def _create_status_bar(self):
        """创建状态栏（包含进度条）"""
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

    def _setup_shadows(self):
        """为关键区域设置阴影效果"""
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

    def _add_shadow(self, widget, blur_radius=12, offset=(0, 2), color=(0, 0, 0, 40)):
        """为任意widget添加专业阴影效果"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setOffset(offset[0], offset[1])
        shadow.setColor(QColor(color[0], color[1], color[2], color[3]))
        widget.setGraphicsEffect(shadow)

    # ========== 公共接口方法 ==========

    def set_button_callbacks(self, callbacks: dict):
        """设置按钮回调函数

        Args:
            callbacks: 按钮名称到回调函数的映射
        """
        button_map = {
            'add': self.add_btn,
            'edit': self.edit_btn,
            'delete': self.delete_btn,
            'start': self.start_btn,
            'start_public': self.start_public_btn,
            'stop': self.stop_btn,
            'log_window': self.log_window_btn,
            'exit': self.exit_btn,
            'copy_local': self.copy_local_btn,
            'browse_local': self.browse_local_btn,
            'copy_public': self.copy_public_btn,
            'browse_public': self.browse_public_btn,
        }

        for name, callback in callbacks.items():
            if name in button_map:
                button_map[name].clicked.connect(callback)

    def set_checkbox_callback(self, callback):
        """设置复选框回调"""
        self.startup_checkbox.stateChanged.connect(callback)

    def set_table_callbacks(self, context_menu_callback, double_click_callback, selection_changed_callback):
        """设置表格回调"""
        self.service_table.customContextMenuRequested.connect(context_menu_callback)
        self.service_table.itemDoubleClicked.connect(double_click_callback)
        self.service_table.selectionModel().selectionChanged.connect(selection_changed_callback, Qt.DirectConnection)

    def get_selected_row(self) -> int:
        """获取当前选中的行索引"""
        selected_items = self.service_table.selectedItems()
        if selected_items:
            return selected_items[0].row()
        return -1

    def update_service_table(self, services: list, status_colors: dict):
        """更新服务表格

        Args:
            services: 服务列表
            status_colors: 状态颜色映射
        """
        from service import ServiceStatus

        # 保存当前选中的行
        selected_row = self.get_selected_row()

        # 清空表格
        self.service_table.setRowCount(0)

        # 添加服务到表格
        for service in services:
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
            status_item.setForeground(QColor(status_colors.get(service.status, "#95a5a6")))
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

    def set_buttons_enabled(self, enabled: bool):
        """设置按钮启用/禁用状态"""
        self.start_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.start_public_btn.setEnabled(enabled)
        self.add_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)

    def show_context_menu(self, position: QPoint, callbacks: dict):
        """显示服务上下文菜单"""
        menu = QMenu()

        actions = [
            ("启动服务", callbacks.get('start')),
            ("启动公网访问", callbacks.get('start_public')),
            ("停止服务", callbacks.get('stop')),
            None,  # 分隔符
            ("编辑服务", callbacks.get('edit')),
            ("删除服务", callbacks.get('delete')),
        ]

        for item in actions:
            if item is None:
                menu.addSeparator()
            else:
                name, callback = item
                if callback:
                    action = QAction(name, self)
                    action.triggered.connect(callback)
                    menu.addAction(action)

        menu.exec_(self.service_table.viewport().mapToGlobal(position))

    def show_message(self, title: str, message: str, icon=QMessageBox.Information):
        """显示消息对话框"""
        QMessageBox.information(self, title, message) if icon == QMessageBox.Information else \
        QMessageBox.warning(self, title, message) if icon == QMessageBox.Warning else \
        QMessageBox.critical(self, title, message)

    def show_question(self, title: str, message: str) -> bool:
        """显示确认对话框"""
        return QMessageBox.question(self, title, message) == QMessageBox.Yes

    def copy_to_clipboard(self, text: str):
        """复制文本到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def open_browser(self, url: str):
        """在浏览器中打开URL"""
        import webbrowser
        webbrowser.open(url)

    # ========== 进度条控制 ==========

    def start_progress(self, operation_name: str = "操作"):
        """开始进度条动画"""
        self.progress_label.setText(f"{operation_name}中...")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.set_buttons_enabled(False)

    def stop_progress(self, success: bool = True):
        """停止进度条动画"""
        self.progress_bar.setValue(100 if success else 0)
        if success:
            self.progress_label.setText("完成")
            QTimer.singleShot(1000, self.hide_progress)
        else:
            self.progress_label.setText("失败")
            self.progress_bar.hide()
        self.set_buttons_enabled(True)

    def hide_progress(self):
        """隐藏进度条"""
        self.progress_bar.hide()
        self.progress_label.setText("")

    def set_progress_value(self, value: int):
        """设置进度条值"""
        self.progress_bar.setValue(value)

    def select_row(self, row: int):
        """选中指定行"""
        if 0 <= row < self.service_table.rowCount():
            self.service_table.selectRow(row)
