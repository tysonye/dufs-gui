"""服务状态模块 - 使用 Enum 实现现代化的状态管理"""

from enum import Enum, auto
from typing import Dict, Set, Optional


class ServiceState(Enum):
    """服务状态枚举
    
    使用 Enum 替代字符串状态，提供类型安全和更好的 IDE 支持
    """
    STOPPED = auto()    # 已停止
    STARTING = auto()   # 启动中
    RUNNING = auto()    # 运行中
    STOPPING = auto()   # 停止中
    ERROR = auto()      # 错误状态
    
    def __str__(self) -> str:
        """返回状态的中文描述"""
        descriptions = {
            ServiceState.STOPPED: "已停止",
            ServiceState.STARTING: "启动中",
            ServiceState.RUNNING: "运行中",
            ServiceState.STOPPING: "停止中",
            ServiceState.ERROR: "错误"
        }
        return descriptions.get(self, "未知")
    
    @classmethod
    def from_string(cls, status_str: str) -> "ServiceState":
        """从字符串转换为枚举值
        
        Args:
            status_str: 状态字符串
            
        Returns:
            ServiceState: 对应的枚举值
        """
        mapping = {
            "已停止": cls.STOPPED,
            "启动中": cls.STARTING,
            "运行中": cls.RUNNING,
            "停止中": cls.STOPPING,
            "错误": cls.ERROR,
            # 兼容旧代码的英文状态
            "STOPPED": cls.STOPPED,
            "STARTING": cls.STARTING,
            "RUNNING": cls.RUNNING,
            "STOPPING": cls.STOPPING,
            "ERROR": cls.ERROR,
        }
        return mapping.get(status_str, cls.STOPPED)


class PublicAccessState(Enum):
    """公网访问状态枚举"""
    STOPPED = auto()    # 已停止
    STARTING = auto()   # 启动中
    RUNNING = auto()    # 运行中
    STOPPING = auto()   # 停止中
    ERROR = auto()      # 错误状态
    
    def __str__(self) -> str:
        """返回状态的中文描述"""
        descriptions = {
            PublicAccessState.STOPPED: "已停止",
            PublicAccessState.STARTING: "启动中",
            PublicAccessState.RUNNING: "运行中",
            PublicAccessState.STOPPING: "停止中",
            PublicAccessState.ERROR: "错误"
        }
        return descriptions.get(self, "未知")
    
    @classmethod
    def from_string(cls, status_str: str) -> "PublicAccessState":
        """从字符串转换为枚举值"""
        mapping = {
            "stopped": cls.STOPPED,
            "starting": cls.STARTING,
            "running": cls.RUNNING,
            "stopping": cls.STOPPING,
            "error": cls.ERROR,
        }
        return mapping.get(status_str.lower(), cls.STOPPED)


class ServiceStateMachine:
    """服务状态机 - 管理状态转换规则
    
    使用 Enum 实现类型安全的状态管理
    """
    
    def __init__(self):
        """初始化状态机"""
        # 定义服务状态转换规则
        self._transitions: Dict[ServiceState, Set[ServiceState]] = {
            ServiceState.STOPPED: {ServiceState.STARTING},
            ServiceState.STARTING: {ServiceState.RUNNING, ServiceState.STOPPED, ServiceState.ERROR},
            ServiceState.RUNNING: {ServiceState.STOPPING, ServiceState.ERROR},
            ServiceState.STOPPING: {ServiceState.STOPPED, ServiceState.ERROR},
            ServiceState.ERROR: {ServiceState.STOPPED, ServiceState.STARTING}
        }
        
        # 定义公网访问状态转换规则
        self._public_transitions: Dict[PublicAccessState, Set[PublicAccessState]] = {
            PublicAccessState.STOPPED: {PublicAccessState.STARTING},
            PublicAccessState.STARTING: {PublicAccessState.RUNNING, PublicAccessState.STOPPING, PublicAccessState.STOPPED},
            PublicAccessState.RUNNING: {PublicAccessState.STOPPING, PublicAccessState.STOPPED},
            PublicAccessState.STOPPING: {PublicAccessState.STOPPED},
            PublicAccessState.ERROR: {PublicAccessState.STOPPED, PublicAccessState.STARTING}
        }
    
    def can_transition(self, current: ServiceState, new: ServiceState) -> bool:
        """检查状态转换是否合法
        
        Args:
            current: 当前状态
            new: 新状态
            
        Returns:
            bool: 转换是否合法
        """
        if not isinstance(current, ServiceState) or not isinstance(new, ServiceState):
            return False
        
        # 状态相同，无需转换
        if current == new:
            return True
        
        # 检查当前状态是否在转换规则中
        if current not in self._transitions:
            return False
        
        # 检查新状态是否在允许的转换列表中
        return new in self._transitions[current]
    
    def can_transition_public(self, current: PublicAccessState, new: PublicAccessState) -> bool:
        """检查公网访问状态转换是否合法
        
        Args:
            current: 当前状态
            new: 新状态
            
        Returns:
            bool: 转换是否合法
        """
        if not isinstance(current, PublicAccessState) or not isinstance(new, PublicAccessState):
            return False
        
        if current == new:
            return True
        
        if current not in self._public_transitions:
            return False
        
        return new in self._public_transitions[current]
    
    def get_valid_transitions(self, state: ServiceState) -> Set[ServiceState]:
        """获取从当前状态可以转换到的所有状态
        
        Args:
            state: 当前状态
            
        Returns:
            Set[ServiceState]: 可转换的状态集合
        """
        return self._transitions.get(state, set()).copy()
    
    def validate_combined_state(self, service_state: ServiceState, 
                               public_state: PublicAccessState) -> bool:
        """验证服务状态和公网访问状态的组合是否合法
        
        Args:
            service_state: 服务状态
            public_state: 公网访问状态
            
        Returns:
            bool: 状态组合是否合法
        """
        # 服务未运行时，公网访问不能运行
        if service_state == ServiceState.STOPPED and \
           public_state in [PublicAccessState.RUNNING, PublicAccessState.STARTING]:
            return False
        
        return True


# 向后兼容：保留旧的字符串常量
class ServiceStatus:
    """向后兼容的字符串状态常量"""
    STOPPED = "已停止"
    RUNNING = "运行中"
    STARTING = "启动中"
    ERROR = "错误"
