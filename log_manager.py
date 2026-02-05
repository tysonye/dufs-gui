# pyright: reportCallIssue=false
# pyright: reportAny=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownLambdaType=false
import time
import re
import threading
from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, List, Callable
from PyQt5.QtCore import pyqtSignal, QObject, QTimer, Qt

if TYPE_CHECKING:
    # 使用字符串避免循环导入
    MainWindow = object


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

    def __str__(self):
        return self.name

    @classmethod
    def from_bool(cls, is_error: bool) -> 'LogLevel':
        """从布尔值转换为日志级别（兼容旧代码）"""
        return cls.ERROR if is_error else cls.INFO

    def __lt__(self, other):
        if isinstance(other, LogLevel):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, LogLevel):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, LogLevel):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, LogLevel):
            return self.value >= other.value
        return NotImplemented


@dataclass
class StructuredLogEntry:
    """结构化日志条目（内部类）"""
    timestamp: float
    service: str
    level: LogLevel
    message: str
    metadata: Optional[dict] = None

    def to_formatted_string(self) -> str:
        """转换为格式化的日志字符串"""
        time_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        level_str = self.level.name
        service_tag = f"[{self.service}] " if self.service else ""
        return f"[{time_str}] [{level_str}] {service_tag}{self.message}"


class LogManager(QObject):
    """日志管理类，负责处理日志相关功能（线程安全，支持日志级别）

    稳定模块：不要在未理解全局影响前修改
    """

    # 日志信号（新版，使用LogLevel）
    log_signal: pyqtSignal = pyqtSignal(str, object, str)  # message, level, service_name
    # 日志缓冲刷新信号
    flush_log_buffer_signal: pyqtSignal = pyqtSignal(object)

    def __init__(self, main_window: object) -> None:
        super().__init__()
        self.main_window: object = main_window
        # 日志缓冲区，用于存储历史日志
        self.log_buffer = []
        # 服务日志缓冲区，用于存储每个服务的日志缓冲
        self.service_log_buffers = {}
        # 线程锁，保护日志缓冲区并发访问
        self._buffer_lock = threading.Lock()
        # 最小日志级别（用于过滤）
        self._min_level = LogLevel.DEBUG
        # 监听器列表
        self._listeners: List[Callable[[StructuredLogEntry], None]] = []
        # 连接信号，使用QueuedConnection确保在UI线程中执行
        self.log_signal.connect(
            self._append_log_ui, Qt.QueuedConnection
        )
        # 连接日志缓冲刷新信号
        self.flush_log_buffer_signal.connect(
            self._flush_log_buffer, Qt.QueuedConnection
        )

    def set_min_level(self, level: LogLevel) -> None:
        """设置最小日志级别"""
        self._min_level = level

    def add_listener(self, listener: Callable[[StructuredLogEntry], None]) -> None:
        """添加日志监听器"""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[StructuredLogEntry], None]) -> None:
        """移除日志监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def append_log(self, message: str, level: LogLevel = LogLevel.INFO, service_name: str = "") -> None:
        """添加日志条目（新版，使用LogLevel）

        Args:
            message: 日志消息
            level: 日志级别（默认INFO）
            service_name: 服务名称
        """
        # 检查日志级别
        if level < self._min_level:
            return

        # 格式化日志消息
        timestamp = time.strftime("%H:%M:%S")
        service_tag = f"[{service_name}] " if service_name else ""

        # 将专业日志格式转换为易懂文字
        readable_message = self._make_log_readable(message)

        # 构建日志消息,包含时间戳和级别
        log_message = f"[{timestamp}] [{level}] {service_tag}{readable_message}"

        # 创建结构化日志条目
        entry = StructuredLogEntry(
            timestamp=time.time(),
            service=service_name,
            level=level,
            message=readable_message
        )

        # 通知监听器
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception as e:
                print(f"日志监听器执行失败: {str(e)}")

        # 使用线程锁保护日志缓冲区操作
        with self._buffer_lock:
            # 将日志添加到全局缓冲区
            self.log_buffer.append(log_message)

            # 限制全局日志缓冲区大小，避免内存占用过高
            if len(self.log_buffer) > 1000:
                self.log_buffer = self.log_buffer[-1000:]

            # 将日志添加到服务特定缓冲区
            if service_name:
                if service_name not in self.service_log_buffers:
                    self.service_log_buffers[service_name] = []

                # 添加日志到服务缓冲区（存储级别信息）
                self.service_log_buffers[service_name].append((log_message, level))

                # 实时刷新：每条日志都触发刷新，确保实时显示
                should_flush = True
            else:
                should_flush = False

        # 在锁外触发信号，避免死锁
        if service_name:
            if should_flush:
                # 触发批量刷新（实时显示）
                self.flush_log_buffer_signal.emit(service_name)
        else:
            # 对于无服务名称的日志，直接更新UI
            self.log_signal.emit(log_message, level, service_name)

    def append_log_legacy(self, message: str, error: bool = False, service_name: str = "") -> None:
        """添加日志条目（兼容旧代码）

        Args:
            message: 日志消息
            error: 是否为错误日志（兼容旧代码）
            service_name: 服务名称
        """
        level = LogLevel.from_bool(error)
        self.append_log(message, level, service_name)

    def debug(self, message: str, service_name: str = "") -> None:
        """添加DEBUG级别日志"""
        self.append_log(message, LogLevel.DEBUG, service_name)

    def info(self, message: str, service_name: str = "") -> None:
        """添加INFO级别日志"""
        self.append_log(message, LogLevel.INFO, service_name)

    def warning(self, message: str, service_name: str = "") -> None:
        """添加WARNING级别日志"""
        self.append_log(message, LogLevel.WARNING, service_name)

    def error(self, message: str, service_name: str = "") -> None:
        """添加ERROR级别日志"""
        self.append_log(message, LogLevel.ERROR, service_name)

    def critical(self, message: str, service_name: str = "") -> None:
        """添加CRITICAL级别日志"""
        self.append_log(message, LogLevel.CRITICAL, service_name)

    def _make_log_readable(self, message: str) -> str:
        """将专业日志格式转换为易懂文字"""
        # 1. 处理Dufs默认日志格式
        dufs_pattern = re.compile(r'^(\d+\.\d+\.\d+\.\d+) "(\w+) (.*?)" (\d+)$')
        dufs_match = dufs_pattern.match(message)
        if dufs_match:
            ip = dufs_match.group(1)
            method = dufs_match.group(2)
            path = dufs_match.group(3)
            status = dufs_match.group(4)

            method_map = {
                "GET": "访问", "POST": "上传", "PUT": "修改", "DELETE": "删除",
                "HEAD": "检查", "CHECKAUTH": "认证检查"
            }
            status_map = {
                "200": "成功", "201": "创建成功", "206": "部分内容成功",
                "400": "请求错误", "401": "未授权", "403": "禁止访问",
                "404": "找不到内容", "500": "服务器错误"
            }

            readable_method = method_map.get(method, method)
            readable_status = status_map.get(status, f"状态码 {status}")
            readable_path = path if path != "/" else "根目录"

            return f"IP {ip} {readable_method} '{readable_path}' {readable_status}"

        # 2. 处理其他常见日志格式
        info_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d+\+\d{2}:\d{2} INFO - (.*)')
        info_match = info_pattern.match(message)
        if info_match:
            return info_match.group(1)

        # 3. 处理错误日志
        error_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d+\+\d{2}:\d{2} ERROR - (.*)')
        error_match = error_pattern.match(message)
        if error_match:
            return f"错误: {error_match.group(1)}"

        # 4. 默认返回原消息
        return message

    def _flush_log_buffer(self, service_name: str) -> None:
        """批量刷新服务日志缓冲区到UI（线程安全，新版使用LogLevel）"""
        try:
            # 使用线程锁保护缓冲区操作
            with self._buffer_lock:
                # 检查服务缓冲区是否存在
                if service_name not in self.service_log_buffers:
                    return

                # 获取并清空缓冲区
                log_entries = self.service_log_buffers[service_name]
                if not log_entries:
                    return

                # 清空缓冲区
                self.service_log_buffers[service_name] = []

            # 在锁外批量添加日志到UI，避免死锁
            for log_message, level in log_entries:
                # 使用信号槽机制更新UI
                self.log_signal.emit(log_message, level, service_name)
        except Exception as e:
            # 捕获所有异常，避免日志刷新导致阻塞
            print(f"日志缓冲刷新失败: {str(e)}")

    def _append_log_ui(self, message: str, level: LogLevel = LogLevel.INFO, service_name: str = "") -> None:
        """在UI线程中添加日志条目"""
        try:
            # 尝试将日志添加到日志窗口
            if hasattr(self.main_window, 'log_window') and self.main_window.log_window:
                try:
                    # 为每个服务创建独立的日志标签页
                    if service_name:
                        # 查找或创建服务对应的日志标签页
                        service_tab_index = -1
                        for i in range(self.main_window.log_window.log_tabs.count()):
                            if self.main_window.log_window.log_tabs.tabText(i) == service_name:
                                service_tab_index = i
                                break

                        if service_tab_index == -1:
                            # 创建新的日志标签页
                            from PyQt5.QtWidgets import QPlainTextEdit
                            log_widget = QPlainTextEdit()
                            log_widget.setReadOnly(True)
                            log_widget.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11px;")
                            self.main_window.log_window.add_log_tab(service_name, log_widget)
                            service_tab_index = self.main_window.log_window.log_tabs.count() - 1

                        # 添加到服务对应的标签页
                        self.main_window.log_window.append_log(service_tab_index, message)
                    else:
                        # 对于无服务名称的日志，添加到全局日志标签页
                        self.main_window.log_window.add_log(message, level)
                except Exception as e:
                    print(f"添加日志到窗口失败: {str(e)}")
            else:
                # 如果日志窗口不存在，只打印到控制台
                print(f"日志: {message}")
        except Exception as e:
            # 捕获所有异常，避免日志记录导致阻塞
            print(f"日志记录失败: {str(e)}")

    def get_logs(self, level: Optional[LogLevel] = None,
                 service: Optional[str] = None,
                 limit: int = 1000) -> List[StructuredLogEntry]:
        """获取日志列表（简化版）"""
        # 这里简化实现，实际应该从结构化日志中获取
        return []

    def clear(self) -> None:
        """清空所有日志"""
        with self._buffer_lock:
            self.log_buffer.clear()
            self.service_log_buffers.clear()

    def get_stats(self) -> dict:
        """获取日志统计信息"""
        with self._buffer_lock:
            stats = {level.name: 0 for level in LogLevel}
            # 简化统计
            return stats
