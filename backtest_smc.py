from __future__ import annotations

from typing import Sequence

from backtest import Backtester, BacktestResult
from core.market_structure import Candle
from main import SMCEngine


class SMCBacktestStrategy:
    """Adapts SMCEngine to the candle-by-candle Backtester contract.

    Only history up to the current index is supplied to SMCEngine. Targets are
    derived from already-confirmed pivots in that history, never from future
    candles.
    """

    def __init__(
        self,
        min_score: float = 70.0,
        min_rr: float = 2.0,
        risk_pct: float = 1.0,
        balance: float = 10_000.0,
        analysis_window: int = 300,
    ) -> None:
        self.engine = SMCEngine(
            min_score=min_score,
            min_rr=min_rr,
            risk_pct=risk_pct,
        )
        if analysis_window < 50:
            raise ValueError("analysis_window must be >= 50")
        self.analysis_window = analysis_window
        self.balance = balance
        # A confirmed setup must be consumed once.  Without this guard the
        # same historical OB can generate a fresh signal after every exit.
        self._used_setups: set[tuple] = set()

    def signal(self, index: int, history: Sequence[Candle]) -> dict | None:
        if len(history) < 10:
            return None

        # Use a bounded rolling history. All data still precedes the signal
        # candle, so this is look-ahead safe while preventing the quadratic
        # growth of repeatedly analyzing the entire multi-year dataset.
        analysis_history = history[-self.analysis_window:]
        structure = self.engine.market_structure.analyze(analysis_history)
        if structure.bias not in {"BUY", "SELL"}:
            return None

        targets = self._targets(structure.to_dict(), structure.bias, history[-1].close)
        if targets is None:
            return None

        result = self.engine.analyze(
            analysis_history,
            balance=self.balance,
            tp1_level=targets[0],
            tp2_level=targets[1],
            structure=structure,
        )

        if result.get("status") != "APPROVED":
            return None

        entry = result.get("entry") or {}
        entry_price = entry.get("entry")
        stop_loss = entry.get("stop_loss")
        tp1 = entry.get("tp1")
        if entry_price is None or stop_loss is None or tp1 is None:
            return None

        order_block = result.get("order_block") or {}
        selected_ob = order_block.get("selected") or {}

        # Order-block/displacement indices are relative to the rolling
        # analysis window. Convert them back to absolute dataset indices
        # before using them as setup identity; otherwise the same historical
        # setup can acquire a different key every time the window advances.
        window_start = max(0, index + 1 - self.analysis_window)
        ob_index = selected_ob.get("index")
        displacement_index = selected_ob.get("displacement_index")
        if ob_index is None or displacement_index is None:
            return None
        setup_key = (
            result["market_structure"]["bias"],
            window_start + int(ob_index),
            window_start + int(displacement_index),
            round(float(entry_price), 10),
            round(float(stop_loss), 10),
        )
        if setup_key in self._used_setups:
            return None

        self._used_setups.add(setup_key)
        return {
            "direction": result["market_structure"]["bias"],
            "entry": entry_price,
            "stop_loss": stop_loss,
            "take_profit": tp1,
            "score": (result.get("score") or {}).get("total", 0.0),
        }

    def diagnose(self, candles: Sequence[Candle]) -> dict[str, int]:
        """Count where candidate signals are filtered during a backtest pass."""
        counts = {
            "history_ready": 0,
            "structure_bias": 0,
            "targets_found": 0,
            "displacement": 0,
            "order_block": 0,
            "entry_approved": 0,
        }

        for i in range(len(candles)):
            history = candles[: i + 1]
            if len(history) < 10:
                continue
            counts["history_ready"] += 1

            analysis_history = history[-self.analysis_window:]
            structure = self.engine.market_structure.analyze(analysis_history)
            if structure.bias not in {"BUY", "SELL"}:
                continue
            counts["structure_bias"] += 1

            targets = self._targets(structure.to_dict(), structure.bias, history[-1].close)
            if targets is None:
                continue
            counts["targets_found"] += 1

            result = self.engine.analyze(
                analysis_history, balance=self.balance,
                tp1_level=targets[0], tp2_level=targets[1],
            )
            displacement = result.get("displacement", {})
            if displacement.get("valid"):
                counts["displacement"] += 1
            order_block = result.get("order_block", {})
            if order_block.get("valid"):
                counts["order_block"] += 1
            if result.get("status") == "APPROVED":
                counts["entry_approved"] += 1

        return counts

    @staticmethod
    def _targets(structure: dict, bias: str, current_price: float) -> tuple[float, float] | None:
        pivots = sorted(structure.get("pivots", []), key=lambda x: x["index"])

        if bias == "BUY":
            # TP1 is the nearest confirmed swing high above price; TP2 is the
            # next farther high. This preserves EntryEngine's tp2 > tp1 rule.
            highs = sorted({p["price"] for p in pivots if p["kind"] == "HIGH" and p["price"] > current_price})
            return (highs[0], highs[1]) if len(highs) >= 2 else None

        if bias == "SELL":
            # For shorts, the nearest lower low is TP1 and the next lower low
            # is TP2, so TP2 < TP1.
            lows = sorted({p["price"] for p in pivots if p["kind"] == "LOW" and p["price"] < current_price}, reverse=True)
            return (lows[0], lows[1]) if len(lows) >= 2 else None

        return None



def run_smc_backtest(
    candles: Sequence[Candle],
    *,
    min_score: float = 70.0,
    min_rr: float = 2.0,
    risk_pct: float = 1.0,
    balance: float = 10_000.0,
    start_index: int = 0,
    analysis_window: int = 300,
) -> BacktestResult:
    strategy = SMCBacktestStrategy(
        min_score=min_score,
        min_rr=min_rr,
        risk_pct=risk_pct,
        balance=balance,
        analysis_window=analysis_window,
    )
    return Backtester().run(candles, strategy.signal, start_index=start_index)
