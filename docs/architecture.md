# Architecture du Système

Documentation de l'architecture du système d'automatisation Marstek.

## 📐 Vue d'ensemble

Le système Marstek Automation est une application distribuée qui gère automatiquement 3 batteries Marstek Venus-E via une API UDP, avec intégration Tempo RTE et notifications Telegram.

## 🏗️ Architecture générale

\`\`\`mermaid
graph TB
    subgraph "Raspberry Pi / Serveur"
        subgraph "Docker Compose"
            UI[Streamlit UI<br/>Port 8501]
            API[FastAPI Backend<br/>Port 8000]
            Worker[RQ Worker]
        end
        
        subgraph "Services"
            DB[(PostgreSQL<br/>+ TimescaleDB)]
            Redis[(Redis Cache)]
        end
        
        subgraph "External"
            TempoAPI[Tempo RTE API]
            Telegram[Telegram Bot]
        end
    end
    
    subgraph "Réseau Local"
        Batt1[Batterie 1<br/>192.168.1.100:30001]
        Batt2[Batterie 2<br/>192.168.1.101:30002]
        Batt3[Batterie 3<br/>192.168.1.102:30003]
    end
    
    subgraph "Accès Distant"
        Cloudflare[Cloudflare Tunnel]
        User[Utilisateur Web]
    end
    
    UI --> API
    API --> DB
    API --> Redis
    API --> Batt1
    API --> Batt2
    API --> Batt3
    API --> TempoAPI
    API --> Telegram
    Worker --> DB
    Worker --> Redis
    Cloudflare --> UI
    Cloudflare --> API
    User --> Cloudflare
\`\`\`

## 🔄 Flux de données

### 1. Découverte des batteries

\`\`\`mermaid
sequenceDiagram
    participant User
    participant API
    participant UDPClient
    participant Battery
    
    User->>API: POST /api/v1/batteries/discover
    API->>UDPClient: broadcast_discover()
    UDPClient->>Battery: UDP Broadcast
    Battery-->>UDPClient: Device Info
    UDPClient-->>API: List[DeviceInfo]
    API->>API: Register/Update in DB
    API-->>User: List[BatteryResponse]
\`\`\`

## 🗄️ Schéma de base de données

### Diagramme ER

\`\`\`mermaid
erDiagram
    Battery ||--o{ BatteryStatusLog : "has"
    ScheduleConfig ||--o{ APSchedulerJob : "triggers"
    
    Battery {
        int id PK
        string name
        string ip_address
        int udp_port
        string ble_mac UK
        string wifi_mac
        bool is_active
        datetime last_seen_at
    }
    
    BatteryStatusLog {
        int battery_id PK,FK
        datetime timestamp PK
        int soc
        float bat_power
        float pv_power
        float ongrid_power
        float offgrid_power
        string mode
        float bat_temp
        float bat_capacity
    }
    
    ScheduleConfig {
        int id PK
        string name
        string mode_type
        time start_time
        time end_time
        int week_days
        int power_setpoint
        bool is_active
    }
\`\`\`

## 🔧 Composants principaux

### Backend (FastAPI)

\`\`\`
backend/app/
├── main.py                 # Point d'entrée FastAPI
├── config.py              # Configuration Pydantic
├── database.py            # Session DB async
├── core/
│   ├── marstek_client.py  # Client UDP Marstek
│   ├── battery_manager.py # Orchestration batteries
│   ├── mode_controller.py # Logique modes
│   └── tempo_service.py   # Service Tempo RTE
├── api/
│   └── routes/            # Endpoints REST
├── models/                # Modèles SQLAlchemy
├── scheduler/             # APScheduler jobs
└── notifications/         # Système notifications
\`\`\`
