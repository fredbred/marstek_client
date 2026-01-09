"""Configuration page."""

from datetime import time

import httpx
import streamlit as st

# API configuration
API_BASE_URL = "http://marstek-backend:8000"
API_TIMEOUT = 10.0


def fetch_tempo_config() -> dict:
    """Récupère la configuration Tempo depuis l'API."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/config/tempo", timeout=API_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"enabled": True, "target_soc_red": 95, "precharge_hour": "22:00", "precharge_power": -1000}


def save_tempo_config(enabled: bool, target_soc: int, precharge_hour: str, precharge_power: int) -> bool:
    """Sauvegarde la configuration Tempo via l'API."""
    try:
        response = httpx.put(
            f"{API_BASE_URL}/api/v1/config/tempo",
            json={
                "enabled": enabled,
                "target_soc_red": target_soc,
                "precharge_hour": precharge_hour,
                "precharge_power": precharge_power,
            },
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde: {e}")
        return False


def fetch_schedules() -> list:
    """Récupère les schedules depuis l'API."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/scheduler/schedules", timeout=API_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


st.title("⚙️ Configuration")

# Section horaires Auto/Manuel
with st.expander("🕐 Horaires Auto/Manuel", expanded=True):
    st.info("ℹ️ Les horaires sont configurés dans le scheduler backend (6h AUTO, 22h MANUAL)")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Mode AUTO")
        st.metric("Début", "06:00")
        st.metric("Fin", "22:00")

    with col2:
        st.subheader("Mode MANUAL")
        st.metric("Début", "22:00")
        st.metric("Fin", "06:00")
    
    st.caption("💡 Pour modifier ces horaires, contactez l'administrateur système.")

# Section Tempo - Charger config depuis API
with st.expander("📅 Paramètres Tempo", expanded=True):
    # Charger la config actuelle
    tempo_config = fetch_tempo_config()
    
    enable_tempo = st.checkbox(
        "Activer stratégie Tempo", 
        value=tempo_config.get("enabled", True),
        key="tempo_enabled"
    )

    if enable_tempo:
        col1, col2 = st.columns(2)

        with col1:
            target_soc_red = st.slider(
                "SOC cible veille jour rouge (%)", 
                80, 100, 
                tempo_config.get("target_soc_red", 95), 
                key="soc_red"
            )
            st.caption("🔴 Niveau de charge avant un jour rouge Tempo")

        with col2:
            # Parser l'heure depuis la config
            precharge_str = tempo_config.get("precharge_hour", "22:00")
            try:
                h, m = map(int, precharge_str.split(":"))
                precharge_default = time(h, m)
            except Exception:
                precharge_default = time(22, 0)
            
            precharge_hour = st.time_input(
                "Heure de précharge", 
                value=precharge_default, 
                key="precharge_hour"
            )
            st.caption("⏰ Heure de début de précharge automatique")

        # Puissance de charge (affichée en positif mais stockée en négatif)
        # La valeur DB est négative (-1000), on l'affiche en positif (1000)
        db_power = tempo_config.get("precharge_power", -1000)
        display_power = abs(db_power) if db_power else 1000
        
        precharge_power_display = st.slider(
            "Puissance de charge (W)",
            500, 3000,
            display_power,
            step=100,
            key="precharge_power"
        )
        st.caption("⚡ Puissance de charge par batterie (valeur négative = charge depuis réseau)")
        
        # Convertir en négatif pour le stockage
        precharge_power = -abs(precharge_power_display)

        st.info(
            f"💡 La précharge sera activée à **{precharge_hour.strftime('%H:%M')}** la veille d'un jour rouge Tempo "
            f"pour charger à **{abs(precharge_power)}W** jusqu'à **{target_soc_red}%**."
        )
    else:
        target_soc_red = 95
        precharge_hour = time(22, 0)
        precharge_power = -1000

    if st.button("💾 Sauvegarder Tempo", key="save_tempo"):
        precharge_str = precharge_hour.strftime("%H:%M")
        
        if save_tempo_config(enable_tempo, target_soc_red, precharge_str, precharge_power):
            st.success(f"✅ Configuration Tempo sauvegardée!")
            st.write(f"- SOC cible: **{target_soc_red}%**")
            st.write(f"- Heure précharge: **{precharge_str}**")
            st.write(f"- Puissance: **{abs(precharge_power)}W** (charge)")
            st.rerun()

# Section seuils batteries (informative pour l'instant)
with st.expander("🔋 Seuils Batteries", expanded=False):
    st.info("ℹ️ Les seuils sont gérés par le backend. Cette section est informative.")
    
    col1, col2 = st.columns(2)

    with col1:
        st.metric("SOC min décharge", "20%")
        st.metric("Alerte SOC faible", "20%")

    with col2:
        st.metric("Température max", "50°C")
        st.metric("Timeout hors ligne", "15 min")

# Section vérification config actuelle
with st.expander("🔍 Configuration actuelle (Debug)", expanded=False):
    st.subheader("Config Tempo dans la base de données")
    config = fetch_tempo_config()
    st.json(config)
    
    st.subheader("Correspondance")
    st.write(f"- `enabled`: {config.get('enabled')}")
    st.write(f"- `target_soc_red`: {config.get('target_soc_red')}%")
    st.write(f"- `precharge_hour`: {config.get('precharge_hour')}")
    st.write(f"- `precharge_power`: {config.get('precharge_power')}W (négatif = charge)")
