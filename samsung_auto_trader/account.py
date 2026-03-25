"""
Account operations: balance, holdings, etc.
Uses kis_auth directly for API calls (like example code).
"""
import sys
sys.path.insert(0, '/workspaces/open-trading-api/examples_user')

import kis_auth as ka
import config
from logger import setup_logger

logger = setup_logger(__name__)


class AccountData:
    """Represents account data snapshot."""
    
    def __init__(self, balance: int, samsung_quantity: int, samsung_value: int):
        self.balance = balance           # Available balance in KRW
        self.samsung_quantity = samsung_quantity  # Number of shares held
        self.samsung_value = samsung_value        # Market value of Samsung holdings
    
    def __repr__(self) -> str:
        return (
            f"AccountData(balance={self.balance:,} KRW, "
            f"samsung_qty={self.samsung_quantity}, "
            f"samsung_value={self.samsung_value:,} KRW)"
        )


def get_account_balance() -> AccountData:
    """
    Get account balance and Samsung holdings using kis_auth.
    
    Returns:
        AccountData object with balance and holdings
        
    Raises:
        Exception if API call fails
    """
    # Get account info from kis_auth (already configured by auth)
    trenv = ka.getTREnv()
    
    # Endpoint to get holdings (보유종목 조회)
    api_url = "/uapi/domestic-stock/v1/trading/inquire-balance"
    
    # TR_ID for balance inquiry (TTTC8434R real, VTTC8434R paper)
    # kis_auth will auto-convert TTTC8434R to VTTC8434R if isPaperTrading()
    tr_id = "TTTC8434R"
    
    # Prepare params - use backtester reference for proper settings
    params = {
        "CANO": trenv.my_acct,
        "ACNT_PRDT_CD": trenv.my_prod,
        "AFHR_FLPR_YN": "N",         # Exclude after-hours
        "OFL_YN": "",                 # OFF-market 
        "INQR_DVSN": "02",            # By stock (종목별)
        "UNPR_DVSN": "01",            # Unit price division
        "FUND_STTL_ICLD_YN": "N",    # Don't include fund settlement
        "FNCG_AMT_AUTO_RDPT_YN": "N", # Don't auto-repay loan
        "PRCS_DVSN": "01",            # Don't include previous day trades
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    
    try:
        logger.debug(f"Fetching account balance via kis_auth for {trenv.my_acct}...")
        
        # Use kis_auth._url_fetch directly (like example code)
        resp = ka._url_fetch(api_url, tr_id, "", params, postFlag=False)
        
        # Check if response is successful
        if not resp.isOK():
            logger.error(f"API returned error: {resp.ERRstr}")
            raise Exception(f"API error: {resp.ERRstr}")
        
        # Get output2 for summary data (total cash, total equity)
        output2 = resp.getBody().output2
        if not output2:
            logger.warning("No balance data in output2")
            return AccountData(0, 0, 0)
        
        balance_data = output2[0] if isinstance(output2, list) else output2
        
        # Get total available cash (현주문가능금액)
        total_cash = int(balance_data.get("nass_amt", 0))
        
        # Get output1 for holdings (종목별 잔고)
        output1 = resp.getBody().output1
        
        samsung_qty = 0
        samsung_value = 0
        
        # Find Samsung (005930) in holdings
        if output1:
            for holding in output1:
                symbol = holding.get("pdno", "")
                if symbol == "005930":  # Samsung Electronics
                    samsung_qty = int(holding.get("hldg_qty", 0))
                    # Market value = current price * quantity
                    current_price = int(holding.get("prpr", 0))
                    samsung_value = current_price * samsung_qty
                    logger.info(f"Samsung holdings: {samsung_qty} shares @ {current_price} KRW = {samsung_value:,} KRW")
                    break
        
        logger.info(f"Account balance: {total_cash:,} KRW available")
        
        return AccountData(total_cash, samsung_qty, samsung_value)
        
    except Exception as e:
        logger.error(f"Failed to get account balance: {e}")
        raise
