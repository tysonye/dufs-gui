"""日志窗口文件"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QPlainTextEdit
)
from constants import LOG_WINDOW_STYLESHEET


class LogWindow(QMainWindow):
    """独立日志窗口，用于显示服务日志"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dufs 日志窗口")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(LOG_WINDOW_STYLESHEET)

        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局（仅包含标签页，无搜索栏）
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建日志Tab容器
        self.log_tabs = QTabWidget()
        self.log_tabs.setTabsClosable(False)  # 禁用关闭按钮
        main_layout.addWidget(self.log_tabs)

        # 保存原始日志内容的字典
        self.original_logs = {}

    def add_log_tab(self, service_name, log_widget, skip_initial_content=False):
        """添加日志标签页

        Args:
            service_name: 服务名称
            log_widget: 日志控件
            skip_initial_content: 是否跳过初始内容
        """
        index = self.log_tabs.count()
        self.log_tabs.addTab(log_widget, service_name)

        # 初始化原始日志内容
        self.original_logs[index] = []

        # 将当前日志控件的内容添加到原始日志
        if not skip_initial_content:
            current_logs = log_widget.toPlainText().split('\n')
            if current_logs and current_logs[0]:
                self.original_logs[index].extend(current_logs)

    def remove_log_tab(self, index):
        """移除日志标签页"""
        if 0 <= index < self.log_tabs.count():
            self.log_tabs.removeTab(index)

            # 更新原始日志字典的键
            new_logs = {}
            for i in range(self.log_tabs.count()):
                if i < index:
                    if i in self.original_logs:
                        new_logs[i] = self.original_logs[i]
                elif i > index:
                    if i in self.original_logs:
                        new_logs[i-1] = self.original_logs[i]
            self.original_logs = new_logs

    def set_current_tab(self, service_name):
        """设置当前活动标签页

        Args:
            service_name: 服务名称
        """
        for i in range(self.log_tabs.count()):
            if self.log_tabs.tabText(i) == service_name:
                self.log_tabs.setCurrentIndex(i)
                return True
        return False

    def append_log(self, index, message):
        """添加日志条目，同时保存到原始日志"""
        if index < 0 or index >= self.log_tabs.count():
            return

        log_widget = self.log_tabs.widget(index)
        if not log_widget:
            return

        # 保存到原始日志
        if index not in self.original_logs:
            self.original_logs[index] = []
        self.original_logs[index].append(message)

        # 直接添加到控件
        log_widget.appendPlainText(message)

    def add_log(self, message, level=None):
        """添加日志条目到当前活动标签页"""
        # 添加到当前活动的标签页
        current_index = self.log_tabs.currentIndex()
        if current_index >= 0:
            self.append_log(current_index, message)

    def add_system_message(self, message):
        """添加系统消息到全局日志标签页"""
        # 查找或创建全局日志标签页
        global_tab_index = -1
        for i in range(self.log_tabs.count()):
            if self.log_tabs.tabText(i) in ["系统", "日志", "全局"]:
                global_tab_index = i
                break

        if global_tab_index == -1:
            # 创建系统日志标签页（放在第一个位置）
            log_widget = QPlainTextEdit()
            log_widget.setReadOnly(True)
            log_widget.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11px;")
            self.add_log_tab("系统", log_widget)
            global_tab_index = self.log_tabs.count() - 1
            # 移到第一个位置
            if global_tab_index > 0:
                self.log_tabs.tabBar().moveTab(global_tab_index, 0)
                global_tab_index = 0

        self.append_log(global_tab_index, message)
