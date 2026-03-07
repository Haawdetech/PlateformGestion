#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
#  BoutikManager — Script de mise à jour rapide
#  Usage : bash update.sh "Description de la modification"
# ─────────────────────────────────────────────────────────────────────

cd "$(dirname "$0")"

MESSAGE="${1:-Mise à jour}"

echo ""
echo "🚀  Envoi des modifications sur GitHub..."
echo "📝  Message : $MESSAGE"
echo ""

git add .
git commit -m "$MESSAGE"
git push origin main

echo ""
echo "✅  Envoyé ! GitHub compile maintenant Mac + Windows."
echo "🔗  Voir l'avancement : vérifiez l'onglet 'Actions' sur GitHub"
echo "📦  Les fichiers seront dans l'onglet 'Releases' dans ~3 minutes"
echo ""
