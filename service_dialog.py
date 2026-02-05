"""服务配置对话框文件"""
# pyright: reportUnannotatedClassAttribute=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnusedCallResult=false

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QGroupBox, QGridLayout, QCheckBox, QFileDialog, 
    QMessageBox
)
from PyQt5.QtCore import Qt
from service import DufsService

# 对话框样式表 - 现代化设计
DIALOG_STYLESHEET = """
/* 现代化对话框样式 */
QDialog {
    background-color: #f8f9fa;
    font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
}

/* 分组框样式 - 圆角卡片设计 */
QGroupBox {
    font-weight: 600;
    font-size: 14px;
    color: #2c3e50;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 15px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}

/* 按钮样式 - 圆角设计 */
QPushButton {
    background-color: #4a6fa5;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 500;
    min-width: 80px;
    min-height: 30px;
}

QPushButton:hover {
    background-color: #3a5a8a;
}

QPushButton:pressed {
    background-color: #2a4a7a;
}

/* 取消按钮使用中性色 */
QPushButton#CancelBtn {
    background-color: #6c757d;
}
QPushButton#CancelBtn:hover {
    background-color: #5a6268;
}

/* 操作按钮 - 主要操作使用强调色 */
QPushButton#ActionBtn {
    background-color: #007bff;
}
QPushButton#ActionBtn:hover {
    background-color: #0069d9;
}

/* 操作按钮 - 危险操作使用警示色 */
QPushButton#DangerBtn {
    background-color: #dc3545;
}
QPushButton#DangerBtn:hover {
    background-color: #c82333;
}

/* 输入框样式 - 现代化设计 */
QLineEdit {
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 6px 10px;
    background-color: #ffffff;
    selection-background-color: #4a6fa5;
    selection-color: white;
    min-height: 28px;
}

QLineEdit:focus {
    border-color: #4a6fa5;
}

/* 验证失败的输入框 */
QLineEdit[validation="failed"] {
    border-color: #dc3545;
    background-color: #fff5f5;
}

QLineEdit[validation="failed"]::placeholder {
    color: #dc3545;
}

/* 标签样式 */
QLabel {
    color: #495057;
    font-size: 13px;
}

QLabel#Required {
    color: #dc3545;
    font-weight: 500;
}

/* 复选框样式 - 现代化 */
QCheckBox {
    spacing: 8px;
    font-size: 13px;
    color: #2c3e50;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #adb5bd;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #4a6fa5;
}

QCheckBox::indicator:checked {
    background-color: #4a6fa5;
    border-color: #4a6fa5;
    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-check.png);
}

QCheckBox::indicator:checked:hover {
    background-color: #3a5a8a;
    border-color: #3a5a8a;
}

/* 提示文本 */
QLabel#TipLabel {
    color: #6c757d;
    font-size: 12px;
    font-style: italic;
    margin-top: 4px;
}
"""



