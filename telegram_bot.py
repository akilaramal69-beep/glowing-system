import logging
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

class TelegramReporter:
    def __init__(self):
        self.enabled = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        if self.enabled:
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            logger.info("Telegram notifications enabled.")
        else:
            logger.warning("Telegram configuration missing. Notifications disabled.")

    async def send_message(self, text: str):
        if not self.enabled:
            return
        try:
            await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def report_buy(self, token_address: str, amount_sol: float, signature: str = None):
        msg = (
            f"🚀 *BUY EXECUTED*\n\n"
            f"Token: `{token_address}`\n"
            f"Amount: `{amount_sol} SOL`\n"
            f"TX: [Solscan](https://solscan.io/tx/{signature})" if signature else ""
        )
        await self.send_message(msg)

    async def report_error(self, error_msg: str):
        await self.send_message(f"⚠️ *ERROR*\n\n{error_msg}")

    async def report_status(self, status: str):
        await self.send_message(f"ℹ️ *STATUS UPDATE*\n\n{status}")

# Global instance
telegram_reporter = TelegramReporter()
