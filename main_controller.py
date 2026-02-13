"""主窗口控制器 - 负责业务逻辑和状态管理（协调者模式）"""

import os
import subprocess
import sys
import threading
import time
from typing import Optional
from PyQt5.QtCore import QTimer, pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import QDialog, QMessageBox

from config_manager import ConfigManager
from service import DufsService, ServiceStatus
from service_manager import ServiceManager
from log_manager import LogManager
from log_window import LogWindow
from service_dialog import DufsServiceDialog
from service_info_dialog import ServiceInfoDialog
from constants import AppConstants
from auto_saver import AutoSaver

from config_controller import ConfigController
from service_controller import ServiceController
from tray_controller import TrayController
from lazy_loader import LazyImport


class MainController(QObject):
    """主窗口控制器 - 作为协调者，组合三个子控制器"""

    # 信号定义
    update_service_tree_signal = pyqtSignal()
    update_address_fields_signal = pyqtSignal(str, str)
    update_progress_signal = pyqtSignal(int)

    def __init__(self, view, auto_saver: AutoSaver):
        super().__init__()
        self.view = view
        self.auto_saver = auto_saver

        # 初始化管理器
        self.config_manager = ConfigManager()
        self.manager = ServiceManager()
        self.log_manager = LogManager(view)

        # 初始化子控制器（注意：ConfigController 需要 log_manager 来记录自动恢复服务的日志）
        self.config_controller = ConfigController(self.manager, self._on_service_status_updated, self.log_manager)
        self.service_controller = ServiceController(self.manager, self.log_manager, view)
        self.tray_controller = TrayController(view)

        # 连接子控制器信号
        self._connect_controller_signals()

        # 初始化日志窗口
        self.log_window: Optional[LogWindow] = None

        # 进度条状态
        self.progress_value = 0

        # 连接信号
        self._connect_signals()

        # 设置回调
        self._setup_callbacks()

        # 加载配置
        self._load_config()

    def _connect_controller_signals(self):
        """连接子控制器信号"""
        self.service_controller.service_updated.connect(self._on_update_service_tree)
        self.service_controller.progress_updated.connect(self._set_progress_value)
        self.service_controller.operation_started.connect(self.view.start_progress)
        self.service_controller.operation_finished.connect(self.view.stop_progress)

    def _connect_signals(self):
        """连接信号"""
        self.view.update_service_tree_signal.connect(self._on_update_service_tree)
        self.view.update_address_fields_signal.connect(self._on_update_address_fields)
        self.view.update_progress_signal.connect(self._set_progress_value)

        self.update_service_tree_signal.connect(self._on_update_service_tree)
        self.update_address_fields_signal.connect(self._on_update_address_fields)
        self.update_progress_signal.connect(self._set_progress_value)

    def _setup_callbacks(self):
        """设置UI回调"""
        # 按钮回调
        button_callbacks = {
            'add': self.add_service,
            'edit': self.edit_service,
            'delete': self.delete_service,
            'start': self.start_service,
            'start_public': self.start_public_access,
            'stop': self.stop_service,
            'batch_start': self.batch_start_services,
            'batch_stop': self.batch_stop_services,
            'log_window': self.open_log_window,
            'exit': self.exit_application,
            'help': self.show_help,
            'copy_local': self._copy_local_addr,
            'browse_local': self._browse_local_addr,
            'copy_public': self._copy_public_addr,
            'browse_public': self._browse_public_addr,
        }
        self.view.set_button_callbacks(button_callbacks)

        # 复选框回调
        self.view.set_checkbox_callback(self._toggle_startup)

        # 表格回调
        self.view.set_table_callbacks(
            self._show_service_context_menu,
            self._on_service_double_clicked,
            self._on_service_selection_changed
        )

    def init_tray_manager(self):
        """初始化托盘管理器"""
        return self.tray_controller.init_tray_manager()

    # ========== 配置管理（委托给ConfigController） ==========

    def _load_config(self):
        """加载配置"""
        if self.config_controller.load_config():
            self._update_service_tree()
            self.save_config()

    def save_config(self, normal_exit: bool = False) -> bool:
        """保存配置"""
        return self.config_controller.save_config(normal_exit)

    # ========== 服务CRUD操作（委托给ServiceController） ==========

    def add_service(self):
        """添加服务"""
        if self.service_controller.add_service():
            self._update_service_tree()
            self.save_config()

    def edit_service(self):
        """编辑服务"""
        row = self.view.get_selected_row()
        if self.service_controller.edit_service(row):
            self._update_service_tree()
            self.save_config()

    def delete_service(self):
        """删除服务"""
        row = self.view.get_selected_row()
        if row < 0 or row >= len(self.manager.services):
            self.view.show_message("警告", "请选择要删除的服务", icon=3)
            return

        service = self.manager.services[row]
        if self.view.show_question("确认", f"确定要删除服务 '{service.name}' 吗？\n\n删除前将自动停止服务。"):
            if self.service_controller.delete_service(row):
                self._update_service_tree()
                self.save_config()
                self.view.update_address_fields("", "")
                self.view.show_message("成功", f"服务 '{service.name}' 已成功删除")

    # ========== 服务启动/停止（委托给ServiceController） ==========

    def start_service(self):
        """启动内网共享"""
        row = self.view.get_selected_row()
        if row < 0 or row >= len(self.manager.services):
            self.view.show_message("警告", "请选择要启动内网共享的服务", icon=3)
            return

        service = self.manager.services[row]

        # 检查端口冲突并处理
        try:
            current_port = int(service.port)
            conflict_service = next(
                (s for i, s in enumerate(self.manager.services) if i != row and int(s.port) == current_port),
                None
            )

            if conflict_service:
                self.manager.release_allocated_port(current_port)
                new_port = self.manager.find_available_port(current_port + 1)
                self.view.show_message(
                    "端口已更换",
                    f"原端口 {current_port} 与服务 '{conflict_service.name}' 冲突，已自动更换为 {new_port}"
                )
                service.port = str(new_port)
                self.save_config()
            else:
                self.manager.release_allocated_port(current_port)
                new_port = self.manager.find_available_port(current_port)
                if new_port != current_port:
                    self.view.show_message(
                        "端口已更换",
                        f"原端口 {current_port} 为黑名单端口或已被占用，已自动更换为 {new_port}"
                    )
                    service.port = str(new_port)
                    self.save_config()
        except Exception as e:
            self.view.show_message("警告", f"端口检查失败: {str(e)}", icon=3)
            return

        # 委托给ServiceController
        self.service_controller.start_service(row)

    def stop_service(self):
        """停止共享服务"""
        row = self.view.get_selected_row()
        if row < 0 or row >= len(self.manager.services):
            self.view.show_message("警告", "请选择要停止共享服务的服务", icon=3)
            return

        service = self.manager.services[row]
        if service.status == ServiceStatus.STOPPED and service.public_access_status != "running":
            self.view.show_message("警告", "服务已经停止", icon=3)
            return

        self.service_controller.stop_service(row)

    def start_public_access(self):
        """启动公网共享（优化版）"""
        from PyQt5.QtWidgets import QApplication

        if self.service_controller.is_operation_in_progress:
            self.view.show_message("警告", "有操作正在进行中，请稍后再试", icon=3)
            return

        row = self.view.get_selected_row()
        if row < 0 or row >= len(self.manager.services):
            self.view.show_message("警告", "请选择要启动公网共享的服务", icon=3)
            return

        service = self.manager.services[row]
        if service.public_access_status == "running":
            self.view.show_message("警告", "公网共享已经在运行中", icon=3)
            return

        # 异步检查并下载 cloudflared
        self._check_and_start_public_async(service)

    def _check_and_start_public_async(self, service):
        """异步检查 cloudflared 并启动公网服务"""
        from PyQt5.QtWidgets import QApplication

        # 立即显示进度条，提升用户体验
        self.view.start_progress("检查公网组件...")
        self.service_controller.is_operation_in_progress = True
        QApplication.processEvents()

        def check_and_launch():
            try:
                # 快速检查文件是否存在（不导入模块）
                cloudflared_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'cloudflared.exe'
                )
                # 快速检查文件是否存在（不触发下载对话框）
                if not os.path.exists(cloudflared_path):
                    # 需要下载，回到主线程执行
                    self.update_progress_signal.emit(10)

                    def show_download_and_start():
                        with LazyImport('cloudflare_tunnel') as ct:
                            if ct.check_and_download_cloudflared(self.view):
                                # 下载成功，继续启动
                                self._do_start_public_access(service)
                            else:
                                # 下载失败或用户取消
                                self.view.stop_progress(success=False)
                                self.service_controller.is_operation_in_progress = False

                    QTimer.singleShot(0, show_download_and_start)
                else:
                    # 文件已存在，直接启动
                    self._do_start_public_access(service)
            except Exception as e:
                print(f"[公网启动] 检查失败: {e}")
                self.view.stop_progress(success=False)
                self.service_controller.is_operation_in_progress = False

        # 在新线程中执行检查
        threading.Thread(target=check_and_launch, daemon=True).start()

    def _do_start_public_access(self, service):
        """执行公网服务启动（优化版）"""
        from PyQt5.QtWidgets import QApplication

        # 更新进度条状态
        self.view.start_progress("启动公网共享")
        self.update_progress_signal.emit(20)
        QApplication.processEvents()

        # 检查内网服务状态
        if service.status != ServiceStatus.RUNNING:
            # 检查端口
            try:
                current_port = int(service.port)
                conflict_service = next(
                    (s for s in self.manager.services if s != service and s.status == ServiceStatus.RUNNING and int(s.port) == current_port),
                    None
                )

                if conflict_service:
                    self.manager.release_allocated_port(current_port)
                    new_port = self.manager.find_available_port(current_port)
                    # 延迟显示端口更换提示，避免阻塞
                    QTimer.singleShot(0, lambda: self.view.show_message(
                        "端口已更换",
                        f"原端口 {current_port} 与服务 '{conflict_service.name}' 冲突，已自动更换为 {new_port}"
                    ))
                    service.port = str(new_port)
                    self.save_config()
                else:
                    self.manager.release_allocated_port(current_port)
                    new_port = self.manager.find_available_port(current_port)
                    if new_port != current_port:
                        QTimer.singleShot(0, lambda: self.view.show_message(
                            "端口已更换",
                            f"原端口 {current_port} 为黑名单端口或已被占用，已自动更换为 {new_port}"
                        ))
                        service.port = str(new_port)
                        self.save_config()
            except Exception as e:
                self.view.stop_progress(success=False)
                self.service_controller.is_operation_in_progress = False
                QTimer.singleShot(0, lambda: self.view.show_message("警告", f"端口检查失败: {str(e)}", icon=3))
                return

            self.update_progress_signal.emit(30)
            QApplication.processEvents()

            # 先启动内网服务
            threading.Thread(target=service.start, args=(self.log_manager,), daemon=True).start()

            # 监控内网服务启动，然后启动公网服务
            def monitor_internal_then_public():
                max_wait = 80  # 减少等待时间 100->80
                wait_count = 0

                while wait_count < max_wait:
                    time.sleep(0.05)  # 减少睡眠间隔 0.1->0.05，提高响应速度
                    wait_count += 1

                    # 每10次迭代更新一次进度条，减少UI更新频率
                    if wait_count % 10 == 0:
                        if service.status == ServiceStatus.RUNNING:
                            self.update_progress_signal.emit(60)
                        elif service.status == ServiceStatus.ERROR:
                            self.view.stop_progress(success=False)
                            self.service_controller.is_operation_in_progress = False
                            return
                        else:
                            progress = min(30 + wait_count // 4, 55)
                            self.update_progress_signal.emit(progress)

                if service.status != ServiceStatus.RUNNING:
                    self.view.stop_progress(success=False)
                    self.service_controller.is_operation_in_progress = False
                    return

                self.update_progress_signal.emit(60)

                # 启动公网服务
                threading.Thread(target=service.start_public_access, args=(self.log_manager,), daemon=True).start()

                # 轮询公网服务状态（更快响应）
                wait_count = 0
                max_wait_public = 150  # 最多等待15秒
                while wait_count < max_wait_public:
                    time.sleep(0.1)
                    wait_count += 1

                    if service.public_access_status == "running":
                        self.view.stop_progress(success=True)
                        self.service_controller.is_operation_in_progress = False
                        return
                    elif service.public_access_status == "error":
                        self.view.stop_progress(success=False)
                        self.service_controller.is_operation_in_progress = False
                        return
                    else:
                        # 每5次迭代更新一次进度
                        if wait_count % 5 == 0:
                            progress = min(60 + wait_count // 3, 95)
                            self.update_progress_signal.emit(progress)

                self.view.stop_progress(success=False)
                self.service_controller.is_operation_in_progress = False

            threading.Thread(target=monitor_internal_then_public, daemon=True).start()
        else:
            # 直接启动公网服务
            self.update_progress_signal.emit(50)
            QApplication.processEvents()

            threading.Thread(target=service.start_public_access, args=(self.log_manager,), daemon=True).start()

            # 监控公网服务启动
            def monitor_public_only():
                max_wait = 150  # 最多等待15秒
                wait_count = 0
                while wait_count < max_wait:
                    time.sleep(0.1)
                    wait_count += 1

                    if service.public_access_status == "running":
                        self.view.stop_progress(success=True)
                        self.service_controller.is_operation_in_progress = False
                        return
                    elif service.public_access_status == "error":
                        self.view.stop_progress(success=False)
                        self.service_controller.is_operation_in_progress = False
                        return
                    else:
                        # 每5次迭代更新一次进度
                        if wait_count % 5 == 0:
                            progress = min(50 + wait_count // 3, 95)
                            self.update_progress_signal.emit(progress)

                self.view.stop_progress(success=False)
                self.service_controller.is_operation_in_progress = False

            threading.Thread(target=monitor_public_only, daemon=True).start()

    # ========== 进度条控制 ==========

    def _set_progress_value(self, value: int):
        """设置进度条值"""
        self.progress_value = value
        self.view.set_progress_value(value)

    # ========== 事件处理 ==========

    def _on_service_status_updated(self):
        """处理服务状态更新信号"""
        try:
            self.update_service_tree_signal.emit()

            row = self.view.get_selected_row()
            if 0 <= row < len(self.manager.services):
                service = self.manager.services[row]
                self._update_address_fields_for_service(service)
            else:
                for service in self.manager.services:
                    if service.status == ServiceStatus.RUNNING and service.local_addr:
                        self._update_address_fields_for_service(service)
                        break

            self.save_config()
        except Exception as e:
            print(f"处理服务状态更新失败: {str(e)}")

    def _update_service_tree(self):
        """更新服务表格"""
        self.view.update_service_table(self.manager.services, AppConstants.STATUS_COLORS)

    def _on_update_service_tree(self):
        """信号触发的服务表格更新"""
        self._update_service_tree()
        # 同时更新地址显示（避免递归，直接调用地址更新逻辑）
        row = self.view.get_selected_row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            self._update_address_fields_for_service(service)
        else:
            for service in self.manager.services:
                if service.status == ServiceStatus.RUNNING and service.local_addr:
                    self._update_address_fields_for_service(service)
                    break

    def _update_address_fields_for_service(self, service: DufsService):
        """更新地址编辑框"""
        try:
            local_addr = str(service.local_addr)
            public_url = str(getattr(service, 'public_url', ''))
            self.update_address_fields_signal.emit(local_addr, public_url)
        except Exception as e:
            print(f"更新地址编辑框失败: {str(e)}")

    def _on_update_address_fields(self, local_addr: str, public_addr: str):
        """信号触发的地址更新"""
        self.view.update_address_fields(local_addr, public_addr)

    def _on_service_selection_changed(self):
        """服务选择变更事件"""
        try:
            row = self.view.get_selected_row()
            if 0 <= row < len(self.manager.services):
                service = self.manager.services[row]
                self._update_address_fields_for_service(service)

                # 如果日志窗口已打开，同步切换标签
                if self.log_window and self.log_window.isVisible():
                    self.log_window.set_current_tab(service.name)
        except Exception as e:
            print(f"服务选择变更处理失败: {str(e)}")

    def _on_service_double_clicked(self, item):
        """服务双击事件"""
        row = item.row()
        if 0 <= row < len(self.manager.services):
            service = self.manager.services[row]
            # 直接使用已导入的 ServiceInfoDialog
            dialog = ServiceInfoDialog(parent=self.view, service=service)
            dialog.exec_()

    def _show_service_context_menu(self, position):
        """显示服务上下文菜单"""
        if self.view.get_selected_row() < 0:
            return

        callbacks = {
            'start': self.start_service,
            'start_public': self.start_public_access,
            'stop': self.stop_service,
            'edit': self.edit_service,
            'delete': self.delete_service,
        }
        self.view.show_context_menu(position, callbacks)

    # ========== 地址操作 ==========

    def _copy_local_addr(self):
        """复制本地地址"""
        addr = self.view.get_local_address()
        if addr:
            self.view.copy_to_clipboard(addr)
            self.view.show_message("提示", "本地地址已复制到剪贴板")
        else:
            self.view.show_message("警告", "本地地址为空，请先启动服务", icon=3)

    def _browse_local_addr(self):
        """浏览器访问本地地址"""
        addr = self.view.get_local_address()
        if addr:
            self.view.open_browser(addr)
        else:
            self.view.show_message("警告", "本地地址为空，请先启动服务", icon=3)

    def _copy_public_addr(self):
        """复制公网地址"""
        addr = self.view.get_public_address()
        if addr:
            self.view.copy_to_clipboard(addr)
            self.view.show_message("提示", "公网地址已复制到剪贴板")
        else:
            self.view.show_message("警告", "公网地址为空，请先启动公网访问", icon=3)

    def _browse_public_addr(self):
        """浏览器访问公网地址"""
        addr = self.view.get_public_address()
        if addr:
            self.view.open_browser(addr)
        else:
            self.view.show_message("警告", "公网地址为空，请先启动公网访问", icon=3)

    # ========== 其他功能 ==========

    def open_log_window(self):
        """打开日志窗口（优化版）"""
        from PyQt5.QtWidgets import QApplication

        # 1. 创建窗口
        if not self.log_window:
            self.log_window = LogWindow(self.view)

        # 2. 创建服务标签页
        self._create_log_tabs_lazy()

        # 3. 加载日志内容（在显示前加载，避免空白闪烁）
        self._load_log_history_async()

        # 4. 激活当前选中服务的标签页
        current_row = self.view.get_selected_row()
        if 0 <= current_row < len(self.manager.services):
            service = self.manager.services[current_row]
            self.log_window.set_current_tab(service.name)

        # 5. 显示窗口
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()

        # 6. 强制处理事件，确保UI立即刷新
        QApplication.processEvents()

    def _create_log_tabs_lazy(self):
        """创建日志标签页（极简版 - 预创建控件但延迟设置内容）"""
        from PyQt5.QtWidgets import QPlainTextEdit
        from service import ServiceStatus

        # 获取运行中的服务名称集合
        running_service_names = {s.name for s in self.manager.services if s.status == ServiceStatus.RUNNING}

        # 1. 获取现有标签页（倒序遍历避免索引问题）
        existing_tabs = {}
        for i in range(self.log_window.log_tabs.count() - 1, -1, -1):
            tab_name = self.log_window.log_tabs.tabText(i)
            existing_tabs[tab_name] = i

        # 2. 移除不需要的标签页（包括已停止的服务和"提示"标签）
        for tab_name, index in existing_tabs.items():
            if tab_name not in running_service_names or tab_name == "提示":
                self.log_window.log_tabs.removeTab(index)

        # 3. 为运行中的服务创建标签页（使用极简初始化，不设置样式）
        current_tabs = {self.log_window.log_tabs.tabText(i) for i in range(self.log_window.log_tabs.count())}
        for service_name in running_service_names:
            if service_name not in current_tabs:
                log_widget = QPlainTextEdit()
                log_widget.setReadOnly(True)
                self.log_window.add_log_tab(service_name, log_widget)

    def _load_log_history_async(self):
        """加载历史日志（极速版 - 立即显示当前标签）"""
        import re
        from PyQt5.QtWidgets import QPlainTextEdit

        log_buffer = self.log_manager.log_buffer
        if not log_buffer:
            return

        # 只加载最近50条，保证速度
        max_logs_to_load = 50
        total_logs = len(log_buffer)
        logs_to_load = log_buffer[-max_logs_to_load:] if total_logs > max_logs_to_load else log_buffer

        # 获取当前活动标签页
        current_index = self.log_window.log_tabs.currentIndex()
        current_service = self.log_window.log_tabs.tabText(current_index) if current_index >= 0 else None

        # 预构建服务名称到控件的映射
        service_widget_map = {}
        for i in range(self.log_window.log_tabs.count()):
            service_name = self.log_window.log_tabs.tabText(i)
            widget = self.log_window.log_tabs.widget(i)
            if isinstance(widget, QPlainTextEdit):
                service_widget_map[service_name] = widget

        # 按服务分组日志（简化正则，只找服务名）
        service_logs = {}
        for log_message in logs_to_load:
            match = re.search(r'\[.*?\] \[.*?\] \[(.*?)\]', log_message)
            if match:
                service_name = match.group(1)
                if service_name != "全局日志" and service_name in service_widget_map:
                    service_logs.setdefault(service_name, []).append(log_message)

        # 立即显示当前活动标签的内容
        if current_service and current_service in service_logs:
            widget = service_widget_map[current_service]
            logs = service_logs[current_service]
            widget.setPlainText("\n".join(logs))

        # 后台加载其他标签
        other_services = [s for s in service_logs.keys() if s != current_service]
        for service_name in other_services:
            widget = service_widget_map[service_name]
            logs = service_logs[service_name]
            widget.setPlainText("\n".join(logs))

    def _clear_loading_hints(self):
        """清空加载提示文本（简化版，避免触发耗时操作）"""
        from PyQt5.QtWidgets import QPlainTextEdit

        # 清空所有加载提示（直接设置空文本，不触发过滤）
        for i in range(self.log_window.log_tabs.count()):
            widget = self.log_window.log_tabs.widget(i)
            if widget and isinstance(widget, QPlainTextEdit):
                text = widget.toPlainText()
                if "日志加载中" in text:
                    # 使用 clear() 而不是 setPlainText("")，避免触发不必要的信号
                    widget.clear()

    def _toggle_startup(self, checked):
        """切换开机自启状态（使用延迟加载）"""
        try:
            # 延迟导入 startup_manager，减少启动时间
            with LazyImport('startup_manager') as sm:
                if checked:
                    sm.StartupManager.enable_startup()
                    self.view.show_message("提示", "已设置为开机自启")
                else:
                    sm.StartupManager.disable_startup()
                    self.view.show_message("提示", "已取消开机自启")
        except Exception as e:
            self.view.show_message("错误", f"设置开机自启失败: {str(e)}", icon=3)

    def exit_application(self):
        """退出应用程序"""
        self._on_exit(normal_exit=True)

    def _on_exit(self, normal_exit: bool = True):
        """真正退出程序"""
        self.auto_saver.stop()

        for service in self.manager.services:
            if service.process:
                try:
                    service.process.terminate()
                    service.process.wait(timeout=2)
                except (OSError, subprocess.SubprocessError):
                    pass
            if hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                try:
                    service.cloudflared_process.terminate()
                    service.cloudflared_process.wait(timeout=2)
                except (OSError, subprocess.SubprocessError):
                    pass

        self.save_config(normal_exit=normal_exit)

        if self.log_window:
            self.log_window.close()

        self.tray_controller.hide()

        from PyQt5.QtWidgets import QApplication
        QApplication.quit()

    def handle_close_event(self, event):
        """处理关闭事件"""
        if not event.spontaneous():
            print("[系统事件] 检测到系统关闭，正在保存状态...")
            self._on_exit(normal_exit=False)
            event.accept()
        else:
            event.ignore()
            self.view.hide()
            self.tray_controller.show_message("DufsGUI", "程序已最小化到托盘")

    def batch_start_services(self):
        """批量启动所有服务"""
        if not self.manager.services:
            self.view.show_message("提示", "没有可启动的服务")
            return
        
        started_count = 0
        for i, service in enumerate(self.manager.services):
            if service.status != ServiceStatus.RUNNING:
                self.service_controller.start_service(i)
                started_count += 1
        
        if started_count > 0:
            self.view.show_message("成功", f"已启动 {started_count} 个服务")
        else:
            self.view.show_message("提示", "所有服务已在运行中")

    def batch_stop_services(self):
        """批量停止所有服务"""
        if not self.manager.services:
            self.view.show_message("提示", "没有可停止的服务")
            return
        
        stopped_count = 0
        for i, service in enumerate(self.manager.services):
            if service.status == ServiceStatus.RUNNING:
                self.service_controller.stop_service(i)
                stopped_count += 1
        
        if stopped_count > 0:
            self.view.show_message("成功", f"已停止 {stopped_count} 个服务")
        else:
            self.view.show_message("提示", "没有运行中的服务")

    def show_help(self):
        """显示帮助信息"""
        help_text = """
<h2>DufsGUI 使用帮助</h2>

<h3>📁 服务管理</h3>
<ul>
<li><b>新建服务</b>：点击右上角"+ 新建服务"按钮创建文件共享服务</li>
<li><b>编辑服务</b>：选中服务后，在右侧面板点击"编辑"按钮</li>
<li><b>删除服务</b>：选中服务后，在右侧面板点击"删除"按钮</li>
</ul>

<h3>▶️ 服务控制</h3>
<ul>
<li><b>启动内网共享</b>：启动本地文件共享服务</li>
<li><b>启动公网共享</b>：通过 Cloudflare Tunnel 创建公网访问链接</li>
<li><b>停止服务</b>：停止当前选中的服务</li>
</ul>

<h3>🔗 访问地址</h3>
<ul>
<li>服务启动后，内网和公网地址会显示在右侧面板</li>
<li>点击"复制"按钮复制地址到剪贴板</li>
<li>点击"访问"按钮在浏览器中打开</li>
</ul>

<h3>📋 其他功能</h3>
<ul>
<li><b>开机自启</b>：勾选底部"开机自动启动"复选框</li>
<li><b>日志窗口</b>：点击"查看日志"查看服务运行日志</li>
<li><b>托盘图标</b>：关闭窗口后程序会继续运行在系统托盘</li>
</ul>

<h3>💡 提示</h3>
<ul>
<li>双击服务列表中的服务可查看详细信息</li>
<li>右键点击服务可快速操作</li>
<li>程序会自动保存配置</li>
</ul>
        """
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle("使用帮助")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(help_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
