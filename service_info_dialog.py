"""服务详情信息对话框"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QGridLayout, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
from service import DufsService, ServiceStatus


class ServiceInfoDialog(QDialog):
    """服务详情信息对话框（加强版，带生命周期管理）"""
    
    def __init__(self, parent=None, service: DufsService = None):
        super().__init__(parent)
        self.service = service
        self._is_closed = False  # 标记对话框是否已关闭
        self._setup_ui()
        self._fill_data()
    
    def closeEvent(self, event):
        """关闭事件处理（防止重复回调）"""
        self._is_closed = True
        event.accept()
    
    def reject(self):
        """拒绝对话框（重写以确保正确关闭）"""
        self._is_closed = True
        super().reject()
    
    def accept(self):
        """接受对话框（重写以确保正确关闭）"""
        self._is_closed = True
        super().accept()
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("服务详情")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setContentsMargins(15, 15, 15, 15)
        basic_layout.setSpacing(10)
        
        basic_layout.addWidget(QLabel("服务名称:"), 0, 0)
        self.name_label = QLabel()
        basic_layout.addWidget(self.name_label, 0, 1)
        
        basic_layout.addWidget(QLabel("服务路径:"), 1, 0)
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        basic_layout.addWidget(self.path_label, 1, 1)
        
        basic_layout.addWidget(QLabel("端口:"), 2, 0)
        self.port_label = QLabel()
        basic_layout.addWidget(self.port_label, 2, 1)
        
        basic_layout.addWidget(QLabel("绑定地址:"), 3, 0)
        self.bind_label = QLabel()
        basic_layout.addWidget(self.bind_label, 3, 1)
        
        basic_layout.addWidget(QLabel("服务状态:"), 4, 0)
        self.status_label = QLabel()
        basic_layout.addWidget(self.status_label, 4, 1)
        
        layout.addWidget(basic_group)
        
        # 权限信息组
        perm_group = QGroupBox("权限配置")
        perm_layout = QGridLayout(perm_group)
        perm_layout.setContentsMargins(15, 15, 15, 15)
        perm_layout.setSpacing(10)
        
        perm_layout.addWidget(QLabel("允许上传:"), 0, 0)
        self.upload_label = QLabel()
        perm_layout.addWidget(self.upload_label, 0, 1)
        
        perm_layout.addWidget(QLabel("允许删除:"), 1, 0)
        self.delete_label = QLabel()
        perm_layout.addWidget(self.delete_label, 1, 1)
        
        perm_layout.addWidget(QLabel("允许搜索:"), 2, 0)
        self.search_label = QLabel()
        perm_layout.addWidget(self.search_label, 2, 1)
        
        perm_layout.addWidget(QLabel("允许存档:"), 3, 0)
        self.archive_label = QLabel()
        perm_layout.addWidget(self.archive_label, 3, 1)
        
        perm_layout.addWidget(QLabel("允许所有操作:"), 4, 0)
        self.allow_all_label = QLabel()
        perm_layout.addWidget(self.allow_all_label, 4, 1)
        
        layout.addWidget(perm_group)
        
        # 认证信息组
        auth_group = QGroupBox("认证配置")
        auth_layout = QGridLayout(auth_group)
        auth_layout.setContentsMargins(15, 15, 15, 15)
        auth_layout.setSpacing(10)
        
        auth_layout.addWidget(QLabel("认证状态:"), 0, 0)
        self.auth_status_label = QLabel()
        auth_layout.addWidget(self.auth_status_label, 0, 1)
        
        auth_layout.addWidget(QLabel("用户名:"), 1, 0)
        self.auth_user_label = QLabel()
        auth_layout.addWidget(self.auth_user_label, 1, 1)
        
        layout.addWidget(auth_group)
        
        # 访问地址组
        if self.service and self.service.status == ServiceStatus.RUNNING:
            addr_group = QGroupBox("访问地址")
            addr_layout = QVBoxLayout(addr_group)
            addr_layout.setContentsMargins(15, 15, 15, 15)
            
            self.addr_text = QTextEdit()
            self.addr_text.setReadOnly(True)
            self.addr_text.setMaximumHeight(80)
            addr_layout.addWidget(self.addr_text)
            
            layout.addWidget(addr_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def _fill_data(self):
        """填充数据"""
        if not self.service:
            return
        
        # 基本信息
        self.name_label.setText(self.service.name)
        self.path_label.setText(self.service.serve_path)
        self.port_label.setText(self.service.port)
        self.bind_label.setText(self.service.bind if self.service.bind else "所有地址")
        self.status_label.setText(self.service.status)
        
        # 根据状态设置颜色
        if self.service.status == ServiceStatus.RUNNING:
            self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        elif self.service.status == ServiceStatus.ERROR:
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: #95a5a6;")
        
        # 权限信息
        self.upload_label.setText("是" if self.service.allow_upload else "否")
        self.delete_label.setText("是" if self.service.allow_delete else "否")
        self.search_label.setText("是" if self.service.allow_search else "否")
        self.archive_label.setText("是" if self.service.allow_archive else "否")
        self.allow_all_label.setText("是" if self.service.allow_all else "否")
        
        # 认证信息
        auth_user = getattr(self.service, 'auth_user', '')
        if auth_user:
            self.auth_status_label.setText("已启用")
            self.auth_status_label.setStyleSheet("color: #2ecc71;")
            self.auth_user_label.setText(auth_user)
        else:
            self.auth_status_label.setText("未启用")
            self.auth_status_label.setStyleSheet("color: #95a5a6;")
            self.auth_user_label.setText("-")
        
        # 访问地址
        if hasattr(self, 'addr_text') and self.service.local_addr:
            self.addr_text.setText(f"本地访问: {self.service.local_addr}")
