#!/bin/bash
# Script d'installation pour Raspberry Pi 5
# Système d'automatisation Marstek

set -e

echo "🔋 Installation Marstek Automation sur Raspberry Pi 5"
echo "=================================================="
echo ""

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les erreurs
error() {
    echo -e "${RED}❌ Erreur: $1${NC}" >&2
    exit 1
}

# Fonction pour afficher les succès
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Fonction pour afficher les warnings
warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Vérifier que nous sommes sur une Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    warning "Ce script est conçu pour Raspberry Pi, mais continue..."
fi

# Vérifier les prérequis
echo "📋 Vérification des prérequis..."
echo ""

# Git
if ! command -v git &> /dev/null; then
    echo "Installation de Git..."
    sudo apt-get update
    sudo apt-get install -y git
    success "Git installé"
else
    success "Git déjà installé: $(git --version)"
fi

# Docker
if ! command -v docker &> /dev/null; then
    echo "Installation de Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    success "Docker installé"
    warning "Vous devez vous déconnecter/reconnecter pour que les permissions Docker prennent effet"
else
    success "Docker déjà installé: $(docker --version)"
fi

# Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Installation de Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    success "Docker Compose installé"
else
    if command -v docker-compose &> /dev/null; then
        success "Docker Compose déjà installé: $(docker-compose --version)"
    else
        success "Docker Compose déjà installé: $(docker compose version)"
    fi
fi

# Python 3.11 (pour les scripts)
if ! command -v python3 &> /dev/null; then
    echo "Installation de Python 3..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
    success "Python 3 installé: $(python3 --version)"
else
    success "Python 3 déjà installé: $(python3 --version)"
fi

echo ""
echo "📦 Clonage du repository..."
echo ""

# Cloner le repository
INSTALL_DIR="$HOME/marstek_client"
if [ -d "$INSTALL_DIR" ]; then
    warning "Le répertoire $INSTALL_DIR existe déjà"
    read -p "Voulez-vous le supprimer et le recloner? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        success "Ancien répertoire supprimé"
    else
        echo "Mise à jour du repository existant..."
        cd "$INSTALL_DIR"
        git pull origin main || warning "Impossible de mettre à jour, continuons..."
        cd - > /dev/null
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    git clone https://github.com/fredbred/marstek_client.git "$INSTALL_DIR"
    success "Repository cloné dans $INSTALL_DIR"
else
    success "Repository déjà présent dans $INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo ""
echo "⚙️  Configuration de l'environnement..."
echo ""

# Créer le fichier .env à partir du template
if [ ! -f .env ]; then
    if [ -f env.template ]; then
        cp env.template .env
        success "Fichier .env créé à partir de env.template"
        warning "⚠️  IMPORTANT: Éditez le fichier .env avec vos paramètres:"
        echo "   nano $INSTALL_DIR/.env"
        echo ""
        echo "   Variables essentielles à configurer:"
        echo "   - DATABASE_URL"
        echo "   - REDIS_URL"
        echo "   - BATTERY_1_IP, BATTERY_2_IP, BATTERY_3_IP"
        echo "   - BATTERY_1_PORT, BATTERY_2_PORT, BATTERY_3_PORT"
        echo "   - TELEGRAM_BOT_TOKEN (optionnel)"
        echo "   - TELEGRAM_CHAT_ID (optionnel)"
        echo "   - TEMPO_CONTRACT_NUMBER (optionnel)"
    else
        warning "Fichier env.template non trouvé, création d'un .env vide"
        touch .env
    fi
else
    success "Fichier .env existe déjà"
fi

echo ""
echo "🐳 Vérification de Docker..."
echo ""

# Vérifier que Docker fonctionne
if sudo docker ps &> /dev/null; then
    success "Docker fonctionne correctement"
else
    error "Docker ne fonctionne pas. Vérifiez avec: sudo systemctl status docker"
fi

echo ""
echo "📊 Résumé de l'installation:"
echo "=============================="
echo "✅ Repository cloné: $INSTALL_DIR"
echo "✅ Fichier .env: $INSTALL_DIR/.env"
echo ""
echo "📝 Prochaines étapes:"
echo "====================="
echo ""
echo "1. Configurez le fichier .env:"
echo "   cd $INSTALL_DIR"
echo "   nano .env"
echo ""
echo "2. Démarrer les services:"
echo "   cd $INSTALL_DIR"
echo "   docker compose up -d"
echo ""
echo "3. Initialiser la base de données:"
echo "   docker compose exec backend alembic upgrade head"
echo ""
echo "4. Découvrir les batteries (optionnel):"
echo "   docker compose exec backend python scripts/discover_batteries.py"
echo ""
echo "5. Accéder à l'interface:"
echo "   - Interface web: http://$(hostname -I | awk '{print $1}'):8501"
echo "   - API: http://$(hostname -I | awk '{print $1}'):8000"
echo "   - Documentation API: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
success "Installation terminée! 🎉"
