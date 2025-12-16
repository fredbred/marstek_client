# Installation sur Raspberry Pi 5

Guide d'installation complète du système Marstek Automation sur Raspberry Pi 5.

## Prérequis

- Raspberry Pi 5 avec Raspberry Pi OS (64-bit recommandé)
- Connexion réseau (Wi-Fi ou Ethernet)
- Au moins 4 Go de RAM
- Au moins 10 Go d'espace disque libre
- Accès SSH activé

## Installation automatique

### Option 1: Script d'installation

```bash
# Télécharger et exécuter le script d'installation
curl -fsSL https://raw.githubusercontent.com/fredbred/marstek_client/main/scripts/install_raspberry.sh | bash
```

### Option 2: Installation manuelle

```bash
# 1. Cloner le repository
cd ~
git clone https://github.com/fredbred/marstek_client.git
cd marstek_client

# 2. Installer Docker et Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt-get install -y docker-compose-plugin

# 3. Se déconnecter/reconnecter pour activer les permissions Docker
exit
# (reconnectez-vous ensuite)
```

## Configuration

### 1. Créer le fichier .env

```bash
cd ~/marstek_client
cp env.template .env
nano .env
```

### 2. Variables essentielles à configurer

```env
# Base de données (par défaut, Docker Compose gère cela)
DATABASE_URL=postgresql+asyncpg://marstek_user:marstek_pass@postgres:5432/marstek_db

# Redis (par défaut, Docker Compose gère cela)
REDIS_URL=redis://redis:6379/0

# Adresses IP des batteries (à adapter selon votre réseau)
BATTERY_1_IP=192.168.1.100
BATTERY_1_PORT=30001
BATTERY_2_IP=192.168.1.101
BATTERY_2_PORT=30002
BATTERY_3_IP=192.168.1.102
BATTERY_3_PORT=30003

# Notifications Telegram (optionnel)
TELEGRAM_BOT_TOKEN=votre_token_bot
TELEGRAM_CHAT_ID=votre_chat_id
TELEGRAM_ENABLED=true

# Tempo RTE (optionnel)
TEMPO_ENABLED=true
TEMPO_CONTRACT_NUMBER=votre_numero_contrat
```

### 3. Obtenir un token Telegram (optionnel)

1. Créer un bot via [@BotFather](https://t.me/botfather) sur Telegram
2. Envoyer `/newbot` et suivre les instructions
3. Copier le token reçu dans `TELEGRAM_BOT_TOKEN`
4. Obtenir votre Chat ID via [@userinfobot](https://t.me/userinfobot)
5. Copier votre ID dans `TELEGRAM_CHAT_ID`

## Démarrage

### 1. Démarrer les services

```bash
cd ~/marstek_client
docker compose up -d
```

Cette commande démarre:
- PostgreSQL + TimescaleDB (port 5432)
- Redis (port 6379)
- Backend FastAPI (port 8000)
- Interface Streamlit (port 8501)
- Worker pour les tâches asynchrones

### 2. Vérifier que tout fonctionne

```bash
# Voir les logs
docker compose logs -f

# Vérifier les services
docker compose ps
```

### 3. Initialiser la base de données

```bash
docker compose exec backend alembic upgrade head
```

### 4. Découvrir les batteries (optionnel)

```bash
docker compose exec backend python scripts/discover_batteries.py
```

## Accès à l'application

Une fois démarré, accédez à:

- **Interface web Streamlit**: http://192.168.1.47:8501
- **API FastAPI**: http://192.168.1.47:8000
- **Documentation API**: http://192.168.1.47:8000/docs
- **Interface API alternative**: http://192.168.1.47:8000/redoc

## Commandes utiles

### Arrêter les services

```bash
docker compose down
```

### Redémarrer les services

```bash
docker compose restart
```

### Voir les logs

```bash
# Tous les services
docker compose logs -f

# Un service spécifique
docker compose logs -f backend
docker compose logs -f ui
```

### Mettre à jour le code

```bash
cd ~/marstek_client
git pull origin main
docker compose down
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Sauvegarder la base de données

```bash
cd ~/marstek_client
./scripts/backup.sh
```

Les sauvegardes sont stockées dans `~/marstek_client/backups/`

## Dépannage

### Docker ne démarre pas

```bash
sudo systemctl status docker
sudo systemctl start docker
sudo systemctl enable docker
```

### Port déjà utilisé

Si un port est déjà utilisé, modifiez `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Changer 8000 en 8001
```

### Problème de permissions Docker

```bash
sudo usermod -aG docker $USER
# Puis se déconnecter/reconnecter
```

### Base de données ne démarre pas

```bash
# Vérifier les logs
docker compose logs postgres

# Réinitialiser la base (⚠️ supprime toutes les données)
docker compose down -v
docker compose up -d postgres
docker compose exec backend alembic upgrade head
```

### Batteries non détectées

1. Vérifier que les batteries sont sur le même réseau
2. Vérifier les adresses IP dans `.env`
3. Tester la connectivité:
   ```bash
   ping 192.168.1.100  # Remplacer par l'IP de votre batterie
   ```
4. Vérifier les ports UDP:
   ```bash
   sudo netstat -ulnp | grep 30001
   ```

## Optimisations Raspberry Pi

### Augmenter la mémoire swap (si nécessaire)

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Modifier CONF_SWAPSIZE=2048 (ou plus)
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Désactiver les services inutiles

```bash
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

### Monitoring des ressources

```bash
# Installer htop
sudo apt-get install htop
htop
```

## Support

Pour plus d'aide:
- Documentation: [docs/](docs/)
- Dépannage: [docs/troubleshooting.md](docs/troubleshooting.md)
- Issues GitHub: https://github.com/fredbred/marstek_client/issues
