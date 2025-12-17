# Guide de Workflow Git - Prévention des Conflits

## 🎯 Objectif

Ce guide explique comment éviter les conflits de merge et maintenir un historique Git propre.

## 📋 Workflow Recommandé

### 1. Workflow de Branches

```
main (production)
  └── develop (développement)
       └── feature/xxx (nouvelles fonctionnalités)
       └── fix/xxx (corrections de bugs)
       └── refactor/xxx (refactoring)
```

**Règles** :
- `main` : Toujours stable, ne jamais commit directement
- `develop` : Branche d'intégration, merge depuis les features
- Features : Branches courtes (1-3 jours max), une fonctionnalité = une branche

### 2. Commandes Essentielles

```bash
# Avant de commencer une nouvelle feature
git checkout develop
git pull origin develop
git checkout -b feature/ma-feature

# Pendant le développement (régulièrement)
git add .
git commit -m "feat: description"
git push origin feature/ma-feature

# Avant de merger dans develop
git checkout develop
git pull origin develop
git checkout feature/ma-feature
git rebase develop  # ou git merge develop
# Résoudre les conflits si nécessaire
git push origin feature/ma-feature --force-with-lease

# Merge dans develop
git checkout develop
git merge --no-ff feature/ma-feature
git push origin develop
```

### 3. Prévention des Conflits

#### A. Pull régulièrement depuis develop

```bash
# Au moins une fois par jour
git checkout develop
git pull origin develop
git checkout feature/ma-feature
git rebase develop
```

#### B. Commits fréquents et petits

```bash
# ❌ MAUVAIS : Un gros commit avec tout
git commit -m "feat: ajout de tout"

# ✅ BON : Commits atomiques
git commit -m "feat: ajout de la route /batteries"
git commit -m "feat: ajout du schéma BatteryResponse"
git commit -m "test: ajout des tests pour /batteries"
```

#### C. Communication avec l'équipe

- Avant de modifier un fichier partagé, vérifier qui l'a modifié récemment
- Utiliser `git blame` pour voir l'historique
- Discuter des changements majeurs avant de les implémenter

### 4. Résolution des Conflits

#### Étape 1 : Identifier les conflits

```bash
# Vérifier s'il y a des conflits
git status

# Chercher les marqueurs de conflit
grep -r "<<<<<<< HEAD" .
```

#### Étape 2 : Résoudre manuellement

1. Ouvrir le fichier avec conflit
2. Chercher les marqueurs `<<<<<<<`, `=======`, `>>>>>>>`
3. Choisir la bonne version ou fusionner les deux
4. Supprimer les marqueurs
5. Tester que le code fonctionne

#### Étape 3 : Finaliser

```bash
git add <fichier-résolu>
git commit -m "fix: résolution conflit dans <fichier>"
```

### 5. Outils Automatiques

#### Pre-commit Hooks (déjà configuré)

Le fichier `.pre-commit-config.yaml` contient déjà `check-merge-conflict` qui détecte les conflits avant le commit.

**Installation** :
```bash
pip install pre-commit
pre-commit install
```

#### Script de détection

Créer un script `scripts/check-conflicts.sh` :

```bash
#!/bin/bash
# Détecte les conflits non résolus

if grep -r "<<<<<<< HEAD\|=======\|>>>>>>> origin" --include="*.py" --include="*.toml" --include="*.yml" .; then
    echo "❌ Conflits détectés !"
    exit 1
else
    echo "✅ Aucun conflit détecté"
    exit 0
fi
```

### 6. Stratégies de Merge

#### A. Rebase (recommandé pour features)

```bash
git checkout feature/ma-feature
git rebase develop
# Résoudre les conflits si nécessaire
git rebase --continue
```

**Avantages** : Historique linéaire, propre
**Inconvénients** : Réécrit l'historique (ne pas faire sur main/develop)

#### B. Merge (pour intégration)

```bash
git checkout develop
git merge --no-ff feature/ma-feature
```

