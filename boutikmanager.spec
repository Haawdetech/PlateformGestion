# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — BoutikManager (PySide6 + QWebEngine + Flask)
# Usage : pyinstaller boutikmanager.spec --clean

import sys
from pathlib import Path

# Trouver les ressources Qt WebEngine (nécessaires pour QWebEngineView)
try:
    import PySide6
    pyside6_dir = Path(PySide6.__file__).parent
except Exception:
    pyside6_dir = None

block_cipher = None

a = Analysis(
    ['main.py'],                          # ← Point d'entrée PySide6
    pathex=['.'],
    binaries=[],
    datas=[
        # Templates et fichiers statiques Flask
        ('templates',    'templates'),
        ('static',       'static'),
        # Modules Python locaux
        ('app.py',       '.'),
        ('flask_thread.py', '.'),
        ('app_window.py',   '.'),
    ],
    hiddenimports=[
        # Flask / Werkzeug
        'flask',
        'jinja2',
        'jinja2.ext',
        'werkzeug',
        'werkzeug.security',
        'werkzeug.serving',
        'werkzeug.middleware.proxy_fix',
        'click',
        'sqlite3',
        # PySide6 modules utilisés
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebChannel',
        'PySide6.QtPrintSupport',
        'PySide6.QtPdf',
        'PySide6.QtNetwork',
        # Divers
        'json',
        'platform',
        'threading',
        'urllib.request',
        'subprocess',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'pydoc', 'test',
        'matplotlib', 'numpy',           # pas utilisés
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Exécutable ──────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,               # Mode COLLECT (dossier)
    name='BoutikManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                        # Pas de terminal visible
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icône (décommenter si tu as un .ico/.icns)
    # icon='assets/icon.ico',
)

# ── Collecte de tous les fichiers (inclut les .dll Qt) ──
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'Qt6WebEngineCore*',
        'Qt6WebEngine*',
    ],
    name='BoutikManager',
)

# ── macOS : créer un .app bundle ─────────────────────────
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='BoutikManager.app',
        # icon='assets/icon.icns',
        bundle_identifier='com.boutikmanager.app',
        info_plist={
            'CFBundleShortVersionString': '2.0',
            'CFBundleVersion': '2.0',
            'NSHighResolutionCapable': True,
            'NSCameraUsageDescription': '',
        },
    )
