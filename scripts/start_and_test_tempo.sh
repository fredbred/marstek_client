#!/bin/bash
# Script pour démarrer les services et tester l'API Tempo
# Usage: ./scripts/start_and_test_tempo.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "🚀 Démarrage des services Docker..."
echo ""

# Démarrer les services
docker compose up -d

echo ""
echo "⏳ Attente du démarrage du backend (10 secondes)..."
sleep 10

echo ""
echo "🧪 Test de l'API Tempo..."
echo ""

# Exécuter le test
./scripts/test_tempo_docker.sh
