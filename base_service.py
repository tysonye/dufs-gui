"""基础服务模块 - 负责Dufs服务的核心功能"""

import os
import threading
import subprocess
import time
import signal
import atexit
from typing import Optional

from PyQt5.QtCore import pyqtSignal, QObject, QMetaObject, Qt, pyqtSlot

from constants import get_resource_path, AppConstants
from service_state import ServiceStatus, ServiceStateMachine
from cloudflare_tunnel import CloudflareTunnel


class BaseService(QObject):
    """基础服务类 - 负责Dufs服务的核心功能（加强子进程生命周期管理）"""

    # 信号定义
    status_updated = pyqtSignal()
    progress_updated = pyqtSignal(int, str)
    log_updated = pyqtSignal(str, bool, str)

    # 类级别的进程跟踪，用于程序退出时统一清理
    _all_services = []
    _cleanup_registered = False

    # 类级别的状态机实例（单例模式，确保一致性）
    _state_machine = None

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

        # 初始化类级别的状态机（只创建一次）
        if BaseService._state_machine is None:
            BaseService._state_machine = ServiceStateMachine()

        # 进程信息（使用进程组管理）
        self.process: Optional[subprocess.Popen] = None
        self._process_group_id: Optional[int] = None
        self.status = ServiceStatus.STOPPED

        # 访问地址
        self.local_addr = ""

        # 线程锁
        self.lock = threading.Lock()

        # 停止标志，防止重复停止
        self._is_stopping = False

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

        # 注册到全局服务列表
        BaseService._all_services.append(self)

        # 注册程序退出清理（只执行一次）
        if not BaseService._cleanup_registered:
            atexit.register(BaseService._cleanup_all_services)
            BaseService._cleanup_registered = True

    @classmethod
    def _cleanup_all_services(cls):
        """程序退出时统一清理所有服务"""
        print("[系统退出] 正在清理所有服务进程...")
        for service in cls._all_services:
            try:
                if service.process and service.process.poll() is None:
                    print(f"  终止服务: {service.name}")
                    service._terminate_process_group()
            except Exception as e:
                print(f"  清理服务失败 {service.name}: {str(e)}")

    def _terminate_process_group(self):
        """终止整个进程组（防止孤儿进程）"""
        if not self.process:
            return

        try:
            # 尝试终止整个进程组
            if hasattr(self.process, 'pid') and self.process.pid:
                try:
                    # Windows: 使用 taskkill 终止进程树
                    import platform
                    if platform.system() == 'Windows':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                                     capture_output=True, check=False)
                    else:
                        # Linux/Mac: 使用进程组信号
                        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                except Exception as e:
                    print(f"终止进程组失败: {str(e)}")

            # 确保进程已终止
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=1)
        except Exception as e:
            print(f"终止进程失败: {str(e)}")

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
        # 使用类级别的状态机实例（单例模式，确保一致性）
        state_machine = BaseService._state_machine
        if state_machine is None:
            state_machine = ServiceStateMachine()
            BaseService._state_machine = state_machine

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
        """启动服务（加强版，启动前检测端口）

        Args:
            log_manager: 日志管理器实例

        Returns:
            bool: 启动是否成功
        """
        try:
            # 确保服务未在运行中
            if self.status != ServiceStatus.STOPPED:
                if log_manager:
                    log_manager.append_log_legacy(f"服务 '{self.name}' 已在运行中，跳过启动", False, self.name)
                return False

            # 记录启动服务日志
            if log_manager:
                log_manager.append_log_legacy(f"开始启动服务 '{self.name}'", False, self.name)

            # 启动前检测端口是否可用
            from utils import check_port_conflict
            port_int = int(self.port)
            is_available, port_msg = check_port_conflict(port_int, self.bind or "0.0.0.0")
            if not is_available:
                if log_manager:
                    log_manager.append_log_legacy(f"服务 '{self.name}' 启动失败: {port_msg}", True, self.name)
                print(f"[启动失败] {port_msg}")
                return False

            # 更新服务状态为启动中
            if not self.update_status(ServiceStatus.STARTING):
                if log_manager:
                    log_manager.append_log_legacy(f"服务 '{self.name}' 状态转换失败，无法启动", True, self.name)
                return False

            # 检查dufs.exe是否存在
            dufs_path = get_resource_path("dufs.exe")
            if not os.path.exists(dufs_path):
                if log_manager:
                    log_manager.append_log_legacy(f"dufs.exe 文件不存在: {dufs_path}", True, self.name)
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
                    log_manager.append_log_legacy(f"服务 '{self.name}' 启动成功，地址: {self.local_addr}", False, self.name)
                return True
            else:
                # 服务启动失败
                try:
                    output = self.process.stdout.read()
                    if log_manager:
                        log_manager.append_log_legacy(f"服务 '{self.name}' 启动失败: {output}", True, self.name)
                except Exception as e:
                    print(f"读取错误输出失败: {str(e)}")
                self.update_status(ServiceStatus.ERROR)
                return False
        except Exception as e:
            if log_manager:
                log_manager.append_log_legacy(f"启动服务失败: {str(e)}", True, self.name)
            self.update_status(ServiceStatus.ERROR)
            return False

    def stop(self, log_manager=None) -> bool:
        """停止服务（加强版，防止重复停止和孤儿进程）

        Args:
            log_manager: 日志管理器实例

        Returns:
            bool: 停止是否成功
        """
        # 使用锁防止并发停止
        with self.lock:
            # 检查是否已在停止中
            if self._is_stopping:
                if log_manager:
                    log_manager.append_log_legacy(f"服务 '{self.name}' 正在停止中，跳过重复请求", False, self.name)
                return False

            # 确保服务正在运行
            if self.status == ServiceStatus.STOPPED:
                if log_manager:
                    log_manager.append_log_legacy(f"服务 '{self.name}' 已停止，无需停止", False, self.name)
                return False

            # 设置停止标志
            self._is_stopping = True

        try:
            # 记录停止服务日志
            if log_manager:
                log_manager.append_log_legacy(f"开始停止服务 '{self.name}'", False, self.name)

            # 停止公网共享
            if self.public_access_status == "running":
                try:
                    self.stop_public_access(log_manager)
                except Exception as e:
                    print(f"停止公网共享失败: {str(e)}")

            # 停止内网服务
            if self.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING, ServiceStatus.ERROR]:
                if self.process:
                    try:
                        # 使用进程组终止
                        self._terminate_process_group()
                    except Exception as e:
                        print(f"终止进程失败: {str(e)}")

            # 更新状态
            self.update_status(ServiceStatus.STOPPED)
            self.local_addr = ""

            if log_manager:
                log_manager.append_log_legacy(f"服务 '{self.name}' 已停止", False, self.name)
            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log_legacy(f"停止服务失败: {str(e)}", True, self.name)
            self.update_status(ServiceStatus.ERROR)
            return False
        finally:
            # 重置停止标志
            self._is_stopping = False

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
        """读取服务输出（非阻塞版，防止线程卡住）

        Args:
            log_manager: 日志管理器实例
        """
        import select
        import sys

        try:
            if self.process and self.process.stdout:
                # 获取文件描述符
                stdout_fd = self.process.stdout.fileno()

                # 设置非阻塞模式（Windows不支持，使用超时轮询）
                if sys.platform == 'win32':
                    # Windows: 使用超时轮询避免阻塞
                    import msvcrt
                    msvcrt.setmode(stdout_fd, os.O_BINARY)

                while self.process.poll() is None:
                    try:
                        # 使用select检查是否有数据可读（带超时）
                        if sys.platform != 'win32':
                            readable, _, _ = select.select([self.process.stdout], [], [], 0.5)
                            if not readable:
                                continue

                        # 读取一行（带超时保护）
                        line = self.process.stdout.readline()
                        if not line:
                            # 没有数据，短暂休眠避免CPU占用过高
                            time.sleep(0.1)
                            continue

                        if line.strip():
                            if log_manager:
                                log_manager.append_log_legacy(line.strip(), False, self.name)
                    except Exception as e:
                        print(f"读取服务输出失败: {str(e)}")
                        break
        except Exception as e:
            if log_manager:
                log_manager.append_log_legacy(f"读取服务输出失败: {str(e)}", True, self.name)


