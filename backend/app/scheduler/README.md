# Scheduler - Planification des batteries

## Vue d'ensemble

Le système de planification utilise APScheduler avec persistance PostgreSQL pour gérer automatiquement les modes des batteries Marstek.

## Jobs programmés

### 1. `job_switch_to_auto` - 6h00
- **Fréquence** : Tous les jours à 6h00
- **Action** : Passe toutes les batteries en mode AUTO
- **Trigger** : Cron (6:00)

### 2. `job_switch_to_manual_night` - 22h00
- **Fréquence** : Tous les jours à 22h00
- **Action** : Passe toutes les batteries en mode MANUAL avec 0W décharge
- **Trigger** : Cron (22:00)

### 3. `job_check_tempo_tomorrow` - 11h30
- **Fréquence** : Tous les jours à 11h30
- **Action** : Vérifie si le lendemain est un jour rouge Tempo et active la précharge si nécessaire
- **Trigger** : Cron (11:30)

### 4. `job_monitor_batteries` - Toutes les 5 minutes
- **Fréquence** : Toutes les 5 minutes
- **Action** : Récupère le status des batteries et le sauvegarde en TimescaleDB, envoie des alertes si nécessaire
- **Trigger** : Interval (5 minutes)

### 5. `job_health_check` - Toutes les 1 minute
- **Fréquence** : Toutes les 1 minute
- **Action** : Vérifie la connectivité des batteries et met à jour `last_seen_at`
- **Trigger** : Interval (1 minute)

## Persistance

Les jobs sont persistés dans PostgreSQL via `SQLAlchemyJobStore` :
- Table : `apscheduler_jobs`
- Survit aux redémarrages de l'application
- Les jobs en retard sont exécutés au démarrage (misfire_grace_time: 5 minutes)

## Configuration

Les paramètres du scheduler sont dans `app.config.SchedulerSettings` :
- `timezone` : Europe/Paris (par défaut)
- `max_workers` : 4 (par défaut)
- `auto_mode_start_hour` : 6
- `auto_mode_end_hour` : 22
- `manual_mode_start_hour` : 22
- `manual_mode_end_hour` : 6

## Utilisation

Le scheduler est automatiquement initialisé et démarré au démarrage de FastAPI via `app/main.py`.

### Démarrer manuellement

```python
from app.scheduler import init_scheduler, start_scheduler

scheduler = init_scheduler()
start_scheduler()
```

### Arrêter proprement

```python
from app.scheduler import shutdown_scheduler

await shutdown_scheduler()
```

## Logs

Tous les jobs utilisent structlog pour un logging structuré :
- `scheduled_job_started` : Début d'un job
- `scheduled_job_completed` : Fin réussie d'un job
- `scheduled_job_failed` : Échec d'un job

## Gestion d'erreurs

- Chaque job gère ses propres erreurs
- Les échecs sont loggés mais n'empêchent pas les autres jobs
- Les jobs en retard sont exécutés au démarrage (coalesce=True)

