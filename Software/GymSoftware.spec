# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('third_party/adb/adb.exe', '.'), ('third_party/adb/AdbWinApi.dll', '.'), ('third_party/adb/AdbWinUsbApi.dll', '.')],
    datas=[('assets', 'assets'), ('clientsManagement', 'clientsManagement'), ('entries_management', 'entries_management'), ('mainwindow', 'mainwindow'), ('membershipsInfo', 'membershipsInfo'), ('membershipsPlans', 'membershipsPlans')],
    hiddenimports=[],
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
    name='GymSoftware',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\GymLogo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GymSoftware',
)
