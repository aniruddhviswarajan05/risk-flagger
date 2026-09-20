"""
Core rules engine for detecting unusual stock volume patterns.
This module has NO AWS dependencies so it can be tested locally
before you ever touch Lambda/API Gateway.

Flag implemented: VOLUME SPIKE ANOMALY
  Today's volume is significantly higher than the recent average,
  which can indicate unusual interest, an information leak ahead
  of news, or the early stage of a pump-and-dump pattern.

You can add more rules later (see bottom of file for a template),
but per the hackathon judging guide: get ONE flag working end-to-end
before adding more.
"""

import yfinance as yf
from datetime import datetime, timezone


VOLUME_SPIKE_THRESHOLD = 3.0  # today's volume must be >= 3x the 30-day average
LOOKBACK_DAYS = 30


def fetch_stock_data(ticker: str, market: str = "IN"):
    """
    Pulls recent daily price/volume history for a stock.

    market="IN"  -> NSE-listed stock. Yahoo Finance needs a '.NS' suffix
                    (e.g. 'RELIANCE.NS'); added automatically if missing.
    market="US"  -> US-listed stock. Used as-is, no suffix
                    (e.g. 'AAPL', 'TSLA').
    """
    ticker = ticker.upper().strip()

    if market == "IN" and not ticker.endswith(".NS"):
        ticker = ticker + ".NS"
    # market == "US": no suffix needed, yfinance resolves US tickers directly

    stock = yf.Ticker(ticker)
    hist = stock.history(period=f"{LOOKBACK_DAYS + 5}d")  # small buffer for holidays

    if hist.empty:
        raise ValueError(f"No data found for ticker '{ticker}' (market={market}). Check the symbol.")

    return ticker, hist


def check_volume_spike(ticker: str, market: str = "IN") -> dict:
    """
    Runs the volume spike rule against a ticker and returns a
    structured result. This is the function both the Lambda handler
    and your local test script call.

    market: "IN" (NSE, default) or "US".
    """
    ticker, hist = fetch_stock_data(ticker, market)

    # Clean volume data and baseline average
    valid_volumes = hist["Volume"].dropna()
    if not valid_volumes.empty:
        today_volume = int(valid_volumes.iloc[-1])
        baseline = valid_volumes.iloc[:-1]
        avg_volume = float(baseline.mean()) if not baseline.empty else float(today_volume)
    else:
        today_volume = 0
        avg_volume = 0.0

    # Clean close prices (handle NaNs if off-hours / unfinalized)
    valid_closes = hist["Close"].dropna()
    if not valid_closes.empty:
        today_close = float(valid_closes.iloc[-1])
        prev_close = float(valid_closes.iloc[-2]) if len(valid_closes) > 1 else today_close
        price_change_pct = ((today_close - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
    else:
        today_close = 0.0
        prev_close = 0.0
        price_change_pct = 0.0

    ratio = today_volume / avg_volume if avg_volume > 0 else 0
    flagged = ratio >= VOLUME_SPIKE_THRESHOLD

    return {
        "ticker": ticker,
        "market": market,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule": "VOLUME_SPIKE_ANOMALY",
        "flagged": bool(flagged),
        "metrics": {
            "today_volume": int(today_volume),
            "avg_30d_volume": round(float(avg_volume), 2),
            "volume_ratio": round(float(ratio), 2),
            "threshold": VOLUME_SPIKE_THRESHOLD,
            "today_close": round(float(today_close), 2),
            "price_change_pct": round(float(price_change_pct), 2),
        },
    }


# ---------------------------------------------------------------
# TEMPLATE FOR ADDING A SECOND RULE LATER (only if time remains)
# ---------------------------------------------------------------
# def check_price_volume_divergence(ticker: str) -> dict:
#     """Price rising while volume falling = weak/suspicious rally."""
#     ticker, hist = fetch_stock_data(ticker)
#     ... same pattern: compute metrics, return a dict with
#     "flagged", "rule", and "metrics" keys so the rest of the
#     pipeline (Bedrock explainer, DynamoDB storage) doesn't change.
