"""程序入口文件"""

# pyright: reportImplicitRelativeImport=false
# 允许使用绝对导入以支持直接运行: python main.py

import sys
import os
import traceback

# 添加详细调试信息
print("=== DufsGUI 启动 ===", file=sys.stderr)
print(f"时间: {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}", file=sys.stderr)
print(f"Python: {sys.version}", file=sys.stderr)
print(f"当前目录: {os.getcwd()}", file=sys.stderr)
print(f"sys.executable: {sys.executable}", file=sys.stderr)
print(f"frozen: {getattr(sys, 'frozen', False)}", file=sys.stderr)

# 打印环境变量信息
print("=== 环境变量信息 ===", file=sys.stderr)
print(f"PATH: {os.environ.get('PATH', '')[:500]}...", file=sys.stderr)
print(f"TEMP: {os.environ.get('TEMP', '')}", file=sys.stderr)
print(f"TMP: {os.environ.get('TMP', '')}", file=sys.stderr)
print(f"APPDATA: {os.environ.get('APPDATA', '')}", file=sys.stderr)

# 获取程序基础目录
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
print(f"base_dir: {base_dir}", file=sys.stderr)

# 确保工作目录设置为程序基础目录
os.chdir(base_dir)
print(f"工作目录已更改为: {os.getcwd()}", file=sys.stderr)

# 设置 Qt 插件路径
if getattr(sys, 'frozen', False):
    qt_plugin_path = os.path.join(base_dir, '_internal', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(qt_plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
        print(f"Qt 插件路径: {qt_plugin_path}", file=sys.stderr)
    else:
        print(f"警告: Qt 插件路径不存在: {qt_plugin_path}", file=sys.stderr)
        # 尝试其他可能的插件路径
        alternative_paths = [
            os.path.join(base_dir, 'PyQt5', 'Qt5', 'plugins'),
            os.path.join(base_dir, 'Qt5', 'plugins')
        ]
        for path in alternative_paths:
            if os.path.exists(path):
                os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = path
                print(f"使用替代 Qt 插件路径: {path}", file=sys.stderr)
                break

# 检查 _internal 文件夹
internal_path = os.path.join(base_dir, '_internal')
print(f"_internal 存在: {os.path.exists(internal_path)}", file=sys.stderr)
if os.path.exists(internal_path):
    print(f"_internal 内容: {os.listdir(internal_path)[:5]}", file=sys.stderr)

# 尝试导入模块
try:
    import subprocess
    from PyQt5.QtWidgets import QApplication
    print("PyQt5 导入成功", file=sys.stderr)
    from main_window import MainWindow
    print("MainWindow 导入成功", file=sys.stderr)
except Exception as e:
    print(f"导入错误: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# 设置环境变量来减少字体警告
try:
    # 设置QT_QPA_FONTDIR环境变量，只使用系统默认字体目录
    windir = os.environ.get('WINDIR', 'C:\\Windows')
    font_dir = os.path.join(windir, 'Fonts')
    print(f"系统字体目录: {font_dir}", file=sys.stderr)
    if os.path.exists(font_dir):
        os.environ['QT_QPA_FONTDIR'] = font_dir
        print(f"QT_QPA_FONTDIR设置成功: {font_dir}", file=sys.stderr)
    else:
        print(f"警告: 系统字体目录不存在: {font_dir}", file=sys.stderr)
    # 设置QT_LOGGING_RULES环境变量，忽略字体警告
    os.environ['QT_LOGGING_RULES'] = 'qt.qpa.fonts=false'
    print("QT_LOGGING_RULES设置成功: qt.qpa.fonts=false", file=sys.stderr)
    # 添加额外的字体相关环境变量
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
    print("QT_ENABLE_HIGHDPI_SCALING设置成功: 0", file=sys.stderr)
except Exception as e:
    print(f"环境变量设置失败: {e}", file=sys.stderr)
    # 忽略环境变量设置错误
    pass


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
        print("main() 函数开始执行", file=sys.stderr)
        
        # 清理残留进程
        clean_residual_processes()
        
        # 创建应用程序实例
        print("创建 QApplication...", file=sys.stderr)
        app = QApplication(sys.argv)
        print("QApplication 创建成功", file=sys.stderr)
        
        # 创建主窗口
        print("创建 MainWindow...", file=sys.stderr)
        window = MainWindow()
        print("MainWindow 创建成功", file=sys.stderr)
        
        # 显示主窗口
        print("显示主窗口...", file=sys.stderr)
        window.show()
        print("主窗口显示成功", file=sys.stderr)
        
        # 运行应用程序
        print("开始事件循环...", file=sys.stderr)
        try:
            exit_code = app.exec_()
            print(f"事件循环结束，退出代码: {exit_code}", file=sys.stderr)
            sys.exit(exit_code)
        except Exception as e:
            print(f"事件循环异常: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"程序启动失败: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
