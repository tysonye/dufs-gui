"""服务控制器 - 负责服务的CRUD操作和启动/停止控制"""

import threading
import time
from typing import Optional, Callable
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QDialog

from service import DufsService, ServiceStatus
from service_manager import ServiceManager
from log_manager import LogManager
from service_dialog import DufsServiceDialog


class ServiceController(QObject):
    """服务控制器 - 负责服务CRUD和生命周期管理"""

    # 信号定义
    service_updated = pyqtSignal()
    progress_updated = pyqtSignal(int)
    operation_started = pyqtSignal(str)
    operation_finished = pyqtSignal(bool)

    def __init__(self, manager: ServiceManager, log_manager: LogManager, view=None):
        super().__init__()
        self.manager = manager
        self.log_manager = log_manager
        self.view = view
        self.is_operation_in_progress = False

    def set_view(self, view):
        """设置视图"""
        self.view = view

    def add_service(self) -> bool:
        """添加服务"""
        dialog = DufsServiceDialog(parent=self.view, existing_services=self.manager.services)
        if dialog.exec_() == QDialog.Accepted:
            # 自动更换重复的服务名称
            unique_name = self._generate_unique_service_name(dialog.service.name)
            dialog.service.name = unique_name

            # 检查端口冲突
            try:
                current_port = int(dialog.service.port)
                conflict_service = next(
                    (s for s in self.manager.services if int(s.port) == current_port),
                    None
                )
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

            # 添加服务
            self.manager.add_service(dialog.service)
            self.service_updated.emit()
            return True
        return False

    def edit_service(self, row: int) -> bool:
        """编辑服务"""
        if row < 0 or row >= len(self.manager.services):
            return False

        service = self.manager.services[row]
        was_running = service.status == ServiceStatus.RUNNING
        was_public_running = getattr(service, 'public_access_status', '') == "running"
        old_port = int(service.port)

        # 记录原始配置
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

        dialog = DufsServiceDialog(parent=self.view, service=service, edit_index=row, existing_services=self.manager.services)
        if dialog.exec_() == QDialog.Accepted:
            # 自动更换重复的服务名称
            unique_name = self._generate_unique_service_name(dialog.service.name, exclude_index=row)
            dialog.service.name = unique_name

            # 检查配置是否有变化
            has_changes = any(
                original_data[key] != getattr(dialog.service, key, '')
                for key in original_data
            )

            # 如果服务正在运行且有配置变化，先停止它
            if was_running and has_changes:
                self._stop_service_internal(service, was_public_running)

            # 释放旧端口
            try:
                self.manager.release_allocated_port(old_port)
            except ValueError:
                pass

            # 检查端口冲突
            try:
                current_port = int(dialog.service.port)
                conflict_service = next(
                    (s for i, s in enumerate(self.manager.services) if i != row and int(s.port) == current_port),
                    None
                )
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
            self.service_updated.emit()

            # 如果服务之前在运行且有配置变化，重启它
            if was_running and has_changes:
                updated_service = self.manager.services[row]
                time.sleep(0.1)
                threading.Thread(target=updated_service.start, args=(self.log_manager,), daemon=True).start()
                if was_public_running:
                    time.sleep(1)
                    threading.Thread(target=updated_service.start_public_access, args=(self.log_manager,), daemon=True).start()

            return True
        return False

    def delete_service(self, row: int) -> bool:
        """删除服务"""
        if row < 0 or row >= len(self.manager.services):
            return False

        service = self.manager.services[row]

        # 自动停止服务
        if service.status == ServiceStatus.RUNNING:
            self._stop_service_internal(service, False)

        # 删除服务
        self.manager.remove_service(row)
        self.service_updated.emit()
        return True

    def start_service(self, row: int) -> bool:
        """启动服务"""
        if self.is_operation_in_progress:
            return False

        if row < 0 or row >= len(self.manager.services):
            return False

        service = self.manager.services[row]
        if service.status == ServiceStatus.RUNNING:
            return False
        if service.status == ServiceStatus.STARTING:
            return False

        # 检查端口
        try:
            current_port = int(service.port)
            conflict_service = next(
                (s for i, s in enumerate(self.manager.services) if i != row and int(s.port) == current_port),
                None
            )

            if conflict_service:
                self.manager.release_allocated_port(current_port)
                new_port = self.manager.find_available_port(current_port + 1)
                service.port = str(new_port)
            else:
                self.manager.release_allocated_port(current_port)
                new_port = self.manager.find_available_port(current_port)
                if new_port != current_port:
                    service.port = str(new_port)
        except ValueError:
            return False

        self.is_operation_in_progress = True
        self.operation_started.emit("启动内网共享")

        # 启动服务
        threading.Thread(target=service.start, args=(self.log_manager,), daemon=True).start()

        # 监控进度
        def monitor_progress():
            max_wait = 100
            wait_count = 0
            while wait_count < max_wait:
                time.sleep(0.1)
                wait_count += 1

                if service.status == ServiceStatus.RUNNING:
                    self.is_operation_in_progress = False
                    self.operation_finished.emit(True)
                    return
                elif service.status == ServiceStatus.ERROR:
                    self.is_operation_in_progress = False
                    self.operation_finished.emit(False)
                    return
                else:
                    progress = min(80 + wait_count, 95)
                    self.progress_updated.emit(progress)

            self.is_operation_in_progress = False
            self.operation_finished.emit(False)

        QTimer.singleShot(200, monitor_progress)
        return True

    def stop_service(self, row: int) -> bool:
        """停止服务"""
        if self.is_operation_in_progress:
            return False

        if row < 0 or row >= len(self.manager.services):
            return False

        service = self.manager.services[row]
        if service.status == ServiceStatus.STOPPED and service.public_access_status != "running":
            return False

        self.is_operation_in_progress = True
        self.operation_started.emit("停止共享服务")

        # 停止服务
        threading.Thread(target=service.stop, args=(self.log_manager,), daemon=True).start()

        # 监控进度
        def monitor_stop_progress():
            max_wait = 100
            wait_count = 0
            while wait_count < max_wait:
                time.sleep(0.1)
                wait_count += 1

                if service.status == ServiceStatus.STOPPED:
                    self.is_operation_in_progress = False
                    self.operation_finished.emit(True)
                    return
                elif service.status == ServiceStatus.ERROR:
                    self.is_operation_in_progress = False
                    self.operation_finished.emit(False)
                    return
                else:
                    progress = min(80 + wait_count, 95)
                    self.progress_updated.emit(progress)

            self.is_operation_in_progress = False
            self.operation_finished.emit(False)

        QTimer.singleShot(200, monitor_stop_progress)
        return True

    def _stop_service_internal(self, service: DufsService, stop_public: bool = True):
        """内部停止服务（不更新UI）"""
        # 停止公网服务
        if stop_public and getattr(service, 'public_access_status', '') == "running":
            try:
                if hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                    service.cloudflared_process.terminate()
                    service.cloudflared_process.wait(timeout=5)
                    service.cloudflared_process = None
            except Exception as e:
                print(f"终止cloudflared进程失败: {str(e)}")

        # 停止内网服务
        if service.process:
            try:
                service.process.terminate()
                service.process.wait(timeout=5)
                service.process = None
            except Exception as e:
                print(f"终止服务进程失败: {str(e)}")

        # 强制更新服务状态为已停止
        with service.lock:
            service.status = ServiceStatus.STOPPED
        service.status_updated.emit()
        if hasattr(service, 'public_access_status'):
            service.public_access_status = "stopped"
            service.status_updated.emit()

    def _generate_unique_service_name(self, base_name: str, exclude_index: int = None) -> str:
        """生成唯一的服务名称"""
        existing_names = [
            service.name for i, service in enumerate(self.manager.services)
            if exclude_index is None or i != exclude_index
        ]

        if base_name not in existing_names:
            return base_name

        counter = 1
        while counter <= 1000:
            new_name = f"{base_name}_{counter}"
            if new_name not in existing_names:
                return new_name
            counter += 1

        return f"{base_name}_{int(time.time())}"

    def _on_service_status_updated(self):
        """处理服务状态更新"""
        self.service_updated.emit()
