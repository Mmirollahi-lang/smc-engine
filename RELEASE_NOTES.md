# SMC Engine 0.1.0-rc1

## Included
- Market Structure: pivots, HH/HL/LH/LL, BOS, CHoCH
- Liquidity: equal highs/lows and wick-reclaim sweeps
- Displacement detection
- Order Block detection
- FVG detection
- Entry and R:R validation
- Fixed-risk position sizing
- Setup scoring and mentor explanation
- End-to-end SMC backtest adapter
- CSV CLI runner

## Validation
- Full regression suite: 27 passed.
- End-to-end synthetic harness runs without runtime errors.

## Important limitation
The included synthetic harness is a software-validation fixture, not evidence of trading profitability. No claim of live-market performance is made. Before live use, run the engine on clean historical data with a defined train/validation/test split and realistic fees, slippage, spread, and execution assumptions.


## Stage 3 — Parameter robustness

- Added `Backtester.run(..., start_index=...)` for out-of-sample evaluation with full historical warm-up.
- Added `optimize.py` for deterministic grid search over `min_score` and `min_rr`.
- Training selection uses net-R / max-drawdown rather than raw win rate.
- Validation is evaluated only after the train/validation split.
- Added `run_optimization.py` and optimizer tests.
- Current 1000-candle sample: training selected `min_score=65`, `min_rr=1.5`, but the holdout contains only 1 trade, so it is **not sufficient evidence** for deploying those parameters.
