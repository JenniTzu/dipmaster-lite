# 檔案位置： src/capital_manager.py
import pandas as pd

def calculate_investment_plan(total_budget, n_batches, analysis, evidence, is_us=True):
    """精算師模組：產出 8 欄位實證決策總表"""
    is_downtrend = analysis.get('Is_Downtrend', False)
    # 美股用即時匯率換算；台股 fx=1（直接以台幣計算）
    fx = evidence.get('Metrics', {}).get('美元匯率', 32.0) if is_us else 1.0

    current_price = analysis.get('Current_Price', 0)
    ma240 = analysis.get('MA240', current_price)
    current_bias = analysis.get('Bias_%', 0)

    if current_price <= 0:
        return {"summary": {"allocated": 0, "usage": 0, "is_downtrend": is_downtrend}, "table": pd.DataFrame()}

    batch_twd = total_budget / n_batches if n_batches > 0 else 0
    cost_col = "加權均成 (USD/股)" if is_us else "加權均成 (TWD/股)"
    plan = []
    accumulated_shares = 0
    accumulated_cost_twd = 0

    for i in range(n_batches):
        target_bias = current_bias - (i * 2.0)
        target_price = ma240 * (1 + target_bias / 100) if ma240 else current_price

        if i == 0 and target_price > current_price:
            target_price = current_price

        if target_price <= 0:
            continue

        # 台股支援零股交易，與美股同樣以整股計算
        shares = int((batch_twd / fx) // target_price)
        if shares <= 0:
            continue

        batch_cost_twd = shares * target_price * fx
        usd_cost = shares * target_price if is_us else 0

        accumulated_shares += shares
        accumulated_cost_twd += batch_cost_twd
        w_avg_cost = (accumulated_cost_twd / fx) / accumulated_shares

        plan.append({
            "階梯": f"第 {i+1} 批",
            "觸發條件 (Bias%)": f"{target_bias:.1f}%",
            "目標成交價": round(target_price, 2),
            "投入金額 (TWD)": round(batch_cost_twd, 0),
            "建議買入 (股)": shares,
            "美金原幣 (USD)": round(usd_cost, 2) if is_us else "-",
            "累積 (股)": accumulated_shares,
            cost_col: round(w_avg_cost, 2)
        })

    df_plan = pd.DataFrame(plan)

    return {
        "summary": {
            "allocated": accumulated_cost_twd,
            "usage": (accumulated_cost_twd / total_budget * 100) if total_budget > 0 else 0,
            "is_downtrend": is_downtrend
        },
        "table": df_plan
    }
