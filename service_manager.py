"""服务管理器文件"""
# pyright: reportAny=false
# pyright: reportUnannotatedClassAttribute=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false

from service import DufsService, ServiceStatus
from port_service import PortService


class ServiceManager:
    """服务管理器，负责管理所有Dufs服务"""

    def __init__(self) -> None:
        """初始化服务管理器"""
        self.services: list[DufsService] = []  # 服务列表
        self.port_service = PortService()  # 端口服务
    
    def add_service(self, service: DufsService) -> None:
        """添加服务
        
        Args:
            service (DufsService): 服务实例
        """
        self.services.append(service)
    
    def remove_service(self, index: int) -> None:
        """移除服务

        Args:
            index (int): 服务索引
        """
        if 0 <= index < len(self.services):
            # 释放端口
            if hasattr(self.services[index], 'port'):
                try:
                    port = int(self.services[index].port)
                    self.port_service.release_port(port)
                except (ValueError, AttributeError):
                    pass
            # 移除服务
            _ = self.services.pop(index)
    
    def edit_service(self, index: int, new_service: DufsService) -> None:
        """编辑服务
        
        Args:
            index (int): 服务索引
            new_service (DufsService): 新的服务实例
        """
        if 0 <= index < len(self.services):
            # 更新服务（注意：端口释放应该在调用此方法之前完成）
            self.services[index] = new_service
    
    def find_available_port(self, preferred_port: int) -> int:
        """查找可用端口（委托给 PortService）

        Args:
            preferred_port (int): 首选端口

        Returns:
            int: 可用的端口号
        """
        return self.port_service.allocate_port(preferred_port)

    def release_allocated_port(self, port: int) -> None:
        """释放已分配的端口（委托给 PortService）

        Args:
            port (int): 端口号
        """
        self.port_service.release_port(port)
    
    def get_service_by_name(self, name: str) -> DufsService | None:
        """通过名称获取服务
        
        Args:
            name (str): 服务名称
            
        Returns:
            DufsService: 服务实例
        """
        for service in self.services:
            if service.name == name:
                return service
        return None
    
    def get_running_services(self) -> list[DufsService]:
        """获取所有运行中的服务
        
        Returns:
            list: 运行中的服务列表
        """
        return [service for service in self.services if service.status == ServiceStatus.RUNNING]
    
    def stop_all_services(self, log_manager=None) -> None:
        """停止所有服务
        
        Args:
            log_manager: 日志管理器实例
        """
        for service in self.services:
            if service.status == ServiceStatus.RUNNING:
                try:
                    service.stop(log_manager)
                except (OSError, RuntimeError):
                    pass
    
    def cleanup_resources(self) -> None:
        """清理资源"""
        self.stop_all_services()
        # 清空服务列表
        self.services.clear()
        # 清空已分配端口
        self._allocated_ports.clear()
