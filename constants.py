import os
import sys
from PyQt5.QtGui import QColor

# 应用程序常量
class AppConstants:
    """应用程序常量类"""
    MIN_WINDOW_WIDTH = 900
    MIN_WINDOW_HEIGHT = 600
    MAIN_LAYOUT_MARGINS = (20, 20, 20, 20)
    MAIN_LAYOUT_SPACING = 16

    # 状态颜色映射（用于表格状态显示）
    STATUS_COLORS = {
        'running': QColor('#10B981'),    # 绿色 - 运行中
        'stopped': QColor('#EF4444'),    # 红色 - 已停止
        'error': QColor('#F59E0B'),      # 橙色 - 错误
        'starting': QColor('#3B82F6'),   # 蓝色 - 启动中
        'stopping': QColor('#8B5CF6'),   # 紫色 - 停止中
        'pending': QColor('#6B7280'),    # 灰色 - 待定
    }

    # 状态文本映射
    STATUS_TEXTS = {
        'running': '运行中',
        'stopped': '已停止',
        'error': '错误',
        'starting': '启动中',
        'stopping': '停止中',
        'pending': '待定',
    }

    # 被浏览器阻止的端口
    BROWSER_BLOCKED_PORTS = {
        1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 77, 79,
        87, 95, 101, 102, 103, 104, 109, 110, 111, 113, 115, 117, 119, 123, 135,
        139, 143, 179, 389, 465, 512, 513, 514, 515, 526, 530, 531, 532, 540, 556,
        563, 587, 601, 636, 993, 995, 2049, 3659, 4045, 6000, 6665, 6666, 6667,
        6668, 6669
    }

    # 系统保留端口（1-1023）
    SYSTEM_RESERVED_PORTS = set(range(1, 1024)) - BROWSER_BLOCKED_PORTS

    # 服务启动等待时间（秒）
    SERVICE_START_WAIT_SECONDS = 2.0

    # 超时配置（秒）
    TIMEOUTS = {
        'process_terminate': 5.0,      # 进程终止超时
        'process_kill': 2.0,           # 进程强制终止超时
        'port_check': 1.0,             # 端口检查超时
        'service_stop_wait': 5.0,      # 服务停止等待超时
        'cloudflare_start': 30.0,      # Cloudflare启动超时
        'cleanup_wait': 10.0,          # 清理等待超时
    }

    # 重试配置
    RETRY_CONFIG = {
        'max_download_retries': 3,     # 下载最大重试次数
        'max_wait_iterations': 100,    # 最大等待迭代次数
        'wait_interval': 0.1,          # 等待间隔（秒）
    }

    # 端口配置
    PORT_CONFIG = {
        'min_port': 1,                 # 最小端口号
        'max_port': 65535,             # 最大端口号
        'system_reserved_max': 1023,   # 系统保留端口最大值
        'preferred_start': 5000,       # 首选起始端口
        'search_range': 50,            # 端口搜索范围
        'backup_start': 8000,          # 备用起始端口
        'backup_range': 100,           # 备用端口范围
    }

    # UI 颜色常量
    COLORS = {
        'primary': '#3B82F6',
        'primary_dark': '#2563EB',
        'success': '#10B981',
        'success_dark': '#059669',
        'danger': '#EF4444',
        'danger_dark': '#DC2626',
        'warning': '#F59E0B',
        'purple': '#8B5CF6',
        'text_primary': '#0F172A',
        'text_secondary': '#64748B',
        'text_muted': '#94A3B8',
        'border': '#E2E8F0',
        'border_hover': '#CBD5E1',
        'bg_white': '#FFFFFF',
        'bg_light': '#F8FAFC',
        'bg_hover': '#F1F5F9',
    }

    # 字体大小
    FONT_SIZES = {
        'small': '12px',
        'normal': '13px',
        'medium': '14px',
        'large': '15px',
        'xlarge': '16px',
        'title': '26px',
        'stat_value': '26px',
    }


