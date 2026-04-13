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
from open_orders import OpenOrder, OpenOrdersService
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

    open_orders = _load_open_orders(logger, open_orders_service)
    if open_orders is None:
        return
    if not open_orders:
        logger.info("No open orders found for %s (%s). Nothing to cancel.", TARGET_NAME, TARGET_SYMBOL)
        return

    _log_open_order_summary(logger, "Open orders before cleanup", open_orders)

    cancelled_count = 0
    for order in open_orders:
        if not order.order_no:
            logger.warning("Skipping open order without order_no: %s", order)
            continue

        logger.info(
            "Cancel order request | order_no=%s branch=%s side=%s unfilled_qty=%s price=%s",
            order.order_no,
            order.order_branch,
            order.side,
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
            logger.exception("Cancel failed for source_order_no=%s: %s", order.order_no, exc)

    logger.info(
        "Submitted %s cancel request(s). Waiting %s seconds before verifying remaining open orders.",
        cancelled_count,
        POST_CANCEL_SETTLE_SECONDS,
    )
    time.sleep(POST_CANCEL_SETTLE_SECONDS)

    remaining = _load_open_orders(logger, open_orders_service, context="after cleanup")
    if remaining is None:
        return
    if not remaining:
        logger.info("Emergency cleanup complete. No open orders remain for %s.", TARGET_SYMBOL)
        return

    logger.warning("Cleanup finished but %s open order(s) still remain.", len(remaining))
    _log_open_order_summary(logger, "Open orders after cleanup", remaining, warning=True)



def _load_open_orders(
    logger,
    open_orders_service: OpenOrdersService,
    context: str = "before cleanup",
) -> list[OpenOrder] | None:
    try:
        orders = open_orders_service.get_open_orders(TARGET_SYMBOL)
        logger.info("Loaded %s open order(s) for %s %s.", len(orders), TARGET_SYMBOL, context)
        return orders
    except Exception as exc:
        logger.exception("Failed to query open orders %s: %s", context, exc)
        return None



def _log_open_order_summary(logger, title: str, orders: list[OpenOrder], warning: bool = False) -> None:
    log_fn = logger.warning if warning else logger.info
    log_fn("%s | count=%s", title, len(orders))
    if not orders:
        log_fn("  - no open orders")
        return

    for order in orders:
        log_fn(
            "  - side=%s order_no=%s branch=%s qty=%s filled=%s unfilled=%s price=%s time=%s",
            order.side,
            order.order_no,
            order.order_branch,
            order.order_qty,
            order.filled_qty,
            order.unfilled_qty,
            order.order_price,
            order.order_time,
        )


if __name__ == "__main__":
    main()
