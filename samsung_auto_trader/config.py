from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TOKEN_CACHE_PATH = BASE_DIR / "token_cache.json"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "trader.log"

MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"
TOKEN_ENDPOINT = "/oauth2/tokenP"
HASHKEY_ENDPOINT = "/uapi/hashkey"
PRICE_ENDPOINT = "/uapi/domestic-stock/v1/quotations/inquire-price"
BALANCE_ENDPOINT = "/uapi/domestic-stock/v1/trading/inquire-balance"
ORDER_CASH_ENDPOINT = "/uapi/domestic-stock/v1/trading/order-cash"
ORDER_REVISE_CANCEL_ENDPOINT = "/uapi/domestic-stock/v1/trading/order-rvsecncl"
OPEN_ORDERS_ENDPOINT = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"

# These TR IDs and endpoints are isolated here so they can be adjusted easily if
# your mock account environment uses a different mapping.
TR_ID_PRICE = "FHKST01010100"
TR_ID_BALANCE_DEMO = "VTTC8434R"
TR_ID_ORDER_BUY_DEMO = "VTTC0012U"
TR_ID_ORDER_SELL_DEMO = "VTTC0011U"
TR_ID_ORDER_CANCEL_DEMO = "VTTC0803U"
# Recent mock-trading guidance uses VTTC0081R for inquire-daily-ccld.
TR_ID_OPEN_ORDERS_DEMO = "VTTC0081R"
TR_ID_HASHKEY = "HASH"

MARKET_DIVISION = "J"
EXCHANGE_CODE = "KRX"
ORDER_TYPE_LIMIT = "00"
ORDER_TYPE_MARKET = "01"
RVSE_CNCL_CANCEL_CODE = "02"
QTY_ALL_ORDER_YN = "Y"

TARGET_SYMBOL = "005930"
TARGET_NAME = "Samsung Electronics"
BUY_OFFSET_KRW = 1000
SELL_OFFSET_KRW = 1000
DEFAULT_ORDER_QTY = 1

# Inventory / capital controls.
INITIAL_POSITION = 20
MIN_POSITION = 5
MAX_POSITION = 40

KST = ZoneInfo("Asia/Seoul")
TRADING_START = time(hour=9, minute=10)
CLOSEOUT_START = time(hour=15, minute=20)
TRADING_END = time(hour=15, minute=30)

PRE_MARKET_SLEEP_SECONDS = 60
POLL_INTERVAL_SECONDS = 20
POST_ORDER_SETTLE_SECONDS = 5
POST_CANCEL_SETTLE_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5


@dataclass(frozen=True)
class Credentials:
    account_no: str
    app_key: str
    app_secret: str

    @property
    def cano(self) -> str:
        return self.account_no.split("-")[0]

    @property
    def acnt_prdt_cd(self) -> str:
        if "-" in self.account_no:
            return self.account_no.split("-")[1]
        return "01"



def load_credentials() -> Credentials:
    raw_account = os.getenv("GH_ACCOUNT", "").strip()
    app_key = os.getenv("GH_APPKEY", "").strip()
    app_secret = os.getenv("GH_APPSECRET", "").strip()

    if not raw_account:
        raise RuntimeError("GH_ACCOUNT environment variable is missing.")
    if not app_key:
        raise RuntimeError("GH_APPKEY environment variable is missing.")
    if not app_secret:
        raise RuntimeError("GH_APPSECRET environment variable is missing.")

    account_no = normalize_account(raw_account)
    return Credentials(account_no=account_no, app_key=app_key, app_secret=app_secret)



def normalize_account(value: str) -> str:
    cleaned = value.strip()
    if cleaned.isdigit() and len(cleaned) == 8:
        return f"{cleaned}-01"

    if "-" in cleaned:
        front, back = cleaned.split("-", 1)
        if front.isdigit() and len(front) == 8 and back.isdigit() and len(back) == 2:
            return cleaned

    raise RuntimeError(
        "GH_ACCOUNT must be either 8 digits (example: 12345678) or 8-2 format "
        "(example: 12345678-01)."
    )



def now_kst() -> datetime:
    return datetime.now(KST)



def today_kst_str() -> str:
    return now_kst().strftime("%Y%m%d")
