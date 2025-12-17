#!/bin/bash
# Trouver le dépôt sur le Pi5 et analyser les changements

set -e

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PI5_IP="${PI5_IP:-192.168.1.47}"
PI5_USERNAME="${PI5_USERNAME:-fred}"
PI5_PASSWORD="${PI5_PASSWORD}"

if [ -z "$PI5_PASSWORD" ]; then
    echo "❌ PI5_PASSWORD non défini dans .env"
    exit 1
fi

run_on_pi5() {
    sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI5_USERNAME}@${PI5_IP}" "$1"
}

echo "🔍 Recherche du dépôt sur le Pi5..."
REPO_PATH=$(run_on_pi5 "find ~ -name '.git' -type d 2>/dev/null | grep -E 'marstek|ahw' | head -1 | xargs dirname" 2>/dev/null || echo "")

if [ -z "$REPO_PATH" ]; then
    echo "⚠️ Dépôt non trouvé. Recherche dans les répertoires courants..."
    REPO_PATH=$(run_on_pi5 "ls -d ~/marstek* ~/ahw* 2>/dev/null | head -1" 2>/dev/null || echo "")
fi

if [ -z "$REPO_PATH" ]; then
    echo "❌ Impossible de trouver le dépôt. Veuillez spécifier le chemin manuellement."
    echo "Exemple: export REPO_PATH=/home/fred/marstek-automation"
    exit 1
fi

echo "✅ Dépôt trouvé: $REPO_PATH"
echo ""

echo "📊 Analyse des changements..."
echo ""

echo "1️⃣ État du dépôt:"
run_on_pi5 "cd '$REPO_PATH' && git status" || true
echo ""

echo "2️⃣ Derniers commits:"
run_on_pi5 "cd '$REPO_PATH' && git log --oneline -5" || true
echo ""

echo "3️⃣ Fichiers modifiés:"
run_on_pi5 "cd '$REPO_PATH' && git diff --name-status HEAD" || true
echo ""

echo "4️⃣ Fichiers en staging:"
run_on_pi5 "cd '$REPO_PATH' && git diff --cached --name-status" || true
echo ""

echo "5️⃣ Fichiers non trackés:"
run_on_pi5 "cd '$REPO_PATH' && git ls-files --others --exclude-standard" || true
echo ""

echo "6️⃣ Commits sur GitHub non présents sur Pi5:"
run_on_pi5 "cd '$REPO_PATH' && git fetch origin 2>&1 && git log --oneline HEAD..origin/main" || true
echo ""

echo "7️⃣ Commits sur Pi5 non présents sur GitHub:"
run_on_pi5 "cd '$REPO_PATH' && git log --oneline origin/main..HEAD" || true
echo ""

echo "8️⃣ Fichiers différents entre HEAD et origin/main:"
run_on_pi5 "cd '$REPO_PATH' && git diff --name-status HEAD origin/main" || true
echo ""

echo "✅ Analyse terminée"
