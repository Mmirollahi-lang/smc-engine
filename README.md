# SMC Engine

End-to-end Smart Money Concepts analysis pipeline.

## Modules

- `core/market_structure.py`
- `core/liquidity.py`
- `core/displacement.py`
- `core/order_block.py`
- `core/fvg.py`
- `core/entry_engine.py`
- `core/risk_manager.py`
- `core/scoring.py`
- `core/mentor.py`
- `main.py`

## Pipeline

Market Structure -> Liquidity -> Displacement -> Order Block -> FVG ->
Entry/Targets -> Risk -> Scoring -> Mentor.

The pipeline intentionally returns `WAIT` when downstream information such as
opposing liquidity targets has not been supplied; it does not invent targets.
