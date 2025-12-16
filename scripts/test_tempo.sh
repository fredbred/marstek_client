#!/bin/bash
# Script de test pour l'API Tempo RTE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔍 Test de l'API Tempo RTE"
echo "================================"
echo ""

# Charger les variables d'environnement
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | grep -v '^$' | xargs)
else
    echo "❌ Fichier .env non trouvé"
    exit 1
fi

# Vérifier le numéro de contrat
if [ -z "$TEMPO_CONTRACT_NUMBER" ] || [ "$TEMPO_CONTRACT_NUMBER" = "" ]; then
    echo "❌ TEMPO_CONTRACT_NUMBER non défini dans .env"
    echo ""
    echo "📝 Ajoutez votre numéro de contrat dans .env:"
    echo "   TEMPO_CONTRACT_NUMBER=votre_numero_de_contrat"
    exit 1
fi

echo "✅ Numéro de contrat: ${TEMPO_CONTRACT_NUMBER:0:3}***"
echo ""

# Tester depuis la Raspberry Pi
if [ -n "$PI5_IP" ] && [ -n "$PI5_USERNAME" ] && [ -n "$PI5_PASSWORD" ]; then
    echo "🧪 Test depuis la Raspberry Pi..."
    echo ""
    
    sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no "$PI5_USERNAME@$PI5_IP" "cd ~/marstek_client && python3 -c \"
import asyncio
import os
import json
from datetime import date
import httpx

contract = os.getenv('TEMPO_CONTRACT_NUMBER', '').strip()
if not contract:
    print('❌ TEMPO_CONTRACT_NUMBER non défini sur la Pi')
    exit(1)

BASE_URL = 'https://digital.iservices.rte-france.com/open_api/tempo_like_supply_contract/v1'
today = date.today()
url = f'{BASE_URL}/tempo_like_calendars'
params = {'start_date': today.isoformat(), 'end_date': today.isoformat(), 'contract_number': contract}

async def test():
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        print(f'Status: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            print('✅ Réponse reçue!')
            print(json.dumps(data, indent=2))
            calendars = data.get('tempo_like_calendars', [])
            for entry in calendars:
                if entry.get('date') == today.isoformat():
                    color = entry.get('value') or entry.get('color', 'UNKNOWN')
                    print(f'✅ Couleur Tempo: {color}')
                    break
        else:
            print(f'❌ Erreur: {r.text[:200]}')

asyncio.run(test())
\""
else
    echo "⚠️  Variables PI5_* non définies"
    echo "   Testez depuis la Raspberry Pi ou installez httpx localement"
fi
