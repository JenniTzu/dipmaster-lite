# 檔案位置： src/capital_manager.py
import pandas as pd

TW_LOT_SIZE = 1000  # 台股最小交易單位：1 張 = 1,000 股

def calculate_investment_plan(total_budget, n_batches, analysis, evidence, is_us=True):
    """精算師模組：產出 8 欄位實證決策總表"""
    is_downtrend = analysis.get('Is_Downtrend', False)
    fx = evidence.get('Metrics', {}).get('美元匯率', 32.0) if is_us else 1.0

    current_price = analysis.get('Current_Price', 0)
    ma240 = analysis.get('MA240', current_price)
    current_bias = analysis.get('Bias_%', 0)

    if current_price <= 0:
        return {"summary": {"allocated": 0, "usage": 0, "is_downtrend": is_downtrend}, "table": pd.DataFrame()}

    batch_twd = total_budget / n_batches if n_batches > 0 else 0
    buy_col = "建議買入 (股)" if is_us else "建議買入 (張)"
    acc_col = "累積 (股)" if is_us else "累積 (張)"

    plan = []
    accumulated_qty = 0
    accumulated_cost_twd = 0

    for i in range(n_batches):
        target_bias = current_bias - (i * 2.0)
        target_price = ma240 * (1 + target_bias / 100) if ma240 else current_price

        if i == 0 and target_price > current_price:
            target_price = current_price

        if target_price <= 0:
            continue

        if is_us:
            qty = int((batch_twd / fx) // target_price)  # 整股
            if qty <= 0:
                continue
            batch_cost_twd = qty * target_price * fx
            usd_cost = qty * target_price
        else:
            qty = int(batch_twd // (target_price * TW_LOT_SIZE))  # 整張
            if qty <= 0:
                continue
            batch_cost_twd = qty * TW_LOT_SIZE * target_price
            usd_cost = 0

        accumulated_qty += qty
        accumulated_cost_twd += batch_cost_twd

        if is_us:
            w_avg_cost = (accumulated_cost_twd / fx) / accumulated_qty
        else:
            w_avg_cost = accumulated_cost_twd / (accumulated_qty * TW_LOT_SIZE)

        plan.append({
            "階梯": f"第 {i+1} 批",
            "觸發條件 (Bias%)": f"{target_bias:.1f}%",
            "目標成交價": round(target_price, 2),
            "投入金額 (TWD)": round(batch_cost_twd, 0),
            buy_col: qty,
            "美金原幣 (USD)": round(usd_cost, 2) if is_us else "-",
            acc_col: accumulated_qty,
            "加權平均成本 (每股)": round(w_avg_cost, 2)
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