# Tools

Small self-contained tools, one per subfolder, served with GitHub Pages.

Base URL: `https://georgechou.github.io/Tools/`

| Folder | What it does | Example |
| --- | --- | --- |
| `stock-chart/` | Price chart with range tabs | `stock-chart/?symbol=NASDAQ:NVDA&range=1y` |
| `stock-info/` | Compact strip: price, change, headline stats | `stock-info/?symbol=NASDAQ:NVDA` |
| `stock-fundamentals/` | Valuation, margins, financial statements | `stock-fundamentals/?symbol=NASDAQ:NVDA` |

## Parameters

All stock tools take:

- `symbol`: TradingView `EXCHANGE:TICKER` (default `NASDAQ:AAPL`)
- `theme`: `light` or `dark` (default `light`)

`stock-chart` also takes `range`: `1d` `1m` `3m` `1y` `5y` `all` (default `1y`).
