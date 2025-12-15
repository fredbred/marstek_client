"""Main Streamlit application."""

from datetime import datetime

import streamlit as st

from components.battery_card import battery_card
from utils import (
    check_api_health,
    fetch_batteries_status,
    fetch_current_mode,
    fetch_power_history,
    set_auto_mode,
    set_manual_mode,
)

# Page configuration
st.set_page_config(
    page_title="Marstek Control",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar
with st.sidebar:
    st.title("⚡ Marstek Automation")

    # API status
    api_status = check_api_health()
    status_emoji = "🟢" if api_status else "🔴"
    status_text = "Online" if api_status else "Offline"
    st.metric("API Status", f"{status_emoji} {status_text}")

    st.divider()

    # Quick actions
    st.subheader("Actions rapides")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 AUTO", use_container_width=True):
            if set_auto_mode():
                st.success("Mode AUTO activé")
                st.rerun()

    with col2:
        if st.button("🔧 MANUAL", use_container_width=True):
            if set_manual_mode():
                st.success("Mode MANUAL activé")
                st.rerun()

    st.divider()

    # Refresh button
    if st.button("🔄 Actualiser", use_container_width=True):
        st.rerun()

# Main dashboard
st.title("🔋 Dashboard Batteries")

# Auto-refresh
auto_refresh = st.checkbox("🔄 Actualisation automatique (30s)", value=False)
if auto_refresh:
    import time

    time.sleep(30)
    st.rerun()

# Row 1: Battery cards
st.subheader("État des batteries")
batteries = fetch_batteries_status()

if batteries:
    cols = st.columns(min(len(batteries), 3))
    for i, (col, battery) in enumerate(zip(cols, batteries[:3])):
        with col:
            battery_card(battery)
else:
    st.warning("Aucune batterie trouvée. Vérifiez la connexion à l'API.")

# Row 2: Power history chart
st.subheader("Historique de puissance")
chart_data = fetch_power_history()
if not chart_data.empty:
    st.line_chart(chart_data.set_index("timestamp")["power"])
else:
    st.info("Aucune donnée historique disponible pour le moment.")

# Row 3: Current mode
st.subheader("Mode actuel")
current_mode = fetch_current_mode()
mode_emoji = {"Auto": "🔄", "Manual": "🔧", "Unknown": "❓"}.get(current_mode, "❓")
st.info(f"{mode_emoji} Mode actuel: **{current_mode}**")

# Row 4: Quick stats
st.subheader("Statistiques rapides")
if batteries:
    avg_soc = sum(b.get("soc", 0) for b in batteries if not b.get("error")) / max(
        len([b for b in batteries if not b.get("error")]), 1
    )
    total_power = sum(b.get("bat_power", 0) or b.get("power", 0) for b in batteries)
    online_count = len([b for b in batteries if not b.get("error")])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("SOC Moyen", f"{avg_soc:.1f}%")
    with col2:
        st.metric("Puissance Totale", f"{total_power:.0f}W")
    with col3:
        st.metric("Batteries Online", f"{online_count}/{len(batteries)}")

# Footer
st.divider()
st.caption(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
