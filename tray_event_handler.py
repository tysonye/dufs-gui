"""托盘事件处理器 - 负责托盘事件处理和服务操作"""

from typing import Optional
from PyQt5.QtWidgets import QSystemTrayIcon


class TrayEventHandler:
    """托盘事件处理器 - 负责事件处理和服务操作"""

    def __init__(self, main_window, tray_icon: Optional[QSystemTrayIcon] = None):
        """
        初始化事件处理器

        Args:
            main_window: 主窗口实例
            tray_icon: 托盘图标实例
        """
        self.main_window = main_window
        self.tray_icon = tray_icon

    def set_tray_icon(self, tray_icon: QSystemTrayIcon):
        """设置托盘图标"""
        self.tray_icon = tray_icon

    def on_tray_activated(self, reason):
        """托盘图标激活事件

        Args:
            reason: 激活原因
        """
        if reason == QSystemTrayIcon.Trigger:
            self.on_restore_window()

    def on_restore_window(self):
        """恢复窗口"""
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        elif not self.main_window.isVisible():
            self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def on_exit(self):
        """退出程序"""
        if self.tray_icon:
            self.tray_icon.hide()

        # 调用主窗口的退出方法
        if hasattr(self.main_window, '_on_exit'):
            self.main_window._on_exit()
        else:
            self.main_window.close()

    def _get_controller(self):
        """获取控制器（支持新旧架构）"""
        if hasattr(self.main_window, 'controller'):
            return self.main_window.controller
        return None

    def start_service(self, index: int):
        """启动服务"""
        controller = self._get_controller()
        if controller:
            controller.view.select_row(index)
            controller.start_service()

    def stop_service(self, index: int):
        """停止服务"""
        controller = self._get_controller()
        if controller:
            controller.view.select_row(index)
            controller.stop_service()

    def start_public_access(self, index: int):
        """启动公网访问"""
        controller = self._get_controller()
        if controller:
            controller.view.select_row(index)
            controller.start_public_access()

    def stop_public_access(self, index: int):
        """停止公网访问"""
        controller = self._get_controller()
        if controller:
            controller.view.select_row(index)
            # 获取服务并停止公网访问
            if index < len(controller.manager.services):
                service = controller.manager.services[index]
                if hasattr(service, 'stop_public_access'):
                    service.stop_public_access(controller.log_manager)

    def view_logs(self, index: int):
        """查看服务日志"""
        controller = self._get_controller()
        if controller:
            controller.view.select_row(index)
            controller.open_log_window()

    def show_message(self, title: str, message: str,
                     icon=QSystemTrayIcon.Information, duration: int = 3000):
        """显示托盘消息"""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, duration)

    def hide_tray_icon(self):
        """隐藏托盘图标"""
        if self.tray_icon:
            self.tray_icon.hide()

    def show_tray_icon(self):
        """显示托盘图标"""
        if self.tray_icon:
            self.tray_icon.show()

    def get_event_callbacks(self) -> dict:
        """获取事件回调函数字典"""
        return {
            'restore': self.on_restore_window,
            'exit': self.on_exit,
            'start': self.start_service,
            'stop': self.stop_service,
            'start_public': self.start_public_access,
            'stop_public': self.stop_public_access,
            'view_logs': self.view_logs,
        }
