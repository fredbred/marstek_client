#!/bin/bash
# Script pour installer l'application sur la Raspberry Pi via SSH
# Utilise les variables PI5_USERNAME et PI5_PASSWORD du fichier .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔋 Installation Marstek Automation sur Raspberry Pi 5${NC}"
echo "=================================================="
echo ""

# Charger les variables depuis .env
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Fichier .env non trouvé dans $PROJECT_ROOT${NC}"
    exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)

if [ -z "$PI5_USERNAME" ] || [ -z "$PI5_PASSWORD" ]; then
    echo -e "${RED}❌ Variables PI5_USERNAME et/ou PI5_PASSWORD non définies${NC}"
    exit 1
fi

PI5_IP="${PI5_IP:-192.168.1.47}"

# Vérifier sshpass
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️  Installation de sshpass...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass 2>/dev/null || echo "Installation requise: brew install hudochenkov/sshpass/sshpass"
        fi
    fi
fi

echo -e "${GREEN}✅ Connexion à $PI5_USERNAME@$PI5_IP${NC}"

# Tester la connexion
if ! sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 "$PI5_USERNAME@$PI5_IP" "echo 'OK'" &>/dev/null; then
    echo -e "${RED}❌ Impossible de se connecter${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Connexion réussie!${NC}"

# Exécuter l'installation
sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$PI5_USERNAME@$PI5_IP" 'bash -s' << 'REMOTE_SCRIPT'
set -e
INSTALL_DIR="$HOME/marstek_client"

# Installer les dépendances
if ! command -v git &> /dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y git
fi

if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y docker-compose-plugin
fi

# Cloner le repo
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR" && git pull origin main || true
else
    git clone https://github.com/fredbred/marstek_client.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
[ ! -f .env ] && [ -f env.template ] && cp env.template .env

echo "✅ Installation terminée!"
echo "Configurez .env puis: docker compose up -d"
REMOTE_SCRIPT

echo -e "${GREEN}✅ Terminé!${NC}"
