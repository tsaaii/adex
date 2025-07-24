# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['advitia_app.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data'), ('assets/logo.png', 'assets')],
    hiddenimports=['serial', 'serial.tools.list_ports', 'google.cloud.storage', 'google.api_core.exceptions', 'google.auth', 'PIL._tkinter_finder', 'PIL.Image', 'PIL.ImageTk', 'pandas._libs.testing', 'cv2', 'reportlab.pdfgen.canvas', 'reportlab.lib.pagesizes', 'reportlab.platypus', 'psutil', 'tkinter.filedialog', 'tkinter.messagebox'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'jupyter', 'cv2.aruco', 'cv2.face', 'cv2.tracking'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    exclude_binaries=True,
    name='SAC_monitor_Palacole',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['right.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='SAC_monitor_Palacole',
)
