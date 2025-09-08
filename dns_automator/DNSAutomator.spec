# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.')],
    hiddenimports=['tkinter', 'requests', 'gspread', 'oauth2client.service_account', 'xml.etree.ElementTree', 'json', 'os', 'time', 're', 'socket', 'threading', 'atexit'],
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
    name='DNSAutomator',
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
    icon=['icons.ico'],
)
app = BUNDLE(
    exe,
    name='DNSAutomator.app',
    icon='icons.ico',
    bundle_identifier=None,
)
