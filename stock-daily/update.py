"""Refresh the price files that the stock-daily and stock-compare pages read.

For every entry in symbols.json this writes data/<symbol>.json with about
five years of daily closing prices from Yahoo Finance (via yfinance), plus a
fundamentals snapshot for companies. It also writes data/fx.json with the
latest exchange rates to the US dollar for every currency in use.
Run by .github/workflows/stock-daily.yml; can also be run by hand:

    pip install yfinance
    python stock-daily/update.py
"""
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

# Yahoo field name -> name used in the data files.
FUNDAMENTALS = {
    "trailingPE": "peTrailing",
    "forwardPE": "peForward",
    "enterpriseToEbitda": "evToEbitda",
    "priceToSalesTrailing12Months": "priceToSales",
    "priceToBook": "priceToBook",
    "grossMargins": "grossMargin",
    "operatingMargins": "operatingMargin",
    "profitMargins": "netMargin",
    "returnOnEquity": "returnOnEquity",
    "revenueGrowth": "revenueGrowth",
    "totalRevenue": "revenue",
    "totalDebt": "totalDebt",
    "totalCash": "totalCash",
    "dividendYield": "dividendYieldPct",
    "targetMeanPrice": "targetMean",
    "numberOfAnalystOpinions": "analystCount",
    "recommendationKey": "recommendation",
    "financialCurrency": "financialCurrency",
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def session():
    # Yahoo rejects plain scripted requests; yfinance's browser-like session gets through.
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        return None
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return curl_requests.Session(impersonate="chrome", **({"verify": ca} if ca else {}))


def clean(value):
    """Keep JSON-safe values only: Yahoo sometimes returns NaN or 'Infinity'."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    return value if isinstance(value, str) else None


def fetch(entry, sess, previous):
    ticker = yf.Ticker(entry["symbol"], session=sess)
    hist = ticker.history(period="5y", interval="1d", auto_adjust=False)
    hist = hist.dropna(subset=["Close"])
    if len(hist) < 30:
        raise RuntimeError(f"only {len(hist)} rows returned")
    out = {
        "symbol": entry["symbol"],
        "name": entry.get("name", entry["symbol"]),
        "localName": entry.get("localName", ""),
        "kind": entry.get("kind", "stock"),
        "exchange": previous.get("exchange", ""),
        "currency": previous.get("currency", ""),
        "marketCap": previous.get("marketCap"),
        "updated": now(),
        "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
        "close": [round(float(c), 2) for c in hist["Close"]],
    }
    # Everything below is best-effort: on a failure the last good values are kept.
    try:
        meta = ticker.history_metadata or {}
        out["exchange"] = meta.get("fullExchangeName") or meta.get("exchangeName") or out["exchange"]
        out["currency"] = meta.get("currency") or out["currency"]
    except Exception as err:  # noqa: BLE001
        print(f"  {entry['symbol']}: no metadata ({err})")
    if out["kind"] == "index":
        out["marketCap"] = None
        return out
    try:
        cap = ticker.fast_info.get("marketCap")
        out["marketCap"] = float(cap) if cap else out["marketCap"]
    except Exception as err:  # noqa: BLE001
        print(f"  {entry['symbol']}: no market cap ({err})")
    out["fundamentals"] = previous.get("fundamentals", {})
    out["fundamentalsUpdated"] = previous.get("fundamentalsUpdated", "")
    try:
        info = ticker.info or {}
        found = {ours: clean(info.get(theirs)) for theirs, ours in FUNDAMENTALS.items()}
        if sum(v is not None for v in found.values()) >= 5:
            out["fundamentals"] = found
            out["fundamentalsUpdated"] = now()
        else:
            print(f"  {entry['symbol']}: fundamentals came back empty; kept the previous ones")
    except Exception as err:  # noqa: BLE001
        print(f"  {entry['symbol']}: no fundamentals ({err}); kept the previous ones")
    return out


def fetch_fx(currencies, sess, previous):
    """Units of each currency per one US dollar."""
    rates = dict(previous.get("rates", {}))
    rates["USD"] = 1.0
    for cur in sorted(currencies - {"USD", ""}):
        try:
            hist = yf.Ticker(f"{cur}=X", session=sess).history(period="5d", interval="1d")
            rates[cur] = round(float(hist["Close"].dropna().iloc[-1]), 4)
        except Exception as err:  # noqa: BLE001
            print(f"  no exchange rate for {cur} ({err}); kept the previous one")
    return {"base": "USD", "rates": rates, "updated": now()}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    entries = json.loads((HERE / "symbols.json").read_text(encoding="utf-8"))
    DATA.mkdir(exist_ok=True)
    sess = session()
    failed, currencies = [], set()
    for entry in entries:
        # "^SOX" is saved as "_SOX.json": a caret is awkward in a web address.
        path = DATA / (entry["symbol"].replace("^", "_") + ".json")
        previous = read_json(path)
        try:
            out = fetch(entry, sess, previous)
        except Exception as err:  # noqa: BLE001
            # Keep the previous file so the pages keep showing the last good data.
            print(f"FAILED {entry['symbol']}: {err}")
            failed.append(entry["symbol"])
            currencies.add(previous.get("currency", ""))
            continue
        write_json(path, out)
        currencies.add(out["currency"])
        if out["kind"] == "stock":
            currencies.add(out.get("fundamentals", {}).get("financialCurrency") or "")
        print(f"ok {entry['symbol']}: {len(out['close'])} days to {out['dates'][-1]}, close {out['close'][-1]}")
    fx_path = DATA / "fx.json"
    fx = fetch_fx(currencies, sess, read_json(fx_path))
    write_json(fx_path, fx)
    print(f"ok fx: {fx['rates']}")
    if failed:
        sys.exit(f"{len(failed)} of {len(entries)} symbols failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
