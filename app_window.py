"""
app_window.py — Fenêtre principale PySide6
Contient un QWebEngineView qui affiche l'app Flask locale.
Design identique à 100% (même Bootstrap, même CSS).
"""
import subprocess
import sys
import os
import tempfile
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFrame, QApplication
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtCore import QUrl, Qt, QSize, QMarginsF
from PySide6.QtGui import QIcon, QFont, QColor, QPalette, QPageLayout, QPageSize


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
        self.setMinimumSize(900, 600)

        # Fond sombre pendant le chargement
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#111827"))
        self.setPalette(palette)

        # Démarrer en plein écran (fenêtre maximisée)
        self.showMaximized()

    # ── Création du WebEngineView ─────────────
    def _setup_webview(self):
        # Profil dédié (cookies, cache isolés de Chrome/Safari)
        self.profile = QWebEngineProfile("BoutikManager", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)

        # Page personnalisée
        self.page = BoutikPage(self.profile)

        # Gestion impression (pdfPrintingFinished seulement, pas printRequested)
        self.page.pdfPrintingFinished.connect(self._on_pdf_ready)

        # Vue web
        self.web_view = QWebEngineView(self)
        self.web_view.setPage(self.page)
        self.setCentralWidget(self.web_view)

        # Auto-déclenchement impression sur les pages /imprimer
        self._last_print_url = None
        self._print_title = "Imprimer la facture"
        self.web_view.loadFinished.connect(self._on_load_finished)

    # ── Chargement de l'app Flask ─────────────
    def _load_app(self):
        self.web_view.load(QUrl(f"{self.base_url}/"))

    # ── Auto-impression quand la page /imprimer se charge ──
    def _on_load_finished(self, ok: bool):
        url = self.web_view.url().toString()
        if not ok:
            return

        # Quand on quitte la page d'impression, réinitialise pour permettre
        # de ré-imprimer si on revient sur la même facture
        if '/imprimer' not in url:
            self._last_print_url = None
            return

        # Déclenche l'impression une seule fois par chargement de page
        if url != self._last_print_url:
            self._last_print_url = url
            # Récupère le titre de la page (ex: "Facture FACT-2026-0001 — BoutikManager")
            self._print_title = self.web_view.title() or "Imprimer la facture"
            from PySide6.QtCore import QTimer
            QTimer.singleShot(400, self._on_print_requested)

    # ── Impression : génère un PDF A4 paysage ────────────
    def _on_print_requested(self):
        try:
            pdf_path = os.path.join(tempfile.gettempdir(), 'boutik_facture.pdf')
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Landscape,
                QMarginsF(0, 0, 0, 0)
            )
            self.page.printToPdf(pdf_path, layout)
        except Exception as e:
            print(f"[BOUTIK] Erreur printToPdf: {e}", flush=True)

    def _on_pdf_ready(self, path: str, success: bool):
        if not success:
            return
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
            from PySide6.QtGui import QPainter
            from PySide6.QtCore import QSize, QRect

            # ── Charger le PDF ────────────────────────
            doc = QPdfDocument(self)
            err = doc.load(path)
            # doc.load() renvoie QPdfDocument.Error ; Error.None_ = succès
            if err != QPdfDocument.Error.None_:
                doc.close()
                return

            # ── Configurer l'imprimante A4 paysage ───
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)

            # ── Afficher le dialogue avec le numéro de facture ──
            dialog = QPrintDialog(printer, self)
            dialog.setWindowTitle(self._print_title)
            dialog.setWindowFlags(
                dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
            dialog.raise_()
            dialog.activateWindow()

            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                doc.close()
                return

            # ── Rendre chaque page sur l'imprimante ──
            painter = QPainter(printer)
            w, h = printer.width(), printer.height()
            for page_num in range(doc.pageCount()):
                if page_num > 0:
                    printer.newPage()
                image = doc.render(page_num, QSize(w, h))
                painter.drawImage(QRect(0, 0, w, h), image)
            painter.end()
            doc.close()

        except Exception as e:
            print(f"[BOUTIK] Erreur impression: {e}", flush=True)
            import traceback; traceback.print_exc()

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
