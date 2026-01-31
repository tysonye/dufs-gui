"""程序入口文件"""

# pyright: reportImplicitRelativeImport=false
# 允许使用绝对导入以支持直接运行: python main.py

import sys
import os
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

# 设置环境变量来减少字体警告
try:
    # 设置QT_QPA_FONTDIR环境变量，只使用系统默认字体目录
    os.environ['QT_QPA_FONTDIR'] = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
    # 设置QT_LOGGING_RULES环境变量，忽略字体警告
    os.environ['QT_LOGGING_RULES'] = 'qt.qpa.fonts=false'
except Exception:
    # 忽略环境变量设置错误
    pass


def clean_residual_processes():
    """清理残留的 dufs 和 cloudflared 进程"""
    from utils import kill_all_dufs_and_cloudflared
    
    print("=" * 50)
    print("程序启动：正在清理残留进程...")
    print("=" * 50)
    
    # 使用统一的清理函数
    kill_all_dufs_and_cloudflared()
    
    print("=" * 50)
    print("残留进程清理完成")
    print("=" * 50)


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
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
