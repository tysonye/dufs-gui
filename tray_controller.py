"""托盘控制器 - 负责托盘管理和消息显示（增强版）

功能增强：
1. 动态托盘图标 - 根据服务状态实时变化
2. 丰富托盘菜单 - 常用操作快捷入口
3. 托盘状态实时更新 - 监控服务状态变化
4. 增强稳定性 - 添加异常保护和恢复机制
5. 性能优化 - 智能更新，避免频繁刷新
"""

import os
import threading
import time
from typing import List, Optional, Callable, Dict
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QColor, QFont
from PyQt5.QtCore import QTimer, Qt, QObject, pyqtSignal

from service import ServiceStatus


class TrayIconGenerator:
    """托盘图标生成器 - 动态生成状态相关图标"""

    @staticmethod
    def create_status_icon(status_summary: str) -> QIcon:
        """根据服务状态摘要创建图标

        Args:
            status_summary: 服务状态摘要，如 "2/3" 表示2个服务运行中

        Returns:
            QIcon: 动态生成的图标
        """
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 根据状态确定颜色
        if "0/" in status_summary or "/" not in status_summary:
            # 无服务运行 - 灰色
            color = QColor(158, 158, 158)
        elif status_summary.startswith("1/"):
            # 部分服务运行 - 橙色
            color = QColor(245, 158, 11)
        elif "运行中" in status_summary or "满" in status_summary:
            # 全部运行 - 绿色
            color = QColor(16, 185, 129)
        else:
            # 默认蓝色
            color = QColor(59, 130, 246)

        # 绘制圆形背景
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)

        # 绘制服务器图标形状
        painter.setPen(QColor(255, 255, 255))
        painter.setBrush(QColor(255, 255, 255))

        # 服务器矩形
        painter.drawRect(8, 10, 16, 3)
        painter.drawRect(8, 15, 16, 3)
        painter.drawRect(8, 20, 16, 3)

        # 指示灯
        if "运行" in status_summary or "1/" in status_summary or "满" in status_summary:
            painter.setBrush(QColor(16, 185, 129))
        else:
            painter.setBrush(QColor(100, 100, 100))
        painter.drawEllipse(10, 11, 2, 2)
        painter.drawEllipse(10, 16, 2, 2)
        painter.drawEllipse(10, 21, 2, 2)

        painter.end()

        return QIcon(pixmap)

    @staticmethod
    def create_simple_icon(color: QColor, symbol: str = "D") -> QIcon:
        """创建简单图标

        Args:
            color: 图标颜色
            symbol: 符号字符

        Returns:
            QIcon: 生成的图标
        """
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制圆形背景
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)

        # 绘制文字
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 14, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, symbol)

        painter.end()

        return QIcon(pixmap)


