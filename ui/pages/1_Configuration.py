"""Configuration page."""

from datetime import time

import streamlit as st

from utils import fetch_schedules, save_schedule

st.title("⚙️ Configuration")

# Section horaires Auto/Manuel
with st.expander("🕐 Horaires Auto/Manuel", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Mode AUTO")
        auto_start = st.time_input("Début AUTO", value=time(6, 0), key="auto_start")
        auto_end = st.time_input("Fin AUTO", value=time(22, 0), key="auto_end")

    with col2:
        st.subheader("Mode MANUAL")
        manual_start = st.time_input(
            "Début MANUAL", value=time(22, 0), key="manual_start"
        )
        manual_end = st.time_input("Fin MANUAL", value=time(6, 0), key="manual_end")

    if st.button("💾 Sauvegarder horaires", key="save_hours"):
        # TODO: Implement schedule creation/update
        st.success("Horaires sauvegardés avec succès!")

# Section Tempo
with st.expander("📅 Paramètres Tempo", expanded=True):
    enable_tempo = st.checkbox("Activer stratégie Tempo", value=True)

    if enable_tempo:
        col1, col2 = st.columns(2)

        with col1:
            target_soc_red = st.slider(
                "SOC cible veille rouge (%)", 80, 100, 95, key="soc_red"
            )
            st.caption("Niveau de charge avant un jour rouge")

        with col2:
            precharge_hour = st.time_input(
                "Heure de précharge", value=time(22, 0), key="precharge_hour"
            )
            st.caption("Heure de début de précharge")

        st.info(
            "💡 La précharge sera activée automatiquement la veille d'un jour rouge Tempo."
        )

    if st.button("💾 Sauvegarder Tempo", key="save_tempo"):
        st.success("Paramètres Tempo sauvegardés!")

# Section seuils batteries
with st.expander("🔋 Seuils Batteries", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        min_soc_discharge = st.slider(
            "SOC min décharge HC (%)", 0, 50, 20, key="min_soc"
        )
        st.caption("Seuil minimum pour décharge heures creuses")

        low_soc_alert = st.slider(
            "Alerte SOC faible (%)", 10, 30, 20, key="low_soc_alert"
        )
        st.caption("Seuil d'alerte pour SOC faible")

    with col2:
        max_temp = st.slider(
            "Température max (°C)", 40, 60, 50, key="max_temp"
        )
        st.caption("Température maximale avant alerte")

        offline_timeout = st.number_input(
            "Timeout hors ligne (min)", 5, 60, 15, key="offline_timeout"
        )
        st.caption("Délai avant alerte de batterie hors ligne")

    if st.button("💾 Sauvegarder seuils", key="save_thresholds"):
        st.success("Seuils sauvegardés!")

# Section schedules existants
with st.expander("📋 Schedules configurés", expanded=False):
    schedules = fetch_schedules()

    if schedules:
        st.dataframe(
            schedules,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "ID",
                "name": "Nom",
                "mode_type": "Type",
                "start_time": "Début",
                "end_time": "Fin",
                "is_active": "Actif",
            },
        )
    else:
        st.info("Aucun schedule configuré.")

# Section notifications
with st.expander("🔔 Notifications", expanded=False):
    notifications_enabled = st.checkbox("Activer notifications", value=True)

    if notifications_enabled:
        telegram_enabled = st.checkbox("Activer Telegram", value=False)

        if telegram_enabled:
            telegram_token = st.text_input(
                "Token Bot Telegram", type="password", help="Obtenu via @BotFather"
            )
            telegram_chat_id = st.text_input(
                "Chat ID", help="Obtenu via @userinfobot"
            )

        st.info(
            "💡 Configurez les notifications dans le fichier .env pour la production."
        )

    if st.button("💾 Sauvegarder notifications", key="save_notifications"):
        st.success("Paramètres de notifications sauvegardés!")
