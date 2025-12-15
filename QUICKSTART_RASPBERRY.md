# 🚀 Guide Rapide - Installation sur Raspberry Pi 5

## Connexion à votre Raspberry Pi

Votre Raspberry Pi est à l'adresse **192.168.1.47**. Connectez-vous via SSH :

```bash
ssh pi@192.168.1.47
# ou
ssh votre_utilisateur@192.168.1.47
```

## Installation en 3 étapes

### Étape 1 : Exécuter le script d'installation

Une fois connecté à votre Raspberry Pi, exécutez :

```bash
curl -fsSL https://raw.githubusercontent.com/fredbred/marstek_client/main/scripts/install_raspberry.sh | bash
```

Ce script va :
- ✅ Installer Git, Docker, Docker Compose, Python 3
- ✅ Cloner le repository `marstek_client`
- ✅ Créer le fichier `.env` à partir du template
- ✅ Vérifier que Docker fonctionne

**Durée estimée : 5-10 minutes**

### Étape 2 : Configurer le fichier .env

Éditez le fichier `.env` avec vos paramètres :

```bash
cd ~/marstek_client
nano .env
```

**Variables essentielles à configurer :**

```env
# Adresses IP de vos batteries (à adapter)
BATTERY_1_IP=192.168.1.100
BATTERY_1_PORT=30001
BATTERY_2_IP=192.168.1.101
BATTERY_2_PORT=30002
BATTERY_3_IP=192.168.1.102
BATTERY_3_PORT=30003

# Notifications Telegram (optionnel mais recommandé)
TELEGRAM_BOT_TOKEN=votre_token
TELEGRAM_CHAT_ID=votre_chat_id
TELEGRAM_ENABLED=true

# Tempo RTE (optionnel)
TEMPO_ENABLED=true
TEMPO_CONTRACT_NUMBER=votre_numero
```

**Note :** Les variables `DATABASE_URL` et `REDIS_URL` sont déjà configurées pour Docker Compose, vous n'avez généralement pas besoin de les modifier.

### Étape 3 : Démarrer l'application

```bash
cd ~/marstek_client

# Démarrer tous les services
docker compose up -d

# Initialiser la base de données
docker compose exec backend alembic upgrade head

# Vérifier que tout fonctionne
docker compose ps
docker compose logs -f
```

## Accès à l'application

Une fois démarré, ouvrez votre navigateur :

- **Interface web** : http://192.168.1.47:8501
- **API** : http://192.168.1.47:8000
- **Documentation API** : http://192.168.1.47:8000/docs

## Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f

# Arrêter les services
docker compose down

# Redémarrer les services
docker compose restart

# Mettre à jour le code
cd ~/marstek_client
git pull origin main
docker compose down
docker compose build
docker compose up -d
```

## Obtenir un token Telegram (optionnel)

1. Ouvrez Telegram et cherchez [@BotFather](https://t.me/botfather)
2. Envoyez `/newbot` et suivez les instructions
3. Copiez le token reçu dans `TELEGRAM_BOT_TOKEN` du fichier `.env`
4. Cherchez [@userinfobot](https://t.me/userinfobot) pour obtenir votre Chat ID
5. Copiez votre ID dans `TELEGRAM_CHAT_ID` du fichier `.env`

## Dépannage rapide

### Docker ne fonctionne pas

```bash
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Puis déconnectez-vous et reconnectez-vous
```

### Port déjà utilisé

Modifiez les ports dans `docker-compose.yml` si nécessaire.

### Voir les logs d'erreur

```bash
docker compose logs backend
docker compose logs ui
docker compose logs postgres
```

## Support

Pour plus d'informations, consultez :
- [Documentation complète](docs/INSTALLATION_RASPBERRY.md)
- [Guide de dépannage](docs/troubleshooting.md)
- [Issues GitHub](https://github.com/fredbred/marstek_client/issues)

---

**Bon test ! 🎉**
