# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app locally
streamlit run app.py

# Install dependencies
pip install -r requirements.txt
```

There are no tests or linting scripts defined. The app is deployed to Streamlit Community Cloud (free tier) — the live version updates when `main` is pushed to GitHub.

## Architecture

This is a **decoupled 4-module Streamlit app** for data-driven investment dip-buying decisions. Data flows strictly one-way: `data_loader → analyzer → capital_manager → app.py (UI)`.

### Module roles

| File | Role | Key output |
|---|---|---|
| `src/data_loader.py` | Fetch & cache raw market data | `get_stock_data(ticker)` → DataFrame with `Close`, `MA240`, `MA240_Slope`; `get_market_evidence()` → global evidence dict |
| `src/analyzer.py` | Compute bias%, slope, trend diagnosis | `analyze_stock(df)` → dict with `Current_Price`, `MA240`, `Bias_%`, `Is_Downtrend`, `Narrative` |
| `src/capital_manager.py` | Generate staged buy plan with cost averaging | `calculate_investment_plan(...)` → dict with `summary` and `table` DataFrame (8 columns) |
| `app.py` | Streamlit UI, session state, ticker normalization | Renders Global Command Center + Master Table |

### Critical data contracts

**`get_stock_data(ticker)`** returns a DataFrame with columns: `Close`, `MA240`, `MA240_Slope`. If data is unavailable, returns `None`. The 240-day window uses `expanding().mean()` as fallback when history < 240 days (common for newer ETFs — treat MA240 as unreliable in those cases).

**`analyze_stock(df)`** returns exactly these 5 keys — `capital_manager` depends on all of them:
```python
{'Current_Price', 'MA240', 'Bias_%', 'Is_Downtrend', 'Narrative'}
```

**`calculate_investment_plan(total_budget, n_batches, analysis, evidence, is_us)`** — the `is_us` flag controls whether FX conversion (USD/TWD) applies to the shares calculation. It is derived in `app.py` as `not (symbol.endswith(".TW") or symbol.endswith(".TWO"))` — covers both TWSE and TPEx-listed securities.

### Ticker normalization

`normalize_ticker()` in `app.py` auto-appends `.TW` to bare 4–6 digit numeric codes (e.g. `0050` → `0050.TW`). Taiwan stocks/ETFs listed on TWSE use `.TW`; TPEx/OTC-listed securities use `.TWO` and must be entered manually.

### Global evidence dict structure

`get_market_evidence()` returns:
```python
{
  'TAIEX_PE': float, 'TAIEX_Label': str, 'PE_Hist': pd.Series,
  'Charts': {name: pd.Series},   # bias% series or raw close
  'Metrics': {name: value},      # latest scalar per indicator
  'FX_Percentile': float,        # USD/TWD 5-year percentile
  'Last_Synced': str
}
```
This dict is cached in `st.session_state['evidence']` for the session lifetime to avoid redundant API calls on every interaction.

### Key business logic

- **Bias%** = `(Price_adj − 240MA_adj) / 240MA_adj × 100` — computed over adjusted (auto_adjust=True) prices to strip dividend distortion.
- **Slope intercept**: if `MA240_Slope < 0` (5-day diff of MA240), the plan is flagged as downtrend and shown as a warning.
- **Staged buy ladder**: each batch steps down by 2% bias from current bias. First batch is capped at current price if target > current.
- **Shares calculation**: `int((batch_twd / fx) // target_price)` — floors to whole shares; Taiwan market lot sizes (1張 = 1000股) are not enforced.
