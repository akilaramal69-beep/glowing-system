import asyncio
import json
import logging
import websockets
from config import WSS_ENDPOINT

logger = logging.getLogger(__name__)

# Raydium Liquidity Pool V4 Program ID
RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

class NewPoolScanner:
    def __init__(self, callback):
        self.callback = callback # Function to call when a new pool is found

    async def start_listening(self):
        logger.info(f"Starting New Pool Scanner on Raydium ({RAYDIUM_LP_V4})...")
        
        async with websockets.connect(WSS_ENDPOINT) as websocket:
            # Subscribe to logs for the Raydium LP program
            sub = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [RAYDIUM_LP_V4]},
                    {"commitment": "confirmed"}
                ]
            }
            await websocket.send(json.dumps(sub))
            logger.info("Subscribed to Raydium LP logs.")

            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if "params" in data:
                        result = data["params"]["result"]
                        logs = result["value"]["logs"]
                        signature = result["value"]["signature"]
                        
                        # Look for 'initialize2' which signifies a new pool creation
                        if any("initialize2" in str(log) for log in logs):
                            logger.info(f"New Raydium Pool Detected! TX: {signature}")
                            # In a real sniper, you'd call getTransaction here to extract the Mint
                            # and then pass it to the callback for analysis.
                            
                            # Placeholder: Simulated Mint Extraction
                            # In production, use: response = await rpc.get_transaction(signature)
                            token_mint = "ABC...123" # This would be parsed from inner instructions
                            await self.callback(token_mint, signature)
                            
                except websockets.ConnectionClosed:
                    logger.warning("Scanner WebSocket closed. Reconnecting...")
                    break
                except Exception as e:
                    logger.error(f"Error in scanner loop: {e}")
                    continue
