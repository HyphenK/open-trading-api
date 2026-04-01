from __future__ import annotations

import logging
import time
from dataclasses import asdict

from account import AccountService, AccountSnapshot
from config import (
    BUY_OFFSET_KRW,
    DEFAULT_ORDER_QTY,
    POLL_INTERVAL_SECONDS,
    POST_ORDER_SETTLE_SECONDS,
    PRE_MARKET_SLEEP_SECONDS,
    SELL_OFFSET_KRW,
    TARGET_NAME,
    TARGET_SYMBOL,
    TRADING_END,
    TRADING_START,
    now_kst,
)
from market_data import MarketDataService
from open_orders import OpenOrder, OpenOrdersService
from orders import OrderResult, OrderService, get_kospi_tick_size, round_price_down_to_tick, round_price_up_to_tick


class SamsungTrader:
    def __init__(
        self,
        market_data: MarketDataService,
        account: AccountService,
        orders: OrderService,
        open_orders: OpenOrdersService,
        logger: logging.Logger,
    ) -> None:
        self.market_data = market_data
        self.account = account
        self.orders = orders
        self.open_orders = open_orders
        self.logger = logger

    def run(self) -> None:
        self.logger.info("Trader booted for %s (%s).", TARGET_NAME, TARGET_SYMBOL)

        while True:
            now = now_kst()
            now_t = now.time()

            if now_t < TRADING_START:
                self.logger.info(
                    "Trading window not started yet. Waiting until %s KST. now=%s",
                    TRADING_START.strftime("%H:%M"),
                    now.isoformat(timespec="seconds"),
                )
                time.sleep(PRE_MARKET_SLEEP_SECONDS)
                continue

            if now_t >= TRADING_END:
                self.logger.info(
                    "Trading window ended at %s KST. Program will stop. now=%s",
                    TRADING_END.strftime("%H:%M"),
                    now.isoformat(timespec="seconds"),
                )
                return

            self._run_cycle()
            time.sleep(POLL_INTERVAL_SECONDS)

    def _run_cycle(self) -> None:
        self.logger.info("Starting trade cycle.")

        current_price = self.market_data.get_current_price(TARGET_SYMBOL)
        tick_size = get_kospi_tick_size(current_price)
        self.logger.info("Current price: %s KRW | inferred_tick_size=%s", current_price, tick_size)

        before_snapshot = self.account.get_snapshot(TARGET_SYMBOL)
        open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
        self._log_snapshot("Holdings before order", before_snapshot)
        self._log_status_block(before_snapshot, open_orders)

        if open_orders:
            self.logger.info(
                "Open orders detected for %s. Skipping new orders this cycle.",
                TARGET_SYMBOL,
            )
            self.logger.info("Trade cycle finished.")
            return

        raw_buy_price = max(1, current_price - BUY_OFFSET_KRW)
        raw_sell_price = current_price + SELL_OFFSET_KRW
        buy_price = max(1, round_price_down_to_tick(raw_buy_price))
        sell_price = round_price_up_to_tick(raw_sell_price)

        self.logger.info(
            "Price normalized by tick size | current=%s tick=%s raw_buy=%s buy=%s raw_sell=%s sell=%s",
            current_price,
            tick_size,
            raw_buy_price,
            buy_price,
            raw_sell_price,
            sell_price,
        )

        if self._can_place_buy(before_snapshot, buy_price):
            self.logger.info("Buy order request: qty=%s, price=%s", DEFAULT_ORDER_QTY, buy_price)
            buy_result = self.orders.place_buy_limit(TARGET_SYMBOL, DEFAULT_ORDER_QTY, buy_price)
            self._log_order_result(buy_result)
            self.logger.info(
                "Waiting %s seconds before post-buy balance check.",
                POST_ORDER_SETTLE_SECONDS,
            )
            time.sleep(POST_ORDER_SETTLE_SECONDS)
            after_buy = self.account.get_snapshot(TARGET_SYMBOL)
            after_buy_open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
            self._log_snapshot("Holdings after buy", after_buy)
            self._log_status_block(after_buy, after_buy_open_orders)
            self._log_execution_guess("buy", before_snapshot, after_buy)
            working_snapshot = after_buy
        else:
            self.logger.info("Buy order skipped: available cash was not enough or cash could not be parsed.")
            working_snapshot = before_snapshot

        sell_qty = self._sellable_qty(working_snapshot)
        if sell_qty > 0:
            self.logger.info(
                "Sell order request: qty=%s, price=%s | based_on_sellable_qty_only",
                sell_qty,
                sell_price,
            )
            sell_result = self.orders.place_sell_limit(TARGET_SYMBOL, sell_qty, sell_price)
            self._log_order_result(sell_result)
            self.logger.info(
                "Waiting %s seconds before post-sell balance check.",
                POST_ORDER_SETTLE_SECONDS,
            )
            time.sleep(POST_ORDER_SETTLE_SECONDS)
            after_sell = self.account.get_snapshot(TARGET_SYMBOL)
            after_sell_open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
            self._log_snapshot("Holdings after sell", after_sell)
            self._log_status_block(after_sell, after_sell_open_orders)
            self._log_execution_guess("sell", working_snapshot, after_sell)
        else:
            self.logger.info(
                "Sell order skipped: no sellable Samsung shares were found. "
                "holding=%s",
                asdict(working_snapshot.holding) if working_snapshot.holding else None,
            )

        self.logger.info("Trade cycle finished.")

    def _get_open_orders_safe(self, symbol: str) -> list[OpenOrder]:
        try:
            return self.open_orders.get_open_orders(symbol)
        except Exception as exc:
            self.logger.warning("Open-order inquiry failed; continuing without blocking orders: %s", exc)
            return []

    @staticmethod
    def _can_place_buy(snapshot: AccountSnapshot, buy_price: int) -> bool:
        if snapshot.cash_available is None:
            return True
        return snapshot.cash_available >= buy_price * DEFAULT_ORDER_QTY

    @staticmethod
    def _sellable_qty(snapshot: AccountSnapshot) -> int:
        if snapshot.holding is None:
            return 0
        return max(snapshot.holding.sellable_qty, 0)

    def _log_snapshot(self, prefix: str, snapshot: AccountSnapshot) -> None:
        holding_dict = asdict(snapshot.holding) if snapshot.holding else None
        self.logger.info(
            "%s | cash_available=%s | total_eval_amount=%s | samsung_holding=%s",
            prefix,
            snapshot.cash_available,
            snapshot.total_eval_amount,
            holding_dict,
        )

    def _log_status_block(self, snapshot: AccountSnapshot, open_orders: list[OpenOrder]) -> None:
        holding = snapshot.holding
        qty = holding.qty if holding else 0
        sellable_qty = holding.sellable_qty if holding else 0
        avg_price = holding.avg_price if holding else 0
        buy_open = sum(order.unfilled_qty for order in open_orders if order.side == "buy")
        sell_open = sum(order.unfilled_qty for order in open_orders if order.side == "sell")

        lines = [
            "=" * 68,
            f"[STATUS] {now_kst().strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"holding | symbol={TARGET_SYMBOL} qty={qty} sellable_qty={sellable_qty} avg_price={avg_price}",
            f"open_orders | buy_open={buy_open} sell_open={sell_open} total_open={len(open_orders)}",
        ]

        if open_orders:
            for order in open_orders:
                lines.append(
                    "  - "
                    f"side={order.side} order_no={order.order_no} time={order.order_time} "
                    f"qty={order.order_qty} filled={order.filled_qty} unfilled={order.unfilled_qty} "
                    f"price={order.order_price}"
                )
        else:
            lines.append("  - no open orders")

        lines.append("=" * 68)
        self.logger.info("\n%s", "\n".join(lines))

    def _log_order_result(self, result: OrderResult) -> None:
        self.logger.info(
            "%s order accepted | order_no=%s | order_time=%s | qty=%s | price=%s",
            result.side.capitalize(),
            result.order_no,
            result.order_time,
            result.requested_qty,
            result.requested_price,
        )

    def _log_execution_guess(self, side: str, before: AccountSnapshot, after: AccountSnapshot) -> None:
        before_qty = before.holding.qty if before.holding else 0
        after_qty = after.holding.qty if after.holding else 0

        executed = False
        if side == "buy" and after_qty > before_qty:
            executed = True
        if side == "sell" and after_qty < before_qty:
            executed = True

        self.logger.info(
            "Execution check for %s: before_qty=%s, after_qty=%s, executed=%s",
            side,
            before_qty,
            after_qty,
            executed,
        )
