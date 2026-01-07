# Marstek Automation

Système d'automatisation pour batteries Marstek Venus-E.

## 🚀 Démarrage Rapide

```bash
# Installation
make setup
# Éditer .env avec votre configuration

# Build et démarrage
docker compose build
docker compose up -d

# Voir les logs
make logs
```

## 📋 Commandes Disponibles

Voir `make help` pour la liste complète.

### Développement

```bash
make build          # Build Docker images
make up             # Démarrer tous les services
make down           # Arrêter tous les services
make logs           # Voir les logs
make test           # Lancer les tests
make lint           # Vérifier le code
make format         # Formater le code
```

### Nettoyage Docker

```bash
make clean-images   # Supprimer images non utilisées
make clean-cache    # Supprimer cache de build
make clean-all      # Nettoyage complet (⚠️ attention)
```

## 📚 Documentation

- `docs/architecture.md` - Architecture du système
- `docs/api.md` - Documentation API
- `docs/deployment.md` - Guide de déploiement
- `docs/troubleshooting.md` - Guide de dépannage
- `docs/INSTALLATION_RASPBERRY.md` - Installation sur Raspberry Pi
- `CODE_REVIEW_TIMING_ISSUES.md` - Analyse des problèmes de timing

## 🐛 Dépannage

### Build Docker échoue

1. Nettoyer le cache : `docker compose build --no-cache`
2. Vérifier `backend/pyproject.toml` (syntaxe TOML)
3. Vérifier les logs : `docker compose logs backend`

### Batteries ne changent pas de mode

Voir le rapport détaillé : `CODE_REVIEW_TIMING_ISSUES.md`

Les problèmes courants :
- Timeout UDP trop court (maintenant 15s)
- Polling trop fréquent (batteries instables si <60s)
- Solution : Les paramètres ont été optimisés en v0.2.0

### Plus d'aide

Consultez `docs/troubleshooting.md` pour le guide complet.
