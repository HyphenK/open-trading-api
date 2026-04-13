from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from auth import AuthManager
from api_client import APIClient
from config import (
    OPEN_ORDERS_ENDPOINT,
    TR_ID_OPEN_ORDERS_DEMO,
    TARGET_SYMBOL,
)
from logger import get_logger


KST = ZoneInfo("Asia/Seoul")


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y%m%d")


def main() -> None:
    load_dotenv()
    logger = get_logger()

    auth = AuthManager(logger=logger)
    api_client = APIClient(auth_manager=auth, logger=logger)

    today = today_kst()

    params = {
        "CANO": auth.cano,
        "ACNT_PRDT_CD": auth.acnt_prdt_cd,
        "INQR_STRT_DT": today,
        "INQR_END_DT": today,
        "SLL_BUY_DVSN_CD": "00",
        "INQR_DVSN": "00",
        "PDNO": "",               # 전체 종목 조회
        "CCLD_DVSN": "00",        # 전체
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "INQR_DVSN_2": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    logger.info(
        "Requesting raw daily-ccld data | endpoint=%s tr_id=%s date=%s",
        OPEN_ORDERS_ENDPOINT,
        TR_ID_OPEN_ORDERS_DEMO,
        today,
    )

    data = api_client.get(
        OPEN_ORDERS_ENDPOINT,
        TR_ID_OPEN_ORDERS_DEMO,
        params=params,
    )

    print("\n" + "=" * 100)
    print("RAW RESPONSE (FULL JSON)")
    print("=" * 100)
    print(json.dumps(data, ensure_ascii=False, indent=2))

    output1 = data.get("output1", []) or []
    output2 = data.get("output2", []) or []

    print("\n" + "=" * 100)
    print(f"output1 row count = {len(output1)}")
    print(f"output2 row count = {len(output2)}")
    print("=" * 100)

    if output1:
        print("\n[output1 first row keys]")
        print(sorted(output1[0].keys()))

    samsung_rows = [row for row in output1 if str(row.get("pdno", "")).strip() == TARGET_SYMBOL]

    print("\n" + "=" * 100)
    print(f"SAMSUNG ({TARGET_SYMBOL}) ROW COUNT = {len(samsung_rows)}")
    print("=" * 100)
    print(json.dumps(samsung_rows, ensure_ascii=False, indent=2))

    print("\n" + "=" * 100)
    print("ROW SUMMARY")
    print("=" * 100)
    for i, row in enumerate(output1, start=1):
        pdno = row.get("pdno")
        odno = row.get("odno")
        ord_tmd = row.get("ord_tmd")
        sll_buy_dvsn_cd_name = row.get("sll_buy_dvsn_cd_name")
        ord_qty = row.get("ord_qty")
        tot_ccld_qty = row.get("tot_ccld_qty")
        rmn_qty = row.get("rmn_qty")
        tot_ccld_rmnd_qty = row.get("tot_ccld_rmnd_qty")
        ord_unpr = row.get("ord_unpr")
        print(
            f"[{i}] pdno={pdno} odno={odno} time={ord_tmd} side={sll_buy_dvsn_cd_name} "
            f"ord_qty={ord_qty} filled={tot_ccld_qty} "
            f"rmn_qty={rmn_qty} tot_ccld_rmnd_qty={tot_ccld_rmnd_qty} price={ord_unpr}"
        )


if __name__ == "__main__":
    main()
