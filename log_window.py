"""日志窗口文件"""

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QComboBox, QTabWidget, QPlainTextEdit
)

# 仅在类型检查时导入，避免运行时依赖问题
if TYPE_CHECKING:
    from PyQt5.QtWidgets import (
        QLineEdit, QComboBox, QTabWidget, QPlainTextEdit
    )


class LogWindow(QMainWindow):
    """独立日志窗口，用于显示服务日志"""

    # 类型注解
    search_edit: 'QLineEdit'
    filter_combo: 'QComboBox'
    log_tabs: 'QTabWidget'
    original_logs: dict[int, list[str]]

    def __init__(self, parent: 'QWidget | None' = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dufs 日志窗口")
        self.setMinimumSize(800, 600)
        
        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加日志过滤和搜索控件
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索日志...")  # type: ignore[attr-defined]
        self.search_edit.textChanged.connect(self._on_search_text_changed)  # type: ignore[attr-defined]
        filter_layout.addWidget(self.search_edit)  # type: ignore[arg-type]
        
        # 搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._on_search_clicked)  # type: ignore
        filter_layout.addWidget(search_btn)
        
        # 过滤选项
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "错误", "信息"])  # type: ignore
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)  # type: ignore
        filter_layout.addWidget(self.filter_combo)
        
        main_layout.addLayout(filter_layout)
        
        # 创建日志Tab容器
        self.log_tabs = QTabWidget()
        self.log_tabs.setTabsClosable(True)  # type: ignore
        self.log_tabs.currentChanged.connect(self._on_tab_changed)  # type: ignore
        main_layout.addWidget(self.log_tabs)
        
        # 保存原始日志内容的字典，用于搜索和过滤
        self.original_logs = {}  # 键为tab索引，值为原始日志内容
    
    def add_log_tab(self, service_name: str, log_widget: QPlainTextEdit) -> None:
        """添加日志标签页"""
        index = self.log_tabs.count()
        self.log_tabs.addTab(log_widget, service_name)
        
        # 初始化原始日志内容
        self.original_logs[index] = []
        
        # 将当前日志控件的内容添加到原始日志
        current_logs = log_widget.toPlainText().split('\n')
        if current_logs and current_logs[0]:  # 避免添加空行
            self.original_logs[index].extend(current_logs)
    
    def update_log_tab_title(self, index: int, title: str) -> None:
        """更新日志标签页标题"""
        if 0 <= index < self.log_tabs.count():
            self.log_tabs.setTabText(index, title)
    
    def remove_log_tab(self, index: int) -> None:
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
    
    def _on_search_text_changed(self, text: str) -> None:
        """搜索文本变化时的处理"""
        self._apply_filter()
    
    def _on_search_clicked(self) -> None:
        """搜索按钮点击时的处理"""
        self._apply_filter()
    
    def _on_filter_changed(self, text: str) -> None:
        """过滤选项变化时的处理"""
        self._apply_filter()
    
    def _on_clear_clicked(self) -> None:
        """清除搜索和过滤"""
        self.search_edit.clear()
        self.filter_combo.setCurrentIndex(0)
        self._apply_filter()
    
    def _on_tab_changed(self, index: int) -> None:
        """切换标签页时的处理"""
        self._apply_filter()
    
    def _apply_filter(self) -> None:
        """应用搜索和过滤条件"""
        current_index = self.log_tabs.currentIndex()  # type: ignore
        if current_index == -1:
            return
        
        log_widget = self.log_tabs.currentWidget()  # type: ignore
        if not log_widget:
            return
        
        # 获取当前标签页的原始日志
        if current_index not in self.original_logs:
            return
        
        search_text = self.search_edit.text().lower()  # type: ignore
        filter_level = self.filter_combo.currentText()  # type: ignore
        
        # 保存当前滚动位置
        scroll_bar = log_widget.verticalScrollBar()  # type: ignore
        scroll_position = scroll_bar.value()  # type: ignore
        is_scrolled_to_bottom = scroll_bar.value() == scroll_bar.maximum()  # type: ignore
        
        # 清空当前日志
        log_widget.clear()  # type: ignore
        
        # 应用过滤
        for line in self.original_logs[current_index]:
            show_line = True
            
            # 搜索过滤
            if search_text and search_text not in line.lower():
                show_line = False
            
            # 级别过滤
            if filter_level == "错误" and "[ERROR]" not in line:
                show_line = False
            elif filter_level == "信息" and "[INFO]" not in line:
                show_line = False
            
            if show_line:
                log_widget.appendPlainText(line)  # type: ignore
        
        # 恢复滚动位置
        if is_scrolled_to_bottom:
            # 避免使用ensureCursorVisible()，直接设置滚动条到最大值
            scroll_bar = log_widget.verticalScrollBar()  # type: ignore
            scroll_bar.setValue(scroll_bar.maximum())  # type: ignore
        else:
            scroll_bar.setValue(scroll_position)  # type: ignore
    
    def append_log(self, index: int, message: str) -> None:
        """添加日志条目，同时保存到原始日志"""
        if index < 0 or index >= self.log_tabs.count():  # type: ignore
            return
        
        log_widget = self.log_tabs.widget(index)  # type: ignore
        if not log_widget:
            return
        
        # 保存到原始日志
        if index not in self.original_logs:
            self.original_logs[index] = []
        self.original_logs[index].append(message)
        
        # 应用过滤后显示
        search_text = self.search_edit.text().lower()  # type: ignore
        filter_level = self.filter_combo.currentText()  # type: ignore
        
        show_line = True
        if search_text and search_text not in message.lower():
            show_line = False
        
        if filter_level == "错误" and "[ERROR]" not in message:
            show_line = False
        elif filter_level == "信息" and "[INFO]" not in message:
            show_line = False
        
        if show_line:
            log_widget.appendPlainText(message)  # type: ignore
    
    def add_log(self, message: str, error: bool = False) -> None:
        """添加日志条目到默认标签页"""
        # 直接调用 _add_log_ui 方法，确保在UI线程中执行
        self._add_log_ui(message, error)
    
    def _add_log_ui(self, message: str, error: bool = False) -> None:
        """在UI线程中添加日志条目"""
        # 添加到当前活动的标签页，如果没有则创建默认标签页
        if self.log_tabs.count() == 0:
            # 创建默认日志标签页
            default_widget = QPlainTextEdit()
            default_widget.setReadOnly(True)
            default_widget.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11px;")
            self.add_log_tab("日志", default_widget)
        
        # 添加到当前活动的标签页
        current_index = self.log_tabs.currentIndex()
        if current_index >= 0:
            self.append_log(current_index, message)
