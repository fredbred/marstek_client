# Guide de Déploiement

Guide complet pour déployer Marstek Automation sur un Raspberry Pi.

## 📋 Prérequis

- Raspberry Pi 4 (recommandé) ou serveur Linux
- Système d'exploitation : Raspberry Pi OS (Debian) ou Ubuntu
- Accès root/sudo
- Connexion Internet stable

## 🔧 Installation système

### 1. Mise à jour du système

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 2. Installation Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Installation Docker Compose

```bash
sudo apt install docker-compose-plugin -y
```

## 🚀 Déploiement de l'application

### 1. Cloner le repository

```bash
git clone <repo-url>
cd marstek-automation
```

### 2. Configuration

```bash
cp .env.example .env
nano .env  # Configurer variables
```

### 3. Première installation

```bash
docker compose build
docker compose up -d
docker compose ps
```

### 4. Initialisation de la base de données

```bash
sleep 30
docker compose exec backend alembic upgrade head
```

### 5. Découverte des batteries

```bash
docker compose exec backend python scripts/discover_batteries.py
```

## 📊 Monitoring

```bash
# Logs en temps réel
docker compose logs -f

# Statut des services
docker compose ps

# Vérification de la base de données
docker compose exec postgres psql -U marstek -d marstek_db -c "SELECT COUNT(*) FROM batteries;"
```

## 💾 Backup automatique

### Configuration Crontab

```bash
crontab -e
# Ajouter:
0 2 * * * /home/pi/marstek-automation/scripts/backup.sh >> /var/log/marstek-backup.log 2>&1
```
