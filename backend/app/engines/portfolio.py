"""Mean-variance portfolio helpers via PyPortfolioOpt."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.engines.investment import project_growth

TWOPLACES = Decimal("0.01")


def _money(v: float | Decimal) -> Decimal:
    return Decimal(str(v)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def load_returns_csv(path: str | Path) -> pd.DataFrame:
    """Load wide CSV of monthly asset returns and convert to price levels.

    PyPortfolioOpt's mean_historical_return / sample_cov expect prices.
    """
    df = pd.read_csv(path)
    for col in list(df.columns):
        if col.lower() in {"date", "month", "period"}:
            df = df.drop(columns=[col])
    returns = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    # Convert simple returns → synthetic price index starting at 100.
    prices = (1 + returns).cumprod() * 100.0
    return prices.dropna(how="any")


def optimize_portfolio(
    prices: pd.DataFrame,
    risk_free_rate: float = 0.05,
) -> dict[str, Any]:
    """Max-Sharpe and min-volatility portfolios + frontier sample + Sharpe.

    `prices` must be a DataFrame of asset price levels (not raw returns).
    """
    from pypfopt import EfficientFrontier, expected_returns, risk_models

    mu = expected_returns.mean_historical_return(prices, frequency=12)
    cov = risk_models.sample_cov(prices, frequency=12)

    ef_sharpe = EfficientFrontier(mu, cov)
    ef_sharpe.max_sharpe(risk_free_rate=risk_free_rate)
    clean_sharpe = ef_sharpe.clean_weights()
    ret_s, vol_s, sharpe_s = ef_sharpe.portfolio_performance(risk_free_rate=risk_free_rate)

    ef_min = EfficientFrontier(mu, cov)
    ef_min.min_volatility()
    clean_min = ef_min.clean_weights()
    ret_m, vol_m, sharpe_m = ef_min.portfolio_performance(risk_free_rate=risk_free_rate)

    # Efficient frontier sample via target returns.
    frontier: list[dict[str, float]] = []
    try:
        targets = np.linspace(float(mu.min()), float(mu.max()), 8)
        for t in targets:
            ef = EfficientFrontier(mu, cov)
            try:
                ef.efficient_return(t)
                r, v, s = ef.portfolio_performance(risk_free_rate=risk_free_rate)
                frontier.append({"return": float(r), "volatility": float(v), "sharpe": float(s)})
            except Exception:
                continue
    except Exception:
        pass

    corpus_15y = project_growth(
        monthly_amount=10000,
        years=15,
        expected_return=float(ret_s),
    )

    return {
        "max_sharpe": {
            "weights": {k: float(v) for k, v in clean_sharpe.items()},
            "expected_return": float(ret_s),
            "volatility": float(vol_s),
            "sharpe": float(sharpe_s),
        },
        "min_volatility": {
            "weights": {k: float(v) for k, v in clean_min.items()},
            "expected_return": float(ret_m),
            "volatility": float(vol_m),
            "sharpe": float(sharpe_m),
        },
        "frontier": frontier,
        "corpus_15y_from_10k_sip": corpus_15y,
    }
