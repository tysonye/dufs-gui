"""事件总线模块 - 实现发布-订阅模式，解耦模块间通信"""

from typing import Callable, Dict, List, Any
from PyQt5.QtCore import QObject, pyqtSignal, Qt


class EventBus(QObject):
    """事件总线 - 全局事件发布订阅系统
    
    使用单例模式确保全局唯一实例
    支持跨线程的事件分发
    """
    
    _instance = None
    
    # 通用事件信号
    _event_signal = pyqtSignal(str, object)  # 事件名, 数据
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_signal.connect(self._dispatch_event, Qt.QueuedConnection)
    
    def subscribe(self, event_name: str, callback: Callable) -> None:
        """订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数，接收事件数据作为参数
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)
    
    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """取消订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in self._subscribers:
            if callback in self._subscribers[event_name]:
                self._subscribers[event_name].remove(callback)
    
    def publish(self, event_name: str, data: Any = None) -> None:
        """发布事件
        
        Args:
            event_name: 事件名称
            data: 事件数据
        """
        # 使用信号机制确保跨线程安全
        self._event_signal.emit(event_name, data)
    
    def _dispatch_event(self, event_name: str, data: Any) -> None:
        """分发事件到所有订阅者
        
        Args:
            event_name: 事件名称
            data: 事件数据
        """
        if event_name in self._subscribers:
            # 复制列表避免在迭代时修改
            callbacks = self._subscribers[event_name].copy()
            for callback in callbacks:
                try:
                    if data is not None:
                        callback(data)
                    else:
                        callback()
                except Exception as e:
                    print(f"事件处理失败 [{event_name}]: {str(e)}")
    
    def clear(self, event_name: str = None) -> None:
        """清除订阅
        
        Args:
            event_name: 事件名称，如果为None则清除所有订阅
        """
        if event_name is None:
            self._subscribers.clear()
        elif event_name in self._subscribers:
            del self._subscribers[event_name]


# 全局事件总线实例
event_bus = EventBus()


# 预定义的事件名称
class Events:
    """预定义的事件名称常量"""
    
    # 服务相关事件
    SERVICE_STATUS_CHANGED = "service.status_changed"
    SERVICE_ADDED = "service.added"
    SERVICE_DELETED = "service.deleted"
    SERVICE_EDITED = "service.edited"
    
    # 配置相关事件
    CONFIG_SAVED = "config.saved"
    CONFIG_LOADED = "config.loaded"
    
    # 日志相关事件
    LOG_APPENDED = "log.appended"
    
    # 托盘相关事件
    TRAY_MENU_UPDATE = "tray.menu_update"
    TRAY_MESSAGE_SHOW = "tray.message_show"
    
    # 应用生命周期事件
    APP_STARTING = "app.starting"
    APP_EXITING = "app.exiting"
