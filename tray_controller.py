"""托盘控制器 - 负责托盘管理和消息显示（合并版）"""

import os
from typing import List, Optional, Callable
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon

from service import ServiceStatus


class TrayMenuBuilder:
    """托盘菜单构建器 - 负责菜单创建和状态渲染（内部类）"""

    def __init__(self, main_window, icon_path: str = "icon.ico"):
        """
        初始化菜单构建器

        Args:
            main_window: 主窗口实例
            icon_path: 图标路径
        """
        self.main_window = main_window
        self.icon_path = icon_path
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.tray_menu: Optional[QMenu] = None
        self.service_menu: Optional[QMenu] = None

        # 用于智能更新的状态哈希
        self._last_menu_hash: Optional[int] = None

    def build_tray_icon(self) -> Optional[QSystemTrayIcon]:
        """构建托盘图标

        Returns:
            QSystemTrayIcon: 托盘图标实例
        """
        from constants import get_resource_path

        icon_full_path = get_resource_path(self.icon_path)

        if os.path.exists(icon_full_path):
            icon = QIcon(icon_full_path)
            self.tray_icon = QSystemTrayIcon(icon, self.main_window)
        else:
            self.tray_icon = QSystemTrayIcon(self.main_window)

        self.tray_icon.setToolTip("DufsGUI - 服务管理器")
        self.tray_icon.show()  # 显示托盘图标
        return self.tray_icon

    def build_tray_menu(self, callbacks: dict) -> QMenu:
        """构建托盘菜单

        Args:
            callbacks: 回调函数字典，包含restore、exit等

        Returns:
            QMenu: 托盘菜单
        """
        self.tray_menu = QMenu()

        # 添加恢复窗口动作
        restore_action = QAction("恢复窗口", self.main_window)
        if callbacks.get('restore'):
            restore_action.triggered.connect(callbacks['restore'])
        self.tray_menu.addAction(restore_action)

        # 添加分隔线
        self.tray_menu.addSeparator()

        # 添加服务管理子菜单
        self.service_menu = QMenu("服务管理")
        self.tray_menu.addMenu(self.service_menu)

        # 添加分隔线
        self.tray_menu.addSeparator()

        # 添加退出动作
        exit_action = QAction("退出程序", self.main_window)
        if callbacks.get('exit'):
            exit_action.triggered.connect(callbacks['exit'])
        self.tray_menu.addAction(exit_action)

        return self.tray_menu

    def update_service_menu(self, services: List, callbacks: dict) -> bool:
        """更新服务菜单

        Args:
            services: 服务列表
            callbacks: 回调函数字典，包含start、stop、start_public、stop_public、view_logs

        Returns:
            bool: 是否更新了菜单
        """
        if not self.service_menu:
            return False

        # 计算当前服务状态的哈希值
        current_hash = hash(str([(s.name, s.status, getattr(s, 'public_access_status', 'stopped'))
                                  for s in services]))

        # 如果状态没有变化，跳过更新
        if self._last_menu_hash == current_hash:
            return False

        self._last_menu_hash = current_hash

        # 清空服务管理子菜单
        self.service_menu.clear()

        if services:
            self._build_service_menu_with_services(services, callbacks)
        else:
            self._build_empty_service_menu()

        return True

    def _build_service_menu_with_services(self, services: List, callbacks: dict):
        """构建有服务时的菜单

        Args:
            services: 服务列表
            callbacks: 回调函数字典
        """
        # 添加服务统计信息
        running_count = sum(1 for s in services if s.status == ServiceStatus.RUNNING)
        total_count = len(services)
        stats_action = QAction(f"服务统计: {running_count}/{total_count} 运行中", self.main_window)
        stats_action.setEnabled(False)
        self.service_menu.addAction(stats_action)
        self.service_menu.addSeparator()

        for i, service in enumerate(services):
            # 创建服务操作子菜单
            service_submenu = self._create_service_submenu(service, i, callbacks)
            self.service_menu.addMenu(service_submenu)

    def _create_service_submenu(self, service, index: int, callbacks: dict) -> QMenu:
        """创建服务子菜单

        Args:
            service: 服务实例
            index: 服务索引
            callbacks: 回调函数字典

        Returns:
            QMenu: 服务子菜单
        """
        service_submenu = QMenu()

        # 根据状态设置菜单标题和图标
        status_text = f"{service.name} [{service.status}]"
        status_icon = self._get_status_icon(service.status)
        service_submenu.setTitle(f"{status_icon} {status_text}")

        # 添加启动/停止动作
        if service.status == ServiceStatus.RUNNING:
            stop_action = QAction("⏹ 停止服务", self.main_window)
            if callbacks.get('stop'):
                stop_action.triggered.connect(lambda checked, idx=index: callbacks['stop'](idx))
            service_submenu.addAction(stop_action)
        else:
            start_action = QAction("▶ 启动服务", self.main_window)
            if callbacks.get('start'):
                start_action.triggered.connect(lambda checked, idx=index: callbacks['start'](idx))
            service_submenu.addAction(start_action)

        # 添加公网访问动作
        if service.status == ServiceStatus.RUNNING:
            service_submenu.addSeparator()
            public_status = getattr(service, 'public_access_status', 'stopped')
            if public_status == "running":
                stop_public_action = QAction("🌐 停止公网访问", self.main_window)
                if callbacks.get('stop_public'):
                    stop_public_action.triggered.connect(lambda checked, idx=index: callbacks['stop_public'](idx))
                service_submenu.addAction(stop_public_action)
            else:
                start_public_action = QAction("🌐 启动公网访问", self.main_window)
                if callbacks.get('start_public'):
                    start_public_action.triggered.connect(lambda checked, idx=index: callbacks['start_public'](idx))
                service_submenu.addAction(start_public_action)

        # 添加查看日志动作
        service_submenu.addSeparator()
        log_action = QAction("📋 查看日志", self.main_window)
        if callbacks.get('view_logs'):
            log_action.triggered.connect(lambda checked, idx=index: callbacks['view_logs'](idx))
        service_submenu.addAction(log_action)

        return service_submenu

    def _build_empty_service_menu(self):
        """构建无服务时的菜单"""
        # 添加无服务提示
        no_service_action = QAction("⚠ 无服务配置", self.main_window)
        no_service_action.setEnabled(False)
        self.service_menu.addAction(no_service_action)

        # 添加提示信息
        tip_action = QAction("  请先在主窗口添加服务", self.main_window)
        tip_action.setEnabled(False)
        self.service_menu.addAction(tip_action)

    def _get_status_icon(self, status: str) -> str:
        """获取状态对应的图标

        Args:
            status: 服务状态

        Returns:
            str: 状态图标
        """
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


