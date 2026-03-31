from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PriceBar:
    timestamp: str
    close: float


@dataclass
class TradeResult:
    pnl: float
    fee: float = 0.0


def load_price_series(csv_path: Path) -> list[PriceBar]:
    rows: list[PriceBar] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamp = row.get("timestamp") or row.get("date") or row.get("Date") or ""
            close_raw = row.get("close") or row.get("Close") or row.get("adj_close") or row.get("Adj Close")
            if not timestamp or close_raw in (None, ""):
                continue
            rows.append(PriceBar(timestamp=timestamp, close=float(close_raw)))
    return rows


def summarize_price_series(series: list[PriceBar], window: int = 20) -> dict[str, Any]:
    closes = [bar.close for bar in series]
    if len(closes) < 2:
        return {
            "observations": len(closes),
            "trend": "insufficient-data",
            "latest_close": closes[0] if closes else None,
            "chart": [],
            "metrics": {},
        }

    returns = [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes)) if closes[i - 1] > 0]
    running_peak = closes[0]
    max_drawdown = 0.0
    equity_curve = []
    cumulative = 1.0
    for idx, bar in enumerate(series):
        if idx > 0 and closes[idx - 1] > 0:
            cumulative *= closes[idx] / closes[idx - 1]
        running_peak = max(running_peak, bar.close)
        drawdown = 0.0 if running_peak <= 0 else (bar.close / running_peak) - 1.0
        max_drawdown = min(max_drawdown, drawdown)
        equity_curve.append({"x": bar.timestamp, "y": round(cumulative, 6)})

    trailing = closes[-window:] if len(closes) >= window else closes
    slope = trailing[-1] - trailing[0]
    trend = "uptrend" if slope > 0 else "downtrend" if slope < 0 else "flat"
    avg_return = sum(returns) / len(returns)
    volatility = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns)) if returns else 0.0
    sharpe_like = 0.0 if volatility == 0 else avg_return / volatility

    return {
        "observations": len(closes),
        "trend": trend,
        "latest_close": closes[-1],
        "chart": [{"x": bar.timestamp, "y": round(bar.close, 6)} for bar in series],
        "equity_curve": equity_curve,
        "metrics": {
            "total_return": round(cumulative - 1.0, 6),
            "max_drawdown": round(max_drawdown, 6),
            "average_period_return": round(avg_return, 6),
            "volatility": round(volatility, 6),
            "sharpe_like": round(sharpe_like, 6),
            "window": window,
        },
    }


def summarize_backtest(
    trade_pnls: list[float],
    fees: list[float] | None = None,
    starting_capital: float = 10000.0,
) -> dict[str, Any]:
    fees = fees or [0.0 for _ in trade_pnls]
    if len(fees) != len(trade_pnls):
        raise ValueError("fees length must match trade_pnls length")

    equity = starting_capital
    peak = starting_capital
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    curve = [{"x": 0, "y": round(equity, 6)}]
    drawdowns: list[float] = []

    for idx, (pnl, fee) in enumerate(zip(trade_pnls, fees), start=1):
        net = pnl - fee
        equity += net
        peak = max(peak, equity)
        drawdown = 0.0 if peak <= 0 else (equity / peak) - 1.0
        drawdowns.append(drawdown)
        if net >= 0:
            wins += 1
            gross_profit += net
        else:
            losses += 1
            gross_loss += abs(net)
        curve.append({"x": idx, "y": round(equity, 6)})

    trades = len(trade_pnls)
    net_profit = equity - starting_capital
    profit_factor = gross_profit / gross_loss if gross_loss else None
    expectancy = net_profit / trades if trades else 0.0

    return {
        "trades": trades,
        "net_profit": round(net_profit, 6),
        "win_rate": round((wins / trades) if trades else 0.0, 6),
        "profit_factor": round(profit_factor, 6) if profit_factor is not None else None,
        "expectancy": round(expectancy, 6),
        "max_drawdown": round(min(drawdowns) if drawdowns else 0.0, 6),
        "ending_equity": round(equity, 6),
        "equity_curve": curve,
    }


def sample_strategy_report() -> dict[str, Any]:
    sample_prices = [
        PriceBar("2026-01-01", 100.0),
        PriceBar("2026-01-02", 101.2),
        PriceBar("2026-01-03", 103.0),
        PriceBar("2026-01-04", 102.4),
        PriceBar("2026-01-05", 105.1),
        PriceBar("2026-01-06", 107.8),
    ]
    market = summarize_price_series(sample_prices, window=4)
    backtest = summarize_backtest([120.0, -45.0, 80.0, 35.0], fees=[2.0, 2.0, 2.0, 2.0])
    return {
        "market": market,
        "backtest": backtest,
        "notes": [
            "Use these summaries as a reporting layer, not as proof of deployable edge.",
            "For serious research, combine this with out-of-sample testing, fees, slippage, and position sizing.",
        ],
    }
