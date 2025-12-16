# Guide pour finaliser le merge sur le Pi5

## État actuel
- ✅ Dépôt Git initialisé
- ✅ Commit initial créé avec les fichiers locaux
- ✅ Fichiers de configuration sauvegardés dans `/tmp/pi5_backup/`
- ⚠️ Fetch depuis GitHub nécessite une authentification

## Option 1: Merge manuel (recommandé)

### Étape 1: Se connecter au Pi5
```bash
ssh fred@192.168.1.47
cd /home/fred/marstek_client
```

### Étape 2: Configurer l'authentification GitHub

**Option A: Utiliser un token GitHub (recommandé)**
```bash
# Créer un token sur https://github.com/settings/tokens
# Puis configurer:
git remote set-url origin https://<TOKEN>@github.com/fredbred/marstek_client.git
```

**Option B: Utiliser SSH (si clés configurées)**
```bash
git remote set-url origin git@github.com:fredbred/marstek_client.git
```

### Étape 3: Récupérer les commits depuis GitHub
```bash
git fetch origin main
```

### Étape 4: Voir les différences
```bash
git log --oneline HEAD..origin/main  # Commits sur GitHub
git diff --stat HEAD origin/main      # Fichiers différents
```

### Étape 5: Faire le merge
```bash
git merge origin/main --no-commit
```

### Étape 6: Résoudre les conflits (si nécessaire)
```bash
git status  # Voir les fichiers en conflit
# Éditer les fichiers marqués "both modified"
# Puis:
git add <fichiers-résolus>
```

### Étape 7: Restaurer les fichiers de configuration
```bash
cp /tmp/pi5_backup/.env .
# Vérifier docker-compose.yml si nécessaire
```

### Étape 8: Finaliser le commit
```bash
git add .
git commit -m "Merge: Intégration GitHub avec modifications locales Pi5"
```

## Option 2: Utiliser rsync pour synchroniser

Si le merge est trop complexe, vous pouvez synchroniser manuellement:

```bash
# Depuis votre machine locale
rsync -avz --exclude='.git' --exclude='.env' \
  /Users/fredbred/.cursor/worktrees/marstek-automation/ahw/ \
  fred@192.168.1.47:/home/fred/marstek_client/

# Puis restaurer .env sur le Pi5
ssh fred@192.168.1.47 "cp /tmp/pi5_backup/.env /home/fred/marstek_client/"
```

## Fichiers à préserver absolument

- `.env` - Configuration locale (IPs batteries, credentials)
- `docker-compose.yml` - Configuration Docker spécifique au Pi5
- `config/*.yaml` - Configurations spécifiques

## Vérification après merge

```bash
cd /home/fred/marstek_client
git status
git log --oneline -5
# Vérifier que .env est présent et correct
cat .env | grep -E "BATTERY|PI5"
```
