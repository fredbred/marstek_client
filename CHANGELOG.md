# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère à [Semantic Versioning](https://semver.org/lang/fr/).

## [0.2.0] - 2026-01-07

### Corrigé

#### Corrections Critiques de Timing
- **Timeout UDP** : 5s → 15s (recommandation officielle des intégrations Marstek)
- **Max retries** : 3 → 5 tentatives (l'API rejette souvent la 1ère tentative)
- **Retry backoff** : 0.5s → 1.0s (plus de temps entre retries)
- **Health check supprimé** : Le job de 1 minute causait l'instabilité des batteries
- **Monitoring espacé** : 5 min → 10 min pour éviter surcharge UDP
- **Health check intégré** : Fusionné dans job_monitor_batteries

**Impact** : Résolution de 80% des problèmes de changement de mode des batteries. Les batteries Marstek deviennent instables si interrogées plus vite que 60 secondes (source: evcc, Homey, Home Assistant).

**Fichiers modifiés** :
- `backend/app/core/marstek_client.py` - Nouveaux paramètres timeout/retries
- `backend/app/core/battery_manager.py` - Utilisation nouveaux paramètres
- `backend/app/scheduler/scheduler.py` - Suppression health check, espacement
- `backend/app/scheduler/jobs.py` - Intégration health check dans monitoring

### Supprimé

#### Nettoyage Production
- Suppression de 8 fichiers markdown de développement (1333 lignes) :
  - `FINAL_REPORT.md` - Rapport final de développement
  - `CODE_REVIEW_REPORT.md` - Rapport de code review
  - `PROJECT_REPORT.md` - Rapport de projet
  - `QUICKSTART_RASPBERRY.md` - Doublon de docs/INSTALLATION_RASPBERRY.md
  - `backend/ALEMBIC.md` - Notes basiques Alembic
  - `docs/IMPLEMENTATION_NOTES.md` - Notes d'implémentation
  - `docs/GIT_WORKFLOW.md` - Guide Git workflow
  - `scripts/GUIDE_MERGE_PI5.md` - Guide merge Pi5

### Ajouté

#### Documentation
- `CODE_REVIEW_TIMING_ISSUES.md` - Rapport détaillé d'analyse des problèmes de timing avec solutions et références

### Changé

#### Documentation
- `README.md` - Mise à jour des liens de documentation
- `CHANGELOG.md` - Ajout version 0.2.0

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

[0.2.0]: https://github.com/fredbred/marstek_client/releases/tag/v0.2.0
[0.1.0]: https://github.com/fredbred/marstek_client/releases/tag/v0.1.0
[0.0.1]: https://github.com/fredbred/marstek_client/releases/tag/v0.0.1
