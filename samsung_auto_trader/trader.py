from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import datetime

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
)
from market_data import MarketDataService
from orders import OrderResult, OrderService


class SamsungTrader:
    def __init__(
        self,
        market_data: MarketDataService,
        account: AccountService,
        orders: OrderService,
        logger: logging.Logger,
    ) -> None:
        self.market_data = market_data
        self.account = account
        self.orders = orders
        self.logger = logger

    def run(self) -> None:
        self.logger.info("Trader booted for %s (%s).", TARGET_NAME, TARGET_SYMBOL)

        while True:
            now = datetime.now()
            now_t = now.time()

            if now_t < TRADING_START:
                self.logger.info("Trading window not started yet. Waiting until 09:10.")
                time.sleep(PRE_MARKET_SLEEP_SECONDS)
                continue

            if now_t >= TRADING_END:
                self.logger.info("Trading window ended at 15:30. Program will stop.")
                return

            self._run_cycle()
            time.sleep(POLL_INTERVAL_SECONDS)

    def _run_cycle(self) -> None:
        self.logger.info("Starting trade cycle.")

        current_price = self.market_data.get_current_price(TARGET_SYMBOL)
        self.logger.info("Current price: %s KRW", current_price)

        before_snapshot = self.account.get_snapshot(TARGET_SYMBOL)
        self._log_snapshot("Holdings before order", before_snapshot)

        buy_price = max(1, current_price - BUY_OFFSET_KRW)
        sell_price = current_price + SELL_OFFSET_KRW

        if self._can_place_buy(before_snapshot, buy_price):
            self.logger.info("Buy order request: qty=%s, price=%s", DEFAULT_ORDER_QTY, buy_price)
            buy_result = self.orders.place_buy_limit(TARGET_SYMBOL, DEFAULT_ORDER_QTY, buy_price)
            self._log_order_result(buy_result)
            time.sleep(POST_ORDER_SETTLE_SECONDS)
            after_buy = self.account.get_snapshot(TARGET_SYMBOL)
            self._log_snapshot("Holdings after buy", after_buy)
            self._log_execution_guess("buy", before_snapshot, after_buy)
            working_snapshot = after_buy
        else:
            self.logger.info("Buy order skipped: available cash was not enough or cash could not be parsed.")
            working_snapshot = before_snapshot

        sell_qty = self._sellable_qty(working_snapshot)
        if sell_qty > 0:
            self.logger.info("Sell order request: qty=%s, price=%s", sell_qty, sell_price)
            sell_result = self.orders.place_sell_limit(TARGET_SYMBOL, sell_qty, sell_price)
            self._log_order_result(sell_result)
            time.sleep(POST_ORDER_SETTLE_SECONDS)
            after_sell = self.account.get_snapshot(TARGET_SYMBOL)
            self._log_snapshot("Holdings after sell", after_sell)
            self._log_execution_guess("sell", working_snapshot, after_sell)
        else:
            self.logger.info("Sell order skipped: no sellable Samsung shares were found.")

        self.logger.info("Trade cycle finished.")

    @staticmethod
    def _can_place_buy(snapshot: AccountSnapshot, buy_price: int) -> bool:
        if snapshot.cash_available is None:
            return True
        return snapshot.cash_available >= buy_price * DEFAULT_ORDER_QTY

    @staticmethod
    def _sellable_qty(snapshot: AccountSnapshot) -> int:
        if snapshot.holding is None:
            return 0
        return max(snapshot.holding.sellable_qty, snapshot.holding.qty, 0)

    def _log_snapshot(self, prefix: str, snapshot: AccountSnapshot) -> None:
        holding_dict = asdict(snapshot.holding) if snapshot.holding else None
        self.logger.info(
            "%s | cash_available=%s | total_eval_amount=%s | samsung_holding=%s",
            prefix,
            snapshot.cash_available,
            snapshot.total_eval_amount,
            holding_dict,
        )

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
