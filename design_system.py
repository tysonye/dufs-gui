"""设计系统 - 统一界面风格"""

from PyQt5.QtWidgets import QPushButton, QLabel
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve


class DesignSystem:
    """设计系统 - 统一管理界面样式"""
    
    # 色彩系统（语义化命名）
    COLORS = {
        'primary': '#4a6fa5',
        'primary_dark': '#3a5a8a',
        'primary_light': '#5a7fb5',
        'success': '#28a745',
        'success_dark': '#218838',
        'warning': '#ffc107',
        'danger': '#dc3545',
        'danger_dark': '#c82333',
        'info': '#17a2b8',
        'info_dark': '#138496',
        'text_primary': '#2c3e50',
        'text_secondary': '#6c757d',
        'text_muted': '#95a5a6',
        'border': '#e1e5eb',
        'surface': '#ffffff',
        'background': '#f5f7fa',
        'hover_bg': '#e8f4fd'
    }
    
    # 间距系统（8px基准）
    SPACING = {
        'xs': 4, 'sm': 8, 'md': 16, 'lg': 24, 'xl': 32
    }
    
    # 圆角系统
    RADIUS = {
        'sm': 4, 'md': 6, 'lg': 8, 'xl': 12
    }
    
    # 阴影系统
    SHADOWS = {
        'sm': '0 1px 3px rgba(0,0,0,0.08)',
        'md': '0 2px 8px rgba(0,0,0,0.1)',
        'lg': '0 4px 12px rgba(0,0,0,0.12)'
    }
    
    # 字体系统
    FONTS = {
        'family': '"Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif',
        'size_sm': '11px',
        'size_md': '13px',
        'size_lg': '14px',
        'size_xl': '16px'
    }
    
    @staticmethod
    def get_button_style(variant='primary', size='md'):
        """动态生成按钮样式"""
        color = DesignSystem.COLORS.get(variant, DesignSystem.COLORS['primary'])
        color_dark = DesignSystem.COLORS.get(f'{variant}_dark', color)
        radius = DesignSystem.RADIUS.get(size, 6)
        padding_v = DesignSystem.SPACING.get(size, 16) - 2
        padding_h = DesignSystem.SPACING['lg']
        
        btn_id = f"{variant.capitalize()}Btn"
        color_light = DesignSystem.COLORS.get(f'{variant}_light', color)
        darker_color = DesignSystem._darken_color(color_dark)
        
        return f"""
        QPushButton#{btn_id} {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {color}, stop:1 {color_dark});
            color: white;
            border: none;
            border-radius: {radius}px;
            padding: {padding_v}px {padding_h}px;
            font-weight: 500;
            min-height: 32px;
            min-width: 85px;
        }}
        QPushButton#{btn_id}:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {color_light}, stop:1 {color});
        }}
        QPushButton#{btn_id}:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {color_dark}, stop:1 {darker_color});
        }}
        QPushButton#{btn_id}:disabled {{
            background: #c5c9d1;
            color: #a0a5b0;
        }}
        """
    
    @staticmethod
    def _darken_color(hex_color):
        """将颜色变暗"""
        hex_color = hex_color.lstrip('#')
        r = max(0, int(hex_color[0:2], 16) - 20)
        g = max(0, int(hex_color[2:4], 16) - 20)
        b = max(0, int(hex_color[4:6], 16) - 20)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    @staticmethod
    def get_global_stylesheet():
        """获取全局样式表"""
        c = DesignSystem.COLORS
        r = DesignSystem.RADIUS
        f = DesignSystem.FONTS
        
        return f"""
        /* 全局基础设置 */
        * {{
            font-family: {f['family']};
            font-size: {f['size_md']};
            outline: none;
        }}
        
        QWidget {{
            background-color: {c['background']};
            color: {c['text_primary']};
        }}
        
        /* 卡片式容器 */
        QGroupBox {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['surface']}, stop:1 #fafbfc);
            border: 1px solid {c['border']};
            border-radius: {r['xl']}px;
            margin-top: 18px;
            padding-top: 15px;
            font-weight: 600;
            color: {c['text_primary']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px;
            background: {c['surface']};
            border-radius: {r['sm']}px;
            font-size: {f['size_lg']};
        }}
        
        /* 输入框 */
        QLineEdit {{
            background: {c['surface']};
            border: 1px solid #d1d9e6;
            border-radius: {r['md']}px;
            padding: 8px 12px;
            selection-background-color: {c['primary']};
            selection-color: white;
            min-height: 30px;
        }}
        
        QLineEdit:focus {{
            border-color: {c['primary']};
            border-width: 1.5px;
        }}
        
        QLineEdit:read-only {{
            background-color: #f8f9fc;
            color: {c['text_secondary']};
        }}

        /* 按钮 */
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['primary']}, stop:1 {c['primary_dark']});
            color: white;
            border: none;
            border-radius: {r['md']}px;
            padding: 8px 16px;
            font-weight: 500;
            min-width: 85px;
            min-height: 32px;
        }}

        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['primary_light']}, stop:1 {c['primary']});
        }}

        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['primary_dark']}, stop:1 {DesignSystem._darken_color(c['primary_dark'])});
        }}

        QPushButton:disabled {{
            background: #c5c9d1;
            color: #a0a5b0;
        }}

        /* 语义化按钮 */
        QPushButton#StartBtn {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['success']}, stop:1 {c['success_dark']});
        }}
        QPushButton#StartBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2dc94e, stop:1 #259d3d);
        }}

        QPushButton#StopBtn {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['danger']}, stop:1 {c['danger_dark']});
        }}
        QPushButton#StopBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e44c58, stop:1 #d33545);
        }}

        QPushButton#PublicBtn {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['info']}, stop:1 {c['info_dark']});
        }}
        QPushButton#PublicBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1abcce, stop:1 #169ab9);
        }}

        QPushButton#InfoBtn {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6c757d, stop:1 #5a6268);
        }}
        QPushButton#InfoBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #7c858d, stop:1 #6a7278);
        }}

        /* 表格 */
        QTableWidget {{
            background: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: {r['lg']}px;
            gridline-color: #f0f2f5;
            alternate-background-color: #fafbfc;
            outline: none;
        }}
        
        QTableWidget::item {{
            padding: 8px 10px;
            border-bottom: 1px solid #f0f2f5;
        }}
        
        QTableWidget::item:selected {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['primary']}, stop:1 {c['primary_dark']});
            color: white;
            border-radius: {r['sm']}px;
        }}
        
        QTableWidget::item:!selected:hover {{
            background-color: {c['hover_bg']};
            border-radius: {r['sm']}px;
        }}
        
        QHeaderView::section {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f8f9fc, stop:1 #f0f2f5);
            color: #495057;
            padding: 10px 8px;
            border: none;
            border-bottom: 2px solid {c['border']};
            font-weight: 600;
            font-size: {f['size_md']};
        }}
        
        QHeaderView::section:first {{
            border-top-left-radius: {r['lg']}px;
        }}
        
        QHeaderView::section:last {{
            border-top-right-radius: {r['lg']}px;
        }}
        
        /* 状态栏 */
        QStatusBar {{
            background: {c['surface']};
            border-top: 1px solid {c['border']};
            color: {c['text_secondary']};
            padding: 4px 10px;
            font-size: {f['size_sm']};
        }}
        
        QStatusBar QLabel {{
            padding: 3px 10px;
            border-radius: {r['sm']}px;
            background: #f0f2f5;
            margin: 0 3px;
        }}
        
        /* 复选框 */
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {r['sm']}px;
            border: 1.5px solid #adb5bd;
            background: {c['surface']};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {c['primary']};
        }}
        
        QCheckBox::indicator:checked {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c['primary']}, stop:1 {c['primary_dark']});
            border-color: {c['primary_dark']};
        }}
        
        /* 滚动条 */
        QScrollBar:vertical {{
            background: #f0f2f5;
            width: 10px;
            border-radius: 5px;
            margin: 2px 0;
        }}
        
        QScrollBar::handle:vertical {{
            background: #c5c9d1;
            border-radius: 5px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: #a0a5b0;
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            background: none;
        }}
        
        /* 菜单 */
        QMenu {{
            background-color: {c['surface']};
            border: 1px solid #E0E0E0;
            border-radius: {r['sm']}px;
            padding: 5px;
        }}
        
        QMenu::item {{
            padding: 6px 20px;
            border-radius: 3px;
        }}
        
        QMenu::item:selected {{
            background-color: {c['primary']};
            color: white;
        }}
        """


