"""
app_window.py — Fenêtre principale PySide6
Contient un QWebEngineView qui affiche l'app Flask locale.
Design identique à 100% (même Bootstrap, même CSS).
"""
import subprocess
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFrame, QApplication
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtCore import QUrl, Qt, QSize
from PySide6.QtGui import QIcon, QFont, QColor, QPalette
from PySide6.QtPrintSupport import QPrintDialog, QPrinter


# ─────────────────────────────────────────────
# Page web personnalisée
# ─────────────────────────────────────────────
class BoutikPage(QWebEnginePage):
    """
    Page QWebEngine personnalisée.
    - Redirige les nouveaux onglets vers la même fenêtre
    - Gère l'impression native
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Activer le JS, le localStorage, etc.
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

    def createWindow(self, _type):
        """Les liens target=_blank s'ouvrent dans la même page."""
        return self

    def javaScriptConsoleMessage(self, level, message, line, source):
        """Supprimer les messages de console (mode production)."""
        pass

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        """
        Ouvre les URLs externes dans le vrai navigateur.
        Les URLs localhost restent dans l'app.
        """
        host = url.host()
        if host and host not in ('127.0.0.1', 'localhost'):
            # URL externe → ouvre dans le navigateur du système
            if sys.platform == 'darwin':
                subprocess.Popen(['open', url.toString()])
            elif sys.platform == 'win32':
                subprocess.Popen(['start', url.toString()], shell=True)
            else:
                subprocess.Popen(['xdg-open', url.toString()])
            return False  # bloquer dans l'app
        return True


# ─────────────────────────────────────────────
# Fenêtre principale
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    """
    Fenêtre principale de BoutikManager.
    Affiche l'application Flask dans un QWebEngineView.
    """

    def __init__(self, port: int, parent=None):
        super().__init__(parent)
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"

        self._setup_window()
        self._setup_webview()
        self._load_app()

    # ── Configuration de la fenêtre ──────────
    def _setup_window(self):
        self.setWindowTitle("BoutikManager")
        self.setMinimumSize(1100, 650)
        self.resize(1380, 820)

        # Icône (optionnelle — décommente si tu as un .ico)
        # self.setWindowIcon(QIcon("assets/icon.ico"))

        # Fond sombre pendant le chargement
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#0f0f1a"))
        self.setPalette(palette)

    # ── Création du WebEngineView ─────────────
    def _setup_webview(self):
        # Profil dédié (cookies, cache isolés de Chrome/Safari)
        self.profile = QWebEngineProfile("BoutikManager", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)

        # Page personnalisée
        self.page = BoutikPage(self.profile)

        # Gestion impression (window.print())
        self.page.printRequested.connect(self._on_print_requested)

        # Vue web
        self.web_view = QWebEngineView(self)
        self.web_view.setPage(self.page)
        self.setCentralWidget(self.web_view)

    # ── Chargement de l'app Flask ─────────────
    def _load_app(self):
        self.web_view.load(QUrl(f"{self.base_url}/"))

    # ── Impression native ─────────────────────
    def _on_print_requested(self):
        """
        Intercepte window.print() du navigateur et ouvre
        la boîte de dialogue d'impression native du système.
        """
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPrinter.PageSize.A4)
        printer.setPageOrientation(QPrinter.Orientation.Landscape)  # factures en paysage

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Imprimer la facture")

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            # Imprime la page courante sur l'imprimante sélectionnée
            self.page.print(printer, lambda success: None)

    # ── Raccourcis clavier ────────────────────
    def keyPressEvent(self, event):
        # F5 → recharger
        if event.key() == Qt.Key.Key_F5:
            self.web_view.reload()
        # F11 → plein écran
        elif event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        # Ctrl+W / Cmd+Q → quitter
        elif event.key() == Qt.Key.Key_Q and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            QApplication.quit()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Quitte proprement (arrête Flask via le thread principal)."""
        QApplication.quit()
        event.accept()
