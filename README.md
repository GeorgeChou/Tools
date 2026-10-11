# Tools

Small self-contained tools, one per subfolder, served with GitHub Pages.

Base URL: `https://georgechou.github.io/Tools/`

| Folder | What it does | Example |
| --- | --- | --- |
| `stock-chart/` | Price chart with range tabs | `stock-chart/?symbol=NASDAQ:NVDA&range=1y` |
| `stock-info/` | Compact strip: price, change, headline stats | `stock-info/?symbol=NASDAQ:NVDA` |
| `stock-fundamentals/` | Valuation, margins, financial statements | `stock-fundamentals/?symbol=NASDAQ:NVDA` |
| `stock-daily/` | Daily-close chart and info strip from price files kept in this repo, for exchanges the TradingView widgets block | `stock-daily/?symbol=4063.T&view=chart` |

## Parameters

The three TradingView tools (`stock-chart`, `stock-info`, `stock-fundamentals`) take:

- `symbol`: TradingView `EXCHANGE:TICKER` (default `NASDAQ:AAPL`)
- `theme`: `light` or `dark` (default `light`)

`stock-chart` also takes `range`: `1d` `1m` `3m` `1y` `5y` `all` (default `1y`).

## Which tool for which exchange

`stock-chart` and `stock-info` use TradingView's free embed widgets. TradingView does
not license every exchange for those widgets: Tokyo (`TSE:`) symbols show "This symbol
is only available on TradingView". `stock-fundamentals` works for Tokyo symbols.

| Exchange | Chart | Info | Fundamentals |
| --- | --- | --- | --- |
| US (`NASDAQ:`) | `stock-chart` | `stock-info` | `stock-fundamentals` |
| Taipei Exchange (`TPEX:`) | `stock-chart` | `stock-info` | `stock-fundamentals` |
| Tokyo (`TSE:`) | `stock-daily` (`view=chart`) | `stock-daily` (`view=info`) | `stock-fundamentals` |

Checked on 2026-10-11 with `NASDAQ:ENTG`, `TPEX:6488` and `TSE:4063`, `4004`, `2802`, `4186`, `3436`.
Other exchanges are untested: open the embed URL in a browser before relying on it.

## stock-daily

A chart and info strip drawn from price files in this repo, with no third-party widget.

- `symbol`: Yahoo Finance symbol, e.g. `4063.T` (default `4063.T`). It must be listed in `stock-daily/symbols.json`.
- `view`: `chart`, `info` or `both` (default `both`)
- `range`: tab opened first: `1m` `3m` `6m` `ytd` `1y` `5y` (default `1y`)
- `theme`: `light` or `dark` (default `light`)

How it works:

- `stock-daily/symbols.json` lists the symbols to track, with English and local names.
- `stock-daily/update.py` downloads about five years of daily closes for each symbol
  from Yahoo Finance (through the `yfinance` package) into `stock-daily/data/<symbol>.json`.
- `.github/workflows/stock-daily.yml` runs that script on weekdays at 07:40 and 21:40 UTC,
  and whenever `symbols.json` changes, then commits the refreshed files. GitHub Pages
  republishes on each commit.
- `stock-daily/index.html` reads the file for the requested symbol and draws the page.

To add a company, add a line to `symbols.json` and commit. The workflow fetches its
prices within a few minutes.

Limits: prices are end-of-day closes, not live. Returns are price-only and exclude
dividends. 52-week highs and lows are closing levels, so they differ from intraday
figures on finance sites. If Yahoo refuses a request, the workflow run fails and the
page keeps showing the last good data; the "Updated" time on the page shows its age.
GitHub pauses scheduled workflows after 60 days with no commits to a repo; re-enable
it from the Actions tab.
