"""Nuitka 打包脚本"""
import subprocess
import sys
import os

# Nuitka 打包命令
# 注意：需要在安装 Nuitka 后运行此脚本

def build():
    """使用 Nuitka 打包程序"""
    
    # 打包配置
    cmd = [
        sys.executable,  # Python 解释器
        "-m", "nuitka",  # 使用 Nuitka 模块
        "--standalone",  # 打包为独立可执行文件
        "--onefile",     # 打包为单个文件
        "--windows-disable-console",  # 禁用控制台窗口（GUI程序）
        "--windows-icon-from-ico=app.ico",  # 程序图标（如果有）
        "--enable-plugin=pyqt5",  # 启用 PyQt5 插件
        "--include-package=PyQt5",  # 包含 PyQt5 包
        "--include-data-dir=./bin=bin",  # 包含 bin 目录（dufs.exe 和 cloudflared.exe）
        "--output-dir=dist",  # 输出目录
        "--output-filename=DufsGUI.exe",  # 输出文件名
        "main.py"  # 入口文件
    ]
    
    print("开始打包...")
    print(f"命令: {' '.join(cmd)}")
    print()
    
    # 执行打包命令
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        print("\n打包成功！")
        print(f"输出文件: dist/DufsGUI.exe")
    else:
        print(f"\n打包失败，返回码: {result.returncode}")
        return False
    
    return True


def install_nuitka():
    """安装 Nuitka"""
    print("正在安装 Nuitka...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "nuitka"], 
                          capture_output=False, text=True)
    return result.returncode == 0


if __name__ == "__main__":
    # 检查 Nuitka 是否已安装
    try:
        import nuitka
        print("Nuitka 已安装")
    except ImportError:
        print("Nuitka 未安装，正在安装...")
        if not install_nuitka():
            print("安装 Nuitka 失败")
            sys.exit(1)
    
    # 开始打包
    if build():
        print("\n打包完成！")
    else:
        print("\n打包失败！")
        sys.exit(1)
