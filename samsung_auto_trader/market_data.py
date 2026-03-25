"""
Market data operations for Samsung Electronics.
Get current price, etc.
"""
from typing import Optional
import config
import api_client
from logger import setup_logger

logger = setup_logger(__name__)

# Cache for last price check (to avoid excessive API calls)
_last_price: Optional[int] = None
_last_price_bid: Optional[int] = None
_last_price_ask: Optional[int] = None


def get_current_price() -> tuple[int, int, int]:
    """
    Get current market price for Samsung Electronics.
    
    Returns:
        tuple: (current_price, bid_price, ask_price) in KRW
        
    Raises:
        Exception if API call fails or price cannot be retrieved
    """
    client = api_client.get_api_client()
    
    # Endpoint to get current quotation (현재가 조회)
    path = "/uapi/domestic-stock/v1/quotations/inquire-price"
    
    # TR_ID for current price inquiry (모의투자)
    tr_id = "FHKST01010100"
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",  # Stock market
        "FID_INPUT_ISCD": config.STOCK_CODE  # Stock code
    }
    
    try:
        logger.debug(f"Fetching current price for {config.STOCK_CODE}...")
        response = client.get(path, params, tr_id=tr_id)
        
        # Check for API error
        if client.check_response_error(response):
            raise Exception(f"API error: {response}")
        
        # Parse response
        output = response.get('output', {})
        current_price = int(output.get('stck_prpr', 0))  # 주식현재가
        bid_price = int(output.get('askp1', 0))          # 매도호가1
        ask_price = int(output.get('bidp1', 0))          # 매수호가1
        
        if current_price == 0:
            raise ValueError("Invalid current price")
        
        logger.info(f"현재가: {current_price:,} KRW | 매도호가: {bid_price:,} | 매수호가: {ask_price:,}")
        
        # Update cache
        global _last_price, _last_price_bid, _last_price_ask
        _last_price = current_price
        _last_price_bid = bid_price
        _last_price_ask = ask_price
        
        return current_price, bid_price, ask_price
        
    except Exception as e:
        logger.error(f"Failed to get current price: {e}")
        raise


def calculate_order_prices(current_price: int) -> tuple[int, int]:
    """
    Calculate buy and sell order prices based on current price.
    
    Args:
        current_price: current market price
        
    Returns:
        tuple: (buy_price, sell_price)
    """
    buy_price = current_price - config.BUY_ORDER_OFFSET
    sell_price = current_price + config.SELL_ORDER_OFFSET
    
    logger.debug(
        f"Order prices - Buy: {buy_price:,} KRW, Sell: {sell_price:,} KRW "
        f"(offset: ±{config.BUY_ORDER_OFFSET:,})"
    )
    
    return buy_price, sell_price
