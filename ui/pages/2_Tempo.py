"""Tempo calendar page."""

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from utils import fetch_tempo_calendar, fetch_tempo_today, fetch_tempo_tomorrow

st.title("📅 Calendrier Tempo")

# Today and tomorrow
col1, col2 = st.columns(2)

today_color = fetch_tempo_today()
tomorrow_color = fetch_tempo_tomorrow()

color_emoji = {"BLUE": "🔵", "WHITE": "⚪", "RED": "🔴", "UNKNOWN": "❓"}
color_names = {"BLUE": "BLEU", "WHITE": "BLANC", "RED": "ROUGE", "UNKNOWN": "INCONNU"}

with col1:
    emoji = color_emoji.get(today_color, "❓")
    name = color_names.get(today_color, "INCONNU")
    st.metric("Aujourd'hui", f"{emoji} {name}")

with col2:
    emoji = color_emoji.get(tomorrow_color, "❓")
    name = color_names.get(tomorrow_color, "INCONNU")
    st.metric("Demain", f"{emoji} {name}")

st.divider()

# Calendar view
st.subheader("Calendrier mensuel")

# Month selector
current_month = datetime.now().month
current_year = datetime.now().year

col1, col2 = st.columns(2)
with col1:
    selected_month = st.selectbox(
        "Mois",
        range(1, 13),
        index=current_month - 1,
        format_func=lambda x: datetime(current_year, x, 1).strftime("%B %Y"),
    )

with col2:
    selected_year = st.selectbox("Année", range(2024, 2026), index=0)

# Calculate date range for the month
start_date = date(selected_year, selected_month, 1)
if selected_month == 12:
    end_date = date(selected_year + 1, 1, 1) - timedelta(days=1)
else:
    end_date = date(selected_year, selected_month + 1, 1) - timedelta(days=1)

# Fetch calendar data
with st.spinner("Chargement du calendrier Tempo..."):
    calendar_data = fetch_tempo_calendar(start_date, end_date)

if not calendar_data.empty:
    # Create calendar view
    calendar_data["date"] = pd.to_datetime(calendar_data["date"]).dt.date
    calendar_data["emoji"] = calendar_data["color"].map(color_emoji)
    calendar_data["display"] = calendar_data["emoji"] + " " + calendar_data["color"]

    # Display as styled dataframe
    display_df = calendar_data[["date", "color", "display"]].copy()
    display_df.columns = ["Date", "Couleur", "Affichage"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Statistics
    st.subheader("Statistiques du mois")
    color_counts = calendar_data["color"].value_counts()

    col1, col2, col3 = st.columns(3)
    with col1:
        blue_count = color_counts.get("BLUE", 0)
        st.metric("Jours BLEUS", blue_count)
    with col2:
        white_count = color_counts.get("WHITE", 0)
        st.metric("Jours BLANCS", white_count)
    with col3:
        red_count = color_counts.get("RED", 0)
        st.metric("Jours ROUGES", red_count)

    # Remaining days info
    st.info(
        f"📊 Total: {len(calendar_data)} jours | "
        f"🔵 {blue_count} | ⚪ {white_count} | 🔴 {red_count}"
    )
else:
    st.warning("Impossible de charger le calendrier Tempo. Vérifiez la connexion à l'API.")

# Date range selector for custom range
st.divider()
st.subheader("Plage personnalisée")

col1, col2 = st.columns(2)
with col1:
    custom_start = st.date_input("Date de début", value=date.today())
with col2:
    custom_end = st.date_input("Date de fin", value=date.today() + timedelta(days=7))

if st.button("📥 Charger plage"):
    with st.spinner("Chargement..."):
        custom_data = fetch_tempo_calendar(custom_start, custom_end)

    if not custom_data.empty:
        st.dataframe(custom_data, use_container_width=True, hide_index=True)
    else:
        st.warning("Aucune donnée disponible pour cette plage.")
