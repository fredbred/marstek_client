#!/bin/bash
# Script de connexion SSH à la Raspberry Pi 5
# Utilise les variables PI5_USERNAME et PI5_PASSWORD du fichier .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔌 Connexion à la Raspberry Pi 5"
echo "=================================="
echo ""

# Charger les variables depuis .env
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Fichier .env non trouvé dans $PROJECT_ROOT${NC}"
    echo "   Créez le fichier .env avec les variables suivantes:"
    echo "   PI5_USERNAME=votre_utilisateur"
    echo "   PI5_PASSWORD=votre_mot_de_passe"
    exit 1
fi

# Source le fichier .env
export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)

# Vérifier que les variables sont définies
if [ -z "$PI5_USERNAME" ] || [ -z "$PI5_PASSWORD" ]; then
    echo -e "${RED}❌ Variables PI5_USERNAME et/ou PI5_PASSWORD non définies dans .env${NC}"
    exit 1
fi

PI5_IP="${PI5_IP:-192.168.1.47}"

echo -e "${GREEN}✅ Connexion à $PI5_USERNAME@$PI5_IP${NC}"
echo ""

# Vérifier si sshpass est installé
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️  sshpass n'est pas installé. Installation...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass
        else
            echo -e "${RED}❌ Homebrew n'est pas installé. Installez sshpass manuellement ou utilisez:${NC}"
            echo "   brew install hudochenkov/sshpass/sshpass"
            exit 1
        fi
    else
        sudo apt-get update && sudo apt-get install -y sshpass
    fi
fi

# Tester la connexion
echo "Test de connexion..."
if sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 "$PI5_USERNAME@$PI5_IP" "echo 'Connexion réussie!' && whoami && hostname" 2>&1; then
    echo -e "${GREEN}✅ Connexion SSH réussie!${NC}"
    echo ""
    echo "Vous pouvez maintenant exécuter des commandes sur la Raspberry Pi."
    echo ""
    echo "Exemples:"
    echo "  $0 'whoami'"
    echo "  $0 'docker --version'"
    echo "  $0 'cd ~ && pwd'"
    echo ""
    
    # Si des arguments sont fournis, exécuter la commande
    if [ $# -gt 0 ]; then
        echo "Exécution de la commande: $*"
        sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$PI5_USERNAME@$PI5_IP" "$@"
    fi
else
    echo -e "${RED}❌ Échec de la connexion SSH${NC}"
    echo "   Vérifiez:"
    echo "   - Que la Raspberry Pi est allumée et connectée au réseau"
    echo "   - Que l'adresse IP est correcte ($PI5_IP)"
    echo "   - Que SSH est activé sur la Raspberry Pi"
    echo "   - Que les identifiants sont corrects"
    exit 1
fi
