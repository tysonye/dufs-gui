"""PyInstaller 打包脚本 - 依赖文件放入 _internal 子文件夹"""
import os
import subprocess
import sys
import shutil


def build():
    """使用 PyInstaller 进行 onedir 打包"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, 'dist')
    build_dir = os.path.join(base_dir, 'build')

    # 清理旧的构建目录
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    # 构建 PyInstaller 命令
    # 注意：PyInstaller 6.x 会自动创建 _internal 文件夹存放依赖
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=DufsGUI",
        "--onedir",                    # 文件夹模式
        "--windowed",                  # 无控制台窗口
        "--icon=icon.ico",
        "--add-data=dufs.exe;lib",       # 包含 dufs.exe 到 lib 目录
        "--add-data=cloudflared.exe;lib",       # 包含 cloudflared.exe 到 lib 目录
        "--add-data=icon.ico;lib",       # 包含 icon.ico 到 lib 目录
        "--collect-all=PyQt5",         # 收集 PyQt5 所有文件
        "--distpath=dist",             # 输出目录
        "--workpath=build",            # 临时构建目录
        "--clean",                     # 清理临时文件
        "--noconfirm",                 # 不确认覆盖
        "main.py"
    ]

    print("开始打包...")
    print(f"模式: onedir (依赖放入 _internal 子文件夹)")
    print()

    # 执行打包命令
    result = subprocess.run(cmd, cwd=base_dir)

    if result.returncode == 0:
        print("\n打包成功！")
        print(f"\n输出目录: {os.path.join(base_dir, 'dist', 'DufsGUI')}")
        print(f"可执行文件: {os.path.join(base_dir, 'dist', 'DufsGUI', 'DufsGUI.exe')}")
        print(f"\n目录结构:")
        print(f"  DufsGUI.exe          - 主程序")
        print(f"  _internal/           - 依赖文件夹")
        print(f"    ├── lib/           - 工具文件目录")
        print(f"    │   ├── dufs.exe")
        print(f"    │   ├── cloudflared.exe")
        print(f"    │   ├── icon.ico")
        print(f"    │   └── ...")
        print(f"    └── ...")
    else:
        print(f"\n打包失败，返回码: {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