class TrayMenuBuilder:
    """托盘菜单构建器 - 负责菜单创建和状态渲染（增强版）"""

    # 菜单样式配置
    MENU_STYLE = """
    QMenu {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 6px;
    }
    QMenu::item {
        padding: 8px 24px;
        border-radius: 6px;
        color: #1E293B;
    }
    QMenu::item:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #EFF6FF, stop:1 #DBEAFE);
        color: #1E40AF;
    }
    QMenu::separator {
        height: 1px;
        background: #E2E8F0;
        margin: 4px 8px;
    }
    """

    def __init__(self, main_window, icon_path: str = "icon.ico"):
        """初始化菜单构建器"""
        self.main_window = main_window
        self.icon_path = icon_path
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.tray_menu: Optional[QMenu] = None
        self.service_menu: Optional[QMenu] = None

        # 状态哈希，用于智能更新
        self._last_menu_hash: Optional[int] = None
        # 最后更新时间
        self._last_update_time: float = 0
        # 最小更新间隔（毫秒）
        self._min_update_interval: int = 500
        # 缓存的图标
        self._icon_cache: Dict[str, QIcon] = {}

    def build_tray_icon(self, status_summary: str = "0/0") -> Optional[QSystemTrayIcon]:
        """构建托盘图标（增强版，支持动态图标）"""
        from constants import get_resource_path

        # 优先使用自定义图标
        icon_full_path = get_resource_path(self.icon_path)

        if os.path.exists(icon_full_path):
            icon = QIcon(icon_full_path)
            self.tray_icon = QSystemTrayIcon(icon, self.main_window)
        else:
            # 使用动态图标
            self.tray_icon = QSystemTrayIcon(
                TrayIconGenerator.create_status_icon(status_summary),
                self.main_window
            )

        # 设置工具提示（显示详细状态）
        self._update_tooltip(status_summary)
        self.tray_icon.show()

        return self.tray_icon

    def _update_tooltip(self, status_summary: str):
        """更新工具提示"""
        tooltip_lines = [
            "DufsGUI - 文件共享服务管理",
            f"服务状态: {status_summary}",
            "双击打开主窗口"
        ]
        self.tray_icon.setToolTip("\n".join(tooltip_lines))

    def update_icon_and_menu(self, services: List, callbacks: dict, force: bool = False) -> bool:
        """更新托盘图标和菜单

        Args:
            services: 服务列表
            callbacks: 回调函数字典
            force: 是否强制更新

        Returns:
            bool: 是否更新了界面
        """
        current_time = time.time() * 1000

        # 计算当前状态哈希
        running_count = sum(1 for s in services if s.status == ServiceStatus.RUNNING)
        total_count = len(services)
        status_summary = f"{running_count}/{total_count}"

        current_hash = hash((
            tuple((s.name, s.status, getattr(s, 'public_access_status', 'stopped')) for s in services),
            status_summary
        ))

        # 检查是否需要更新
        if not force and self._last_menu_hash == current_hash:
            if current_time - self._last_update_time < self._min_update_interval:
                return False

        self._last_menu_hash = current_hash
        self._last_update_time = current_time

        # 更新图标
        self._update_icon(status_summary)

        # 更新菜单
        self._update_menu(services, callbacks)

        # 更新工具提示
        self._update_tooltip(status_summary)

        return True

    def _update_icon(self, status_summary: str):
        """更新托盘图标"""
        if not self.tray_icon:
            return

        # 使用缓存的图标
        if status_summary not in self._icon_cache:
            self._icon_cache[status_summary] = TrayIconGenerator.create_status_icon(status_summary)

        # 只有在图标不同时才更新
        current_icon = self.tray_icon.icon()
        new_icon = self._icon_cache[status_summary]
        if current_icon.pixmap(32).toImage() != new_icon.pixmap(32).toImage():
            self.tray_icon.setIcon(new_icon)

    def _update_menu(self, services: List, callbacks: dict):
        """更新托盘菜单"""
        if not self.tray_menu:
            return

        # 清空并重建服务子菜单
        self.service_menu.clear()

        if services:
            self._build_service_menu_with_services(services, callbacks)
        else:
            self._build_empty_service_menu()

    def build_tray_menu(self, callbacks: dict) -> QMenu:
        """构建托盘菜单（增强版）"""
        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet(self.MENU_STYLE)

        # ========== 快捷操作区域 ==========
        quick_actions_header = QAction("⚡ 快捷操作", self.main_window)
        quick_actions_header.setEnabled(False)
        quick_actions_header.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.tray_menu.addAction(quick_actions_header)

        # 全部启动
        if callbacks.get('start_all'):
            start_all_action = QAction("▶ 启动全部服务", self.main_window)
            start_all_action.triggered.connect(callbacks['start_all'])
            self.tray_menu.addAction(start_all_action)

        # 全部停止
        if callbacks.get('stop_all'):
            stop_all_action = QAction("⏹ 停止全部服务", self.main_window)
            stop_all_action.triggered.connect(callbacks['stop_all'])
            self.tray_menu.addAction(stop_all_action)

        self.tray_menu.addSeparator()

        # ========== 服务管理区域 ==========
        services_header = QAction("📁 服务管理", self.main_window)
        services_header.setEnabled(False)
        services_header.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.tray_menu.addAction(services_header)

        # 服务子菜单
        self.service_menu = QMenu("管理服务列表", self.main_window)
        self.tray_menu.addMenu(self.service_menu)

        # 填充服务列表
        self._update_menu_services(callbacks)

        self.tray_menu.addSeparator()

        # ========== 主窗口操作 ==========
        # 显示主窗口
        if callbacks.get('restore'):
            restore_action = QAction("📺 显示主窗口", self.main_window)
            restore_action.triggered.connect(callbacks['restore'])
            self.tray_menu.addAction(restore_action)

        # 查看日志
        if callbacks.get('view_logs'):
            log_action = QAction("📋 查看日志", self.main_window)
            log_action.triggered.connect(callbacks['view_logs'])
            self.tray_menu.addAction(log_action)

        # 检查更新
        if callbacks.get('check_update'):
            update_action = QAction("🔄 检查 Cloudflared 更新", self.main_window)
            update_action.triggered.connect(callbacks['check_update'])
            self.tray_menu.addAction(update_action)

        self.tray_menu.addSeparator()

        # ========== 底部操作 ==========
        # 退出程序
        if callbacks.get('exit'):
            exit_action = QAction("❌ 退出程序", self.main_window)
            exit_action.setFont(QFont("Microsoft YaHei", 9))
            exit_action.triggered.connect(callbacks['exit'])
            self.tray_menu.addAction(exit_action)

        return self.tray_menu

    def _update_menu_services(self, callbacks: dict):
        """更新服务列表（内部方法）"""
        # 获取服务列表（从主窗口）
        services = []
        if hasattr(self.main_window, 'controller') and self.main_window.controller:
            services = self.main_window.controller.manager.services

        if services:
            self._build_service_menu_with_services(services, callbacks)
        else:
            self._build_empty_service_menu()

    def _build_service_menu_with_services(self, services: List, callbacks: dict):
        """构建有服务时的菜单"""
        running_count = sum(1 for s in services if s.status == ServiceStatus.RUNNING)
        total_count = len(services)

        # 服务统计
        stats_action = QAction(f"  运行中: {running_count}/{total_count}", self.main_window)
        stats_action.setEnabled(False)
        stats_action.setFont(QFont("Microsoft YaHei", 9))
        self.service_menu.addAction(stats_action)
        self.service_menu.addSeparator()

        # 逐个显示服务
        for i, service in enumerate(services):
            self._add_service_menu_item(service, i, callbacks)

    def _add_service_menu_item(self, service, index: int, callbacks: dict):
        """添加单个服务菜单项"""
        # 获取服务状态
        status = service.status
        public_status = getattr(service, 'public_access_status', 'stopped')

        # 根据状态生成菜单项
        status_icon = self._get_status_icon(status)
        menu_text = f"{status_icon} {service.name}"

        # 创建服务子菜单
        service_submenu = QMenu(menu_text, self.main_window)

        # 状态显示
        status_display = QAction(f"状态: {status}", self.main_window)
        status_display.setEnabled(False)
        service_submenu.addAction(status_display)

        # 端口显示
        port_display = QAction(f"端口: {service.port}", self.main_window)
        port_display.setEnabled(False)
        service_submenu.addAction(port_display)

        # 公网状态
        if public_status == "running":
            public_url = getattr(service, 'public_url', '')
            if public_url:
                public_display = QAction(f"公网: {public_url[:40]}...", self.main_window)
                public_display.setEnabled(False)
                service_submenu.addAction(public_display)

        service_submenu.addSeparator()

        # 操作按钮
        if status == ServiceStatus.RUNNING:
            # 停止按钮
            if callbacks.get('stop'):
                stop_action = QAction("⏹ 停止", self.main_window)
                stop_action.triggered.connect(lambda checked, idx=index: callbacks['stop'](idx))
                service_submenu.addAction(stop_action)

            # 公网切换
            if public_status == "running":
                if callbacks.get('stop_public'):
                    stop_public_action = QAction("🌐 关闭公网访问", self.main_window)
                    stop_public_action.triggered.connect(lambda checked, idx=index: callbacks['stop_public'](idx))
                    service_submenu.addAction(stop_public_action)
            else:
                if callbacks.get('start_public'):
                    start_public_action = QAction("🌐 开启公网访问", self.main_window)
                    start_public_action.triggered.connect(lambda checked, idx=index: callbacks['start_public'](idx))
                    service_submenu.addAction(start_public_action)
        else:
            # 启动按钮
            if callbacks.get('start'):
                start_action = QAction("▶ 启动", self.main_window)
                start_action.triggered.connect(lambda checked, idx=index: callbacks['start'](idx))
                service_submenu.addAction(start_action)

        service_submenu.addSeparator()

        # 编辑和删除
        if callbacks.get('edit'):
            edit_action = QAction("✏ 编辑服务", self.main_window)
            edit_action.triggered.connect(lambda checked, idx=index: callbacks['edit'](idx))
            service_submenu.addAction(edit_action)

        if callbacks.get('view_logs'):
            log_action = QAction("📋 查看日志", self.main_window)
            log_action.triggered.connect(lambda checked, idx=index: callbacks['view_logs'](idx))
            service_submenu.addAction(log_action)

        self.service_menu.addMenu(service_submenu)

    def _build_empty_service_menu(self):
        """构建无服务时的菜单"""
        no_service_action = QAction("  暂无服务配置", self.main_window)
        no_service_action.setEnabled(False)
        self.service_menu.addAction(no_service_action)

    def _get_status_icon(self, status: str) -> str:
        """获取状态对应的图标"""
        status_icons = {
            ServiceStatus.RUNNING: "🟢",
            ServiceStatus.STARTING: "🔵",
            ServiceStatus.ERROR: "🔴",
            ServiceStatus.STOPPED: "⚪"
        }
        return status_icons.get(status, "⚪")

    def get_tray_icon(self) -> Optional[QSystemTrayIcon]:
        """获取托盘图标"""
        return self.tray_icon

    def get_tray_menu(self) -> Optional[QMenu]:
        """获取托盘菜单"""
        return self.tray_menu

    def get_service_menu(self) -> Optional[QMenu]:
        """获取服务菜单"""
        return self.service_menu


