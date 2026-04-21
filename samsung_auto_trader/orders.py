from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api_client import APIClient
from config import (
    EXCHANGE_CODE,
    ORDER_CASH_ENDPOINT,
    ORDER_REVISE_CANCEL_ENDPOINT,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    QTY_ALL_ORDER_YN,
    RVSE_CNCL_CANCEL_CODE,
    TR_ID_ORDER_BUY_DEMO,
    TR_ID_ORDER_CANCEL_DEMO,
    TR_ID_ORDER_SELL_DEMO,
)


@dataclass
class OrderResult:
    side: str
    requested_qty: int
    requested_price: int
    order_no: str | None
    order_time: str | None
    raw: dict[str, Any]


@dataclass
class CancelResult:
    order_no: str | None
    order_time: str | None
    raw: dict[str, Any]


def get_kospi_tick_size(price: int) -> int:
    if price < 2_000:
        return 1
    if price < 5_000:
        return 5
    if price < 20_000:
        return 10
    if price < 50_000:
        return 50
    if price < 200_000:
        return 100
    if price < 500_000:
        return 500
    return 1_000


def round_price_down_to_tick(price: int) -> int:
    tick = get_kospi_tick_size(price)
    return (price // tick) * tick


def round_price_up_to_tick(price: int) -> int:
    tick = get_kospi_tick_size(price)
    return ((price + tick - 1) // tick) * tick


class OrderService:
    def __init__(self, api_client: APIClient, cano: str, acnt_prdt_cd: str) -> None:
        self.api_client = api_client
        self.cano = cano
        self.acnt_prdt_cd = acnt_prdt_cd

    def place_buy_limit(self, symbol: str, qty: int, price: int) -> OrderResult:
        safe_price = max(1, round_price_down_to_tick(price))
        return self._place_order("buy", symbol, qty, safe_price, order_type=ORDER_TYPE_LIMIT)

    def place_sell_limit(self, symbol: str, qty: int, price: int) -> OrderResult:
        safe_price = max(1, round_price_up_to_tick(price))
        return self._place_order("sell", symbol, qty, safe_price, order_type=ORDER_TYPE_LIMIT)

    def place_buy_market(self, symbol: str, qty: int) -> OrderResult:
        return self._place_order("buy", symbol, qty, 0, order_type=ORDER_TYPE_MARKET)

    def place_sell_market(self, symbol: str, qty: int) -> OrderResult:
        return self._place_order("sell", symbol, qty, 0, order_type=ORDER_TYPE_MARKET)

    def cancel_order(self, symbol: str, order_no: str, order_branch: str | None, qty: int, price: int) -> CancelResult:
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "KRX_FWDG_ORD_ORGNO": order_branch or "",
            "ORGN_ODNO": order_no,
            "ORD_DVSN": ORDER_TYPE_LIMIT,
            "RVSE_CNCL_DVSN_CD": RVSE_CNCL_CANCEL_CODE,
            "ORD_QTY": str(max(qty, 0)),
            "ORD_UNPR": str(max(price, 0)),
            "QTY_ALL_ORD_YN": QTY_ALL_ORDER_YN,
            "PDNO": symbol,
            "EXCG_ID_DVSN_CD": EXCHANGE_CODE,
        }
        data = self.api_client.post(
            ORDER_REVISE_CANCEL_ENDPOINT,
            TR_ID_ORDER_CANCEL_DEMO,
            body=body,
            use_hashkey=True,
        )
        output = data.get("output", {})
        return CancelResult(
            order_no=str(output.get("ODNO") or output.get("KRX_FWDG_ORD_ORGNO") or "") or None,
            order_time=str(output.get("ORD_TMD") or "") or None,
            raw=data,
        )

    def _place_order(self, side: str, symbol: str, qty: int, price: int, order_type: str) -> OrderResult:
        tr_id = TR_ID_ORDER_BUY_DEMO if side == "buy" else TR_ID_ORDER_SELL_DEMO
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": symbol,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price),
            "EXCG_ID_DVSN_CD": EXCHANGE_CODE,
            "SLL_TYPE": "01" if side == "sell" else "",
            "CNDT_PRIC": "",
        }
        data = self.api_client.post(ORDER_CASH_ENDPOINT, tr_id, body=body, use_hashkey=True)
        output = data.get("output", {})
        return OrderResult(
            side=side,
            requested_qty=qty,
            requested_price=price,
            order_no=str(output.get("KRX_FWDG_ORD_ORGNO") or output.get("ODNO") or "") or None,
            order_time=str(output.get("ORD_TMD") or "") or None,
            raw=data,
        )
