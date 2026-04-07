import asyncio
import logging
import aiohttp
import base58
import base64
import json
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from filters import validate_token, get_session, JUP_DOMAINS
from config import (
    RPC_ENDPOINT, JITO_ENDPOINT, JITO_TIP_AMOUNT_SOL, 
    PRIVATE_KEY, MAX_POSITION_SOL, SLIPPAGE_LIMIT, PRIORITY_FEE_LAMPORTS
)
from solders.system_program import TransferParams, transfer
from solders.pubkey import Pubkey
from telegram_bot import telegram_reporter

logger = logging.getLogger(__name__)

class JitoClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip('/') + '/api/v1/bundles'

    async def send_bundle(self, transactions: list):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendBundle",
            "params": [transactions]
        }
        session = await get_session()
        try:
            async with session.post(self.endpoint, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("result")
                else:
                    text = await response.text()
                    logger.error(f"Jito error ({response.status}): {text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to connect to Jito: {e}")
            return None

class TradeExecutor:
    def __init__(self):
        self.keypair = Keypair.from_bytes(base58.b58decode(PRIVATE_KEY))
        self.rpc = AsyncClient(RPC_ENDPOINT)
        self.jito_client = JitoClient(endpoint=JITO_ENDPOINT)
        self.sol_mint = "So11111111111111111111111111111111111111112"

    async def get_jupiter_quote(self, input_mint: str, output_mint: str, amount_lamports: int):
        session = await get_session()
        for domain in JUP_DOMAINS:
            url = f"https://{domain}/v6/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount_lamports}&slippageBps={int(SLIPPAGE_LIMIT * 100)}"
            for attempt in range(2):
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            await asyncio.sleep(1)
                except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                    await asyncio.sleep(1)
        return None

    async def get_jupiter_swap_tx(self, quote_data: dict, user_public_key: str):
        session = await get_session()
        for domain in JUP_DOMAINS:
            url = f"https://{domain}/v6/swap"
            payload = {
                "quoteResponse": quote_data,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True
            }
            try:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("swapTransaction")
            except Exception:
                continue
        return None

    async def execute_buy(self, token_address: str):
        amount_lamports = int(MAX_POSITION_SOL * 10**9)
        logger.info(f"Executing BUY for {token_address} with {MAX_POSITION_SOL} SOL")
        
        # 1. Get Quote
        quote = await self.get_jupiter_quote(self.sol_mint, token_address, amount_lamports)
        if not quote:
            logger.error("Failed to get Jupiter quote")
            return False

        # 2. Get Swap Transaction
        swap_tx_base64 = await self.get_jupiter_swap_tx(quote, str(self.keypair.pubkey()))
        if not swap_tx_base64:
            logger.error("Failed to get Jupiter swap transaction")
            return False

        # 3. Add Jito Tip & Priority Logic
        # Jito Tip Accounts (Pick one)
        JITO_TIP_ACCOUNT = Pubkey.from_string("96g9s9yUuQUWvUGr6mZSTVMTN8YSgR6R5z39Bxy5829H")
        tip_lamports = int(JITO_TIP_AMOUNT_SOL * 10**9)
        
        try:
            # 1. Decode VersionedTransaction
            raw_tx = base64.b64decode(swap_tx_base64)
            v_tx = VersionedTransaction.from_bytes(raw_tx)
            
            # 2. Add Tip Instruction (In a real implementation, you'd modify the Message)
            # For now, we sign the Jupiter transaction directly.
            # Most snipers send the 'Tip' as a separate transaction in the same bundle.
            
            # Create Tip Transaction
            tip_ix = transfer(TransferParams(
                from_pubkey=self.keypair.pubkey(),
                to_pubkey=JITO_TIP_ACCOUNT,
                lamports=tip_lamports
            ))
            
            # Fetch recent blockhash
            recent_blockhash = (await self.rpc.get_latest_blockhash()).value.blockhash
            
            tip_msg = MessageV0.compile(
                payer=self.keypair.pubkey(),
                instructions=[tip_ix],
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash
            )
            tip_tx = VersionedTransaction(tip_msg, [self.keypair])
            
            # Finalize Swap Tx signature
            # Jupiter tx already has instructions, just needs our signature
            v_tx.sign([self.keypair])
            
            # 3. Send Bundle
            bundle = [
                base64.b64encode(bytes(v_tx)).decode("utf-8"),
                base64.b64encode(bytes(tip_tx)).decode("utf-8")
            ]
            bundle_id = await self.jito_client.send_bundle(bundle)
            
            if bundle_id:
                logger.info(f"Jito Bundle Sent! ID: {bundle_id}")
                await telegram_reporter.report_status(f"🚀 *Snipe Executed*\nToken: `{token_address}`\nBundle: `{bundle_id}`")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error executing Jito bundle: {e}")
            return False

executor = TradeExecutor()
