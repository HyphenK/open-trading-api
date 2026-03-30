from __future__ import annotations

from typing import Any

from api_client import APIClient
from config import MARKET_DIVISION, PRICE_ENDPOINT, TARGET_SYMBOL, TR_ID_PRICE


class MarketDataService:
    def __init__(self, api_client: APIClient) -> None:
        self.api_client = api_client

    def get_current_price(self, symbol: str = TARGET_SYMBOL) -> int:
        params = {
            "FID_COND_MRKT_DIV_CODE": MARKET_DIVISION,
            "FID_INPUT_ISCD": symbol,
        }
        data = self.api_client.get(PRICE_ENDPOINT, TR_ID_PRICE, params=params)
        output = data.get("output", {})

        # KIS samples use output.stck_prpr for current price.
        price = _first_int(output, "stck_prpr", "stck_prdy_clpr", "current_price")
        if price <= 0:
            raise RuntimeError(f"Unable to parse current price from response: {output}")
        return price



def _first_int(source: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = source.get(key)
        if value is None or value == "":
            continue
        return int(str(value).replace(",", ""))
    return 0
