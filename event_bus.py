"""事件总线模块 - 实现发布-订阅模式，解耦模块间通信（加强版）"""

import weakref
import traceback
from typing import Callable, Dict, List, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, Qt


class EventBus(QObject):
    """事件总线 - 全局事件发布订阅系统（加强版，带防护机制）
    
    使用单例模式确保全局唯一实例
    支持跨线程的事件分发
    添加异常防护和生命周期管理
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
        
        # 使用弱引用存储订阅者，避免内存泄漏
        self._subscribers: Dict[str, List[weakref.ref]] = {}
        self._hard_refs: Dict[str, List[Callable]] = {}  # 用于非方法回调
        
        # 调试模式
        self._debug_mode = False
        
        # 事件统计
        self._event_stats: Dict[str, int] = {}
        
        self._event_signal.connect(self._dispatch_event, Qt.QueuedConnection)
    
    def set_debug_mode(self, enabled: bool = True):
        """设置调试模式"""
        self._debug_mode = enabled
    
    def _log(self, message: str):
        """调试日志"""
        if self._debug_mode:
            print(f"[EventBus] {message}")
    
    def subscribe(self, event_name: str, callback: Callable, use_weak_ref: bool = True) -> None:
        """订阅事件（加强版，支持弱引用）
        
        Args:
            event_name: 事件名称
            callback: 回调函数，接收事件数据作为参数
            use_weak_ref: 是否使用弱引用（默认True，避免内存泄漏）
        """
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
            self._hard_refs[event_name] = []
        
        # 检查是否已订阅
        if use_weak_ref:
            # 使用弱引用存储方法绑定
            ref = weakref.ref(callback)
            if ref not in self._subscribers[event_name]:
                self._subscribers[event_name].append(ref)
                self._log(f"订阅事件 '{event_name}' (弱引用)")
        else:
            # 使用硬引用（用于普通函数）
            if callback not in self._hard_refs[event_name]:
                self._hard_refs[event_name].append(callback)
                self._log(f"订阅事件 '{event_name}' (硬引用)")
    
    def unsubscribe(self, event_name: str, callback: Callable) -> bool:
        """取消订阅事件（加强版）
        
        Args:
            event_name: 事件名称
            callback: 回调函数
            
        Returns:
            bool: 是否成功取消
        """
        removed = False
        
        if event_name in self._subscribers:
            # 尝试从弱引用列表中移除
            ref = weakref.ref(callback)
            if ref in self._subscribers[event_name]:
                self._subscribers[event_name].remove(ref)
                removed = True
                self._log(f"取消订阅事件 '{event_name}' (弱引用)")
            
            # 尝试从硬引用列表中移除
            if event_name in self._hard_refs and callback in self._hard_refs[event_name]:
                self._hard_refs[event_name].remove(callback)
                removed = True
                self._log(f"取消订阅事件 '{event_name}' (硬引用)")
        
        return removed
    
    def publish(self, event_name: str, data: Any = None, source: str = None) -> None:
        """发布事件（加强版，带来源追踪）
        
        Args:
            event_name: 事件名称
            data: 事件数据
            source: 事件来源（用于调试）
        """
        # 统计事件
        self._event_stats[event_name] = self._event_stats.get(event_name, 0) + 1
        
        if self._debug_mode:
            src_info = f" from {source}" if source else ""
            print(f"[EventBus] 发布事件 '{event_name}'{src_info}")
        
        # 使用信号机制确保跨线程安全
        self._event_signal.emit(event_name, data)
    
    def _dispatch_event(self, event_name: str, data: Any) -> None:
        """分发事件到所有订阅者（加强版，带异常防护）
        
        Args:
            event_name: 事件名称
            data: 事件数据
        """
        if event_name not in self._subscribers:
            return
        
        # 收集所有有效的回调
        callbacks = []
        
        # 处理弱引用回调
        dead_refs = []
        for ref in self._subscribers[event_name]:
            callback = ref()
            if callback is not None:
                callbacks.append(callback)
            else:
                dead_refs.append(ref)
        
        # 清理已失效的弱引用
        for ref in dead_refs:
            self._subscribers[event_name].remove(ref)
            self._log(f"清理失效的订阅者 '{event_name}'")
        
        # 处理硬引用回调
        if event_name in self._hard_refs:
            callbacks.extend(self._hard_refs[event_name])
        
        # 执行回调（带异常防护）
        for callback in callbacks:
            try:
                if data is not None:
                    callback(data)
                else:
                    callback()
            except Exception as e:
                # 记录详细错误信息，但不中断其他回调
                error_msg = f"事件处理失败 [{event_name}]: {str(e)}"
                print(error_msg)
                if self._debug_mode:
                    traceback.print_exc()
    
    def clear(self, event_name: str = None) -> None:
        """清除订阅
        
        Args:
            event_name: 事件名称，如果为None则清除所有订阅
        """
        if event_name is None:
            self._subscribers.clear()
            self._hard_refs.clear()
            self._log("清除所有订阅")
        elif event_name in self._subscribers:
            del self._subscribers[event_name]
            if event_name in self._hard_refs:
                del self._hard_refs[event_name]
            self._log(f"清除事件 '{event_name}' 的所有订阅")
    
    def get_stats(self) -> Dict[str, int]:
        """获取事件统计信息"""
        return self._event_stats.copy()
    
    def get_subscriber_count(self, event_name: str = None) -> int:
        """获取订阅者数量
        
        Args:
            event_name: 事件名称，如果为None则返回所有订阅者总数
        """
        if event_name:
            weak_count = len(self._subscribers.get(event_name, []))
            hard_count = len(self._hard_refs.get(event_name, []))
            return weak_count + hard_count
        else:
            total = 0
            for event in self._subscribers:
                total += len(self._subscribers[event])
            for event in self._hard_refs:
                total += len(self._hard_refs[event])
            return total


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
