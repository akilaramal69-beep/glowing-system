import asyncio
import json
import logging
import websockets
import time
from config import (
    WSS_ENDPOINT, SMART_WALLETS, CONFIRMATION_COUNT, 
    CONFIRMATION_WINDOW_SECONDS, BOT_MODE, MIN_SCORE_TO_BUY
)
from filters import validate_token, WHITELISTED_TOKENS
from executor import executor
from state import state_manager
from telegram_bot import telegram_reporter
from scanner import NewPoolScanner
from algo import score_token, should_buy

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def handle_new_token(token_mint: str, signature: str, dex: str = "Raydium"):
    logger.info(f"Analyzing new {dex} token: {token_mint}")
    
    # 1. Score the token
    score, reasons = await score_token(token_mint, signature, dex=dex)
    
    # 2. Telegram Alert for high potential tokens
    if score > 50:
        await telegram_reporter.report_status(f"🔍 *New {dex} Launch*: `{score}/100`\nMint: `{token_mint}`\nReasons: {', '.join(reasons)}")

    # 3. Decision
    if await should_buy(score):
        logger.info(f"Score {score} >= {MIN_SCORE_TO_BUY}. Executing SNIPER BUY!")
        success = await executor.execute_buy(token_mint)
        if success:
            state_manager.add_position(token_mint, 1.0, 0.5)
    else:
        logger.info(f"Score {score} insufficient for buy.")

async def start_heartbeat():
    while True:
        logger.info(f"--- Koyeb Heartbeat: Solana Bot [{BOT_MODE}] is Active ---")
        await asyncio.sleep(30)

async def monitor_wallets():
    # ... (Keep existing monitor_wallets logic here)
    # I'll include the full function for clarity or just replace the call
    if not SMART_WALLETS:
        logger.error("No SMART_WALLETS configured. Exiting.")
        return

    logger.info(f"Starting WebSocket listener for {len(SMART_WALLETS)} wallets...")
    
    async with websockets.connect(WSS_ENDPOINT) as websocket:
        for wallet in SMART_WALLETS:
            sub = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [wallet]},
                    {"commitment": "confirmed"}
                ]
            }
            await websocket.send(json.dumps(sub))
            logger.info(f"Subscribed to logs for wallet: {wallet}")

        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                
                if "params" in data:
                    result = data["params"]["result"]
                    logs = result["value"]["logs"]
                    signature = result["value"]["signature"]
                    
                    swap_programs = ["JUP", "675k1q", "9W959D"]
                    is_swap = any(prog in str(logs) for prog in swap_programs)
                    
                    if is_swap:
                        logger.info(f"Swap detected in tx: {signature}")
                        token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" 
                        if token_address in WHITELISTED_TOKENS:
                            logger.info(f"Signal for stablecoin {token_address} ignored.")
                            continue

                        state_manager.record_signal(token_address)
                        count = state_manager.get_signal_count(token_address, CONFIRMATION_WINDOW_SECONDS)
                        logger.info(f"Signal for {token_address}: {count}/{CONFIRMATION_COUNT}")
                        
                        if count >= CONFIRMATION_COUNT:
                            if token_address not in state_manager.positions:
                                if await validate_token(token_address, SMART_WALLETS[0]):
                                    success = await executor.execute_buy(token_address)
                                    if success:
                                        state_manager.add_position(token_address, 1.0, 0.5)
                                else:
                                    logger.info(f"Validation failed for {token_address}")
                                    await telegram_reporter.report_status(f"Filter rejected token: `{token_address}`")
            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed. Reconnecting...")
                break
            except Exception as e:
                logger.error(f"Error in listener loop: {e}")
                continue

async def main():
    await telegram_reporter.report_status(f"🤖 Bot started in *{BOT_MODE}* mode.")
    
    tasks = [asyncio.create_task(start_heartbeat())]
    
    if BOT_MODE == "ALGO_SNIPER":
        scanner = NewPoolScanner(callback=handle_new_token)
        tasks.append(asyncio.create_task(scanner.start_listening()))
    else:
        tasks.append(asyncio.create_task(monitor_wallets()))
    
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Bot shutting down...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
