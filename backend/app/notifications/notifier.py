"""Notification system using Apprise."""

from datetime import datetime
from typing import TYPE_CHECKING

import structlog
from apprise import Apprise

from app.config import get_settings
from app.core.tempo_service import TempoColor

if TYPE_CHECKING:
    from app.models import Battery

logger = structlog.get_logger(__name__)
settings = get_settings()


# Message templates
TEMPLATES = {
    "mode_changed": """
🔄 *Changement de Mode*

Ancien: {old_mode}
Nouveau: {new_mode}
Heure: {timestamp}

Batteries affectées: {battery_count}
    """,
    "tempo_red_alert": """
🔴 *ALERTE TEMPO ROUGE*

Demain sera un jour ROUGE
Charge batterie activée: {target_soc}%

Jours rouges restants: {remaining_red}
    """,
    "tempo_blue_alert": """
🔵 *INFO TEMPO BLEU*

Demain sera un jour BLEU
Mode économique activé

Jours bleus restants: {remaining_blue}
    """,
    "battery_issue": """
⚠️ *Problème Batterie*

Batterie: {battery_name} ({battery_id})
IP: {ip_address}

Problème: {issue}
Heure: {timestamp}
    """,
    "battery_low_soc": """
🔋 *Batterie Faible*

Batterie: {battery_name} ({battery_id})
SOC: {soc}%

Seuil d'alerte: {threshold}%
Heure: {timestamp}
    """,
    "battery_offline": """
📴 *Batterie Hors Ligne*

Batterie: {battery_name} ({battery_id})
IP: {ip_address}

Dernière connexion: {last_seen}
Heure: {timestamp}
    """,
}


