import logging
from config import MIN_LIQUIDITY_SOL, MAX_TOP_HOLDERS_PERCENT, MIN_SCORE_TO_BUY, MAX_DEV_BUY_PERCENT
from filters import is_lp_burned, get_top_holders_percent, validate_token

logger = logging.getLogger(__name__)

async def get_dev_buy_amount(tx_data, token_mint):
    if not tx_data: return 0
    try:
        # Check post-token-balances for the first account (the creator)
        meta = tx_data.value.transaction.meta
        if meta and meta.post_token_balances:
            # We assume the creator is account 0 in the instruction
            # and they have a balance in the new token mint
            for balance in meta.post_token_balances:
                if str(balance.mint) == token_mint:
                    # Simplified: check the amount as a percentage of total supply
                    # Total supply is usually 1,000,000,000 (1B) for memes
                    amount = float(balance.ui_token_amount.ui_amount or 0)
                    percent = (amount / 1_000_000_000) * 100
                    return percent
    except Exception:
        pass
    return 0

async def score_token(token_mint: str, signature: str, dex: str = "Raydium", tx_data: any = None):
    score = 0
    reasons = []

    # 1. Base Validation (Freeze Authority, Sell Simulation)
    if not await validate_token(token_mint, "ALGO_MODE"):
        return 0, ["Base validation failed"]

    # 2. Dev Buy Check (+20 pts or Penalty)
    dev_pct = await get_dev_buy_amount(tx_data, token_mint)
    if dev_pct > MAX_DEV_BUY_PERCENT:
        reasons.append(f"🚩 High Dev Buy ({dev_pct:.1f}%)")
        score -= 50 # Massive penalty for dev-dump risk
    elif dev_pct > 0:
        score += 20
        reasons.append(f"Dev Skin in Game ({dev_pct:.1f}%)")

    # 3. DEX Specific logic
    if dex == "Raydium":
        if await is_lp_burned(token_mint):
            score += 30
            reasons.append("LP Burned/Locked")
    elif dex == "Pump.fun":
        score += 40
        reasons.append("Pump.fun Early Launcher (Automatic renounced)")

    # 4. Holder Distribution (+20 points)
    top_holders_pct = await get_top_holders_percent(token_mint)
    if top_holders_pct < MAX_TOP_HOLDERS_PERCENT:
        score += 20
        reasons.append(f"Good Distribution ({top_holders_pct}%)")
    
    logger.info(f"[{dex}] Token {token_mint} Score: {score}/100. Reasons: {reasons}")
    return score, reasons

async def should_buy(score: int):
    return score >= MIN_SCORE_TO_BUY
