from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from core.market_structure import Candle
from backtest_smc import run_smc_backtest


def load_csv(path: str) -> list[Candle]:
    rows=[]
    with open(path, newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            rows.append(Candle(r['timestamp'], float(r['open']), float(r['high']), float(r['low']), float(r['close'])))
    return rows


def main() -> None:
    p=argparse.ArgumentParser(description='SMC Engine backtest runner')
    p.add_argument('csv', help='CSV with timestamp,open,high,low,close')
    p.add_argument('--balance', type=float, default=10000.0)
    p.add_argument('--min-score', type=float, default=70.0)
    p.add_argument('--min-rr', type=float, default=2.0)
    p.add_argument('--risk-pct', type=float, default=1.0)
    p.add_argument('--out', default='backtest_result.json')
    args=p.parse_args()
    candles=load_csv(args.csv)
    result=run_smc_backtest(candles, min_score=args.min_score, min_rr=args.min_rr, risk_pct=args.risk_pct, balance=args.balance)
    payload=result.to_dict()
    Path(args.out).write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    main()