class Notifier:
    """Notification service using Apprise."""

    def __init__(self) -> None:
        self.enabled = settings.notification.enabled

        if not self.enabled:
            logger.info("notifications_disabled")
            self.apprise = None
            return

        self.apprise = Apprise()

        # Add Telegram notification if configured
        if settings.notification.telegram_enabled:
            if (
                settings.notification.telegram_bot_token
                and settings.notification.telegram_chat_id
            ):
                telegram_url = (
                    f"tgram://{settings.notification.telegram_bot_token}/"
                    f"{settings.notification.telegram_chat_id}"
                )
                self.apprise.add(telegram_url)
                logger.info("telegram_notification_added")
            else:
                logger.warning("telegram_config_incomplete")

        # Add Apprise URLs if provided
        if settings.notification.urls:
            for url in settings.notification.urls.split(","):
                url = url.strip()
                if url:
                    self.apprise.add(url)
                    logger.info("notification_url_added", url=url[:20] + "...")

        if not self.apprise:
            logger.warning("no_notification_channels_configured")

    async def send_info(self, title: str, message: str) -> bool:
        """Send informational notification.

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            body = f"*{title}*\n\n{message}"
            result = await self._send_async(body, body_format="markdown")

            logger.info("notification_sent", level="info", title=title)
            return result

        except Exception as e:
            logger.error("notification_send_error", level="info", error=str(e))
            return False

    async def send_warning(self, title: str, message: str) -> bool:
        """Send warning notification.

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            body = f"⚠️ *{title}*\n\n{message}"
            result = await self._send_async(body, body_format="markdown")

            logger.info("notification_sent", level="warning", title=title)
            return result

        except Exception as e:
            logger.error("notification_send_error", level="warning", error=str(e))
            return False

    async def send_error(self, title: str, message: str) -> bool:
        """Send error notification.

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            body = f"❌ *{title}*\n\n{message}"
            result = await self._send_async(body, body_format="markdown")

            logger.info("notification_sent", level="error", title=title)
            return result

        except Exception as e:
            logger.error("notification_send_error", level="error", error=str(e))
            return False

    async def notify_mode_changed(
        self, old_mode: str, new_mode: str, battery_count: int = 1
    ) -> bool:
        """Notify about mode change.

        Args:
            old_mode: Previous mode
            new_mode: New mode
            battery_count: Number of batteries affected

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = TEMPLATES["mode_changed"].format(
                old_mode=old_mode,
                new_mode=new_mode,
                timestamp=timestamp,
                battery_count=battery_count,
            )

            result = await self.send_info("Changement de Mode", message.strip())

            logger.info(
                "mode_change_notified",
                old_mode=old_mode,
                new_mode=new_mode,
                battery_count=battery_count,
            )

            return result

        except Exception as e:
            logger.error("mode_change_notification_error", error=str(e))
            return False

    async def notify_tempo_alert(
        self,
        color: TempoColor,
        target_soc: int | None = None,
        remaining_days: dict[str, int] | None = None,
    ) -> bool:
        """Notify about Tempo color alert.

        Args:
            color: Tempo color (RED, BLUE, etc.)
            target_soc: Target SOC for precharge (for RED days)
            remaining_days: Remaining days by color

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            if color == TempoColor.RED:
                remaining_red = remaining_days.get("RED", 0) if remaining_days else 0
                message = TEMPLATES["tempo_red_alert"].format(
                    target_soc=target_soc or 100,
                    remaining_red=remaining_red,
                )
                result = await self.send_warning("Alerte Tempo Rouge", message.strip())

            elif color == TempoColor.BLUE:
                remaining_blue = remaining_days.get("BLUE", 0) if remaining_days else 0
                message = TEMPLATES["tempo_blue_alert"].format(
                    remaining_blue=remaining_blue,
                )
                result = await self.send_info("Info Tempo Bleu", message.strip())

            else:
                # WHITE or UNKNOWN - no alert
                return False

            logger.info("tempo_alert_notified", color=color.value)

            return result

        except Exception as e:
            logger.error("tempo_alert_notification_error", error=str(e))
            return False

    async def notify_battery_issue(self, battery: "Battery", issue: str) -> bool:
        """Notify about battery issue.

        Args:
            battery: Battery instance
            issue: Issue description

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = TEMPLATES["battery_issue"].format(
                battery_name=battery.name,
                battery_id=battery.id,
                ip_address=battery.ip_address,
                issue=issue,
                timestamp=timestamp,
            )

            result = await self.send_warning("Problème Batterie", message.strip())

            logger.info("battery_issue_notified", battery_id=battery.id, issue=issue)

            return result

        except Exception as e:
            logger.error("battery_issue_notification_error", error=str(e))
            return False

    async def notify_battery_low_soc(
        self, battery: "Battery", soc: int, threshold: int = 20
    ) -> bool:
        """Notify about low battery SOC.

        Args:
            battery: Battery instance
            soc: Current SOC percentage
            threshold: Alert threshold

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = TEMPLATES["battery_low_soc"].format(
                battery_name=battery.name,
                battery_id=battery.id,
                soc=soc,
                threshold=threshold,
                timestamp=timestamp,
            )

            result = await self.send_warning("Batterie Faible", message.strip())

            logger.info(
                "battery_low_soc_notified",
                battery_id=battery.id,
                soc=soc,
                threshold=threshold,
            )

            return result

        except Exception as e:
            logger.error("battery_low_soc_notification_error", error=str(e))
            return False

    async def notify_battery_offline(
        self, battery: "Battery", last_seen: datetime | None = None
    ) -> bool:
        """Notify about battery going offline.

        Args:
            battery: Battery instance
            last_seen: Last seen timestamp

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            last_seen_str = (
                last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else "Jamais"
            )

            message = TEMPLATES["battery_offline"].format(
                battery_name=battery.name,
                battery_id=battery.id,
                ip_address=battery.ip_address,
                last_seen=last_seen_str,
                timestamp=timestamp,
            )

            result = await self.send_warning("Batterie Hors Ligne", message.strip())

            logger.info("battery_offline_notified", battery_id=battery.id)

            return result

        except Exception as e:
            logger.error("battery_offline_notification_error", error=str(e))
            return False

    async def _send_async(self, body: str, body_format: str = "text") -> bool:
        """Send notification asynchronously.

        Args:
            body: Message body
            body_format: Message format (text, markdown, html)

        Returns:
            True if sent successfully, False otherwise
        """
        import asyncio

        # Apprise doesn't have native async support, so we run it in executor
        loop = asyncio.get_event_loop()

        def _send_sync() -> bool:
            """Send notification synchronously."""
            if self.apprise is None:
                return False
            try:
                return bool(self.apprise.notify(body=body, body_format=body_format))

            except Exception as e:
                logger.error("apprise_notify_error", error=str(e))
                return False

        return await loop.run_in_executor(None, _send_sync)
