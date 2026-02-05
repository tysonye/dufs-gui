"""程序入口文件"""

# pyright: reportImplicitRelativeImport=false
# 允许使用绝对导入以支持直接运行: python main.py

import sys
import os
import traceback

# 获取程序基础目录
def get_base_dir():
    """获取程序基础目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))

# 确保工作目录设置为程序基础目录
base_dir = get_base_dir()
os.chdir(base_dir)

# 设置 Qt 插件路径
if getattr(sys, 'frozen', False):
    qt_plugin_path = os.path.join(base_dir, '_internal', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(qt_plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
    else:
        # 尝试其他可能的插件路径
        alternative_paths = [
            os.path.join(base_dir, 'PyQt5', 'Qt5', 'plugins'),
            os.path.join(base_dir, 'Qt5', 'plugins')
        ]
        for path in alternative_paths:
            if os.path.exists(path):
                os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = path
                break

# 设置环境变量来减少字体警告
try:
    # 设置QT_QPA_FONTDIR环境变量，只使用系统默认字体目录
    windir = os.environ.get('WINDIR', 'C:\\Windows')
    font_dir = os.path.join(windir, 'Fonts')
    if os.path.exists(font_dir):
        os.environ['QT_QPA_FONTDIR'] = font_dir
    # 设置QT_LOGGING_RULES环境变量，忽略字体警告
    os.environ['QT_LOGGING_RULES'] = 'qt.qpa.fonts=false'
    # 添加额外的字体相关环境变量
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
except Exception:
    # 忽略环境变量设置错误
    pass

# 尝试导入模块
try:
    import subprocess
    from PyQt5.QtWidgets import QApplication
    from main_window import MainWindow
except Exception:
    # 导入失败，创建错误日志
    error_log = os.path.join(base_dir, 'error.log')
    with open(error_log, 'w', encoding='utf-8') as f:
        f.write('导入失败:\n')
        traceback.print_exc(file=f)
    sys.exit(1)


def clean_residual_processes():
    """清理残留的 dufs 和 cloudflared 进程"""
    try:
        # 创建 startupinfo 隐藏控制台窗口
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # 获取所有进程
        output = subprocess.check_output(
            ["tasklist"],
            universal_newlines=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # 检查并清理 dufs 进程
        if "dufs.exe" in output:
            print("清理残留的 dufs.exe 进程")
            subprocess.run(
                ["taskkill", "/F", "/IM", "dufs.exe"],
                capture_output=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        # 检查并清理 cloudflared 进程
        if "cloudflared.exe" in output:
            print("清理残留的 cloudflared.exe 进程")
            subprocess.run(
                ["taskkill", "/F", "/IM", "cloudflared.exe"],
                capture_output=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
    except Exception as e:
        print(f"清理残留进程失败: {str(e)}")


def main():
    """主函数"""
    try:
        # 清理残留进程
        clean_residual_processes()
        
        # 创建应用程序实例
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow()
        
        # 显示主窗口
        window.show()
        
        # 运行应用程序
        try:
            exit_code = app.exec_()
            sys.exit(exit_code)
        except Exception:
            # 事件循环异常，创建错误日志
            error_log = os.path.join(base_dir, 'event_loop_error.log')
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write('事件循环异常:\n')
                traceback.print_exc(file=f)
            sys.exit(1)
    except Exception:
        # 程序启动失败，创建错误日志
        error_log = os.path.join(base_dir, 'startup_error.log')
        with open(error_log, 'w', encoding='utf-8') as f:
            f.write('程序启动失败:\n')
            traceback.print_exc(file=f)
        sys.exit(1)


if __name__ == "__main__":
    main()
