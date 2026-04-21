from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api_client import APIClient
from config import (
    BALANCE_ENDPOINT,
    PSBL_ORDER_ENDPOINT,
    TARGET_SYMBOL,
    TR_ID_BALANCE_DEMO,
    TR_ID_PSBL_ORDER_DEMO,
)


@dataclass
class HoldingSnapshot:
    symbol: str
    qty: int
    sellable_qty: int
    avg_price: int


@dataclass
class AccountSnapshot:
    cash_available: int | None
    total_eval_amount: int | None
    holding: HoldingSnapshot | None
    raw_output1: list[dict[str, Any]]
    raw_output2: list[dict[str, Any]]


class AccountService:
    def __init__(self, api_client: APIClient, cano: str, acnt_prdt_cd: str) -> None:
        self.api_client = api_client
        self.cano = cano
        self.acnt_prdt_cd = acnt_prdt_cd

    def get_snapshot(self, symbol: str = TARGET_SYMBOL) -> AccountSnapshot:
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        data = self.api_client.get(BALANCE_ENDPOINT, TR_ID_BALANCE_DEMO, params=params)
        output1 = data.get("output1", []) or []
        output2 = data.get("output2", []) or []

        holding = self._parse_holding(output1, symbol)

        # CHANGED:
        # cash_available 는 이제 inquire-balance output2 에서 읽지 않는다.
        # 오직 inquire-psbl-order 의 ord_psbl_cash 만 사용한다.
        cash_available = self._get_orderable_cash(symbol)

        total_eval_amount = _extract_summary_int(output2, "tot_evlu_amt", "scts_evlu_amt")

        return AccountSnapshot(
            cash_available=cash_available,
            total_eval_amount=total_eval_amount,
            holding=holding,
            raw_output1=output1,
            raw_output2=output2,
        )

    def _get_orderable_cash(self, symbol: str) -> int | None:
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": symbol,
            "ORD_UNPR": "0",
            "ORD_DVSN": "01",  # 시장가 기준 조회
            "CMA_EVLU_AMT_ICLD_YN": "Y",
            "OVRS_ICLD_YN": "Y",
        }

        data = self.api_client.get(
            PSBL_ORDER_ENDPOINT,
            TR_ID_PSBL_ORDER_DEMO,
            params=params,
        )

        output = data.get("output", {}) or {}
        value = _first_int(output, "ord_psbl_cash")

        return value if value != 0 else None

    @staticmethod
    def _parse_holding(rows: list[dict[str, Any]], symbol: str) -> HoldingSnapshot | None:
        for row in rows:
            row_symbol = str(row.get("pdno") or row.get("PDNO") or "").strip()
            if row_symbol != symbol:
                continue

            return HoldingSnapshot(
                symbol=symbol,
                qty=_first_int(row, "hldg_qty", "hold_qty", "cblc_qty"),
                sellable_qty=_first_int(row, "ord_psbl_qty", "sell_psbl_qty", "ord_qty"),
                avg_price=_first_int(
                    row,
                    "pchs_avg_pric",
                    "pchs_avg_pric",
                    "pchs_avg_pric",
                    "purchase_avg_price",
                ),
            )

        return None


def _extract_summary_int(rows: list[dict[str, Any]], *keys: str) -> int | None:
    if not rows:
        return None

    row = rows[0]
    value = _first_int(row, *keys)
    return value if value != 0 else None


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
