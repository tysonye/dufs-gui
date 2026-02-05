"""服务状态模块 - 使用 Enum 实现现代化的状态管理（合并版）"""

import time
from enum import Enum, auto
from typing import Dict, Set, Optional, Callable


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
    """服务状态机 - 管理状态转换规则（加强版，添加硬校验和日志）

    稳定模块：不要在未理解全局影响前修改
    """

    def __init__(self, logger: Optional[Callable] = None):
        """初始化状态机

        Args:
            logger: 可选的日志回调函数
        """
        self._logger = logger

        # 定义服务状态转换规则
        self.service_transitions = {
            ServiceStatus.STOPPED: [ServiceStatus.STARTING],
            ServiceStatus.STARTING: [ServiceStatus.RUNNING, ServiceStatus.STOPPED, ServiceStatus.ERROR],
            ServiceStatus.RUNNING: [ServiceStatus.STOPPED, ServiceStatus.ERROR],
            ServiceStatus.ERROR: [ServiceStatus.STOPPED, ServiceStatus.STARTING]
        }

        # 定义公网访问状态转换规则
        self.public_transitions = {
            "stopped": ["starting"],
            "starting": ["running", "stopping", "stopped"],
            "running": ["stopping", "stopped"],
            "stopping": ["stopped"]
        }

        # 状态转换历史（用于调试和审计）
        self._transition_history = []
        self._max_history = 100

    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self._logger:
            try:
                self._logger(message, level)
            except Exception:
                pass
        # 同时打印到控制台
        print(f"[{level}] {message}")

    def can_transition(self, current_status: str, new_status: str, public_access: bool = False) -> bool:
        """检查状态转换是否合法（加强版，带日志和审计）

        Args:
            current_status (str): 当前状态
            new_status (str): 新状态
            public_access (bool): 是否为公网访问状态

        Returns:
            bool: 状态转换是否合法
        """
        try:
            # 确保参数有效
            if not current_status or not new_status:
                self._log("状态转换检查失败：状态参数为空", "WARNING")
                return False

            # 状态相同，无需转换
            if current_status == new_status:
                return True

            # 检查状态转换规则
            if public_access:
                transitions = self.public_transitions
                status_type = "公网访问"
            else:
                transitions = self.service_transitions
                status_type = "服务"

            # 检查当前状态是否在转换规则中
            if current_status not in transitions:
                self._log(f"非法{status_type}状态: {current_status}", "ERROR")
                return False

            # 检查新状态是否在允许的转换列表中
            allowed = transitions[current_status]
            if new_status not in allowed:
                self._log(f"非法状态转换: {current_status} -> {new_status} (允许: {allowed})", "WARNING")
                return False

            return True
        except Exception as e:
            # 捕获所有异常，确保方法不会崩溃
            self._log(f"状态转换检查异常: {str(e)}", "ERROR")
            return False

    def validate_and_transition(self, current_status: str, new_status: str,
                                public_access: bool = False) -> tuple[bool, str]:
        """验证并执行状态转换（返回详细结果）

        Args:
            current_status (str): 当前状态
            new_status (str): 新状态
            public_access (bool): 是否为公网访问状态

        Returns:
            tuple[bool, str]: (是否成功, 详细信息)
        """
        if not self.can_transition(current_status, new_status, public_access):
            status_type = "公网访问" if public_access else "服务"
            msg = f"{status_type}状态转换被拒绝: {current_status} -> {new_status}"
            self._log(msg, "WARNING")
            return False, msg

        # 记录转换历史
        self._record_transition(current_status, new_status, public_access)

        status_type = "公网访问" if public_access else "服务"
        msg = f"{status_type}状态转换成功: {current_status} -> {new_status}"
        self._log(msg, "INFO")
        return True, msg

    def _record_transition(self, from_status: str, to_status: str, public_access: bool):
        """记录状态转换历史"""
        self._transition_history.append({
            'timestamp': time.time(),
            'from': from_status,
            'to': to_status,
            'type': 'public' if public_access else 'service'
        })

        # 限制历史记录大小
        if len(self._transition_history) > self._max_history:
            self._transition_history = self._transition_history[-self._max_history:]

    def get_transition_history(self) -> list:
        """获取状态转换历史"""
        return self._transition_history.copy()

    def validate_combined_state(self, service_status: str, public_status: str) -> tuple[bool, str]:
        """验证服务状态和公网访问状态的组合是否合法（加强版）

        Args:
            service_status (str): 服务状态
            public_status (str): 公网访问状态

        Returns:
            tuple[bool, str]: (是否合法, 详细信息)
        """
        try:
            # 确保参数有效
            if not service_status or not public_status:
                return False, "状态参数为空"

            # 服务未运行时，公网访问不能运行
            if service_status == ServiceStatus.STOPPED and public_status in ["running", "starting"]:
                msg = f"非法状态组合: 服务已停止但公网访问状态为 {public_status}"
                self._log(msg, "ERROR")
                return False, msg

            # 服务启动中或运行中时，公网访问状态可以是任意合法状态
            return True, "状态组合合法"
        except Exception as e:
            # 捕获所有异常，确保方法不会崩溃
            msg = f"状态组合验证异常: {str(e)}"
            self._log(msg, "ERROR")
            return False, msg

    def get_valid_transitions(self, current_status: str, public_access: bool = False) -> list:
        """获取从当前状态可以转换到的所有状态

        Args:
            current_status (str): 当前状态
            public_access (bool): 是否为公网访问状态

        Returns:
            list: 可转换的状态列表
        """
        if public_access:
            transitions = self.public_transitions
        else:
            transitions = self.service_transitions

        return transitions.get(current_status, []).copy()


# 向后兼容：保留旧的字符串常量
class ServiceStatus:
    """向后兼容的字符串状态常量"""
    STOPPED = "已停止"
    RUNNING = "运行中"
    STARTING = "启动中"
    ERROR = "错误"
