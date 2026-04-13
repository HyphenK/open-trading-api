from __future__ import annotations

import logging
import time
from dataclasses import asdict

from account import AccountService, AccountSnapshot
from config import (
    BUY_OFFSET_KRW,
    CLOSEOUT_START,
    DEFAULT_ORDER_QTY,
    INITIAL_POSITION,
    MAX_POSITION,
    MIN_POSITION,
    POLL_INTERVAL_SECONDS,
    POST_CANCEL_SETTLE_SECONDS,
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
        self._initialized_today = False
        self._closeout_done_today = False
        self._last_trading_day = None

    def run(self) -> None:
        self.logger.info("Trader booted for %s (%s).", TARGET_NAME, TARGET_SYMBOL)

        while True:
            now = now_kst()
            self._roll_daily_flags_if_needed(now.strftime("%Y%m%d"))
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

            if not self._initialized_today:
                self._initialize_inventory()
                self._initialized_today = True

            if now_t >= CLOSEOUT_START and not self._closeout_done_today:
                self._run_closeout()
                self._closeout_done_today = True
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if self._closeout_done_today:
                self.logger.info(
                    "Closeout already completed for today. Waiting until end of trading window."
                )
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            self._run_cycle()
            time.sleep(POLL_INTERVAL_SECONDS)

    def _roll_daily_flags_if_needed(self, trading_day: str) -> None:
        if self._last_trading_day == trading_day:
            return
        self._last_trading_day = trading_day
        self._initialized_today = False
        self._closeout_done_today = False

    def _initialize_inventory(self) -> None:
        self.logger.info(
            "Inventory bootstrap started | initial=%s min=%s max=%s",
            INITIAL_POSITION,
            MIN_POSITION,
            MAX_POSITION,
        )
        snapshot = self.account.get_snapshot(TARGET_SYMBOL)
        open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
        self._log_snapshot("Holdings before bootstrap", snapshot)
        self._log_status_block(snapshot, open_orders)

        if open_orders:
            self.logger.info("Bootstrap skipped because open orders already exist.")
            return

        holding_qty = self._holding_qty(snapshot)
        shortage = max(INITIAL_POSITION - holding_qty, 0)
        if shortage <= 0:
            self.logger.info("Bootstrap skipped: current holding already meets initial position target.")
            return

        current_price = self.market_data.get_current_price(TARGET_SYMBOL)
        affordable_qty = self._affordable_qty(snapshot, current_price)
        buy_qty = min(shortage, affordable_qty)
        if buy_qty <= 0:
            self.logger.info(
                "Bootstrap skipped: insufficient cash for market buy | holding_qty=%s shortage=%s cash_available=%s current_price=%s",
                holding_qty,
                shortage,
                snapshot.cash_available,
                current_price,
            )
            return

        self.logger.info(
            "Bootstrap market buy request | current_holding=%s target_initial=%s shortage=%s affordable=%s buy_qty=%s est_price=%s",
            holding_qty,
            INITIAL_POSITION,
            shortage,
            affordable_qty,
            buy_qty,
            current_price,
        )
        result = self.orders.place_buy_market(TARGET_SYMBOL, buy_qty)
        self._log_order_result(result)
        self.logger.info("Waiting %s seconds before bootstrap balance check.", POST_ORDER_SETTLE_SECONDS)
        time.sleep(POST_ORDER_SETTLE_SECONDS)
        after_snapshot = self.account.get_snapshot(TARGET_SYMBOL)
        after_open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
        self._log_snapshot("Holdings after bootstrap", after_snapshot)
        self._log_status_block(after_snapshot, after_open_orders)
        self._log_execution_guess("buy", snapshot, after_snapshot)

    def _run_closeout(self) -> None:
        self.logger.info(
            "Closeout window started at %s KST. Cancelling open orders and liquidating sellable shares.",
            CLOSEOUT_START.strftime("%H:%M"),
        )
        open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
        if open_orders:
            self._cancel_open_orders(open_orders)
        else:
            self.logger.info("No open orders to cancel during closeout.")

        self.logger.info("Waiting %s seconds after cancel requests.", POST_CANCEL_SETTLE_SECONDS)
        time.sleep(POST_CANCEL_SETTLE_SECONDS)

        snapshot = self.account.get_snapshot(TARGET_SYMBOL)
        self._log_snapshot("Holdings before closeout liquidation", snapshot)
        self._log_status_block(snapshot, self._get_open_orders_safe(TARGET_SYMBOL))
        sell_qty = self._sell_qty_for_closeout(snapshot)
        if sell_qty <= 0:
            self.logger.info("Closeout liquidation skipped: no sellable quantity.")
            return

        self.logger.info("Closeout market sell request | qty=%s", sell_qty)
        result = self.orders.place_sell_market(TARGET_SYMBOL, sell_qty)
        self._log_order_result(result)
        self.logger.info("Waiting %s seconds before closeout balance check.", POST_ORDER_SETTLE_SECONDS)
        time.sleep(POST_ORDER_SETTLE_SECONDS)
        after_snapshot = self.account.get_snapshot(TARGET_SYMBOL)
        self._log_snapshot("Holdings after closeout liquidation", after_snapshot)
        self._log_status_block(after_snapshot, self._get_open_orders_safe(TARGET_SYMBOL))
        self._log_execution_guess("sell", snapshot, after_snapshot)

    def _run_cycle(self) -> None:
        self.logger.info("Starting trade cycle.")

        current_price = self.market_data.get_current_price(TARGET_SYMBOL)
        tick_size = get_kospi_tick_size(current_price)
        self.logger.info("Current price: %s KRW | inferred_tick_size=%s", current_price, tick_size)

        before_snapshot = self.account.get_snapshot(TARGET_SYMBOL)
        open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
        self._log_snapshot("Holdings before order", before_snapshot)
        self._log_status_block(before_snapshot, open_orders)

        effective_position = self._effective_position(before_snapshot, open_orders)
        holding_qty = self._holding_qty(before_snapshot)
        buy_open_qty, _ = self._open_order_qtys(open_orders)

        max_guard_triggered = False
        if effective_position >= MAX_POSITION and buy_open_qty > 0:
            self.logger.warning(
                "Max position guard triggered by effective position. Cancelling all open buy orders | holding_qty=%s effective_position=%s max=%s buy_open_qty=%s",
                holding_qty,
                effective_position,
                MAX_POSITION,
                buy_open_qty,
            )
            max_guard_triggered = True

        if holding_qty > MAX_POSITION and buy_open_qty > 0:
            self.logger.warning(
                "Max position guard triggered by holding quantity overflow. Cancelling all open buy orders | holding_qty=%s effective_position=%s max=%s buy_open_qty=%s",
                holding_qty,
                effective_position,
                MAX_POSITION,
                buy_open_qty,
            )
            max_guard_triggered = True

        if max_guard_triggered:
            self._cancel_open_orders([order for order in open_orders if order.side == "buy"])
            self.logger.info("Waiting %s seconds after max-guard buy-order cancels.", POST_CANCEL_SETTLE_SECONDS)
            time.sleep(POST_CANCEL_SETTLE_SECONDS)
            before_snapshot = self.account.get_snapshot(TARGET_SYMBOL)
            open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
            self._log_snapshot("Holdings after max-guard cancel", before_snapshot)
            self._log_status_block(before_snapshot, open_orders)
            effective_position = self._effective_position(before_snapshot, open_orders)

        if open_orders:
            self.logger.info("Open orders detected for %s. Skipping new orders this cycle.", TARGET_SYMBOL)
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

        working_snapshot = before_snapshot
        buy_qty = self._buy_qty_for_cycle(before_snapshot, [], buy_price)
        if buy_qty > 0:
            self.logger.info("Buy order request: qty=%s, price=%s", buy_qty, buy_price)
            buy_result = self.orders.place_buy_limit(TARGET_SYMBOL, buy_qty, buy_price)
            self._log_order_result(buy_result)
            self.logger.info("Waiting %s seconds before post-buy balance check.", POST_ORDER_SETTLE_SECONDS)
            time.sleep(POST_ORDER_SETTLE_SECONDS)
            after_buy = self.account.get_snapshot(TARGET_SYMBOL)
            after_buy_open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
            self._log_snapshot("Holdings after buy", after_buy)
            self._log_status_block(after_buy, after_buy_open_orders)
            self._log_execution_guess("buy", before_snapshot, after_buy)
            working_snapshot = after_buy
        else:
            self.logger.info(
                "Buy order skipped: max position reached, open buy exposure already counted, or available cash was not enough | holding_qty=%s effective_position=%s cash_available=%s max_position=%s",
                self._holding_qty(before_snapshot),
                effective_position,
                before_snapshot.cash_available,
                MAX_POSITION,
            )

        sell_qty = self._sell_qty_for_cycle(working_snapshot)
        if sell_qty > 0:
            self.logger.info(
                "Sell order request: qty=%s, price=%s | sellable_qty=%s min_position=%s",
                sell_qty,
                sell_price,
                self._sellable_qty(working_snapshot),
                MIN_POSITION,
            )
            sell_result = self.orders.place_sell_limit(TARGET_SYMBOL, sell_qty, sell_price)
            self._log_order_result(sell_result)
            self.logger.info("Waiting %s seconds before post-sell balance check.", POST_ORDER_SETTLE_SECONDS)
            time.sleep(POST_ORDER_SETTLE_SECONDS)
            after_sell = self.account.get_snapshot(TARGET_SYMBOL)
            after_sell_open_orders = self._get_open_orders_safe(TARGET_SYMBOL)
            self._log_snapshot("Holdings after sell", after_sell)
            self._log_status_block(after_sell, after_sell_open_orders)
            self._log_execution_guess("sell", working_snapshot, after_sell)
        else:
            self.logger.info(
                "Sell order skipped: no sellable Samsung shares above minimum inventory floor. holding=%s",
                asdict(working_snapshot.holding) if working_snapshot.holding else None,
            )

        self.logger.info("Trade cycle finished.")

    def _cancel_open_orders(self, open_orders: list[OpenOrder]) -> None:
        for order in open_orders:
            if not order.order_no:
                self.logger.warning("Skipping cancel for open order without order number: %s", order)
                continue
            self.logger.info(
                "Cancel order request | order_no=%s branch=%s side=%s unfilled_qty=%s price=%s",
                order.order_no,
                order.order_branch,
                order.side,
                order.unfilled_qty,
                order.order_price,
            )
            try:
                self.orders.cancel_order(
                    TARGET_SYMBOL,
                    order.order_no,
                    order.order_branch,
                    order.unfilled_qty,
                    order.order_price,
                )
            except Exception as exc:
                self.logger.warning("Cancel order failed for %s: %s", order.order_no, exc)

    def _get_open_orders_safe(self, symbol: str) -> list[OpenOrder]:
        try:
            return self.open_orders.get_open_orders(symbol)
        except Exception as exc:
            self.logger.error("Open-order inquiry failed; blocking new orders this cycle: %s", exc)
            raise

    @staticmethod
    def _holding_qty(snapshot: AccountSnapshot) -> int:
        if snapshot.holding is None:
            return 0
        return max(snapshot.holding.qty, 0)

    @staticmethod
    def _sellable_qty(snapshot: AccountSnapshot) -> int:
        if snapshot.holding is None:
            return 0
        return max(snapshot.holding.sellable_qty, 0)

    @staticmethod
    def _affordable_qty(snapshot: AccountSnapshot, unit_price: int) -> int:
        if unit_price <= 0:
            return 0
        if snapshot.cash_available is None:
            return 0
        return max(snapshot.cash_available // unit_price, 0)

    @staticmethod
    def _open_order_qtys(open_orders: list[OpenOrder]) -> tuple[int, int]:
        buy_open = sum(max(order.unfilled_qty, 0) for order in open_orders if order.side == "buy")
        sell_open = sum(max(order.unfilled_qty, 0) for order in open_orders if order.side == "sell")
        return buy_open, sell_open

    def _effective_position(self, snapshot: AccountSnapshot, open_orders: list[OpenOrder]) -> int:
        holding_qty = self._holding_qty(snapshot)
        buy_open, sell_open = self._open_order_qtys(open_orders)
        return holding_qty + buy_open - sell_open

    def _buy_qty_for_cycle(self, snapshot: AccountSnapshot, open_orders: list[OpenOrder], buy_price: int) -> int:
        effective_position = self._effective_position(snapshot, open_orders)
        room = max(MAX_POSITION - effective_position, 0)
        if room <= 0:
            return 0
        affordable = self._affordable_qty(snapshot, buy_price)
        if affordable <= 0:
            return 0
        return min(DEFAULT_ORDER_QTY, room, affordable)

    def _sell_qty_for_cycle(self, snapshot: AccountSnapshot) -> int:
        holding_qty = self._holding_qty(snapshot)
        sellable_qty = self._sellable_qty(snapshot)
        inventory_room = max(holding_qty - MIN_POSITION, 0)
        return min(DEFAULT_ORDER_QTY, sellable_qty, inventory_room)

    def _sell_qty_for_closeout(self, snapshot: AccountSnapshot) -> int:
        return self._sellable_qty(snapshot)

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
        buy_open, sell_open = self._open_order_qtys(open_orders)
        effective_position = self._effective_position(snapshot, open_orders)

        lines = [
            "=" * 68,
            f"[STATUS] {now_kst().strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"holding | symbol={TARGET_SYMBOL} qty={qty} sellable_qty={sellable_qty} avg_price={avg_price}",
            f"inventory_limits | initial={INITIAL_POSITION} min={MIN_POSITION} max={MAX_POSITION} effective_position={effective_position}",
            f"open_orders | buy_open={buy_open} sell_open={sell_open} total_open={len(open_orders)}",
        ]

        if open_orders:
            for order in open_orders:
                lines.append(
                    "  - "
                    f"side={order.side} order_no={order.order_no} time={order.order_time} "
                    f"qty={order.order_qty} filled={order.filled_qty} unfilled={order.unfilled_qty} "
                    f"price={order.order_price} branch={order.order_branch}"
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
