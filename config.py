from dataclasses import dataclass

@dataclass(frozen=True)
class SMCConfig:
    min_score: float = 70.0
    min_rr: float = 2.0
    risk_pct: float = 1.0
    structure_left: int = 2
    structure_right: int = 2
    structure_min_distance_pct: float = 0.001
    liquidity_tolerance_pct: float = 0.0015
    displacement_atr_period: int = 14
    displacement_min_body_ratio: float = 0.60
    displacement_min_close_location: float = 0.70
    displacement_min_atr_ratio: float = 1.20
