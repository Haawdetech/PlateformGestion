#!/bin/bash
# ─────────────────────────────────────────────────
#  BoutikManager — Script de démarrage (PySide6)
# ─────────────────────────────────────────────────

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

# Installer / mettre à jour les dépendances
echo "📦  Vérification des dépendances..."
pip install -r requirements.txt --quiet

echo "✅  Lancement de BoutikManager..."
echo "────────────────────────────────────────────"
echo ""

# Lancer l'interface PySide6 (Flask démarre en arrière-plan)
python3 main.py
