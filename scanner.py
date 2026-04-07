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
        for attempt in range(3):
            try:
                signature = Signature.from_string(signature_str)
                tx_data = await self.rpc.get_transaction(
                    signature, 
                    max_supported_transaction_version=0,
                    encoding="json"
                )
                
                if not tx_data or not tx_data.value:
                    logger.warning(f"Attempt {attempt+1}: TX {signature_str} not found yet. Retrying...")
                    await asyncio.sleep(1)
                    continue
                
                # 1. Resolve Account Keys (Static + LUT)
                message = tx_data.value.transaction.transaction.message
                meta = tx_data.value.transaction.meta
                
                static_keys = message.account_keys
                # Address Lookup Tables (LUT) resolution
                loaded_writable = meta.loaded_addresses.writable if hasattr(meta, 'loaded_addresses') and meta.loaded_addresses else []
                loaded_readonly = meta.loaded_addresses.readonly if hasattr(meta, 'loaded_addresses') and meta.loaded_addresses else []
                
                all_keys = static_keys + loaded_writable + loaded_readonly
                instructions = message.instructions
                
                # 2. Instruction-level parsing with LUT support
                if dex == "Pump.fun":
                    for inst in instructions:
                        program_id = str(all_keys[inst.program_id_index])
                        if program_id == PUMP_FUN_PROGRAM:
                            # In Pump.fun 'create' instruction, Account 0 is the Mint
                            mint_index = inst.accounts[0]
                            mint_address = str(all_keys[mint_index])
                            logger.info(f"Successfully extracted Pump.fun Mint: {mint_address}")
                            return (mint_address, tx_data)
                else:
                    # Raydium 'initialize2' check
                    for inst in instructions:
                        program_id = str(all_keys[inst.program_id_index])
                        if program_id == RAYDIUM_LP_V4:
                            for acc_idx in inst.accounts:
                                acc_str = str(all_keys[acc_idx])
                                if len(acc_str) > 30 and acc_str not in [RAYDIUM_LP_V4, PUMP_FUN_PROGRAM]:
                                    if acc_str != "So11111111111111111111111111111111111111112":
                                        return (acc_str, tx_data)
                
                # Final Fallback to metadata
                if meta and hasattr(meta, 'post_token_balances') and meta.post_token_balances:
                    for balance in meta.post_token_balances:
                        mint = str(balance.mint)
                        if mint not in ["So11111111111111111111111111111111111111112"]:
                            return (mint, tx_data)
                
                return None
            except Exception as e:
                logger.error(f"Error extracting mint (attempt {attempt+1}): {e}")
                await asyncio.sleep(1)
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
                            result = await self.extract_mint_from_tx(signature, dex)
                            if result:
                                mint, tx_data = result
                                await self.callback(mint, signature, dex=dex, tx_data=tx_data)
                            else:
                                logger.warning(f"Could not extract mint for {signature}")
                            
                except websockets.ConnectionClosed:
                    logger.warning("Scanner WebSocket closed. Reconnecting...")
                    break
                except Exception as e:
                    logger.error(f"Error in scanner loop: {e}")
                    continue
