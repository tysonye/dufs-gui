"""服务模块 - 协调者模式，组合状态机、Cloudflare隧道和基础服务"""

# 为了向后兼容，从子模块导入所有公共接口
from service_state import ServiceStatus, ServiceStateMachine
from cloudflare_tunnel import CloudflareTunnel
from base_service import BaseService

# DufsService 别名，保持向后兼容
DufsService = BaseService

# 导出所有公共接口
__all__ = [
    'ServiceStatus',
    'ServiceStateMachine',
    'CloudflareTunnel',
    'BaseService',
    'DufsService',
]
