"""
flask_thread.py — Lance Flask dans un QThread PySide6
Le serveur Flask tourne en arrière-plan pendant que
l'interface PySide6 affiche l'app dans un QWebEngineView.
"""
import socket
import logging
import threading
from PySide6.QtCore import QThread, Signal


def find_free_port(start: int = 5000, end: int = 5020) -> int:
    """Trouve un port libre entre start et end."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return 5000


class FlaskThread(QThread):
    """QThread qui démarre le serveur Flask."""

    # Signal émis quand le serveur est prêt (envoie le port)
    server_ready = Signal(int)
    # Signal émis en cas d'erreur au démarrage
    server_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.port = find_free_port()

    def run(self):
        """Point d'entrée du thread : démarre Flask."""
        try:
            # Supprimer les logs Werkzeug (sauf erreurs)
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            from app import app as flask_app, init_db

            # Initialiser la base de données (tables + admin par défaut)
            # IMPORTANT : init_db() doit être appelé ici (pas seulement dans
            # __main__) pour que ça fonctionne avec PyInstaller sur Windows/macOS
            init_db()

            # Notifier l'interface que le serveur va démarrer
            # (petit délai pour laisser Qt afficher le splash)
            def _notify():
                import time
                time.sleep(0.8)
                self.server_ready.emit(self.port)

            threading.Thread(target=_notify, daemon=True).start()

            # Lancer Flask (bloquant)
            flask_app.run(
                host='127.0.0.1',
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            self.server_error.emit(str(e))
