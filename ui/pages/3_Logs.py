"""Logs and history page."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils import fetch_logs


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

st.title("📋 Historique")

# Filters
st.subheader("Filtres")

col1, col2, col3 = st.columns(3)

with col1:
    date_range = st.date_input(
        "Période",
        value=(date.today() - timedelta(days=7), date.today()),
        key="date_range",
    )

with col2:
    battery_filter = st.selectbox(
        "Batterie",
        ["Toutes", "Batterie 1", "Batterie 2", "Batterie 3"],
        key="battery_filter",
    )

with col3:
    mode_filter = st.selectbox(
        "Mode",
        ["Tous", "Auto", "Manual"],
        key="mode_filter",
    )

# Fetch logs
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = date.today() - timedelta(days=7)
    end_date = date.today()

with st.spinner("Chargement des logs..."):
        # #region agent log
        _debug_log("B", "pages/3_Logs.py:logs:before", "Before fetch_logs", {"start_date": str(start_date), "end_date": str(end_date)})
        # #endregion
        try:
            logs_df = fetch_logs(start_date, end_date)
            # #region agent log
            _debug_log("B", "pages/3_Logs.py:logs:after", "After fetch_logs", {"empty": logs_df.empty, "rows": len(logs_df) if not logs_df.empty else 0})
            # #endregion
        except Exception as e:
            # #region agent log
            _debug_log("B", "pages/3_Logs.py:logs:error", "fetch_logs failed", {"error": str(e), "error_type": type(e).__name__})
            # #endregion
            st.error(f"Erreur lors du chargement des logs: {e}")
            logs_df = pd.DataFrame()

# Display logs
st.subheader("Logs")

if not logs_df.empty:
    # Apply filters
    if battery_filter != "Toutes":
        battery_id = int(battery_filter.split()[-1])
        logs_df = logs_df[logs_df["battery_id"] == battery_id]

    if mode_filter != "Tous":
        logs_df = logs_df[logs_df["mode"] == mode_filter]

    # Format dataframe
    if "timestamp" in logs_df.columns:
        logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])
        logs_df = logs_df.sort_values("timestamp", ascending=False)

    # Display
    st.dataframe(
        logs_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": "Date/Heure",
            "battery_id": "Batterie",
            "soc": "SOC (%)",
            "power": "Puissance (W)",
            "mode": "Mode",
        },
    )

    # Statistics
    st.subheader("Statistiques")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if "soc" in logs_df.columns:
            avg_soc = logs_df["soc"].mean()
            st.metric("SOC Moyen", f"{avg_soc:.1f}%")

    with col2:
        if "power" in logs_df.columns:
            avg_power = logs_df["power"].mean()
            st.metric("Puissance Moyenne", f"{avg_power:.0f}W")

    with col3:
        total_records = len(logs_df)
        st.metric("Enregistrements", total_records)

    with col4:
        if "mode" in logs_df.columns:
            most_common_mode = logs_df["mode"].mode()[0] if not logs_df["mode"].empty else "N/A"
            st.metric("Mode le plus fréquent", most_common_mode)

    # Export
    st.divider()
    st.subheader("Export")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Exporter CSV", use_container_width=True):
            csv = logs_df.to_csv(index=False)
            st.download_button(
                "Télécharger CSV",
                csv,
                f"logs_{start_date}_{end_date}.csv",
                "text/csv",
                key="download_csv",
            )

    with col2:
        if st.button("📊 Exporter Excel", use_container_width=True):
            # Note: Requires openpyxl
            try:
                from io import BytesIO

                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    logs_df.to_excel(writer, index=False, sheet_name="Logs")
                excel_data = output.getvalue()
                st.download_button(
                    "Télécharger Excel",
                    excel_data,
                    f"logs_{start_date}_{end_date}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel",
                )
            except ImportError:
                st.error("openpyxl n'est pas installé. Installez-le avec: pip install openpyxl")

else:
    st.info("Aucun log disponible pour la période sélectionnée.")
    st.caption("Les logs seront disponibles une fois que le système commencera à enregistrer des données.")

# Real-time log viewer (optional)
with st.expander("📺 Visionneuse de logs en temps réel", expanded=False):
    auto_refresh_logs = st.checkbox("Actualisation automatique", value=False)

    if auto_refresh_logs:
        import time

        st.info("Actualisation toutes les 10 secondes...")
        time.sleep(10)
        st.rerun()

    # Display last 50 entries
    if not logs_df.empty:
        recent_logs = logs_df.head(50)
        st.dataframe(recent_logs, use_container_width=True, hide_index=True)
