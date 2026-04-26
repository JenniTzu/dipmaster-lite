# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Identity & Deployment

- **App name**: DipMaster Lite — 快速乖離診斷
- **GitHub repo**: `github.com/JenniTzu/dipmaster-lite`
- **Live URL**: `https://dipmaster-lite-b8v8na4gubqcmum7urzhv2.streamlit.app/`
- **Platform**: Streamlit Community Cloud (free tier) — pushes to `main` auto-deploy

## Commands

```bash
# Run locally
streamlit run app.py

# Install dependencies
pip install -r requirements.txt
```

No tests or linting scripts defined.

## Architecture

Decoupled 4-module app. Data flows one-way: `data_loader → analyzer → capital_manager → app.py`.

| File | Role | Key output |
|---|---|---|
| `src/data_loader.py` | Fetch market data (parallel) | `get_stock_data(ticker)` → DataFrame; `get_market_evidence()` → evidence dict |
| `src/analyzer.py` | Compute bias%, slope, trend | `analyze_stock(df)` → 5-key dict |
| `src/capital_manager.py` | Generate staged buy plan | `calculate_investment_plan(...)` → summary + table DataFrame |
| `app.py` | Streamlit UI + ticker normalization | Global dashboard + Master Table |

## Critical Data Contracts

**`get_stock_data(ticker)`** → DataFrame with `Close`, `MA240`, `MA240_Slope`. Returns `None` if unavailable. Uses `expanding().mean()` fallback when history < 240 days (new ETFs) — MA240 unreliable in that case.

**`analyze_stock(df)`** → exactly these 5 keys (`capital_manager` depends on all):
```python
{'Current_Price', 'MA240', 'Bias_%', 'Is_Downtrend', 'Narrative'}
```

**`calculate_investment_plan(total_budget, n_batches, analysis, evidence, is_us)`** — `is_us` is derived in `app.py` as `not (symbol.endswith(".TW") or symbol.endswith(".TWO"))`. Covers both TWSE (`.TW`) and TPEx (`.TWO`) securities.

## Ticker Normalization

`normalize_ticker()` in `app.py` auto-appends `.TW` to bare 4–6 digit numeric codes (`0050` → `0050.TW`). Tickers already containing `.` are passed through unchanged. TPEx-listed securities (`.TWO`) must be entered manually.

## Data Caching Behaviour

`get_market_evidence()` is cached in `st.session_state['evidence']` for the entire session lifetime. Data refreshes only when the user opens a new session or clicks the **🔄 重新整理** button (which deletes the key and calls `st.rerun()`). There is no TTL or background scheduler — this is intentional since yfinance data is EOD.

`get_market_evidence()` fetches 5 tickers (SPY, QQQ, ^TWII, ^VIX, TWD=X) in parallel via `ThreadPoolExecutor(max_workers=5)`. TWD=X is fetched with `period="5y"` to support the FX percentile calculation, avoiding a second API call.

## Global Evidence Dict Structure

```python
{
  'TAIEX_PE': float, 'TAIEX_Label': str, 'PE_Hist': pd.Series,
  'Charts': {name: pd.Series},   # bias% series or raw close (last 365 days)
  'Metrics': {name: value},      # latest scalar per indicator
  'FX_Percentile': float,        # USD/TWD position in 5-year range
  'Last_Synced': str             # datetime string, shown in UI
}
```

## Key Business Logic

- **Bias%** = `(Price_adj − 240MA_adj) / 240MA_adj × 100` using `auto_adjust=True` prices.
- **Slope intercept**: `MA240_Slope < 0` (5-day diff of MA240) flags downtrend.
- **Staged buy ladder**: each batch steps down 2% bias from current. First batch capped at current price if target > current.
- **Shares (US)**: `int((batch_twd / fx) // target_price)` — whole shares.
- **Lots (TW)**: `int(batch_twd // (target_price * TW_LOT_SIZE))` — whole lots (`TW_LOT_SIZE = 1000`). `batch_cost_twd = lots × 1000 × target_price`. Weighted-average-cost is always per-share in TWD. Column labels switch dynamically: `"建議買入 (張)"` / `"累積 (張)"` for TW; `"建議買入 (股)"` / `"累積 (股)"` for US. Batches where budget < 1-lot cost are skipped silently; `app.py` shows a warning when `len(table) < n_batches`.
