"""端口服务模块 - 负责端口分配和管理"""
# pyright: reportAny=false

import socket
import threading
from typing import Optional
from constants import AppConstants


class PortService:
    """端口服务 - 负责端口分配、冲突检测和释放"""

    def __init__(self) -> None:
        """初始化端口服务"""
        self._allocated_ports: set[int] = set()
        self._lock: threading.Lock = threading.Lock()

    def allocate_port(self, preferred_port: int, exclude_ports: Optional[set[int]] = None) -> int:
        """分配可用端口

        Args:
            preferred_port: 首选端口
            exclude_ports: 需要排除的端口集合

        Returns:
            int: 分配的端口号

        Raises:
            ValueError: 无法找到可用端口
        """
        with self._lock:
            exclude = exclude_ports or set()

            # 检查首选端口
            if preferred_port not in exclude and self._is_port_valid(preferred_port):
                self._allocated_ports.add(preferred_port)
                return preferred_port

            # 在首选端口附近查找
            port_config = AppConstants.PORT_CONFIG
            for port in range(preferred_port + 1, preferred_port + port_config['search_range']):
                if port not in exclude and self._is_port_valid(port):
                    self._allocated_ports.add(port)
                    return port

            # 从备用端口范围查找
            for port in range(port_config['backup_start'], port_config['backup_start'] + port_config['backup_range']):
                if port not in exclude and self._is_port_valid(port):
                    self._allocated_ports.add(port)
                    return port

            raise ValueError("无法找到可用端口")

    def release_port(self, port: int) -> None:
        """释放端口

        Args:
            port: 端口号
        """
        with self._lock:
            self._allocated_ports.discard(port)

    def is_port_available(self, port: int) -> bool:
        """检查端口是否可用（外部接口）

        Args:
            port: 端口号

        Returns:
            bool: 端口是否可用
        """
        with self._lock:
            return self._is_port_valid(port)

    def _is_port_valid(self, port: int) -> bool:
        """检查端口是否有效（内部方法）

        Args:
            port: 端口号

        Returns:
            bool: 端口是否有效
        """
        port_config = AppConstants.PORT_CONFIG

        # 检查端口范围
        if not (port_config['min_port'] <= port <= port_config['max_port']):
            return False

        # 检查是否已分配
        if port in self._allocated_ports:
            return False

        # 检查浏览器黑名单端口
        if port in AppConstants.BROWSER_BLOCKED_PORTS:
            return False

        # 检查系统保留端口
        if port <= port_config['system_reserved_max']:
            return False

        # 检查端口是否被占用
        return self._check_port_binding(port)

    def _check_port_binding(self, port: int) -> bool:
        """检查端口是否可以绑定

        Args:
            port: 端口号

        Returns:
            bool: 端口是否可以绑定
        """
        check_hosts = ["127.0.0.1", "0.0.0.0"]

        # 尝试获取本地IP
        try:
            from utils import get_local_ip
            local_ip = get_local_ip()
            if local_ip != "127.0.0.1" and local_ip not in check_hosts:
                check_hosts.append(local_ip)
        except (ImportError, OSError):
            pass

        timeout = AppConstants.TIMEOUTS['port_check']

        for host in check_hosts:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    s.bind((host, port))
            except OSError as e:
                import errno
                if e.errno in (errno.EADDRINUSE, errno.EACCES):
                    return False

        return True

    def find_alternative_port(self, conflict_port: int, exclude_ports: Optional[set[int]] = None) -> int:
        """查找替代端口（当指定端口冲突时）

        Args:
            conflict_port: 冲突的端口号
            exclude_ports: 需要排除的端口集合

        Returns:
            int: 替代端口号
        """
        return self.allocate_port(conflict_port + 1, exclude_ports)

    def get_allocated_ports(self) -> set[int]:
        """获取已分配的端口集合

        Returns:
            set[int]: 已分配的端口集合
        """
        with self._lock:
            return self._allocated_ports.copy()

    def clear_all_ports(self) -> None:
        """清空所有已分配的端口"""
        with self._lock:
            self._allocated_ports.clear()

    def validate_port_range(self, port: int) -> tuple[bool, str]:
        """验证端口范围

        Args:
            port: 端口号

        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        port_config = AppConstants.PORT_CONFIG

        if not isinstance(port, int):
            return False, "端口号必须是整数"

        if port < port_config['min_port']:
            return False, f"端口号不能小于 {port_config['min_port']}"

        if port > port_config['max_port']:
            return False, f"端口号不能大于 {port_config['max_port']}"

        if port <= port_config['system_reserved_max']:
            return False, f"端口 {port} 是系统保留端口，需要管理员权限"

        if port in AppConstants.BROWSER_BLOCKED_PORTS:
            return False, f"端口 {port} 被浏览器阻止，无法使用"

        return True, ""
