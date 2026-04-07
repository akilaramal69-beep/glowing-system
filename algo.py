import logging
from config import MIN_LIQUIDITY_SOL, MAX_TOP_HOLDERS_PERCENT, MIN_SCORE_TO_BUY
from filters import is_lp_burned, get_top_holders_percent, validate_token

logger = logging.getLogger(__name__)

async def score_token(token_mint: str, signature: str):
    score = 0
    reasons = []

    # 1. Base Validation (Freeze Authority, Sell Simulation)
    if not await validate_token(token_mint, "ALGO_MODE"):
        return 0, ["Base validation failed"]

    # 2. LP Burn check (+40 points)
    if await is_lp_burned(token_mint):
        score += 40
        reasons.append("LP Burned/Locked")
    else:
        reasons.append("LP NOT Burned")

    # 3. Top Holders check (+30 points)
    top_holders_pct = await get_top_holders_percent(token_mint)
    if top_holders_pct < MAX_TOP_HOLDERS_PERCENT:
        score += 30
        reasons.append(f"Good Distribution ({top_holders_pct}%)")
    else:
        reasons.append(f"High Concentration ({top_holders_pct}%)")

    # 4. Liquidity Check (+30 points)
    # Placeholder: In production, fetch pool SOL balance
    liquidity_sol = 20 # Mocked
    if liquidity_sol >= MIN_LIQUIDITY_SOL:
        score += 30
        reasons.append(f"Adequate Liquidity ({liquidity_sol} SOL)")
    
    logger.info(f"Token {token_mint} Score: {score}/100. Reasons: {reasons}")
    return score, reasons

async def should_buy(score: int):
    return score >= MIN_SCORE_TO_BUY
