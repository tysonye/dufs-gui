"""主窗口控制器 - 负责业务逻辑和状态管理（协调者模式）"""

import sys
import threading
import time
from typing import Optional
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QDialog

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

        # 初始化子控制器
        self.config_controller = ConfigController(self.manager, self._on_service_status_updated)
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
            'log_window': self.open_log_window,
            'exit': self.exit_application,
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
        """启动公网共享"""
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

        # 先检查并下载 cloudflared（使用延迟加载）
        with LazyImport('cloudflare_tunnel') as ct:
            if not ct.check_and_download_cloudflared(self.view):
                return

        # 启动进度条
        self.view.start_progress("启动公网共享")
        self.service_controller.is_operation_in_progress = True

        # 检查内网服务状态
        if service.status != ServiceStatus.RUNNING:
            # 先检查端口
            try:
                current_port = int(service.port)
                conflict_service = next(
                    (s for s in self.manager.services if s != service and s.status == ServiceStatus.RUNNING and int(s.port) == current_port),
                    None
                )

                if conflict_service:
                    self.manager.release_allocated_port(current_port)
                    new_port = self.manager.find_available_port(current_port)
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
                self.view.stop_progress(success=False)
                self.service_controller.is_operation_in_progress = False
                self.view.show_message("警告", f"端口检查失败: {str(e)}", icon=3)
                return

            # 先启动内网服务，再启动公网服务
            threading.Thread(target=service.start, args=(self.log_manager,), daemon=True).start()

            # 监控内网服务启动，然后启动公网服务
            def monitor_internal_then_public():
                max_wait = 100
                wait_count = 0

                while wait_count < max_wait:
                    time.sleep(0.1)
                    wait_count += 1
                    if service.status == ServiceStatus.RUNNING:
                        break
                    elif service.status == ServiceStatus.ERROR:
                        self.view.stop_progress(success=False)
                        self.service_controller.is_operation_in_progress = False
                        return
                    else:
                        progress = min(40 + wait_count // 2, 60)
                        self.update_progress_signal.emit(progress)

                if service.status != ServiceStatus.RUNNING:
                    self.view.stop_progress(success=False)
                    self.service_controller.is_operation_in_progress = False
                    return

                # 启动公网服务
                threading.Thread(target=service.start_public_access, args=(self.log_manager,), daemon=True).start()

                # 轮询公网服务状态
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
                        progress = min(60 + wait_count, 95)
                        self.update_progress_signal.emit(progress)

                self.view.stop_progress(success=False)
                self.service_controller.is_operation_in_progress = False

            QTimer.singleShot(200, monitor_internal_then_public)
        else:
            # 直接启动公网服务
            threading.Thread(target=service.start_public_access, args=(self.log_manager,), daemon=True).start()

            # 监控公网服务启动
            def monitor_public_only():
                max_wait = 100
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
                        progress = min(80 + wait_count, 95)
                        self.update_progress_signal.emit(progress)

                self.view.stop_progress(success=False)
                self.service_controller.is_operation_in_progress = False

            QTimer.singleShot(200, monitor_public_only)

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

    def _on_service_selection_changed(self, selected, deselected):
        """服务选择变更事件"""
        try:
            row = self.view.get_selected_row()
            if 0 <= row < len(self.manager.services):
                service = self.manager.services[row]
                self._update_address_fields_for_service(service)
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
        """打开日志窗口"""
        if not self.log_window:
            self.log_window = LogWindow(self.view)

        for service in self.manager.services:
            service_name = service.name
            service_tab_index = -1
            for i in range(self.log_window.log_tabs.count()):
                if self.log_window.log_tabs.tabText(i) == service_name:
                    service_tab_index = i
                    break

            if service_tab_index == -1:
                from PyQt5.QtWidgets import QPlainTextEdit
                log_widget = QPlainTextEdit()
                log_widget.setReadOnly(True)
                log_widget.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11px;")
                self.log_window.add_log_tab(service_name, log_widget)

        import re
        for log_message in self.log_manager.log_buffer:
            service_match = re.search(r'\[\d{2}:\d{2}:\d{2}\] \[(INFO|ERROR)\] \[(.*?)\]', log_message)
            if service_match:
                service_name = service_match.group(2)
                if service_name and service_name != "全局日志":
                    for i in range(self.log_window.log_tabs.count()):
                        if self.log_window.log_tabs.tabText(i) == service_name:
                            self.log_window.append_log(i, log_message)
                            break

        self.log_window.show()

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
                except Exception:
                    pass
            if hasattr(service, 'cloudflared_process') and service.cloudflared_process:
                try:
                    service.cloudflared_process.terminate()
                    service.cloudflared_process.wait(timeout=2)
                except Exception:
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
