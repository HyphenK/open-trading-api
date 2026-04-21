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


def _log_open_orders(logger, title: str, orders) -> None:
    logger.info("=" * 68)
    logger.info(title)
    if not orders:
        logger.info("  - no open orders")
        logger.info("=" * 68)
        return

    for order in orders:
        logger.info(
            "  - side=%s order_no=%s branch=%s qty=%s filled=%s unfilled=%s price=%s",
            order.side,
            order.order_no,
            order.order_branch,
            order.order_qty,
            order.filled_qty,
            order.unfilled_qty,
            order.order_price,
        )
    logger.info("=" * 68)


def main() -> None:
    logger = setup_logging()
    credentials = load_credentials()

    logger.info(
        "Emergency order cleanup booted for %s (%s).",
        TARGET_NAME,
        TARGET_SYMBOL,
    )
    logger.info(
        "Loaded credentials for account ending with %s",
        credentials.account_no[-2:],
    )

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

    open_orders_service = OpenOrdersService(
        api_client,
        credentials.cano,
        credentials.acnt_prdt_cd,
    )
    order_service = OrderService(
        api_client,
        credentials.cano,
        credentials.acnt_prdt_cd,
    )

    try:
        open_orders = open_orders_service.get_open_orders(TARGET_SYMBOL)
    except Exception as exc:
        logger.exception("Failed to query open orders for cleanup: %s", exc)
        return

    _log_open_orders(logger, f"Open orders before cleanup for {TARGET_SYMBOL}", open_orders)

    if not open_orders:
        logger.info("No open orders found for %s (%s). Nothing to cancel.", TARGET_NAME, TARGET_SYMBOL)
        return

    cancelled_count = 0
    failed_count = 0

    for order in open_orders:
        if not order.order_no:
            logger.warning("Skipping open order without order_no: %s", order)
            failed_count += 1
            continue

        if order.unfilled_qty <= 0:
            logger.info(
                "Skipping order with non-positive unfilled quantity | order_no=%s qty=%s",
                order.order_no,
                order.unfilled_qty,
            )
            continue

        logger.info(
            "Cancel order request | side=%s order_no=%s branch=%s unfilled_qty=%s price=%s",
            order.side,
            order.order_no,
            order.order_branch,
            order.unfilled_qty,
            order.order_price,
        )

        try:
            result = order_service.cancel_order(
                TARGET_SYMBOL,
                order.order_no,
                order.order_branch,
                order.unfilled_qty,
                order.order_price,
            )
            cancelled_count += 1
            logger.info(
                "Cancel accepted | source_order_no=%s cancel_order_no=%s cancel_time=%s",
                order.order_no,
                result.order_no,
                result.order_time,
            )
        except Exception as exc:
            failed_count += 1
            logger.exception("Cancel failed for source_order_no=%s: %s", order.order_no, exc)

    logger.info(
        "Cancel routine finished | requested=%s accepted=%s failed=%s",
        len(open_orders),
        cancelled_count,
        failed_count,
    )

    logger.info(
        "Waiting %s seconds before verifying remaining open orders.",
        POST_CANCEL_SETTLE_SECONDS,
    )
    time.sleep(POST_CANCEL_SETTLE_SECONDS)

    try:
        remaining = open_orders_service.get_open_orders(TARGET_SYMBOL)
    except Exception as exc:
        logger.exception("Failed to verify open orders after cleanup: %s", exc)
        return

    _log_open_orders(logger, f"Open orders after cleanup for {TARGET_SYMBOL}", remaining)

    if not remaining:
        logger.info("Emergency cleanup complete. No open orders remain for %s.", TARGET_SYMBOL)
        return

    logger.warning("Cleanup finished but %s open order(s) still remain.", len(remaining))


if __name__ == "__main__":
    main()
