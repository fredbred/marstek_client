#!/bin/bash
# Script de code review pour vérifier black, ruff, isort et mypy

set -e

echo "🔍 Code Review - Vérification black, ruff, isort, mypy"
echo "======================================================"
echo ""

BLACK_ERRORS=false
ISORT_ERRORS=false
RUFF_ERRORS=false
MYPY_WARNINGS=false

if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
    echo "📦 Utilisation de Docker pour la vérification..."
    echo ""
    echo "💡 Note: Installation des dépendances de dev dans chaque conteneur..."
    echo ""
    
    # Fonction pour exécuter une commande avec installation des dépendances dev
    run_with_dev() {
        docker compose run --rm backend sh -c \
            "cd /app && poetry install --with dev --no-root >/dev/null 2>&1 && $1"
    }
    
    echo "🔍 Vérification Black (formatage)..."
    if run_with_dev "poetry run black --check app" 2>&1; then
        echo "✅ Black: OK"
    else
        echo "❌ Black: Erreurs de formatage détectées"
        BLACK_ERRORS=true
    fi
    echo ""
    
    echo "🔍 Vérification isort (imports)..."
    if run_with_dev "poetry run isort --check-only app" 2>&1; then
        echo "✅ isort: OK"
    else
        echo "❌ isort: Erreurs d'imports détectées"
        ISORT_ERRORS=true
    fi
    echo ""
    
    echo "🔍 Vérification Ruff (linting)..."
    if run_with_dev "poetry run ruff check app" 2>&1; then
        echo "✅ Ruff: OK"
    else
        echo "❌ Ruff: Erreurs de linting détectées"
        RUFF_ERRORS=true
    fi
    echo ""
    
    echo "🔍 Vérification MyPy (types)..."
    if run_with_dev "poetry run mypy app --ignore-missing-imports" 2>&1; then
        echo "✅ MyPy: OK"
    else
        echo "⚠️  MyPy: Avertissements de types détectés"
        MYPY_WARNINGS=true
    fi
    echo ""
    
    echo "======================================================"
    echo "📊 Résumé"
    echo "======================================================"
    
    if [ "$BLACK_ERRORS" = true ]; then
        echo "❌ Black: Erreurs détectées"
        echo "   Corriger avec: docker compose run --rm backend sh -c 'cd /app && poetry install --with dev --no-root && poetry run black app tests'"
    else
        echo "✅ Black: OK"
    fi
    
    if [ "$ISORT_ERRORS" = true ]; then
        echo "❌ isort: Erreurs détectées"
        echo "   Corriger avec: docker compose run --rm backend sh -c 'cd /app && poetry install --with dev --no-root && poetry run isort app tests'"
    else
        echo "✅ isort: OK"
    fi
    
    if [ "$RUFF_ERRORS" = true ]; then
        echo "❌ Ruff: Erreurs détectées"
        echo "   Corriger avec: docker compose run --rm backend sh -c 'cd /app && poetry install --with dev --no-root && poetry run ruff check --fix app tests'"
    else
        echo "✅ Ruff: OK"
    fi
    
    if [ "$MYPY_WARNINGS" = true ]; then
        echo "⚠️  MyPy: Avertissements détectés"
        echo "   Vérifier: docker compose run --rm backend sh -c 'cd /app && poetry install --with dev --no-root && poetry run mypy app --ignore-missing-imports'"
    else
        echo "✅ MyPy: OK"
    fi
    
    echo ""
    
    if [ "$BLACK_ERRORS" = true ] || [ "$ISORT_ERRORS" = true ] || [ "$RUFF_ERRORS" = true ]; then
        echo "❌ Code review: ÉCHEC"
        exit 1
    else
        echo "✅ Code review: SUCCÈS"
        exit 0
    fi
    
else
    echo "⚠️  Docker non disponible."
    echo ""
    echo "Pour installer les outils localement:"
    echo "  cd backend && poetry install --with dev"
    echo ""
    echo "Puis exécutez:"
    echo "  poetry run black --check app"
    echo "  poetry run isort --check-only app"
    echo "  poetry run ruff check app"
    echo "  poetry run mypy app --ignore-missing-imports"
    exit 1
fi
