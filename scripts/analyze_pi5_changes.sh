#!/bin/bash
# Script pour analyser les changements sur le Pi5 et préparer un merge intelligent

set -e

# Charger les variables d'environnement
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

echo "📊 Analyse des changements sur le Pi5..."
echo ""

# Fonction pour exécuter des commandes sur le Pi5
run_on_pi5() {
    sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI5_USERNAME}@${PI5_IP}" "$1"
}

echo "1️⃣ État du dépôt sur le Pi5:"
run_on_pi5 "cd marstek-automation && git status" || echo "⚠️ Impossible de se connecter ou le dépôt n'existe pas"
echo ""

echo "2️⃣ Derniers commits sur le Pi5:"
run_on_pi5 "cd marstek-automation && git log --oneline -5" || true
echo ""

echo "3️⃣ Fichiers modifiés (non commités):"
run_on_pi5 "cd marstek-automation && git diff --name-status HEAD" || true
echo ""

echo "4️⃣ Fichiers en staging:"
run_on_pi5 "cd marstek-automation && git diff --cached --name-status" || true
echo ""

echo "5️⃣ Fichiers non trackés:"
run_on_pi5 "cd marstek-automation && git ls-files --others --exclude-standard" || true
echo ""

echo "6️⃣ Commits sur GitHub non présents sur Pi5:"
run_on_pi5 "cd marstek-automation && git fetch origin 2>&1 && git log --oneline HEAD..origin/main" || true
echo ""

echo "7️⃣ Commits sur Pi5 non présents sur GitHub:"
run_on_pi5 "cd marstek-automation && git log --oneline origin/main..HEAD" || true
echo ""

echo "8️⃣ Statistiques des différences:"
run_on_pi5 "cd marstek-automation && git diff --stat HEAD origin/main" || true
echo ""

echo "✅ Analyse terminée"
