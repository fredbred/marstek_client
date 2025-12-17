"""Utility functions for Streamlit app."""

import os
from datetime import date, datetime, timedelta
from typing import Any

import httpx
import pandas as pd
import streamlit as st

# API base URL
API_BASE_URL = os.getenv("API_URL", os.getenv("API_BASE_URL", "http://localhost:8000"))
API_TIMEOUT = 30.0

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


@st.cache_data(ttl=5)
def check_api_health() -> bool:
    """Check if API is healthy.

    Returns:
        True if API is online, False otherwise
    """
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False

def fetch_batteries() -> list[dict[str, Any]]:
    """Fetch list of batteries from API.

    Returns:
        List of battery dictionaries
    """
    # #region agent log
    _debug_log("A", "utils.py:fetch_batteries:entry", "fetch_batteries called", {"api_base_url": API_BASE_URL})
    # #endregion
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/batteries", timeout=API_TIMEOUT)
        # #region agent log
        _debug_log("D", "utils.py:fetch_batteries:response", "API response received", {"status_code": response.status_code})
        # #endregion
        response.raise_for_status()
        result = response.json()
        # #region agent log
        _debug_log("A", "utils.py:fetch_batteries:success", "fetch_batteries success", {"count": len(result) if result else 0})
        # #endregion
        return result
    except Exception as e:
        # #region agent log
        _debug_log("A", "utils.py:fetch_batteries:error", "fetch_batteries failed", {"error": str(e), "error_type": type(e).__name__})
        # #endregion
        st.error(f"Erreur lors de la récupération des batteries: {e}")
        return []

def fetch_battery_status(battery_id: int) -> dict[str, Any] | None:
    """Fetch status of a specific battery.

    Args:
        battery_id: Battery ID

    Returns:
        Battery status dictionary or None if error
    """
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/batteries/{battery_id}/status", timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors de la récupération du status de la batterie {battery_id}: {e}")
        return None

def fetch_batteries_status() -> list[dict[str, Any]]:
    """Fetch status of all batteries.

    Returns:
        List of battery status dictionaries
    """
    batteries = fetch_batteries()
    statuses = []

    for battery in batteries:
        status = fetch_battery_status(battery["id"])
        if status:
            status["name"] = battery["name"]
            status["id"] = battery["id"]
            statuses.append(status)
        else:
            # Add placeholder for offline battery
            statuses.append(
                {
                    "id": battery["id"],
                    "name": battery["name"],
                    "soc": 0,
                    "power": 0,
                    "mode": "Offline",
                    "error": True,
                }
            )

    return statuses

def fetch_current_mode() -> str:
    """Fetch current mode of all batteries.

    Returns:
        Current mode string
    """
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/modes/current", timeout=API_TIMEOUT)
        response.raise_for_status()
        modes = response.json()
        if modes:
            # Return the most common mode
            mode_counts = {}
            for mode_data in modes:
                mode = mode_data.get("mode", "Unknown")
                mode_counts[mode] = mode_counts.get(mode, 0) + 1
            return max(mode_counts.items(), key=lambda x: x[1])[0]
        return "Unknown"
    except Exception as e:
        st.error(f"Erreur lors de la récupération du mode: {e}")
        return "Unknown"

def fetch_power_history(hours: int = 24) -> pd.DataFrame:
    """Fetch power history for chart.

    Args:
        hours: Number of hours to fetch

    Returns:
        DataFrame with power data
    """
    # TODO: Implement when history endpoint is available
    # For now, return empty DataFrame
    try:
        # Create date range and ensure same length
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        timestamps = pd.date_range(start=start_time, end=end_time, freq="H", inclusive="left")
        # Ensure power array matches timestamp length
        power_values = [0] * len(timestamps)
        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "power": power_values,
            }
        )
    except Exception:
        # Return empty DataFrame on error
        return pd.DataFrame(columns=["timestamp", "power"])

