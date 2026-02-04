"""程序入口文件 - 调试版本"""
import sys
import os
import traceback

# 将日志输出到固定位置（桌面）
desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
log_file = os.path.join(desktop, 'dufs_gui_debug.log')

class Logger:
    def __init__(self, filepath):
        self.file = open(filepath, 'w', encoding='utf-8')
        
    def write(self, message):
        self.file.write(message)
        self.file.flush()
        
    def flush(self):
        self.file.flush()

sys.stderr = Logger(log_file)
sys.stdout = Logger(log_file)

print("=== DufsGUI 启动中 ===")
print(f"时间: {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}")
print(f"Python 版本: {sys.version}")
print(f"当前目录: {os.getcwd()}")
print(f"sys.executable: {sys.executable}")
print(f"sys.argv[0]: {sys.argv[0]}")
print(f"frozen: {getattr(sys, 'frozen', False)}")

# 获取程序目录
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
print(f"base_dir: {base_dir}")

# 检查文件存在性
print("\n=== 文件检查 ===")
for filename in ['dufs.exe', 'icon.ico']:
    filepath = os.path.join(base_dir, filename)
    print(f"{filename}: {os.path.exists(filepath)} - {filepath}")

# 检查 _internal 文件夹
print("\n=== _internal 检查 ===")
internal_path = os.path.join(base_dir, '_internal')
print(f"_internal 存在: {os.path.exists(internal_path)}")
if os.path.exists(internal_path):
    print(f"_internal 内容: {os.listdir(internal_path)[:10]}")
    # 检查 Qt 插件
    qt_plugin_path = os.path.join(internal_path, 'PyQt5', 'Qt5', 'plugins', 'platforms')
    print(f"Qt 插件路径存在: {os.path.exists(qt_plugin_path)}")
    if os.path.exists(qt_plugin_path):
        print(f"Qt 插件: {os.listdir(qt_plugin_path)}")

# 设置 Qt 插件路径
try:
    if getattr(sys, 'frozen', False):
        qt_plugin_path = os.path.join(base_dir, '_internal', 'PyQt5', 'Qt5', 'plugins')
        if os.path.exists(qt_plugin_path):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
            print(f"\nQt 插件路径设置: {qt_plugin_path}")
        else:
            print(f"\n警告: Qt 插件路径不存在: {qt_plugin_path}")
    
except Exception as e:
    print(f"\n设置 Qt 插件路径失败: {e}")
    traceback.print_exc()

# 尝试导入模块
try:
    print("\n=== 导入测试 ===")
    from PyQt5.QtWidgets import QApplication
    print("PyQt5 导入成功")
    
    import main_window
    print("main_window 导入成功")
    
    import service
    print("service 导入成功")
    
    import constants
    print("constants 导入成功")
    
    import cloudflared_downloader
    print("cloudflared_downloader 导入成功")
    
    # 导入其他模块
    import config_manager
    import log_manager
    import service_manager
    print("所有模块导入成功")
    
except Exception as e:
    print(f"导入错误: {e}")
    traceback.print_exc()

# 尝试创建应用
try:
    print("\n=== 创建应用 ===")
    app = QApplication(sys.argv)
    print("QApplication 创建成功")
    
    print("创建 MainWindow...")
    window = main_window.MainWindow()
    print("MainWindow 创建成功")
    
    print("显示主窗口...")
    window.show()
    print("主窗口显示成功")
    
    print("开始事件循环...")
    sys.exit(app.exec_())
    
except Exception as e:
    print(f"应用启动失败: {e}")
    traceback.print_exc()
    sys.exit(1)
