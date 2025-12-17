#!/bin/bash
# Finaliser le merge intelligent sur le Pi5

set -e

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PI5_IP="${PI5_IP:-192.168.1.47}"
PI5_USERNAME="${PI5_USERNAME:-fred}"
PI5_PASSWORD="${PI5_PASSWORD}"
REPO_PATH="/home/fred/marstek_client"
# Utiliser HTTPS au lieu de SSH pour éviter les problèmes de clés
GITHUB_REPO="https://github.com/fredbred/marstek_client.git"

if [ -z "$PI5_PASSWORD" ]; then
    echo "❌ PI5_PASSWORD non défini dans .env"
    exit 1
fi

run_on_pi5() {
    sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI5_USERNAME}@${PI5_IP}" "$1"
}

echo "🔄 Finalisation du merge sur le Pi5..."
echo ""

# Étape 1: Vérifier que le dépôt est initialisé
echo "1️⃣ Vérification du dépôt Git..."
GIT_INIT=$(run_on_pi5 "cd '$REPO_PATH' && git rev-parse --git-dir 2>/dev/null && echo 'OK' || echo 'NO'" 2>/dev/null || echo "NO")

if [ "$GIT_INIT" = "NO" ]; then
    echo "⚠️ Initialisation du dépôt Git..."
    run_on_pi5 "cd '$REPO_PATH' && git init && git branch -M main" || true
fi

# Étape 2: Configurer le remote avec HTTPS
echo "2️⃣ Configuration du remote origin (HTTPS)..."
run_on_pi5 "cd '$REPO_PATH' && git remote remove origin 2>/dev/null || true && git remote add origin '$GITHUB_REPO'" || true
echo ""

# Étape 3: Ajouter tous les fichiers et créer un commit initial
echo "3️⃣ Création d'un commit initial avec les fichiers locaux..."
run_on_pi5 "cd '$REPO_PATH' && git add -A && git status --short | head -10" || true
COMMIT_EXISTS=$(run_on_pi5 "cd '$REPO_PATH' && git rev-parse HEAD 2>/dev/null && echo 'YES' || echo 'NO'" 2>/dev/null || echo "NO")

if [ "$COMMIT_EXISTS" = "NO" ]; then
    run_on_pi5 "cd '$REPO_PATH' && git commit -m 'WIP: Changements locaux sur Pi5 avant merge' || echo 'Aucun changement à commiter'" || true
else
    echo "✅ Commit initial existe déjà"
fi
echo ""

# Étape 4: Fetch depuis GitHub
echo "4️⃣ Récupération des commits depuis GitHub..."
run_on_pi5 "cd '$REPO_PATH' && git fetch origin main 2>&1" || true
echo ""

# Étape 5: Afficher les différences
echo "5️⃣ Différences entre local et GitHub:"
run_on_pi5 "cd '$REPO_PATH' && git diff --stat HEAD origin/main 2>/dev/null | head -20 || echo 'Impossible de comparer (dépôt peut-être déjà à jour)'" || true
echo ""

# Étape 6: Tenter le merge
echo "6️⃣ Tentative de merge..."
MERGE_STATUS=$(run_on_pi5 "cd '$REPO_PATH' && git merge origin/main --no-commit 2>&1 && echo 'SUCCESS' || echo 'CONFLICT'" 2>/dev/null || echo "ERROR")

if [ "$MERGE_STATUS" = "SUCCESS" ]; then
    echo "✅ Merge réussi sans conflits"
    echo "7️⃣ Restauration des fichiers de configuration..."
    run_on_pi5 "cd '$REPO_PATH' && cp /tmp/pi5_backup/.env . 2>/dev/null || echo 'Fichier .env déjà présent ou backup non disponible'" || true
    echo ""
    echo "8️⃣ Finalisation du commit..."
    run_on_pi5 "cd '$REPO_PATH' && git commit -m 'Merge: Intégration GitHub avec modifications locales Pi5'" || true
    echo "✅ Merge terminé avec succès!"
elif [ "$MERGE_STATUS" = "CONFLICT" ]; then
    echo "⚠️ Conflits détectés. Résolution nécessaire:"
    echo ""
    echo "Sur le Pi5, exécutez:"
    echo "  cd $REPO_PATH"
    echo "  git status  # Voir les fichiers en conflit"
    echo "  # Résoudre les conflits manuellement"
    echo "  git add ."
    echo "  cp /tmp/pi5_backup/.env .  # Restaurer .env"
    echo "  git commit -m 'Merge: Intégration GitHub avec modifications locales Pi5'"
else
    echo "❌ Erreur lors du merge. Vérifiez manuellement."
fi

echo ""
echo "✅ Script terminé"
