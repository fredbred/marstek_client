#!/bin/bash
# Préparer un merge intelligent entre les changements locaux du Pi5 et le dépôt GitHub

set -e

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PI5_IP="${PI5_IP:-192.168.1.47}"
PI5_USERNAME="${PI5_USERNAME:-fred}"
PI5_PASSWORD="${PI5_PASSWORD}"
REPO_PATH="/home/fred/marstek_client"

if [ -z "$PI5_PASSWORD" ]; then
    echo "❌ PI5_PASSWORD non défini dans .env"
    exit 1
fi

run_on_pi5() {
    sshpass -p "$PI5_PASSWORD" ssh -o StrictHostKeyChecking=no "${PI5_USERNAME}@${PI5_IP}" "$1"
}

echo "📊 Analyse détaillée des changements sur le Pi5..."
echo ""

# Vérifier si le dépôt existe
if ! run_on_pi5 "test -d '$REPO_PATH'" 2>/dev/null; then
    echo "❌ Le dépôt $REPO_PATH n'existe pas sur le Pi5"
    exit 1
fi

echo "✅ Dépôt trouvé: $REPO_PATH"
echo ""

# Analyser les fichiers modifiés localement sur le Pi5
echo "📝 Fichiers modifiés localement (à préserver):"
run_on_pi5 "cd '$REPO_PATH' && find . -type f -name '*.env' -o -name '*.log' -o -name '*.pyc' -o -name '__pycache__' -prune -o -type f -newermt '2024-12-15' -print 2>/dev/null | head -20" || true
echo ""

# Vérifier les fichiers de configuration spécifiques au Pi5
echo "🔧 Fichiers de configuration à préserver:"
run_on_pi5 "cd '$REPO_PATH' && ls -la .env docker-compose.override.yml config/*.yaml 2>/dev/null | head -10" || true
echo ""

# Créer un rapport détaillé
echo "📋 Création d'un rapport détaillé..."
run_on_pi5 "cd '$REPO_PATH' && cat > /tmp/pi5_changes_report.txt << 'REPORTEOF'
=== RAPPORT DES CHANGEMENTS SUR PI5 ===
Date: $(date)

Fichiers modifiés récemment:
$(find . -type f -name '*.py' -o -name '*.yaml' -o -name '*.yml' -o -name '*.sh' | xargs ls -lt 2>/dev/null | head -20)

Fichiers de configuration:
$(ls -la .env docker-compose*.yml config/*.yaml 2>/dev/null)

Fichiers dans .gitignore qui pourraient être modifiés:
$(find . -name '.env' -o -name '*.log' -o -name 'poetry.lock' 2>/dev/null)
REPORTEOF
cat /tmp/pi5_changes_report.txt" 2>&1 || true
echo ""

echo "✅ Analyse terminée"
echo ""
echo "📌 Prochaines étapes recommandées:"
echo "1. Examiner les fichiers de configuration (.env, docker-compose.yml, etc.)"
echo "2. Sauvegarder les changements locaux importants"
echo "3. Initialiser le dépôt Git sur le Pi5"
echo "4. Configurer le remote origin"
echo "5. Faire un merge intelligent"
