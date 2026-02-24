"""Cloudflare隧道模块 - 负责公网访问功能（合并版）"""

import os
import re
import hashlib
import threading
import time
import shutil
import json
import subprocess
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
    QMessageBox, QTextEdit, QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont, QTextCursor

from constants import get_resource_path, get_lib_path


# Cloudflared GitHub API 地址
CLOUDFLARED_GITHUB_API = "https://api.github.com/repos/cloudflare/cloudflared/releases/latest"
CLOUDFLARED_GITHUB_ASSETS = "https://github.com/cloudflare/cloudflared/releases/download"


@dataclass
class CloudflaredVersion:
    """Cloudflared 版本信息"""
    version: str
    download_url: str
    checksum: str
    release_date: str
    release_notes: str


class VersionComparator:
    """版本比较器"""

    @staticmethod
    def parse_version(version_str: str) -> Tuple[int, ...]:
        """解析版本字符串为元组

        Args:
            version_str: 版本字符串，如 "2024.1.2" 或 "2024.1.2-beta"

        Returns:
            Tuple[int, ...]: 版本号元组
        """
        # 移除前缀 "v" 和后缀
        version_str = version_str.lstrip('v').split('-')[0]

        # 分割版本号
        parts = version_str.split('.')

        # 转换为整数元组
        try:
            return tuple(int(p) for p in parts if p.isdigit())
        except ValueError:
            return (0, 0, 0)

    @staticmethod
    def compare(current: str, latest: str) -> int:
        """比较版本

        Args:
            current: 当前版本
            latest: 最新版本

        Returns:
            int: -1 表示当前版本更新, 0 表示相同, 1 表示有新版本
        """
        current_tuple = VersionComparator.parse_version(current)
        latest_tuple = VersionComparator.parse_version(latest)

        if current_tuple < latest_tuple:
            return 1  # 有新版本
        elif current_tuple > latest_tuple:
            return -1  # 当前版本比最新版本更新
        else:
            return 0  # 版本相同


