"""Service de notifications Telegram."""

from typing import Any

from telegram import Bot
from telegram.error import TelegramError

from marstek.core.config import TelegramConfig
from marstek.core.logger import get_logger

logger = get_logger(__name__)


class TelegramService:
    """Service pour envoyer des notifications Telegram."""

    def __init__(self, config: TelegramConfig) -> None:
        """Initialize Telegram service.

        Args:
            config: Configuration Telegram
        """
        self.config = config
        self._bot: Bot | None = None

        if config.enabled and config.bot_token:
            self._bot = Bot(token=config.bot_token)

    async def send_message(
        self, message: str, parse_mode: str | None = None
    ) -> bool:
        """Envoie un message Telegram.

        Args:
            message: Message à envoyer
            parse_mode: Mode de parsing (Markdown, HTML, etc.)

        Returns:
            True si succès, False sinon
        """
        if not self.config.enabled:
            logger.debug("telegram_disabled", message_preview=message[:50])
            return False

        if not self._bot:
            logger.warning("telegram_bot_not_initialized")
            return False

        if not self.config.chat_id:
            logger.warning("telegram_chat_id_not_configured")
            return False

        try:
            await self._bot.send_message(
                chat_id=self.config.chat_id,
                text=message,
                parse_mode=parse_mode,
            )

            logger.info("telegram_message_sent", chat_id=self.config.chat_id)
            return True

        except TelegramError as e:
            logger.error(
                "telegram_send_error",
                error=str(e),
                error_code=e.message if hasattr(e, "message") else None,
            )
            return False

    async def send_notification(
        self,
        title: str,
        message: str,
        level: str = "INFO",
    ) -> bool:
        """Envoie une notification formatée.

        Args:
            title: Titre de la notification
            message: Message détaillé
            level: Niveau (INFO, WARNING, ERROR)

        Returns:
            True si succès, False sinon
        """
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "SUCCESS": "✅",
        }

        emoji = emoji_map.get(level.upper(), "📢")

        formatted_message = f"{emoji} *{title}*\n\n{message}"

        return await self.send_message(formatted_message, parse_mode="Markdown")

    async def notify_battery_status(
        self, battery_id: str, status: dict[str, Any]
    ) -> bool:
        """Envoie une notification de status de batterie.

        Args:
            battery_id: ID de la batterie
            status: Dict avec les informations de status

        Returns:
            True si succès, False sinon
        """
        soc = status.get("soc", "N/A")
        voltage = status.get("voltage", "N/A")
        power = status.get("power", "N/A")
        mode = status.get("mode", "N/A")

        message = f"""*Batterie {battery_id}*

🔋 SOC: {soc}%
⚡ Tension: {voltage}V
💪 Puissance: {power}W
⚙️ Mode: {mode}
"""

        return await self.send_message(message, parse_mode="Markdown")

    async def notify_mode_change(
        self, battery_id: str, old_mode: str, new_mode: str
    ) -> bool:
        """Envoie une notification de changement de mode.

        Args:
            battery_id: ID de la batterie
            old_mode: Ancien mode
            new_mode: Nouveau mode

        Returns:
            True si succès, False sinon
        """
        message = f"""*Changement de mode*

Batterie: {battery_id}
Ancien mode: {old_mode}
Nouveau mode: {new_mode}
"""

        return await self.send_notification(
            "Changement de mode", message, level="INFO"
        )

    async def notify_error(
        self, battery_id: str, error_message: str
    ) -> bool:
        """Envoie une notification d'erreur.

        Args:
            battery_id: ID de la batterie
            error_message: Message d'erreur

        Returns:
            True si succès, False sinon
        """
        message = f"""*Erreur batterie*

Batterie: {battery_id}
Erreur: {error_message}
"""

        return await self.send_notification(
            "Erreur détectée", message, level="ERROR"
        )

