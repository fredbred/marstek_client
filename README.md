# Marstek Automation

Système d'automatisation complet pour batteries Marstek Venus-E avec optimisation Tempo RTE.

## 📋 Description

Marstek Automation est une solution complète pour gérer automatiquement plusieurs batteries Marstek Venus-E (5kWh chacune) avec :

- 🔄 **Gestion automatique des modes** : Passage automatique entre modes AUTO (6h-22h) et MANUAL (22h-6h)
- ⚡ **Optimisation Tempo RTE** : Intégration avec l'API Tempo pour optimiser les jours rouges
- 📊 **Interface de monitoring** : Dashboard Streamlit en temps réel
- 📱 **Notifications** : Alertes via Apprise (Telegram, Email, etc.)
- 🐳 **Déploiement Docker** : Architecture containerisée avec Docker Compose
- 📈 **Base de données temporelle** : TimescaleDB pour l'historique des données

## 🏗️ Architecture

```
marstek-automation/
├── docker-compose.yml          # Orchestration des services
├── .env.example                # Variables d'environnement template
├── .gitignore                  # Fichiers à ignorer
├── README.md                   # Documentation principale
├── backend/                    # Application FastAPI
│   ├── Dockerfile
│   ├── pyproject.toml          # Dépendances Poetry
│   ├── app/
│   │   ├── main.py             # Point d'entrée FastAPI
│   │   ├── config.py            # Configuration
│   │   ├── api/                 # Routes API
│   │   ├── core/                # Utilitaires partagés
│   │   ├── models/              # Modèles de données
│   │   ├── scheduler/          # Gestionnaire de scheduler
│   │   └── notifications/      # Services de notification
│   └── tests/                  # Tests unitaires
├── ui/                         # Interface Streamlit
│   ├── Dockerfile
│   ├── requirements.txt
│   └── streamlit_app.py
└── scripts/
    └── discover_batteries.py    # Découverte automatique des batteries
```

## 📦 Prérequis

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Python 3.11+** (pour développement local)
- Accès réseau aux batteries Marstek (même réseau local)
- API Open activée sur chaque batterie via l'app Marstek

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone <repository-url>
cd marstek-automation
```

### 2. Configurer l'environnement

```bash
cp env.template .env
```

Éditer `.env` avec vos paramètres :

```env
# Batteries (utiliser le script de découverte)
BATTERY_1_IP=192.168.1.100
BATTERY_1_PORT=30001
BATTERY_2_IP=192.168.1.101
BATTERY_2_PORT=30002
BATTERY_3_IP=192.168.1.102
BATTERY_3_PORT=30003

# Database
POSTGRES_PASSWORD=votre_mot_de_passe_securise

# Notifications
NOTIFICATION_URLS=telegram://bot_token@telegram/chat_id/
```

### 3. Découvrir les batteries (optionnel)

```bash
python scripts/discover_batteries.py
```

Ce script envoie un broadcast UDP pour découvrir automatiquement les batteries sur le réseau local.

### 4. Lancer avec Docker Compose

```bash
docker-compose up -d
```

Les services suivants seront démarrés :
- **postgres** : Base de données TimescaleDB (port 5432)
- **redis** : Cache et queue (port 6379)
- **backend** : API FastAPI (port 8000)
- **worker** : Worker RQ pour tâches en arrière-plan
- **ui** : Interface Streamlit (port 8501)

### 5. Vérifier le statut

```bash
docker-compose ps
```

Accéder à l'interface :
- **Streamlit UI** : http://localhost:8501
- **API FastAPI** : http://localhost:8000
- **API Docs** : http://localhost:8000/docs

## ⚙️ Configuration

### Batteries Marstek

1. **Activer l'API Open** dans l'application mobile Marstek pour chaque batterie
2. **Configurer le port UDP** dans l'app (recommandé : 30001, 30002, 30003)
3. **Configurer les IPs statiques** dans votre routeur (recommandé)

### Variables d'environnement principales

| Variable | Description | Défaut |
|----------|-------------|--------|
| `BATTERY_X_IP` | Adresse IP de la batterie X | - |
| `BATTERY_X_PORT` | Port UDP de la batterie X | 30000+X |
| `AUTO_MODE_START_HOUR` | Heure de début mode AUTO | 6 |
| `AUTO_MODE_END_HOUR` | Heure de fin mode AUTO | 22 |
| `TEMPO_ENABLED` | Activer l'intégration Tempo | true |
| `TEMPO_CONTRACT_NUMBER` | Numéro de contrat Tempo | - |
| `NOTIFICATION_URLS` | URLs Apprise (Telegram, etc.) | - |

Voir `env.template` pour la liste complète.

## 📖 Usage

### Interface Streamlit

Accéder à http://localhost:8501 pour :
- Visualiser le statut des batteries en temps réel
- Consulter l'historique des modes
- Configurer les paramètres

### API REST

L'API FastAPI est disponible sur http://localhost:8000 avec documentation interactive sur `/docs`.

Exemples d'endpoints :
- `GET /health` : Health check
- `GET /api/v1/batteries/status` : Statut de toutes les batteries
- `POST /api/v1/batteries/{id}/mode` : Changer le mode d'une batterie

### Scripts

#### Découvrir les batteries

```bash
python scripts/discover_batteries.py
```

## 🔧 Développement

### Setup environnement local

```bash
cd backend
poetry install
poetry shell
```

### Lancer les tests

```bash
cd backend
poetry run pytest
```

### Linting & Formatage

```bash
cd backend
poetry run black .
poetry run isort .
poetry run ruff check .
poetry run mypy app
```

## 📚 Documentation

- [Notes d'implémentation](docs/IMPLEMENTATION_NOTES.md)
- [API Marstek](docs/MarstekDeviceOpenApi.pdf)

## 🐛 Dépannage

### Les batteries ne sont pas détectées

1. Vérifier que l'API Open est activée dans l'app Marstek
2. Vérifier que vous êtes sur le même réseau local
3. Vérifier les ports UDP dans la configuration
4. Utiliser le script de découverte : `python scripts/discover_batteries.py`

### Erreurs de connexion à la base de données

1. Vérifier que PostgreSQL est démarré : `docker-compose ps postgres`
2. Vérifier les credentials dans `.env`
3. Vérifier les logs : `docker-compose logs postgres`

### L'interface Streamlit ne se charge pas

1. Vérifier que le service UI est démarré : `docker-compose ps ui`
2. Vérifier les logs : `docker-compose logs ui`
3. Vérifier la connexion à l'API backend

## 📝 Licence

MIT

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci de créer une issue avant de soumettre une PR.
