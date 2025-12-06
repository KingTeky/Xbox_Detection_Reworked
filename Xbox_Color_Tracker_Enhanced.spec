# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Main_ODSystem_Enhanced_Edition.py'],
    pathex=[],
    binaries=[('C:\\Users\\Cedan\\AppData\\Local\\Programs\\Python\\Python310\\lib\\site-packages\\vgamepad\\win\\vigem\\client\\x64\\ViGEmClient.dll', 'vgamepad/win/vigem/client/x64/')],
    datas=[('All_icons_pngs', 'All_icons_pngs'), ('C:\\Users\\Cedan\\AppData\\Local\\Programs\\Python\\Python310\\lib\\site-packages\\ultralytics\\cfg\\default.yaml', 'ultralytics/cfg'), ('yolov8n.pt', '.'), ('config.json', '.')],
    hiddenimports=['ultralytics', 'torch', 'vgamepad', 'vgamepad.win', 'vgamepad.win.vigem_client', 'win32gui', 'win32api', 'inputs', 'mss', 'pygetwindow', 'pytesseract'],
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
    a.binaries,
    a.datas,
    [],
    name='Xbox_Color_Tracker_Enhanced',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['All_icons_pngs\\KT_OD_App_iconV3.1Multi.ico'],
)