class Theme:
    """统一主题系统 - 管理应用程序的颜色和样式"""
    
    # 主色调
    PRIMARY = "#3B82F6"
    PRIMARY_DARK = "#2563EB"
    PRIMARY_LIGHT = "#EFF6FF"
    
    # 辅助色
    SUCCESS = "#10B981"
    SUCCESS_DARK = "#059669"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"
    DANGER_DARK = "#DC2626"
    INFO = "#8B5CF6"
    INFO_DARK = "#7C3AED"
    
    # 中性色
    BACKGROUND = "#F8FAFC"
    SURFACE = "#FFFFFF"
    BORDER = "#E2E8F0"
    BORDER_HOVER = "#CBD5E1"
    TEXT_PRIMARY = "#1E293B"
    TEXT_SECONDARY = "#64748B"
    TEXT_MUTED = "#94A3B8"
    
    # 深色模式（预留）
    DARK_BACKGROUND = "#1E293B"
    DARK_SURFACE = "#334155"
    DARK_BORDER = "#475569"
    DARK_TEXT_PRIMARY = "#F1F5F9"
    DARK_TEXT_SECONDARY = "#94A3B8"
    
    @staticmethod
    def get_stylesheet(is_dark_mode: bool = False) -> str:
        """获取统一样式表
        
        Args:
            is_dark_mode: 是否使用深色模式
            
        Returns:
            str: QSS 样式表字符串
        """
        if is_dark_mode:
            bg = Theme.DARK_BACKGROUND
            surface = Theme.DARK_SURFACE
            border = Theme.DARK_BORDER
            text_primary = Theme.DARK_TEXT_PRIMARY
            text_secondary = Theme.DARK_TEXT_SECONDARY
        else:
            bg = Theme.BACKGROUND
            surface = Theme.SURFACE
            border = Theme.BORDER
            text_primary = Theme.TEXT_PRIMARY
            text_secondary = Theme.TEXT_SECONDARY
        
        return f"""
        * {{
            font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif;
            font-size: 10pt;
        }}
        QMainWindow, QDialog {{
            background-color: {bg};
        }}
        QWidget {{
            color: {text_primary};
        }}
        QLabel {{
            color: {text_primary};
        }}
        QLineEdit, QTextEdit, QComboBox {{
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px 10px;
            background-color: {surface};
            color: {text_primary};
            min-height: 20px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {Theme.PRIMARY};
        }}
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {Theme.PRIMARY}, stop:1 {Theme.PRIMARY_DARK});
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: 600;
            min-height: 28px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 #5F8FE7, stop:1 #4B7BDF);
        }}
        QPushButton:pressed {{
            background: {Theme.PRIMARY_DARK};
        }}
        QPushButton:disabled {{
            background: #CBD5E1;
            color: #94A3B8;
        }}
        QGroupBox {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #ffffff, stop:1 #fafbfc);
            border: 1px solid {border};
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 5px;
            font-weight: 600;
            color: {text_primary};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 2px 6px;
            background: white;
            border-radius: 4px;
            font-size: 12px;
            color: {text_secondary};
        }}
        QTableWidget {{
            border: none;
            background-color: transparent;
            outline: none;
            gridline-color: {border};
        }}
        QTableWidget::item {{
            padding: 10px 12px;
            border-bottom: 1px solid {border};
            font-size: 12px;
        }}
        QTableWidget::item:selected {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 {Theme.PRIMARY_LIGHT}, stop:1 #DBEAFE);
            color: {Theme.PRIMARY_DARK};
            border-radius: 6px;
        }}
        QHeaderView::section {{
            background-color: {surface};
            padding: 10px 12px;
            border: none;
            border-bottom: 2px solid {border};
            font-weight: 600;
            color: {text_secondary};
        }}
        QStatusBar {{
            background-color: {surface};
            border-top: 1px solid {border};
            font-size: 9pt;
            color: {text_secondary};
        }}
        """


class IconManager:
    """图标资源管理类 - 管理应用中使用的图标资源"""
    
    # 使用 emoji 作为默认图标，可替换为实际图标文件
    ICONS = {
        'start': '▶',
        'stop': '⏹',
        'public': '🌐',
        'info': 'ℹ',
        'log': '📋',
        'refresh': '🔄',
        'add': '➕',
        'edit': '✎',
        'delete': '🗑',
        'exit': '✕',
        'help': '❓',
        'copy': '📋',
        'open': '🔗',
        'settings': '⚙',
        'service': '📂',
        'folder': '📁',
        'globe': '🌍',
        'chart': '📊',
        'play': '▶',
        'square': '⏹',
    }
    
    @staticmethod
    def get_icon(name: str) -> str:
        """获取图标字符
        
        Args:
            name: 图标名称
            
        Returns:
            str: 图标字符
        """
        return IconManager.ICONS.get(name, '')
    
    @staticmethod
    def get_button_text(name: str, text: str) -> str:
        """获取带图标的按钮文本
        
        Args:
            name: 图标名称
            text: 按钮文本
            
        Returns:
            str: 带图标的按钮文本
        """
        icon = IconManager.ICONS.get(name, '')
        if icon:
            return f"{icon} {text}"
        return text


# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')


def get_lib_path() -> str:
    """获取库文件目录路径

    Returns:
        str: 库文件目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 开发环境路径
        base_dir = os.path.dirname(os.path.abspath(__file__))

    lib_dir = os.path.join(base_dir, 'lib')
    os.makedirs(lib_dir, exist_ok=True)
    return lib_dir


def get_resource_path(filename: str) -> str:
    """获取资源文件的绝对路径

    Args:
        filename: 资源文件名

    Returns:
        str: 资源文件的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 开发环境路径
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, filename)


