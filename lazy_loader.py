"""延迟加载模块 - 实现模块的按需加载，优化启动性能"""

import importlib
from typing import Any, Optional


class LazyLoader:
    """延迟加载器 - 按需导入模块，减少启动时间
    
    使用示例:
        # 延迟导入 tray_manager
        tray_manager_loader = LazyLoader('tray_manager')
        
        # 第一次使用时才真正导入
        tray_manager = tray_manager_loader.get()
        tray_manager.TrayManager(...)
    """
    
    def __init__(self, module_name: str, attr_name: Optional[str] = None):
        """
        初始化延迟加载器
        
        Args:
            module_name: 模块名称（如 'tray_manager'）
            attr_name: 可选，模块中的属性名称（如 'TrayManager'）
        """
        self.module_name = module_name
        self.attr_name = attr_name
        self._module: Optional[Any] = None
        self._attr: Optional[Any] = None
    
    def get(self) -> Any:
        """获取模块或属性
        
        Returns:
            Any: 模块或模块中的属性
        """
        if self._module is None:
            self._module = importlib.import_module(self.module_name)
            
        if self.attr_name is not None and self._attr is None:
            self._attr = getattr(self._module, self.attr_name)
            return self._attr
            
        return self._module
    
    def is_loaded(self) -> bool:
        """检查模块是否已加载
        
        Returns:
            bool: 是否已加载
        """
        return self._module is not None
    
    def reload(self) -> Any:
        """重新加载模块
        
        Returns:
            Any: 重新加载后的模块
        """
        if self._module is not None:
            self._module = importlib.reload(self._module)
            if self.attr_name is not None:
                self._attr = getattr(self._module, self.attr_name)
                return self._attr
        return self.get()


class LazyImport:
    """延迟导入装饰器/上下文管理器
    
    使用示例:
        # 作为装饰器
        @LazyImport('cloudflared_downloader')
        def check_cloudflared(downloader):
            return downloader.check_and_download()
        
        # 作为上下文管理器
        with LazyImport('tray_manager') as tm:
            tray = tm.TrayManager(window)
    """
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self._module: Optional[Any] = None
    
    def __enter__(self) -> Any:
        self._module = importlib.import_module(self.module_name)
        return self._module
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def __call__(self, func):
        """作为装饰器使用"""
        def wrapper(*args, **kwargs):
            module = importlib.import_module(self.module_name)
            return func(module, *args, **kwargs)
        return wrapper


# 预定义的延迟加载器实例
# 这些模块在启动时不需要立即加载

# 托盘管理器延迟加载器
tray_manager_loader = LazyLoader('tray_manager', 'TrayManager')

# Cloudflare隧道延迟加载器（包含下载功能）
cloudflare_tunnel_loader = LazyLoader('cloudflare_tunnel')

# 启动管理器延迟加载器
startup_manager_loader = LazyLoader('startup_manager')

# 服务信息对话框延迟加载器
service_info_dialog_loader = LazyLoader('service_info_dialog', 'ServiceInfoDialog')
