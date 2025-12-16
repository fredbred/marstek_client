#!/bin/bash
# Script pour faire un merge intelligent des changements du Pi5 avec le dépôt GitHub

set -e

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PI5_IP="${PI5_IP:-192.168.1.47}"
PI5_USERNAME="${PI5_USERNAME:-fred}"
PI5_PASSWORD="${PI5_PASSWORD}"
REPO_PATH="/home/fred/marstek_client"
GITHUB_REPO="git@github.com:fredbred/marstek_client.git"

if [ -z "$PI5_PASSWORD" ]; then
    echo "❌ PI5_PASSWORD non défini dans .env"
    exit 1
fi

run_on_pi5() {
    sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI5_USERNAME}@${PI5_IP}" "$1"
}

echo "🔄 Merge intelligent des changements du Pi5..."
echo ""

# Étape 1: Sauvegarder les fichiers de configuration importants
echo "1️⃣ Sauvegarde des fichiers de configuration..."
run_on_pi5 "cd '$REPO_PATH' && mkdir -p /tmp/pi5_backup && cp -v .env docker-compose.yml config/*.yaml /tmp/pi5_backup/ 2>/dev/null || true" || true
echo "✅ Fichiers sauvegardés dans /tmp/pi5_backup/"
echo ""

# Étape 2: Initialiser le dépôt Git si nécessaire
echo "2️⃣ Vérification de l'état Git..."
GIT_INIT=$(run_on_pi5 "cd '$REPO_PATH' && git rev-parse --git-dir 2>/dev/null && echo 'OK' || echo 'NO'" 2>/dev/null || echo "NO")

if [ "$GIT_INIT" = "NO" ]; then
    echo "⚠️ Dépôt Git non initialisé. Initialisation..."
    run_on_pi5 "cd '$REPO_PATH' && git init && git branch -M main" || true
fi

# Étape 3: Configurer le remote origin
echo "3️⃣ Configuration du remote origin..."
run_on_pi5 "cd '$REPO_PATH' && git remote remove origin 2>/dev/null || true && git remote add origin '$GITHUB_REPO'" || true
echo ""

# Étape 4: Commit initial des fichiers locaux
echo "4️⃣ Création d'un commit initial avec les fichiers locaux..."
run_on_pi5 "cd '$REPO_PATH' && git add -A && git commit -m 'WIP: Changements locaux sur Pi5 avant merge' 2>/dev/null || echo 'Aucun changement à commiter'" || true
echo ""

# Étape 5: Fetch depuis GitHub
echo "5️⃣ Récupération des commits depuis GitHub..."
run_on_pi5 "cd '$REPO_PATH' && git fetch origin main" || true
echo ""

# Étape 6: Afficher les différences
echo "6️⃣ Différences entre local et GitHub:"
run_on_pi5 "cd '$REPO_PATH' && git diff --stat HEAD origin/main 2>/dev/null || echo 'Impossible de comparer'" || true
echo ""

echo "✅ Préparation terminée"
echo ""
echo "📌 Pour finaliser le merge, exécutez sur le Pi5:"
echo "   cd $REPO_PATH"
echo "   git merge origin/main --no-commit"
echo "   # Examiner les conflits et les résoudre"
echo "   # Restaurer les fichiers de configuration: cp /tmp/pi5_backup/.env ."
echo "   git commit -m 'Merge: Intégration des changements GitHub avec modifications locales Pi5'"
