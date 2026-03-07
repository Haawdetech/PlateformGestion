#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
#  BoutikManager — Script de build PyInstaller
#  Crée un exécutable standalone dans dist/BoutikManager
# ─────────────────────────────────────────────────────────────────────

cd "$(dirname "$0")"

echo ""
echo "🏗️  BoutikManager — Build PyInstaller"
echo "────────────────────────────────────────────"

# Activer le venv
if [ ! -d "venv" ]; then
    echo "📦  Création de l'environnement virtuel..."
    python3 -m venv venv
fi
source venv/bin/activate

# Installer les dépendances
echo "📦  Installation des dépendances..."
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

# Nettoyer les anciens builds
echo "🧹  Nettoyage des anciens builds..."
rm -rf dist build __pycache__

# Lancer PyInstaller
echo "⚙️   Compilation en cours (peut prendre 1-2 minutes)..."
pyinstaller boutikmanager.spec --clean --noconfirm

# Résultat
if [ -f "dist/BoutikManager" ]; then
    echo ""
    echo "✅  Build réussi !"
    echo "   Exécutable : $(pwd)/dist/BoutikManager"
    echo ""
    echo "   Pour lancer : ./dist/BoutikManager"
    echo "   (La base de données sera dans ~/BoutikManager/boutique.db)"
    echo "────────────────────────────────────────────"
elif [ -f "dist/BoutikManager.exe" ]; then
    echo ""
    echo "✅  Build réussi !"
    echo "   Exécutable : $(pwd)/dist/BoutikManager.exe"
    echo "────────────────────────────────────────────"
else
    echo ""
    echo "❌  Échec du build. Vérifiez les erreurs ci-dessus."
    exit 1
fi