# 对话框样式表（完整版）
DIALOG_STYLESHEET = """
QDialog {
    background-color: #F8FAFC;
}
QLabel {
    color: #1E293B;
    font-size: 13px;
}
QLineEdit, QComboBox {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 20px;
}
QLineEdit:focus, QComboBox:focus {
    border: 2px solid #3B82F6;
}
QLineEdit:read-only {
    background-color: #F1F5F9;
    color: #64748B;
}
QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #fafbfc);
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 5px;
    font-weight: 600;
    color: #1E293B;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 2px 6px;
    background: white;
    border-radius: 4px;
    font-size: 12px;
    color: #475569;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4F7FD7, stop:1 #3B6BCF);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
    min-width: 90px;
    min-height: 36px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #5F8FE7, stop:1 #4B7BDF);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #3F6FC7, stop:1 #2B5BBF);
}
QCheckBox {
    color: #1E293B;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #CBD5E1;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4F7FD7, stop:1 #3B6BCF);
    border-color: #3B6BCF;
}
"""

# 日志窗口样式表
LOG_WINDOW_STYLESHEET = """
QMainWindow {
    background-color: #F8FAFC;
}
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background: white;
}
QTabBar::tab {
    background: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 4px 10px;
    margin-right: 2px;
    color: #64748B;
    font-weight: 500;
    font-size: 11px;
}
QTabBar::tab:selected {
    background: white;
    color: #3B82F6;
    border-bottom: 2px solid #3B82F6;
}
QTabBar::tab:hover:!selected {
    background: #E2E8F0;
    color: #475569;
}
QPlainTextEdit {
    background-color: #1E293B;
    color: #E2E8F0;
    border: none;
    border-radius: 0 0 8px 8px;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    selection-background-color: #3B82F6;
}
"""


