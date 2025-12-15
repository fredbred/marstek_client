# Alembic Migrations

## Setup

Alembic est configuré pour gérer les migrations de base de données avec support TimescaleDB.

## Commandes principales

### Créer une nouvelle migration

```bash
cd backend
poetry run alembic revision --autogenerate -m "description de la migration"
```

### Appliquer les migrations

```bash
poetry run alembic upgrade head
```

### Revenir en arrière

```bash
poetry run alembic downgrade -1
```

### Voir l'état actuel

```bash
poetry run alembic current
```

### Voir l'historique

```bash
poetry run alembic history
```

## Migration initiale

La migration initiale (`001_initial_migration.py`) crée :
- Table `batteries` : Informations sur les batteries
- Table `schedule_configs` : Configurations de planning
- Table `battery_status_logs` : Logs de status (hypertable TimescaleDB)
- Extension TimescaleDB
- Hypertable pour `battery_status_logs` avec chunk_time_interval de 1 jour

## Configuration

L'URL de la base de données est automatiquement récupérée depuis les variables d'environnement via `app.config.get_settings()`.

## Notes

- Les migrations sont asynchrones (async/await)
- TimescaleDB est automatiquement activé lors de la première migration
- L'hypertable est créée avec un intervalle de chunk de 1 jour pour optimiser les requêtes temporelles

