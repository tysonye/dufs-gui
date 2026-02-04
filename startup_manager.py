"""开机自启管理模块"""

import os
import sys
import winreg


class StartupManager:
    """开机自启管理器"""
    
    APP_NAME = "DufsGUI"
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    @staticmethod
    def _get_exe_path():
        """获取当前可执行文件路径"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            return os.path.abspath(sys.argv[0])
    
    @classmethod
    def enable_startup(cls):
        """启用开机自启"""
        exe_path = cls._get_exe_path()
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_PATH, 0, winreg.KEY_WRITE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_PATH)
        
        winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
    
    @classmethod
    def disable_startup(cls):
        """禁用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_PATH, 0, winreg.KEY_WRITE)
            try:
                winreg.DeleteValue(key, cls.APP_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
    
    @classmethod
    def is_startup_enabled(cls):
        """检查是否已设置开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_PATH, 0, winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, cls.APP_NAME)
                winreg.CloseKey(key)
                return value.strip('"') == cls._get_exe_path()
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except FileNotFoundError:
            return False
