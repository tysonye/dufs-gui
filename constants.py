"""常量定义文件"""
import hashlib
import os


# 可执行文件哈希验证
def verify_executable(file_path: str, expected_hash: str | None = None) -> bool:
    """验证可执行文件完整性
    
    Args:
        file_path: 文件路径
        expected_hash: 预期的SHA256哈希值（可选）
        
    Returns:
        bool: 验证是否通过
    """
    if not os.path.exists(file_path):
        return False
    
    # 如果没有提供哈希值，仅检查文件存在性
    if expected_hash is None:
        return True
    
    try:
        # 计算文件哈希
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        return file_hash == expected_hash
    except Exception:
        return False


# 应用常量集中管理类
class AppConstants:
    """应用常量集中管理类

    用于集中管理所有应用常量，提高代码的可维护性和一致性
    """
    # 窗口尺寸常量
    MIN_WINDOW_WIDTH: int = 1000
    MIN_WINDOW_HEIGHT: int = 700
    DIALOG_WIDTH: int = 750
    DIALOG_HEIGHT: int = 550

    # 端口配置常量
    DEFAULT_PORT: int = 5001
    PORT_TRY_LIMIT: int = 100
    PORT_TRY_LIMIT_BACKUP: int = 50
    BACKUP_START_PORT: int = 8000
    SERVICE_START_WAIT_SECONDS: float = 0.5
    PROCESS_TERMINATE_TIMEOUT: int = 2

    # 日志配置常量
    MAX_LOG_LINES: int = 2000
    MAX_LOG_BUFFER_SIZE: int = 100  # 最大日志缓冲区大小
    DEFAULT_LOG_REFRESH_INTERVAL: int = 50  # 默认日志刷新间隔（ms）
    MAX_LOG_REFRESH_INTERVAL: int = 200  # 最大日志刷新间隔（ms）

    # 布局常量
    MAIN_LAYOUT_MARGINS: tuple[int, int, int, int] = (20, 20, 20, 10)
    MAIN_LAYOUT_SPACING: int = 15
    DIALOG_LAYOUT_MARGINS: tuple[int, int, int, int] = (20, 20, 20, 20)
    DIALOG_LAYOUT_SPACING: int = 15
    BASIC_LAYOUT_MARGINS: tuple[int, int, int, int] = (15, 15, 15, 15)
    BASIC_LAYOUT_SPACING: int = 12

    # 服务状态颜色映射
    STATUS_COLORS: dict[str, str] = {
        "运行中": "#2ecc71",  # 绿色
        "启动中": "#3498db",  # 蓝色
        "停止中": "#9b59b6",  # 紫色
        "未运行": "#95a5a6",  # 灰色
        "错误": "#e74c3c"       # 红色
    }

    # 浏览器黑名单端口（Chrome/Firefox/Edge 等浏览器禁止访问的端口）
    # 来源：https://www.chromium.org/administrators/policy-list-3/#RestrictedPorts
    BROWSER_BLOCKED_PORTS: list[int] = [
        1,      # tcpmux
        7,      # echo
        9,      # discard
        11,     # systat
        13,     # daytime
        15,     # netstat
        17,     # qotd
        19,     # chargen
        20,     # ftp-data
        21,     # ftp
        22,     # ssh
        23,     # telnet
        25,     # smtp
        37,     # time
        42,     # name
        43,     # whois
        53,     # dns
        69,     # tftp
        77,     # priv-rjs
        79,     # finger
        87,     # ttylink
        95,     # supdup
        101,    # hostriame
        102,    # iso-tsap
        103,    # gppitnp
        104,    # acr-nema
        109,    # pop2
        110,    # pop3
        111,    # sunrpc
        113,    # auth
        115,    # sftp
        117,    # uucp-path
        119,    # nntp
        123,    # ntp
        135,    # loc-srv / epmap
        137,    # netbios-ns
        138,    # netbios-dgm
        139,    # netbios-ssn
        143,    # imap2
        161,    # snmp
        179,    # bgp
        389,    # ldap
        427,    # svrloc
        465,    # smtp+ssl
        512,    # print / exec
        513,    # login
        514,    # shell
        515,    # printer
        526,    # tempo
        530,    # courier
        531,    # conference
        532,    # netnews
        540,    # uucp
        548,    # afp
        554,    # rtsp
        556,    # remotefs
        563,    # nntp+ssl
        587,    # smtp
        601,    # syslog-conn
        636,    # ldap+ssl
        993,    # imap+ssl
        995,    # pop3+ssl
        1719,   # h323gatestat
        1720,   # h323hostcall
        1723,   # pptp
        2049,   # nfs
        3659,   # apple-sasl
        4045,   # lockd
        5060,   # sip
        5061,   # sips
        6000,   # x11
        6566,   # sane-port
        6665,   # irc (alternate)
        6666,   # irc (alternate)
        6667,   # irc (default)
        6668,   # irc (alternate)
        6669,   # irc (alternate)
        6697,   # irc+tls
        10080,  # amanda
    ]

    # 系统保留端口（Windows系统服务常用端口）
    SYSTEM_RESERVED_PORTS: list[int] = [
        80,     # http
        443,    # https
        445,    # microsoft-ds
        3306,   # mysql
        3389,   # rdp
        5432,   # postgresql
        5900,   # vnc
        6379,   # redis
        8080,   # http-alt
        8443,   # https-alt
        9200,   # elasticsearch
        27017,  # mongodb
    ]

    # 最大路径深度限制
    MAX_PATH_DEPTH: int = 20