def fetch_tempo_today() -> str:
    """Fetch today's Tempo color.

    Returns:
        Tempo color string (BLUE, WHITE, RED, UNKNOWN)
    """
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/tempo/today", timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("color", "UNKNOWN")
    except Exception as e:
        st.error(f"Erreur lors de la récupération de la couleur Tempo: {e}")
        return "UNKNOWN"

def fetch_tempo_tomorrow() -> str:
    """Fetch tomorrow's Tempo color.

    Returns:
        Tempo color string (BLUE, WHITE, RED, UNKNOWN)
    """
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/tempo/tomorrow", timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("color", "UNKNOWN")
    except Exception as e:
        st.error(f"Erreur lors de la récupération de la couleur Tempo demain: {e}")
        return "UNKNOWN"

def fetch_tempo_calendar(start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch Tempo calendar for date range.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        DataFrame with Tempo calendar data
    """
    # #region agent log
    _debug_log("B", "utils.py:fetch_tempo_calendar:entry", "fetch_tempo_calendar called", {"start_date": str(start_date), "end_date": str(end_date)})
    # #endregion
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/tempo/calendar",
            params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            timeout=API_TIMEOUT,
        )
        # #region agent log
        _debug_log("D", "utils.py:fetch_tempo_calendar:response", "API response received", {"status_code": response.status_code})
        # #endregion
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        # #region agent log
        _debug_log("B", "utils.py:fetch_tempo_calendar:success", "fetch_tempo_calendar success", {"rows": len(df), "columns": list(df.columns) if not df.empty else []})
        # #endregion
        return df
    except Exception as e:
        # #region agent log
        _debug_log("B", "utils.py:fetch_tempo_calendar:error", "fetch_tempo_calendar failed", {"error": str(e), "error_type": type(e).__name__})
        # #endregion
        st.error(f"Erreur lors de la récupération du calendrier Tempo: {e}")
        return pd.DataFrame()

def set_auto_mode() -> bool:
    """Set all batteries to AUTO mode.

    Returns:
        True if successful, False otherwise
    """
    try:
        response = httpx.post(f"{API_BASE_URL}/api/v1/modes/auto", timeout=API_TIMEOUT)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur lors du passage en mode AUTO: {e}")
        return False

def set_manual_mode() -> bool:
    """Set all batteries to MANUAL mode.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use default manual night config
        config = {
            "time_num": 0,
            "start_time": "22:00",
            "end_time": "06:00",
            "week_set": 127,  # All days
            "power": 0,
            "enable": 1,
        }
        response = httpx.post(
            f"{API_BASE_URL}/api/v1/modes/manual", json=config, timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur lors du passage en mode MANUAL: {e}")
        return False

def fetch_schedules() -> list[dict[str, Any]]:
    """Fetch list of schedules.

    Returns:
        List of schedule dictionaries
    """
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v1/schedules", timeout=API_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des schedules: {e}")
        return []

def save_schedule(schedule_data: dict[str, Any]) -> bool:
    """Save a schedule.

    Args:
        schedule_data: Schedule data dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        response = httpx.post(
            f"{API_BASE_URL}/api/v1/schedules", json=schedule_data, timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde du schedule: {e}")
        return False

def fetch_logs(start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch logs for date range.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        DataFrame with logs
    """
    # #region agent log
    _debug_log("B", "utils.py:fetch_logs:entry", "fetch_logs called", {"start_date": str(start_date), "end_date": str(end_date)})
    # #endregion
    # TODO: Implement when logs endpoint is available
    # For now, return empty DataFrame
    # #region agent log
    _debug_log("B", "utils.py:fetch_logs:empty", "fetch_logs returning empty DataFrame (not implemented)")
    # #endregion
    return pd.DataFrame(
        {
            "timestamp": [],
            "battery_id": [],
            "soc": [],
            "power": [],
            "mode": [],
        }
    )
