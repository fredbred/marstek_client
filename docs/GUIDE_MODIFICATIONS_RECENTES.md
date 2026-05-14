# Guide des modifications récentes

Ce document résume les changements importants du dépôt et comment **mettre à jour** une installation existante (Raspberry Pi, Docker).

**Source de vérité des horaires** : ouvrir `backend/app/scheduler/scheduler.py` sur la branche déployée (`main`). Les valeurs ci-dessous correspondent à la configuration actuelle de `main` (Tempo **12:30**, monitoring **5 min**, job health fusionné dans le monitoring).

## Mettre à jour le code et les conteneurs

```bash
cd /path/to/marstek_client
git fetch origin
git pull origin main

docker compose build backend worker ui
docker compose up -d
```

Après une coupure de courant ou un redémarrage du Pi :

```bash
cd /path/to/marstek_client
docker compose ps -a
# Si postgres/redis sont « Exited » :
docker compose start postgres redis
docker compose restart backend worker
```

Les services **postgres** et **redis** ont désormais `restart: unless-stopped` dans `docker-compose.yml` : ils redémarrent avec Docker au boot (si les conteneurs ont été créés avec cette version du fichier).

## Planificateur (APScheduler)

Fuseau : **Europe/Paris** (voir `settings.scheduler.timezone`).

| Heure  | Job | Rôle |
|--------|-----|------|
| **06:00** | `switch_to_auto` | Mode **AUTO** sur toutes les batteries actives |
| **22:00** | `switch_to_manual_night` | Check Tempo nuit : hors rouge, **Auto conservé** ; si **demain = jour rouge Tempo** → précharge Passive / UPS (puissance négative, voir config) |
| **12:30** | `check_tempo_tomorrow` | Si **demain = rouge** : notification Telegram seule, aucune action batterie |
| **Toutes les 5 min** | `monitor_batteries` | Une requête légère par batterie, **20 s** d'écart entre batteries (rate limiting API Marstek) |

L'ancien job « health check » toutes les minutes a été **fusionné** dans le monitoring toutes les 5 minutes pour respecter les recommandations de polling (éviter moins de 60 s par batterie en cumulé).

## Notifications (Telegram / Apprise)

Variables d'environnement typiques (`.env`) :

- `NOTIFICATIONS_ENABLED` / configuration notification dans les settings
- `TELEGRAM_ENABLED=true`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

Comportement actuel des jobs :

- **06:00** : message de succès ou d'échec partiel selon les batteries
- **22:00** : notification Auto conservé hors rouge, ou résultat précharge Passive / UPS si demain est rouge
- **12:30** jour rouge détecté : alerte **🔴 JOUR ROUGE DEMAIN**
- **Monitoring** : SOC **100 %** (une fois par jour et par batterie, reset si SOC inférieur à 95 %)
- **Toutes batteries hors ligne** : alerte seulement après **3 cycles d'échec consécutifs** (environ 15 minutes avec un pas de 5 minutes), pour limiter les faux positifs (timeouts UDP)

## Tempo et modes Marstek

- À **12:30**, `check_tempo_tomorrow` envoie seulement une notification si demain est rouge ; aucune charge n'est lancée en heures pleines.
- À **22:00**, `switch_to_manual_night` consulte encore une fois Tempo : si demain est rouge, charge nocturne en mode **Passive / UPS** pendant 8 h avec puissance lue depuis la base (`AppConfig` clé `tempo_precharge_power`, défaut **-1000** W si absent). Sinon aucune commande batterie n'est envoyée et le mode Auto/autoconsommation est conservé.

Paramètres exposés côté API config (voir `backend/app/api/routes/config.py`) :

- `tempo_precharge_hour`, `tempo_precharge_power` (stockage selon implémentation actuelle).

## API Marstek : polling et stabilité

- Éviter de poller une même batterie plus souvent que **environ 60 s** en moyenne.
- Référence communautaire : https://github.com/jaapp/ha-marstek-local-api (recommandations et problèmes connus firmware).

## Fichiers utiles pour le suivi

| Fichier | Contenu |
|---------|---------|
| `backend/app/scheduler/jobs.py` | Jobs + notifications + monitoring |
| `backend/app/scheduler/scheduler.py` | Horaires cron / interval |
| `backend/app/core/mode_controller.py` | Logique AUTO / nuit / précharge Tempo |
| `backend/app/notifications/notifier.py` | Apprise / Telegram |
| `docker-compose.yml` | `restart: unless-stopped` postgres et redis |

## Vérifier rapidement que le backend tourne

```bash
curl -s http://localhost:8000/health
docker compose logs backend --tail=50 | grep scheduler_started
```

Si le scheduler ne démarre pas, vérifier `backend/app/main.py` : `start_scheduler()` doit être appelé **sans** `await` (fonction synchrone).

---

*À maintenir à chaque évolution majeure du scheduler ou des notifications.*
