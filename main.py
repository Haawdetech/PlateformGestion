"""
main.py — Point d'entrée PySide6 de BoutikManager
Lance Flask en arrière-plan + affiche l'app dans une fenêtre native.
"""
import sys
import os

# ── Fix macOS : résolution DNS lente ─────────
import socket
socket.getfqdn = lambda name='': 'localhost'

# ── Chemins PyInstaller ───────────────────────
if getattr(sys, 'frozen', False):
    # Dans l'exécutable PyInstaller
    BASE_DIR = sys._MEIPASS
    DATA_DIR = os.path.join(os.path.expanduser('~'), 'BoutikManager')
    os.makedirs(DATA_DIR, exist_ok=True)
    os.environ['BOUTIK_DATA_DIR'] = DATA_DIR
    os.chdir(BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR

# ── Imports PySide6 ───────────────────────────
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QBrush, QPen

# ── Import modules locaux ─────────────────────
from flask_thread import FlaskThread
from app_window import MainWindow


# ─────────────────────────────────────────────
# Splash screen dessiné en code (pas besoin d'image)
# ─────────────────────────────────────────────
def make_splash() -> QSplashScreen:
    """Crée un splash screen sombre avec le nom de l'app."""
    w, h = 480, 280
    pix = QPixmap(w, h)
    pix.fill(QColor("#0f0f1a"))

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fond avec dégradé subtil
    painter.fillRect(0, 0, w, h, QColor("#0f0f1a"))

    # Bordure bleue
    pen = QPen(QColor("#4361ee"), 2)
    painter.setPen(pen)
    painter.drawRoundedRect(4, 4, w - 8, h - 8, 12, 12)

    # Icône boutique
    painter.setPen(Qt.PenStyle.NoPen)
    font_icon = QFont("Arial", 52)
    painter.setFont(font_icon)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(0, 30, w, 90, Qt.AlignmentFlag.AlignCenter, "🏪")

    # Titre
    font_title = QFont("Arial", 22, QFont.Weight.Bold)
    painter.setFont(font_title)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(0, 120, w, 40, Qt.AlignmentFlag.AlignCenter, "BoutikManager")

    # Sous-titre
    font_sub = QFont("Arial", 11)
    painter.setFont(font_sub)
    painter.setPen(QColor("#a0a0c0"))
    painter.drawText(0, 162, w, 25, Qt.AlignmentFlag.AlignCenter, "Gestion de boutique — v2.0")

    # Barre de chargement (fond)
    bar_x, bar_y, bar_w, bar_h = 60, 210, w - 120, 8
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#2a2a4a")))
    painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 4, 4)

    # Barre de chargement (progression animée)
    painter.setBrush(QBrush(QColor("#4361ee")))
    painter.drawRoundedRect(bar_x, bar_y, int(bar_w * 0.6), bar_h, 4, 4)

    # Texte chargement
    font_loading = QFont("Arial", 9)
    painter.setFont(font_loading)
    painter.setPen(QColor("#6060a0"))
    painter.drawText(0, 230, w, 20, Qt.AlignmentFlag.AlignCenter, "Démarrage du serveur...")

    painter.end()

    splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    return splash


# ─────────────────────────────────────────────
# Point d'entrée principal
# ─────────────────────────────────────────────
def main():
    # Nécessaire avant QApplication sur certains systèmes
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-logging')

    app = QApplication(sys.argv)
    app.setApplicationName("BoutikManager")
    app.setApplicationDisplayName("BoutikManager")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("BoutikManager")

    # DPI haute résolution
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Afficher le splash screen
    splash = make_splash()
    splash.show()
    app.processEvents()

    # Variable pour la fenêtre principale
    main_window = None

    # ── Démarrer Flask dans un thread ─────────
    flask_thread = FlaskThread()

    def on_server_ready(port: int):
        """Appelé quand Flask est prêt : ferme le splash, ouvre la fenêtre."""
        nonlocal main_window
        splash.close()
        main_window = MainWindow(port)
        main_window.show()

    def on_server_error(error: str):
        """Erreur au démarrage Flask."""
        from PySide6.QtWidgets import QMessageBox
        splash.close()
        msg = QMessageBox()
        msg.setWindowTitle("Erreur de démarrage")
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(f"Impossible de démarrer BoutikManager :\n{error}")
        msg.exec()
        sys.exit(1)

    flask_thread.server_ready.connect(on_server_ready)
    flask_thread.server_error.connect(on_server_error)
    flask_thread.start()

    # Quand l'app Qt se ferme, arrêter le thread Flask
    app.aboutToQuit.connect(flask_thread.terminate)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
