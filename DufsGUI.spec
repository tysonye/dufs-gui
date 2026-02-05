# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os
import sys
from pathlib import Path

# 获取当前目录（spec 文件所在目录）
current_dir = str(Path.cwd())

# 查找 dufs.exe 和 cloudflared.exe
datas = []

# 查找 dufs.exe
dufs_path = os.path.join(current_dir, 'dufs.exe')
if os.path.exists(dufs_path):
    datas.append((dufs_path, 'lib'))

# 查找 cloudflared.exe（可能在 lib 目录）
cloudflared_paths = [
    os.path.join(current_dir, 'cloudflared.exe'),
    os.path.join(current_dir, 'lib', 'cloudflared.exe'),
]
for path in cloudflared_paths:
    if os.path.exists(path):
        datas.append((path, 'lib'))
        break

# 查找 icon.ico
icon_path = os.path.join(current_dir, 'icon.ico')
if os.path.exists(icon_path):
    datas.append((icon_path, 'lib'))

binaries = []
hiddenimports = [
    'main_window',
    'main_view',
    'service_info_dialog',
    'service_dialog',
    'service_state',
    'base_service',
    'cloudflare_tunnel',
    'service',
    'service_manager',
    'service_controller',
    'service_config',
    'config_manager',
    'config_controller',
    'log_manager',
    'log_window',
    'tray_controller',
    'tray_manager',
    'tray_event_handler',
    'event_bus',
    'auto_saver',
    'startup_manager',
    'lazy_loader',
    'utils',
    'constants',
]
tmp_ret = collect_all('PyQt5')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[current_dir],  # 添加项目目录到搜索路径
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DufsGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'] if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DufsGUI',
)
