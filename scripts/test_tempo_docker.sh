#!/bin/bash
# Script de test pour l'API Tempo RTE via Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🧪 Test de l'API Tempo RTE via Docker"
echo "===================================="
echo ""

cd "$PROJECT_DIR"

# Vérifier que les services sont démarrés
if ! docker compose ps | grep -q "backend.*Up"; then
    echo "⚠️  Les services Docker ne sont pas démarrés"
    echo ""
    echo "💡 Démarrez les services avec:"
    echo "   docker compose up -d"
    exit 1
fi

echo "✅ Service backend démarré"
echo ""

# Test de l'API Tempo
docker compose exec -T backend python3 << 'PYTHON_TEST'
import asyncio
from datetime import date
from app.core.tempo_service import TempoService

print("🔍 Test TempoService")
print("=" * 60)
print()

async def test():
    try:
        service = TempoService()
        
        # Test 1: Aujourd'hui
        print("Test 1: Couleur Tempo aujourd'hui")
        print("-" * 60)
        color_today = await service.get_tempo_color()
        print(f"✅ Couleur Tempo aujourd'hui: {color_today.value}")
        print()
        
        # Test 2: Demain
        print("Test 2: Couleur Tempo demain")
        print("-" * 60)
        color_tomorrow = await service.get_tomorrow_color()
        print(f"✅ Couleur Tempo demain: {color_tomorrow.value}")
        print()
        
        # Test 3: Précharge
        print("Test 3: Vérification précharge")
        print("-" * 60)
        should_precharge = await service.should_activate_precharge()
        print(f"✅ Précharge nécessaire: {should_precharge}")
        print()
        
        await service.close()
        
        print("=" * 60)
        print("✅ Tous les tests sont passés!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

asyncio.run(test())
PYTHON_TEST
