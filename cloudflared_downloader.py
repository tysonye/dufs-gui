"""cloudflared下载器模块，带进度对话框"""

import os
import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from constants import get_lib_path


class DownloadThread(QThread):
    """下载线程"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    download_finished = pyqtSignal(bool, str)

    def __init__(self, url, temp_path, final_path):
        super().__init__()
        self.url = url
        self.temp_path = temp_path
        self.final_path = final_path
        self._is_running = True

    def run(self):
        try:
            self.status_updated.emit("正在连接服务器...")
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            self.status_updated.emit("正在下载...")
            with open(self.temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self._is_running:
                        break
                    if chunk:
                        _ = f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress_updated.emit(progress)

            if self._is_running:
                # 下载完成，重命名临时文件为正式文件
                try:
                    if os.path.exists(self.final_path):
                        os.remove(self.final_path)
                    os.rename(self.temp_path, self.final_path)
                    self.download_finished.emit(True, "下载完成")
                except Exception as e:
                    self.download_finished.emit(False, f"文件保存失败: {str(e)}")
            else:
                # 下载被取消，删除临时文件
                try:
                    if os.path.exists(self.temp_path):
                        os.remove(self.temp_path)
                except Exception:
                    pass
                self.download_finished.emit(False, "下载已取消")
        except Exception as e:
            # 下载失败，删除临时文件
            try:
                if os.path.exists(self.temp_path):
                    os.remove(self.temp_path)
            except Exception:
                pass
            self.download_finished.emit(False, f"下载失败: {str(e)}")

    def stop(self):
        self._is_running = False


class CloudflaredDownloadDialog(QDialog):
    """cloudflared下载进度对话框"""

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

        self.download_thread = DownloadThread(url, temp_path, final_path)
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
            # 显示文件大小
            try:
                lib_dir = get_lib_path()
                final_path = os.path.join(lib_dir, "cloudflared.exe")
                file_size = os.path.getsize(final_path)
                self.status_label.setText(f"下载完成! 文件大小: {file_size / 1024 / 1024:.2f} MB")
            except Exception:
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


def check_and_download_cloudflared(parent=None, max_retries=3):
    """检查并下载cloudflared

    Args:
        parent: 父窗口
        max_retries: 最大重试次数

    Returns:
        bool: 是否成功（已存在或下载成功）
    """
    # 检查是否已存在（优先从 _internal/lib 文件夹查找）
    lib_dir = get_lib_path()
    cloudflared_path = os.path.join(lib_dir, "cloudflared.exe")
    if os.path.exists(cloudflared_path):
        return True

    # 清理可能存在的临时文件
    temp_path = os.path.join(lib_dir, "cloudflared.exe.tmp")
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
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
