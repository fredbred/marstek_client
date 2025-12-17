#!/bin/bash
# Script de détection des conflits Git non résolus

set -e

echo "🔍 Vérification des conflits Git..."

# Chercher les marqueurs de conflit (exclure docs et scripts qui peuvent contenir des exemples)
CONFLICTS=$(grep -r "<<<<<<< HEAD\|=======\|>>>>>>> origin" \
    --include="*.py" \
    --include="*.toml" \
    --include="*.yml" \
    --include="*.yaml" \
    --exclude-dir="docs" \
    --exclude="resolve-conflicts.py" \
    . 2>/dev/null || true)

if [ -n "$CONFLICTS" ]; then
    echo "❌ Conflits détectés dans les fichiers suivants :"
    echo "$CONFLICTS" | cut -d: -f1 | sort -u
    echo ""
    echo "💡 Pour résoudre :"
    echo "   1. Ouvrir chaque fichier"
    echo "   2. Chercher les marqueurs <<<<<<< HEAD, =======, >>>>>>> origin"
    echo "   3. Résoudre manuellement ou utiliser: python3 scripts/resolve-conflicts.py"
    exit 1
else
    echo "✅ Aucun conflit détecté"
    exit 0
fi
