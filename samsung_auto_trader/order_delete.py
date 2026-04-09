from __future__ import annotations

import time

from api_client import APIClient
from auth import AuthManager
from config import (
    MOCK_BASE_URL,
    POST_CANCEL_SETTLE_SECONDS,
    TARGET_NAME,
    TARGET_SYMBOL,
    load_credentials,
)
from logger import setup_logging
from open_orders import OpenOrdersService
from orders import OrderService


def main() -> None:
    logger = setup_logging()
    credentials = load_credentials()

    logger.info("Emergency order cleanup booted for %s (%s).", TARGET_NAME, TARGET_SYMBOL)
    logger.info("Loaded credentials for account ending with %s", credentials.account_no[-2:])

    auth_manager = AuthManager(
        base_url=MOCK_BASE_URL,
        app_key=credentials.app_key,
        app_secret=credentials.app_secret,
        logger=logger,
    )
    api_client = APIClient(base_url=MOCK_BASE_URL, auth_manager=auth_manager, logger=logger)
    open_orders_service = OpenOrdersService(api_client, credentials.cano, credentials.acnt_prdt_cd)
    order_service = OrderService(api_client, credentials.cano, credentials.acnt_prdt_cd)

    try:
        open_orders = open_orders_service.get_open_orders(TARGET_SYMBOL)
    except Exception as exc:
        logger.exception("Failed to query open orders for cleanup: %s", exc)
        return

    if not open_orders:
        logger.info("No open orders found for %s (%s). Nothing to cancel.", TARGET_NAME, TARGET_SYMBOL)
        return

    logger.info("Found %s open order(s) for %s. Starting cancel routine.", len(open_orders), TARGET_SYMBOL)
    for order in open_orders:
        logger.info(
            "Cancel order request | order_no=%s branch=%s side=%s unfilled_qty=%s price=%s",
            order.order_no,
            order.order_branch,
            order.side,
            order.unfilled_qty,
            order.order_price,
        )
        if not order.order_no:
            logger.warning("Skipping open order without order_no: %s", order)
            continue
        try:
            result = order_service.cancel_order(
                TARGET_SYMBOL,
                order.order_no,
                order.order_branch,
                order.unfilled_qty,
                order.order_price,
            )
            logger.info(
                "Cancel accepted | source_order_no=%s cancel_order_no=%s cancel_time=%s",
                order.order_no,
                result.order_no,
                result.order_time,
            )
        except Exception as exc:
            logger.exception("Cancel failed for source_order_no=%s: %s", order.order_no, exc)

    logger.info("Waiting %s seconds before verifying remaining open orders.", POST_CANCEL_SETTLE_SECONDS)
    time.sleep(POST_CANCEL_SETTLE_SECONDS)

    try:
        remaining = open_orders_service.get_open_orders(TARGET_SYMBOL)
    except Exception as exc:
        logger.exception("Failed to verify open orders after cleanup: %s", exc)
        return

    if not remaining:
        logger.info("Emergency cleanup complete. No open orders remain for %s.", TARGET_SYMBOL)
        return

    logger.warning("Cleanup finished but %s open order(s) still remain.", len(remaining))
    for order in remaining:
        logger.warning(
            "Remaining open order | side=%s order_no=%s branch=%s unfilled_qty=%s price=%s",
            order.side,
            order.order_no,
            order.order_branch,
            order.unfilled_qty,
            order.order_price,
        )


if __name__ == "__main__":
    main()
