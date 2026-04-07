import asyncio
import json
import logging
import websockets
from solana.rpc.async_api import AsyncClient
from config import WSS_ENDPOINT, RAYDIUM_LP_V4, PUMP_FUN_PROGRAM, RPC_ENDPOINT
from solders.pubkey import Pubkey
from solders.signature import Signature

logger = logging.getLogger(__name__)

class NewPoolScanner:
    def __init__(self, callback):
        self.callback = callback
        self.rpc = AsyncClient(RPC_ENDPOINT)

    async def extract_mint_from_tx(self, signature_str: str, dex: str):
        try:
            signature = Signature.from_string(signature_str)
            # Fetch transaction details
            tx_data = await self.rpc.get_transaction(
                signature, 
                max_supported_transaction_version=0,
                encoding="json"
            )
            if not tx_data or not tx_data.value:
                return None
            
            # 2. Extract Mint from Metadata (Most reliable way)
            meta = tx_data.value.transaction.meta
            if meta and meta.post_token_balances:
                # The first token balance in a creation tx is usually the new mint
                for balance in meta.post_token_balances:
                    mint = str(balance.mint)
                    # Ignore WSOL and other common tokens
                    if mint not in ["So11111111111111111111111111111111111111112"]:
                        return mint
            
            # Fallback to account keys if metadata parsing fails
            accounts = tx_data.value.transaction.transaction.message.account_keys
            for acc in accounts:
                acc_str = str(acc)
                if len(acc_str) > 30 and acc_str not in [RAYDIUM_LP_V4, PUMP_FUN_PROGRAM, signature_str]:
                    return acc_str
            return None
        except Exception as e:
            logger.error(f"Error extracting mint from {signature}: {e}")
            return None

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
                        
                        dex = None
                        if "initialize2" in logs:
                            dex = "Raydium"
                        elif "Create" in logs:
                            dex = "Pump.fun"
                        
                        if dex:
                            logger.info(f"New {dex} detected! Signature: {signature}")
                            mint = await self.extract_mint_from_tx(signature, dex)
                            if mint:
                                await self.callback(mint, signature, dex=dex)
                            else:
                                logger.warning(f"Could not extract mint for {signature}")
                            
                except websockets.ConnectionClosed:
                    logger.warning("Scanner WebSocket closed. Reconnecting...")
                    break
                except Exception as e:
                    logger.error(f"Error in scanner loop: {e}")
                    continue
