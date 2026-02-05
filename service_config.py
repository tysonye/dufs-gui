"""服务配置模块 - 解耦配置数据和运行态"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ServiceConfig:
    """服务配置数据类 - 纯配置，不包含运行时状态"""
    
    # 基本配置
    name: str = "默认服务"
    serve_path: str = "."
    port: str = "5000"
    bind: str = ""
    
    # 权限配置
    allow_all: bool = False
    allow_upload: bool = False
    allow_delete: bool = False
    allow_search: bool = False
    allow_symlink: bool = False
    allow_archive: bool = False
    
    # 多用户权限规则
    auth_rules: List[dict] = field(default_factory=list)
    
    # 认证配置
    auth_user: str = ""
    auth_pass: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            'name': self.name,
            'serve_path': self.serve_path,
            'port': self.port,
            'bind': self.bind,
            'allow_all': self.allow_all,
            'allow_upload': self.allow_upload,
            'allow_delete': self.allow_delete,
            'allow_search': self.allow_search,
            'allow_symlink': self.allow_symlink,
            'allow_archive': self.allow_archive,
            'auth_rules': self.auth_rules,
            'auth_user': self.auth_user,
            'auth_pass': self.auth_pass,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ServiceConfig':
        """从字典创建配置"""
        return cls(
            name=data.get('name', '默认服务'),
            serve_path=data.get('serve_path', '.'),
            port=data.get('port', '5000'),
            bind=data.get('bind', ''),
            allow_all=data.get('allow_all', False),
            allow_upload=data.get('allow_upload', False),
            allow_delete=data.get('allow_delete', False),
            allow_search=data.get('allow_search', False),
            allow_symlink=data.get('allow_symlink', False),
            allow_archive=data.get('allow_archive', False),
            auth_rules=data.get('auth_rules', []),
            auth_user=data.get('auth_user', ''),
            auth_pass=data.get('auth_pass', ''),
        )
    
    def copy(self) -> 'ServiceConfig':
        """创建配置副本"""
        return ServiceConfig.from_dict(self.to_dict())


@dataclass
class ServiceRuntime:
    """服务运行时数据类 - 纯运行时状态，不包含配置"""
    
    # 进程信息
    process: Optional[object] = None
    status: str = "已停止"
    
    # 访问地址
    local_addr: str = ""
    
    # 公网访问状态
    public_access_status: str = "stopped"
    public_url: str = ""
    cloudflared_process: Optional[object] = None
    cloudflared_monitor_terminate: bool = False
    
    # 停止标志
    is_stopping: bool = False
    
    def reset(self):
        """重置运行时状态"""
        self.process = None
        self.status = "已停止"
        self.local_addr = ""
        self.public_access_status = "stopped"
        self.public_url = ""
        self.cloudflared_process = None
        self.cloudflared_monitor_terminate = False
        self.is_stopping = False
