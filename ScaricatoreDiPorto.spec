# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ScaricatoreDiPorto.py'],
    pathex=[],
    binaries=[('.venv/Lib/site-packages/vosk/libvosk.dll', 'vosk')],
    datas=[],
    hiddenimports=['vosk', 'pywin32', 'wmi'],
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
    name='ScaricatoreDiPorto',
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
    icon=['images\\icona64.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScaricatoreDiPorto',
)