# 全局样式表配置
GLOBAL_STYLESHEET = """
/* ===== 全局基础设置 ===== */
* {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 13px;
    outline: none;
}

QWidget {
    background-color: #F8FAFC;
    color: #1E293B;
}

/* ===== 卡片式容器设计 - 增强阴影 ===== */
QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #fafbfc);
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    margin-top: 20px;
    padding-top: 18px;
    font-weight: 600;
    color: #1E293B;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 18px;
    padding: 0 10px;
    background: white;
    border-radius: 4px;
    font-size: 14px;
    color: #475569;
}

/* ===== 按钮系统（含交互反馈） ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4F7FD7, stop:1 #3B6BCF);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    min-width: 80px;
    min-height: 28px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #5F8FE7, stop:1 #4B7BDF);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #3F6FC7, stop:1 #2B5BBF);
}

QPushButton:disabled {
    background: #CBD5E1;
    color: #94A3B8;
}

/* 语义化按钮 */
QPushButton#StartBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
    min-height: 28px;
    padding: 6px 14px;
}
QPushButton#StartBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22C989, stop:0 #14A979);
}
QPushButton#StopBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF4444, stop:1 #DC2626);
    min-height: 28px;
    padding: 6px 14px;
}
QPushButton#StopBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF5554, stop:0 #F03636);
}
QPushButton#PublicBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8B5CF6, stop:1 #7C3AED);
    min-height: 28px;
    padding: 6px 14px;
}
QPushButton#PublicBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9B6CF6, stop:0 #8C4AED);
}
QPushButton#InfoBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64748B, stop:1 #475569);
    min-height: 28px;
    padding: 6px 14px;
}
QPushButton#InfoBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #74859B, stop:0 #586579);
}

/* 工具栏按钮样式 */
QPushButton#ToolBtn {
    background: #F8FAFC;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 5px;
    padding: 4px 10px;
    font-weight: 500;
    min-height: 24px;
    max-height: 28px;
    font-size: 11px;
}
QPushButton#ToolBtn:hover {
    background: #F1F5F9;
    border-color: #CBD5E1;
}

QPushButton#ToolBtnGreen {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
    color: white;
    border: none;
    border-radius: 5px;
    padding: 4px 10px;
    font-weight: 600;
    min-height: 24px;
    max-height: 28px;
    font-size: 11px;
}
QPushButton#ToolBtnGreen:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22C989, stop:1 #14A979);
}

QPushButton#ToolBtnBlue {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3B82F6, stop:1 #2563EB);
    color: white;
    border: none;
    border-radius: 5px;
    padding: 4px 10px;
    font-weight: 600;
    min-height: 24px;
    max-height: 28px;
    font-size: 11px;
}
QPushButton#ToolBtnBlue:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4B92F6, stop:1 #3573EB);
}

QPushButton#ToolBtnRed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF4444, stop:1 #DC2626);
    color: white;
    border: none;
    border-radius: 5px;
    padding: 4px 10px;
    font-weight: 600;
    min-height: 24px;
    max-height: 28px;
    font-size: 11px;
}
QPushButton#ToolBtnRed:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF5544, stop:0 #EC3636);
}

QPushButton#SmallBtn {
    background: #F8FAFC;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: 500;
    min-height: 20px;
    max-height: 22px;
}
QPushButton#SmallBtn:hover {
    background: #F1F5F9;
    border-color: #CBD5E1;
}

/* ===== 主要操作按钮 ===== */
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3B82F6, stop:1 #2563EB);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-weight: 700;
    font-size: 14px;
    min-height: 44px;
}
QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1D4ED8);
}
QPushButton#PrimaryBtn:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D4ED8, stop:1 #1E40AF);
}

/* 服务控制按钮 - 增强视觉 */
QPushButton#ActionBtnGreen,
QPushButton#ActionBtnBlue,
QPushButton#ActionBtnRed {
    border: none;
    border-radius: 5px;
    padding: 4px 10px;
    font-weight: 600;
    font-size: 11px;
    min-height: 24px;
    max-height: 28px;
}

QPushButton#ActionBtnGreen {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669);
    color: white;
}
QPushButton#ActionBtnGreen:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22C989, stop:1 #14A979);
}

QPushButton#ActionBtnBlue {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3B82F6, stop:1 #2563EB);
    color: white;
}
QPushButton#ActionBtnBlue:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4B92F6, stop:1 #3573EB);
}

QPushButton#ActionBtnRed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF4444, stop:1 #DC2626);
    color: white;
}
QPushButton#ActionBtnRed:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF5544, stop:0 #EC3636);
}

/* ===== 输入框优化 - 添加焦点动画 ===== */
QLineEdit {
    background: white;
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 10px 14px;
    selection-background-color: #4F7FD7;
    selection-color: white;
    min-height: 34px;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #4F7FD7;
    border-width: 2px;
}

QLineEdit:read-only {
    background-color: #F8FAFC;
    color: #64748B;
    border-color: #E2E8F0;
}

QLineEdit:hover:!read-only {
    border-color: #CBD5E1;
}

/* ===== 表格现代化 - 优化行高和选中态 ===== */
QTableWidget {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    gridline-color: #F1F5F9;
    alternate-background-color: #FAFBFC;
    outline: none;
}

QTableWidget::item {
    padding: 12px 14px;
    border-bottom: 1px solid #F1F5F9;
}

QTableWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #EFF6FF, stop:1 #DBEAFE);
    color: #1E40AF;
    border-radius: 6px;
}

QTableWidget::item:!selected:hover {
    background-color: #F8FAFC;
    border-radius: 6px;
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #FAFBFC, stop:1 #F1F5F9);
    color: #475569;
    padding: 14px 12px;
    border: none;
    border-bottom: 2px solid #E2E8F0;
    font-weight: 700;
    font-size: 13px;
}

QHeaderView::section:first {
    border-top-left-radius: 12px;
}

QHeaderView::section:last {
    border-top-right-radius: 12px;
}

/* ===== 状态栏 ===== */
QStatusBar {
    background: white;
    border-top: 1px solid #E2E8F0;
    color: #64748B;
    padding: 6px 12px;
    font-size: 12px;
}

QStatusBar QLabel {
    padding: 4px 12px;
    border-radius: 6px;
    background: #F1F5F9;
    margin: 0 4px;
}

QStatusBar QLabel#RunningCount {
    background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
    color: #065F46;
    font-weight: 600;
}

/* ===== 复选框优化 ===== */
QCheckBox {
    color: #1E293B;
    font-size: 13px;
    spacing: 10px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid #CBD5E1;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #4F7FD7;
    background-color: #F8FAFC;
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4F7FD7, stop:1 #3B6BCF);
    border-color: #3B6BCF;
    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-check.png);
}

/* ===== 滚动条美化 ===== */
QScrollBar:vertical {
    background: #F1F5F9;
    width: 12px;
    border-radius: 6px;
    margin: 4px 0;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 6px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

QScrollBar:horizontal {
    background: #F1F5F9;
    height: 12px;
    border-radius: 6px;
    margin: 0 4px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 6px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}

/* ===== 菜单样式 ===== */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 6px;
}

QMenu::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EFF6FF, stop:1 #DBEAFE);
    color: #1E40AF;
}

/* ===== 消息框样式 ===== */
QMessageBox {
    background-color: #FFFFFF;
}

QMessageBox QPushButton {
    min-width: 90px;
    padding: 8px 20px;
    border-radius: 8px;
    font-weight: 600;
}
"""


