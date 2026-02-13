"""配置控制器 - 负责配置的加载、保存和自动恢复"""

import time
from typing import Callable, Optional
from PyQt5.QtCore import QTimer

from config_manager import ConfigManager
from service import DufsService, ServiceStatus
from service_manager import ServiceManager
from log_manager import LogManager


class ConfigController:
    """配置控制器 - 负责配置管理和自动恢复"""

    def __init__(self, manager: ServiceManager, status_callback: Optional[Callable] = None, log_manager: Optional[LogManager] = None):
        """
        初始化配置控制器

        Args:
            manager: 服务管理器实例
            status_callback: 状态更新回调函数
            log_manager: 日志管理器实例
        """
        self.manager = manager
        self.config_manager = ConfigManager()
        self.status_callback = status_callback
        self.log_manager = log_manager

    def load_config(self) -> bool:
        """加载配置（增强版，带错误恢复）

        Returns:
            bool: 加载是否成功
        """
        try:
            services_config = self.config_manager.get_services()
            app_state = self.config_manager.get_app_state()

            # 验证配置数据类型
            if not isinstance(services_config, list):
                print(f"[配置加载] 服务配置格式错误，期望列表类型，实际为 {type(services_config)}")
                services_config = []

            if not isinstance(app_state, dict):
                print(f"[配置加载] 应用状态格式错误，期望字典类型，实际为 {type(app_state)}")
                app_state = {}

            # 检查上次是否正常退出
            normal_exit = app_state.get('normal_exit', True)
            last_exit_time = app_state.get('last_exit_time', 0)

            # 如果上次不是正常退出，或者距离上次退出超过5分钟，认为是异常退出
            time_since_last_exit = time.time() - last_exit_time
            should_auto_start = not normal_exit or time_since_last_exit > 300

            if should_auto_start:
                print(f"[自动恢复] 检测到异常退出，准备恢复服务。normal_exit={normal_exit}, time_since_last_exit={time_since_last_exit:.0f}秒")

            for service_config in services_config:
                # 验证服务配置类型
                if not isinstance(service_config, dict):
                    print(f"[配置加载] 跳过无效的服务配置项: {service_config}")
                    continue

                try:
                    service = DufsService(
                        name=str(service_config.get('name', '默认服务')),
                        serve_path=str(service_config.get('serve_path', '.')),
                        port=str(service_config.get('port', '5000')),
                        bind=str(service_config.get('bind', ''))
                    )
                    service.allow_upload = service_config.get('allow_upload', False)
                    service.allow_delete = service_config.get('allow_delete', False)
                    service.allow_search = service_config.get('allow_search', False)
                    service.allow_archive = service_config.get('allow_archive', False)
                    service.allow_all = service_config.get('allow_all', False)
                    service.auth_user = service_config.get('auth_user', '')
                    service.auth_pass = service_config.get('auth_pass', '')
                except Exception as e:
                    print(f"[配置加载] 创建服务失败: {str(e)}")
                    continue

                # 连接服务状态更新信号
                if self.status_callback:
                    service.status_updated.connect(self.status_callback)

                # 检查并自动更换重复的服务名称
                unique_name = self._generate_unique_service_name(service.name)
                service.name = unique_name

                # 检查并自动更换重复的端口
                try:
                    current_port = int(service.port)
                    conflict = any(
                        int(existing_service.port) == current_port
                        for existing_service in self.manager.services
                    )
                    if conflict:
                        new_port = self.manager.find_available_port(current_port)
                        service.port = str(new_port)
                    else:
                        # 通过 port_service 分配端口
                        self.manager.port_service.allocate_port(current_port)
                except ValueError:
                    port = self.manager.find_available_port(5001)
                    service.port = str(port)

                self.manager.add_service(service)

                # 自动恢复服务运行状态
                if should_auto_start:
                    auto_start = service_config.get('auto_start', False)
                    public_auto_start = service_config.get('public_auto_start', False)
                    if auto_start:
                        QTimer.singleShot(1000, lambda s=service, p=public_auto_start: self._auto_start_service(s, p))

            return True
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
            return False

    def save_config(self, normal_exit: bool = False) -> bool:
        """保存配置

        Args:
            normal_exit: 是否为正常退出

        Returns:
            bool: 保存是否成功
        """
        try:
            services_config = []
            for service in self.manager.services:
                service_config = {
                    'name': service.name,
                    'serve_path': service.serve_path,
                    'port': service.port,
                    'bind': service.bind,
                    'allow_upload': service.allow_upload,
                    'allow_delete': service.allow_delete,
                    'allow_search': service.allow_search,
                    'allow_archive': service.allow_archive,
                    'allow_all': service.allow_all,
                    'auth_user': getattr(service, 'auth_user', ''),
                    'auth_pass': getattr(service, 'auth_pass', ''),
                    'auto_start': service.status == ServiceStatus.RUNNING,
                    'public_auto_start': getattr(service, 'public_access_status', 'stopped') == 'running'
                }
                services_config.append(service_config)

            self.config_manager.set_services(services_config)
            self.config_manager.update_app_state(
                normal_exit=normal_exit,
                last_exit_time=time.time()
            )
            return True
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            return False

    def _auto_start_service(self, service: DufsService, public_auto_start: bool = False):
        """自动启动服务

        Args:
            service: 服务实例
            public_auto_start: 是否同时启动公网访问
        """
        try:
            # 找到服务索引
            service_index = -1
            for i, s in enumerate(self.manager.services):
                if s.name == service.name:
                    service_index = i
                    break

            if service_index < 0:
                return

            # 启动内网服务
            if service.status == ServiceStatus.STOPPED:
                print(f"[自动恢复] 正在启动服务: {service.name}")
                import threading
                # 使用传入的 log_manager 来记录日志
                threading.Thread(target=service.start, args=(self.log_manager,), daemon=True).start()

                # 如果需要，同时启动公网访问
                if public_auto_start:
                    def start_public_when_ready():
                        max_wait = 50
                        wait_count = 0
                        while wait_count < max_wait:
                            time.sleep(0.1)
                            wait_count += 1
                            if service.status == ServiceStatus.RUNNING:
                                print(f"[自动恢复] 正在启动公网访问: {service.name}")
                                threading.Thread(target=service.start_public_access, args=(self.log_manager,), daemon=True).start()
                                return

                    threading.Thread(target=start_public_when_ready, daemon=True).start()
        except Exception as e:
            print(f"[自动恢复] 启动服务失败: {str(e)}")

    def _generate_unique_service_name(self, base_name: str, exclude_index: int = None) -> str:
        """生成唯一的服务名称

        Args:
            base_name: 基础名称
            exclude_index: 排除的索引

        Returns:
            str: 唯一的服务名称
        """
        existing_names = [
            service.name for i, service in enumerate(self.manager.services)
            if exclude_index is None or i != exclude_index
        ]

        if base_name not in existing_names:
            return base_name

        counter = 1
        while counter <= 1000:
            new_name = f"{base_name}_{counter}"
            if new_name not in existing_names:
                return new_name
            counter += 1

        return f"{base_name}_{int(time.time())}"
