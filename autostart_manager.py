"""开机自启管理模块"""
import os
import sys
import winreg
from pathlib import Path


class AutoStartManager:
    """Windows开机自启管理器"""
    
    REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "DufsGUI"
    
    @classmethod
    def is_enabled(cls) -> bool:
        """检查开机自启是否已启用"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_KEY, 0, winreg.KEY_READ) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, cls.APP_NAME)
                    return value == cls._get_executable_path()
                except FileNotFoundError:
                    return False
        except Exception as e:
            print(f"检查开机自启状态失败: {str(e)}")
            return False
    
    @classmethod
    def enable(cls) -> bool:
        """启用开机自启"""
        try:
            exe_path = cls._get_executable_path()
            if not exe_path:
                print("无法获取可执行文件路径")
                return False
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_KEY, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, exe_path)
            print(f"已启用开机自启: {exe_path}")
            return True
        except Exception as e:
            print(f"启用开机自启失败: {str(e)}")
            return False
    
    @classmethod
    def disable(cls) -> bool:
        """禁用开机自启"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_KEY, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, cls.APP_NAME)
                    print("已禁用开机自启")
                    return True
                except FileNotFoundError:
                    # 键不存在，视为成功
                    return True
        except Exception as e:
            print(f"禁用开机自启失败: {str(e)}")
            return False
    
    @classmethod
    def _get_executable_path(cls) -> str | None:
        """获取当前可执行文件的完整路径"""
        try:
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe
                exe_path = sys.executable
            else:
                # 如果是Python脚本，返回None（不支持脚本开机自启）
                print("Python脚本模式不支持开机自启，请打包为exe后使用")
                return None
            
            # 确保路径存在
            if os.path.exists(exe_path):
                return exe_path
            return None
        except Exception as e:
            print(f"获取可执行文件路径失败: {str(e)}")
            return None
    
    @classmethod
    def toggle(cls, enable: bool) -> bool:
        """切换开机自启状态"""
        if enable:
            return cls.enable()
        else:
            return cls.disable()
