"""Refresh the daily price files that stock-daily/index.html reads.

For every entry in symbols.json this writes data/<symbol>.json with about
five years of daily closing prices from Yahoo Finance (via yfinance).
Run by .github/workflows/stock-daily.yml; can also be run by hand:

    pip install yfinance
    python stock-daily/update.py
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def session():
    # Yahoo rejects plain scripted requests; yfinance's browser-like session gets through.
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        return None
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return curl_requests.Session(impersonate="chrome", **({"verify": ca} if ca else {}))


def fetch(entry, sess):
    ticker = yf.Ticker(entry["symbol"], session=sess)
    hist = ticker.history(period="5y", interval="1d", auto_adjust=False)
    hist = hist.dropna(subset=["Close"])
    if len(hist) < 30:
        raise RuntimeError(f"only {len(hist)} rows returned")
    out = {
        "symbol": entry["symbol"],
        "name": entry.get("name", entry["symbol"]),
        "localName": entry.get("localName", ""),
        "exchange": "",
        "currency": "",
        "marketCap": None,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
        "close": [round(float(c), 2) for c in hist["Close"]],
    }
    # Extras are best-effort: the chart works without them.
    try:
        meta = ticker.history_metadata or {}
        out["exchange"] = meta.get("fullExchangeName") or meta.get("exchangeName") or ""
        out["currency"] = meta.get("currency") or ""
    except Exception as err:  # noqa: BLE001
        print(f"  {entry['symbol']}: no metadata ({err})")
    try:
        cap = ticker.fast_info.get("marketCap")
        out["marketCap"] = float(cap) if cap else None
    except Exception as err:  # noqa: BLE001
        print(f"  {entry['symbol']}: no market cap ({err})")
    return out


def main():
    entries = json.loads((HERE / "symbols.json").read_text(encoding="utf-8"))
    DATA.mkdir(exist_ok=True)
    sess = session()
    failed = []
    for entry in entries:
        try:
            out = fetch(entry, sess)
        except Exception as err:  # noqa: BLE001
            # Keep the previous file so the embed keeps showing the last good data.
            print(f"FAILED {entry['symbol']}: {err}")
            failed.append(entry["symbol"])
            continue
        path = DATA / f"{entry['symbol']}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ok {entry['symbol']}: {len(out['close'])} days to {out['dates'][-1]}, close {out['close'][-1]}")
    if failed:
        sys.exit(f"{len(failed)} of {len(entries)} symbols failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
