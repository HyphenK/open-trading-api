from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api_client import APIClient
from config import OPEN_ORDERS_ENDPOINT, TARGET_SYMBOL, TR_ID_OPEN_ORDERS_DEMO, today_kst_str


@dataclass
class OpenOrder:
    symbol: str
    side: str
    order_no: str | None
    order_time: str | None
    order_branch: str | None
    order_price: int
    order_qty: int
    filled_qty: int
    unfilled_qty: int
    raw: dict[str, Any]


class OpenOrdersService:
    def __init__(self, api_client: APIClient, cano: str, acnt_prdt_cd: str) -> None:
        self.api_client = api_client
        self.cano = cano
        self.acnt_prdt_cd = acnt_prdt_cd

    def get_open_orders(self, symbol: str = TARGET_SYMBOL) -> list[OpenOrder]:
        today = today_kst_str()
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "INQR_STRT_DT": today,
            "INQR_END_DT": today,
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            # Query broadly, then filter in Python. This has been more reliable than
            # requesting a single symbol directly for inquire-daily-ccld.
            "PDNO": "",
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "INQR_DVSN_2": "",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        data = self.api_client.get(OPEN_ORDERS_ENDPOINT, TR_ID_OPEN_ORDERS_DEMO, params=params)
        rows = self._extract_rows(data)

        open_orders: list[OpenOrder] = []
        for row in rows:
            order = self._parse_order(row)
            if order is None:
                continue
            if order.symbol != symbol:
                continue
            if order.unfilled_qty <= 0:
                continue
            open_orders.append(order)

        return open_orders

    @staticmethod
    def _extract_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = [
            data.get("output1"),
            data.get("output"),
            data.get("output2"),
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                return [row for row in candidate if isinstance(row, dict)]
        return []

    @staticmethod
    def _parse_order(row: dict[str, Any]) -> OpenOrder | None:
        symbol = _first_str(row, "pdno", "PDNO")
        if not symbol:
            return None

        order_qty = _first_int(row, "ord_qty", "ORD_QTY", "tot_ord_qty", "TOT_ORD_QTY")
        filled_qty = _first_int(
            row,
            "tot_ccld_qty",
            "TOT_CCLD_QTY",
            "ccld_qty",
            "CCLD_QTY",
        )
        unfilled_qty = _first_int(
            row,
            "rmn_qty",
            "RMN_QTY",
            "tot_ccld_rmnd_qty",
            "TOT_CCLD_RMND_QTY",
            "ord_psbl_qty",
        )

        if unfilled_qty <= 0 and order_qty > 0:
            unfilled_qty = max(order_qty - filled_qty, 0)

        return OpenOrder(
            symbol=symbol,
            side=_infer_side(row),
            order_no=_nullable(_first_str(row, "odno", "ODNO", "ord_no", "ORD_NO")),
            order_time=_nullable(_first_str(row, "ord_tmd", "ORD_TMD", "order_time")),
            order_branch=_nullable(
                _first_str(row, "ord_gno_brno", "ORD_GNO_BRNO", "krx_fwdg_ord_orgno")
            ),
            order_price=_first_int(row, "ord_unpr", "ORD_UNPR", "avg_prvs", "order_price"),
            order_qty=order_qty,
            filled_qty=filled_qty,
            unfilled_qty=unfilled_qty,
            raw=row,
        )


def _infer_side(row: dict[str, Any]) -> str:
    raw = _first_str(
        row,
        "sll_buy_dvsn_cd",
        "SLL_BUY_DVSN_CD",
        "trad_dvsn_name",
        "trad_dvsn",
        "trade_type",
    )
    normalized = raw.upper()

    if raw in {"01", "BUY", "매수"} or "매수" in raw or "BUY" in normalized:
        return "buy"
    if raw in {"02", "SELL", "매도"} or "매도" in raw or "SELL" in normalized:
        return "sell"

    return "buy"


def _first_int(source: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = source.get(key)
        if value is None or value == "":
            continue
        try:
            return int(str(value).replace(",", ""))
        except ValueError:
            continue
    return 0


def _first_str(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _nullable(value: str) -> str | None:
    return value or None
