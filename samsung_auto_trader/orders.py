"""
Order placement operations: buy, sell, order status.
"""
from typing import Optional, Dict, Any
import config
import api_client
from logger import setup_logger

logger = setup_logger(__name__)


class OrderResult:
    """Represents order result."""
    
    def __init__(self, order_id: str, status: str, quantity: int, price: int):
        self.order_id = order_id
        self.status = status           # Success, Pending, Failed, etc.
        self.quantity = quantity
        self.price = price
        self.message = ""
    
    def __repr__(self) -> str:
        return (
            f"OrderResult(id={self.order_id}, status={self.status}, "
            f"qty={self.quantity}, price={self.price:,})"
        )


def place_buy_order(quantity: int, price: int) -> OrderResult:
    """
    Place a buy order for Samsung Electronics.
    
    Args:
        quantity: number of shares to buy
        price: limit price per share
        
    Returns:
        OrderResult with order details
        
    Raises:
        Exception if order fails
    """
    client = api_client.get_api_client()
    
    # Endpoint to place buy/sell order (지정가 주문)
    path = "/uapi/domestic-stock/v1/trading/order-cash"
    
    # TR_ID for order placement
    tr_id = "TTTC0802U"
    
    # Prepare account info
    account_parts = config.GH_ACCOUNT.split('-')
    cano = account_parts[0]
    acnt_prdt_cd = account_parts[1] if len(account_parts) > 1 else ""
    
    body = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": config.STOCK_CODE,
        "ORD_DVSN": "00",              # 00: Limit order (지정가)
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "ORD_DVSN_NAME": "지정가"       # For log/clarity
    }
    
    try:
        logger.info(f"Placing BUY order: {quantity} shares @ {price:,} KRW")
        response = client.post(path, body, tr_id=tr_id)
        
        # Check for API error
        if client.check_response_error(response):
            error_msg = response.get('msg1', response.get('msg', 'Unknown error'))
            logger.error(f"Buy order failed: {error_msg}")
            return OrderResult("", "FAILED", quantity, price)
        
        # Parse response
        output = response.get('output', {})
        order_id = output.get('ODNO', '')  # Order number
        msg = response.get('msg1', '')
        
        result = OrderResult(order_id, "PENDING", quantity, price)
        result.message = msg
        
        logger.info(f"✓ Buy order placed: Order ID={order_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to place buy order: {e}")
        return OrderResult("", "ERROR", quantity, price)


def place_sell_order(quantity: int, price: int) -> OrderResult:
    """
    Place a sell order for Samsung Electronics.
    
    Args:
        quantity: number of shares to sell
        price: limit price per share
        
    Returns:
        OrderResult with order details
        
    Raises:
        Exception if order fails
    """
    client = api_client.get_api_client()
    
    # Endpoint to place buy/sell order (지정가 주문)
    path = "/uapi/domestic-stock/v1/trading/order-cash"
    
    # TR_ID for order placement (모의투자)
    tr_id = "VTTC0802U"
    
    # Prepare account info
    account_parts = config.GH_ACCOUNT.split('-')
    cano = account_parts[0]
    acnt_prdt_cd = account_parts[1] if len(account_parts) > 1 else ""
    
    body = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": config.STOCK_CODE,
        "ORD_DVSN": "01",              # 01: Sell limit order (지정가 매도)
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "ORD_DVSN_NAME": "지정가"       # For log/clarity
    }
    
    try:
        logger.info(f"Placing SELL order: {quantity} shares @ {price:,} KRW")
        response = client.post(path, body, tr_id=tr_id)
        
        # Check for API error
        if client.check_response_error(response):
            error_msg = response.get('msg1', response.get('msg', 'Unknown error'))
            logger.error(f"Sell order failed: {error_msg}")
            return OrderResult("", "FAILED", quantity, price)
        
        # Parse response
        output = response.get('output', {})
        order_id = output.get('ODNO', '')  # Order number
        msg = response.get('msg1', '')
        
        result = OrderResult(order_id, "PENDING", quantity, price)
        result.message = msg
        
        logger.info(f"✓ Sell order placed: Order ID={order_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to place sell order: {e}")
        return OrderResult("", "ERROR", quantity, price)


def get_order_status(order_id: str) -> Dict[str, Any]:
    """
    Check status of a placed order.
    
    Args:
        order_id: order number
        
    Returns:
        dict with order status details
        
    Raises:
        Exception if API call fails
    """
    client = api_client.get_api_client()
    
    # Endpoint to check unexecuted orders
    path = "/uapi/domestic-stock/v1/trading/inquire-balance"
    
    # TR_ID for balance inquiry (모의투자)
    tr_id = "VTTC8434R"
    
    # Prepare account info
    account_parts = config.GH_ACCOUNT.split('-')
    cano = account_parts[0]
    acnt_prdt_cd = account_parts[1] if len(account_parts) > 1 else ""
    
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "AFHR_FLPR_YN": "N",
        "INQR_DVSN": "01",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_VAL_NK100": ""
    }
    
    try:
        logger.debug(f"Checking status of order {order_id}...")
        response = client.get(path, params, tr_id=tr_id)
        
        if client.check_response_error(response):
            logger.warning(f"Failed to get order status for {order_id}")
            return {}
        
        # Search for the order in response
        output2 = response.get('output2', [])
        if isinstance(output2, list):
            for order in output2:
                if order.get('ODNO', '') == order_id:
                    return {
                        'order_id': order_id,
                        'status': order.get('ord_stat', 'Unknown'),
                        'quantity': int(order.get('qty', 0)),
                        'executed_qty': int(order.get('exec_qty', 0)),
                        'price': int(order.get('ord_unpr', 0))
                    }
        
        logger.debug(f"Order {order_id} not found in recent orders")
        return {}
        
    except Exception as e:
        logger.warning(f"Error checking order status: {e}")
        return {}