class DufsServiceDialog(QDialog):
    """服务配置对话框"""
    
    def __init__(self, parent: QDialog | None = None, service: DufsService | None = None, edit_index: int | None = None, existing_services: list[DufsService] | None = None):
        super().__init__(parent)
        # 应用对话框样式表
        self.setStyleSheet(DIALOG_STYLESHEET)
        
        self.setWindowTitle("服务配置")
        self.setMinimumSize(750, 550)
        # 去掉标题栏的问号按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 初始化属性
        self.service: DufsService = service or DufsService()
        self.edit_index: int | None = edit_index
        self.existing_services: list[DufsService] = existing_services or []
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 添加基本配置组
        self._add_basic_config(main_layout)
        
        # 添加权限配置组
        self._add_permission_config(main_layout)
        
        # 添加账户认证配置组
        self._add_auth_config(main_layout)
        
        # 添加按钮组
        self._add_buttons(main_layout)
        
        # 填充现有数据
        self._fill_existing_data()
        
        # 标记对话框是否已关闭，防止重复回调
        self._is_closed = False
    
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
    
    def _add_basic_config(self, layout: QVBoxLayout) -> None:
        """添加基本配置组"""
        basic_group = QGroupBox("基本配置")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setContentsMargins(15, 15, 15, 15)
        basic_layout.setSpacing(10)
        
        # 服务名称
        basic_layout.addWidget(QLabel("服务名称:"), 0, 0)
        self.name_edit: QLineEdit = QLineEdit()
        basic_layout.addWidget(self.name_edit, 0, 1)
        
        # 服务路径
        basic_layout.addWidget(QLabel("服务路径:"), 1, 0)
        path_layout = QHBoxLayout()
        self.path_edit: QLineEdit = QLineEdit()
        path_layout.addWidget(self.path_edit)
        browse_btn = QPushButton("浏览")
        _ = browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        basic_layout.addLayout(path_layout, 1, 1)
        
        # 端口
        basic_layout.addWidget(QLabel("端口:"), 2, 0)
        self.port_edit: QLineEdit = QLineEdit()
        basic_layout.addWidget(self.port_edit, 2, 1)
        
        # 绑定地址
        basic_layout.addWidget(QLabel("绑定地址:"), 3, 0)
        self.bind_edit: QLineEdit = QLineEdit()
        self.bind_edit.setPlaceholderText("留空表示绑定所有地址")
        basic_layout.addWidget(self.bind_edit, 3, 1)
        
        # 将basic_group添加到传入的layout中
        layout.addWidget(basic_group)
    
    def _add_permission_config(self, layout: QVBoxLayout) -> None:
        """添加权限配置组"""
        perm_group = QGroupBox("权限配置")
        perm_layout = QHBoxLayout(perm_group)
        perm_layout.setContentsMargins(15, 15, 15, 15)
        perm_layout.setSpacing(20)

        # 允许上传
        self.upload_check: QCheckBox = QCheckBox("允许上传")
        perm_layout.addWidget(self.upload_check)

        # 允许删除
        self.delete_check: QCheckBox = QCheckBox("允许删除")
        perm_layout.addWidget(self.delete_check)

        # 允许搜索
        self.search_check: QCheckBox = QCheckBox("允许搜索")
        self.search_check.setChecked(True)
        perm_layout.addWidget(self.search_check)

        # 允许存档
        self.archive_check: QCheckBox = QCheckBox("允许存档")
        self.archive_check.setChecked(True)
        perm_layout.addWidget(self.archive_check)

        # 允许所有操作
        self.allow_all_check: QCheckBox = QCheckBox("允许所有操作")
        perm_layout.addWidget(self.allow_all_check)

        perm_layout.addStretch()

        # 将perm_group添加到传入的layout中
        layout.addWidget(perm_group)
    
    def _add_auth_config(self, layout: QVBoxLayout) -> None:
        """添加账户认证配置组"""
        auth_group = QGroupBox("账户认证（可选）")
        auth_layout = QGridLayout(auth_group)
        auth_layout.setContentsMargins(15, 15, 15, 15)
        auth_layout.setSpacing(10)

        # 用户名
        auth_layout.addWidget(QLabel("用户名:"), 0, 0)
        self.auth_user_edit: QLineEdit = QLineEdit()
        self.auth_user_edit.setPlaceholderText("留空表示无需认证")
        auth_layout.addWidget(self.auth_user_edit, 0, 1)

        # 密码
        auth_layout.addWidget(QLabel("密码:"), 1, 0)
        self.auth_pass_edit: QLineEdit = QLineEdit()
        self.auth_pass_edit.setPlaceholderText("留空表示无需认证")
        self.auth_pass_edit.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(self.auth_pass_edit, 1, 1)

        # 将auth_group添加到传入的layout中
        layout.addWidget(auth_group)
    
    def _add_buttons(self, layout: QVBoxLayout) -> None:
        """添加按钮组"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        _ = cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        _ = ok_btn.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def _fill_existing_data(self) -> None:
        """填充现有数据"""
        if self.service:
            self.name_edit.setText(self.service.name)
            self.path_edit.setText(self.service.serve_path)
            self.port_edit.setText(self.service.port)
            self.bind_edit.setText(self.service.bind)
            
            # 添加路径验证提示
            if not os.path.exists(self.service.serve_path):
                self.path_edit.setStyleSheet("border: 1px solid #e74c3c;")
                self.path_edit.setToolTip("服务路径不存在")
            else:
                self.path_edit.setStyleSheet("")
                self.path_edit.setToolTip("")
            
            # 填充权限配置
            self.upload_check.setChecked(self.service.allow_upload)
            self.delete_check.setChecked(self.service.allow_delete)
            self.search_check.setChecked(self.service.allow_search)
            self.archive_check.setChecked(self.service.allow_archive)
            self.allow_all_check.setChecked(self.service.allow_all)
            
            # 填充认证配置
            if hasattr(self.service, 'auth_user'):
                self.auth_user_edit.setText(self.service.auth_user)
            if hasattr(self.service, 'auth_pass'):
                self.auth_pass_edit.setText(self.service.auth_pass)
    
    def _browse_path(self) -> None:
        """浏览路径"""
        path = QFileDialog.getExistingDirectory(self, "选择服务路径")
        if path:
            self.path_edit.setText(path)
    
    def _validate_service_path(self, path: str) -> tuple[bool, str]:
        """验证服务路径的安全性

        Args:
            path: 路径字符串

        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        # 路径规范化
        normalized_path = os.path.normpath(path)
        absolute_path = os.path.abspath(normalized_path)

        # 检查路径是否存在
        if not os.path.exists(absolute_path):
            return False, f"路径 '{path}' 不存在"

        # 检查是否为目录
        if not os.path.isdir(absolute_path):
            return False, f"路径 '{path}' 不是有效目录"

        # 防止路径遍历攻击
        if ".." in normalized_path:
            return False, "路径包含非法字符 '.."

        return True, ""

    def _on_ok_clicked(self) -> None:
        """确定按钮点击事件（加强版，带安全验证）"""
        # 验证输入
        if not self.name_edit.text():
            QMessageBox.critical(self, "错误", "服务名称不能为空")
            return

        if not self.path_edit.text():
            QMessageBox.critical(self, "错误", "服务路径不能为空")
            return

        if not self.port_edit.text():
            QMessageBox.critical(self, "错误", "端口不能为空")
            return

        # 验证端口是否为数字
        try:
            port = int(self.port_edit.text())
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "错误", "请输入有效的端口号（1-65535）")
            return

        # 验证服务路径（安全验证）
        path = self.path_edit.text()
        is_valid, error_msg = self._validate_service_path(path)
        if not is_valid:
            QMessageBox.critical(self, "错误", error_msg)
            return

        # 更新服务（名称重复检查由主窗口处理）
        self.service.name = self.name_edit.text()
        self.service.serve_path = os.path.abspath(os.path.normpath(path))
        self.service.port = self.port_edit.text()
        self.service.bind = self.bind_edit.text()

        # 更新权限配置
        self.service.allow_upload = self.upload_check.isChecked()
        self.service.allow_delete = self.delete_check.isChecked()
        self.service.allow_search = self.search_check.isChecked()
        self.service.allow_archive = self.archive_check.isChecked()
        self.service.allow_all = self.allow_all_check.isChecked()

        # 更新认证配置
        self.service.auth_user = self.auth_user_edit.text()
        # 注意：密码以明文存储，实际生产环境应考虑加密
        self.service.auth_pass = self.auth_pass_edit.text()

        # 接受对话框
        self.accept()
