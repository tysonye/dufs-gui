# pyright: reportCallIssue=false
# pyright: reportAny=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownLambdaType=false
import time
import re
import threading
from typing import TYPE_CHECKING
from PyQt5.QtCore import pyqtSignal, QObject, QTimer, Qt

if TYPE_CHECKING:
    # 使用字符串避免循环导入
    MainWindow = object


class LogManager(QObject):
    """日志管理类，负责处理日志相关功能（线程安全）"""

    # 日志信号
    log_signal: pyqtSignal = pyqtSignal(str, bool, str)
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
        # 连接信号，使用QueuedConnection确保在UI线程中执行
        self.log_signal.connect(
            self._append_log_ui, Qt.QueuedConnection
        )
        # 连接日志缓冲刷新信号
        self.flush_log_buffer_signal.connect(
            self._flush_log_buffer, Qt.QueuedConnection
        )
    
    def append_log(self, message: str, error: bool = False, service_name: str = "") -> None:
        """添加日志条目,将专业日志格式转换为易懂文字"""
        # 格式化日志消息
        timestamp = time.strftime("%H:%M:%S")
        service_tag = f"[{service_name}] " if service_name else ""

        # 根据错误级别设置日志级别和颜色
        if error:
            level = "ERROR"
        else:
            level = "INFO"

        # 将专业日志格式转换为易懂文字
        readable_message = self._make_log_readable(message)

        # 构建日志消息,包含时间戳和级别
        log_message = f"[{timestamp}] [{level}] {service_tag}{readable_message}"

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
                
                # 添加日志到服务缓冲区
                self.service_log_buffers[service_name].append((log_message, error))
                
                # 优化批量刷新条件
                should_flush = len(self.service_log_buffers[service_name]) >= 3
            else:
                should_flush = False

        # 在锁外触发信号，避免死锁
        if service_name:
            if should_flush:  # 降低缓冲区大小，确保日志及时显示
                # 触发批量刷新
                self.flush_log_buffer_signal.emit(service_name)
        else:
            # 对于无服务名称的日志，直接更新UI
            self.log_signal.emit(log_message, error, service_name)
    
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
        """批量刷新服务日志缓冲区到UI（线程安全）"""
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
            for log_message, error in log_entries:
                # 使用信号槽机制更新UI
                self.log_signal.emit(log_message, error, service_name)
        except Exception as e:
            # 捕获所有异常，避免日志刷新导致阻塞
            print(f"日志缓冲刷新失败: {str(e)}")
    
    def _append_log_ui(self, message: str, error: bool = False, service_name: str = "") -> None:
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
                        self.main_window.log_window.add_log(message, error)
                except Exception as e:
                    print(f"添加日志到窗口失败: {str(e)}")
            else:
                # 如果日志窗口不存在，只打印到控制台
                print(f"日志: {message}")
        except Exception as e:
            # 捕获所有异常，避免日志记录导致阻塞
            print(f"日志记录失败: {str(e)}")
