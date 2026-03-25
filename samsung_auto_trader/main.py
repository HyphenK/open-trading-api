"""
Main entry point for Samsung Auto Trader.
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after adding to path
import config
from logger import setup_logger
import trader

logger = setup_logger(__name__)


def main():
    """Main entry point."""
    try:
        # Setup logging
        logger.info("Initializing Samsung Auto Trader...")
        
        # Verify configuration
        logger.info(f"Stock: {config.STOCK_NAME} ({config.STOCK_CODE})")
        logger.info(f"Account: {config.GH_ACCOUNT}")
        logger.info(f"API Base URL: {config.BASE_URL}")
        
        # Start trading
        trader.run_trading_loop()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Startup error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


