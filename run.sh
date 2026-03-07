#!/bin/bash
# ─────────────────────────────────────────────────
#  BoutikManager — Script de démarrage
# ─────────────────────────────────────────────────

# Se placer dans le répertoire du script
cd "$(dirname "$0")"

echo ""
echo "🏪  BoutikManager"
echo "────────────────────────────────────────────"

# Vérifier Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌  Python 3 est requis."
    echo "    Installez-le depuis https://python.org"
    exit 1
fi

# Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo "📦  Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer le venv
source venv/bin/activate

# Installer les dépendances si nécessaire
if ! python3 -c "import flask" &>/dev/null 2>&1; then
    echo "📦  Installation de Flask..."
    pip install -r requirements.txt --quiet
fi

echo "✅  Prêt ! Ouverture sur http://localhost:5000"
echo "   (Appuyez sur Ctrl+C pour arrêter)"
echo "────────────────────────────────────────────"
echo ""

python3 app.py
