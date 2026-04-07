# Solana Smart Money Copy-Trading Bot (2026)

A production-ready, Dockerized Solana bot optimized for low latency and anti-MEV protection. Supports both **Copy-Trading** and **Algorithmic Sniping**. Designed to run as a **Koyeb Worker**.

## 🚀 Features

- **Jito Bundle Submission**: All trades are sent as Jito bundles with custom tips and priority fees to guarantee landing.
- **LUT-Aware Scanner**: Supports Address Lookup Tables (LUT) for 100% accurate token extraction on any DEX.
- **Jupiter V6 Aggregator**: Uses Jupiter Swap API for best price execution.
- **Copy-Trading Mode**: Follow smart wallets with multi-wallet confirmation logic.
- **Algorithmic Sniper Mode**: 
  - **Multi-DEX Scanning**: Real-time detection of new **Raydium** pools and **Pump.fun** bonding curve launches.
  - **Automated Scoring**: Safety checks for LP burns, insider distribution, and platform-specific metrics.
- **Safety Filters**: Honeypot detection, freeze authority checks, and market cap verification.
- **Telegram Notifications**: Real-time alerts for buys, filter rejections, and scanning events.
- **State Persistence**: Positions are saved to `positions.json` to survive restarts.

## 🛠️ Installation

### 1. Prerequisites
- [Docker](https://www.docker.com/)
- [Helius](https://helius.dev/) or QuickNode API Key
- Solana Wallet Private Key (Base58)

### 2. Setup
Clone the repository and install dependencies (if running locally):
```bash
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

## 🚢 Deployment on Koyeb

This bot is designed to run as a **Worker** service (no public ports needed).

1.  **Create App**: Go to Koyeb and create a new Web Service or Worker.
2.  **Environment Variables**: 
    - Set `PRIVATE_KEY` as a Secret.
    - Set `RPC_ENDPOINT`, `WSS_ENDPOINT`, `SMART_WALLETS`, etc.
3.  **Deploy**: Connect your GitHub repository or use the provided `Dockerfile`.

## ⚙️ Configuration Parameters

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MAX_POSITION_SOL` | Amount of SOL to spend per trade | `0.5` |
| `JITO_TIP_AMOUNT_SOL`| Tip for Jito validators (needed for bundles) | `0.0001` |
| `STOP_LOSS_PERCENT` | Auto-sell at -X% from entry | `15` |
| `CONFIRMATION_COUNT`| Number of wallets required for a trade | `2` |
| `TELEGRAM_BOT_TOKEN`| Token from BotFather | `None` |
| `TELEGRAM_CHAT_ID` | Your Telegram User/Chat ID | `None` |

## ⚠️ Disclaimer

Trading cryptocurrencies, especially meme coins on Solana, carries significant risk. This software is provided "as is" and the developers are not responsible for any financial losses. **Test with small amounts first!**
