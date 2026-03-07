# -*- mode: python ; coding: utf-8 -*-
# Fichier de configuration PyInstaller pour BoutikManager
# Usage : pyinstaller boutikmanager.spec --clean

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),   # Dossier templates Jinja2
        ('static',    'static'),      # CSS, JS, images
    ],
    hiddenimports=[
        'flask',
        'jinja2',
        'jinja2.ext',
        'werkzeug',
        'werkzeug.security',
        'werkzeug.serving',
        'click',
        'sqlite3',
        'webbrowser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
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
    name='BoutikManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # True = fenêtre terminal visible (pratique pour voir les erreurs)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
