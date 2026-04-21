from __future__ import annotations

import json

from auth import AuthManager
from api_client import APIClient
from config import (
    MOCK_BASE_URL,
    BALANCE_ENDPOINT,
    TR_ID_BALANCE_DEMO,
    load_credentials,
)
from logger import setup_logging


def main():
    logger = setup_logging()
    credentials = load_credentials()

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
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "Y",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    data = api_client.get(
        BALANCE_ENDPOINT,
        TR_ID_BALANCE_DEMO,
        params=params,
    )

    print("\n===== RAW BALANCE RESPONSE =====")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
