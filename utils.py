"""工具函数文件"""
# pyright: reportAny=false

import socket


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
    except Exception:
        pass
    
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
    except ImportError:
        pass
    
    # 方法3：尝试解析主机名
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass
    
    # 最后手段：返回127.0.0.1
    return "127.0.0.1"
