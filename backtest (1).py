from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Sequence

from core.market_structure import Candle


@dataclass(frozen=True)
class BacktestTrade:
    entry_index: int
    exit_index: int
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    score: float
    pnl_r: float
    outcome: str


@dataclass(frozen=True)
class BacktestResult:
    trades: list[dict]
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate_pct: float
    net_r: float
    profit_factor: float | None
    max_drawdown_r: float

    def to_dict(self) -> dict:
        return asdict(self)


class Backtester:
    """Small deterministic candle-by-candle execution simulator.

    The caller supplies a signal function for each candle index. A signal must
    contain: direction, entry, stop_loss and take_profit. No future candles are
    passed into the signal function, preventing look-ahead in signal creation.
    """

    def run(
        self,
        candles: Sequence[Candle],
        signal_fn: Callable[[int, Sequence[Candle]], dict | None],
        *,
        start_index: int = 0,
    ) -> BacktestResult:
        trades: list[BacktestTrade] = []
        if start_index < 0 or start_index > len(candles):
            raise ValueError("start_index must be within candle range")
        i = start_index

        while i < len(candles):
            signal = signal_fn(i, candles[: i + 1])
            if not signal:
                i += 1
                continue

            direction = signal.get("direction")
            entry = float(signal.get("entry", 0))
            stop = float(signal.get("stop_loss", 0))
            target = float(signal.get("take_profit", 0))
            score = float(signal.get("score", 0))
            score = float(signal.get("score", 0))

            if direction not in {"BUY", "SELL"} or entry <= 0 or stop <= 0 or target <= 0:
                i += 1
                continue
            if direction == "BUY" and not (stop < entry < target):
                i += 1
                continue
            if direction == "SELL" and not (target < entry < stop):
                i += 1
                continue

            risk = abs(entry - stop)
            exit_index = None
            outcome = "TIMEOUT"
            pnl_r = 0.0

            # The signal candle creates a pending limit order.  If the entry
            # is already touched, it fills on this candle; otherwise we wait
            # for a later candle.  No PnL is counted before the fill.
            fill_index = None
            fill_candle = None
            for j in range(i + 1, len(candles)):
                c = candles[j]

                entry_touched = c.low <= entry <= c.high
                if direction == "BUY":
                    invalidated_before_fill = c.low <= stop
                else:
                    invalidated_before_fill = c.high >= stop

                # If both entry and stop are touched on the same candle,
                # count the fill and let the fill-candle execution logic
                # resolve it conservatively as a stop loss.
                if entry_touched:
                    fill_index = j
                    fill_candle = c
                    break

                # If price reaches the protective side without touching the
                # limit entry first, cancel the pending order.
                if invalidated_before_fill:
                    break

            if fill_index is None:
                i += 1
                continue

            # Evaluate the fill candle itself conservatively.  If both stop
            # and target are touched on the fill candle, stop wins.
            c = fill_candle
            if direction == "BUY":
                hit_stop = c.low <= stop
                hit_target = c.high >= target
            else:
                hit_stop = c.high >= stop
                hit_target = c.low <= target

            if hit_stop:
                exit_index = fill_index
                outcome = "LOSS"
                pnl_r = -1.0
            elif hit_target:
                exit_index = fill_index
                outcome = "WIN"
                pnl_r = abs(target - entry) / risk
            else:
                for j in range(fill_index + 1, len(candles)):
                    c = candles[j]
                    if direction == "BUY":
                        hit_stop = c.low <= stop
                        hit_target = c.high >= target
                    else:
                        hit_stop = c.high >= stop
                        hit_target = c.low <= target

                    # Conservative assumption when both are touched in one
                    # candle: stop is hit first.
                    if hit_stop:
                        exit_index = j
                        outcome = "LOSS"
                        pnl_r = -1.0
                        break
                    if hit_target:
                        exit_index = j
                        outcome = "WIN"
                        pnl_r = abs(target - entry) / risk
                        break

            if exit_index is None:
                i += 1
                continue

            trades.append(
                BacktestTrade(
                    entry_index=fill_index,
                    exit_index=exit_index,
                    direction=direction,
                    entry=entry,
                    stop_loss=stop,
                    take_profit=target,
                    score=round(score, 2),
                    pnl_r=round(pnl_r, 6),
                    outcome=outcome,
                )
            )
            i = exit_index + 1

        wins = sum(t.outcome == "WIN" for t in trades)
        losses = sum(t.outcome == "LOSS" for t in trades)
        breakeven = sum(t.outcome == "BREAKEVEN" for t in trades)
        total = len(trades)
        win_rate = (wins / total * 100.0) if total else 0.0
        gross_profit = sum(t.pnl_r for t in trades if t.pnl_r > 0)
        gross_loss = -sum(t.pnl_r for t in trades if t.pnl_r < 0)
        profit_factor = gross_profit / gross_loss if gross_loss else (None if not gross_profit else float("inf"))

        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for trade in trades:
            equity += trade.pnl_r
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)

        return BacktestResult(
            trades=[asdict(t) for t in trades],
            total_trades=total,
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            win_rate_pct=round(win_rate, 2),
            net_r=round(sum((t.pnl_r for t in trades), 0.0), 4),
            profit_factor=None if profit_factor is None else round(profit_factor, 4),
            max_drawdown_r=round(max_dd, 4),
        )
