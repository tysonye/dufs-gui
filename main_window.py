"""主窗口文件 - 协调者模式，组合View、Controller和AutoSaver"""

from main_view import MainView
from main_controller import MainController
from auto_saver import AutoSaver


class MainWindow(MainView):
    """主窗口类 - 作为协调者，组合View、Controller和AutoSaver

    重构说明:
    - 继承自MainView，保留所有UI功能
    - 通过Controller处理业务逻辑
    - 通过AutoSaver处理自动保存
    - 保持向后兼容性
    """

    def __init__(self):
        # 先初始化视图（父类）
        super().__init__()

        # 初始化自动保存器
        self.auto_saver = AutoSaver(
            save_callback=self._on_auto_save,
            interval_ms=30000  # 每30秒保存一次
        )

        # 初始化控制器（依赖注入View和AutoSaver）
        self.controller = MainController(self, self.auto_saver)

        # 启动自动保存
        self.auto_saver.start(parent=self)

        # 初始化托盘管理器
        self.tray_manager = self.controller.init_tray_manager()

    def _on_auto_save(self, normal_exit: bool):
        """自动保存回调"""
        self.controller.save_config(normal_exit=normal_exit)

    def closeEvent(self, event):
        """关闭事件 - 委托给控制器处理"""
        self.controller.handle_close_event(event)

    # ========== 向后兼容的公共接口 ==========

    @property
    def manager(self):
        """服务管理器（向后兼容）"""
        return self.controller.manager

    @property
    def config_manager(self):
        """配置管理器（向后兼容）"""
        return self.controller.config_manager

    @property
    def log_manager(self):
        """日志管理器（向后兼容）"""
        return self.controller.log_manager

    @property
    def log_window(self):
        """日志窗口（向后兼容）"""
        return self.controller.log_window

    def update_service_tree(self):
        """更新服务表格（向后兼容）"""
        self.controller._update_service_tree()

    def _save_config(self, normal_exit: bool = False):
        """保存配置（向后兼容）"""
        return self.controller.save_config(normal_exit=normal_exit)

    def _on_exit(self, normal_exit: bool = True):
        """退出程序（向后兼容）"""
        self.controller._on_exit(normal_exit=normal_exit)
