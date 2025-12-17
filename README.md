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

### Gestion Git

```bash
make check-conflicts      # Vérifier les conflits Git
make resolve-conflicts    # Résoudre automatiquement les conflits simples
```

## 🔧 Prévention des Conflits Git

**⚠️ IMPORTANT** : Avant chaque commit, vérifiez les conflits :

```bash
make check-conflicts
```

Si des conflits sont détectés :
1. Résoudre automatiquement les conflits simples : `make resolve-conflicts`
2. Résoudre manuellement les conflits complexes
3. Vérifier à nouveau : `make check-conflicts`

Voir `docs/GIT_WORKFLOW.md` pour le guide complet.

## 📚 Documentation

- `docs/GIT_WORKFLOW.md` - Guide complet de workflow Git
- `docs/architecture.md` - Architecture du système
- `docs/api.md` - Documentation API

## 🐛 Dépannage

### Build Docker échoue

1. Vérifier les conflits : `make check-conflicts`
2. Nettoyer le cache : `docker compose build --no-cache`
3. Vérifier `backend/pyproject.toml` (syntaxe TOML)

### Conflits Git

Utiliser `make resolve-conflicts` pour résoudre automatiquement les conflits simples.
