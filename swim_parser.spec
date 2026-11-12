# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec dosyası — swim-result-parser Windows .exe build

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('swim_icon.ico', '.'),
    ],
    hiddenimports=['pdfplumber', 'pdfminer', 'pdfminer.high_level',
                   'pdfminer.layout', 'pdfminer.converter', 'pdfminer.pdfpage',
                   'PIL', 'Pillow'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YuzmeYarisiSorgula',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # pencere açılmasın, sadece GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='swim_icon.ico',   # uygulama ikonu
)
