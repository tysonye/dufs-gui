"""工具函数文件"""
# pyright: reportAny=false

import socket


def get_local_ip() -> str:
    """获取本地IP地址
    
    Returns:
        str: 本地IP地址
    """
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 设置超时时间为1秒，避免网络操作阻塞
        s.settimeout(1.0)
        # 连接到一个外部服务器（不需要实际连接成功）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 如果出错，返回默认本地地址
        return "127.0.0.1"
