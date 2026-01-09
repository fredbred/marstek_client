"""Reusable battery card component."""

from typing import Any

import streamlit as st


def battery_card(battery_data: dict[str, Any]) -> None:
    """Display a battery card component.

    Args:
        battery_data: Dictionary with battery data (id, name, soc, power, mode, etc.)
    """
    battery_id = battery_data.get("id", 0)
    battery_name = battery_data.get("name", f"Batterie {battery_id}")
    soc = battery_data.get("soc", 0)
    power = battery_data.get("bat_power", 0) or battery_data.get("power", 0)
    mode = battery_data.get("mode", "Unknown")
    error_msg = battery_data.get("error")
    is_offline = error_msg is True or error_msg == "No cached data - wait for scheduler"
    is_stale = isinstance(error_msg, str) and "timeout" in error_msg.lower()
    cache_age = battery_data.get("cache_age_seconds", 0)
    is_cache_old = cache_age > 600  # Plus de 10 minutes

    # Card container
    with st.container():
        # Header
        if is_offline:
            st.error(f"🔋 {battery_name} - 📴 Hors ligne")
        elif is_stale or is_cache_old:
            st.warning(f"🔋 {battery_name} - ⚠️ Données en cache")
        else:
            st.subheader(f"🔋 {battery_name}")

        # SOC metric
        if is_offline:
            st.metric("SOC", "N/A", delta=None)
            st.progress(0.0)
        else:
            delta_power = f"{power:+.0f}W" if power else None
            st.metric("SOC", f"{soc}%", delta=delta_power)
            st.progress(soc / 100.0)

        # Additional info
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Mode: {mode}")
        with col2:
            if not is_offline:
                temp = battery_data.get("bat_temp")
                if temp:
                    st.caption(f"Temp: {temp:.1f}°C")

        # Power details
        if not is_offline:
            with st.expander("Détails"):
                pv_power = battery_data.get("pv_power", 0) or 0
                ongrid_power = battery_data.get("ongrid_power", 0) or 0
                offgrid_power = battery_data.get("offgrid_power", 0) or 0

                st.write(f"**PV:** {pv_power:.0f}W")
                st.write(f"**Réseau:** {ongrid_power:.0f}W")
                st.write(f"**Hors réseau:** {offgrid_power:.0f}W")

                capacity = battery_data.get("bat_capacity")
                if capacity:
                    st.write(f"**Capacité restante:** {capacity:.0f}Wh")
