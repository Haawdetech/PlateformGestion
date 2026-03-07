"""
BoutikManager — Lanceur pour l'exécutable PyInstaller
Démarre Flask dans un thread, puis ouvre le navigateur automatiquement.
"""
import threading
import webbrowser
import time
import socket

from app import app, init_db


def find_free_port(start=5000, end=5020):
    """Trouve le premier port libre entre start et end."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return start  # fallback


def _open_browser(port):
    """Attend 1,5 s puis ouvre le navigateur."""
    time.sleep(1.5)
    webbrowser.open(f'http://127.0.0.1:{port}')


if __name__ == '__main__':
    init_db()

    port = find_free_port()

    print('\n' + '═' * 50)
    print('  🏪  BoutikManager est démarré !')
    print(f'  🌐  Ouverture de http://localhost:{port}...')
    print('  (Fermez cette fenêtre pour arrêter)')
    print('═' * 50 + '\n')

    # Ouvre le navigateur en arrière-plan
    threading.Thread(target=_open_browser, args=(port,), daemon=True).start()

    # Lance Flask (bloquant)
    app.run(debug=False, host='127.0.0.1', port=port)
