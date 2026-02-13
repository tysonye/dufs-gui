"""Cloudflare隧道模块 - 负责公网访问功能（合并版）"""

import os
import re
import hashlib
import threading
import time
import shutil
from typing import Optional, Callable

import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from constants import get_resource_path, get_lib_path


# Cloudflared 官方SHA256校验和（需要定期更新）
# 从 https://github.com/cloudflare/cloudflared/releases 获取最新版本的校验和
CLOUDFLARED_SHA256_CHECKSUM = None  # 设置为None表示跳过校验，或填入实际校验和


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
                    log_manager.append_log_legacy(f"cloudflared.exe 文件不存在: {cloudflared_path}", True, self.service_name)
                return False

            # 构建cloudflared命令
            cmd = [cloudflared_path, "tunnel", "--url", local_addr]

            # 记录启动公网访问的日志
            if log_manager:
                log_manager.append_log_legacy(f"启动公网访问: {local_addr}", False, self.service_name)

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
                log_manager.append_log_legacy(f"启动公网共享失败: {str(e)}", True, self.service_name)
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
                    log_manager.append_log_legacy("停止公网访问", False, self.service_name)

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
                    log_manager.append_log_legacy("公网访问已停止", False, self.service_name)

            # 重置监控线程引用
            self.monitor_thread = None
            self.process = None

            return True
        except Exception as e:
            if log_manager:
                log_manager.append_log_legacy(f"停止公网共享失败: {str(e)}", True, self.service_name)
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
                        log_manager.append_log_legacy("云流服务启动超时", True, self.service_name)
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
                            log_manager.append_log_legacy(f"公网地址: {url}", False, self.service_name)
                elif "error" in line.lower():
                    if log_manager:
                        log_manager.append_log_legacy(f"Cloudflare错误: {line.strip()}", True, self.service_name)
                else:
                    # 传递所有日志到 log_manager 进行转换和显示
                    if log_manager:
                        log_manager.append_log_legacy(line.strip(), False, self.service_name)

            # 处理进程退出（仅在未主动终止时更新状态）
            if not self.monitor_terminate and process.poll() is not None:
                self.public_url = ""
                self._update_status("stopped")
        except Exception as e:
            if log_manager:
                log_manager.append_log_legacy(f"监控cloudflared失败: {str(e)}", True, self.service_name)
            self._update_status("error")


# ========== 下载相关功能（合并自 cloudflared_downloader.py）==========

