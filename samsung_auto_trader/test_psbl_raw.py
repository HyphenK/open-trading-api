from __future__ import annotations

import json

from auth import AuthManager
from api_client import APIClient
from config import MOCK_BASE_URL, TARGET_SYMBOL, load_credentials
from logger import setup_logging


PSBL_ORDER_ENDPOINT = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
TR_ID_PSBL_ORDER_DEMO = "VTTC8908R"  # 모의투자 주문가능조회용으로 commonly used
TEST_PRICE = 210000                  # 테스트용 기준가 (원)
TEST_ORDER_TYPE = "00"               # 00=지정가, 01=시장가


def main() -> None:
    logger = setup_logging()
    credentials = load_credentials()

    logger.info(
        "Loaded credentials for account ending with %s",
        credentials.account_no[-2:],
    )

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

    params = {
        "CANO": credentials.cano,
        "ACNT_PRDT_CD": credentials.acnt_prdt_cd,
        "PDNO": TARGET_SYMBOL,                  # 삼성전자
        "ORD_UNPR": str(TEST_PRICE),            # 테스트 기준 가격
        "ORD_DVSN": TEST_ORDER_TYPE,            # 00=지정가
        "CMA_EVLU_AMT_ICLD_YN": "Y",
        "OVRS_ICLD_YN": "Y",
    }

    logger.info(
        "Requesting raw psbl-order data | endpoint=%s tr_id=%s symbol=%s price=%s ord_dvsn=%s",
        PSBL_ORDER_ENDPOINT,
        TR_ID_PSBL_ORDER_DEMO,
        TARGET_SYMBOL,
        TEST_PRICE,
        TEST_ORDER_TYPE,
    )

    data = api_client.get(
        PSBL_ORDER_ENDPOINT,
        TR_ID_PSBL_ORDER_DEMO,
        params=params,
    )

    print("\n" + "=" * 100)
    print("RAW PSBL-ORDER RESPONSE (FULL JSON)")
    print("=" * 100)
    print(json.dumps(data, ensure_ascii=False, indent=2))

    output = data.get("output", {}) or {}

    print("\n" + "=" * 100)
    print("KEY FIELDS")
    print("=" * 100)

    keys_of_interest = [
        "ord_psbl_cash",      # 주문가능현금
        "max_buy_qty",        # 최대매수가능수량
        "psbl_qty_calc_unpr", # 계산 기준 단가
        "ord_psbl_sbst",      # 주문가능대용금액(있으면)
        "ruse_psbl_amt",      # 재사용 가능 금액류가 있으면
    ]

    for k in keys_of_interest:
        if k in output:
            print(f"{k}: {output.get(k)}")

    print("\n[OUTPUT KEYS]")
    print(sorted(output.keys()))


if __name__ == "__main__":
    main()
