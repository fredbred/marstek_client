# Code Review - Problèmes de Timing et Changement de Mode

**Date** : 2026-01-07
**Objectif** : Identifier et corriger les problèmes de timing empêchant les changements de mode

---

## 🔍 Problèmes Identifiés

### 1. ⚠️ CRITIQUE : Health Check trop fréquent (toutes les 1 minute)

**Localisation** : `backend/app/scheduler/scheduler.py:139`

```python
trigger=IntervalTrigger(minutes=1, timezone=settings.scheduler.timezone),
```

**Problème** : Les batteries Marstek deviennent **instables si on les interroge plus vite que 60 secondes**. Le health check s'exécute toutes les minutes ET le monitoring toutes les 5 minutes, ce qui crée des collisions.

**Impact** :
- Batteries qui ne répondent plus
- Paquets UDP ignorés silencieusement
- Changements de mode qui échouent

**Source** : [evcc-io/evcc Discussion #22582](https://github.com/evcc-io/evcc/discussions/22582)

### 2. ⚠️ Timeout UDP trop court (5 secondes)

**Localisation** : `backend/app/core/marstek_client.py:58`

```python
def __init__(
    self,
    timeout: float = 5.0,  # ❌ TROP COURT
    max_retries: int = 3,  # ❌ PAS ASSEZ
```

**Problème** : L'API Marstek nécessite **15 secondes de timeout** par tentative car elle rejette souvent les commandes à la première tentative.

**Impact** : Timeouts prématurés alors que la batterie était en train de répondre

**Source** : [Homey-Marstek-Connector](https://community.homey.app/t/app-pro-marstek-venus-connector-monitor-control-and-automate-your-marstek-home-battery/143139)

### 3. ⚠️ Nombre de retries insuffisant (3 au lieu de 5)

**Problème** : L'API Marstek nécessite jusqu'à **5 tentatives** car elle rejette la plupart des écritures à la première tentative.

**Impact** : Échecs de changement de mode alors qu'un retry supplémentaire aurait réussi

### 4. Pas de vérification du mode actuel avant changement

**Localisation** : `backend/app/core/mode_controller.py:36-148`

**Problème** : On envoie toujours la commande de changement de mode, même si la batterie est déjà dans le bon mode.

**Impact** :
- Requêtes inutiles qui surchargent les batteries
- Risque d'instabilité accrue

### 5. Pas de délai après changement de mode

**Problème** : Après avoir envoyé une commande de changement de mode, on ne vérifie jamais que le mode a bien été appliqué.

**Impact** : On pense que le mode a changé alors que la batterie n'a pas encore appliqué le changement

### 6. Changements de mode en parallèle

**Localisation** : `backend/app/core/battery_manager.py:242-275`

```python
tasks = []
for battery in batteries:
    # ...
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Problème** : Les 3 batteries changent de mode simultanément, ce qui peut surcharger le réseau UDP local.

**Impact** : Collisions de paquets UDP, réponses perdues

### 7. Monitoring trop fréquent (toutes les 5 minutes)

**Localisation** : `backend/app/scheduler/scheduler.py:129`

**Problème** : Combiné avec le health check, cela crée trop de trafic vers les batteries.

**Impact** : Communication qui se détériore avec le temps

---

## ✅ Solutions Recommandées

### Solution 1 : Augmenter le timeout et les retries

**Fichier** : `backend/app/core/marstek_client.py`

```python
def __init__(
    self,
    timeout: float = 15.0,  # ✅ 15s comme recommandé
    max_retries: int = 5,    # ✅ 5 retries maximum
    retry_backoff: float = 1.0,  # ✅ Augmenter le backoff
    instance_id: int = 0,
) -> None:
```

### Solution 2 : Espacer le health check

**Fichier** : `backend/app/scheduler/scheduler.py`

```python
# AVANT : Toutes les 1 minute
trigger=IntervalTrigger(minutes=1, timezone=settings.scheduler.timezone),

# APRÈS : Toutes les 2 minutes (pour éviter collision avec monitoring 5min)
trigger=IntervalTrigger(minutes=2, timezone=settings.scheduler.timezone),
```

**OU MIEUX** : Supprimer le health check et l'intégrer au monitoring

### Solution 3 : Vérifier le mode actuel avant changement

**Fichier** : `backend/app/core/mode_controller.py`

Ajouter dans `switch_to_auto_mode` et `switch_to_manual_night` :

```python
async def switch_to_auto_mode(self, db: AsyncSession) -> dict[int, bool]:
    logger.info("switching_to_auto_mode")

    # ✅ NOUVEAU : Vérifier le mode actuel
    current_modes = await self.battery_manager.get_current_modes(db)

    # Ne changer que les batteries qui ne sont pas déjà en AUTO
    batteries_to_change = [
        bid for bid, mode in current_modes.items()
        if mode != "Auto"
    ]

    if not batteries_to_change:
        logger.info("all_batteries_already_in_auto_mode")
        return {bid: True for bid in current_modes.keys()}

    logger.info("batteries_need_mode_change",
                count=len(batteries_to_change),
                battery_ids=batteries_to_change)

    # ... reste du code
```

### Solution 4 : Ajouter une vérification après changement

**Fichier** : `backend/app/core/mode_controller.py`

```python
async def switch_to_auto_mode(self, db: AsyncSession) -> dict[int, bool]:
    # ... code existant de changement de mode ...

    # ✅ NOUVEAU : Attendre et vérifier le changement
    await asyncio.sleep(5)  # Laisser le temps à la batterie d'appliquer

    # Vérifier que le mode a bien changé
    verification = await self.battery_manager.verify_modes(db, expected_mode="Auto")

    return verification
```

### Solution 5 : Séquencer les changements de mode

**Fichier** : `backend/app/core/battery_manager.py`

```python
async def set_mode_all(
    self, db: AsyncSession, mode_config: dict[str, Any]
) -> dict[int, bool]:
    # ... code existant ...

    # ✅ OPTION 1 : Séquencer avec délai
    success_dict: dict[int, bool] = {}
    for battery in batteries:
        try:
            if mode == "auto":
                result = await self.client.set_mode_auto(
                    battery.ip_address, battery.udp_port
                )
            # ...
            success_dict[battery.id] = result
            await asyncio.sleep(2)  # Délai entre chaque batterie
        except Exception as e:
            logger.error("mode_set_failed", battery_id=battery.id, error=str(e))
            success_dict[battery.id] = False

    return success_dict
```

### Solution 6 : Fusionner health check et monitoring

**Fichier** : `backend/app/scheduler/jobs.py`

Supprimer `job_health_check` et intégrer la logique dans `job_monitor_batteries` :

```python
async def job_monitor_batteries() -> None:
    """Exécuté toutes les 10 minutes - Log status + health check + alertes."""
    logger.debug("scheduled_job_started", job="monitor_batteries")

    async with async_session_maker() as db:
        try:
            manager = BatteryManager()

            # Récupérer les status (sert aussi de health check)
            status_dict = await manager.get_all_status(db)

            # Mettre à jour last_seen_at pour les batteries qui répondent
            for battery_id, status_data in status_dict.items():
                if "error" not in status_data:
                    await db.execute(
                        update(Battery)
                        .where(Battery.id == battery_id)
                        .values(last_seen_at=datetime.utcnow())
                    )

            # Logger en base de données
            await manager.log_status_to_db(db)

            # ... reste du code alertes ...
```

**Fichier** : `backend/app/scheduler/scheduler.py`

```python
# AVANT : 2 jobs séparés (1min + 5min)
# job_health_check : 1min
# job_monitor_batteries : 5min

# APRÈS : 1 seul job unifié
add_job(
    id="monitor_batteries",
    func=job_monitor_batteries,
    trigger=IntervalTrigger(minutes=10, timezone=settings.scheduler.timezone),  # ✅ 10 minutes
    max_instances=1,
    coalesce=True,
)
```

### Solution 7 : Ajouter une méthode get_current_modes

**Fichier** : `backend/app/core/battery_manager.py`

```python
async def get_current_modes(self, db: AsyncSession) -> dict[int, str]:
    """Récupère le mode actuel de toutes les batteries.

    Returns:
        Dictionnaire {battery_id: mode_string}
    """
    stmt = select(Battery).where(Battery.is_active)
    result = await db.execute(stmt)
    batteries = result.scalars().all()

    if not batteries:
        return {}

    # Récupérer les modes en séquence (pas en parallèle)
    modes_dict: dict[int, str] = {}

    for battery in batteries:
        try:
            mode_info = await self.client.get_current_mode(
                battery.ip_address, battery.udp_port
            )
            modes_dict[battery.id] = mode_info.mode or "Unknown"
            await asyncio.sleep(1)  # Délai entre chaque requête
        except Exception as e:
            logger.error("get_mode_failed", battery_id=battery.id, error=str(e))
            modes_dict[battery.id] = "Unknown"

    return modes_dict
```

---

## 🎯 Plan d'Action

### Phase 1 : Corrections Critiques (Impact Immédiat)

1. ✅ **Augmenter timeout à 15s** (marstek_client.py)
2. ✅ **Augmenter retries à 5** (marstek_client.py)
3. ✅ **Supprimer health check séparé** ou passer à 2min minimum
4. ✅ **Espacer monitoring à 10 minutes** (scheduler.py)

### Phase 2 : Améliorations Qualité

5. ✅ **Ajouter vérification mode actuel** avant changement
6. ✅ **Ajouter délai après changement** de mode
7. ✅ **Séquencer les changements** au lieu de paralléliser

### Phase 3 : Validation

8. ✅ **Tester pendant 24h** avec les nouvelles valeurs
9. ✅ **Monitorer les logs** pour vérifier les succès de changement de mode
10. ✅ **Ajuster si nécessaire** les timings selon les résultats réels

---

## 📊 Timing Recommandé Final

| Job | Fréquence Actuelle | Fréquence Recommandée | Raison |
|-----|-------------------|----------------------|--------|
| Health Check | 1 minute | **SUPPRIMER** | Cause instabilité |
| Monitor Batteries | 5 minutes | **10 minutes** | Éviter surcharge |
| Switch to Auto | 6h00 | 6h00 ✅ | OK |
| Switch to Manual | 22h00 | 22h00 ✅ | OK |
| Tempo Check | 11h30 | 11h30 ✅ | OK |

| Paramètre UDP | Valeur Actuelle | Valeur Recommandée | Raison |
|---------------|----------------|-------------------|--------|
| Timeout | 5s | **15s** | API lente à répondre |
| Max Retries | 3 | **5** | API rejette souvent 1ère tentative |
| Retry Backoff | 0.5s | **1.0s** | Laisser plus de temps |

---

## 📚 Sources

- [Marstek Venus E Timeout - evcc Discussion](https://github.com/evcc-io/evcc/discussions/22582)
- [Marstek Venus Connector - Homey Forum](https://community.homey.app/t/app-pro-marstek-venus-connector-monitor-control-and-automate-your-marstek-home-battery/143139)
- [Marstek Local API - Home Assistant](https://community.home-assistant.io/t/marstek-local-api-v1-0-0-stable-release/942264)
- [Marstek Device Open API Documentation](https://manuals.plus/m/d0c8656e5b0773c24100f04f4e4e35d0c4e6f9ac6b6408b0765f2eb3872c2dbf)

---

## 🚨 Recommandations Immédiates

**À FAIRE MAINTENANT :**

1. Supprimer ou désactiver le health check (1 minute)
2. Augmenter le timeout UDP à 15s
3. Augmenter max_retries à 5
4. Espacer le monitoring à 10 minutes minimum

**Ces 4 changements devraient résoudre 80% des problèmes de changement de mode.**

