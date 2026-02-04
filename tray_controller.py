"""托盘控制器 - 负责托盘管理和消息显示"""

from typing import Optional
from PyQt5.QtWidgets import QSystemTrayIcon

from tray_manager import TrayManager


class TrayController:
    """托盘控制器 - 负责托盘管理和消息显示"""

    def __init__(self, main_window):
        """
        初始化托盘控制器

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        self.tray_manager: Optional[TrayManager] = None

    def init_tray_manager(self) -> Optional[TrayManager]:
        """初始化托盘管理器

        Returns:
            TrayManager: 托盘管理器实例
        """
        self.tray_manager = TrayManager(self.main_window)
        return self.tray_manager

    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.Information, duration: int = 3000):
        """显示托盘消息

        Args:
            title: 消息标题
            message: 消息内容
            icon: 消息图标
            duration: 显示持续时间（毫秒）
        """
        if self.tray_manager:
            self.tray_manager.show_message(title, message, icon, duration)

    def hide(self):
        """隐藏托盘图标"""
        if self.tray_manager:
            self.tray_manager.hide()

    def show(self):
        """显示托盘图标"""
        if self.tray_manager:
            self.tray_manager.show()

    def get_tray_manager(self) -> Optional[TrayManager]:
        """获取托盘管理器"""
        return self.tray_manager
