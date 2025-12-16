# Documentation API

Documentation complète de l'API REST Marstek Automation.

## 📚 Base URL

```
http://localhost:8000/api/v1
```

## 📖 Documentation OpenAPI

La documentation interactive est disponible à :
- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`
- **OpenAPI JSON** : `http://localhost:8000/openapi.json`

## 🔋 Endpoints Batteries

### Liste des batteries

```http
GET /api/v1/batteries
```

**Exemple curl :**
```bash
curl -X GET "http://localhost:8000/api/v1/batteries"
```

### Statut d'une batterie

```http
GET /api/v1/batteries/{battery_id}/status
```

**Exemple curl :**
```bash
curl -X GET "http://localhost:8000/api/v1/batteries/1/status"
```

### Découvrir les batteries

```http
POST /api/v1/batteries/discover
```

**Exemple curl :**
```bash
curl -X POST "http://localhost:8000/api/v1/batteries/discover"
```

## ⚙️ Endpoints Modes

### Passer en mode AUTO

```http
POST /api/v1/modes/auto
```

**Exemple curl :**
```bash
curl -X POST "http://localhost:8000/api/v1/modes/auto"
```

## 📅 Endpoints Tempo

### Couleur Tempo aujourd'hui

```http
GET /api/v1/tempo/today
```

**Exemple curl :**
```bash
curl -X GET "http://localhost:8000/api/v1/tempo/today"
```

Voir la documentation complète dans Swagger UI pour tous les endpoints.
