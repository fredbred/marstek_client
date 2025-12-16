# Guide de Dépannage

Solutions aux problèmes courants rencontrés avec Marstek Automation.

## 🔍 Diagnostic rapide

```bash
# Statut des conteneurs
docker compose ps

# Logs récents
docker compose logs --tail=50

# Santé de l'API
curl http://localhost:8000/health
```

## 🐛 Problèmes courants

### 1. Services ne démarrent pas

**Solutions:**
```bash
# Vérifier les ports
sudo netstat -tulpn | grep -E '8000|8501|5432|6379'

# Vérifier les logs
docker compose logs backend

# Redémarrer proprement
docker compose down
docker compose up -d
```

### 2. Base de données inaccessible

**Solutions:**
```bash
# Vérifier que PostgreSQL est démarré
docker compose ps postgres

# Tester la connexion
docker compose exec postgres psql -U marstek -d marstek_db -c "SELECT 1;"
```

### 3. Batteries non découvertes

**Solutions:**
```bash
# Vérifier la connectivité réseau
ping 192.168.1.100

# Tester la découverte manuellement
docker compose exec backend python scripts/discover_batteries.py
```

### 4. Erreurs de migration Alembic

**Solutions:**
```bash
# Vérifier l'état des migrations
docker compose exec backend alembic current

# Forcer une migration
docker compose exec backend alembic stamp head
docker compose exec backend alembic upgrade head
```

## 🔧 Commandes utiles

### Diagnostic complet

```bash
docker compose ps
curl -s http://localhost:8000/health
docker compose logs backend --tail=10
```

### Réinstallation complète

```bash
docker compose down -v
docker system prune -a --volumes
cp .env.example .env
nano .env
docker compose build
docker compose up -d
```
