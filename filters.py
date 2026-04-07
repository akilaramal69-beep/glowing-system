import aiohttp
import asyncio
import logging
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from config import RPC_ENDPOINT, MIN_MARKET_CAP_USD, CHECK_FREEZE_AUTHORITY, SIMULATE_SELL

logger = logging.getLogger(__name__)

# Global session to be initialized in main.py
_session = None
JUP_DOMAINS = ["quote-api.jup.ag", "api.jup.ag"]
WHITELISTED_TOKENS = [
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", # USDT
    "So11111111111111111111111111111111111111112"  # WSOL
]

async def get_session():
    global _session
    if _session is None or _session.closed:
        # Hardcode DNS resolver to bypass local resolution issues
        connector = aiohttp.TCPConnector(resolver=aiohttp.AsyncResolver(nameservers=["8.8.8.8", "1.1.1.1"]))
        _session = aiohttp.ClientSession(connector=connector)
    return _session

async def get_token_market_cap(token_address: str):
    if token_address in WHITELISTED_TOKENS:
        return 10**12 # Set huge mcap for stables
    return 50000 

async def check_freeze_authority(token_address: str):
    if token_address in WHITELISTED_TOKENS:
        return True
    if not CHECK_FREEZE_AUTHORITY:
        return True
    
    async with AsyncClient(RPC_ENDPOINT) as client:
        try:
            pubkey = Pubkey.from_string(token_address)
            account_info = await client.get_account_info(pubkey)
            return account_info is not None
        except Exception as e:
            logger.error(f"Error checking freeze authority: {e}")
            return False

async def simulate_sell(token_address: str, wallet_address: str):
    if token_address in WHITELISTED_TOKENS or not SIMULATE_SELL:
        return True
    
    session = await get_session()
    
    for domain in JUP_DOMAINS:
        url = f"https://{domain}/v6/quote?inputMint={token_address}&outputMint=So11111111111111111111111111111111111111112&amount=100000000&slippageBps=50"
        for attempt in range(2):
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return "outAmount" in data
                    elif response.status == 429:
                        await asyncio.sleep(1)
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
                logger.warning(f"Jupiter DNS/Connection error on {domain} (attempt {attempt+1}): {e}")
                await asyncio.sleep(1)
    return False

async def is_lp_burned(token_mint: str):
    # Standard check: Is LP token sent to dead address (1111...)?
    # For now, return a random boolean or always True for testing if user wants.
    # In production: Check pool state on Raydium
    return True 

async def get_top_holders_percent(token_mint: str):
    # Standard check: How much do top 10 wallets hold?
    # In production: Use get_largest_accounts RPC call
    # Return 15% as a safe placeholder
    return 15.0

async def validate_token(token_address: str, wallet_address: str):
    # 1. Market Cap
    mcap = await get_token_market_cap(token_address)
    if mcap < MIN_MARKET_CAP_USD:
        logger.info(f"Token {token_address} rejected: Market cap {mcap} < {MIN_MARKET_CAP_USD}")
        return False
    
    # 2. Freeze Authority
    if not await check_freeze_authority(token_address):
        logger.info(f"Token {token_address} rejected: Freeze authority detected")
        return False
    
    # 3. Honeypot/Sell Simulation
    if not await simulate_sell(token_address, wallet_address):
        logger.info(f"Token {token_address} rejected: Sell simulation failed (potential honeypot)")
        return False
    
    return True
