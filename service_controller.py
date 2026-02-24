"""服务控制器 - 负责服务的CRUD操作和启动/停止控制"""

import subprocess
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

    def _resolve_port_conflict(self, port: int, exclude_index: int = None) -> int:
        """解析端口冲突，返回可用端口

        Args:
            port: 首选端口
            exclude_index: 排除的服务索引（编辑时使用）

        Returns:
            int: 可用端口号
        """
        try:
            current_port = int(port)
            # 检查端口冲突
            conflict_service = next(
                (s for i, s in enumerate(self.manager.services)
                 if (exclude_index is None or i != exclude_index) and int(s.port) == current_port),
                None
            )
            if conflict_service:
                # 有冲突，查找新端口
                return self.manager.find_available_port(current_port)
            else:
                # 无冲突，但仍需验证端口可用性
                return self.manager.find_available_port(current_port)
        except ValueError:
            # 端口无效，使用默认端口
            return self.manager.find_available_port(5001)

    def add_service(self) -> bool:
        """添加服务"""
        dialog = DufsServiceDialog(parent=self.view, existing_services=self.manager.services)
        if dialog.exec_() == QDialog.Accepted:
            # 自动更换重复的服务名称
            unique_name = self.manager.generate_unique_service_name(dialog.service.name)
            dialog.service.name = unique_name

            # 检查并解析端口冲突
            new_port = self._resolve_port_conflict(dialog.service.port)
            dialog.service.port = str(new_port)

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
            unique_name = self.manager.generate_unique_service_name(dialog.service.name, exclude_index=row)
            dialog.service.name = unique_name

            # 检查配置是否有变化
            has_changes = any(
                original_data[key] != getattr(dialog.service, key, '')
                for key in original_data
            )

            # 记录修改内容到日志
            if self.log_manager and has_changes:
                changes = []
                if original_data['name'] != dialog.service.name:
                    changes.append(f"名称: '{original_data['name']}' -> '{dialog.service.name}'")
                if original_data['serve_path'] != dialog.service.serve_path:
                    changes.append(f"路径: '{original_data['serve_path']}' -> '{dialog.service.serve_path}'")
                if original_data['port'] != dialog.service.port:
                    changes.append(f"端口: {original_data['port']} -> {dialog.service.port}")
                if original_data['bind'] != dialog.service.bind:
                    changes.append(f"绑定: '{original_data['bind']}' -> '{dialog.service.bind}'")
                if original_data['allow_upload'] != dialog.service.allow_upload:
                    changes.append(f"允许上传: {original_data['allow_upload']} -> {dialog.service.allow_upload}")
                if original_data['allow_delete'] != dialog.service.allow_delete:
                    changes.append(f"允许删除: {original_data['allow_delete']} -> {dialog.service.allow_delete}")
                if original_data['allow_search'] != dialog.service.allow_search:
                    changes.append(f"允许搜索: {original_data['allow_search']} -> {dialog.service.allow_search}")
                if original_data['allow_archive'] != dialog.service.allow_archive:
                    changes.append(f"允许归档: {original_data['allow_archive']} -> {dialog.service.allow_archive}")
                if original_data['allow_all'] != dialog.service.allow_all:
                    changes.append(f"允许所有: {original_data['allow_all']} -> {dialog.service.allow_all}")
                if original_data['auth_user'] != dialog.service.auth_user:
                    changes.append(f"认证用户变更")
                
                if changes:
                    change_str = "; ".join(changes)
                    self.log_manager.info(f"修改服务配置: {change_str}", unique_name)

            # 如果服务正在运行且有配置变化，先停止它
            if was_running and has_changes:
                if self.log_manager:
                    self.log_manager.info(f"服务配置变更，正在停止服务以应用更改", unique_name)
                self._stop_service_internal(service, was_public_running)
                # 等待服务完全停止，使用状态检查代替固定时间
                self._wait_for_service_stop(service, timeout=5.0)

            # 释放旧端口
            try:
                self.manager.release_allocated_port(old_port)
            except ValueError:
                pass

            # 检查并解析端口冲突
            new_port = self._resolve_port_conflict(dialog.service.port, exclude_index=row)
            dialog.service.port = str(new_port)

            # 连接服务状态更新信号
            dialog.service.status_updated.connect(self._on_service_status_updated)

            # 更新服务
            self.manager.edit_service(row, dialog.service)
            self.service_updated.emit()
            
            if self.log_manager:
                self.log_manager.info(f"服务配置已更新", unique_name)

            # 如果服务之前在运行且有配置变化，重启它
            if was_running and has_changes:
                updated_service = self.manager.services[row]
                # 确保服务状态已更新为已停止
                if updated_service.status != ServiceStatus.STOPPED:
                    updated_service.status = ServiceStatus.STOPPED
                    updated_service.status_updated.emit()

                # 禁用按钮，防止用户在重启过程中操作
                if self.view and hasattr(self.view, 'set_buttons_enabled'):
                    self.view.set_buttons_enabled(False)
                self.is_operation_in_progress = True

                try:
                    # 等待状态稳定
                    time.sleep(0.3)
                    # 使用主线程启动服务，避免并发问题
                    updated_service.start(self.log_manager)
                    if was_public_running:
                        time.sleep(0.5)
                        updated_service.start_public_access(self.log_manager)
                finally:
                    # 恢复按钮状态
                    self.is_operation_in_progress = False
                    if self.view and hasattr(self.view, 'set_buttons_enabled'):
                        self.view.set_buttons_enabled(True)

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
        """启动服务（带竞态条件保护）"""
        # 原子性检查：使用锁保护操作状态和服务状态检查
        with self.manager._port_lock:
            if self.is_operation_in_progress:
                return False

            if row < 0 or row >= len(self.manager.services):
                return False

            service = self.manager.services[row]
            # 检查服务状态，避免重复启动
            if service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                return False

            # 设置操作状态（在锁内完成，确保原子性）
            self.is_operation_in_progress = True

        # 检查端口（在锁外执行，避免长时间持有锁）
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
            self.is_operation_in_progress = False
            return False

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
        """停止服务（带竞态条件保护）"""
        # 原子性检查：使用锁保护操作状态和服务状态检查
        with self.manager._port_lock:
            if self.is_operation_in_progress:
                return False

            if row < 0 or row >= len(self.manager.services):
                return False

            service = self.manager.services[row]
            # 检查服务状态，避免重复停止
            if service.status == ServiceStatus.STOPPED and service.public_access_status != "running":
                return False

            # 设置操作状态（在锁内完成，确保原子性）
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
        """内部停止服务（不更新UI，带超时保护）"""
        # 停止公网服务
        if stop_public and getattr(service, 'public_access_status', '') == "running":
            try:
                if hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                    service.cloudflared_process.terminate()
                    try:
                        service.cloudflared_process.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        # 超时后强制终止
                        try:
                            service.cloudflared_process.kill()
                            service.cloudflared_process.wait(timeout=2.0)
                        except Exception as kill_error:
                            if self.log_manager:
                                self.log_manager.warning(f"强制终止cloudflared进程失败: {str(kill_error)}", service.name)
                    service.cloudflared_process = None
            except (OSError, subprocess.SubprocessError) as e:
                if self.log_manager:
                    self.log_manager.warning(f"终止cloudflared进程失败: {str(e)}", service.name)

        # 停止内网服务
        if service.process:
            try:
                service.process.terminate()
                try:
                    service.process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    # 超时后强制终止
                    try:
                        service.process.kill()
                        service.process.wait(timeout=2.0)
                    except Exception as kill_error:
                        if self.log_manager:
                            self.log_manager.warning(f"强制终止服务进程失败: {str(kill_error)}", service.name)
                service.process = None
            except (OSError, subprocess.SubprocessError) as e:
                if self.log_manager:
                    self.log_manager.warning(f"终止服务进程失败: {str(e)}", service.name)

        # 强制更新服务状态为已停止
        with service.lock:
            service.status = ServiceStatus.STOPPED
        service.status_updated.emit()
        if hasattr(service, 'public_access_status'):
            service.public_access_status = "stopped"
            service.status_updated.emit()

    def _wait_for_service_stop(self, service: DufsService, timeout: float = 5.0) -> bool:
        """等待服务完全停止（非阻塞实现）

        Args:
            service: 服务实例
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功停止
        """
        # 使用 QTimer 实现非阻塞等待
        self._stop_check_count = 0
        self._stop_check_max = int(timeout * 10)  # 每100ms检查一次
        self._stop_result = False

        def check_stopped():
            self._stop_check_count += 1
            if service.status == ServiceStatus.STOPPED:
                self._stop_result = True
                if hasattr(self, '_stop_timer') and self._stop_timer:
                    self._stop_timer.stop()
                return

            if self._stop_check_count >= self._stop_check_max:
                # 超时后强制设置状态
                if service.status != ServiceStatus.STOPPED:
                    service.status = ServiceStatus.STOPPED
                    service.status_updated.emit()
                if hasattr(self, '_stop_timer') and self._stop_timer:
                    self._stop_timer.stop()

        self._stop_timer = QTimer()
        self._stop_timer.timeout.connect(check_stopped)
        self._stop_timer.start(100)  # 每100ms检查一次

        # 立即检查一次
        check_stopped()

        return self._stop_result

    def _on_service_status_updated(self):
        """处理服务状态更新"""
        self.service_updated.emit()
