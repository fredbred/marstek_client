# Notes d'implémentation

## Protocole UDP Marstek

Le client UDP (`marstek/api/marstek_client.py`) utilise le protocole **JSON-RPC over UDP** selon MarstekDeviceOpenApi.pdf.

### Protocole implémenté

1. **Format JSON-RPC** :
   - Requête : `{"id": 1, "method": "Bat.GetStatus", "params": {"id": 0}}`
   - Réponse : `{"id": 1, "src": "VenusC-mac", "result": {...}}`

2. **Méthodes utilisées** :
   - `Bat.GetStatus` : Status de la batterie (SOC, température, capacité)
   - `ES.GetStatus` : Informations énergétiques (puissances, énergies)
   - `ES.GetMode` : Mode actuel du device
   - `ES.SetMode` : Changer le mode (Auto, Manual, AI, Passive)

3. **Port par défaut** : 30000 (configurable entre 49152-65535)

### Configuration requise

- L'API Open doit être activée via l'application mobile Marstek
- Le port UDP doit être configuré dans l'app pour **chaque device individuellement**
  - Port par défaut: 30000
  - **Recommandation**: Utiliser des ports différents pour chaque batterie (ex: 30001, 30002, 30003)
  - Ports recommandés: entre 49152 et 65535
- Le device doit être sur le même réseau local (LAN)

### Configuration multi-batteries

Pour plusieurs batteries, il est recommandé d'utiliser des ports UDP différents :
- **Batterie 1** : Port 30001
- **Batterie 2** : Port 30002
- **Batterie 3** : Port 30003

Cela permet :
- Une meilleure organisation et traçabilité
- D'éviter les conflits potentiels
- De faciliter le debugging dans les logs

## API Tempo RTE

L'endpoint exact de l'API Tempo RTE doit être vérifié dans la documentation officielle RTE.

Actuellement configuré avec :
- URL: `https://www.api-rte.com/application/json`
- Endpoint: `/tempo`

À ajuster selon la documentation réelle.

## Déploiement

### Prérequis

1. Raspberry Pi avec Docker & Docker Compose
2. Accès réseau aux batteries Marstek (même réseau local)
3. Cloudflare Tunnel configuré (optionnel, pour accès distant)

### Configuration Cloudflare Tunnel

1. Installer `cloudflared` sur le Raspberry Pi
2. Créer un tunnel :
```bash
cloudflared tunnel create marstek
cloudflared tunnel route dns marstek streamlit.yourdomain.com
```

3. Configurer le tunnel pour exposer le port Streamlit (8501)

### Variables d'environnement

Créer un fichier `.env` (non versionné) :
```env
POSTGRES_PASSWORD=your_secure_password
MARSTEK_TELEGRAM_BOT_TOKEN=your_telegram_token
MARSTEK_TELEGRAM_CHAT_ID=your_chat_id
MARSTEK_TEMPO_CONTRACT_NUMBER=your_contract_number
```

## Monitoring

### Logs

Les logs sont structurés en JSON (par défaut) et peuvent être envoyés à :
- Un système de logging centralisé (Loki, ELK, etc.)
- Un service de monitoring (Grafana, etc.)

### Métriques

Les métriques sont stockées dans TimescaleDB et peuvent être visualisées via :
- L'interface Streamlit (dashboard intégré)
- Grafana (avec TimescaleDB comme source)

## Tests

Les tests unitaires couvrent :
- Client Marstek (avec mocks)
- Service Tempo (avec mocks)
- Configuration

Pour tester avec de vraies batteries, utiliser un environnement de test isolé.

