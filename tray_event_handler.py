"""托盘事件处理器 - 负责托盘事件处理和服务操作（加强版，带状态同步）"""

import threading
from typing import Optional
from PyQt5.QtWidgets import QSystemTrayIcon
from PyQt5.QtCore import QMetaObject, Qt


class TrayEventHandler:
    """托盘事件处理器 - 负责事件处理和服务操作（加强版）

    改进点：
    1. 托盘只发送"请求"，由 main_controller 仲裁
    2. 添加状态检查，避免重复操作
    3. 使用线程锁保护状态访问
    """

    def __init__(self, main_window, tray_icon: Optional[QSystemTrayIcon] = None):
        """
        初始化事件处理器

        Args:
            main_window: 主窗口实例
            tray_icon: 托盘图标实例
        """
        self.main_window = main_window
        self.tray_icon = tray_icon
        self._lock = threading.Lock()
        self._pending_operations = set()  # 跟踪正在进行的操作

    def set_tray_icon(self, tray_icon: QSystemTrayIcon):
        """设置托盘图标"""
        self.tray_icon = tray_icon

    def _is_operation_pending(self, operation: str) -> bool:
        """检查操作是否正在进行中"""
        with self._lock:
            return operation in self._pending_operations

    def _set_operation_pending(self, operation: str, pending: bool):
        """设置操作状态"""
        with self._lock:
            if pending:
                self._pending_operations.add(operation)
            else:
                self._pending_operations.discard(operation)

    def on_tray_activated(self, reason):
        """托盘图标激活事件

        Args:
            reason: 激活原因
        """
        if reason == QSystemTrayIcon.Trigger:
            # 使用 QMetaObject.invokeMethod 确保在主线程执行
            QMetaObject.invokeMethod(
                self.main_window,
                "show",
                Qt.QueuedConnection
            )
            self.on_restore_window()

    def on_restore_window(self):
        """恢复窗口（线程安全）"""
        # 检查主窗口是否仍然有效
        if not self.main_window:
            return

        # 在主线程中执行UI操作
        def _restore():
            try:
                if self.main_window.isMinimized():
                    self.main_window.showNormal()
                elif not self.main_window.isVisible():
                    self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()
            except Exception as e:
                print(f"恢复窗口失败: {str(e)}")

        # 如果当前不在主线程，使用信号槽机制
        if threading.current_thread() != threading.main_thread():
            QMetaObject.invokeMethod(self.main_window, lambda: _restore(), Qt.QueuedConnection)
        else:
            _restore()

    def on_exit(self):
        """退出程序（带确认和等待）"""
        import time

        # 检查是否有正在进行的操作
        with self._lock:
            if self._pending_operations:
                print(f"[Tray] 有操作正在进行中: {self._pending_operations}")
                # 等待操作完成，最多等待10秒
                max_wait = 10.0
                wait_interval = 0.5
                elapsed = 0
                while self._pending_operations and elapsed < max_wait:
                    time.sleep(wait_interval)
                    elapsed += wait_interval
                    print(f"[Tray] 等待操作完成... {elapsed:.1f}s")

        if self.tray_icon:
            self.tray_icon.hide()

        # 调用主窗口的退出方法
        if hasattr(self.main_window, '_on_exit'):
            self.main_window._on_exit()
        elif hasattr(self.main_window, 'controller'):
            self.main_window.controller.exit_application()
        else:
            self.main_window.close()

    def _get_controller(self):
        """获取控制器（支持新旧架构）"""
        if hasattr(self.main_window, 'controller'):
            return self.main_window.controller
        return None

    def _get_service_status(self, index: int) -> Optional[str]:
        """获取服务状态"""
        controller = self._get_controller()
        if not controller or not hasattr(controller, 'manager'):
            return None

        services = controller.manager.services
        if index < 0 or index >= len(services):
            return None

        return services[index].status

    def start_service(self, index: int):
        """启动服务（带状态检查）"""
        operation_key = f"start_{index}"

        # 检查是否已有相同操作在进行中
        if self._is_operation_pending(operation_key):
            print(f"[Tray] 服务 {index} 启动操作已在进行中，跳过重复请求")
            return

        # 检查服务状态
        status = self._get_service_status(index)
        if status == "运行中":
            print(f"[Tray] 服务 {index} 已在运行中，跳过启动请求")
            return

        controller = self._get_controller()
        if not controller:
            return

        # 标记操作进行中
        self._set_operation_pending(operation_key, True)

        try:
            # 发送请求给 controller 仲裁
            controller.view.select_row(index)
            controller.start_service()
        finally:
            # 延迟清除操作标记（给操作完成时间）
            import threading
            def clear_pending():
                import time
                time.sleep(2)
                self._set_operation_pending(operation_key, False)
            threading.Thread(target=clear_pending, daemon=True).start()

    def stop_service(self, index: int):
        """停止服务（带状态检查）"""
        operation_key = f"stop_{index}"

        if self._is_operation_pending(operation_key):
            print(f"[Tray] 服务 {index} 停止操作已在进行中，跳过重复请求")
            return

        # 检查服务状态
        status = self._get_service_status(index)
        if status == "已停止":
            print(f"[Tray] 服务 {index} 已停止，跳过停止请求")
            return

        controller = self._get_controller()
        if not controller:
            return

        self._set_operation_pending(operation_key, True)

        try:
            controller.view.select_row(index)
            controller.stop_service()
        finally:
            import threading
            def clear_pending():
                import time
                time.sleep(2)
                self._set_operation_pending(operation_key, False)
            threading.Thread(target=clear_pending, daemon=True).start()

    def start_public_access(self, index: int):
        """启动公网访问（带状态检查）"""
        operation_key = f"start_public_{index}"

        if self._is_operation_pending(operation_key):
            print(f"[Tray] 服务 {index} 公网启动操作已在进行中，跳过重复请求")
            return

        controller = self._get_controller()
        if not controller:
            return

        # 检查服务状态
        services = controller.manager.services
        if index >= len(services):
            return

        service = services[index]
        if service.public_access_status == "running":
            print(f"[Tray] 服务 {index} 公网访问已在运行中，跳过启动请求")
            return

        self._set_operation_pending(operation_key, True)

        try:
            controller.view.select_row(index)
            controller.start_public_access()
        finally:
            import threading
            def clear_pending():
                import time
                time.sleep(5)  # 公网启动时间较长
                self._set_operation_pending(operation_key, False)
            threading.Thread(target=clear_pending, daemon=True).start()

    def stop_public_access(self, index: int):
        """停止公网访问（带状态检查）"""
        operation_key = f"stop_public_{index}"

        if self._is_operation_pending(operation_key):
            print(f"[Tray] 服务 {index} 公网停止操作已在进行中，跳过重复请求")
            return

        controller = self._get_controller()
        if not controller:
            return

        # 检查服务状态
        services = controller.manager.services
        if index >= len(services):
            return

        service = services[index]
        if service.public_access_status != "running":
            print(f"[Tray] 服务 {index} 公网访问未在运行中，跳过停止请求")
            return

        self._set_operation_pending(operation_key, True)

        try:
            controller.view.select_row(index)
            if hasattr(service, 'stop_public_access'):
                service.stop_public_access(controller.log_manager)
        finally:
            self._set_operation_pending(operation_key, False)

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
