"""托盘管理模块 - 协调者模式，组合MenuBuilder和EventHandler"""

import threading
from PyQt5.QtWidgets import QSystemTrayIcon
from PyQt5.QtCore import QTimer

from tray_menu_builder import TrayMenuBuilder
from tray_event_handler import TrayEventHandler


class TrayManager:
    """系统托盘管理器 - 作为协调者，组合MenuBuilder和EventHandler（线程安全）

    重构说明:
    - 通过TrayMenuBuilder构建和管理菜单
    - 通过TrayEventHandler处理事件
    - 添加线程锁保护服务列表访问
    - 保持向后兼容性
    """

    def __init__(self, main_window):
        """初始化托盘管理器

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window

        # 线程锁，保护服务列表访问
        self._services_lock = threading.Lock()

        # 初始化菜单构建器
        self.menu_builder = TrayMenuBuilder(main_window)

        # 初始化事件处理器
        self.event_handler = TrayEventHandler(main_window)

        # 初始化托盘
        self._init_tray()

        # 定时更新托盘菜单
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_tray_menu)
        self.update_timer.start(2000)  # 每2秒更新一次

        # 立即更新一次菜单
        self.update_tray_menu()

    def _init_tray(self):
        """初始化托盘图标和菜单"""
        # 构建托盘图标
        self.tray_icon = self.menu_builder.build_tray_icon()

        if not self.tray_icon:
            return

        # 设置事件处理器的托盘图标
        self.event_handler.set_tray_icon(self.tray_icon)

        # 构建托盘菜单
        callbacks = self.event_handler.get_event_callbacks()
        tray_menu = self.menu_builder.build_tray_menu(callbacks)

        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)

        # 连接托盘图标点击事件
        self.tray_icon.activated.connect(self.event_handler.on_tray_activated)

        # 显示托盘图标
        self.tray_icon.show()

    def update_tray_menu(self):
        """更新托盘菜单（线程安全）"""
        # 使用线程锁保护服务列表访问
        with self._services_lock:
            # 获取服务列表
            services = []
            if hasattr(self.main_window, 'manager') and hasattr(self.main_window.manager, 'services'):
                services = list(self.main_window.manager.services)  # 复制列表避免外部修改
            elif hasattr(self.main_window, 'controller') and hasattr(self.main_window.controller.manager, 'services'):
                # 新架构
                services = list(self.main_window.controller.manager.services)  # 复制列表避免外部修改

        # 获取事件回调
        callbacks = self.event_handler.get_event_callbacks()

        # 更新服务菜单
        self.menu_builder.update_service_menu(services, callbacks)

    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.Information, duration=3000):
        """显示托盘消息

        Args:
            title: 消息标题
            message: 消息内容
            icon: 消息图标
            duration: 显示持续时间（毫秒）
        """
        self.event_handler.show_message(title, message, icon, duration)

    def hide(self):
        """隐藏托盘图标"""
        self.event_handler.hide_tray_icon()

    def show(self):
        """显示托盘图标"""
        self.event_handler.show_tray_icon()

    # ========== 向后兼容的公共接口 ==========

    @property
    def tray_icon(self):
        """托盘图标（向后兼容）"""
        return self.menu_builder.get_tray_icon()

    @tray_icon.setter
    def tray_icon(self, value):
        """设置托盘图标"""
        self.menu_builder.tray_icon = value

    @property
    def tray_menu(self):
        """托盘菜单（向后兼容）"""
        return self.menu_builder.get_tray_menu()

    @property
    def service_menu(self):
        """服务菜单（向后兼容）"""
        return self.menu_builder.get_service_menu()

    def _on_restore_window(self):
        """恢复窗口（向后兼容）"""
        self.event_handler.on_restore_window()

    def _on_exit(self):
        """退出程序（向后兼容）"""
        # 停止定时器
        self.update_timer.stop()
        self.event_handler.on_exit()

    def _on_start_service(self, index: int):
        """启动服务（向后兼容）"""
        self.event_handler.start_service(index)

    def _on_stop_service(self, index: int):
        """停止服务（向后兼容）"""
        self.event_handler.stop_service(index)

    def _on_start_public_access(self, index: int):
        """启动公网访问（向后兼容）"""
        self.event_handler.start_public_access(index)

    def _on_stop_public_access(self, index: int):
        """停止公网访问（向后兼容）"""
        self.event_handler.stop_public_access(index)

    def _on_view_logs(self, index: int):
        """查看服务日志（向后兼容）"""
        self.event_handler.view_logs(index)
