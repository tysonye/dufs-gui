"""服务状态模块 - 状态常量定义"""


class ServiceStatus:
    """服务状态常量"""
    STOPPED = "未运行"
    RUNNING = "内网"
    STARTING = "启动中"
    ERROR = "错误"
    PUBLIC = "公网"
