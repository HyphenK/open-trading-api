from __future__ import annotations

from account import AccountService
from api_client import APIClient
from auth import AuthManager
from config import MOCK_BASE_URL, load_credentials
from logger import setup_logging
from market_data import MarketDataService
from orders import OrderService
from open_orders import OpenOrdersService
from trader import SamsungTrader



def main() -> None:
    logger = setup_logging()
    credentials = load_credentials()

    logger.info("Loaded credentials for account ending with %s", credentials.account_no[-2:])

    auth_manager = AuthManager(
        base_url=MOCK_BASE_URL,
        app_key=credentials.app_key,
        app_secret=credentials.app_secret,
        logger=logger,
    )
    api_client = APIClient(base_url=MOCK_BASE_URL, auth_manager=auth_manager, logger=logger)

    market_data = MarketDataService(api_client)
    account_service = AccountService(api_client, credentials.cano, credentials.acnt_prdt_cd)
    order_service = OrderService(api_client, credentials.cano, credentials.acnt_prdt_cd)
    open_orders_service = OpenOrdersService(api_client, credentials.cano, credentials.acnt_prdt_cd)

    trader = SamsungTrader(market_data, account_service, order_service, open_orders_service, logger)
    trader.run()


if __name__ == "__main__":
    main()
