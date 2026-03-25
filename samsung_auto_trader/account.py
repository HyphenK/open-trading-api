"""
Account operations: balance, holdings, etc.
"""
from typing import Dict, List, Optional
import config
import api_client
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
    Get account balance and Samsung holdings.
    Uses parameters from backtester reference.
    
    Returns:
        AccountData object with balance and holdings
    """
    client = api_client.get_api_client()
    
    # Endpoint to get holdings
    path = "/uapi/domestic-stock/v1/trading/inquire-balance"
    
    # TR_ID for balance inquiry (TTTC8434R real, VTTC8434R paper - api_client will handle conversion)
    tr_id = "TTTC8434R"
    
    # Prepare account info
    account_parts = config.GH_ACCOUNT.split('-')
    cano = account_parts[0]
    acnt_prdt_cd = account_parts[1] if len(account_parts) > 1 else "01"
    
    # Params from backtester - these are verified working
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "AFHR_FLPR_YN": "N",           # Exclude after-hours
        "OFL_YN": "",                   # OFF-market
        "INQR_DVSN": "02",              # By stock (backtester uses 02)
        "UNPR_DVSN": "01",              # Unit price division
        "FUND_STTL_ICLD_YN": "N",      # Don't include fund settlement
        "FNCG_AMT_AUTO_RDPT_YN": "N",  # Don't auto-repay loan
        "PRCS_DVSN": "01",              # Don't include previous day trades (backtester uses 01)
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    
    try:
        logger.debug(f"Fetching account balance for {cano}...")
        response = client.get(path, params, tr_id=tr_id)
        
        # Check for error
        if client.check_response_error(response):
            raise Exception(f"API error in response")
        
        # Handle kis_auth APIResp or dict response
        if hasattr(response, 'getBody'):
            # kis_auth APIResp
            body = response.getBody()
            output2 = body.output2 if hasattr(body, 'output2') else []
            output1 = body.output1 if hasattr(body, 'output1') else []
        else:
            # Dict response
            output2 = response.get('output2', [])
            output1 = response.get('output1', [])
        
        # Get total available cash from output2
        total_cash = 0
        if output2:
            balance_data = output2[0] if isinstance(output2, list) else output2
            total_cash = int(balance_data.get('nass_amt', 0))
        
        # Find Samsung (005930) in holdings from output1
        samsung_qty = 0
        samsung_value = 0
        
        if output1:
            for holding in output1:
                symbol = holding.get('pdno', '').lstrip('0') or holding.get('pdno', '')
                if symbol == '5930':  # Samsung after lstrip
                    samsung_qty = int(holding.get('hldg_qty', 0))
                    current_price = int(holding.get('prpr', 0))
                    samsung_value = current_price * samsung_qty
                    logger.info(f"Samsung holdings: {samsung_qty} shares @ {current_price} KRW = {samsung_value:,} KRW")
                    break
        
        logger.info(f"Account balance: {total_cash:,} KRW available")
        
        return AccountData(total_cash, samsung_qty, samsung_value)
        
    except Exception as e:
        logger.error(f"Failed to get account balance: {e}")
        raise