**Avantages** : Préserve l'historique complet
**Inconvénients** : Peut créer des commits de merge

### 7. Configuration Git Recommandée

```bash
# Configurer le merge tool
git config --global merge.tool vimdiff
# ou
git config --global merge.tool meld

# Configurer le format de commit
git config --global core.editor "vim"

# Alias utiles
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
```

### 8. Checklist Avant Merge

- [ ] Tous les tests passent (`make test`)
- [ ] Le code est formaté (`make format`)
- [ ] Aucun conflit détecté (`scripts/check-conflicts.sh`)
- [ ] La branche est à jour avec develop (`git rebase develop`)
- [ ] Le code a été reviewé (si travail en équipe)
- [ ] La documentation est à jour

### 9. Gestion des Worktrees

Si vous utilisez plusieurs worktrees (comme dans ce projet) :

```bash
# Lister les worktrees
git worktree list

# Créer un nouveau worktree
git worktree add ../autre-branche feature/autre-feature

# Supprimer un worktree
git worktree remove ../autre-branche

# Nettoyer les worktrees supprimés
git worktree prune
```

**⚠️ Important** : Les conflits doivent être résolus dans TOUS les worktrees actifs.

### 10. En Cas de Conflit Complexe

Si un conflit est trop complexe :

1. **Sauvegarder votre travail** :
   ```bash
   git stash
   ```

2. **Récupérer la version de develop** :
   ```bash
   git checkout develop
   git pull origin develop
   ```

3. **Recréer votre feature** :
   ```bash
   git checkout -b feature/ma-feature-v2
   git stash pop
   # Appliquer vos changements progressivement
   ```

## 🚨 Erreurs à Éviter

1. **❌ Ne jamais commit directement sur main/develop**
2. **❌ Ne jamais faire `git push --force` sur main/develop**
3. **❌ Ne jamais ignorer les conflits** (toujours les résoudre)
4. **❌ Ne jamais merger sans tester**
5. **❌ Ne jamais commit de gros changements en une fois**

## 📚 Ressources

- [Git Book - Résolution de conflits](https://git-scm.com/book/fr/v2/Les-branches-avec-Git-Résoudre-les-conflits-de-fusion)
- [Atlassian - Git Merge vs Rebase](https://www.atlassian.com/git/tutorials/merging-vs-rebasing)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

## 🔧 Scripts Utiles

### Détection de conflits

```bash
# Vérifier les conflits avant commit
./scripts/check-conflicts.sh
# ou
make check-conflicts
```

### Résolution automatique

```bash
# Résoudre automatiquement les conflits simples (formatage uniquement)
python3 scripts/resolve-conflicts.py --dry-run  # Simulation
python3 scripts/resolve-conflicts.py            # Application
# ou
make resolve-conflicts
```

### Installation Pre-commit Hooks

```bash
# Installer pre-commit
pip install pre-commit

# Installer les hooks
pre-commit install

# Tester manuellement
pre-commit run --all-files
```

Les hooks détecteront automatiquement les conflits avant chaque commit.

## 🎯 Checklist Avant Chaque Commit

1. **Vérifier les conflits** :
   ```bash
   make check-conflicts
   ```

2. **Mettre à jour depuis develop** :
   ```bash
   git checkout develop
   git pull origin develop
   git checkout feature/ma-feature
   git rebase develop
   ```

3. **Tester le code** :
   ```bash
   make test
   make lint
   ```

4. **Formater le code** :
   ```bash
   make format
   ```

5. **Vérifier à nouveau les conflits** :
   ```bash
   make check-conflicts
   ```

6. **Commit** :
   ```bash
   git add .
   git commit -m "feat: description"
   ```

## ⚠️ En Cas de Conflit

1. **Ne pas paniquer** - Les conflits sont normaux
2. **Utiliser l'outil automatique** : `make resolve-conflicts`
3. **Résoudre manuellement** les conflits complexes
4. **Tester** après résolution : `make test`
5. **Vérifier** qu'il n'en reste plus : `make check-conflicts`
