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
            # 更新服务（注意：端口释放应该在调用此方法之前完成）
            self.services[index] = new_service
    
    def find_available_port(self, preferred_port: int) -> int:
        """查找可用端口
        
        Args:
            preferred_port (int): 首选端口
            
        Returns:
            int: 可用的端口号
        """
        with self._port_lock:
            # 检查首选端口是否可用
            if self._is_port_available(preferred_port):
                self._allocated_ports.add(preferred_port)
                return preferred_port
            
            # 优先在首选端口附近查找
            for port in range(preferred_port + 1, preferred_port + self._get_port_range()):
                if self._is_port_available(port):
                    self._allocated_ports.add(port)
                    return port
            
            # 从备用端口范围查找
            for port in range(self._get_backup_start_port(), self._get_backup_start_port() + self._get_backup_port_range()):
                if self._is_port_available(port):
                    self._allocated_ports.add(port)
                    return port
            
            raise ValueError("无法找到可用端口")
    
    def _get_port_range(self) -> int:
        """获取端口搜索范围"""
        return 50  # 从常量中获取，增加灵活性
    
    def _get_backup_start_port(self) -> int:
        """获取备用端口起始位置"""
        return 8000  # 从常量中获取
    
    def _get_backup_port_range(self) -> int:
        """获取备用端口范围"""
        return 100  # 从常量中获取
    
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

        # 检查端口是否被其他进程占用（检查多个关键地址）
        check_hosts = ["127.0.0.1", "0.0.0.0"]
        try:
            from utils import get_local_ip
            local_ip = get_local_ip()
            if local_ip != "127.0.0.1":
                check_hosts.append(local_ip)
        except Exception:
            pass
        
        for host in check_hosts:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.settimeout(0.5)
                    s.bind((host, port))
            except OSError as e:
                import errno
                if e.errno in (errno.EADDRINUSE, errno.EACCES):
                    return False
                # 其他错误继续检查
        
        return True
    
    def release_allocated_port(self, port: int) -> None:
        """释放已分配的端口
        
        Args:
            port (int): 端口号
        """
        with self._port_lock:
            if port in self._allocated_ports:
                self._allocated_ports.remove(port)
    
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