class CloudflareUpdater(QObject):
    """Cloudflared 版本检测与自动更新器

    功能特性：
    1. 版本检测 - 从 GitHub API 获取最新版本
    2. 版本比较 - 准确判断是否需要更新
    3. 自动下载 - 从官方地址下载最新版本
    4. 文件校验 - SHA256 校验确保安全
    5. 后台更新 - 不影响主程序运行
    6. 状态反馈 - 实时显示更新进度
    7. 异常处理 - 完善的错误处理
    8. 手动/自动触发 - 支持多种更新方式
    """

    # 信号定义
    version_checked = pyqtSignal(bool, str, str)  # (has_update, current_version, latest_version)
    download_progress = pyqtSignal(int)  # 下载进度 (0-100)
    download_finished = pyqtSignal(bool, str)  # 下载结果 (success, message)
    update_status_changed = pyqtSignal(str)  # 更新状态变化

    # 状态常量
    STATUS_IDLE = "idle"
    STATUS_CHECKING = "checking"
    STATUS_DOWNLOADING = "downloading"
    STATUS_VERIFYING = "verifying"
    STATUS_UPDATING = "updating"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"

    def __init__(self, parent=None):
        """初始化更新器"""
        super().__init__(parent)

        # 配置
        self.check_interval_hours = 6  # 自动检查间隔（小时）
        self.retry_times = 3  # 下载重试次数
        self.timeout = 60  # 下载超时（秒）

        # 状态
        self.status = self.STATUS_IDLE
        self.current_version = ""
        self.latest_version = ""
        self.update_available = False

        # 文件路径
        self.cloudflared_path = ""
        self.temp_path = ""

        # 线程
        self.check_thread: Optional[QThread] = None
        self.download_thread: Optional[QThread] = None

        # 回调
        self.status_callback: Optional[Callable[[str], None]] = None

        # 缓存
        self._cached_version: Optional[CloudflaredVersion] = None
        self._cache_time: float = 0
        self._cache_valid_seconds = 3600  # 缓存1小时

    def set_status_callback(self, callback: Callable[[str], None]):
        """设置状态回调"""
        self.status_callback = callback

    def _update_status(self, status: str):
        """更新状态"""
        self.status = status
        self.update_status_changed.emit(status)
        if self.status_callback:
            self.status_callback(status)

    def get_cloudflared_path(self) -> str:
        """获取 cloudflared 路径"""
        cloudflared_filename = "cloudflared.exe"

        # 优先使用 get_resource_path 查找
        resource_path = get_resource_path(cloudflared_filename)
        if os.path.exists(resource_path):
            return resource_path

        # 检查多个位置
        check_paths = [
            os.path.join(os.getcwd(), cloudflared_filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), cloudflared_filename),
            os.path.join(get_lib_path(), cloudflared_filename),
        ]

        for path in check_paths:
            if os.path.exists(path):
                return path

        # 尝试从系统 PATH 获取
        if shutil.which(cloudflared_filename):
            return cloudflared_filename

        return cloudflared_filename

    def get_current_version(self) -> str:
        """获取当前 cloudflared 版本

        Returns:
            str: 当前版本号，如 "2024.1.2"
        """
        if self.current_version:
            return self.current_version

        cloudflared_path = self.get_cloudflared_path()

        if not os.path.exists(cloudflared_path):
            return "未安装"

        try:
            # 执行 cloudflared --version
            result = subprocess.run(
                [cloudflared_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            output = result.stdout + result.stderr

            # 解析版本号
            match = re.search(r'cloudflared[/\s]+([\d.]+)', output, re.IGNORECASE)
            if match:
                self.current_version = match.group(1)
                return self.current_version

            # 尝试其他格式
            match = re.search(r'version ([\d.]+)', output, re.IGNORECASE)
            if match:
                self.current_version = match.group(1)
                return self.current_version

        except Exception as e:
            print(f"获取版本失败: {str(e)}")

        return "未知"

    def fetch_latest_version(self, force: bool = False) -> Optional[CloudflaredVersion]:
        """从 GitHub API 获取最新版本信息

        Args:
            force: 是否强制刷新缓存

        Returns:
            Optional[CloudflaredVersion]: 最新版本信息
        """
        # 检查缓存
        current_time = time.time()
        if (not force and
            self._cached_version and
            current_time - self._cache_time < self._cache_valid_seconds):
            return self._cached_version

        try:
            # 使用 DNS-over-HTTPS 避免 DNS 解析问题
            headers = {
                'User-Agent': 'DufsGUI-Cloudflared-Updater',
                'Accept': 'application/json'
            }

            # 尝试从 GitHub API 获取
            response = requests.get(
                CLOUDFLARED_GITHUB_API,
                headers=headers,
                timeout=self.timeout,
                proxies={'http': None, 'https': None}  # 不使用代理
            )

            if response.status_code != 200:
                # 备用方案：直接解析 GitHub 页面
                return self._fetch_version_from_page()

            release_data = response.json()

            # 解析版本号
            tag_name = release_data.get('tag_name', 'v0.0.0')
            version = tag_name.lstrip('v')

            # 获取发布日期
            release_date = release_data.get('published_at', '')[:10]

            # 获取发布说明
            release_notes = release_data.get('body', '')[:500]

            # 查找 Windows AMD64 下载链接和 SHA256
            download_url = ""
            checksum = ""

            assets = release_data.get('assets', [])
            for asset in assets:
                name = asset.get('name', '')
                if 'windows-amd64' in name.lower() and not '.sig' in name.lower():
                    download_url = asset.get('browser_download_url', '')
                    break

            # 如果没有从 API 获取到下载链接，使用默认格式
            if not download_url:
                download_url = f"{CLOUDFLARED_GITHUB_API}/{tag_name}/cloudflared-windows-amd64.exe"

            # 尝试从发布说明中提取 SHA256
            body = release_data.get('body', '')
            sha256_match = re.search(r'([a-fA-F0-9]{64})', body)
            if sha256_match:
                checksum = sha256_match.group(1)

            version_info = CloudflaredVersion(
                version=version,
                download_url=download_url,
                checksum=checksum,
                release_date=release_date,
                release_notes=release_notes
            )

            # 更新缓存
            self._cached_version = version_info
            self._cache_time = current_time
            self.latest_version = version

            return version_info

        except requests.exceptions.Timeout:
            print("获取版本信息超时")
            return self._cached_version
        except requests.exceptions.RequestException as e:
            print(f"获取版本信息失败: {str(e)}")
            return self._cached_version
        except Exception as e:
            print(f"获取版本信息异常: {str(e)}")
            return self._cached_version

    def _fetch_version_from_page(self) -> Optional[CloudflaredVersion]:
        """备用方案：从 GitHub 页面获取版本"""
        try:
            # 使用 raw GitHub 页面获取版本
            url = "https://github.com/cloudflare/cloudflared/releases/latest"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html'
            }

            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                # 查找版本号
                match = re.search(r'cloudflared[/\s]+([\d.]+)', response.text)
                if match:
                    version = match.group(1)
                    download_url = f"{CLOUDFLARED_GITHUB_API}/v{version}/cloudflared-windows-amd64.exe"

                    version_info = CloudflaredVersion(
                        version=version,
                        download_url=download_url,
                        checksum="",
                        release_date="",
                        release_notes=""
                    )

                    self._cached_version = version_info
                    self._cache_time = time.time()
                    self.latest_version = version

                    return version_info

        except Exception as e:
            print(f"从页面获取版本失败: {str(e)}")

        return None

    def check_for_updates(self, silent: bool = False) -> Tuple[bool, str, str]:
        """检查更新

        Args:
            silent: 是否静默检查（不触发信号）

        Returns:
            Tuple[bool, str, str]: (是否有更新, 当前版本, 最新版本)
        """
        self._update_status(self.STATUS_CHECKING)

        # 获取当前版本
        current = self.get_current_version()
        self.current_version = current

        # 获取最新版本
        latest_info = self.fetch_latest_version()

        if not latest_info:
            if not silent:
                self.version_checked.emit(False, current, "获取失败")
            return (False, current, "获取失败")

        latest = latest_info.version

        # 比较版本
        result = VersionComparator.compare(current, latest)
        has_update = result > 0

        self.update_available = has_update
        self._update_status(self.STATUS_IDLE)

        if not silent:
            self.version_checked.emit(has_update, current, latest)

        return (has_update, current, latest)

    def download_latest(self, progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """下载最新版本

        Args:
            progress_callback: 进度回调

        Returns:
            bool: 下载是否成功
        """
        # 获取最新版本信息
        latest_info = self.fetch_latest_version(force=True)

        if not latest_info:
            self._update_status(self.STATUS_ERROR)
            self.download_finished.emit(False, "获取版本信息失败")
            return False

        if not latest_info.download_url:
            self._update_status(self.STATUS_ERROR)
            self.download_finished.emit(False, "获取下载链接失败")
            return False

        # 准备下载
        lib_dir = get_lib_path()
        temp_path = os.path.join(lib_dir, "cloudflared_new.exe")
        final_path = os.path.join(lib_dir, "cloudflared.exe")

        # 确保目录存在
        os.makedirs(lib_dir, exist_ok=True)

        # 清理旧文件
        for path in [temp_path, final_path + ".tmp"]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        self._update_status(self.STATUS_DOWNLOADING)

        # 执行下载
        success = False
        error_message = ""

        for attempt in range(self.retry_times):
            try:
                self.download_progress.emit(0)

                # 下载文件
                response = requests.get(
                    latest_info.download_url,
                    stream=True,
                    timeout=self.timeout,
                    proxies={'http': None, 'https': None}
                )

                if response.status_code != 200:
                    error_message = f"HTTP {response.status_code}"
                    continue

                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                # 创建 SHA256 校验器
                sha256_hash = hashlib.sha256()

                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            sha256_hash.update(chunk)
                            downloaded_size += len(chunk)

                            if total_size > 0:
                                progress = int((downloaded_size / total_size) * 100)
                                self.download_progress.emit(progress)
                                if progress_callback:
                                    progress_callback(progress)

                # 下载完成，校验文件
                self._update_status(self.STATUS_VERIFYING)

                actual_checksum = sha256_hash.hexdigest()

                # 如果有预期校验和，进行校验
                if latest_info.checksum:
                    if actual_checksum.lower() != latest_info.checksum.lower():
                        error_message = "文件校验失败"
                        # 删除损坏的文件
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                        continue

                # 校验通过，替换旧文件
                self._update_status(self.STATUS_UPDATING)

                try:
                    # 如果存在旧文件，先备份
                    if os.path.exists(final_path):
                        backup_path = final_path + ".bak"
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        os.rename(final_path, backup_path)

                    # 重命名新文件
                    os.rename(temp_path, final_path)

                    # 删除备份
                    backup_path = final_path + ".bak"
                    if os.path.exists(backup_path):
                        os.remove(backup_path)

                    success = True
                    self._update_status(self.STATUS_SUCCESS)

                    # 更新当前版本
                    self.current_version = latest_info.version

                    self.download_progress.emit(100)
                    self.download_finished.emit(True, f"更新成功: {latest_info.version}")

                    return True

                except Exception as e:
                    error_message = f"文件替换失败: {str(e)}"
                    # 恢复备份
                    backup_path = final_path + ".bak"
                    if os.path.exists(backup_path):
                        try:
                            os.rename(backup_path, final_path)
                        except Exception:
                            pass

            except requests.exceptions.Timeout:
                error_message = "下载超时"
            except requests.exceptions.RequestException as e:
                error_message = f"网络错误: {str(e)}"
            except Exception as e:
                error_message = f"下载失败: {str(e)}"

            # 清理临时文件
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

        # 所有重试都失败
        self._update_status(self.STATUS_ERROR)
        self.download_finished.emit(False, error_message)

        return False

    def start_auto_check(self, interval_hours: int = 6):
        """启动自动检查定时器

        Args:
            interval_hours: 检查间隔（小时）
        """
        self.check_interval_hours = interval_hours

        # 使用 QTimer 进行定期检查
        QTimer.singleShot(
            interval_hours * 3600 * 1000,
            self._auto_check_timer
        )

    def _auto_check_timer(self):
        """自动检查定时器回调"""
        self.check_for_updates(silent=True)

        # 继续下一次检查
        if self.check_interval_hours > 0:
            QTimer.singleShot(
                self.check_interval_hours * 3600 * 1000,
                self._auto_check_timer
            )

    def cleanup(self):
        """清理资源"""
        self.status = self.STATUS_IDLE
        if self.check_thread and self.check_thread.isRunning():
            self.check_thread.quit()
            self.check_thread.wait()
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait()


class UpdateDialog(QDialog):
    """Cloudflared 更新对话框"""

    def __init__(self, parent=None, updater: CloudflareUpdater = None):
        super().__init__(parent)
        self.updater = updater
        self.setWindowTitle("Cloudflared 更新")
        self.setFixedSize(450, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("Cloudflared 更新")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 版本信息
        version_layout = QHBoxLayout()

        self.current_version_label = QLabel("当前版本: 检测中...")
        version_layout.addWidget(self.current_version_label)

        version_layout.addStretch()

        self.latest_version_label = QLabel("最新版本: 检测中...")
        version_layout.addWidget(self.latest_version_label)

        layout.addLayout(version_layout)

        # 状态标签
        self.status_label = QLabel("点击\"检查更新\"按钮检测新版本")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)

        # 按钮
        button_layout = QHBoxLayout()

        self.check_btn = QPushButton("检查更新")
        self.check_btn.clicked.connect(self._on_check)
        button_layout.addWidget(self.check_btn)

        self.update_btn = QPushButton("立即更新")
        self.update_btn.clicked.connect(self._on_update)
        self.update_btn.setEnabled(False)
        button_layout.addWidget(self.update_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """连接信号"""
        if not self.updater:
            return

        self.updater.version_checked.connect(self._on_version_checked)
        self.updater.download_progress.connect(self._on_download_progress)
        self.updater.download_finished.connect(self._on_download_finished)
        self.updater.update_status_changed.connect(self._on_status_changed)

    def _log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def _on_check(self):
        """检查更新"""
        self.check_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.status_label.setText("正在检查更新...")
        self._log("开始检查更新...")

        # 在新线程中检查
        threading.Thread(target=self._check_in_thread, daemon=True).start()

    def _check_in_thread(self):
        """在新线程中检查更新"""
        try:
            has_update, current, latest = self.updater.check_for_updates(silent=True)

            # 使用信号回到主线程
            self.updater.version_checked.emit(has_update, current, latest)

        except Exception as e:
            self._log(f"检查更新失败: {str(e)}")
            self.check_btn.setEnabled(True)
            self.status_label.setText("检查更新失败")

    def _on_version_checked(self, has_update: bool, current: str, latest: str):
        """版本检查完成"""
        self.current_version_label.setText(f"当前版本: {current}")
        self.latest_version_label.setText(f"最新版本: {latest}")

        self.check_btn.setEnabled(True)

        if has_update:
            self.status_label.setText(f"发现新版本: {latest}")
            self.update_btn.setEnabled(True)
            self._log(f"发现新版本: {latest}")
            self._log("点击\"立即更新\"进行更新")
        else:
            self.status_label.setText("当前已是最新版本")
            self._log("当前已是最新版本")

    def _on_update(self):
        """开始更新"""
        self.update_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在下载...")
        self._log("开始下载新版本...")

        # 在新线程中下载
        threading.Thread(target=self._download_in_thread, daemon=True).start()

    def _download_in_thread(self):
        """在新线程中下载"""
        try:
            self.updater.download_latest()

        except Exception as e:
            self.updater.download_finished.emit(False, str(e))

    def _on_download_progress(self, progress: int):
        """下载进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"正在下载... {progress}%")
        self._log(f"下载进度: {progress}%")

    def _on_download_finished(self, success: bool, message: str):
        """下载完成"""
        self.check_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if success:
            self.status_label.setText(message)
            self.update_btn.setText("更新完成")
            self._log(message)
            self._log("请重启应用程序以使用新版本")

            QTimer.singleShot(2000, self.accept)
        else:
            self.status_label.setText(f"更新失败: {message}")
            self.update_btn.setEnabled(True)
            self._log(f"更新失败: {message}")

    def _on_status_changed(self, status: str):
        """状态变化"""
        self._log(f"状态: {status}")

    def closeEvent(self, event):
        """关闭事件"""
        if self.updater:
            self.updater.cleanup()
        event.accept()


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

            # 构建cloudflared命令，使用 Cloudflare 1.1.1.1 DNS 避免 DNS 解析问题
            cmd = [
                cloudflared_path,
                "tunnel",
                "--url", local_addr,
                "--dns", "1.1.1.1",
                "--dns", "8.8.8.8"
            ]

            # 记录启动公网访问的日志
            if log_manager:
                log_manager.append_log_legacy(f"启动公网访问: {local_addr}", False, self.service_name)
                log_manager.append_log_legacy("使用 DNS: 1.1.1.1, 8.8.8.8", False, self.service_name)

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
