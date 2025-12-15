"""Interface Streamlit pour monitoring et configuration."""

import asyncio
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from marstek.core.config import AppConfig
from marstek.core.logger import get_logger
from marstek.database.models import Database
from marstek.database.repository import (
    BatteryStatusRepository,
    ModeChangeRepository,
    TempoRepository,
)

logger = get_logger(__name__)

# Configuration
CONFIG_PATH = Path("config/config.yaml")


@st.cache_resource
def load_config() -> AppConfig:
    """Charge la configuration (cached)."""
    return AppConfig.from_yaml(CONFIG_PATH)


@st.cache_resource
def get_database() -> Database:
    """Obtient la connexion DB (cached)."""
    config = load_config()
    return Database(config.database)


async def get_latest_status() -> dict[str, Any]:
    """Récupère le dernier status de toutes les batteries."""
    db = get_database()
    async with db.async_session() as session:
        repo = BatteryStatusRepository(session)
        records = await repo.get_latest_status()
        return {r.battery_id: r for r in records}


async def get_status_history(battery_id: str, hours: int = 24) -> pd.DataFrame:
    """Récupère l'historique des status."""
    from datetime import datetime, timedelta

    db = get_database()
    async with db.async_session() as session:
        repo = BatteryStatusRepository(session)
        start_time = datetime.utcnow() - timedelta(hours=hours)
        records = await repo.get_status_history(battery_id, start_time)

        data = [
            {
                "timestamp": r.timestamp,
                "soc": r.soc,
                "voltage": r.voltage,
                "current": r.current,
                "power": r.power,
                "temperature": r.temperature,
                "mode": r.mode,
            }
            for r in records
        ]

        return pd.DataFrame(data)


async def get_recent_mode_changes(limit: int = 20) -> pd.DataFrame:
    """Récupère les changements de mode récents."""
    db = get_database()
    async with db.async_session() as session:
        repo = ModeChangeRepository(session)
        records = await repo.get_recent_changes(limit=limit)

        data = [
            {
                "timestamp": r.timestamp,
                "battery_id": r.battery_id,
                "old_mode": r.old_mode,
                "new_mode": r.new_mode,
                "reason": r.reason,
                "success": r.success,
            }
            for r in records
        ]

        return pd.DataFrame(data)


def main() -> None:
    """Point d'entrée principal de l'application Streamlit."""
    st.set_page_config(
        page_title="Marstek Automation",
        page_icon="🔋",
        layout="wide",
    )

    st.title("🔋 Marstek Automation Dashboard")

    try:
        config = load_config()
    except FileNotFoundError:
        st.error(f"Configuration file not found: {CONFIG_PATH}")
        st.info("Please create config/config.yaml from config.example.yaml")
        return

    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        st.write(f"**Batteries:** {len(config.batteries)}")
        st.write(f"**Timezone:** {config.scheduler.timezone}")

        st.header("Navigation")
        page = st.radio(
            "Page",
            ["Dashboard", "Historique", "Changements de mode", "Configuration"],
        )

    # Main content
    if page == "Dashboard":
        st.header("Status des batteries")

        # Récupérer les status
        status_dict = asyncio.run(get_latest_status())

        # Afficher les cartes pour chaque batterie
        cols = st.columns(len(config.batteries))

        for idx, battery_config in enumerate(config.batteries):
            with cols[idx]:
                st.subheader(battery_config.name)
                st.caption(f"ID: {battery_config.id}")

                if battery_config.id in status_dict:
                    status = status_dict[battery_config.id]

                    # SOC
                    soc = status.soc or 0
                    st.metric("SOC", f"{soc:.1f}%")
                    st.progress(soc / 100)

                    # Autres métriques
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Tension", f"{status.voltage or 0:.1f}V")
                        st.metric("Puissance", f"{status.power or 0:.0f}W")
                    with col2:
                        st.metric("Courant", f"{status.current or 0:.1f}A")
                        st.metric("Température", f"{status.temperature or 0:.1f}°C")

                    st.caption(f"Mode: {status.mode or 'UNKNOWN'}")
                    st.caption(f"Dernière mise à jour: {status.timestamp}")

                else:
                    st.warning("Aucune donnée disponible")

    elif page == "Historique":
        st.header("Historique des status")

        battery_id = st.selectbox(
            "Batterie",
            [b.id for b in config.batteries],
        )

        hours = st.slider("Période (heures)", 1, 168, 24)

        if st.button("Charger l'historique"):
            with st.spinner("Chargement..."):
                df = asyncio.run(get_status_history(battery_id, hours))

                if not df.empty:
                    st.line_chart(df.set_index("timestamp")[["soc", "voltage", "power"]])

                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Aucune donnée disponible pour cette période")

    elif page == "Changements de mode":
        st.header("Historique des changements de mode")

        limit = st.slider("Nombre d'événements", 10, 100, 20)

        if st.button("Charger les changements"):
            with st.spinner("Chargement..."):
                df = asyncio.run(get_recent_mode_changes(limit))

                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Aucun changement de mode enregistré")

    elif page == "Configuration":
        st.header("Configuration")

        st.subheader("Batteries")
        for battery in config.batteries:
            with st.expander(battery.name):
                st.write(f"**ID:** {battery.id}")
                st.write(f"**IP:** {battery.ip}")
                st.write(f"**Port:** {battery.port}")

        st.subheader("Modes")
        st.json({
            "AUTO": {
                "start": f"{config.modes['auto'].start_hour}:00",
                "end": f"{config.modes['auto'].end_hour}:00",
            },
            "MANUAL": {
                "start": f"{config.modes['manual'].start_hour}:00",
                "end": f"{config.modes['manual'].end_hour}:00",
            },
        })

        st.subheader("Services")
        st.write(f"**Tempo RTE:** {'✅ Activé' if config.tempo.enabled else '❌ Désactivé'}")
        st.write(f"**Telegram:** {'✅ Activé' if config.telegram.enabled else '❌ Désactivé'}")


if __name__ == "__main__":
    main()

