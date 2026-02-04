# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# 硬编码本地模块列表
local_modules = [
    'cloudflared_downloader',
    'config_manager',
    'constants',
    'log_manager',
    'log_window',
    'main_window',
    'service',
    'service_dialog',
    'service_info_dialog',
    'service_manager',
    'tray_manager',
    'utils',
]

print(f"包含的本地模块: {local_modules}")

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        ('dufs.exe', '.'),
        ('icon.ico', '.'),
    ],
    hiddenimports=local_modules + [
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'requests',
        'certifi',
        'charset_normalizer',
        'cryptography',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DufsGUI',
)
