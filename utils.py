"""工具函数文件"""
# pyright: reportAny=false

import socket
import subprocess
import time
import os
import importlib.util


def get_local_ip() -> str:
    """获取本地IP地址
    
    Returns:
        str: 本地IP地址
    """
    try:
        # 使用上下文管理器确保套接字正确关闭
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # 设置超时时间为1秒，避免网络操作阻塞
            s.settimeout(1.0)
            # 连接到一个外部服务器（不需要实际连接成功）
            s.connect(("8.8.8.8", 80))
            # 获取本地IP地址
            return s.getsockname()[0]
    except Exception:
        # 如果出错，返回默认本地地址
        return "127.0.0.1"


def kill_all_dufs_and_cloudflared(log_manager=None, service_name: str = "") -> bool:
    """智能清理所有 dufs 和 cloudflared 进程（Windows专用）
    
    Args:
        log_manager: 日志管理器实例
        service_name: 服务名称（用于日志）
        
    Returns:
        bool: 是否成功清理
    """
    prefix = f"[{service_name}] " if service_name else ""
    
    def log(msg, is_error=False):
        if log_manager:
            log_manager.append_log(msg, is_error, service_name or "系统")
        else:
            print(f"{prefix}{msg}")
    
    try:
        log("开始智能清理 dufs 和 cloudflared 进程")
        
        # 1. 优先使用psutil清理进程树
        if importlib.util.find_spec("psutil"):
            cleaned = _cleanup_with_psutil(log_manager, service_name)
        else:
            # 2. 降级到taskkill
            cleaned = _cleanup_with_taskkill(log_manager, service_name)
        
        # 3. 验证清理结果
        return _verify_process_cleanup(log_manager, service_name)
    
    except Exception as e:
        log(f"清理进程时出错: {str(e)}", True)
        return False


def _cleanup_with_psutil(log_manager, service_name):
    """使用psutil清理进程树"""
    import psutil
    
    prefix = f"[{service_name}] " if service_name else ""
    cleaned_any = False
    current_pid = os.getpid()
    
    def log(msg, is_error=False):
        if log_manager:
            log_manager.append_log(msg, is_error, service_name or "系统")
        else:
            print(f"{prefix}{msg}")
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            proc_info = proc.info
            proc_name = proc_info['name'].lower()
            pid = proc_info['pid']
            
            # 跳过自身
            if pid == current_pid:
                continue
            
            # 检查是否为目标进程
            if 'dufs.exe' in proc_name or 'cloudflared.exe' in proc_name:
                # 终止进程树
                parent = psutil.Process(pid)
                children = parent.children(recursive=True)
                
                # 先终止子进程
                for child in children:
                    try:
                        child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # 等待子进程结束
                gone, alive = psutil.wait_procs(children, timeout=3)
                
                # 强制终止未结束的进程
                for p in alive:
                    try:
                        p.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # 终止主进程
                try:
                    parent.terminate()
                    parent.wait(timeout=3)
                    log(f"已清理进程树 PID:{pid}, 子进程数:{len(children)}")
                    cleaned_any = True
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        parent.kill()
                        parent.wait(timeout=2)
                        log(f"强制清理进程 PID:{pid}")
                        cleaned_any = True
                    except Exception as e:
                        log(f"清理进程失败 PID:{pid}, 错误: {str(e)}", True)
        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            log(f"处理进程时出错: {str(e)}", True)
    
    return cleaned_any


def _cleanup_with_taskkill(log_manager, service_name):
    """使用taskkill清理进程"""
    prefix = f"[{service_name}] " if service_name else ""
    
    def log(msg, is_error=False):
        if log_manager:
            log_manager.append_log(msg, is_error, service_name or "系统")
        else:
            print(f"{prefix}{msg}")
    
    log("使用taskkill清理进程")
    
    # 多次尝试终止
    for i in range(3):
        try:
            subprocess.run(
                ["taskkill", "/IM", "dufs.exe", "/F", "/T"],
                capture_output=True,
                shell=True,
                timeout=5
            )
        except Exception:
            pass
        
        try:
            subprocess.run(
                ["taskkill", "/IM", "cloudflared.exe", "/F", "/T"],
                capture_output=True,
                shell=True,
                timeout=5
            )
        except Exception:
            pass
        
        time.sleep(0.3)
    
    return True


def _verify_process_cleanup(log_manager, service_name) -> bool:
    """验证进程是否已清理"""
    prefix = f"[{service_name}] " if service_name else ""
    all_cleaned = True
    
    def log(msg, is_error=False):
        if log_manager:
            log_manager.append_log(msg, is_error, service_name or "系统")
        else:
            print(f"{prefix}{msg}")
    
    time.sleep(0.5)
    
    # 检查 dufs.exe
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq dufs.exe"],
            capture_output=True,
            text=True,
            shell=True,
            timeout=5
        )
        if "dufs.exe" not in result.stdout.lower():
            log("dufs.exe 进程已清理完成")
        else:
            log("警告：dufs.exe 进程可能未完全清理", True)
            all_cleaned = False
    except Exception:
        pass
    
    # 检查 cloudflared.exe
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq cloudflared.exe"],
            capture_output=True,
            text=True,
            shell=True,
            timeout=5
        )
        if "cloudflared.exe" not in result.stdout.lower():
            log("cloudflared.exe 进程已清理完成")
        else:
            log("警告：cloudflared.exe 进程可能未完全清理", True)
            all_cleaned = False
    except Exception:
        pass
    
    return all_cleaned
