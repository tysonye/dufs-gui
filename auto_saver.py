"""自动保存模块 - 负责配置的定时自动保存"""

from PyQt5.QtCore import QTimer
from typing import Callable, Optional


class AutoSaver:
    """自动保存管理器 - 独立负责配置的定时自动保存"""

    DEFAULT_INTERVAL = 30000  # 默认30秒

    def __init__(self, save_callback: Callable[[bool], None], interval_ms: int = DEFAULT_INTERVAL):
        """
        初始化自动保存器

        Args:
            save_callback: 保存回调函数，接收normal_exit参数
            interval_ms: 自动保存间隔（毫秒）
        """
        self._save_callback = save_callback
        self._interval_ms = interval_ms
        self._timer: Optional[QTimer] = None

    def start(self, parent=None):
        """启动自动保存定时器"""
        self._timer = QTimer(parent)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(self._interval_ms)

    def stop(self):
        """停止自动保存定时器"""
        if self._timer and self._timer.isActive():
            self._timer.stop()

    def trigger_save(self, normal_exit: bool = False) -> bool:
        """
        立即触发保存

        Args:
            normal_exit: 是否为正常退出

        Returns:
            保存是否成功
        """
        try:
            self._save_callback(normal_exit)
            return True
        except Exception as e:
            print(f"自动保存配置失败: {str(e)}")
            return False

    def _on_timeout(self):
        """定时器超时回调"""
        self.trigger_save(normal_exit=False)

    def is_running(self) -> bool:
        """检查自动保存是否正在运行"""
        return self._timer is not None and self._timer.isActive()

    def set_interval(self, interval_ms: int):
        """修改自动保存间隔"""
        self._interval_ms = interval_ms
        if self.is_running():
            self._timer.setInterval(interval_ms)