class TrayController:
    """托盘控制器 - 负责托盘管理和消息显示（合并版）"""

    def __init__(self, main_window):
        """
        初始化托盘控制器

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        self.menu_builder: Optional[TrayMenuBuilder] = None

    def init_tray_manager(self):
        """初始化托盘管理器（简化版）

        Returns:
            TrayMenuBuilder: 菜单构建器实例
        """
        self.menu_builder = TrayMenuBuilder(self.main_window)
        # 创建并显示托盘图标
        self.menu_builder.build_tray_icon()
        # 创建托盘菜单
        callbacks = {
            'restore': self.restore_window,
            'exit': self.exit_application
        }
        tray_menu = self.menu_builder.build_tray_menu(callbacks)
        # 设置托盘图标菜单
        if self.menu_builder.tray_icon:
            self.menu_builder.tray_icon.setContextMenu(tray_menu)
            # 连接双击信号（左键双击恢复窗口）
            self.menu_builder.tray_icon.activated.connect(self._on_tray_activated)
        return self.menu_builder

    def _on_tray_activated(self, reason):
        """托盘图标激活事件处理"""
        # reason 1 = 左键单击, 2 = 右键单击, 3 = 双击
        # 只有双击(reason=3)时才恢复窗口，其他情况不处理（右键菜单由setContextMenu自动处理）
        if reason == 3:  # 双击
            self.restore_window()

    def restore_window(self):
        """恢复主窗口"""
        if self.main_window:
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()

    def exit_application(self):
        """退出应用程序"""
        if self.main_window:
            self.main_window.close()

    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.Information, duration: int = 3000):
        """显示托盘消息

        Args:
            title: 消息标题
            message: 消息内容
            icon: 消息图标
            duration: 显示持续时间（毫秒）
        """
        if self.menu_builder and self.menu_builder.tray_icon:
            self.menu_builder.tray_icon.showMessage(title, message, icon, duration)

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
