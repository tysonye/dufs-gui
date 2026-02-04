"""结构化日志模块 - 提供分级过滤和结构化日志支持"""

import time
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, List, Callable


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()
    
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
    """结构化日志条目"""
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


class StructuredLogManager:
    """结构化日志管理器 - 支持分级过滤和批量操作"""
    
    def __init__(self, min_level: LogLevel = LogLevel.INFO):
        """
        初始化结构化日志管理器
        
        Args:
            min_level: 最小日志级别，低于此级别的日志将被忽略
        """
        self.min_level = min_level
        self._logs: List[StructuredLogEntry] = []
        self._filters: List[Callable[[StructuredLogEntry], bool]] = []
        self._listeners: List[Callable[[StructuredLogEntry], None]] = []
    
    def set_min_level(self, level: LogLevel) -> None:
        """设置最小日志级别"""
        self.min_level = level
    
    def add_filter(self, filter_func: Callable[[StructuredLogEntry], bool]) -> None:
        """添加日志过滤器
        
        Args:
            filter_func: 过滤器函数，返回True表示保留该日志
        """
        self._filters.append(filter_func)
    
    def remove_filter(self, filter_func: Callable[[StructuredLogEntry], bool]) -> None:
        """移除日志过滤器"""
        if filter_func in self._filters:
            self._filters.remove(filter_func)
    
    def add_listener(self, listener: Callable[[StructuredLogEntry], None]) -> None:
        """添加日志监听器
        
        Args:
            listener: 监听器函数，当日志被添加时调用
        """
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[StructuredLogEntry], None]) -> None:
        """移除日志监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def log(self, message: str, level: LogLevel = LogLevel.INFO, 
            service: str = "", metadata: Optional[dict] = None) -> bool:
        """添加日志条目
        
        Args:
            message: 日志消息
            level: 日志级别
            service: 服务名称
            metadata: 附加元数据
            
        Returns:
            bool: 是否成功添加日志
        """
        # 检查日志级别
        if level < self.min_level:
            return False
        
        # 创建日志条目
        entry = StructuredLogEntry(
            timestamp=time.time(),
            service=service,
            level=level,
            message=message,
            metadata=metadata
        )
        
        # 应用过滤器
        for filter_func in self._filters:
            if not filter_func(entry):
                return False
        
        # 添加到日志列表
        self._logs.append(entry)
        
        # 限制日志数量
        if len(self._logs) > 10000:
            self._logs = self._logs[-5000:]
        
        # 通知监听器
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception as e:
                print(f"日志监听器执行失败: {str(e)}")
        
        return True
    
    def debug(self, message: str, service: str = "", metadata: Optional[dict] = None) -> bool:
        """添加DEBUG级别日志"""
        return self.log(message, LogLevel.DEBUG, service, metadata)
    
    def info(self, message: str, service: str = "", metadata: Optional[dict] = None) -> bool:
        """添加INFO级别日志"""
        return self.log(message, LogLevel.INFO, service, metadata)
    
    def warning(self, message: str, service: str = "", metadata: Optional[dict] = None) -> bool:
        """添加WARNING级别日志"""
        return self.log(message, LogLevel.WARNING, service, metadata)
    
    def error(self, message: str, service: str = "", metadata: Optional[dict] = None) -> bool:
        """添加ERROR级别日志"""
        return self.log(message, LogLevel.ERROR, service, metadata)
    
    def critical(self, message: str, service: str = "", metadata: Optional[dict] = None) -> bool:
        """添加CRITICAL级别日志"""
        return self.log(message, LogLevel.CRITICAL, service, metadata)
    
    def get_logs(self, level: Optional[LogLevel] = None, 
                 service: Optional[str] = None,
                 limit: int = 1000) -> List[StructuredLogEntry]:
        """获取日志列表
        
        Args:
            level: 过滤的日志级别，只返回大于等于此级别的日志
            service: 过滤的服务名称
            limit: 最大返回数量
            
        Returns:
            List[StructuredLogEntry]: 日志条目列表
        """
        result = self._logs.copy()
        
        if level is not None:
            result = [log for log in result if log.level >= level]
        
        if service is not None:
            result = [log for log in result if log.service == service]
        
        return result[-limit:]
    
    def clear(self) -> None:
        """清空所有日志"""
        self._logs.clear()
    
    def get_stats(self) -> dict:
        """获取日志统计信息"""
        stats = {level.name: 0 for level in LogLevel}
        for log in self._logs:
            stats[log.level.name] += 1
        return stats


# 全局结构化日志管理器实例
structured_log_manager = StructuredLogManager()
