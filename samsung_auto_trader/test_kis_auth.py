"""
직접 kis_auth를 사용하여 계좌 조회 테스트
"""
import sys
import os
sys.path.insert(0, '/workspaces/open-trading-api/examples_user')

import kis_auth as ka

# kis_auth를 사용한 계좌 조회 테스트
print("=" * 60)
print("kis_auth direct test")
print("=" * 60)

try:
    # 인증
    print("1. Authenticating...")
    ka.auth()
    trenv = ka.getTREnv()
    
    print(f"   Account: {trenv.my_acct}")
    print(f"   Product: {trenv.my_prod}")
    
    # 모의투자 설정 확인
    print(f"   Is Paper Trading: {ka.isPaperTrading()}")
    
    # 현재가 조회 테스트 (성공하는 것으로 알려짐)
    print("\n2. Current price test...")
    api_url = "/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": "005930"
    }
    try:
        resp = ka._url_fetch(api_url, "FHKST01010100", "", params, postFlag=False)
        if resp.status_code == 200:
            print(f"   ✓ Current price query SUCCESS")
            print(f"   Response: {resp.text[:100]}...")
        else:
            print(f"   ✗ Current price query FAILED: {resp.status_code}")
    except Exception as e:
        print(f"   ✗ Current price query ERROR: {e}")
    
    # 계좌 조회 테스트
    print("\n3. Account balance test...")
    api_url = "/uapi/domestic-stock/v1/trading/inquire-balance"
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",  # 종목별
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",  # 전일매매미포함
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    try:
        resp = ka._url_fetch(api_url, "TTTC8434R", "", params, postFlag=False)
        if resp.status_code == 200 or resp.status_code == 0:
            print(f"   ✓ Account balance query SUCCESS")
            print(f"   Response code: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}...")
        else:
            print(f"   ✗ Account balance query FAILED: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}...")
    except Exception as e:
        print(f"   ✗ Account balance query ERROR: {e}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
