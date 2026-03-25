"""
Main trading logic and orchestration.
Manages trading window, order execution, and loop rhythm.
"""
from datetime import datetime, time
import time as time_module
import config
import market_data
import account
import orders
from logger import setup_logger

logger = setup_logger(__name__)


class TradingSession:
    """Manages a trading session with proper timing and logging."""
    
    def __init__(self):
        self.start_time = time(config.TRADING_START_HOUR, config.TRADING_START_MINUTE)
        self.end_time = time(config.TRADING_END_HOUR, config.TRADING_END_MINUTE)
        self.session_active = False
        self.trade_count = 0
    
    def is_within_trading_window(self) -> bool:
        """Check if current time is within trading window (KST)."""
        now = datetime.now(config.KST).time()
        return self.start_time <= now <= self.end_time
    
    def log_session_status(self) -> None:
        """Log current session status."""
        now = datetime.now(config.KST)
        is_trading = self.is_within_trading_window()
        
        if is_trading and not self.session_active:
            logger.info("=" * 60)
            logger.info(f"🟢 TRADING WINDOW OPENED at {now.strftime('%H:%M:%S')}")
            logger.info(f"   Trading will end at {self.end_time.strftime('%H:%M:%S')}")
            logger.info("=" * 60)
            self.session_active = True
        
        elif not is_trading and self.session_active:
            logger.info("=" * 60)
            logger.info(f"🔴 TRADING WINDOW CLOSED at {now.strftime('%H:%M:%S')}")
            logger.info(f"   Total trades executed: {self.trade_count}")
            logger.info("=" * 60)
            self.session_active = False


def execute_single_trade_cycle() -> bool:
    """
    Execute a single trade cycle:
    1. Check current price
    2. Check account balance
    3. Place buy order
    4. Place sell order
    5. Verify execution
    
    Returns:
        True if cycle completed successfully, False otherwise
    """
    logger.info("-" * 60)
    logger.info("Starting new trade cycle...")
    
    try:
        # Step 1: Get current price
        current_price, bid, ask = market_data.get_current_price()
        buy_price, sell_price = market_data.calculate_order_prices(current_price)
        
        # Step 2: Check account balance BEFORE orders
        logger.info("Checking account balance before orders...")
        account_before = account.get_account_balance()
        
        # Step 3: Place buy order
        logger.info(f"Placing buy order for 1 share @ {buy_price:,} KRW...")
        buy_result = orders.place_buy_order(quantity=1, price=buy_price)
        
        if buy_result.status == "FAILED" or buy_result.status == "ERROR":
            logger.warning("Buy order failed, skipping sell order for this cycle")
            return False
        
        # Wait a bit before placing sell order to avoid throttling
        time_module.sleep(config.POLLING_INTERVAL)
        
        # Step 4: Place sell order
        logger.info(f"Placing sell order for 1 share @ {sell_price:,} KRW...")
        sell_result = orders.place_sell_order(quantity=1, price=sell_price)
        
        if sell_result.status == "FAILED" or sell_result.status == "ERROR":
            logger.warning("Sell order failed")
            return False
        
        # Wait before checking account again
        time_module.sleep(config.BALANCE_CHECK_INTERVAL)
        
        # Step 5: Check account balance AFTER orders
        logger.info("Checking account balance after orders...")
        account_after = account.get_account_balance()
        
        # Log balance changes
        balance_change = account_after.balance - account_before.balance
        samsung_change = account_after.samsung_quantity - account_before.samsung_quantity
        
        logger.info(f"Balance change: {balance_change:+,} KRW")
        logger.info(f"Samsung holdings change: {samsung_change:+d} shares")
        
        if samsung_change != 0:
            logger.info(f"✓ Order execution confirmed: Samsung holdings changed by {samsung_change:+d}")
        else:
            logger.info("⚠ No Samsung holdings change detected (order may still be pending)")
        
        logger.info("Trade cycle completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during trade cycle: {e}")
        return False


def run_trading_loop() -> None:
    """
    Main trading loop.
    Runs continuous cycles between trading hours.
    Exits gracefully outside trading window.
    """
    session = TradingSession()
    
    logger.info("=" * 60)
    logger.info("Samsung Auto Trader Started")
    logger.info(f"Trading window: {session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}")
    logger.info(f"Target: {config.STOCK_NAME} ({config.STOCK_CODE})")
    logger.info("=" * 60)
    
    try:
        while True:
            now = datetime.now(config.KST)
            
            # Log session status changes
            session.log_session_status()
            
            # Check if within trading window
            if not session.is_within_trading_window():
                logger.debug(f"Outside trading window ({now.strftime('%H:%M:%S')}), sleeping...")
                time_module.sleep(60)  # Sleep 1 minute outside trading hours
                continue
            
            # Execute trade cycle
            success = execute_single_trade_cycle()
            if success:
                session.trade_count += 1
            
            # Wait before next cycle (respect API rate limits)
            logger.info(f"Waiting {config.POLLING_INTERVAL}s before next cycle...")
            time_module.sleep(config.POLLING_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("🛑 Trading stopped by user")
        logger.info(f"Total trades executed: {session.trade_count}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"\n💥 Fatal error in trading loop: {e}")
        raise
