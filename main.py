"""程序入口文件 - 使用 Win32 API 启动画面（最快显示）"""

import sys
import os
import traceback
import threading

# 获取程序基础目录
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))

base_dir = get_base_dir()
os.chdir(base_dir)

# ========== 第1步：立即显示 Win32 启动画面（在导入 Qt 之前）==========
from win32_splash import Win32SplashScreen
splash = Win32SplashScreen("DufsGUI", "文件服务器管理工具")

# 设置 Qt 插件路径（打包后）
if getattr(sys, 'frozen', False):
    qt_plugin_path = os.path.join(base_dir, '_internal', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(qt_plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path

# 优化 Qt 环境变量
try:
    os.environ['QT_QPA_FONTDIR'] = r'C:\Windows\Fonts'
    os.environ['QT_LOGGING_RULES'] = 'qt.qpa.fonts=false'
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
except (OSError, ValueError):
    pass


# ========== 第2步：导入 Qt 模块 ==========
try:
    import subprocess
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer
except ImportError:
    error_log = os.path.join(base_dir, 'error.log')
    with open(error_log, 'w', encoding='utf-8') as f:
        f.write('Qt 导入失败:\n')
        traceback.print_exc(file=f)
    splash.close()
    sys.exit(1)


def clean_residual_processes_async():
    """异步清理残留进程"""
    def cleanup():
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            for proc_name in ['dufs.exe', 'cloudflared.exe']:
                try:
                    output = subprocess.check_output(
                        ['tasklist', '/FI', f'IMAGENAME eq {proc_name}'],
                        universal_newlines=True,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=2
                    )
                    
                    if proc_name in output:
                        subprocess.run(
                            ['taskkill', '/F', '/IM', proc_name],
                            capture_output=True,
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            timeout=5
                        )
                except (subprocess.SubprocessError, OSError):
                    pass
        except (subprocess.SubprocessError, OSError):
            pass
    
    thread = threading.Thread(target=cleanup, daemon=True)
    thread.start()
    return thread


def initialize_application():
    """初始化应用程序 - 优化版：快速显示窗口框架"""
    try:
        splash.update_progress("清理残留进程...", 10)
        cleanup_thread = clean_residual_processes_async()
        
        splash.update_progress("加载程序模块...", 30)
        from main_window import MainWindow
        
        cleanup_thread.join(timeout=0.5)
        
        splash.update_progress("创建主界面框架...", 50)
        # 创建主窗口（只创建UI框架，控制器延迟初始化）
        main_window = MainWindow()
        
        splash.update_progress("显示主窗口...", 70)
        # 立即显示主窗口框架
        main_window.show()
        main_window.activateWindow()
        main_window.raise_()
        
        splash.update_progress("初始化完成...", 100)
        
        return main_window
        
    except Exception as e:
        splash.update_progress(f"错误: {str(e)}", 0)
        raise


def main():
    """主函数"""
    main_window = None  # 保持对主窗口的引用，防止被垃圾回收
    
    try:
        splash.update_progress("初始化 Qt...", 5)
        app = QApplication(sys.argv)
        
        def do_initialization():
            nonlocal main_window
            try:
                main_window = initialize_application()
                if main_window is None:
                    splash.close()
                    sys.exit(1)
                
                # 主窗口已显示，关闭启动画面
                splash.close()
                
            except Exception:
                error_log = os.path.join(base_dir, 'startup_error.log')
                with open(error_log, 'w', encoding='utf-8') as f:
                    f.write('程序启动失败:\n')
                    traceback.print_exc(file=f)
                splash.close()
                sys.exit(1)
        
        # 延迟执行初始化，让 Win32 闪屏先显示
        QTimer.singleShot(100, do_initialization)
        exit_code = app.exec_()
        sys.exit(exit_code)
        
    except Exception:
        error_log = os.path.join(base_dir, 'startup_error.log')
        with open(error_log, 'w', encoding='utf-8') as f:
            f.write('程序启动失败:\n')
            traceback.print_exc(file=f)
        splash.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
