from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from core.market_structure import Candle, MarketStructureEngine
from core.liquidity import LiquiditySweepEngine
from core.displacement import DisplacementEngine
from core.order_block import OrderBlockEngine
from core.fvg import FVGEngine
from core.entry_engine import EntryEngine
from core.risk_manager import RiskManager
from core.scoring import ScoringEngine
from core.mentor import MentorEngine


class SMCEngine:
    """End-to-end deterministic SMC analysis pipeline."""

    def __init__(
        self,
        min_score: float = 70.0,
        min_rr: float = 2.0,
        risk_pct: float = 1.0,
    ) -> None:
        self.market_structure = MarketStructureEngine()
        self.liquidity = LiquiditySweepEngine()
        self.displacement = DisplacementEngine()
        self.order_block = OrderBlockEngine()
        self.fvg = FVGEngine()
        self.entry = EntryEngine(min_rr=min_rr)
        self.risk = RiskManager(risk_pct=risk_pct)
        self.scoring = ScoringEngine(min_score=min_score)
        self.mentor = MentorEngine()

    def analyze(
        self,
        candles: Sequence[Candle],
        balance: float | None = None,
        tp1_level: float | None = None,
        tp2_level: float | None = None,
        structure=None,
    ) -> dict:
        if structure is None:
            structure = self.market_structure.analyze(candles)

        if structure.bias == "NO_TRADE":
            return self._early_result(
                structure.to_dict(),
                "Market structure is not sufficiently defined."
            )

        pivots = [
            self._pivot_from_dict(x)
            for x in structure.pivots
        ]

        liquidity = self.liquidity.analyze(candles, pivots)
        breaks = [
            *[self._break_from_dict(x) for x in structure.bos],
            *[self._break_from_dict(x) for x in structure.choch],
        ]

        displacement = self.displacement.analyze(candles, breaks)

        if not displacement.valid:
            return self._partial_result(
                structure.to_dict(),
                liquidity.to_dict(),
                displacement.to_dict(),
                "Waiting for confirmed displacement."
            )

        displacement_events = [
            self._displacement_from_dict(x)
            for x in displacement.events
        ]

        order_block = self.order_block.analyze(
            candles,
            displacement_events,
            breaks,
        )

        if not order_block.valid:
            return self._partial_result(
                structure.to_dict(),
                liquidity.to_dict(),
                displacement.to_dict(),
                order_block.reason,
                order_block=order_block.to_dict(),
            )

        fvg = self.fvg.analyze(candles, order_block.selected)

        # If explicit targets are not supplied, remain in WAIT rather than
        # inventing liquidity/structure levels.
        entry = self.entry.calculate(
            bias=structure.bias,
            order_block=order_block.selected,
            fvg=fvg.selected,
            tp1_level=tp1_level,
            tp2_level=tp2_level,
        )

        risk = None
        if balance is not None and entry.entry is not None and entry.stop_loss is not None:
            risk = self.risk.calculate(
                balance=balance,
                entry=entry.entry,
                stop_loss=entry.stop_loss,
            )

        setup = {
            "bias": structure.bias,
            "structure_confidence": structure.confidence,
            "liquidity_sweep": bool(liquidity.sweeps),
            "displacement": displacement.valid,
            "displacement_score": (
                displacement.latest["score"] if displacement.latest else 0
            ),
            "order_block": order_block.valid,
            "order_block_score": (
                order_block.selected["score"] if order_block.selected else 0
            ),
            "fvg": bool(fvg.selected),
            "fvg_score": fvg.selected["score"] if fvg.selected else 0,
            "rr_tp1": entry.risk_reward_tp1 or 0,
            "entry_status": entry.status,
            "entry_reason": entry.reason,
            "bos_confirmed": bool(structure.bos),
            "choch_confirmed": bool(structure.choch),
        }

        score = self.scoring.score(setup)
        final_decision = "APPROVE" if entry.status == "APPROVED" and score.decision == "APPROVE" else "REJECT"
        setup["final_decision"] = final_decision
        mentor = self.mentor.explain(setup, score.to_dict())

        return {
            "status": entry.status,
            "decision": final_decision,
            "market_structure": structure.to_dict(),
            "liquidity": liquidity.to_dict(),
            "displacement": displacement.to_dict(),
            "order_block": order_block.to_dict(),
            "fvg": fvg.to_dict(),
            "entry": entry.to_dict(),
            "risk": risk.to_dict() if risk else None,
            "score": score.to_dict(),
            "mentor": mentor.to_dict(),
        }

    @staticmethod
    def _pivot_from_dict(x: dict):
        from core.market_structure import Pivot
        return Pivot(**x)

    @staticmethod
    def _break_from_dict(x: dict):
        from core.market_structure import BreakEvent
        return BreakEvent(**x)

    @staticmethod
    def _displacement_from_dict(x: dict):
        from core.displacement import DisplacementEvent
        return DisplacementEvent(**x)

    @staticmethod
    def _early_result(structure: dict, reason: str) -> dict:
        return {
            "status": "NO_TRADE",
            "market_structure": structure,
            "reason": reason,
        }

    @staticmethod
    def _partial_result(
        structure: dict,
        liquidity: dict,
        displacement: dict,
        reason: str,
        order_block: dict | None = None,
    ) -> dict:
        result = {
            "status": "WAIT",
            "market_structure": structure,
            "liquidity": liquidity,
            "displacement": displacement,
            "reason": reason,
        }
        if order_block is not None:
            result["order_block"] = order_block
        return result