class AnimatedButton(QPushButton):
    """带动画效果的按钮"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._original_geometry = None
        
    def mousePressEvent(self, event):
        """按下时轻微下沉"""
        self._original_geometry = self.geometry()
        # 创建下沉效果
        new_geometry = self._original_geometry.adjusted(0, 1, 0, 1)
        self.setGeometry(new_geometry)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """释放时弹性回弹"""
        if self._original_geometry:
            self._animation.setStartValue(self.geometry())
            self._animation.setEndValue(self._original_geometry)
            self._animation.start()
        super().mouseReleaseEvent(event)


class StatusBadge(QLabel):
    """状态徽章组件"""
    
    STYLES = {
        # 英文 key（用于公网访问状态）
        'running': ('#28a745', '●', '运行中'),
        'starting': ('#ffc107', '◐', '启动中'),
        'stopped': ('#6c757d', '○', '已停止'),
        'stopping': ('#9b59b6', '◑', '停止中'),
        'error': ('#dc3545', '✕', '错误'),
        # 中文 key（用于服务状态）
        '运行中': ('#28a745', '●', '运行中'),
        '启动中': ('#ffc107', '◐', '启动中'),
        '停止中': ('#9b59b6', '◑', '停止中'),
        '已停止': ('#6c757d', '○', '已停止'),
        '错误': ('#dc3545', '✕', '错误')
    }
    
    def __init__(self, status='stopped', parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        # 设置尺寸策略以适应单元格
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setContentsMargins(4, 2, 4, 2)
        self.update_status(status)

    def update_status(self, status):
        """更新状态显示"""
        color, icon, text = self.STYLES.get(status, self.STYLES['stopped'])
        self.setText(f"{icon} {text}")
        # 使用纯色背景配白色文字，确保清晰可见
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                padding: 4px 10px;
                font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif;
                font-weight: bold;
                font-size: 11px;
                min-width: 70px;
                min-height: 18px;
                qproperty-alignment: AlignCenter;
            }}
        """)
        self.setProperty('status', status)
