# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère à [Semantic Versioning](https://semver.org/lang/fr/).

## [0.1.0] - 2024-01-15

### Ajouté

#### Backend
- Client UDP Marstek avec support JSON-RPC
- Découverte automatique des batteries via UDP broadcast
- Gestionnaire de batteries avec parallélisation
- Contrôleur de modes (AUTO, MANUAL, Tempo precharge)
- Service Tempo RTE avec cache Redis
- Système de notifications Telegram via Apprise
- Scheduler APScheduler avec persistance PostgreSQL
- API REST complète (batteries, modes, schedules, tempo)
- Rate limiting avec slowapi
- Modèles de données (Battery, BatteryStatusLog, ScheduleConfig)
- Migrations Alembic avec support TimescaleDB
- Logging structuré avec structlog
- Tests unitaires complets avec pytest

#### Frontend
- Interface Streamlit multi-pages
- Dashboard avec cartes batteries
- Page de configuration
- Calendrier Tempo
- Historique et logs avec export CSV/Excel
- Composants réutilisables

#### Infrastructure
- Docker Compose avec tous les services
- Configuration Cloudflare Tunnel
- Script de backup automatique PostgreSQL
- CI/CD GitHub Actions
- Pre-commit hooks (black, isort, ruff, mypy)

#### Documentation
- Architecture complète avec diagrammes Mermaid
- Documentation API avec exemples curl
- Guide de déploiement Raspberry Pi
- Guide de dépannage
- Configuration Cloudflare Tunnel
- Alternative Tailscale

### Sécurité
- CORS restrictif configurable
- Rate limiting sur tous les endpoints
- Validation stricte des inputs avec Pydantic
- Secrets via variables d'environnement
- Cloudflare Access pour authentification

### Performance
- Index de base de données optimisés
- Connection pooling PostgreSQL
- Cache Redis pour API Tempo
- Parallélisation des opérations batteries
- TimescaleDB pour requêtes time-series efficaces

### Tests
- Suite de tests complète (marstek_client, battery_manager, mode_controller, tempo_service, notifier, scheduler)
- Fixtures pytest réutilisables
- Coverage avec Codecov
- Tests CI/CD automatisés

## [0.0.1] - 2024-01-01

### Ajouté
- Structure initiale du projet
- Configuration de base Docker
- Documentation initiale

[0.1.0]: https://github.com/yourusername/marstek-automation/releases/tag/v0.1.0
[0.0.1]: https://github.com/yourusername/marstek-automation/releases/tag/v0.0.1
