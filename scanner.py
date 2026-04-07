import asyncio
import json
import logging
import websockets
from config import WSS_ENDPOINT, RAYDIUM_LP_V4, PUMP_FUN_PROGRAM

logger = logging.getLogger(__name__)

class NewPoolScanner:
    def __init__(self, callback):
        self.callback = callback

    async def start_listening(self):
        logger.info("Starting Multi-DEX Scanner (Raydium + Pump.fun)...")
        
        async with websockets.connect(WSS_ENDPOINT) as websocket:
            # 1. Raydium Subscription
            await websocket.send(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                "params": [{"mentions": [RAYDIUM_LP_V4]}, {"commitment": "confirmed"}]
            }))
            
            # 2. Pump.fun Subscription
            await websocket.send(json.dumps({
                "jsonrpc": "2.0", "id": 2, "method": "logsSubscribe",
                "params": [{"mentions": [PUMP_FUN_PROGRAM]}, {"commitment": "confirmed"}]
            }))
            
            logger.info("Subscribed to Raydium and Pump.fun logs.")

            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if "params" in data:
                        result = data["params"]["result"]
                        logs = str(result["value"]["logs"])
                        signature = result["value"]["signature"]
                        
                        # Raydium New Pool
                        if "initialize2" in logs:
                            logger.info(f"New Raydium Pool: {signature}")
                            await self.callback("ABC...123", signature, dex="Raydium")
                        
                        # Pump.fun New Token
                        elif "Create" in logs:
                            logger.info(f"New Pump.fun Launch: {signature}")
                            await self.callback("XYZ...789", signature, dex="Pump.fun")
                            
                except websockets.ConnectionClosed:
                    logger.warning("Scanner WebSocket closed. Reconnecting...")
                    break
                except Exception as e:
                    logger.error(f"Error in scanner loop: {e}")
                    continue
