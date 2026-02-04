"""基础服务模块 - 负责Dufs服务的核心功能"""

import os
import threading
import subprocess
import time
from typing import Optional

from PyQt5.QtCore import pyqtSignal, QObject, QMetaObject, Qt, pyqtSlot

from constants import get_resource_path, AppConstants
from service_state_machine import ServiceStatus, ServiceStateMachine
from cloudflare_tunnel import CloudflareTunnel


class BaseService(QObject):
    """基础服务类 - 负责Dufs服务的核心功能"""

    # 信号定义
    status_updated = pyqtSignal()
    progress_updated = pyqtSignal(int, str)
    log_updated = pyqtSignal(str, bool, str)

    def __init__(self, name: str = "默认服务", serve_path: str = ".", port: str = "5000", bind: str = ""):
        super().__init__()
        self.name = name
        self.serve_path = serve_path
        self.port = port
        self.bind = bind

        # 权限设置
        self.allow_all = False
        self.allow_upload = False
        self.allow_delete = False
        self.allow_search = False
        self.allow_symlink = False
        self.allow_archive = False

        # 多用户权限规则
        self.auth_rules = []

        # 认证配置
        self.auth_user = ""
        self.auth_pass = ""

        # 进程信息
        self.process: Optional[subprocess.Popen] = None
        self.status = ServiceStatus.STOPPED

        # 访问地址
        self.local_addr = ""

        # 线程锁
        self.lock = threading.Lock()

        # 初始化Cloudflare隧道
        self.cloudflare_tunnel = CloudflareTunnel(name)
        self.cloudflare_tunnel.set_callbacks(
            status_callback=self._on_cloudflare_status_changed,
            url_callback=self._on_cloudflare_url_changed
        )

        # 公网访问状态（兼容旧代码）
        self.public_access_status = "stopped"
        self.public_url = ""
        self.cloudflared_process = None
        self.cloudflared_monitor_terminate = False

    def _on_cloudflare_status_changed(self, status: str):
        """Cloudflare状态变更回调"""
        self.public_access_status = status
        self.status_updated.emit()

    def _on_cloudflare_url_changed(self, url: str):
        """Cloudflare URL变更回调"""
        self.public_url = url

    def update_status(self, status: str | None = None, public_access_status: str | None = None) -> bool:
        """统一更新服务状态和公网访问状态（线程安全）

        Args:
            status (str, optional): 服务状态
            public_access_status (str, optional): 公网访问状态

        Returns:
            bool: 状态更新是否成功
        """
        # 创建状态机实例
        state_machine = ServiceStateMachine()

        # 使用线程锁保护整个验证和更新过程
        with self.lock:
            # 增强状态验证
            if status is not None and status not in [ServiceStatus.STOPPED, ServiceStatus.STARTING, ServiceStatus.RUNNING, ServiceStatus.ERROR]:
                print(f"无效的服务状态: {status}")
                return False

            if public_access_status is not None and public_access_status not in ["stopped", "starting", "running", "stopping"]:
                print(f"无效的公网访问状态: {public_access_status}")
                return False

            # 验证状态转换的合法性
            if status is not None:
                if not state_machine.can_transition(self.status, status):
                    return False

            if public_access_status is not None:
                if not state_machine.can_transition(self.public_access_status, public_access_status, public_access=True):
                    return False

            # 验证状态组合的合法性
            new_service_status = status if status is not None else self.status
            new_public_status = public_access_status if public_access_status is not None else self.public_access_status
            if not state_machine.validate_combined_state(new_service_status, new_public_status):
                return False

            # 更新服务状态
            if status is not None:
                self.status = status

            # 更新公网访问状态
            if public_access_status is not None:
                self.public_access_status = public_access_status

        # 发送状态更新信号（在锁外执行，避免死锁）
        if threading.current_thread() != threading.main_thread():
            QMetaObject.invokeMethod(
                self,
                "_emit_status_updated",
                Qt.QueuedConnection
            )
        else:
            self._emit_status_updated()

        return True

    @pyqtSlot()
    def _emit_status_updated(self):
        """在主线程中安全发射状态更新信号"""
        self.status_updated.emit()

    def start(self, log_manager=None) -> bool:
        """启动服务

        Args:
            log_manager: 日志管理器实例

        Returns:
            bool: 启动是否成功
        """
        try:
            # 确保服务未在运行中
            if self.status != ServiceStatus.STOPPED:
                if log_manager:
                    log_manager.append_log(f"服务 '{self.name}' 已在运行中，跳过启动", False, self.name)
                return False

            # 记录启动服务日志
            if log_manager:
                log_manager.append_log(f"开始启动服务 '{self.name}'", False, self.name)

            # 更新服务状态为启动中
            if not self.update_status(ServiceStatus.STARTING):
                if log_manager:
                    log_manager.append_log(f"服务 '{self.name}' 状态转换失败，无法启动", True, self.name)
                return False

            # 检查dufs.exe是否存在
            dufs_path = get_resource_path("dufs.exe")
            if not os.path.exists(dufs_path):
                if log_manager:
                    log_manager.append_log(f"dufs.exe 文件不存在: {dufs_path}", True, self.name)
                self.update_status(ServiceStatus.ERROR)
                return False

            # 构建dufs命令
            cmd = [dufs_path]
            cmd.extend([self.serve_path])
            cmd.extend(["--port", self.port])

            if self.bind:
                cmd.extend(["--bind", self.bind])

            if self.allow_upload:
                cmd.extend(["--allow-upload"])

            if self.allow_delete:
                cmd.extend(["--allow-delete"])

            if self.allow_search:
                cmd.extend(["--allow-search"])

            if self.allow_archive:
                cmd.extend(["--allow-archive"])

            if self.allow_all:
                cmd.extend(["--allow-all"])

            # 添加认证配置
            if self.auth_user and self.auth_pass:
                auth_rule = f"{self.auth_user}:{self.auth_pass}@/:rw"
                cmd.extend(["--auth", auth_rule])

            # 启动进程（隐藏控制台窗口）
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                shell=False,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 等待服务启动
            time.sleep(AppConstants.SERVICE_START_WAIT_SECONDS)

            # 检查服务是否启动成功
            if self.process.poll() is None:
                # 构建本地地址
                try:
                    from utils import get_local_ip
                    ip = get_local_ip()
                    self.local_addr = f"http://{ip}:{self.port}"
                except Exception as e:
                    print(f"构建本地地址失败: {str(e)}")
                    self.local_addr = f"http://localhost:{self.port}"

                # 启动日志线程
                threading.Thread(target=self.read_service_output, args=(log_manager,), daemon=True).start()

                # 更新状态为运行中
                self.update_status(ServiceStatus.RUNNING)

                if log_manager:
                    log_manager.append_log(f"服务 '{self.name}' 启动成功，地址: {self.local_addr}", False, self.name)
                return True
            else:
                # 服务启动失败
                try:
                    output = self.process.stdout.read()
                    if log_manager:
                        log_manager.append_log(f"服务 '{self.name}' 启动失败: {output}", True, self.name)
                except Exception as e:
                    print(f"读取错误输出失败: {str(e)}")
                self.update_status(ServiceStatus.ERROR)
                return False
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"启动服务失败: {str(e)}", True, self.name)
            self.update_status(ServiceStatus.ERROR)
            return False

    def stop(self, log_manager=None) -> bool:
        """停止服务

        Args:
            log_manager: 日志管理器实例

        Returns:
            bool: 停止是否成功
        """
        try:
            # 确保服务正在运行
            if self.status == ServiceStatus.STOPPED:
                if log_manager:
                    log_manager.append_log(f"服务 '{self.name}' 已停止，无需停止", False, self.name)
                return False

            # 记录停止服务日志
            if log_manager:
                log_manager.append_log(f"开始停止服务 '{self.name}'", False, self.name)

            # 停止公网共享
            if self.public_access_status == "running":
                self.stop_public_access(log_manager)

            # 停止内网服务
            if self.status == ServiceStatus.RUNNING:
                if self.process:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=AppConstants.PROCESS_TERMINATE_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        print(f"服务 '{self.name}' 进程终止超时，强制终止")
                        self.process.kill()

            # 更新状态
            self.update_status(ServiceStatus.STOPPED)
            self.local_addr = ""

            if log_manager:
                log_manager.append_log(f"服务 '{self.name}' 已停止", False, self.name)
            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"停止服务失败: {str(e)}", True, self.name)
            self.update_status(ServiceStatus.ERROR)
            return False

    def start_public_access(self, log_manager=None) -> bool:
        """启动公网访问

        Args:
            log_manager: 日志管理器实例

        Returns:
            bool: 启动是否成功
        """
        # 更新兼容属性
        self.cloudflared_process = self.cloudflare_tunnel.process

        result = self.cloudflare_tunnel.start(self.local_addr, log_manager)

        # 同步状态
        self.public_access_status = self.cloudflare_tunnel.status
        self.public_url = self.cloudflare_tunnel.public_url
        self.cloudflared_process = self.cloudflare_tunnel.process

        return result

    def stop_public_access(self, log_manager=None) -> bool:
        """停止公网访问

        Args:
            log_manager: 日志管理器实例

        Returns:
            bool: 停止是否成功
        """
        # 设置监控线程终止标志（兼容旧代码）
        self.cloudflared_monitor_terminate = True

        result = self.cloudflare_tunnel.stop(log_manager)

        # 同步状态
        self.public_access_status = self.cloudflare_tunnel.status
        self.public_url = self.cloudflare_tunnel.public_url
        self.cloudflared_process = None
        self.cloudflared_monitor_thread = None

        return result

    def is_cloudflared_running(self) -> bool:
        """检查cloudflared进程是否正在运行"""
        return self.cloudflare_tunnel.is_running()

    def read_service_output(self, log_manager=None):
        """读取服务输出

        Args:
            log_manager: 日志管理器实例
        """
        try:
            if self.process and self.process.stdout:
                while self.process.poll() is None:
                    try:
                        line = self.process.stdout.readline()
                        if not line:
                            break
                        if line.strip():
                            if log_manager:
                                log_manager.append_log(line.strip(), False, self.name)
                    except Exception as e:
                        print(f"读取服务输出失败: {str(e)}")
                        break
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"读取服务输出失败: {str(e)}", True, self.name)


