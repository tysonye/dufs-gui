"""自动保存模块 - 负责配置的定时自动保存（加强版，带抖动保护）"""

import time
from PyQt5.QtCore import QTimer
from typing import Callable, Optional


class AutoSaver:
    """自动保存管理器 - 独立负责配置的定时自动保存（加强版）

    改进点：
    1. 添加抖动保护 - 短时间内多次触发只保存一次
    2. 添加脏数据标志 - 只在数据变化时才保存
    3. 添加最近保存时间检查 - 避免过于频繁的保存
    """

    DEFAULT_INTERVAL = 30000  # 默认30秒
    DEBOUNCE_INTERVAL = 2000  # 抖动保护间隔（2秒）
    MIN_SAVE_INTERVAL = 5000  # 最小保存间隔（5秒）

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

        # 抖动保护相关
        self._is_dirty = False  # 脏数据标志
        self._last_save_time = 0  # 上次保存时间
        self._pending_save = False  # 有待保存的数据
        self._debounce_timer: Optional[QTimer] = None  # 抖动定时器

    def start(self, parent=None):
        """启动自动保存定时器"""
        self._timer = QTimer(parent)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(self._interval_ms)

        # 初始化抖动定时器
        self._debounce_timer = QTimer(parent)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_save)

    def stop(self):
        """停止自动保存定时器"""
        if self._timer and self._timer.isActive():
            self._timer.stop()
        if self._debounce_timer and self._debounce_timer.isActive():
            self._debounce_timer.stop()

    def mark_dirty(self):
        """标记数据已变化（脏数据）"""
        self._is_dirty = True
        self._pending_save = True

    def trigger_save(self, normal_exit: bool = False) -> bool:
        """
        立即触发保存（带抖动保护）

        Args:
            normal_exit: 是否为正常退出

        Returns:
            保存是否成功
        """
        # 检查是否需要保存
        if not self._is_dirty and not normal_exit:
            return True  # 数据未变化，无需保存

        # 检查最近保存时间（防抖）
        current_time = time.time() * 1000
        time_since_last_save = current_time - self._last_save_time

        if time_since_last_save < self.MIN_SAVE_INTERVAL and not normal_exit:
            # 距离上次保存时间太短，启动抖动定时器
            if self._debounce_timer and not self._debounce_timer.isActive():
                remaining = self.MIN_SAVE_INTERVAL - time_since_last_save
                self._debounce_timer.start(int(remaining))
                print(f"[AutoSaver] 保存被防抖，将在 {remaining/1000:.1f} 秒后执行")
            return True

        # 立即执行保存
        return self._do_save(normal_exit)

    def _do_save(self, normal_exit: bool = False) -> bool:
        """执行实际保存操作"""
        try:
            self._save_callback(normal_exit)
            self._last_save_time = time.time() * 1000
            self._is_dirty = False
            self._pending_save = False
            return True
        except Exception as e:
            print(f"自动保存配置失败: {str(e)}")
            return False

    def _on_timeout(self):
        """定时器超时回调（带抖动保护）"""
        if self._is_dirty or self._pending_save:
            self.trigger_save(normal_exit=False)

    def is_running(self) -> bool:
        """检查自动保存是否正在运行"""
        return self._timer is not None and self._timer.isActive()

    def set_interval(self, interval_ms: int):
        """修改自动保存间隔"""
        self._interval_ms = interval_ms
        if self.is_running():
            self._timer.setInterval(interval_ms)

    def get_stats(self) -> dict:
        """获取自动保存统计信息"""
        return {
            'is_dirty': self._is_dirty,
            'pending_save': self._pending_save,
            'last_save_time': self._last_save_time,
            'time_since_last_save': time.time() * 1000 - self._last_save_time,
            'is_running': self.is_running(),
        }
