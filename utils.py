"""工具函数文件"""
# pyright: reportAny=false

import socket
import errno
import logging

# 配置日志
logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """获取本地IP地址
    
    Returns:
        str: 本地IP地址
    """
    try:
        # 方法1：尝试连接外部服务器
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1.0)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and ip != "127.0.0.1":
                return ip
    except (socket.error, OSError) as e:
        logger.debug(f"方法1获取IP失败: {str(e)}")

    try:
        # 方法2：获取所有网络接口
        import netifaces
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            # 跳过回环接口和虚拟接口
            if interface.startswith(('lo', 'docker', 'veth', 'br', 'vmnet', 'ppp')):
                continue
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    # 排除回环地址和链路本地地址
                    if ip != '127.0.0.1' and not ip.startswith('169.254'):
                        return ip
    except ImportError as e:
        logger.debug(f"netifaces模块未安装: {str(e)}")

    # 方法3：尝试解析主机名
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != "127.0.0.1":
            return ip
    except (socket.error, OSError) as e:
        logger.debug(f"方法3获取IP失败: {str(e)}")

    # 最后手段：返回127.0.0.1
    logger.warning("所有方法获取IP均失败，返回127.0.0.1")
    return "127.0.0.1"


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """检查端口是否可用（启动前检测）

    Args:
        port: 端口号
        host: 绑定地址

    Returns:
        bool: 端口是否可用
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(1.0)
            result = s.bind((host, port))
            return True
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            return False
        # 其他错误（如权限不足）也视为不可用
        return False
    except (OSError, ValueError):
        return False


def check_port_conflict(port: int, host: str = "0.0.0.0") -> tuple[bool, str]:
    """检查端口冲突并返回详细信息

    Args:
        port: 端口号
        host: 绑定地址

    Returns:
        tuple[bool, str]: (是否可用, 详细信息)
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(1.0)
            s.bind((host, port))
            return True, f"端口 {port} 可用"
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            return False, f"端口 {port} 已被占用"
        elif e.errno == errno.EACCES:
            return False, f"端口 {port} 需要管理员权限"
        elif e.errno == errno.EADDRNOTAVAIL:
            return False, f"地址 {host} 不可用"
        else:
            return False, f"端口 {port} 检查失败: {str(e)}"
    except (OSError, ValueError) as e:
        return False, f"端口检查异常: {str(e)}"
