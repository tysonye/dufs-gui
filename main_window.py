"""主窗口文件 - 协调者模式，组合View、Controller和AutoSaver"""

from PyQt5.QtCore import QTimer
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
    - 优化：延迟初始化控制器，加快窗口显示速度
    """

    def __init__(self):
        # 先初始化视图（父类）- 只创建UI框架
        super().__init__()

        # 延迟初始化控制器（关键优化）
        self.auto_saver = None
        self.controller = None
        self.tray_manager = None
        self._init_timer = QTimer()
        self._init_timer.singleShot(100, self._init_controller)

    def _init_controller(self):
        """延迟初始化控制器"""
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

        # 更新UI显示
        self._on_controller_ready()

    def _on_controller_ready(self):
        """控制器初始化完成后的回调"""
        # 更新服务表格
        if hasattr(self, 'controller') and self.controller:
            self.update_service_tree()

    def _on_auto_save(self, normal_exit: bool):
        """自动保存回调"""
        if self.controller:
            self.controller.save_config(normal_exit=normal_exit)

    def closeEvent(self, event):
        """关闭事件 - 委托给控制器处理"""
        if self.controller:
            self.controller.handle_close_event(event)
        else:
            event.accept()

    # ========== 向后兼容的公共接口 ==========

    @property
    def manager(self):
        """服务管理器（向后兼容）"""
        return self.controller.manager if self.controller else None

    @property
    def config_manager(self):
        """配置管理器（向后兼容）"""
        return self.controller.config_manager if self.controller else None

    @property
    def log_manager(self):
        """日志管理器（向后兼容）"""
        return self.controller.log_manager if self.controller else None

    @property
    def log_window(self):
        """日志窗口（向后兼容）"""
        return self.controller.log_window if self.controller else None

    def update_service_tree(self):
        """更新服务表格（向后兼容）"""
        if self.controller:
            self.controller._update_service_tree()

    def _save_config(self, normal_exit: bool = False):
        """保存配置（向后兼容）"""
        if self.controller:
            return self.controller.save_config(normal_exit=normal_exit)
        return False

    def _on_exit(self, normal_exit: bool = True):
        """退出程序（向后兼容）"""
        if self.controller:
            self.controller._on_exit(normal_exit=normal_exit)
