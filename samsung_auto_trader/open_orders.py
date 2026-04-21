from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import (
    OPEN_ORDERS_ENDPOINT,
    TARGET_SYMBOL,
    TR_ID_OPEN_ORDERS_DEMO,
    today_kst_str,
)


@dataclass
class OpenOrder:
    symbol: str
    side: str
    order_no: str
    order_branch_no: str
    order_time: str
    order_type_name: str
    order_qty: int
    filled_qty: int
    unfilled_qty: int
    price: int
    raw: dict[str, Any]


class OpenOrdersService:
    def __init__(self, api_client, cano: str, acnt_prdt_cd: str):
        self.api_client = api_client
        self.cano = cano
        self.acnt_prdt_cd = acnt_prdt_cd

    def get_open_orders(self, symbol: str = TARGET_SYMBOL) -> list[OpenOrder]:
        today = today_kst_str()

        base_params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "INQR_STRT_DT": today,
            "INQR_END_DT": today,
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            "PDNO": "",  # 전체 조회 후 파이썬에서 종목 필터링
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "INQR_DVSN_2": "",
        }

        rows = self._fetch_all_rows(base_params)
        open_orders: list[OpenOrder] = []

        for row in rows:
            order = self._parse_order(row)
            if order is None:
                continue
            if order.symbol != symbol:
                continue
            if not self._looks_open(row, order):
                continue
            open_orders.append(order)

        return self._dedupe_by_order_no(open_orders)

    def _fetch_all_rows(self, base_params: dict[str, str]) -> list[dict[str, Any]]:
        all_rows: list[dict[str, Any]] = []
        seen_tokens: set[tuple[str, str]] = set()

        ctx_fk100 = ""
        ctx_nk100 = ""

        while True:
            params = {
                **base_params,
                "CTX_AREA_FK100": ctx_fk100,
                "CTX_AREA_NK100": ctx_nk100,
            }

            data = self.api_client.get(
                OPEN_ORDERS_ENDPOINT,
                TR_ID_OPEN_ORDERS_DEMO,
                params=params,
            )

            rows = data.get("output1", []) or []
            all_rows.extend(rows)

            next_fk100 = str(data.get("ctx_area_fk100") or "").strip()
            next_nk100 = str(data.get("ctx_area_nk100") or "").strip()
            token = (next_fk100, next_nk100)

            if not rows:
                break
            if not next_nk100:
                break
            if token in seen_tokens:
                break

            seen_tokens.add(token)
            ctx_fk100 = next_fk100
            ctx_nk100 = next_nk100

        return all_rows

    @staticmethod
    def _parse_order(row: dict[str, Any]) -> OpenOrder | None:
        symbol = _first_str(row, "pdno", "PDNO")
        if not symbol:
            return None

        side_name = _first_str(row, "sll_buy_dvsn_cd_name", "SLL_BUY_DVSN_CD_NAME")
        side = _normalize_side(side_name)
        if not side:
            return None

        order_no = _first_str(row, "odno", "ODNO")
        order_branch_no = _first_str(row, "ord_gno_brno", "ORD_GNO_BRNO")
        order_type_name = _first_str(row, "ord_dvsn_name", "ORD_DVSN_NAME")
        order_time = _normalize_time(_first_str(row, "ord_tmd", "ORD_TMD", "infm_tmd", "INFM_TMD"))
        order_qty = _first_int(row, "ord_qty", "ORD_QTY")
        filled_qty = _first_int(row, "tot_ccld_qty", "TOT_CCLD_QTY")
        price = _first_int(row, "ord_unpr", "ORD_UNPR")

        # rmn_qty는 사용하지 않는다.
        # 대신 남아 있는 수량은 order_qty - filled_qty 로 계산한다.
        unfilled_qty = max(order_qty - filled_qty, 0)

        return OpenOrder(
            symbol=symbol,
            side=side,
            order_no=order_no,
            order_branch_no=order_branch_no,
            order_time=order_time,
            order_type_name=order_type_name,
            order_qty=order_qty,
            filled_qty=filled_qty,
            unfilled_qty=unfilled_qty,
            price=price,
            raw=row,
        )

    @staticmethod
    def _looks_open(row: dict[str, Any], order: OpenOrder) -> bool:
        if not order.order_no:
            return False

        cncl_yn = _first_str(row, "cncl_yn", "CNCL_YN").upper()
        if cncl_yn == "Y":
            return False

        side_name = _first_str(row, "sll_buy_dvsn_cd_name", "SLL_BUY_DVSN_CD_NAME")
        if "취소" in side_name:
            return False

        if order.order_qty <= 0:
            return False

        if order.filled_qty >= order.order_qty:
            return False

        if order.filled_qty < 0:
            return False
        if order.filled_qty > order.order_qty:
            return False

        return True

    @staticmethod
    def _dedupe_by_order_no(orders: list[OpenOrder]) -> list[OpenOrder]:
        latest_by_no: dict[str, OpenOrder] = {}

        for order in orders:
            prev = latest_by_no.get(order.order_no)
            if prev is None:
                latest_by_no[order.order_no] = order
                continue

            if order.order_time >= prev.order_time:
                latest_by_no[order.order_no] = order

        deduped = list(latest_by_no.values())
        deduped.sort(key=lambda o: (o.order_time, o.order_no), reverse=True)
        return deduped


def _normalize_side(side_name: str) -> str:
    if "매수" in side_name and "취소" not in side_name:
        return "buy"
    if "매도" in side_name and "취소" not in side_name:
        return "sell"
    return ""


def _normalize_time(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 6:
        return digits
    return raw.strip()


def _first_str(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _first_int(row: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip().replace(",", "")
        if text == "":
            continue
        try:
            return int(float(text))
        except ValueError:
            continue
    return 0