class TrayController(QObject):
    """托盘控制器 - 负责托盘管理和消息显示（增强版）

    信号定义:
        service_state_changed: 服务状态变化时触发
    """

    # 信号定义
    service_state_changed = pyqtSignal()

    def __init__(self, main_window):
        """初始化托盘控制器"""
        super().__init__()
        self.main_window = main_window
        self.menu_builder: Optional[TrayMenuBuilder] = None

        # 状态监控
        self._monitor_timer: Optional[QTimer] = None
        self._last_service_count: int = 0
        self._last_running_count: int = 0

        # 回调函数缓存
        self._callbacks: dict = {}

    def init_tray_manager(self):
        """初始化托盘管理器"""
        self.menu_builder = TrayMenuBuilder(self.main_window)

        # 创建初始图标
        self.menu_builder.build_tray_icon("0/0")

        # 初始化回调
        self._init_callbacks()

        # 创建菜单
        tray_menu = self.menu_builder.build_tray_menu(self._callbacks)

        # 设置托盘图标菜单
        if self.menu_builder.tray_icon:
            self.menu_builder.tray_icon.setContextMenu(tray_menu)

            # 连接信号
            self.menu_builder.tray_icon.activated.connect(self._on_tray_activated)
            self.menu_builder.tray_icon.messageClicked.connect(self._on_message_clicked)

        # 启动状态监控
        self._start_monitoring()

        return self.menu_builder

    def _init_callbacks(self):
        """初始化回调函数"""
        self._callbacks = {
            'restore': self.restore_window,
            'start_all': self._start_all_services,
            'stop_all': self._stop_all_services,
            'start': self._start_service_by_index,
            'stop': self._stop_service_by_index,
            'start_public': self._start_public_by_index,
            'stop_public': self._stop_public_by_index,
            'edit': self._edit_service_by_index,
            'view_logs': self._view_logs_by_index,
            'check_update': self._check_cloudflared_update,
            'exit': self.exit_application
        }

    def _start_monitoring(self):
        """启动状态监控定时器"""
        self._monitor_timer = QTimer(self.main_window)
        self._monitor_timer.timeout.connect(self._check_service_state)
        self._monitor_timer.start(2000)  # 每2秒检查一次

    def _check_service_state(self):
        """检查服务状态变化"""
        if not hasattr(self.main_window, 'controller') or not self.main_window.controller:
            return

        try:
            services = self.main_window.controller.manager.services
            running_count = sum(1 for s in services if s.status == ServiceStatus.RUNNING)

            # 检测到变化时更新托盘
            if len(services) != self._last_service_count or running_count != self._last_running_count:
                self._last_service_count = len(services)
                self._last_running_count = running_count
                self.update_tray()

                # 发出状态变化信号
                self.service_state_changed.emit()
        except Exception as e:
            print(f"检查服务状态失败: {str(e)}")

    def update_tray(self, force: bool = False):
        """更新托盘图标和菜单"""
        if not self.menu_builder:
            return

        try:
            services = []
            if hasattr(self.main_window, 'controller') and self.main_window.controller:
                services = self.main_window.controller.manager.services

            self.menu_builder.update_icon_and_menu(services, self._callbacks, force)
        except Exception as e:
            print(f"更新托盘失败: {str(e)}")

    def _on_tray_activated(self, reason):
        """托盘图标激活事件处理"""
        # 双击恢复窗口
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_window()
        # 单击也恢复窗口（更友好的交互）
        elif reason == QSystemTrayIcon.Trigger:
            self.restore_window()

    def _on_message_clicked(self):
        """托盘消息点击事件"""
        self.restore_window()

    def restore_window(self):
        """恢复主窗口"""
        if not self.main_window:
            return

        try:
            if self.main_window.isMinimized():
                self.main_window.showNormal()
            elif not self.main_window.isVisible():
                self.main_window.show()

            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception as e:
            print(f"恢复窗口失败: {str(e)}")

    def exit_application(self):
        """退出应用程序"""
        if self.main_window:
            self.main_window.close()

    # ========== 服务操作回调 ==========

    def _start_all_services(self):
        """启动所有服务"""
        self._execute_service_operation('start_all')

    def _stop_all_services(self):
        """停止所有服务"""
        self._execute_service_operation('stop_all')

    def _start_service_by_index(self, index: int):
        """根据索引启动服务"""
        self._execute_service_operation('start', index)

    def _stop_service_by_index(self, index: int):
        """根据索引停止服务"""
        self._execute_service_operation('stop', index)

    def _start_public_by_index(self, index: int):
        """根据索引启动公网访问"""
        self._execute_service_operation('start_public', index)

    def _stop_public_by_index(self, index: int):
        """根据索引停止公网访问"""
        self._execute_service_operation('stop_public', index)

    def _edit_service_by_index(self, index: int):
        """根据索引编辑服务"""
        self._execute_service_operation('edit', index)

    def _view_logs_by_index(self, index: int):
        """根据索引查看日志"""
        self._execute_service_operation('view_logs', index)

    def _check_cloudflared_update(self):
        """检查 Cloudflared 更新"""
        self._execute_service_operation('check_update', -1)

    def _execute_service_operation(self, operation: str, index: int = -1):
        """执行服务操作

        Args:
            operation: 操作名称
            index: 服务索引
        """
        if not hasattr(self.main_window, 'controller') or not self.main_window.controller:
            return

        try:
            controller = self.main_window.controller

            # 选中对应行
            if index >= 0:
                if hasattr(self.main_window, 'update_service_tree'):
                    # 视图有选中方法
                    pass

            # 根据操作类型执行
            if operation == 'start_all':
                if hasattr(controller, 'batch_start_services'):
                    controller.batch_start_services()
            elif operation == 'stop_all':
                if hasattr(controller, 'batch_stop_services'):
                    controller.batch_stop_services()
            elif operation == 'start':
                if hasattr(controller, 'start_service'):
                    controller.start_service()
            elif operation == 'stop':
                if hasattr(controller, 'stop_service'):
                    controller.stop_service()
            elif operation == 'start_public':
                if hasattr(controller, 'start_public_access'):
                    controller.start_public_access()
            elif operation == 'stop_public':
                if hasattr(controller, 'stop_service'):
                    controller.stop_service()
            elif operation == 'edit':
                if hasattr(controller, 'edit_service'):
                    controller.edit_service()
            elif operation == 'view_logs':
                if hasattr(controller, 'open_log_window'):
                    controller.open_log_window()
            elif operation == 'check_update':
                if hasattr(controller, 'open_cloudflared_update_dialog'):
                    controller.open_cloudflared_update_dialog()

            # 延迟更新托盘状态
            QTimer.singleShot(500, self.update_tray)

        except Exception as e:
            print(f"执行服务操作失败: {str(e)}")

    def show_message(self, title: str, message: str,
                     icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information,
                     duration: int = 3000):
        """显示托盘消息

        Args:
            title: 消息标题
            message: 消息内容
            icon: 消息图标
            duration: 显示持续时间（毫秒）
        """
        if self.menu_builder and self.menu_builder.tray_icon:
            self.menu_builder.tray_icon.showMessage(title, message, icon, duration)

    def show_service_status_message(self, service_name: str, status: str):
        """显示服务状态消息

        Args:
            service_name: 服务名称
            status: 服务状态
        """
        status_messages = {
            ServiceStatus.RUNNING: f"服务 {service_name} 已启动",
            ServiceStatus.STOPPED: f"服务 {service_name} 已停止",
            ServiceStatus.ERROR: f"服务 {service_name} 启动失败",
            ServiceStatus.STARTING: f"服务 {service_name} 正在启动..."
        }

        message = status_messages.get(status, f"服务 {service_name} 状态: {status}")

        icon = QSystemTrayIcon.Information
        if status == ServiceStatus.ERROR:
            icon = QSystemTrayIcon.Warning
        elif status == ServiceStatus.RUNNING:
            icon = QSystemTrayIcon.Information

        self.show_message("DufsGUI", message, icon, 2000)

    def hide(self):
        """隐藏托盘图标"""
        if self.menu_builder and self.menu_builder.tray_icon:
            self.menu_builder.tray_icon.hide()

    def show(self):
        """显示托盘图标"""
        if self.menu_builder and self.menu_builder.tray_icon:
            self.menu_builder.tray_icon.show()

    def get_menu_builder(self) -> Optional[TrayMenuBuilder]:
        """获取菜单构建器"""
        return self.menu_builder

    def cleanup(self):
        """清理资源"""
        if self._monitor_timer:
            self._monitor_timer.stop()
            self._monitor_timer = None
