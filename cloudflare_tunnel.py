"""Cloudflare隧道模块 - 负责公网访问功能"""

import os
import re
import threading
import time
import shutil
from typing import Optional, Callable

from constants import get_resource_path


class CloudflareTunnel:
    """Cloudflare隧道管理器 - 负责公网访问功能"""

    def __init__(self, service_name: str):
        """
        初始化Cloudflare隧道

        Args:
            service_name: 所属服务名称（用于日志）
        """
        self.service_name = service_name
        self.process: Optional[object] = None
        self.public_url: str = ""
        self.status: str = "stopped"  # stopped, starting, running, stopping

        # 监控相关属性
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_terminate: bool = False

        # 状态更新回调
        self.status_callback: Optional[Callable[[str], None]] = None
        self.url_callback: Optional[Callable[[str], None]] = None

    def set_callbacks(self, status_callback: Callable[[str], None], url_callback: Callable[[str], None]):
        """设置状态更新回调

        Args:
            status_callback: 状态更新回调函数
            url_callback: URL更新回调函数
        """
        self.status_callback = status_callback
        self.url_callback = url_callback

    def get_cloudflared_path(self) -> str:
        """获取cloudflared路径，优先从lib文件夹查找"""
        cloudflared_filename = "cloudflared.exe"

        # 优先使用 get_resource_path 查找（支持 lib 子文件夹）
        resource_path = get_resource_path(cloudflared_filename)
        if os.path.exists(resource_path):
            return resource_path

        # 检查多个位置
        check_paths = [
            os.path.join(os.getcwd(), cloudflared_filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), cloudflared_filename),
        ]

        for path in check_paths:
            if os.path.exists(path):
                return path

        # 尝试从系统PATH获取
        if shutil.which(cloudflared_filename):
            return cloudflared_filename

        return cloudflared_filename

    def start(self, local_addr: str, log_manager=None) -> bool:
        """启动Cloudflare隧道

        Args:
            local_addr: 本地服务地址
            log_manager: 日志管理器实例

        Returns:
            bool: 启动是否成功
        """
        import subprocess

        try:
            # 检查cloudflared.exe是否存在
            cloudflared_path = self.get_cloudflared_path()
            if not os.path.exists(cloudflared_path):
                if log_manager:
                    log_manager.append_log(f"cloudflared.exe 文件不存在: {cloudflared_path}", True, self.service_name)
                return False

            # 构建cloudflared命令
            cmd = [cloudflared_path, "tunnel", "--url", local_addr]

            # 记录启动公网访问的日志
            if log_manager:
                log_manager.append_log(f"启动公网访问: {local_addr}", False, self.service_name)

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

            # 更新状态
            self._update_status("starting")

            # 启动监控线程
            self.monitor_terminate = False
            self.monitor_thread = threading.Thread(
                target=self._monitor_process,
                args=(log_manager,),
                daemon=True
            )
            self.monitor_thread.start()

            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"启动公网共享失败: {str(e)}", True, self.service_name)
            self._update_status("stopped")
            return False

    def stop(self, log_manager=None) -> bool:
        """停止Cloudflare隧道

        Args:
            log_manager: 日志管理器实例

        Returns:
            bool: 停止是否成功
        """
        try:
            # 设置监控线程终止标志
            self.monitor_terminate = True

            # 保存进程引用
            process = self.process
            if process:
                # 记录停止公网访问的日志
                if log_manager:
                    log_manager.append_log("停止公网访问", False, self.service_name)

                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"终止cloudflared进程失败: {str(e)}")

                # 更新状态
                self.public_url = ""
                self._update_status("stopped")

                # 记录停止成功的日志
                if log_manager:
                    log_manager.append_log("公网访问已停止", False, self.service_name)

            # 重置监控线程引用
            self.monitor_thread = None
            self.process = None

            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"停止公网共享失败: {str(e)}", True, self.service_name)
            return False

    def is_running(self) -> bool:
        """检查cloudflared进程是否正在运行"""
        if self.process is None:
            return False
        return self.process.poll() is None

    def _update_status(self, status: str):
        """更新状态并触发回调"""
        self.status = status
        if self.status_callback:
            self.status_callback(status)

    def _update_url(self, url: str):
        """更新URL并触发回调"""
        self.public_url = url
        if self.url_callback:
            self.url_callback(url)

    def _monitor_process(self, log_manager=None):
        """监控cloudflared进程

        Args:
            log_manager: 日志管理器实例
        """
        try:
            process = self.process
            if not process:
                return

            # 重置终止标志
            self.monitor_terminate = False

            # 添加超时检查
            start_time = time.time()
            timeout = 30  # 30秒超时

            # 读取输出
            for line in iter(process.stdout.readline, ''):
                # 检查终止标志
                if self.monitor_terminate:
                    break

                if time.time() - start_time > timeout:
                    if log_manager:
                        log_manager.append_log("云流服务启动超时", True, self.service_name)
                    break

                if not process.poll() is None:
                    break

                # 处理输出
                if "trycloudflare.com" in line:
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        url = match.group(0)
                        self._update_url(url)
                        self._update_status("running")
                        if log_manager:
                            log_manager.append_log(f"公网地址: {url}", False, self.service_name)
                elif "error" in line.lower():
                    if log_manager:
                        log_manager.append_log(f"Cloudflare错误: {line.strip()}", True, self.service_name)
                else:
                    if log_manager:
                        log_manager.append_log(line.strip(), False, self.service_name)

            # 处理进程退出（仅在未主动终止时更新状态）
            if not self.monitor_terminate and process.poll() is not None:
                self.public_url = ""
                self._update_status("stopped")
        except Exception as e:
            if log_manager:
                log_manager.append_log(f"监控cloudflared失败: {str(e)}", True, self.service_name)
            self._update_status("error")
