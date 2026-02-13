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
        # 1. 处理Dufs带时间戳的日志格式 (如: 2026-02-11T10:42:45+08:00 INFO - 127.0.0.1 "GET /" 200)
        # 也处理 method 和 path 为 "-" 的情况 (如: 2026-02-11T10:42:45+08:00 INFO - 127.0.0.1 "- -" 200)
        dufs_timestamp_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d+[\+\-]\d{2}:\d{2} (\w+) - (\d+\.\d+\.\d+\.\d+) "([^"]*)" (\d+)$')
        dufs_timestamp_match = dufs_timestamp_pattern.match(message)
        if dufs_timestamp_match:
            level = dufs_timestamp_match.group(1)
            ip = dufs_timestamp_match.group(2)
            request_part = dufs_timestamp_match.group(3)
            status = dufs_timestamp_match.group(4)

            # 解析请求部分 (method path)
            request_match = re.match(r'^(\S+)\s+(.+)$', request_part)
            if request_match:
                method = request_match.group(1)
                path = request_match.group(2)
            else:
                method = "-"
                path = "-"

            method_map = {
                "GET": "访问", "POST": "上传", "PUT": "修改", "DELETE": "删除",
                "HEAD": "检查", "CHECKAUTH": "认证检查", "-": "访问"
            }
            status_map = {
                "200": "成功", "201": "创建成功", "206": "部分内容成功",
                "400": "请求错误", "401": "未授权", "403": "禁止访问",
                "404": "找不到内容", "500": "服务器错误"
            }

            readable_method = method_map.get(method, method)
            readable_status = status_map.get(status, f"状态码 {status}")
            readable_path = path if path != "/" and path != "-" else "根目录"

            return f"IP {ip} {readable_method} '{readable_path}' {readable_status}"

        # 2. 处理Dufs默认日志格式 (无时间戳)
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

        # 3. 处理 cloudflared 日志格式 (如: 2025-02-11T10:42:45Z INF Starting tunnel)
        # cloudflared 使用 Z 表示 UTC，日志级别为 INF/ERR/WRN 等
        cloudflared_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d+Z (\w+) (.*)$')
        cloudflared_match = cloudflared_pattern.match(message)
        if cloudflared_match:
            level = cloudflared_match.group(1)
            msg = cloudflared_match.group(2)

            # 定义 cloudflared 日志翻译映射表
            translations = {
                # 隧道创建
                'Your quick Tunnel has been created': None,  # 特殊处理，提取URL
                # 连接相关
                'Connected to': None,  # 特殊处理，提取位置
                'Connecting to': None,  # 特殊处理，提取位置
                'Connection registered': '连接已注册',
                'Registered tunnel connection': '已注册隧道连接',
                # 启动相关
                'Starting tunnel': '正在启动公网隧道...',
                'Initial protocol': '初始化协议',
                'Using': '使用功能',
                # 配置相关
                'Cannot determine default configuration path': '使用默认配置（无需配置文件）',
                'GOOS': '系统信息',
                'Settings:': '配置设置',
                # 版本信息
                'cloudflared version': 'Cloudflared 版本',
                'Version': '版本信息',
                # 服务相关
                'Starting metrics server': '启动监控服务',
                # 关闭相关
                'Tunnel server stopped': '公网隧道已停止',
                'Initiating graceful shutdown': '正在优雅关闭...',
                'context canceled': '操作已取消',
                # ICMP 代理
                'ICMP proxy will use': 'ICMP 代理使用',
                'as source for IPv4': '作为 IPv4 源地址',
                'as source for IPv6': '作为 IPv6 源地址',
                # 连接偏好
                'Tunnel connection curve preferences': '隧道连接加密偏好',
                # 证书相关
                'does not support loading the system root certificate pool': '不支持加载系统根证书池',
                'Please use --origincert': '请使用 --origincert 参数指定证书路径',
                # 更新相关
                'will not automatically update on Windows systems': '在 Windows 系统上不会自动更新',
                # 感谢信息
                'Thank you for trying Cloudflare Tunnel': '欢迎使用 Cloudflare Tunnel',
                'be aware that these account-less Tunnels have no uptime guarantee': '注意：无账户隧道不保证服务可用性',
                # 错误相关
                'Error opening metrics server listener': '监控服务启动失败: 端口被占用',
                'failed to dial edge': '连接 Cloudflare 边缘节点失败: 网络超时',
                'bind: Only one usage of each socket address': '端口已被占用，请稍后再试',
            }

            # 尝试匹配翻译
            for pattern, translation in translations.items():
                if pattern in msg:
                    if pattern == 'Your quick Tunnel has been created':
                        url_match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', msg)
                        if url_match:
                            return f"公网隧道已创建: {url_match.group(0)}"
                        return "公网隧道已创建"
                    elif pattern in ['Connected to', 'Connecting to']:
                        # 尝试匹配 "Connecting to [region: LAX]" 或 "Connected to LAX" 格式
                        location_match = re.search(r'\[region:\s*(\w+)\]|Connected to\s+(\w+)|Connecting to.*?\s(\w+)[\s\]]', msg)
                        if location_match:
                            # 获取第一个非None的匹配组
                            location = location_match.group(1) or location_match.group(2) or location_match.group(3)
                            location_names = {
                                'LAX': '洛杉矶', 'SFO': '旧金山', 'SEA': '西雅图',
                                'NYC': '纽约', 'IAD': '华盛顿', 'MIA': '迈阿密',
                                'ORD': '芝加哥', 'DFW': '达拉斯', 'DEN': '丹佛',
                                'ATL': '亚特兰大', 'BOS': '波士顿', 'PHX': '凤凰城',
                                'SIN': '新加坡', 'HKG': '香港', 'NRT': '东京',
                                'LHR': '伦敦', 'FRA': '法兰克福', 'AMS': '阿姆斯特丹',
                                'SJC': '圣何塞', 'YYZ': '多伦多', 'SCL': '圣地亚哥',
                                'GRU': '圣保罗', 'JNB': '约翰内斯堡', 'SYD': '悉尼',
                                'MRS': '马赛', 'MXP': '米兰', 'ARN': '斯德哥尔摩',
                            }
                            location_cn = location_names.get(location, location)
                            if 'Connecting to' in msg:
                                return f"正在连接到 {location_cn}({location}) 数据中心..."
                            return f"已连接到 {location_cn}({location}) 数据中心"
                        return "已连接到 Cloudflare 数据中心"
                    elif pattern == 'Initial protocol':
                        protocol_match = re.search(r'Initial protocol (\w+)', msg)
                        protocol = protocol_match.group(1) if protocol_match else '未知'
                        return f"初始化协议: {protocol}"
                    elif pattern == 'Using':
                        using_match = re.search(r'Using \[(\w+)\]', msg)
                        feature = using_match.group(1) if using_match else msg
                        return f"使用功能: {feature}"
                    elif pattern == 'GOOS':
                        goos_match = re.search(r'GOOS: (\w+), GOARCH: (\w+)', msg)
                        if goos_match:
                            return f"系统: {goos_match.group(1)} {goos_match.group(2)}"
                        return "系统信息"
                    elif pattern == 'cloudflared version':
                        version_match = re.search(r'cloudflared version ([\d.]+)', msg)
                        version = version_match.group(1) if version_match else '未知'
                        return f"Cloudflared 版本: {version}"
                    elif pattern == 'Starting metrics server':
                        addr_match = re.search(r'on ([\d.:]+)', msg)
                        addr = addr_match.group(1) if addr_match else '本地'
                        return f"启动监控服务: {addr}"
                    elif pattern == 'Settings:':
                        # 简化配置信息
                        return "加载配置设置..."
                    elif pattern == 'Version':
                        # 提取版本号
                        version_match = re.search(r'Version\s+([\w.]+)', msg)
                        if version_match:
                            return f"版本: {version_match.group(1)}"
                        return "版本信息"
                    elif pattern == 'ICMP proxy will use':
                        # 提取 IP 地址和类型
                        ip_match = re.search(r'use ([\d.]+|[\w:]+).*?(IPv4|IPv6)', msg)
                        if ip_match:
                            ip_type = ip_match.group(2)
                            return f"ICMP 代理已配置 ({ip_type})"
                        return "ICMP 代理配置"
                    elif pattern == 'Tunnel connection curve preferences':
                        return "隧道加密连接已建立"
                    elif pattern == 'does not support loading the system root certificate pool':
                        return "证书配置提示: 使用内置证书池"
                    elif pattern == 'will not automatically update on Windows systems':
                        return "提示: Windows 系统需手动更新 cloudflared"
                    elif pattern == 'Thank you for trying Cloudflare Tunnel':
                        return "欢迎使用 Cloudflare 隧道服务"
                    elif pattern == 'be aware that these account-less Tunnels have no uptime guarantee':
                        return "提示: 免费隧道不保证 100% 可用性"
                    elif pattern == 'Registered tunnel connection':
                        # 提取连接信息
                        conn_match = re.search(r'connection=([\w-]+).*?ip=([\d.]+).*?location=(\w+)', msg)
                        if conn_match:
                            location = conn_match.group(3)
                            location_names = {
                                'LAX': '洛杉矶', 'SFO': '旧金山', 'SEA': '西雅图',
                                'NYC': '纽约', 'IAD': '华盛顿', 'MIA': '迈阿密',
                                'ORD': '芝加哥', 'DFW': '达拉斯', 'DEN': '丹佛',
                                'ATL': '亚特兰大', 'BOS': '波士顿', 'PHX': '凤凰城',
                                'SIN': '新加坡', 'HKG': '香港', 'NRT': '东京',
                                'LHR': '伦敦', 'FRA': '法兰克福', 'AMS': '阿姆斯特丹',
                                'SJC': '圣何塞', 'YYZ': '多伦多', 'SCL': '圣地亚哥',
                                'GRU': '圣保罗', 'JNB': '约翰内斯堡', 'SYD': '悉尼',
                                'MRS': '马赛', 'MXP': '米兰', 'ARN': '斯德哥尔摩',
                            }
                            location_cn = location_names.get(location, location)
                            return f"隧道连接已注册 ({location_cn})"
                        return "隧道连接已注册"
                    elif translation:
                        return translation

            # 处理 tunnelID 等技术细节
            if 'tunnelID' in msg or ('Connection' in msg and 'registered' in msg):
                return "正在初始化隧道连接..."

            # 处理 Generated Connector ID
            if 'Generated Connector ID' in msg or 'Connector ID' in msg:
                return "生成连接器 ID..."

            # 处理错误和警告
            if level == 'ERR':
                # 简化常见错误
                if 'bind:' in msg and 'Only one usage' in msg:
                    return "错误: 端口已被占用，请稍后再试"
                elif 'failed to dial edge' in msg:
                    return "错误: 连接 Cloudflare 失败，请检查网络"
                elif 'connection attempt failed' in msg.lower():
                    return "错误: 连接超时，请检查网络"
                return f"错误: {msg}"
            elif level == 'WRN':
                return f"警告: {msg}"
            else:
                # INF 级别返回简化消息
                return msg

        # 4. 处理其他常见日志格式 (只提取消息部分)
        info_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d+[\+\-]\d{2}:\d{2} INFO - (.*)')
        info_match = info_pattern.match(message)
        if info_match:
            return info_match.group(1)

        # 5. 处理错误日志
        error_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d+[\+\-]\d{2}:\d{2} ERROR - (.*)')
        error_match = error_pattern.match(message)
        if error_match:
            return f"错误: {error_match.group(1)}"

        # 6. 默认返回原消息
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