# 全局样式表配置
GLOBAL_STYLESHEET = """
/* ===== 全局基础设置 ===== */
* {
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 13px;
    outline: none;
}

QWidget {
    background-color: #f5f7fa;
    color: #333945;
}

/* ===== 卡片式容器设计 ===== */
QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #fafbfc);
    border: 1px solid #e1e5eb;
    border-radius: 10px;
    margin-top: 18px;
    padding-top: 15px;
    font-weight: 600;
    color: #2c3e50;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
    background: white;
    border-radius: 4px;
    font-size: 14px;
}

/* ===== 按钮系统（含交互反馈） ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4a6fa5, stop:1 #3a5a8a);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-width: 85px;
    min-height: 32px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #5a7fb5, stop:1 #4a6a9a);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #3a5a8a, stop:1 #2a4a7a);
}

QPushButton:disabled {
    background: #c5c9d1;
    color: #a0a5b0;
}

/* 语义化按钮 */
QPushButton#StartBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #28a745, stop:1 #218838);
}
QPushButton#StartBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2dc94e, stop:1 #259d3d);
}
QPushButton#StopBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dc3545, stop:1 #c82333);
}
QPushButton#StopBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e44c58, stop:1 #d33545);
}
QPushButton#PublicBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #17a2b8, stop:1 #138496);
}
QPushButton#PublicBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1abcce, stop:1 #169ab9);
}
QPushButton#InfoBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6c757d, stop:1 #5a6268);
}
QPushButton#InfoBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7c858d, stop:1 #6a7278);
}

/* ===== 输入框优化 ===== */
QLineEdit {
    background: white;
    border: 1px solid #d1d9e6;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #4a6fa5;
    selection-color: white;
    min-height: 30px;
}

QLineEdit:focus {
    border-color: #4a6fa5;
    border-width: 1.5px;
}

QLineEdit:read-only {
    background-color: #f8f9fc;
    color: #6c757d;
}

/* ===== 表格现代化 ===== */
QTableWidget {
    background: white;
    border: 1px solid #e1e5eb;
    border-radius: 8px;
    gridline-color: #f0f2f5;
    alternate-background-color: #fafbfc;
    outline: none;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #f0f2f5;
}

QTableWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4a6fa5, stop:1 #3a5a8a);
    color: white;
    border-radius: 4px;
}

QTableWidget::item:!selected:hover {
    background-color: #e8f4fd;
    border-radius: 4px;
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f8f9fc, stop:1 #f0f2f5);
    color: #495057;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #e1e5eb;
    font-weight: 600;
    font-size: 13px;
}

QHeaderView::section:first {
    border-top-left-radius: 8px;
}

QHeaderView::section:last {
    border-top-right-radius: 8px;
}

/* ===== 状态栏 ===== */
QStatusBar {
    background: white;
    border-top: 1px solid #e1e5eb;
    color: #6c757d;
    padding: 4px 10px;
    font-size: 12px;
}

QStatusBar QLabel {
    padding: 3px 10px;
    border-radius: 4px;
    background: #f0f2f5;
    margin: 0 3px;
}

QStatusBar QLabel#RunningCount {
    background: #d4edda;
    color: #155724;
    font-weight: 500;
}

/* ===== 复选框优化 ===== */
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid #adb5bd;
    background: white;
}

QCheckBox::indicator:hover {
    border-color: #4a6fa5;
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4a6fa5, stop:1 #3a5a8a);
    border-color: #3a5a8a;
    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-check.png);
}

/* ===== 滚动条美化 ===== */
QScrollBar:vertical {
    background: #f0f2f5;
    width: 10px;
    border-radius: 5px;
    margin: 2px 0;
}

QScrollBar::handle:vertical {
    background: #c5c9d1;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #a0a5b0;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

/* ===== 菜单样式 ===== */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 5px;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 3px;
}

QMenu::item:selected {
    background-color: #3498DB;
    color: white;
}

/* ===== 消息框样式 ===== */
QMessageBox {
    background-color: #FFFFFF;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 6px 16px;
}
"""

# 配置文件路径
# 仅支持Windows系统
import os

# 延迟初始化的配置目录和文件路径
_config_dir: str | None = None
_config_file: str | None = None

def get_config_dir() -> str:
    """获取配置目录（延迟初始化）"""
    global _config_dir
    if _config_dir is None:
        _config_dir = os.path.join(os.environ['APPDATA'], 'DufsGUI')
        # 创建配置目录（如果不存在）
        os.makedirs(_config_dir, exist_ok=True)
    return _config_dir

def get_config_file() -> str:
    """获取配置文件路径（延迟初始化）"""
    global _config_file
    if _config_file is None:
        _config_file = os.path.join(get_config_dir(), 'dufs_config.json')
    return _config_file

# 为了兼容性，保留 CONFIG_FILE 变量，但使用延迟初始化
CONFIG_FILE = property(get_config_file)
