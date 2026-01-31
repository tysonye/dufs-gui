"""服务管理器文件"""
# pyright: reportAny=false
# pyright: reportUnannotatedClassAttribute=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false

import socket
import threading
from service import DufsService, ServiceStatus
from constants import AppConstants


class ServiceManager:
    """服务管理器，负责管理所有Dufs服务"""
    
    def __init__(self) -> None:
        """初始化服务管理器"""
        self.services: list[DufsService] = []  # 服务列表
        self._allocated_ports: set[int] = set()  # 已分配的端口集合
        self._port_lock: threading.Lock = threading.Lock()  # 端口分配锁
    
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
                    self.release_allocated_port(port)
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
            # 释放旧端口
            try:
                old_port = int(self.services[index].port)
                self.release_allocated_port(old_port)
            except (ValueError, AttributeError):
                pass
            # 更新服务
            self.services[index] = new_service
    
    def find_available_port(self, preferred_port: int) -> int:
        """智能查找可用端口
        
        Args:
            preferred_port (int): 首选端口
            
        Returns:
            int: 可用的端口号
        """
        with self._port_lock:
            # 1. 检查端口范围有效性
            preferred_port = max(1024, min(65535, preferred_port))
            
            # 2. 尝试首选端口
            if self._is_port_available(preferred_port):
                self._allocated_ports.add(preferred_port)
                return preferred_port
            
            # 3. 在首选端口附近搜索（上下双向搜索）
            search_range = min(100, AppConstants.PORT_TRY_LIMIT)
            for offset in range(1, search_range + 1):
                for direction in [1, -1]:  # 先向上，再向下
                    port = preferred_port + (offset * direction)
                    if 1024 <= port <= 65535:
                        if self._is_port_available(port):
                            self._allocated_ports.add(port)
                            return port
            
            # 4. 从备用端口范围查找
            for port in range(self._get_backup_start_port(), self._get_backup_start_port() + self._get_backup_port_range()):
                if self._is_port_available(port):
                    self._allocated_ports.add(port)
                    return port
            
            raise ValueError("无法找到可用端口")
    
    def _get_port_range(self) -> int:
        """获取端口搜索范围"""
        return AppConstants.PORT_TRY_LIMIT_BACKUP

    def _get_backup_start_port(self) -> int:
        """获取备用端口起始位置"""
        return AppConstants.BACKUP_START_PORT

    def _get_backup_port_range(self) -> int:
        """获取备用端口范围"""
        return AppConstants.PORT_TRY_LIMIT
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用

        Args:
            port (int): 端口号

        Returns:
            bool: 端口是否可用
        """
        # 检查是否已在已分配端口中
        if port in self._allocated_ports:
            return False

        # 检查是否为浏览器黑名单端口
        if port in AppConstants.BROWSER_BLOCKED_PORTS:
            return False

        # 检查是否为系统保留端口
        if port in AppConstants.SYSTEM_RESERVED_PORTS:
            return False

        # 检查端口是否被其他进程占用（更全面的检查）
        hosts = ["127.0.0.1", "0.0.0.0"]
        for host in hosts:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.settimeout(0.5)  # 增加超时时间
                    s.bind((host, port))
            except (OSError, socket.timeout):
                return False
        
        return True
    
    def release_allocated_port(self, port: int) -> None:
        """释放已分配的端口
        
        Args:
            port (int): 端口号
        """
        with self._port_lock:
            if port in self._allocated_ports:
                self._allocated_ports.remove(port)
    
    def allocate_port(self, port: int) -> None:
        """分配端口到已分配集合
        
        Args:
            port (int): 端口号
        """
        with self._port_lock:
            self._allocated_ports.add(port)
    
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
                except Exception:
                    pass
    
    def cleanup_resources(self) -> None:
        """清理资源"""
        self.stop_all_services()
        # 清空服务列表
        self.services.clear()
        # 清空已分配端口
        self._allocated_ports.clear()
