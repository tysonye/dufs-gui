"""托盘管理模块"""
# pyright: reportAny=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false

import os
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QTimer
from service import ServiceStatus


class TrayManager:
    """系统托盘管理器"""
    
    def __init__(self, main_window):
        """初始化托盘管理器
        
        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        self.tray_icon = None
        self.tray_menu = None
        self.service_menu = None
        self.service_actions = []
        
        # 初始化托盘
        self._init_tray()
        
        # 定时更新托盘菜单
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_tray_menu)
        self.update_timer.start(2000)  # 每2秒更新一次
        
        # 立即更新一次菜单
        self.update_tray_menu()
    
    def _init_tray(self):
        """初始化托盘图标和菜单"""
        # 检查图标文件是否存在
        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            # 如果图标文件不存在，使用默认图标
            icon = QSystemTrayIcon.MessageIcon.Information
        
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(icon, self.main_window)
        self.tray_icon.setToolTip("DufsGUI - 服务管理器")
        
        # 创建托盘菜单
        self.tray_menu = QMenu()
        
        # 添加恢复窗口动作
        restore_action = QAction("恢复窗口", self.main_window)
        restore_action.triggered.connect(self._on_restore_window)
        self.tray_menu.addAction(restore_action)
        
        # 添加分隔线
        self.tray_menu.addSeparator()
        
        # 添加服务管理子菜单
        self.service_menu = QMenu("服务管理")
        self.tray_menu.addMenu(self.service_menu)
        
        # 添加分隔线
        self.tray_menu.addSeparator()
        
        # 添加退出动作
        exit_action = QAction("退出程序", self.main_window)
        exit_action.triggered.connect(self._on_exit)
        self.tray_menu.addAction(exit_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # 连接托盘图标点击事件
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
    
    def update_tray_menu(self):
        """更新托盘菜单"""
        if not self.service_menu:
            return
        
        # 清空服务管理子菜单
        self.service_menu.clear()
        
        # 添加服务状态菜单项
        services = []
        if hasattr(self.main_window, 'manager') and hasattr(self.main_window.manager, 'services'):
            services = self.main_window.manager.services
        
        if services:
            # 添加服务统计信息
            running_count = sum(1 for s in services if s.status == ServiceStatus.RUNNING)
            total_count = len(services)
            stats_action = QAction(f"服务统计: {running_count}/{total_count} 运行中", self.main_window)
            stats_action.setEnabled(False)
            self.service_menu.addAction(stats_action)
            self.service_menu.addSeparator()
            
            for i, service in enumerate(services):
                # 创建服务操作子菜单
                service_submenu = QMenu()
                
                # 根据状态设置菜单标题和图标
                status_text = f"{service.name} [{service.status}]"
                if service.status == ServiceStatus.RUNNING:
                    # 运行中 - 使用绿色标识
                    service_submenu.setTitle(f"🟢 {status_text}")
                elif service.status == ServiceStatus.STARTING:
                    # 启动中 - 使用蓝色标识
                    service_submenu.setTitle(f"🔵 {status_text}")
                elif service.status == ServiceStatus.ERROR:
                    # 错误 - 使用红色标识
                    service_submenu.setTitle(f"🔴 {status_text}")
                else:
                    # 停止/其他 - 使用灰色标识
                    service_submenu.setTitle(f"⚪ {status_text}")
                
                # 添加启动/停止动作
                if service.status == ServiceStatus.RUNNING:
                    stop_action = QAction("⏹ 停止服务", self.main_window)
                    stop_action.triggered.connect(lambda checked, idx=i: self._on_stop_service(idx))
                    service_submenu.addAction(stop_action)
                else:
                    start_action = QAction("▶ 启动服务", self.main_window)
                    start_action.triggered.connect(lambda checked, idx=i: self._on_start_service(idx))
                    service_submenu.addAction(start_action)
                
                # 添加公网访问动作
                if service.status == ServiceStatus.RUNNING:
                    service_submenu.addSeparator()
                    if hasattr(service, 'public_access_status') and service.public_access_status == "running":
                        stop_public_action = QAction("🌐 停止公网访问", self.main_window)
                        stop_public_action.triggered.connect(lambda checked, idx=i: self._on_stop_public_access(idx))
                        service_submenu.addAction(stop_public_action)
                    else:
                        start_public_action = QAction("🌐 启动公网访问", self.main_window)
                        start_public_action.triggered.connect(lambda checked, idx=i: self._on_start_public_access(idx))
                        service_submenu.addAction(start_public_action)
                
                # 添加查看日志动作
                service_submenu.addSeparator()
                log_action = QAction("📋 查看日志", self.main_window)
                log_action.triggered.connect(lambda checked, idx=i: self._on_view_logs(idx))
                service_submenu.addAction(log_action)
                
                # 添加服务子菜单到服务管理菜单
                self.service_menu.addMenu(service_submenu)
        else:
            # 添加无服务提示
            no_service_action = QAction("⚠ 无服务配置", self.main_window)
            no_service_action.setEnabled(False)
            self.service_menu.addAction(no_service_action)
            
            # 添加提示信息
            tip_action = QAction("  请先在主窗口添加服务", self.main_window)
            tip_action.setEnabled(False)
            self.service_menu.addAction(tip_action)
    
    def _get_status_color(self, status):
        """获取状态对应的颜色
        
        Args:
            status: 服务状态
            
        Returns:
            QColor: 状态对应的颜色
        """
        from constants import AppConstants
        color_hex = AppConstants.STATUS_COLORS.get(status, "#95a5a6")
        return QColor(color_hex)
    
    def _on_tray_activated(self, reason):
        """托盘图标激活事件
        
        Args:
            reason: 激活原因
        """
        if reason == QSystemTrayIcon.Trigger:
            # 左键点击托盘图标
            self._on_restore_window()
    
    def _on_restore_window(self):
        """恢复窗口"""
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        elif not self.main_window.isVisible():
            self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
    
    def _on_exit(self):
        """退出程序"""
        # 停止定时器
        self.update_timer.stop()
        
        # 隐藏托盘图标
        if self.tray_icon:
            self.tray_icon.hide()
        
        # 调用主窗口的退出方法
        if hasattr(self.main_window, '_on_exit'):
            self.main_window._on_exit()
        else:
            self.main_window.close()
    
    def _on_start_service(self, index):
        """启动服务
        
        Args:
            index: 服务索引
        """
        if hasattr(self.main_window, '_start_service'):
            # 模拟选择服务并启动
            self.main_window.service_table.selectRow(index)
            self.main_window._start_service()
    
    def _on_stop_service(self, index):
        """停止服务
        
        Args:
            index: 服务索引
        """
        if hasattr(self.main_window, '_stop_service'):
            # 模拟选择服务并停止
            self.main_window.service_table.selectRow(index)
            self.main_window._stop_service()
    
    def _on_start_public_access(self, index):
        """启动公网访问
        
        Args:
            index: 服务索引
        """
        if hasattr(self.main_window, '_start_public_access'):
            # 模拟选择服务并启动公网访问
            self.main_window.service_table.selectRow(index)
            self.main_window._start_public_access()
    
    def _on_stop_public_access(self, index):
        """停止公网访问
        
        Args:
            index: 服务索引
        """
        if hasattr(self.main_window, '_stop_public_access'):
            # 模拟选择服务并停止公网访问
            self.main_window.service_table.selectRow(index)
            self.main_window._stop_public_access()
    
    def _on_view_logs(self, index):
        """查看服务日志
        
        Args:
            index: 服务索引
        """
        if hasattr(self.main_window, '_open_log_window'):
            # 先选择对应的服务行
            if hasattr(self.main_window, 'service_table'):
                self.main_window.service_table.selectRow(index)
            self.main_window._open_log_window()
    
    def show_message(self, title, message, icon=QSystemTrayIcon.Information, duration=3000):
        """显示托盘消息
        
        Args:
            title: 消息标题
            message: 消息内容
            icon: 消息图标
            duration: 显示持续时间（毫秒）
        """
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, duration)
    
    def hide(self):
        """隐藏托盘图标"""
        if self.tray_icon:
            self.tray_icon.hide()
    
    def show(self):
        """显示托盘图标"""
        if self.tray_icon:
            self.tray_icon.show()
