from __future__ import annotations

import json

from auth import AuthManager
from api_client import APIClient
from config import (
    MOCK_BASE_URL,
    TR_ID_BALANCE,
    load_credentials,
)
from logger import setup_logging


def main() -> None:
    logger = setup_logging()
    credentials = load_credentials()

    logger.info(
        "Loaded credentials for account ending with %s",
        credentials.account_no[-2:],
    )

    # auth / api client 구성
    auth_manager = AuthManager(
        base_url=MOCK_BASE_URL,
        app_key=credentials.app_key,
        app_secret=credentials.app_secret,
        logger=logger,
    )

    api_client = APIClient(
        base_url=MOCK_BASE_URL,
        auth_manager=auth_manager,
        logger=logger,
    )

    # 🔥 잔고 조회 파라미터 (account.py 그대로 복붙)
    params = {
        "CANO": credentials.cano,
        "ACNT_PRDT_CD": credentials.acnt_prdt_cd,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",   # ← 현재 코드와 동일
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "Y",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    logger.info("Requesting raw balance data...")

    data = api_client.get(
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        TR_ID_INQUIRE_BALANCE_DEMO,
        params=params,
    )

    # 🔥 전체 raw 출력
    print("\n" + "=" * 100)
    print("RAW RESPONSE (FULL JSON)")
    print("=" * 100)
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # 🔥 output1 (보유 종목)
    output1 = data.get("output1", []) or []
    print("\n" + "=" * 100)
    print(f"output1 (holdings) count = {len(output1)}")
    print("=" * 100)

    for i, row in enumerate(output1, start=1):
        print(f"[{i}] {json.dumps(row, ensure_ascii=False)}")

    # 🔥 output2 (계좌 요약)
    output2 = data.get("output2", []) or []
    print("\n" + "=" * 100)
    print(f"output2 (summary) count = {len(output2)}")
    print("=" * 100)

    if output2:
        summary = output2[0]
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        # 🔥 핵심 필드만 따로 출력
        print("\n[KEY FIELDS]")
        keys_of_interest = [
            "dnca_tot_amt",     # 예수금
            "ord_psbl_cash",    # 주문가능현금 (있을 수도 있음)
            "nrcvb_buy_amt",    # 미수 관련
            "tot_evlu_amt",     # 총 평가금액
            "bfdy_tot_asst_evlu_amt",
        ]

        for k in keys_of_interest:
            print(f"{k}: {summary.get(k)}")


if __name__ == "__main__":
    main()
