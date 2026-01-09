#!/bin/bash
set -e

# Créer le répertoire logs avec les bonnes permissions
mkdir -p /app/logs
chmod 777 /app/logs 2>/dev/null || true

# Si le venv n'existe pas, l'installer
if [ ! -d ".venv" ]; then
    echo "📦 Installation des dépendances..."
    poetry lock --no-update 2>/dev/null || true
    poetry install --no-root --only main
fi

# Vérifier que uvicorn est installé
if [ ! -f ".venv/bin/uvicorn" ]; then
    echo "📦 Installation de uvicorn..."
    poetry install --no-root --only main
fi

# Exécuter la commande passée en argument
exec "$@"
