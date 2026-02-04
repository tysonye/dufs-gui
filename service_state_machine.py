"""服务状态机模块 - 负责状态管理和转换验证"""


class ServiceStatus:
    """服务状态枚举"""
    STOPPED = "已停止"
    RUNNING = "运行中"
    STARTING = "启动中"
    ERROR = "错误"


class ServiceStateMachine:
    """服务状态机，确保状态转换的合法性"""

    def __init__(self):
        """初始化状态机"""
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

    def can_transition(self, current_status: str, new_status: str, public_access: bool = False) -> bool:
        """检查状态转换是否合法

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
                return False

            # 状态相同，无需转换
            if current_status == new_status:
                return True

            # 检查状态转换规则
            if public_access:
                transitions = self.public_transitions
            else:
                transitions = self.service_transitions

            # 检查当前状态是否在转换规则中
            if current_status not in transitions:
                return False

            # 检查新状态是否在允许的转换列表中
            return new_status in transitions[current_status]
        except Exception:
            # 捕获所有异常，确保方法不会崩溃
            return False

    def validate_combined_state(self, service_status: str, public_status: str) -> bool:
        """验证服务状态和公网访问状态的组合是否合法

        Args:
            service_status (str): 服务状态
            public_status (str): 公网访问状态

        Returns:
            bool: 状态组合是否合法
        """
        try:
            # 确保参数有效
            if not service_status or not public_status:
                return False

            # 服务未运行时，公网访问不能运行
            if service_status == ServiceStatus.STOPPED and public_status in ["running", "starting"]:
                return False

            # 服务启动中或运行中时，公网访问状态可以是任意合法状态
            return True
        except Exception:
            # 捕获所有异常，确保方法不会崩溃
            return False