class DownloadThread(QThread):
    """下载线程（内部类，带校验）"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    download_finished = pyqtSignal(bool, str)

    def __init__(self, url, temp_path, final_path, expected_checksum=None):
        super().__init__()
        self.url = url
        self.temp_path = temp_path
        self.final_path = final_path
        self.expected_checksum = expected_checksum
        self._is_running = True
        self._downloaded_size = 0

    def run(self):
        try:
            self.status_updated.emit("正在连接服务器...")
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            self._downloaded_size = 0

            # 创建SHA256校验器
            sha256_hash = hashlib.sha256()

            self.status_updated.emit("正在下载...")
            with open(self.temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self._is_running:
                        break
                    if chunk:
                        _ = f.write(chunk)
                        sha256_hash.update(chunk)
                        self._downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = int((self._downloaded_size / total_size) * 100)
                            self.progress_updated.emit(progress)

            if self._is_running:
                # 下载完成，验证校验和
                if self.expected_checksum:
                    actual_checksum = sha256_hash.hexdigest()
                    if actual_checksum.lower() != self.expected_checksum.lower():
                        # 校验失败，删除文件
                        try:
                            os.remove(self.temp_path)
                        except (IOError, OSError):
                            pass
                        self.download_finished.emit(
                            False,
                            f"文件校验失败！\n预期: {self.expected_checksum}\n实际: {actual_checksum}"
                        )
                        return
                    else:
                        print(f"[Cloudflared] SHA256校验通过: {actual_checksum}")

                # 校验通过，重命名临时文件为正式文件
                try:
                    if os.path.exists(self.final_path):
                        os.remove(self.final_path)
                    os.rename(self.temp_path, self.final_path)
                    self.download_finished.emit(True, "下载完成")
                except (IOError, OSError) as e:
                    self.download_finished.emit(False, f"文件保存失败: {str(e)}")
            else:
                # 下载被取消，删除临时文件
                try:
                    if os.path.exists(self.temp_path):
                        os.remove(self.temp_path)
                except (IOError, OSError):
                    pass
                self.download_finished.emit(False, "下载已取消")
        except (IOError, OSError) as e:
            # 下载失败，删除临时文件
            try:
                if os.path.exists(self.temp_path):
                    os.remove(self.temp_path)
            except (IOError, OSError):
                pass
            self.download_finished.emit(False, f"下载失败: {str(e)}")

    def stop(self):
        self._is_running = False

    def get_downloaded_size(self):
        """获取已下载大小"""
        return self._downloaded_size


class CloudflaredDownloadDialog(QDialog):
    """cloudflared下载进度对话框（内部类）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载 Cloudflared")
        self.setFixedSize(400, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 状态标签
        self.status_label = QLabel("准备下载...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_btn)

        # 下载线程
        self.download_thread = None

    def start_download(self):
        """开始下载"""
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        lib_dir = get_lib_path()
        final_path = os.path.join(lib_dir, "cloudflared.exe")
        temp_path = os.path.join(lib_dir, "cloudflared.exe.tmp")

        self.download_thread = DownloadThread(
            url, temp_path, final_path,
            expected_checksum=CLOUDFLARED_SHA256_CHECKSUM
        )
        self.download_thread.progress_updated.connect(self._update_progress)
        self.download_thread.status_updated.connect(self._update_status)
        self.download_thread.download_finished.connect(self._on_finished)
        self.download_thread.start()

    def _update_progress(self, progress):
        """更新进度"""
        self.progress_bar.setValue(progress)

    def _update_status(self, status):
        """更新状态"""
        self.status_label.setText(status)

    def _on_finished(self, success, message):
        """下载完成处理"""
        if success:
            self.status_label.setText("下载完成!")
            self.progress_bar.setValue(100)
            self.cancel_btn.setText("确定")
            self.cancel_btn.clicked.disconnect()
            self.cancel_btn.clicked.connect(self.accept)
            # 显示文件大小和校验信息
            try:
                lib_dir = get_lib_path()
                final_path = os.path.join(lib_dir, "cloudflared.exe")
                file_size = os.path.getsize(final_path)
                size_text = f"文件大小: {file_size / 1024 / 1024:.2f} MB"
                if CLOUDFLARED_SHA256_CHECKSUM:
                    self.status_label.setText(f"下载完成! {size_text}\nSHA256校验通过")
                else:
                    self.status_label.setText(f"下载完成! {size_text}")
            except (IOError, OSError):
                pass
        else:
            self.status_label.setText(message)
            self.progress_bar.setValue(0)
            self.cancel_btn.setText("关闭")
            self.cancel_btn.clicked.disconnect()
            self.cancel_btn.clicked.connect(self.reject)

    def _on_cancel(self):
        """取消下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait(1000)
        self.reject()

    def closeEvent(self, event):
        """关闭事件"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait(1000)
        event.accept()


def verify_cloudflared_checksum(file_path, expected_checksum):
    """验证cloudflared文件的SHA256校验和（内部函数）

    Args:
        file_path: 文件路径
        expected_checksum: 预期的SHA256校验和

    Returns:
        bool: 校验是否通过
    """
    if not expected_checksum:
        return True  # 没有提供校验和，跳过校验

    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)

        actual_checksum = sha256_hash.hexdigest()
        return actual_checksum.lower() == expected_checksum.lower()
    except (IOError, OSError) as e:
        print(f"校验文件失败: {str(e)}")
        return False


def check_and_download_cloudflared(parent=None, max_retries=3, verify_checksum=True):
    """检查并下载cloudflared（内部函数，带校验）

    Args:
        parent: 父窗口
        max_retries: 最大重试次数
        verify_checksum: 是否验证校验和

    Returns:
        bool: 是否成功（已存在或下载成功）
    """
    # 检查是否已存在（优先从 _internal/lib 文件夹查找）
    lib_dir = get_lib_path()
    cloudflared_path = os.path.join(lib_dir, "cloudflared.exe")

    if os.path.exists(cloudflared_path):
        # 验证已存在文件的校验和
        if verify_checksum and CLOUDFLARED_SHA256_CHECKSUM:
            if verify_cloudflared_checksum(cloudflared_path, CLOUDFLARED_SHA256_CHECKSUM):
                print("[Cloudflared] 本地文件校验通过")
                return True
            else:
                print("[Cloudflared] 本地文件校验失败，需要重新下载")
                # 删除损坏的文件
                try:
                    os.remove(cloudflared_path)
                except (IOError, OSError) as e:
                    print(f"删除损坏文件失败: {str(e)}")
        else:
            return True

    # 清理可能存在的临时文件
    temp_path = os.path.join(lib_dir, "cloudflared.exe.tmp")
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except (IOError, OSError):
        pass

    # 询问用户是否下载
    reply = QMessageBox.question(
        parent,
        "下载 Cloudflared",
        "未找到公网服务文件，需要下载才能使用公网访问功能。（开启梯子下载更快）\n\n是否立即下载?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )

    if reply == QMessageBox.No:
        return False

    # 尝试下载，支持重试
    for attempt in range(max_retries):
        # 显示下载对话框
        dialog = CloudflaredDownloadDialog(parent)
        dialog.start_download()
        result = dialog.exec_()

        if result == QDialog.Accepted:
            # 下载成功，再次验证
            if verify_checksum and CLOUDFLARED_SHA256_CHECKSUM:
                if verify_cloudflared_checksum(cloudflared_path, CLOUDFLARED_SHA256_CHECKSUM):
                    print("[Cloudflared] 下载文件校验通过")
                    return True
                else:
                    QMessageBox.warning(
                        parent,
                        "校验失败",
                        "下载的文件校验失败，可能已被篡改或下载不完整。"
                    )
                    # 删除损坏的文件
                    try:
                        os.remove(cloudflared_path)
                    except (IOError, OSError):
                        pass
            else:
                return True

        # 下载失败，询问是否重试
        if attempt < max_retries - 1:
            retry_reply = QMessageBox.question(
                parent,
                "下载失败",
                f"下载失败（第 {attempt + 1}/{max_retries} 次尝试），是否重试?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if retry_reply == QMessageBox.No:
                return False
        else:
            # 最后一次尝试失败
            QMessageBox.warning(
                parent,
                "下载失败",
                f"下载失败（已尝试 {max_retries} 次），请检查网络连接或手动下载。"
            )

    return False
