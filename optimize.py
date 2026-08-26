from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from math import isfinite
from typing import Sequence

from backtest_smc import run_smc_backtest
from core.market_structure import Candle


@dataclass(frozen=True)
class ParameterResult:
    min_score: float
    min_rr: float
    total_trades: int
    net_r: float
    profit_factor: float | None
    max_drawdown_r: float
    win_rate_pct: float
    train_score: float

    def to_dict(self) -> dict:
        data = asdict(self)
        if data["profit_factor"] is not None and not isfinite(data["profit_factor"]):
            data["profit_factor"] = None
        return data


@dataclass(frozen=True)
class OptimizationResult:
    split_index: int
    train: ParameterResult
    validation: ParameterResult
    leaderboard: list[ParameterResult]

    def to_dict(self) -> dict:
        return {
            "split_index": self.split_index,
            "train": self.train.to_dict(),
            "validation": self.validation.to_dict(),
            "leaderboard": [item.to_dict() for item in self.leaderboard],
        }


def _objective(result) -> float:
    """Risk-adjusted training objective; deliberately avoids raw win rate."""
    if result.total_trades < 5:
        return float("-inf")
    dd = max(result.max_drawdown_r, 1.0)
    return result.net_r / dd


def _evaluate(
    candles: Sequence[Candle],
    *,
    min_score: float,
    min_rr: float,
    start_index: int,
) -> ParameterResult:
    result = run_smc_backtest(
        candles,
        min_score=min_score,
        min_rr=min_rr,
        risk_pct=1.0,
        balance=10_000.0,
        start_index=start_index,
    )
    return ParameterResult(
        min_score=min_score,
        min_rr=min_rr,
        total_trades=result.total_trades,
        net_r=result.net_r,
        profit_factor=result.profit_factor,
        max_drawdown_r=result.max_drawdown_r,
        win_rate_pct=result.win_rate_pct,
        train_score=round(_objective(result), 6),
    )


def optimize_and_validate(
    candles: Sequence[Candle],
    *,
    split_ratio: float = 0.70,
    min_scores: Sequence[float] = (65.0, 70.0, 75.0, 80.0),
    min_rrs: Sequence[float] = (1.5, 2.0, 2.5, 3.0),
) -> OptimizationResult:
    """Tune only on the first segment, then evaluate the winner once on holdout.

    The validation run receives the entire candle history as context but the
    Backtester does not permit signals before split_index. This preserves
    indicator/structure warm-up while keeping future validation candles hidden
    from training decisions.
    """
    if not candles:
        raise ValueError("candles must not be empty")
    if not 0.5 <= split_ratio <= 0.9:
        raise ValueError("split_ratio must be between 0.5 and 0.9")

    split = int(len(candles) * split_ratio)
    if split < 10 or split >= len(candles):
        raise ValueError("dataset is too small for the requested split")

    leaderboard: list[ParameterResult] = []
    for min_score, min_rr in product(min_scores, min_rrs):
        leaderboard.append(
            _evaluate(
                candles,
                min_score=float(min_score),
                min_rr=float(min_rr),
                start_index=0,
            )
        )

    leaderboard.sort(
        key=lambda x: (
            x.train_score,
            x.net_r,
            x.profit_factor if x.profit_factor is not None else -1.0,
            -x.max_drawdown_r,
        ),
        reverse=True,
    )
    winner = leaderboard[0]

    validation_raw = run_smc_backtest(
        candles,
        min_score=winner.min_score,
        min_rr=winner.min_rr,
        risk_pct=1.0,
        balance=10_000.0,
        start_index=split,
    )
    validation = ParameterResult(
        min_score=winner.min_score,
        min_rr=winner.min_rr,
        total_trades=validation_raw.total_trades,
        net_r=validation_raw.net_r,
        profit_factor=validation_raw.profit_factor,
        max_drawdown_r=validation_raw.max_drawdown_r,
        win_rate_pct=validation_raw.win_rate_pct,
        train_score=round(_objective(validation_raw), 6),
    )

    return OptimizationResult(
        split_index=split,
        train=winner,
        validation=validation,
        leaderboard=leaderboard,
    )
