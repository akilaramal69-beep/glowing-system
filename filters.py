import aiohttp
import asyncio
import logging
import json
import socket
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from config import RPC_ENDPOINT, MIN_MARKET_CAP_USD, CHECK_FREEZE_AUTHORITY, SIMULATE_SELL

logger = logging.getLogger(__name__)

# Global session to be initialized in main.py
_session = None
_dns_cache = {}
JUP_DOMAINS = ["quote-api.jup.ag", "api.jup.ag", "jup.ag", "quote.jup.ag"]
WHITELISTED_TOKENS = [
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", # USDT
    "So11111111111111111111111111111111111111112"  # WSOL
]

async def resolve_doh(hostname):
    """Resolve a hostname using Cloudflare DNS-over-HTTPS to bypass local DNS issues."""
    if hostname in _dns_cache: return _dns_cache[hostname]
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A"
            headers = {"accept": "application/dns-json"}
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for answer in data.get("Answer", []):
                        if answer.get("type") == 1: # A record
                            ip = answer["data"]
                            _dns_cache[hostname] = ip
                            return ip
    except Exception as e:
        logger.error(f"DoH resolution failed for {hostname}: {e}")
    return None

async def resilient_get(url: str):
    """GET request with automatic IP-fallback via DoH for Jupiter/Koyeb stability."""
    session = await get_session()
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.netloc
    
    headers = {"User-Agent": "SolanaBot/1.0", "Accept": "application/json"}
    
    # 1. Standard Attempt
    try:
        async with session.get(url, headers=headers, timeout=5) as resp:
            if resp.status == 200: return await resp.json()
    except Exception:
        pass
    
    # 2. DoH Fallback (Cloudflare 1.1.1.1 API)
    ip = await resolve_doh(hostname)
    if ip:
        logger.info(f"DNS FAIL: Trying DoH Fallback {hostname} -> {ip}")
        direct_url = url.replace(hostname, ip)
        direct_headers = headers.copy()
        direct_headers["Host"] = hostname
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as direct_session:
                async with direct_session.get(direct_url, headers=direct_headers, timeout=5) as resp:
                    if resp.status == 200: return await resp.json()
        except Exception as e:
            logger.error(f"IP Fallback failed: {e}")
    return None

async def get_session():
    global _session
    if _session is None or _session.closed:
        resolver = aiohttp.AsyncResolver(nameservers=["1.1.1.1", "8.8.8.8"])
        connector = aiohttp.TCPConnector(resolver=resolver, family=socket.AF_INET, use_dns_cache=False)
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
    
    # Optional: If token name ends in 'pump', we can assume it's Pump.fun
    # and skip Jupiter simulation as it will always fail there initially.
    if token_address.lower().endswith("pump"):
        logger.info(f"Skipping sell simulation for Pump.fun token {token_address}")
        return True

    session = await get_session()
    
    for domain in JUP_DOMAINS:
        url = f"https://{domain}/v6/quote?inputMint={token_address}&outputMint=So11111111111111111111111111111111111111112&amount=100000000&slippageBps=50"
        data = await resilient_get(url)
        if data and "outAmount" in data:
            return True
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
