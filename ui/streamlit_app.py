"""Main Streamlit application."""

from datetime import datetime

import streamlit as st
import pandas as pd


from components.battery_card import battery_card

# #region agent log
def _debug_log(hypothesis_id, location, message, data=None):
    """Helper function for debug logging."""
    try:
        import json
        from datetime import datetime
        log_path = "/app/.cursor/debug.log"
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
# #endregion

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
# #region agent log
_debug_log("C", "streamlit_app.py:batteries:before", "Before fetch_batteries_status")
# #endregion
try:
    batteries = fetch_batteries_status()
    # #region agent log
    _debug_log("C", "streamlit_app.py:batteries:after", "After fetch_batteries_status", {"count": len(batteries) if batteries else 0})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("C", "streamlit_app.py:batteries:error", "fetch_batteries_status failed", {"error": str(e), "error_type": type(e).__name__})
    # #endregion
    st.error(f"Erreur lors de la récupération des batteries: {e}")
    batteries = []

if batteries:
    cols = st.columns(min(len(batteries), 3))
    for i, (col, battery) in enumerate(zip(cols, batteries[:3])):
        with col:
            battery_card(battery)
else:
    st.warning("Aucune batterie trouvée. Vérifiez la connexion à l'API.")

# Row 2: Power history chart
st.subheader("Historique de puissance")
# #region agent log
_debug_log("B", "streamlit_app.py:power_history:before", "Before fetch_power_history")
# #endregion
try:
    chart_data = fetch_power_history()
    # #region agent log
    _debug_log("B", "streamlit_app.py:power_history:after", "After fetch_power_history", {"empty": chart_data.empty, "rows": len(chart_data) if not chart_data.empty else 0})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("B", "streamlit_app.py:power_history:error", "fetch_power_history failed", {"error": str(e), "error_type": type(e).__name__})
    # #endregion
    st.error(f"Erreur lors de la récupération de l'historique: {e}")
    chart_data = pd.DataFrame()
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
# #region agent log
_debug_log("E", "streamlit_app.py:stats:before", "Before stats calculation", {"batteries_count": len(batteries) if batteries else 0})
# #endregion
if batteries:
    try:
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
    except Exception as e:
        # #region agent log
        _debug_log("E", "streamlit_app.py:stats:error", "Stats calculation failed", {"error": str(e), "error_type": type(e).__name__})
        # #endregion
        st.error(f"Erreur lors du calcul des statistiques: {e}")

# Footer
st.divider()
st.caption(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

