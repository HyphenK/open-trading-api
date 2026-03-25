"""
Configuration and constants for Samsung auto trader.
Loads environment variables for credentials.
"""
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from datetime import timezone, timedelta

# Load environment variables from .env file (if exists)
load_dotenv()

# --- Credentials (from environment variables) ---
# GH_ACCOUNT: 8-digit account number only (product code 01 added automatically)
_account_raw = os.getenv("GH_ACCOUNT")
GH_ACCOUNT = f"{_account_raw}-01" if _account_raw else None  # Auto-append product code
GH_APPKEY = os.getenv("GH_APPKEY")
GH_APPSECRET = os.getenv("GH_APPSECRET")

# Validate required credentials
if not all([_account_raw, GH_APPKEY, GH_APPSECRET]):
    raise ValueError(
        "Missing required environment variables: "
        "GH_ACCOUNT (8-digit), GH_APPKEY, GH_APPSECRET"
    )

# --- API Configuration ---
BASE_URL = "https://openapi.koreainvestment.com:9443"
API_VERSION = "1.0.2"

# --- Trading Configuration ---
STOCK_CODE = "005930"  # Samsung Electronics
STOCK_NAME = "삼성전자"

# Trading window (trading hours: 09:10 - 15:30)
TRADING_START_HOUR = 9
TRADING_START_MINUTE = 10
TRADING_END_HOUR = 15
TRADING_END_MINUTE = 30

# Order price offset (KRW)
BUY_ORDER_OFFSET = 2000    # Buy at current_price - 2000
SELL_ORDER_OFFSET = 2000   # Sell at current_price + 2000

# API Polling intervals (seconds)
PRICE_CHECK_INTERVAL = 30      # Check current price every 30s
BALANCE_CHECK_INTERVAL = 60    # Check balance after order
POLLING_INTERVAL = 5           # General polling interval between loops

# Timeout settings
API_TIMEOUT = 10               # seconds

# Token cache file
TOKEN_CACHE_FILE = "token_cache.json"

# --- Timezone Configuration ---
KST = ZoneInfo("Asia/Seoul")  # Korea Standard Time (UTC+9)

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FILE = "auto_trader.log"
