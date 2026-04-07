import os
from dotenv import load_dotenv

load_dotenv()

# RPC Configuration
RPC_ENDPOINT = os.getenv("RPC_ENDPOINT", "https://api.mainnet-beta.solana.com")
FALLBACK_RPC = os.getenv("FALLBACK_RPC", "https://api.mainnet-beta.solana.com")
WSS_ENDPOINT = os.getenv("WSS_ENDPOINT", "wss://api.mainnet-beta.solana.com")

# DEX Programs
RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
PUMP_FUN_PROGRAM = "6EF8rrecthJ5Dwk84S5aB4x7YF9wYc6iV6h51zJ8U6S"

# Bot Operation Mode
BOT_MODE = os.getenv("BOT_MODE", "COPY_TRADE").upper() # COPY_TRADE or ALGO_SNIPER

# Jito Configuration
JITO_ENDPOINT = os.getenv("JITO_ENDPOINT", "https://mainnet.block-engine.jito.wtf")
JITO_UUID = os.getenv("JITO_UUID", "")  # Optional
JITO_TIP_AMOUNT_SOL = float(os.getenv("JITO_TIP_AMOUNT_SOL", "0.0001"))

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Wallet Configuration
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
SMART_WALLETS = os.getenv("SMART_WALLETS", "").split(",")
SMART_WALLETS = [w.strip() for w in SMART_WALLETS if w.strip()]

# Trading Logic
MAX_POSITION_SOL = float(os.getenv("MAX_POSITION_SOL", "0.5"))
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "15"))
SLIPPAGE_LIMIT = float(os.getenv("SLIPPAGE_LIMIT", "20"))
CONFIRMATION_COUNT = int(os.getenv("CONFIRMATION_COUNT", "2"))
CONFIRMATION_WINDOW_SECONDS = int(os.getenv("CONFIRMATION_WINDOW_SECONDS", "60"))

# Filter Logic
MIN_MARKET_CAP_USD = float(os.getenv("MIN_MARKET_CAP_USD", "10000"))
CHECK_FREEZE_AUTHORITY = os.getenv("CHECK_FREEZE_AUTHORITY", "True").lower() == "true"
SIMULATE_SELL = os.getenv("SIMULATE_SELL", "True").lower() == "true"

# Algo Sniper Thresholds
MIN_LIQUIDITY_SOL = float(os.getenv("MIN_LIQUIDITY_SOL", "10"))
MAX_TOP_HOLDERS_PERCENT = float(os.getenv("MAX_TOP_HOLDERS_PERCENT", "30"))
MAX_DEV_BUY_PERCENT = float(os.getenv("MAX_DEV_BUY_PERCENT", "10"))
MIN_SCORE_TO_BUY = int(os.getenv("MIN_SCORE_TO_BUY", "70"))
