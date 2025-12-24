# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['dufs_ui.py'],
    pathex=[],
    binaries=[
        ('dufs.exe', '.'),
    ],
    datas=[
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'pystray',
        'PIL.Image',
    ],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'unittest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DufsServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='DufsServer',
)
